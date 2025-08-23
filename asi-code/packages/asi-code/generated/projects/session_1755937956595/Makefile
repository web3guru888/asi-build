# Makefile

```Makefile
# MLOps Platform Makefile
# Language: Go
# Framework: Standard
# Components: API Gateway, Model Server

# Variables
GO := go
GOMOD := $(GO) mod
GOBUILD := $(GO) build
GOTEST := $(GO) test
GOVET := $(GO) vet
GOFMT := gofmt
GOIMPORTS := goimports
BINARY := mlops-platform
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DATE := $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')
LDFLAGS := -X main.version=$(VERSION) -X main.commit=$(COMMIT) -X main.date=$(DATE)

# Directories
CMD_DIR := cmd
API_DIR := cmd/api
GATEWAY_DIR := cmd/gateway
MODEL_SERVER_DIR := cmd/model-server
INTERNAL_DIR := internal
CONFIG_DIR := internal/config

# Binaries
API_BINARY := $(BINARY)-api
GATEWAY_BINARY := $(BINARY)-gateway
MODEL_SERVER_BINARY := $(BINARY)-model-server

# Files
GO_FILES := $(shell find . -name "*.go" -type f | grep -v "vendor/")
GO_MOD_FILES := go.mod go.sum

# Platforms
PLATFORMS := linux/amd64 linux/arm64 windows/amd64 darwin/amd64 darwin/arm64

# Default target
.PHONY: all
all: fmt vet build

# Dependencies
.PHONY: deps
deps:
	$(GOMOD) tidy
	$(GOMOD) download

# Format code
.PHONY: fmt
fmt:
	$(GOFMT) -s -w $(GO_FILES)
	$(GOIMPORTS) -w $(GO_FILES)

# Vet code
.PHONY: vet
vet:
	$(GOVET) ./...

# Run tests
.PHONY: test
test:
	$(GOTEST) -race -coverprofile=coverage.txt -covermode=atomic ./...

# Run tests with verbose output
.PHONY: test-verbose
test-verbose:
	$(GOTEST) -v -race -coverprofile=coverage.txt -covermode=atomic ./...

# Build all components
.PHONY: build
build: build-api build-gateway build-model-server

# Build API service
.PHONY: build-api
build-api:
	$(GOBUILD) -ldflags "$(LDFLAGS)" -o bin/$(API_BINARY) $(API_DIR)/main.go

# Build Gateway service
.PHONY: build-gateway
build-gateway:
	$(GOBUILD) -ldflags "$(LDFLAGS)" -o bin/$(GATEWAY_BINARY) $(GATEWAY_DIR)/main.go

# Build Model Server service
.PHONY: build-model-server
build-model-server:
	$(GOBUILD) -ldflags "$(LDFLAGS)" -o bin/$(MODEL_SERVER_BINARY) $(MODEL_SERVER_DIR)/main.go

# Cross-compile for all platforms
.PHONY: build-all
build-all:
	@echo "Building for all platforms..."
	@for platform in $(PLATFORMS); do \
		platform_split=($${platform//\// }); \
		GOOS=$${platform_split[0]} GOARCH=$${platform_split[1]} CGO_ENABLED=0 \
		$(GOBUILD) -ldflags "$(LDFLAGS)" -o bin/$(BINARY)-$${GOOS}-$${GOARCH} $(API_DIR)/main.go; \
	done

# Clean build artifacts
.PHONY: clean
clean:
	rm -rf bin/
	rm -f coverage.txt
	rm -f *.prof

# Create necessary directories
.PHONY: mkdirs
mkdirs:
	mkdir -p bin
	mkdir -p logs
	mkdir -p data/models
	mkdir -p config

# Run API service locally
.PHONY: run-api
run-api: mkdirs
	$(GOBUILD) -o bin/$(API_BINARY) $(API_DIR)/main.go
	./bin/$(API_BINARY)

# Run Gateway service locally
.PHONY: run-gateway
run-gateway: mkdirs
	$(GOBUILD) -o bin/$(GATEWAY_BINARY) $(GATEWAY_DIR)/main.go
	./bin/$(GATEWAY_BINARY)

# Run Model Server service locally
.PHONY: run-model-server
run-model-server: mkdirs
	$(GOBUILD) -o bin/$(MODEL_SERVER_BINARY) $(MODEL_SERVER_DIR)/main.go
	./bin/$(MODEL_SERVER_BINARY)

# Run complete platform locally (in parallel)
.PHONY: run
run: mkdirs
	@echo "Starting MLOps Platform services..."
	@$(GOBUILD) -o bin/$(API_BINARY) $(API_DIR)/main.go &
	@$(GOBUILD) -o bin/$(GATEWAY_BINARY) $(GATEWAY_DIR)/main.go &
	@$(GOBUILD) -o bin/$(MODEL_SERVER_BINARY) $(MODEL_SERVER_DIR)/main.go &
	@echo "All services started. Use 'make stop' to stop them."
	@echo "API: http://localhost:8080"
	@echo "Gateway: http://localhost:8081"
	@echo "Model Server: http://localhost:8082"

# Stop running platform services
.PHONY: stop
stop:
	@echo "Stopping MLOps Platform services..."
	@pkill -f $(API_BINARY) || true
	@pkill -f $(GATEWAY_BINARY) || true
	@pkill -f $(MODEL_SERVER_BINARY) || true
	@echo "Services stopped."

# Generate documentation
.PHONY: docs
docs:
	@echo "Generating documentation..."
	@$(GO) doc ./... > DOCUMENTATION.md

# Check if go.mod files are updated
.PHONY: check-mod
check-mod:
	@echo "Checking go.mod files..."
	@$(GOMOD) tidy -n

# Update go.mod files
.PHONY: update-mod
update-mod:
	@echo "Updating go.mod files..."
	@$(GOMOD) tidy

# Generate mocks for interfaces (assuming mockery is installed)
.PHONY: mock
mock:
	@echo "Generating mocks..."
	@mockery --all --dir=./$(INTERNAL_DIR) --output=./internal/mocks

# Show version information
.PHONY: version
version:
	@echo "Version: $(VERSION)"
	@echo "Commit: $(COMMIT)"
	@echo "Build Date: $(DATE)"

# Show help
.PHONY: help
help:
	@echo "MLOps Platform Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make deps          Install dependencies"
	@echo "  make fmt           Format code"
	@echo "  make vet           Vet code"
	@echo "  make test          Run tests"
	@echo "  make test-verbose  Run tests with verbose output"
	@echo "  make build         Build all components"
	@echo "  make build-api     Build API service"
	@echo "  make build-gateway Build Gateway service"
	@echo "  make build-model-server Build Model Server service"
	@echo "  make build-all     Cross-compile for all platforms"
	@echo "  make run           Run complete platform locally"
	@echo "  make run-api       Run API service locally"
	@echo "  make run-gateway   Run Gateway service locally"
	@echo "  make run-model-server Run Model Server service locally"
	@echo "  make stop          Stop running platform services"
	@echo "  make clean         Clean build artifacts"
	@echo "  make mkdirs        Create necessary directories"
	@echo "  make docs          Generate documentation"
	@echo "  make check-mod     Check if go.mod files are updated"
	@echo "  make update-mod    Update go.mod files"
	@echo "  make mock          Generate mocks for interfaces"
	@echo "  make version       Show version information"
	@echo "  make help          Show this help message"

# Default help target
.PHONY: default
default: help
```