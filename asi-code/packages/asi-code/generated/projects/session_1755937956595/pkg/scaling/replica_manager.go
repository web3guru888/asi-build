package scaling

import (
	"context"
	"fmt"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/deployer"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/monitoring/metrics"
)

// ReplicaManager handles the scaling and lifecycle management of model server replicas
type ReplicaManager struct {
	config       *config.Config
	deployer     *deployer.ModelDeployer
	loader       *loader.ModelLoader
	metrics      *metrics.Metrics
	logger       *logging.Logger
	replicas     map[string]*Replica // modelID -> Replica
	mu           sync.RWMutex
	stopCh       chan struct{}
	shutdownOnce sync.Once
}

// Replica represents a running model server instance
type Replica struct {
	ID          string
	ModelID     string
	Version     string
	Endpoint    string
	Ready       bool
	StartedAt   time.Time
	Process     *os.Process
	HealthCheck func() error
}

// NewReplicaManager creates a new replica manager instance
func NewReplicaManager(
	cfg *config.Config,
	deployer *deployer.ModelDeployer,
	loader *loader.ModelLoader,
	metrics *metrics.Metrics,
	logger *logging.Logger,
) *ReplicaManager {
	if logger == nil {
		logger = logging.NewLogger()
	}
	if metrics == nil {
		metrics = metrics.NewMetrics()
	}

	rm := &ReplicaManager{
		config:   cfg,
		deployer: deployer,
		loader:   loader,
		metrics:  metrics,
		logger:   logger,
		replicas: make(map[string]*Replica),
		stopCh:   make(chan struct{}),
	}

	// Start background monitoring
	go rm.monitorReplicas()

	return rm
}

// ScaleOut increases the number of replicas for a given model
func (rm *ReplicaManager) ScaleOut(ctx context.Context, modelID, version string, count int) error {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if count <= 0 {
		return fmt.Errorf("replica count must be positive")
	}

	currentCount := 0
	for _, replica := range rm.replicas {
		if replica.ModelID == modelID && replica.Version == version && replica.Ready {
			currentCount++
		}
	}

	desiredCount := count
	rm.logger.Info(fmt.Sprintf("Scaling out model %s:%s from %d to %d replicas", modelID, version, currentCount, desiredCount))

	for i := currentCount; i < desiredCount; i++ {
		replica, err := rm.startReplica(ctx, modelID, version)
		if err != nil {
			rm.logger.Error(fmt.Sprintf("Failed to start replica %d for model %s:%s: %v", i+1, modelID, version, err))
			continue
		}

		rm.replicas[replica.ID] = replica
		rm.metrics.IncReplicaCount(modelID, version)
		rm.logger.Info(fmt.Sprintf("Started replica %s for model %s:%s", replica.ID, modelID, version))
	}

	return nil
}

// ScaleIn decreases the number of replicas for a given model
func (rm *ReplicaManager) ScaleIn(ctx context.Context, modelID, version string, count int) error {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if count < 0 {
		return fmt.Errorf("replica count cannot be negative")
	}

	var replicasToRemove []*Replica
	for _, replica := range rm.replicas {
		if replica.ModelID == modelID && replica.Version == version {
			replicasToRemove = append(replicasToRemove, replica)
		}
	}

	toRemove := len(replicasToRemove) - count
	if toRemove <= 0 {
		return nil // Nothing to remove
	}

	if toRemove > len(replicasToRemove) {
		toRemove = len(replicasToRemove)
	}

	rm.logger.Info(fmt.Sprintf("Scaling in model %s:%s by removing %d replicas", modelID, version, toRemove))

	for i := 0; i < toRemove; i++ {
		replica := replicasToRemove[i]
		if err := rm.stopReplica(ctx, replica); err != nil {
			rm.logger.Error(fmt.Sprintf("Error stopping replica %s: %v", replica.ID, err))
			continue
		}

		delete(rm.replicas, replica.ID)
		rm.metrics.DecReplicaCount(modelID, version)
		rm.logger.Info(fmt.Sprintf("Removed replica %s for model %s:%s", replica.ID, modelID, version))
	}

	return nil
}

// GetReplicaStats returns current replica statistics
func (rm *ReplicaManager) GetReplicaStats(ctx context.Context) map[string]int {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	stats := make(map[string]int)
	for _, replica := range rm.replicas {
		key := fmt.Sprintf("%s:%s", replica.ModelID, replica.Version)
		stats[key]++
	}
	return stats
}

// ListReplicas returns all active replicas
func (rm *ReplicaManager) ListReplicas(ctx context.Context) []*Replica {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	replicas := make([]*Replica, 0, len(rm.replicas))
	for _, replica := range rm.replicas {
		replicas = append(replicas, replica)
	}
	return replicas
}

// Shutdown gracefully stops all replicas and cleans up resources
func (rm *ReplicaManager) Shutdown(ctx context.Context) error {
	var err error
	rm.shutdownOnce.Do(func() {
		close(rm.stopCh)
		rm.logger.Info("Shutting down replica manager")

		rm.mu.Lock()
		defer rm.mu.Unlock()

		for id, replica := range rm.replicas {
			if e := rm.stopReplica(ctx, replica); e != nil {
				rm.logger.Error(fmt.Sprintf("Error stopping replica %s: %v", id, e))
				if err == nil {
					err = e
				}
			}
			delete(rm.replicas, id)
			rm.metrics.DecReplicaCount(replica.ModelID, replica.Version)
		}
	})
	return err
}

// startReplica launches a new model server process
func (rm *ReplicaManager) startReplica(ctx context.Context, modelID, version string) (*Replica, error) {
	// Deploy model to local filesystem
	modelPath, err := rm.deployer.DeployModel(ctx, modelID, version)
	if err != nil {
		return nil, fmt.Errorf("failed to deploy model: %w", err)
	}

	// Generate unique replica ID
	replicaID := fmt.Sprintf("%s-%s-%d", modelID, version, time.Now().UnixNano())

	// Start model server process
	cmd := exec.CommandContext(ctx,
		"mlops-model-server",
		"--model-path", modelPath,
		"--model-id", modelID,
		"--version", version,
		"--replica-id", replicaID,
		"--port", fmt.Sprintf("%d", 8080+len(rm.replicas)),
	)

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start model server process: %w", err)
	}

	replica := &Replica{
		ID:        replicaID,
		ModelID:   modelID,
		Version:   version,
		Endpoint:  fmt.Sprintf("http://localhost:%d", 8080+len(rm.replicas)),
		StartedAt: time.Now(),
		Process:   cmd.Process,
		HealthCheck: func() error {
			client := &http.Client{Timeout: 5 * time.Second}
			resp, err := client.Get(fmt.Sprintf("%s/health", replica.Endpoint))
			if err != nil {
				return err
			}
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusOK {
				return fmt.Errorf("health check failed with status: %s", resp.Status)
			}
			return nil
		},
	}

	// Monitor process completion
	go func() {
		_ = cmd.Wait()
		rm.mu.Lock()
		if _, exists := rm.replicas[replicaID]; exists {
			delete(rm.replicas, replicaID)
			rm.metrics.DecReplicaCount(modelID, version)
			rm.logger.Warn(fmt.Sprintf("Replica %s exited unexpectedly", replicaID))
		}
		rm.mu.Unlock()
	}()

	// Wait for server readiness
	if err := rm.waitForReplicaReady(ctx, replica); err != nil {
		_ = cmd.Process.Kill()
		return nil, fmt.Errorf("replica failed to become ready: %w", err)
	}

	replica.Ready = true
	return replica, nil
}

// stopReplica stops a running replica
func (rm *ReplicaManager) stopReplica(ctx context.Context, replica *Replica) error {
	if replica.Process == nil {
		return nil
	}

	// Try graceful shutdown first
	if err := replica.Process.Signal(syscall.SIGTERM); err != nil {
		rm.logger.Warn(fmt.Sprintf("Failed to send SIGTERM to replica %s: %v", replica.ID, err))
	}

	// Wait for process to exit gracefully
	waitDone := make(chan error, 1)
	go func() {
		waitDone <- replica.Process.Wait()
	}()

	select {
	case <-ctx.Done():
		rm.logger.Warn(fmt.Sprintf("Context canceled while waiting for replica %s to stop", replica.ID))
		return ctx.Err()
	case err := <-waitDone:
		if err != nil {
			rm.logger.Info(fmt.Sprintf("Replica %s stopped with error: %v", replica.ID, err))
		} else {
			rm.logger.Info(fmt.Sprintf("Replica %s stopped successfully", replica.ID))
		}
		return nil
	case <-time.After(30 * time.Second):
		rm.logger.Warn(fmt.Sprintf("Replica %s did not stop gracefully, forcing kill", replica.ID))
		if killErr := replica.Process.Kill(); killErr != nil {
			return fmt.Errorf("failed to kill process: %w", killErr)
		}
		<-waitDone // Wait for the process to be reaped
		return nil
	}
}

// waitForReplicaReady waits for the replica to become ready
func (rm *ReplicaManager) waitForReplicaReady(ctx context.Context, replica *Replica) error {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	timeout := time.After(60 * time.Second)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-timeout:
			return fmt.Errorf("timeout waiting for replica %s to become ready", replica.ID)
		case <-ticker.C:
			if err := replica.HealthCheck(); err == nil {
				return nil
			}
			// Continue polling
		}
	}
}

// monitorReplicas runs periodic health checks on all replicas
func (rm *ReplicaManager) monitorReplicas() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-rm.stopCh:
			return
		case <-ticker.C:
			rm.checkAllReplicas()
		}
	}
}

// checkAllReplicas performs health checks on all running replicas
func (rm *ReplicaManager) checkAllReplicas() {
	rm.mu.RLock()
	replicas := make([]*Replica, 0, len(rm.replicas))
	for _, r := range rm.replicas {
		replicas = append(replicas, r)
	}
	rm.mu.RUnlock()

	for _, replica := range replicas {
		if err := replica.HealthCheck(); err != nil {
			rm.logger.Error(fmt.Sprintf("Replica %s health check failed: %v", replica.ID, err))
			rm.handleReplicaFailure(replica)
		}
	}
}

// handleReplicaFailure handles failed replicas by restarting them
func (rm *ReplicaManager) handleReplicaFailure(failed *Replica) {
	go func() {
		rm.mu.Lock()
		defer rm.mu.Unlock()

		// Only attempt restart if replica still exists
		if _, exists := rm.replicas[failed.ID]; !exists {
			return
		}

		rm.logger.Info(fmt.Sprintf("Attempting to restart failed replica %s", failed.ID))

		// Stop the failed process
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		if err := rm.stopReplica(ctx, failed); err != nil {
			rm.logger.Error(fmt.Sprintf("Error stopping failed replica %s: %v", failed.ID, err))
		}
		cancel()

		delete(rm.replicas, failed.ID)
		rm.metrics.DecReplicaCount(failed.ModelID, failed.Version)

		// Start a replacement
		newReplica, err := rm.startReplica(context.Background(), failed.ModelID, failed.Version)
		if err != nil {
			rm.logger.Error(fmt.Sprintf("Failed to restart replica for model %s:%s: %v", failed.ModelID, failed.Version, err))
			return
		}

		rm.replicas[newReplica.ID] = newReplica
		rm.metrics.IncReplicaCount(failed.ModelID, failed.Version)
		rm.logger.Info(fmt.Sprintf("Successfully restarted replica for model %s:%s as %s", failed.ModelID, failed.Version, newReplica.ID))
	}()
}