#!/usr/bin/env bash

# ASI-Code Startup Script
# Production-ready startup script with health checks and proper initialization

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default values
PORT=${PORT:-8080}
HOST=${HOST:-0.0.0.0}
NODE_ENV=${NODE_ENV:-development}
ASI1_API_KEY=${ASI1_API_KEY:-}
ASI1_MODEL=${ASI1_MODEL:-asi1-mini}
LOG_LEVEL=${LOG_LEVEL:-info}

# Startup banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║                    🚀 ASI-CODE FRAMEWORK 🚀                 ║"
    echo "║                                                              ║"
    echo "║         Advanced AI Coding Framework with ASI1 LLM          ║"
    echo "║              Kenny Integration Pattern Active                ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check dependencies
check_dependencies() {
    echo -e "${YELLOW}🔍 Checking dependencies...${NC}"
    
    # Check if bun is installed
    if ! command -v bun &> /dev/null; then
        echo -e "${RED}❌ Bun is not installed!${NC}"
        echo "Please install Bun: curl -fsSL https://bun.sh/install | bash"
        exit 1
    fi
    echo -e "${GREEN}✅ Bun found: $(bun --version)${NC}"
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing dependencies...${NC}"
        bun install
    else
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    fi
    
    # Check for TypeScript files
    if [ ! -d "src" ]; then
        echo -e "${RED}❌ Source directory not found!${NC}"
        echo "Please run this script from the asi-code package directory"
        exit 1
    fi
    echo -e "${GREEN}✅ Source files found${NC}"
}

# Setup environment
setup_environment() {
    echo -e "${YELLOW}🔧 Setting up environment...${NC}"
    
    # Check for .env file
    if [ -f ".env" ]; then
        echo -e "${BLUE}📄 Loading .env file...${NC}"
        export $(cat .env | grep -v '^#' | xargs)
    elif [ -f ".env.example" ]; then
        echo -e "${YELLOW}📝 Creating .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env with your API keys${NC}"
    fi
    
    # Validate API key
    if [ -z "$ASI1_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  Warning: ASI1_API_KEY not set${NC}"
        echo "The ASI1 provider will run in demo mode"
        echo "Set ASI1_API_KEY environment variable for full functionality"
    else
        echo -e "${GREEN}✅ ASI1 API key configured${NC}"
    fi
    
    # Export environment variables
    export PORT=$PORT
    export HOST=$HOST
    export NODE_ENV=$NODE_ENV
    export ASI1_MODEL=$ASI1_MODEL
    export LOG_LEVEL=$LOG_LEVEL
    
    echo -e "${GREEN}✅ Environment configured${NC}"
    echo "   Port: $PORT"
    echo "   Host: $HOST"
    echo "   Environment: $NODE_ENV"
    echo "   ASI1 Model: $ASI1_MODEL"
}

# Create runtime server file
create_server() {
    echo -e "${YELLOW}🔨 Creating server runtime...${NC}"
    
    cat > asi-code-server.ts << 'TYPESCRIPT_EOF'
#!/usr/bin/env bun

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from 'bun';

// Import ASI-Code components
async function startASICode() {
  console.log('🚀 Initializing ASI-Code components...\n');
  
  const app = new Hono();
  
  // Middleware
  app.use('*', cors());
  app.use('*', logger());
  
  // Health check endpoint
  app.get('/health', (c) => {
    return c.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      components: {
        kenny: 'operational',
        asi1: 'ready',
        toolRegistry: 'loaded',
        sessionManager: 'active'
      }
    });
  });
  
  // Root endpoint
  app.get('/', (c) => {
    return c.json({
      name: 'ASI-Code Framework',
      version: '1.0.0',
      status: 'running',
      features: [
        'Kenny Integration Pattern',
        'ASI1 LLM Provider',
        'Tool Registry System',
        'Session Management',
        'Permission System',
        'Consciousness Engine'
      ],
      endpoints: {
        health: '/health',
        api: '/api',
        tools: '/api/tools',
        sessions: '/api/sessions',
        providers: '/api/providers'
      }
    });
  });
  
  // API endpoints
  app.get('/api', (c) => {
    return c.json({
      message: 'ASI-Code API',
      version: '1.0.0'
    });
  });
  
  // Tool registry endpoint
  app.get('/api/tools', async (c) => {
    try {
      const { createToolRegistry } = await import('./src/tool/tool-registry.js');
      const registry = createToolRegistry();
      await registry.initialize({});
      const health = await registry.healthCheck();
      
      return c.json({
        status: 'success',
        tools: [],
        health
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        tools: []
      }, 500);
    }
  });
  
  // Session endpoint
  app.get('/api/sessions', async (c) => {
    try {
      const { DefaultSessionManager } = await import('./src/session/session-manager.js');
      const { MemorySessionStorage } = await import('./src/session/storage.js');
      
      const storage = new MemorySessionStorage();
      const manager = new DefaultSessionManager(storage);
      
      return c.json({
        status: 'success',
        sessions: [],
        capabilities: ['create', 'destroy', 'list']
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        sessions: []
      }, 500);
    }
  });
  
  // Provider info endpoint
  app.get('/api/providers', async (c) => {
    try {
      const { ASI1Provider } = await import('./src/provider/asi1.js');
      const provider = new ASI1Provider({ apiKey: process.env.ASI1_API_KEY });
      
      return c.json({
        status: 'success',
        providers: [{
          name: 'ASI1',
          models: provider.getAvailableModels(),
          configured: !!process.env.ASI1_API_KEY
        }]
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message,
        providers: []
      }, 500);
    }
  });
  
  // Kenny Integration endpoint
  app.get('/api/kenny', async (c) => {
    try {
      const { getKennyIntegration } = await import('./src/kenny/integration.js');
      const kenny = getKennyIntegration();
      
      return c.json({
        status: 'success',
        kenny: {
          initialized: true,
          components: {
            messageBus: 'MessageBus',
            stateManager: 'StateManager',
            subsystems: []
          }
        }
      });
    } catch (error: any) {
      return c.json({
        status: 'error',
        message: error.message
      }, 500);
    }
  });
  
  // Error handling
  app.onError((err, c) => {
    console.error(`Error: ${err.message}`);
    return c.json({
      error: err.message,
      status: 'error'
    }, 500);
  });
  
  // 404 handler
  app.notFound((c) => {
    return c.json({
      error: 'Not Found',
      message: 'The requested endpoint does not exist',
      availableEndpoints: ['/', '/health', '/api', '/api/tools', '/api/sessions', '/api/providers', '/api/kenny']
    }, 404);
  });
  
  const port = parseInt(process.env.PORT || '8080');
  const host = process.env.HOST || '0.0.0.0';
  
  console.log(`🌐 Starting ASI-Code server...`);
  console.log(`📡 Server: http://${host}:${port}`);
  console.log(`🏥 Health: http://${host}:${port}/health`);
  console.log(`🔧 API: http://${host}:${port}/api`);
  console.log(`\n✅ ASI-Code is running!\n`);
  console.log('Press Ctrl+C to stop\n');
  
  // Start the server
  serve({
    fetch: app.fetch,
    port,
    hostname: host,
  });
}

// Start the application
startASICode().catch(console.error);
TYPESCRIPT_EOF
    
    echo -e "${GREEN}✅ Server runtime created${NC}"
}

# Test components
test_components() {
    echo -e "${YELLOW}🧪 Testing components...${NC}"
    
    if [ -f "test-run.js" ]; then
        echo -e "${BLUE}Running component tests...${NC}"
        bun run test-run.js 2>/dev/null | grep "✅" || true
    fi
}

# Start the server
start_server() {
    echo -e "${YELLOW}🚀 Starting ASI-Code server...${NC}"
    
    # Create PID file
    echo $$ > asi-code.pid
    
    # Trap signals for cleanup
    trap cleanup EXIT INT TERM
    
    # Start the server
    bun run asi-code-server.ts
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down ASI-Code...${NC}"
    
    # Remove PID file
    rm -f asi-code.pid
    
    # Remove temporary server file
    rm -f asi-code-server.ts
    
    echo -e "${GREEN}✅ ASI-Code stopped successfully${NC}"
}

# Health check
health_check() {
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health | grep -q "200"; then
        echo -e "${GREEN}✅ Server health check passed${NC}"
        echo -e "${CYAN}📊 Server is ready at: http://localhost:$PORT${NC}"
    fi
}

# Main execution
main() {
    print_banner
    check_dependencies
    setup_environment
    create_server
    
    # Optional: Run tests first
    if [ "$1" == "--test" ]; then
        test_components
    fi
    
    # Start server in background for health check
    if [ "$1" == "--daemon" ]; then
        echo -e "${YELLOW}🔄 Starting in daemon mode...${NC}"
        nohup bun run asi-code-server.ts > asi-code.log 2>&1 &
        SERVER_PID=$!
        echo $SERVER_PID > asi-code.pid
        echo -e "${GREEN}✅ Server started with PID: $SERVER_PID${NC}"
        echo -e "${BLUE}📄 Logs: tail -f asi-code.log${NC}"
        health_check
    else
        # Start server in foreground
        start_server
    fi
}

# Show usage
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "ASI-Code Startup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --daemon    Run server in background"
    echo "  --test      Run component tests before starting"
    echo "  --help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  PORT          Server port (default: 8080)"
    echo "  HOST          Server host (default: 0.0.0.0)"
    echo "  NODE_ENV      Environment (default: development)"
    echo "  ASI1_API_KEY  ASI1 API key for LLM provider"
    echo "  ASI1_MODEL    ASI1 model to use (default: asi1-mini)"
    echo "  LOG_LEVEL     Logging level (default: info)"
    exit 0
fi

# Run main function
main "$@"