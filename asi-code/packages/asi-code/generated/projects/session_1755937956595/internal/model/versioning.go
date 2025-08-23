package model

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// ModelVersion represents a specific version of a machine learning model
type ModelVersion struct {
	ID           string    `json:"id"`
	Name         string    `json:"name"`
	Version      string    `json:"version"`
	Path         string    `json:"path"`
	Stage        string    `json:"stage"` // e.g., "Staging", "Production", "Archived"
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	Checksum     string    `json:"checksum"`
	Metadata     map[string]string `json:"metadata,omitempty"`
	Description  string    `json:"description,omitempty"`
	Author       string    `json:"author,omitempty"`
}

// VersioningManager handles model version lifecycle and stage promotion
type VersioningManager struct {
	config     *config.Config
	logger     *logging.Logger
	repository *ModelRepository
	mu         sync.RWMutex
}

// NewVersioningManager creates a new version manager
func NewVersioningManager(cfg *config.Config, repo *ModelRepository, logger *logging.Logger) *VersioningManager {
	if logger == nil {
		logger = logging.NewLogger(cfg)
	}
	return &VersioningManager{
		config:     cfg,
		logger:     logger,
		repository: repo,
	}
}

// CreateVersion registers a new version of a model
func (vm *VersioningManager) CreateVersion(ctx context.Context, modelName, modelPath, checksum, author, description string, metadata map[string]string) (*ModelVersion, error) {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}
	if modelPath == "" {
		return nil, fmt.Errorf("model path is required")
	}

	// Generate version ID using timestamp and hash
	versionID := fmt.Sprintf("%s-%d", strings.ToLower(modelName), time.Now().UnixNano())
	versionStr := time.Now().Format("v20060102-150405")

	// Validate model exists in repository
	modelExists, err := vm.repository.ModelExists(ctx, modelName)
	if err != nil {
		vm.logger.Error("failed to check model existence", "model", modelName, "error", err)
		return nil, fmt.Errorf("failed to verify model: %w", err)
	}
	if !modelExists {
		return nil, fmt.Errorf("model %s does not exist in repository", modelName)
	}

	// Create version entry
	version := &ModelVersion{
		ID:          versionID,
		Name:        modelName,
		Version:     versionStr,
		Path:        modelPath,
		Stage:       "Staging",
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
		Checksum:    checksum,
		Metadata:    metadata,
		Description: description,
		Author:      author,
	}

	// Persist version metadata
	if err := vm.repository.SaveModelVersion(ctx, version); err != nil {
		vm.logger.Error("failed to save model version", "model", modelName, "version", versionStr, "error", err)
		return nil, fmt.Errorf("failed to save model version: %w", err)
	}

	vm.logger.Info("model version created", "model", modelName, "version", versionStr, "stage", "Staging")

	return version, nil
}

// GetVersion retrieves a specific model version by ID
func (vm *VersioningManager) GetVersion(ctx context.Context, versionID string) (*ModelVersion, error) {
	vm.mu.RLock()
	defer vm.mu.RUnlock()

	if versionID == "" {
		return nil, fmt.Errorf("version ID is required")
	}

	version, err := vm.repository.GetModelVersion(ctx, versionID)
	if err != nil {
		vm.logger.Error("failed to retrieve model version", "version_id", versionID, "error", err)
		return nil, fmt.Errorf("model version not found: %w", err)
	}

	return version, nil
}

// ListVersions returns all versions of a model, sorted by creation time (newest first)
func (vm *VersioningManager) ListVersions(ctx context.Context, modelName string) ([]*ModelVersion, error) {
	vm.mu.RLock()
	defer vm.mu.RUnlock()

	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}

	versions, err := vm.repository.ListModelVersions(ctx, modelName)
	if err != nil {
		vm.logger.Error("failed to list model versions", "model", modelName, "error", err)
		return nil, fmt.Errorf("failed to list versions: %w", err)
	}

	// Sort by creation time, newest first
	sort.Slice(versions, func(i, j int) bool {
		return versions[i].CreatedAt.After(versions[j].CreatedAt)
	})

	return versions, nil
}

// ListVersionsByStage returns all versions of a model in a specific stage
func (vm *VersioningManager) ListVersionsByStage(ctx context.Context, modelName, stage string) ([]*ModelVersion, error) {
	vm.mu.RLock()
	defer vm.mu.RUnlock()

	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}
	if stage == "" {
		return nil, fmt.Errorf("stage is required")
	}

	versions, err := vm.repository.ListModelVersions(ctx, modelName)
	if err != nil {
		vm.logger.Error("failed to list model versions", "model", modelName, "error", err)
		return nil, fmt.Errorf("failed to list versions: %w", err)
	}

	var filtered []*ModelVersion
	for _, v := range versions {
		if strings.EqualFold(v.Stage, stage) {
			filtered = append(filtered, v)
		}
	}

	return filtered, nil
}

// PromoteVersion moves a model version to a new stage (e.g., Staging -> Production)
func (vm *VersioningManager) PromoteVersion(ctx context.Context, versionID, targetStage string, promote bool) (*ModelVersion, error) {
	vm.mu.Lock()
	defer vm.mu.Unlock()

	if versionID == "" {
		return nil, fmt.Errorf("version ID is required")
	}
	if targetStage == "" {
		return nil, fmt.Errorf("target stage is required")
	}

	// Validate stage
	validStages := []string{"Staging", "Production", "Archived"}
	isValidStage := false
	for _, s := range validStages {
		if strings.EqualFold(s, targetStage) {
			targetStage = s
			isValidStage = true
			break
		}
	}
	if !isValidStage {
		return nil, fmt.Errorf("invalid stage: must be one of %v", validStages)
	}

	version, err := vm.repository.GetModelVersion(ctx, versionID)
	if err != nil {
		vm.logger.Error("failed to get model version for promotion", "version_id", versionID, "error", err)
		return nil, fmt.Errorf("model version not found: %w", err)
	}

	// Determine new stage based on promote flag
	newStage := version.Stage
	if promote {
		newStage = targetStage
	} else {
		newStage = "Archived"
	}

	// Update version stage
	version.Stage = newStage
	version.UpdatedAt = time.Now()

	if err := vm.repository.SaveModelVersion(ctx, version); err != nil {
		vm.logger.Error("failed to save promoted model version", "version_id", versionID, "stage", newStage, "error", err)
		return nil, fmt.Errorf("failed to promote model version: %w", err)
	}

	vm.logger.Info("model version promoted", "version_id", versionID, "from", version.Stage, "to", newStage)

	return version, nil
}

// GetProductionVersion returns the current production version of a model
func (vm *VersioningManager) GetProductionVersion(ctx context.Context, modelName string) (*ModelVersion, error) {
	vm.mu.RLock()
	defer vm.mu.RUnlock()

	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}

	versions, err := vm.ListVersionsByStage(ctx, modelName, "Production")
	if err != nil {
		return nil, err
	}

	if len(versions) == 0 {
		return nil, nil // No production version yet
	}

	// Return the most recently promoted production version
	return versions[0], nil
}

// ArchiveVersion moves a version to Archived stage
func (vm *VersioningManager) ArchiveVersion(ctx context.Context, versionID string) (*ModelVersion, error) {
	return vm.PromoteVersion(ctx, versionID, "Archived", true)
}

// ValidateVersion checks the integrity of a model version
func (vm *VersioningManager) ValidateVersion(ctx context.Context, version *ModelVersion) error {
	if version == nil {
		return fmt.Errorf("version is nil")
	}
	if version.ID == "" {
		return fmt.Errorf("version ID is missing")
	}
	if version.Name == "" {
		return fmt.Errorf("model name is missing")
	}
	if version.Path == "" {
		return fmt.Errorf("model path is missing")
	}

	// Check if file exists
	if _, err := os.Stat(version.Path); os.IsNotExist(err) {
		return fmt.Errorf("model file does not exist at path: %s", version.Path)
	}

	vm.logger.Debug("model version validated successfully", "version_id", version.ID, "model", version.Name)
	return nil
}

// GetVersionHistory returns a timeline of version stage changes
// For simplicity, we assume each SaveModelVersion call records a state
func (vm *VersioningManager) GetVersionHistory(ctx context.Context, modelName string) (map[string][]StageTransition, error) {
	vm.mu.RLock()
	defer vm.mu.RUnlock()

	versions, err := vm.ListVersions(ctx, modelName)
	if err != nil {
		return nil, err
	}

	history := make(map[string][]StageTransition)
	for _, v := range versions {
		// In a real system, we'd load audit log; here we synthesize from current state
		transitions := []StageTransition{
			{
				From:      "none",
				To:        v.Stage,
				Timestamp: v.CreatedAt,
				Reason:    "initial registration",
			},
		}
		history[v.ID] = transitions
	}

	return history, nil
}

// StageTransition represents a change in model version stage
type StageTransition struct {
	From      string    `json:"from"`
	To        string    `json:"to"`
	Timestamp time.Time `json:"timestamp"`
	Reason    string    `json:"reason"`
}