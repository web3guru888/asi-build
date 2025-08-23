package model

import (
	"context"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/registry"
	"mlops-platform/internal/model/versioning"
)

// ModelLoader handles loading models from local storage or remote registry
type ModelLoader struct {
	cfg        *config.Config
	logger     *logging.Logger
	registry   *registry.Client
	versioning *versioning.ModelVersionManager
	cache      map[string]*LoadedModel
	mu         sync.RWMutex
}

// LoadedModel represents a model that has been loaded into memory
type LoadedModel struct {
	ID         string
	Version    string
	Path       string
	LoadedAt   time.Time
	Format     string
	Metadata   map[string]interface{}
	Handler    ModelHandler
	RefCount   int
	CloseFunc  func() error
}

// ModelHandler defines the interface for interacting with a loaded model
type ModelHandler interface {
	Predict(context.Context, map[string]interface{}) (map[string]interface{}, error)
	HealthCheck() map[string]interface{}
	Close() error
}

// NewModelLoader creates a new model loader instance
func NewModelLoader(cfg *config.Config, logger *logging.Logger, reg *registry.Client, ver *versioning.ModelVersionManager) *ModelLoader {
	return &ModelLoader{
		cfg:        cfg,
		logger:     logger,
		registry:   reg,
		versioning: ver,
		cache:      make(map[string]*LoadedModel),
	}
}

// LoadModel loads a model by ID and version
// It checks local cache first, then attempts to download from registry if not found
func (ml *ModelLoader) LoadModel(ctx context.Context, modelID, version string) (*LoadedModel, error) {
	if modelID == "" {
		return nil, fmt.Errorf("model ID cannot be empty")
	}

	if version == "" {
		version = "latest"
	}

	cacheKey := fmt.Sprintf("%s:%s", modelID, version)
	ml.mu.RLock()
	if cached, exists := ml.cache[cacheKey]; exists {
		cached.RefCount++
		ml.mu.RUnlock()
		ml.logger.Info("model served from cache", "model_id", modelID, "version", version)
		return cached, nil
	}
	ml.mu.RUnlock()

	// Resolve version if "latest" is requested
	resolvedVersion := version
	if version == "latest" {
		latestVersion, err := ml.versioning.GetLatestVersion(ctx, modelID)
		if err != nil {
			ml.logger.Error("failed to get latest version", "model_id", modelID, "error", err)
			return nil, fmt.Errorf("failed to resolve latest version: %w", err)
		}
		resolvedVersion = latestVersion
	}

	// Create model path
	modelPath, err := ml.getModelPath(modelID, resolvedVersion)
	if err != nil {
		ml.logger.Error("failed to get model path", "model_id", modelID, "version", resolvedVersion, "error", err)
		return nil, fmt.Errorf("failed to determine model path: %w", err)
	}

	// Check if model exists locally
	localExists, err := ml.checkModelExists(modelPath)
	if err != nil {
		ml.logger.Warn("error checking local model", "model_id", modelID, "version", resolvedVersion, "error", err)
	}
	if !localExists {
		ml.logger.Info("model not found locally, downloading from registry", "model_id", modelID, "version", resolvedVersion)
		if err := ml.downloadModelFromRegistry(ctx, modelID, resolvedVersion, modelPath); err != nil {
			ml.logger.Error("failed to download model from registry", "model_id", modelID, "version", resolvedVersion, "error", err)
			return nil, fmt.Errorf("failed to download model: %w", err)
		}
	}

	// Load model from filesystem
	loadedModel, err := ml.loadModelFromFS(ctx, modelID, resolvedVersion, modelPath)
	if err != nil {
		ml.logger.Error("failed to load model from filesystem", "model_id", modelID, "version", resolvedVersion, "error", err)
		return nil, fmt.Errorf("failed to load model from path %s: %w", modelPath, err)
	}

	// Store in cache
	ml.mu.Lock()
	ml.cache[cacheKey] = loadedModel
	loadedModel.RefCount = 1
	ml.mu.Unlock()

	ml.logger.Info("model loaded successfully", "model_id", modelID, "version", resolvedVersion, "path", modelPath)
	return loadedModel, nil
}

// UnloadModel unloads a model and removes it from cache
// It decrements the reference counter and only unloads when refcount reaches zero
func (ml *ModelLoader) UnloadModel(modelID, version string) error {
	cacheKey := fmt.Sprintf("%s:%s", modelID, version)
	ml.mu.Lock()
	defer ml.mu.Unlock()

	if model, exists := ml.cache[cacheKey]; exists {
		model.RefCount--
		if model.RefCount <= 0 {
			// Call the close function if defined
			if model.CloseFunc != nil {
				if err := model.CloseFunc(); err != nil {
					ml.logger.Error("error closing model", "model_id", modelID, "version", version, "error", err)
					return fmt.Errorf("failed to close model: %w", err)
				}
			}
			delete(ml.cache, cacheKey)
			ml.logger.Info("model unloaded and removed from cache", "model_id", modelID, "version", version)
		} else {
			ml.logger.Debug("model still has active references", "model_id", modelID, "version", version, "refcount", model.RefCount)
		}
	}
	return nil
}

// GetLoadedModel returns a model from the cache if it exists
func (ml *ModelLoader) GetLoadedModel(modelID, version string) (*LoadedModel, bool) {
	cacheKey := fmt.Sprintf("%s:%s", modelID, version)
	ml.mu.RLock()
	defer ml.mu.RUnlock()

	model, exists := ml.cache[cacheKey]
	return model, exists
}

// ListLoadedModels returns all currently loaded models
func (ml *ModelLoader) ListLoadedModels() []*LoadedModel {
	ml.mu.RLock()
	defer ml.mu.RUnlock()

	models := make([]*LoadedModel, 0, len(ml.cache))
	for _, model := range ml.cache {
		models = append(models, model)
	}
	return models
}

// loadModelFromFS loads a model from the local filesystem
// Currently supports ONNX, TensorFlow SavedModel, and PyTorch formats
func (ml *ModelLoader) loadModelFromFS(ctx context.Context, modelID, version, modelPath string) (*LoadedModel, error) {
	// Read metadata if available
	metadata, err := ml.readMetadata(modelPath)
	if err != nil {
		ml.logger.Warn("no metadata found for model", "model_id", modelID, "version", version, "error", err)
		metadata = make(map[string]interface{})
	}

	// Detect model format
	format, err := ml.detectModelFormat(modelPath)
	if err != nil {
		return nil, fmt.Errorf("failed to detect model format: %w", err)
	}

	// Create appropriate model handler based on format
	var handler ModelHandler
	var closeFunc func() error

	switch strings.ToLower(format) {
	case "onnx":
		handler, closeFunc, err = ml.loadONNXModel(ctx, modelPath)
		if err != nil {
			return nil, fmt.Errorf("failed to load ONNX model: %w", err)
		}
	case "tensorflow", "savedmodel":
		handler, closeFunc, err = ml.loadTensorFlowModel(ctx, modelPath)
		if err != nil {
			return nil, fmt.Errorf("failed to load TensorFlow model: %w", err)
		}
	case "pytorch", "torchscript":
		handler, closeFunc, err = ml.loadPyTorchModel(ctx, modelPath)
		if err != nil {
			return nil, fmt.Errorf("failed to load PyTorch model: %w", err)
		}
	default:
		return nil, fmt.Errorf("unsupported model format: %s", format)
	}

	loadedModel := &LoadedModel{
		ID:         modelID,
		Version:    version,
		Path:       modelPath,
		LoadedAt:   time.Now(),
		Format:     format,
		Metadata:   metadata,
		Handler:    handler,
		CloseFunc:  closeFunc,
		RefCount:   0,
	}

	return loadedModel, nil
}

// downloadModelFromRegistry downloads a model from the model registry
func (ml *ModelLoader) downloadModelFromRegistry(ctx context.Context, modelID, version, targetPath string) error {
	// Create directory structure
	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		return fmt.Errorf("failed to create model directory: %w", err)
	}

	// Download model archive
	archivePath := targetPath + ".tar.gz"
	if err := ml.registry.DownloadModel(ctx, modelID, version, archivePath); err != nil {
		return fmt.Errorf("failed to download model archive: %w", err)
	}
	defer os.Remove(archivePath) // Clean up archive after extraction

	// Extract model
	if err := ml.extractModelArchive(archivePath, targetPath); err != nil {
		return fmt.Errorf("failed to extract model archive: %w", err)
	}

	ml.logger.Info("model downloaded and extracted", "model_id", modelID, "version", version, "path", targetPath)
	return nil
}

// detectModelFormat detects the model format based on file structure and extensions
func (ml *ModelLoader) detectModelFormat(modelPath string) (string, error) {
	info, err := os.Stat(modelPath)
	if err != nil {
		return "", fmt.Errorf("failed to stat model path: %w", err)
	}

	if !info.IsDir() {
		return "", fmt.Errorf("model path must be a directory")
	}

	files, err := os.ReadDir(modelPath)
	if err != nil {
		return "", fmt.Errorf("failed to read model directory: %w", err)
	}

	var hasONNX, hasPB, hasPT, hasMar bool

	for _, file := range files {
		name := strings.ToLower(file.Name())
		if strings.HasSuffix(name, ".onnx") {
			hasONNX = true
		}
		if name == "model.onnx" {
			return "ONNX", nil
		}
		if strings.HasSuffix(name, ".pb") || (file.IsDir() && (name == "saved_model" || name == "variables")) {
			hasPB = true
		}
		if strings.HasSuffix(name, ".pt") || strings.HasSuffix(name, ".pth") || strings.HasSuffix(name, ".torchscript") {
			hasPT = true
		}
		if name == "model.pt" || name == "model.pth" {
			return "PyTorch", nil
		}
		if name == "model.mar" {
			hasMar = true
		}
	}

	if hasONNX {
		return "ONNX", nil
	}
	if hasPB {
		return "TensorFlow", nil
	}
	if hasPT {
		return "PyTorch", nil
	}
	if hasMar {
		return "TorchServe", nil
	}

	// Check for TensorFlow SavedModel signature
	savedModelPath := filepath.Join(modelPath, "saved_model.pb")
	if _, err := os.Stat(savedModelPath); err == nil {
		return "TensorFlow", nil
	}

	return "", fmt.Errorf("unable to detect model format from files in %s", modelPath)
}

// readMetadata reads model metadata from metadata.json file if present
func (ml *ModelLoader) readMetadata(modelPath string) (map[string]interface{}, error) {
	metadataPath := filepath.Join(modelPath, "metadata.json")
	data, err := os.ReadFile(metadataPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("metadata.json not found")
		}
		return nil, err
	}

	var metadata map[string]interface{}
	if err := json.Unmarshal(data, &metadata); err != nil {
		return nil, fmt.Errorf("invalid metadata.json format: %w", err)
	}

	return metadata, nil
}

// extractModelArchive extracts a model archive to the target path
func (ml *ModelLoader) extractModelArchive(archivePath, targetPath string) error {
	file, err := os.Open(archivePath)
	if err != nil {
		return err
	}
	defer file.Close()

	gzReader, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer gzReader.Close()

	tarReader := tar.NewReader(gzReader)

	for {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}

		target := filepath.Join(targetPath, header.Name)
		switch header.Typeflag {
		case tar.TypeDir:
			if _, err := os.Stat(target); err != nil {
				if err := os.MkdirAll(target, 0755); err != nil {
					return err
				}
			}
		case tar.TypeReg:
			f, err := os.OpenFile(target, os.O_CREATE|os.O_RDWR, os.FileMode(header.Mode))
			if err != nil {
				return err
			}

			if _, err := io.Copy(f, tarReader); err != nil {
				f.Close()
				return err
			}
			f.Close()
		}
	}
	return nil
}

// getModelPath returns the filesystem path where a model should be stored
func (ml *ModelLoader) getModelPath(modelID, version string) (string, error) {
	if ml.cfg.ModelStorage.Local.Path == "" {
		return "", fmt.Errorf("local model storage path not configured")
	}

	safeModelID := sanitizePath(modelID)
	safeVersion := sanitizePath(version)

	return filepath.Join(ml.cfg.ModelStorage.Local.Path, safeModelID, safeVersion), nil
}

// checkModelExists checks if a model exists in the local filesystem
func (ml *ModelLoader) checkModelExists(modelPath string) (bool, error) {
	_, err := os.Stat(modelPath)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, err
}

// sanitizePath sanitizes a string to be used as a safe filesystem path component
func sanitizePath(name string) string {
	return strings.Map(func(r rune) rune {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' || r == '_' || r == '.' {
			return r
		}
		return '_'
	}, name)
}

// loadONNXModel loads an ONNX model using ONNX Runtime
// This is a placeholder - in production, you'd use CGO bindings to ONNX Runtime
func (ml *ModelLoader) loadONNXModel(ctx context.Context, modelPath string) (ModelHandler, func() error, error) {
	// In a real implementation, this would bind to ONNX Runtime C API
	// For now, we return a mock handler
	handler := &MockModelHandler{
		modelType: "onnx",
	}
	closeFunc := func() error {
		ml.logger.Debug("ONNX model closed", "path", modelPath)
		return nil
	}

	ml.logger.Info("ONNX model mock handler created", "path", modelPath)
	return handler, closeFunc, nil
}

// loadTensorFlowModel loads a TensorFlow model
// This is a placeholder - in production, you'd use TensorFlow Serving or direct bindings
func (ml *ModelLoader) loadTensorFlowModel(ctx context.Context, modelPath string) (ModelHandler, func() error, error) {
	// In a real implementation, this would bind to TensorFlow C API
	// For now, we return a mock handler
	handler := &MockModelHandler{
		modelType: "tensorflow",
	}
	closeFunc := func() error {
		ml.logger.Debug("TensorFlow model closed", "path", modelPath)
		return nil
	}

	ml.logger.Info("TensorFlow model mock handler created", "path", modelPath)
	return handler, closeFunc, nil
}

// loadPyTorchModel loads a PyTorch model
// This is a placeholder - in production, you'd use PyTorch C++ API (LibTorch)
func (ml *ModelLoader) loadPyTorchModel(ctx context.Context, modelPath string) (ModelHandler, func() error, error) {
	// In a real implementation, this would bind to LibTorch C++ API
	// For now, we return a mock handler
	handler := &MockModelHandler{
		modelType: "pytorch",
	}
	closeFunc := func() error {
		ml.logger.Debug("PyTorch model closed", "path", modelPath)
		return nil
	}

	ml.logger.Info("PyTorch model mock handler created", "path", modelPath)
	return handler, closeFunc, nil
}

// MockModelHandler is a placeholder for actual model handlers
// In production, each model type would have its own implementation
type MockModelHandler struct {
	modelType string
}

func (m *MockModelHandler) Predict(ctx context.Context, input map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{
		"model":     m.modelType,
		"prediction": "mock_prediction",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}, nil
}

func (m *MockModelHandler) HealthCheck() map[string]interface{} {
	return map[string]interface{}{
		"status":    "healthy",
		"modelType": m.modelType,
		"checks": map[string]interface{}{
			"loaded":    true,
			"ready":     true,
			"timestamp": time.Now().UTC().Format(time.RFC3339),
		},
	}
}

func (m *MockModelHandler) Close() error {
	return nil
}
import (
	"archive/tar"
	"compress/gzip"
	"encoding/json"
)