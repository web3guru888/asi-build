/**
 * WebSocket Module Exports
 * 
 * Main entry point for WebSocket functionality in ASI-Code.
 * Exports all WebSocket classes, types, and utilities.
 */

// Core WebSocket server
export { WSServer } from './websocket-server.js';

// Connection and message management
export { WSConnectionManager } from './connection-manager.js';
export { WSMessageQueue } from './message-queue.js';

// Compression and binary support
export { WSCompressionManager, WSBinaryManager, WSMessageUtils } from './compression.js';

// Client reconnection
export { 
  WSClientReconnection,
  createReconnectingWebSocket,
  waitForConnection 
} from './client-reconnection.js';

// Middleware
export {
  createAuthMiddleware,
  createAuthHandler,
  createRateLimitMiddleware,
  createValidationMiddleware,
  createLoggingMiddleware,
  createMessageSizeLimitMiddleware,
  createMetadataMiddleware,
  createErrorHandlingMiddleware,
  createBinaryMessageMiddleware,
  createDefaultMiddlewareStack
} from './middleware.js';

// Types
export type {
  // Base message types
  WSMessage,
  WSMessageType,
  WSBaseMessage,
  
  // Connection types
  WSConnectionState,
  WSChannelState,
  WSSubscriptionState,
  WSQueuedMessage,
  WSRateLimitState,
  WSBinaryMessage,
  WSCompressionOptions,
  
  // Specific message types
  WSAuthMessage,
  WSPingMessage,
  WSPongMessage,
  WSReadyMessage,
  WSChannelJoinMessage,
  WSChannelLeaveMessage,
  WSChannelMessage,
  WSChannelBroadcastMessage,
  WSSubscribeMessage,
  WSUnsubscribeMessage,
  WSSubscriptionEventMessage,
  WSAIStreamStartMessage,
  WSAIStreamChunkMessage,
  WSAIStreamEndMessage,
  WSAIStreamErrorMessage,
  WSToolExecuteStartMessage,
  WSToolExecuteProgressMessage,
  WSToolExecuteResultMessage,
  WSToolExecuteErrorMessage,
  WSSessionUpdateMessage,
  WSSystemStatusMessage,
  WSSystemNotificationMessage,
  WSErrorMessage,
  
  // Event and middleware types
  WSEventHandler,
  WSEventHandlers,
  WSMiddleware,
  WSMiddlewareContext,
  WSServerEvents
} from './types.js';

// Re-export client reconnection types
export type {
  ReconnectionConfig,
  ConnectionState,
  ReconnectionEvents
} from './client-reconnection.js';

// Default configurations
export const defaultWebSocketConfig = {
  enabled: true,
  path: '/ws',
  maxConnections: 1000,
  heartbeat: {
    enabled: true,
    interval: 30000, // 30 seconds
    timeout: 60000,  // 60 seconds
  },
  compression: {
    enabled: true,
    threshold: 1024, // 1KB
    level: 6,
  },
  auth: {
    enabled: false,
    type: 'jwt' as const,
    timeout: 300, // 5 minutes
  },
  rateLimiting: {
    enabled: true,
    messagesPerSecond: 10,
    messagesPerMinute: 100,
    bytesPerSecond: 10240, // 10KB
  },
  messageQueue: {
    enabled: true,
    maxSize: 1000,
    persistence: false,
    ttl: 3600, // 1 hour
  },
  channels: {
    enabled: true,
    maxChannelsPerConnection: 50,
    channelNamePattern: '^[a-zA-Z0-9_-]{1,64}$',
  },
  binary: {
    enabled: true,
    maxSize: 10485760, // 10MB
    allowedTypes: ['application/octet-stream', 'application/json', 'text/plain'],
  },
  reconnection: {
    enabled: true,
    maxRetries: 5,
    backoffMultiplier: 1.5,
    maxBackoffTime: 30000, // 30 seconds
  },
};

// Utility functions
export const WebSocketUtils = {
  /**
   * Generate a unique message ID
   */
  generateMessageId: () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  
  /**
   * Create a basic message
   */
  createMessage: (type: string, data?: any, metadata?: Record<string, any>) => ({
    id: WebSocketUtils.generateMessageId(),
    type,
    timestamp: Date.now(),
    data,
    metadata,
  }),
  
  /**
   * Validate message format
   */
  isValidMessage: (msg: any): msg is WSMessage => {
    return msg && 
           typeof msg.id === 'string' && 
           typeof msg.type === 'string' && 
           typeof msg.timestamp === 'number';
  },
  
  /**
   * Check if message is a system message
   */
  isSystemMessage: (msg: WSMessage): boolean => {
    return msg.type.startsWith('connection:') || 
           msg.type.startsWith('system:');
  },
  
  /**
   * Check if message expects a response
   */
  expectsResponse: (msg: WSMessage): boolean => {
    const responseExpected = [
      'connection:auth',
      'channel:join',
      'subscription:subscribe',
      'ai:stream:start',
      'tool:execute:start',
    ];
    return responseExpected.includes(msg.type);
  },
  
  /**
   * Format message for logging
   */
  formatMessageForLog: (msg: WSMessage, includeData = false): string => {
    const parts = [
      `[${msg.type}]`,
      `ID: ${msg.id}`,
      `Time: ${new Date(msg.timestamp).toISOString()}`,
    ];
    
    if (includeData && msg.data) {
      const dataStr = JSON.stringify(msg.data);
      parts.push(`Data: ${dataStr.length > 100 ? dataStr.substring(0, 100) + '...' : dataStr}`);
    }
    
    return parts.join(' | ');
  },
};

// Export version info
export const VERSION = '1.0.0';
export const PROTOCOL_VERSION = '1.0';

// Export library info
export const WebSocketLibraryInfo = {
  version: VERSION,
  protocolVersion: PROTOCOL_VERSION,
  features: [
    'real-time messaging',
    'channel/room support',
    'message queuing',
    'compression',
    'binary messages',
    'authentication',
    'rate limiting',
    'heartbeat/ping-pong',
    'auto-reconnection',
    'AI streaming',
    'tool execution',
    'subscription management',
  ],
  supportedMessageTypes: [
    'connection:*',
    'channel:*',
    'subscription:*',
    'ai:stream:*',
    'tool:execute:*',
    'session:*',
    'system:*',
    'custom:*',
  ],
};