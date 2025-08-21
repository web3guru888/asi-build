/**
 * Kenny Integration Pattern Tests
 */

import { describe, it, expect, beforeEach, afterEach } from 'bun:test';
import { createKennyIntegration, type KennyMessage, type KennyContext } from '../src/kenny/index.js';
import { defaultConfig } from '../src/index.js';

describe('Kenny Integration Pattern', () => {
  let kenny: any;
  let context: KennyContext;

  beforeEach(async () => {
    kenny = createKennyIntegration();
    await kenny.initialize(defaultConfig);
    context = kenny.createContext('test-session', 'test-user');
  });

  afterEach(async () => {
    await kenny.cleanup();
  });

  it('should initialize successfully', async () => {
    expect(kenny).toBeDefined();
    expect(context).toBeDefined();
    expect(context.sessionId).toBe('test-session');
    expect(context.userId).toBe('test-user');
  });

  it('should create context with correct structure', () => {
    expect(context.id).toBeDefined();
    expect(context.sessionId).toBe('test-session');
    expect(context.userId).toBe('test-user');
    expect(context.consciousness).toBeDefined();
    expect(context.consciousness.level).toBe(1);
    expect(context.consciousness.state).toBe('active');
  });

  it('should process messages', async () => {
    const message: KennyMessage = {
      id: 'test-msg-1',
      type: 'user',
      content: 'Hello, ASI-Code!',
      timestamp: new Date(),
      context
    };

    const response = await kenny.process(message);
    
    expect(response).toBeDefined();
    expect(response.type).toBe('assistant');
    expect(response.content).toContain('Processed');
    expect(response.context.id).toBe(context.id);
  });

  it('should update context', async () => {
    const updates = {
      metadata: { testKey: 'testValue' }
    };

    await kenny.updateContext(context.id, updates);
    const updatedContext = await kenny.getContext(context.id);
    
    expect(updatedContext?.metadata.testKey).toBe('testValue');
  });

  it('should emit events during processing', async () => {
    let eventReceived = false;
    kenny.on('message:processed', () => {
      eventReceived = true;
    });

    const message: KennyMessage = {
      id: 'test-msg-2',
      type: 'user',
      content: 'Test event emission',
      timestamp: new Date(),
      context
    };

    await kenny.process(message);
    expect(eventReceived).toBe(true);
  });
});