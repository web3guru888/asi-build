# ASI-Code Test Suite

This directory contains comprehensive tests for the ASI-Code system, covering all major components and integration scenarios.

## Test Structure

### Core Component Tests
- **`kenny.test.ts`** - Tests for the Kenny Integration Pattern
- **`consciousness.test.ts`** - Tests for the Consciousness Engine
- **`sat.test.ts`** - Tests for the Software Architecture Taskforce (SAT)
- **`app.test.ts`** - Tests for App Context and Lifecycle Manager

### Integration Tests
- **`integration.test.ts`** - End-to-end system integration tests

### Utilities
- **`test-utils.ts`** - Helper functions, mocks, and utilities for testing

## Running Tests

### All Tests
```bash
bun test
```

### Specific Test File
```bash
bun test kenny.test.ts
bun test consciousness.test.ts
bun test sat.test.ts
bun test app.test.ts
bun test integration.test.ts
```

### With Coverage
```bash
bun test --coverage
```

### Watch Mode
```bash
bun test --watch
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Use mocks for dependencies
- Focus on specific functionality

### Integration Tests
- Test component interactions
- Test end-to-end workflows
- Verify system behavior

### Error Handling Tests
- Test error conditions
- Verify graceful failure handling
- Test recovery mechanisms

## Test Utilities

The `test-utils.ts` file provides:

- **Mock Factories**: Create mock providers, tools, contexts, and messages
- **Test Helpers**: Utility functions for common test operations
- **Event Testing**: Utilities for testing event emission
- **Console Capture**: Capture console output for testing
- **Configuration**: Mock configurations for testing

### Example Usage

```typescript
import { 
  createMockProvider,
  createMockKennyContext,
  createMockKennyMessage,
  assertEventEmitted
} from './test-utils.js';

// Create mocks
const mockProvider = createMockProvider();
const mockContext = createMockKennyContext();
const mockMessage = createMockKennyMessage('Hello, world!');

// Test event emission
await assertEventEmitted(emitter, 'test:event', expectedData);
```

## Test Coverage Areas

### Kenny Integration Pattern
- ✅ Context creation and management
- ✅ Message processing
- ✅ Event emission
- ✅ Subsystem integration
- ✅ Error handling

### Consciousness Engine
- ✅ Provider integration
- ✅ State management
- ✅ Memory operations
- ✅ Consciousness processing
- ✅ Event handling

### SAT Engine
- ✅ Pattern detection
- ✅ Metrics calculation
- ✅ Project analysis
- ✅ Recommendation generation
- ✅ File handling

### App Context & Lifecycle
- ✅ Component registration
- ✅ Dependency management
- ✅ Startup/shutdown sequences
- ✅ Health checks
- ✅ Error recovery

### Integration Scenarios
- ✅ Full system initialization
- ✅ Component interaction
- ✅ Tool execution workflows
- ✅ Permission system integration
- ✅ Error propagation

## Test Configuration

Tests use the following configuration:

- **Test Framework**: Bun's built-in test runner
- **Mocking**: Bun's `mock()` function
- **Assertions**: Bun's `expect()` API
- **Async Testing**: Native Promise/async-await support
- **Test Isolation**: Each test has proper setup/teardown

## Best Practices

### Test Organization
1. Group related tests using `describe()` blocks
2. Use descriptive test names that explain the scenario
3. Include both positive and negative test cases
4. Test edge cases and error conditions

### Test Data
1. Use the mock factories in `test-utils.ts`
2. Create realistic test data
3. Avoid hardcoded values where possible
4. Clean up test data after each test

### Async Testing
1. Always use `await` for async operations
2. Handle promise rejections appropriately
3. Use proper timeouts for event testing
4. Clean up async resources in `afterEach`

### Error Testing
1. Test both expected and unexpected errors
2. Verify error messages and types
3. Test error recovery mechanisms
4. Ensure system stability after errors

## Contributing to Tests

When adding new features:

1. **Write Tests First**: Follow TDD principles
2. **Test All Paths**: Cover success, failure, and edge cases
3. **Use Existing Utilities**: Leverage `test-utils.ts` helpers
4. **Document Complex Tests**: Add comments for complex scenarios
5. **Update This README**: Keep documentation current

### Test Template

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { createMockProvider } from './test-utils.js';

describe('Component Name', () => {
  let component: any;

  beforeEach(() => {
    // Setup
    component = createComponent();
  });

  afterEach(async () => {
    // Cleanup
    await component.cleanup();
  });

  it('should do something correctly', () => {
    // Arrange
    const input = 'test input';
    
    // Act
    const result = component.doSomething(input);
    
    // Assert
    expect(result).toBeDefined();
    expect(result).toBe('expected output');
  });

  it('should handle errors gracefully', async () => {
    // Test error conditions
    await expect(component.doInvalidOperation()).rejects.toThrow('Expected error message');
  });
});
```

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

## Performance Considerations

- Tests should run quickly (< 10s for full suite)
- Use mocks to avoid external dependencies
- Clean up resources to prevent memory leaks
- Avoid unnecessary async operations

## Future Enhancements

- [ ] Performance benchmarking tests
- [ ] Load testing for concurrent operations
- [ ] Property-based testing for complex logic
- [ ] Visual regression testing for CLI output
- [ ] Automated test generation