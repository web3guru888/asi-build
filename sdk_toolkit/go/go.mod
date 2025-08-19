module github.com/kenny-agi/rdk/sdk/go

go 1.21

require (
	github.com/gorilla/websocket v1.5.1
	golang.org/x/net v0.17.0 // indirect
)

require (
	github.com/stretchr/testify v1.8.4 // for testing
	github.com/google/uuid v1.3.1 // for unique identifiers
)

require (
	github.com/davecgh/go-spew v1.1.1 // indirect
	github.com/pmezard/go-difflib v1.0.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)

// Optional dependencies for advanced features
require (
	github.com/prometheus/client_golang v1.16.0 // metrics
	github.com/sirupsen/logrus v1.9.3 // structured logging
	go.opentelemetry.io/otel v1.16.0 // observability
	go.opentelemetry.io/otel/trace v1.16.0 // tracing
)

// For high-performance JSON operations
require (
	github.com/json-iterator/go v1.1.12
	github.com/modern-go/concurrent v0.0.0-20180228061459-e0a39a4cb421 // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
)

// For configuration management
require (
	github.com/spf13/viper v1.16.0
	github.com/spf13/pflag v1.0.5
)

// Development and testing dependencies
require (
	github.com/golang/mock v1.6.0
	github.com/onsi/ginkgo/v2 v2.11.0
	github.com/onsi/gomega v1.27.8
)

// Optional: Rate limiting
require (
	golang.org/x/time v0.3.0
)

// Optional: Circuit breaker pattern
require (
	github.com/sony/gobreaker v0.5.0
)

// Optional: Retry mechanisms
require (
	github.com/cenkalti/backoff/v4 v4.2.1
)

// Replace with local development if needed
// replace github.com/kenny-agi/rdk/sdk/go => ./

retract (
	v0.1.0 // Contains security vulnerability
	v0.2.0 // Breaking API changes
)