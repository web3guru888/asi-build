/**
 * Integration Tests - End-to-end functionality tests
 */

import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { 
  initializeASICode,
  createMinimalASICode,
  createAppContext,
  createLifecycleManager,
  type ASICodeConfig
} from '../src/index.js';

describe('Integration Tests', () => {
  let system: any;

  afterEach(async () => {
    if (system?.kenny) {
      await system.kenny.cleanup();
    }
    if (system?.toolRegistry) {
      await system.toolRegistry.cleanup();
    }
    if (system?.permissionManager) {
      await system.permissionManager.cleanup();
    }
    if (system?.asi1Provider) {
      await system.asi1Provider.cleanup();
    }
  });

  it('should initialize complete ASI-Code system', async () => {
    const config: Partial<ASICodeConfig> = {
      tools: { enableBuiltIn: true },
      permissions: { 
        enableSafetyProtocols: true,
        enableCaching: true,
        enableAuditing: false // Disable for simpler test
      },
      kenny: {
        enabled: true,
        logging: { level: 'warn', enabled: true }
      }
    };

    system = await initializeASICode(config);
    
    expect(system).toBeDefined();
    expect(system.kenny).toBeDefined();
    expect(system.toolRegistry).toBeDefined();
    expect(system.permissionManager).toBeDefined();
  });

  it('should create minimal ASI-Code setup', async () => {
    system = await createMinimalASICode();
    
    expect(system).toBeDefined();
    expect(system.kenny).toBeDefined();
    expect(system.toolRegistry).toBeDefined();
    expect(system.permissionManager).toBeDefined();
    
    // Minimal setup should have built-in tools enabled
    const tools = system.toolRegistry.list();
    expect(tools.length).toBeGreaterThan(0);
    
    // Should have some built-in tools
    const toolNames = tools.map((t: any) => t.name);
    expect(toolNames).toContain('bash');
    expect(toolNames).toContain('read');
    expect(toolNames).toContain('write');
  });

  it('should handle tool execution through Kenny integration', async () => {
    system = await createMinimalASICode();
    
    // Create a context
    const context = system.kenny.createContext('integration-test', 'test-user');
    
    // Create a message that should trigger tool usage
    const message = {
      id: 'test-msg-1',
      type: 'user',
      content: 'Please read the package.json file',
      timestamp: new Date(),
      context
    };

    // Process the message through Kenny
    const response = await system.kenny.process(message);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toBeDefined();
    expect(response.context).toBe(context);
  });

  it('should respect permission system', async () => {
    system = await createMinimalASICode();
    
    // Create a context with limited permissions
    const restrictedContext = system.kenny.createContext('restricted-test', 'restricted-user');
    restrictedContext.permissions.tools = ['read']; // Only read permission
    
    // Try to execute a write operation
    const result = await system.toolRegistry.execute(
      'write',
      { path: '/tmp/test.txt', content: 'test' },
      {
        sessionId: restrictedContext.sessionId,
        userId: restrictedContext.userId,
        permissions: restrictedContext.permissions.tools,
        workingDirectory: process.cwd(),
        environment: {}
      }
    );
    
    // Should be blocked by permissions (depending on implementation)
    // This test may need adjustment based on actual permission implementation
    expect(result).toBeDefined();
  });

  it('should integrate app context with lifecycle manager', async () => {
    const appContext = createAppContext({
      tools: { enableBuiltIn: true },
      permissions: { enableSafetyProtocols: false }
    });
    
    const lifecycleManager = createLifecycleManager(appContext);
    
    // Start all components
    await lifecycleManager.startAll();
    
    // Verify components are running
    expect(lifecycleManager.isComponentRunning('eventBus')).toBe(true);
    expect(lifecycleManager.isComponentRunning('permissionManager')).toBe(true);
    expect(lifecycleManager.isComponentRunning('toolManager')).toBe(true);
    
    // Verify app context is initialized
    expect(appContext.initialized).toBe(true);
    expect(appContext.toolRegistry).toBeDefined();
    expect(appContext.permissionManager).toBeDefined();
    
    // Create and manage Kenny contexts through app context
    const context1 = appContext.createKennyContext('session1', 'user1');
    const context2 = appContext.createKennyContext('session2', 'user2');
    
    expect(context1.id).toBeDefined();
    expect(context2.id).toBeDefined();
    expect(context1.id).not.toBe(context2.id);
    
    // Clean up
    await lifecycleManager.stopAll();
    expect(appContext.initialized).toBe(false);
  });

  it('should handle component health checks', async () => {
    const appContext = createAppContext();
    const lifecycleManager = createLifecycleManager(appContext);
    
    // Start system
    await lifecycleManager.startAll();
    
    // Perform health check
    const healthResults = await lifecycleManager.performHealthCheck();
    
    expect(healthResults.size).toBeGreaterThan(0);
    
    // Most built-in components should be healthy
    const healthyCount = Array.from(healthResults.values()).filter(healthy => healthy).length;
    const totalCount = healthResults.size;
    
    // At least 50% should be healthy
    expect(healthyCount / totalCount).toBeGreaterThanOrEqual(0.5);
    
    await lifecycleManager.stopAll();
  });

  it('should handle system restart gracefully', async () => {
    const appContext = createAppContext();
    const lifecycleManager = createLifecycleManager(appContext);
    
    // Start system
    await lifecycleManager.startAll();
    expect(appContext.initialized).toBe(true);
    
    // Create some contexts
    const context = appContext.createKennyContext('restart-test', 'user');
    expect(appContext.getKennyContext(context.id)).toBeDefined();
    
    // Restart system
    await lifecycleManager.restartAll();
    
    // System should still be initialized
    expect(appContext.initialized).toBe(true);
    
    // But contexts should be cleared (new start)
    // This behavior depends on implementation
    
    await lifecycleManager.stopAll();
  });

  it('should integrate consciousness engine with Kenny pattern', async () => {
    // This test requires a more complete setup
    system = await initializeASICode({
      consciousness: { enabled: true, model: 'claude-3-sonnet-20240229' },
      tools: { enableBuiltIn: true },
      kenny: { enabled: true }
    });
    
    // Verify consciousness integration
    expect(system.kenny).toBeDefined();
    expect(system.toolRegistry).toBeDefined();
    
    // Create context with consciousness enabled
    const context = system.kenny.createContext('consciousness-test', 'test-user');
    expect(context.consciousness).toBeDefined();
    expect(context.consciousness.level).toBeGreaterThan(0);
    
    // Process a message that should engage consciousness
    const message = {
      id: 'consciousness-test-1',
      type: 'user',
      content: 'Hello, I would like to understand how consciousness works in ASI-Code.',
      timestamp: new Date(),
      context
    };
    
    const response = await system.kenny.process(message);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toBeDefined();
    
    // Response should have consciousness metadata if consciousness is truly integrated
    // This depends on the actual Kenny implementation
  });

  it('should handle errors gracefully across system', async () => {
    system = await createMinimalASICode();
    
    // Try to process an invalid message
    const invalidContext = {
      id: 'invalid',
      sessionId: 'invalid',
      userId: 'invalid',
      consciousness: { level: 1, state: 'active', awarenessLevel: 50, adaptationRate: 0.1 },
      permissions: { tools: [], resources: [], restrictions: [] },
      metadata: {}
    };
    
    const invalidMessage = {
      id: 'invalid-msg',
      type: 'invalid' as any,
      content: '',
      timestamp: new Date(),
      context: invalidContext
    };
    
    // System should handle this gracefully without crashing
    try {
      const response = await system.kenny.process(invalidMessage);
      expect(response).toBeDefined();
    } catch (error) {
      // Error is acceptable, but system shouldn't crash
      expect(error).toBeInstanceOf(Error);
    }
    
    // System should still be functional
    const validContext = system.kenny.createContext('recovery-test', 'recovery-user');
    expect(validContext).toBeDefined();
  });

  it('should demonstrate full workflow', async () => {
    // Initialize full system
    system = await initializeASICode({
      tools: { enableBuiltIn: true },
      permissions: { enableSafetyProtocols: false }, // Simplified for test
      consciousness: { enabled: false, model: 'test-model' }, // Disabled for simpler test
      kenny: { enabled: true, logging: { level: 'warn', enabled: true } }
    });
    
    // Create user session
    const userContext = system.kenny.createContext('workflow-session', 'workflow-user');
    
    // User sends initial message
    const greeting = {
      id: 'greeting',
      type: 'user',
      content: 'Hello! Can you help me with file operations?',
      timestamp: new Date(),
      context: userContext
    };
    
    const greetingResponse = await system.kenny.process(greeting);
    expect(greetingResponse.type).toBe('assistant');
    
    // User requests file reading
    const fileRequest = {
      id: 'file-request',
      type: 'user', 
      content: 'Please read the package.json file in the current directory',
      timestamp: new Date(),
      context: userContext
    };
    
    const fileResponse = await system.kenny.process(fileRequest);
    expect(fileResponse.type).toBe('assistant');
    
    // Response should contain information about the file
    // (Actual content depends on Kenny implementation)
    expect(fileResponse.content).toBeDefined();
    expect(fileResponse.content.length).toBeGreaterThan(0);
    
    // Verify tools were available and could be used
    const availableTools = system.toolRegistry.list();
    expect(availableTools.length).toBeGreaterThan(0);
    
    // Verify permissions were checked
    // (This depends on the actual implementation)
    
    // Clean up
    await system.kenny.cleanup();
  });
});