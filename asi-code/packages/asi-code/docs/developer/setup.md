# Development Setup

This guide walks you through setting up a development environment for contributing to ASI-Code.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Development Workflow](#development-workflow)
- [Building and Testing](#building-and-testing)
- [Debugging](#debugging)
- [IDE Configuration](#ide-configuration)
- [Contributing Guidelines](#contributing-guidelines)

## Prerequisites

### System Requirements

- **Node.js**: Version 18.0.0 or higher
- **Bun**: Version 1.0.0 or higher (recommended for development)
- **Git**: Latest version
- **Operating System**: Windows 10+, macOS 10.15+, or Linux

### Development Tools

- **Code Editor**: VS Code (recommended) with extensions
- **Terminal**: Modern terminal with UTF-8 support
- **Docker**: For containerized development (optional)

## Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/asi-team/asi-code.git
cd asi-code/packages/asi-code

# Verify you're in the right directory
ls -la
# Should see: src/, test/, package.json, etc.
```

### 2. Install Dependencies

```bash
# Install Bun (if not already installed)
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# Install project dependencies
bun install

# Verify installation
bun --version
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

Add your development configuration:

```bash
# Development Environment
NODE_ENV=development

# API Keys (get from respective providers)
ANTHROPIC_API_KEY=your-development-anthropic-key
OPENAI_API_KEY=your-development-openai-key

# Development Server
ASI_CODE_PORT=3000
ASI_CODE_HOST=localhost

# Debug Settings
DEBUG=asi-code:*
LOG_LEVEL=debug

# Development Database (optional)
DATABASE_URL=postgresql://localhost:5432/asicode_dev
REDIS_URL=redis://localhost:6379

# Testing
TEST_ANTHROPIC_API_KEY=your-test-api-key
TEST_OPENAI_API_KEY=your-test-api-key
```

### 4. Build Project

```bash
# Build TypeScript
bun run build

# Build CLI
bun run build:bin

# Verify build
ls -la dist/
ls -la bin/
```

### 5. Run Tests

```bash
# Run all tests
bun test

# Run specific test suite
bun test kenny.test.ts

# Run with coverage
bun test --coverage

# Watch mode for development
bun test --watch
```

## Development Workflow

### 1. Development Server

```bash
# Start development server with hot reload
bun dev

# Or start built version
bun start

# Check server health
curl http://localhost:3000/health
```

### 2. Code Structure

Understanding the codebase structure:

```
src/
├── kenny/              # Kenny Integration Pattern
│   ├── index.ts        # Main KIP implementation
│   ├── integration.ts  # Integration utilities
│   ├── message-bus.ts  # Message handling
│   └── state-manager.ts # State management
├── consciousness/      # Consciousness Engine
│   ├── index.ts        # Core consciousness logic
│   └── memory.ts       # Memory management
├── provider/          # AI Provider System
│   ├── index.ts       # Provider manager
│   ├── anthropic.ts   # Anthropic provider
│   └── openai.ts      # OpenAI provider
├── tool/              # Tool Management
│   ├── base-tool.ts   # Base tool class
│   ├── built-in-tools/ # Built-in tools
│   └── tool-registry.ts # Tool registration
├── server/            # HTTP/SSE Server
├── session/           # Session Management
├── permission/        # Security & Permissions
├── config/            # Configuration
├── logging/           # Logging System
├── cli/               # Command Line Interface
└── index.ts           # Main entry point
```

### 3. Making Changes

#### Step-by-Step Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   ```bash
   # Edit files
   nano src/kenny/new-feature.ts
   
   # Add tests
   nano test/kenny-new-feature.test.ts
   ```

3. **Test Changes**
   ```bash
   # Run tests
   bun test
   
   # Run specific tests
   bun test kenny
   
   # Check types
   bun run typecheck
   ```

4. **Build and Verify**
   ```bash
   # Build project
   bun run build
   
   # Test CLI
   ./bin/asi-code.js --version
   
   # Manual testing
   bun dev
   ```

5. **Commit Changes**
   ```bash
   # Stage changes
   git add .
   
   # Commit with conventional commit format
   git commit -m "feat(kenny): add new integration feature"
   ```

### 4. Development Scripts

```bash
# Package.json scripts
bun run dev          # Development server with hot reload
bun run build        # Build TypeScript and CLI
bun run test         # Run all tests
bun run test:watch   # Test watch mode
bun run lint         # Run ESLint
bun run format       # Format code with Prettier
bun run typecheck    # TypeScript type checking
bun run clean        # Clean build artifacts
```

## Building and Testing

### Build Process

The project uses a multi-stage build process:

```bash
# 1. TypeScript compilation
bun run tsc

# 2. CLI bundle creation
bun build src/cli/index.ts --outdir bin --target node --format esm --outfile asi-code.js

# 3. Make CLI executable
chmod +x bin/asi-code.js

# Complete build
bun run build
```

### Testing Strategy

#### Unit Tests

```bash
# Run all unit tests
bun test

# Run specific test file
bun test kenny.test.ts

# Run tests with specific pattern
bun test --grep "consciousness"

# Debug failing tests
bun test --verbose kenny.test.ts
```

#### Integration Tests

```bash
# Run integration tests
bun test integration/

# Run end-to-end tests
bun test e2e/

# Run with real providers (requires API keys)
TEST_REAL_PROVIDERS=true bun test
```

#### Test Structure

```typescript
// test/kenny.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { createKennyIntegration } from '../src/kenny/index.js';
import { createMockProvider } from './fixtures/mocks.js';

describe('Kenny Integration Pattern', () => {
  let kenny: KennyIntegrationPattern;
  let mockProvider: Provider;

  beforeEach(() => {
    kenny = createKennyIntegration();
    mockProvider = createMockProvider();
  });

  afterEach(async () => {
    await kenny.cleanup();
  });

  it('should initialize correctly', async () => {
    await kenny.initialize({ providers: { default: mockProvider } });
    expect(kenny.isInitialized).toBe(true);
  });

  it('should process messages', async () => {
    await kenny.initialize({ providers: { default: mockProvider } });
    
    const context = kenny.createContext('test-session');
    const message = {
      id: 'test-1',
      type: 'user' as const,
      content: 'Hello, world!',
      timestamp: new Date(),
      context
    };

    const response = await kenny.process(message);
    expect(response.type).toBe('assistant');
    expect(response.content).toBeDefined();
  });
});
```

### Performance Testing

```bash
# Benchmark tests
bun run benchmark

# Memory usage monitoring
bun --inspect dev

# Performance profiling
bun --inspect-brk=0.0.0.0:9229 dev
```

## Debugging

### Debug Configuration

Enable debug logging for specific components:

```bash
# Debug all ASI-Code components
DEBUG=asi-code:* bun dev

# Debug specific components
DEBUG=asi-code:kenny,asi-code:consciousness bun dev

# Debug levels
DEBUG_LEVEL=verbose bun dev
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug ASI-Code Server",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/index.ts",
      "runtimeExecutable": "bun",
      "runtimeArgs": ["--inspect=0.0.0.0:9229"],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "asi-code:*"
      },
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    },
    {
      "name": "Debug CLI",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/src/cli/index.ts",
      "runtimeExecutable": "bun",
      "args": ["start"],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "asi-code:cli"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Tests",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/node_modules/.bin/bun",
      "args": ["test", "${file}"],
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    }
  ]
}
```

### Debugging Tools

```bash
# Node.js inspector
bun --inspect dev

# Chrome DevTools
# Open chrome://inspect in Chrome browser

# Memory leaks
bun --inspect --expose-gc dev

# CPU profiling
bun --prof dev
```

### Log Analysis

```bash
# View logs in real-time
tail -f logs/asi-code.log

# Filter logs by component
grep "kenny" logs/asi-code.log

# JSON log parsing
cat logs/asi-code.log | jq 'select(.component == "consciousness")'

# Error analysis
grep -i error logs/asi-code.log | tail -20
```

## IDE Configuration

### VS Code Setup

#### Recommended Extensions

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-vscode.vscode-typescript-next",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode.vscode-jest"
  ]
}
```

#### Workspace Settings

```json
// .vscode/settings.json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true,
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "eslint.format.enable": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/node_modules": true,
    "**/dist": true,
    "**/.git": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/dist": true
  },
  "typescript.preferences.includePackageJsonAutoImports": "on"
}
```

#### Workspace Tasks

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Build",
      "type": "shell",
      "command": "bun run build",
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "silent",
        "focus": false,
        "panel": "shared"
      }
    },
    {
      "label": "Test",
      "type": "shell",
      "command": "bun test",
      "group": "test",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    },
    {
      "label": "Dev Server",
      "type": "shell",
      "command": "bun dev",
      "group": "build",
      "isBackground": true,
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    }
  ]
}
```

### Code Quality Tools

#### ESLint Configuration

```json
// .eslintrc.json
{
  "extends": [
    "@typescript-eslint/recommended",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "root": true,
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "no-console": "warn",
    "prefer-const": "error"
  }
}
```

#### Prettier Configuration

```json
// .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}
```

## Contributing Guidelines

### Code Style

1. **TypeScript**: Use strict TypeScript with proper typing
2. **Naming**: Use camelCase for variables, PascalCase for classes
3. **Comments**: Use JSDoc for public APIs
4. **Imports**: Use relative imports within the project
5. **Error Handling**: Always handle errors gracefully

### Commit Guidelines

Use conventional commit format:

```bash
# Feature
git commit -m "feat(kenny): add new message routing capability"

# Bug fix
git commit -m "fix(consciousness): resolve memory leak in state manager"

# Documentation
git commit -m "docs(api): update provider interface documentation"

# Test
git commit -m "test(integration): add end-to-end workflow tests"

# Refactor
git commit -m "refactor(tool): simplify tool execution pipeline"
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/description
   ```

2. **Implement Changes**
   - Write code following style guidelines
   - Add comprehensive tests
   - Update documentation

3. **Test Thoroughly**
   ```bash
   bun test
   bun run lint
   bun run build
   ```

4. **Create Pull Request**
   - Use descriptive title
   - Include detailed description
   - Reference related issues
   - Add screenshots/examples if applicable

### Development Best Practices

1. **Test-Driven Development**
   ```bash
   # Write test first
   nano test/new-feature.test.ts
   
   # Run test (should fail)
   bun test new-feature.test.ts
   
   # Implement feature
   nano src/new-feature.ts
   
   # Run test (should pass)
   bun test new-feature.test.ts
   ```

2. **Code Reviews**
   - Review your own code before submitting
   - Address all PR feedback
   - Keep PRs focused and small
   - Include rationale for design decisions

3. **Documentation**
   - Update relevant documentation
   - Add inline comments for complex logic
   - Include usage examples
   - Keep README files current

### Development Helpers

#### Useful Scripts

```bash
#!/bin/bash
# dev-setup.sh - Development environment setup

# Install dependencies
bun install

# Set up git hooks
cp .githooks/* .git/hooks/
chmod +x .git/hooks/*

# Create development database
createdb asicode_dev

# Start development services
docker-compose -f docker-compose.dev.yml up -d

echo "Development environment ready!"
```

#### Git Hooks

```bash
#!/bin/sh
# .githooks/pre-commit - Run before each commit

# Run tests
bun test

# Run linting
bun run lint

# Check types
bun run typecheck

# Build project
bun run build

echo "Pre-commit checks passed!"
```

---

With this development setup, you're ready to contribute to ASI-Code! Start with small changes and gradually work on more complex features as you become familiar with the codebase.