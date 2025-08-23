/**
 * WebSocket Event Types and Message Schemas
 *
 * Comprehensive type definitions for WebSocket communication in ASI-Code.
 * Includes message types, event schemas, and connection management types.
 */

// Base message types
export type WSMessageType =
  // Connection management
  | 'connection:auth'
  | 'connection:ping'
  | 'connection:pong'
  | 'connection:close'
  | 'connection:error'
  | 'connection:ready'

  // Channel/Room management
  | 'channel:join'
  | 'channel:leave'
  | 'channel:message'
  | 'channel:broadcast'
  | 'channel:list'

  // Subscription management
  | 'subscription:subscribe'
  | 'subscription:unsubscribe'
  | 'subscription:event'
  | 'subscription:list'

  // AI streaming
  | 'ai:stream:start'
  | 'ai:stream:chunk'
  | 'ai:stream:end'
  | 'ai:stream:error'

  // Tool execution
  | 'tool:execute:start'
  | 'tool:execute:progress'
  | 'tool:execute:result'
  | 'tool:execute:error'
  | 'tool:execute:end'

  // Session events
  | 'session:update'
  | 'session:history'
  | 'session:clear'

  // System events
  | 'system:status'
  | 'system:notification'
  | 'system:error'

  // Custom events
  | 'custom:event';

// Base message structure
export interface WSBaseMessage {
  id: string;
  type: WSMessageType;
  timestamp: number;
  data?: any;
  metadata?: Record<string, any>;
}

// Connection messages
export interface WSAuthMessage extends WSBaseMessage {
  type: 'connection:auth';
  data: {
    token?: string;
    sessionId?: string;
    userId?: string;
    credentials?: Record<string, any>;
  };
}

export interface WSPingMessage extends WSBaseMessage {
  type: 'connection:ping';
  data?: {
    timestamp: number;
  };
}

export interface WSPongMessage extends WSBaseMessage {
  type: 'connection:pong';
  data: {
    timestamp: number;
    latency?: number;
  };
}

export interface WSReadyMessage extends WSBaseMessage {
  type: 'connection:ready';
  data: {
    connectionId: string;
    capabilities: string[];
    maxMessageSize: number;
    heartbeatInterval: number;
  };
}

// Channel/Room messages
export interface WSChannelJoinMessage extends WSBaseMessage {
  type: 'channel:join';
  data: {
    channel: string;
    password?: string;
    metadata?: Record<string, any>;
  };
}

export interface WSChannelLeaveMessage extends WSBaseMessage {
  type: 'channel:leave';
  data: {
    channel: string;
  };
}

export interface WSChannelMessage extends WSBaseMessage {
  type: 'channel:message';
  data: {
    channel: string;
    message: any;
    sender?: string;
    broadcast?: boolean;
  };
}

export interface WSChannelBroadcastMessage extends WSBaseMessage {
  type: 'channel:broadcast';
  data: {
    channel: string;
    message: any;
    exclude?: string[];
  };
}

// Subscription messages
export interface WSSubscribeMessage extends WSBaseMessage {
  type: 'subscription:subscribe';
  data: {
    event: string;
    filter?: Record<string, any>;
    options?: {
      includeHistory?: boolean;
      maxHistory?: number;
    };
  };
}

export interface WSUnsubscribeMessage extends WSBaseMessage {
  type: 'subscription:unsubscribe';
  data: {
    event: string;
  };
}

export interface WSSubscriptionEventMessage extends WSBaseMessage {
  type: 'subscription:event';
  data: {
    event: string;
    payload: any;
    source?: string;
  };
}

// AI streaming messages
export interface WSAIStreamStartMessage extends WSBaseMessage {
  type: 'ai:stream:start';
  data: {
    requestId: string;
    provider: string;
    model: string;
    prompt: string;
    options?: Record<string, any>;
  };
}

export interface WSAIStreamChunkMessage extends WSBaseMessage {
  type: 'ai:stream:chunk';
  data: {
    requestId: string;
    chunk: string;
    index: number;
    finished: boolean;
    usage?: {
      tokens: number;
      cost?: number;
    };
  };
}

export interface WSAIStreamEndMessage extends WSBaseMessage {
  type: 'ai:stream:end';
  data: {
    requestId: string;
    totalChunks: number;
    totalTokens: number;
    duration: number;
    cost?: number;
  };
}

export interface WSAIStreamErrorMessage extends WSBaseMessage {
  type: 'ai:stream:error';
  data: {
    requestId: string;
    error: string;
    code?: string;
    retryable?: boolean;
  };
}

// Tool execution messages
export interface WSToolExecuteStartMessage extends WSBaseMessage {
  type: 'tool:execute:start';
  data: {
    executionId: string;
    toolName: string;
    parameters: Record<string, any>;
    sessionId: string;
  };
}

export interface WSToolExecuteProgressMessage extends WSBaseMessage {
  type: 'tool:execute:progress';
  data: {
    executionId: string;
    progress: number; // 0-100
    status: string;
    output?: string;
    stage?: string;
  };
}

export interface WSToolExecuteResultMessage extends WSBaseMessage {
  type: 'tool:execute:result';
  data: {
    executionId: string;
    result: any;
    success: boolean;
    duration: number;
    output?: string;
  };
}

export interface WSToolExecuteErrorMessage extends WSBaseMessage {
  type: 'tool:execute:error';
  data: {
    executionId: string;
    error: string;
    code?: string;
    stage?: string;
  };
}

// Session messages
export interface WSSessionUpdateMessage extends WSBaseMessage {
  type: 'session:update';
  data: {
    sessionId: string;
    update: {
      messages?: any[];
      context?: Record<string, any>;
      status?: string;
    };
  };
}

// System messages
export interface WSSystemStatusMessage extends WSBaseMessage {
  type: 'system:status';
  data: {
    status: 'healthy' | 'degraded' | 'error';
    components: Record<
      string,
      {
        status: string;
        message?: string;
      }
    >;
    timestamp: number;
  };
}

export interface WSSystemNotificationMessage extends WSBaseMessage {
  type: 'system:notification';
  data: {
    level: 'info' | 'warning' | 'error';
    title: string;
    message: string;
    actions?: Array<{
      label: string;
      action: string;
    }>;
  };
}

// Error message
export interface WSErrorMessage extends WSBaseMessage {
  type:
    | 'connection:error'
    | 'ai:stream:error'
    | 'tool:execute:error'
    | 'system:error';
  data: {
    error: string;
    code?: string;
    details?: any;
    retryable?: boolean;
    timestamp: number;
  };
}

// Union type of all message types
export type WSMessage =
  | WSAuthMessage
  | WSPingMessage
  | WSPongMessage
  | WSReadyMessage
  | WSChannelJoinMessage
  | WSChannelLeaveMessage
  | WSChannelMessage
  | WSChannelBroadcastMessage
  | WSSubscribeMessage
  | WSUnsubscribeMessage
  | WSSubscriptionEventMessage
  | WSAIStreamStartMessage
  | WSAIStreamChunkMessage
  | WSAIStreamEndMessage
  | WSAIStreamErrorMessage
  | WSToolExecuteStartMessage
  | WSToolExecuteProgressMessage
  | WSToolExecuteResultMessage
  | WSToolExecuteErrorMessage
  | WSSessionUpdateMessage
  | WSSystemStatusMessage
  | WSSystemNotificationMessage
  | WSErrorMessage;

// Connection state
export interface WSConnectionState {
  id: string;
  authenticated: boolean;
  userId?: string;
  sessionId?: string;
  channels: Set<string>;
  subscriptions: Set<string>;
  lastPing?: number;
  lastPong?: number;
  messageQueue: WSMessage[];
  metadata: Record<string, any>;
  createdAt: number;
  lastActivity: number;
}

// Channel state
export interface WSChannelState {
  name: string;
  connections: Set<string>;
  metadata: Record<string, any>;
  history: WSMessage[];
  maxHistory: number;
  createdAt: number;
  lastActivity: number;
}

// Subscription state
export interface WSSubscriptionState {
  event: string;
  connections: Set<string>;
  filter?: Record<string, any>;
  options?: {
    includeHistory?: boolean;
    maxHistory?: number;
  };
  history: any[];
  createdAt: number;
}

// Message queue entry
export interface WSQueuedMessage {
  connectionId: string;
  message: WSMessage;
  attempts: number;
  maxAttempts: number;
  nextAttempt: number;
  priority: number;
  persistent: boolean;
}

// Rate limiting state
export interface WSRateLimitState {
  connectionId: string;
  messagesPerSecond: number;
  messagesPerMinute: number;
  bytesPerSecond: number;
  windowStart: number;
  messageCount: number;
  byteCount: number;
  violations: number;
}

// Binary message support
export interface WSBinaryMessage {
  id: string;
  type: string;
  format: 'base64' | 'buffer' | 'arraybuffer';
  data: string | Buffer | ArrayBuffer;
  size: number;
  checksum?: string;
  metadata?: Record<string, any>;
}

// Compression options
export interface WSCompressionOptions {
  enabled: boolean;
  threshold: number; // bytes
  level: number; // 1-9
  windowBits?: number;
  memLevel?: number;
}

// Event handlers
export type WSEventHandler<T = WSMessage> = (
  connectionId: string,
  message: T,
  context: {
    connection: WSConnectionState;
    server: any;
  }
) => Promise<void> | void;

export interface WSEventHandlers {
  [key: string]: WSEventHandler;
}

// Middleware context
export interface WSMiddlewareContext {
  connectionId: string;
  connection: WSConnectionState;
  message: WSMessage;
  rawMessage: string | Buffer;
  server: any;
  next: () => Promise<void>;
  error: (error: Error) => void;
  respond: (message: WSMessage) => Promise<void>;
  broadcast: (
    message: WSMessage,
    filter?: (conn: WSConnectionState) => boolean
  ) => Promise<void>;
}

export type WSMiddleware = (
  context: WSMiddlewareContext
) => Promise<void> | void;

// Server events
export interface WSServerEvents {
  'connection:open': (
    connectionId: string,
    connection: WSConnectionState
  ) => void;
  'connection:close': (
    connectionId: string,
    code?: number,
    reason?: string
  ) => void;
  'connection:error': (connectionId: string, error: Error) => void;
  'connection:authenticated': (connectionId: string, userId: string) => void;
  'message:received': (connectionId: string, message: WSMessage) => void;
  'message:sent': (connectionId: string, message: WSMessage) => void;
  'channel:joined': (connectionId: string, channel: string) => void;
  'channel:left': (connectionId: string, channel: string) => void;
  'subscription:added': (connectionId: string, event: string) => void;
  'subscription:removed': (connectionId: string, event: string) => void;
  'rate:limited': (connectionId: string, type: string) => void;
  'queue:full': (connectionId: string) => void;
}
