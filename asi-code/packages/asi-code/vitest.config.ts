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
      reporter: ['text', 'json', 'html', 'lcov', 'clover', 'cobertura'],
      reportsDirectory: 'coverage',
      cleanOnRerun: true,
      all: true,
      include: ['src/**/*'],
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
        '**/mocks/**',
        '**/index.ts', // Barrel exports
        '**/types.ts', // Type definitions
        '**/*.interface.ts',
        '**/*.type.ts',
        '**/constants.ts'
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
        },
        'src/security/': {
          branches: 95,
          functions: 95,
          lines: 95,
          statements: 95
        }
      }
    },
    reporters: ['verbose', 'json', 'html', 'junit'],
    outputFile: {
      json: 'test-results/results.json',
      html: 'test-results/index.html',
      junit: 'test-results/junit.xml'
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
    ],
    // Enhanced features
    bail: 1, // Stop after first failure in CI
    passWithNoTests: false,
    logHeapUsage: true,
    isolate: true,
    sequence: {
      concurrent: true,
      shuffle: false
    },
    pool: 'threads',
    poolOptions: {
      threads: {
        maxThreads: 4,
        minThreads: 1
      }
    },
    silent: false
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@test': resolve(__dirname, 'test'),
      '@fixtures': resolve(__dirname, 'test/fixtures'),
      '@mocks': resolve(__dirname, 'test/mocks'),
      '@utils': resolve(__dirname, 'test/utils')
    }
  },
  define: {
    __TEST__: true,
    __DEV__: false,
    __VITEST__: true
  },
  esbuild: {
    target: 'node18'
  }
});