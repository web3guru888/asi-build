/**
 * Consciousness Engine Tests
 */

import { describe, it, expect, beforeEach, afterEach, mock } from 'bun:test';
import { 
  createConsciousnessEngine, 
  defaultConsciousnessConfig,
  type ConsciousnessEngine,
  type ConsciousnessConfig 
} from '../src/consciousness/index.js';
import type { KennyMessage, KennyContext } from '../src/kenny/index.js';
import type { Provider } from '../src/provider/index.js';

describe('Consciousness Engine', () => {
  let engine: ConsciousnessEngine;
  let mockProvider: Provider;
  let context: KennyContext;

  beforeEach(() => {
    // Create mock provider
    mockProvider = {
      name: 'test-provider',
      config: {
        name: 'test-provider',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet-20240229'
      },
      initialize: mock(async () => {}),
      generate: mock(async (messages) => ({
        content: `Processed: ${messages[messages.length - 1].content}`,
        model: 'claude-3-sonnet-20240229',
        usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 }
      })),
      streamGenerate: mock(async function* (messages) {
        yield 'Processed: ';
        yield messages[messages.length - 1].content;
        return {
          content: `Processed: ${messages[messages.length - 1].content}`,
          model: 'claude-3-sonnet-20240229',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 }
        };
      }),
      isAvailable: mock(async () => true),
      cleanup: mock(async () => {}),
      on: mock(() => mockProvider),
      off: mock(() => mockProvider),
      emit: mock(() => false),
      removeAllListeners: mock(() => mockProvider)
    } as any;

    // Create test context
    context = {
      id: 'test-context',
      sessionId: 'test-session',
      userId: 'test-user',
      consciousness: {
        level: 50,
        state: 'active',
        awarenessLevel: 60,
        adaptationRate: 0.1
      },
      permissions: {
        tools: ['read', 'write'],
        resources: ['file-system'],
        restrictions: []
      },
      metadata: {
        createdAt: new Date().toISOString(),
        lastActive: new Date().toISOString()
      }
    };

    // Create consciousness engine
    engine = createConsciousnessEngine(defaultConsciousnessConfig);
  });

  afterEach(async () => {
    await engine.cleanup();
  });

  it('should create consciousness engine with default config', () => {
    expect(engine).toBeDefined();
    expect(engine.config).toEqual(defaultConsciousnessConfig);
    expect(engine.config.enabled).toBe(true);
  });

  it('should initialize with provider', async () => {
    await engine.initialize(mockProvider);
    expect(mockProvider.initialize).toHaveBeenCalled();
  });

  it('should process message with consciousness when enabled', async () => {
    const config: ConsciousnessConfig = { ...defaultConsciousnessConfig, enabled: true };
    engine = createConsciousnessEngine(config);
    await engine.initialize(mockProvider);

    const message: KennyMessage = {
      id: 'test-msg-1',
      type: 'user',
      content: 'Hello, consciousness!',
      timestamp: new Date(),
      context
    };

    const response = await engine.processMessage(message, context);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toContain('Processed: Hello, consciousness!');
    expect(response.metadata?.consciousness).toBeDefined();
    expect(mockProvider.generate).toHaveBeenCalled();
  });

  it('should pass through without consciousness when disabled', async () => {
    const config: ConsciousnessConfig = { ...defaultConsciousnessConfig, enabled: false };
    engine = createConsciousnessEngine(config);

    const message: KennyMessage = {
      id: 'test-msg-2',
      type: 'user',
      content: 'Hello, basic mode!',
      timestamp: new Date(),
      context
    };

    const response = await engine.processMessage(message, context);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toContain('Echo: Hello, basic mode!');
    expect(response.metadata?.consciousness).toBe(false);
    expect(mockProvider.generate).not.toHaveBeenCalled();
  });

  it('should update consciousness state', async () => {
    const initialState = await engine.getState(context.id);
    expect(initialState).toBeNull();

    const message: KennyMessage = {
      id: 'test-msg-3',
      type: 'user',
      content: 'This is a complex message that should increase awareness levels due to its length and complexity.',
      timestamp: new Date(),
      context
    };

    const updatedState = await engine.updateState(context, { message });
    
    expect(updatedState).toBeDefined();
    expect(updatedState.level).toBeGreaterThanOrEqual(0);
    expect(updatedState.awareness).toBeGreaterThanOrEqual(0);
    expect(updatedState.engagement).toBeGreaterThanOrEqual(0);
    expect(updatedState.timestamp).toBeInstanceOf(Date);
  });

  it('should add and retrieve memories', async () => {
    const memoryContent = { interaction: 'test', type: 'learning' };
    
    const memoryId = await engine.addMemory({
      type: 'interaction',
      content: memoryContent,
      importance: 80,
      lastAccessed: new Date(),
      associatedContext: context.id
    });

    expect(memoryId).toBeDefined();
    expect(memoryId).toMatch(/^mem_/);

    const memories = await engine.retrieveMemories(context.id, 'interaction', 5);
    expect(memories).toHaveLength(1);
    expect(memories[0].content).toEqual(memoryContent);
    expect(memories[0].importance).toBe(80);
  });

  it('should filter memories by context', async () => {
    const context2Id = 'other-context';
    
    // Add memory for first context
    await engine.addMemory({
      type: 'pattern',
      content: { pattern: 'context1' },
      importance: 70,
      lastAccessed: new Date(),
      associatedContext: context.id
    });

    // Add memory for second context
    await engine.addMemory({
      type: 'pattern',
      content: { pattern: 'context2' },
      importance: 60,
      lastAccessed: new Date(),
      associatedContext: context2Id
    });

    // Add global memory (no context)
    await engine.addMemory({
      type: 'preference',
      content: { global: 'setting' },
      importance: 90,
      lastAccessed: new Date()
    });

    const context1Memories = await engine.retrieveMemories(context.id);
    const context2Memories = await engine.retrieveMemories(context2Id);

    // Context 1 should get its specific memory + global memory
    expect(context1Memories).toHaveLength(2);
    
    // Context 2 should get its specific memory + global memory
    expect(context2Memories).toHaveLength(2);
  });

  it('should emit events during processing', async () => {
    await engine.initialize(mockProvider);
    
    let responseEvent: any = null;
    engine.on('consciousness:response', (event) => {
      responseEvent = event;
    });

    const message: KennyMessage = {
      id: 'test-msg-4',
      type: 'user',
      content: 'Test event emission',
      timestamp: new Date(),
      context
    };

    await engine.processMessage(message, context);
    
    expect(responseEvent).toBeDefined();
    expect(responseEvent.input).toEqual(message);
    expect(responseEvent.output).toBeDefined();
    expect(responseEvent.state).toBeDefined();
  });

  it('should handle errors gracefully', async () => {
    const errorProvider = {
      ...mockProvider,
      generate: mock(async () => {
        throw new Error('Provider error');
      })
    };

    await engine.initialize(errorProvider);

    const message: KennyMessage = {
      id: 'test-msg-5',
      type: 'user',
      content: 'This should fail',
      timestamp: new Date(),
      context
    };

    await expect(engine.processMessage(message, context)).rejects.toThrow('Provider error');
  });

  it('should clean up expired memories', async () => {
    // Add a memory that expires immediately
    const expiredMemoryId = await engine.addMemory({
      type: 'interaction',
      content: { test: 'expired' },
      importance: 50,
      lastAccessed: new Date(),
      expiresAt: new Date(Date.now() - 1000), // 1 second ago
      associatedContext: context.id
    });

    // Add a fresh memory
    await engine.addMemory({
      type: 'interaction',
      content: { test: 'fresh' },
      importance: 60,
      lastAccessed: new Date(),
      associatedContext: context.id
    });

    // Retrieve memories - should only get the fresh one
    const memories = await engine.retrieveMemories(context.id);
    expect(memories).toHaveLength(1);
    expect(memories[0].content.test).toBe('fresh');
  });

  it('should calculate complexity correctly', async () => {
    const simpleMessage: KennyMessage = {
      id: 'simple',
      type: 'user',
      content: 'Hi',
      timestamp: new Date(),
      context
    };

    const complexMessage: KennyMessage = {
      id: 'complex',
      type: 'user',
      content: 'This is a very complex message with multiple sentences. It contains technical terms, questions, and requires deep analysis. How would you handle advanced architectural patterns in distributed systems?',
      timestamp: new Date(),
      context
    };

    await engine.initialize(mockProvider);

    // Process both messages and check state changes
    await engine.processMessage(simpleMessage, context);
    const simpleState = await engine.getState(context.id);

    // Reset context for fair comparison
    context.id = 'test-context-2';
    await engine.processMessage(complexMessage, context);
    const complexState = await engine.getState(context.id);

    // Complex message should result in higher awareness
    expect(complexState!.awareness).toBeGreaterThanOrEqual(simpleState!.awareness);
  });
});