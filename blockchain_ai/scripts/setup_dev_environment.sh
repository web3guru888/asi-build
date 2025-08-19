#!/bin/bash
# Kenny AGI Blockchain Audit Trail - Development Environment Setup Script

set -e  # Exit on any error

echo "🚀 Setting up Kenny AGI Blockchain Audit Trail Development Environment"
echo "=================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running on supported OS
check_os() {
    echo "Checking operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_status "Detected Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_status "Detected macOS"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Check for required system dependencies
check_dependencies() {
    echo "Checking system dependencies..."
    
    # Check for Python 3.9+
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if (( $(echo "$PYTHON_VERSION >= 3.9" | bc -l) )); then
            print_status "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.9+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found"
        exit 1
    fi
    
    # Check for Node.js and npm
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_status "Node.js $NODE_VERSION found"
    else
        print_warning "Node.js not found. Installing..."
        install_nodejs
    fi
    
    # Check for Git
    if command -v git &> /dev/null; then
        print_status "Git found"
    else
        print_error "Git not found. Please install Git."
        exit 1
    fi
    
    # Check for Docker
    if command -v docker &> /dev/null; then
        print_status "Docker found"
    else
        print_warning "Docker not found. Installing..."
        install_docker
    fi
    
    # Check for Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_status "Docker Compose found"
    else
        print_warning "Docker Compose not found. Installing..."
        install_docker_compose
    fi
}

# Install Node.js
install_nodejs() {
    if [[ "$OS" == "linux" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install node
        else
            print_error "Homebrew not found. Please install Node.js manually."
            exit 1
        fi
    fi
    
    print_status "Node.js installed"
}

# Install Docker
install_docker() {
    if [[ "$OS" == "linux" ]]; then
        # Install Docker on Linux
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        print_status "Docker installed"
        print_warning "Please log out and back in for Docker permissions to take effect"
    elif [[ "$OS" == "macos" ]]; then
        print_error "Please install Docker Desktop for Mac manually from https://docker.com"
        exit 1
    fi
}

# Install Docker Compose
install_docker_compose() {
    if [[ "$OS" == "linux" ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_status "Docker Compose installed"
    elif [[ "$OS" == "macos" ]]; then
        print_status "Docker Compose comes with Docker Desktop on macOS"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    echo "Setting up Python virtual environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_status "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip
    print_status "pip upgraded"
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Python dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi
    
    # Install development dependencies
    pip install pytest pytest-asyncio pytest-cov black flake8 isort mypy pre-commit
    print_status "Development dependencies installed"
}

# Setup Node.js environment for smart contracts
setup_nodejs_env() {
    echo "Setting up Node.js environment for smart contracts..."
    
    cd contracts
    
    # Initialize npm if package.json doesn't exist
    if [ ! -f "package.json" ]; then
        npm init -y
        print_status "npm initialized"
    fi
    
    # Install Hardhat and dependencies
    npm install --save-dev hardhat @nomiclabs/hardhat-ethers @nomiclabs/hardhat-waffle \
        ethereum-waffle chai @nomiclabs/hardhat-etherscan dotenv @openzeppelin/contracts
    
    print_status "Hardhat and smart contract dependencies installed"
    
    # Initialize Hardhat if not already done
    if [ ! -f "hardhat.config.js" ]; then
        print_warning "hardhat.config.js already exists, skipping Hardhat initialization"
    fi
    
    cd ..
}

# Setup IPFS node
setup_ipfs() {
    echo "Setting up IPFS..."
    
    # Check if IPFS is already installed
    if command -v ipfs &> /dev/null; then
        print_status "IPFS already installed"
        return
    fi
    
    # Download and install IPFS
    if [[ "$OS" == "linux" ]]; then
        wget https://dist.ipfs.io/kubo/v0.22.0/kubo_v0.22.0_linux-amd64.tar.gz
        tar -xvzf kubo_v0.22.0_linux-amd64.tar.gz
        cd kubo
        sudo bash install.sh
        cd ..
        rm -rf kubo kubo_v0.22.0_linux-amd64.tar.gz
    elif [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install ipfs
        else
            print_error "Homebrew not found. Please install IPFS manually."
            exit 1
        fi
    fi
    
    # Initialize IPFS
    ipfs init
    print_status "IPFS installed and initialized"
}

# Setup pre-commit hooks
setup_precommit() {
    echo "Setting up pre-commit hooks..."
    
    if [ -f ".pre-commit-config.yaml" ]; then
        source venv/bin/activate
        pre-commit install
        print_status "Pre-commit hooks installed"
    else
        print_warning ".pre-commit-config.yaml not found, skipping pre-commit setup"
    fi
}

# Create necessary directories
create_directories() {
    echo "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p test_results
    mkdir -p deployments
    mkdir -p artifacts
    
    print_status "Directories created"
}

# Setup environment variables
setup_env_vars() {
    echo "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Created .env from .env.example"
            print_warning "Please edit .env file with your specific configuration"
        else
            print_warning ".env.example not found, creating basic .env file"
            cat > .env << EOF
# Kenny AGI Blockchain Audit Trail Environment Variables
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Add your specific configuration here
EOF
            print_status "Basic .env file created"
        fi
    else
        print_status ".env file already exists"
    fi
}

# Start development services
start_services() {
    echo "Starting development services..."
    
    # Start Docker services
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d postgres redis ipfs
        print_status "Development services started"
        
        # Wait for services to be ready
        echo "Waiting for services to be ready..."
        sleep 10
        
        # Check service health
        if docker-compose ps | grep -q "Up"; then
            print_status "Services are running"
        else
            print_warning "Some services may not be ready yet"
        fi
    else
        print_warning "docker-compose.yml not found, skipping service startup"
    fi
}

# Run initial tests
run_initial_tests() {
    echo "Running initial tests..."
    
    source venv/bin/activate
    
    # Run basic Python tests
    if [ -d "tests" ]; then
        python -m pytest tests/unit --tb=short
        print_status "Unit tests passed"
    else
        print_warning "No tests directory found"
    fi
}

# Generate development certificates (if needed)
setup_ssl_certificates() {
    echo "Setting up SSL certificates for development..."
    
    if [ ! -d "certs" ]; then
        mkdir -p certs
        cd certs
        
        # Generate self-signed certificate for development
        openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
            -subj "/C=US/ST=State/L=City/O=Kenny-AGI/CN=localhost"
        
        cd ..
        print_status "Development SSL certificates generated"
    else
        print_status "SSL certificates already exist"
    fi
}

# Main execution
main() {
    echo "Starting Kenny AGI Blockchain Audit Trail setup..."
    echo
    
    check_os
    check_dependencies
    setup_python_env
    setup_nodejs_env
    setup_ipfs
    setup_precommit
    create_directories
    setup_env_vars
    setup_ssl_certificates
    start_services
    run_initial_tests
    
    echo
    echo "=================================================================="
    echo -e "${GREEN}✅ Development environment setup complete!${NC}"
    echo "=================================================================="
    echo
    echo "Next steps:"
    echo "1. Edit .env file with your configuration"
    echo "2. Activate the virtual environment: source venv/bin/activate"
    echo "3. Start the API server: uvicorn src.main:app --reload"
    echo "4. Access the API documentation at http://localhost:8000/docs"
    echo "5. Run tests: python scripts/test_system.py"
    echo
    echo "For smart contract development:"
    echo "1. cd contracts"
    echo "2. npx hardhat compile"
    echo "3. npx hardhat test"
    echo
    echo "Useful commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Stop services: docker-compose down"
    echo "- Restart services: docker-compose restart"
    echo
}

# Execute main function
main "$@"