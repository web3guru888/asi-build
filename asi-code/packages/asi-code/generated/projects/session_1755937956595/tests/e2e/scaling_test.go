package e2e

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"mlops-platform/internal/config"
)

const (
	gatewayAddress   = "http://localhost:8080"
	modelServerPort  = 9000
	maxWaitTime      = 30 * time.Second
	pollInterval     = 500 * time.Millisecond
	testModelName    = "test-model"
	testModelVersion = "v1"
)

var (
	testPayload = map[string]interface{}{
		"data": []float64{1.0, 2.0, 3.0},
	}
)

type PredictionRequest struct {
	ModelName    string      `json:"model_name"`
	ModelVersion string      `json:"model_version,omitempty"`
	Input        interface{} `json:"input"`
}

type PredictionResponse struct {
	Output     interface{} `json:"output"`
	ModelName  string      `json:"model_name"`
	Version    string      `json:"version"`
	StatusCode int         `json:"status_code"`
}

type ModelStatus struct {
	Name       string   `json:"name"`
	Versions   []string `json:"versions"`
	ActivePort int      `json:"active_port"`
}

type DeployModelRequest struct {
	Name       string            `json:"name"`
	Version    string            `json:"version"`
	ModelPath  string            `json:"model_path"`
	Executor   string            `json:"executor"`
	Resources  map[string]string `json:"resources,omitempty"`
	Replicas   int               `json:"replicas,omitempty"`
}

func TestModelScalingE2E(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping e2e test in short mode")
	}

	ctx, cancel := context.WithTimeout(context.Background(), maxWaitTime)
	defer cancel()

	t.Run("scaling operations across gateway and model servers", func(t *testing.T) {
		// Check if services are ready
		require.Eventually(t, func() bool {
			return isServiceReady(gatewayAddress + "/health") && isModelServerReady(fmt.Sprintf("http://localhost:%d/health", modelServerPort))
		}, maxWaitTime, pollInterval, "gateway and model server should be ready")

		modelDir := setupTestModel(t)
		defer os.RemoveAll(modelDir)

		// Deploy model with 1 replica
		t.Log("Deploying model with 1 replica...")
		err := deployModel(t, testModelName, testModelVersion, modelDir, 1)
		require.NoError(t, err)

		// Wait for model to be available
		require.Eventually(t, func() bool {
			status, err := getModelStatus(t, testModelName)
			return err == nil && len(status.Versions) > 0 && status.ActivePort > 0
		}, maxWaitTime, pollInterval)

		// Test prediction with single replica
		t.Log("Testing prediction with 1 replica...")
		resp1, err := makePrediction(testModelName, testModelVersion, testPayload)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp1.StatusCode)
		assert.NotNil(t, resp1.Output)

		// Scale to 3 replicas
		t.Log("Scaling model to 3 replicas...")
		err = scaleModel(t, testModelName, testModelVersion, 3)
		require.NoError(t, err)

		time.Sleep(3 * time.Second) // Allow time for scaling

		// Verify model status shows multiple instances (simulated)
		status, err := getModelStatus(t, testModelName)
		require.NoError(t, err)
		require.GreaterOrEqual(t, status.ActivePort, modelServerPort)

		// Run concurrent predictions to test load balancing
		t.Log("Running concurrent predictions to test load balancing...")
		var wg sync.WaitGroup
		const concurrency = 10
		var successCount int32
		var mu sync.Mutex

		for i := 0; i < concurrency; i++ {
			wg.Add(1)
			go func(id int) {
				defer wg.Done()
				resp, err := makePrediction(testModelName, testModelVersion, testPayload)
				if err == nil && resp.StatusCode == http.StatusOK {
					mu.Lock()
					successCount++
					mu.Unlock()
				}
			}(i)
		}

		wg.Wait()

		assert.Equal(t, int32(concurrency), successCount, "all concurrent requests should succeed")

		// Scale down to 1 replica
		t.Log("Scaling model down to 1 replica...")
		err = scaleModel(t, testModelName, testModelVersion, 1)
		require.NoError(t, err)

		time.Sleep(3 * time.Second) // Allow time to scale down

		// Final prediction test
		t.Log("Final prediction test after scaling down...")
		resp2, err := makePrediction(testModelName, testModelVersion, testPayload)
		require.NoError(t, err)
		assert.Equal(t, http.StatusOK, resp2.StatusCode)
		assert.NotNil(t, resp2.Output)
		assert.Equal(t, testModelName, resp2.ModelName)
	})
}

func isServiceReady(url string) bool {
	resp, err := http.Get(url)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

func isModelServerReady(url string) bool {
	resp, err := http.Get(url)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

func setupTestModel(t *testing.T) string {
	dir, err := os.MkdirTemp("", "test-model-*")
	require.NoError(t, err)

	modelContent := `{
		"name": "test-model",
		"version": "v1",
		"format": "onnx",
		"metadata": {
			"created": "%s",
			"framework": "pytorch",
			"input_shape": [null, 3],
			"output_shape": [null, 1]
		}
	}`

	now := time.Now().Format(time.RFC3339)
	err = os.WriteFile(filepath.Join(dir, "model.json"), []byte(fmt.Sprintf(modelContent, now)), 0644)
	require.NoError(t, err)

	// Create dummy binary file
	err = os.WriteFile(filepath.Join(dir, "model.onnx"), []byte("dummy-onnx-content"), 0644)
	require.NoError(t, err)

	return dir
}

func deployModel(t *testing.T, name, version, modelPath string, replicas int) error {
	reqBody := DeployModelRequest{
		Name:      name,
		Version:   version,
		ModelPath: modelPath,
		Executor:  "onnx",
		Replicas:  replicas,
		Resources: map[string]string{
			"cpu":    "500m",
			"memory": "512Mi",
		},
	}

	data, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("failed to marshal deploy request: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/models/deploy", gatewayAddress)
	resp, err := http.Post(url, "application/json", bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("failed to send deploy request: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("deploy request failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func scaleModel(t *testing.T, name, version string, replicas int) error {
	reqBody := map[string]interface{}{
		"replicas": replicas,
	}

	data, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("failed to marshal scale request: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/models/%s/%s/scale", gatewayAddress, name, version)
	req, err := http.NewRequest(http.MethodPut, url, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("failed to create scale request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send scale request: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("scale request failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func makePrediction(modelName, version string, input interface{}) (*PredictionResponse, error) {
	reqBody := PredictionRequest{
		ModelName:    modelName,
		ModelVersion: version,
		Input:        input,
	}

	data, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal prediction request: %w", err)
	}

	url := fmt.Sprintf("%s/api/v1/predict", gatewayAddress)
	resp, err := http.Post(url, "application/json", bytes.NewReader(data))
	if err != nil {
		return nil, fmt.Errorf("failed to send prediction request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read prediction response: %w", err)
	}

	var predictionResp PredictionResponse
	if err := json.Unmarshal(body, &predictionResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal prediction response: %w, body: %s", err, string(body))
	}

	predictionResp.StatusCode = resp.StatusCode
	return &predictionResp, nil
}

func getModelStatus(t *testing.T, modelName string) (*ModelStatus, error) {
	url := fmt.Sprintf("%s/api/v1/models/%s/status", gatewayAddress, modelName)
	resp, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to get model status: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get status failed with status %d: %s", resp.StatusCode, string(body))
	}

	var status ModelStatus
	if err := json.Unmarshal(body, &status); err != nil {
		return nil, fmt.Errorf("failed to unmarshal model status: %w", err)
	}

	return &status, nil
}

func TestMain(m *testing.M) {
	// Set up test configuration
	os.Setenv("GATEWAY_PORT", "8080")
	os.Setenv("MODEL_SERVER_PORT", "9000")
	os.Setenv("MODEL_STORAGE_PATH", "/tmp/models")
	os.Setenv("LOG_LEVEL", "info")

	code := m.Run()

	// Cleanup
	os.Unsetenv("GATEWAY_PORT")
	os.Unsetenv("MODEL_SERVER_PORT")
	os.Unsetenv("MODEL_STORAGE_PATH")
	os.Unsetenv("LOG_LEVEL")

	os.Exit(code)
}