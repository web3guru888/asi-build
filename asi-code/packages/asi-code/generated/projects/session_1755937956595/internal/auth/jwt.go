package auth

import (
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v4"
	"mlops-platform/internal/config"
	"mlops-platform/internal/logging"
)

// JWTManager handles JWT token generation and validation
type JWTManager struct {
	secretKey     string
	tokenDuration time.Duration
	logger        logging.Logger
}

// Claims represents the payload in JWT token
type Claims struct {
	UserID   string `json:"user_id"`
	Email    string `json:"email"`
	Username string `json:"username"`
	Role     string `json:"role"`
	jwt.RegisteredClaims
}

// NewJWTManager creates a new JWT manager instance
func NewJWTManager(cfg *config.AuthConfig, logger logging.Logger) (*JWTManager, error) {
	if cfg == nil {
		return nil, errors.New("auth config cannot be nil")
	}
	if cfg.JWTSecretKey == "" {
		return nil, errors.New("JWT secret key must be set")
	}
	if cfg.JWTExpiryMinutes == 0 {
		return nil, errors.New("JWT expiry minutes must be greater than 0")
	}

	return &JWTManager{
		secretKey:     cfg.JWTSecretKey,
		tokenDuration: time.Duration(cfg.JWTExpiryMinutes) * time.Minute,
		logger:        logger,
	}, nil
}

// GenerateToken generates a new JWT token for the given user claims
func (m *JWTManager) GenerateToken(userID, email, username, role string) (string, error) {
	now := time.Now()
	claims := &Claims{
		UserID:   userID,
		Email:    email,
		Username: username,
		Role:     role,
		RegisteredClaims: jwt.RegisteredClaims{
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(m.tokenDuration)),
			Issuer:    "mlops-platform-auth",
			Subject:   userID,
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signedToken, err := token.SignedString([]byte(m.secretKey))
	if err != nil {
		m.logger.Error("failed to sign JWT token", "error", err)
		return "", fmt.Errorf("failed to sign token: %w", err)
	}

	m.logger.Info("JWT token generated successfully", "user_id", userID, "expires_in", m.tokenDuration)
	return signedToken, nil
}

// ValidateToken parses and validates the provided JWT token
func (m *JWTManager) ValidateToken(accessToken string) (*Claims, error) {
	if accessToken == "" {
		return nil, errors.New("token is required")
	}

	// Remove "Bearer " prefix if present
	tokenString := strings.TrimPrefix(accessToken, "Bearer ")
	tokenString = strings.TrimSpace(tokenString)

	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(m.secretKey), nil
	})

	if err != nil {
		m.logger.Error("failed to parse token", "error", err)
		return nil, fmt.Errorf("invalid token: %w", err)
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token claims")
	}

	// Additional validation
	if claims.Issuer != "mlops-platform-auth" {
		return nil, errors.New("invalid token issuer")
	}

	if time.Now().After(claims.ExpiresAt.Time) {
		return nil, errors.New("token expired")
	}

	m.logger.Debug("token validated successfully", "user_id", claims.UserID, "role", claims.Role)
	return claims, nil
}

// FromAuthHeader extracts the token from Authorization header
func (m *JWTManager) FromAuthHeader(r *http.Request) (string, error) {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return "", errors.New("authorization header missing")
	}

	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		return "", errors.New("invalid authorization header format")
	}

	token := parts[1]
	if token == "" {
		return "", errors.New("token missing in authorization header")
	}

	return token, nil
}

// Middleware creates an HTTP middleware that validates JWT tokens
func (m *JWTManager) Middleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token, err := m.FromAuthHeader(r)
		if err != nil {
			m.logger.Warn("authentication failed", "error", err, "path", r.URL.Path, "method", r.Method)
			http.Error(w, "Forbidden: authentication required", http.StatusForbidden)
			return
		}

		claims, err := m.ValidateToken(token)
		if err != nil {
			m.logger.Warn("invalid token in middleware", "error", err, "path", r.URL.Path, "method", r.Method)
			http.Error(w, "Forbidden: invalid or expired token", http.StatusForbidden)
			return
		}

		// Add claims to context for downstream handlers
		ctx := context.WithValue(r.Context(), "claims", claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}