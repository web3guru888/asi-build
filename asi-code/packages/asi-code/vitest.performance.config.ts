import { defineConfig } from 'vitest/config';
import baseConfig from './vitest.config';

export default defineConfig({
  ...baseConfig,
  test: {
    ...baseConfig.test,
    include: ['test/performance/**/*.{test,spec,bench}.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/unit/**',
      '**/integration/**',
      '**/e2e/**',
      '**/security/**'
    ],
    name: 'performance',
    environment: 'node',
    testTimeout: 60000,
    hookTimeout: 30000,
    setupFiles: ['./test/performance/setup.ts'],
    coverage: {
      enabled: false // Performance tests don't need coverage
    },
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true,
        isolate: false
      }
    },
    benchmark: {
      reporters: ['verbose', 'json'],
      outputFile: {
        json: 'test-results/benchmark.json'
      }
    }
  }
});