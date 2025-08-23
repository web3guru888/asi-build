/**
 * Complete AI Coding Session E2E Test
 * 
 * Tests the full user journey from login to completing
 * a coding task with AI assistance
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, AIHelpers, ToolHelpers } from '../helpers/test-helpers';

test.describe('Complete AI Coding Session', () => {
  let authHelpers: AuthHelpers;
  let workspaceHelpers: WorkspaceHelpers;
  let aiHelpers: AIHelpers;
  let toolHelpers: ToolHelpers;
  
  test.beforeEach(async ({ page }) => {
    authHelpers = new AuthHelpers(page);
    workspaceHelpers = new WorkspaceHelpers(page);
    aiHelpers = new AIHelpers(page);
    toolHelpers = new ToolHelpers(page);
  });
  
  test('User can complete full coding workflow with AI assistance', async ({ page }) => {
    // Step 1: Authenticate as developer user
    await authHelpers.loginAs('test-developer');
    
    // Step 2: Create new workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'React Todo App',
      description: 'Building a todo app with AI assistance',
      type: 'javascript',
      template: 'react-typescript'
    });
    
    // Step 3: Open the workspace
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 4: Create a new component file
    await workspaceHelpers.createFile('src/components/TodoList.tsx', '');
    
    // Step 5: Use AI to generate component code
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage(
      'Create a React TypeScript component for a todo list with add, toggle, and delete functionality'
    );
    
    const aiResponse = await aiHelpers.waitForAIResponse();
    expect(aiResponse).toContain('interface');
    expect(aiResponse).toContain('useState');
    
    // Step 6: Accept AI code suggestion
    await aiHelpers.acceptCodeSuggestion();
    
    // Step 7: Verify code was inserted
    const editorContent = await page.locator('[data-testid="code-editor"]').textContent();
    expect(editorContent).toContain('TodoList');
    expect(editorContent).toContain('interface');
    
    // Step 8: Run code analysis
    await aiHelpers.runCodeAnalysis();
    
    // Step 9: Execute build command
    const buildOutput = await toolHelpers.executeCommand('npm run build');
    expect(buildOutput).toContain('compiled successfully');
    
    // Step 10: Search for related files
    const searchResults = await toolHelpers.searchFiles('Todo');
    expect(searchResults.length).toBeGreaterThan(0);
    
    // Step 11: Test the component
    await aiHelpers.sendMessage('Generate unit tests for the TodoList component');
    const testResponse = await aiHelpers.waitForAIResponse();
    expect(testResponse).toContain('test');
    expect(testResponse).toContain('expect');
    
    // Step 12: Create test file
    await workspaceHelpers.createFile('src/components/TodoList.test.tsx', '');
    await aiHelpers.acceptCodeSuggestion();
    
    // Step 13: Run tests
    const testOutput = await toolHelpers.executeCommand('npm test');
    expect(testOutput).toContain('PASS');
    
    // Step 14: Save and commit work
    await page.keyboard.press('Control+S');
    await expect(page.locator('[data-testid="file-saved"]')).toBeVisible();
  });
  
  test('User can refactor existing code with AI assistance', async ({ page }) => {
    // Step 1: Authenticate and setup workspace
    await authHelpers.loginAs('test-developer');
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Refactoring Project',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create a file with code that needs refactoring
    const legacyCode = `
function calculateTotal(items) {
  var total = 0;
  for (var i = 0; i < items.length; i++) {
    if (items[i].active) {
      total = total + items[i].price;
    }
  }
  return total;
}
    `;
    
    await workspaceHelpers.createFile('src/utils/calculator.js', legacyCode);
    
    // Step 3: Select code to refactor
    await page.locator('[data-testid="code-editor"]').click();
    await page.keyboard.press('Control+A');
    
    // Step 4: Request refactoring
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('Refactor this code to use modern JavaScript features');
    
    const refactoringResponse = await aiHelpers.waitForAIResponse();
    expect(refactoringResponse).toContain('const');
    expect(refactoringResponse).toContain('filter');
    expect(refactoringResponse).toContain('reduce');
    
    // Step 5: Apply refactoring
    await aiHelpers.acceptCodeSuggestion();
    
    // Step 6: Verify refactored code
    const refactoredCode = await page.locator('[data-testid="code-editor"]').textContent();
    expect(refactoredCode).toContain('const');
    expect(refactoredCode).not.toContain('var');
    
    // Step 7: Test refactored code
    await toolHelpers.executeCommand('node src/utils/calculator.js');
  });
  
  test('User can debug code with AI assistance', async ({ page }) => {
    // Step 1: Setup workspace with buggy code
    await authHelpers.loginAs('test-developer');
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Debug Session',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create file with bugs
    const buggyCode = `
function divide(a, b) {
  return a / b; // Bug: no division by zero check
}

function processArray(arr) {
  return arr.map(item => item.value.toUpperCase()); // Bug: assumes value exists
}
    `;
    
    await workspaceHelpers.createFile('src/buggy.js', buggyCode);
    
    // Step 3: Run code to trigger errors
    const output = await toolHelpers.executeCommand('node src/buggy.js');
    expect(output).toContain('Error');
    
    // Step 4: Ask AI for debugging help
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('Help me debug this code. I\'m getting errors.');
    
    const debugResponse = await aiHelpers.waitForAIResponse();
    expect(debugResponse).toContain('division by zero');
    expect(debugResponse).toContain('undefined');
    
    // Step 5: Apply bug fixes
    await aiHelpers.acceptCodeSuggestion();
    
    // Step 6: Verify fixes
    const fixedCode = await page.locator('[data-testid="code-editor"]').textContent();
    expect(fixedCode).toContain('if');
    expect(fixedCode).toContain('throw');
    
    // Step 7: Test fixed code
    const testOutput = await toolHelpers.executeCommand('node src/buggy.js');
    expect(testOutput).not.toContain('Error');
  });
  
  test('User can collaborate on code review', async ({ page, context }) => {
    // Step 1: Setup as first user (developer)
    await authHelpers.loginAs('test-developer');
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Code Review Session',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create code for review
    const codeForReview = `
export class UserService {
  async createUser(userData) {
    // TODO: Add validation
    const user = await this.database.save(userData);
    return user;
  }
}
    `;
    
    await workspaceHelpers.createFile('src/services/UserService.js', codeForReview);
    
    // Step 3: Request code review from AI
    await aiHelpers.openAIChat();
    await aiHelpers.sendMessage('Please review this code and suggest improvements');
    
    const reviewResponse = await aiHelpers.waitForAIResponse();
    expect(reviewResponse).toContain('validation');
    expect(reviewResponse).toContain('error handling');
    
    // Step 4: Open second browser context for reviewer
    const reviewerPage = await context.newPage();
    const reviewerAuth = new AuthHelpers(reviewerPage);
    const reviewerWorkspace = new WorkspaceHelpers(reviewerPage);
    const reviewerAI = new AIHelpers(reviewerPage);
    
    // Step 5: Login as admin (reviewer)
    await reviewerAuth.loginAs('test-admin');
    await reviewerWorkspace.openWorkspace(workspaceId);
    
    // Step 6: Add review comments
    await reviewerPage.locator('[data-testid="code-editor"]').click();
    await reviewerPage.click('[data-testid="add-comment"]');
    await reviewerPage.fill('[data-testid="comment-text"]', 'Please add input validation');
    await reviewerPage.click('[data-testid="submit-comment"]');
    
    // Step 7: Verify comment appears in original session
    await expect(page.locator('[data-testid="review-comment"]')).toBeVisible();
    
    // Step 8: Address review feedback with AI
    await aiHelpers.sendMessage('Add input validation as suggested in the review');
    const validationResponse = await aiHelpers.waitForAIResponse();
    expect(validationResponse).toContain('validation');
    
    await aiHelpers.acceptCodeSuggestion();
    
    // Step 9: Mark review as resolved
    await page.click('[data-testid="resolve-comment"]');
    await expect(page.locator('[data-testid="comment-resolved"]')).toBeVisible();
  });
});