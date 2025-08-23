package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"mlops-platform/cmd/gateway/internal/config"
	"mlops-platform/cmd/gateway/internal/logging"
	"mlops-platform/cmd/gateway/internal/monitoring"
	"mlops-platform/cmd/gateway/internal/api"
	"mlops-platform/cmd/gateway/internal/api/middleware"
	"mlops-platform/cmd/gateway/internal/auth"
	"mlops-platform/cmd/gateway/internal/model/service"

	"go.uber.org/zap"
)

var (
	configFile = flag.String("config", "configs/gateway.yaml", "Path to configuration file")
)

func main() {
	flag.Parse()

	// Load configuration
	cfg, err := config.Load(*configFile)
	if err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Failed to load config: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger, err := logging.NewLogger(cfg.LogLevel, cfg.Environment)
	if err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer func(logger *zap.Logger) {
		_ = logger.Sync()
	}(logger)

	// Initialize monitoring (metrics, tracing, health checks)
	monitor := monitoring.NewMonitor(cfg.ServiceName, cfg.Environment)
	monitor.SetupMetrics()
	monitor.SetupTracing(cfg.TracingEndpoint)
	monitor.SetupHealthCheck()

	// Initialize dependencies
	authSvc := auth.NewJWTService(cfg.JWTSecretKey, 24*time.Hour)
	modelSvc := model_service.NewModelService(cfg.ModelRegistryURL, cfg.ModelStoragePath)

	// Setup HTTP server with routes and middleware
	engine := api.NewServer(cfg)
	router := engine.Router()

	// Apply global middleware
	router.Use(middleware.LoggingMiddleware(logger))
	router.Use(middleware.TracingMiddleware())
	router.Use(middleware.MetricsMiddleware(monitor))

	// Auth middleware for protected routes
	protected := router.Group("/v1")
	protected.Use(middleware.AuthMiddleware(authSvc.ValidateToken))

	// Public API routes
	api.SetupRoutes(router, authSvc, modelSvc, logger, monitor)
	// Protected API routes (e.g., model deployment, inference management)
	api.SetupProtectedRoutes(protected, modelSvc, logger, monitor)

	// Mount health check handler
	router.Get("/health", monitor.HealthCheckHandler)

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.Port),
		Handler: router,
	}

	// Run server in a separate goroutine
	go func() {
		logger.Info("gateway service starting", zap.Int("port", cfg.Port), zap.String("env", cfg.Environment))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("gateway server failed to start", zap.Error(err))
			os.Exit(1)
		}
	}()

	// Graceful shutdown handler
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("shutting down gateway server gracefully...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("gateway server forced to shutdown", zap.Error(err))
	}

	monitor.Close() // Close monitoring resources like tracer, metrics exporter
	logger.Info("gateway server stopped")
}