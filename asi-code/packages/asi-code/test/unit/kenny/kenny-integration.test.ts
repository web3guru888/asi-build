/**
 * Unit tests for Kenny Integration Pattern (KIP)
 * 
 * Tests the core Kenny Integration Pattern implementation including:
 * - Context creation and management
 * - Message processing
 * - Event emission
 * - Error handling
 * - State management
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  DefaultKennyIntegration,
  createKennyIntegration,
  type KennyContext,
  type KennyMessage,
  type KennyIntegrationPattern
} from '../../../src/kenny/index.js';
import { createMockConfig } from '../../test-utils.js';

describe('Kenny Integration Pattern', () => {
  let kenny: KennyIntegrationPattern;
  let mockConfig: any;

  beforeEach(() => {
    kenny = createKennyIntegration();
    mockConfig = createMockConfig();
  });

  afterEach(async () => {
    await kenny.cleanup();
  });

  describe('initialization', () => {
    it('should initialize with valid config', async () => {
      const eventSpy = vi.fn();
      kenny.on('initialized', eventSpy);

      await kenny.initialize(mockConfig);

      expect(eventSpy).toHaveBeenCalledWith({ config: mockConfig });
    });

    it('should throw error when processing message before initialization', async () => {
      const context = kenny.createContext('session-1');
      const message: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Hello',
        timestamp: new Date(),
        context
      };

      await expect(kenny.process(message)).rejects.toThrow('Kenny Integration Pattern not initialized');
    });
  });

  describe('context management', () => {
    beforeEach(async () => {
      await kenny.initialize(mockConfig);
    });

    it('should create context with correct properties', () => {
      const sessionId = 'session-123';
      const userId = 'user-456';
      
      const context = kenny.createContext(sessionId, userId);

      expect(context).toMatchObject({
        sessionId,
        userId,
        metadata: {},
        consciousness: {
          level: 1,
          state: 'active',
          lastActivity: expect.any(Date)
        }
      });
      expect(context.id).toMatch(/^ctx_\d+_[a-z0-9]+$/);
    });

    it('should create context without userId', () => {
      const sessionId = 'session-123';
      
      const context = kenny.createContext(sessionId);

      expect(context).toMatchObject({
        sessionId,
        userId: undefined,
        metadata: {},
        consciousness: {
          level: 1,
          state: 'active',
          lastActivity: expect.any(Date)
        }
      });
    });

    it('should emit context:created event', () => {
      const eventSpy = vi.fn();
      kenny.on('context:created', eventSpy);

      const context = kenny.createContext('session-1');

      expect(eventSpy).toHaveBeenCalledWith(context);
    });

    it('should retrieve context by id', async () => {
      const context = kenny.createContext('session-1');
      
      const retrieved = await kenny.getContext(context.id);
      
      expect(retrieved).toEqual(context);
    });

    it('should return null for non-existent context', async () => {
      const retrieved = await kenny.getContext('non-existent');
      
      expect(retrieved).toBeNull();
    });

    it('should update context', async () => {
      const context = kenny.createContext('session-1');
      const eventSpy = vi.fn();
      kenny.on('context:updated', eventSpy);
      
      const updates = {
        metadata: { test: 'value' },
        consciousness: {
          ...context.consciousness,
          level: 2
        }
      };
      
      await kenny.updateContext(context.id, updates);
      
      const updated = await kenny.getContext(context.id);
      expect(updated).toMatchObject(updates);
      expect(eventSpy).toHaveBeenCalledWith({
        contextId: context.id,
        updates,
        context: updated
      });
    });

    it('should throw error when updating non-existent context', async () => {
      await expect(kenny.updateContext('non-existent', {})).rejects.toThrow('Context not found: non-existent');
    });
  });

  describe('message processing', () => {
    let context: KennyContext;

    beforeEach(async () => {
      await kenny.initialize(mockConfig);
      context = kenny.createContext('session-1', 'user-1');
    });

    it('should process user message and return assistant response', async () => {
      const receivedSpy = vi.fn();
      const processedSpy = vi.fn();
      kenny.on('message:received', receivedSpy);
      kenny.on('message:processed', processedSpy);

      const userMessage: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Hello Kenny',
        timestamp: new Date(),
        context
      };

      const response = await kenny.process(userMessage);

      expect(response).toMatchObject({
        type: 'assistant',
        content: 'Processed: Hello Kenny',
        context,
        metadata: {
          processed: true,
          originalMessageId: 'msg-1'
        }
      });
      expect(response.id).toMatch(/^resp_\d+_[a-z0-9]+$/);
      expect(response.timestamp).toBeInstanceOf(Date);

      expect(receivedSpy).toHaveBeenCalledWith(userMessage);
      expect(processedSpy).toHaveBeenCalledWith({
        original: userMessage,
        response
      });
    });

    it('should update consciousness state during processing', async () => {
      const userMessage: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Hello Kenny',
        timestamp: new Date(),
        context
      };

      const beforeProcessing = await kenny.getContext(context.id);
      const originalActivity = beforeProcessing!.consciousness.lastActivity;

      // Wait a bit to ensure timestamp difference
      await new Promise(resolve => setTimeout(resolve, 10));

      await kenny.process(userMessage);

      const afterProcessing = await kenny.getContext(context.id);
      expect(afterProcessing!.consciousness.state).toBe('active');
      expect(afterProcessing!.consciousness.lastActivity.getTime())
        .toBeGreaterThan(originalActivity.getTime());
    });

    it('should handle system messages', async () => {
      const systemMessage: KennyMessage = {
        id: 'msg-sys-1',
        type: 'system',
        content: 'System initialization',
        timestamp: new Date(),
        context
      };

      const response = await kenny.process(systemMessage);

      expect(response.type).toBe('assistant');
      expect(response.content).toBe('Processed: System initialization');
    });

    it('should handle tool messages', async () => {
      const toolMessage: KennyMessage = {
        id: 'msg-tool-1',
        type: 'tool',
        content: 'Tool execution result',
        timestamp: new Date(),
        context,
        metadata: { toolName: 'test-tool' }
      };

      const response = await kenny.process(toolMessage);

      expect(response.type).toBe('assistant');
      expect(response.content).toBe('Processed: Tool execution result');
    });
  });

  describe('event handling', () => {
    beforeEach(async () => {
      await kenny.initialize(mockConfig);
    });

    it('should emit all expected events during typical workflow', async () => {
      const events: string[] = [];
      
      kenny.on('context:created', () => events.push('context:created'));
      kenny.on('message:received', () => events.push('message:received'));
      kenny.on('context:updated', () => events.push('context:updated'));
      kenny.on('message:processed', () => events.push('message:processed'));

      const context = kenny.createContext('session-1');
      const message: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Test message',
        timestamp: new Date(),
        context
      };

      await kenny.process(message);

      expect(events).toEqual([
        'context:created',
        'message:received',
        'context:updated',
        'message:processed'
      ]);
    });
  });

  describe('cleanup', () => {
    beforeEach(async () => {
      await kenny.initialize(mockConfig);
    });

    it('should clear all contexts and listeners', async () => {
      const eventSpy = vi.fn();
      kenny.on('cleaned', eventSpy);
      
      // Create some contexts
      kenny.createContext('session-1');
      kenny.createContext('session-2');

      await kenny.cleanup();

      // Contexts should be cleared
      expect(await kenny.getContext('session-1')).toBeNull();
      expect(await kenny.getContext('session-2')).toBeNull();
      
      // Should emit cleaned event
      expect(eventSpy).toHaveBeenCalled();
      
      // Event listeners should be removed
      expect(kenny.listenerCount('initialized')).toBe(0);
      expect(kenny.listenerCount('message:received')).toBe(0);
    });
  });

  describe('error handling', () => {
    it('should handle initialization errors gracefully', async () => {
      const invalidConfig = null as any;
      
      // Should not throw, but might not work as expected
      await expect(kenny.initialize(invalidConfig)).resolves.not.toThrow();
    });

    it('should handle context update with invalid data', async () => {
      await kenny.initialize(mockConfig);
      const context = kenny.createContext('session-1');
      
      // This should work since we're using Object.assign
      const invalidUpdate = { invalidProperty: 'test' } as any;
      await expect(kenny.updateContext(context.id, invalidUpdate))
        .resolves.not.toThrow();
      
      const updated = await kenny.getContext(context.id);
      expect((updated as any).invalidProperty).toBe('test');
    });
  });

  describe('DefaultKennyIntegration class', () => {
    it('should be an instance of EventEmitter', () => {
      const integration = new DefaultKennyIntegration();
      expect(integration).toBeInstanceOf(require('eventemitter3').EventEmitter);
    });

    it('should implement KennyIntegrationPattern interface', () => {
      const integration = new DefaultKennyIntegration();
      
      expect(typeof integration.initialize).toBe('function');
      expect(typeof integration.process).toBe('function');
      expect(typeof integration.createContext).toBe('function');
      expect(typeof integration.updateContext).toBe('function');
      expect(typeof integration.getContext).toBe('function');
      expect(typeof integration.cleanup).toBe('function');
    });
  });

  describe('factory function', () => {
    it('should create new instance each time', () => {
      const integration1 = createKennyIntegration();
      const integration2 = createKennyIntegration();
      
      expect(integration1).not.toBe(integration2);
      expect(integration1).toBeInstanceOf(DefaultKennyIntegration);
      expect(integration2).toBeInstanceOf(DefaultKennyIntegration);
    });
  });

  describe('consciousness state management', () => {
    beforeEach(async () => {
      await kenny.initialize(mockConfig);
    });

    it('should initialize consciousness with correct defaults', () => {
      const context = kenny.createContext('session-1');
      
      expect(context.consciousness).toEqual({
        level: 1,
        state: 'active',
        lastActivity: expect.any(Date)
      });
    });

    it('should update consciousness during message processing', async () => {
      const context = kenny.createContext('session-1');
      const originalActivity = context.consciousness.lastActivity;
      
      // Ensure time difference
      await new Promise(resolve => setTimeout(resolve, 10));
      
      const message: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Test',
        timestamp: new Date(),
        context
      };
      
      await kenny.process(message);
      
      const updatedContext = await kenny.getContext(context.id);
      expect(updatedContext!.consciousness.state).toBe('active');
      expect(updatedContext!.consciousness.lastActivity.getTime())
        .toBeGreaterThan(originalActivity.getTime());
    });
  });

  describe('message ID generation', () => {
    beforeEach(async () => {
      await kenny.initialize(mockConfig);
    });

    it('should generate unique message IDs', async () => {
      const context = kenny.createContext('session-1');
      const message: KennyMessage = {
        id: 'msg-1',
        type: 'user',
        content: 'Test',
        timestamp: new Date(),
        context
      };

      const response1 = await kenny.process(message);
      const response2 = await kenny.process(message);

      expect(response1.id).not.toBe(response2.id);
      expect(response1.id).toMatch(/^resp_\d+_[a-z0-9]+$/);
      expect(response2.id).toMatch(/^resp_\d+_[a-z0-9]+$/);
    });
  });

  describe('context ID generation', () => {
    it('should generate unique context IDs', () => {
      const context1 = kenny.createContext('session-1');
      const context2 = kenny.createContext('session-2');

      expect(context1.id).not.toBe(context2.id);
      expect(context1.id).toMatch(/^ctx_\d+_[a-z0-9]+$/);
      expect(context2.id).toMatch(/^ctx_\d+_[a-z0-9]+$/);
    });
  });
});
