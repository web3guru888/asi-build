package storage

import (
	"context"
	"fmt"
	"io"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"cloud.google.com/go/storage"
	"google.golang.org/api/option"
	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// GCSService handles interactions with Google Cloud Storage
// for model storage, retrieval, and versioning in the MLOps platform.
type GCSService struct {
	client     *storage.Client
	bucketName string
	basePath   string
	logger     logging.Logger
}

// GCSConfig holds configuration specific to GCS
type GCSConfig struct {
	BucketName string `mapstructure:"bucket_name"`
	BasePath   string `mapstructure:"base_path"`
	CredentialsFile string `mapstructure:"credentials_file,omitempty"`
	ProjectID  string `mapstructure:"project_id"`
}

// NewGCSService creates and initializes a new GCS storage service.
func NewGCSService(ctx context.Context, cfg *config.Config, logger logging.Logger) (*GCSService, error) {
	var gcsCfg GCSConfig
	if err := cfg.LoadSub("storage.gcs", &gcsCfg); err != nil {
		return nil, fmt.Errorf("failed to load GCS config: %w", err)
	}

	if gcsCfg.BucketName == "" {
		return nil, fmt.Errorf("GCS bucket_name is required")
	}

	var clientOpts []option.ClientOption
	if gcsCfg.CredentialsFile != "" {
		clientOpts = append(clientOpts, option.WithCredentialsFile(gcsCfg.CredentialsFile))
	}
	if gcsCfg.ProjectID != "" {
		clientOpts = append(clientOpts, option.WithProjectID(gcsCfg.ProjectID))
	}

	client, err := storage.NewClient(ctx, clientOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to create GCS client: %w", err)
	}

	logger.Info("GCS client initialized", map[string]interface{}{
		"bucket":   gcsCfg.BucketName,
		"basePath": gcsCfg.BasePath,
	})

	return &GCSService{
		client:     client,
		bucketName: gcsCfg.BucketName,
		basePath:   cleanPath(gcsCfg.BasePath),
		logger:     logger,
	}, nil
}

// UploadModel uploads a model file to GCS with appropriate metadata.
func (g *GCSService) UploadModel(ctx context.Context, modelID, version, filePath string) error {
	objectKey := g.getModelObjectKey(modelID, version)

	// Detect content type
	contentType := "application/octet-stream"
	ext := strings.ToLower(filepath.Ext(filePath))
	if mimeType := mime.TypeByExtension(ext); mimeType != "" {
		contentType = mimeType
	}

	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open model file: %w", err)
	}
	defer file.Close()

	wc := g.client.Bucket(g.bucketName).Object(objectKey).NewWriter(ctx)
	wc.ContentType = contentType
	wc.Metadata = map[string]string{
		"model_id": modelID,
		"version":  version,
		"uploaded": time.Now().UTC().Format(time.RFC3339),
	}

	if _, err = io.Copy(wc, file); err != nil {
		// Attempt to delete partial upload on failure
		_ = g.client.Bucket(g.bucketName).Object(objectKey).Delete(ctx)
		return fmt.Errorf("failed to upload model to GCS: %w", err)
	}

	if err := wc.Close(); err != nil {
		_ = g.client.Bucket(g.bucketName).Object(objectKey).Delete(ctx)
		return fmt.Errorf("failed to finalize GCS upload: %w", err)
	}

	g.logger.Info("Model uploaded successfully to GCS",
		map[string]interface{}{
			"model_id": modelID,
			"version":  version,
			"object":   objectKey,
		})

	return nil
}

// DownloadModel downloads a model from GCS to a local file path.
func (g *GCSService) DownloadModel(ctx context.Context, modelID, version, targetPath string) error {
	objectKey := g.getModelObjectKey(modelID, version)

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		return fmt.Errorf("failed to create target directory: %w", err)
	}

	// Open local file for writing
	file, err := os.Create(targetPath)
	if err != nil {
		return fmt.Errorf("failed to create target file: %w", err)
	}
	defer file.Close()

	// Create reader from GCS object
	rc, err := g.client.Bucket(g.bucketName).Object(objectKey).NewReader(ctx)
	if err != nil {
		if err == storage.ErrObjectNotExist {
			return fmt.Errorf("model not found in GCS: model_id=%s, version=%s", modelID, version)
		}
		return fmt.Errorf("failed to read object from GCS: %w", err)
	}
	defer rc.Close()

	// Copy content
	if _, err := io.Copy(file, rc); err != nil {
		// Clean up partially downloaded file
		_ = os.Remove(targetPath)
		return fmt.Errorf("failed to download model from GCS: %w", err)
	}

	g.logger.Info("Model downloaded successfully from GCS",
		map[string]interface{}{
			"model_id":   modelID,
			"version":    version,
			"object":     objectKey,
			"targetPath": targetPath,
		})

	return nil
}

// ModelExists checks if a specific model version exists in GCS.
func (g *GCSService) ModelExists(ctx context.Context, modelID, version string) (bool, error) {
	objectKey := g.getModelObjectKey(modelID, version)

	_, err := g.client.Bucket(g.bucketName).Object(objectKey).Attrs(ctx)
	if err != nil {
		if err == storage.ErrObjectNotExist {
			return false, nil
		}
		return false, fmt.Errorf("failed to check model existence in GCS: %w", err)
	}

	return true, nil
}

// ListModelVersions returns all available versions of a model.
func (g *GCSService) ListModelVersions(ctx context.Context, modelID string) ([]string, error) {
	prefix := filepath.Join(g.basePath, modelID) + "/"
	var versions []string

	it := g.client.Bucket(g.bucketName).Objects(ctx, &storage.Query{
		Prefix:   prefix,
		Versions: false,
	})

	for {
		attrs, err := it.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to iterate GCS objects: %w", err)
		}

		// Parse version from object key (basePath/modelID/version/model.bin)
		relKey, err := filepath.Rel(g.basePath, attrs.Name)
		if err != nil {
			continue
		}

		parts := strings.Split(strings.Trim(relKey, "/"), "/")
		if len(parts) >= 2 {
			version := parts[1]
			if !contains(versions, version) {
				versions = append(versions, version)
			}
		}
	}

	return versions, nil
}

// DeleteModel removes all versions of a model from GCS.
func (g *GCSService) DeleteModel(ctx context.Context, modelID string) error {
	prefix := filepath.Join(g.basePath, modelID) + "/"

	it := g.client.Bucket(g.bucketName).Objects(ctx, &storage.Query{
		Prefix: prefix,
	})

	var deleteErrors []string
	for {
		attrs, err := it.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("failed to list objects for deletion: %w", err)
		}

		if err := g.client.Bucket(g.bucketName).Object(attrs.Name).Delete(ctx); err != nil {
			if err != storage.ErrObjectNotExist {
				deleteErrors = append(deleteErrors, fmt.Sprintf("object=%s: %v", attrs.Name, err))
			}
			continue
		}

		g.logger.Info("Deleted model object",
			map[string]interface{}{
				"model_id": modelID,
				"object":   attrs.Name,
			})
	}

	if len(deleteErrors) > 0 {
		return fmt.Errorf("failed to delete some model objects: %s", strings.Join(deleteErrors, "; "))
	}

	return nil
}

// DeleteModelVersion removes a specific version of a model.
func (g *GCSService) DeleteModelVersion(ctx context.Context, modelID, version string) error {
	objectKey := g.getModelObjectKey(modelID, version)

	err := g.client.Bucket(g.bucketName).Object(objectKey).Delete(ctx)
	if err != nil && err != storage.ErrObjectNotExist {
		return fmt.Errorf("failed to delete model version from GCS: %w", err)
	}

	if err == storage.ErrObjectNotExist {
		return fmt.Errorf("model version not found: model_id=%s, version=%s", modelID, version)
	}

	g.logger.Info("Model version deleted",
		map[string]interface{}{
			"model_id": modelID,
			"version":  version,
		})

	return nil
}

// GetModelURL returns a signed URL for accessing the model object.
func (g *GCSService) GetModelURL(ctx context.Context, modelID, version string, duration time.Duration) (string, error) {
	objectKey := g.getModelObjectKey(modelID, version)

	url, err := g.client.Bucket(g.bucketName).SignedURL(objectKey, &storage.SignedURLOptions{
		Method:  http.MethodGet,
		Expires: time.Now().Add(duration),
	})
	if err != nil {
		return "", fmt.Errorf("failed to generate signed URL: %w", err)
	}

	return url, nil
}

// Close shuts down the GCS client connection.
func (g *GCSService) Close() error {
	return g.client.Close()
}

// getModelObjectKey constructs the GCS object key for a model.
func (g *GCSService) getModelObjectKey(modelID, version string) string {
	return filepath.Join(g.basePath, modelID, version, "model.bin")
}

// cleanPath ensures the path format is consistent
func cleanPath(p string) string {
	return strings.Trim(strings.ReplaceAll(p, "\\", "/"), "/")
}

// contains checks if a string exists in a slice
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}