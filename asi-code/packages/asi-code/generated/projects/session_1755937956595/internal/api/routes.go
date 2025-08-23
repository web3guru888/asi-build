package api

import (
	"log"
	"net/http"

	"mlops-platform/internal/api/handlers"
	"mlops-platform/internal/auth/middleware"
	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"mlops-platform/internal/monitoring/healthcheck"
)

// SetupRoutes initializes and configures all HTTP routes for the API gateway.
// It registers handlers for model deployment, inference, versioning, authentication, and health checks.
func SetupRoutes(cfg *config.Config, log *logging.Logger, modelService *service.ModelService) *http.ServeMux {
	mux := http.NewServeMux()

	// Initialize handlers
	h := &handlers.Handlers{
		Config:       cfg,
		Logger:       log,
		ModelService: modelService,
	}

	// Public routes
	mux.HandleFunc("GET /health", healthcheck.HealthCheckHandler)
	mux.HandleFunc("POST /auth/login", h.LoginHandler)
	mux.HandleFunc("POST /auth/validate", h.ValidateTokenHandler)

	// Model inference route (public but requires valid token)
	mux.HandleFunc("POST /predict", middleware.Authenticate(h.PredictHandler))

	// Protected model management routes
	protected := middleware.Authenticate(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			if r.URL.Path == "/models/deploy" {
				h.DeployModelHandler(w, r)
				return
			}
		case http.MethodGet:
			if r.URL.Path == "/models" {
				h.ListModelsHandler(w, r)
				return
			} else if len(r.URL.Path) > 7 && r.URL.Path[:7] == "/models/" {
				h.GetModelHandler(w, r)
				return
			}
		case http.MethodDelete:
			if len(r.URL.Path) > 7 && r.URL.Path[:7] == "/models/" {
				h.DeleteModelHandler(w, r)
				return
			}
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}))

	mux.Handle("/models/", protected)
	mux.Handle("/models/deploy", protected)
	mux.Handle("/models", protected)

	log.Info("Routes initialized",
		"api_addr", cfg.APIHost+":"+cfg.APIPort,
		"model_server_addr", cfg.ModelServerHost+":"+cfg.ModelServerPort)

	return mux
}