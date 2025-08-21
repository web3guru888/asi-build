import { defineConfig } from 'vitest/config';
import baseConfig from './vitest.config';

export default defineConfig({
  ...baseConfig,
  test: {
    ...baseConfig.test,
    include: ['test/security/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/unit/**',
      '**/integration/**',
      '**/e2e/**',
      '**/performance/**'
    ],
    name: 'security',
    environment: 'node',
    testTimeout: 30000,
    hookTimeout: 15000,
    setupFiles: ['./test/security/setup.ts'],
    coverage: {
      ...baseConfig.test?.coverage,
      reporter: ['text', 'json'],
      reportsDirectory: 'coverage/security',
      thresholds: {
        global: {
          branches: 60,
          functions: 60,
          lines: 60,
          statements: 60
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