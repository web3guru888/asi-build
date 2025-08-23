package api

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/api/routes"
	"mlops-platform/internal/monitoring/healthcheck"
	"mlops-platform/internal/monitoring/metrics"
	"mlops-platform/internal/monitoring/tracing"
)

// Server encapsulates the HTTP server and its dependencies
type Server struct {
	httpServer *http.Server
	config     *config.Config
	logger     *logging.Logger
}

// NewServer creates and initializes a new API server
func NewServer(cfg *config.Config, logger *logging.Logger) *Server {
	mux := http.NewServeMux()

	// Setup monitoring endpoints first (should not require auth)
	mux.HandleFunc("/health", healthcheck.Handler)
	mux.HandleFunc("/metrics", metrics.Handler)

	// Setup API routes with middleware
	apiHandler := routes.SetupRoutes(cfg, logger)
	mux.Handle("/api/", apiHandler)

	// Wrap with tracing middleware
	tracedHandler := tracing.Middleware(mux, logger)

	// Create HTTP server
	httpServer := &http.Server{
		Addr:         cfg.Server.Host + ":" + cfg.Server.Port,
		Handler:      tracedHandler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	return &Server{
		httpServer: httpServer,
		config:     cfg,
		logger:     logger,
	}
}

// Start runs the server and listens for incoming requests
func (s *Server) Start() error {
	// Use context for graceful shutdown
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	// Start server in a goroutine
	go func() {
		s.logger.Info(fmt.Sprintf("API server starting on %s:%s", s.config.Server.Host, s.config.Server.Port))
		if err := s.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			s.logger.Error(fmt.Sprintf("API server failed to start: %v", err))
		}
	}()

	// Block until termination signal is received
	<-ctx.Done()

	s.logger.Info("Shutting down API server gracefully...")

	// Create shutdown context with timeout
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()

	// Attempt graceful shutdown
	if err := s.httpServer.Shutdown(shutdownCtx); err != nil {
		s.logger.Error(fmt.Sprintf("API server forced to shutdown: %v", err))
		return err
	}

	s.logger.Info("API server stopped gracefully")
	return nil
}

// Run initializes and starts the server
func Run(cfg *config.Config) {
	logger := logging.NewLogger(cfg)

	server := NewServer(cfg, logger)

	if err := server.Start(); err != nil {
		log.Printf("Server exited with error: %v", err)
		os.Exit(1)
	}
}