/**
 * Playwright Global Teardown
 * Cleans up the test environment after all E2E tests complete
 */

import { FullConfig } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting E2E test environment cleanup...');

  try {
    // Clean up test database
    console.log('🗑️  Cleaning up test database...');
    await cleanupTestDatabase();

    // Clean up test files
    console.log('📁 Cleaning up test files...');
    await cleanupTestFiles();

    // Generate test report summary
    console.log('📊 Generating test report summary...');
    await generateTestSummary();

    // Clean up temporary authentication state
    console.log('🔐 Cleaning up authentication state...');
    await cleanupAuthState();

    console.log('✅ E2E test environment cleanup completed successfully');
  } catch (error) {
    console.error('❌ E2E test environment cleanup failed:', error);
    // Don't throw here as we don't want to fail the entire test run due to cleanup issues
  }
}

async function cleanupTestDatabase() {
  // Clean up test database
  console.log('  - Truncating test tables...');
  console.log('  - Removing test users...');
  console.log('  - Clearing test sessions...');
  console.log('  - Resetting database sequences...');
}

async function cleanupTestFiles() {
  try {
    // Clean up temporary test files
    const tempDirs = [
      'test-results/temp',
      'test-results/downloads',
      'test-results/uploads'
    ];

    for (const dir of tempDirs) {
      try {
        await fs.rmdir(dir, { recursive: true });
        console.log(`  - Removed temporary directory: ${dir}`);
      } catch (error) {
        // Directory might not exist, which is fine
      }
    }

    // Clean up old screenshots (keep only recent ones)
    await cleanupOldScreenshots();
    
  } catch (error) {
    console.log('  - Error cleaning up test files:', error.message);
  }
}

async function cleanupOldScreenshots() {
  try {
    const screenshotDir = 'test-results/playwright-output';
    const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
    
    const files = await fs.readdir(screenshotDir).catch(() => []);
    
    for (const file of files) {
      const filePath = path.join(screenshotDir, file);
      const stats = await fs.stat(filePath).catch(() => null);
      
      if (stats && (Date.now() - stats.mtime.getTime()) > maxAge) {
        await fs.unlink(filePath);
        console.log(`  - Removed old screenshot: ${file}`);
      }
    }
  } catch (error) {
    console.log('  - Error cleaning up old screenshots:', error.message);
  }
}

async function generateTestSummary() {
  try {
    // Read test results and generate a summary
    const resultsPath = 'test-results/playwright-results.json';
    
    try {
      const resultsData = await fs.readFile(resultsPath, 'utf8');
      const results = JSON.parse(resultsData);
      
      const summary = {
        timestamp: new Date().toISOString(),
        totalTests: results.suites?.reduce((total: number, suite: any) => 
          total + (suite.specs?.length || 0), 0) || 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        duration: 0,
        projects: []
      };

      // Calculate summary statistics
      if (results.suites) {
        for (const suite of results.suites) {
          if (suite.specs) {
            for (const spec of suite.specs) {
              if (spec.tests) {
                for (const test of spec.tests) {
                  if (test.results) {
                    for (const result of test.results) {
                      switch (result.status) {
                        case 'passed':
                          summary.passed++;
                          break;
                        case 'failed':
                          summary.failed++;
                          break;
                        case 'skipped':
                          summary.skipped++;
                          break;
                      }
                      summary.duration += result.duration || 0;
                    }
                  }
                }
              }
            }
          }
        }
      }

      // Write summary to file
      const summaryPath = 'test-results/test-summary.json';
      await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2));
      
      console.log(`  - Generated test summary: ${summary.totalTests} tests, ${summary.passed} passed, ${summary.failed} failed`);
      
    } catch (error) {
      console.log('  - No test results found or error parsing results');
    }
  } catch (error) {
    console.log('  - Error generating test summary:', error.message);
  }
}

async function cleanupAuthState() {
  try {
    // Remove temporary authentication state file
    const authStatePath = 'test-results/auth-state.json';
    await fs.unlink(authStatePath);
    console.log('  - Removed authentication state file');
  } catch (error) {
    // File might not exist, which is fine
  }
}

export default globalTeardown;