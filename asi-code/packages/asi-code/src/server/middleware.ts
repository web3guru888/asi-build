/**
 * Server Middleware Components
 *
 * Authentication, CORS, error handling, rate limiting, and logging
 * middleware for the ASI-Code HTTP server.
 */

import type { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { HTTPException } from 'hono/http-exception';
import crypto from 'crypto';
import type { ServerConfig } from './server.js';

// Rate limiting store
class MemoryRateLimitStore {
  private readonly requests = new Map<
    string,
    { count: number; windowStart: number }
  >();

  isAllowed(key: string, windowMs: number, maxRequests: number): boolean {
    const now = Date.now();
    const entry = this.requests.get(key);

    if (!entry || now - entry.windowStart > windowMs) {
      // New window or first request
      this.requests.set(key, { count: 1, windowStart: now });
      return true;
    }

    if (entry.count < maxRequests) {
      entry.count++;
      return true;
    }

    return false;
  }

  cleanup(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    for (const [key, entry] of this.requests.entries()) {
      if (now - entry.windowStart > 60000) {
        // Clean entries older than 1 minute
        expiredKeys.push(key);
      }
    }

    for (const key of expiredKeys) {
      this.requests.delete(key);
    }
  }
}

const rateLimitStore = new MemoryRateLimitStore();

// SECURITY FIX: Constant-time string comparison to prevent timing attacks
function constantTimeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  
  return result === 0;
}

// Cleanup rate limit store periodically
setInterval(() => {
  rateLimitStore.cleanup();
}, 60000);

export function setupMiddleware(app: Hono, config: ServerConfig): void {
  // CORS middleware
  app.use(
    '*',
    cors({
      origin: config.cors.origin,
      credentials: config.cors.credentials,
      allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowHeaders: ['Content-Type', 'Authorization', 'x-api-key'],
    })
  );

  // Request logging
  app.use('*', logger());

  // Rate limiting middleware
  app.use('*', async (c, next) => {
    const clientIp =
      c.req.header('x-forwarded-for') || c.req.header('x-real-ip') || 'unknown';

    const isAllowed = rateLimitStore.isAllowed(
      clientIp,
      config.rateLimit.windowMs,
      config.rateLimit.maxRequests
    );

    if (!isAllowed) {
      return c.json(
        {
          error: 'Rate limit exceeded',
          message: `Too many requests from ${clientIp}. Please try again later.`,
        },
        429
      );
    }

    await next();
  });

  // Authentication middleware for API routes
  if (config.auth.enabled) {
    app.use('/api/*', async (c, next) => {
      // Skip authentication for health check and events
      if (c.req.path === '/health' || c.req.path === '/api/events') {
        await next();
        return;
      }

      const apiKey =
        c.req.header('x-api-key') ||
        c.req.header('authorization')?.replace('Bearer ', '') ||
        c.req.query('api_key');

      if (!apiKey) {
        return c.json(
          {
            error: 'Authentication required',
            message:
              'API key must be provided via x-api-key header, Authorization header, or api_key query parameter',
          },
          401
        );
      }

      // SECURITY FIX: Use constant-time comparison to prevent timing attacks
      if (!apiKey || !constantTimeCompare(apiKey, config.auth.apiKey)) {
        return c.json(
          {
            error: 'Invalid API key',
            message: 'The provided API key is not valid',
          },
          401
        );
      }

      await next();
    });
  }

  // SECURITY FIX: Enhanced request validation middleware
  app.use('*', async (c, next) => {
    // Validate request method
    const allowedMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'];
    if (!allowedMethods.includes(c.req.method)) {
      return c.json({
        error: 'Method not allowed',
        message: 'HTTP method not allowed'
      }, 405);
    }

    // Validate Content-Type for POST/PUT/PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(c.req.method)) {
      const contentType = c.req.header('content-type');

      if (
        !contentType?.includes('application/json') &&
        !contentType?.includes('multipart/form-data') &&
        !contentType?.includes('application/x-www-form-urlencoded')
      ) {
        return c.json(
          {
            error: 'Invalid content type',
            message: 'Content-Type must be application/json for API requests',
          },
          400
        );
      }
    }

    // SECURITY FIX: Validate request headers for potential attacks
    const userAgent = c.req.header('user-agent');
    if (userAgent && userAgent.length > 500) {
      return c.json({
        error: 'Invalid request',
        message: 'User-Agent header too long'
      }, 400);
    }

    // Check for suspicious headers
    const suspiciousHeaders = ['x-forwarded-host', 'x-original-url', 'x-rewrite-url'];
    for (const header of suspiciousHeaders) {
      if (c.req.header(header)) {
        console.warn(`Suspicious header detected: ${header}`);
      }
    }

    await next();
  });

  // Request size limiting
  app.use('*', async (c, next) => {
    const contentLength = c.req.header('content-length');
    if (contentLength && parseInt(contentLength) > 10 * 1024 * 1024) {
      // 10MB limit
      return c.json(
        {
          error: 'Request too large',
          message: 'Request body exceeds maximum size of 10MB',
        },
        413
      );
    }

    await next();
  });

  // Error handling middleware
  app.use('*', async (c, next) => {
    try {
      await next();
    } catch (error) {
      // SECURITY FIX: Log errors safely without exposing sensitive data
      const errorId = Math.random().toString(36).substr(2, 9);
      console.error(`Server error [${errorId}]:`, {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
        requestId: (c as any).get('requestId')
      });

      if (error instanceof HTTPException) {
        return error.getResponse();
      }

      if (error instanceof Error) {
        // Check for specific error types
        if (error.message.includes('JSON')) {
          return c.json(
            {
              error: 'Invalid JSON',
              message: 'Request body contains invalid JSON',
            },
            400
          );
        }

        if (error.message.includes('timeout')) {
          return c.json(
            {
              error: 'Request timeout',
              message: 'The request took too long to process',
            },
            408
          );
        }

        if (error.message.includes('not found')) {
          return c.json(
            {
              error: 'Not found',
              message: 'Resource not found',
              requestId: (c as any).get('requestId')
            },
            404
          );
        }

        // SECURITY FIX: Never expose detailed error messages in any environment
        return c.json(
          {
            error: 'Internal server error',
            message: 'An unexpected error occurred',
            requestId: (c as any).get('requestId')
          },
          500
        );
      }

      return c.json(
        {
          error: 'Unknown error',
          message: 'An unknown error occurred',
        },
        500
      );
    }
  });

  // Security headers middleware
  app.use('*', async (c, next) => {
    await next();

    // Add security headers
    c.header('X-Content-Type-Options', 'nosniff');
    c.header('X-Frame-Options', 'DENY');
    c.header('X-XSS-Protection', '1; mode=block');
    c.header('Referrer-Policy', 'strict-origin-when-cross-origin');

    // Only add HSTS in production with HTTPS
    if (process.env.NODE_ENV === 'production') {
      c.header(
        'Strict-Transport-Security',
        'max-age=31536000; includeSubDomains'
      );
    }
  });

  // Request tracking middleware
  app.use('*', async (c, next) => {
    const startTime = Date.now();
    const requestId = `req_${startTime}_${Math.random().toString(36).substr(2, 9)}`;

    // Add request ID to context (using any to bypass type checking for now)
    (c as any).set('requestId', requestId);
    c.header('X-Request-ID', requestId);

    await next();

    const duration = Date.now() - startTime;
    console.log(
      `[${requestId}] ${c.req.method} ${c.req.path} - ${c.res.status} (${duration}ms)`
    );
  });
}

// Helper function to create API key validation middleware
export function createApiKeyMiddleware(validApiKey: string) {
  return async (c: any, next: any) => {
    const apiKey =
      c.req.header('x-api-key') ||
      c.req.header('authorization')?.replace('Bearer ', '') ||
      c.req.query('api_key');

    if (!apiKey || apiKey !== validApiKey) {
      return c.json(
        {
          error: 'Unauthorized',
          message: 'Invalid or missing API key',
        },
        401
      );
    }

    await next();
  };
}

// Helper function to create session validation middleware
export function createSessionMiddleware() {
  return async (c: any, next: any) => {
    const sessionId = c.req.param('id') || c.req.header('x-session-id');

    if (!sessionId) {
      return c.json(
        {
          error: 'Session required',
          message: 'Session ID must be provided',
        },
        400
      );
    }

    // Add session ID to context for use in handlers
    c.set('sessionId', sessionId);
    await next();
  };
}

// Health check with detailed system info
export function createHealthCheckHandler() {
  return (c: any) => {
    const memoryUsage = process.memoryUsage();
    const uptime = process.uptime();

    return c.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: Math.floor(uptime),
      memory: {
        rss: Math.round(memoryUsage.rss / 1024 / 1024), // MB
        heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024), // MB
        heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024), // MB
      },
      node: process.version,
      environment: process.env.NODE_ENV || 'development',
    });
  };
}
