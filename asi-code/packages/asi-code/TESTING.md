# ASI-Code Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the ASI-Code framework. Our testing approach ensures reliability, performance, security, and maintainability across all components.

## Testing Framework

We use **Vitest** as our primary testing framework, complemented by specialized tools for different testing scenarios:

- **Unit Tests**: Vitest with mocking capabilities
- **Integration Tests**: Vitest with real system integration
- **End-to-End Tests**: Playwright for browser-based testing
- **Performance Tests**: Vitest benchmarking with custom performance utilities
- **Security Tests**: Vitest with specialized security testing utilities

## Test Structure

```
test/
├── unit/                     # Unit tests for individual components
│   ├── kenny/               # Kenny Integration Pattern tests
│   ├── provider/            # ASI1 Provider tests
│   ├── tool/                # Tool Registry and built-in tools
│   ├── session/             # Session Management tests
│   ├── permission/          # Permission Manager tests
│   └── config/              # Configuration Manager tests
├── integration/             # Integration tests
│   ├── server-integration.test.ts
│   ├── tool-pipeline.test.ts
│   └── kenny-coordination.test.ts
├── e2e/                     # End-to-end tests
├── performance/             # Performance and load tests
├── security/                # Security and vulnerability tests
├── fixtures/                # Test data and fixtures
└── test-utils.ts           # Shared testing utilities
```

## Test Categories

### 1. Unit Tests

Unit tests focus on individual components in isolation with comprehensive mocking.

**Coverage Areas:**
- Kenny Integration Pattern (message bus, state manager)
- ASI1 Provider implementation
- Tool Registry and built-in tools
- Session Management system
- Permission Manager and safety protocols
- Configuration Manager

**Example:**
```typescript
describe('MessageBus', () => {
  let messageBus: MessageBus;
  
  beforeEach(() => {
    messageBus = new MessageBus();
  });
  
  it('should publish and receive events', async () => {
    const callback = vi.fn();
    messageBus.subscribe({ type: 'test.event' }, callback);
    
    await messageBus.publish({
      type: 'test.event',
      source: 'test',
      data: { message: 'Hello' }
    });
    
    expect(callback).toHaveBeenCalledOnce();
  });
});
```

**Running Unit Tests:**
```bash
npm run test:unit
npm run test:unit --coverage
npm run test:unit --watch
```

### 2. Integration Tests

Integration tests verify component interactions and end-to-end workflows.

**Coverage Areas:**
- Server functionality with real HTTP requests
- Tool execution pipeline
- Kenny subsystem coordination
- Database integration
- External service integration

**Example:**
```typescript
describe('Server Integration', () => {
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  
  beforeAll(async () => {
    server = createServer({ port: 3002 });
    request = supertest(`http://localhost:3002`);
  });
  
  it('should execute tools through API', async () => {
    const response = await request
      .post('/api/sessions/123/tools/read/execute')
      .send({
        parameters: { path: '/test/file.txt' },
        context: { permissions: ['read_files'] }
      })
      .expect(200);
      
    expect(response.body.success).toBe(true);
  });
});
```

**Running Integration Tests:**
```bash
npm run test:integration
```

### 3. Performance Tests

Performance tests measure system performance, identify bottlenecks, and prevent regressions.

**Coverage Areas:**
- Load testing for concurrent operations
- Tool execution benchmarks
- Memory leak detection
- API response time testing
- Resource utilization monitoring

**Example:**
```typescript
describe('Performance Tests', () => {
  bench('Tool execution performance', async () => {
    const promises = Array.from({ length: 100 }, () =>
      toolRegistry.execute('read', { path: '/test/file.txt' }, context)
    );
    
    const results = await Promise.all(promises);
    expect(results.every(r => r.success)).toBe(true);
  });
});
```

**Running Performance Tests:**
```bash
npm run test:performance
npm run benchmark
```

### 4. Security Tests

Security tests validate input sanitization, authorization, and vulnerability prevention.

**Coverage Areas:**
- Input validation and sanitization
- Authentication and authorization
- SQL injection prevention
- XSS prevention
- Path traversal protection
- Rate limiting
- Session security

**Example:**
```typescript
describe('Security Tests', () => {
  it('should prevent path traversal attacks', async () => {
    const maliciousPaths = [
      '../etc/passwd',
      '../../etc/passwd',
      '/etc/passwd'
    ];
    
    for (const path of maliciousPaths) {
      const result = await readTool.execute({ path }, context);
      expect(result.success).toBe(false);
      expect(result.error).toMatch(/traversal|blocked|denied/i);
    }
  });
});
```

**Running Security Tests:**
```bash
npm run test:security
npm audit
```

## Coverage Targets

We maintain high code coverage standards:

- **Overall Coverage**: 90%+ lines, branches, functions
- **Kenny Integration Pattern**: 95%+ (critical system component)
- **Permission Manager**: 95%+ (security-critical)
- **Tool Registry**: 90%+
- **Session Management**: 90%+
- **Provider Implementation**: 85%+

## Testing Utilities

### Mock Factories

```typescript
// Create mock providers, tools, contexts, and messages
const mockProvider = createMockProvider();
const mockTool = createMockTool();
const mockContext = createMockKennyContext();
const mockMessage = createMockKennyMessage('Hello, world!');
```

### Test Helpers

```typescript
// Utility functions for common test operations
const tempDir = createTempDir();
const eventEmitter = createMockEventEmitter();
const config = createMockConfig();
```

### Event Testing

```typescript
// Test event emission
await assertEventEmitted(emitter, 'test:event', expectedData);
```

### Console Capture

```typescript
// Capture console output for testing
const consoleSpy = captureConsole();
// ... perform operations
expect(consoleSpy.logs).toContain('expected message');
consoleSpy.restore();
```

## Test Data Management

### Fixtures

Test fixtures are stored in `/test/fixtures/` and provide consistent test data:

```typescript
// Load test fixtures
import { loadFixture } from './fixtures/loader.js';

const testUser = loadFixture('users/test-user.json');
const testSession = loadFixture('sessions/active-session.json');
```

### File System Mocking

We use `memfs` for file system operations in tests:

```typescript
import { vol } from 'memfs';

beforeEach(() => {
  vol.fromJSON({
    '/test/file.txt': 'test content',
    '/data/config.json': JSON.stringify({ key: 'value' })
  });
});

afterEach(() => {
  vol.reset();
});
```

## Continuous Integration

### GitHub Actions Workflow

Our CI/CD pipeline runs comprehensive tests on every push and pull request:

```yaml
# .github/workflows/test.yml
jobs:
  unit-tests:
    # Run unit tests on multiple Node.js and Bun versions
  integration-tests:
    # Run integration tests with real services
  e2e-tests:
    # Run end-to-end tests with Playwright
  performance-tests:
    # Run performance benchmarks (main branch only)
  security-tests:
    # Run security tests and audits
  coverage-report:
    # Generate and upload coverage reports
```

### Coverage Reporting

We use Codecov for coverage reporting and tracking:

- Coverage reports are generated for each test suite
- Combined coverage reports show overall project health
- Coverage badges are displayed in the README
- Pull requests show coverage diff

## Running Tests

### All Tests

```bash
# Run all test suites
npm run test:all

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### Specific Test Suites

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# End-to-end tests
npm run test:e2e

# Performance tests
npm run test:performance

# Security tests
npm run test:security
```

### Test Debugging

```bash
# Run tests with verbose output
npm run test -- --verbose

# Run specific test file
npm run test -- kenny.test.ts

# Run tests matching pattern
npm run test -- --grep "should handle errors"

# Run tests with debugging
npm run test -- --inspect-brk
```

## Best Practices

### Test Organization

1. **Group related tests** using `describe()` blocks
2. **Use descriptive test names** that explain the scenario
3. **Include both positive and negative test cases**
4. **Test edge cases and error conditions**
5. **Keep tests focused and atomic**

### Test Data

1. **Use mock factories** from `test-utils.ts`
2. **Create realistic test data** that represents actual usage
3. **Avoid hardcoded values** where possible
4. **Clean up test data** after each test
5. **Use fixtures** for complex test scenarios

### Async Testing

1. **Always use `await`** for async operations
2. **Handle promise rejections** appropriately
3. **Use proper timeouts** for event testing
4. **Clean up async resources** in `afterEach`

### Error Testing

1. **Test both expected and unexpected errors**
2. **Verify error messages and types**
3. **Test error recovery mechanisms**
4. **Ensure system stability after errors**

## Performance Considerations

- Tests should run quickly (< 30s for full suite)
- Use mocks to avoid external dependencies
- Clean up resources to prevent memory leaks
- Avoid unnecessary async operations
- Use parallelization where possible

## Troubleshooting

### Common Issues

1. **Tests hanging**: Check for unresolved promises or missing `await`
2. **Mock not working**: Ensure mock is created in `beforeEach`
3. **File system tests failing**: Check permissions and cleanup
4. **Event tests timing out**: Increase timeout or check event names

### Debug Tips

1. Use `console.log` for debugging (captured in tests)
2. Add `--verbose` flag for detailed output
3. Run single tests to isolate issues
4. Check test dependencies and order

## Contributing to Tests

When adding new features:

1. **Write tests first** (TDD approach)
2. **Test all code paths** (success, failure, edge cases)
3. **Use existing utilities** from `test-utils.ts`
4. **Document complex test scenarios**
5. **Update this documentation** as needed

### Test Template

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('Component Name', () => {
  let component: ComponentType;
  
  beforeEach(() => {
    component = createComponent();
  });
  
  afterEach(async () => {
    await component.cleanup();
  });
  
  it('should do something correctly', async () => {
    // Arrange
    const input = 'test input';
    
    // Act
    const result = await component.doSomething(input);
    
    // Assert
    expect(result).toBeDefined();
    expect(result.success).toBe(true);
  });
  
  it('should handle errors gracefully', async () => {
    await expect(component.doInvalidOperation())
      .rejects.toThrow('Expected error message');
  });
});
```

## Metrics and Monitoring

### Coverage Metrics

- Line coverage: Percentage of executable lines covered
- Branch coverage: Percentage of execution branches covered
- Function coverage: Percentage of functions called
- Statement coverage: Percentage of statements executed

### Performance Metrics

- Test execution time
- Memory usage during tests
- Resource utilization
- Benchmark results over time

### Quality Metrics

- Test reliability (flakiness detection)
- Test maintenance burden
- Code-to-test ratio
- Bug detection effectiveness

## Future Enhancements

- [ ] Property-based testing for complex logic
- [ ] Visual regression testing for CLI output
- [ ] Automated test generation
- [ ] Mutation testing for test quality
- [ ] Chaos engineering tests
- [ ] Contract testing for API boundaries

---

For questions about testing or to contribute improvements to our testing strategy, please reach out to the development team or create an issue in the repository.