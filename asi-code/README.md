# ASI-Code

**Advanced Software Intelligence Code Generation and Analysis Platform**

ASI-Code is a comprehensive platform that combines AI-powered code generation, architectural analysis, and intelligent software development assistance through the innovative Kenny Integration Pattern (KIP).

## 🌟 Key Features

### Kenny Integration Pattern (KIP)
- **Consciousness-Aware AI**: Advanced AI processing with awareness levels and adaptive behavior
- **Context Management**: Sophisticated session and context handling for multi-turn interactions
- **Event-Driven Architecture**: Real-time communication and state management

### AI Provider Support
- **Anthropic Claude**: Full support for Claude 3 models with streaming
- **OpenAI GPT**: Compatible with GPT-4 and other OpenAI models
- **Extensible Framework**: Easy integration of custom AI providers

### Built-in Tools System
- **File Operations**: Read, write, and manage files with permission controls
- **System Commands**: Execute shell commands with security constraints
- **Pattern Matching**: Glob-based file discovery and content search
- **Extensible**: Create custom tools for specialized workflows

### Software Architecture Taskforce (SAT)
- **Pattern Detection**: Automatically identify architectural patterns in codebases
- **Metrics Analysis**: Calculate complexity, coupling, and cohesion metrics
- **Recommendations**: Get actionable insights for improving code architecture
- **Multi-Language**: Support for TypeScript, JavaScript, Python, Java, and more

### Advanced Features
- **Consciousness Engine**: AI awareness and adaptation based on interaction patterns
- **Session Management**: Persistent conversations with context retention
- **Permission System**: Fine-grained access control for operations
- **HTTP/SSE Server**: Real-time API with Server-Sent Events
- **LSP Integration**: Language Server Protocol support for editors
- **MCP Support**: Model Context Protocol for interoperability

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/asi-team/asi-code.git
cd asi-code

# Install dependencies
bun install

# Build the project
bun run workspace:build
```

### Initialize ASI-Code

```bash
# Initialize in your project
cd packages/asi-code
bun run asi-code init --provider anthropic --api-key your-api-key

# Or using environment variables
export ANTHROPIC_API_KEY=your-key-here
bun run asi-code init
```

### Start the Server

```bash
# Start the ASI-Code server
bun run asi-code start

# Custom port and host
bun run asi-code start --port 8000 --host 0.0.0.0
```

### Analyze Your Project

```bash
# Run architectural analysis
bun run asi-code analyze

# Analyze specific directory with output
bun run asi-code analyze ./src --output analysis.json --format json
```

## 📋 API Endpoints

### Session Management
- `POST /api/sessions` - Create new session
- `GET /api/sessions/:id` - Get session details  
- `DELETE /api/sessions/:id` - Delete session
- `POST /api/sessions/:id/messages` - Add message
- `GET /api/sessions/:id/messages` - Get messages

### AI Providers
- `GET /api/providers` - List available providers
- `POST /api/providers/:name/generate` - Generate response

### Tools
- `GET /api/tools` - List available tools
- `POST /api/tools/:name/execute` - Execute tool

### Real-time Events
- `GET /api/events` - Server-Sent Events stream

## 🔧 Configuration

ASI-Code uses YAML configuration files:

```yaml
# asi-code.config.yml
asi:
  name: "ASI-Code"
  version: "0.1.0"
  environment: "development"

providers:
  anthropic:
    enabled: true
    model: "claude-3-sonnet-20240229"
    maxTokens: 4000
    temperature: 0.7

kenny:
  enabled: true
  contextWindowSize: 20
  adaptationRate: 0.1

consciousness:
  enabled: true
  awarenessThreshold: 70
  memoryRetentionHours: 24
  personalityTraits:
    curiosity: 80
    helpfulness: 90
    creativity: 70

server:
  port: 3000
  host: "localhost"
  cors:
    origin: ["http://localhost:3000"]
    credentials: true
```

## 🏗️ Architecture

ASI-Code follows a modular, event-driven architecture:

```
packages/asi-code/src/
├── kenny/          # Kenny Integration Pattern core
├── provider/       # AI provider implementations
├── tool/          # Built-in tools system
├── session/       # Session management
├── server/        # Hono HTTP/SSE server
├── consciousness/ # Consciousness engine
├── agent/         # Agent configurations
├── permission/    # Permission system
├── lsp/           # Language Server Protocol
├── mcp/           # Model Context Protocol
├── storage/       # Storage abstraction
├── bus/           # Event bus system
├── config/        # Configuration system
└── sat/           # Software Architecture Taskforce
```

## 🧪 Development

### Building

```bash
# Build all packages
bun run workspace:build

# Development mode with watching
bun run workspace:dev
```

### Testing

```bash
# Run tests
bun run workspace:test

# Run tests in watch mode
bun test --watch
```

### Linting and Formatting

```bash
# Lint code
bun run lint

# Format code
bun run format
```

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](./docs/DEVELOPMENT_GUIDE.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📖 Documentation

- [Architecture Overview](./docs/ARCHITECTURE.md)
- [Kenny Integration Pattern](./docs/KENNY_PATTERN.md)
- [Provider System](./docs/PROVIDER_SYSTEM.md)
- [Tool System](./docs/TOOL_SYSTEM.md)
- [API Reference](./docs/API_REFERENCE.md)
- [Development Guide](./docs/DEVELOPMENT_GUIDE.md)

## 🔐 Security

ASI-Code implements comprehensive security measures:

- **Permission System**: Fine-grained access controls
- **API Key Management**: Secure provider authentication
- **Command Execution**: Sandboxed system operations
- **Input Validation**: Comprehensive parameter validation
- **Rate Limiting**: Configurable request throttling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Bun](https://bun.sh) for superior performance
- Powered by [Hono](https://hono.dev) for lightweight HTTP handling
- Inspired by advanced AI interaction patterns and consciousness research

---

**ASI-Code** - Empowering developers with advanced software intelligence.

For questions, support, or contributions, please visit our [GitHub repository](https://github.com/asi-team/asi-code) or open an issue.