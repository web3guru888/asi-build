package model

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"strings"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// ModelRegistryClient handles communication with the model registry
// to list, download, and retrieve metadata about registered models.
type ModelRegistryClient struct {
	baseURL    *url.URL
	httpClient *http.Client
	logger     logging.Logger
}

// ModelMetadata represents the metadata of a model version from the registry
type ModelMetadata struct {
	Name         string            `json:"name"`
	Version      string            `json:"version"`
	Project      string            `json:"project"`
	Description  string            `json:"description"`
	Format       string            `json:"format"` // e.g., ONNX, TensorFlow, PyTorch
	Metrics      map[string]any    `json:"metrics,omitempty"`
	Parameters   map[string]any    `json:"parameters,omitempty"`
	Tags         map[string]string `json:"tags,omitempty"`
	CreatedAt    time.Time         `json:"created_at"`
	ExperimentID string            `json:"experiment_id,omitempty"`
	RunID        string            `json:"run_id,omitempty"`
	StoragePath  string            `json:"storage_path"`
	Checksum     string            `json:"checksum,omitempty"`
}

// RegistryModelResponse is the response structure from the list models API
type RegistryModelResponse struct {
	Models []ModelMetadata `json:"models"`
}

// NewModelRegistryClient creates a new client for interacting with the model registry
func NewModelRegistryClient(config *config.Config, logger logging.Logger) (*ModelRegistryClient, error) {
	if config.ModelRegistryURL == "" {
		return nil, fmt.Errorf("model registry URL is required")
	}

	parsedURL, err := url.Parse(config.ModelRegistryURL)
	if err != nil {
		return nil, fmt.Errorf("invalid model registry URL %s: %w", config.ModelRegistryURL, err)
	}

	client := &http.Client{
		Timeout: 30 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:          100,
			MaxConnsPerHost:       10,
			MaxIdleConnsPerHost:   10,
			IdleConnTimeout:       90 * time.Second,
			TLSHandshakeTimeout:   10 * time.Second,
			ExpectContinueTimeout: 1 * time.Second,
		},
	}

	return &ModelRegistryClient{
		baseURL:    parsedURL,
		httpClient: client,
		logger:     logger.With("component", "model_registry_client"),
	}, nil
}

// ListModels retrieves all available models from the registry
func (c *ModelRegistryClient) ListModels(ctx context.Context) ([]ModelMetadata, error) {
	listURL := c.baseURL.ResolveReference(&url.URL{Path: "/api/v1/models"})
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, listURL.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "mlops-model-server/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to list models: %w", err)
	}
	defer func() {
		if closeErr := resp.Body.Close(); closeErr != nil {
			c.logger.Warn("failed to close response body", "error", closeErr)
		}
	}()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return nil, fmt.Errorf("registry request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var response RegistryModelResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode registry response: %w", err)
	}

	return response.Models, nil
}

// GetModel retrieves metadata for a specific model by name and version
func (c *ModelRegistryClient) GetModel(ctx context.Context, modelName, version string) (*ModelMetadata, error) {
	if modelName == "" {
		return nil, fmt.Errorf("model name is required")
	}
	if version == "" {
		version = "latest"
	}

	path := fmt.Sprintf("/api/v1/models/%s/versions/%s", url.PathEscape(modelName), url.PathEscape(version))
	modelURL := c.baseURL.ResolveReference(&url.URL{Path: path})

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, modelURL.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "mlops-model-server/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to get model metadata: %w", err)
	}
	defer func() {
		if closeErr := resp.Body.Close(); closeErr != nil {
			c.logger.Warn("failed to close response body", "error", closeErr)
		}
	}()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("model %s:%s not found in registry", modelName, version)
	}
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return nil, fmt.Errorf("get model request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var metadata ModelMetadata
	if err := json.NewDecoder(resp.Body).Decode(&metadata); err != nil {
		return nil, fmt.Errorf("failed to decode model metadata: %w", err)
	}

	return &metadata, nil
}

// DownloadModel downloads a model artifact from the registry to a local path
func (c *ModelRegistryClient) DownloadModel(ctx context.Context, modelName, version, targetDir string) (string, *ModelMetadata, error) {
	metadata, err := c.GetModel(ctx, modelName, version)
	if err != nil {
		return "", nil, err
	}

	if metadata.StoragePath == "" {
		return "", nil, fmt.Errorf("model %s:%s has no storage path in registry", modelName, version)
	}

	// Create the target directory if it doesn't exist
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return "", nil, fmt.Errorf("failed to create target directory %s: %w", targetDir, err)
	}

	// Construct local path for the model
	localPath := filepath.Join(targetDir, modelName, metadata.Version)
	if err := os.MkdirAll(localPath, 0755); err != nil {
		return "", nil, fmt.Errorf("failed to create model directory %s: %w", localPath, err)
	}

	// Build download URL
	downloadPath := path.Join("/api/v1/models", url.PathEscape(modelName), "versions", url.PathEscape(metadata.Version), "download")
	downloadURL := c.baseURL.ResolveReference(&url.URL{Path: downloadPath})

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, downloadURL.String(), nil)
	if err != nil {
		return "", nil, fmt.Errorf("failed to create download request: %w", err)
	}

	req.Header.Set("User-Agent", "mlops-model-server/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", nil, fmt.Errorf("failed to download model: %w", err)
	}
	defer func() {
		if closeErr := resp.Body.Close(); closeErr != nil {
			c.logger.Warn("failed to close download response body", "error", closeErr)
		}
	}()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return "", nil, fmt.Errorf("download request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Extract filename from content disposition if available
	filename := metadata.Name + ".bin"
	if contentDisp := resp.Header.Get("Content-Disposition"); contentDisp != "" {
		if parts := strings.Split(contentDisp, "filename="); len(parts) > 1 {
			filename = strings.Trim(parts[1], "\"'")
		}
	}

	// Create destination file
	destFile := filepath.Join(localPath, filename)
	file, err := os.Create(destFile)
	if err != nil {
		return "", nil, fmt.Errorf("failed to create destination file %s: %w", destFile, err)
	}

	// Copy response body to file
	_, err = io.Copy(file, resp.Body)
	closeErr := file.Close()
	if err != nil {
		return "", nil, fmt.Errorf("failed to copy model data to file: %w", err)
	}
	if closeErr != nil {
		return "", nil, fmt.Errorf("failed to close destination file: %w", closeErr)
	}

	// Verify file was written
	if _, statErr := os.Stat(destFile); os.IsNotExist(statErr) {
		return "", nil, fmt.Errorf("downloaded model file does not exist: %s", destFile)
	}

	c.logger.Info("model downloaded successfully",
		"model", modelName,
		"version", metadata.Version,
		"destination", destFile,
		"size", getFileSize(destFile),
		"format", metadata.Format)

	return destFile, metadata, nil
}

// getFileSize returns the size of a file in bytes
func getFileSize(filePath string) int64 {
	if info, err := os.Stat(filePath); err == nil {
		return info.Size()
	}
	return -1
}

// Close shuts down the registry client
func (c *ModelRegistryClient) Close() error {
	// Close idle connections
	if c.httpClient != nil {
		c.httpClient.CloseIdleConnections()
	}
	return nil
}