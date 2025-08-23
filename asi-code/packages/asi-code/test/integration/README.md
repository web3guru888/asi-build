# ASI-Code Integration Test Suite

A comprehensive integration test suite for ASI-Code that validates all system components working together in realistic scenarios.

## Overview

This integration test suite covers:

- **API Integration**: All HTTP endpoints, request/response handling, error scenarios
- **WebSocket Integration**: Real-time messaging, connection management, streaming
- **Database Integration**: CRUD operations, transactions, migrations, connection pooling
- **Provider Integration**: ASI1, Anthropic, and OpenAI API integrations with fallback
- **Tool System Integration**: All 8 built-in tools with permission validation
- **Authentication & Permissions**: Auth flows, RBAC, session security, audit logging
- **Error Handling & Recovery**: Fault tolerance, graceful degradation, circuit breakers
- **Performance & Load Testing**: Throughput, response times, resource utilization

## Test Architecture

### Test Structure

```
test/integration/
├── README.md                              # This file
├── setup.ts                              # Global test setup
├── integration-test-runner.ts            # Test orchestration utility
├── api-integration.test.ts               # API endpoint testing
├── websocket-integration.test.ts         # WebSocket functionality
├── database-integration.test.ts          # Database operations
├── provider-integration.test.ts          # AI provider integrations
├── tool-integration.test.ts              # Tool system testing
├── auth-permission-integration.test.ts   # Security & permissions
├── error-recovery-integration.test.ts    # Error handling & recovery
└── performance-load-integration.test.ts  # Performance & load testing
```

### Test Categories

#### 1. API Integration Tests (`api-integration.test.ts`)
- **Health & Status Endpoints**: System health, component status
- **Session Management**: CRUD operations, lifecycle, isolation
- **Provider API**: Text generation, streaming, provider switching
- **Tool API**: Execution, parameter validation, error handling
- **SSE Events**: Server-sent events, real-time updates
- **Error Handling**: Malformed requests, rate limiting, validation

#### 2. WebSocket Integration Tests (`websocket-integration.test.ts`)
- **Connection Management**: Establishment, heartbeat, graceful closure
- **Real-time Messaging**: Broadcasting, channels, subscriptions
- **AI Streaming**: Provider streaming integration via WebSocket
- **Tool Execution**: Real-time tool execution with progress updates
- **Session Management**: WebSocket-based session operations
- **Error Handling**: Connection failures, message corruption, recovery

#### 3. Database Integration Tests (`database-integration.test.ts`)
- **Connection Management**: Pool management, health checks, failover
- **CRUD Operations**: Create, read, update, delete with validation
- **Transaction Management**: ACID properties, rollback, nested transactions
- **Migration System**: Schema versioning, rollback, failure handling
- **Performance**: Query optimization, bulk operations, indexing
- **Data Integrity**: Constraints, validation, consistency

#### 4. Provider Integration Tests (`provider-integration.test.ts`)
- **Provider Initialization**: Configuration, authentication, health checks
- **Text Generation**: Request/response handling, parameter validation
- **Streaming**: Real-time text streaming, chunked responses
- **Error Handling**: Rate limiting, timeouts, fallback mechanisms
- **Load Balancing**: Provider switching, failure detection
- **Monitoring**: Performance metrics, usage tracking

#### 5. Tool Integration Tests (`tool-integration.test.ts`)
- **Built-in Tools**: All 8 tools (bash, read, write, edit, search, delete, move, list)
- **Permission Validation**: Access control, resource restrictions
- **Error Handling**: Invalid parameters, file system errors, timeouts
- **Concurrent Execution**: Thread safety, resource conflicts
- **Performance**: Execution times, resource utilization
- **Security**: Path traversal protection, command injection prevention

#### 6. Authentication & Permission Tests (`auth-permission-integration.test.ts`)
- **Authentication Methods**: Password, API keys, JWT tokens
- **Permission Validation**: Role-based access, resource restrictions
- **Session Security**: Isolation, timeout, hijacking prevention
- **Audit Logging**: Security events, violation tracking
- **Rate Limiting**: User-based limits, security policies
- **Multi-tenant Security**: Data isolation, cross-tenant protection

#### 7. Error Recovery Tests (`error-recovery-integration.test.ts`)
- **Network Failures**: Connection recovery, timeout handling
- **Component Failures**: Graceful degradation, circuit breakers
- **Resource Exhaustion**: Memory leaks, connection limits
- **System Recovery**: Automatic recovery, manual intervention
- **Monitoring**: Error tracking, alerting, metrics

#### 8. Performance & Load Tests (`performance-load-integration.test.ts`)
- **Baseline Performance**: Single request response times
- **Load Testing**: Multiple concurrent users, sustained load
- **Stress Testing**: Resource limits, breaking points
- **Endurance Testing**: Extended duration, memory stability
- **Spike Testing**: Sudden load increases, recovery
- **Resource Monitoring**: Memory, CPU, network utilization

## Running Tests

### Prerequisites

1. **Node.js 18+** with npm/bun
2. **PostgreSQL** (for database tests)
3. **Redis** (for caching tests)
4. **Environment Variables**:
   ```bash
   export NODE_ENV=test
   export DATABASE_URL=postgresql://test:test@localhost:5432/asi_code_test
   export REDIS_URL=redis://localhost:6379
   export ANTHROPIC_API_KEY=your_test_key
   export OPENAI_API_KEY=your_test_key
   ```

### Quick Start

```bash
# Run all integration tests
npm run test:integration

# Run specific test suite
npm run test:integration -- api-integration
npm run test:integration -- websocket-integration
npm run test:integration -- performance-load

# Run with coverage
npm run test:integration:coverage

# Run in watch mode
npm run test:integration:watch
```

### Advanced Usage

```bash
# Run with verbose output
npm run test:integration -- --reporter=verbose

# Run only failed tests
npm run test:integration -- --retry-failed

# Run performance tests only
npm run test:integration -- performance-load-integration.test.ts

# Generate detailed reports
npm run test:integration -- --reporter=html,json,junit
```

## Configuration

### Test Runner Configuration

The integration test runner can be configured via `integration-test-runner.ts`:

```typescript
const config: TestRunnerConfig = {
  suites: {
    'api-integration': {
      enabled: true,
      timeout: 60000,
      retries: 2,
      parallel: false
    }
    // ... other suites
  },
  global: {
    timeout: 300000,
    retries: 1,
    bail: false,
    coverage: true
  },
  reporting: {
    formats: ['json', 'html', 'junit'],
    outputDir: './test-reports/integration'
  }
};
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Environment mode | `test` |
| `LOG_LEVEL` | Logging verbosity | `error` |
| `TEST_TIMEOUT` | Global test timeout | `300000` |
| `TEST_RETRIES` | Number of retries | `2` |
| `TEST_PARALLEL` | Parallel execution | `false` |
| `DATABASE_URL` | Test database connection | `postgresql://localhost:5432/test` |
| `REDIS_URL` | Test Redis connection | `redis://localhost:6379` |

## Test Data Management

### Mock Data

Tests use controlled mock data to ensure predictable results:

- **Users**: Predefined test users with different roles
- **Sessions**: Generated session data with known states
- **Files**: Virtual file system using `memfs`
- **Providers**: Mock AI providers with configurable responses

### Test Isolation

Each test suite runs in isolation:

- **Database**: Separate test database with cleanup
- **File System**: Virtual file system reset between tests
- **Network**: Mock HTTP clients to avoid external dependencies
- **Ports**: Unique ports for each test server instance

## Performance Benchmarks

### Response Time Targets

| Operation | Target (95th percentile) |
|-----------|-------------------------|
| Health Check | < 100ms |
| Session Creation | < 500ms |
| Tool Execution | < 1000ms |
| File Read (1KB) | < 200ms |
| Provider Request | < 2000ms |

### Throughput Targets

| Load Level | Concurrent Users | Target RPS |
|------------|------------------|------------|
| Light | 10 | 50+ |
| Medium | 50 | 20+ |
| Heavy | 100 | 10+ |

### Resource Limits

| Resource | Limit |
|----------|-------|
| Memory Growth | < 100MB over 30s |
| Connection Pool | < 90% utilization |
| CPU Usage | < 80% sustained |

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check for port usage
lsof -i :3003-3007

# Kill processes using test ports
pkill -f "node.*test"
```

#### 2. Database Connection Errors
```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432

# Reset test database
dropdb asi_code_test && createdb asi_code_test
```

#### 3. Memory Issues
```bash
# Monitor memory usage
node --max-old-space-size=4096 npm run test:integration

# Enable garbage collection logs
node --trace-gc npm run test:integration
```

#### 4. Test Timeouts
```bash
# Increase timeout for slow tests
VITEST_TIMEOUT=600000 npm run test:integration

# Run tests sequentially
npm run test:integration -- --no-threads
```

### Debug Mode

Enable debug logging for detailed test execution:

```bash
# Enable all debug logs
DEBUG=* npm run test:integration

# Enable specific component logs
DEBUG=asi:server,asi:tool npm run test:integration

# Enable test runner logs
DEBUG=test:* npm run test:integration
```

### Performance Profiling

Profile test performance to identify bottlenecks:

```bash
# CPU profiling
node --prof npm run test:integration
node --prof-process isolate-*.log > profile.txt

# Memory profiling
node --inspect npm run test:integration
# Open chrome://inspect in Chrome
```

## Contributing

### Adding New Tests

1. **Choose the appropriate test file** based on the component being tested
2. **Follow the existing test structure** with proper setup/teardown
3. **Use descriptive test names** that explain the scenario
4. **Include both positive and negative test cases**
5. **Add performance assertions** where appropriate

### Test Patterns

```typescript
describe('Component Integration', () => {
  beforeEach(async () => {
    // Setup test environment
    await setupTestData();
  });

  afterEach(async () => {
    // Cleanup resources
    await cleanupTestData();
  });

  it('should handle normal operation correctly', async () => {
    // Arrange
    const testData = createTestData();

    // Act
    const result = await performOperation(testData);

    // Assert
    expect(result).toMatchObject({
      success: true,
      data: expect.any(Object)
    });
  });

  it('should handle error conditions gracefully', async () => {
    // Test error scenarios
    await expect(performInvalidOperation()).rejects.toThrow();
  });
});
```

### Performance Tests

```typescript
it('should meet performance targets', async () => {
  const startTime = performance.now();
  
  const results = await Promise.all(
    Array.from({ length: 100 }, () => performOperation())
  );
  
  const duration = performance.now() - startTime;
  const throughput = results.length / (duration / 1000);
  
  expect(throughput).toBeGreaterThan(50); // 50 RPS target
  expect(duration).toBeLessThan(5000); // 5s max duration
});
```

## Monitoring & Reporting

### Test Reports

Integration test reports are generated in multiple formats:

- **HTML Report**: `./test-reports/integration/results.html`
- **JSON Report**: `./test-reports/integration/results.json`
- **JUnit XML**: `./test-reports/integration/results.xml`
- **Coverage Report**: `./coverage/integration/index.html`

### Metrics Collection

The test suite collects comprehensive metrics:

- **Response Times**: Min, max, average, percentiles
- **Throughput**: Requests per second, concurrent users
- **Resource Usage**: Memory, CPU, network utilization
- **Error Rates**: Failed requests, error types
- **System Health**: Component status, availability

### Continuous Integration

Integration tests are designed for CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Integration Tests
  run: |
    npm run test:integration
    npm run test:integration:coverage
  env:
    NODE_ENV: test
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
    REDIS_URL: ${{ secrets.TEST_REDIS_URL }}

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage/integration/lcov.info
```

## Best Practices

### 1. Test Independence
- Each test should be independent and not rely on others
- Use proper setup/teardown to ensure clean state
- Avoid shared state between tests

### 2. Realistic Scenarios
- Test real-world usage patterns
- Include edge cases and error conditions
- Use realistic data volumes and concurrency

### 3. Performance Awareness
- Include performance assertions in tests
- Monitor resource usage during tests
- Set realistic performance targets

### 4. Error Testing
- Test all error conditions and recovery scenarios
- Verify error messages and status codes
- Test graceful degradation under load

### 5. Security Testing
- Include security-focused test scenarios
- Test permission boundaries and access controls
- Validate input sanitization and validation

## Support

For questions or issues with the integration test suite:

1. **Check the troubleshooting section** above
2. **Review test logs** in `./test-reports/integration/`
3. **Create an issue** with test output and system information
4. **Contact the development team** for urgent issues

---

**Last Updated**: December 2024  
**Test Suite Version**: 1.0.0  
**ASI-Code Version**: Latest