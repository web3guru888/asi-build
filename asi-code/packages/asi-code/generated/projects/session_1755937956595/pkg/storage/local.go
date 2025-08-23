package storage

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

// LocalStorage implements a file-based storage system for models and artifacts.
// It provides thread-safe operations for saving, loading, listing, and deleting model files.
type LocalStorage struct {
	basePath string
	mutex    *sync.RWMutex
	logger   logging.Logger
}

// NewLocalStorage creates a new instance of LocalStorage using the provided configuration.
func NewLocalStorage(cfg *config.Config, logger logging.Logger) (*LocalStorage, error) {
	if cfg == nil {
		return nil, fmt.Errorf("config cannot be nil")
	}
	if logger == nil {
		return nil, fmt.Errorf("logger cannot be nil")
	}

	// Use ModelStoragePath from config, fallback to default if not set
	basePath := cfg.ModelStoragePath
	if basePath == "" {
		basePath = "./models" // default relative path
	}

	// Ensure the base path exists
	if err := os.MkdirAll(basePath, 0755); err != nil {
		return nil, fmt.Errorf("failed to create model storage directory: %w", err)
	}

	return &LocalStorage{
		basePath: basePath,
		mutex:    &sync.RWMutex{},
		logger:   logger,
	}, nil
}

// Save stores a model artifact from the reader into the specified model and version path.
// The model name and version are validated before saving.
func (s *LocalStorage) Save(ctx context.Context, modelName, version, fileName string, reader io.Reader) error {
	if modelName == "" {
		return fmt.Errorf("model name is required")
	}
	if version == "" {
		return fmt.Errorf("version is required")
	}
	if reader == nil {
		return fmt.Errorf("reader cannot be nil")
	}
	if fileName == "" {
		fileName = "model.bin" // default filename if not provided
	}

	// Validate model name and version (simple alphanumeric + underscore/hyphen allowed)
	if !isValidName(modelName) {
		return fmt.Errorf("invalid model name: %s", modelName)
	}
	if !isValidVersion(version) {
		return fmt.Errorf("invalid version: %s", version)
	}

	// Build destination path
	destPath := s.modelVersionPath(modelName, version)
	fullPath := filepath.Join(destPath, fileName)

	s.logger.Info("saving model artifact", map[string]interface{}{
		"model":    modelName,
		"version":  version,
		"filename": fileName,
		"path":     fullPath,
	})

	s.mutex.Lock()
	defer s.mutex.Unlock()

	// Ensure model version directory exists
	if err := os.MkdirAll(destPath, 0755); err != nil {
		return fmt.Errorf("failed to create model version directory: %w", err)
	}

	// Create the destination file
	file, err := os.Create(fullPath)
	if err != nil {
		return fmt.Errorf("failed to create file at %s: %w", fullPath, err)
	}
	defer file.Close()

	// Copy data from reader to file with context-aware progress
	done := make(chan error, 1)
	go func() {
		_, copyErr := io.Copy(file, reader)
		if copyErr != nil {
			// Attempt to rollback by removing partially written file
			_ = os.Remove(fullPath)
		}
		done <- copyErr
	}()

	select {
	case <-ctx.Done():
		// Context cancelled or timeout
		_ = os.Remove(fullPath) // best effort cleanup
		return fmt.Errorf("save operation cancelled: %w", ctx.Err())
	case err = <-done:
		if err != nil {
			return fmt.Errorf("failed to copy model data: %w", err)
		}
	}

	s.logger.Info("model artifact saved successfully", map[string]interface{}{
		"model":    modelName,
		"version":  version,
		"filename": fileName,
	})

	return nil
}

// Load returns a reader for the specified model, version, and file.
// Returns os.ErrNotExist if the file or version does not exist.
func (s *LocalStorage) Load(ctx context.Context, modelName, version, fileName string) (io.ReadCloser, error) {
	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}
	if version == "" {
		return nil, fmt.Errorf("version is required")
	}
	if fileName == "" {
		fileName = "model.bin"
	}

	// Validate inputs
	if !isValidName(modelName) {
		return nil, fmt.Errorf("invalid model name: %s", modelName)
	}
	if !isValidVersion(version) {
		return nil, fmt.Errorf("invalid version: %s", version)
	}

	filePath := filepath.Join(s.modelVersionPath(modelName, version), fileName)

	s.logger.Debug("loading model artifact", map[string]interface{}{
		"model":    modelName,
		"version":  version,
		"filename": fileName,
		"path":     filePath,
	})

	s.mutex.RLock()
	defer s.mutex.RUnlock()

	// Check if file exists and is readable
	info, err := os.Stat(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("model %s:%s/%s not found: %w", modelName, version, fileName, os.ErrNotExist)
		}
		return nil, fmt.Errorf("failed to stat file: %w", err)
	}

	if info.IsDir() {
		return nil, fmt.Errorf("file %s is a directory", fileName)
	}

	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %w", err)
	}

	return &contextReadCloser{
		ReadCloser: file,
		ctx:        ctx,
		cancelFunc: func() { _ = file.Close() },
	}, nil
}

// ListModels returns all model names stored in the system.
func (s *LocalStorage) ListModels(ctx context.Context) ([]string, error) {
	s.mutex.RLock()
	defer s.mutex.RUnlock()

	entries, err := os.ReadDir(s.basePath)
	if err != nil {
		return nil, fmt.Errorf("failed to list models: %w", err)
	}

	var models []string
	for _, entry := range entries {
		if entry.IsDir() {
			models = append(models, entry.Name())
		}
	}

	s.logger.Debug("listed models", map[string]interface{}{
		"count": len(models),
		"names": models,
	})

	return models, nil
}

// ListVersions returns all versions available for a given model.
func (s *LocalStorage) ListVersions(ctx context.Context, modelName string) ([]string, error) {
	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}
	if !isValidName(modelName) {
		return nil, fmt.Errorf("invalid model name: %s", modelName)
	}

	modelPath := filepath.Join(s.basePath, modelName)

	s.mutex.RLock()
	defer s.mutex.RUnlock()

	entries, err := os.ReadDir(modelPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("model %s not found: %w", modelName, os.ErrNotExist)
		}
		return nil, fmt.Errorf("failed to list versions for model %s: %w", modelName, err)
	}

	var versions []string
	for _, entry := range entries {
		if entry.IsDir() {
			versions = append(versions, entry.Name())
		}
	}

	s.logger.Debug("listed model versions", map[string]interface{}{
		"model":   modelName,
		"count":   len(versions),
		"versions": versions,
	})

	return versions, nil
}

// DeleteModel removes all data associated with a model, including all versions.
func (s *LocalStorage) DeleteModel(ctx context.Context, modelName string) error {
	if modelName == "" {
		return fmt.Errorf("model name is required")
	}
	if !isValidName(modelName) {
		return fmt.Errorf("invalid model name: %s", modelName)
	}

	modelPath := filepath.Join(s.basePath, modelName)

	s.logger.Info("deleting model", map[string]interface{}{
		"model": modelName,
		"path":  modelPath,
	})

	s.mutex.Lock()
	defer s.mutex.Unlock()

	if err := os.RemoveAll(modelPath); err != nil {
		return fmt.Errorf("failed to delete model %s: %w", modelName, err)
	}

	s.logger.Info("model deleted successfully", map[string]interface{}{
		"model": modelName,
	})

	return nil
}

// DeleteVersion removes a specific version of a model.
// Does not delete the model directory itself if other versions exist.
func (s *LocalStorage) DeleteVersion(ctx context.Context, modelName, version string) error {
	if modelName == "" {
		return fmt.Errorf("model name is required")
	}
	if version == "" {
		return fmt.Errorf("version is required")
	}
	if !isValidName(modelName) {
		return fmt.Errorf("invalid model name: %s", modelName)
	}
	if !isValidVersion(version) {
		return fmt.Errorf("invalid version: %s", version)
	}

	versionPath := s.modelVersionPath(modelName, version)

	s.logger.Info("deleting model version", map[string]interface{}{
		"model":   modelName,
		"version": version,
		"path":    versionPath,
	})

	s.mutex.Lock()
	defer s.mutex.Unlock()

	info, err := os.Stat(versionPath)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("model version %s:%s not found: %w", modelName, version, os.ErrNotExist)
		}
		return fmt.Errorf("failed to stat version path: %w", err)
	}

	if !info.IsDir() {
		return fmt.Errorf("version path is not a directory")
	}

	if err := os.RemoveAll(versionPath); err != nil {
		return fmt.Errorf("failed to delete version %s of model %s: %w", version, modelName, err)
	}

	s.logger.Info("model version deleted successfully", map[string]interface{}{
		"model":   modelName,
		"version": version,
	})

	return nil
}

// Exists checks if a specific model version file exists.
func (s *LocalStorage) Exists(ctx context.Context, modelName, version, fileName string) (bool, error) {
	if modelName == "" {
		return false, fmt.Errorf("model name is required")
	}
	if version == "" {
		return false, fmt.Errorf("version is required")
	}
	if fileName == "" {
		fileName = "model.bin"
	}

	if !isValidName(modelName) {
		return false, fmt.Errorf("invalid model name: %s", modelName)
	}
	if !isValidVersion(version) {
		return false, fmt.Errorf("invalid version: %s", version)
	}

	filePath := filepath.Join(s.modelVersionPath(modelName, version), fileName)

	s.mutex.RLock()
	defer s.mutex.RUnlock()

	_, err := os.Stat(filePath)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, fmt.Errorf("error checking existence: %w", err)
}

// GetModelPath returns the filesystem path where a model version is stored.
// Useful for direct access by model loaders or external tools.
func (s *LocalStorage) GetModelPath(modelName, version string) (string, error) {
	if modelName == "" {
		return "", fmt.Errorf("model name is required")
	}
	if version == "" {
		return "", fmt.Errorf("version is required")
	}
	if !isValidName(modelName) {
		return "", fmt.Errorf("invalid model name: %s", modelName)
	}
	if !isValidVersion(version) {
		return "", fmt.Errorf("invalid version: %s", version)
	}

	return s.modelVersionPath(modelName, version), nil
}

// Close performs any necessary cleanup. For local storage, this is a no-op.
func (s *LocalStorage) Close() error {
	s.logger.Debug("local storage closed", nil)
	return nil
}

// modelVersionPath constructs the path for a specific model and version.
func (s *LocalStorage) modelVersionPath(modelName, version string) string {
	return filepath.Join(s.basePath, modelName, version)
}

// isValidName checks if model name contains only allowed characters.
func isValidName(name string) bool {
	return name != "" && strings.ToLower(name) == name &&
		strings.IndexFunc(name, func(r rune) bool {
			return !((r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' || r == '_')
		}) == -1
}

// isValidVersion checks if version string is valid.
func isValidVersion(version string) bool {
	return version != "" && strings.IndexFunc(version, func(r rune) bool {
		return !((r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '-' || r == '.' || r == '_')
	}) == -1
}

// contextReadCloser wraps a ReadCloser with context cancellation support.
type contextReadCloser struct {
	io.ReadCloser
	ctx        context.Context
	cancelFunc func()
}

func (c *contextReadCloser) Read(p []byte) (n int, err error) {
	select {
	case <-c.ctx.Done():
		return 0, c.ctx.Err()
	default:
		return c.ReadCloser.Read(p)
	}
}

func (c *contextReadCloser) Close() error {
	err := c.ReadCloser.Close()
	if c.cancelFunc != nil {
		c.cancelFunc()
	}
	return err
}