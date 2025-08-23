import crypto from 'crypto';
import bcrypt from 'bcryptjs';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../logging/logger.js';

export interface APIKey {
  id: string;
  name: string;
  key: string;
  hashedKey: string;
  userId: string;
  permissions: string[];
  isActive: boolean;
  expiresAt?: Date;
  createdAt: Date;
  lastUsedAt?: Date;
  usageCount: number;
  rateLimit?: {
    requests: number;
    windowMs: number;
  };
  ipWhitelist?: string[];
}

export interface APIKeyMetadata {
  id: string;
  name: string;
  userId: string;
  permissions: string[];
  isActive: boolean;
  expiresAt?: Date;
  createdAt: Date;
  lastUsedAt?: Date;
  usageCount: number;
  keyPrefix: string; // First 8 chars for identification
}

export interface CreateAPIKeyRequest {
  name: string;
  userId: string;
  permissions: string[];
  expiresAt?: Date;
  rateLimit?: {
    requests: number;
    windowMs: number;
  };
  ipWhitelist?: string[];
}

export interface APIKeyValidationResult {
  isValid: boolean;
  key?: APIKey;
  error?: string;
  shouldRotate?: boolean;
}

export class APIKeyManager {
  private readonly keys: Map<string, APIKey> = new Map();
  private readonly userKeys: Map<string, Set<string>> = new Map();
  private readonly rotationSchedule: Map<string, Date> = new Map();
  private auditLog: Array<{
    action: string;
    keyId: string;
    userId: string;
    timestamp: Date;
    metadata?: any;
  }> = [];

  constructor() {
    this.scheduleKeyRotation();
    this.startCleanupJob();
  }

  /**
   * Generate a new API key
   */
  async generateAPIKey(
    request: CreateAPIKeyRequest
  ): Promise<{ key: APIKey; plainKey: string }> {
    try {
      const keyId = uuidv4();
      const plainKey = this.generateSecureKey();
      const hashedKey = await bcrypt.hash(plainKey, 12);

      const apiKey: APIKey = {
        id: keyId,
        name: request.name,
        key: plainKey,
        hashedKey,
        userId: request.userId,
        permissions: request.permissions,
        isActive: true,
        expiresAt: request.expiresAt,
        createdAt: new Date(),
        usageCount: 0,
        rateLimit: request.rateLimit,
        ipWhitelist: request.ipWhitelist,
      };

      // Store the key (don't store plain key in production)
      this.keys.set(keyId, { ...apiKey, key: '' }); // Remove plain key from storage

      // Track user keys
      if (!this.userKeys.has(request.userId)) {
        this.userKeys.set(request.userId, new Set());
      }
      this.userKeys.get(request.userId)!.add(keyId);

      // Schedule rotation if needed
      if (request.expiresAt) {
        this.rotationSchedule.set(keyId, request.expiresAt);
      }

      // Audit log
      this.logAuditEvent('key_created', keyId, request.userId, {
        name: request.name,
        permissions: request.permissions,
        expiresAt: request.expiresAt,
      });

      logger.info('API key generated', {
        keyId,
        userId: request.userId,
        name: request.name,
        permissions: request.permissions,
      });

      return { key: apiKey, plainKey };
    } catch (error) {
      logger.error('Failed to generate API key', error);
      throw new Error('API key generation failed');
    }
  }

  /**
   * Validate an API key
   */
  async validateAPIKey(
    providedKey: string,
    clientIP?: string
  ): Promise<APIKeyValidationResult> {
    try {
      // Extract key ID from the key format (aki_xxxx_yyyy...)
      const keyPrefix = providedKey.substring(0, 12);

      // Find matching key by comparing hashes (in production, use database lookup)
      for (const [keyId, storedKey] of this.keys.entries()) {
        if (await bcrypt.compare(providedKey, storedKey.hashedKey)) {
          return await this.validateStoredKey(storedKey, clientIP);
        }
      }

      this.logAuditEvent('key_validation_failed', 'unknown', 'unknown', {
        keyPrefix,
        clientIP,
      });

      return {
        isValid: false,
        error: 'Invalid API key',
      };
    } catch (error) {
      logger.error('API key validation error', error);
      return {
        isValid: false,
        error: 'Validation error',
      };
    }
  }

  /**
   * Validate a stored key
   */
  private async validateStoredKey(
    key: APIKey,
    clientIP?: string
  ): Promise<APIKeyValidationResult> {
    // Check if key is active
    if (!key.isActive) {
      this.logAuditEvent('key_validation_failed', key.id, key.userId, {
        reason: 'inactive',
        clientIP,
      });
      return {
        isValid: false,
        error: 'API key is inactive',
      };
    }

    // Check expiration
    if (key.expiresAt && new Date() > key.expiresAt) {
      this.logAuditEvent('key_validation_failed', key.id, key.userId, {
        reason: 'expired',
        expiresAt: key.expiresAt,
        clientIP,
      });

      // Auto-deactivate expired keys
      await this.deactivateKey(key.id);

      return {
        isValid: false,
        error: 'API key has expired',
        shouldRotate: true,
      };
    }

    // Check IP whitelist
    if (key.ipWhitelist && key.ipWhitelist.length > 0 && clientIP) {
      if (!key.ipWhitelist.includes(clientIP)) {
        this.logAuditEvent('key_validation_failed', key.id, key.userId, {
          reason: 'ip_not_whitelisted',
          clientIP,
          whitelist: key.ipWhitelist,
        });
        return {
          isValid: false,
          error: 'IP address not whitelisted',
        };
      }
    }

    // Update usage statistics
    key.lastUsedAt = new Date();
    key.usageCount++;

    this.logAuditEvent('key_used', key.id, key.userId, {
      clientIP,
      usageCount: key.usageCount,
    });

    return {
      isValid: true,
      key,
    };
  }

  /**
   * Rotate an API key
   */
  async rotateAPIKey(
    keyId: string
  ): Promise<{ key: APIKey; plainKey: string }> {
    try {
      const existingKey = this.keys.get(keyId);
      if (!existingKey) {
        throw new Error('API key not found');
      }

      // Generate new key
      const plainKey = this.generateSecureKey();
      const hashedKey = await bcrypt.hash(plainKey, 12);

      // Update existing key
      existingKey.key = plainKey;
      existingKey.hashedKey = hashedKey;
      existingKey.usageCount = 0;
      existingKey.lastUsedAt = undefined;

      // Remove plain key from storage
      const rotatedKey = { ...existingKey, key: '' };
      this.keys.set(keyId, rotatedKey);

      this.logAuditEvent('key_rotated', keyId, existingKey.userId);

      logger.info('API key rotated', { keyId, userId: existingKey.userId });

      return { key: existingKey, plainKey };
    } catch (error) {
      logger.error('Failed to rotate API key', error);
      throw error;
    }
  }

  /**
   * Deactivate an API key
   */
  async deactivateKey(keyId: string): Promise<void> {
    try {
      const key = this.keys.get(keyId);
      if (!key) {
        throw new Error('API key not found');
      }

      key.isActive = false;
      this.logAuditEvent('key_deactivated', keyId, key.userId);

      logger.info('API key deactivated', { keyId, userId: key.userId });
    } catch (error) {
      logger.error('Failed to deactivate API key', error);
      throw error;
    }
  }

  /**
   * Delete an API key
   */
  async deleteKey(keyId: string): Promise<void> {
    try {
      const key = this.keys.get(keyId);
      if (!key) {
        throw new Error('API key not found');
      }

      // Remove from maps
      this.keys.delete(keyId);
      this.userKeys.get(key.userId)?.delete(keyId);
      this.rotationSchedule.delete(keyId);

      this.logAuditEvent('key_deleted', keyId, key.userId);

      logger.info('API key deleted', { keyId, userId: key.userId });
    } catch (error) {
      logger.error('Failed to delete API key', error);
      throw error;
    }
  }

  /**
   * Get API key metadata (without sensitive data)
   */
  getKeyMetadata(keyId: string): APIKeyMetadata | null {
    const key = this.keys.get(keyId);
    if (!key) {
      return null;
    }

    return {
      id: key.id,
      name: key.name,
      userId: key.userId,
      permissions: key.permissions,
      isActive: key.isActive,
      expiresAt: key.expiresAt,
      createdAt: key.createdAt,
      lastUsedAt: key.lastUsedAt,
      usageCount: key.usageCount,
      keyPrefix: key.hashedKey.substring(0, 8),
    };
  }

  /**
   * Get all keys for a user
   */
  getUserKeys(userId: string): APIKeyMetadata[] {
    const userKeyIds = this.userKeys.get(userId);
    if (!userKeyIds) {
      return [];
    }

    return Array.from(userKeyIds)
      .map(keyId => this.getKeyMetadata(keyId))
      .filter((metadata): metadata is APIKeyMetadata => metadata !== null);
  }

  /**
   * Generate secure API key
   */
  private generateSecureKey(): string {
    const prefix = 'aki'; // API Key Identifier
    const timestamp = Date.now().toString(36);
    const randomBytes = crypto.randomBytes(32).toString('hex');

    return `${prefix}_${timestamp}_${randomBytes}`;
  }

  /**
   * Schedule automatic key rotation
   */
  private scheduleKeyRotation(): void {
    setInterval(
      () => {
        this.checkAndRotateKeys();
      },
      24 * 60 * 60 * 1000
    ); // Check daily

    logger.info('API key rotation schedule initialized');
  }

  /**
   * Check and rotate keys that need rotation
   */
  private async checkAndRotateKeys(): Promise<void> {
    const now = new Date();
    const keysToRotate: string[] = [];

    this.rotationSchedule.forEach((expiryDate, keyId) => {
      // Rotate keys 7 days before expiry
      const rotationDate = new Date(
        expiryDate.getTime() - 7 * 24 * 60 * 60 * 1000
      );
      if (now >= rotationDate) {
        keysToRotate.push(keyId);
      }
    });

    for (const keyId of keysToRotate) {
      try {
        await this.rotateAPIKey(keyId);
        logger.info('Auto-rotated API key', { keyId });
      } catch (error) {
        logger.error('Failed to auto-rotate API key', { keyId, error });
      }
    }
  }

  /**
   * Start cleanup job for expired keys
   */
  private startCleanupJob(): void {
    setInterval(
      () => {
        this.cleanupExpiredKeys();
      },
      24 * 60 * 60 * 1000
    ); // Daily cleanup

    logger.info('API key cleanup job started');
  }

  /**
   * Cleanup expired and inactive keys
   */
  private cleanupExpiredKeys(): void {
    const now = new Date();
    const keysToCleanup: string[] = [];

    this.keys.forEach((key, keyId) => {
      // Cleanup keys expired for more than 30 days
      if (key.expiresAt && !key.isActive) {
        const expiredDays =
          (now.getTime() - key.expiresAt.getTime()) / (24 * 60 * 60 * 1000);
        if (expiredDays > 30) {
          keysToCleanup.push(keyId);
        }
      }
    });

    keysToCleanup.forEach(keyId => {
      try {
        this.deleteKey(keyId);
        logger.info('Cleaned up expired API key', { keyId });
      } catch (error) {
        logger.error('Failed to cleanup API key', { keyId, error });
      }
    });
  }

  /**
   * Log audit event
   */
  private logAuditEvent(
    action: string,
    keyId: string,
    userId: string,
    metadata?: any
  ): void {
    const event = {
      action,
      keyId,
      userId,
      timestamp: new Date(),
      metadata,
    };

    this.auditLog.push(event);

    // Keep only last 10000 audit events in memory
    if (this.auditLog.length > 10000) {
      this.auditLog = this.auditLog.slice(-5000);
    }

    logger.debug('API key audit event', event);
  }

  /**
   * Get audit log for a key
   */
  getKeyAuditLog(
    keyId: string
  ): Array<{ action: string; timestamp: Date; metadata?: any }> {
    return this.auditLog
      .filter(event => event.keyId === keyId)
      .map(event => ({
        action: event.action,
        timestamp: event.timestamp,
        metadata: event.metadata,
      }));
  }

  /**
   * Get usage statistics
   */
  getUsageStatistics(): {
    totalKeys: number;
    activeKeys: number;
    expiredKeys: number;
    totalUsage: number;
  } {
    let activeKeys = 0;
    let expiredKeys = 0;
    let totalUsage = 0;
    const now = new Date();

    this.keys.forEach(key => {
      if (key.isActive) {
        if (key.expiresAt && now > key.expiresAt) {
          expiredKeys++;
        } else {
          activeKeys++;
        }
      }
      totalUsage += key.usageCount;
    });

    return {
      totalKeys: this.keys.size,
      activeKeys,
      expiredKeys,
      totalUsage,
    };
  }
}

// Singleton instance
let apiKeyManagerInstance: APIKeyManager | null = null;

export function getAPIKeyManager(): APIKeyManager {
  if (!apiKeyManagerInstance) {
    apiKeyManagerInstance = new APIKeyManager();
  }
  return apiKeyManagerInstance;
}

export default APIKeyManager;
