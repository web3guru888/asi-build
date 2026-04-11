# Kenny AGI SDK Generator

This directory contains the complete SDK generator system for Kenny AGI RDK (Reality Development Kit), providing automated generation of client libraries for multiple programming languages.

## 🎯 Overview

The Kenny AGI SDK Generator creates production-ready Software Development Kits (SDKs) from the OpenAPI 3.0 specification, enabling developers to integrate Kenny AGI capabilities into their applications using native language paradigms.

## 📁 Directory Structure

```
sdks/
├── openapi/                    # OpenAPI specifications
│   └── kenny-agi-api.yaml      # Complete API specification
├── generator/                  # Generator configurations
│   ├── config-python.yaml     # Python SDK configuration
│   ├── config-typescript.yaml # TypeScript SDK configuration
│   └── config-go.yaml         # Go SDK configuration
├── scripts/                   # Build and generation scripts
│   └── generate-sdks.sh       # Main generation script
├── python/                    # Generated Python SDK
├── typescript/                # Generated TypeScript/JavaScript SDK
├── go/                       # Generated Go SDK
├── docs/                     # SDK documentation
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** (v14+) with npm
- **Java** (JDK 11+) for OpenAPI Generator
- **Python** (3.8+) for Python SDK
- **Go** (1.19+) for Go SDK

### Generate All SDKs

```bash
# Navigate to sdks directory
cd /home/ubuntu/code/kenny/sdks

# Run the generation script
./scripts/generate-sdks.sh
```

This will:
1. Install OpenAPI Generator CLI (if needed)
2. Generate Python SDK with async support
3. Generate TypeScript/JavaScript SDK with full type definitions
4. Generate Go SDK with context support
5. Create usage examples and documentation

## 🔧 SDK Features

### 🐍 Python SDK (`python/`)

**Features:**
- Full async/await support with `asyncio`
- Type hints for all models and methods
- Pydantic models for data validation
- Context manager support
- Built-in retry mechanisms
- Comprehensive error handling

**Installation:**
```bash
cd python/
pip install -e .
```

**Usage:**
```python
import asyncio
from kenny_agi_sdk import ApiClient, Configuration, SystemApi

async def main():
    config = Configuration(
        host="http://localhost:8000",
        access_token="your_api_key"
    )
    
    async with ApiClient(config) as client:
        system_api = SystemApi(client)
        health = await system_api.health_check()
        print(f"System status: {health.status}")

asyncio.run(main())
```

### 📝 TypeScript/JavaScript SDK (`typescript/`)

**Features:**
- Full TypeScript type definitions
- Support for both Node.js and browser environments
- Promise-based async operations
- Tree-shakeable ESM modules
- Built-in request/response interceptors
- Runtime type checking

**Installation:**
```bash
cd typescript/
npm install
npm run build
```

**Usage:**
```typescript
import { Configuration, SystemApi, AGICoreApi } from './dist';

const config = new Configuration({
    basePath: "http://localhost:8000",
    accessToken: "your_api_key"
});

const systemApi = new SystemApi(config);
const agiApi = new AGICoreApi(config);

// Check system health
const health = await systemApi.healthCheck();
console.log(`System status: ${health.status}`);

// Process a thought
const result = await agiApi.processThought({
    prompt: "What is consciousness?",
    context: { source: "typescript_example" }
});
```

### 🔷 Go SDK (`go/`)

**Features:**
- Context-aware operations
- Strong type safety
- Comprehensive error handling
- HTTP client customization
- Request/response middleware
- Goroutine-safe operations

**Installation:**
```bash
cd go/
go mod tidy
go build ./...
```

**Usage:**
```go
package main

import (
    "context"
    "fmt"
    "log"
    
    kennyagi "./openapi"
)

func main() {
    config := kennyagi.NewConfiguration()
    config.Host = "localhost:8000"
    config.Scheme = "http"
    
    client := kennyagi.NewAPIClient(config)
    ctx := context.WithValue(
        context.Background(), 
        kennyagi.ContextAccessToken, 
        "your_api_key",
    )
    
    // Check system health
    health, _, err := client.SystemApi.HealthCheck(ctx).Execute()
    if err != nil {
        log.Fatalf("Error: %v", err)
    }
    fmt.Printf("System status: %s\n", health.Status)
}
```

## 🔧 Customization

### Modifying the OpenAPI Specification

Edit `/home/ubuntu/code/kenny/sdks/openapi/kenny-agi-api.yaml` to:
- Add new endpoints
- Update existing endpoint definitions
- Modify schemas and models
- Change authentication methods

### SDK Configuration

Each SDK has its own configuration file in the `generator/` directory:

- `config-python.yaml`: Python-specific settings
- `config-typescript.yaml`: TypeScript/JavaScript settings  
- `config-go.yaml`: Go-specific settings

### Custom Generation Options

Modify `scripts/generate-sdks.sh` to:
- Add new languages
- Change generation parameters
- Add post-processing steps
- Include additional templates

## 📚 Generated Documentation

Each generated SDK includes comprehensive documentation:

### Python SDK Documentation
- `/python/docs/` - API documentation
- `/python/README.md` - Setup and usage guide
- `/python/example_usage.py` - Working examples

### TypeScript SDK Documentation
- `/typescript/README.md` - Setup and usage guide
- `/typescript/src/` - Source code with inline documentation
- `/typescript/example_usage.ts` - Working examples

### Go SDK Documentation
- `/go/docs/` - API documentation
- `/go/README.md` - Setup and usage guide
- `/go/example_usage.go` - Working examples

## 🛠️ Advanced Usage

### Custom Client Configuration

#### Python
```python
from kenny_agi_sdk import Configuration

config = Configuration(
    host="https://api.kenny-agi.dev",
    access_token="your_token",
    timeout=60,
    retry_count=3,
    verify_ssl=True
)
```

#### TypeScript
```typescript
const config = new Configuration({
    basePath: "https://api.kenny-agi.dev",
    accessToken: "your_token",
    credentials: "include",
    headers: {
        "User-Agent": "MyApp/1.0.0"
    }
});
```

#### Go
```go
config := kennyagi.NewConfiguration()
config.Host = "api.kenny-agi.dev"
config.Scheme = "https"
config.DefaultHeader["User-Agent"] = "MyApp/1.0.0"
config.HTTPClient = &http.Client{
    Timeout: 60 * time.Second,
}
```

### Error Handling

#### Python
```python
from kenny_agi_sdk.exceptions import ApiException

try:
    result = await agi_api.get_agi_status()
except ApiException as e:
    if e.status == 401:
        print("Authentication failed")
    elif e.status == 500:
        print(f"Server error: {e.body}")
```

#### TypeScript
```typescript
try {
    const result = await agiApi.getAgiStatus();
} catch (error) {
    if (error.status === 401) {
        console.log("Authentication failed");
    } else if (error.status === 500) {
        console.log(`Server error: ${error.body}`);
    }
}
```

#### Go
```go
result, response, err := client.AGICoreApi.GetAgiStatus(ctx).Execute()
if err != nil {
    if response.StatusCode == 401 {
        log.Println("Authentication failed")
    } else {
        log.Printf("API error: %v", err)
    }
}
```

### WebSocket Support

While the generated SDKs handle REST APIs, WebSocket connections need to be implemented separately:

#### Python WebSocket Client
```python
import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8000/ws"
    headers = {"Authorization": "Bearer your_api_key"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        # Send message
        await websocket.send("What is consciousness?")
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        print(f"AGI Response: {data}")

asyncio.run(websocket_client())
```

## 🧪 Testing

### Running SDK Tests

#### Python
```bash
cd python/
pip install -r test-requirements.txt
python -m pytest test/
```

#### TypeScript
```bash
cd typescript/
npm test
```

#### Go
```bash
cd go/
go test ./...
```

### Integration Testing

Test against live Kenny AGI API:
```bash
# Start Kenny AGI API server
python /home/ubuntu/code/kenny/api/main.py

# Run SDK tests
./scripts/test-all-sdks.sh
```

## 🔄 Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/sdk-generation.yml`:

```yaml
name: SDK Generation and Testing

on:
  push:
    paths:
      - 'sdks/openapi/**'
      - 'api/**'
  pull_request:
    paths:
      - 'sdks/**'

jobs:
  generate-and-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Setup Go
      uses: actions/setup-go@v4
      with:
        go-version: '1.20'
    
    - name: Setup Java
      uses: actions/setup-java@v3
      with:
        java-version: '11'
    
    - name: Generate SDKs
      run: |
        cd sdks
        ./scripts/generate-sdks.sh
    
    - name: Test Python SDK
      run: |
        cd sdks/python
        pip install -e .
        python -m pytest test/
    
    - name: Test TypeScript SDK
      run: |
        cd sdks/typescript
        npm install
        npm test
    
    - name: Test Go SDK
      run: |
        cd sdks/go
        go mod tidy
        go test ./...
```

## 🚀 Publishing SDKs

### Python Package (PyPI)
```bash
cd python/
python -m build
python -m twine upload dist/*
```

### NPM Package
```bash
cd typescript/
npm publish --access public
```

### Go Module
```bash
cd go/
git tag v0.1.0
git push origin v0.1.0
```

## 🔧 Troubleshooting

### Common Issues

#### Java not found
```bash
sudo apt update
sudo apt install openjdk-11-jdk
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

#### OpenAPI Generator installation fails
```bash
# Alternative installation via Docker
docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
  -i /local/openapi/kenny-agi-api.yaml \
  -g python \
  -o /local/python/
```

#### TypeScript compilation errors
```bash
cd typescript/
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### Go module issues
```bash
cd go/
go mod tidy
go clean -cache
go build ./...
```

## 🤝 Contributing

### Adding New SDK Languages

1. Create configuration file in `generator/`
2. Update `generate-sdks.sh` script
3. Add language-specific example
4. Update documentation

### Improving Generated Code

1. Modify OpenAPI specification
2. Update generator configurations
3. Add custom templates (if needed)
4. Test thoroughly

## 📜 License

This SDK generator is part of Kenny AGI RDK and is licensed under the MIT License.

## 🔗 Resources

- [OpenAPI Generator](https://openapi-generator.tech/)
- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3)
- [Kenny AGI RDK Documentation](https://kenny-agi.dev/docs)
- [Kenny AGI GitHub Repository](https://github.com/kenny-agi/rdk)

---

**🎯 Ready to integrate Kenny AGI into your application?** Choose your preferred language SDK and start building!

**⚠️ Important:** Kenny AGI provides access to advanced artificial general intelligence capabilities. Always follow safety guidelines and ethical considerations when using consciousness manipulation or reality alteration features.