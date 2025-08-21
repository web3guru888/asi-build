import { defineConfig } from 'vitest/config';
import baseConfig from './vitest.config';

export default defineConfig({
  ...baseConfig,
  test: {
    ...baseConfig.test,
    include: ['test/integration/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/unit/**',
      '**/e2e/**',
      '**/performance/**',
      '**/security/**'
    ],
    name: 'integration',
    environment: 'node',
    testTimeout: 30000,
    hookTimeout: 15000,
    setupFiles: ['./test/integration/setup.ts'],
    coverage: {
      ...baseConfig.test?.coverage,
      reporter: ['text', 'json', 'html'],
      reportsDirectory: 'coverage/integration',
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        }
      }
    },
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true
      }
    }
  }
});