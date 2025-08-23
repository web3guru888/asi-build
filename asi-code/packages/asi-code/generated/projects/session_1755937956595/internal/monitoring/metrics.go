package monitoring

import (
	"context"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

var (
	// ModelServingLatency records the latency of model prediction requests.
	ModelServingLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "model_serving_latency_milliseconds",
			Help:    "Model serving latency in milliseconds.",
			Buckets: prometheus.ExponentialBuckets(1, 2, 10),
		},
		[]string{"model_name", "model_version", "success"},
	)

	// ModelPredictionsCount counts the number of prediction requests per model.
	ModelPredictionsCount = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "model_predictions_total",
			Help: "Total number of model prediction requests.",
		},
		[]string{"model_name", "model_version", "status"},
	)

	// ModelLoadDuration records the duration of model loading operations.
	ModelLoadDuration = prometheus.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "model_load_duration_seconds",
			Help:    "Duration of model loading in seconds.",
			Buckets: prometheus.ExponentialBuckets(0.1, 2, 10),
		},
	)

	// ModelDeployDuration records the duration of model deployment operations.
	ModelDeployDuration = prometheus.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "model_deploy_duration_seconds",
			Help:    "Duration of model deployment in seconds.",
			Buckets: prometheus.ExponentialBuckets(1, 2, 10),
		},
	)

	// HTTPRequestsTotal counts total HTTP requests to the model server.
	HTTPRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests.",
		},
		[]string{"handler", "method", "code"},
	)

	// HTTPRequestDuration records request latencies.
	HTTPRequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request latency in seconds.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"handler", "method"},
	)
)

// RegisterMetrics initializes and registers the prometheus metrics.
func RegisterMetrics() {
	prometheus.MustRegister(ModelServingLatency)
	prometheus.MustRegister(ModelPredictionsCount)
	prometheus.MustRegister(ModelLoadDuration)
	prometheus.MustRegister(ModelDeployDuration)
	prometheus.MustRegister(HTTPRequestsTotal)
	prometheus.MustRegister(HTTPRequestDuration)
}

// StartMetricsServer starts the HTTP server to expose prometheus metrics.
func StartMetricsServer(cfg *config.Config, logger logging.Logger) *http.Server {
	if !cfg.Monitoring.EnableMetrics {
		logger.Warn("Metrics server is disabled in configuration.")
		return nil
	}

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())

	server := &http.Server{
		Addr:    cfg.Monitoring.MetricsAddr,
		Handler: mux,
	}

	go func() {
		logger.Info("Starting metrics server", "address", cfg.Monitoring.MetricsAddr)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("Metrics server failed", "error", err)
		}
	}()

	return server
}

// RecordPredictionLatency records the latency of a prediction request.
func RecordPredictionLatency(modelName, modelVersion string, duration time.Duration, success bool) {
	status := "success"
	if !success {
		status = "error"
	}
	ModelServingLatency.WithLabelValues(modelName, modelVersion, status).Observe(float64(duration.Milliseconds()))
}

// IncrementPredictionsCount increments the prediction counter for the given model and outcome.
func IncrementPredictionsCount(modelName, modelVersion, status string) {
	ModelPredictionsCount.WithLabelValues(modelName, modelVersion, status).Inc()
}

// RecordModelLoadDuration records the duration of model loading.
func RecordModelLoadDuration(duration time.Duration) {
	ModelLoadDuration.Observe(duration.Seconds())
}

// RecordModelDeployDuration records the duration of model deployment.
func RecordModelDeployDuration(duration time.Duration) {
	ModelDeployDuration.Observe(duration.Seconds())
}

// InstrumentHandler wraps an http.HandlerFunc and records HTTP request metrics.
func InstrumentHandler(handlerName, method string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		HTTPRequestsTotal.WithLabelValues(handlerName, method, "pending").Inc()

		// Simple response writer wrapper to capture status code
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
		defer func() {
			statusCode := rw.statusCode
			HTTPRequestsTotal.WithLabelValues(
				handlerName,
				method,
				statusCodeToString(statusCode),
			).Inc()
			HTTPRequestDuration.WithLabelValues(handlerName, method).Observe(time.Since(start).Seconds())
		}()

		next(rw, r)
	}
}

// responseWriter is a minimal wrapper to capture the status code.
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

// WriteHeader captures the status code before delegating.
func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// statusCodeToString converts HTTP status code to string.
func statusCodeToString(statusCode int) string {
	switch {
	case statusCode >= 200 && statusCode < 300:
		return "2xx"
	case statusCode >= 300 && statusCode < 400:
		return "3xx"
	case statusCode >= 400 && statusCode < 500:
		return "4xx"
	case statusCode >= 500:
		return "5xx"
	default:
		return "unknown"
	}
}

// ShutdownMetricsServer shuts down the metrics server gracefully.
func ShutdownMetricsServer(server *http.Server, logger logging.Logger) {
	if server == nil {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*10)
	defer cancel()

	logger.Info("Shutting down metrics server...")
	if err := server.Shutdown(ctx); err != nil {
		logger.Error("Failed to shutdown metrics server", "error", err)
	}
}