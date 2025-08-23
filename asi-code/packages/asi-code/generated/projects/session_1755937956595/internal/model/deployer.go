package model

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/model/registry/client"
	"mlops-platform/internal/model/versioning"
	"mlops-platform/internal/monitoring/metrics"
	"mlops-platform/internal/monitoring/tracing"

	"go.opentelemetry.io/otel"
	"go.uber.org/zap"
)

// Deployer handles the deployment lifecycle of machine learning models
type Deployer struct {
	cfg          *config.Config
	logger       *zap.Logger
	loader       *loader.Loader
	registry     *client.RegistryClient
	versioner    *versioning.Versioner
	metrics      *metrics.Metrics
	tracer       tracing.Tracer
	deployments  map[string]*DeploymentStatus // modelID -> status
	deploymentDir string
}

// DeploymentStatus represents the current state of a deployed model
type DeploymentStatus struct {
	ModelID     string    `json:"model_id"`
	Version     string    `json:"version"`
	Status      string    `json:"status"` // "pending", "deploying", "running", "failed", "stopped"
	Endpoint    string    `json:"endpoint,omitempty"`
	Ports       []int     `json:"ports"`
	ProcessPID  int       `json:"process_pid,omitempty"`
	StartedAt   time.Time `json:"started_at"`
	StoppedAt   *time.Time `json:"stopped_at,omitempty"`
	Error       string    `json:"error,omitempty"`
	Labels      map[string]string `json:"labels,omitempty"`
}

// NewDeployer creates a new model deployer
func NewDeployer(
	cfg *config.Config,
	logger *logging.Logger,
	loader *loader.Loader,
	registry *client.RegistryClient,
	versioner *versioning.Versioner,
	metrics *metrics.Metrics,
) *Deployer {
	return &Deployer{
		cfg:           cfg,
		logger:        logger,
		loader:        loader,
		registry:      registry,
		versioner:     versioner,
		metrics:       metrics,
		tracer:        otel.Tracer("model-deployer"),
		deployments:   make(map[string]*DeploymentStatus),
		deploymentDir: filepath.Join(cfg.ModelStoragePath, "deployments"),
	}
}

// DeployModel pulls the model from registry and starts serving it
func (d *Deployer) DeployModel(ctx context.Context, modelID, version string, labels map[string]string) (*DeploymentStatus, error) {
	ctx, span := d.tracer.Start(ctx, "Deployer.DeployModel")
	defer span.End()

	log := d.logger.With(zap.String("model_id", modelID), zap.String("version", version))

	// Validate model ID
	if !isValidModelID(modelID) {
		err := fmt.Errorf("invalid model ID format: %s", modelID)
		span.RecordError(err)
		return nil, err
	}

	// Register metrics
	d.metrics.IncrementDeploymentAttempts(modelID, version)

	// Create deployment directory if it doesn't exist
	if err := os.MkdirAll(d.deploymentDir, 0755); err != nil {
		d.logger.Error("failed to create deployment directory", zap.Error(err), zap.String("path", d.deploymentDir))
		return nil, fmt.Errorf("failed to create deployment directory: %w", err)
	}

	// Download model from registry
	modelPath, err := d.downloadModel(ctx, modelID, version)
	if err != nil {
		d.logger.Error("failed to download model", zap.Error(err))
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to download model: %w", err)
	}

	// Load model metadata and validate
	modelMeta, err := d.loader.LoadModelMetadata(modelPath)
	if err != nil {
		d.logger.Error("failed to load model metadata", zap.Error(err))
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to load model metadata: %w", err)
	}

	// Find available port for model server
	port, err := d.findAvailablePort()
	if err != nil {
		err = fmt.Errorf("no available ports for model deployment")
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, err
	}

	deployDir := filepath.Join(d.deploymentDir, fmt.Sprintf("%s_%s", modelID, version))
	if err := os.MkdirAll(deployDir, 0755); err != nil {
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to create deployment instance directory: %w", err)
	}

	// Prepare environment variables for model server
	env := []string{
		fmt.Sprintf("MODEL_PATH=%s", modelPath),
		fmt.Sprintf("MODEL_NAME=%s", modelMeta.Name),
		fmt.Sprintf("MODEL_VERSION=%s", version),
		fmt.Sprintf("PORT=%d", port),
		fmt.Sprintf("LOG_LEVEL=%s", d.cfg.LogLevel),
	}

	// Start model server process
	cmd := exec.CommandContext(ctx, "model-server", "--model-dir", modelPath, "--port", fmt.Sprintf("%d", port))
	cmd.Dir = deployDir
	cmd.Env = append(os.Environ(), env...)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to create stderr pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("failed to start model server process: %w", err)
	}

	// Stream logs asynchronously
	go d.streamProcessLogs(modelID, version, stdout, stderr)

	// Wait for server to become ready
	endpoint := fmt.Sprintf("http://localhost:%d/health", port)
	if err := d.waitForServerReady(ctx, endpoint, 30*time.Second); err != nil {
		cmd.Process.Kill()
		d.metrics.IncrementDeploymentFailures(modelID, version)
		span.RecordError(err)
		return nil, fmt.Errorf("model server failed to become ready: %w", err)
	}

	// Create deployment status
	deployment := &DeploymentStatus{
		ModelID:    modelID,
		Version:    version,
		Status:     "running",
		Endpoint:   fmt.Sprintf("http://localhost:%d", port),
		Ports:      []int{port},
		ProcessPID: cmd.Process.Pid,
		StartedAt:  time.Now(),
		Labels:     labels,
	}

	// Store deployment
	d.deployments[modelID] = deployment

	// Update metrics
	d.metrics.IncrementActiveDeployments(modelID, version)
	d.metrics.RecordDeploymentDuration(modelID, version, time.Since(span.SpanContext().SpanID().Timestamp()))

	log.Info("model deployed successfully", zap.Int("pid", cmd.Process.Pid), zap.String("endpoint", deployment.Endpoint))

	return deployment, nil
}

// UndeployModel stops a running model deployment
func (d *Deployer) UndeployModel(ctx context.Context, modelID string) error {
	ctx, span := d.tracer.Start(ctx, "Deployer.UndeployModel")
	defer span.End()

	deployment, exists := d.deployments[modelID]
	if !exists {
		err := fmt.Errorf("no active deployment found for model: %s", modelID)
		span.RecordError(err)
		return err
	}

	log := d.logger.With(zap.String("model_id", modelID))

	// Kill the process
	if err := d.killProcess(deployment.ProcessPID); err != nil {
		d.logger.Warn("failed to kill model server process", zap.Int("pid", deployment.ProcessPID), zap.Error(err))
		// Continue despite error - process might have already terminated
	}

	// Update deployment status
	stoppedAt := time.Now()
	deployment.Status = "stopped"
	deployment.StoppedAt = &stoppedAt

	delete(d.deployments, modelID)

	d.metrics.DecrementActiveDeployments(modelID, deployment.Version)

	log.Info("model undeployed successfully", zap.Int("pid", deployment.ProcessPID))

	return nil
}

// GetDeploymentStatus returns the current status of a model deployment
func (d *Deployer) GetDeploymentStatus(modelID string) (*DeploymentStatus, bool) {
	status, exists := d.deployments[modelID]
	return status, exists
}

// ListDeployments returns all current deployments
func (d *Deployer) ListDeployments() []*DeploymentStatus {
	deployments := make([]*DeploymentStatus, 0, len(d.deployments))
	for _, status := range d.deployments {
		deployments = append(deployments, status)
	}
	return deployments
}

// downloadModel fetches model from registry
func (d *Deployer) downloadModel(ctx context.Context, modelID, version string) (string, error) {
	ctx, span := d.tracer.Start(ctx, "Deployer.downloadModel")
	defer span.End()

	modelDir := filepath.Join(d.cfg.ModelStoragePath, "models", modelID, version)
	if err := os.MkdirAll(modelDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create model directory: %w", err)
	}

	modelPath, err := d.registry.DownloadModel(ctx, modelID, version, modelDir)
	if err != nil {
		return "", fmt.Errorf("failed to download model from registry: %w", err)
	}

	return modelPath, nil
}

// findAvailablePort finds an available port for model deployment
func (d *Deployer) findAvailablePort() (int, error) {
	startPort := d.cfg.ModelServerStartPort
	maxAttempts := d.cfg.ModelServerPortRangeSize

	for attempt := 0; attempt < maxAttempts; attempt++ {
		port := startPort + attempt

		// Check if port is available
		conn, err := net.DialTimeout("tcp", fmt.Sprintf(":%d", port), 50*time.Millisecond)
		if err != nil {
			// Port is likely available
			return port, nil
		}
		conn.Close()
	}

	return 0, fmt.Errorf("no available ports in range %d-%d", startPort, startPort+maxAttempts-1)
}

// waitForServerReady checks if the model server is ready to serve
func (d *Deployer) waitForServerReady(ctx context.Context, endpoint string, timeout time.Duration) error {
	ctx, span := d.tracer.Start(ctx, "Deployer.waitForServerReady")
	defer span.End()

	client := &http.Client{Timeout: 10 * time.Second}
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	timeoutCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	for {
		select {
		case <-timeoutCtx.Done():
			return fmt.Errorf("timed out waiting for server readiness: %w", timeoutCtx.Err())
		case <-ticker.C:
			req, _ := http.NewRequestWithContext(timeoutCtx, "GET", endpoint, nil)
			resp, err := client.Do(req)
			if err == nil && resp.StatusCode == http.StatusOK {
				resp.Body.Close()
				return nil
			}
			if resp != nil {
				resp.Body.Close()
			}
		}
	}
}

// streamProcessLogs pipes process output to application logs
func (d *Deployer) streamProcessLogs(modelID, version string, stdout, stderr io.ReadCloser) {
	log := d.logger.With(zap.String("model_id", modelID), zap.String("version", version))

	go func() {
		scanner := bufio.NewScanner(stdout)
		for scanner.Scan() {
			log.Info("model server stdout", zap.String("output", scanner.Text()))
		}
	}()

	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			log.Error("model server stderr", zap.String("error", scanner.Text()))
		}
	}()
}

// killProcess terminates a process by PID
func (d *Deployer) killProcess(pid int) error {
	process, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("failed to find process: %w", err)
	}

	if err := process.Signal(syscall.SIGTERM); err != nil {
		return fmt.Errorf("failed to send SIGTERM: %w", err)
	}

	// Wait for graceful shutdown
	select {
	case <-time.After(10 * time.Second):
		// Force kill if process doesn't terminate gracefully
		if err := process.Kill(); err != nil {
			return fmt.Errorf("failed to force kill process: %w", err)
		}
		d.logger.Warn("process killed forcefully after timeout", zap.Int("pid", pid))
	case <-d.waitForProcessExit(process, 10*time.Second):
		// Process exited gracefully
		return nil
	}

	return nil
}

// waitForProcessExit waits for a process to exit
func (d *Deployer) waitForProcessExit(process *os.Process, timeout time.Duration) chan bool {
	done := make(chan bool, 1)
	go func() {
		defer close(done)
		_, err := process.Wait()
		if err != nil {
			d.logger.Debug("process wait error", zap.Error(err))
		}
		done <- true
	}()

	timer := time.NewTimer(timeout)
	defer timer.Stop()

	select {
	case <-done:
		return done
	case <-timer.C:
		// Timeout, process may still be running
		select {
		case <-done:
			return done
		default:
			close(done)
			return done
		}
	}
}

// isValidModelID validates model ID format
func isValidModelID(id string) bool {
	if id == "" {
		return false
	}
	
	// Allow lowercase alphanumeric, hyphens, underscores, periods
	validChars := "abcdefghijklmnopqrstuvwxyz0123456789-_."
	for _, char := range id {
		if !strings.ContainsRune(validChars, char) {
			return false
		}
	}
	return true
}

// GetActiveDeploymentsCount returns the number of currently active deployments
func (d *Deployer) GetActiveDeploymentsCount() int {
	return len(d.deployments)
}

// HealthCheck performs a health check on the deployer system
func (d *Deployer) HealthCheck(ctx context.Context) error {
	// Check if deployment directory is writable
	if err := d.canWriteToDeploymentDir(); err != nil {
		return fmt.Errorf("deployment directory check failed: %w", err)
	}

	// Check if we can execute model server binary
	if err := d.canExecuteModelServer(); err != nil {
		return fmt.Errorf("model server binary check failed: %w", err)
	}

	return nil
}

// canWriteToDeploymentDir checks if deployment directory is writable
func (d *Deployer) canWriteToDeploymentDir() error {
	testFile := filepath.Join(d.deploymentDir, ".healthcheck")
	if err := os.WriteFile(testFile, []byte("healthcheck"), 0644); err != nil {
		return err
	}
	return os.Remove(testFile)
}

// canExecuteModelServer checks if model-server binary is available
func (d *Deployer) canExecuteModelServer() error {
	path, err := exec.LookPath("model-server")
	if err != nil {
		return fmt.Errorf("model-server binary not found in PATH: %w", err)
	}

	// Test execute with --help (non-destructive)
	cmd := exec.Command(path, "--help")
	return cmd.Run()
}