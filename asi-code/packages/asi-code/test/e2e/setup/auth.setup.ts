/**
 * Authentication Setup for E2E Tests
 * 
 * Handles user authentication and session management
 * for end-to-end testing scenarios
 */

import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const authFile = path.join(__dirname, '../fixtures/auth.json');

setup('authenticate users', async ({ page }) => {
  // Read test credentials
  const credentialsPath = path.join(__dirname, '../fixtures/test-credentials.json');
  let testUsers = [];
  
  try {
    testUsers = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
  } catch (error) {
    throw new Error('Test credentials not found. Run global setup first.');
  }
  
  const authStates = {};
  
  // Authenticate each test user
  for (const user of testUsers) {
    console.log(`🔐 Authenticating user: ${user.email}`);
    
    // Navigate to login page
    await page.goto('/auth/login');
    
    // Fill login form
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    
    // Submit login
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful authentication
    await expect(page).toHaveURL('/dashboard');
    
    // Verify user is logged in
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    
    // Extract authentication state
    const context = page.context();
    const cookies = await context.cookies();
    const storageState = await context.storageState();
    
    authStates[user.id] = {
      cookies,
      origins: storageState.origins,
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
        permissions: user.permissions
      }
    };
    
    console.log(`✅ User ${user.email} authenticated successfully`);
  }
  
  // Save authentication states
  fs.writeFileSync(authFile, JSON.stringify(authStates, null, 2));
  
  console.log('🎯 All users authenticated and states saved');
});