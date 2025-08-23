package model

import (
	"context"
	"fmt"
	"io"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/deployer"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/model/registry"
	"mlops-platform/internal/model/versioning"
)

// ModelService handles the high-level business logic for managing ML models
// across lifecycle stages: registration, loading, serving, updating, and deletion.
type ModelService struct {
	config        *config.Config
	logger        logging.Logger
	loader        *loader.ModelLoader
	deployer      *deployer.ModelDeployer
	registry      *registry.ModelRegistryClient
	versionManager *versioning.VersionManager
	repo          *ModelRepository

	mu       sync.RWMutex
	models   map[string]*ModelInstance // model name -> active instance
}

// ModelInstance represents a running ML model instance with metadata
type ModelInstance struct {
	Name         string
	Version      string
	Path         string
	LoadedAt     time.Time
	Ready        bool
	HealthLast   time.Time
	HealthStatus string
	Metrics      map[string]interface{}
	DeployInfo   *deployer.DeploymentInfo
}

// NewModelService creates and initializes a new ModelService
func NewModelService(
	cfg *config.Config,
	logger logging.Logger,
	loader *loader.ModelLoader,
	deployer *deployer.ModelDeployer,
	regClient *registry.ModelRegistryClient,
	repo *ModelRepository,
) (*ModelService, error) {
	if cfg == nil {
		return nil, fmt.Errorf("config is required")
	}
	if logger == nil {
		return nil, fmt.Errorf("logger is required")
	}
	if loader == nil {
		return nil, fmt.Errorf("model loader is required")
	}
	if deployer == nil {
		return nil, fmt.Errorf("model deployer is required")
	}
	if regClient == nil {
		return nil, fmt.Errorf("model registry client is required")
	}
	if repo == nil {
		return nil, fmt.Errorf("model repository is required")
	}

	versionManager, err := versioning.NewVersionManager(versioning.Config{
		StoragePath: cfg.Model.StoragePath,
		Policy:      cfg.Model.VersioningPolicy,
		Retention:   cfg.Model.RetentionDays,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to initialize version manager: %w", err)
	}

	service := &ModelService{
		config:        cfg,
		logger:        logger,
		loader:        loader,
		deployer:      deployer,
		registry:      regClient,
		versionManager: versionManager,
		repo:          repo,
		models:        make(map[string]*ModelInstance),
	}

	return service, nil
}

// RegisterModel registers a new model version from the model registry
func (s *ModelService) RegisterModel(ctx context.Context, modelName, version string) error {
	const op = "ModelService.RegisterModel"

	s.logger.Infof("registering model %s:%s from registry", modelName, version)

	// Fetch model metadata from registry
	modelMeta, err := s.registry.GetModel(ctx, modelName, version)
	if err != nil {
		return fmt.Errorf("%s: failed to get model from registry: %w", op, err)
	}

	// Resolve version if latest was requested
	resolvedVersion := version
	if strings.ToLower(version) == "latest" {
		list, err := s.registry.ListModelVersions(ctx, modelName)
		if err != nil {
			return fmt.Errorf("%s: failed to list versions: %w", op, err)
		}
		if len(list) == 0 {
			return fmt.Errorf("%s: no versions found for model %s", op, modelName)
		}
		resolvedVersion = list[0].Version // assume sorted descending
	}

	// Download model from registry
	downloadPath := filepath.Join(s.config.Model.StoragePath, modelName, resolvedVersion)
	if err := s.registry.DownloadModel(ctx, modelName, resolvedVersion, downloadPath); err != nil {
		return fmt.Errorf("%s: failed to download model: %w", op, err)
	}

	// Create version entry
	ver := &versioning.Version{
		ModelName:   modelName,
		Version:     resolvedVersion,
		Path:        downloadPath,
		Description: modelMeta.Description,
		Timestamp:   time.Now(),
		Source:      fmt.Sprintf("registry://%s", s.config.Model.RegistryURL),
		Status:      "downloaded",
	}

	if err := s.versionManager.CreateVersion(ver); err != nil {
		return fmt.Errorf("%s: failed to record version: %w", op, err)
	}

	// Save to local repository
	if err := s.repo.UpsertModel(ctx, ver); err != nil {
		return fmt.Errorf("%s: failed to save to repository: %w", op, err)
	}

	s.logger.Infof("model %s:%s successfully registered and downloaded to %s", modelName, resolvedVersion, downloadPath)
	return nil
}

// LoadModel loads a registered model into memory for serving
func (s *ModelService) LoadModel(ctx context.Context, modelName, version string) error {
	const op = "ModelService.LoadModel"

	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.models[modelName]; exists {
		// Check if same version is already loaded
		if s.models[modelName].Version == version {
			if s.models[modelName].Ready {
				s.logger.Infof("model %s:%s is already loaded and ready", modelName, version)
				return nil
			}
			delete(s.models, modelName)
		} else {
			// Unload previous version
			s.unloadModelLocked(modelName)
		}
	}

	// Determine storage path
	var modelPath string
	if version == "latest" {
		localVersions, err := s.repo.GetModelVersions(ctx, modelName)
		if err != nil {
			return fmt.Errorf("%s: failed to get local versions: %w", op, err)
		}
		if len(localVersions) == 0 {
			return fmt.Errorf("%s: no local versions found for model %s", op, modelName)
		}
		version = localVersions[0].Version // latest by semver or timestamp
	}

	// Load from storage
	storagePath := filepath.Join(s.config.Model.StoragePath, modelName, version)
	if _, err := os.Stat(storagePath); os.IsNotExist(err) {
		return fmt.Errorf("%s: model not found at path %s", op, storagePath)
	}

	modelPath = storagePath
	if !s.isModelSupported(modelPath) {
		return fmt.Errorf("%s: unsupported model format or framework", op)
	}

	s.logger.Infof("loading model %s:%s from %s", modelName, version, modelPath)

	instance := &ModelInstance{
		Name:     modelName,
		Version:  version,
		Path:     modelPath,
		LoadedAt: time.Now(),
		Ready:    false,
		Metrics:  make(map[string]interface{}),
	}

	// Actually load the model
	loadedModel, err := s.loader.Load(ctx, modelPath)
	if err != nil {
		return fmt.Errorf("%s: failed to load model: %w", op, err)
	}

	// Verify model is callable
	if err := s.loader.Validate(loadedModel); err != nil {
		return fmt.Errorf("%s: model validation failed: %w", op, err)
	}

	instance.Ready = true
	instance.HealthStatus = "passing"
	s.models[modelName] = instance

	// Update repository status
	if err := s.repo.UpdateModelStatus(ctx, modelName, version, "loaded", ""); err != nil {
		s.logger.Warnf("failed to update model status in repo: %v", err)
	}

	s.logger.Infof("model %s:%s loaded successfully", modelName, version)
	return nil
}

// UnloadModel unloads a loaded model from memory
func (s *ModelService) UnloadModel(ctx context.Context, modelName string) error {
	const op = "ModelService.UnloadModel"

	s.mu.Lock()
	defer s.mu.Unlock()

	return s.unloadModelLocked(modelName)
}

// unloadModelLocked unloads a model (must be called with lock held)
func (s *ModelService) unloadModelLocked(modelName string) error {
	if instance, exists := s.models[modelName]; exists {
		// Optionally unload from loader
		if err := s.loader.Unload(instance.Path); err != nil {
			s.logger.Warnf("failed to unload model %s from loader: %v", modelName, err)
		}

		// Update repository
		if err := s.repo.UpdateModelStatus(context.Background(), modelName, instance.Version, "unloaded", ""); err != nil {
			s.logger.Warnf("failed to update model status in repo: %v", err)
		}

		delete(s.models, modelName)
		s.logger.Infof("model %s unloaded successfully", modelName)
		return nil
	}

	s.logger.Warnf("attempted to unload non-existent model: %s", modelName)
	return nil
}

// Predict runs inference on a loaded model
func (s *ModelService) Predict(ctx context.Context, modelName string, payload io.Reader) (*PredictResponse, error) {
	const op = "ModelService.Predict"

	s.mu.RLock()
	instance, exists := s.models[modelName]
	if !exists {
		s.mu.RUnlock()
		return nil, fmt.Errorf("%s: model %s not loaded", op, modelName)
	}
	if !instance.Ready {
		s.mu.RUnlock()
		return nil, fmt.Errorf("%s: model %s is not ready", op, modelName)
	}
	s.mu.RUnlock()

	// Forward prediction to loader
	result, err := s.loader.Predict(ctx, instance.Path, payload)
	if err != nil {
		return nil, fmt.Errorf("%s: prediction failed: %w", op, err)
	}

	// Update metrics
	s.mu.Lock()
	instance.Metrics["last_prediction_at"] = time.Now()
	instance.Metrics["prediction_count"] = instance.Metrics["prediction_count"].(float64) + 1
	s.mu.Unlock()

	return &PredictResponse{
		ModelName:    modelName,
		Version:      instance.Version,
		Prediction:   result,
		ProcessedAt:  time.Now().UTC(),
		StatusCode:   200,
		ErrorMessage: "",
	}, nil
}

// GetModelStatus returns the operational status of a model
func (s *ModelService) GetModelStatus(ctx context.Context, modelName string) (*ModelStatus, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	instance, exists := s.models[modelName]
	if !exists {
		return nil, fmt.Errorf("model %s not found", modelName)
	}

	// Check health periodically
	if time.Since(instance.HealthLast) > 30*time.Second {
		healthy := s.loader.IsHealthy(ctx, instance.Path)
		instance.HealthStatus = map[bool]string{true: "passing", false: "critical"}[healthy]
		instance.HealthLast = time.Now()
	}

	return &ModelStatus{
		Name:           instance.Name,
		Version:        instance.Version,
		LoadedAt:       instance.LoadedAt,
		Ready:          instance.Ready,
		HealthStatus:   instance.HealthStatus,
		HealthLast:     instance.HealthLast,
		PredictionCount: instance.Metrics["prediction_count"].(float64),
		Path:           instance.Path,
	}, nil
}

// ListLoadedModels returns all currently loaded models
func (s *ModelService) ListLoadedModels(ctx context.Context) []*ModelStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()

	statuses := make([]*ModelStatus, 0, len(s.models))
	for name, instance := range s.models {
		status := &ModelStatus{
			Name:           name,
			Version:        instance.Version,
			LoadedAt:       instance.LoadedAt,
			Ready:          instance.Ready,
			HealthStatus:   instance.HealthStatus,
			HealthLast:     instance.HealthLast,
			PredictionCount: instance.Metrics["prediction_count"].(float64),
			Path:           instance.Path,
		}
		statuses = append(statuses, status)
	}
	return statuses
}

// DeployModel deploys a model to a model server
func (s *ModelService) DeployModel(ctx context.Context, modelName, version string, replicas int) (*deployer.DeploymentInfo, error) {
	const op = "ModelService.DeployModel"

	s.logger.Infof("deploying model %s:%s with %d replicas", modelName, version, replicas)

	// First ensure model is registered and available
	if err := s.RegisterModel(ctx, modelName, version); err != nil {
		return nil, fmt.Errorf("%s: failed to register model: %w", op, err)
	}

	// Get model path
	modelPath := filepath.Join(s.config.Model.StoragePath, modelName, version)
	if _, err := os.Stat(modelPath); os.IsNotExist(err) {
		return nil, fmt.Errorf("%s: model not found at %s", op, modelPath)
	}

	// Perform deployment
	deployInfo, err := s.deployer.Deploy(ctx, modelName, version, modelPath, replicas)
	if err != nil {
		return nil, fmt.Errorf("%s: deployment failed: %w", op, err)
	}

	// Update instance if loaded
	s.mu.Lock()
	if instance, exists := s.models[modelName]; exists && instance.Version == version {
		instance.DeployInfo = deployInfo
	}
	s.mu.Unlock()

	// Update repository
	if err := s.repo.UpdateModelStatus(ctx, modelName, version, "deployed", deployInfo.Endpoint); err != nil {
		s.logger.Warnf("failed to update model deployment status: %v", err)
	}

	s.logger.Infof("model %s:%s deployed successfully to %s", modelName, version, deployInfo.Endpoint)
	return deployInfo, nil
}

// ScaleModelReplicas scales the number of replicas for a deployed model
func (s *ModelService) ScaleModelReplicas(ctx context.Context, modelName, version string, replicas int) error {
	const op = "ModelService.ScaleModelReplicas"

	s.logger.Infof("scaling model %s:%s to %d replicas", modelName, version, replicas)

	if replicas <= 0 {
		return fmt.Errorf("%s: replicas must be positive", op)
	}

	return s.deployer.Scale(ctx, modelName, version, replicas)
}

// GetModelArtifact returns the raw model artifact reader
func (s *ModelService) GetModelArtifact(ctx context.Context, modelName, version string) (io.ReadCloser, error) {
	const op = "ModelService.GetModelArtifact"

	path := filepath.Join(s.config.Model.StoragePath, modelName, version)
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("%s: failed to open model file: %w", op, err)
	}
	return file, nil
}

// isModelSupported checks if the model format is supported
func (s *ModelService) isModelSupported(path string) bool {
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		return false
	}

	// This is framework-dependent; placeholder for actual model validation
	ext := strings.ToLower(filepath.Ext(path))
	supported := map[string]bool{
		".pb":   true, // TensorFlow
		".onnx": true,
		".pt":   true, // PyTorch
		".pth":  true,
		".joblib": true, // Scikit-learn
		".h5":   true, // Keras
	}

	return supported[ext]
}

// PredictResponse represents the response from a prediction request
type PredictResponse struct {
	ModelName    string      `json:"model_name"`
	Version      string      `json:"version"`
	Prediction   interface{} `json:"prediction"`
	ProcessedAt  time.Time   `json:"processed_at"`
	StatusCode   int         `json:"status_code"`
	ErrorMessage string      `json:"error_message,omitempty"`
}

// ModelStatus represents the current status of a loaded model
type ModelStatus struct {
	Name             string  `json:"name"`
	Version          string  `json:"version"`
	LoadedAt         time.Time `json:"loaded_at"`
	Ready            bool    `json:"ready"`
	HealthStatus     string  `json:"health_status"`
	HealthLast       time.Time `json:"health_last"`
	PredictionCount  float64 `json:"prediction_count"`
	Path             string  `json:"path"`
	Endpoint         string  `json:"endpoint,omitempty"`
	Replicas         int     `json:"replicas,omitempty"`
}