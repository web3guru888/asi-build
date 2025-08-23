/**
 * WebSocket Middleware
 *
 * Collection of middleware functions for WebSocket connections including
 * authentication, rate limiting, logging, and message validation.
 */

import jwt from 'jsonwebtoken';
import { nanoid } from 'nanoid';
import type {
  WSConnectionState,
  WSMessage,
  WSMiddleware,
  WSMiddlewareContext,
} from './types.js';
import type { ServerConfig } from '../../config/config-types.js';

/**
 * Authentication middleware
 */
export function createAuthMiddleware(
  config: ServerConfig['websocket']['auth']
): WSMiddleware {
  if (!config?.enabled) {
    return async (context: WSMiddlewareContext) => {
      await context.next();
    };
  }

  return async (context: WSMiddlewareContext) => {
    const { connection, message, respond } = context;

    // Skip auth for certain message types
    const skipAuthTypes = [
      'connection:auth',
      'connection:ping',
      'connection:pong',
    ];
    if (skipAuthTypes.includes(message.type)) {
      await context.next();
      return;
    }

    // Check if connection is authenticated
    if (!connection.authenticated) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Authentication required',
          code: 'AUTH_REQUIRED',
          timestamp: Date.now(),
        },
      });
      return;
    }

    // Check auth timeout
    if (config.timeout && connection.lastActivity) {
      const elapsed = Date.now() - connection.lastActivity;
      if (elapsed > config.timeout * 1000) {
        connection.authenticated = false;
        await respond({
          id: nanoid(),
          type: 'connection:error',
          timestamp: Date.now(),
          data: {
            error: 'Authentication expired',
            code: 'AUTH_EXPIRED',
            timestamp: Date.now(),
          },
        });
        return;
      }
    }

    await context.next();
  };
}

/**
 * Authentication handler for auth messages
 */
export function createAuthHandler(
  config: ServerConfig['websocket']['auth'],
  secretKey?: string
): WSMiddleware {
  if (!config?.enabled) {
    return async (context: WSMiddlewareContext) => {
      await context.next();
    };
  }

  return async (context: WSMiddlewareContext) => {
    const { connection, message, respond, connectionId, server } = context;

    if (message.type === 'connection:auth') {
      try {
        const { token, sessionId, userId, credentials } = message.data || {};
        let authenticated = false;
        let authUserId: string | undefined;

        switch (config.type) {
          case 'jwt':
            if (token && secretKey) {
              try {
                const decoded = jwt.verify(token, secretKey) as any;
                authenticated = true;
                authUserId = decoded.sub || decoded.userId || decoded.id;
              } catch (error) {
                console.error('JWT verification failed:', error);
              }
            }
            break;

          case 'token':
            // Simple token-based auth (implement your own logic)
            if (token) {
              // TODO: Validate token against your token store
              authenticated = await validateToken(token);
              authUserId = userId;
            }
            break;

          case 'session':
            if (sessionId) {
              // TODO: Validate session against your session store
              authenticated = await validateSession(sessionId);
              authUserId = userId;
            }
            break;

          default:
            if (credentials) {
              // Custom authentication logic
              authenticated = await customAuth(credentials);
              authUserId = credentials.userId;
            }
        }

        if (authenticated) {
          connection.authenticated = true;
          connection.userId = authUserId;
          connection.metadata.authType = config.type;
          connection.metadata.authenticatedAt = Date.now();

          await respond({
            id: nanoid(),
            type: 'connection:ready',
            timestamp: Date.now(),
            data: {
              connectionId,
              authenticated: true,
              userId: authUserId,
            },
          });

          server.emit(
            'connection:authenticated',
            connectionId,
            authUserId || 'unknown'
          );
        } else {
          await respond({
            id: nanoid(),
            type: 'connection:error',
            timestamp: Date.now(),
            data: {
              error: 'Authentication failed',
              code: 'AUTH_FAILED',
              timestamp: Date.now(),
            },
          });
        }
      } catch (error) {
        console.error('Authentication error:', error);
        await respond({
          id: nanoid(),
          type: 'connection:error',
          timestamp: Date.now(),
          data: {
            error: 'Authentication error',
            code: 'AUTH_ERROR',
            timestamp: Date.now(),
          },
        });
      }
    }

    await context.next();
  };
}

/**
 * Rate limiting middleware
 */
export function createRateLimitMiddleware(
  config: ServerConfig['websocket']['rateLimiting']
): WSMiddleware {
  if (!config?.enabled) {
    return async (context: WSMiddlewareContext) => {
      await context.next();
    };
  }

  const rateLimits = new Map<
    string,
    {
      messageCount: number;
      byteCount: number;
      windowStart: number;
      violations: number;
      blocked: boolean;
      blockUntil?: number;
    }
  >();

  return async (context: WSMiddlewareContext) => {
    const { connectionId, rawMessage, respond, server } = context;

    const now = Date.now();
    const messageSize = Buffer.byteLength(rawMessage);
    const messagesPerSecond = config.messagesPerSecond || 10;
    const messagesPerMinute = config.messagesPerMinute || 100;
    const bytesPerSecond = config.bytesPerSecond || 10240;

    let rateLimit = rateLimits.get(connectionId);
    if (!rateLimit) {
      rateLimit = {
        messageCount: 0,
        byteCount: 0,
        windowStart: now,
        violations: 0,
        blocked: false,
      };
      rateLimits.set(connectionId, rateLimit);
    }

    // Check if currently blocked
    if (
      rateLimit.blocked &&
      rateLimit.blockUntil &&
      now < rateLimit.blockUntil
    ) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Rate limit exceeded - temporarily blocked',
          code: 'RATE_LIMIT_BLOCKED',
          retryAfter: rateLimit.blockUntil - now,
          timestamp: Date.now(),
        },
      });
      return;
    }

    // Reset window if needed (60-second window)
    if (now - rateLimit.windowStart > 60000) {
      rateLimit.windowStart = now;
      rateLimit.messageCount = 0;
      rateLimit.byteCount = 0;
      rateLimit.blocked = false;
      rateLimit.blockUntil = undefined;
    }

    // Update counters
    rateLimit.messageCount++;
    rateLimit.byteCount += messageSize;

    // Check limits
    const secondsInWindow = Math.max(1, (now - rateLimit.windowStart) / 1000);
    const currentMps = rateLimit.messageCount / secondsInWindow;
    const currentBps = rateLimit.byteCount / secondsInWindow;

    let violated = false;
    let violationType = '';

    if (currentMps > messagesPerSecond) {
      violated = true;
      violationType = 'messages_per_second';
    } else if (rateLimit.messageCount > messagesPerMinute) {
      violated = true;
      violationType = 'messages_per_minute';
    } else if (currentBps > bytesPerSecond) {
      violated = true;
      violationType = 'bytes_per_second';
    }

    if (violated) {
      rateLimit.violations++;
      server.emit('rate:limited', connectionId, violationType);

      // Progressive blocking
      if (rateLimit.violations > 3) {
        rateLimit.blocked = true;
        rateLimit.blockUntil =
          now + Math.min(rateLimit.violations * 5000, 300000); // Max 5 minutes
      }

      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: `Rate limit exceeded: ${violationType}`,
          code: 'RATE_LIMIT_EXCEEDED',
          violations: rateLimit.violations,
          retryAfter: 1000,
          timestamp: Date.now(),
        },
      });
      return;
    }

    await context.next();
  };
}

/**
 * Message validation middleware
 */
export function createValidationMiddleware(): WSMiddleware {
  return async (context: WSMiddlewareContext) => {
    const { message, respond } = context;

    // Validate basic message structure
    if (!message.id || !message.type || !message.timestamp) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Invalid message format',
          code: 'INVALID_MESSAGE',
          details: 'Message must have id, type, and timestamp fields',
          timestamp: Date.now(),
        },
      });
      return;
    }

    // Validate message ID format
    if (typeof message.id !== 'string' || message.id.length === 0) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Invalid message ID',
          code: 'INVALID_MESSAGE_ID',
          timestamp: Date.now(),
        },
      });
      return;
    }

    // Validate timestamp
    if (typeof message.timestamp !== 'number' || message.timestamp <= 0) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Invalid timestamp',
          code: 'INVALID_TIMESTAMP',
          timestamp: Date.now(),
        },
      });
      return;
    }

    // Check timestamp skew (allow up to 5 minutes difference)
    const now = Date.now();
    const skew = Math.abs(now - message.timestamp);
    if (skew > 300000) {
      // 5 minutes
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Message timestamp too far from server time',
          code: 'TIMESTAMP_SKEW',
          serverTime: now,
          messageTime: message.timestamp,
          timestamp: Date.now(),
        },
      });
      return;
    }

    await context.next();
  };
}

/**
 * Logging middleware
 */
export function createLoggingMiddleware(
  options: {
    logLevel?: 'debug' | 'info' | 'warn' | 'error';
    includeData?: boolean;
    maxDataLength?: number;
  } = {}
): WSMiddleware {
  const {
    logLevel = 'info',
    includeData = false,
    maxDataLength = 1000,
  } = options;

  return async (context: WSMiddlewareContext) => {
    const { connectionId, message, connection } = context;
    const startTime = Date.now();

    try {
      await context.next();

      if (logLevel === 'debug' || logLevel === 'info') {
        const logData: any = {
          connectionId,
          messageType: message.type,
          messageId: message.id,
          duration: Date.now() - startTime,
          userId: connection.userId,
          authenticated: connection.authenticated,
        };

        if (includeData) {
          const data = message.data;
          if (data && typeof data === 'object') {
            const dataStr = JSON.stringify(data);
            if (dataStr.length > maxDataLength) {
              logData.data = dataStr.substring(0, maxDataLength) + '...';
              logData.dataTruncated = true;
            } else {
              logData.data = data;
            }
          }
        }

        console.log('WS Message processed:', logData);
      }
    } catch (error) {
      console.error('WS Message processing error:', {
        connectionId,
        messageType: message.type,
        messageId: message.id,
        error: error instanceof Error ? error.message : String(error),
        duration: Date.now() - startTime,
      });
      throw error;
    }
  };
}

/**
 * Message size limiting middleware
 */
export function createMessageSizeLimitMiddleware(
  maxSize: number = 1024 * 1024
): WSMiddleware {
  return async (context: WSMiddlewareContext) => {
    const { rawMessage, respond } = context;
    const messageSize = Buffer.byteLength(rawMessage);

    if (messageSize > maxSize) {
      await respond({
        id: nanoid(),
        type: 'connection:error',
        timestamp: Date.now(),
        data: {
          error: 'Message too large',
          code: 'MESSAGE_TOO_LARGE',
          size: messageSize,
          maxSize,
          timestamp: Date.now(),
        },
      });
      return;
    }

    await context.next();
  };
}

/**
 * Connection metadata middleware
 */
export function createMetadataMiddleware(): WSMiddleware {
  return async (context: WSMiddlewareContext) => {
    const { connection, message } = context;

    // Update connection activity
    connection.lastActivity = Date.now();

    // Track message counts
    if (!connection.metadata.messageCount) {
      connection.metadata.messageCount = 0;
    }
    connection.metadata.messageCount++;

    // Track message types
    if (!connection.metadata.messageTypes) {
      connection.metadata.messageTypes = {};
    }
    const typeCount = connection.metadata.messageTypes[message.type] || 0;
    connection.metadata.messageTypes[message.type] = typeCount + 1;

    await context.next();
  };
}

/**
 * Error handling middleware
 */
export function createErrorHandlingMiddleware(): WSMiddleware {
  return async (context: WSMiddlewareContext) => {
    try {
      await context.next();
    } catch (error) {
      console.error('WebSocket middleware error:', error);

      const errorResponse = {
        id: nanoid(),
        type: 'connection:error' as const,
        timestamp: Date.now(),
        data: {
          error: 'Internal server error',
          code: 'INTERNAL_ERROR',
          timestamp: Date.now(),
        },
      };

      try {
        await context.respond(errorResponse);
      } catch (responseError) {
        console.error('Failed to send error response:', responseError);
      }

      // Emit error event
      context.error(error instanceof Error ? error : new Error(String(error)));
    }
  };
}

/**
 * Binary message handling middleware
 */
export function createBinaryMessageMiddleware(
  config: ServerConfig['websocket']['binary']
): WSMiddleware {
  if (!config?.enabled) {
    return async (context: WSMiddlewareContext) => {
      await context.next();
    };
  }

  return async (context: WSMiddlewareContext) => {
    const { rawMessage, respond } = context;

    // Check if message is binary
    if (Buffer.isBuffer(rawMessage)) {
      const maxSize = config.maxSize || 10485760; // 10MB default

      if (rawMessage.length > maxSize) {
        await respond({
          id: nanoid(),
          type: 'connection:error',
          timestamp: Date.now(),
          data: {
            error: 'Binary message too large',
            code: 'BINARY_TOO_LARGE',
            size: rawMessage.length,
            maxSize,
            timestamp: Date.now(),
          },
        });
        return;
      }

      // TODO: Process binary message
      // For now, just pass through
    }

    await context.next();
  };
}

// Helper functions for authentication
async function validateToken(token: string): Promise<boolean> {
  // TODO: Implement token validation logic
  // This could check against a database, cache, etc.
  return token.length > 0;
}

async function validateSession(sessionId: string): Promise<boolean> {
  // TODO: Implement session validation logic
  return sessionId.length > 0;
}

async function customAuth(credentials: any): Promise<boolean> {
  // TODO: Implement custom authentication logic
  return credentials?.userId;
}

// Export convenience function to create common middleware stack
export function createDefaultMiddlewareStack(
  config: ServerConfig['websocket']
): WSMiddleware[] {
  const middleware: WSMiddleware[] = [];

  // Error handling (should be first)
  middleware.push(createErrorHandlingMiddleware());

  // Logging
  middleware.push(createLoggingMiddleware({ logLevel: 'info' }));

  // Message size limiting
  middleware.push(createMessageSizeLimitMiddleware());

  // Rate limiting
  if (config.rateLimiting?.enabled) {
    middleware.push(createRateLimitMiddleware(config.rateLimiting));
  }

  // Message validation
  middleware.push(createValidationMiddleware());

  // Binary message support
  if (config.binary?.enabled) {
    middleware.push(createBinaryMessageMiddleware(config.binary));
  }

  // Authentication handler (handles auth messages)
  if (config.auth?.enabled) {
    middleware.push(createAuthHandler(config.auth));
  }

  // Authentication middleware (checks auth for other messages)
  if (config.auth?.enabled) {
    middleware.push(createAuthMiddleware(config.auth));
  }

  // Connection metadata tracking
  middleware.push(createMetadataMiddleware());

  return middleware;
}
