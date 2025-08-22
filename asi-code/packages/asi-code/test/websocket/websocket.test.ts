/**
 * WebSocket Tests
 * 
 * Comprehensive tests for WebSocket functionality including
 * connection management, messaging, and real-time features.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import WebSocket from 'ws';
import { WSConnectionManager } from '../../src/server/websocket/connection-manager.js';
import { WSMessageQueue } from '../../src/server/websocket/message-queue.js';
import { WSCompressionManager, WSBinaryManager } from '../../src/server/websocket/compression.js';
import { WSClientReconnection } from '../../src/server/websocket/client-reconnection.js';
import { createDefaultMiddlewareStack } from '../../src/server/websocket/middleware.js';
import type { WSMessage, WSConnectionState } from '../../src/server/websocket/types.js';

describe('WSConnectionManager', () => {
  let connectionManager: WSConnectionManager;
  let mockWebSocket: any;

  beforeEach(() => {
    const config = {
      enabled: true,
      maxConnections: 100,
      heartbeat: { enabled: true, interval: 1000, timeout: 2000 },
      compression: { enabled: false, threshold: 1024, level: 6 },
      auth: { enabled: false, type: 'jwt' as const, timeout: 300 },
      rateLimiting: { enabled: false, messagesPerSecond: 10, messagesPerMinute: 100, bytesPerSecond: 10240 },
      messageQueue: { enabled: true, maxSize: 1000, persistence: false, ttl: 3600 },
      channels: { enabled: true, maxChannelsPerConnection: 50, channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$' },
      binary: { enabled: true, maxSize: 10485760, allowedTypes: ['application/octet-stream'] },
      reconnection: { enabled: true, maxRetries: 5, backoffMultiplier: 1.5, maxBackoffTime: 30000 },
    };

    connectionManager = new WSConnectionManager(config);

    mockWebSocket = {
      readyState: WebSocket.OPEN,
      send: vi.fn(),
      close: vi.fn(),
      on: vi.fn(),
      ping: vi.fn(),
    };
  });

  afterEach(() => {
    connectionManager.cleanup();
  });

  describe('Connection Management', () => {
    it('should add a new connection', () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      
      expect(connectionId).toBeDefined();
      expect(typeof connectionId).toBe('string');
      
      const stats = connectionManager.getStats();
      expect(stats.connections).toBe(1);
    });

    it('should remove a connection', () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      connectionManager.removeConnection(connectionId);
      
      const stats = connectionManager.getStats();
      expect(stats.connections).toBe(0);
    });

    it('should enforce connection limit', () => {
      // Set a low limit for testing
      const limitedConfig = {
        enabled: true,
        maxConnections: 1,
        heartbeat: { enabled: false, interval: 1000, timeout: 2000 },
        compression: { enabled: false, threshold: 1024, level: 6 },
        auth: { enabled: false, type: 'jwt' as const, timeout: 300 },
        rateLimiting: { enabled: false, messagesPerSecond: 10, messagesPerMinute: 100, bytesPerSecond: 10240 },
        messageQueue: { enabled: true, maxSize: 1000, persistence: false, ttl: 3600 },
        channels: { enabled: true, maxChannelsPerConnection: 50, channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$' },
        binary: { enabled: true, maxSize: 10485760, allowedTypes: ['application/octet-stream'] },
        reconnection: { enabled: true, maxRetries: 5, backoffMultiplier: 1.5, maxBackoffTime: 30000 },
      };

      const limitedManager = new WSConnectionManager(limitedConfig);
      
      const firstConnection = limitedManager.addConnection(mockWebSocket as any);
      expect(firstConnection).toBeDefined();

      const secondMockWs = { ...mockWebSocket };
      expect(() => {
        limitedManager.addConnection(secondMockWs as any);
      }).toThrow('Maximum connections exceeded');

      limitedManager.cleanup();
    });
  });

  describe('Channel Management', () => {
    it('should allow joining channels', () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      const joined = connectionManager.joinChannel(connectionId, 'test-channel');
      
      expect(joined).toBe(true);
      
      const stats = connectionManager.getStats();
      expect(stats.channels).toBe(1);
    });

    it('should allow leaving channels', () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      connectionManager.joinChannel(connectionId, 'test-channel');
      
      const left = connectionManager.leaveChannel(connectionId, 'test-channel');
      expect(left).toBe(true);
      
      const stats = connectionManager.getStats();
      expect(stats.channels).toBe(0);
    });

    it('should broadcast to channel members', async () => {
      const connectionId1 = connectionManager.addConnection(mockWebSocket as any);
      const connectionId2 = connectionManager.addConnection({ ...mockWebSocket } as any);
      
      connectionManager.joinChannel(connectionId1, 'test-channel');
      connectionManager.joinChannel(connectionId2, 'test-channel');
      
      const message: WSMessage = {
        id: 'test-message',
        type: 'channel:message',
        timestamp: Date.now(),
        data: { text: 'Hello channel!' },
      };
      
      await connectionManager.broadcastToChannel('test-channel', message);
      
      // Should send to both connections
      expect(mockWebSocket.send).toHaveBeenCalledTimes(4); // 2 ready messages + 2 channel messages
    });
  });

  describe('Subscription Management', () => {
    it('should allow subscribing to events', () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      const subscribed = connectionManager.subscribe(connectionId, 'test-event');
      
      expect(subscribed).toBe(true);
      
      const stats = connectionManager.getStats();
      expect(stats.subscriptions).toBe(1);
    });

    it('should publish events to subscribers', async () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      connectionManager.subscribe(connectionId, 'test-event');
      
      await connectionManager.publishEvent('test-event', { message: 'Hello world!' });
      
      expect(mockWebSocket.send).toHaveBeenCalledTimes(2); // Ready message + event message
    });
  });

  describe('Message Handling', () => {
    it('should handle ping messages', async () => {
      const connectionId = connectionManager.addConnection(mockWebSocket as any);
      
      const pingMessage: WSMessage = {
        id: 'ping-test',
        type: 'connection:ping',
        timestamp: Date.now(),
        data: { timestamp: Date.now() },
      };
      
      // Simulate message handling
      await connectionManager['handleMessage'](connectionId, JSON.stringify(pingMessage));
      
      // Should respond with pong
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"connection:pong"')
      );
    });
  });
});

describe('WSMessageQueue', () => {
  let messageQueue: WSMessageQueue;

  beforeEach(() => {
    const config = {
      enabled: true,
      maxSize: 100,
      persistence: false,
      ttl: 3600,
    };

    messageQueue = new WSMessageQueue(config);
  });

  afterEach(() => {
    messageQueue.cleanup();
  });

  it('should queue messages', async () => {
    const message: WSMessage = {
      id: 'test-message',
      type: 'test:message',
      timestamp: Date.now(),
      data: { text: 'Test message' },
    };

    await messageQueue.queueMessage('connection-1', message);
    
    expect(messageQueue.getQueueSize('connection-1')).toBe(1);
    expect(messageQueue.getTotalQueueSize()).toBe(1);
  });

  it('should process connection queue', async () => {
    const message: WSMessage = {
      id: 'test-message',
      type: 'test:message',
      timestamp: Date.now(),
      data: { text: 'Test message' },
    };

    await messageQueue.queueMessage('connection-1', message);
    
    let processedMessage: WSMessage | null = null;
    const sendFunction = vi.fn(async (msg: WSMessage) => {
      processedMessage = msg;
      return true;
    });
    
    const processed = await messageQueue.processConnectionQueue('connection-1', sendFunction);
    
    expect(processed).toBe(1);
    expect(sendFunction).toHaveBeenCalledWith(message);
    expect(processedMessage).toEqual(message);
    expect(messageQueue.getQueueSize('connection-1')).toBe(0);
  });

  it('should handle failed message delivery', async () => {
    const message: WSMessage = {
      id: 'test-message',
      type: 'test:message',
      timestamp: Date.now(),
      data: { text: 'Test message' },
    };

    await messageQueue.queueMessage('connection-1', message, { maxAttempts: 2 });
    
    const failedSendFunction = vi.fn(async () => false);
    
    // First attempt should fail, message should remain in queue
    await messageQueue.processConnectionQueue('connection-1', failedSendFunction);
    expect(messageQueue.getQueueSize('connection-1')).toBe(1);
    
    // Second attempt should fail and remove message
    await messageQueue.processConnectionQueue('connection-1', failedSendFunction);
    expect(messageQueue.getQueueSize('connection-1')).toBe(0);
    
    expect(failedSendFunction).toHaveBeenCalledTimes(2);
  });
});

describe('WSCompressionManager', () => {
  let compressionManager: WSCompressionManager;

  beforeEach(() => {
    compressionManager = new WSCompressionManager({
      enabled: true,
      threshold: 100,
      level: 6,
    });
  });

  it('should compress large messages', async () => {
    const largeMessage = 'x'.repeat(200); // Larger than threshold
    
    const result = await compressionManager.compressMessage(largeMessage);
    
    expect(result.compressed).toBe(true);
    expect(result.compressedSize).toBeLessThan(result.originalSize);
  });

  it('should not compress small messages', async () => {
    const smallMessage = 'small';
    
    const result = await compressionManager.compressMessage(smallMessage);
    
    expect(result.compressed).toBe(false);
    expect(result.compressedSize).toBe(result.originalSize);
  });

  it('should decompress messages', async () => {
    const originalMessage = 'This is a test message that should be compressed and then decompressed.';
    
    const compressed = await compressionManager.compressMessage(originalMessage);
    expect(compressed.compressed).toBe(true);
    
    const decompressed = await compressionManager.decompressMessage(
      compressed.data, 
      compressed.compressed
    );
    
    expect(decompressed.data.toString()).toBe(originalMessage);
  });
});

describe('WSBinaryManager', () => {
  let binaryManager: WSBinaryManager;

  beforeEach(() => {
    binaryManager = new WSBinaryManager({
      maxSize: 1024 * 1024, // 1MB
      allowedTypes: ['application/octet-stream'],
    });
  });

  it('should create binary messages', () => {
    const data = Buffer.from('Hello World', 'utf8');
    
    const binaryMessage = binaryManager.createBinaryMessage(
      'application/octet-stream',
      data,
      { description: 'Test binary data' }
    );
    
    expect(binaryMessage.type).toBe('application/octet-stream');
    expect(binaryMessage.size).toBe(data.length);
    expect(binaryMessage.format).toBe('buffer');
    expect(binaryMessage.metadata?.description).toBe('Test binary data');
  });

  it('should parse binary messages', () => {
    const originalData = Buffer.from('Hello World', 'utf8');
    
    const binaryMessage = binaryManager.createBinaryMessage(
      'application/octet-stream',
      originalData
    );
    
    const parsed = binaryManager.parseBinaryMessage(binaryMessage);
    
    expect(parsed.valid).toBe(true);
    expect(parsed.data.toString()).toBe('Hello World');
    expect(parsed.size).toBe(originalData.length);
  });

  it('should chunk large binary messages', () => {
    const largeData = Buffer.alloc(1000, 'x');
    const chunkSize = 300;
    
    const binaryMessage = binaryManager.createBinaryMessage(
      'application/octet-stream',
      largeData
    );
    
    const chunks = binaryManager.chunkBinaryMessage(binaryMessage, chunkSize);
    
    expect(chunks.length).toBe(Math.ceil(largeData.length / chunkSize));
    
    // Verify chunk metadata
    chunks.forEach((chunk, index) => {
      expect(chunk.metadata?.isChunk).toBe(true);
      expect(chunk.metadata?.chunkIndex).toBe(index);
      expect(chunk.metadata?.totalChunks).toBe(chunks.length);
      expect(chunk.metadata?.originalId).toBe(binaryMessage.id);
    });
  });

  it('should reassemble chunked messages', () => {
    const originalData = Buffer.from('This is a test message for chunking', 'utf8');
    const chunkSize = 10;
    
    const binaryMessage = binaryManager.createBinaryMessage(
      'application/octet-stream',
      originalData
    );
    
    const chunks = binaryManager.chunkBinaryMessage(binaryMessage, chunkSize);
    const reassembled = binaryManager.reassembleChunkedMessage(chunks);
    
    expect(reassembled).toBeDefined();
    expect(reassembled!.id).toBe(binaryMessage.id);
    
    const parsedReassembled = binaryManager.parseBinaryMessage(reassembled!);
    expect(parsedReassembled.data.toString()).toBe(originalData.toString());
  });
});

describe('WSClientReconnection', () => {
  // Mock WebSocket for client testing
  const MockWebSocket = vi.fn().mockImplementation(() => ({
    readyState: WebSocket.CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));

  beforeEach(() => {
    (global as any).WebSocket = MockWebSocket;
  });

  it('should create reconnection client', () => {
    const client = new WSClientReconnection('ws://localhost:3000/ws', {
      enabled: true,
      maxRetries: 3,
      initialDelay: 1000,
    });
    
    expect(client).toBeDefined();
    expect(client.getState().status).toBe('disconnected');
  });

  it('should queue messages when disconnected', async () => {
    const client = new WSClientReconnection('ws://localhost:3000/ws');
    
    const message: WSMessage = {
      id: 'test-msg',
      type: 'test:message',
      timestamp: Date.now(),
      data: { text: 'Hello' },
    };
    
    // Should queue message when disconnected
    await client.send(message);
    
    const stats = client.getStats();
    expect(stats.queuedMessages).toBe(1);
    
    client.cleanup();
  });
});

describe('Middleware', () => {
  it('should create default middleware stack', () => {
    const config = {
      enabled: true,
      rateLimiting: { enabled: true, messagesPerSecond: 10, messagesPerMinute: 100, bytesPerSecond: 10240 },
      auth: { enabled: false, type: 'jwt' as const, timeout: 300 },
      binary: { enabled: true, maxSize: 10485760, allowedTypes: ['application/octet-stream'] },
    };
    
    const middleware = createDefaultMiddlewareStack(config);
    
    expect(middleware).toBeDefined();
    expect(Array.isArray(middleware)).toBe(true);
    expect(middleware.length).toBeGreaterThan(0);
  });
});

describe('Integration Tests', () => {
  it('should handle end-to-end message flow', async () => {
    const connectionManager = new WSConnectionManager({
      enabled: true,
      maxConnections: 100,
      heartbeat: { enabled: false, interval: 1000, timeout: 2000 },
      compression: { enabled: false, threshold: 1024, level: 6 },
      auth: { enabled: false, type: 'jwt' as const, timeout: 300 },
      rateLimiting: { enabled: false, messagesPerSecond: 10, messagesPerMinute: 100, bytesPerSecond: 10240 },
      messageQueue: { enabled: true, maxSize: 1000, persistence: false, ttl: 3600 },
      channels: { enabled: true, maxChannelsPerConnection: 50, channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$' },
      binary: { enabled: true, maxSize: 10485760, allowedTypes: ['application/octet-stream'] },
      reconnection: { enabled: true, maxRetries: 5, backoffMultiplier: 1.5, maxBackoffTime: 30000 },
    });

    const messageQueue = new WSMessageQueue({
      enabled: true,
      maxSize: 100,
      persistence: false,
      ttl: 3600,
    });

    const mockWs = {
      readyState: WebSocket.OPEN,
      send: vi.fn(),
      close: vi.fn(),
      on: vi.fn(),
      ping: vi.fn(),
    };

    // Add connection
    const connectionId = connectionManager.addConnection(mockWs as any);
    
    // Join channel
    connectionManager.joinChannel(connectionId, 'test-channel');
    
    // Subscribe to events
    connectionManager.subscribe(connectionId, 'test-event');
    
    // Queue a message
    const message: WSMessage = {
      id: 'integration-test',
      type: 'test:message',
      timestamp: Date.now(),
      data: { text: 'Integration test message' },
    };
    
    await messageQueue.queueMessage(connectionId, message);
    
    // Process queue
    const processed = await messageQueue.processConnectionQueue(
      connectionId,
      async (msg) => {
        await connectionManager.sendMessage(connectionId, msg);
        return true;
      }
    );
    
    expect(processed).toBe(1);
    
    // Broadcast to channel
    await connectionManager.broadcastToChannel('test-channel', {
      id: 'channel-broadcast',
      type: 'channel:message',
      timestamp: Date.now(),
      data: { text: 'Channel broadcast' },
    });
    
    // Publish event
    await connectionManager.publishEvent('test-event', { message: 'Event published' });
    
    // Verify messages were sent
    expect(mockWs.send).toHaveBeenCalled();
    
    // Cleanup
    connectionManager.cleanup();
    messageQueue.cleanup();
  });
});