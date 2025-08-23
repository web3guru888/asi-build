# ASI-Code Testing Infrastructure

This document provides comprehensive guidance on the ASI-Code testing infrastructure, including setup, best practices, and usage examples.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Types](#test-types)
- [Setup & Configuration](#setup--configuration)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Utilities](#test-utilities)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The ASI-Code testing infrastructure is built with modern tools and follows industry best practices to ensure comprehensive test coverage and reliable CI/CD pipelines.

### Technology Stack

- **Unit/Integration Tests**: Vitest with TypeScript support
- **E2E Tests**: Playwright with multi-browser support
- **API Tests**: Supertest integration
- **Performance Tests**: Custom benchmarking suite
- **Security Tests**: Automated vulnerability scanning
- **Mocking**: Advanced mock generators and fixtures
- **Coverage**: V8 coverage with detailed reporting

### Test Architecture

```
test/
├── fixtures/           # Test data and mock objects
├── mocks/             # Advanced mocking utilities
├── database/          # Database testing utilities
├── api/               # API testing framework
├── performance/       # Performance benchmarking
├── e2e/               # End-to-end tests
├── unit/              # Unit tests
├── integration/       # Integration tests
├── security/          # Security tests
└── utils/             # Test utilities and helpers
```

## 🧪 Test Types

### 1. Unit Tests
Fast, isolated tests for individual functions and components.

```bash
# Run unit tests
bun run test:unit

# Run with coverage
bun run test:unit --coverage

# Watch mode
bun run test:unit --watch
```

### 2. Integration Tests
Tests that verify component interactions and API endpoints.

```bash
# Run integration tests
bun run test:integration

# Run with database setup
DATABASE_URL=postgresql://test:test@localhost:5432/test_db bun run test:integration
```

### 3. End-to-End Tests
Browser-based tests using Playwright across multiple browsers.

```bash
# Run E2E tests
bun run test:e2e

# Run specific browser
bunx playwright test --project=chromium

# Run in headed mode
bunx playwright test --headed

# Debug mode
bunx playwright test --debug
```

### 4. Performance Tests
Benchmarking and load testing with detailed metrics.

```bash
# Run performance tests
bun run test:performance

# Run benchmarks only
bun run benchmark

# Load testing
bun run test:load
```

### 5. Security Tests
Automated security scanning and vulnerability testing.

```bash
# Run security tests
bun run test:security

# Run audit only
bun audit
```

## ⚙️ Setup & Configuration

### Prerequisites

```bash
# Install dependencies
bun install

# Setup test environment
cp .env.example .env.test

# Setup test database (if using PostgreSQL)
createdb asi_code_test
```

### Environment Variables

```env
# Test environment
NODE_ENV=test
LOG_LEVEL=error

# Database
DATABASE_URL=postgresql://test:test@localhost:5432/asi_code_test
REDIS_URL=redis://localhost:6379/1

# API Keys (test values)
ANTHROPIC_API_KEY=test-anthropic-key
OPENAI_API_KEY=test-openai-key

# Security
JWT_SECRET=test-jwt-secret-very-long-and-secure
ENCRYPTION_KEY=test-encryption-key-32-chars-long
```

### Vitest Configuration

The test infrastructure includes multiple Vitest configurations:

- `vitest.config.ts` - Base configuration
- `vitest.unit.config.ts` - Unit tests
- `vitest.integration.config.ts` - Integration tests
- `vitest.performance.config.ts` - Performance tests
- `vitest.security.config.ts` - Security tests

### Coverage Thresholds

```typescript
// Coverage thresholds by module
{
  global: { branches: 80, functions: 80, lines: 80, statements: 80 },
  'src/kenny/': { branches: 90, functions: 90, lines: 90, statements: 90 },
  'src/security/': { branches: 95, functions: 95, lines: 95, statements: 95 }
}
```

## 🏃 Running Tests

### All Tests
```bash
# Run all test suites
bun run test:all

# Quick test run (unit only)
bun run test

# With coverage
bun run test:coverage
```

### Specific Test Suites
```bash
# Unit tests only
bun run test:unit

# Integration tests with database
bun run test:integration

# E2E tests (all browsers)
bun run test:e2e

# Performance tests
bun run test:performance

# Security tests
bun run test:security
```

### Test Filtering
```bash
# Run tests matching pattern
bun run test:unit kenny

# Run specific test file
bun run test:unit test/unit/kenny/message-bus.test.ts

# Run tests with tag
bun run test:unit --grep="@integration"
```

### Debug Mode
```bash
# Debug unit tests
bun run test:unit --inspect-brk

# Debug E2E tests
bunx playwright test --debug

# UI mode for tests
bun run test:ui
```

## ✍️ Writing Tests

### Unit Test Example

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { KennyFixtures, createMockProvider } from '@test/fixtures';
import { MessageBus } from '@/kenny/message-bus';

describe('MessageBus', () => {
  let messageBus: MessageBus;
  
  beforeEach(() => {
    messageBus = new MessageBus();
  });

  it('should publish events to subscribers', async () => {
    const callback = vi.fn();
    messageBus.subscribe({ type: 'test.event' }, callback);
    
    await messageBus.publish({
      type: 'test.event',
      source: 'test',
      data: { message: 'Hello World' }
    });
    
    expect(callback).toHaveBeenCalledOnce();
    expect(callback.mock.calls[0][0]).toMatchObject({
      type: 'test.event',
      data: { message: 'Hello World' }
    });
  });
});
```

### Integration Test Example

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { ApiTestHelpers, DatabaseTestHelpers } from '@test';
import { createServer } from '@/server';

describe('API Integration', () => {
  let client: ApiTestClient;
  let dbManager: DatabaseTestManager;

  beforeAll(async () => {
    const app = createServer();
    client = ApiTestHelpers.createClient(app);
    
    dbManager = DatabaseTestHelpers.createManager(database);
    await dbManager.setup();
  });

  afterAll(async () => {
    await dbManager.cleanup();
  });

  it('should create and retrieve a session', async () => {
    // Create session
    const createResponse = await client.post('/sessions', {
      userId: 'test-user'
    }).expect(201);

    expect(createResponse.body).toHaveProperty('id');
    
    // Retrieve session
    const getResponse = await client
      .get(`/sessions/${createResponse.body.id}`)
      .expect(200);
      
    expect(getResponse.body.userId).toBe('test-user');
  });
});
```

### E2E Test Example

```typescript
import { test, expect } from '@playwright/test';

test.describe('Kenny Chat Interface', () => {
  test('should send and receive messages', async ({ page }) => {
    await page.goto('/chat');
    
    // Send a message
    await page.fill('[data-testid="message-input"]', 'Hello Kenny!');
    await page.click('[data-testid="send-button"]');
    
    // Wait for response
    await expect(page.locator('[data-testid="message-response"]')).toBeVisible();
    
    // Verify response content
    const response = await page.textContent('[data-testid="message-response"]');
    expect(response).toContain('Hello');
  });
});
```

### Performance Test Example

```typescript
import { bench, describe } from 'vitest';
import { PerformanceTestHelpers } from '@test/performance';

describe('Kenny Performance', () => {
  bench('message processing', async () => {
    const kenny = new Kenny();
    await kenny.processMessage('test message');
  }, { iterations: 1000 });

  bench('large dataset processing', async () => {
    const data = PerformanceTestHelpers.generateTestData.large();
    await processLargeDataset(data);
  });
});
```

## 🔧 Test Utilities

### Fixtures
Pre-built test data and mock objects:

```typescript
import { KennyFixtures, ProviderFixtures, ToolFixtures } from '@test/fixtures';

// Create test data
const context = KennyFixtures.defaultContext();
const message = KennyFixtures.userMessage('Hello');
const provider = ProviderFixtures.anthropicConfig();
```

### Mocks
Advanced mocking utilities:

```typescript
import { Mocks } from '@test/mocks';

// Mock file system
const mockFs = new Mocks.FileSystem();
mockFs.addFile('/test/file.txt', 'content');

// Mock HTTP client
const mockHttp = new Mocks.HttpClient();
mockHttp.addResponse('GET', '/api/test', { status: 'ok' });

// Mock database
const mockDb = new Mocks.Database();
mockDb.insertData('users', [{ id: '1', name: 'Test User' }]);
```

### Database Testing
Database utilities for testing:

```typescript
import { DatabaseTestHelpers } from '@test/database';

const { manager, factory, utils } = await DatabaseTestHelpers.setupTestEnvironment(db);

// Create test data
const user = await factory.createUser();
const session = await factory.createSession(user.id);

// Verify data
const userCount = await utils.countRecords('users');
expect(userCount).toBe(1);
```

### API Testing
API testing framework:

```typescript
import { ApiTestHelpers } from '@test/api';

const client = ApiTestHelpers.createClient(app);

// Test authentication
const authTests = client.buildAuthTests(validCredentials, invalidCredentials);
await authTests.testValidLogin();

// Test CRUD operations
const crudTests = client.buildCrudTests('users', userData, updateData);
await crudTests.testCreate();
```

## 🚀 CI/CD Integration

### GitHub Actions Workflow

The testing infrastructure integrates with GitHub Actions for automated testing:

```yaml
# Example workflow integration
- name: Run Unit Tests
  run: bun run test:unit --coverage

- name: Run Integration Tests
  run: bun run test:integration
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}

- name: Run E2E Tests
  run: bun run test:e2e

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage/lcov.info
```

### Coverage Requirements

Tests must maintain coverage thresholds:
- **Global**: 80% (branches, functions, lines, statements)
- **Kenny Module**: 90%
- **Security Module**: 95%

### Test Results

Test results are automatically:
- Published as JUnit XML for CI integration
- Uploaded as HTML reports for detailed analysis
- Sent to Codecov for coverage tracking
- Summarized in GitHub PR comments

## 💡 Best Practices

### Test Organization
- Group related tests in `describe` blocks
- Use descriptive test names that explain the behavior
- Follow the AAA pattern: Arrange, Act, Assert
- Keep tests focused and independent

### Test Data
- Use fixtures for consistent test data
- Avoid hardcoded values; use constants or generators
- Clean up test data between tests
- Use factory functions for complex object creation

### Mocking
- Mock external dependencies and side effects
- Use real implementations for internal modules when possible
- Keep mocks simple and focused
- Verify mock interactions when relevant

### Performance
- Keep unit tests fast (< 1 second each)
- Use appropriate test isolation
- Run expensive tests (E2E, performance) separately
- Monitor test execution time and optimize slow tests

### Coverage
- Aim for high coverage but focus on quality
- Test edge cases and error conditions
- Don't test implementation details
- Use coverage reports to identify untested code

## 🔍 Troubleshooting

### Common Issues

#### Tests Failing Locally
```bash
# Clear node modules and reinstall
rm -rf node_modules bun.lockb
bun install

# Reset test database
dropdb asi_code_test && createdb asi_code_test

# Clear test cache
rm -rf coverage test-results
```

#### E2E Tests Timing Out
```bash
# Increase timeout in playwright.config.ts
timeout: 60 * 1000

# Run with headed browser to debug
bunx playwright test --headed --timeout=0
```

#### Coverage Issues
```bash
# Generate detailed coverage report
bun run test:coverage --reporter=html

# Exclude files from coverage
# Update vitest.config.ts exclude patterns
```

#### Database Connection Issues
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Reset test database
npm run db:reset:test
```

### Debug Tips

1. **Use Debug Mode**: Run tests with `--debug` or `--inspect-brk`
2. **Console Logging**: Add `console.log` statements (remove before commit)
3. **Test Isolation**: Run single test files to isolate issues
4. **Check Environment**: Verify environment variables are set correctly
5. **Update Dependencies**: Ensure all testing dependencies are up to date

### Getting Help

- Check the [GitHub Issues](https://github.com/asi-team/asi-code/issues) for known problems
- Review the [API Documentation](./API.md) for usage examples
- Join our [Discord](https://discord.gg/asi-code) for community support
- Create a detailed issue report with reproduction steps

## 📊 Test Metrics

The testing infrastructure tracks various metrics:

- **Test Execution Time**: Monitor performance of test suites
- **Coverage Trends**: Track coverage changes over time  
- **Flaky Test Detection**: Identify unreliable tests
- **Performance Benchmarks**: Monitor application performance
- **Security Scan Results**: Track vulnerability findings

These metrics are available in:
- GitHub Actions workflow summaries
- Codecov dashboard
- Test result artifacts
- Performance benchmark reports

---

For more information, see:
- [API Documentation](./API.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Development Setup](./DEVELOPMENT_GUIDE.md)