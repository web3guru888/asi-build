package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// Config represents the main configuration structure for the MLops platform
type Config struct {
	Environment string `json:"environment"`
	ServiceName string `json:"service_name"`

	APIGateway APIGatewayConfig `json:"api_gateway"`
	ModelServer ModelServerConfig `json:"model_server"`
	Database DatabaseConfig `json:"database"`
	Storage StorageConfig `json:"storage"`
	ModelRegistry ModelRegistryConfig `json:"model_registry"`
	Logging LoggingConfig `json:"logging"`
	Monitoring MonitoringConfig `json:"monitoring"`
	Security SecurityConfig `json:"security"`
	Features FeatureFlags `json:"feature_flags"`
}

// APIGatewayConfig holds configuration for the API gateway
type APIGatewayConfig struct {
	Host       string        `json:"host"`
	Port       int           `json:"port"`
	ReadTimeout  time.Duration `json:"read_timeout"`
	WriteTimeout time.Duration `json:"write_timeout"`
	IdleTimeout  time.Duration `json:"idle_timeout"`
	EnableTLS  bool          `json:"enable_tls"`
	TLSCertPath string       `json:"tls_cert_path"`
	TLSKeyPath  string       `json:"tls_key_path"`
	MaxBodySize int64        `json:"max_body_size"`
}

// ModelServerConfig holds configuration for the model server
type ModelServerConfig struct {
	Host              string        `json:"host"`
	Port              int           `json:"port"`
	MaxConcurrency    int           `json:"max_concurrency"`
	LoadTimeout       time.Duration `json:"load_timeout"`
	PredictTimeout    time.Duration `json:"predict_timeout"`
	HealthCheckPeriod time.Duration `json:"health_check_period"`
	ModelDir          string        `json:"model_dir"`
	MaxModelSize      int64         `json:"max_model_size"`
	GPUSupport        bool          `json:"gpu_support"`
}

// DatabaseConfig holds database connection settings
type DatabaseConfig struct {
	Driver          string        `json:"driver"`
	DSN             string        `json:"dsn"`
	MaxOpenConns    int           `json:"max_open_conns"`
	MaxIdleConns    int           `json:"max_idle_conns"`
	ConnMaxLifetime time.Duration `json:"conn_max_lifetime"`
	MigrationsPath  string        `json:"migrations_path"`
}

// StorageConfig defines storage backend configuration
type StorageConfig struct {
	Type       string `json:"type"` // "local", "s3", "gcs"
	Bucket     string `json:"bucket"`
	Region     string `json:"region"`
	AccessKey  string `json:"access_key"`
	SecretKey  string `json:"secret_key"`
	Endpoint   string `json:"endpoint"`
	LocalPath  string `json:"local_path"`
	EnableCache bool  `json:"enable_cache"`
	CachePath  string `json:"cache_path"`
}

// ModelRegistryConfig contains settings for interacting with model registry
type ModelRegistryConfig struct {
	BaseURL    string `json:"base_url"`
	APIKey     string `json:"api_key"`
	Username   string `json:"username"`
	Password   string `json:"password"`
	Timeout    time.Duration `json:"timeout"`
	RetryCount int         `json:"retry_count"`
}

// LoggingConfig controls logging behavior across services
type LoggingConfig struct {
	Level      string `json:"level"` // debug, info, warn, error
	Format     string `json:"format"` // json, text
	Output     string `json:"output"` // stdout, file, both
	Filepath   string `json:"filepath"`
	MaxSize    int    `json:"max_size"` // MB
	MaxBackups int    `json:"max_backups"`
	MaxAge     int    `json:"max_age"` // days
	Compress   bool   `json:"compress"`
}

// MonitoringConfig defines observability settings
type MonitoringConfig struct {
	PrometheusAddr string        `json:"prometheus_addr"`
	TracingEnabled bool          `json:"tracing_enabled"`
	TracingEndpoint string       `json:"tracing_endpoint"`
	HealthCheckInterval time.Duration `json:"health_check_interval"`
	MetricsInterval time.Duration `json:"metrics_interval"`
}

// SecurityConfig contains security-related settings
type SecurityConfig struct {
	JWTSecret         string        `json:"jwt_secret"`
	JWTExpiryHours    time.Duration `json:"jwt_expiry_hours"`
	AllowedOrigins    []string      `json:"allowed_origins"`
	EnableRateLimiting bool         `json:"enable_rate_limiting"`
	RateLimitRequestsPerSecond float64 `json:"rate_limit_requests_per_second"`
	MaxRequestBodySize int64       `json:"max_request_body_size"`
	EnableAuth        bool         `json:"enable_auth"`
}

// FeatureFlags enables/disables experimental features
type FeatureFlags struct {
	EnableModelScaling     bool `json:"enable_model_scaling"`
	EnableAutoPruning      bool `json:"enable_auto_pruning"`
	EnableShadowTesting    bool `json:"enable_shadow_testing"`
	EnableCanaryDeployments bool `json:"enable_canary_deployments"`
	EnableModelExplainability bool `json:"enable_model_explainability"`
}

// LoadConfig loads configuration from a JSON file.
// It supports environment-specific config files (e.g., config.development.json).
func LoadConfig(configPath string) (*Config, error) {
	if configPath == "" {
		configPath = "config"
	}

	// Determine environment
	env := getEnvironment()

	// Build config file paths
	configFiles := []string{
		filepath.Join(configPath, "config.json"),
		filepath.Join(configPath, fmt.Sprintf("config.%s.json", env)),
	}

	var config Config
	var loaded bool

	for _, file := range configFiles {
		if _, err := os.Stat(file); os.IsNotExist(err) {
			continue
		}

		data, err := os.ReadFile(file)
		if err != nil {
			return nil, fmt.Errorf("failed to read config file %s: %w", file, err)
		}

		if err := json.Unmarshal(data, &config); err != nil {
			return nil, fmt.Errorf("failed to parse config file %s: %w", file, err)
		}
		loaded = true

		// Merge with default values and apply environment overrides if needed
		config.applyDefaults(env)
	}

	if !loaded {
		return nil, errors.New("no valid config file found in paths: " + strings.Join(configFiles, ", "))
	}

	if err := config.validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return &config, nil
}

// getEnvironment determines the current environment.
// It checks ENV first, then FALLBACK_ENV, defaults to "development".
func getEnvironment() string {
	env := os.Getenv("ENV")
	if env == "" {
		env = os.Getenv("FALLBACK_ENV")
	}
	if env == "" {
		env = "development"
	}
	return env
}

// once ensures defaults are applied only once
var defaultsOnce sync.Once

// applyDefaults sets default values for missing configuration fields
func (c *Config) applyDefaults(env string) {
	defaultsOnce.Do(func() {
		if c.Environment == "" {
			c.Environment = env
		}
		if c.ServiceName == "" {
			c.ServiceName = "mlops-platform"
		}

		// API Gateway Defaults
		if c.APIGateway.Host == "" {
			c.APIGateway.Host = "0.0.0.0"
		}
		if c.APIGateway.Port == 0 {
			c.APIGateway.Port = 8080
		}
		if c.APIGateway.ReadTimeout == 0 {
			c.APIGateway.ReadTimeout = 30 * time.Second
		}
		if c.APIGateway.WriteTimeout == 0 {
			c.APIGateway.WriteTimeout = 30 * time.Second
		}
		if c.APIGateway.IdleTimeout == 0 {
			c.APIGateway.IdleTimeout = 120 * time.Second
		}
		if c.APIGateway.MaxBodySize == 0 {
			c.APIGateway.MaxBodySize = 32 << 20 // 32 MB
		}

		// Model Server Defaults
		if c.ModelServer.Host == "" {
			c.ModelServer.Host = "0.0.0.0"
		}
		if c.ModelServer.Port == 0 {
			c.ModelServer.Port = 9000
		}
		if c.ModelServer.MaxConcurrency == 0 {
			c.ModelServer.MaxConcurrency = runtime.NumCPU()
		}
		if c.ModelServer.LoadTimeout == 0 {
			c.ModelServer.LoadTimeout = 60 * time.Second
		}
		if c.ModelServer.PredictTimeout == 0 {
			c.ModelServer.PredictTimeout = 30 * time.Second
		}
		if c.ModelServer.HealthCheckPeriod == 0 {
			c.ModelServer.HealthCheckPeriod = 10 * time.Second
		}
		if c.ModelServer.ModelDir == "" {
			c.ModelServer.ModelDir = "./models"
		}
		if c.ModelServer.MaxModelSize == 0 {
			c.ModelServer.MaxModelSize = 1 << 30 // 1GB
		}

		// Database Defaults
		if c.Database.Driver == "" {
			c.Database.Driver = "sqlite"
		}
		if c.Database.DSN == "" {
			c.Database.DSN = "./data/database.db"
		}
		if c.Database.MaxOpenConns == 0 {
			c.Database.MaxOpenConns = 25
		}
		if c.Database.MaxIdleConns == 0 {
			c.Database.MaxIdleConns = 25
		}
		if c.Database.ConnMaxLifetime == 0 {
			c.Database.ConnMaxLifetime = 5 * time.Minute
		}
		if c.Database.MigrationsPath == "" {
			c.Database.MigrationsPath = "./migrations"
		}

		// Storage Defaults
		if c.Storage.Type == "" {
			c.Storage.Type = "local"
		}
		if c.Storage.LocalPath == "" {
			c.Storage.LocalPath = "./storage"
		}
		if c.Storage.CachePath == "" {
			c.Storage.CachePath = "./cache"
		}

		// Model Registry Defaults
		if c.ModelRegistry.BaseURL == "" {
			c.ModelRegistry.BaseURL = "http://localhost:8081"
		}
		if c.ModelRegistry.Timeout == 0 {
			c.ModelRegistry.Timeout = 30 * time.Second
		}
		if c.ModelRegistry.RetryCount == 0 {
			c.ModelRegistry.RetryCount = 3
		}

		// Logging Defaults
		if c.Logging.Level == "" {
			c.Logging.Level = "info"
		}
		if c.Logging.Format == "" {
			c.Logging.Format = "json"
		}
		if c.Logging.Output == "" {
			c.Logging.Output = "stdout"
		}
		if c.Logging.Filepath == "" {
			c.Logging.Filepath = "./logs/platform.log"
		}
		if c.Logging.MaxSize == 0 {
			c.Logging.MaxSize = 100 // 100 MB
		}
		if c.Logging.MaxBackups == 0 {
			c.Logging.MaxBackups = 3
		}
		if c.Logging.MaxAge == 0 {
			c.Logging.MaxAge = 28 // days
		}

		// Monitoring Defaults
		if c.Monitoring.PrometheusAddr == "" {
			c.Monitoring.PrometheusAddr = ":9090"
		}
		if c.Monitoring.HealthCheckInterval == 0 {
			c.Monitoring.HealthCheckInterval = 30 * time.Second
		}
		if c.Monitoring.MetricsInterval == 0 {
			c.Monitoring.MetricsInterval = 15 * time.Second
		}

		// Security Defaults
		if c.Security.JWTExpiryHours == 0 {
			c.Security.JWTExpiryHours = 72 * time.Hour
		}
		if len(c.Security.AllowedOrigins) == 0 {
			c.Security.AllowedOrigins = []string{"*"}
		}
		if c.Security.RateLimitRequestsPerSecond == 0 {
			c.Security.RateLimitRequestsPerSecond = 100.0
		}
		if c.Security.MaxRequestBodySize == 0 {
			c.Security.MaxRequestBodySize = 32 << 20 // 32 MB
		}
	})
}

// validate performs validation on the configuration
func (c *Config) validate() error {
	if c.APIGateway.Port <= 0 || c.APIGateway.Port > 65535 {
		return errors.New("api_gateway.port must be between 1 and 65535")
	}
	if c.ModelServer.Port <= 0 || c.ModelServer.Port > 65535 {
		return errors.New("model_server.port must be between 1 and 65535")
	}
	if c.APIGateway.ReadTimeout <= 0 {
		return errors.New("api_gateway.read_timeout must be positive")
	}
	if c.APIGateway.WriteTimeout <= 0 {
		return errors.New("api_gateway.write_timeout must be positive")
	}
	if c.ModelServer.LoadTimeout <= 0 {
		return errors.New("model_server.load_timeout must be positive")
	}
	if c.ModelServer.PredictTimeout <= 0 {
		return errors.New("model_server.predict_timeout must be positive")
	}

	// Validate storage configuration
	switch c.Storage.Type {
	case "local", "s3", "gcs":
		// Valid types
	default:
		return fmt.Errorf("storage.type must be 'local', 's3', or 'gcs', got '%s'", c.Storage.Type)
	}

	// For local storage, ensure paths exist or can be created
	if c.Storage.Type == "local" {
		if err := ensureDir(c.Storage.LocalPath); err != nil {
			return fmt.Errorf("failed to create local storage path %s: %w", c.Storage.LocalPath, err)
		}
		if err := ensureDir(c.Storage.CachePath); err != nil {
			return fmt.Errorf("failed to create cache path %s: %w", c.Storage.CachePath, err)
		}
		if err := ensureDir(c.ModelServer.ModelDir); err != nil {
			return fmt.Errorf("failed to create model directory %s: %w", c.ModelServer.ModelDir, err)
		}
		if err := ensureDir(filepath.Dir(c.Logging.Filepath)); err != nil {
			return fmt.Errorf("failed to create log file directory %s: %w", filepath.Dir(c.Logging.Filepath), err)
		}
	}

	// Validate JWT secret presence when auth is enabled
	if c.Security.EnableAuth && c.Security.JWTSecret == "" {
		return errors.New("security.jwt_secret is required when enable_auth is true")
	}

	return nil
}

// ensureDir creates a directory if it doesn't exist
func ensureDir(dir string) error {
	if dir == "" {
		return nil
	}
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("cannot create directory %s: %w", dir, err)
	}
	return nil
}

// GetConfigFilePath returns the appropriate config file path based on environment
func GetConfigFilePath(basePath, environment string) string {
	if environment == "" {
		environment = getEnvironment()
	}
	return filepath.Join(basePath, fmt.Sprintf("config.%s.json", environment))
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return strings.ToLower(c.Environment) == "development"
}

// IsProduction returns true if running in production mode
func (c *Config) IsProduction() bool {
	return strings.ToLower(c.Environment) == "production"
}

// IsTesting returns true if running in testing mode
func (c *Config) IsTesting() bool {
	return strings.ToLower(c.Environment) == "testing" || strings.ToLower(c.Environment) == "test"
}

// String returns a string representation of the config (redacted for security)
func (c *Config) String() string {
	type redactedConfig struct {
		Environment string `json:"environment"`
		ServiceName string `json:"service_name"`
		APIGateway  struct {
			Host string `json:"host"`
			Port int    `json:"port"`
		} `json:"api_gateway"`
		ModelServer struct {
			Host string `json:"host"`
			Port int    `json:"port"`
		} `json:"model_server"`
		Database struct {
			Driver string `json:"driver"`
			DSN    string `json:"dsn"`
		} `json:"database"`
		Storage struct {
			Type      string `json:"type"`
			Bucket    string `json:"bucket"`
			LocalPath string `json:"local_path"`
		} `json:"storage"`
		Logging LoggingConfig `json:"logging"`
	}

	rc := redactedConfig{
		Environment: c.Environment,
		ServiceName: c.ServiceName,
	}
	rc.APIGateway.Host = c.APIGateway.Host
	rc.APIGateway.Port = c.APIGateway.Port
	rc.ModelServer.Host = c.ModelServer.Host
	rc.ModelServer.Port = c.ModelServer.Port
	rc.Database.Driver = c.Database.Driver
	rc.Database.DSN = "[REDACTED]"
	rc.Storage.Type = c.Storage.Type
	rc.Storage.Bucket = c.Storage.Bucket
	rc.Storage.LocalPath = c.Storage.LocalPath
	rc.Logging = c.Logging

	data, _ := json.MarshalIndent(rc, "", "  ")
	return string(data)
}