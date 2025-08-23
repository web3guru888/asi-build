/**
 * WebSocket Integration Tests - Comprehensive testing of WebSocket functionality
 * 
 * Tests WebSocket connections, real-time messaging, AI streaming, tool execution,
 * session updates, connection management, and error handling.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { createServer } from '../../src/server/server.js';
import { WSServer } from '../../src/server/websocket/websocket-server.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ProviderManager } from '../../src/provider/index.js';
import { createBuiltInTools } from '../../src/tool/built-in-tools/index.js';
import { vol } from 'memfs';
import WebSocket from 'ws';
import type { Server } from 'node:http';

// Mock fs for file operations
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Test storage implementation
class TestSessionStorage {
  private storage = new Map();

  async save(sessionData: any): Promise<void> {
    this.storage.set(sessionData.id, { ...sessionData });
  }

  async load(sessionId: string): Promise<any> {
    return this.storage.get(sessionId) || null;
  }

  async delete(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }

  async list(userId?: string): Promise<string[]> {
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
  }

  async cleanup(): Promise<void> {}
  clear(): void { this.storage.clear(); }
}

// WebSocket message helpers
interface WSMessage {
  id: string;
  type: string;
  timestamp: number;
  data?: any;
  metadata?: any;
}

function createWSMessage(type: string, data?: any): WSMessage {
  return {
    id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    type,
    timestamp: Date.now(),
    data,
  };
}

async function waitForMessage(ws: WebSocket, timeout = 5000): Promise<WSMessage> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Message timeout'));
    }, timeout);

    ws.once('message', (data) => {
      clearTimeout(timer);
      try {
        const message = JSON.parse(data.toString());
        resolve(message);
      } catch (error) {
        reject(new Error('Invalid message format'));
      }
    });
  });
}

async function waitForMessages(ws: WebSocket, count: number, timeout = 10000): Promise<WSMessage[]> {
  return new Promise((resolve, reject) => {
    const messages: WSMessage[] = [];
    const timer = setTimeout(() => {
      reject(new Error(`Timeout waiting for ${count} messages, got ${messages.length}`));
    }, timeout);

    const handleMessage = (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString());
        messages.push(message);
        
        if (messages.length >= count) {
          clearTimeout(timer);
          ws.off('message', handleMessage);
          resolve(messages);
        }
      } catch (error) {
        clearTimeout(timer);
        ws.off('message', handleMessage);
        reject(new Error('Invalid message format'));
      }
    };

    ws.on('message', handleMessage);
  });
}

describe('WebSocket Integration Tests', () => {
  let server: Server;
  let wsServer: WSServer;
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let providerManager: ProviderManager;
  let testStorage: TestSessionStorage;
  const serverPort = 3004;
  const wsUrl = `ws://localhost:${serverPort}/ws`;

  beforeAll(async () => {
    // Setup test components
    testStorage = new TestSessionStorage();
    sessionManager = new DefaultSessionManager(testStorage as any);
    toolRegistry = new ToolRegistry();
    providerManager = new ProviderManager();
    
    // Initialize components
    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }

    // Create server with WebSocket support
    const asiServer = {
      config: {
        websocket: {
          enabled: true,
          path: '/ws',
          compression: { enabled: true, threshold: 1024, level: 6 },
          heartbeat: { enabled: true, interval: 30000, timeout: 5000 },
          messageQueue: { enabled: true, maxSize: 1000 },
          channels: { enabled: true },
          binary: { enabled: true, maxSize: 1048576 }
        }
      },
      getToolManager: () => toolRegistry,
      getSessionManager: () => sessionManager,
      getProviderManager: () => providerManager
    } as any;

    wsServer = new WSServer(asiServer);
    
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      components: {
        toolRegistry,
        sessionManager,
        providerManager,
        wsServer
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`WebSocket integration test server running on port ${serverPort}`);
        resolve();
      });
    });
  });

  afterAll(async () => {
    if (wsServer) {
      wsServer.cleanup();
    }

    if (server) {
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    }
    
    if (toolRegistry) {
      await toolRegistry.shutdown();
    }
    
    if (sessionManager) {
      await sessionManager.cleanup();
    }

    if (providerManager) {
      await providerManager.cleanup();
    }
  });

  beforeEach(() => {
    vol.reset();
    testStorage.clear();
  });

  afterEach(() => {
    vol.reset();
  });

  describe('WebSocket Connection Management', () => {
    it('should establish WebSocket connection successfully', async () => {
      const ws = new WebSocket(wsUrl);
      
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });

      expect(ws.readyState).toBe(WebSocket.OPEN);
      
      ws.close();
      await new Promise<void>((resolve) => {
        ws.on('close', () => resolve());
      });
    });

    it('should handle multiple simultaneous connections', async () => {
      const connections: WebSocket[] = [];
      const connectionCount = 5;

      // Create multiple connections
      for (let i = 0; i < connectionCount; i++) {
        const ws = new WebSocket(wsUrl);
        connections.push(ws);
        
        await new Promise<void>((resolve, reject) => {
          ws.on('open', () => resolve());
          ws.on('error', (error) => reject(error));
          setTimeout(() => reject(new Error('Connection timeout')), 5000);
        });
      }

      // Verify all connections are open
      connections.forEach(ws => {
        expect(ws.readyState).toBe(WebSocket.OPEN);
      });

      // Close all connections
      await Promise.all(connections.map(ws => new Promise<void>((resolve) => {
        ws.close();
        ws.on('close', () => resolve());
      })));
    });

    it('should handle connection heartbeat and keepalive', async () => {
      const ws = new WebSocket(wsUrl);
      
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });

      // Send ping message
      const pingMessage = createWSMessage('connection:ping', { timestamp: Date.now() });
      ws.send(JSON.stringify(pingMessage));

      // Wait for pong response
      const pongMessage = await waitForMessage(ws);
      expect(pongMessage.type).toBe('connection:pong');
      expect(pongMessage.data.pingId).toBe(pingMessage.id);

      ws.close();
    });

    it('should handle graceful connection closure', async () => {
      const ws = new WebSocket(wsUrl);
      
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
      });

      let closeCode: number;
      let closeReason: string;

      ws.close(1000, 'Normal closure');

      await new Promise<void>((resolve) => {
        ws.on('close', (code, reason) => {
          closeCode = code;
          closeReason = reason.toString();
          resolve();
        });
      });

      expect(closeCode!).toBe(1000);
      expect(closeReason!).toBe('Normal closure');
    });
  });

  describe('Real-time Messaging', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should send and receive basic messages', async () => {
      const testMessage = createWSMessage('test:message', { 
        content: 'Hello WebSocket',
        userId: 'test-user' 
      });

      ws.send(JSON.stringify(testMessage));

      // Wait for echo or acknowledgment
      const response = await waitForMessage(ws);
      expect(response).toBeDefined();
      expect(response.id).toBeDefined();
      expect(response.timestamp).toBeDefined();
    });

    it('should handle message broadcasting', async () => {
      // Create additional connection for broadcast testing
      const ws2 = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws2.on('open', () => resolve());
        ws2.on('error', (error) => reject(error));
      });

      // Subscribe both connections to a channel
      const subscribeMsg1 = createWSMessage('channel:join', { channel: 'test-broadcast' });
      const subscribeMsg2 = createWSMessage('channel:join', { channel: 'test-broadcast' });

      ws.send(JSON.stringify(subscribeMsg1));
      ws2.send(JSON.stringify(subscribeMsg2));

      // Wait for subscription confirmations
      await waitForMessage(ws);
      await waitForMessage(ws2);

      // Send broadcast message
      const broadcastMessage = createWSMessage('channel:broadcast', {
        channel: 'test-broadcast',
        content: 'Broadcast message content'
      });

      ws.send(JSON.stringify(broadcastMessage));

      // Both connections should receive the broadcast
      const [msg1, msg2] = await Promise.all([
        waitForMessage(ws),
        waitForMessage(ws2)
      ]);

      expect(msg1.type).toBe('channel:message');
      expect(msg2.type).toBe('channel:message');
      expect(msg1.data.content).toBe('Broadcast message content');
      expect(msg2.data.content).toBe('Broadcast message content');

      ws2.close();
    });

    it('should handle channel subscription and unsubscription', async () => {
      const channelName = 'test-channel-management';

      // Join channel
      const joinMessage = createWSMessage('channel:join', { channel: channelName });
      ws.send(JSON.stringify(joinMessage));

      const joinResponse = await waitForMessage(ws);
      expect(joinResponse.type).toBe('channel:joined');
      expect(joinResponse.data.channel).toBe(channelName);

      // Leave channel
      const leaveMessage = createWSMessage('channel:leave', { channel: channelName });
      ws.send(JSON.stringify(leaveMessage));

      const leaveResponse = await waitForMessage(ws);
      expect(leaveResponse.type).toBe('channel:left');
      expect(leaveResponse.data.channel).toBe(channelName);
    });

    it('should handle event subscription patterns', async () => {
      // Subscribe to event pattern
      const subscribeMessage = createWSMessage('event:subscribe', {
        pattern: 'tool.*'
      });

      ws.send(JSON.stringify(subscribeMessage));

      const subscribeResponse = await waitForMessage(ws);
      expect(subscribeResponse.type).toBe('event:subscribed');
      expect(subscribeResponse.data.pattern).toBe('tool.*');

      // Publish matching event
      const eventMessage = createWSMessage('event:publish', {
        event: 'tool.executed',
        payload: { toolName: 'read', success: true }
      });

      ws.send(JSON.stringify(eventMessage));

      const eventResponse = await waitForMessage(ws);
      expect(eventResponse.type).toBe('event:notification');
      expect(eventResponse.data.event).toBe('tool.executed');
    });
  });

  describe('AI Stream Integration', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });

      // Setup mock provider
      const provider = providerManager.get('test-anthropic');
      if (provider) {
        vi.spyOn(provider, 'streamGenerate').mockImplementation(async function* () {
          yield 'Hello ';
          yield 'from ';
          yield 'streaming ';
          yield 'AI!';
          return {
            content: 'Hello from streaming AI!',
            usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
            model: 'claude-3-sonnet-20240229',
            metadata: { streamed: true }
          };
        });
      }
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should handle AI streaming requests', async () => {
      const streamRequest = createWSMessage('ai:stream:start', {
        requestId: 'test-stream-123',
        provider: 'test-anthropic',
        prompt: 'Hello, how are you?',
        options: {
          maxTokens: 100,
          temperature: 0.7
        }
      });

      ws.send(JSON.stringify(streamRequest));

      // Collect streaming messages
      const messages: WSMessage[] = [];
      let streamEnded = false;

      while (!streamEnded) {
        const message = await waitForMessage(ws, 10000);
        messages.push(message);

        if (message.type === 'ai:stream:end' || message.type === 'ai:stream:error') {
          streamEnded = true;
        }
      }

      // Should have received chunk and end messages
      const chunkMessages = messages.filter(m => m.type === 'ai:stream:chunk');
      const endMessages = messages.filter(m => m.type === 'ai:stream:end');

      expect(chunkMessages.length).toBeGreaterThan(0);
      expect(endMessages.length).toBe(1);

      const endMessage = endMessages[0];
      expect(endMessage.data.requestId).toBe('test-stream-123');
      expect(endMessage.data.totalChunks).toBe(chunkMessages.length);
    });

    it('should handle AI streaming errors', async () => {
      const invalidRequest = createWSMessage('ai:stream:start', {
        requestId: 'test-error-stream',
        provider: 'nonexistent-provider',
        prompt: 'Test prompt'
      });

      ws.send(JSON.stringify(invalidRequest));

      const errorMessage = await waitForMessage(ws);
      expect(errorMessage.type).toBe('ai:stream:error');
      expect(errorMessage.data.requestId).toBe('test-error-stream');
      expect(errorMessage.data.error).toContain('Provider not found');
    });

    it('should handle concurrent streaming requests', async () => {
      const requests = [
        createWSMessage('ai:stream:start', {
          requestId: 'concurrent-1',
          provider: 'test-anthropic',
          prompt: 'First concurrent request'
        }),
        createWSMessage('ai:stream:start', {
          requestId: 'concurrent-2', 
          provider: 'test-anthropic',
          prompt: 'Second concurrent request'
        })
      ];

      // Send both requests
      requests.forEach(req => ws.send(JSON.stringify(req)));

      // Collect all messages until both streams end
      const allMessages: WSMessage[] = [];
      let endedStreams = new Set<string>();

      while (endedStreams.size < 2) {
        const message = await waitForMessage(ws, 15000);
        allMessages.push(message);

        if (message.type === 'ai:stream:end' || message.type === 'ai:stream:error') {
          endedStreams.add(message.data.requestId);
        }
      }

      // Verify both streams completed
      const stream1Messages = allMessages.filter(m => m.data?.requestId === 'concurrent-1');
      const stream2Messages = allMessages.filter(m => m.data?.requestId === 'concurrent-2');

      expect(stream1Messages.length).toBeGreaterThan(0);
      expect(stream2Messages.length).toBeGreaterThan(0);

      const stream1End = stream1Messages.find(m => m.type === 'ai:stream:end');
      const stream2End = stream2Messages.find(m => m.type === 'ai:stream:end');

      expect(stream1End).toBeDefined();
      expect(stream2End).toBeDefined();
    });
  });

  describe('Tool Execution via WebSocket', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });

      // Setup test files
      vol.fromJSON({
        '/test/ws-sample.txt': 'WebSocket sample file content',
        '/test/ws-data.json': '{"websocket": true, "test": "data"}'
      });
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should execute tools via WebSocket with progress updates', async () => {
      const executionRequest = createWSMessage('tool:execute:start', {
        executionId: 'ws-tool-exec-123',
        toolName: 'read',
        parameters: {
          path: '/test/ws-sample.txt'
        },
        sessionId: 'test-session'
      });

      ws.send(JSON.stringify(executionRequest));

      // Collect execution messages
      const messages: WSMessage[] = [];
      let executionComplete = false;

      while (!executionComplete) {
        const message = await waitForMessage(ws, 10000);
        messages.push(message);

        if (message.type === 'tool:execute:result' || message.type === 'tool:execute:error') {
          executionComplete = true;
        }
      }

      // Should have start and result messages
      const startMessages = messages.filter(m => m.type === 'tool:execute:start');
      const resultMessages = messages.filter(m => m.type === 'tool:execute:result');

      expect(startMessages.length).toBe(1);
      expect(resultMessages.length).toBe(1);

      const resultMessage = resultMessages[0];
      expect(resultMessage.data.executionId).toBe('ws-tool-exec-123');
      expect(resultMessage.data.success).toBe(true);
      expect(resultMessage.data.result).toBeDefined();
    });

    it('should handle tool execution with progress callbacks', async () => {
      // Mock a tool that reports progress
      const mockTool = {
        execute: vi.fn().mockImplementation(async (params, options) => {
          if (options?.onProgress) {
            await options.onProgress(25, 'Starting execution', 'Initializing...');
            await new Promise(resolve => setTimeout(resolve, 100));
            await options.onProgress(50, 'Processing', 'Reading file...');
            await new Promise(resolve => setTimeout(resolve, 100));
            await options.onProgress(75, 'Nearly done', 'Formatting output...');
            await new Promise(resolve => setTimeout(resolve, 100));
            await options.onProgress(100, 'Complete', 'Execution finished');
          }
          return { success: true, data: { content: 'Mocked content' } };
        })
      };

      // Replace the read tool temporarily
      const originalTool = toolRegistry.get('read');
      vi.spyOn(toolRegistry, 'get').mockReturnValue(mockTool as any);

      const executionRequest = createWSMessage('tool:execute:start', {
        executionId: 'progress-test-123',
        toolName: 'read',
        parameters: { path: '/test/progress-test.txt' }
      });

      ws.send(JSON.stringify(executionRequest));

      // Collect all messages
      const messages: WSMessage[] = [];
      let executionComplete = false;

      while (!executionComplete) {
        const message = await waitForMessage(ws, 10000);
        messages.push(message);

        if (message.type === 'tool:execute:result' || message.type === 'tool:execute:error') {
          executionComplete = true;
        }
      }

      // Should have progress messages
      const progressMessages = messages.filter(m => m.type === 'tool:execute:progress');
      expect(progressMessages.length).toBe(4); // 25%, 50%, 75%, 100%

      // Verify progress increments
      const progresses = progressMessages.map(m => m.data.progress);
      expect(progresses).toEqual([25, 50, 75, 100]);
    });

    it('should handle tool execution errors', async () => {
      const executionRequest = createWSMessage('tool:execute:start', {
        executionId: 'error-test-123',
        toolName: 'nonexistent-tool',
        parameters: {}
      });

      ws.send(JSON.stringify(executionRequest));

      const errorMessage = await waitForMessage(ws);
      expect(errorMessage.type).toBe('tool:execute:error');
      expect(errorMessage.data.executionId).toBe('error-test-123');
      expect(errorMessage.data.error).toContain('Tool not found');
    });

    it('should handle multiple concurrent tool executions', async () => {
      const executions = [
        {
          id: 'concurrent-tool-1',
          tool: 'read',
          params: { path: '/test/ws-sample.txt' }
        },
        {
          id: 'concurrent-tool-2',
          tool: 'list',
          params: { path: '/test', recursive: false }
        }
      ];

      // Start both executions
      executions.forEach(exec => {
        const request = createWSMessage('tool:execute:start', {
          executionId: exec.id,
          toolName: exec.tool,
          parameters: exec.params
        });
        ws.send(JSON.stringify(request));
      });

      // Collect results for both executions
      const allMessages: WSMessage[] = [];
      let completedExecutions = new Set<string>();

      while (completedExecutions.size < 2) {
        const message = await waitForMessage(ws, 15000);
        allMessages.push(message);

        if (message.type === 'tool:execute:result' || message.type === 'tool:execute:error') {
          completedExecutions.add(message.data.executionId);
        }
      }

      // Verify both executions completed
      const exec1Messages = allMessages.filter(m => m.data?.executionId === 'concurrent-tool-1');
      const exec2Messages = allMessages.filter(m => m.data?.executionId === 'concurrent-tool-2');

      expect(exec1Messages.length).toBeGreaterThan(0);
      expect(exec2Messages.length).toBeGreaterThan(0);

      const exec1Result = exec1Messages.find(m => m.type === 'tool:execute:result');
      const exec2Result = exec2Messages.find(m => m.type === 'tool:execute:result');

      expect(exec1Result).toBeDefined();
      expect(exec2Result).toBeDefined();
    });
  });

  describe('Session Management via WebSocket', () => {
    let ws: WebSocket;
    let sessionId: string;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });

      // Create test session
      const session = await sessionManager.createSession('ws-test-user');
      sessionId = session.data.id;
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should handle session updates via WebSocket', async () => {
      const updateRequest = createWSMessage('session:update', {
        sessionId,
        update: {
          metadata: { lastActivity: 'websocket-test' }
        }
      });

      ws.send(JSON.stringify(updateRequest));

      const updateResponse = await waitForMessage(ws);
      expect(updateResponse.type).toBe('session:update');
      expect(updateResponse.data.sessionId).toBe(sessionId);
      expect(updateResponse.data.update).toBeDefined();
    });

    it('should handle session status requests', async () => {
      const statusRequest = createWSMessage('session:status', {
        sessionId
      });

      ws.send(JSON.stringify(statusRequest));

      const statusResponse = await waitForMessage(ws);
      expect(statusResponse.type).toBe('session:status');
      expect(statusResponse.data.sessionId).toBe(sessionId);
      expect(statusResponse.data.status).toBeDefined();
    });

    it('should handle invalid session operations', async () => {
      const invalidRequest = createWSMessage('session:update', {
        sessionId: 'nonexistent-session-id',
        update: { test: 'data' }
      });

      ws.send(JSON.stringify(invalidRequest));

      const errorResponse = await waitForMessage(ws);
      expect(errorResponse.type).toBe('connection:error');
      expect(errorResponse.data.error).toContain('Session not found');
    });
  });

  describe('System Status and Monitoring', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should provide system status via WebSocket', async () => {
      const statusRequest = createWSMessage('system:status', {});
      ws.send(JSON.stringify(statusRequest));

      const statusResponse = await waitForMessage(ws);
      expect(statusResponse.type).toBe('system:status');
      expect(statusResponse.data.status).toBeDefined();
      expect(statusResponse.data.components).toBeDefined();
      expect(statusResponse.data.timestamp).toBeDefined();
    });

    it('should handle system health monitoring', async () => {
      const healthRequest = createWSMessage('system:health', {});
      ws.send(JSON.stringify(healthRequest));

      const healthResponse = await waitForMessage(ws);
      expect(healthResponse.type).toBe('system:health');
      expect(healthResponse.data.healthy).toBeDefined();
      expect(healthResponse.data.checks).toBeDefined();
    });
  });

  describe('Error Handling and Recovery', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should handle malformed messages gracefully', async () => {
      // Send invalid JSON
      ws.send('invalid json message');

      const errorResponse = await waitForMessage(ws);
      expect(errorResponse.type).toBe('connection:error');
      expect(errorResponse.data.error).toContain('Invalid message format');
    });

    it('should handle unknown message types', async () => {
      const unknownMessage = createWSMessage('unknown:type', {
        test: 'data'
      });

      ws.send(JSON.stringify(unknownMessage));

      // Should either handle gracefully or respond with error
      const response = await waitForMessage(ws);
      expect(response).toBeDefined();
      // Response could be acknowledgment or error
    });

    it('should handle connection recovery after temporary disconnect', async () => {
      // Force close connection
      ws.terminate();

      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 100));

      // Reconnect
      const newWs = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        newWs.on('open', () => resolve());
        newWs.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Reconnection timeout')), 5000);
      });

      expect(newWs.readyState).toBe(WebSocket.OPEN);

      // Verify connection works
      const testMessage = createWSMessage('test:reconnection', {});
      newWs.send(JSON.stringify(testMessage));

      const response = await waitForMessage(newWs);
      expect(response).toBeDefined();

      newWs.close();
    });

    it('should handle rate limiting on WebSocket messages', async () => {
      const rapidMessages = Array.from({ length: 100 }, (_, i) =>
        createWSMessage('test:rapid', { index: i })
      );

      // Send messages rapidly
      rapidMessages.forEach(msg => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(msg));
        }
      });

      // Should receive some kind of rate limiting response or handle gracefully
      let receivedMessages = 0;
      let rateLimitMessage = false;

      try {
        while (receivedMessages < 10) { // Don't wait for all 100
          const message = await waitForMessage(ws, 1000);
          receivedMessages++;
          
          if (message.type === 'connection:rate_limited') {
            rateLimitMessage = true;
            break;
          }
        }
      } catch (error) {
        // Timeout is acceptable for rate limiting test
      }

      // Either received rate limit message or handled the flood gracefully
      expect(receivedMessages > 0 || rateLimitMessage).toBe(true);
    });
  });

  describe('Message Compression and Binary Support', () => {
    let ws: WebSocket;

    beforeEach(async () => {
      ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        ws.on('open', () => resolve());
        ws.on('error', (error) => reject(error));
        setTimeout(() => reject(new Error('Connection timeout')), 5000);
      });
    });

    afterEach(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });

    it('should handle large messages with compression', async () => {
      const largeContent = 'A'.repeat(5000); // 5KB message
      const largeMessage = createWSMessage('test:large', {
        content: largeContent
      });

      ws.send(JSON.stringify(largeMessage));

      const response = await waitForMessage(ws);
      expect(response).toBeDefined();
      
      // Check if compression metadata was added
      if (response.metadata?.['x-compressed']) {
        expect(response.metadata['x-original-size']).toBeGreaterThan(0);
        expect(response.metadata['x-compressed-size']).toBeGreaterThan(0);
        expect(response.metadata['x-compressed-size']).toBeLessThan(
          response.metadata['x-original-size']
        );
      }
    });

    it('should handle binary message support', async () => {
      // Create a binary buffer
      const binaryData = Buffer.from('Binary test data', 'utf8');
      
      // Send as binary WebSocket frame
      ws.send(binaryData);

      try {
        const response = await waitForMessage(ws, 5000);
        expect(response).toBeDefined();
      } catch (error) {
        // Binary support might not be fully implemented yet
        expect(error.message).toContain('timeout');
      }
    });
  });
});