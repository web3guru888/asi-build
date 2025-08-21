# Contributing to ASI-Code

Thank you for your interest in contributing to ASI-Code! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Guidelines](#development-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

ASI-Code is committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our Code of Conduct:

### Our Pledge

We pledge to make participation in our project and community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at conduct@asi-code.dev.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Node.js**: Version 18.0.0 or higher
- **Bun**: Version 1.0.0 or higher (recommended runtime)
- **Git**: For version control
- **TypeScript**: Knowledge of TypeScript is essential
- **Editor**: VS Code with TypeScript and ESLint extensions recommended

### Areas for Contribution

We welcome contributions in several areas:

1. **Core Framework**: Kenny Integration Pattern, Consciousness Engine
2. **Provider Support**: New AI provider integrations
3. **Tools**: Built-in and custom tool development
4. **Documentation**: User guides, API docs, tutorials
5. **Testing**: Unit tests, integration tests, performance tests
6. **Security**: Security audits, vulnerability fixes
7. **Performance**: Optimization and profiling
8. **Examples**: Sample applications and use cases

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/asi-code.git
cd asi-code/packages/asi-code
```

### 2. Install Dependencies

```bash
# Install dependencies with Bun (recommended)
bun install

# Or with npm
npm install
```

### 3. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Add your API keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
```

### 4. Build and Test

```bash
# Build the project
bun run build

# Run tests
bun test

# Run in development mode
bun dev
```

### 5. Verify Installation

```bash
# Test CLI
./bin/asi-code.js --version

# Start server
bun run start
```

## Project Structure

Understanding the project structure is crucial for effective contribution:

```
asi-code/
├── src/                    # Source code
│   ├── kenny/             # Kenny Integration Pattern
│   │   ├── index.ts       # Main KIP implementation
│   │   ├── integration.ts # Integration utilities
│   │   ├── message-bus.ts # Message handling
│   │   └── state-manager.ts # State management
│   ├── consciousness/     # Consciousness Engine
│   │   ├── index.ts       # Core consciousness logic
│   │   └── memory.ts      # Memory management
│   ├── provider/          # AI Provider System
│   │   ├── index.ts       # Provider manager
│   │   ├── anthropic.ts   # Anthropic provider
│   │   └── openai.ts      # OpenAI provider
│   ├── tool/              # Tool Management
│   │   ├── base-tool.ts   # Base tool class
│   │   ├── built-in-tools/ # Built-in tools
│   │   └── tool-registry.ts # Tool registration
│   ├── server/            # HTTP/SSE Server
│   ├── session/           # Session Management
│   ├── permission/        # Security & Permissions
│   ├── sat/               # Software Architecture Taskforce
│   ├── config/            # Configuration
│   ├── logging/           # Logging System
│   ├── cli/               # Command Line Interface
│   └── index.ts           # Main entry point
├── test/                   # Test files
├── docs/                   # Documentation
├── examples/               # Example applications
├── bin/                    # CLI executables
└── package.json           # Package configuration
```

### Key Components

#### Kenny Integration Pattern (KIP)
- **Purpose**: Standardized AI integration architecture
- **Location**: `src/kenny/`
- **Key Files**: `index.ts`, `integration.ts`, `message-bus.ts`

#### Consciousness Engine
- **Purpose**: Advanced AI awareness and context management
- **Location**: `src/consciousness/`
- **Key Files**: `index.ts`, memory management, state tracking

#### Provider System
- **Purpose**: Multi-provider AI service integration
- **Location**: `src/provider/`
- **Key Files**: Provider interfaces, implementations

#### Tool System
- **Purpose**: Extensible tool execution framework
- **Location**: `src/tool/`
- **Key Files**: Base classes, built-in tools, registry

## Development Guidelines

### Code Style

We use TypeScript with strict type checking and ESLint for code quality.

#### TypeScript Guidelines

```typescript
// Use explicit types where helpful
interface KennyMessage {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  context: KennyContext;
}

// Use proper async/await patterns
async function processMessage(message: KennyMessage): Promise<KennyMessage> {
  try {
    const result = await consciousness.process(message);
    return result;
  } catch (error) {
    logger.error('Failed to process message', { error, messageId: message.id });
    throw error;
  }
}

// Use proper error handling
class ASICodeError extends Error {
  constructor(
    message: string,
    public code: string,
    public cause?: Error
  ) {
    super(message);
    this.name = 'ASICodeError';
  }
}
```

#### Naming Conventions

- **Files**: kebab-case (`kenny-integration.ts`)
- **Classes**: PascalCase (`KennyIntegration`)
- **Interfaces**: PascalCase with descriptive names (`KennyMessage`)
- **Functions**: camelCase (`processMessage`)
- **Constants**: SCREAMING_SNAKE_CASE (`DEFAULT_CONFIG`)
- **Events**: namespace:action (`kenny:message_processed`)

#### Code Organization

```typescript
// 1. Imports (external first, then internal)
import { EventEmitter } from 'eventemitter3';
import type { Logger } from 'winston';

import type { KennyContext } from './types.js';
import { createLogger } from '../logging/index.js';

// 2. Types and interfaces
export interface ComponentConfig {
  enabled: boolean;
  options: Record<string, any>;
}

// 3. Constants
const DEFAULT_TIMEOUT = 30000;

// 4. Main implementation
export class Component extends EventEmitter {
  private logger: Logger;
  
  constructor(private config: ComponentConfig) {
    super();
    this.logger = createLogger('component');
  }
  
  // Public methods first
  async initialize(): Promise<void> {
    // Implementation
  }
  
  // Private methods last
  private validateConfig(): void {
    // Implementation
  }
}

// 5. Factory functions
export function createComponent(config: ComponentConfig): Component {
  return new Component(config);
}
```

### Documentation Standards

#### Code Documentation

```typescript
/**
 * Processes a message through the Kenny Integration Pattern
 * 
 * @param message - The message to process
 * @param context - The current context
 * @returns Promise resolving to the processed response
 * 
 * @example
 * ```typescript
 * const response = await kenny.process(message, context);
 * console.log(response.content);
 * ```
 * 
 * @throws {ASICodeError} When message processing fails
 */
async function processMessage(
  message: KennyMessage, 
  context: KennyContext
): Promise<KennyMessage> {
  // Implementation
}
```

#### README Files

Each major component should have its own README with:
- Purpose and overview
- API documentation
- Usage examples
- Configuration options
- Testing instructions

### Error Handling

#### Error Types

```typescript
// Base error class
export class ASICodeError extends Error {
  constructor(
    message: string,
    public code: string,
    public context?: Record<string, any>
  ) {
    super(message);
    this.name = 'ASICodeError';
  }
}

// Specific error types
export class ProviderError extends ASICodeError {
  constructor(message: string, provider: string, cause?: Error) {
    super(message, 'PROVIDER_ERROR', { provider });
    this.cause = cause;
  }
}

export class ToolExecutionError extends ASICodeError {
  constructor(message: string, toolName: string, exitCode?: number) {
    super(message, 'TOOL_ERROR', { toolName, exitCode });
  }
}
```

#### Error Handling Patterns

```typescript
// Async function error handling
async function riskyOperation(): Promise<Result> {
  try {
    const result = await someAsyncOperation();
    return { success: true, data: result };
  } catch (error) {
    logger.error('Operation failed', { error });
    
    if (error instanceof ProviderError) {
      // Handle provider-specific errors
      throw new ASICodeError('Provider operation failed', 'PROVIDER_FAILED', { cause: error });
    }
    
    // Re-throw unexpected errors
    throw error;
  }
}

// Event emitter error handling
emitter.on('error', (error) => {
  logger.error('Event emitter error', { error });
  // Handle or re-emit as needed
});
```

### Logging

We use structured logging with Winston. Follow these patterns:

```typescript
import { createLogger } from '../logging/index.js';

const logger = createLogger('component-name');

// Info level for normal operations
logger.info('Component initialized', { config: this.config });

// Debug level for detailed information
logger.debug('Processing message', { messageId: message.id, type: message.type });

// Warning level for recoverable issues
logger.warn('Provider timeout, retrying', { provider: 'anthropic', attempt: 2 });

// Error level for failures
logger.error('Failed to process message', { 
  error: error.message, 
  messageId: message.id,
  stack: error.stack 
});
```

### Performance Guidelines

#### Async Operations

```typescript
// Use Promise.all for parallel operations
const [providers, tools, sessions] = await Promise.all([
  loadProviders(),
  loadTools(),
  loadSessions()
]);

// Use proper timeout handling
const result = await Promise.race([
  operation(),
  new Promise((_, reject) => 
    setTimeout(() => reject(new Error('Timeout')), 5000)
  )
]);
```

#### Memory Management

```typescript
// Clean up resources
class ResourceManager {
  private resources = new Map<string, Resource>();
  
  async cleanup(): Promise<void> {
    await Promise.all(
      Array.from(this.resources.values()).map(r => r.cleanup())
    );
    this.resources.clear();
  }
}

// Use WeakMap for memory-sensitive caches
const cache = new WeakMap<Object, CachedData>();
```

## Testing

### Test Structure

We use Bun's built-in test runner with a comprehensive test suite:

```
test/
├── unit/                  # Unit tests
│   ├── kenny.test.ts     # Kenny Integration Pattern tests
│   ├── consciousness.test.ts # Consciousness Engine tests
│   └── providers.test.ts # Provider tests
├── integration/          # Integration tests
│   ├── end-to-end.test.ts # Full system tests
│   └── api.test.ts       # API endpoint tests
├── performance/          # Performance tests
└── fixtures/             # Test data and mocks
```

### Writing Tests

#### Unit Tests

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { createKennyIntegration } from '../src/kenny/index.js';
import { createMockProvider, createMockContext } from './fixtures/mocks.js';

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

  it('should initialize with valid configuration', async () => {
    const config = { providers: { default: mockProvider } };
    
    await expect(kenny.initialize(config)).resolves.not.toThrow();
    expect(kenny.isInitialized).toBe(true);
  });

  it('should process messages correctly', async () => {
    await kenny.initialize({ providers: { default: mockProvider } });
    
    const context = createMockContext();
    const message = {
      id: 'test-1',
      type: 'user' as const,
      content: 'Hello, world!',
      timestamp: new Date(),
      context
    };

    const response = await kenny.process(message);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toMatch(/processed/i);
  });

  it('should handle errors gracefully', async () => {
    const kenny = createKennyIntegration();
    
    await expect(kenny.process(invalidMessage)).rejects.toThrow('Kenny Integration Pattern not initialized');
  });
});
```

#### Integration Tests

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'bun:test';
import { createASIServer } from '../src/server/index.js';
import { createTestClient } from './fixtures/test-client.js';

describe('ASI-Code Server Integration', () => {
  let server: ASIServer;
  let client: TestClient;

  beforeAll(async () => {
    server = createASIServer(testConfig);
    await server.start();
    client = createTestClient(server.url);
  });

  afterAll(async () => {
    await client.disconnect();
    await server.stop();
  });

  it('should handle complete message workflow', async () => {
    // Create session
    const session = await client.createSession();
    expect(session.id).toBeDefined();

    // Send message
    const response = await client.sendMessage(session.id, {
      content: 'Generate a React component',
      type: 'user'
    });

    expect(response.content).toContain('React');
    expect(response.type).toBe('assistant');
  });
});
```

### Test Guidelines

1. **Test Names**: Use descriptive names that explain the scenario
2. **Test Structure**: Follow Arrange-Act-Assert pattern
3. **Mocking**: Use mocks for external dependencies
4. **Coverage**: Aim for >90% code coverage
5. **Performance**: Include performance regression tests
6. **Error Cases**: Test both success and failure scenarios

### Running Tests

```bash
# Run all tests
bun test

# Run specific test file
bun test kenny.test.ts

# Run with coverage
bun test --coverage

# Run in watch mode
bun test --watch

# Run performance tests
bun test performance/
```

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   git checkout -b fix/issue-description
   ```

2. **Make Changes**
   - Follow coding guidelines
   - Add/update tests
   - Update documentation
   - Ensure all tests pass

3. **Commit Messages**
   Use conventional commit format:
   ```
   type(scope): description

   [optional body]

   [optional footer]
   ```

   Examples:
   ```
   feat(kenny): add message persistence
   fix(consciousness): resolve memory leak in state manager
   docs(api): update provider interface documentation
   test(integration): add end-to-end workflow tests
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

### Pull Request Requirements

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] CI/CD checks passing
- [ ] Linked to relevant issue(s)

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Peer Review**: At least one maintainer review required
3. **Testing**: Reviewer tests functionality
4. **Approval**: Approved PRs are merged by maintainers

## Release Process

### Version Management

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Steps

1. **Prepare Release**
   ```bash
   # Update version
   npm version minor  # or major/patch
   
   # Update CHANGELOG.md
   # Update documentation
   ```

2. **Create Release Branch**
   ```bash
   git checkout -b release/v1.2.0
   git push origin release/v1.2.0
   ```

3. **Testing and QA**
   - Full test suite
   - Manual testing
   - Performance verification
   - Security review

4. **Tag and Release**
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```

5. **Publish**
   ```bash
   npm publish
   # or
   bun publish
   ```

### Release Notes

Each release includes:
- New features
- Bug fixes
- Breaking changes
- Upgrade instructions
- Performance improvements
- Security updates

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Discord**: Real-time chat (coming soon)
- **Email**: contact@asi-code.dev

### Getting Help

1. **Documentation**: Check docs/ directory first
2. **Examples**: Review examples/ directory
3. **Issues**: Search existing GitHub issues
4. **Discussions**: Ask in GitHub Discussions
5. **Support**: Email support@asi-code.dev

### Reporting Issues

When reporting bugs, please include:

```markdown
## Bug Description
Clear description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 12.0]
- Node.js: [e.g., 18.17.0]
- Bun: [e.g., 1.0.0]
- ASI-Code: [e.g., 1.2.0]

## Additional Context
Screenshots, logs, etc.
```

### Feature Requests

For feature requests, please include:
- Use case and motivation
- Proposed solution
- Alternatives considered
- Additional context

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributor graphs
- Special acknowledgments for significant contributions

Thank you for contributing to ASI-Code! 🚀