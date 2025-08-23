/**
 * Multi-Agent Orchestration E2E Tests
 * 
 * Tests agent deployment, coordination, task distribution,
 * and multi-agent collaboration workflows
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, WebSocketHelpers } from '../helpers/test-helpers';

test.describe('Multi-Agent Orchestration', () => {
  let authHelpers: AuthHelpers;
  let workspaceHelpers: WorkspaceHelpers;
  let wsHelpers: WebSocketHelpers;
  
  test.beforeEach(async ({ page }) => {
    authHelpers = new AuthHelpers(page);
    workspaceHelpers = new WorkspaceHelpers(page);
    wsHelpers = new WebSocketHelpers(page);
    
    // Login as admin with agent management permissions
    await authHelpers.loginAs('test-admin');
  });
  
  test('Supervisor agent can deploy and manage worker agents', async ({ page }) => {
    // Step 1: Navigate to agent management dashboard
    await page.goto('/agents/dashboard');
    await expect(page.locator('[data-testid="agent-dashboard"]')).toBeVisible();
    
    // Step 2: Create supervisor agent
    await page.click('[data-testid="create-supervisor-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Test Supervisor');
    await page.selectOption('[data-testid="agent-type"]', 'supervisor');
    await page.fill('[data-testid="max-workers"]', '5');
    await page.click('[data-testid="create-agent-button"]');
    
    // Step 3: Verify supervisor agent is created
    await expect(page.locator('[data-testid="agent-created-success"]')).toBeVisible();
    const supervisorId = await page.locator('[data-testid="supervisor-id"]').textContent();
    expect(supervisorId).toBeTruthy();
    
    // Step 4: Deploy worker agents through supervisor
    await page.click(`[data-testid="supervisor-${supervisorId}"]`);
    await page.click('[data-testid="deploy-workers"]');
    
    // Configure worker agents
    const workerConfigs = [
      { type: 'analyzer', capabilities: ['code_analysis', 'syntax_checking'] },
      { type: 'executor', capabilities: ['command_execution', 'file_operations'] },
      { type: 'specialist', capabilities: ['refactoring', 'optimization'] }
    ];
    
    for (const config of workerConfigs) {
      await page.click('[data-testid="add-worker"]');
      await page.selectOption('[data-testid="worker-type"]', config.type);
      
      // Add capabilities
      for (const capability of config.capabilities) {
        await page.check(`[data-testid="capability-${capability}"]`);
      }
      
      await page.click('[data-testid="deploy-worker-button"]');
      await expect(page.locator('[data-testid="worker-deployed"]')).toBeVisible();
    }
    
    // Step 5: Verify all agents are running
    await page.goto('/agents/status');
    const runningAgents = await page.locator('[data-testid="agent-status-running"]').count();
    expect(runningAgents).toBe(4); // 1 supervisor + 3 workers
    
    // Step 6: Test agent communication
    await wsHelpers.connectToWebSocket();
    
    // Send message to supervisor
    await wsHelpers.sendWebSocketMessage({
      type: 'agent_command',
      target: supervisorId,
      command: 'get_status'
    });
    
    const response = await wsHelpers.waitForWebSocketMessage();
    expect(response.type).toBe('agent_response');
    expect(response.data.status).toBe('active');
    expect(response.data.managed_agents).toHaveLength(3);
  });
  
  test('Task decomposition and parallel execution', async ({ page }) => {
    // Step 1: Setup workspace for complex task
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Multi-Agent Task Test',
      type: 'javascript',
      template: 'monorepo'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Submit complex task requiring decomposition
    await page.click('[data-testid="ai-orchestration-panel"]');
    
    const complexTask = `
      Analyze this entire codebase and:
      1. Find all TODO comments
      2. Check for security vulnerabilities  
      3. Optimize performance bottlenecks
      4. Generate comprehensive documentation
      5. Run all tests and fix failing ones
    `;
    
    await page.fill('[data-testid="complex-task-input"]', complexTask);
    await page.click('[data-testid="submit-complex-task"]');
    
    // Step 3: Verify task decomposition
    await expect(page.locator('[data-testid="task-decomposed"]')).toBeVisible();
    
    const subtasks = await page.locator('[data-testid="subtask-item"]').all();
    expect(subtasks.length).toBeGreaterThan(3);
    
    // Step 4: Monitor parallel execution
    await page.click('[data-testid="execution-monitor"]');
    
    // Verify agents are working in parallel
    const activeAgents = await page.locator('[data-testid="agent-working"]').count();
    expect(activeAgents).toBeGreaterThan(1);
    
    // Step 5: Track task progress
    await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();
    
    // Wait for at least one subtask to complete
    await expect(page.locator('[data-testid="subtask-completed"]:first')).toBeVisible({ timeout: 60000 });
    
    // Step 6: Verify results aggregation
    await page.waitForSelector('[data-testid="all-tasks-completed"]', { timeout: 120000 });
    
    const results = await page.locator('[data-testid="task-results"]').textContent();
    expect(results).toContain('TODO comments found');
    expect(results).toContain('Security scan completed');
    expect(results).toContain('Performance analysis done');
  });
  
  test('Agent failure handling and recovery', async ({ page }) => {
    // Step 1: Create agents with intentional failure scenarios
    await page.goto('/agents/dashboard');
    
    // Create supervisor with failure handling
    await page.click('[data-testid="create-supervisor-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Resilient Supervisor');
    await page.check('[data-testid="enable-failure-recovery"]');
    await page.fill('[data-testid="max-retries"]', '3');
    await page.click('[data-testid="create-agent-button"]');
    
    const supervisorId = await page.locator('[data-testid="supervisor-id"]').textContent();
    
    // Step 2: Deploy worker agents
    await page.click(`[data-testid="supervisor-${supervisorId}"]`);
    await page.click('[data-testid="deploy-workers"]');
    
    // Create multiple workers
    for (let i = 0; i < 3; i++) {
      await page.click('[data-testid="add-worker"]');
      await page.selectOption('[data-testid="worker-type"]', 'executor');
      await page.click('[data-testid="deploy-worker-button"]');
    }
    
    // Step 3: Submit task to agents
    await page.goto(`/workspaces/${await workspaceHelpers.createWorkspace({ name: 'Failure Test' })}`);
    
    await page.click('[data-testid="ai-orchestration-panel"]');
    await page.fill('[data-testid="task-input"]', 'Run comprehensive test suite');
    await page.click('[data-testid="submit-task"]');
    
    // Step 4: Simulate agent failure
    await page.goto('/agents/dashboard');
    const workerAgents = await page.locator('[data-testid^="worker-agent-"]').all();
    
    // Kill one worker agent
    await workerAgents[0].click();
    await page.click('[data-testid="simulate-failure"]');
    await expect(page.locator('[data-testid="agent-failed"]')).toBeVisible();
    
    // Step 5: Verify supervisor handles failure
    await expect(page.locator('[data-testid="failure-detected"]')).toBeVisible();
    await expect(page.locator('[data-testid="recovery-initiated"]')).toBeVisible();
    
    // Step 6: Verify task reallocation
    await expect(page.locator('[data-testid="task-reallocated"]')).toBeVisible();
    
    // Step 7: Verify new agent deployment
    await expect(page.locator('[data-testid="replacement-agent-deployed"]')).toBeVisible();
    
    // Step 8: Verify task completion despite failure
    await page.goto('/tasks/monitor');
    await expect(page.locator('[data-testid="task-completed-successfully"]')).toBeVisible({ timeout: 60000 });
  });
  
  test('Load balancing and resource optimization', async ({ page }) => {
    // Step 1: Create supervisor with load balancing
    await page.goto('/agents/dashboard');
    
    await page.click('[data-testid="create-supervisor-agent"]');
    await page.fill('[data-testid="agent-name"]', 'Load Balancer Supervisor');
    await page.check('[data-testid="enable-load-balancing"]');
    await page.selectOption('[data-testid="balancing-strategy"]', 'least_loaded');
    await page.click('[data-testid="create-agent-button"]');
    
    const supervisorId = await page.locator('[data-testid="supervisor-id"]').textContent();
    
    // Step 2: Deploy multiple worker agents with different capacities
    await page.click(`[data-testid="supervisor-${supervisorId}"]`);
    
    const workerConfigs = [
      { name: 'High Capacity Worker', maxTasks: 10, cpu: 4, memory: 8 },
      { name: 'Medium Capacity Worker', maxTasks: 5, cpu: 2, memory: 4 },
      { name: 'Low Capacity Worker', maxTasks: 2, cpu: 1, memory: 2 }
    ];
    
    for (const config of workerConfigs) {
      await page.click('[data-testid="add-worker"]');
      await page.fill('[data-testid="worker-name"]', config.name);
      await page.fill('[data-testid="max-concurrent-tasks"]', config.maxTasks.toString());
      await page.fill('[data-testid="cpu-allocation"]', config.cpu.toString());
      await page.fill('[data-testid="memory-allocation"]', config.memory.toString());
      await page.click('[data-testid="deploy-worker-button"]');
    }
    
    // Step 3: Submit multiple tasks simultaneously
    const workspaceId = await workspaceHelpers.createWorkspace({ name: 'Load Test' });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    const tasks = [
      'Analyze code complexity',
      'Run security scan',
      'Generate documentation',
      'Optimize performance',
      'Run test suite',
      'Check code style',
      'Validate dependencies',
      'Build project'
    ];
    
    // Submit all tasks rapidly
    for (const task of tasks) {
      await page.fill('[data-testid="quick-task-input"]', task);
      await page.click('[data-testid="submit-quick-task"]');
      await page.waitForTimeout(100); // Small delay to prevent UI issues
    }
    
    // Step 4: Monitor load distribution
    await page.goto('/agents/monitoring');
    
    // Verify tasks are distributed based on capacity
    const highCapacityLoad = await page.locator('[data-testid="high-capacity-load"]').textContent();
    const mediumCapacityLoad = await page.locator('[data-testid="medium-capacity-load"]').textContent();
    const lowCapacityLoad = await page.locator('[data-testid="low-capacity-load"]').textContent();
    
    // High capacity worker should have more tasks
    expect(parseInt(highCapacityLoad || '0')).toBeGreaterThan(parseInt(mediumCapacityLoad || '0'));
    expect(parseInt(mediumCapacityLoad || '0')).toBeGreaterThan(parseInt(lowCapacityLoad || '0'));
    
    // Step 5: Monitor resource utilization
    await expect(page.locator('[data-testid="resource-monitor"]')).toBeVisible();
    
    const cpuUsage = await page.locator('[data-testid="total-cpu-usage"]').textContent();
    const memoryUsage = await page.locator('[data-testid="total-memory-usage"]').textContent();
    
    expect(parseFloat(cpuUsage || '0')).toBeGreaterThan(0);
    expect(parseFloat(memoryUsage || '0')).toBeGreaterThan(0);
    
    // Step 6: Verify all tasks complete
    await expect(page.locator('[data-testid="all-tasks-completed"]')).toBeVisible({ timeout: 90000 });
  });
  
  test('Agent coordination protocol', async ({ page }) => {
    // Step 1: Create multiple supervisors for coordination testing
    await page.goto('/agents/dashboard');
    
    const supervisorConfigs = [
      { name: 'Frontend Supervisor', domain: 'frontend' },
      { name: 'Backend Supervisor', domain: 'backend' },
      { name: 'DevOps Supervisor', domain: 'devops' }
    ];
    
    const supervisorIds = [];
    
    for (const config of supervisorConfigs) {
      await page.click('[data-testid="create-supervisor-agent"]');
      await page.fill('[data-testid="agent-name"]', config.name);
      await page.selectOption('[data-testid="agent-domain"]', config.domain);
      await page.check('[data-testid="enable-coordination"]');
      await page.click('[data-testid="create-agent-button"]');
      
      const supervisorId = await page.locator('[data-testid="supervisor-id"]').textContent();
      supervisorIds.push(supervisorId);
    }
    
    // Step 2: Submit cross-domain task requiring coordination
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Full Stack App',
      type: 'fullstack'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    const crossDomainTask = `
      Build a complete web application with:
      - React frontend with user authentication
      - Node.js backend API with database
      - Docker containerization and deployment pipeline
    `;
    
    await page.click('[data-testid="ai-orchestration-panel"]');
    await page.fill('[data-testid="complex-task-input"]', crossDomainTask);
    await page.click('[data-testid="submit-complex-task"]');
    
    // Step 3: Verify coordination protocol
    await page.goto('/agents/coordination');
    
    // Check supervisor communication
    await expect(page.locator('[data-testid="coordination-initiated"]')).toBeVisible();
    await expect(page.locator('[data-testid="task-negotiation"]')).toBeVisible();
    
    // Step 4: Monitor task distribution across domains
    const frontendTasks = await page.locator('[data-testid="frontend-tasks"]').count();
    const backendTasks = await page.locator('[data-testid="backend-tasks"]').count();
    const devopsTasks = await page.locator('[data-testid="devops-tasks"]').count();
    
    expect(frontendTasks).toBeGreaterThan(0);
    expect(backendTasks).toBeGreaterThan(0);
    expect(devopsTasks).toBeGreaterThan(0);
    
    // Step 5: Verify dependency management
    await expect(page.locator('[data-testid="dependency-resolution"]')).toBeVisible();
    
    // Backend should start before frontend integration
    const backendStartTime = await page.locator('[data-testid="backend-start-time"]').textContent();
    const frontendStartTime = await page.locator('[data-testid="frontend-start-time"]').textContent();
    
    expect(parseInt(backendStartTime || '0')).toBeLessThan(parseInt(frontendStartTime || '0'));
    
    // Step 6: Verify successful coordination
    await expect(page.locator('[data-testid="coordination-successful"]')).toBeVisible({ timeout: 120000 });
    await expect(page.locator('[data-testid="full-application-complete"]')).toBeVisible();
  });
});