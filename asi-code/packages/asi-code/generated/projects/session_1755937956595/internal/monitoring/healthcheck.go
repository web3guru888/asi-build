package monitoring

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"runtime"
	"sort"
	"sync"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// HealthStatus represents the overall health status of the service
type HealthStatus string

// Health check result constants
const (
	HealthStatusPassing HealthStatus = "passing"
	HealthStatusWarning HealthStatus = "warning"
	HealthStatusCritical HealthStatus = "critical"
)

// HealthCheckResult represents the result of a single health check
type HealthCheckResult struct {
	Name      string        `json:"name"`
	Status    HealthStatus  `json:"status"`
	Took      time.Duration `json:"took"`
	LastError string        `json:"lastError,omitempty"`
	Details   interface{}   `json:"details,omitempty"`
}

// HealthCheckFunc defines the signature for a health check function
type HealthCheckFunc func(ctx context.Context) *HealthCheckResult

// HealthChecker manages health checks for the application
type HealthChecker struct {
	checks     map[string]HealthCheckFunc
	logger     *logging.Logger
	timeout    time.Duration
	interval   time.Duration
	results    map[string]*HealthCheckResult
	resultsMux sync.RWMutex
}

// HealthCheckResponse represents the response for health check endpoint
type HealthCheckResponse struct {
	Status   HealthStatus           `json:"status"`
	Version  string                 `json:"version"`
	Host     string                 `json:"host"`
	Took     time.Duration          `json:"took"`
	Checks   []*HealthCheckResult   `json:"checks"`
	Count    int                    `json:"count"`
	Passing  int                    `json:"passing"`
	Critical int                    `json:"critical"`
	Warning  int                    `json:"warning"`
}

// NewHealthChecker creates a new health checker instance
func NewHealthChecker(cfg *config.Config, logger *logging.Logger) *HealthChecker {
	if logger == nil {
		logger = logging.New()
	}

	healthChecker := &HealthChecker{
		checks:  make(map[string]HealthCheckFunc),
		logger:  logger,
		timeout: time.Duration(cfg.HealthCheckTimeoutSeconds) * time.Second,
		interval: time.Duration(cfg.HealthCheckIntervalSeconds) * time.Second,
		results: make(map[string]*HealthCheckResult),
	}

	// Register built-in health checks
	healthChecker.RegisterCheck("self", healthChecker.checkSelf)
	healthChecker.RegisterCheck("goroutines", healthChecker.checkGoroutines)
	healthChecker.RegisterCheck("memory", healthChecker.checkMemory)
	healthChecker.RegisterCheck("disk", healthChecker.checkDisk)

	return healthChecker
}

// RegisterCheck registers a new health check with the given name and function
func (h *HealthChecker) RegisterCheck(name string, check HealthCheckFunc) {
	h.checks[name] = check
	h.logger.Info("registered health check", "name", name)
}

// checkSelf performs a basic self-check
func (h *HealthChecker) checkSelf(ctx context.Context) *HealthCheckResult {
	start := time.Now()

	result := &HealthCheckResult{
		Name:   "self",
		Status: HealthStatusPassing,
		Took:   time.Since(start),
		Details: map[string]string{
			"message": "Service is running",
		},
	}

	return result
}

// checkGoroutines checks the number of active goroutines
func (h *HealthChecker) checkGoroutines(ctx context.Context) *HealthCheckResult {
	start := time.Now()

	numGoroutines := runtime.NumGoroutine()
	status := HealthStatusPassing

	// Warning if more than 1000 goroutines, critical if more than 5000
	if numGoroutines > 5000 {
		status = HealthStatusCritical
	} else if numGoroutines > 1000 {
		status = HealthStatusWarning
	}

	result := &HealthCheckResult{
		Name:   "goroutines",
		Status: status,
		Took:   time.Since(start),
		Details: map[string]interface{}{
			"count": numGoroutines,
		},
	}

	return result
}

// checkMemory checks memory usage
func (h *HealthChecker) checkMemory(ctx context.Context) *HealthCheckResult {
	start := time.Now()

	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	status := HealthStatusPassing
	var lastError string

	// Check if memory usage is too high (arbitrary thresholds)
	if memStats.Alloc > 512*1024*1024 { // 512MB
		status = HealthStatusWarning
	}
	if memStats.Alloc > 1024*1024*1024 { // 1GB
		status = HealthStatusCritical
		lastError = "memory usage exceeds 1GB threshold"
	}

	result := &HealthCheckResult{
		Name:      "memory",
		Status:    status,
		Took:      time.Since(start),
		LastError: lastError,
		Details: map[string]interface{}{
			"alloc":           memStats.Alloc,
			"total_alloc":     memStats.TotalAlloc,
			"sys":             memStats.Sys,
			"num_gc":          memStats.NumGC,
			"pause_total_ns":  memStats.PauseTotalNs,
			"heap_objects":    memStats.HeapObjects,
			"heap_idle":       memStats.HeapIdle,
			"heap_inuse":      memStats.HeapInuse,
			"heap_released":   memStats.HeapReleased,
			"heap_sys":        memStats.HeapSys,
			"stack_inuse":     memStats.StackInuse,
			"stack_sys":       memStats.StackSys,
			"mspan_inuse":     memStats.MSpanInuse,
			"mspan_sys":       memStats.MSpanSys,
			"mcache_inuse":    memStats.MCacheInuse,
			"mcache_sys":      memStats.MCacheSys,
			"buck_hash_sys":   memStats.BuckHashSys,
			"gc_sys":          memStats.GCSys,
			"other_sys":       memStats.OtherSys,
			"next_gc":         memStats.NextGC,
			"last_gc":         time.Unix(0, int64(memStats.LastGC)).Format(time.RFC3339),
		},
	}

	return result
}

// checkDisk checks disk space availability
func (h *HealthChecker) checkDisk(ctx context.Context) *HealthCheckResult {
	start := time.Now()

	var stat syscall.Statfs_t
	path := "/"
	err := syscall.Statfs(path, &stat)
	if err != nil {
		return &HealthCheckResult{
			Name:      "disk",
			Status:    HealthStatusCritical,
			Took:      time.Since(start),
			LastError: fmt.Sprintf("failed to get disk stats: %v", err),
			Details: map[string]interface{}{
				"path": path,
			},
		}
	}

	// Calculate available and total space in bytes
	available := stat.Bavail * uint64(stat.Bsize)
	total := stat.Blocks * uint64(stat.Bsize)
	used := total - available
	usedPercent := float64(used) / float64(total) * 100

	status := HealthStatusPassing
	if usedPercent > 90 {
		status = HealthStatusCritical
	} else if usedPercent > 80 {
		status = HealthStatusWarning
	}

	result := &HealthCheckResult{
		Name:   "disk",
		Status: status,
		Took:   time.Since(start),
		Details: map[string]interface{}{
			"path":          path,
			"available":     available,
			"total":         total,
			"used":          used,
			"used_percent":  fmt.Sprintf("%.2f", usedPercent),
			"free_blocks":   stat.Bfree,
			"available":     stat.Bavail,
			"block_size":    stat.Bsize,
			"blocks":        stat.Blocks,
			"fragments":     stat.Bfree - stat.Bavail,
			"fragment_size": stat.Bsize,
		},
	}

	return result
}

// Run executes all registered health checks concurrently
func (h *HealthChecker) Run(ctx context.Context) *HealthCheckResponse {
	start := time.Now()

	// Create a context with timeout for health checks
	checkCtx, cancel := context.WithTimeout(ctx, h.timeout)
	defer cancel()

	// Channel to collect results
	results := make(chan *HealthCheckResult, len(h.checks))

	// Execute each check in a separate goroutine
	var wg sync.WaitGroup
	for name, check := range h.checks {
		wg.Add(1)
		go func(name string, check HealthCheckFunc) {
			defer wg.Done()
			result := check(checkCtx)
			results <- result
		}(name, check)
	}

	// Close results channel when all checks are done
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect all results
	var healthResults []*HealthCheckResult
	for result := range results {
		healthResults = append(healthResults, result)
	}

	// Sort results by name for consistent output
	sort.Slice(healthResults, func(i, j int) bool {
		return healthResults[i].Name < healthResults[j].Name
	})

	// Calculate overall status
	status := HealthStatusPassing
	passing, warning, critical := 0, 0, 0
	for _, result := range healthResults {
		h.resultsMux.Lock()
		h.results[result.Name] = result
		h.resultsMux.Unlock()

		switch result.Status {
		case HealthStatusCritical:
			critical++
		case HealthStatusWarning:
			warning++
		case HealthStatusPassing:
			passing++
		}

		if result.Status == HealthStatusCritical {
			status = HealthStatusCritical
		} else if result.Status == HealthStatusWarning && status != HealthStatusCritical {
			status = HealthStatusWarning
		}
	}

	// Get hostname
	hostname, _ := os.Hostname()

	response := &HealthCheckResponse{
		Status:   status,
		Version:  config.Version,
		Host:     hostname,
		Took:     time.Since(start),
		Checks:   healthResults,
		Count:    len(healthResults),
		Passing:  passing,
		Critical: critical,
		Warning:  warning,
	}

	return response
}

// ServeHTTP handles health check requests
func (h *HealthChecker) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	// Support query parameters for detailed response
	detailed := r.URL.Query().Get("detailed") != "false"

	response := h.Run(ctx)

	// Set appropriate status code based on health
	statusCode := http.StatusOK
	if response.Status == HealthStatusCritical {
		statusCode = http.StatusServiceUnavailable
	} else if response.Status == HealthStatusWarning {
		statusCode = http.StatusTooManyRequests
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	if detailed {
		// Full detailed response
		if err := json.NewEncoder(w).Encode(response); err != nil {
			h.logger.Error("failed to encode health check response", "error", err)
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		}
	} else {
		// Minimal response
		minimal := map[string]interface{}{
			"status":  response.Status,
			"version": response.Version,
			"host":    response.Host,
			"took":    response.Took,
		}

		if err := json.NewEncoder(w).Encode(minimal); err != nil {
			h.logger.Error("failed to encode minimal health check response", "error", err)
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
		}
	}
}

// GetLastResults returns the results of the last health check execution
func (h *HealthChecker) GetLastResults() map[string]*HealthCheckResult {
	h.resultsMux.RLock()
	defer h.resultsMux.RUnlock()

	results := make(map[string]*HealthCheckResult)
	for k, v := range h.results {
		results[k] = v
	}

	return results
}

// StartPeriodicCheck runs health checks periodically in the background
func (h *HealthChecker) StartPeriodicCheck(ctx context.Context) {
	if h.interval <= 0 {
		h.logger.Info("periodic health checks disabled", "interval", h.interval)
		return
	}

	ticker := time.NewTicker(h.interval)
	h.logger.Info("starting periodic health checks", "interval", h.interval)

	go func() {
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				h.logger.Debug("running periodic health check")
				h.Run(ctx)
			case <-ctx.Done():
				h.logger.Info("stopping periodic health checks")
				return
			}
		}
	}()
}

// AddCustomCheck allows adding a custom health check from outside
func (h *HealthChecker) AddCustomCheck(name string, check HealthCheckFunc) error {
	if _, exists := h.checks[name]; exists {
		return fmt.Errorf("health check with name '%s' already exists", name)
	}

	h.RegisterCheck(name, check)
	return nil
}