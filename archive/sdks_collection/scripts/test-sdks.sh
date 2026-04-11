#!/bin/bash

# Kenny AGI SDK Testing Script
# Comprehensive testing for all generated SDKs

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
TEST_RESULTS_DIR="$SDK_ROOT/test-results"

# Test configuration
KENNY_API_URL="${KENNY_API_URL:-http://localhost:8000}"
KENNY_API_KEY="${KENNY_API_KEY:-test_api_key_123}"

echo -e "${BLUE}Kenny AGI SDK Testing Suite${NC}"
echo -e "${BLUE}============================${NC}"
echo ""

# Create test results directory
mkdir -p "$TEST_RESULTS_DIR"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if API server is running
check_api_server() {
    echo -e "${BLUE}Checking Kenny AGI API server...${NC}"
    
    if curl -s --fail "$KENNY_API_URL/health" >/dev/null; then
        echo -e "${GREEN}✓ API server is running at $KENNY_API_URL${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ API server not available at $KENNY_API_URL${NC}"
        echo -e "${YELLOW}Starting mock API server for testing...${NC}"
        start_mock_server
        return $?
    fi
}

# Function to start mock API server for testing
start_mock_server() {
    cat > "$TEST_RESULTS_DIR/mock_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Mock Kenny AGI API Server for SDK Testing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import json

app = FastAPI(title="Mock Kenny AGI API", version="0.1.0-test")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "Kenny AGI RDK API",
        "version": "0.1.0-alpha",
        "status": "operational",
        "endpoints": {"docs": "/docs", "health": "/health"}
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {"api": "operational", "agi": "ready"}
    }

@app.get("/api/v1/agi/status")
async def get_agi_status():
    return {
        "success": True,
        "message": "AGI status retrieved",
        "data": {
            "status": "ready",
            "modules": {"consciousness": "active", "reality": "stable"},
            "performance": {"cpu_usage": 45.2, "memory_usage": 67.8}
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/agi/initialize")
async def initialize_agi(config: dict):
    return {
        "success": True,
        "message": "AGI initialized successfully",
        "data": {"status": "initialized", "config": config},
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/agi/think")
async def process_thought(request: dict):
    return {
        "success": True,
        "message": "Thought processed",
        "data": {
            "prompt": request.get("prompt", ""),
            "response": "This is a mock response to: " + request.get("prompt", ""),
            "processing_time": 0.123
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/consciousness/level")
async def get_consciousness_level():
    return {
        "success": True,
        "message": "Consciousness level retrieved",
        "data": {
            "level": "ENLIGHTENED",
            "value": 75.5,
            "active": True
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
EOF

    # Start mock server in background
    python3 "$TEST_RESULTS_DIR/mock_server.py" > "$TEST_RESULTS_DIR/mock_server.log" 2>&1 &
    MOCK_SERVER_PID=$!
    echo $MOCK_SERVER_PID > "$TEST_RESULTS_DIR/mock_server.pid"
    
    # Wait for server to start
    sleep 3
    
    if curl -s --fail "$KENNY_API_URL/health" >/dev/null; then
        echo -e "${GREEN}✓ Mock API server started successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to start mock API server${NC}"
        return 1
    fi
}

# Function to stop mock server
stop_mock_server() {
    if [ -f "$TEST_RESULTS_DIR/mock_server.pid" ]; then
        PID=$(cat "$TEST_RESULTS_DIR/mock_server.pid")
        if ps -p "$PID" > /dev/null; then
            kill "$PID"
            echo -e "${BLUE}Mock server stopped${NC}"
        fi
        rm -f "$TEST_RESULTS_DIR/mock_server.pid"
    fi
}

# Function to test Python SDK
test_python_sdk() {
    echo -e "${BLUE}Testing Python SDK...${NC}"
    
    if [ ! -d "$SDK_ROOT/python" ]; then
        echo -e "${RED}✗ Python SDK not found${NC}"
        return 1
    fi
    
    if ! command_exists python3; then
        echo -e "${RED}✗ Python 3 not found${NC}"
        return 1
    fi
    
    cd "$SDK_ROOT/python"
    
    # Install SDK
    pip3 install -e . > "$TEST_RESULTS_DIR/python_install.log" 2>&1
    
    # Create test script
    cat > test_sdk.py << EOF
#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, '.')

try:
    from kenny_agi_sdk import ApiClient, Configuration
    from kenny_agi_sdk.kenny_agi_sdk.api.system_api import SystemApi
    from kenny_agi_sdk.kenny_agi_sdk.api.agi_core_api import AGICoreApi
    from kenny_agi_sdk.kenny_agi_sdk.api.consciousness_api import ConsciousnessApi
    from kenny_agi_sdk.kenny_agi_sdk.models.agi_config_request import AGIConfigRequest
    from kenny_agi_sdk.kenny_agi_sdk.models.think_request import ThinkRequest
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def test_python_sdk():
    try:
        # Configure client
        configuration = Configuration(
            host="$KENNY_API_URL",
            access_token="$KENNY_API_KEY"
        )
        
        async with ApiClient(configuration) as api_client:
            # Test System API
            system_api = SystemApi(api_client)
            health = await system_api.health_check()
            print(f"Health check: {health.status}")
            
            # Test AGI Core API
            agi_api = AGICoreApi(api_client)
            status = await agi_api.get_agi_status()
            print(f"AGI status: {status.success}")
            
            # Test initialization
            config = AGIConfigRequest(
                name="TestAGI",
                consciousness_enabled=True,
                safety_mode=True
            )
            init_result = await agi_api.initialize_agi(config)
            print(f"AGI init: {init_result.success}")
            
            # Test thinking
            think_request = ThinkRequest(
                prompt="Test prompt",
                context={"test": True}
            )
            thought = await agi_api.process_thought(think_request)
            print(f"Thought processing: {thought.success}")
            
            # Test Consciousness API
            consciousness_api = ConsciousnessApi(api_client)
            level = await consciousness_api.get_consciousness_level()
            print(f"Consciousness level: {level.success}")
            
        print("✓ Python SDK test passed")
        return True
        
    except Exception as e:
        print(f"✗ Python SDK test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_python_sdk())
    sys.exit(0 if result else 1)
EOF
    
    # Run test
    if python3 test_sdk.py > "$TEST_RESULTS_DIR/python_test.log" 2>&1; then
        echo -e "${GREEN}✓ Python SDK test passed${NC}"
        PYTHON_TEST_RESULT="PASS"
    else
        echo -e "${RED}✗ Python SDK test failed${NC}"
        echo -e "${YELLOW}Check $TEST_RESULTS_DIR/python_test.log for details${NC}"
        PYTHON_TEST_RESULT="FAIL"
    fi
    
    cd - > /dev/null
}

# Function to test TypeScript SDK
test_typescript_sdk() {
    echo -e "${BLUE}Testing TypeScript SDK...${NC}"
    
    if [ ! -d "$SDK_ROOT/typescript" ]; then
        echo -e "${RED}✗ TypeScript SDK not found${NC}"
        return 1
    fi
    
    if ! command_exists npm; then
        echo -e "${RED}✗ npm not found${NC}"
        return 1
    fi
    
    cd "$SDK_ROOT/typescript"
    
    # Install dependencies and build
    npm install > "$TEST_RESULTS_DIR/typescript_install.log" 2>&1
    npm run build >> "$TEST_RESULTS_DIR/typescript_install.log" 2>&1
    
    # Create test script
    cat > test_sdk.js << EOF
const { 
    Configuration, 
    SystemApi, 
    AGICoreApi, 
    ConsciousnessApi 
} = require('./dist/index.js');

async function testTypeScriptSDK() {
    try {
        // Configure client
        const config = new Configuration({
            basePath: "$KENNY_API_URL",
            accessToken: "$KENNY_API_KEY"
        });
        
        // Test System API
        const systemApi = new SystemApi(config);
        const health = await systemApi.healthCheck();
        console.log(\`Health check: \${health.status}\`);
        
        // Test AGI Core API  
        const agiApi = new AGICoreApi(config);
        const status = await agiApi.getAgiStatus();
        console.log(\`AGI status: \${status.success}\`);
        
        // Test initialization
        const initConfig = {
            name: "TestAGI",
            consciousness_enabled: true,
            safety_mode: true
        };
        const initResult = await agiApi.initializeAgi(initConfig);
        console.log(\`AGI init: \${initResult.success}\`);
        
        // Test thinking
        const thinkRequest = {
            prompt: "Test prompt",
            context: { test: true }
        };
        const thought = await agiApi.processThought(thinkRequest);
        console.log(\`Thought processing: \${thought.success}\`);
        
        // Test Consciousness API
        const consciousnessApi = new ConsciousnessApi(config);
        const level = await consciousnessApi.getConsciousnessLevel();
        console.log(\`Consciousness level: \${level.success}\`);
        
        console.log("✓ TypeScript SDK test passed");
        return true;
        
    } catch (error) {
        console.log(\`✗ TypeScript SDK test failed: \${error.message}\`);
        return false;
    }
}

testTypeScriptSDK().then(success => {
    process.exit(success ? 0 : 1);
});
EOF
    
    # Run test
    if node test_sdk.js > "$TEST_RESULTS_DIR/typescript_test.log" 2>&1; then
        echo -e "${GREEN}✓ TypeScript SDK test passed${NC}"
        TYPESCRIPT_TEST_RESULT="PASS"
    else
        echo -e "${RED}✗ TypeScript SDK test failed${NC}"
        echo -e "${YELLOW}Check $TEST_RESULTS_DIR/typescript_test.log for details${NC}"
        TYPESCRIPT_TEST_RESULT="FAIL"
    fi
    
    cd - > /dev/null
}

# Function to test Go SDK
test_go_sdk() {
    echo -e "${BLUE}Testing Go SDK...${NC}"
    
    if [ ! -d "$SDK_ROOT/go" ]; then
        echo -e "${RED}✗ Go SDK not found${NC}"
        return 1
    fi
    
    if ! command_exists go; then
        echo -e "${RED}✗ Go not found${NC}"
        return 1
    fi
    
    cd "$SDK_ROOT/go"
    
    # Initialize module and install dependencies
    go mod tidy > "$TEST_RESULTS_DIR/go_install.log" 2>&1
    
    # Create test script
    cat > test_sdk.go << EOF
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "strings"
    
    kennyagi "./openapi"
)

func main() {
    // Configure client
    config := kennyagi.NewConfiguration()
    
    // Parse URL
    apiURL := "$KENNY_API_URL"
    if strings.HasPrefix(apiURL, "http://") {
        config.Scheme = "http"
        config.Host = strings.TrimPrefix(apiURL, "http://")
    } else if strings.HasPrefix(apiURL, "https://") {
        config.Scheme = "https"
        config.Host = strings.TrimPrefix(apiURL, "https://")
    }
    
    client := kennyagi.NewAPIClient(config)
    ctx := context.WithValue(
        context.Background(),
        kennyagi.ContextAccessToken,
        "$KENNY_API_KEY",
    )
    
    // Test System API
    health, _, err := client.SystemApi.HealthCheck(ctx).Execute()
    if err != nil {
        log.Printf("Health check failed: %v", err)
        os.Exit(1)
    }
    fmt.Printf("Health check: %s\\n", health.Status)
    
    // Test AGI Core API
    status, _, err := client.AGICoreApi.GetAgiStatus(ctx).Execute()
    if err != nil {
        log.Printf("AGI status failed: %v", err)
        os.Exit(1)
    }
    fmt.Printf("AGI status: %v\\n", status.Success)
    
    // Test initialization
    initConfig := kennyagi.AGIConfigRequest{
        Name:                kennyagi.PtrString("TestAGI"),
        ConsciousnessEnabled: kennyagi.PtrBool(true),
        SafetyMode:          kennyagi.PtrBool(true),
    }
    initResult, _, err := client.AGICoreApi.InitializeAgi(ctx).AGIConfigRequest(initConfig).Execute()
    if err != nil {
        log.Printf("AGI init failed: %v", err)
        os.Exit(1)
    }
    fmt.Printf("AGI init: %v\\n", initResult.Success)
    
    // Test thinking
    thinkRequest := kennyagi.ThinkRequest{
        Prompt: "Test prompt",
        Context: map[string]interface{}{"test": true},
    }
    thought, _, err := client.AGICoreApi.ProcessThought(ctx).ThinkRequest(thinkRequest).Execute()
    if err != nil {
        log.Printf("Thought processing failed: %v", err)
        os.Exit(1)
    }
    fmt.Printf("Thought processing: %v\\n", thought.Success)
    
    // Test Consciousness API
    level, _, err := client.ConsciousnessApi.GetConsciousnessLevel(ctx).Execute()
    if err != nil {
        log.Printf("Consciousness level failed: %v", err)
        os.Exit(1)
    }
    fmt.Printf("Consciousness level: %v\\n", level.Success)
    
    fmt.Println("✓ Go SDK test passed")
}
EOF
    
    # Run test
    if go run test_sdk.go > "$TEST_RESULTS_DIR/go_test.log" 2>&1; then
        echo -e "${GREEN}✓ Go SDK test passed${NC}"
        GO_TEST_RESULT="PASS"
    else
        echo -e "${RED}✗ Go SDK test failed${NC}"
        echo -e "${YELLOW}Check $TEST_RESULTS_DIR/go_test.log for details${NC}"
        GO_TEST_RESULT="FAIL"
    fi
    
    cd - > /dev/null
}

# Function to generate test report
generate_test_report() {
    echo -e "${BLUE}Generating test report...${NC}"
    
    cat > "$TEST_RESULTS_DIR/test_report.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Kenny AGI SDK Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2196F3; color: white; padding: 20px; margin-bottom: 20px; }
        .result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .pass { background: #4CAF50; color: white; }
        .fail { background: #F44336; color: white; }
        .info { background: #FFC107; color: black; }
        .section { margin: 20px 0; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Kenny AGI SDK Test Report</h1>
        <p>Generated on: $(date)</p>
        <p>API Endpoint: $KENNY_API_URL</p>
    </div>
    
    <div class="section">
        <h2>Test Results Summary</h2>
        <div class="result ${PYTHON_TEST_RESULT,,}">Python SDK: $PYTHON_TEST_RESULT</div>
        <div class="result ${TYPESCRIPT_TEST_RESULT,,}">TypeScript SDK: $TYPESCRIPT_TEST_RESULT</div>
        <div class="result ${GO_TEST_RESULT,,}">Go SDK: $GO_TEST_RESULT</div>
    </div>
    
    <div class="section">
        <h2>Test Details</h2>
        
        <h3>Python SDK Test Output</h3>
        <pre>$(cat "$TEST_RESULTS_DIR/python_test.log" 2>/dev/null || echo "No output")</pre>
        
        <h3>TypeScript SDK Test Output</h3>
        <pre>$(cat "$TEST_RESULTS_DIR/typescript_test.log" 2>/dev/null || echo "No output")</pre>
        
        <h3>Go SDK Test Output</h3>
        <pre>$(cat "$TEST_RESULTS_DIR/go_test.log" 2>/dev/null || echo "No output")</pre>
    </div>
    
    <div class="section">
        <h2>Environment Information</h2>
        <pre>
OS: $(uname -a)
Python: $(python3 --version 2>/dev/null || echo "Not installed")
Node.js: $(node --version 2>/dev/null || echo "Not installed")
npm: $(npm --version 2>/dev/null || echo "Not installed")
Go: $(go version 2>/dev/null || echo "Not installed")
        </pre>
    </div>
</body>
</html>
EOF
    
    echo -e "${GREEN}✓ Test report generated: $TEST_RESULTS_DIR/test_report.html${NC}"
}

# Cleanup function
cleanup() {
    echo -e "${BLUE}Cleaning up...${NC}"
    stop_mock_server
    
    # Clean test files
    [ -f "$SDK_ROOT/python/test_sdk.py" ] && rm -f "$SDK_ROOT/python/test_sdk.py"
    [ -f "$SDK_ROOT/typescript/test_sdk.js" ] && rm -f "$SDK_ROOT/typescript/test_sdk.js"
    [ -f "$SDK_ROOT/go/test_sdk.go" ] && rm -f "$SDK_ROOT/go/test_sdk.go"
}

# Trap cleanup on exit
trap cleanup EXIT

# Main testing function
main() {
    echo -e "${BLUE}Starting SDK testing...${NC}"
    echo ""
    
    # Initialize test results
    PYTHON_TEST_RESULT="SKIP"
    TYPESCRIPT_TEST_RESULT="SKIP"
    GO_TEST_RESULT="SKIP"
    
    # Check API server
    if ! check_api_server; then
        echo -e "${RED}Cannot proceed without API server${NC}"
        exit 1
    fi
    
    # Run tests based on arguments
    case "${1:-all}" in
        "python")
            test_python_sdk
            ;;
        "typescript" | "ts")
            test_typescript_sdk
            ;;
        "go")
            test_go_sdk
            ;;
        "all")
            test_python_sdk
            test_typescript_sdk
            test_go_sdk
            ;;
        *)
            echo -e "${YELLOW}Usage: $0 [python|typescript|go|all]${NC}"
            exit 0
            ;;
    esac
    
    # Generate report
    generate_test_report
    
    # Summary
    echo ""
    echo -e "${BLUE}Test Summary:${NC}"
    echo -e "  Python SDK:     $PYTHON_TEST_RESULT"
    echo -e "  TypeScript SDK: $TYPESCRIPT_TEST_RESULT"
    echo -e "  Go SDK:         $GO_TEST_RESULT"
    echo ""
    echo -e "${BLUE}Test artifacts saved to: $TEST_RESULTS_DIR${NC}"
    
    # Exit with appropriate code
    if [[ "$PYTHON_TEST_RESULT" == "FAIL" ]] || [[ "$TYPESCRIPT_TEST_RESULT" == "FAIL" ]] || [[ "$GO_TEST_RESULT" == "FAIL" ]]; then
        echo -e "${RED}Some tests failed${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

# Run main function
main "$@"