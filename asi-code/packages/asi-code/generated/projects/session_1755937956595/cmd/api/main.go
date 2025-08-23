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

	"mlops-platform/internal/api"
	"mlops-platform/internal/api/middleware"
	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/monitoring"
)

func main() {
	// Parse command line flags
	configPath := flag.String("config", "./config.yaml", "path to config file")
	flag.Parse()

	// Load configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load config: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger := logging.NewLogger(cfg.Logging.Level, cfg.Logging.Format)
	defer logger.Sync()

	// Initialize monitoring components
	metrics := monitoring.NewMetrics(cfg.Monitoring.MetricsEnabled)
	tracer := monitoring.NewTracer(cfg.Monitoring.TracingEnabled, cfg.ServiceName)
	healthChecker := monitoring.NewHealthChecker()

	// Build router with middleware
	router := api.NewRouter()
	router.Use(middleware.Logger(logger))
	router.Use(middleware.Metrics(metrics))
	router.Use(middleware.Tracing(tracer))

	// Apply auth middleware if enabled
	if cfg.Auth.Enabled {
		authMiddleware := middleware.NewAuth(cfg.Auth.JWTSecret)
		router.Use(authMiddleware.ValidateToken)
	}

	// Register health check endpoint
	healthHandler := monitoring.NewHealthHandler(healthChecker)
	router.Get("/health", healthHandler.Check)

	// Initialize API server
	apiServer := api.NewServer(cfg.Server.Host, cfg.Server.Port, router, logger)

	// Start server
	go func() {
		logger.Info("API server starting", "addr", apiServer.Addr())
		if err := apiServer.Start(); err != nil && err != http.ErrServerClosed {
			logger.Error("API server failed to start", "error", err)
			panic(err)
		}
	}()

	// Handle graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("Shutting down API server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := apiServer.Shutdown(ctx); err != nil {
		logger.Error("API server forced shutdown", "error", err)
		os.Exit(1)
	}

	logger.Info("API server stopped gracefully")
}