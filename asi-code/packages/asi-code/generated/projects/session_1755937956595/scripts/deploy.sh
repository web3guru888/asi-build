#!/bin/bash
set -e

# Configuration
PLATFORM_NAME="mlops-platform"
GO_VERSION="1.22.0"
REPO_ROOT=$(git rev-parse --show-toplevel)
BUILD_DIR="${REPO_ROOT}/build"
BIN_DIR="${BUILD_DIR}/bin"
ARTIFACTS_DIR="${BUILD_DIR}/artifacts"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
COMMIT_SHA=$(git rev-parse --short HEAD)
VERSION_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.1-dev")
GO_LDFLAGS="-X main.version=${VERSION_TAG} -X main.commit=${COMMIT_SHA} -X main.date=${TIMESTAMP}"

# Ensure build directories exist
mkdir -p ${BIN_DIR} ${ARTIFACTS_DIR}

# Color setup for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]$(date '+ %Y-%m-%d %H:%M:%S')${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]$(date '+ %Y-%m-%d %H:%M:%S')${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]$(date '+ %Y-%m-%d %H:%M:%S')${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]$(date '+ %Y-%m-%d %H:%M:%S')${NC} $1"
}

# Check required tools
check_dependencies() {
    log "Checking dependencies..."
    local missing_deps=()

    command -v go >/dev/null 2>&1 || missing_deps+=("go")
    command -v git >/dev/null 2>&1 || missing_deps+=("git")

    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        error "Please install them before proceeding."
        exit 1
    fi

    # Verify Go version
    local go_version=$(go version | awk '{print $3}' | sed 's/go//')
    if [ "$(printf '%s\n' "${GO_VERSION}" "${go_version}" | sort -V | head -n1)" = "${GO_VERSION}" ]; then
        log "Go version $go_version OK"
    else
        warn "Go version $go_version < required $GO_VERSION, proceeding anyway..."
    fi
}

# Build Go binaries
build_binaries() {
    log "Building platform binaries..."

    # Define targets with their main packages
    local targets=(
        "api:cmd/api/main.go"
        "gateway:cmd/gateway/main.go" 
        "model-server:cmd/model-server/main.go"
    )

    for target in "${targets[@]}"; do
        local binary_name=$(echo $target | cut -d':' -f1)
        local main_path=$(echo $target | cut -d':' -f2)
        
        log "Building ${binary_name}..."
        GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build \
            -ldflags="${GO_LDFLAGS}" \
            -o "${BIN_DIR}/${binary_name}" \
            "${REPO_ROOT}/${main_path}"
        
        if [ $? -ne 0 ]; then
            error "Failed to build ${binary_name}"
            exit 1
        fi
        success "Built ${binary_name} successfully"
    done
}

# Generate version manifest
generate_version_manifest() {
    log "Generating version manifest..."
    cat > ${ARTIFACTS_DIR}/version.json << EOF
{
    "platform": "${PLATFORM_NAME}",
    "version": "${VERSION_TAG}",
    "commit": "${COMMIT_SHA}",
    "build_timestamp": "${TIMESTAMP}",
    "go_version": "${GO_VERSION}",
    "components": {
        "api": {
            "binary": "api",
            "path": "${BIN_DIR}/api"
        },
        "gateway": {
            "binary": "gateway",
            "path": "${BIN_DIR}/gateway"
        },
        "model_server": {
            "binary": "model-server",
            "path": "${BIN_DIR}/model-server"
        }
    },
    "dependencies": {
        "go_mod": $(go list -m -json all | jq -s 'map({name: .Path, version: .Version, replace: if .Replace != null then .Replace.Path else null end})')
    }
}
EOF
}

# Create deployment artifacts
package_artifacts() {
    log "Creating deployment artifacts..."

    # Create platform tarball
    local tarball_name="${PLATFORM_NAME}-${VERSION_TAG}-${COMMIT_SHA}.tar.gz"
    tar -czf "${ARTIFACTS_DIR}/${tarball_name}" \
        -C "${BIN_DIR}" . \
        --transform "s,^,${PLATFORM_NAME}/bin/,"

    # Include config templates if they exist
    if [ -d "${REPO_ROOT}/configs" ]; then
        tar -rf "${ARTIFACTS_DIR}/${tarball_name%.tar.gz}.tar" \
            --transform "s,^${REPO_ROOT}/,${PLATFORM_NAME}/configs/," \
            $(find ${REPO_ROOT}/configs -type f)
        gzip "${ARTIFACTS_DIR}/${tarball_name%.tar.gz}.tar"
    fi

    success "Created artifact: ${ARTIFACTS_DIR}/${tarball_name}"
    
    # Generate SHA256 checksum
    sha256sum "${ARTIFACTS_DIR}/${tarball_name}" > "${ARTIFACTS_DIR}/${tarball_name}.sha256"
    success "Generated checksum: ${ARTIFACTS_DIR}/${tarball_name}.sha256"
}

# Validate build
validate_build() {
    log "Validating build artifacts..."

    for binary in api gateway model-server; do
        local bin_path="${BIN_DIR}/${binary}"
        if [ ! -f "${bin_path}" ]; then
            error "Missing expected binary: ${bin_path}"
            exit 1
        fi

        # Check binary is executable
        if [ ! -x "${bin_path}" ]; then
            error "Binary not executable: ${bin_path}"
            exit 1
        fi

        # Test version flag
        local version_output=$(${bin_path} -version 2>&1 || echo "error")
        if [[ "${version_output}" != *"${VERSION_TAG}"* && "${version_output}" != *"error"* ]]; then
            warn "Version flag may not be working correctly for ${binary}"
        fi

        success "Validated ${binary} binary"
    done
}

# Deployment preparation
prepare_deployment() {
    log "Preparing deployment configuration..."

    # Create deployment config directory
    local deploy_dir="${ARTIFACTS_DIR}/deployment"
    mkdir -p "${deploy_dir}/config"
    mkdir -p "${deploy_dir}/scripts"
    mkdir -p "${deploy_dir}/manifests"

    # Create basic deployment script
    cat > "${deploy_dir}/scripts/deploy-platform.sh" << 'EOF'
#!/bin/bash
set -e

# Basic deployment script
DEPLOY_DIR="/opt/mlops-platform"
VERSION="${1:-latest}"

echo "Deploying MLOps platform to ${DEPLOY_DIR}"

# Create directories
sudo mkdir -p ${DEPLOY_DIR}/{bin,config,data,logs}

# Extract binaries (expected in current directory)
sudo cp api gateway model-server ${DEPLOY_DIR}/bin/
sudo chmod +x ${DEPLOY_DIR}/bin/*

# Create systemd services
sudo tee /etc/systemd/system/mlops-api.service > /dev/null << 'UNIT'
[Unit]
Description=MLOps Platform API
After=network.target

[Service]
Type=exec
User=mlops
Group=mlops
ExecStart=/opt/mlops-platform/bin/api -config /opt/mlops-platform/config/api.yaml
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
UNIT

# Repeat for gateway and model-server services...
echo "Deployment complete. Run 'systemctl daemon-reload' to activate services."
EOF

    chmod +x "${deploy_dir}/scripts/deploy-platform.sh"
    success "Prepared deployment configuration"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    # Remove temporary files if needed
    true
}

# Signal handling
trap cleanup EXIT
trap 'error "Deployment interrupted"; exit 130' INT
trap 'error "Deployment terminated"; exit 143' TERM

# Main execution
main() {
    log "Starting deployment process for ${PLATFORM_NAME}"
    log "Version: ${VERSION_TAG}, Commit: ${COMMIT_SHA}"

    check_dependencies
    build_binaries
    generate_version_manifest
    package_artifacts
    validate_build
    prepare_deployment

    success "Deployment build completed successfully!"
    echo
    echo "Artifacts location: ${ARTIFACTS_DIR}"
    echo "Version manifest: ${ARTIFACTS_DIR}/version.json"
    echo "Binary packages: $(ls ${ARTIFACTS_DIR}/*.tar.gz)"
    echo
    success "Ready for deployment!"
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi