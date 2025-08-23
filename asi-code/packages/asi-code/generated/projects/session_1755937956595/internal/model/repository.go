package model

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// ModelRepository manages the storage and retrieval of model artifacts.
// It handles local filesystem operations for storing, listing, and removing models
// in versioned directories, supporting MLOps workflows.
type ModelRepository struct {
	basePath string
	mu       sync.RWMutex
	logger   *logging.Logger
}

// ModelInfo represents metadata about a stored model.
type ModelInfo struct {
	ModelID      string    `json:"model_id"`
	Version      string    `json:"version"`
	Path         string    `json:"path"`
	Size         int64     `json:"size"`
	CreatedAt    time.Time `json:"created_at"`
	Format       string    `json:"format"` // e.g., "ONNX", "TensorFlow", "PyTorch", "SKLearn"
	Description  string    `json:"description,omitempty"`
	UploadedBy   string    `json:"uploaded_by,omitempty"`
	Labels       map[string]string `json:"labels,omitempty"`
}

// NewModelRepository creates a new instance of ModelRepository.
// It ensures the base path exists and is writable.
func NewModelRepository(cfg *config.Config, logger *logging.Logger) (*ModelRepository, error) {
	repoPath := cfg.ModelRepositoryPath
	if repoPath == "" {
		repoPath = "./models"
	}

	absPath, err := filepath.Abs(repoPath)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve model repository path: %w", err)
	}

	// Ensure the directory exists
	if err := os.MkdirAll(absPath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create model repository directory: %w", err)
	}

	repo := &ModelRepository{
		basePath: absPath,
		logger:   logger.With("component", "model_repository"),
	}

	repo.logger.Info("model repository initialized", "path", absPath)
	return repo, nil
}

// StoreModel saves a model artifact to the repository.
// The model is stored under {base_path}/{model_id}/{version}/model.bin
// It returns the full path where the model was stored.
func (r *ModelRepository) StoreModel(ctx context.Context, modelID, version, format, uploadedBy, description string, labels map[string]string, reader io.Reader) (string, error) {
	if modelID == "" {
		return "", fmt.Errorf("modelID is required")
	}
	if version == "" {
		version = "latest"
	}

	// Sanitize inputs to prevent path traversal
	if !r.isValidName(modelID) || !r.isValidName(version) {
		return "", fmt.Errorf("invalid modelID or version: alphanumeric, hyphens, underscores only")
	}

	modelDir := filepath.Join(r.basePath, modelID, version)
	modelPath := filepath.Join(modelDir, "model.bin")

	// Lock for writing to prevent race conditions during directory creation
	r.mu.Lock()
	defer r.mu.Unlock()

	// Create model version directory
	if err := os.MkdirAll(modelDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create model directory: %w", err)
	}

	// Create the model file
	file, err := os.Create(modelPath)
	if err != nil {
		return "", fmt.Errorf("failed to create model file: %w", err)
	}

	// Use context-aware copying if needed (though io.Copy doesn't support ctx natively)
	var copyErr error
	done := make(chan struct{})
	go func() {
		defer close(done)
		_, copyErr = io.Copy(file, reader)
		_ = file.Close()
	}()

	select {
	case <-done:
		if copyErr != nil {
			_ = os.Remove(modelPath)
			return "", fmt.Errorf("failed to write model data: %w", copyErr)
		}
	case <-ctx.Done():
		// Cleanup on timeout or cancellation
		_ = file.Close()
		_ = os.Remove(modelPath)
		<-done // Ensure go routine finishes
		return "", ctx.Err()
	}

	// Sync to disk
	if err := file.Sync(); err != nil {
		_ = os.Remove(modelPath)
		return "", fmt.Errorf("failed to sync model to disk: %w", err)
	}

	r.logger.Info("model stored successfully",
		"model_id", modelID,
		"version", version,
		"path", modelPath,
		"format", format,
		"uploaded_by", uploadedBy,
	)

	return modelPath, nil
}

// GetModelPath retrieves the local filesystem path for a stored model.
// Returns empty string and nil error if not found.
func (r *ModelRepository) GetModelPath(modelID, version string) (string, error) {
	if modelID == "" {
		return "", fmt.Errorf("modelID is required")
	}
	if version == "" {
		version = "latest"
	}

	// Sanitize inputs
	if !r.isValidName(modelID) || !r.isValidName(version) {
		return "", fmt.Errorf("invalid modelID or version")
	}

	r.mu.RLock()
	defer r.mu.RUnlock()

	modelDir := filepath.Join(r.basePath, modelID, version)
	modelPath := filepath.Join(modelDir, "model.bin")

	if _, err := os.Stat(modelPath); os.IsNotExist(err) {
		return "", nil
	} else if err != nil {
		return "", fmt.Errorf("failed to stat model: %w", err)
	}

	return modelPath, nil
}

// ListModels returns metadata for all models in the repository.
func (r *ModelRepository) ListModels(ctx context.Context) ([]*ModelInfo, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var models []*ModelInfo

	err := filepath.WalkDir(r.basePath, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() {
			// Parse path: {base}/{model_id}/{version}
			rel, err := filepath.Rel(r.basePath, path)
			if err != nil || rel == "." {
				return nil
			}

			parts := strings.Split(rel, string(os.PathSeparator))
			if len(parts) == 2 {
				modelID := parts[0]
				version := parts[1]

				// Skip hidden or invalid directories
				if strings.HasPrefix(modelID, ".") || strings.HasPrefix(version, ".") {
					return nil
				}

				modelPath := filepath.Join(path, "model.bin")
				if stat, statErr := os.Stat(modelPath); statErr == nil {
					info := &ModelInfo{
						ModelID:   modelID,
						Version:   version,
						Path:      modelPath,
						Size:      stat.Size(),
						CreatedAt: stat.ModTime(),
						Format:    r.detectFormat(modelPath),
					}
					models = append(models, info)
				}
			}
		}

		// Respect context cancellation during long walks
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			return nil
		}
	})

	if err != nil {
		return nil, fmt.Errorf("failed to list models: %w", err)
	}

	return models, nil
}

// ListModelVersions returns all versions of a specific model.
func (r *ModelRepository) ListModelVersions(ctx context.Context, modelID string) ([]*ModelInfo, error) {
	if modelID == "" {
		return nil, fmt.Errorf("modelID is required")
	}

	r.mu.RLock()
	defer r.mu.RUnlock()

	modelDir := filepath.Join(r.basePath, modelID)
	if _, err := os.Stat(modelDir); os.IsNotExist(err) {
		return []*ModelInfo{}, nil
	}

	var versions []*ModelInfo
	err := filepath.WalkDir(modelDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() {
			rel, _ := filepath.Rel(modelDir, path)
			if rel == "." {
				return nil
			}

			version := rel
			if !r.isValidName(version) {
				return nil
			}

			modelPath := filepath.Join(path, "model.bin")
			if stat, statErr := os.Stat(modelPath); statErr == nil {
				info := &ModelInfo{
					ModelID:   modelID,
					Version:   version,
					Path:      modelPath,
					Size:      stat.Size(),
					CreatedAt: stat.ModTime(),
					Format:    r.detectFormat(modelPath),
				}
				versions = append(versions, info)
			}
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			return nil
		}
	})

	if err != nil {
		return nil, fmt.Errorf("failed to list model versions: %w", err)
	}

	return versions, nil
}

// GetModelMetadata retrieves metadata for a specific model version.
func (r *ModelRepository) GetModelMetadata(modelID, version string) (*ModelInfo, error) {
	if modelID == "" {
		return nil, fmt.Errorf("modelID is required")
	}
	if version == "" {
		version = "latest"
	}

	if !r.isValidName(modelID) || !r.isValidName(version) {
		return nil, fmt.Errorf("invalid modelID or version")
	}

	r.mu.RLock()
	defer r.mu.RUnlock()

	modelDir := filepath.Join(r.basePath, modelID, version)
	modelPath := filepath.Join(modelDir, "model.bin")

	stat, err := os.Stat(modelPath)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to stat model: %w", err)
	}

	return &ModelInfo{
		ModelID:   modelID,
		Version:   version,
		Path:      modelPath,
		Size:      stat.Size(),
		CreatedAt: stat.ModTime(),
		Format:    r.detectFormat(modelPath),
	}, nil
}

// DeleteModel removes a specific model version from the repository.
// If it's the last version, deletes the entire model.
func (r *ModelRepository) DeleteModel(modelID, version string) error {
	if modelID == "" {
		return fmt.Errorf("modelID is required")
	}
	if version == "" {
		version = "latest"
	}

	if !r.isValidName(modelID) || !r.isValidName(version) {
		return fmt.Errorf("invalid modelID or version")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	versionPath := filepath.Join(r.basePath, modelID, version)
	if _, err := os.Stat(versionPath); os.IsNotExist(err) {
		return nil
	}

	if err := os.RemoveAll(versionPath); err != nil {
		return fmt.Errorf("failed to delete model version: %w", err)
	}

	// Check if model directory is now empty
	modelDir := filepath.Join(r.basePath, modelID)
	entries, err := os.ReadDir(modelDir)
	if err != nil {
		return fmt.Errorf("failed to read model directory: %w", err)
	}

	if len(entries) == 0 {
		if err := os.Remove(modelDir); err != nil {
			r.logger.Warn("failed to remove empty model directory", "path", modelDir, "error", err)
		}
	}

	r.logger.Info("model version deleted",
		"model_id", modelID,
		"version", version,
	)

	return nil
}

// isValidName checks if a model ID or version follows safe naming conventions.
func (r *ModelRepository) isValidName(name string) bool {
	if name == "" || len(name) > 255 {
		return false
	}
	for _, c := range name {
		if !(c >= 'a' && c <= 'z' ||
			c >= 'A' && c <= 'Z' ||
			c >= '0' && c <= '9' ||
			c == '-' || c == '_' || c == '.') {
			return false
		}
	}
	return !strings.HasPrefix(name, ".")
}

// detectFormat guesses the model format based on file extension or signature.
// This is a basic placeholder and can be extended with magic bytes detection.
func (r *ModelRepository) detectFormat(path string) string {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".onnx":
		return "ONNX"
	case ".pb", ".pbtxt":
		return "TensorFlow"
	case ".pt", ".pth", ".bin":
		return "PyTorch"
	case ".pkl", ".pickle":
		return "SKLearn"
	case ".h5":
		return "Keras"
	default:
		return "Unknown"
	}
}