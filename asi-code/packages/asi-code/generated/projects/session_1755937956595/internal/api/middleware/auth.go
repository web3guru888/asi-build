package middleware

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"mlops-platform/internal/auth/jwt"
	"mlops-platform/internal/logging"
)

// AuthMiddleware handles JWT-based authentication for API endpoints.
// It extracts the token from the Authorization header, validates it,
// and sets the authenticated user information in the request context.
type AuthMiddleware struct {
	jwtService *jwt.JWTService
	logger     *logging.Logger
}

// NewAuthMiddleware creates a new instance of AuthMiddleware.
func NewAuthMiddleware(jwtService *jwt.JWTService, logger *logging.Logger) *AuthMiddleware {
	return &AuthMiddleware{
		jwtService: jwtService,
		logger:     logger,
	}
}

// AuthRequired is the middleware function that validates the incoming request.
func (am *AuthMiddleware) AuthRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Extract token from Authorization header
		tokenString := am.extractToken(r)
		if tokenString == "" {
			am.logger.Warn("Authorization header missing or malformed", map[string]interface{}{
				"method": r.Method,
				"url":    r.URL.String(),
				"remote": r.RemoteAddr,
			})
			http.Error(w, "Authorization header is required", http.StatusUnauthorized)
			return
		}

		// Validate JWT token
		claims, err := am.jwtService.ValidateToken(tokenString)
		if err != nil {
			am.logger.Warn("Invalid or expired JWT token", map[string]interface{}{
				"method": r.Method,
				"url":    r.URL.String(),
				"remote": r.RemoteAddr,
				"error":  err.Error(),
			})
			http.Error(w, "Invalid or expired token", http.StatusUnauthorized)
			return
		}

		// Check if token is expired
		if time.Now().Unix() > claims.ExpiresAt {
			am.logger.Warn("JWT token expired", map[string]interface{}{
				"method":   r.Method,
				"url":      r.URL.String(),
				"remote":   r.RemoteAddr,
				"username": claims.Username,
			})
			http.Error(w, "Token has expired", http.StatusUnauthorized)
			return
		}

		// Log successful authentication
		am.logger.Info("User authenticated successfully", map[string]interface{}{
			"username": claims.Username,
			"method":   r.Method,
			"url":      r.URL.String(),
			"remote":   r.RemoteAddr,
		})

		// Create context with user claims
		ctx := context.WithValue(r.Context(), "user", claims)
		r = r.WithContext(ctx)

		// Call the next handler
		next.ServeHTTP(w, r)
	})
}

// extractToken retrieves the JWT token from the Authorization header.
// Supports "Bearer <token>" format only.
func (am *AuthMiddleware) extractToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return ""
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
		return ""
	}

	return parts[1]
}

// UnauthorizedResponse sends a standardized unauthorized response.
func UnauthorizedResponse(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnauthorized)
	if err := json.NewEncoder(w).Encode(map[string]string{
		"error": "unauthorized access",
	}); err != nil {
		log.Printf("Failed to encode unauthorized response: %v", err)
	}
}

// ForbiddenResponse sends a standardized forbidden response.
func ForbiddenResponse(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusForbidden)
	if err := json.NewEncoder(w).Encode(map[string]string{
		"error": "forbidden: insufficient permissions",
	}); err != nil {
		log.Printf("Failed to encode forbidden response: %v", err)
	}
}

// WithRole checks if the authenticated user has one of the required roles.
func (am *AuthMiddleware) WithRole(requiredRoles ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			user := r.Context().Value("user")
			if user == nil {
				UnauthorizedResponse(w)
				return
			}

			claims, ok := user.(*jwt.Claims)
			if !ok {
				am.logger.Error("Failed to assert user claims type", nil)
				UnauthorizedResponse(w)
				return
			}

			hasRole := false
			for _, role := range requiredRoles {
				if claims.Role == role {
					hasRole = true
					break
				}
			}

			if !hasRole {
				am.logger.Warn("User lacks required role", map[string]interface{}{
					"username": claims.Username,
					"required": requiredRoles,
					"actual":   claims.Role,
					"method":   r.Method,
					"url":      r.URL.String(),
				})
				ForbiddenResponse(w)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// GetAuthenticatedUser extracts authenticated user claims from context.
func GetAuthenticatedUser(ctx context.Context) (*jwt.Claims, bool) {
	user, exists := ctx.Value("user").(*jwt.Claims)
	return user, exists
}

// RequireAdmin is a convenience middleware that ensures the user has admin role.
func (am *AuthMiddleware) RequireAdmin(next http.Handler) http.Handler {
	return am.WithRole("admin")(next)
}

// OptionalAuth allows requests without authentication but validates token if present.
func (am *AuthMiddleware) OptionalAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		tokenString := am.extractToken(r)
		if tokenString == "" {
			// No token provided - proceed without authentication
			next.ServeHTTP(w, r)
			return
		}

		// Token provided - validate it
		claims, err := am.jwtService.ValidateToken(tokenString)
		if err != nil {
			am.logger.Warn("Optional auth: invalid token provided", map[string]interface{}{
				"method": r.Method,
				"url":    r.URL.String(),
				"error":  err.Error(),
			})
			http.Error(w, "Invalid token in Authorization header", http.StatusUnauthorized)
			return
		}

		if time.Now().Unix() > claims.ExpiresAt {
			am.logger.Warn("Optional auth: token has expired", map[string]interface{}{
				"username": claims.Username,
				"method":   r.Method,
				"url":      r.URL.String(),
			})
			http.Error(w, "Token has expired", http.StatusUnauthorized)
			return
		}

		am.logger.Debug("Optional authentication successful", map[string]interface{}{
			"username": claims.Username,
			"method":   r.Method,
			"url":      r.URL.String(),
		})

		// Add user to context even if not required
		ctx := context.WithValue(r.Context(), "user", claims)
		r = r.WithContext(ctx)

		next.ServeHTTP(w, r)
	})
}