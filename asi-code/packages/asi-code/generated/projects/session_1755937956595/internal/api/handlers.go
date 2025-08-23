package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/model/service"
	"mlops-platform/internal/model/versioning"
	"mlops-platform/internal/monitoring/metrics"
)

// ModelDeployRequest represents the request body for deploying a model
type ModelDeployRequest struct {
	ModelName    string            `json:"model_name" validate:"required"`
	Version      string            `json:"version" validate:"required"`
	ArtifactPath string            `json:"artifact_path" validate:"required"`
	Metadata     map[string]string `json:"metadata,omitempty"`
	Scaling      int               `json:"scaling" validate:"min=1,max=10"`
}

// ModelPredictRequest represents the prediction request payload
type ModelPredictRequest struct {
	ModelName string          `json:"model_name" validate:"required"`
	Version   string          `json:"version"`
	Inputs    json.RawMessage `json:"inputs" validate:"required"`
}

// ModelPredictResponse represents the prediction response
type ModelPredictResponse struct {
	ModelName string          `json:"model_name"`
	Version   string          `json:"version"`
	Outputs   json.RawMessage `json:"outputs"`
	LatencyMs int64           `json:"latency_ms"`
	Timestamp time.Time       `json:"timestamp"`
}

// HealthResponse represents health check response
type HealthResponse struct {
	Status    string    `json:"status"`
	Timestamp time.Time `json:"timestamp"`
	Service   string    `json:"service"`
	Version   string    `json:"version"`
}

// ErrorResponse represents error response
type ErrorResponse struct {
	Error     string    `json:"error"`
	Timestamp time.Time `json:"timestamp"`
}

// Handlers encapsulates all HTTP handlers for the API
type Handlers struct {
	ModelService *service.ModelService
	Versioning   *versioning.Versioning
	Config       *config.Config
	Logger       *logging.Logger
	Metrics      *metrics.Metrics
}

// NewHandlers creates a new instance of Handlers
func NewHandlers(
	modelSvc *service.ModelService,
	versioning *versioning.Versioning,
	cfg *config.Config,
	logger *logging.Logger,
	metrics *metrics.Metrics,
) *Handlers {
	return &Handlers{
		ModelService: modelSvc,
		Versioning:   versioning,
		Config:       cfg,
		Logger:       logger,
		Metrics:      metrics,
	}
}

// DeployModel handles model deployment requests
func (h *Handlers) DeployModel(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	h.Logger.Info("Received model deployment request")

	var req ModelDeployRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.handleError(w, fmt.Sprintf("invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	// Basic validation
	if req.ModelName == "" {
		h.handleError(w, "model_name is required", http.StatusBadRequest)
		return
	}
	if req.Version == "" {
		h.handleError(w, "version is required", http.StatusBadRequest)
		return
	}
	if req.ArtifactPath == "" {
		h.handleError(w, "artifact_path is required", http.StatusBadRequest)
		return
	}
	if req.Scaling <= 0 || req.Scaling > 10 {
		req.Scaling = 1 // default
	}

	// Record metrics
	start := time.Now()
	h.Metrics.IncrementDeployAttempts(req.ModelName)
	defer func() {
		latency := time.Since(start).Milliseconds()
		h.Metrics.ObserveDeployLatency(req.ModelName, float64(latency))
	}()

	// Deploy model
	err := h.ModelService.DeployModel(ctx, service.DeployModelRequest{
		ModelName:    req.ModelName,
		Version:      req.Version,
		ArtifactPath: req.ArtifactPath,
		Metadata:     req.Metadata,
		Scaling:      req.Scaling,
	})
	if err != nil {
		h.Logger.Error("Model deployment failed", "error", err, "model", req.ModelName, "version", req.Version)
		h.handleError(w, fmt.Sprintf("failed to deploy model: %v", err), http.StatusInternalServerError)
		h.Metrics.IncrementDeployFailures(req.ModelName)
		return
	}

	// Success response
	h.Logger.Info("Model deployed successfully", "model", req.ModelName, "version", req.Version)
	h.Metrics.IncrementDeploys(req.ModelName)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message":   "Model deployed successfully",
		"model":     req.ModelName,
		"version":   req.Version,
		"timestamp": time.Now().UTC(),
	})
}

// Predict handles model inference requests
func (h *Handlers) Predict(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	h.Logger.Info("Received prediction request")

	var req ModelPredictRequest
	body, err := io.ReadAll(r.Body)
	if err != nil {
		h.handleError(w, "failed to read request body", http.StatusBadRequest)
		return
	}
	if err := json.Unmarshal(body, &req); err != nil {
		h.handleError(w, fmt.Sprintf("invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	if req.ModelName == "" {
		h.handleError(w, "model_name is required", http.StatusBadRequest)
		return
	}
	if req.Inputs == nil {
		h.handleError(w, "inputs are required", http.StatusBadRequest)
		return
	}

	// Default to latest version if not specified
	version := req.Version
	if version == "" {
		latestVersion, err := h.Versioning.GetLatestVersion(ctx, req.ModelName)
		if err != nil {
			h.handleError(w, fmt.Sprintf("failed to get latest version: %v", err), http.StatusNotFound)
			return
		}
		version = latestVersion
	}

	// Record metrics
	start := time.Now()
	h.Metrics.IncrementPredictionAttempts(req.ModelName, version)
	defer func() {
		latency := time.Since(start).Milliseconds()
		h.Metrics.ObservePredictionLatency(req.ModelName, version, float64(latency))
	}()

	// Perform prediction
	outputs, err := h.ModelService.Predict(ctx, req.ModelName, version, req.Inputs)
	if err != nil {
		h.Logger.Error("Prediction failed", "error", err, "model", req.ModelName, "version", version)
		h.handleError(w, fmt.Sprintf("prediction failed: %v", err), http.StatusInternalServerError)
		h.Metrics.IncrementPredictionFailures(req.ModelName, version)
		return
	}

	// Success response
	h.Logger.Info("Prediction successful", "model", req.ModelName, "version", version)
	h.Metrics.IncrementPredictions(req.ModelName, version)

	response := ModelPredictResponse{
		ModelName: req.ModelName,
		Version:   version,
		Outputs:   outputs,
		LatencyMs: time.Since(start).Milliseconds(),
		Timestamp: time.Now().UTC(),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(response); err != nil {
		h.Logger.Error("Failed to encode prediction response", "error", err)
	}
}

// GetModelStatus returns the status of a deployed model
func (h *Handlers) GetModelStatus(w http.ResponseWriter, r *http.Request) {
	modelName := r.URL.Query().Get("model_name")
	if modelName == "" {
		h.handleError(w, "model_name query parameter is required", http.StatusBadRequest)
		return
	}

	status, err := h.ModelService.GetModelStatus(r.Context(), modelName)
	if err != nil {
		h.Logger.Error("Failed to get model status", "error", err, "model", modelName)
		h.handleError(w, fmt.Sprintf("failed to get model status: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"model_name": modelName,
		"status":     status,
		"timestamp":  time.Now().UTC(),
	})
}

// ListModels returns all registered models
func (h *Handlers) ListModels(w http.ResponseWriter, r *http.Request) {
	models, err := h.Versioning.ListModels(r.Context())
	if err != nil {
		h.Logger.Error("Failed to list models", "error", err)
		h.handleError(w, fmt.Sprintf("failed to list models: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"models":    models,
		"count":     len(models),
		"timestamp": time.Now().UTC(),
	})
}

// GetModelVersion returns version details for a specific model
func (h *Handlers) GetModelVersion(w http.ResponseWriter, r *http.Request) {
	modelName := r.URL.Query().Get("model_name")
	version := r.URL.Query().Get("version")

	if modelName == "" {
		h.handleError(w, "model_name query parameter is required", http.StatusBadRequest)
		return
	}

	var versionInfo interface{}
	var err error

	if version != "" {
		versionInfo, err = h.Versioning.GetVersionInfo(r.Context(), modelName, version)
	} else {
		versionInfo, err = h.Versioning.GetLatestVersionInfo(r.Context(), modelName)
	}

	if err != nil {
		h.Logger.Error("Failed to get model version info", "error", err, "model", modelName, "version", version)
		h.handleError(w, fmt.Sprintf("failed to get version info: %v", err), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"model_name": modelName,
		"version":    version,
		"info":       versionInfo,
		"timestamp":  time.Now().UTC(),
	})
}

// HealthCheck returns health status of the API service
func (h *Handlers) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.Logger.Debug("Health check received")

	serviceName := "api-gateway"
	if r.URL.Query().Get("service") != "" {
		serviceName = r.URL.Query().Get("service")
	}

	// You can extend this to check dependencies (DB, model servers, etc.)
	response := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now().UTC(),
		Service:   serviceName,
		Version:   h.Config.Version,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

// handleError writes error response with proper logging and metrics
func (h *Handlers) handleError(w http.ResponseWriter, message string, statusCode int) {
	h.Logger.Error("Request failed", "error", message, "status_code", statusCode)
	h.Metrics.IncrementErrors("api", statusCode)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(ErrorResponse{
		Error:     message,
		Timestamp: time.Now().UTC(),
	})
}

// RegisterRoutes sets up all HTTP routes for the API
func (h *Handlers) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /api/v1/models/deploy", h.DeployModel)
	mux.HandleFunc("POST /api/v1/models/predict", h.Predict)
	mux.HandleFunc("GET /api/v1/models/status", h.GetModelStatus)
	mux.HandleFunc("GET /api/v1/models", h.ListModels)
	mux.HandleFunc("GET /api/v1/models/version", h.GetModelVersion)
	mux.HandleFunc("GET /health", h.HealthCheck)
	mux.HandleFunc("GET /ready", h.HealthCheck)
	mux.HandleFunc("GET /live", h.HealthCheck)

	// Versioned health checks
	mux.HandleFunc("GET /health/{service}", h.HealthCheck)
}

// GetMetricsHandler returns the Prometheus metrics handler
func (h *Handlers) GetMetricsHandler() http.Handler {
	return h.Metrics.GetHandler()
}

// GetTracingHandler returns the tracing endpoint handler (OTLP, etc.)
func (h *Handlers) GetTracingHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Tracing endpoint"))
	}
}

// HomeHandler returns basic welcome message
func (h *Handlers) HomeHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		h.handleError(w, "not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"message": "Welcome to MLOps Platform API",
		"version": h.Config.Version,
		"status":  "running",
	})
}

// ApplyMiddleware wraps handlers with common middleware
func (h *Handlers) ApplyMiddleware(handler http.Handler) http.Handler {
	return h.loggingMiddleware(h.metricsMiddleware(handler))
}

// loggingMiddleware logs incoming requests
func (h *Handlers) loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		h.Logger.Info("Request received",
			"method", r.Method,
			"path", r.URL.Path,
			"remote", r.RemoteAddr,
		)

		next.ServeHTTP(w, r)

		h.Logger.Info("Request completed",
			"method", r.Method,
			"path", r.URL.Path,
			"duration_ms", time.Since(start).Milliseconds(),
		)
	})
}

// metricsMiddleware collects HTTP request metrics
func (h *Handlers) metricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		h.Metrics.IncrementRequests(r.URL.Path, r.Method)
		defer func() {
			latency := time.Since(start).Milliseconds()
			h.Metrics.ObserveRequestLatency(r.URL.Path, r.Method, float64(latency))
		}()
		next.ServeHTTP(w, r)
	})
}

// EnableCORS adds CORS headers to responses
func (h *Handlers) EnableCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}