/**
 * Real-time Multi-User Collaboration E2E Tests
 * 
 * Tests simultaneous user editing, conflict resolution,
 * shared workspaces, and collaborative features
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, WebSocketHelpers, AIHelpers } from '../helpers/test-helpers';

test.describe('Real-time Multi-User Collaboration', () => {
  test('Multiple users can edit files simultaneously with conflict resolution', async ({ browser }) => {
    // Step 1: Create two browser contexts for different users
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();
    
    const auth1 = new AuthHelpers(page1);
    const auth2 = new AuthHelpers(page2);
    const workspace1 = new WorkspaceHelpers(page1);
    const workspace2 = new WorkspaceHelpers(page2);
    const ws1 = new WebSocketHelpers(page1);
    const ws2 = new WebSocketHelpers(page2);
    
    // Step 2: Login as different users
    await auth1.loginAs('test-developer');
    await auth2.loginAs('test-admin');
    
    // Step 3: Create shared workspace
    const workspaceId = await workspace1.createWorkspace({
      name: 'Collaborative Workspace',
      type: 'javascript',
      template: 'react-typescript'
    });
    
    // Step 4: Share workspace with second user
    await page1.goto(`/workspaces/${workspaceId}/settings`);
    await page1.click('[data-testid="share-workspace"]');
    await page1.fill('[data-testid="collaborator-email"]', 'admin@test.asi-code.dev');
    await page1.selectOption('[data-testid="permission-level"]', 'edit');
    await page1.click('[data-testid="send-invitation"]');
    
    // Step 5: Accept invitation and join workspace
    await workspace2.openWorkspace(workspaceId);
    await expect(page2.locator('[data-testid="workspace-loaded"]')).toBeVisible();
    
    // Step 6: Create file and start editing simultaneously
    await workspace1.createFile('src/shared.js', '// Shared file for collaboration testing\n');
    
    // Wait for file to appear in second user's view
    await expect(page2.locator('[data-testid="file-shared.js"]')).toBeVisible();
    
    // Step 7: Both users edit the same file
    await page1.click('[data-testid="file-shared.js"]');
    await page2.click('[data-testid="file-shared.js"]');
    
    // User 1 adds code at the top
    await page1.locator('[data-testid="code-editor"]').click();
    await page1.keyboard.press('Home');
    await page1.keyboard.type('const user1Addition = "hello";\n');
    
    // User 2 adds code at the bottom
    await page2.locator('[data-testid="code-editor"]').click();
    await page2.keyboard.press('End');
    await page2.keyboard.type('\nconst user2Addition = "world";');
    
    // Step 8: Verify real-time synchronization
    await expect(page1.locator('[data-testid="collaborator-cursor-admin"]')).toBeVisible();
    await expect(page2.locator('[data-testid="collaborator-cursor-developer"]')).toBeVisible();
    
    // Step 9: Create merge conflict scenario
    await page1.keyboard.press('End');
    await page1.keyboard.type('\nconst conflictVariable = "version1";');
    
    await page2.keyboard.press('End');  
    await page2.keyboard.type('\nconst conflictVariable = "version2";');
    
    // Step 10: Verify conflict detection and resolution
    await expect(page1.locator('[data-testid="merge-conflict-detected"]')).toBeVisible();
    await expect(page2.locator('[data-testid="merge-conflict-detected"]')).toBeVisible();
    
    // Resolve conflict on page1
    await page1.click('[data-testid="resolve-conflict"]');
    await page1.click('[data-testid="accept-both-changes"]');
    await page1.click('[data-testid="apply-resolution"]');
    
    // Step 11: Verify conflict resolution propagates
    await expect(page2.locator('[data-testid="conflict-resolved"]')).toBeVisible();
    
    const finalContent1 = await page1.locator('[data-testid="code-editor"]').textContent();
    const finalContent2 = await page2.locator('[data-testid="code-editor"]').textContent();
    
    expect(finalContent1).toBe(finalContent2);
    expect(finalContent1).toContain('user1Addition');
    expect(finalContent1).toContain('user2Addition');
    expect(finalContent1).toContain('version1');
    expect(finalContent1).toContain('version2');
    
    await context1.close();
    await context2.close();
  });
  
  test('Shared AI sessions and collaborative code generation', async ({ browser }) => {
    // Step 1: Setup multiple users
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();
    
    const auth1 = new AuthHelpers(page1);
    const auth2 = new AuthHelpers(page2);
    const workspace1 = new WorkspaceHelpers(page1);
    const workspace2 = new WorkspaceHelpers(page2);
    const ai1 = new AIHelpers(page1);
    const ai2 = new AIHelpers(page2);
    
    await auth1.loginAs('test-developer');
    await auth2.loginAs('test-admin');
    
    // Step 2: Create shared workspace
    const workspaceId = await workspace1.createWorkspace({
      name: 'AI Collaboration Test',
      type: 'javascript'
    });
    
    await page1.goto(`/workspaces/${workspaceId}/settings`);
    await page1.click('[data-testid="share-workspace"]');
    await page1.fill('[data-testid="collaborator-email"]', 'admin@test.asi-code.dev');
    await page1.click('[data-testid="send-invitation"]');
    
    await workspace2.openWorkspace(workspaceId);
    
    // Step 3: Start shared AI session
    await ai1.openAIChat();
    await page1.click('[data-testid="start-shared-ai-session"]');
    await page1.fill('[data-testid="session-name"]', 'Collaborative Feature Development');
    await page1.click('[data-testid="create-shared-session"]');
    
    // Step 4: Second user joins AI session
    await ai2.openAIChat();
    await expect(page2.locator('[data-testid="shared-ai-session-available"]')).toBeVisible();
    await page2.click('[data-testid="join-shared-session"]');
    
    // Step 5: Collaborative AI interaction
    await ai1.sendMessage('Let\'s create a user authentication system. Can you start with the login component?');
    
    // Second user can see the message
    await expect(page2.locator('[data-testid="ai-message"]')).toContainText('authentication system');
    
    const aiResponse1 = await ai1.waitForAIResponse();
    expect(aiResponse1).toContain('login component');
    
    // Step 6: Second user adds to the conversation
    await ai2.sendMessage('Also add password validation and remember me functionality');
    
    const aiResponse2 = await ai2.waitForAIResponse();
    expect(aiResponse2).toContain('password validation');
    expect(aiResponse2).toContain('remember me');
    
    // Step 7: Collaborative code acceptance
    await page1.click('[data-testid="accept-suggestion"]');
    await workspace1.createFile('src/Login.jsx', '');
    
    // Second user can see the new file
    await expect(page2.locator('[data-testid="file-Login.jsx"]')).toBeVisible();
    
    // Step 8: Continue collaborative development
    await ai2.sendMessage('Now let\'s add form validation');
    const validationResponse = await ai2.waitForAIResponse();
    
    await page2.click('[data-testid="accept-suggestion"]');
    
    // Both users see the updated code
    const code1 = await page1.locator('[data-testid="code-editor"]').textContent();
    const code2 = await page2.locator('[data-testid="code-editor"]').textContent();
    expect(code1).toBe(code2);
    expect(code1).toContain('validation');
    
    await context1.close();
    await context2.close();
  });
  
  test('Live cursor tracking and presence awareness', async ({ browser }) => {
    // Step 1: Setup collaborative environment
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    const context3 = await browser.newContext();
    
    const pages = [
      await context1.newPage(),
      await context2.newPage(), 
      await context3.newPage()
    ];
    
    const users = ['test-developer', 'test-admin', 'test-viewer'];
    const authHelpers = pages.map(page => new AuthHelpers(page));
    const workspaceHelpers = pages.map(page => new WorkspaceHelpers(page));
    
    // Step 2: Login all users
    for (let i = 0; i < users.length; i++) {
      await authHelpers[i].loginAs(users[i]);
    }
    
    // Step 3: Create and share workspace
    const workspaceId = await workspaceHelpers[0].createWorkspace({
      name: 'Presence Tracking Test',
      type: 'javascript'
    });
    
    // Share with other users
    await pages[0].goto(`/workspaces/${workspaceId}/settings`);
    await pages[0].click('[data-testid="share-workspace"]');
    await pages[0].fill('[data-testid="collaborator-email"]', 'admin@test.asi-code.dev');
    await pages[0].click('[data-testid="add-collaborator"]');
    await pages[0].fill('[data-testid="collaborator-email"]', 'viewer@test.asi-code.dev');
    await pages[0].click('[data-testid="add-collaborator"]');
    await pages[0].click('[data-testid="save-collaborators"]');
    
    // Step 4: All users join workspace
    for (let i = 1; i < pages.length; i++) {
      await workspaceHelpers[i].openWorkspace(workspaceId);
    }
    
    // Step 5: Create file for collaborative editing
    await workspaceHelpers[0].createFile('src/collaborative.js', `
// Collaborative editing test file
function example() {
  return "hello world";
}
    `);
    
    // Step 6: All users open the same file
    for (const page of pages) {
      await page.click('[data-testid="file-collaborative.js"]');
    }
    
    // Step 7: Test presence indicators
    await expect(pages[0].locator('[data-testid="active-collaborators"]')).toContainText('3 users');
    
    // Verify each user sees others
    await expect(pages[0].locator('[data-testid="user-admin-presence"]')).toBeVisible();
    await expect(pages[0].locator('[data-testid="user-viewer-presence"]')).toBeVisible();
    
    await expect(pages[1].locator('[data-testid="user-developer-presence"]')).toBeVisible();
    await expect(pages[1].locator('[data-testid="user-viewer-presence"]')).toBeVisible();
    
    // Step 8: Test cursor tracking
    await pages[0].locator('[data-testid="code-editor"]').click();
    await pages[0].keyboard.press('ArrowDown');
    await pages[0].keyboard.press('End');
    
    // Other users should see cursor movement
    await expect(pages[1].locator('[data-testid="cursor-developer"]')).toBeVisible();
    await expect(pages[2].locator('[data-testid="cursor-developer"]')).toBeVisible();
    
    // Step 9: Test selection tracking
    await pages[1].locator('[data-testid="code-editor"]').click();
    await pages[1].keyboard.press('Control+A');
    
    // Others should see selection
    await expect(pages[0].locator('[data-testid="selection-admin"]')).toBeVisible();
    await expect(pages[2].locator('[data-testid="selection-admin"]')).toBeVisible();
    
    // Step 10: Test typing indicators
    await pages[2].locator('[data-testid="code-editor"]').click();
    await pages[2].keyboard.type('// Adding comment');
    
    // Others should see typing indicator
    await expect(pages[0].locator('[data-testid="typing-indicator-viewer"]')).toBeVisible();
    await expect(pages[1].locator('[data-testid="typing-indicator-viewer"]')).toBeVisible();
    
    // Step 11: Test user disconnection
    await context2.close(); // User 2 leaves
    
    // Remaining users should see updated presence
    await expect(pages[0].locator('[data-testid="active-collaborators"]')).toContainText('2 users');
    await expect(pages[2].locator('[data-testid="active-collaborators"]')).toContainText('2 users');
    
    await context1.close();
    await context3.close();
  });
  
  test('Collaborative code review and comments', async ({ browser }) => {
    // Step 1: Setup reviewer and developer
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const developerPage = await context1.newPage();
    const reviewerPage = await context2.newPage();
    
    const developerAuth = new AuthHelpers(developerPage);
    const reviewerAuth = new AuthHelpers(reviewerPage);
    const developerWorkspace = new WorkspaceHelpers(developerPage);
    const reviewerWorkspace = new WorkspaceHelpers(reviewerPage);
    
    await developerAuth.loginAs('test-developer');
    await reviewerAuth.loginAs('test-admin');
    
    // Step 2: Create workspace and code to review
    const workspaceId = await developerWorkspace.createWorkspace({
      name: 'Code Review Test',
      type: 'javascript'
    });
    
    await developerWorkspace.createFile('src/feature.js', `
function processUserData(userData) {
  // TODO: Add validation
  const processed = userData.map(user => {
    return {
      id: user.id,
      name: user.name.toUpperCase(),
      email: user.email
    };
  });
  
  return processed;
}

export default processUserData;
    `);
    
    // Step 3: Share workspace for review
    await developerPage.goto(`/workspaces/${workspaceId}/settings`);
    await developerPage.click('[data-testid="share-workspace"]');
    await developerPage.fill('[data-testid="collaborator-email"]', 'admin@test.asi-code.dev');
    await developerPage.selectOption('[data-testid="permission-level"]', 'review');
    await developerPage.click('[data-testid="send-invitation"]');
    
    // Step 4: Start code review process
    await developerPage.click('[data-testid="request-review"]');
    await developerPage.fill('[data-testid="review-description"]', 'Please review the user data processing function');
    await developerPage.click('[data-testid="submit-review-request"]');
    
    // Step 5: Reviewer opens and reviews code
    await reviewerWorkspace.openWorkspace(workspaceId);
    await reviewerPage.click('[data-testid="file-feature.js"]');
    
    // Add review comments
    await reviewerPage.click('[data-testid="line-3"]'); // TODO line
    await reviewerPage.click('[data-testid="add-comment"]');
    await reviewerPage.fill('[data-testid="comment-text"]', 'Please add input validation. Check for null/undefined userData and validate user object structure.');
    await reviewerPage.selectOption('[data-testid="comment-type"]', 'suggestion');
    await reviewerPage.click('[data-testid="submit-comment"]');
    
    // Add another comment
    await reviewerPage.click('[data-testid="line-6"]'); // name.toUpperCase() line
    await reviewerPage.click('[data-testid="add-comment"]');
    await reviewerPage.fill('[data-testid="comment-text"]', 'Consider handling cases where name might be null or undefined');
    await reviewerPage.selectOption('[data-testid="comment-type"]', 'issue');
    await reviewerPage.click('[data-testid="submit-comment"]');
    
    // Step 6: Developer sees review comments in real-time
    await expect(developerPage.locator('[data-testid="review-comment"]')).toHaveCount(2);
    await expect(developerPage.locator('[data-testid="comment-notification"]')).toBeVisible();
    
    // Step 7: Developer responds to comments
    await developerPage.click('[data-testid="comment-1"]');
    await developerPage.click('[data-testid="reply-to-comment"]');
    await developerPage.fill('[data-testid="reply-text"]', 'Good point! I\'ll add validation. Should I use a schema validator?');
    await developerPage.click('[data-testid="submit-reply"]');
    
    // Step 8: Reviewer sees reply and suggests solution
    await expect(reviewerPage.locator('[data-testid="comment-reply"]')).toBeVisible();
    await reviewerPage.click('[data-testid="reply-to-comment"]');
    await reviewerPage.fill('[data-testid="reply-text"]', 'Yes, joi or zod would work well. Here\'s a quick example: const schema = z.object({ id: z.number(), name: z.string(), email: z.string().email() });');
    await reviewerPage.click('[data-testid="submit-reply"]');
    
    // Step 9: Developer implements suggestions
    await developerPage.locator('[data-testid="code-editor"]').click();
    await developerPage.keyboard.press('Home');
    await developerPage.keyboard.type(`import { z } from 'zod';\n\nconst userSchema = z.object({\n  id: z.number(),\n  name: z.string(),\n  email: z.string().email()\n});\n\n`);
    
    // Update function
    const updatedFunction = `
function processUserData(userData) {
  // Validate input
  if (!userData || !Array.isArray(userData)) {
    throw new Error('Invalid input: userData must be an array');
  }
  
  const processed = userData.map(user => {
    userSchema.parse(user); // Validate each user
    return {
      id: user.id,
      name: user.name?.toUpperCase() || '',
      email: user.email
    };
  });
  
  return processed;
}`;
    
    await developerPage.keyboard.selectAll();
    await developerPage.keyboard.type(updatedFunction);
    
    // Step 10: Mark comments as resolved
    await developerPage.click('[data-testid="resolve-comment-1"]');
    await developerPage.click('[data-testid="resolve-comment-2"]');
    
    // Step 11: Reviewer approves changes
    await expect(reviewerPage.locator('[data-testid="comment-resolved"]')).toHaveCount(2);
    await reviewerPage.click('[data-testid="approve-changes"]');
    await reviewerPage.fill('[data-testid="approval-message"]', 'Great improvements! The validation looks good and error handling is much better.');
    await reviewerPage.click('[data-testid="submit-approval"]');
    
    // Step 12: Developer sees approval
    await expect(developerPage.locator('[data-testid="review-approved"]')).toBeVisible();
    await expect(developerPage.locator('[data-testid="approval-message"]')).toContainText('Great improvements');
    
    await context1.close();
    await context2.close();
  });
  
  test('Workspace permissions and access control', async ({ browser }) => {
    // Step 1: Setup users with different roles
    const contexts = await Promise.all([
      browser.newContext(), // Owner
      browser.newContext(), // Editor
      browser.newContext(), // Viewer
      browser.newContext()  // Non-member
    ]);
    
    const pages = await Promise.all(contexts.map(ctx => ctx.newPage()));
    const [ownerPage, editorPage, viewerPage, outsiderPage] = pages;
    
    const ownerAuth = new AuthHelpers(ownerPage);
    const editorAuth = new AuthHelpers(editorPage);
    const viewerAuth = new AuthHelpers(viewerPage);
    const outsiderAuth = new AuthHelpers(outsiderPage);
    
    await ownerAuth.loginAs('test-admin');
    await editorAuth.loginAs('test-developer');
    await viewerAuth.loginAs('test-viewer');
    await outsiderAuth.loginAs('test-developer'); // Different instance
    
    // Step 2: Owner creates workspace
    const ownerWorkspace = new WorkspaceHelpers(ownerPage);
    const workspaceId = await ownerWorkspace.createWorkspace({
      name: 'Permission Test Workspace',
      type: 'javascript'
    });
    
    // Step 3: Setup permissions
    await ownerPage.goto(`/workspaces/${workspaceId}/settings`);
    
    // Add editor
    await ownerPage.click('[data-testid="add-collaborator"]');
    await ownerPage.fill('[data-testid="collaborator-email"]', 'dev@test.asi-code.dev');
    await ownerPage.selectOption('[data-testid="permission-level"]', 'edit');
    await ownerPage.click('[data-testid="send-invitation"]');
    
    // Add viewer
    await ownerPage.click('[data-testid="add-collaborator"]');
    await ownerPage.fill('[data-testid="collaborator-email"]', 'viewer@test.asi-code.dev');
    await ownerPage.selectOption('[data-testid="permission-level"]', 'view');
    await ownerPage.click('[data-testid="send-invitation"]');
    
    await ownerPage.click('[data-testid="save-permissions"]');
    
    // Step 4: Test owner permissions (full access)
    await ownerWorkspace.createFile('src/owner-file.js', 'console.log("owner file");');
    await expect(ownerPage.locator('[data-testid="file-created"]')).toBeVisible();
    
    // Step 5: Test editor permissions
    const editorWorkspace = new WorkspaceHelpers(editorPage);
    await editorWorkspace.openWorkspace(workspaceId);
    
    // Can read files
    await editorPage.click('[data-testid="file-owner-file.js"]');
    await expect(editorPage.locator('[data-testid="file-content"]')).toContainText('owner file');
    
    // Can create files
    await editorWorkspace.createFile('src/editor-file.js', 'console.log("editor file");');
    await expect(editorPage.locator('[data-testid="file-created"]')).toBeVisible();
    
    // Can edit existing files
    await editorPage.locator('[data-testid="code-editor"]').fill('console.log("edited by editor");');
    await editorPage.keyboard.press('Control+S');
    await expect(editorPage.locator('[data-testid="file-saved"]')).toBeVisible();
    
    // Cannot access admin settings
    await editorPage.goto(`/workspaces/${workspaceId}/settings`);
    await expect(editorPage.locator('[data-testid="access-denied"]')).toBeVisible();
    
    // Step 6: Test viewer permissions
    const viewerWorkspace = new WorkspaceHelpers(viewerPage);
    await viewerWorkspace.openWorkspace(workspaceId);
    
    // Can read files
    await viewerPage.click('[data-testid="file-owner-file.js"]');
    await expect(viewerPage.locator('[data-testid="file-content"]')).toBeVisible();
    
    // Cannot edit files
    await expect(viewerPage.locator('[data-testid="code-editor"]')).toHaveAttribute('readonly', 'true');
    
    // Cannot create files
    await expect(viewerPage.locator('[data-testid="create-file-button"]')).toBeDisabled();
    
    // Step 7: Test non-member access
    await outsiderPage.goto(`/workspaces/${workspaceId}`);
    await expect(outsiderPage.locator('[data-testid="workspace-not-found"]')).toBeVisible();
    
    // Step 8: Test permission changes
    await ownerPage.goto(`/workspaces/${workspaceId}/settings`);
    await ownerPage.click('[data-testid="edit-collaborator-dev"]');
    await ownerPage.selectOption('[data-testid="permission-level"]', 'view');
    await ownerPage.click('[data-testid="update-permissions"]');
    
    // Editor should lose edit access
    await editorPage.reload();
    await expect(editorPage.locator('[data-testid="code-editor"]')).toHaveAttribute('readonly', 'true');
    
    await Promise.all(contexts.map(ctx => ctx.close()));
  });
});