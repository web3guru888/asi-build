package auth

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
	"github.com/golang-jwt/jwt/v4"
)

// Validator defines the interface for request authentication and permission checking
type Validator interface {
	ValidateAPIKey(r *http.Request) (bool, error)
	ValidateJWTToken(token string) (*jwt.Token, error)
	HasPermission(claims jwt.MapClaims, requiredPermission string) bool
	ValidateModelAccess(userID, modelID string, action string) (bool, error)
}

// AuthValidator implements authentication and authorization logic
type AuthValidator struct {
	cfg    *config.Config
	logger *logging.Logger
}

// NewAuthValidator creates a new instance of AuthValidator
func NewAuthValidator(cfg *config.Config, logger *logging.Logger) *AuthValidator {
	return &AuthValidator{
		cfg:    cfg,
		logger: logger,
	}
}

// ValidateAPIKey validates the API key from the request header
func (v *AuthValidator) ValidateAPIKey(r *http.Request) (bool, error) {
	startTime := time.Now()
	defer func() {
		v.logger.WithFields(map[string]interface{}{
			"method":     "ValidateAPIKey",
			"duration":   time.Since(startTime).Milliseconds(),
			"success":    false,
			"remoteAddr": r.RemoteAddr,
		}).Info("API key validation completed")
	}()

	apiKey := r.Header.Get("X-API-Key")
	if apiKey == "" {
		apiKey = r.URL.Query().Get("api_key")
	}

	if apiKey == "" {
		v.logger.Warn("Missing API key in request")
		return false, fmt.Errorf("missing API key")
	}

	// In production, this would validate against a secure store (e.g., database, Redis)
	// For now, validate against configured allowed keys
	for _, validKey := range v.cfg.Security.AllowedAPIKeys {
		if strings.TrimSpace(apiKey) == validKey {
			v.logger.WithFields(map[string]interface{}{
				"method": "ValidateAPIKey",
				"result": "success",
			}).Info("Valid API key provided")
			return true, nil
		}
	}

	v.logger.WithFields(map[string]interface{}{
		"method": "ValidateAPIKey",
		"result": "failed",
	}).Error("Invalid API key provided")
	return false, fmt.Errorf("invalid API key")
}

// ValidateJWTToken parses and validates a JWT token string
func (v *AuthValidator) ValidateJWTToken(tokenString string) (*jwt.Token, error) {
	if tokenString == "" {
		return nil, fmt.Errorf("token is missing")
	}

	// Remove Bearer prefix if present
	tokenString = strings.TrimSpace(strings.Replace(tokenString, "Bearer", "", 1))
	tokenString = strings.TrimSpace(tokenString)

	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Validate signing method
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(v.cfg.Security.JWTSecret), nil
	})

	if err != nil {
		v.logger.WithFields(map[string]interface{}{
			"method": "ValidateJWTToken",
			"error":  err.Error(),
		}).Error("Failed to parse JWT token")
		return nil, fmt.Errorf("failed to parse token: %w", err)
	}

	if !token.Valid {
		v.logger.Warn("Invalid or expired JWT token")
		return nil, fmt.Errorf("invalid token")
	}

	return token, nil
}

// HasPermission checks if the JWT claims include a required permission
func (v *AuthValidator) HasPermission(claims jwt.MapClaims, requiredPermission string) bool {
	if claims["permissions"] == nil {
		v.logger.Warn("No permissions found in claims")
		return false
	}

	permissions, ok := claims["permissions"].([]interface{})
	if !ok {
		// Try to handle as []string
		permStr, ok := claims["permissions"].(string)
		if ok {
			return permStr == requiredPermission || permStr == "*"
		}
		return false
	}

	for _, p := range permissions {
		permission, ok := p.(string)
		if !ok {
			continue
		}
		if permission == requiredPermission || permission == "*" {
			return true
		}
	}

	v.logger.WithFields(map[string]interface{}{
		"requiredPermission": requiredPermission,
	}).Warn("Required permission not granted")
	return false
}

// ValidateModelAccess determines if a user has access to perform an action on a specific model
func (v *AuthValidator) ValidateModelAccess(userID, modelID, action string) (bool, error) {
	if userID == "" || modelID == "" || action == "" {
		return false, fmt.Errorf("invalid input parameters")
	}

	// Log access attempt
	fields := map[string]interface{}{
		"userID":  userID,
		"modelID": modelID,
		"action":  action,
	}
	v.logger.WithFields(fields).Info("Validating model access")

	// In a real implementation, this would check against a policy engine or database
	// For demonstration, implement basic rules:
	switch action {
	case "read":
		// All users can read models (public access)
		return true, nil
	case "update", "delete":
		// Only owners or admins can modify/delete
		isOwner := v.isModelOwner(userID, modelID)
		isAdmin := v.isUserAdmin(userID)
		return isOwner || isAdmin, nil
	case "deploy":
		// Owners and operators can deploy
		isOwner := v.isModelOwner(userID, modelID)
		isOperator := v.isUserOperator(userID)
		isAdmin := v.isUserAdmin(userID)
		return isOwner || isOperator || isAdmin, nil
	default:
		v.logger.WithFields(map[string]interface{}{
			"action": action,
		}).Warn("Unknown action type")
		return false, fmt.Errorf("unknown action type: %s", action)
	}
}

// isModelOwner checks if the user is the owner of the model
// In production, this would query the model registry or database
func (v *AuthValidator) isModelOwner(userID, modelID string) bool {
	// Placeholder logic - in reality, check ownership via model registry
	// For now, assume first part of modelID is the owner ID
	parts := strings.Split(modelID, "/")
	if len(parts) > 0 {
		ownerID := parts[0]
		return ownerID == userID
	}
	return false
}

// isUserAdmin checks if the user has admin privileges
// In production, this would check against identity provider or user service
func (v *AuthValidator) isUserAdmin(userID string) bool {
	for _, adminID := range v.cfg.Security.AdminUserIDs {
		if userID == adminID {
			return true
		}
	}
	return false
}

// isUserOperator checks if the user has operator privileges
// In production, this would check against identity provider or user service
func (v *AuthValidator) isUserOperator(userID string) bool {
	// Operators are allowed to deploy models
	for _, operatorID := range v.cfg.Security.OperatorUserIDs {
		if userID == operatorID {
			return true
		}
	}
	return false
}

// ValidateRequest ensures the request has valid authentication
func (v *AuthValidator) ValidateRequest(ctx context.Context, r *http.Request, requiredPermission string) error {
	// Try API key first
	valid, err := v.ValidateAPIKey(r)
	if err == nil && valid {
		return nil
	}

	// Fall back to JWT
	tokenString := r.Header.Get("Authorization")
	token, err := v.ValidateJWTToken(tokenString)
	if err != nil {
		return fmt.Errorf("authorization failed: %w", err)
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok || !token.Valid {
		return fmt.Errorf("invalid token claims")
	}

	// Check expiration
	if exp, exists := claims["exp"]; exists {
		if float64(time.Now().Unix()) > exp.(float64) {
			return fmt.Errorf("token expired")
		}
	}

	// Validate permissions
	if requiredPermission != "" && !v.HasPermission(claims, requiredPermission) {
		return fmt.Errorf("insufficient permissions: required %s", requiredPermission)
	}

	// Attach user info to context if needed
	userID, _ := claims["sub"].(string)
	if userID != "" {
		ctx = context.WithValue(ctx, "userID", userID)
	}

	return nil
}