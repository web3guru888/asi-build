package storage

import (
	"context"
	"fmt"
	"io"
	"net/url"
	"path/filepath"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/s3/manager"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

// S3Client wraps the AWS S3 client and provides high-level operations for model storage
type S3Client struct {
	client     *s3.Client
	uploader   *manager.Uploader
	downloader *manager.Downloader
	bucket     string
	region     string
	prefix     string
}

// NewS3Client initializes and returns a new S3Client
func NewS3Client(cfg *config.Config) (*S3Client, error) {
	if cfg == nil {
		return nil, fmt.Errorf("config cannot be nil")
	}

	if cfg.S3.Bucket == "" {
		return nil, fmt.Errorf("S3 bucket name is required")
	}

	if cfg.S3.Region == "" {
		return nil, fmt.Errorf("S3 region is required")
	}

	// Load AWS configuration
	awsCfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion(cfg.S3.Region),
		config.WithCredentialsProvider(cfg.CredentialsProvider),
	)
	if err != nil {
		logging.Error("Failed to load AWS config", "error", err)
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	// Create S3 client
	client := s3.NewFromConfig(awsCfg)

	// Create uploader and downloader
	uploader := manager.NewUploader(client)
	downloader := manager.NewDownloader(client)

	// Optional prefix/base path for models
	prefix := cfg.S3.Prefix
	if prefix == "" {
		prefix = "models"
	}

	logging.Info("S3 client initialized",
		"bucket", cfg.S3.Bucket,
		"region", cfg.S3.Region,
		"prefix", prefix,
	)

	return &S3Client{
		client:     client,
		uploader:   uploader,
		downloader: downloader,
		bucket:     cfg.S3.Bucket,
		region:     cfg.S3.Region,
		prefix:     prefix,
	}, nil
}

// UploadModel uploads a model file to S3 with a key based on model name and version
func (s *S3Client) UploadModel(ctx context.Context, modelName, version, filePath string) error {
	key := s.getModelKey(modelName, version)

	file, err := os.Open(filePath)
	if err != nil {
		logging.Error("Failed to open model file for upload", "file", filePath, "error", err)
		return fmt.Errorf("failed to open file %s: %w", filePath, err)
	}
	defer file.Close()

	_, err = s.uploader.Upload(ctx, &s3.PutObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
		Body:   file,
	})
	if err != nil {
		logging.Error("Failed to upload model to S3", "model", modelName, "version", version, "key", key, "error", err)
		return fmt.Errorf("failed to upload model %s:%s to S3: %w", modelName, version, err)
	}

	logging.Info("Model uploaded successfully", "model", modelName, "version", version, "key", key)
	return nil
}

// DownloadModel downloads a model file from S3 to local path
func (s *S3Client) DownloadModel(ctx context.Context, modelName, version, downloadPath string) error {
	key := s.getModelKey(modelName, version)

	// Ensure the directory exists
	if err := os.MkdirAll(downloadPath, os.ModePerm); err != nil {
		logging.Error("Failed to create download directory", "path", downloadPath, "error", err)
		return fmt.Errorf("failed to create download directory %s: %w", downloadPath, err)
	}

	localFile, err := os.Create(filepath.Join(downloadPath, filepath.Base(key)))
	if err != nil {
		logging.Error("Failed to create local file for download", "file", localFile, "error", err)
		return fmt.Errorf("failed to create local file: %w", err)
	}
	defer localFile.Close()

	_, err = s.downloader.Download(ctx, io.WriterAtCloser(localFile), &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		logging.Error("Failed to download model from S3", "model", modelName, "version", version, "key", key, "error", err)
		return fmt.Errorf("failed to download model %s:%s from S3: %w", modelName, version, err)
	}

	logging.Info("Model downloaded successfully", "model", modelName, "version", version, "local_path", localFile.Name())
	return nil
}

// ListModels returns a list of available models (prefixes) in the bucket
func (s *S3Client) ListModels(ctx context.Context) ([]string, error) {
	prefix := s.prefix
	if !strings.HasSuffix(prefix, "/") {
		prefix += "/"
	}

	input := &s3.ListObjectsV2Input{
		Bucket:  aws.String(s.bucket),
		Prefix:  aws.String(prefix),
		Delimiter: aws.String("/"),
	}

	result, err := s.client.ListObjectsV2(ctx, input)
	if err != nil {
		logging.Error("Failed to list models in S3", "bucket", s.bucket, "prefix", prefix, "error", err)
		return nil, fmt.Errorf("failed to list models in bucket %s: %w", s.bucket, err)
	}

	var models []string
	seen := make(map[string]bool)

	for _, prefix := range result.CommonPrefixes {
		// Extract model name from prefix like "models/resnet50/"
		p := aws.ToString(prefix.Prefix)
		rel := strings.TrimPrefix(p, s.prefix+"/")
		parts := strings.Split(rel, "/")
		if len(parts) > 0 && parts[0] != "" {
			modelName := parts[0]
			if !seen[modelName] {
				models = append(models, modelName)
				seen[modelName] = true
			}
		}
	}

	logging.Info("Listed models from S3", "count", len(models))
	return models, nil
}

// ListModelVersions returns all versions available for a given model
func (s *S3Client) ListModelVersions(ctx context.Context, modelName string) ([]string, error) {
	prefix := fmt.Sprintf("%s/%s", s.prefix, modelName)

	input := &s3.ListObjectsV2Input{
		Bucket: aws.String(s.bucket),
		Prefix: aws.String(prefix),
	}

	var versions []string
	var err error
	var result *s3.ListObjectsV2Output

	err = s.client.ListObjectsV2Paginator.NewPaginator(input).ForEachPage(ctx, func(page *s3.ListObjectsV2Output, lastPage bool) bool {
		result = page
		for _, obj := range result.Contents {
			key := aws.ToString(obj.Key)
			// Expect key like "models/resnet50/v1.0.0/model.pkl"
			rel := strings.TrimPrefix(key, prefix+"/")
			parts := strings.Split(rel, "/")
			if len(parts) >= 1 {
				version := parts[0]
				// Avoid duplicates
				found := false
				for _, v := range versions {
					if v == version {
						found = true
						break
					}
				}
				if !found {
					versions = append(versions, version)
				}
			}
		}
		return true // continue iterating
	})

	if err != nil {
		logging.Error("Failed to list model versions in S3", "model", modelName, "error", err)
		return nil, fmt.Errorf("failed to list versions for model %s: %w", modelName, err)
	}

	logging.Info("Listed model versions", "model", modelName, "versions", versions)
	return versions, nil
}

// DeleteModel removes all versions of a model from S3
func (s *S3Client) DeleteModel(ctx context.Context, modelName string) error {
	prefix := fmt.Sprintf("%s/%s", s.prefix, modelName)

	input := &s3.ListObjectsV2Input{
		Bucket: aws.String(s.bucket),
		Prefix: aws.String(prefix),
	}

	var objects []types.ObjectIdentifier
	err := s.client.ListObjectsV2Paginator.NewPaginator(input).ForEachPage(ctx, func(page *s3.ListObjectsV2Output, lastPage bool) bool {
		for _, obj := range page.Contents {
			objects = append(objects, types.ObjectIdentifier{
				Key: obj.Key,
			})
		}
		return true
	})

	if err != nil {
		logging.Error("Failed to list objects for deletion", "model", modelName, "error", err)
		return fmt.Errorf("failed to list objects for model %s: %w", modelName, err)
	}

	if len(objects) == 0 {
		logging.Info("No objects found for model, nothing to delete", "model", modelName)
		return nil
	}

	// Delete in batches of up to 1000
	const batchSize = 1000
	for i := 0; i < len(objects); i += batchSize {
		end := i + batchSize
		if end > len(objects) {
			end = len(objects)
		}

		batch := objects[i:end]
		_, err = s.client.DeleteObjects(ctx, &s3.DeleteObjectsInput{
			Bucket: aws.String(s.bucket),
			Delete: &types.Delete{
				Objects: batch,
				Quiet:   aws.Bool(false),
			},
		})
		if err != nil {
			logging.Error("Failed to delete object batch from S3", "error", err)
			return fmt.Errorf("failed to delete object batch: %w", err)
		}
	}

	logging.Info("Model deleted from S3", "model", modelName, "object_count", len(objects))
	return nil
}

// DeleteModelVersion removes a specific version of a model from S3
func (s *S3Client) DeleteModelVersion(ctx context.Context, modelName, version string) error {
	key := s.getModelKey(modelName, version)

	_, err := s.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		logging.Error("Failed to delete model version from S3", "model", modelName, "version", version, "error", err)
		return fmt.Errorf("failed to delete model %s:%s from S3: %w", modelName, version, err)
	}

	logging.Info("Model version deleted", "model", modelName, "version", version)
	return nil
}

// GetModelMetadata retrieves metadata for a model version from S3
func (s *S3Client) GetModelMetadata(ctx context.Context, modelName, version string) (map[string]string, error) {
	key := s.getModelKey(modelName, version)

	headOutput, err := s.client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		logging.Error("Failed to retrieve model metadata", "model", modelName, "version", version, "error", err)
		return nil, fmt.Errorf("failed to get metadata for model %s:%s: %w", modelName, version, err)
	}

	metadata := make(map[string]string)
	for k, v := range headOutput.Metadata {
		metadata[k] = v
	}

	// Add standard metadata
	if headOutput.ETag != nil {
		metadata["etag"] = *headOutput.ETag
	}
	if headOutput.LastModified != nil {
		metadata["last_modified"] = headOutput.LastModified.Format(time.RFC3339)
	}
	if headOutput.ContentLength > 0 {
		metadata["content_length"] = fmt.Sprintf("%d", headOutput.ContentLength)
	}

	logging.Info("Retrieved model metadata", "model", modelName, "version", version)
	return metadata, nil
}

// SetModelMetadata sets custom metadata for a model object in S3
func (s *S3Client) SetModelMetadata(ctx context.Context, modelName, version string, metadata map[string]string) error {
	key := s.getModelKey(modelName, version)

	// Get current object attributes
	headOutput, err := s.client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		logging.Error("Failed to get current object attributes", "model", modelName, "version", version, "error", err)
		return fmt.Errorf("failed to get object attributes: %w", err)
	}

	// Copy object to itself with new metadata
	_, err = s.client.CopyObject(ctx, &s3.CopyObjectInput{
		Bucket:     aws.String(s.bucket),
		CopySource: aws.String(s.bucket + "/" + key),
		Key:        aws.String(key),
		Metadata:   metadata,
		MetadataDirective: types.MetadataDirectiveReplace,
	})
	if err != nil {
		logging.Error("Failed to update model metadata", "model", modelName, "version", version, "error", err)
		return fmt.Errorf("failed to update metadata for model %s:%s: %w", modelName, version, err)
	}

	logging.Info("Model metadata updated", "model", modelName, "version", version)
	return nil
}

// GeneratePresignedURL generates a temporary presigned URL for downloading a model
func (s *S3Client) GeneratePresignedURL(ctx context.Context, modelName, version string, expires time.Duration) (string, error) {
	key := s.getModelKey(modelName, version)

	presigner := s3.NewPresignClient(s.client)
	presignedReq, err := presigner.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	}, func(opts *s3.PresignOptions) {
		opts.Expires = expires
	})
	if err != nil {
		logging.Error("Failed to generate presigned URL", "model", modelName, "version", version, "error", err)
		return "", fmt.Errorf("failed to generate presigned URL: %w", err)
	}

	logging.Info("Presigned URL generated", "model", modelName, "version", version, "expires_in_seconds", int64(expires.Seconds()))
	return presignedReq.URL, nil
}

// Close shuts down the S3 client cleanly
func (s *S3Client) Close() error {
	// No explicit close needed for AWS SDK v2 clients
	// Resources are managed automatically
	logging.Info("S3 client closed", "bucket", s.bucket)
	return nil
}

// getModelKey constructs the S3 key for a model version
func (s *S3Client) getModelKey(modelName, version string) string {
	// Sanitize inputs to prevent path traversal
	safeModelName := url.PathEscape(modelName)
	safeVersion := url.PathEscape(version)

	// Construct path like: models/resnet50/v1.0.0/model.pkl
	return fmt.Sprintf("%s/%s/%s/model.pkl", s.prefix, safeModelName, safeVersion)
}