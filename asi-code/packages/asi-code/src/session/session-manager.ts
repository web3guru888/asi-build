/**
 * Session Manager Implementation
 * 
 * Manages session lifecycle, creation, retrieval, deletion, and cleanup
 * for the ASI-Code system with Kenny Integration Pattern support.
 */

import { EventEmitter } from 'eventemitter3';
import { nanoid } from 'nanoid';
import { Session, DefaultSession } from './session.js';
import type { SessionStorage } from './storage.js';
import type { KennyContext } from '../kenny/index.js';

export interface SessionConfig {
  maxMessages: number;
  ttl: number; // Time to live in milliseconds
  persistHistory: boolean;
  storageProvider: string;
}

export interface SessionData {
  id: string;
  userId?: string;
  kennyContext: KennyContext;
  messages: any[];
  metadata: Record<string, any>;
  createdAt: Date;
  lastActivity: Date;
  config: SessionConfig;
}

export interface SessionManager extends EventEmitter {
  createSession(userId?: string, config?: Partial<SessionConfig>): Promise<Session>;
  getSession(sessionId: string): Promise<Session | null>;
  deleteSession(sessionId: string): Promise<void>;
  listSessions(userId?: string): Promise<string[]>;
  saveSession(sessionId: string): Promise<void>;
  cleanup(): Promise<void>;
  getActiveSessionCount(): number;
}

export class DefaultSessionManager extends EventEmitter implements SessionManager {
  private sessions = new Map<string, Session>();
  private storage: SessionStorage;
  private cleanupInterval: NodeJS.Timeout | null = null;
  private defaultConfig: SessionConfig = {
    maxMessages: 100,
    ttl: 24 * 60 * 60 * 1000, // 24 hours
    persistHistory: true,
    storageProvider: 'sqlite'
  };

  constructor(storage: SessionStorage) {
    super();
    this.storage = storage;
    this.startCleanupTimer();
    
    // Handle graceful shutdown
    process.on('SIGINT', () => this.cleanup());
    process.on('SIGTERM', () => this.cleanup());
  }

  async createSession(userId?: string, config?: Partial<SessionConfig>): Promise<Session> {
    const sessionConfig = { ...this.defaultConfig, ...config };
    const sessionId = nanoid();
    
    // Create Kenny context for session
    const kennyContext: KennyContext = {
      id: `ctx_${sessionId}`,
      sessionId,
      userId,
      metadata: {
        createdAt: new Date().toISOString(),
        userAgent: 'ASI-Code/1.0',
        sessionType: 'interactive'
      },
      consciousness: {
        level: 1,
        state: 'active',
        lastActivity: new Date()
      }
    };

    const sessionData: SessionData = {
      id: sessionId,
      userId,
      kennyContext,
      messages: [],
      metadata: {
        version: '1.0',
        capabilities: ['chat', 'tools', 'memory'],
        preferences: {}
      },
      createdAt: new Date(),
      lastActivity: new Date(),
      config: sessionConfig
    };

    const session = new DefaultSession(sessionData);
    this.sessions.set(sessionId, session);

    // Set up session event handlers
    this.setupSessionEventHandlers(session);

    // Save to storage if persistence enabled
    if (sessionConfig.persistHistory) {
      try {
        await this.storage.save(sessionData);
      } catch (error) {
        console.error(`Failed to save session ${sessionId}:`, error);
        // Continue without persistence rather than failing
      }
    }

    this.emit('session:created', { 
      sessionId, 
      userId, 
      kennyContextId: kennyContext.id 
    });
    
    return session;
  }

  async getSession(sessionId: string): Promise<Session | null> {
    // Try memory cache first
    let session = this.sessions.get(sessionId);
    if (session && !session.isExpired()) {
      // Update last access
      session.data.lastActivity = new Date();
      return session;
    }

    // Remove expired session from memory
    if (session && session.isExpired()) {
      this.sessions.delete(sessionId);
      this.emit('session:expired', { sessionId });
    }

    // Try loading from storage
    try {
      const sessionData = await this.storage.load(sessionId);
      if (sessionData) {
        // Check if stored session is expired
        const now = Date.now();
        const expiry = sessionData.lastActivity.getTime() + sessionData.config.ttl;
        
        if (now > expiry) {
          await this.storage.delete(sessionId);
          this.emit('session:expired', { sessionId });
          return null;
        }

        // Create session from stored data
        session = new DefaultSession(sessionData);
        this.sessions.set(sessionId, session);
        this.setupSessionEventHandlers(session);
        
        this.emit('session:restored', { sessionId });
        return session;
      }
    } catch (error) {
      console.error(`Failed to load session ${sessionId}:`, error);
      this.emit('session:load_error', { sessionId, error: (error as Error).message });
    }

    return null;
  }

  async deleteSession(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    
    if (session) {
      try {
        await session.cleanup();
      } catch (error) {
        console.error(`Error cleaning up session ${sessionId}:`, error);
      }
      this.sessions.delete(sessionId);
    }

    // Remove from storage
    try {
      await this.storage.delete(sessionId);
    } catch (error) {
      console.error(`Failed to delete session ${sessionId} from storage:`, error);
    }

    this.emit('session:deleted', { sessionId });
  }

  async listSessions(userId?: string): Promise<string[]> {
    try {
      return await this.storage.list(userId);
    } catch (error) {
      console.error('Failed to list sessions:', error);
      // Fall back to memory cache
      const memorySessions = Array.from(this.sessions.values())
        .filter(session => !userId || session.data.userId === userId)
        .map(session => session.data.id);
      
      return memorySessions;
    }
  }

  async saveSession(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.data.config.persistHistory) {
      return;
    }

    try {
      // Update last activity before saving
      session.data.lastActivity = new Date();
      await this.storage.save(session.data);
      this.emit('session:saved', { sessionId });
    } catch (error) {
      console.error(`Failed to save session ${sessionId}:`, error);
      this.emit('session:save_error', { sessionId, error: (error as Error).message });
      throw error;
    }
  }

  getActiveSessionCount(): number {
    return this.sessions.size;
  }

  async getSessionStats(): Promise<{
    total: number;
    active: number;
    expired: number;
    byUser: Record<string, number>;
  }> {
    const stats = {
      total: 0,
      active: 0,
      expired: 0,
      byUser: {} as Record<string, number>
    };

    try {
      const allSessionIds = await this.storage.list();
      stats.total = allSessionIds.length;

      for (const session of this.sessions.values()) {
        if (session.isExpired()) {
          stats.expired++;
        } else {
          stats.active++;
          
          const userId = session.data.userId || 'anonymous';
          stats.byUser[userId] = (stats.byUser[userId] || 0) + 1;
        }
      }
    } catch (error) {
      console.error('Failed to get session stats:', error);
    }

    return stats;
  }

  private setupSessionEventHandlers(session: Session): void {
    session.on('message:added', (data) => {
      this.emit('session:message_added', { ...data, sessionId: session.data.id });
    });

    session.on('context:updated', (data) => {
      this.emit('session:context_updated', { ...data, sessionId: session.data.id });
    });

    session.on('metadata:updated', (data) => {
      this.emit('session:metadata_updated', { ...data, sessionId: session.data.id });
    });

    session.on('messages:trimmed', (data) => {
      this.emit('session:messages_trimmed', { ...data, sessionId: session.data.id });
    });
  }

  private startCleanupTimer(): void {
    // Run cleanup every 5 minutes
    this.cleanupInterval = setInterval(async () => {
      try {
        await this.cleanupExpiredSessions();
      } catch (error) {
        console.error('Error during scheduled cleanup:', error);
      }
    }, 5 * 60 * 1000);
  }

  private async cleanupExpiredSessions(): Promise<void> {
    const expiredSessions: string[] = [];
    const now = Date.now();

    // Check memory sessions
    for (const [id, session] of this.sessions.entries()) {
      if (session.isExpired()) {
        expiredSessions.push(id);
        try {
          await session.cleanup();
        } catch (error) {
          console.error(`Error cleaning up expired session ${id}:`, error);
        }
        this.sessions.delete(id);
      }
    }

    // Cleanup storage
    try {
      await this.storage.cleanup();
    } catch (error) {
      console.error('Error during storage cleanup:', error);
    }

    if (expiredSessions.length > 0) {
      this.emit('sessions:cleaned', { 
        expired: expiredSessions.length, 
        sessionIds: expiredSessions,
        timestamp: new Date()
      });
    }
  }

  async cleanup(): Promise<void> {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Cleanup all active sessions
    const sessionCleanupPromises = Array.from(this.sessions.values()).map(session => 
      session.cleanup().catch(error => 
        console.error(`Error cleaning up session ${session.data.id}:`, error)
      )
    );
    
    await Promise.all(sessionCleanupPromises);
    this.sessions.clear();

    // Cleanup storage
    try {
      await this.storage.cleanup();
    } catch (error) {
      console.error('Error during final storage cleanup:', error);
    }

    this.removeAllListeners();
    this.emit('manager:cleanup');
  }
}

// Factory function
export function createSessionManager(storage: SessionStorage): SessionManager {
  return new DefaultSessionManager(storage);
}