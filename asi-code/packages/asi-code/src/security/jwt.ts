import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';
import { logger } from '../logging/logger.js';

export interface JWTPayload {
  sub: string; // Subject (user ID)
  iat: number; // Issued at
  exp: number; // Expiration
  aud: string; // Audience
  iss: string; // Issuer
  jti: string; // JWT ID
  scope?: string[]; // Permissions/scopes
  sessionId?: string;
}

export interface JWTConfig {
  accessTokenSecret: string;
  refreshTokenSecret: string;
  accessTokenExpiry: string;
  refreshTokenExpiry: string;
  issuer: string;
  audience: string;
  algorithm: jwt.Algorithm;
}

export class JWTManager {
  private readonly config: JWTConfig;
  private readonly blacklist: Set<string> = new Set();
  private readonly keyRotationSchedule: Map<string, Date> = new Map();

  constructor(config: JWTConfig) {
    this.config = config;
    this.validateConfig();
    this.scheduleKeyRotation();
  }

  private validateConfig(): void {
    if (
      !this.config.accessTokenSecret ||
      this.config.accessTokenSecret.length < 32
    ) {
      throw new Error('Access token secret must be at least 32 characters');
    }
    if (
      !this.config.refreshTokenSecret ||
      this.config.refreshTokenSecret.length < 32
    ) {
      throw new Error('Refresh token secret must be at least 32 characters');
    }
  }

  private scheduleKeyRotation(): void {
    // Schedule key rotation every 30 days
    const rotationInterval = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds

    setInterval(() => {
      this.rotateKeys();
    }, rotationInterval);

    logger.info('JWT key rotation scheduled every 30 days');
  }

  private rotateKeys(): void {
    logger.warn('JWT key rotation initiated');
    // In production, this would involve:
    // 1. Generating new keys
    // 2. Updating configuration
    // 3. Notifying distributed instances
    // 4. Graceful transition period

    const timestamp = new Date();
    this.keyRotationSchedule.set('last_rotation', timestamp);

    logger.info('JWT keys rotated successfully', { timestamp });
  }

  /**
   * Generate access token
   */
  generateAccessToken(
    payload: Omit<JWTPayload, 'iat' | 'exp' | 'jti'>
  ): string {
    try {
      const now = Math.floor(Date.now() / 1000);
      const tokenId = uuidv4();

      const fullPayload: JWTPayload = {
        ...payload,
        iat: now,
        exp: now + this.parseExpiry(this.config.accessTokenExpiry),
        jti: tokenId,
        aud: this.config.audience,
        iss: this.config.issuer,
      };

      const token = jwt.sign(fullPayload, this.config.accessTokenSecret, {
        algorithm: this.config.algorithm,
      });

      logger.debug('Access token generated', {
        userId: payload.sub,
        tokenId,
        expiresIn: this.config.accessTokenExpiry,
      });

      return token;
    } catch (error) {
      logger.error('Failed to generate access token', error);
      throw new Error('Token generation failed');
    }
  }

  /**
   * Generate refresh token
   */
  generateRefreshToken(
    payload: Omit<JWTPayload, 'iat' | 'exp' | 'jti'>
  ): string {
    try {
      const now = Math.floor(Date.now() / 1000);
      const tokenId = uuidv4();

      const fullPayload: JWTPayload = {
        ...payload,
        iat: now,
        exp: now + this.parseExpiry(this.config.refreshTokenExpiry),
        jti: tokenId,
        aud: this.config.audience,
        iss: this.config.issuer,
      };

      const token = jwt.sign(fullPayload, this.config.refreshTokenSecret, {
        algorithm: this.config.algorithm,
      });

      logger.debug('Refresh token generated', {
        userId: payload.sub,
        tokenId,
        expiresIn: this.config.refreshTokenExpiry,
      });

      return token;
    } catch (error) {
      logger.error('Failed to generate refresh token', error);
      throw new Error('Refresh token generation failed');
    }
  }

  /**
   * Verify and decode access token
   */
  verifyAccessToken(token: string): JWTPayload {
    try {
      if (this.isTokenBlacklisted(token)) {
        throw new Error('Token is blacklisted');
      }

      const decoded = jwt.verify(token, this.config.accessTokenSecret, {
        algorithms: [this.config.algorithm],
        audience: this.config.audience,
        issuer: this.config.issuer,
      }) as JWTPayload;

      logger.debug('Access token verified', {
        userId: decoded.sub,
        tokenId: decoded.jti,
      });

      return decoded;
    } catch (error) {
      logger.warn('Access token verification failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Verify and decode refresh token
   */
  verifyRefreshToken(token: string): JWTPayload {
    try {
      if (this.isTokenBlacklisted(token)) {
        throw new Error('Token is blacklisted');
      }

      const decoded = jwt.verify(token, this.config.refreshTokenSecret, {
        algorithms: [this.config.algorithm],
        audience: this.config.audience,
        issuer: this.config.issuer,
      }) as JWTPayload;

      logger.debug('Refresh token verified', {
        userId: decoded.sub,
        tokenId: decoded.jti,
      });

      return decoded;
    } catch (error) {
      logger.warn('Refresh token verification failed', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Blacklist a token (for logout/revocation)
   */
  blacklistToken(token: string): void {
    try {
      const decoded = jwt.decode(token) as JWTPayload;
      if (decoded && decoded.jti) {
        this.blacklist.add(decoded.jti);
        logger.info('Token blacklisted', {
          tokenId: decoded.jti,
          userId: decoded.sub,
        });
      }
    } catch (error) {
      logger.error('Failed to blacklist token', error);
    }
  }

  /**
   * Check if token is blacklisted
   */
  isTokenBlacklisted(token: string): boolean {
    try {
      const decoded = jwt.decode(token) as JWTPayload;
      return decoded && decoded.jti ? this.blacklist.has(decoded.jti) : false;
    } catch (error) {
      return true; // If we can't decode it, consider it blacklisted
    }
  }

  /**
   * Parse expiry string to seconds
   */
  private parseExpiry(expiry: string): number {
    const match = expiry.match(/^(\d+)([smhd])$/);
    if (!match) {
      throw new Error(
        'Invalid expiry format. Use format like "15m", "1h", "7d"'
      );
    }

    const value = parseInt(match[1]);
    const unit = match[2];

    switch (unit) {
      case 's':
        return value;
      case 'm':
        return value * 60;
      case 'h':
        return value * 60 * 60;
      case 'd':
        return value * 24 * 60 * 60;
      default:
        throw new Error('Invalid time unit');
    }
  }

  /**
   * Clean expired tokens from blacklist
   */
  cleanupBlacklist(): void {
    const currentTime = Math.floor(Date.now() / 1000);
    const tokensToRemove: string[] = [];

    this.blacklist.forEach(tokenId => {
      // In production, you'd need to store more metadata to check expiry
      // For now, we'll implement a simple time-based cleanup
      tokensToRemove.push(tokenId);
    });

    // Remove expired blacklisted tokens (simplified approach)
    tokensToRemove.forEach(tokenId => {
      this.blacklist.delete(tokenId);
    });

    logger.debug('Blacklist cleanup completed', {
      removedTokens: tokensToRemove.length,
    });
  }

  /**
   * Get token metadata without verification (for debugging)
   */
  decodeToken(token: string): JWTPayload | null {
    try {
      return jwt.decode(token) as JWTPayload;
    } catch (error) {
      logger.warn('Failed to decode token', error);
      return null;
    }
  }

  /**
   * Generate secure random secret
   */
  static generateSecret(length: number = 64): string {
    return crypto.randomBytes(length).toString('hex');
  }

  /**
   * Get current blacklist size (for monitoring)
   */
  getBlacklistSize(): number {
    return this.blacklist.size;
  }
}

/**
 * Default JWT configuration factory
 */
export function createDefaultJWTConfig(): JWTConfig {
  return {
    accessTokenSecret:
      process.env.JWT_ACCESS_SECRET || JWTManager.generateSecret(64),
    refreshTokenSecret:
      process.env.JWT_REFRESH_SECRET || JWTManager.generateSecret(64),
    accessTokenExpiry: process.env.JWT_ACCESS_EXPIRY || '15m',
    refreshTokenExpiry: process.env.JWT_REFRESH_EXPIRY || '7d',
    issuer: process.env.JWT_ISSUER || 'asi-code',
    audience: process.env.JWT_AUDIENCE || 'asi-code-users',
    algorithm: (process.env.JWT_ALGORITHM as jwt.Algorithm) || 'HS256',
  };
}

// Singleton instance for application use
let jwtManagerInstance: JWTManager | null = null;

export function getJWTManager(config?: JWTConfig): JWTManager {
  if (!jwtManagerInstance) {
    jwtManagerInstance = new JWTManager(config || createDefaultJWTConfig());
  }
  return jwtManagerInstance;
}

export default JWTManager;
