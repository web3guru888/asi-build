/**
 * Comprehensive Tool Execution E2E Tests
 * 
 * Tests tool execution sequences, chaining, error handling,
 * and complex multi-tool workflows
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, ToolHelpers, AIHelpers } from '../helpers/test-helpers';

test.describe('Tool Execution Workflows', () => {
  let authHelpers: AuthHelpers;
  let workspaceHelpers: WorkspaceHelpers;
  let toolHelpers: ToolHelpers;
  let aiHelpers: AIHelpers;
  
  test.beforeEach(async ({ page }) => {
    authHelpers = new AuthHelpers(page);
    workspaceHelpers = new WorkspaceHelpers(page);
    toolHelpers = new ToolHelpers(page);
    aiHelpers = new AIHelpers(page);
    
    await authHelpers.loginAs('test-developer');
  });
  
  test('Sequential tool execution with data flow', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Tool Chain Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create source files for tool operations
    await workspaceHelpers.createFile('src/data.json', JSON.stringify({
      users: [
        { id: 1, name: 'John Doe', email: 'john@example.com' },
        { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
      ]
    }, null, 2));
    
    await workspaceHelpers.createFile('src/processor.js', `
const fs = require('fs');

// Read data
const data = JSON.parse(fs.readFileSync('src/data.json', 'utf8'));

// Process data
const processed = data.users.map(user => ({
  ...user,
  processed: true,
  timestamp: new Date().toISOString()
}));

// Write processed data
fs.writeFileSync('src/processed-data.json', JSON.stringify(processed, null, 2));

console.log('Data processed successfully');
    `);
    
    // Step 3: Execute tool chain
    await page.click('[data-testid="tools-panel"]');
    
    // Tool 1: Read original data
    await page.click('[data-testid="tool-read"]');
    await page.fill('[data-testid="read-file-path"]', 'src/data.json');
    await page.click('[data-testid="execute-read"]');
    
    const readResult = await page.locator('[data-testid="tool-result"]').textContent();
    expect(readResult).toContain('John Doe');
    expect(readResult).toContain('Jane Smith');
    
    // Tool 2: Execute processing script
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'node src/processor.js');
    await page.click('[data-testid="execute-bash"]');
    
    const execResult = await page.locator('[data-testid="tool-result"]').textContent();
    expect(execResult).toContain('Data processed successfully');
    
    // Tool 3: Verify processed output
    await page.click('[data-testid="tool-read"]');
    await page.fill('[data-testid="read-file-path"]', 'src/processed-data.json');
    await page.click('[data-testid="execute-read"]');
    
    const processedResult = await page.locator('[data-testid="tool-result"]').textContent();
    expect(processedResult).toContain('processed');
    expect(processedResult).toContain('timestamp');
    
    // Tool 4: Search for specific patterns
    await page.click('[data-testid="tool-search"]');
    await page.fill('[data-testid="search-pattern"]', 'processed.*true');
    await page.fill('[data-testid="search-path"]', 'src/');
    await page.click('[data-testid="execute-search"]');
    
    const searchResult = await page.locator('[data-testid="search-results"]').textContent();
    expect(searchResult).toContain('processed-data.json');
  });
  
  test('Parallel tool execution with result aggregation', async ({ page }) => {
    // Step 1: Setup workspace with multiple files
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Parallel Tools Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Create multiple test files
    const testFiles = [
      { name: 'module1.js', content: 'const func1 = () => "Hello"; module.exports = { func1 };' },
      { name: 'module2.js', content: 'const func2 = () => "World"; module.exports = { func2 };' },
      { name: 'test1.js', content: 'const assert = require("assert"); assert(true);' },
      { name: 'test2.js', content: 'const assert = require("assert"); assert(1 + 1 === 2);' }
    ];
    
    for (const file of testFiles) {
      await workspaceHelpers.createFile(`src/${file.name}`, file.content);
    }
    
    // Step 2: Launch parallel tools
    await page.click('[data-testid="tools-panel"]');
    await page.click('[data-testid="parallel-execution-mode"]');
    
    // Tool Set 1: File operations
    const fileOperations = [
      { tool: 'list', args: 'src/' },
      { tool: 'read', args: 'src/module1.js' },
      { tool: 'read', args: 'src/module2.js' }
    ];
    
    // Execute file operations in parallel
    for (const op of fileOperations) {
      await page.click(`[data-testid="tool-${op.tool}"]`);
      await page.fill(`[data-testid="${op.tool}-input"]`, op.args);
      await page.click(`[data-testid="add-to-parallel-batch"]`);
    }
    
    await page.click('[data-testid="execute-parallel-batch"]');
    
    // Step 3: Monitor parallel execution
    await expect(page.locator('[data-testid="parallel-execution-status"]')).toBeVisible();
    
    const executingTools = await page.locator('[data-testid="tool-executing"]').count();
    expect(executingTools).toBe(3);
    
    // Step 4: Wait for all tools to complete
    await expect(page.locator('[data-testid="parallel-batch-complete"]')).toBeVisible({ timeout: 30000 });
    
    // Step 5: Verify results aggregation
    const results = await page.locator('[data-testid="parallel-results"]').all();
    expect(results).toHaveLength(3);
    
    // Verify list tool found all files
    const listResult = await page.locator('[data-testid="result-list"]').textContent();
    expect(listResult).toContain('module1.js');
    expect(listResult).toContain('module2.js');
    expect(listResult).toContain('test1.js');
    expect(listResult).toContain('test2.js');
    
    // Verify read tools got file contents
    const readResults = await page.locator('[data-testid="result-read"]').all();
    expect(readResults).toHaveLength(2);
  });
  
  test('Tool error handling and recovery', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Error Handling Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Test file operation errors
    await page.click('[data-testid="tools-panel"]');
    
    // Try to read non-existent file
    await page.click('[data-testid="tool-read"]');
    await page.fill('[data-testid="read-file-path"]', 'src/nonexistent.js');
    await page.click('[data-testid="execute-read"]');
    
    // Verify error is handled gracefully
    await expect(page.locator('[data-testid="tool-error"]')).toBeVisible();
    const errorMessage = await page.locator('[data-testid="error-message"]').textContent();
    expect(errorMessage).toContain('File not found');
    
    // Step 3: Test command execution errors
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'invalidcommand --invalid-flag');
    await page.click('[data-testid="execute-bash"]');
    
    await expect(page.locator('[data-testid="tool-error"]')).toBeVisible();
    const commandError = await page.locator('[data-testid="error-message"]').textContent();
    expect(commandError).toContain('command not found');
    
    // Step 4: Test permission errors
    await page.click('[data-testid="tool-write"]');
    await page.fill('[data-testid="write-file-path"]', '/etc/restricted.txt');
    await page.fill('[data-testid="write-content"]', 'test content');
    await page.click('[data-testid="execute-write"]');
    
    await expect(page.locator('[data-testid="tool-error"]')).toBeVisible();
    const permissionError = await page.locator('[data-testid="error-message"]').textContent();
    expect(permissionError).toContain('Permission denied');
    
    // Step 5: Test error recovery
    await page.click('[data-testid="retry-with-correction"]');
    
    // Correct the path
    await page.fill('[data-testid="write-file-path"]', 'src/test.txt');
    await page.click('[data-testid="execute-write"]');
    
    await expect(page.locator('[data-testid="tool-success"]')).toBeVisible();
    
    // Step 6: Test bulk error handling
    await page.click('[data-testid="parallel-execution-mode"]');
    
    const errorProneTasks = [
      { tool: 'read', args: 'nonexistent1.js' },
      { tool: 'read', args: 'src/test.txt' }, // This should succeed
      { tool: 'read', args: 'nonexistent2.js' },
      { tool: 'bash', args: 'echo "success"' } // This should succeed
    ];
    
    for (const task of errorProneTasks) {
      await page.click(`[data-testid="tool-${task.tool}"]`);
      await page.fill(`[data-testid="${task.tool}-input"]`, task.args);
      await page.click('[data-testid="add-to-parallel-batch"]');
    }
    
    await page.click('[data-testid="execute-parallel-batch"]');
    await expect(page.locator('[data-testid="parallel-batch-complete"]')).toBeVisible();
    
    // Verify partial success handling
    const successCount = await page.locator('[data-testid="success-count"]').textContent();
    const errorCount = await page.locator('[data-testid="error-count"]').textContent();
    
    expect(successCount).toBe('2');
    expect(errorCount).toBe('2');
  });
  
  test('Tool chaining with conditional execution', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Conditional Tool Chain',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create conditional workflow
    await page.click('[data-testid="tools-panel"]');
    await page.click('[data-testid="workflow-builder"]');
    
    // Define workflow steps
    const workflow = [
      {
        name: 'check-package-json',
        tool: 'read',
        args: 'package.json',
        onSuccess: 'install-dependencies',
        onError: 'create-package-json'
      },
      {
        name: 'create-package-json',
        tool: 'write',
        args: { path: 'package.json', content: '{"name": "test-project"}' },
        onSuccess: 'install-dependencies'
      },
      {
        name: 'install-dependencies',
        tool: 'bash',
        args: 'npm install',
        onSuccess: 'run-tests',
        onError: 'log-error'
      },
      {
        name: 'run-tests',
        tool: 'bash',
        args: 'npm test',
        onError: 'fix-tests'
      },
      {
        name: 'fix-tests',
        tool: 'write',
        args: { path: 'test/basic.test.js', content: 'test("basic", () => expect(true).toBe(true));' },
        onSuccess: 'run-tests-again'
      }
    ];
    
    // Step 3: Build workflow
    for (const step of workflow) {
      await page.click('[data-testid="add-workflow-step"]');
      await page.fill('[data-testid="step-name"]', step.name);
      await page.selectOption('[data-testid="step-tool"]', step.tool);
      await page.fill('[data-testid="step-args"]', JSON.stringify(step.args));
      
      if (step.onSuccess) {
        await page.fill('[data-testid="on-success"]', step.onSuccess);
      }
      if (step.onError) {
        await page.fill('[data-testid="on-error"]', step.onError);
      }
      
      await page.click('[data-testid="save-step"]');
    }
    
    // Step 4: Execute workflow
    await page.click('[data-testid="execute-workflow"]');
    
    // Step 5: Monitor conditional execution
    await expect(page.locator('[data-testid="workflow-executing"]')).toBeVisible();
    
    // First step should fail (no package.json)
    await expect(page.locator('[data-testid="step-check-package-json-failed"]')).toBeVisible();
    
    // Should trigger error path
    await expect(page.locator('[data-testid="step-create-package-json-executing"]')).toBeVisible();
    await expect(page.locator('[data-testid="step-create-package-json-success"]')).toBeVisible();
    
    // Should continue to success path
    await expect(page.locator('[data-testid="step-install-dependencies-executing"]')).toBeVisible();
    
    // Step 6: Verify final workflow state
    await expect(page.locator('[data-testid="workflow-complete"]')).toBeVisible({ timeout: 60000 });
    
    const workflowResults = await page.locator('[data-testid="workflow-results"]').textContent();
    expect(workflowResults).toContain('package.json created');
    expect(workflowResults).toContain('dependencies installed');
  });
  
  test('Tool integration with AI suggestions', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'AI Tool Integration',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create problematic code
    await workspaceHelpers.createFile('src/buggy.js', `
function calculateSum(numbers) {
  let sum = 0;
  for (let i = 0; i <= numbers.length; i++) { // Bug: <= instead of <
    sum += numbers[i]; // Will cause undefined addition
  }
  return sum;
}

const result = calculateSum([1, 2, 3, 4, 5]);
console.log(result); // Will log NaN
    `);
    
    // Step 3: Run code and detect issues
    await page.click('[data-testid="tools-panel"]');
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'node src/buggy.js');
    await page.click('[data-testid="execute-bash"]');
    
    const output = await page.locator('[data-testid="tool-result"]').textContent();
    expect(output).toContain('NaN');
    
    // Step 4: Ask AI for help
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('The code output is NaN. Can you analyze the code and suggest tools to fix it?');
    
    const aiResponse = await aiHelpers.waitForAIResponse();
    expect(aiResponse).toContain('off-by-one error');
    expect(aiResponse).toContain('tool suggestions');
    
    // Step 5: Apply AI-suggested tool sequence
    await page.click('[data-testid="apply-ai-tool-suggestions"]');
    
    // AI should suggest search tool to find the bug
    await expect(page.locator('[data-testid="ai-suggested-search"]')).toBeVisible();
    await page.click('[data-testid="execute-ai-suggestion"]');
    
    const searchResults = await page.locator('[data-testid="search-results"]').textContent();
    expect(searchResults).toContain('i <= numbers.length');
    
    // AI should suggest edit tool to fix the bug
    await expect(page.locator('[data-testid="ai-suggested-edit"]')).toBeVisible();
    await page.click('[data-testid="execute-ai-suggestion"]');
    
    // Step 6: Verify fix was applied
    await page.click('[data-testid="tool-read"]');
    await page.fill('[data-testid="read-file-path"]', 'src/buggy.js');
    await page.click('[data-testid="execute-read"]');
    
    const fixedCode = await page.locator('[data-testid="tool-result"]').textContent();
    expect(fixedCode).toContain('i < numbers.length');
    expect(fixedCode).not.toContain('i <= numbers.length');
    
    // Step 7: Test the fix
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'node src/buggy.js');
    await page.click('[data-testid="execute-bash"]');
    
    const fixedOutput = await page.locator('[data-testid="tool-result"]').textContent();
    expect(fixedOutput).toContain('15'); // Correct sum
    expect(fixedOutput).not.toContain('NaN');
  });
  
  test('Long-running tool operations with progress tracking', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Long Running Operations',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create large file for processing
    await page.click('[data-testid="tools-panel"]');
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'seq 1 100000 > large-file.txt');
    await page.click('[data-testid="execute-bash"]');
    
    // Step 3: Start long-running operation
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'wc -l large-file.txt && sleep 10 && sort large-file.txt > sorted-file.txt');
    await page.click('[data-testid="execute-bash"]');
    
    // Step 4: Monitor progress
    await expect(page.locator('[data-testid="tool-executing"]')).toBeVisible();
    await expect(page.locator('[data-testid="progress-indicator"]')).toBeVisible();
    
    // Step 5: Verify cancellation capability
    await page.click('[data-testid="cancel-operation"]');
    await expect(page.locator('[data-testid="operation-cancelled"]')).toBeVisible();
    
    // Step 6: Restart operation with progress tracking
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'sort large-file.txt > sorted-file.txt');
    await page.check('[data-testid="enable-progress-tracking"]');
    await page.click('[data-testid="execute-bash"]');
    
    // Monitor detailed progress
    await expect(page.locator('[data-testid="detailed-progress"]')).toBeVisible();
    
    // Wait for completion
    await expect(page.locator('[data-testid="operation-complete"]')).toBeVisible({ timeout: 60000 });
    
    // Step 7: Verify result
    await page.click('[data-testid="tool-bash"]');
    await page.fill('[data-testid="bash-command"]', 'head -5 sorted-file.txt');
    await page.click('[data-testid="execute-bash"]');
    
    const sortedResult = await page.locator('[data-testid="tool-result"]').textContent();
    expect(sortedResult).toContain('1\n2\n3\n4\n5');
  });
});