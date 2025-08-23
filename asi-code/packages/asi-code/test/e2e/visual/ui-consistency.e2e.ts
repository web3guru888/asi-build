/**
 * Visual Regression Testing for UI Consistency
 * 
 * Tests visual consistency across different browsers,
 * screen sizes, and user interactions
 */

import { test, expect } from '@playwright/test';
import { AuthHelpers, WorkspaceHelpers, AIHelpers } from '../helpers/test-helpers';

test.describe('Visual Regression Testing', () => {
  let authHelpers: AuthHelpers;
  let workspaceHelpers: WorkspaceHelpers;
  let aiHelpers: AIHelpers;
  
  test.beforeEach(async ({ page }) => {
    authHelpers = new AuthHelpers(page);
    workspaceHelpers = new WorkspaceHelpers(page);
    aiHelpers = new AIHelpers(page);
    
    await authHelpers.loginAs('test-developer');
  });
  
  test('Dashboard visual consistency across viewports', async ({ page }) => {
    // Step 1: Navigate to dashboard
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="dashboard-loaded"]')).toBeVisible();
    
    // Step 2: Desktop view (1920x1080)
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForLoadState('networkidle');
    
    await expect(page).toHaveScreenshot('dashboard-desktop-1920.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
    
    // Step 3: Laptop view (1366x768)
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.waitForTimeout(500); // Allow layout adjustment
    
    await expect(page).toHaveScreenshot('dashboard-laptop-1366.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
    
    // Step 4: Tablet view (768x1024)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('dashboard-tablet-768.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
    
    // Step 5: Mobile view (375x667)
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('dashboard-mobile-375.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
  });
  
  test('Code editor visual consistency', async ({ page }) => {
    // Step 1: Create workspace and open editor
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Visual Test Workspace',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create test file with various code elements
    const testCode = `
import React, { useState, useEffect } from 'react';
import { Button, Input, Modal } from './components';

interface User {
  id: number;
  name: string;
  email: string;
  isActive: boolean;
}

// Main component with various syntax highlighting
const UserManager: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    fetchUsers();
  }, []);
  
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/users');
      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="user-manager">
      <h1>User Management</h1>
      {loading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      <ul>
        {users.map(user => (
          <li key={user.id}>
            {user.name} - {user.email}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UserManager;
    `;
    
    await workspaceHelpers.createFile('src/UserManager.tsx', testCode);
    
    // Step 3: Test editor with different themes
    
    // Light theme
    await page.click('[data-testid="theme-selector"]');
    await page.click('[data-testid="theme-light"]');
    await page.waitForTimeout(300);
    
    await expect(page.locator('[data-testid="code-editor"]')).toHaveScreenshot('editor-light-theme.png', {
      threshold: 0.1,
      animations: 'disabled'
    });
    
    // Dark theme
    await page.click('[data-testid="theme-selector"]');
    await page.click('[data-testid="theme-dark"]');
    await page.waitForTimeout(300);
    
    await expect(page.locator('[data-testid="code-editor"]')).toHaveScreenshot('editor-dark-theme.png', {
      threshold: 0.1,
      animations: 'disabled'
    });
    
    // High contrast theme
    await page.click('[data-testid="theme-selector"]');
    await page.click('[data-testid="theme-high-contrast"]');
    await page.waitForTimeout(300);
    
    await expect(page.locator('[data-testid="code-editor"]')).toHaveScreenshot('editor-high-contrast-theme.png', {
      threshold: 0.1,
      animations: 'disabled'
    });
    
    // Step 4: Test editor with line numbers and other features
    await page.click('[data-testid="view-options"]');
    await page.check('[data-testid="show-line-numbers"]');
    await page.check('[data-testid="show-minimap"]');
    await page.check('[data-testid="show-whitespace"]');
    
    await expect(page.locator('[data-testid="code-editor"]')).toHaveScreenshot('editor-full-features.png', {
      threshold: 0.1,
      animations: 'disabled'
    });
  });
  
  test('AI chat interface visual consistency', async ({ page }) => {
    // Step 1: Setup workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'AI Chat Visual Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Open AI chat
    await aiHelpers.openAIChat();
    
    // Step 3: Test empty state
    await expect(page.locator('[data-testid="ai-chat-panel"]')).toHaveScreenshot('ai-chat-empty.png', {
      threshold: 0.1
    });
    
    // Step 4: Send message and test conversation view
    await aiHelpers.sendMessage('Hello, can you help me create a React component?');
    
    // Mock AI response for consistent visuals
    await page.evaluate(() => {
      const chatContainer = document.querySelector('[data-testid="ai-chat-messages"]');
      if (chatContainer) {
        chatContainer.innerHTML += `
          <div class="ai-message" data-testid="ai-response">
            <div class="message-header">
              <span class="sender">AI Assistant</span>
              <span class="timestamp">2:34 PM</span>
            </div>
            <div class="message-content">
              I'd be happy to help you create a React component! Here's a simple example:
              
              <pre><code>import React from 'react';

const MyComponent = ({ title, children }) => {
  return (
    <div className="my-component">
      <h2>{title}</h2>
      <div className="content">
        {children}
      </div>
    </div>
  );
};

export default MyComponent;</code></pre>

              Would you like me to add any specific functionality to this component?
            </div>
          </div>
        `;
      }
    });
    
    await expect(page.locator('[data-testid="ai-chat-panel"]')).toHaveScreenshot('ai-chat-conversation.png', {
      threshold: 0.1
    });
    
    // Step 5: Test code suggestion UI
    await page.evaluate(() => {
      const chatContainer = document.querySelector('[data-testid="ai-chat-messages"]');
      if (chatContainer) {
        chatContainer.innerHTML += `
          <div class="ai-message code-suggestion" data-testid="ai-response">
            <div class="message-header">
              <span class="sender">AI Assistant</span>
              <span class="timestamp">2:35 PM</span>
            </div>
            <div class="message-content">
              <div class="suggestion-header">
                <span class="suggestion-icon">💡</span>
                <span class="suggestion-title">Code Suggestion</span>
              </div>
              <div class="suggestion-actions">
                <button class="accept-btn">Accept</button>
                <button class="reject-btn">Reject</button>
                <button class="modify-btn">Modify</button>
              </div>
            </div>
          </div>
        `;
      }
    });
    
    await expect(page.locator('[data-testid="ai-chat-panel"]')).toHaveScreenshot('ai-chat-code-suggestion.png', {
      threshold: 0.1
    });
  });
  
  test('Agent orchestration dashboard visuals', async ({ page }) => {
    // Step 1: Navigate to agent dashboard
    await page.goto('/agents/dashboard');
    
    // Step 2: Mock agent data for consistent visuals
    await page.evaluate(() => {
      // Add mock agents to the dashboard
      const dashboard = document.querySelector('[data-testid="agent-dashboard"]');
      if (dashboard) {
        dashboard.innerHTML = `
          <div class="dashboard-header">
            <h1>Agent Orchestration Dashboard</h1>
            <div class="system-status">
              <span class="status-indicator healthy"></span>
              <span>System Healthy</span>
            </div>
          </div>
          
          <div class="agent-grid">
            <div class="agent-card supervisor">
              <div class="agent-header">
                <span class="agent-type">Supervisor</span>
                <span class="agent-status running">Running</span>
              </div>
              <div class="agent-info">
                <h3>Main Supervisor</h3>
                <p>Managing 5 worker agents</p>
                <div class="metrics">
                  <span>Tasks: 23</span>
                  <span>Uptime: 2h 15m</span>
                </div>
              </div>
            </div>
            
            <div class="agent-card worker">
              <div class="agent-header">
                <span class="agent-type">Worker</span>
                <span class="agent-status busy">Busy</span>
              </div>
              <div class="agent-info">
                <h3>Code Analyzer</h3>
                <p>Analyzing React components</p>
                <div class="progress-bar">
                  <div class="progress" style="width: 75%;"></div>
                </div>
              </div>
            </div>
            
            <div class="agent-card worker">
              <div class="agent-header">
                <span class="agent-type">Worker</span>
                <span class="agent-status idle">Idle</span>
              </div>
              <div class="agent-info">
                <h3>Test Runner</h3>
                <p>Waiting for tasks</p>
                <div class="metrics">
                  <span>Last: 5m ago</span>
                </div>
              </div>
            </div>
            
            <div class="agent-card specialist">
              <div class="agent-header">
                <span class="agent-type">Specialist</span>
                <span class="agent-status working">Working</span>
              </div>
              <div class="agent-info">
                <h3>Performance Optimizer</h3>
                <p>Optimizing bundle size</p>
                <div class="progress-bar">
                  <div class="progress" style="width: 45%;"></div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="task-queue">
            <h2>Task Queue</h2>
            <div class="queue-items">
              <div class="task-item high-priority">
                <span class="priority">High</span>
                <span class="task">Security scan</span>
                <span class="status">Pending</span>
              </div>
              <div class="task-item medium-priority">
                <span class="priority">Medium</span>
                <span class="task">Documentation update</span>
                <span class="status">In Progress</span>
              </div>
              <div class="task-item low-priority">
                <span class="priority">Low</span>
                <span class="task">Code formatting</span>
                <span class="status">Queued</span>
              </div>
            </div>
          </div>
        `;
      }
    });
    
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('agent-dashboard-overview.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
    
    // Step 3: Test agent details modal
    await page.click('[data-testid="agent-card-supervisor"]');
    
    await page.evaluate(() => {
      document.body.innerHTML += `
        <div class="modal-overlay" data-testid="agent-details-modal">
          <div class="modal-content">
            <div class="modal-header">
              <h2>Supervisor Agent Details</h2>
              <button class="close-btn">×</button>
            </div>
            <div class="modal-body">
              <div class="agent-metrics">
                <div class="metric">
                  <label>CPU Usage</label>
                  <div class="metric-bar">
                    <div class="metric-fill" style="width: 45%;"></div>
                  </div>
                  <span>45%</span>
                </div>
                <div class="metric">
                  <label>Memory Usage</label>
                  <div class="metric-bar">
                    <div class="metric-fill" style="width: 60%;"></div>
                  </div>
                  <span>60%</span>
                </div>
                <div class="metric">
                  <label>Task Success Rate</label>
                  <div class="metric-bar">
                    <div class="metric-fill success" style="width: 95%;"></div>
                  </div>
                  <span>95%</span>
                </div>
              </div>
              <div class="managed-agents">
                <h3>Managed Agents</h3>
                <ul>
                  <li>Code Analyzer (Busy)</li>
                  <li>Test Runner (Idle)</li>
                  <li>Performance Optimizer (Working)</li>
                  <li>Security Scanner (Pending)</li>
                  <li>Documentation Generator (Idle)</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      `;
    });
    
    await expect(page.locator('[data-testid="agent-details-modal"]')).toHaveScreenshot('agent-details-modal.png', {
      threshold: 0.1
    });
  });
  
  test('File explorer and navigation visuals', async ({ page }) => {
    // Step 1: Setup workspace with complex folder structure
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'File Explorer Visual Test',
      type: 'javascript',
      template: 'react-typescript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Create nested folder structure
    await page.evaluate(() => {
      const fileExplorer = document.querySelector('[data-testid="file-explorer"]');
      if (fileExplorer) {
        fileExplorer.innerHTML = `
          <div class="file-tree">
            <div class="folder expanded">
              <span class="folder-icon">📁</span>
              <span class="folder-name">src</span>
              <div class="folder-contents">
                <div class="folder">
                  <span class="folder-icon">📁</span>
                  <span class="folder-name">components</span>
                  <div class="folder-contents">
                    <div class="file">
                      <span class="file-icon">⚛️</span>
                      <span class="file-name">Button.tsx</span>
                    </div>
                    <div class="file">
                      <span class="file-icon">⚛️</span>
                      <span class="file-name">Modal.tsx</span>
                    </div>
                    <div class="file">
                      <span class="file-icon">⚛️</span>
                      <span class="file-name">Input.tsx</span>
                    </div>
                  </div>
                </div>
                <div class="folder">
                  <span class="folder-icon">📁</span>
                  <span class="folder-name">hooks</span>
                  <div class="folder-contents">
                    <div class="file">
                      <span class="file-icon">🎣</span>
                      <span class="file-name">useAuth.ts</span>
                    </div>
                    <div class="file">
                      <span class="file-icon">🎣</span>
                      <span class="file-name">useLocalStorage.ts</span>
                    </div>
                  </div>
                </div>
                <div class="folder">
                  <span class="folder-icon">📁</span>
                  <span class="folder-name">utils</span>
                  <div class="folder-contents">
                    <div class="file">
                      <span class="file-icon">🛠️</span>
                      <span class="file-name">helpers.ts</span>
                    </div>
                    <div class="file">
                      <span class="file-icon">🛠️</span>
                      <span class="file-name">constants.ts</span>
                    </div>
                  </div>
                </div>
                <div class="file active">
                  <span class="file-icon">⚛️</span>
                  <span class="file-name">App.tsx</span>
                </div>
                <div class="file">
                  <span class="file-icon">📄</span>
                  <span class="file-name">index.tsx</span>
                </div>
              </div>
            </div>
            <div class="folder">
              <span class="folder-icon">📁</span>
              <span class="folder-name">public</span>
            </div>
            <div class="file">
              <span class="file-icon">📦</span>
              <span class="file-name">package.json</span>
            </div>
            <div class="file">
              <span class="file-icon">⚙️</span>
              <span class="file-name">tsconfig.json</span>
            </div>
          </div>
        `;
      }
    });
    
    await page.waitForTimeout(300);
    
    await expect(page.locator('[data-testid="file-explorer"]')).toHaveScreenshot('file-explorer-structure.png', {
      threshold: 0.1
    });
    
    // Step 3: Test context menu
    await page.click('[data-testid="file-App.tsx"]', { button: 'right' });
    
    await page.evaluate(() => {
      document.body.innerHTML += `
        <div class="context-menu" style="position: fixed; top: 200px; left: 300px;">
          <div class="menu-item">
            <span class="menu-icon">📖</span>
            <span>Open</span>
          </div>
          <div class="menu-item">
            <span class="menu-icon">✏️</span>
            <span>Rename</span>
          </div>
          <div class="menu-item">
            <span class="menu-icon">📋</span>
            <span>Copy</span>
          </div>
          <div class="menu-item">
            <span class="menu-icon">✂️</span>
            <span>Cut</span>
          </div>
          <div class="menu-separator"></div>
          <div class="menu-item danger">
            <span class="menu-icon">🗑️</span>
            <span>Delete</span>
          </div>
        </div>
      `;
    });
    
    await expect(page.locator('.context-menu')).toHaveScreenshot('file-context-menu.png', {
      threshold: 0.1
    });
  });
  
  test('Responsive layout consistency', async ({ page }) => {
    // Step 1: Create workspace
    const workspaceId = await workspaceHelpers.createWorkspace({
      name: 'Responsive Layout Test',
      type: 'javascript'
    });
    await workspaceHelpers.openWorkspace(workspaceId);
    
    // Step 2: Test different breakpoints
    const breakpoints = [
      { name: 'xl', width: 1920, height: 1080 },
      { name: 'lg', width: 1024, height: 768 },
      { name: 'md', width: 768, height: 1024 },
      { name: 'sm', width: 640, height: 960 },
      { name: 'xs', width: 375, height: 667 }
    ];
    
    for (const breakpoint of breakpoints) {
      await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height });
      await page.waitForTimeout(500);
      
      // Test workspace layout at this breakpoint
      await expect(page).toHaveScreenshot(`workspace-${breakpoint.name}.png`, {
        fullPage: true,
        threshold: 0.2,
        animations: 'disabled'
      });
    }
    
    // Step 3: Test panel arrangements
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Show all panels
    await aiHelpers.openAIChat();
    await page.click('[data-testid="tools-panel-toggle"]');
    await page.click('[data-testid="terminal-toggle"]');
    
    await expect(page).toHaveScreenshot('workspace-all-panels.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
    
    // Step 4: Test collapsed panels
    await page.click('[data-testid="collapse-left-panel"]');
    await page.click('[data-testid="collapse-bottom-panel"]');
    
    await expect(page).toHaveScreenshot('workspace-collapsed-panels.png', {
      fullPage: true,
      threshold: 0.2,
      animations: 'disabled'
    });
  });
});