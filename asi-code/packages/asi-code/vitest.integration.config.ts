import { defineConfig } from 'vitest/config';
import baseConfig from './vitest.config';

export default defineConfig({
  ...baseConfig,
  test: {
    ...baseConfig.test,
    include: [
      'test/integration/**/*.{test,spec}.{ts,tsx}',
      'test/integration/*.{test,spec}.{ts,tsx}'
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/unit/**',
      '**/e2e/**',
      '**/performance/**',
      '**/security/**',
      '**/integration-test-runner.ts' // Exclude runner utility
    ],
    name: 'integration',
    environment: 'node',
    testTimeout: 300000, // 5 minutes for comprehensive integration tests
    hookTimeout: 30000,  // 30 seconds for setup/teardown
    setupFiles: ['./test/integration/setup.ts'],
    coverage: {
      ...baseConfig.test?.coverage,
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: 'coverage/integration',
      include: [
        'src/**/*.{ts,js}',
        '!src/**/*.d.ts',
        '!src/**/index.ts',
        '!src/**/*.test.ts',
        '!src/**/*.spec.ts'
      ],
      exclude: [
        'src/**/*.test.ts',
        'src/**/*.spec.ts',
        'src/**/test-*.ts',
        'src/**/mock-*.ts'
      ],
      thresholds: {
        global: {
          branches: 75,
          functions: 80,
          lines: 80,
          statements: 80
        },
        // Specific thresholds for critical components
        'src/server/**': {
          branches: 85,
          functions: 90,
          lines: 90,
          statements: 90
        },
        'src/tool/**': {
          branches: 80,
          functions: 85,
          lines: 85,
          statements: 85
        },
        'src/permission/**': {
          branches: 90,
          functions: 95,
          lines: 95,
          statements: 95
        },
        'src/provider/**': {
          branches: 75,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false, // Allow parallel execution for performance
        minThreads: 1,
        maxThreads: 4
      }
    },
    // Retry configuration for flaky integration tests
    retry: 2,
    // Bail on first failure for faster feedback
    bail: false,
    // Custom reporters for integration test results
    reporters: [
      'default',
      'json',
      'html'
    ],
    outputFile: {
      json: './test-reports/integration/results.json',
      html: './test-reports/integration/results.html'
    },
    // Test isolation and cleanup
    isolate: true,
    // Global test configuration
    globals: true
  },
  // Build configuration for integration tests
  build: {
    target: 'node18',
    sourcemap: true,
    minify: false
  },
  // Define test-specific aliases
  resolve: {
    alias: {
      '@test': new URL('./test', import.meta.url).pathname,
      '@integration': new URL('./test/integration', import.meta.url).pathname
    }
  },
  // Environment variables for integration tests
  define: {
    'process.env.NODE_ENV': '"test"',
    'process.env.VITEST': 'true',
    'process.env.INTEGRATION_TEST': 'true'
  }
});