/**
 * Unit tests for Tool Registry
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ToolRegistry, createToolRegistry } from '../../../src/tool/tool-registry.js';
import { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from '../../../src/tool/base-tool.js';
import { createMockTool, createMockToolExecutionContext, createFailingMockTool } from '../../test-utils.js';
import { resetMessageBus } from '../../../src/kenny/message-bus.js';

// Mock Kenny Integration to avoid circular dependencies
vi.mock('../../../src/kenny/integration.js', () => ({
  getKennyIntegration: () => ({
    getMessageBus: () => ({
      publishSubsystem: vi.fn().mockResolvedValue(undefined)
    })
  })
}));

// Mock tool implementation for testing
class TestTool extends BaseTool {
  constructor(name: string = 'test-tool', overrides: Partial<ToolDefinition> = {}) {
    super({
      name,
      description: 'A test tool for unit testing',
      parameters: [
        {
          name: 'input',
          type: 'string',
          description: 'Test input parameter',
          required: true
        }
      ],
      category: 'custom',
      version: '1.0.0',
      author: 'test',
      ...overrides
    });
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    return {
      success: true,
      data: {
        input: parameters.input,
        output: `Processed: ${parameters.input}`,
        timestamp: new Date().toISOString()
      }
    };
  }
}

class SlowTestTool extends BaseTool {
  constructor() {
    super({
      name: 'slow-tool',
      description: 'A slow tool for timeout testing',
      parameters: [],
      category: 'custom',
      version: '1.0.0'
    });
  }

  async execute(): Promise<ToolResult> {
    await new Promise(resolve => setTimeout(resolve, 2000));
    return { success: true, data: 'slow result' };
  }
}

describe('ToolRegistry', () => {
  let registry: ToolRegistry;
  
  beforeEach(async () => {
    resetMessageBus();
    registry = new ToolRegistry();
    await registry.initialize();
  });
  
  afterEach(async () => {
    await registry.shutdown();
  });

  describe('Initialization and Lifecycle', () => {
    it('should initialize successfully', () => {
      expect(registry).toBeInstanceOf(ToolRegistry);
      expect(registry.metadata.id).toBe('tool-registry');
      expect(registry.status).toBe('running');
    });

    it('should start and stop properly', async () => {
      await registry.start();
      expect(registry.status).toBe('running');
      
      await registry.stop();
      expect(registry.status).toBe('stopped');
    });

    it('should shutdown gracefully', async () => {
      const tool = new TestTool();
      await registry.register(tool);
      
      await registry.shutdown();
      expect(registry.status).toBe('stopped');
    });
  });

  describe('Tool Registration', () => {
    it('should register a tool successfully', async () => {
      const tool = new TestTool();
      
      await registry.register(tool);
      
      const registeredTool = registry.get('test-tool');
      expect(registeredTool).toBe(tool);
      
      const definitions = registry.list();
      expect(definitions).toHaveLength(1);
      expect(definitions[0].name).toBe('test-tool');
    });

    it('should register tool with tags', async () => {
      const tool = new TestTool();
      const tags = ['testing', 'utility'];
      
      await registry.register(tool, tags);
      
      const filteredTools = registry.list({ tags });
      expect(filteredTools).toHaveLength(1);
    });

    it('should prevent duplicate tool registration', async () => {
      const tool1 = new TestTool();
      const tool2 = new TestTool();
      
      await registry.register(tool1);
      
      await expect(registry.register(tool2)).rejects.toThrow(
        'Tool test-tool is already registered'
      );
    });

    it('should unregister tools', async () => {
      const tool = new TestTool();
      await registry.register(tool);
      
      expect(registry.get('test-tool')).toBe(tool);
      
      await registry.unregister('test-tool');
      
      expect(registry.get('test-tool')).toBeNull();
      expect(registry.list()).toHaveLength(0);
    });

    it('should handle unregistering non-existent tool', async () => {
      await expect(registry.unregister('non-existent')).resolves.toBeUndefined();
    });
  });

  describe('Tool Execution', () => {
    let tool: TestTool;
    let context: ToolExecutionContext;

    beforeEach(async () => {
      tool = new TestTool();
      context = createMockToolExecutionContext();
      await registry.register(tool);
    });

    it('should execute tool successfully', async () => {
      const result = await registry.execute('test-tool', { input: 'hello' }, context);
      
      expect(result.success).toBe(true);
      expect(result.data.input).toBe('hello');
      expect(result.data.output).toBe('Processed: hello');
    });

    it('should validate parameters before execution', async () => {
      const result = await registry.execute('test-tool', {}, context); // Missing required 'input'
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid parameters');
    });

    it('should handle tool execution errors', async () => {
      const failingTool = createFailingMockTool('Test error');
      await registry.register(failingTool);
      
      const result = await registry.execute('failing-mock-tool', { input: 'test' }, context);
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Test error');
    });

    it('should handle non-existent tool execution', async () => {
      const result = await registry.execute('non-existent', {}, context);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('not found or not active');
    });

    it('should respect concurrent execution limits', async () => {
      const limitedRegistry = new ToolRegistry({ maxConcurrentExecutions: 1 });
      await limitedRegistry.initialize();
      
      const slowTool = new SlowTestTool();
      await limitedRegistry.register(slowTool);
      
      // Start first execution (will be slow)
      const promise1 = limitedRegistry.execute('slow-tool', {}, context);
      
      // Immediately try second execution - should be rejected due to limit
      const result2 = await limitedRegistry.execute('slow-tool', {}, context);
      
      expect(result2.success).toBe(false);
      expect(result2.error).toContain('Maximum concurrent executions reached');
      
      // Wait for first execution to complete
      const result1 = await promise1;
      expect(result1.success).toBe(true);
      
      await limitedRegistry.shutdown();
    });

    it('should handle execution timeout', async () => {
      const timeoutRegistry = new ToolRegistry({ defaultTimeout: 100 });
      await timeoutRegistry.initialize();
      
      const slowTool = new SlowTestTool();
      await timeoutRegistry.register(slowTool);
      
      const result = await timeoutRegistry.execute('slow-tool', {}, context);
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Execution timeout');
      
      await timeoutRegistry.shutdown();
    });
  });

  describe('Permission Management', () => {
    let mockPermissionManager: any;
    let registryWithPerms: ToolRegistry;

    beforeEach(async () => {
      mockPermissionManager = {
        checkPermission: vi.fn().mockResolvedValue({ granted: true })
      };
      
      registryWithPerms = new ToolRegistry({ permissionManager: mockPermissionManager });
      await registryWithPerms.initialize();
    });

    afterEach(async () => {
      await registryWithPerms.shutdown();
    });

    it('should check permissions before execution', async () => {
      const tool = new TestTool();
      const context = createMockToolExecutionContext({ userId: 'test-user' });
      
      await registryWithPerms.register(tool);
      await registryWithPerms.execute('test-tool', { input: 'test' }, context);
      
      expect(mockPermissionManager.checkPermission).toHaveBeenCalledWith({
        userId: 'test-user',
        sessionId: 'mock-session',
        resource: 'tool.test-tool',
        operation: 'execute',
        context: {
          toolName: 'test-tool',
          category: 'custom'
        }
      });
    });

    it('should deny execution when permissions are denied', async () => {
      mockPermissionManager.checkPermission.mockResolvedValue({ granted: false });
      
      const tool = new TestTool();
      const context = createMockToolExecutionContext({ userId: 'test-user' });
      
      await registryWithPerms.register(tool);
      const result = await registryWithPerms.execute('test-tool', { input: 'test' }, context);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('Permission denied');
    });
  });

  describe('Metrics and Monitoring', () => {
    beforeEach(async () => {
      const tool = new TestTool();
      await registry.register(tool);
    });

    it('should track execution metrics', async () => {
      const context = createMockToolExecutionContext();
      
      // Execute tool multiple times
      await registry.execute('test-tool', { input: 'test1' }, context);
      await registry.execute('test-tool', { input: 'test2' }, context);
      
      const metrics = registry.getMetrics('test-tool');
      
      expect(metrics).toBeDefined();
      expect(metrics.executionCount).toBe(2);
      expect(metrics.successCount).toBe(2);
      expect(metrics.errorCount).toBe(0);
      expect(metrics.averageExecutionTime).toBeGreaterThan(0);
    });

    it('should track error metrics', async () => {
      const failingTool = createFailingMockTool();
      await registry.register(failingTool);
      
      const context = createMockToolExecutionContext();
      await registry.execute('failing-mock-tool', { input: 'test' }, context);
      
      const metrics = registry.getMetrics('failing-mock-tool');
      
      expect(metrics.executionCount).toBe(1);
      expect(metrics.successCount).toBe(0);
      expect(metrics.errorCount).toBe(1);
      expect(metrics.lastError).toBe('Mock tool error');
    });

    it('should get all metrics', () => {
      const allMetrics = registry.getMetrics();
      
      expect(Array.isArray(allMetrics)).toBe(true);
      expect(allMetrics).toHaveLength(1);
      expect(allMetrics[0].toolName).toBe('test-tool');
    });
  });

  describe('Tool Filtering and Listing', () => {
    beforeEach(async () => {
      const tool1 = new TestTool('file-tool', { category: 'file' });
      const tool2 = new TestTool('system-tool', { category: 'system' });
      const tool3 = new TestTool('custom-tool', { category: 'custom' });
      
      await registry.register(tool1, ['file', 'utility']);
      await registry.register(tool2, ['system', 'admin']);
      await registry.register(tool3, ['custom']);
    });

    it('should filter tools by category', () => {
      const fileTools = registry.list({ category: 'file' });
      const systemTools = registry.list({ category: 'system' });
      
      expect(fileTools).toHaveLength(1);
      expect(fileTools[0].name).toBe('file-tool');
      
      expect(systemTools).toHaveLength(1);
      expect(systemTools[0].name).toBe('system-tool');
    });

    it('should filter tools by tags', () => {
      const utilityTools = registry.list({ tags: ['utility'] });
      const adminTools = registry.list({ tags: ['admin'] });
      
      expect(utilityTools).toHaveLength(1);
      expect(utilityTools[0].name).toBe('file-tool');
      
      expect(adminTools).toHaveLength(1);
      expect(adminTools[0].name).toBe('system-tool');
    });

    it('should filter tools by status', () => {
      const activeTools = registry.list({ status: 'active' });
      
      expect(activeTools).toHaveLength(3);
      expect(activeTools.map(t => t.name)).toContain('file-tool');
      expect(activeTools.map(t => t.name)).toContain('system-tool');
      expect(activeTools.map(t => t.name)).toContain('custom-tool');
    });
  });

  describe('Execution Management', () => {
    let tool: TestTool;
    let context: ToolExecutionContext;

    beforeEach(async () => {
      tool = new TestTool();
      context = createMockToolExecutionContext();
      await registry.register(tool);
    });

    it('should track running executions', async () => {
      const slowTool = new SlowTestTool();
      await registry.register(slowTool);
      
      // Start long-running execution
      const promise = registry.execute('slow-tool', {}, context);
      
      // Check running executions
      const runningExecutions = registry.getRunningExecutions();
      expect(runningExecutions).toHaveLength(1);
      expect(runningExecutions[0].toolName).toBe('slow-tool');
      expect(runningExecutions[0].status).toBe('running');
      
      // Wait for completion
      await promise;
      
      // Should no longer be running
      expect(registry.getRunningExecutions()).toHaveLength(0);
    });

    it('should cancel running executions', async () => {
      const slowTool = new SlowTestTool();
      await registry.register(slowTool);
      
      // Start execution
      const promise = registry.execute('slow-tool', {}, context);
      
      const runningExecutions = registry.getRunningExecutions();
      const executionId = runningExecutions[0].id;
      
      // Cancel execution
      const cancelled = await registry.cancelExecution(executionId);
      expect(cancelled).toBe(true);
      
      // Wait for promise to resolve
      await promise;
      
      expect(registry.getRunningExecutions()).toHaveLength(0);
    });

    it('should handle cancelling non-existent execution', async () => {
      const cancelled = await registry.cancelExecution('non-existent-id');
      expect(cancelled).toBe(false);
    });
  });

  describe('Health Check', () => {
    it('should provide health status', async () => {
      const tool1 = new TestTool('tool1');
      const tool2 = new TestTool('tool2');
      
      await registry.register(tool1);
      await registry.register(tool2);
      
      const health = await registry.healthCheck();
      
      expect(health).toMatchObject({
        status: 'healthy',
        timestamp: expect.any(Date),
        details: {
          totalTools: 2,
          activeTools: 2,
          runningExecutions: 0,
          queuedExecutions: 0
        }
      });
      expect(health.message).toContain('2 active tools');
    });

    it('should report unhealthy when stopped', async () => {
      await registry.stop();
      
      const health = await registry.healthCheck();
      expect(health.status).toBe('unhealthy');
    });
  });

  describe('Factory Function', () => {
    it('should create registry using factory function', () => {
      const config = {
        enableMetrics: true,
        maxConcurrentExecutions: 5
      };
      
      const factoryRegistry = createToolRegistry(config);
      
      expect(factoryRegistry).toBeInstanceOf(ToolRegistry);
    });
  });

  describe('Event Handling', () => {
    it('should emit tool registration events', async () => {
      const registrationSpy = vi.fn();
      registry.on('tool.registered', registrationSpy);
      
      const tool = new TestTool();
      await registry.register(tool, ['test-tag']);
      
      expect(registrationSpy).toHaveBeenCalledWith({
        tool: expect.objectContaining({
          tool,
          definition: tool.definition,
          tags: ['test-tag']
        })
      });
    });

    it('should emit execution events', async () => {
      const executionStartSpy = vi.fn();
      const executionCompleteSpy = vi.fn();
      
      registry.on('execution.start', executionStartSpy);
      registry.on('execution.complete', executionCompleteSpy);
      
      const tool = new TestTool();
      await registry.register(tool);
      
      const context = createMockToolExecutionContext();
      const result = await registry.execute('test-tool', { input: 'test' }, context);
      
      expect(executionStartSpy).toHaveBeenCalledWith({
        executionId: expect.stringMatching(/^exec_\d+/),
        toolName: 'test-tool',
        parameters: ['input']
      });
      
      expect(executionCompleteSpy).toHaveBeenCalledWith({
        executionId: expect.stringMatching(/^exec_\d+/),
        toolName: 'test-tool',
        result
      });
    });

    it('should emit error events for failed executions', async () => {
      const errorSpy = vi.fn();
      registry.on('execution.error', errorSpy);
      
      const failingTool = createFailingMockTool('Test error');
      await registry.register(failingTool);
      
      const context = createMockToolExecutionContext();
      await registry.execute('failing-mock-tool', { input: 'test' }, context);
      
      expect(errorSpy).toHaveBeenCalledWith({
        executionId: expect.stringMatching(/^exec_\d+/),
        toolName: 'failing-mock-tool',
        error: 'Test error'
      });
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle tool cleanup errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      // Create a tool that throws during cleanup
      const problematicTool = new TestTool();
      problematicTool.cleanup = vi.fn().mockRejectedValue(new Error('Cleanup failed'));
      
      await registry.register(problematicTool);
      await registry.unregister('test-tool');
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error cleaning up tool test-tool:',
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });

    it('should handle initialization with existing permission manager', async () => {
      const mockPermissionManager = {
        checkPermission: vi.fn().mockResolvedValue({ granted: true })
      };
      
      const registryWithPerms = new ToolRegistry();
      await registryWithPerms.initialize({ permissionManager: mockPermissionManager });
      
      expect(registryWithPerms).toBeInstanceOf(ToolRegistry);
      await registryWithPerms.shutdown();
    });

    it('should maintain execution info consistency', async () => {
      const tool = new TestTool();
      await registry.register(tool);
      
      const context = createMockToolExecutionContext();
      
      // Start execution and immediately check execution info
      const promise = registry.execute('test-tool', { input: 'test' }, context);
      
      // Execution should exist in registry
      let runningExecutions = registry.getRunningExecutions();
      if (runningExecutions.length > 0) {
        expect(runningExecutions[0]).toMatchObject({
          toolName: 'test-tool',
          parameters: { input: 'test' },
          context,
          status: 'running'
        });
      }
      
      const result = await promise;
      
      // After completion, should no longer be running
      expect(registry.getRunningExecutions()).toHaveLength(0);
      expect(result.success).toBe(true);
    });
  });
});