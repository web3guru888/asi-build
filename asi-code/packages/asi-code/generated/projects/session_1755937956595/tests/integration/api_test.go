package api

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/registry"
	"mlops-platform/internal/model/repository"
	"mlops-platform/internal/model/service"
)

func setupTestServer() (*httptest.Server, func()) {
	cfg := &config.Config{
		API: config.APIConfig{
			Host: "localhost",
			Port: 8080,
		},
		ModelServer: config.ModelServerConfig{
			ModelsDir:        "./test_models",
			MaxModelSize:     1073741824, // 1GB
			AllowedModelTypes: []string{"onnx", "pb", "pt", "joblib"},
		},
	}

	logger := logging.NewLogger()

	// Setup test model repository
	modelRepo := repository.NewModelRepository(cfg, logger)

	// Setup model registry client
	registryClient := registry.NewModelRegistryClient(
		&http.Client{Timeout: 10 * time.Second},
		&url.URL{Scheme: "http", Host: "localhost:8081"},
	)

	// Setup model service
	modelService := service.NewModelService(modelRepo, registryClient, logger, cfg)

	// Setup handlers
	handlers := NewHandlers(modelService, cfg)

	// Setup routes
	mux := http.NewServeMux()
	setupRoutes(mux, handlers, cfg)

	// Create test server
	server := httptest.NewTLSServer(mux)

	teardown := func() {
		server.Close()
		os.RemoveAll("./test_models") // Clean up test models directory
	}

	return server, teardown
}

func TestAPIGatewayIntegration(t *testing.T) {
	t.Parallel()

	server, teardown := setupTestServer()
	defer teardown()

	client := &http.Client{Timeout: 30 * time.Second}

	t.Run("health check endpoint", func(t *testing.T) {
		req, err := http.NewRequest("GET", server.URL+"/health", nil)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", resp.StatusCode)
		}

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			t.Fatalf("failed to read response body: %v", err)
		}

		if !strings.Contains(string(body), "healthy") {
			t.Errorf("expected healthy response, got %s", string(body))
		}
	})

	t.Run("list models endpoint", func(t *testing.T) {
		req, err := http.NewRequest("GET", server.URL+"/api/v1/models", nil)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			t.Errorf("expected status 200, got %d", resp.StatusCode)
		}

		// Should return JSON array
		if resp.Header.Get("Content-Type") != "application/json" {
			t.Errorf("expected application/json content type, got %s", resp.Header.Get("Content-Type"))
		}
	})

	t.Run("get model endpoint", func(t *testing.T) {
		req, err := http.NewRequest("GET", server.URL+"/api/v1/models/test-model", nil)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Errorf("expected status 404 for non-existent model, got %d", resp.StatusCode)
		}
	})

	t.Run("deploy model endpoint", func(t *testing.T) {
		// First create test model dir
		err := os.MkdirAll("./test_models", 0755)
		if err != nil {
			t.Fatalf("failed to create test models directory: %v", err)
		}

		payload := strings.NewReader(`{
			"name": "test-model",
			"version": "1.0",
			"source": "registry://test-model:1.0",
			"runtime": "onnx"
		}`)

		req, err := http.NewRequest("POST", server.URL+"/api/v1/models", payload)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusAccepted {
			t.Errorf("expected status 202, got %d", resp.StatusCode)
		}
	})

	t.Run("predict endpoint", func(t *testing.T) {
		payload := strings.NewReader(`{"input": "test"}`)
		req, err := http.NewRequest("POST", server.URL+"/api/v1/models/test-model:predict", payload)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Errorf("expected status 404 for non-existent model, got %d", resp.StatusCode)
		}
	})

	t.Run("delete model endpoint", func(t *testing.T) {
		req, err := http.NewRequest("DELETE", server.URL+"/api/v1/models/test-model", nil)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", resp.StatusCode)
		}
	})
}

func TestModelDeploymentFlow(t *testing.T) {
	t.Parallel()

	server, teardown := setupTestServer()
	defer teardown()

	client := &http.Client{Timeout: 30 * time.Second}

	// Test full deployment flow
	t.Run("complete model lifecycle", func(t *testing.T) {
		modelName := "lifecycle-test"
		version := "1.0"

		// 1. Deploy model
		deployPayload := fmt.Sprintf(`{
			"name": "%s",
			"version": "%s",
			"source": "registry://%s:%s",
			"runtime": "onnx"
		}`, modelName, version, modelName, version)

		deployReq, err := http.NewRequest("POST", server.URL+"/api/v1/models", strings.NewReader(deployPayload))
		if err != nil {
			t.Fatalf("failed to create deploy request: %v", err)
		}
		deployReq.Header.Set("Content-Type", "application/json")

		deployResp, err := client.Do(deployReq)
		if err != nil {
			t.Fatalf("deploy request failed: %v", err)
		}
		deployResp.Body.Close()

		if deployResp.StatusCode != http.StatusAccepted {
			t.Errorf("expected status 202 for deployment, got %d", deployResp.StatusCode)
		}

		// 2. Wait for deployment to complete (simulate)
		time.Sleep(100 * time.Millisecond)

		// 3. List models
		listReq, err := http.NewRequest("GET", server.URL+"/api/v1/models", nil)
		if err != nil {
			t.Fatalf("failed to create list request: %v", err)
		}

		listResp, err := client.Do(listReq)
		if err != nil {
			t.Fatalf("list request failed: %v", err)
		}
		listResp.Body.Close()

		if listResp.StatusCode != http.StatusOK {
			t.Errorf("expected status 200 for list, got %d", listResp.StatusCode)
		}

		// 4. Get specific model
		getReq, err := http.NewRequest("GET", server.URL+"/api/v1/models/"+modelName, nil)
		if err != nil {
			t.Fatalf("failed to create get request: %v", err)
		}

		getResp, err := client.Do(getReq)
		if err != nil {
			t.Fatalf("get request failed: %v", err)
		}
		getResp.Body.Close()

		if getResp.StatusCode != http.StatusOK {
			t.Errorf("expected status 200 for get, got %d", getResp.StatusCode)
		}

		// 5. Predict
		predictPayload := `{"data": [1.0, 2.0, 3.0]}`
		predictReq, err := http.NewRequest("POST", server.URL+"/api/v1/models/"+modelName+":predict", strings.NewReader(predictPayload))
		if err != nil {
			t.Fatalf("failed to create predict request: %v", err)
		}
		predictReq.Header.Set("Content-Type", "application/json")

		predictResp, err := client.Do(predictReq)
		if err != nil {
			t.Fatalf("predict request failed: %v", err)
		}
		predictResp.Body.Close()

		if predictResp.StatusCode != http.StatusNotFound {
			t.Errorf("expected status 404 for predict (model not actually loaded), got %d", predictResp.StatusCode)
		}

		// 6. Delete model
		deleteReq, err := http.NewRequest("DELETE", server.URL+"/api/v1/models/"+modelName, nil)
		if err != nil {
			t.Fatalf("failed to create delete request: %v", err)
		}

		deleteResp, err := client.Do(deleteReq)
		if err != nil {
			t.Fatalf("delete request failed: %v", err)
		}
		deleteResp.Body.Close()

		if deleteResp.StatusCode != http.StatusNoContent {
			t.Errorf("expected status 204 for delete, got %d", deleteResp.StatusCode)
		}
	})
}

func TestErrorHandling(t *testing.T) {
	t.Parallel()

	server, teardown := setupTestServer()
	defer teardown()

	client := &http.Client{Timeout: 30 * time.Second}

	t.Run("invalid json payload", func(t *testing.T) {
		payload := strings.NewReader(`{invalid json}`)
		req, err := http.NewRequest("POST", server.URL+"/api/v1/models", payload)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("expected status 400 for invalid json, got %d", resp.StatusCode)
		}
	})

	t.Run("missing required fields", func(t *testing.T) {
		payload := strings.NewReader(`{"name": ""}`)
		req, err := http.NewRequest("POST", server.URL+"/api/v1/models", payload)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("expected status 400 for missing fields, got %d", resp.StatusCode)
		}
	})

	t.Run("unsupported media type", func(t *testing.T) {
		payload := strings.NewReader(`{"name": "test"}`)
		req, err := http.NewRequest("POST", server.URL+"/api/v1/models", payload)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}
		req.Header.Set("Content-Type", "text/plain")

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusUnsupportedMediaType {
			t.Errorf("expected status 415, got %d", resp.StatusCode)
		}
	})
}

func TestConcurrentRequests(t *testing.T) {
	t.Parallel()

	server, teardown := setupTestServer()
	defer teardown()

	client := &http.Client{Timeout: 30 * time.Second}

	t.Run("handle concurrent health checks", func(t *testing.T) {
		const concurrency = 10
		const requestsPerWorker = 10

		errChan := make(chan error, concurrency*requestsPerWorker)

		for i := 0; i < concurrency; i++ {
			go func() {
				for j := 0; j < requestsPerWorker; j++ {
					req, err := http.NewRequest("GET", server.URL+"/health", nil)
					if err != nil {
						errChan <- fmt.Errorf("failed to create request: %v", err)
						continue
					}

					resp, err := client.Do(req)
					if err != nil {
						errChan <- fmt.Errorf("request failed: %v", err)
						continue
					}

					if resp.StatusCode != http.StatusOK {
						errChan <- fmt.Errorf("expected status 200, got %d", resp.StatusCode)
					}

					resp.Body.Close()
				}
				errChan <- nil
			}()
		}

		// Collect results
		for i := 0; i < concurrency; i++ {
			err := <-errChan
			if err != nil {
				t.Errorf("worker failed: %v", err)
			}
		}
	})
}

func TestAuthenticationHeaders(t *testing.T) {
	t.Parallel()

	server, teardown := setupTestServer()
	defer teardown()

	client := &http.Client{Timeout: 30 * time.Second}

	t.Run("include auth header in responses", func(t *testing.T) {
		req, err := http.NewRequest("GET", server.URL+"/health", nil)
		if err != nil {
			t.Fatalf("failed to create request: %v", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			t.Fatalf("request failed: %v", err)
		}
		defer resp.Body.Close()

		// While we don't have authentication implemented in this test setup,
		// we ensure the security headers are present
		securityHeaders := []string{
			"X-Content-Type-Options",
			"X-Frame-Options",
			"X-XSS-Protection",
		}

		for _, header := range securityHeaders {
			if value := resp.Header.Get(header); value == "" {
				t.Errorf("expected header %s to be present", header)
			}
		}
	})
}