/**
 * E2E Test Helpers
 * 
 * Reusable helper functions and utilities for E2E tests
 */

import { Page, expect, Locator } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export interface TestUser {
  id: string;
  email: string;
  role: string;
  permissions: string[];
  token?: string;
}

export interface TestWorkspace {
  id: string;
  name: string;
  description: string;
  type: string;
  template: string;
}

/**
 * Authentication and User Management
 */
export class AuthHelpers {
  constructor(private page: Page) {}
  
  async loginAs(userId: string): Promise<void> {
    const authFile = path.join(__dirname, '../fixtures/auth.json');
    const authStates = JSON.parse(fs.readFileSync(authFile, 'utf8'));
    
    const userAuth = authStates[userId];
    if (!userAuth) {
      throw new Error(`Authentication state not found for user: ${userId}`);
    }
    
    // Apply stored authentication state
    await this.page.context().addCookies(userAuth.cookies);
    
    // Set localStorage and sessionStorage
    for (const origin of userAuth.origins) {
      await this.page.goto(origin.origin);
      for (const storage of origin.localStorage) {
        await this.page.evaluate(
          ([key, value]) => localStorage.setItem(key, value),
          [storage.name, storage.value]
        );
      }
    }
    
    // Navigate to dashboard to verify authentication
    await this.page.goto('/dashboard');
    await expect(this.page.locator('[data-testid="user-menu"]')).toBeVisible();
  }
  
  async logout(): Promise<void> {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
    await expect(this.page).toHaveURL('/auth/login');
  }
  
  async getCurrentUser(): Promise<TestUser | null> {
    try {
      return await this.page.evaluate(() => {
        const userDataString = localStorage.getItem('current-user') || sessionStorage.getItem('current-user');
        return userDataString ? JSON.parse(userDataString) : null;
      });
    } catch {
      return null;
    }
  }
}

/**
 * Workspace and Project Management
 */
export class WorkspaceHelpers {
  constructor(private page: Page) {}
  
  async createWorkspace(workspace: Partial<TestWorkspace>): Promise<string> {
    await this.page.goto('/workspaces/new');
    
    // Fill workspace details
    await this.page.fill('[data-testid="workspace-name"]', workspace.name || 'Test Workspace');
    await this.page.fill('[data-testid="workspace-description"]', workspace.description || 'E2E Test Workspace');
    await this.page.selectOption('[data-testid="workspace-type"]', workspace.type || 'javascript');
    await this.page.selectOption('[data-testid="workspace-template"]', workspace.template || 'blank');
    
    // Submit creation
    await this.page.click('[data-testid="create-workspace-button"]');
    
    // Wait for workspace to be created
    await expect(this.page.locator('[data-testid="workspace-created-success"]')).toBeVisible();
    
    // Extract workspace ID from URL
    const url = this.page.url();
    const workspaceId = url.split('/workspaces/')[1];
    
    return workspaceId;
  }
  
  async openWorkspace(workspaceId: string): Promise<void> {
    await this.page.goto(`/workspaces/${workspaceId}`);
    await this.waitForWorkspaceToLoad();
  }
  
  async waitForWorkspaceToLoad(): Promise<void> {
    // Wait for essential workspace elements
    await expect(this.page.locator('[data-testid="file-explorer"]')).toBeVisible();
    await expect(this.page.locator('[data-testid="code-editor"]')).toBeVisible();
    await expect(this.page.locator('[data-testid="terminal"]')).toBeVisible();
  }
  
  async openFile(filePath: string): Promise<void> {
    // Navigate through file explorer
    const pathParts = filePath.split('/');
    let currentLocator = this.page.locator('[data-testid="file-explorer"]');
    
    for (let i = 0; i < pathParts.length - 1; i++) {
      const folderLocator = currentLocator.locator(`[data-testid="folder-${pathParts[i]}"]`);
      await folderLocator.click();
    }
    
    // Click on the file
    const fileName = pathParts[pathParts.length - 1];
    await currentLocator.locator(`[data-testid="file-${fileName}"]`).click();
    
    // Wait for file to load in editor
    await expect(this.page.locator('[data-testid="code-editor"]')).toContainText(fileName);
  }
  
  async createFile(filePath: string, content: string = ''): Promise<void> {
    // Right-click in file explorer to open context menu
    await this.page.locator('[data-testid="file-explorer"]').click({ button: 'right' });
    await this.page.click('[data-testid="context-menu-new-file"]');
    
    // Enter file name
    await this.page.fill('[data-testid="new-file-name"]', filePath);
    await this.page.press('[data-testid="new-file-name"]', 'Enter');
    
    // Add content if provided
    if (content) {
      await this.page.fill('[data-testid="code-editor"]', content);
    }
  }
}

/**
 * AI and Agent Interaction Helpers
 */
export class AIHelpers {
  constructor(private page: Page) {}
  
  async openAIChat(): Promise<void> {
    await this.page.click('[data-testid="ai-chat-toggle"]');
    await expect(this.page.locator('[data-testid="ai-chat-panel"]')).toBeVisible();
  }
  
  async sendMessage(message: string): Promise<void> {
    await this.page.fill('[data-testid="ai-chat-input"]', message);
    await this.page.click('[data-testid="ai-chat-send"]');
  }
  
  async waitForAIResponse(): Promise<string> {
    // Wait for AI response to appear
    await this.page.waitForSelector('[data-testid="ai-response"]:last-child', { timeout: 30000 });
    
    // Get the latest response text
    const responseElement = this.page.locator('[data-testid="ai-response"]:last-child');
    return await responseElement.textContent() || '';
  }
  
  async acceptCodeSuggestion(): Promise<void> {
    await this.page.click('[data-testid="accept-suggestion"]');
    await expect(this.page.locator('[data-testid="suggestion-accepted"]')).toBeVisible();
  }
  
  async rejectCodeSuggestion(): Promise<void> {
    await this.page.click('[data-testid="reject-suggestion"]');
    await expect(this.page.locator('[data-testid="suggestion-rejected"]')).toBeVisible();
  }
  
  async runCodeAnalysis(): Promise<void> {
    await this.page.click('[data-testid="analyze-code-button"]');
    await expect(this.page.locator('[data-testid="analysis-complete"]')).toBeVisible();
  }
}

/**
 * Tool Execution Helpers
 */
export class ToolHelpers {
  constructor(private page: Page) {}
  
  async executeCommand(command: string): Promise<string> {
    // Open terminal if not visible
    await this.page.click('[data-testid="terminal-toggle"]');
    
    // Type command
    await this.page.fill('[data-testid="terminal-input"]', command);
    await this.page.press('[data-testid="terminal-input"]', 'Enter');
    
    // Wait for command completion
    await this.page.waitForSelector('[data-testid="command-completed"]', { timeout: 30000 });
    
    // Get command output
    return await this.page.locator('[data-testid="terminal-output"]:last-child').textContent() || '';
  }
  
  async searchFiles(pattern: string): Promise<string[]> {
    await this.page.click('[data-testid="search-toggle"]');
    await this.page.fill('[data-testid="search-input"]', pattern);
    await this.page.press('[data-testid="search-input"]', 'Enter');
    
    // Wait for search results
    await this.page.waitForSelector('[data-testid="search-results"]');
    
    // Extract search results
    const resultElements = await this.page.locator('[data-testid="search-result-item"]').all();
    const results = [];
    
    for (const element of resultElements) {
      const text = await element.textContent();
      if (text) results.push(text);
    }
    
    return results;
  }
}

/**
 * WebSocket and Real-time Communication Helpers
 */
export class WebSocketHelpers {
  constructor(private page: Page) {}
  
  async connectToWebSocket(): Promise<void> {
    // Initialize WebSocket connection
    await this.page.evaluate(() => {
      window.testWebSocket = new WebSocket('ws://localhost:3001');
      window.testWebSocket.onopen = () => {
        document.body.setAttribute('data-websocket-connected', 'true');
      };
    });
    
    // Wait for connection
    await expect(this.page.locator('body[data-websocket-connected="true"]')).toBeVisible();
  }
  
  async sendWebSocketMessage(message: any): Promise<void> {
    await this.page.evaluate((msg) => {
      if (window.testWebSocket && window.testWebSocket.readyState === WebSocket.OPEN) {
        window.testWebSocket.send(JSON.stringify(msg));
      }
    }, message);
  }
  
  async waitForWebSocketMessage(timeout: number = 5000): Promise<any> {
    return await this.page.evaluate((timeoutMs) => {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('WebSocket message timeout')), timeoutMs);
        
        if (window.testWebSocket) {
          window.testWebSocket.onmessage = (event) => {
            clearTimeout(timer);
            resolve(JSON.parse(event.data));
          };
        } else {
          reject(new Error('WebSocket not initialized'));
        }
      });
    }, timeout);
  }
}

/**
 * Performance and Monitoring Helpers
 */
export class PerformanceHelpers {
  constructor(private page: Page) {}
  
  async measurePageLoadTime(): Promise<number> {
    const [response] = await Promise.all([
      this.page.waitForResponse('**/*'),
      this.page.goto('/dashboard')
    ]);
    
    const timing = await this.page.evaluate(() => performance.timing);
    return timing.loadEventEnd - timing.navigationStart;
  }
  
  async measureCodeCompletionTime(): Promise<number> {
    const startTime = Date.now();
    
    // Trigger code completion
    await this.page.fill('[data-testid="code-editor"]', 'console.');
    await this.page.keyboard.press('Control+Space');
    
    // Wait for completion suggestions
    await expect(this.page.locator('[data-testid="completion-popup"]')).toBeVisible();
    
    return Date.now() - startTime;
  }
  
  async getMemoryUsage(): Promise<{ used: number; total: number }> {
    return await this.page.evaluate(() => {
      return {
        used: (performance as any).memory?.usedJSHeapSize || 0,
        total: (performance as any).memory?.totalJSHeapSize || 0
      };
    });
  }
}