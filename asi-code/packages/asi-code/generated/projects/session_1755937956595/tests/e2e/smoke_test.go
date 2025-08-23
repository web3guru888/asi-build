package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"go.uber.org/goleak"
)

func TestMain(m *testing.M) {
	// Ensure no goroutine leaks
	goleak.VerifyTestMain(m)
}

func TestModelServingSmoke(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Check if model server is running
	modelServerURL := "http://localhost:8081"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, modelServerURL+"/health", nil)
	if err != nil {
		t.Fatalf("failed to create request: %v", err)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Skipf("model server not reachable at %s: %v - skipping smoke test", modelServerURL, err)
	}
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "health check should return 200 OK")

	// Verify required headers and response format
	assert.NotEmpty(t, resp.Header.Get("Server"), "Server header should be present")
	assert.Equal(t, "application/json", resp.Header.Get("Content-Type"), "Content-Type should be application/json")

	var healthResp map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&healthResp); err != nil {
		t.Fatalf("failed to decode health response: %v", err)
	}

	assert.Equal(t, "model-server", healthResp["service"], "service name should be model-server")
	assert.Equal(t, "healthy", healthResp["status"], "service status should be healthy")
	assert.Contains(t, healthResp, "version", "version should be present in response")
	assert.Contains(t, healthResp, "uptime", "uptime should be present in response")
	assert.Contains(t, healthResp, "timestamp", "timestamp should be present in response")

	// Test /models endpoint
	modelsReq, err := http.NewRequestWithContext(ctx, http.MethodGet, modelServerURL+"/models", nil)
	if err != nil {
		t.Fatalf("failed to create models request: %v", err)
	}

	modelsResp, err := client.Do(modelsReq)
	if err != nil {
		t.Fatalf("failed to call /models endpoint: %v", err)
	}
	defer modelsResp.Body.Close()

	assert.Equal(t, http.StatusOK, modelsResp.StatusCode, "/models should return 200 OK")

	var modelsRespBody map[string]interface{}
	if err := json.NewDecoder(modelsResp.Body).Decode(&modelsRespBody); err != nil {
		t.Fatalf("failed to decode /models response: %v", err)
	}

	assert.Contains(t, modelsRespBody, "models", "response should contain models key")
	assert.IsType(t, []interface{}{}, modelsRespBody["models"], "models should be an array")

	// Test inference endpoint (assuming default model is loaded)
	inferenceURL := modelServerURL + "/models/test-model:latest/predict"
	inferencePayload := `{"input": [[1.0, 2.0, 3.0, 4.0]]}`
	reqBody := strings.NewReader(inferencePayload)

	inferenceReq, err := http.NewRequestWithContext(ctx, http.MethodPost, inferenceURL, reqBody)
	if err != nil {
		t.Fatalf("failed to create inference request: %v", err)
	}
	inferenceReq.Header.Set("Content-Type", "application/json")

	// We expect either 200 (model exists) or 404 (no default model) but not 5xx
	inferenceResp, err := client.Do(inferenceReq)
	if err != nil {
		t.Fatalf("failed to call inference endpoint: %v", err)
	}
	defer inferenceResp.Body.Close()

	assert.Contains(t, []int{http.StatusOK, http.StatusNotFound, http.StatusBadRequest}, inferenceResp.StatusCode,
		"inference endpoint should return 200, 400, or 404 - not 5xx errors")

	if inferenceResp.StatusCode == http.StatusOK {
		var inferenceResponse map[string]interface{}
		if err := json.NewDecoder(inferenceResp.Body).Decode(&inferenceResponse); err != nil {
			t.Fatalf("failed to decode inference response: %v", err)
		}
		assert.Contains(t, inferenceResponse, "predictions", "successful inference should contain predictions")
		assert.Contains(t, inferenceResponse, "model", "response should contain model metadata")
		assert.Contains(t, inferenceResponse, "version", "response should contain model version")
		assert.Contains(t, inferenceResponse, "inference_time_ms", "response should contain inference timing")
	}
}

func TestAPIGatewaySmoke(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	apiGatewayURL := "http://localhost:8080"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiGatewayURL+"/health", nil)
	if err != nil {
		t.Fatalf("failed to create request: %v", err)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Skipf("api gateway not reachable at %s: %v - skipping smoke test", apiGatewayURL, err)
	}
	defer resp.Body.Close()

	assert.Equal(t, http.StatusOK, resp.StatusCode, "gateway health check should return 200 OK")

	var healthResp map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&healthResp); err != nil {
		t.Fatalf("failed to decode health response: %v", err)
	}

	assert.Equal(t, "api-gateway", healthResp["service"], "service name should be api-gateway")
	assert.Equal(t, "healthy", healthResp["status"], "service status should be healthy")
	assert.Contains(t, healthResp, "version", "version should be present in response")
	assert.Contains(t, healthResp, "uptime", "uptime should be present in response")
	assert.Contains(t, healthResp, "timestamp", "timestamp should be present in response")
	assert.Contains(t, healthResp, "dependencies", "dependencies status should be reported")

	if deps, ok := healthResp["dependencies"].(map[string]interface{}); ok {
		if modelSvc, ok := deps["model-service"]; ok {
			modelStatus := modelSvc.(map[string]interface{})["status"]
			assert.Contains(t, []interface{}{"healthy", "degraded", "unhealthy"}, modelStatus,
				"model-service dependency should have valid status")
		}
	}
}

func TestModelDeploymentLifecycle(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()

	modelServerURL := "http://localhost:8081"

	// Create a temporary model directory
	tmpDir, err := os.MkdirTemp("", "test-model-*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create mock model files
	modelPath := filepath.Join(tmpDir, "model.onnx")
	if err := os.WriteFile(modelPath, []byte("fake model content"), 0644); err != nil {
		t.Fatalf("failed to create mock model file: %v", err)
	}

	// Test model upload endpoint
	uploadURL := fmt.Sprintf("%s/models/upload", modelServerURL)
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)

	part, err := writer.CreateFormFile("model", filepath.Base(modelPath))
	if err != nil {
		t.Fatalf("failed to create form file: %v", err)
	}
	modelData, _ := os.ReadFile(modelPath)
	_, err = part.Write(modelData)
	if err != nil {
		t.Fatalf("failed to write model data: %v", err)
	}

	_ = writer.WriteField("model_id", "test-model")
	_ = writer.WriteField("version", "v1")
	_ = writer.WriteField("framework", "onnx")
	_ = writer.Close()

	uploadReq, err := http.NewRequestWithContext(ctx, http.MethodPost, uploadURL, body)
	if err != nil {
		t.Fatalf("failed to create upload request: %v", err)
	}
	uploadReq.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{Timeout: 15 * time.Second}
	uploadResp, err := client.Do(uploadReq)
	if err != nil {
		t.Fatalf("failed to upload model: %v", err)
	}
	defer uploadResp.Body.Close()

	if uploadResp.StatusCode != http.StatusCreated && uploadResp.StatusCode != http.StatusConflict {
		t.Fatalf("expected status 201 or 409, got %d: %s", uploadResp.StatusCode, slurpBody(uploadResp))
	}

	// Give time for model loading
	time.Sleep(2 * time.Second)

	// Test prediction with uploaded model
	inferenceURL := fmt.Sprintf("%s/models/test-model:v1/predict", modelServerURL)
	inferencePayload := `{"input": [[1.0, 2.0, 3.0, 4.0]]}`
	reqBody := strings.NewReader(inferencePayload)

	inferenceReq, err := http.NewRequestWithContext(ctx, http.MethodPost, inferenceURL, reqBody)
	if err != nil {
		t.Fatalf("failed to create inference request: %v", err)
	}
	inferenceReq.Header.Set("Content-Type", "application/json")

	// Try inference up to 3 times with backoff (model might still be loading)
	var inferenceResp *http.Response
	for i := 0; i < 3; i++ {
		inferenceResp, err = client.Do(inferenceReq)
		if err == nil {
			defer inferenceResp.Body.Close()
			if inferenceResp.StatusCode == http.StatusOK || inferenceResp.StatusCode == http.StatusServiceUnavailable {
				break
			}
		}
		time.Sleep(2 * time.Second)
	}

	if err != nil {
		t.Fatalf("failed to call inference endpoint after retries: %v", err)
	}

	// Either the model is ready or still loading
	if inferenceResp.StatusCode == http.StatusOK {
		var result map[string]interface{}
		if err := json.NewDecoder(inferenceResp.Body).Decode(&result); err != nil {
			t.Fatalf("failed to decode inference response: %v", err)
		}
		assert.Contains(t, result, "predictions")
	} else if inferenceResp.StatusCode == http.StatusServiceUnavailable {
		t.Logf("model still loading (StatusServiceUnavailable) - this is acceptable")
	} else {
		t.Fatalf("unexpected inference status after upload: %d - %s", inferenceResp.StatusCode, slurpBody(inferenceResp))
	}

	// Clean up: undeploy model
	undeployURL := fmt.Sprintf("%s/models/test-model:v1", modelServerURL)
	undeployReq, err := http.NewRequestWithContext(ctx, http.MethodDelete, undeployURL, nil)
	if err != nil {
		t.Fatalf("failed to create undeploy request: %v", err)
	}

	undeployResp, err := client.Do(undeployReq)
	if err != nil {
		t.Fatalf("failed to undeploy model: %v", err)
	}
	defer undeployResp.Body.Close()

	assert.Contains(t, []int{http.StatusOK, http.StatusNotFound}, undeployResp.StatusCode,
		"undeploy should return 200 or 404")
}

func TestIntegrationHealthCheck(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	const maxRetries = 6
	const delay = 5 * time.Second

	var lastErr error
	for i := 0; i < maxRetries; i++ {
		if i > 0 {
			t.Logf("Waiting %v for services to stabilize...", delay)
			time.Sleep(delay)
		}

		// Check both services
		if err := checkServiceHealth("http://localhost:8080/health"); err != nil {
			lastErr = fmt.Errorf("api gateway unhealthy: %w", err)
			continue
		}

		if err := checkServiceHealth("http://localhost:8081/health"); err != nil {
			lastErr = fmt.Errorf("model server unhealthy: %w", err)
			continue
		}

		// Both healthy
		return
	}

	t.Fatalf("Services did not stabilize after %v: %v", maxRetries*delay, lastErr)
}

func checkServiceHealth(url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("status code %d", resp.StatusCode)
	}

	var health map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return err
	}

	status, ok := health["status"].(string)
	if !ok || status != "healthy" {
		return fmt.Errorf("status not healthy: %v", health["status"])
	}

	return nil
}

func slurpBody(resp *http.Response) string {
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
	return fmt.Sprintf("%q", string(body))
}

func TestSignalHandling(t *testing.T) {
	// This test verifies that services can gracefully handle termination signals
	testCases := []struct {
		name       string
		port       string
		binaryPath string
	}{
		{
			name:       "api-gateway",
			port:       "8080",
			binaryPath: "cmd/api/main.go",
		},
		{
			name:       "model-server",
			port:       "8081",
			binaryPath: "cmd/model-server/main.go",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if testing.Short() {
				t.Skip("skipping signal test in short mode")
			}

			// Skip if binary doesn't exist (presumably not built)
			if _, err := os.Stat(tc.binaryPath); os.IsNotExist(err) {
				t.Skipf("%s not found, skipping", tc.binaryPath)
			}

			// Start process
			cmd := exec.Command("go", "run", tc.binaryPath)
			if err := cmd.Start(); err != nil {
				t.Skipf("failed to start %s: %v", tc.name, err)
			}

			// Wait for service to start
			time.Sleep(2 * time.Second)

			// Send interrupt signal
			if err := cmd.Process.Signal(os.Interrupt); err != nil {
				t.Errorf("failed to send interrupt: %v", err)
			}

			// Wait for graceful shutdown
			done := make(chan error, 1)
			go func() {
				done <- cmd.Wait()
			}()

			select {
			case err := <-done:
				if err != nil {
					t.Errorf("process exited with error: %v", err)
				}
			case <-time.After(10 * time.Second):
				t.Errorf("process did not terminate after receiving interrupt")
				_ = cmd.Process.Kill()
			}
		})
	}
}