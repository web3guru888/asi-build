/**
 * Test Utilities - Helper functions and mocks for testing
 */

import { mock } from 'bun:test';
import type { Provider, ProviderConfig, ProviderMessage, ProviderResponse } from '../src/provider/index.js';
import type { KennyContext, KennyMessage } from '../src/kenny/index.js';
import type { Tool, ToolDefinition, ToolExecutionContext, ToolResult } from '../src/tool/index.js';

/**
 * Create a mock provider for testing
 */
export function createMockProvider(config?: Partial<ProviderConfig>): Provider {
  const defaultConfig: ProviderConfig = {
    name: 'mock-provider',
    type: 'anthropic',
    apiKey: 'mock-api-key',
    model: 'mock-model',
    ...config
  };

  return {
    name: defaultConfig.name,
    config: defaultConfig,
    initialize: mock(async () => {}),
    generate: mock(async (messages: ProviderMessage[]): Promise<ProviderResponse> => {
      const lastMessage = messages[messages.length - 1];
      return {
        content: `Mock response to: ${lastMessage.content}`,
        model: defaultConfig.model,
        usage: {
          inputTokens: Math.floor(lastMessage.content.length / 4),
          outputTokens: 20,
          totalTokens: Math.floor(lastMessage.content.length / 4) + 20
        },
        metadata: { mock: true }
      };
    }),
    streamGenerate: mock(async function* (messages: ProviderMessage[]) {
      const lastMessage = messages[messages.length - 1];
      const response = `Mock response to: ${lastMessage.content}`;
      
      // Simulate streaming by yielding chunks
      const words = response.split(' ');
      for (const word of words) {
        yield word + ' ';
      }
      
      return {
        content: response,
        model: defaultConfig.model,
        usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        metadata: { mock: true, streamed: true }
      };
    }),
    isAvailable: mock(async () => true),
    cleanup: mock(async () => {}),
    on: mock(() => ({} as any)),
    off: mock(() => ({} as any)),
    emit: mock(() => false),
    removeAllListeners: mock(() => ({} as any))
  } as Provider;
}

/**
 * Create a mock Kenny context for testing
 */
export function createMockKennyContext(overrides?: Partial<KennyContext>): KennyContext {
  return {
    id: `mock-ctx-${Date.now()}`,
    sessionId: 'mock-session',
    userId: 'mock-user',
    consciousness: {
      level: 50,
      state: 'active',
      awarenessLevel: 60,
      adaptationRate: 0.1
    },
    permissions: {
      tools: ['read', 'write', 'bash'],
      resources: ['file-system', 'network'],
      restrictions: []
    },
    metadata: {
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
      mock: true
    },
    ...overrides
  };
}

/**
 * Create a mock Kenny message for testing
 */
export function createMockKennyMessage(
  content: string,
  type: 'user' | 'assistant' = 'user',
  context?: KennyContext
): KennyMessage {
  return {
    id: `mock-msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type,
    content,
    timestamp: new Date(),
    context: context || createMockKennyContext(),
    metadata: { mock: true }
  };
}

/**
 * Create a mock tool for testing
 */
export function createMockTool(definition?: Partial<ToolDefinition>): Tool {
  const defaultDefinition: ToolDefinition = {
    name: 'mock-tool',
    description: 'A mock tool for testing',
    parameters: [
      {
        name: 'input',
        type: 'string',
        description: 'Input parameter',
        required: true
      }
    ],
    category: 'custom',
    version: '1.0.0',
    author: 'test',
    ...definition
  };

  return {
    definition: defaultDefinition,
    execute: mock(async (parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> => {
      return {
        success: true,
        data: {
          input: parameters.input,
          output: `Mock tool processed: ${parameters.input}`,
          context: context.sessionId
        },
        metadata: { mock: true, executedAt: new Date().toISOString() }
      };
    }),
    validate: mock((parameters: Record<string, any>): boolean => {
      // Simple validation - check required parameters
      return defaultDefinition.parameters
        .filter(p => p.required)
        .every(p => p.name in parameters);
    }),
    cleanup: mock(async () => {}),
    on: mock(() => ({} as any)),
    off: mock(() => ({} as any)),
    emit: mock(() => false),
    removeAllListeners: mock(() => ({} as any))
  } as Tool;
}

/**
 * Create a failing mock tool for error testing
 */
export function createFailingMockTool(errorMessage: string = 'Mock tool error'): Tool {
  const tool = createMockTool({
    name: 'failing-mock-tool',
    description: 'A mock tool that always fails'
  });

  tool.execute = mock(async (): Promise<ToolResult> => {
    throw new Error(errorMessage);
  });

  return tool;
}

/**
 * Create mock tool execution context
 */
export function createMockToolExecutionContext(overrides?: Partial<ToolExecutionContext>): ToolExecutionContext {
  return {
    sessionId: 'mock-session',
    userId: 'mock-user',
    permissions: ['read', 'write', 'execute'],
    workingDirectory: process.cwd(),
    environment: {
      NODE_ENV: 'test',
      MOCK: 'true'
    },
    ...overrides
  };
}

/**
 * Wait for a specified amount of time (useful for async tests)
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create a temporary directory for tests
 */
export function createTempDir(): string {
  const tmpDir = `/tmp/asi-code-test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  return tmpDir;
}

/**
 * Mock event emitter for testing
 */
export function createMockEventEmitter() {
  const listeners = new Map<string, Function[]>();
  
  return {
    on: mock((event: string, listener: Function) => {
      if (!listeners.has(event)) {
        listeners.set(event, []);
      }
      listeners.get(event)!.push(listener);
    }),
    off: mock((event: string, listener: Function) => {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        const index = eventListeners.indexOf(listener);
        if (index > -1) {
          eventListeners.splice(index, 1);
        }
      }
    }),
    emit: mock((event: string, ...args: any[]) => {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        eventListeners.forEach(listener => listener(...args));
        return eventListeners.length > 0;
      }
      return false;
    }),
    removeAllListeners: mock((event?: string) => {
      if (event) {
        listeners.delete(event);
      } else {
        listeners.clear();
      }
    }),
    listenerCount: (event: string) => listeners.get(event)?.length || 0,
    listeners,
    // Add methods to help with testing
    getListeners: (event: string) => listeners.get(event) || [],
    clearListeners: () => listeners.clear()
  };
}

/**
 * Assert that an event was emitted with specific data
 */
export function assertEventEmitted(
  emitter: any,
  eventName: string,
  expectedData?: any,
  timeout = 1000
): Promise<void> {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Event '${eventName}' was not emitted within ${timeout}ms`));
    }, timeout);

    emitter.once(eventName, (data: any) => {
      clearTimeout(timeoutId);
      
      if (expectedData !== undefined) {
        try {
          expect(data).toEqual(expectedData);
        } catch (error) {
          reject(error);
          return;
        }
      }
      
      resolve();
    });
  });
}

/**
 * Create a mock configuration for testing
 */
export function createMockConfig(overrides?: any) {
  return {
    providers: {
      mock: {
        name: 'mock',
        type: 'anthropic',
        apiKey: 'mock-key',
        model: 'mock-model'
      }
    },
    tools: {
      enableBuiltIn: true,
      customTools: [],
      registry: {}
    },
    permissions: {
      enableSafetyProtocols: false,
      enableCaching: false,
      enableAuditing: false,
      storage: { type: 'memory' }
    },
    storage: {
      type: 'memory',
      config: {}
    },
    server: {
      port: 3001,
      host: 'localhost'
    },
    consciousness: {
      enabled: false,
      model: 'mock-model'
    },
    kenny: {
      enabled: true,
      logging: {
        level: 'error',
        enabled: false
      },
      health: {
        checkInterval: 60000,
        enabled: false
      }
    },
    ...overrides
  };
}

/**
 * Capture console output for testing
 */
export function captureConsole() {
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;
  
  const logs: string[] = [];
  const errors: string[] = [];
  const warnings: string[] = [];
  
  console.log = (...args: any[]) => {
    logs.push(args.map(arg => String(arg)).join(' '));
  };
  
  console.error = (...args: any[]) => {
    errors.push(args.map(arg => String(arg)).join(' '));
  };
  
  console.warn = (...args: any[]) => {
    warnings.push(args.map(arg => String(arg)).join(' '));
  };
  
  return {
    logs,
    errors,
    warnings,
    restore: () => {
      console.log = originalLog;
      console.error = originalError;
      console.warn = originalWarn;
    }
  };
}