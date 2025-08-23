package scaling

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/deployer"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/monitoring/metrics"
)

// Autoscaler manages dynamic scaling of model server instances
// based on incoming traffic and resource utilization.
type Autoscaler struct {
	cfg        *config.Config
	deployer   *deployer.Deployer
	loader     *loader.ModelLoader
	metrics    *metrics.Metrics
	logger     logging.Logger
	stopCh     chan struct{}
	wg         sync.WaitGroup
	scalingMu  sync.RWMutex
	replicas   int
	maxReplicas int
	minReplicas int
	cpuThreshold float64 // percentage threshold for scaling
	checkInterval time.Duration
}

// NewAutoscaler creates and initializes a new Autoscaler instance.
func NewAutoscaler(
	cfg *config.Config,
	deployer *deployer.Deployer,
	loader *loader.ModelLoader,
	metrics *metrics.Metrics,
	logger logging.Logger,
) *Autoscaler {
	return &Autoscaler{
		cfg:           cfg,
		deployer:      deployer,
		loader:        loader,
		metrics:       metrics,
		logger:        logger.With("component", "autoscaler"),
		stopCh:        make(chan struct{}),
		replicas:      cfg.ModelServer.Replicas,
		minReplicas:   cfg.ModelServer.MinReplicas,
		maxReplicas:   cfg.ModelServer.MaxReplicas,
		cpuThreshold:  cfg.Autoscaler.CPUThreshold,
		checkInterval: time.Duration(cfg.Autoscaler.CheckIntervalSeconds) * time.Second,
	}
}

// Start begins the autoscaling loop in a separate goroutine.
func (a *Autoscaler) Start(ctx context.Context) error {
	a.logger.Info("starting autoscaler", "min_replicas", a.minReplicas, "max_replicas", a.maxReplicas)

	// Register scaling metrics
	a.metrics.RegisterGauge("model_server_replicas", "Current number of model server replicas")
	a.metrics.SetGauge("model_server_replicas", float64(a.replicas))

	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		ticker := time.NewTicker(a.checkInterval)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				if err := a.reconcileScaling(ctx); err != nil {
					a.logger.Error("error during scaling reconciliation", "error", err)
				}
			case <-a.stopCh:
				a.logger.Info("autoscaler shutdown initiated")
				return
			}
		}
	}()

	return nil
}

// Stop gracefully shuts down the autoscaler.
func (a *Autoscaler) Stop() {
	a.logger.Info("stopping autoscaler")
	close(a.stopCh)
	a.wg.Wait()
}

// GetReplicas returns the current number of replicas.
func (a *Autoscaler) GetReplicas() int {
	a.scalingMu.RLock()
	defer a.scalingMu.RUnlock()
	return a.replicas
}

// ScaleUp increases the number of replicas by one, up to MaxReplicas.
func (a *Autoscaler) ScaleUp(ctx context.Context) error {
	a.scalingMu.Lock()
	defer a.scalingMu.Unlock()

	if a.replicas >= a.maxReplicas {
		a.logger.Debug("max replicas reached, cannot scale up", "current", a.replicas, "max", a.maxReplicas)
		return nil
	}

	newReplicaID := fmt.Sprintf("model-server-%d", time.Now().UnixNano())
	a.logger.Info("scaling up model server", "replica_id", newReplicaID, "from", a.replicas, "to", a.replicas+1)

	if err := a.deployer.DeployModel(ctx, newReplicaID); err != nil {
		a.metrics.IncCounter("autoscaler_scale_up_failure", 1)
		return fmt.Errorf("failed to deploy new model replica %s: %w", newReplicaID, err)
	}

	a.replicas++
	a.metrics.SetGauge("model_server_replicas", float64(a.replicas))
	a.metrics.IncCounter("autoscaler_scale_up", 1)

	return nil
}

// ScaleDown reduces the number of replicas by one, down to MinReplicas.
func (a *Autoscaler) ScaleDown(ctx context.Context) error {
	a.scalingMu.Lock()
	defer a.scalingMu.Unlock()

	if a.replicas <= a.minReplicas {
		a.logger.Debug("min replicas reached, cannot scale down", "current", a.replicas, "min", a.minReplicas)
		return nil
	}

	replicaID := fmt.Sprintf("model-server-%d", time.Now().UnixNano()) // In real use, pick least active
	a.logger.Info("scaling down model server", "replica_id", replicaID, "from", a.replicas, "to", a.replicas-1)

	if err := a.loader.UnloadModel(ctx, replicaID); err != nil {
		a.metrics.IncCounter("autoscaler_scale_down_failure", 1)
		return fmt.Errorf("failed to unload model replica %s: %w", replicaID, err)
	}

	a.replicas--
	a.metrics.SetGauge("model_server_replicas", float64(a.replicas))
	a.metrics.IncCounter("autoscaler_scale_down", 1)

	return nil
}

// reconcileScaling evaluates current load and decides whether to scale.
func (a *Autoscaler) reconcileScaling(ctx context.Context) error {
	load, err := a.getCurrentCPULoad()
	if err != nil {
		return fmt.Errorf("unable to get current CPU load: %w", err)
	}

	a.metrics.SetGauge("autoscaler_cpu_load", load)

	// Simple horizontal scaling logic based on CPU usage
	if load > a.cpuThreshold && a.GetReplicas() < a.maxReplicas {
		return a.ScaleUp(ctx)
	}

	if load < (a.cpuThreshold * 0.7) && a.GetReplicas() > a.minReplicas {
		return a.ScaleDown(ctx)
	}

	return nil
}

// getCurrentCPULoad simulates fetching current CPU utilization.
// In a production system, this would integrate with Prometheus, cAdvisor, or similar.
// For now, we simulate based on request count or stub external metrics.
func (a *Autoscaler) getCurrentCPULoad() (float64, error) {
	// Simulate metric pull – in real world, query Prometheus or use /metrics endpoint
	// Example: query `rate(container_cpu_usage_seconds_total[1m])`
	// As placeholder, return a mock value derived from observed traffic
	value, exists := a.metrics.GetGauge("http_requests_total")
	if !exists {
		return 30.0, nil // default baseline
	}

	// Normalize mock load: assume 1000 req/min ≈ 50%, 2000 req/min ≈ 100%
	mockLoad := (value / 2000.0) * 100.0
	if mockLoad > 100.0 {
		mockLoad = 100.0
	}
	if mockLoad < 0 {
		mockLoad = 0
	}

	return mockLoad, nil
}

// Status returns the current autoscaler state for health or monitoring purposes.
func (a *Autoscaler) Status() map[string]interface{} {
	a.scalingMu.RLock()
	defer a.scalingMu.RUnlock()

	return map[string]interface{}{
		"replicas":        a.replicas,
		"min_replicas":    a.minReplicas,
		"max_replicas":    a.maxReplicas,
		"cpu_threshold":   a.cpuThreshold,
		"interval_seconds": a.checkInterval.Seconds(),
		"status":          "running",
	}
}

// HTTPHandler returns an HTTP handler for autoscaler metrics/status.
func (a *Autoscaler) HTTPHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		status := a.Status()
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(status); err != nil {
			http.Error(w, "failed to encode status", http.StatusInternalServerError)
			return
		}
	}
}