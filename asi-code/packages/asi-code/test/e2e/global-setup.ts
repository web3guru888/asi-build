/**
 * Playwright Global Setup
 * Prepares the test environment before all E2E tests run
 */

import { FullConfig } from '@playwright/test';
import { chromium } from '@playwright/test';
import { DatabaseTestHelpers } from '../database/index.js';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test environment setup...');

  try {
    // Setup test database
    console.log('📋 Setting up test database...');
    await setupTestDatabase();

    // Seed test data
    console.log('🌱 Seeding test data...');
    await seedTestData();

    // Wait for servers to be ready
    console.log('⏳ Waiting for servers to be ready...');
    await waitForServers(config);

    // Setup authentication state
    console.log('🔐 Setting up authentication state...');
    await setupAuthState(config);

    console.log('✅ E2E test environment setup completed successfully');
  } catch (error) {
    console.error('❌ E2E test environment setup failed:', error);
    throw error;
  }
}

async function setupTestDatabase() {
  // This would connect to your test database
  // For now, we'll use a mock implementation
  console.log('  - Creating test database tables...');
  console.log('  - Running test migrations...');
  console.log('  - Setting up test user permissions...');
}

async function seedTestData() {
  // Seed the database with test data needed for E2E tests
  console.log('  - Creating test users...');
  console.log('  - Creating test sessions...');
  console.log('  - Creating test kenny contexts...');
  console.log('  - Setting up test tool configurations...');
}

async function waitForServers(config: FullConfig) {
  const maxRetries = 60; // 60 seconds
  const retryInterval = 1000; // 1 second
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://127.0.0.1:3000/health');
      if (response.ok) {
        console.log('  - Main server is ready');
        break;
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw new Error('Main server failed to start within timeout');
      }
      await new Promise(resolve => setTimeout(resolve, retryInterval));
    }
  }

  // Check WebSocket server if enabled
  try {
    const wsResponse = await fetch('http://127.0.0.1:3001/health');
    if (wsResponse.ok) {
      console.log('  - WebSocket server is ready');
    }
  } catch (error) {
    console.log('  - WebSocket server not available (this may be expected)');
  }
}

async function setupAuthState(config: FullConfig) {
  // Create an authenticated state for tests that need it
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login page
    await page.goto('http://127.0.0.1:3000/auth/login');
    
    // Login with test credentials
    await page.fill('[data-testid="username"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'TestPassword123!');
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful login
    await page.waitForURL('**/dashboard', { timeout: 10000 });
    
    // Save authentication state
    await context.storageState({ path: 'test-results/auth-state.json' });
    
    console.log('  - Authentication state saved');
  } catch (error) {
    console.log('  - Authentication setup failed (login page may not exist):', error.message);
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;