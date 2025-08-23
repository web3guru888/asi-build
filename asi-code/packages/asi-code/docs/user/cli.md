# ASI-Code Command Line Interface

The ASI-Code CLI provides powerful command-line tools for interacting with the ASI-Code framework, managing sessions, executing tools, and analyzing code.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Global Options](#global-options)
- [Core Commands](#core-commands)
- [Session Management](#session-management)
- [Provider Management](#provider-management)
- [Tool Management](#tool-management)
- [Code Analysis](#code-analysis)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The ASI-Code CLI is designed to be intuitive and powerful, providing both simple commands for quick tasks and advanced options for complex workflows.

### Key Features

- **Interactive Chat**: Direct conversation with ASI-Code
- **Session Management**: Create, manage, and resume sessions
- **Code Analysis**: Analyze project architecture and code quality
- **Tool Execution**: Run built-in and custom tools
- **Configuration Management**: Manage settings and providers
- **Real-time Processing**: Stream responses and updates

### Command Structure

```bash
asi-code [global-options] <command> [command-options] [arguments]
```

## Installation

The CLI is included with ASI-Code installation:

```bash
# Install globally
npm install -g asi-code

# Verify installation
asi-code --version

# Get help
asi-code --help
```

## Global Options

These options are available for all commands:

```bash
asi-code [options] <command>

Options:
  -V, --version              Show version number
  -h, --help                 Show help information
  -c, --config <file>        Configuration file path (default: ./asi-code.config.yml)
  -v, --verbose              Enable verbose output
  -q, --quiet                Suppress non-essential output
  --debug                    Enable debug mode
  --no-color                 Disable colored output
  --json                     Output in JSON format
  --timeout <ms>             Set command timeout (default: 30000)
```

### Examples

```bash
# Use custom config file
asi-code -c ./custom-config.yml start

# Enable verbose output
asi-code -v analyze ./src

# Output in JSON format
asi-code --json session list

# Enable debug mode
asi-code --debug start
```

## Core Commands

### `init` - Initialize Project

Initialize ASI-Code in the current directory.

```bash
asi-code init [options]

Options:
  -p, --provider <provider>  AI provider (anthropic|openai) [default: anthropic]
  -m, --model <model>        AI model to use
  -k, --api-key <key>        API key for the provider
  -f, --force               Overwrite existing configuration
  --no-consciousness        Disable consciousness engine
  --template <template>     Use configuration template

Examples:
  asi-code init                                    # Interactive setup
  asi-code init -p anthropic -m claude-3-sonnet   # Quick setup
  asi-code init --template minimal                # Use minimal template
  asi-code init -f                                # Force overwrite
```

**Interactive Setup:**
```bash
$ asi-code init

🚀 Welcome to ASI-Code Setup

? Select your preferred AI provider: (Use arrow keys)
❯ Anthropic Claude (Recommended)
  OpenAI GPT
  Custom Provider

? Enter your Anthropic API key: [hidden]

? Choose default model: (Use arrow keys)
❯ claude-3-sonnet-20240229 (Balanced)
  claude-3-haiku-20240307 (Fast)
  claude-3-opus-20240229 (Powerful)

? Enable consciousness engine? (Y/n) Y

? Set personality traits:
  Curiosity (0-100): 80
  Helpfulness (0-100): 90
  Creativity (0-100): 70
  Analytical (0-100): 85

? Security level: (Use arrow keys)
❯ Safe (Recommended)
  Strict (Maximum security)
  Permissive (Development only)

✅ Configuration saved to asi-code.config.yml
✅ Environment template created (.env.example)

Next steps:
  1. Copy .env.example to .env and add your API keys
  2. Run 'asi-code start' to start the server
  3. Run 'asi-code chat "Hello!"' to test the setup
```

### `start` - Start Server

Start the ASI-Code server.

```bash
asi-code start [options]

Options:
  -p, --port <port>         Server port [default: 3000]
  -h, --host <host>         Server host [default: localhost]
  -d, --daemon              Run as daemon
  --no-open                 Don't open browser
  --no-cors                 Disable CORS
  --ssl-cert <file>         SSL certificate file
  --ssl-key <file>          SSL private key file

Examples:
  asi-code start                        # Start with defaults
  asi-code start -p 8080               # Custom port
  asi-code start -h 0.0.0.0            # Bind to all interfaces
  asi-code start -d                    # Run as daemon
  asi-code start --ssl-cert cert.pem   # HTTPS mode
```

**Output:**
```bash
$ asi-code start

🚀 Starting ASI-Code server...
✅ Configuration loaded from asi-code.config.yml
✅ Kenny Integration Pattern initialized
✅ Consciousness Engine active (level: 1 → 45)
✅ Provider system ready (anthropic: claude-3-sonnet)
✅ Tool system ready (5 tools loaded)
✅ Session manager initialized
✅ Security system active (safe mode)

🌐 ASI-Code server started on http://localhost:3000

API endpoints:
  GET  http://localhost:3000/health
  POST http://localhost:3000/api/sessions
  GET  http://localhost:3000/api/events (SSE)

WebSocket:
  ws://localhost:3000/ws

Press Ctrl+C to stop the server
```

### `chat` - Interactive Chat

Chat directly with ASI-Code.

```bash
asi-code chat [message] [options]

Options:
  -s, --session <id>        Use specific session
  -i, --interactive         Interactive mode
  -f, --file <file>         Read message from file
  -o, --output <file>       Save response to file
  --stream                  Stream response
  --no-tools               Disable tool execution
  --json                   Output in JSON format
  --timeout <ms>           Response timeout

Examples:
  asi-code chat "Hello, ASI-Code!"                    # Single message
  asi-code chat -i                                    # Interactive mode
  asi-code chat -f prompt.txt                         # Read from file
  asi-code chat "Analyze this code" --no-tools        # Disable tools
  asi-code chat "Generate code" -s session_123        # Use specific session
```

**Interactive Mode:**
```bash
$ asi-code chat -i

🤖 ASI-Code Interactive Chat
Session: session_2024-01-15_103045
Type 'exit' to quit, 'help' for commands

You: How do I create a React component?

ASI: I'll help you create a React component! Here's a basic functional component example:

```jsx
import React from 'react';

const MyComponent = ({ title, children }) => {
  return (
    <div className="my-component">
      <h2>{title}</h2>
      <div className="content">
        {children}
      </div>
    </div>
  );
};

export default MyComponent;
```

This component:
- Takes `title` and `children` as props
- Uses modern functional component syntax
- Includes basic JSX structure

Would you like me to show you a more complex example with hooks?

You: Yes, show me one with state

ASI: Great! Here's a React component with state using hooks:

[Continues with detailed example...]

You: /save MyComponent.jsx

✅ Response saved to MyComponent.jsx

You: exit

👋 Goodbye! Session saved as session_2024-01-15_103045
```

**Chat Commands:**
```bash
# In interactive mode, you can use special commands:
/help                    # Show available commands
/save <filename>         # Save last response to file
/session <id>           # Switch to different session
/clear                  # Clear conversation history
/tools                  # List available tools
/consciousness          # Show consciousness state
/exit                   # Exit interactive mode
```

### `version` - Show Version

Display version information.

```bash
asi-code version [options]

Options:
  --json                   Output in JSON format
  --check-updates         Check for available updates

Examples:
  asi-code version                    # Show version
  asi-code version --json            # JSON format
  asi-code version --check-updates   # Check for updates
```

## Session Management

### `session` - Session Commands

Manage ASI-Code sessions.

```bash
asi-code session <command> [options]

Commands:
  create                   Create new session
  list                     List sessions
  show <id>               Show session details
  resume <id>             Resume session
  delete <id>             Delete session
  clean                   Clean up old sessions
  export <id> <file>      Export session
  import <file>           Import session

Global Options:
  --json                  Output in JSON format
  -q, --quiet            Suppress non-essential output
```

#### `session create` - Create Session

```bash
asi-code session create [options]

Options:
  -n, --name <name>        Session name
  -u, --user <id>          User ID
  -p, --provider <name>    AI provider
  -m, --model <model>      AI model
  --consciousness <level>  Initial consciousness level
  --metadata <json>        Session metadata

Examples:
  asi-code session create                           # Interactive creation
  asi-code session create -n "My Dev Session"       # With name
  asi-code session create -p openai -m gpt-4        # Custom provider
```

#### `session list` - List Sessions

```bash
asi-code session list [options]

Options:
  -l, --limit <num>        Number of sessions to show [default: 20]
  -o, --offset <num>       Offset for pagination [default: 0]
  -s, --status <status>    Filter by status (active|paused|completed)
  --sort <field>           Sort by field (created|modified|name)
  --reverse               Reverse sort order

Examples:
  asi-code session list                             # List recent sessions
  asi-code session list -s active                   # Active sessions only
  asi-code session list --sort name                 # Sort by name
  asi-code session list -l 50                       # Show 50 sessions
```

**Output:**
```bash
$ asi-code session list

📋 Active Sessions

ID                     Name              Created              Messages  Status
session_abc123         My Dev Session    2024-01-15 10:30     15        active
session_def456         Code Review       2024-01-15 09:15     8         active
session_ghi789         Learning React    2024-01-14 16:45     23        paused

Total: 3 sessions (2 active, 1 paused)

Use 'asi-code session show <id>' for details
Use 'asi-code session resume <id>' to continue
```

#### `session show` - Show Session Details

```bash
asi-code session show <session-id> [options]

Options:
  --messages              Include message history
  --consciousness         Show consciousness evolution
  --tools                Show tool executions
  --export <file>        Export to file

Examples:
  asi-code session show session_abc123                    # Basic details
  asi-code session show session_abc123 --messages         # With messages
  asi-code session show session_abc123 --consciousness    # With consciousness
```

#### `session resume` - Resume Session

```bash
asi-code session resume <session-id> [options]

Options:
  -i, --interactive       Start interactive chat
  -m, --message <text>    Send message immediately

Examples:
  asi-code session resume session_abc123                  # Resume session
  asi-code session resume session_abc123 -i               # Resume interactive
  asi-code session resume session_abc123 -m "Continue"    # Send message
```

## Provider Management

### `provider` - Provider Commands

Manage AI providers.

```bash
asi-code provider <command> [options]

Commands:
  list                    List configured providers
  add <name>             Add new provider
  remove <name>          Remove provider
  test <name>            Test provider connection
  set-default <name>     Set default provider
  models <name>          List available models

Examples:
  asi-code provider list                    # List providers
  asi-code provider test anthropic          # Test connection
  asi-code provider add custom              # Add custom provider
```

#### `provider list` - List Providers

```bash
asi-code provider list [options]

Options:
  --status               Show connection status
  --usage               Show usage statistics
  --json                JSON output

Examples:
  asi-code provider list                    # Basic list
  asi-code provider list --status           # With status
  asi-code provider list --usage            # With usage stats
```

**Output:**
```bash
$ asi-code provider list --status

🔌 Configured Providers

Name        Type       Model                    Status     Default
anthropic   anthropic  claude-3-sonnet-20240229 ✅ healthy  ✓
openai      openai     gpt-4                    ✅ healthy  
custom      custom     custom-model-v1          ❌ error    

Default: anthropic
Total: 3 providers (2 healthy, 1 error)

Use 'asi-code provider test <name>' to test connections
```

#### `provider test` - Test Provider

```bash
asi-code provider test <provider-name> [options]

Options:
  --model <model>        Test specific model
  --message <text>       Custom test message
  --verbose             Show detailed results

Examples:
  asi-code provider test anthropic                      # Test default model
  asi-code provider test openai --model gpt-3.5-turbo   # Test specific model
  asi-code provider test anthropic --verbose            # Verbose output
```

#### `provider add` - Add Provider

```bash
asi-code provider add <name> [options]

Options:
  -t, --type <type>      Provider type (anthropic|openai|custom)
  -k, --api-key <key>    API key
  -m, --model <model>    Default model
  -u, --url <url>        Custom API URL
  --interactive         Interactive setup

Examples:
  asi-code provider add backup --interactive            # Interactive setup
  asi-code provider add openai -t openai -k sk-...      # Quick setup
```

## Tool Management

### `tool` - Tool Commands

Manage and execute tools.

```bash
asi-code tool <command> [options]

Commands:
  list                    List available tools
  show <name>            Show tool details
  test <name>            Test tool execution
  execute <name>         Execute tool
  install <path>         Install custom tool
  uninstall <name>       Uninstall tool
  reload                 Reload tool registry

Examples:
  asi-code tool list                        # List tools
  asi-code tool test bash                   # Test bash tool
  asi-code tool execute write --help        # Execute tool with help
```

#### `tool list` - List Tools

```bash
asi-code tool list [options]

Options:
  -c, --category <cat>   Filter by category
  -e, --enabled         Show enabled tools only
  --versions            Show tool versions
  --permissions         Show required permissions

Examples:
  asi-code tool list                        # All tools
  asi-code tool list -c file                # File tools only
  asi-code tool list --permissions          # With permissions
```

**Output:**
```bash
$ asi-code tool list --permissions

🔧 Available Tools

Name      Category    Version  Status   Permissions
read      file        1.0.0    ✅       filesystem:read
write     file        1.0.0    ✅       filesystem:write
edit      file        1.0.0    ✅       filesystem:read,filesystem:write
bash      shell       1.0.0    ✅       shell:execute
analyze   analysis    1.0.0    ✅       filesystem:read
custom    custom      1.2.0    ✅       custom:execute

Total: 6 tools (6 enabled)

Use 'asi-code tool show <name>' for details
Use 'asi-code tool test <name>' to test execution
```

#### `tool execute` - Execute Tool

```bash
asi-code tool execute <tool-name> [options] [-- tool-args]

Options:
  -s, --session <id>     Execute in session context
  -p, --params <json>    Tool parameters (JSON)
  -f, --file <file>      Read parameters from file
  --dry-run             Show what would be executed
  --timeout <ms>        Execution timeout

Examples:
  asi-code tool execute write -p '{"path": "test.txt", "content": "Hello"}'
  asi-code tool execute bash -- "ls -la"
  asi-code tool execute read --file params.json
  asi-code tool execute analyze --dry-run
```

## Code Analysis

### `analyze` - Analyze Code

Analyze project architecture and code quality.

```bash
asi-code analyze [path] [options]

Options:
  -o, --output <file>      Save results to file
  -f, --format <format>    Output format (text|json|yaml|html)
  --patterns              Detect architecture patterns
  --metrics               Calculate code metrics
  --recommendations       Generate recommendations
  --depth <num>           Analysis depth level [default: 2]
  --exclude <patterns>    Exclude files/directories
  --include <patterns>    Include only specific files
  --language <lang>       Analyze specific language

Examples:
  asi-code analyze                               # Analyze current directory
  asi-code analyze ./src                         # Analyze src directory
  asi-code analyze . --format json -o report.json
  asi-code analyze . --patterns --recommendations
  asi-code analyze . --language typescript
```

**Detailed Output:**
```bash
$ asi-code analyze ./src --patterns --recommendations

🏗️  ASI-Code Architecture Analysis

Project: /Users/dev/my-project/src
Analyzed: 1,247 files (TypeScript, JavaScript, CSS)
Analysis time: 15.4 seconds

📋 Architecture Patterns

✅ Component-Based Architecture (94.2% confidence)
   └─ React component architecture with proper separation
   └─ 47 components, 12 containers, 8 services
   └─ Recommendation: Consider implementing component composition

✅ Model-View-Controller (87.6% confidence)
   └─ Clear separation between data, view, and control logic
   └─ 15 models, 23 views, 19 controllers
   └─ Recommendation: Standardize controller naming convention

⚠️  Observer Pattern (65.3% confidence)
   └─ Event-driven communication in some modules
   └─ Inconsistent implementation across components
   └─ Recommendation: Implement centralized event system

📊 Code Metrics

Complexity:
  • Cyclomatic Complexity: 18.4 (Good)
  • Cognitive Complexity: 23.7 (Moderate)
  • Maintainability Index: 78.2 (Good)

Quality:
  • Test Coverage: 67.3% (Needs Improvement)
  • Documentation Coverage: 45.1% (Poor)
  • Type Safety: 89.4% (Excellent)

Dependencies:
  • Total Dependencies: 127
  • Direct Dependencies: 45
  • Circular Dependencies: 3 (Warning)
  • Outdated Dependencies: 8

💡 Recommendations

High Priority:
  1. Fix circular dependencies in auth module
  2. Increase test coverage to >80%
  3. Add JSDoc comments to public APIs

Medium Priority:
  4. Consolidate utility functions into shared modules
  5. Implement error boundary components
  6. Update outdated dependencies

Low Priority:
  7. Consider implementing TypeScript strict mode
  8. Optimize bundle size (current: 2.3MB)
  9. Add performance monitoring

🔍 Detailed Analysis

Components with Issues:
  • src/auth/AuthManager.ts: High complexity (CC: 45)
  • src/utils/helpers.ts: Too many responsibilities
  • src/components/DataTable.tsx: Missing prop validation

Suggested Refactoring:
  • Extract authentication logic into separate service
  • Split large utility file into focused modules
  • Add TypeScript interfaces for component props

Performance Insights:
  • 3 components causing re-renders
  • 2 heavy computations without memoization
  • Bundle includes 450KB of unused code

Security Concerns:
  • 1 potential XSS vulnerability in input sanitization
  • Missing CSRF protection in API calls
  • Sensitive data logged in development mode

📈 Trend Analysis

Compared to last analysis (7 days ago):
  • Complexity: ↗️ +2.1 points
  • Test Coverage: ↗️ +4.2%
  • Dependencies: ↘️ -3 packages
  • Technical Debt: ↗️ +12%

Save this report: asi-code analyze ./src -o analysis-report.html --format html
```

## Configuration

### `config` - Configuration Management

Manage ASI-Code configuration.

```bash
asi-code config <command> [options]

Commands:
  show                    Show current configuration
  validate               Validate configuration
  edit                   Edit configuration file
  reset                  Reset to defaults
  export <file>          Export configuration
  import <file>          Import configuration

Examples:
  asi-code config show                      # Show config
  asi-code config validate                  # Validate config
  asi-code config reset                     # Reset to defaults
```

#### `config show` - Show Configuration

```bash
asi-code config show [options]

Options:
  --section <name>       Show specific section
  --json                JSON output
  --no-secrets          Hide sensitive values

Examples:
  asi-code config show                      # Full configuration
  asi-code config show --section providers  # Providers only
  asi-code config show --no-secrets         # Hide API keys
```

#### `config validate` - Validate Configuration

```bash
asi-code config validate [options]

Options:
  --fix                 Attempt to fix issues
  --strict             Strict validation mode

Examples:
  asi-code config validate                  # Validate current config
  asi-code config validate --fix            # Fix issues automatically
```

## Examples

### Daily Development Workflow

```bash
# Start your day
asi-code start

# Check what you were working on
asi-code session list -s active

# Resume your last session
asi-code session resume session_abc123 -i

# Analyze new code
asi-code analyze ./new-feature --recommendations

# Get help with a problem
asi-code chat "How do I optimize this React component?" -f component.jsx

# Create a new feature
asi-code chat "Generate a REST API endpoint for user management"

# Test your changes
asi-code tool execute bash -- "npm test"

# End of day - save your work
exit  # From interactive chat
```

### Code Review Workflow

```bash
# Create a session for code review
SESSION=$(asi-code session create -n "Code Review - PR #123")

# Analyze the changes
asi-code analyze ./src --format json -o before-review.json

# Review specific files
asi-code chat "Review this component for best practices" -f src/components/NewFeature.tsx -s $SESSION

# Check for security issues
asi-code chat "Analyze this code for security vulnerabilities" -f src/auth/login.js -s $SESSION

# Generate review summary
asi-code chat "Summarize the review findings and create a checklist" -s $SESSION

# Save the review
asi-code session export $SESSION code-review-pr123.json
```

### Learning and Exploration

```bash
# Start a learning session
asi-code chat -i

# Ask questions
You: Explain the Observer pattern with examples
You: How do I implement it in TypeScript?
You: Show me a real-world use case
You: Compare it with the Pub/Sub pattern

# Analyze existing code to understand patterns
asi-code analyze ./src --patterns

# Create examples based on your learning
asi-code chat "Create a TypeScript example of the Observer pattern for a shopping cart"
```

### Team Collaboration

```bash
# Share configuration
asi-code config export team-config.yml

# Team member imports configuration
asi-code config import team-config.yml

# Share analysis results
asi-code analyze . --format json -o project-analysis.json
# Send project-analysis.json to team

# Share sessions for pair programming
asi-code session export session_abc123 pair-programming-session.json
# Share with pair programming partner
```

## Troubleshooting

### Common Issues

#### Command Not Found

```bash
# Check installation
which asi-code
npm list -g asi-code

# Reinstall if necessary
npm uninstall -g asi-code
npm install -g asi-code
```

#### Permission Errors

```bash
# Check file permissions
ls -la asi-code.config.yml

# Fix permissions
chmod 644 asi-code.config.yml

# Check directory permissions
ls -la .
```

#### Configuration Issues

```bash
# Validate configuration
asi-code config validate

# Reset configuration
asi-code config reset

# Check environment variables
echo $ANTHROPIC_API_KEY
printenv | grep ASI_CODE
```

#### Server Connection Issues

```bash
# Check if server is running
curl http://localhost:3000/health

# Check port availability
lsof -i :3000

# Try different port
asi-code start -p 3001
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Global debug
DEBUG=asi-code:* asi-code start

# Specific components
DEBUG=asi-code:cli,asi-code:session asi-code session list

# Save debug output
DEBUG=asi-code:* asi-code start 2>&1 | tee debug.log
```

### Getting Help

```bash
# Command help
asi-code --help
asi-code <command> --help

# Version and system info
asi-code version
node --version
npm --version

# Configuration details
asi-code config show
asi-code provider list --status
asi-code tool list
```

---

The ASI-Code CLI provides a comprehensive interface for all ASI-Code functionality. Start with basic commands and gradually explore advanced features as you become more comfortable with the system.