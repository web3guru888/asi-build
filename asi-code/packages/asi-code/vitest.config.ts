import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build}.config.*',
      '**/e2e/**',
      '**/performance/**',
      '**/security/**'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: 'coverage',
      exclude: [
        'node_modules/',
        'test/',
        'coverage/',
        'dist/',
        'bin/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/test-utils.ts',
        '**/fixtures/**',
        '**/mocks/**'
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        },
        'src/kenny/': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        },
        'src/provider/': {
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85
        },
        'src/tool/': {
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85
        },
        'src/session/': {
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85
        },
        'src/permission/': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        }
      }
    },
    reporters: ['verbose', 'json', 'html'],
    outputFile: {
      json: 'test-results/results.json',
      html: 'test-results/index.html'
    },
    setupFiles: ['./test/setup.ts'],
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 10000,
    watchExclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/coverage/**',
      '**/test-results/**'
    ]
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@test': resolve(__dirname, 'test')
    }
  },
  define: {
    __TEST__: true,
    __DEV__: false
  }
});