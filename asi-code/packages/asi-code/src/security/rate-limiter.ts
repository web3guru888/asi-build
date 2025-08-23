import { Context, Next } from 'hono';
import { logger } from '../logging/logger.js';

export interface RateLimitConfig {
  windowMs: number; // Time window in milliseconds
  maxRequests: number; // Maximum requests per window
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
  keyGenerator?: (c: Context) => string;
  onLimitReached?: (
    c: Context,
    info: RateLimitInfo
  ) => Response | Promise<Response>;
  store?: RateLimitStore;
}

export interface RateLimitInfo {
  totalHits: number;
  totalRequestsInWindow: number;
  resetTime: Date;
  remainingRequests: number;
}

export interface RateLimitStore {
  get(key: string): Promise<RateLimitInfo | null>;
  set(key: string, info: RateLimitInfo, windowMs: number): Promise<void>;
  increment(key: string, windowMs: number): Promise<RateLimitInfo>;
  reset(key: string): Promise<void>;
}

/**
 * In-memory rate limit store
 */
export class MemoryRateLimitStore implements RateLimitStore {
  private readonly store: Map<
    string,
    { info: RateLimitInfo; expiresAt: number }
  > = new Map();
  private readonly cleanupInterval: NodeJS.Timeout;

  constructor() {
    // Cleanup expired entries every 5 minutes
    this.cleanupInterval = setInterval(
      () => {
        this.cleanup();
      },
      5 * 60 * 1000
    );
  }

  async get(key: string): Promise<RateLimitInfo | null> {
    const entry = this.store.get(key);
    if (!entry || Date.now() > entry.expiresAt) {
      this.store.delete(key);
      return null;
    }
    return entry.info;
  }

  async set(key: string, info: RateLimitInfo, windowMs: number): Promise<void> {
    this.store.set(key, {
      info,
      expiresAt: Date.now() + windowMs,
    });
  }

  async increment(key: string, windowMs: number): Promise<RateLimitInfo> {
    const now = Date.now();
    const entry = this.store.get(key);

    if (!entry || now > entry.expiresAt) {
      // Create new entry
      const resetTime = new Date(now + windowMs);
      const info: RateLimitInfo = {
        totalHits: 1,
        totalRequestsInWindow: 1,
        resetTime,
        remainingRequests: 0, // Will be calculated by rate limiter
      };

      this.store.set(key, {
        info,
        expiresAt: now + windowMs,
      });

      return info;
    }

    // Update existing entry
    entry.info.totalHits++;
    entry.info.totalRequestsInWindow++;

    return entry.info;
  }

  async reset(key: string): Promise<void> {
    this.store.delete(key);
  }

  private cleanup(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    this.store.forEach((entry, key) => {
      if (now > entry.expiresAt) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => {
      this.store.delete(key);
    });

    if (keysToDelete.length > 0) {
      logger.debug('Rate limit store cleanup', {
        cleanedEntries: keysToDelete.length,
        remainingEntries: this.store.size,
      });
    }
  }

  destroy(): void {
    clearInterval(this.cleanupInterval);
    this.store.clear();
  }
}

/**
 * Rate limiter middleware
 */
export class RateLimiter {
  private readonly config: Required<RateLimitConfig>;

  constructor(config: RateLimitConfig) {
    this.config = {
      windowMs: config.windowMs,
      maxRequests: config.maxRequests,
      skipSuccessfulRequests: config.skipSuccessfulRequests ?? false,
      skipFailedRequests: config.skipFailedRequests ?? false,
      keyGenerator: config.keyGenerator ?? this.defaultKeyGenerator,
      onLimitReached: config.onLimitReached ?? this.defaultLimitReachedHandler,
      store: config.store ?? new MemoryRateLimitStore(),
    };
  }

  /**
   * Create middleware function
   */
  middleware() {
    return async (c: Context, next: Next) => {
      const key = this.config.keyGenerator(c);

      try {
        // Get current rate limit info
        const info = await this.config.store.increment(
          key,
          this.config.windowMs
        );

        // Calculate remaining requests
        info.remainingRequests = Math.max(
          0,
          this.config.maxRequests - info.totalRequestsInWindow
        );

        // Set rate limit headers
        this.setRateLimitHeaders(c, info);

        // Check if limit exceeded
        if (info.totalRequestsInWindow > this.config.maxRequests) {
          logger.warn('Rate limit exceeded', {
            key,
            requests: info.totalRequestsInWindow,
            limit: this.config.maxRequests,
            resetTime: info.resetTime,
            userAgent: c.req.header('user-agent'),
            ip: this.getClientIP(c),
          });

          return this.config.onLimitReached(c, info);
        }

        // Continue to next middleware
        await next();

        // Check if we should skip counting this request
        const shouldSkip = this.shouldSkipRequest(c);
        if (shouldSkip) {
          // Decrement the counter since we're skipping this request
          const currentInfo = await this.config.store.get(key);
          if (currentInfo) {
            currentInfo.totalRequestsInWindow--;
            await this.config.store.set(key, currentInfo, this.config.windowMs);
          }
        }
      } catch (error) {
        logger.error('Rate limiter error', { key, error });
        // Continue on error to avoid blocking requests
        await next();
      }
    };
  }

  /**
   * Default key generator (IP-based)
   */
  private defaultKeyGenerator(c: Context): string {
    const ip = this.getClientIP(c);
    return `rate_limit:${ip}`;
  }

  /**
   * Get client IP address
   */
  private getClientIP(c: Context): string {
    // Check various headers for real IP
    const forwarded = c.req.header('x-forwarded-for');
    if (forwarded) {
      return forwarded.split(',')[0].trim();
    }

    const realIP = c.req.header('x-real-ip');
    if (realIP) {
      return realIP;
    }

    const clientIP = c.req.header('x-client-ip');
    if (clientIP) {
      return clientIP;
    }

    // Fallback to connection remote address
    return c.env?.remoteAddr || 'unknown';
  }

  /**
   * Set rate limit headers
   */
  private setRateLimitHeaders(c: Context, info: RateLimitInfo): void {
    c.header('X-RateLimit-Limit', this.config.maxRequests.toString());
    c.header('X-RateLimit-Remaining', info.remainingRequests.toString());
    c.header(
      'X-RateLimit-Reset',
      Math.ceil(info.resetTime.getTime() / 1000).toString()
    );
    c.header('X-RateLimit-Window', (this.config.windowMs / 1000).toString());
  }

  /**
   * Default handler when limit is reached
   */
  private defaultLimitReachedHandler(
    c: Context,
    info: RateLimitInfo
  ): Response {
    const retryAfter = Math.ceil(
      (info.resetTime.getTime() - Date.now()) / 1000
    );

    return c.json(
      {
        error: 'Too Many Requests',
        message: 'Rate limit exceeded',
        retryAfter,
        limit: this.config.maxRequests,
        windowMs: this.config.windowMs,
      },
      429,
      {
        'Retry-After': retryAfter.toString(),
      }
    );
  }

  /**
   * Check if request should be skipped from counting
   */
  private shouldSkipRequest(c: Context): boolean {
    const statusCode = c.res.status;

    if (this.config.skipSuccessfulRequests && statusCode < 400) {
      return true;
    }

    if (this.config.skipFailedRequests && statusCode >= 400) {
      return true;
    }

    return false;
  }
}

/**
 * Predefined rate limit configurations
 */
export const RateLimitPresets = {
  // Very strict - for sensitive endpoints
  strict: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 5,
  },

  // Standard API rate limit
  standard: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 100,
  },

  // Generous for general use
  generous: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 1000,
  },

  // For login attempts
  login: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 5,
  },

  // For password reset
  passwordReset: {
    windowMs: 60 * 60 * 1000, // 1 hour
    maxRequests: 3,
  },

  // For file uploads
  upload: {
    windowMs: 60 * 60 * 1000, // 1 hour
    maxRequests: 10,
  },
};

/**
 * User-based rate limiting (requires authentication)
 */
export function createUserRateLimiter(
  config: Omit<RateLimitConfig, 'keyGenerator'>
) {
  return new RateLimiter({
    ...config,
    keyGenerator: (c: Context) => {
      // Extract user ID from JWT or session
      const userId = c.get('userId') || c.get('user')?.id;
      if (userId) {
        return `rate_limit:user:${userId}`;
      }

      // Fallback to IP-based if no user
      const ip =
        c.req.header('x-forwarded-for')?.split(',')[0] ||
        c.req.header('x-real-ip') ||
        c.env?.remoteAddr ||
        'unknown';
      return `rate_limit:ip:${ip}`;
    },
  });
}

/**
 * API key based rate limiting
 */
export function createAPIKeyRateLimiter(
  config: Omit<RateLimitConfig, 'keyGenerator'>
) {
  return new RateLimiter({
    ...config,
    keyGenerator: (c: Context) => {
      const apiKey =
        c.req.header('x-api-key') ||
        c.req.header('authorization')?.replace('Bearer ', '');
      if (apiKey) {
        // Use a hash of the API key for privacy
        const crypto = require('crypto');
        const keyHash = crypto
          .createHash('sha256')
          .update(apiKey)
          .digest('hex')
          .substring(0, 16);
        return `rate_limit:api:${keyHash}`;
      }

      // Fallback to IP
      const ip =
        c.req.header('x-forwarded-for')?.split(',')[0] ||
        c.req.header('x-real-ip') ||
        c.env?.remoteAddr ||
        'unknown';
      return `rate_limit:ip:${ip}`;
    },
  });
}

/**
 * Endpoint-specific rate limiting
 */
export function createEndpointRateLimiter(
  endpoint: string,
  config: Omit<RateLimitConfig, 'keyGenerator'>
) {
  return new RateLimiter({
    ...config,
    keyGenerator: (c: Context) => {
      const ip =
        c.req.header('x-forwarded-for')?.split(',')[0] ||
        c.req.header('x-real-ip') ||
        c.env?.remoteAddr ||
        'unknown';
      return `rate_limit:endpoint:${endpoint}:${ip}`;
    },
  });
}

/**
 * Sliding window rate limiter (more sophisticated)
 */
export class SlidingWindowRateLimiter {
  private readonly windows: Map<string, number[]> = new Map();
  private readonly windowMs: number;
  private readonly maxRequests: number;

  constructor(windowMs: number, maxRequests: number) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;

    // Cleanup old windows every minute
    setInterval(() => {
      this.cleanup();
    }, 60 * 1000);
  }

  async isAllowed(
    key: string
  ): Promise<{ allowed: boolean; resetTime: Date; remainingRequests: number }> {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Get or create window
    let window = this.windows.get(key) || [];

    // Remove old timestamps
    window = window.filter(timestamp => timestamp > windowStart);

    // Check if request is allowed
    const allowed = window.length < this.maxRequests;

    if (allowed) {
      window.push(now);
      this.windows.set(key, window);
    }

    const resetTime = new Date(Math.min(...window) + this.windowMs);
    const remainingRequests = Math.max(0, this.maxRequests - window.length);

    return {
      allowed,
      resetTime,
      remainingRequests,
    };
  }

  private cleanup(): void {
    const now = Date.now();
    const cutoff = now - this.windowMs * 2; // Keep some buffer

    this.windows.forEach((window, key) => {
      const filteredWindow = window.filter(timestamp => timestamp > cutoff);
      if (filteredWindow.length === 0) {
        this.windows.delete(key);
      } else {
        this.windows.set(key, filteredWindow);
      }
    });
  }
}

export default RateLimiter;
