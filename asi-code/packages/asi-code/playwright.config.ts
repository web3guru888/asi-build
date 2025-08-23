import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './test/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 3 : 1,
  workers: process.env.CI ? 2 : undefined,
  timeout: 120 * 1000, // 2 minutes for complex AI workflows
  expect: {
    timeout: 30 * 1000, // 30 seconds for assertions
  },
  reporter: [
    ['html', { outputFolder: 'test-results/playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/playwright-results.json' }],
    ['junit', { outputFile: 'test-results/playwright-junit.xml' }],
    ['allure-playwright', { outputFolder: 'test-results/allure-results' }],
    process.env.CI ? ['github'] : ['list']
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15 * 1000,
    navigationTimeout: 30 * 1000,
    // Global test context
    extraHTTPHeaders: {
      'Accept-Language': 'en-US',
    },
  },
  projects: [
    // Setup project for authentication and data seeding
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    
    // Desktop browsers
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { 
        ...devices['Desktop Firefox'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
    },
    
    // Mobile browsers
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
      testIgnore: ['**/desktop-only/**'],
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
      testIgnore: ['**/desktop-only/**'],
    },
    
    // Tablet testing
    {
      name: 'tablet',
      use: { 
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 1366 }
      },
      dependencies: ['setup'],
    },
    
    // Accessibility testing
    {
      name: 'accessibility',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
      testMatch: ['**/accessibility/**/*.e2e.ts'],
    },
    
    // Performance testing
    {
      name: 'performance',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
      testMatch: ['**/performance/**/*.e2e.ts'],
      retries: 0, // No retries for performance tests
    },
    
    // Visual regression testing
    {
      name: 'visual',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
      dependencies: ['setup'],
      testMatch: ['**/visual/**/*.e2e.ts'],
    },
  ],
  
  webServer: [
    {
      command: 'npm run start',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    // WebSocket server for real-time testing
    {
      command: 'npm run start:websocket',
      url: 'ws://127.0.0.1:3001',
      reuseExistingServer: !process.env.CI,
      timeout: 60 * 1000,
    }
  ],
  
  // Global setup and teardown
  globalSetup: require.resolve('./test/e2e/global-setup.ts'),
  globalTeardown: require.resolve('./test/e2e/global-teardown.ts'),
});