import { defineConfig } from 'vitest/config';
import baseConfig from './vitest.config';

export default defineConfig({
  ...baseConfig,
  test: {
    ...baseConfig.test,
    include: ['src/**/*.{test,spec}.{ts,tsx}', 'test/unit/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/integration/**',
      '**/e2e/**',
      '**/performance/**',
      '**/security/**'
    ],
    name: 'unit',
    environment: 'node',
    testTimeout: 5000,
    coverage: {
      ...baseConfig.test?.coverage,
      reporter: ['text', 'json', 'html'],
      reportsDirectory: 'coverage/unit'
    }
  }
});