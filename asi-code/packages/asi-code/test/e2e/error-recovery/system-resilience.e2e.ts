/**
 * System Resilience and Error Recovery E2E Tests
 * 
 * Tests system behavior under failure conditions,
 * recovery mechanisms, and graceful degradation
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, WebSocketHelpers, AIHelpers, PerformanceHelpers } from '../helpers/test-helpers';

test.describe('System Resilience and Error Recovery', () => {
  let authHelpers: AuthHelpers;
  let workspaceHelpers: WorkspaceHelpers;
  let wsHelpers: WebSocketHelpers;
  let aiHelpers: AIHelpers;
  let perfHelpers: PerformanceHelpers;
  
  test.beforeEach(async ({ page }) => {
    authHelpers = new AuthHelpers(page);
    workspaceHelpers = new WorkspaceHelpers(page);
    wsHelpers = new WebSocketHelpers(page);
    aiHelpers = new AIHelpers(page);
    perfHelpers = new PerformanceHelpers(page);
    
    await authHelpers.loginAs('test-developer');
  });
  
  test('Network disconnection and reconnection handling', async ({ page, context }) => {
    // Step 1: Setup workspace and establish connection
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Network Resilience Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Verify normal operation
    await workspaceHelpers.createFile('src/test.js', 'console.log("Before disconnect");');
    await expect(page.locator('[data-testid="file-saved"]')).toBeVisible();
    
    // Step 3: Simulate network disconnection
    await context.setOffline(true);
    
    // Step 4: Verify offline mode detection
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-message"]')).toContainText('Connection lost');
    
    // Step 5: Test offline functionality
    // Local editing should still work
    await page.locator('[data-testid="code-editor"]').fill('console.log("During disconnect");');
    
    // Remote operations should queue
    await page.click('[data-testid="ai-chat-toggle"]');
    await page.fill('[data-testid="ai-chat-input"]', 'Help me with this code');
    await page.click('[data-testid="ai-chat-send"]');
    
    await expect(page.locator('[data-testid="message-queued"]')).toBeVisible();
    
    // Step 6: Verify graceful degradation
    await expect(page.locator('[data-testid="offline-features"]')).toBeVisible();
    
    // Local tools should work
    await page.click('[data-testid="tools-panel"]');
    await page.click('[data-testid="tool-search"]');
    await page.fill('[data-testid="search-pattern"]', 'console');
    await page.click('[data-testid="execute-search"]');
    
    await expect(page.locator('[data-testid="local-search-results"]')).toBeVisible();
    
    // Step 7: Simulate reconnection
    await context.setOffline(false);
    
    // Step 8: Verify automatic reconnection
    await expect(page.locator('[data-testid="reconnecting"]')).toBeVisible();
    await expect(page.locator('[data-testid="connection-restored"]')).toBeVisible({ timeout: 30000 });
    
    // Step 9: Verify data synchronization
    await expect(page.locator('[data-testid="sync-in-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-complete"]')).toBeVisible({ timeout: 15000 });
    
    // Step 10: Test queued operations execution
    await expect(page.locator('[data-testid="ai-response"]')).toBeVisible({ timeout: 30000 });
    
    // Step 11: Verify file changes were preserved
    const fileContent = await page.locator('[data-testid="code-editor"]').textContent();
    expect(fileContent).toContain('During disconnect');
  });
  
  test('AI service failure and fallback mechanisms', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'AI Failure Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create code requiring AI assistance
    await workspaceHelpers.createFile('src/complex.js', `
function complexFunction(data) {
  // This function needs optimization
  let result = [];
  for (let i = 0; i < data.length; i++) {
    for (let j = 0; j < data[i].length; j++) {
      if (data[i][j] > 0) {
        result.push(data[i][j] * 2);
      }
    }
  }
  return result;
}
    `);
    
    // Step 3: Simulate AI service failure
    await page.route('**/api/ai/**', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'AI service temporarily unavailable' })
      });
    });
    
    // Step 4: Test primary AI failure detection
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('Optimize this function for better performance');
    
    await expect(page.locator('[data-testid="ai-service-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="fallback-options"]')).toBeVisible();
    
    // Step 5: Test fallback to alternative AI service
    await page.click('[data-testid="try-fallback-ai"]');
    
    // Mock fallback service
    await page.route('**/api/ai-fallback/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'I can help optimize this function. Consider using Array.flat() and filter() methods.',
          suggestions: ['Use functional programming approaches', 'Reduce nested loops']
        })
      });
    });
    
    await expect(page.locator('[data-testid="fallback-ai-response"]')).toBeVisible();
    const fallbackResponse = await page.locator('[data-testid="ai-response"]').textContent();
    expect(fallbackResponse).toContain('Array.flat');
    
    // Step 6: Test cached responses
    await page.route('**/api/ai/**', route => route.continue()); // Restore service
    
    await aiHelpers.sendMessage('What are the benefits of functional programming?');
    
    // Should use cached/offline knowledge
    await expect(page.locator('[data-testid="cached-response"]')).toBeVisible();
    
    // Step 7: Test graceful degradation to local tools
    await page.route('**/api/ai/**', route => {
      route.fulfill({ status: 503 });
    });
    await page.route('**/api/ai-fallback/**', route => {
      route.fulfill({ status: 503 });
    });
    
    await aiHelpers.sendMessage('Find all console.log statements');
    
    // Should fallback to local search
    await expect(page.locator('[data-testid="local-fallback-activated"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
  });
  
  test('Database connection failure and recovery', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Database Failure Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Simulate database connectivity issues
    await page.route('**/api/workspaces/**', route => {
      if (route.request().method() === 'PUT' || route.request().method() === 'POST') {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Database connection failed' })
        });
      } else {
        route.continue();
      }
    });
    
    // Step 3: Test file save operation during DB failure
    await workspaceHelpers.createFile('src/db-test.js', 'console.log("test");');
    
    await expect(page.locator('[data-testid="save-failed"]')).toBeVisible();
    await expect(page.locator('[data-testid="local-backup-created"]')).toBeVisible();
    
    // Step 4: Verify local backup functionality
    const backupIndicator = await page.locator('[data-testid="backup-indicator"]');
    await expect(backupIndicator).toContainText('Local backup active');
    
    // Step 5: Continue working with local backup
    await page.locator('[data-testid="code-editor"]').fill('console.log("modified during db failure");');
    await page.keyboard.press('Control+S');
    
    await expect(page.locator('[data-testid="saved-to-backup"]')).toBeVisible();
    
    // Step 6: Simulate database recovery
    await page.route('**/api/workspaces/**', route => route.continue());
    
    // Step 7: Test automatic sync on recovery
    await expect(page.locator('[data-testid="database-recovered"]')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('[data-testid="syncing-backup"]')).toBeVisible();
    
    // Step 8: Verify data integrity after sync
    await expect(page.locator('[data-testid="sync-successful"]')).toBeVisible({ timeout: 15000 });
    
    const syncedContent = await page.locator('[data-testid="code-editor"]').textContent();
    expect(syncedContent).toContain('modified during db failure');
    
    // Step 9: Test conflict resolution
    // Simulate another user made changes during outage
    await page.route('**/api/files/src/db-test.js', route => {
      route.fulfill({
        status: 409, // Conflict
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Conflict detected',
          serverVersion: 'console.log("server version");',
          localVersion: 'console.log("modified during db failure");'
        })
      });
    });
    
    await page.keyboard.press('Control+S');
    
    await expect(page.locator('[data-testid="conflict-detected"]')).toBeVisible();
    await expect(page.locator('[data-testid="conflict-resolution-options"]')).toBeVisible();
    
    // Resolve conflict
    await page.click('[data-testid="merge-changes"]');
    await expect(page.locator('[data-testid="conflict-resolved"]')).toBeVisible();
  });
  
  test('Memory pressure and resource exhaustion handling', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Memory Pressure Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create large file to stress memory
    const largeContent = 'const data = ' + JSON.stringify(new Array(10000).fill(0).map((_, i) => ({
      id: i,
      data: 'x'.repeat(1000),
      nested: { items: new Array(100).fill('large string content') }
    }))) + ';';
    
    await workspaceHelpers.createFile('src/large-file.js', largeContent);
    
    // Step 3: Monitor memory usage
    const initialMemory = await perfHelpers.getMemoryUsage();
    expect(initialMemory.used).toBeGreaterThan(0);
    
    // Step 4: Simulate memory pressure
    await page.evaluate(() => {
      // Create memory pressure
      window.memoryStress = [];
      for (let i = 0; i < 1000; i++) {
        window.memoryStress.push(new Array(10000).fill('memory stress'));
      }
    });
    
    // Step 5: Verify memory pressure detection
    await expect(page.locator('[data-testid="memory-warning"]')).toBeVisible({ timeout: 10000 });
    
    // Step 6: Test automatic cleanup mechanisms
    await expect(page.locator('[data-testid="cleanup-initiated"]')).toBeVisible();
    
    // Should close non-essential tabs/editors
    await expect(page.locator('[data-testid="resources-optimized"]')).toBeVisible();
    
    // Step 7: Test graceful degradation
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('Analyze this large file');
    
    // Should limit processing or suggest alternatives
    await expect(page.locator('[data-testid="resource-limited-mode"]')).toBeVisible();
    
    // Step 8: Verify recovery after memory release
    await page.evaluate(() => {
      window.memoryStress = null;
      if (window.gc) window.gc(); // Force garbage collection if available
    });
    
    await expect(page.locator('[data-testid="memory-recovered"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="full-functionality-restored"]')).toBeVisible();
  });
  
  test('Agent failure cascade prevention', async ({ page }) => {
    // Step 1: Setup multi-agent environment
    await page.goto('/agents/dashboard');
    
    // Create supervisor with multiple workers
    await page.click('[data-testid="create-supervisor-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Resilience Test Supervisor');
    await page.check('[data-testid="enable-failure-isolation"]');
    await page.click('[data-testid="create-agent-button"]');
    
    const supervisorId = await page.locator('[data-testid="supervisor-id"]').textContent();
    
    // Deploy multiple worker agents
    await page.click(`[data-testid="supervisor-${supervisorId}"]`);
    
    for (let i = 0; i < 5; i++) {
      await page.click('[data-testid="deploy-worker"]');
      await page.fill('[data-testid="worker-name"]', `Worker-${i + 1}`);
      await page.click('[data-testid="deploy-worker-button"]');
    }
    
    // Step 2: Submit tasks to agents
    const workspaceId = await workspaceHelpers.createWorkspace({ name: 'Agent Failure Test' });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    const tasks = [
      'Analyze code structure',
      'Run security scan',
      'Generate documentation', 
      'Optimize performance',
      'Run test suite'
    ];
    
    for (const task of tasks) {
      await page.fill('[data-testid="task-input"]', task);
      await page.click('[data-testid="submit-task"]');
    }
    
    // Step 3: Simulate cascading failures
    await page.goto('/agents/dashboard');
    
    // Kill multiple workers in sequence
    const workers = await page.locator('[data-testid^="worker-agent-"]').all();
    
    // First failure
    await workers[0].click();
    await page.click('[data-testid="simulate-failure"]');
    await expect(page.locator('[data-testid="agent-failed"]')).toBeVisible();
    
    // Should isolate failure
    await expect(page.locator('[data-testid="failure-isolated"]')).toBeVisible();
    await expect(page.locator('[data-testid="remaining-agents-healthy"]')).toBeVisible();
    
    // Second failure (potential cascade)
    await workers[1].click();
    await page.click('[data-testid="simulate-failure"]');
    
    // Step 4: Verify cascade prevention
    await expect(page.locator('[data-testid="cascade-prevention-activated"]')).toBeVisible();
    await expect(page.locator('[data-testid="circuit-breaker-open"]')).toBeVisible();
    
    // Step 5: Test recovery mechanism
    await expect(page.locator('[data-testid="recovery-mode-initiated"]')).toBeVisible();
    
    // Should deploy replacement agents
    await expect(page.locator('[data-testid="replacement-agents-deploying"]')).toBeVisible();
    await expect(page.locator('[data-testid="replacement-agents-ready"]')).toBeVisible({ timeout: 30000 });
    
    // Step 6: Verify system stability
    const healthyAgents = await page.locator('[data-testid="agent-status-healthy"]').count();
    expect(healthyAgents).toBeGreaterThanOrEqual(3);
    
    // Step 7: Test task completion despite failures
    await page.goto('/tasks/monitor');
    await expect(page.locator('[data-testid="tasks-recovering"]')).toBeVisible();
    await expect(page.locator('[data-testid="all-tasks-completed"]')).toBeVisible({ timeout: 60000 });
  });
  
  test('Session corruption and data recovery', async ({ page }) => {
    // Step 1: Setup workspace with important data
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Session Recovery Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Create multiple files with content
    const files = [
      { name: 'src/app.js', content: 'const app = require("express")();' },
      { name: 'src/utils.js', content: 'module.exports = { helper: () => {} };' },
      { name: 'test/app.test.js', content: 'test("app", () => {});' }
    ];
    
    for (const file of files) {
      await workspaceHelpers.createFile(file.name, file.content);
    }
    
    // Step 2: Simulate session corruption
    await page.evaluate(() => {
      // Corrupt localStorage
      localStorage.setItem('workspace-state', 'corrupted-data-###');
      localStorage.setItem('session-data', null);
      
      // Corrupt sessionStorage
      sessionStorage.clear();
    });
    
    // Step 3: Refresh page to trigger recovery
    await page.reload();
    
    // Step 4: Verify corruption detection
    await expect(page.locator('[data-testid="session-corruption-detected"]')).toBeVisible();
    await expect(page.locator('[data-testid="recovery-options"]')).toBeVisible();
    
    // Step 5: Test automatic recovery
    await page.click('[data-testid="auto-recover-session"]');
    
    await expect(page.locator('[data-testid="recovery-in-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="fetching-from-server"]')).toBeVisible();
    
    // Step 6: Verify data recovery
    await expect(page.locator('[data-testid="recovery-successful"]')).toBeVisible({ timeout: 30000 });
    
    // Should restore workspace state
    await expect(page.locator('[data-testid="file-app.js"]')).toBeVisible();
    await expect(page.locator('[data-testid="file-utils.js"]')).toBeVisible();
    await expect(page.locator('[data-testid="file-app.test.js"]')).toBeVisible();
    
    // Step 7: Verify file contents integrity
    await page.click('[data-testid="file-app.js"]');
    const appContent = await page.locator('[data-testid="code-editor"]').textContent();
    expect(appContent).toContain('express');
    
    // Step 8: Test partial recovery scenario
    await page.evaluate(() => {
      localStorage.setItem('partial-corruption-flag', 'true');
    });
    
    await page.reload();
    
    // Should detect partial corruption
    await expect(page.locator('[data-testid="partial-corruption-detected"]')).toBeVisible();
    
    // Should offer selective recovery
    await expect(page.locator('[data-testid="selective-recovery-options"]')).toBeVisible();
    
    await page.click('[data-testid="recover-workspace-state"]');
    await page.click('[data-testid="keep-local-changes"]');
    
    await expect(page.locator('[data-testid="selective-recovery-complete"]')).toBeVisible();
  });
});