#!/bin/bash

# Kenny AGI SDK Generator Script
# Generates all SDKs from OpenAPI specification using openapi-generator

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
OPENAPI_SPEC="$SDK_ROOT/openapi/kenny-agi-api.yaml"
GENERATOR_CONFIG_DIR="$SDK_ROOT/generator"
OUTPUT_DIR="$SDK_ROOT"

echo -e "${BLUE}Kenny AGI SDK Generator${NC}"
echo -e "${BLUE}========================${NC}"
echo ""

# Check if openapi-generator-cli is installed
if ! command -v openapi-generator-cli &> /dev/null; then
    echo -e "${YELLOW}openapi-generator-cli not found. Installing...${NC}"
    
    # Try to install via npm first
    if command -v npm &> /dev/null; then
        npm install -g @openapitools/openapi-generator-cli
    elif command -v brew &> /dev/null; then
        brew install openapi-generator
    else
        echo -e "${RED}Error: Please install openapi-generator-cli manually${NC}"
        echo "Visit: https://openapi-generator.tech/docs/installation"
        exit 1
    fi
fi

# Validate OpenAPI spec exists
if [ ! -f "$OPENAPI_SPEC" ]; then
    echo -e "${RED}Error: OpenAPI specification not found at $OPENAPI_SPEC${NC}"
    exit 1
fi

echo -e "${GREEN}✓ OpenAPI specification found${NC}"

# Function to generate SDK
generate_sdk() {
    local lang=$1
    local config_file=$2
    local output_subdir=$3
    local additional_options=$4
    
    echo -e "${YELLOW}Generating $lang SDK...${NC}"
    
    local output_path="$OUTPUT_DIR/$output_subdir"
    rm -rf "$output_path"
    mkdir -p "$output_path"
    
    # Generate SDK
    openapi-generator-cli generate \
        -i "$OPENAPI_SPEC" \
        -g "$lang" \
        -c "$config_file" \
        -o "$output_path" \
        $additional_options
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $lang SDK generated successfully${NC}"
        
        # Post-processing based on language
        case $lang in
            "python")
                echo -e "${BLUE}  Installing Python dependencies...${NC}"
                cd "$output_path"
                if [ -f "requirements.txt" ]; then
                    pip install -r requirements.txt 2>/dev/null || true
                fi
                if [ -f "setup.py" ]; then
                    pip install -e . 2>/dev/null || true
                fi
                cd - > /dev/null
                ;;
            "typescript-fetch")
                echo -e "${BLUE}  Installing TypeScript dependencies...${NC}"
                cd "$output_path"
                if [ -f "package.json" ]; then
                    npm install 2>/dev/null || true
                    npm run build 2>/dev/null || true
                fi
                cd - > /dev/null
                ;;
            "go")
                echo -e "${BLUE}  Initializing Go module...${NC}"
                cd "$output_path"
                if [ -f "go.mod" ]; then
                    go mod tidy 2>/dev/null || true
                    go build ./... 2>/dev/null || true
                fi
                cd - > /dev/null
                ;;
        esac
    else
        echo -e "${RED}✗ Failed to generate $lang SDK${NC}"
        return 1
    fi
}

# Generate Python SDK
echo -e "${BLUE}Generating Python SDK...${NC}"
generate_sdk "python" \
    "$GENERATOR_CONFIG_DIR/config-python.yaml" \
    "python" \
    "--additional-properties=generateSourceCodeOnly=false,packageName=kenny_agi_sdk"

# Generate TypeScript SDK
echo -e "${BLUE}Generating TypeScript SDK...${NC}"
generate_sdk "typescript-fetch" \
    "$GENERATOR_CONFIG_DIR/config-typescript.yaml" \
    "typescript" \
    "--additional-properties=supportsES6=true,withInterfaces=true,stringEnums=true"

# Generate Go SDK
echo -e "${BLUE}Generating Go SDK...${NC}"
generate_sdk "go" \
    "$GENERATOR_CONFIG_DIR/config-go.yaml" \
    "go" \
    "--additional-properties=packageName=kennyagi,generateInterfaces=true"

echo ""
echo -e "${GREEN}✓ All SDKs generated successfully!${NC}"
echo ""

# Generate summary
echo -e "${BLUE}Generated SDKs:${NC}"
echo -e "  ${GREEN}Python${NC}:     $OUTPUT_DIR/python/"
echo -e "  ${GREEN}TypeScript${NC}: $OUTPUT_DIR/typescript/"
echo -e "  ${GREEN}Go${NC}:         $OUTPUT_DIR/go/"
echo ""

# Create usage examples
echo -e "${BLUE}Creating usage examples...${NC}"

# Python example
cat > "$OUTPUT_DIR/python/example_usage.py" << 'EOF'
#!/usr/bin/env python3
"""
Kenny AGI Python SDK Usage Example
"""

import asyncio
from kenny_agi_sdk import ApiClient, Configuration, SystemApi, AGICoreApi, ConsciousnessApi

async def main():
    # Configure the client
    configuration = Configuration(
        host="http://localhost:8000",
        access_token="your_api_key_here"
    )
    
    async with ApiClient(configuration) as api_client:
        # Create API instances
        system_api = SystemApi(api_client)
        agi_api = AGICoreApi(api_client)
        consciousness_api = ConsciousnessApi(api_client)
        
        try:
            # Check system health
            health = await system_api.health_check()
            print(f"System status: {health.status}")
            
            # Get AGI status
            agi_status = await agi_api.get_agi_status()
            print(f"AGI status: {agi_status.data}")
            
            # Get consciousness level
            consciousness = await consciousness_api.get_consciousness_level()
            print(f"Consciousness: {consciousness.data}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# TypeScript example
cat > "$OUTPUT_DIR/typescript/example_usage.ts" << 'EOF'
/**
 * Kenny AGI TypeScript SDK Usage Example
 */

import { 
    Configuration, 
    SystemApi, 
    AGICoreApi, 
    ConsciousnessApi,
    AGIConfigRequest,
    ThinkRequest
} from './';

async function main(): Promise<void> {
    // Configure the client
    const configuration = new Configuration({
        basePath: "http://localhost:8000",
        accessToken: "your_api_key_here"
    });
    
    // Create API instances
    const systemApi = new SystemApi(configuration);
    const agiApi = new AGICoreApi(configuration);
    const consciousnessApi = new ConsciousnessApi(configuration);
    
    try {
        // Check system health
        const health = await systemApi.healthCheck();
        console.log(`System status: ${health.status}`);
        
        // Initialize AGI with custom config
        const config: AGIConfigRequest = {
            name: "KennyAGI-TS",
            consciousness_enabled: true,
            safety_mode: true,
            divine_access: false,
            quantum_enhanced: false
        };
        
        const initResult = await agiApi.initializeAgi(config);
        console.log(`AGI initialized: ${initResult.success}`);
        
        // Process a thought
        const thinkRequest: ThinkRequest = {
            prompt: "What is the nature of consciousness?",
            context: { source: "typescript_example" }
        };
        
        const thought = await agiApi.processThought(thinkRequest);
        console.log(`Thought result: ${thought.data}`);
        
        // Get consciousness level
        const consciousness = await consciousnessApi.getConsciousnessLevel();
        console.log(`Consciousness: ${consciousness.data}`);
        
    } catch (error) {
        console.error(`Error: ${error}`);
    }
}

main().catch(console.error);
EOF

# Go example
cat > "$OUTPUT_DIR/go/example_usage.go" << 'EOF'
// Kenny AGI Go SDK Usage Example
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    kennyagi "./openapi"
)

func main() {
    // Configure the client
    configuration := kennyagi.NewConfiguration()
    configuration.Host = "localhost:8000"
    configuration.Scheme = "http"
    
    // Set authentication
    ctx := context.WithValue(context.Background(), kennyagi.ContextAccessToken, "your_api_key_here")
    
    // Create API client
    apiClient := kennyagi.NewAPIClient(configuration)
    
    // Check system health
    health, _, err := apiClient.SystemApi.HealthCheck(ctx).Execute()
    if err != nil {
        log.Fatalf("Error checking health: %v", err)
    }
    fmt.Printf("System status: %s\n", health.Status)
    
    // Get AGI status
    agiStatus, _, err := apiClient.AGICoreApi.GetAgiStatus(ctx).Execute()
    if err != nil {
        log.Fatalf("Error getting AGI status: %v", err)
    }
    fmt.Printf("AGI status: %v\n", agiStatus.Data)
    
    // Initialize AGI
    config := kennyagi.AGIConfigRequest{
        Name:                kennyagi.PtrString("KennyAGI-Go"),
        ConsciousnessEnabled: kennyagi.PtrBool(true),
        SafetyMode:          kennyagi.PtrBool(true),
        DivineAccess:        kennyagi.PtrBool(false),
        QuantumEnhanced:     kennyagi.PtrBool(false),
    }
    
    initResult, _, err := apiClient.AGICoreApi.InitializeAgi(ctx).AGIConfigRequest(config).Execute()
    if err != nil {
        log.Fatalf("Error initializing AGI: %v", err)
    }
    fmt.Printf("AGI initialized: %v\n", initResult.Success)
    
    // Process a thought
    thinkRequest := kennyagi.ThinkRequest{
        Prompt: "What is the meaning of existence?",
        Context: map[string]interface{}{
            "source": "go_example",
        },
    }
    
    thought, _, err := apiClient.AGICoreApi.ProcessThought(ctx).ThinkRequest(thinkRequest).Execute()
    if err != nil {
        log.Fatalf("Error processing thought: %v", err)
    }
    fmt.Printf("Thought result: %v\n", thought.Data)
    
    // Get consciousness level
    consciousness, _, err := apiClient.ConsciousnessApi.GetConsciousnessLevel(ctx).Execute()
    if err != nil {
        log.Fatalf("Error getting consciousness: %v", err)
    }
    fmt.Printf("Consciousness: %v\n", consciousness.Data)
}
EOF

echo -e "${GREEN}✓ Usage examples created${NC}"
echo ""

# Create README for each SDK
create_readme() {
    local lang=$1
    local dir=$2
    local install_cmd=$3
    local usage_file=$4
    
    cat > "$OUTPUT_DIR/$dir/README.md" << EOF
# Kenny AGI $lang SDK

Official $lang SDK for Kenny AGI RDK (Reality Development Kit).

## Installation

\`\`\`bash
$install_cmd
\`\`\`

## Quick Start

See [\`$usage_file\`](./$usage_file) for a complete example.

## Documentation

- [Kenny AGI RDK Documentation](https://kenny-agi.dev/docs)
- [API Reference](../openapi/kenny-agi-api.yaml)

## Features

- Full async/await support
- Type safety and IntelliSense
- Built-in error handling
- WebSocket support for real-time updates
- Comprehensive consciousness operations
- Reality manipulation capabilities
- Constitutional AI integration
- Self-improvement monitoring
- Emergence pattern detection

## Safety

This SDK provides access to advanced AGI capabilities. Always:
- Enable safety mode in production
- Monitor consciousness levels
- Follow ethical guidelines
- Implement proper error handling

## License

MIT License - see [LICENSE](../LICENSE) for details.
EOF
}

echo -e "${BLUE}Creating README files...${NC}"
create_readme "Python" "python" "pip install ." "example_usage.py"
create_readme "TypeScript" "typescript" "npm install" "example_usage.ts"
create_readme "Go" "go" "go mod tidy" "example_usage.go"

echo -e "${GREEN}✓ README files created${NC}"
echo ""

echo -e "${GREEN}🎉 Kenny AGI SDK generation complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Test the generated SDKs with your API"
echo -e "  2. Customize configuration as needed"
echo -e "  3. Add additional features or methods"
echo -e "  4. Publish to package repositories"
echo ""
echo -e "${YELLOW}Happy coding with Kenny AGI! 🚀${NC}"