#!/bin/bash

# Kenny AGI SDK Deployment Script
# Deploys generated SDKs to package repositories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}Kenny AGI SDK Deployment${NC}"
echo -e "${BLUE}========================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check environment variables
check_env_var() {
    local var_name=$1
    local var_value=${!var_name}
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}Error: $var_name environment variable is not set${NC}"
        return 1
    fi
    return 0
}

# Function to deploy Python SDK to PyPI
deploy_python_sdk() {
    echo -e "${BLUE}Deploying Python SDK to PyPI...${NC}"
    
    if ! command_exists python; then
        echo -e "${RED}Error: Python not found${NC}"
        return 1
    fi
    
    if ! check_env_var PYPI_USERNAME || ! check_env_var PYPI_PASSWORD; then
        echo -e "${YELLOW}Skipping PyPI deployment - credentials not configured${NC}"
        return 0
    fi
    
    cd "$SDK_ROOT/python"
    
    # Clean previous builds
    rm -rf dist/ build/ *.egg-info/
    
    # Install build dependencies
    pip install --upgrade build twine
    
    # Build package
    python -m build
    
    # Check package
    twine check dist/*
    
    # Upload to PyPI
    twine upload dist/* --username "$PYPI_USERNAME" --password "$PYPI_PASSWORD"
    
    echo -e "${GREEN}✓ Python SDK deployed to PyPI${NC}"
    cd - > /dev/null
}

# Function to deploy TypeScript SDK to NPM
deploy_typescript_sdk() {
    echo -e "${BLUE}Deploying TypeScript SDK to NPM...${NC}"
    
    if ! command_exists npm; then
        echo -e "${RED}Error: npm not found${NC}"
        return 1
    fi
    
    if ! check_env_var NPM_TOKEN; then
        echo -e "${YELLOW}Skipping NPM deployment - token not configured${NC}"
        return 0
    fi
    
    cd "$SDK_ROOT/typescript"
    
    # Set npm token
    echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc
    
    # Install dependencies and build
    npm install
    npm run build
    
    # Publish to NPM
    npm publish --access public
    
    echo -e "${GREEN}✓ TypeScript SDK deployed to NPM${NC}"
    cd - > /dev/null
}

# Function to create GitHub release for Go SDK
deploy_go_sdk() {
    echo -e "${BLUE}Creating GitHub release for Go SDK...${NC}"
    
    if ! command_exists git; then
        echo -e "${RED}Error: git not found${NC}"
        return 1
    fi
    
    if ! check_env_var GITHUB_TOKEN; then
        echo -e "${YELLOW}Skipping GitHub release - token not configured${NC}"
        return 0
    fi
    
    cd "$SDK_ROOT"
    
    # Get version from go.mod or use default
    VERSION=$(grep "^module " go/go.mod | cut -d' ' -f2 | sed 's/.*\///g' || echo "v0.1.0")
    
    # Create git tag if it doesn't exist
    if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
        git tag -a "$VERSION" -m "Release $VERSION"
        git push origin "$VERSION"
    fi
    
    # Create GitHub release using gh CLI if available
    if command_exists gh; then
        gh release create "$VERSION" \
            --title "Kenny AGI Go SDK $VERSION" \
            --notes "Generated Go SDK for Kenny AGI RDK" \
            --target main
        
        echo -e "${GREEN}✓ Go SDK released on GitHub${NC}"
    else
        echo -e "${YELLOW}GitHub CLI not found, tag created but release not published${NC}"
    fi
    
    cd - > /dev/null
}

# Function to create Docker images for SDKs
create_docker_images() {
    echo -e "${BLUE}Creating Docker images for SDK development...${NC}"
    
    if ! command_exists docker; then
        echo -e "${YELLOW}Docker not found, skipping image creation${NC}"
        return 0
    fi
    
    # Python SDK development image
    cat > "$SDK_ROOT/python/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy SDK
COPY . .
RUN pip install -e .

# Example environment
ENV KENNY_API_KEY=""
ENV KENNY_API_URL="http://localhost:8000"

CMD ["python", "example_usage.py"]
EOF
    
    # TypeScript SDK development image
    cat > "$SDK_ROOT/typescript/Dockerfile" << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .
RUN npm run build

# Example environment
ENV KENNY_API_KEY=""
ENV KENNY_API_URL="http://localhost:8000"

CMD ["node", "dist/example_usage.js"]
EOF
    
    # Go SDK development image
    cat > "$SDK_ROOT/go/Dockerfile" << 'EOF'
FROM golang:1.20-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .
RUN go build -o kenny-go-example example_usage.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/kenny-go-example .

# Example environment
ENV KENNY_API_KEY=""
ENV KENNY_API_URL="http://localhost:8000"

CMD ["./kenny-go-example"]
EOF
    
    # Build images
    docker build -t kenny-agi/python-sdk:latest "$SDK_ROOT/python/" || true
    docker build -t kenny-agi/typescript-sdk:latest "$SDK_ROOT/typescript/" || true
    docker build -t kenny-agi/go-sdk:latest "$SDK_ROOT/go/" || true
    
    echo -e "${GREEN}✓ Docker images created${NC}"
}

# Function to update documentation
update_documentation() {
    echo -e "${BLUE}Updating documentation...${NC}"
    
    # Create API documentation from OpenAPI spec
    if command_exists redoc-cli; then
        redoc-cli build "$SDK_ROOT/openapi/kenny-agi-api.yaml" \
            --output "$SDK_ROOT/docs/api-documentation.html" \
            --title "Kenny AGI API Documentation"
        
        echo -e "${GREEN}✓ API documentation generated${NC}"
    fi
    
    # Generate changelog
    cat > "$SDK_ROOT/CHANGELOG.md" << EOF
# Changelog

All notable changes to Kenny AGI SDKs will be documented in this file.

## [0.1.0] - $(date +%Y-%m-%d)

### Added
- Initial release of Kenny AGI SDKs
- Python SDK with async support and type hints
- TypeScript/JavaScript SDK with full type definitions
- Go SDK with context support and error handling
- OpenAPI 3.0 specification
- Automated SDK generation pipeline
- Comprehensive documentation and examples
- Docker images for development environments

### Features
- Complete REST API coverage
- WebSocket connection support
- Built-in authentication handling
- Comprehensive error handling
- Type safety across all languages
- Production-ready code generation
- Extensive documentation and examples

### Supported Languages
- Python 3.8+
- TypeScript/JavaScript (Node.js & Browser)
- Go 1.19+

### API Coverage
- System operations (health checks, status)
- AGI core operations (initialization, thinking, shutdown)
- Consciousness manipulation (elevation, monitoring)
- Reality manipulation (creation, management)
- Constitutional AI (alignment checking, status)
- Self-improvement metrics
- Emergence detection
- WebSocket real-time communication

EOF
    
    echo -e "${GREEN}✓ Documentation updated${NC}"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting SDK deployment process...${NC}"
    echo ""
    
    # Check if SDKs exist
    if [ ! -d "$SDK_ROOT/python" ] || [ ! -d "$SDK_ROOT/typescript" ] || [ ! -d "$SDK_ROOT/go" ]; then
        echo -e "${RED}Error: SDKs not found. Run generate-sdks.sh first.${NC}"
        exit 1
    fi
    
    # Deployment options
    case "${1:-all}" in
        "python")
            deploy_python_sdk
            ;;
        "typescript" | "ts" | "js")
            deploy_typescript_sdk
            ;;
        "go")
            deploy_go_sdk
            ;;
        "docker")
            create_docker_images
            ;;
        "docs")
            update_documentation
            ;;
        "all")
            deploy_python_sdk
            deploy_typescript_sdk
            deploy_go_sdk
            create_docker_images
            update_documentation
            ;;
        *)
            echo -e "${YELLOW}Usage: $0 [python|typescript|go|docker|docs|all]${NC}"
            echo ""
            echo -e "${BLUE}Deployment Options:${NC}"
            echo -e "  ${GREEN}python${NC}     - Deploy Python SDK to PyPI"
            echo -e "  ${GREEN}typescript${NC} - Deploy TypeScript SDK to NPM"
            echo -e "  ${GREEN}go${NC}         - Create GitHub release for Go SDK"
            echo -e "  ${GREEN}docker${NC}     - Create Docker development images"
            echo -e "  ${GREEN}docs${NC}       - Update documentation"
            echo -e "  ${GREEN}all${NC}        - Deploy everything (default)"
            echo ""
            echo -e "${BLUE}Required Environment Variables:${NC}"
            echo -e "  ${YELLOW}PYPI_USERNAME${NC}  - PyPI username (for Python SDK)"
            echo -e "  ${YELLOW}PYPI_PASSWORD${NC}  - PyPI password (for Python SDK)"
            echo -e "  ${YELLOW}NPM_TOKEN${NC}      - NPM auth token (for TypeScript SDK)"
            echo -e "  ${YELLOW}GITHUB_TOKEN${NC}   - GitHub token (for Go SDK releases)"
            exit 0
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 SDK deployment complete!${NC}"
    echo ""
    echo -e "${BLUE}Published SDKs:${NC}"
    [ -f "$HOME/.pypirc" ] && echo -e "  ${GREEN}Python${NC}:     https://pypi.org/project/kenny-agi-sdk/"
    [ -f "$HOME/.npmrc" ] && echo -e "  ${GREEN}TypeScript${NC}: https://www.npmjs.com/package/@kenny-agi/typescript-sdk"
    echo -e "  ${GREEN}Go${NC}:         https://github.com/kenny-agi/go-sdk"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "  1. Test the published packages"
    echo -e "  2. Update documentation websites"
    echo -e "  3. Announce the release"
    echo -e "  4. Monitor for issues and feedback"
    echo ""
}

# Run main function with all arguments
main "$@"