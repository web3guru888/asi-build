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

	"mlops-platform/cmd/model-server/internal/config"
	"mlops-platform/cmd/model-server/internal/logging"
	"mlops-platform/internal/model/deployer"
	"mlops-platform/internal/model/loader"
	"mlops-platform/internal/model/registry"
	"mlops-platform/internal/model/repository"
	"mlops-platform/internal/model/service"
	"mlops-platform/internal/monitoring/healthcheck"
	"mlops-platform/internal/monitoring/metrics"
	"mlops-platform/internal/monitoring/tracing"
)

func main() {
	var configFile string
	flag.StringVar(&configFile, "config", "config.yaml", "path to config file")
	flag.Parse()

	// Load configuration
	cfg, err := config.Load(configFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load config: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger := logging.NewLogger(cfg.LogLevel, "model-server")
	logger.Infof("Starting model server with config: %+v", cfg)

	// Initialize tracer
	tracer, tracerCloser, err := tracing.InitTracer(cfg.ServiceName, cfg.JaegerEndpoint)
	if err != nil {
		logger.Fatalf("Failed to initialize tracer: %v", err)
	}
	defer tracerCloser.Close()

	// Initialize metrics
	metricsCollector := metrics.NewPrometheusCollector()
	metrics.Use(metricsCollector)

	// Initialize model registry client
	registryClient := registry.NewClient(cfg.ModelRegistryURL, cfg.JWTSecret)

	// Initialize model repository
	modelRepo := repository.NewModelRepository(cfg.StoragePath)

	// Initialize model loader
	modelLoader := loader.NewModelLoader(logger, tracer, modelRepo)

	// Initialize deployer
	deployer := deployer.NewModelDeployer(cfg, logger, modelLoader, registryClient)

	// Initialize model service
	modelService := service.NewModelService(cfg, logger, tracer, deployer, registryClient)

	// Setup HTTP server
	mux := http.NewServeMux()
	healthcheck.RegisterHandlers(mux)
	// Register model serving endpoints
	mux.HandleFunc("/predict", modelService.HandlePredict)
	mux.HandleFunc("/v1/models/", modelService.HandleModelRequest)

	server := &http.Server{
		Addr:         cfg.ServerAddress,
		Handler:      metrics.WithMetrics(mux, metricsCollector),
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan
		logger.Info("Shutting down model server...")

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		if err := server.Shutdown(ctx); err != nil {
			logger.Errorf("Server shutdown failed: %v", err)
		}
	}()

	// Start the server
	logger.Infof("Model server listening on %s", cfg.ServerAddress)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Fatalf("Server failed to start: %v", err)
	}

	logger.Info("Model server stopped gracefully")
}