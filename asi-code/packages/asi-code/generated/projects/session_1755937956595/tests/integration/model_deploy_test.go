package model

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/deployer"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/model/registry"
	"mlops-platform/internal/model/repository"
)

// TestDeployerIntegration performs end-to-end integration testing
// for model deployment, loading, serving, and cleanup
func TestDeployerIntegration(t *testing.T) {
	// Set up test configuration
	cfg := &config.Config{
		ModelServer: config.ModelServerConfig{
			ModelDir:       t.TempDir(),
			MaxModelSizeMB: 1024,
			GracefulShutdownTimeout: 5 * time.Second,
		},
		ModelRegistry: config.ModelRegistryConfig{
			URL:       "https://mock-registry.example.com",
			AuthToken: "test-token",
		},
	}

	// Initialize logger
	logger := logging.NewLogger(&logging.Config{
		Level:  "debug",
		Format: "json",
	})

	// Create mock model registry client
	mockRegistry := &registry.MockClient{
		Models: map[string]registry.ModelMetadata{
			"test-model": {
				Name:    "test-model",
				Version: "v1.0.0",
				Path:    "models/test-model/v1.0.0/model.bin",
				Format:  "onnx",
				Hash:    "sha256:abcd1234",
			},
		},
		DownloadHandler: func(w http.ResponseWriter, r *http.Request) {
			modelData := "fake model binary data"
			http.ServeContent(w, r, "model.bin", time.Now(), strings.NewReader(modelData))
		},
	}

	// Create temporary storage directory
	storageDir := filepath.Join(cfg.ModelServer.ModelDir, "storage")
	if err := os.MkdirAll(storageDir, 0755); err != nil {
		t.Fatalf("failed to create storage dir: %v", err)
	}

	// Initialize repository
	repo := repository.NewModelRepository(storageDir, logger)

	// Initialize model loader
	modelLoader := loader.NewModelLoader(cfg, logger)

	// Initialize deployer
	deployer := deployer.NewModelDeployer(cfg, logger, mockRegistry, repo, modelLoader)

	// Test context
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Test case 1: Deploy a new model
	t.Run("DeployNewModel", func(t *testing.T) {
		err := deployer.DeployModel(ctx, "test-model", "v1.0.0")
		if err != nil {
			t.Fatalf("expected no error, got: %v", err)
		}

		// Verify model is registered in repository
		model, err := repo.GetModel("test-model", "v1.0.0")
		if err != nil {
			t.Fatalf("expected model to be in repository: %v", err)
		}
		if model.Name != "test-model" || model.Version != "v1.0.0" {
			t.Errorf("unexpected model metadata: %+v", model)
		}

		// Verify model files exist
		modelPath := filepath.Join(storageDir, "test-model", "v1.0.0")
		if _, err := os.Stat(modelPath); os.IsNotExist(err) {
			t.Errorf("expected model directory to exist at %s", modelPath)
		}
	})

	// Test case 2: Redeploy existing model (idempotent)
	t.Run("RedeployExistingModel", func(t *testing.T) {
		err := deployer.DeployModel(ctx, "test-model", "v1.0.0")
		if err != nil {
			t.Fatalf("expected redeploy to succeed: %v", err)
		}
	})

	// Test case 3: Load and serve model
	t.Run("LoadAndServeModel", func(t *testing.T) {
		// Load model into memory
		servingModel, err := modelLoader.LoadModel(ctx, "test-model", "v1.0.0")
		if err != nil {
			t.Fatalf("failed to load model: %v", err)
		}
		defer func() {
			if err := modelLoader.UnloadModel("test-model", "v1.0.0"); err != nil {
				t.Logf("warning: failed to unload model during cleanup: %v", err)
			}
		}()

		if servingModel == nil {
			t.Fatal("expected loaded model, got nil")
		}
		if servingModel.Metadata.Name != "test-model" {
			t.Errorf("expected model name test-model, got %s", servingModel.Metadata.Name)
		}

		// Simulate inference request handling
		handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method != http.MethodPost {
				http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
				return
			}
			if r.Header.Get("Content-Type") != "application/json" {
				http.Error(w, "unsupported media type", http.StatusUnsupportedMediaType)
				return
			}

			// Echo back the request for testing
			body, _ := io.ReadAll(r.Body)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			fmt.Fprintf(w, `{"predictions": %s, "model": "test-model", "version": "v1.0.0"}`, string(body))
		})

		// Start test server
		server := httptest.NewServer(handler)
		defer server.Close()

		// Make test prediction request
		client := &http.Client{Timeout: 5 * time.Second}
		resp, err := client.Post(server.URL, "application/json", strings.NewReader(`[0.1,0.2,0.3]`))
		if err != nil {
			t.Fatalf("failed to make prediction request: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", resp.StatusCode)
		}

		body, _ := io.ReadAll(resp.Body)
		if !strings.Contains(string(body), "test-model") {
			t.Errorf("response does not contain model name: %s", string(body))
		}
	})

	// Test case 4: List deployed models
	t.Run("ListDeployedModels", func(t *testing.T) {
		models, err := repo.ListModels()
		if err != nil {
			t.Fatalf("failed to list models: %v", err)
		}

		if len(models) != 1 {
			t.Errorf("expected 1 deployed model, got %d", len(models))
		}
		if models[0].Name != "test-model" || models[0].Version != "v1.0.0" {
			t.Errorf("unexpected model in list: %+v", models[0])
		}
	})

	// Test case 5: Delete deployed model
	t.Run("DeleteDeployedModel", func(t *testing.T) {
		err := deployer.DeleteModel(ctx, "test-model", "v1.0.0")
		if err != nil {
			t.Fatalf("expected no error when deleting model: %v", err)
		}

		// Verify model is removed from repository
		_, err = repo.GetModel("test-model", "v1.0.0")
		if err == nil {
			t.Error("expected model to be deleted, but still exists")
		}

		// Verify model directory is removed
		modelPath := filepath.Join(storageDir, "test-model", "v1.0.0")
		if _, err := os.Stat(modelPath); !os.IsNotExist(err) {
			t.Errorf("expected model directory to be deleted, but still exists at %s", modelPath)
		}
	})
}

// TestDeployerErrorCases tests various error conditions
func TestDeployerErrorCases(t *testing.T) {
	cfg := &config.Config{
		ModelServer: config.ModelServerConfig{
			ModelDir:       t.TempDir(),
			MaxModelSizeMB: 1,
		},
		ModelRegistry: config.ModelRegistryConfig{
			URL:       "https://mock-registry.example.com",
			AuthToken: "test-token",
		},
	}

	logger := logging.NewLogger(&logging.Config{Level: "debug"})

	// Mock registry with various error scenarios
	mockRegistry := &registry.MockClient{
		DownloadHandler: func(w http.ResponseWriter, r *http.Request) {
			// Simulate large file exceeding size limit
			reader := strings.NewReader("this is a very long string that exceeds the model size limit when repeated multiple times")
			largeReader := io.LimitReader(io.TeeReader(reader, os.Stdout), 2*1024*1024) // 2MB
			http.ServeContent(w, r, "large-model.bin", time.Now(), largeReader.(io.ReadSeeker))
		},
	}

	storageDir := filepath.Join(cfg.ModelServer.ModelDir, "storage")
	if err := os.MkdirAll(storageDir, 0755); err != nil {
		t.Fatalf("failed to create storage dir: %v", err)
	}

	repo := repository.NewModelRepository(storageDir, logger)
	modelLoader := loader.NewModelLoader(cfg, logger)
	deployer := deployer.NewModelDeployer(cfg, logger, mockRegistry, repo, modelLoader)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	t.Run("DeployNonExistentModel", func(t *testing.T) {
		err := deployer.DeployModel(ctx, "non-existent", "v1.0.0")
		if err == nil {
			t.Fatal("expected error when deploying non-existent model")
		}
		if !strings.Contains(err.Error(), "model not found") && !strings.Contains(err.Error(), "404") {
			t.Errorf("unexpected error message: %v", err)
		}
	})

	t.Run("DeployModelExceedingSizeLimit", func(t *testing.T) {
		err := deployer.DeployModel(ctx, "large-model", "v1.0.0")
		if err == nil {
			t.Fatal("expected error when deploying model exceeding size limit")
		}
		if !strings.Contains(err.Error(), "exceeds maximum allowed size") {
			t.Errorf("unexpected error message for size limit: %v", err)
		}
	})

	t.Run("DeleteNonExistentModel", func(t *testing.T) {
		err := deployer.DeleteModel(ctx, "non-existent", "v1.0.0")
		if err != nil {
			t.Errorf("expected no error when deleting non-existent model, got: %v", err)
		}
	})
}

// Mock model registry client for testing
type MockClient struct {
	Models          map[string]registry.ModelMetadata
	DownloadHandler func(w http.ResponseWriter, r *http.Request)
}

func (m *MockClient) GetModelMetadata(ctx context.Context, modelName, version string) (*registry.ModelMetadata, error) {
	if metadata, exists := m.Models[modelName]; exists && metadata.Version == version {
		return &metadata, nil
	}
	return nil, fmt.Errorf("model %s:%s not found", modelName, version)
}

func (m *MockClient) ListModels(ctx context.Context, filter string) ([]registry.ModelMetadata, error) {
	var models []registry.ModelMetadata
	for _, metadata := range m.Models {
		if filter == "" || strings.Contains(metadata.Name, filter) {
			models = append(models, metadata)
		}
	}
	return models, nil
}

func (m *MockClient) DownloadModel(ctx context.Context, modelName, version, targetPath string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "http://mock-registry/models/"+modelName+"/"+version, nil)
	if err != nil {
		return err
	}

	rr := httptest.NewRecorder()
	m.DownloadHandler(rr, req)

	if rr.Code >= 400 {
		return fmt.Errorf("download failed with status %d", rr.Code)
	}

	file, err := os.Create(targetPath)
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = io.Copy(file, rr.Body)
	return err
}

func (m *MockClient) UploadModel(ctx context.Context, modelName, version, filePath string) error {
	if _, err := os.Stat(filePath); err != nil {
		return fmt.Errorf("model file not found: %v", err)
	}
	return nil
}

// TestConfigValidation checks configuration requirements
func TestConfigValidation(t *testing.T) {
	tests := []struct {
		name    string
		cfg     *config.Config
		wantErr bool
	}{
		{
			name: "ValidConfig",
			cfg: &config.Config{
				ModelServer: config.ModelServerConfig{
					ModelDir:       t.TempDir(),
					MaxModelSizeMB: 1024,
				},
			},
			wantErr: false,
		},
		{
			name: "InvalidModelDir",
			cfg: &config.Config{
				ModelServer: config.ModelServerConfig{
					ModelDir:       "/invalid/path/that/does/not/exist",
					MaxModelSizeMB: 1024,
				},
			},
			wantErr: true,
		},
		{
			name: "ZeroSizeLimit",
			cfg: &config.Config{
				ModelServer: config.ModelServerConfig{
					ModelDir:       t.TempDir(),
					MaxModelSizeMB: 0,
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			logger := logging.NewLogger(&logging.Config{Level: "debug"})
			storageDir := filepath.Join(tt.cfg.ModelServer.ModelDir, "storage")
			os.MkdirAll(storageDir, 0755)

			repo := repository.NewModelRepository(storageDir, logger)
			modelLoader := loader.NewModelLoader(tt.cfg, logger)
			deployer := deployer.NewModelDeployer(tt.cfg, logger, &registry.MockClient{}, repo, modelLoader)

			// Try to deploy (will trigger config validation)
			err := deployer.DeployModel(context.Background(), "test-model", "v1.0.0")

			if tt.wantErr && err == nil {
				t.Fatal("expected error but got none")
			}
			if !tt.wantErr && err != nil {
				t.Fatalf("expected no error but got: %v", err)
			}
		})
	}
}