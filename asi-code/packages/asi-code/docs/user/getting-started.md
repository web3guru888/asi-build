# Getting Started with ASI-Code

Welcome to ASI-Code! This guide will help you get up and running with the Advanced Software Intelligence Code Generation and Analysis Platform.

## Table of Contents

- [What is ASI-Code?](#what-is-asicode)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [First Steps](#first-steps)
- [Basic Usage](#basic-usage)
- [Next Steps](#next-steps)
- [Common Issues](#common-issues)
- [Getting Help](#getting-help)

## What is ASI-Code?

ASI-Code is a revolutionary AI-powered framework that combines the innovative Kenny Integration Pattern (KIP) with a consciousness-aware architecture to provide intelligent code generation, analysis, and software development assistance.

### Key Features

- **Kenny Integration Pattern**: Standardized AI integration architecture
- **Consciousness Engine**: Advanced AI awareness and context management
- **Multi-Provider Support**: Works with Anthropic Claude, OpenAI GPT, and more
- **Tool System**: Extensible framework for custom development tools
- **Real-time Processing**: Live updates through WebSocket connections
- **CLI Interface**: Powerful command-line tools for developers

### Use Cases

- **Code Generation**: Create functions, components, and entire applications
- **Code Analysis**: Analyze project architecture and identify improvements
- **Development Assistance**: Get intelligent help with coding problems
- **Project Management**: Organize and manage development workflows
- **Learning**: Understand complex codebases and learn new technologies

## Prerequisites

Before installing ASI-Code, ensure you have:

### System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Node.js**: Version 18.0.0 or higher
- **Memory**: At least 4GB RAM (8GB recommended)
- **Storage**: 2GB free disk space

### Required Accounts

You'll need API keys from at least one AI provider:

- **Anthropic**: Sign up at [console.anthropic.com](https://console.anthropic.com)
- **OpenAI**: Sign up at [platform.openai.com](https://platform.openai.com)

### Recommended Tools

- **Code Editor**: VS Code with ASI-Code extension (coming soon)
- **Terminal**: Modern terminal with UTF-8 support
- **Git**: For version control integration

## Installation

### Option 1: NPM (Recommended)

```bash
# Install globally
npm install -g asi-code

# Verify installation
asi-code --version
```

### Option 2: Bun (Faster)

```bash
# Install Bun first (if not already installed)
curl -fsSL https://bun.sh/install | bash

# Install ASI-Code
bun install -g asi-code

# Verify installation
asi-code --version
```

### Option 3: From Source

```bash
# Clone repository
git clone https://github.com/asi-team/asi-code.git
cd asi-code/packages/asi-code

# Install dependencies
npm install

# Build project
npm run build

# Link globally
npm link

# Verify installation
asi-code --version
```

## Quick Start

### 1. Initialize Your First Project

```bash
# Create a new directory
mkdir my-asi-project
cd my-asi-project

# Initialize ASI-Code
asi-code init
```

You'll be prompted to configure your setup:

```
🚀 Welcome to ASI-Code Setup

? Select your preferred AI provider: 
❯ Anthropic Claude (Recommended)
  OpenAI GPT
  Custom Provider

? Enter your API key: [hidden]

? Choose default model:
❯ claude-3-sonnet-20240229
  claude-3-haiku-20240307
  claude-3-opus-20240229

? Enable consciousness engine? (Y/n) y

✅ Configuration saved to asi-code.config.yml
```

### 2. Start the Server

```bash
# Start ASI-Code server
asi-code start

# Output:
# 🚀 Starting ASI-Code server...
# ✅ Kenny Integration Pattern initialized
# ✅ Consciousness Engine active
# ✅ Provider system ready
# ✅ ASI-Code server started on http://localhost:3000
```

### 3. Your First Interaction

Open a new terminal and interact with ASI-Code:

```bash
# Test the CLI
asi-code --help

# Analyze your project
asi-code analyze .

# Get help with a specific question
echo "How do I create a React component?" | asi-code chat
```

## First Steps

### Understanding the Configuration

ASI-Code creates a configuration file (`asi-code.config.yml`) that controls all system behavior:

```yaml
# Basic configuration
providers:
  default:
    name: default
    type: anthropic
    apiKey: ${ANTHROPIC_API_KEY}
    model: claude-3-sonnet-20240229

consciousness:
  enabled: true
  personalityTraits:
    curiosity: 80
    helpfulness: 90
    creativity: 70

security:
  permissionLevel: safe
  allowedCommands:
    - read
    - write
    - analyze
```

### Setting Up Environment Variables

Create a `.env` file in your project directory:

```bash
# AI Provider API Keys
ANTHROPIC_API_KEY=your-anthropic-key-here
OPENAI_API_KEY=your-openai-key-here

# Optional: Customize server settings
ASI_CODE_PORT=3000
ASI_CODE_HOST=localhost

# Optional: Enable debug mode
DEBUG=asi-code:*
```

### Exploring the Interface

ASI-Code provides multiple ways to interact:

#### 1. Command Line Interface (CLI)

```bash
# Core commands
asi-code init              # Initialize project
asi-code start             # Start server
asi-code chat "message"    # Direct chat
asi-code analyze [path]    # Analyze code
asi-code version           # Show version

# Session management
asi-code session list      # List sessions
asi-code session create    # Create session

# Tool management
asi-code tool list         # List available tools
asi-code tool test <name>  # Test a tool
```

#### 2. HTTP API

```bash
# Health check
curl http://localhost:3000/health

# Create session
curl -X POST http://localhost:3000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"userId": "test-user"}'

# Send message
curl -X POST http://localhost:3000/api/v1/sessions/SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, ASI-Code!", "type": "user"}'
```

#### 3. WebSocket (Real-time)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:3000/ws');

// Join a session
ws.send(JSON.stringify({
  type: 'session:join',
  sessionId: 'your-session-id'
}));

// Send a message
ws.send(JSON.stringify({
  type: 'message:send',
  sessionId: 'your-session-id',
  message: {
    content: 'Generate a Python function',
    type: 'user'
  }
}));

// Listen for responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## Basic Usage

### Code Generation

Ask ASI-Code to generate code for you:

```bash
# Generate a React component
asi-code chat "Create a React component for user authentication with email and password fields"

# Generate a Python function
asi-code chat "Write a Python function to calculate the Fibonacci sequence up to n terms"

# Generate a complete API endpoint
asi-code chat "Create an Express.js API endpoint for user registration with validation"
```

### Code Analysis

Use ASI-Code to analyze existing code:

```bash
# Analyze current directory
asi-code analyze .

# Analyze specific file
asi-code analyze ./src/components/UserAuth.tsx

# Get architecture recommendations
asi-code analyze . --recommendations
```

Example output:
```
🏗️  Architecture Analysis Results

Project: /Users/developer/my-project
Analysis time: 2024-01-15T10:30:00.000Z

📋 Detected Patterns:
  • Model-View-Controller (85.2% confidence)
    Standard MVC pattern with clear separation of concerns
  
  • Component-Based Architecture (92.1% confidence)
    React-based component architecture with proper encapsulation

📊 Code Metrics:
  • Lines of Code: 15,847
  • Cyclomatic Complexity: 23.4
  • Dependencies: 45
  • Coupling: Medium (67%)
  • Cohesion: High (84%)

💡 Recommendations:
  • Consider extracting shared utilities into separate modules
  • Reduce dependency on external libraries where possible
  • Implement more comprehensive error handling
  • Add integration tests for critical user flows
```

### Interactive Conversations

Start an interactive session:

```bash
# Start interactive mode
asi-code chat --interactive

# Now you can have a conversation:
You: How do I optimize this React component for performance?
ASI: I'd be happy to help optimize your React component! To provide the best advice, could you share the component code? In general, here are key optimization strategies:

1. **Memoization**: Use React.memo() for functional components
2. **useMemo and useCallback**: Prevent unnecessary recalculations
3. **Code Splitting**: Use React.lazy() for component loading
4. **Virtual DOM optimization**: Proper key props in lists

Could you share your specific component so I can give targeted advice?

You: [paste your component code]
ASI: [provides specific optimization recommendations]
```

### Working with Tools

ASI-Code has built-in tools that can be executed automatically:

```bash
# List available tools
asi-code tool list

# Output:
# Available Tools:
#   • read - Read file contents
#   • write - Write content to files
#   • bash - Execute shell commands
#   • analyze - Analyze code structure
#   • edit - Edit existing files

# Test a tool
asi-code tool test write
```

When you ask ASI-Code to perform actions, it will automatically use tools:

```bash
asi-code chat "Create a new file called 'hello.py' with a simple Hello World program"

# ASI-Code will:
# 1. Generate the Python code
# 2. Use the 'write' tool to create the file
# 3. Confirm the file was created successfully
```

### Session Management

Sessions allow you to maintain context across interactions:

```bash
# Create a new session
SESSION_ID=$(asi-code session create --name "My Development Session")

# Continue a conversation in the same session
asi-code chat "I'm working on a React project" --session $SESSION_ID
asi-code chat "How do I add state management?" --session $SESSION_ID
asi-code chat "Show me an example with Redux" --session $SESSION_ID

# List your sessions
asi-code session list

# Resume a session
asi-code session resume $SESSION_ID
```

## Next Steps

### 1. Explore Advanced Features

- **Consciousness Engine**: Learn how ASI-Code adapts to your coding style
- **Custom Tools**: Create your own tools for specific workflows
- **API Integration**: Build custom applications with ASI-Code API
- **Team Collaboration**: Set up ASI-Code for team development

### 2. Customize Your Setup

```yaml
# Advanced asi-code.config.yml
consciousness:
  enabled: true
  personalityTraits:
    curiosity: 90        # More inquisitive
    helpfulness: 95      # Very helpful
    creativity: 85       # More creative solutions
    analytical: 90       # Detailed analysis

tools:
  enabled:
    - read
    - write
    - bash
    - analyze
    - custom-linter     # Your custom tool
  
security:
  permissionLevel: permissive  # For development
  allowedPaths:
    - ./src
    - ./tests
    - ./docs
  deniedCommands:
    - rm -rf
    - sudo
```

### 3. Learn the Kenny Integration Pattern

The Kenny Integration Pattern (KIP) is the core of ASI-Code. Understanding it helps you:

- Build better integrations
- Extend ASI-Code functionality
- Debug issues effectively
- Optimize performance

Read more: [Kenny Integration Pattern Documentation](../architecture/kenny.md)

### 4. Integrate with Your Workflow

#### VS Code Integration (Coming Soon)

```json
// settings.json
{
  "asi-code.enabled": true,
  "asi-code.serverUrl": "http://localhost:3000",
  "asi-code.autoSuggest": true,
  "asi-code.consciousnessLevel": "active"
}
```

#### Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/sh
asi-code analyze --changed-files --fail-on-issues
```

#### CI/CD Integration

```yaml
# .github/workflows/asi-code.yml
name: ASI-Code Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup ASI-Code
        run: npm install -g asi-code
      - name: Analyze Code
        run: asi-code analyze . --format json --output analysis.json
      - name: Upload Analysis
        uses: actions/upload-artifact@v2
        with:
          name: asi-code-analysis
          path: analysis.json
```

## Common Issues

### Installation Issues

**Problem**: `command not found: asi-code`
```bash
# Solution: Check your PATH
echo $PATH

# Add npm global bin to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH=$PATH:$(npm config get prefix)/bin

# Or reinstall with correct permissions
sudo npm install -g asi-code
```

**Problem**: Permission denied during installation
```bash
# Solution: Use npm prefix or nvm
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g asi-code
```

### Configuration Issues

**Problem**: Invalid API key error
```bash
# Solution: Verify your API key
echo $ANTHROPIC_API_KEY

# Test the key directly
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.anthropic.com/v1/messages
```

**Problem**: Server won't start
```bash
# Solution: Check port availability
lsof -i :3000

# Use different port
asi-code start --port 3001

# Check logs for errors
DEBUG=asi-code:* asi-code start
```

### Runtime Issues

**Problem**: Slow responses
```bash
# Solution: Check consciousness settings
# Edit asi-code.config.yml
consciousness:
  enabled: true
  awarenessThreshold: 50  # Lower for faster responses

# Or disable consciousness temporarily
consciousness:
  enabled: false
```

**Problem**: Tool execution fails
```bash
# Solution: Check permissions
asi-code tool list
asi-code tool test bash

# Check security settings
# Edit asi-code.config.yml
security:
  permissionLevel: permissive  # For development only
```

## Getting Help

### Documentation

- **Full Documentation**: [docs/](../)
- **API Reference**: [../../API.md](../../API.md)
- **Architecture Guide**: [../architecture/](../architecture/)
- **Examples**: [../examples/](../examples/)

### Community

- **GitHub Issues**: [github.com/asi-team/asi-code/issues](https://github.com/asi-team/asi-code/issues)
- **Discussions**: [github.com/asi-team/asi-code/discussions](https://github.com/asi-team/asi-code/discussions)
- **Discord**: [discord.gg/asi-code](https://discord.gg/asi-code) (coming soon)

### Support

- **Email**: support@asi-code.dev
- **Documentation**: docs@asi-code.dev
- **Security**: security@asi-code.dev

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Enable all debug logs
DEBUG=asi-code:* asi-code start

# Enable specific component logs
DEBUG=asi-code:kenny,asi-code:consciousness asi-code start

# Save logs to file
DEBUG=asi-code:* asi-code start 2>&1 | tee asi-code.log
```

### Troubleshooting Commands

```bash
# System information
asi-code --version
node --version
npm --version

# Configuration check
asi-code config validate

# Health check
curl http://localhost:3000/health

# Reset configuration
asi-code config reset
```

---

Congratulations! You're now ready to start using ASI-Code. Begin with simple code generation tasks and gradually explore more advanced features as you become comfortable with the system.

For your next steps, we recommend:
1. Reading the [CLI Documentation](cli.md)
2. Exploring [Configuration Options](configuration.md)
3. Learning about [Best Practices](best-practices.md)

Happy coding with ASI-Code! 🚀