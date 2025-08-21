#!/bin/bash

# ASI-Code Environment Setup Script
# This script sets up the production environment for ASI-Code

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE_FILE="$PROJECT_ROOT/.env.example"

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
SETUP_DATABASE=${SETUP_DATABASE:-true}
SETUP_REDIS=${SETUP_REDIS:-true}
SETUP_MONITORING=${SETUP_MONITORING:-true}
GENERATE_SECRETS=${GENERATE_SECRETS:-true}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate secure random string
generate_secret() {
    openssl rand -hex 32
}

# Function to generate UUID
generate_uuid() {
    if command -v uuidgen > /dev/null 2>&1; then
        uuidgen
    else
        python3 -c "import uuid; print(uuid.uuid4())"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check for required tools
    if ! command_exists openssl; then
        missing_tools+=("openssl")
    fi
    
    if ! command_exists docker; then
        missing_tools+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing_tools+=("docker-compose")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup environment file
setup_env_file() {
    print_status "Setting up environment file..."
    
    if [[ -f "$ENV_FILE" ]]; then
        print_warning "Environment file already exists at $ENV_FILE"
        read -p "Do you want to backup and recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
            print_status "Backed up existing environment file"
        else
            print_status "Keeping existing environment file"
            return
        fi
    fi
    
    # Copy example file
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    
    # Generate secrets if requested
    if [[ "$GENERATE_SECRETS" == "true" ]]; then
        print_status "Generating secure secrets..."
        
        # Generate JWT secret
        JWT_SECRET=$(generate_secret)
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" "$ENV_FILE"
        
        # Generate encryption key
        ENCRYPTION_KEY=$(generate_secret)
        sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" "$ENV_FILE"
        
        # Generate PostgreSQL password
        POSTGRES_PASSWORD=$(generate_secret)
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" "$ENV_FILE"
        
        # Generate Redis password
        REDIS_PASSWORD=$(generate_secret)
        sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" "$ENV_FILE"
        
        # Generate Grafana password
        GRAFANA_PASSWORD=$(generate_secret | cut -c1-16)  # Shorter for usability
        sed -i "s/GRAFANA_PASSWORD=.*/GRAFANA_PASSWORD=$GRAFANA_PASSWORD/" "$ENV_FILE"
        
        print_success "Generated secure secrets"
    fi
    
    # Set environment
    sed -i "s/NODE_ENV=.*/NODE_ENV=$ENVIRONMENT/" "$ENV_FILE"
    
    # Update config path based on environment
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        sed -i "s|ASI_CONFIG_PATH=.*|ASI_CONFIG_PATH=./config/staging.yml|" "$ENV_FILE"
    elif [[ "$ENVIRONMENT" == "production" ]]; then
        sed -i "s|ASI_CONFIG_PATH=.*|ASI_CONFIG_PATH=./config/production.yml|" "$ENV_FILE"
    fi
    
    print_success "Environment file created at $ENV_FILE"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    local dirs=(
        "$PROJECT_ROOT/data"
        "$PROJECT_ROOT/logs"
        "$PROJECT_ROOT/cache"
        "$PROJECT_ROOT/backups"
        "$PROJECT_ROOT/ssl"
    )
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chmod 755 "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/cache" "$PROJECT_ROOT/backups"
    chmod 700 "$PROJECT_ROOT/ssl"  # More restrictive for SSL certificates
    
    print_success "Directories created with proper permissions"
}

# Function to setup database
setup_database() {
    if [[ "$SETUP_DATABASE" != "true" ]]; then
        return
    fi
    
    print_status "Setting up database..."
    
    # Check if PostgreSQL is running
    if ! docker ps | grep -q postgres; then
        print_status "Starting PostgreSQL container..."
        docker-compose up -d postgres
        sleep 10  # Wait for PostgreSQL to start
    fi
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U asicode > /dev/null 2>&1; then
            break
        fi
        if [[ $i -eq 30 ]]; then
            print_error "PostgreSQL failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    print_success "Database setup completed"
}

# Function to setup Redis
setup_redis() {
    if [[ "$SETUP_REDIS" != "true" ]]; then
        return
    fi
    
    print_status "Setting up Redis..."
    
    # Check if Redis is running
    if ! docker ps | grep -q redis; then
        print_status "Starting Redis container..."
        docker-compose up -d redis
        sleep 5  # Wait for Redis to start
    fi
    
    # Wait for Redis to be ready
    print_status "Waiting for Redis to be ready..."
    for i in {1..15}; do
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            break
        fi
        if [[ $i -eq 15 ]]; then
            print_error "Redis failed to start within 15 seconds"
            exit 1
        fi
        sleep 1
    done
    
    print_success "Redis setup completed"
}

# Function to setup monitoring
setup_monitoring() {
    if [[ "$SETUP_MONITORING" != "true" ]]; then
        return
    fi
    
    print_status "Setting up monitoring stack..."
    
    # Start monitoring containers
    docker-compose up -d prometheus grafana loki promtail jaeger
    
    print_status "Waiting for monitoring services to start..."
    sleep 15
    
    print_success "Monitoring stack setup completed"
    print_status "Grafana will be available at http://localhost:3001"
    print_status "Prometheus will be available at http://localhost:9090"
    print_status "Jaeger will be available at http://localhost:16686"
}

# Function to setup SSL certificates (self-signed for development)
setup_ssl() {
    print_status "Setting up SSL certificates..."
    
    SSL_DIR="$PROJECT_ROOT/ssl"
    
    if [[ ! -f "$SSL_DIR/server.crt" ]] || [[ ! -f "$SSL_DIR/server.key" ]]; then
        print_status "Generating self-signed SSL certificate..."
        
        openssl req -x509 -newkey rsa:4096 -keyout "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt" \
            -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        chmod 600 "$SSL_DIR/server.key"
        chmod 644 "$SSL_DIR/server.crt"
        
        print_success "SSL certificates generated"
        print_warning "Using self-signed certificates for development. Use proper certificates in production."
    else
        print_status "SSL certificates already exist"
    fi
}

# Function to validate configuration
validate_configuration() {
    print_status "Validating configuration..."
    
    # Check if environment file exists and has required variables
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "Environment file not found at $ENV_FILE"
        exit 1
    fi
    
    # Source environment file
    source "$ENV_FILE"
    
    # Check required variables
    local required_vars=(
        "NODE_ENV"
        "JWT_SECRET"
        "ENCRYPTION_KEY"
        "DATABASE_URL"
        "REDIS_URL"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    print_success "Configuration validation passed"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check if ASI-Code application is running
    if docker-compose ps asi-code | grep -q "Up"; then
        # Try to reach health endpoint
        for i in {1..10}; do
            if curl -f http://localhost:3000/health > /dev/null 2>&1; then
                print_success "ASI-Code application health check passed"
                break
            fi
            if [[ $i -eq 10 ]]; then
                print_warning "ASI-Code application health check failed"
            fi
            sleep 2
        done
    else
        print_warning "ASI-Code application is not running"
    fi
    
    # Check database connectivity
    if docker-compose exec -T postgres pg_isready -U asicode > /dev/null 2>&1; then
        print_success "Database connectivity check passed"
    else
        print_warning "Database connectivity check failed"
    fi
    
    # Check Redis connectivity
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis connectivity check passed"
    else
        print_warning "Redis connectivity check failed"
    fi
}

# Function to display summary
display_summary() {
    print_status "Setup Summary:"
    echo "=================================="
    echo "Environment: $ENVIRONMENT"
    echo "Config file: .env"
    echo "Application URL: http://localhost:3000"
    echo "Health check: http://localhost:3000/health"
    echo "Metrics: http://localhost:9090"
    echo "Grafana: http://localhost:3001"
    echo "Jaeger: http://localhost:16686"
    echo "=================================="
    echo
    print_success "ASI-Code environment setup completed!"
    echo
    print_status "Next steps:"
    echo "1. Review and update API keys in .env file"
    echo "2. Start the application: docker-compose up -d"
    echo "3. Check logs: docker-compose logs -f asi-code"
    echo "4. Access the application at http://localhost:3000"
}

# Main function
main() {
    echo "ASI-Code Environment Setup Script"
    echo "=================================="
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-database)
                SETUP_DATABASE=false
                shift
                ;;
            --skip-redis)
                SETUP_REDIS=false
                shift
                ;;
            --skip-monitoring)
                SETUP_MONITORING=false
                shift
                ;;
            --skip-secrets)
                GENERATE_SECRETS=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --environment ENV    Set environment (development, staging, production)"
                echo "  --skip-database      Skip database setup"
                echo "  --skip-redis         Skip Redis setup"
                echo "  --skip-monitoring    Skip monitoring setup"
                echo "  --skip-secrets       Skip secret generation"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    print_status "Setting up ASI-Code for $ENVIRONMENT environment..."
    echo
    
    # Run setup steps
    check_prerequisites
    setup_env_file
    create_directories
    setup_ssl
    validate_configuration
    
    if [[ "$ENVIRONMENT" == "development" ]]; then
        setup_database
        setup_redis
        setup_monitoring
    fi
    
    run_health_checks
    display_summary
}

# Run main function with all arguments
main "$@"