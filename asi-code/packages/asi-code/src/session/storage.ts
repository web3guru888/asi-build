/**
 * Session Storage Implementation
 * 
 * SQLite-based persistence layer for session data with backup/restore
 * capabilities and efficient querying.
 */

import { EventEmitter } from 'eventemitter3';
import type { SessionData } from './session-manager.js';

export interface SessionStorage extends EventEmitter {
  save(sessionData: SessionData): Promise<void>;
  load(sessionId: string): Promise<SessionData | null>;
  delete(sessionId: string): Promise<void>;
  list(userId?: string): Promise<string[]>;
  cleanup(): Promise<void>;
  backup(): Promise<string>;
  restore(backupData: string): Promise<void>;
  getStats(): Promise<StorageStats>;
}

export interface StorageStats {
  totalSessions: number;
  totalMessages: number;
  storageSize: number;
  oldestSession?: Date;
  newestSession?: Date;
  userCounts: Record<string, number>;
}

// In-memory implementation for development/testing
export class MemorySessionStorage extends EventEmitter implements SessionStorage {
  private sessions = new Map<string, SessionData>();

  async save(sessionData: SessionData): Promise<void> {
    // Deep clone to prevent reference issues
    const clonedData = JSON.parse(JSON.stringify(sessionData, (key, value) => {
      // Handle Date objects
      if (key === 'createdAt' || key === 'lastActivity' || key === 'timestamp') {
        return value instanceof Date ? value.toISOString() : value;
      }
      return value;
    }));

    // Convert date strings back to Date objects
    clonedData.createdAt = new Date(clonedData.createdAt);
    clonedData.lastActivity = new Date(clonedData.lastActivity);
    if (clonedData.kennyContext?.consciousness?.lastActivity) {
      clonedData.kennyContext.consciousness.lastActivity = new Date(clonedData.kennyContext.consciousness.lastActivity);
    }

    // Convert message timestamps
    if (clonedData.messages) {
      clonedData.messages.forEach((msg: any) => {
        if (msg.timestamp) {
          msg.timestamp = new Date(msg.timestamp);
        }
      });
    }

    this.sessions.set(sessionData.id, clonedData);
    this.emit('session:saved', { sessionId: sessionData.id });
  }

  async load(sessionId: string): Promise<SessionData | null> {
    const session = this.sessions.get(sessionId);
    if (!session) {
      return null;
    }

    this.emit('session:loaded', { sessionId });
    return session;
  }

  async delete(sessionId: string): Promise<void> {
    const existed = this.sessions.delete(sessionId);
    if (existed) {
      this.emit('session:deleted', { sessionId });
    }
  }

  async list(userId?: string): Promise<string[]> {
    if (!userId) {
      return Array.from(this.sessions.keys());
    }
    
    return Array.from(this.sessions.values())
      .filter(session => session.userId === userId)
      .map(session => session.id);
  }

  async cleanup(): Promise<void> {
    const now = Date.now();
    const expiredSessions: string[] = [];

    for (const [id, session] of this.sessions.entries()) {
      const expiry = session.lastActivity.getTime() + session.config.ttl;
      if (now > expiry) {
        expiredSessions.push(id);
        this.sessions.delete(id);
      }
    }

    if (expiredSessions.length > 0) {
      this.emit('sessions:expired', { 
        count: expiredSessions.length, 
        sessionIds: expiredSessions 
      });
    }
  }

  async backup(): Promise<string> {
    const backup = {
      version: '1.0',
      timestamp: new Date().toISOString(),
      sessions: Array.from(this.sessions.values())
    };

    return JSON.stringify(backup, null, 2);
  }

  async restore(backupData: string): Promise<void> {
    try {
      const backup = JSON.parse(backupData);
      
      if (!backup.version || !backup.sessions) {
        throw new Error('Invalid backup format');
      }

      // Clear existing sessions
      this.sessions.clear();

      // Restore sessions
      for (const sessionData of backup.sessions) {
        await this.save(sessionData);
      }

      this.emit('backup:restored', { 
        sessionCount: backup.sessions.length,
        backupDate: backup.timestamp 
      });
    } catch (error) {
      this.emit('backup:error', { error: (error as Error).message });
      throw error;
    }
  }

  async getStats(): Promise<StorageStats> {
    const sessions = Array.from(this.sessions.values());
    const stats: StorageStats = {
      totalSessions: sessions.length,
      totalMessages: 0,
      storageSize: JSON.stringify(sessions).length,
      userCounts: {}
    };

    let oldestDate: Date | null = null;
    let newestDate: Date | null = null;

    for (const session of sessions) {
      stats.totalMessages += session.messages.length;

      // Track user counts
      const userId = session.userId || 'anonymous';
      stats.userCounts[userId] = (stats.userCounts[userId] || 0) + 1;

      // Track date range
      if (!oldestDate || session.createdAt < oldestDate) {
        oldestDate = session.createdAt;
      }
      if (!newestDate || session.createdAt > newestDate) {
        newestDate = session.createdAt;
      }
    }

    if (oldestDate) stats.oldestSession = oldestDate;
    if (newestDate) stats.newestSession = newestDate;

    return stats;
  }
}

// SQLite-based storage implementation
export class SQLiteSessionStorage extends EventEmitter implements SessionStorage {
  private db: any = null;
  private dbPath: string;
  private initialized = false;

  constructor(dbPath: string = './sessions.db') {
    super();
    this.dbPath = dbPath;
  }

  private async ensureInitialized(): Promise<void> {
    if (this.initialized) return;

    try {
      // Note: In a real implementation, you'd use a proper SQLite driver like better-sqlite3
      // For now, we'll fall back to memory storage if SQLite isn't available
      let Database: any = null;
      try {
        Database = (await eval("import('better-sqlite3')")).default;
      } catch (error) {
        // SQLite not available
      }
      
      if (!Database) {
        console.warn('SQLite not available, falling back to memory storage');
        throw new Error('SQLite driver not available');
      }

      this.db = new Database(this.dbPath);
      
      // Create tables
      this.db.exec(`
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY,
          user_id TEXT,
          data TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
          expires_at DATETIME NOT NULL,
          message_count INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
        CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
      `);

      this.initialized = true;
      this.emit('storage:initialized', { dbPath: this.dbPath });
    } catch (error) {
      console.error('Failed to initialize SQLite storage:', error);
      throw error;
    }
  }

  async save(sessionData: SessionData): Promise<void> {
    await this.ensureInitialized();

    const expiresAt = new Date(sessionData.lastActivity.getTime() + sessionData.config.ttl);
    const dataJson = JSON.stringify(sessionData);

    try {
      const stmt = this.db.prepare(`
        INSERT OR REPLACE INTO sessions 
        (id, user_id, data, created_at, last_activity, expires_at, message_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `);

      stmt.run(
        sessionData.id,
        sessionData.userId || null,
        dataJson,
        sessionData.createdAt.toISOString(),
        sessionData.lastActivity.toISOString(),
        expiresAt.toISOString(),
        sessionData.messages.length
      );

      this.emit('session:saved', { sessionId: sessionData.id });
    } catch (error) {
      this.emit('session:save_error', { sessionId: sessionData.id, error: (error as Error).message });
      throw error;
    }
  }

  async load(sessionId: string): Promise<SessionData | null> {
    await this.ensureInitialized();

    try {
      const stmt = this.db.prepare('SELECT data FROM sessions WHERE id = ? AND expires_at > datetime("now")');
      const row = stmt.get(sessionId);

      if (!row) {
        return null;
      }

      const sessionData = JSON.parse(row.data);
      
      // Convert ISO strings back to Date objects
      sessionData.createdAt = new Date(sessionData.createdAt);
      sessionData.lastActivity = new Date(sessionData.lastActivity);
      
      if (sessionData.kennyContext?.consciousness?.lastActivity) {
        sessionData.kennyContext.consciousness.lastActivity = new Date(sessionData.kennyContext.consciousness.lastActivity);
      }

      if (sessionData.messages) {
        sessionData.messages.forEach((msg: any) => {
          if (msg.timestamp) {
            msg.timestamp = new Date(msg.timestamp);
          }
        });
      }

      this.emit('session:loaded', { sessionId });
      return sessionData;
    } catch (error) {
      this.emit('session:load_error', { sessionId, error: (error as Error).message });
      throw error;
    }
  }

  async delete(sessionId: string): Promise<void> {
    await this.ensureInitialized();

    try {
      const stmt = this.db.prepare('DELETE FROM sessions WHERE id = ?');
      const result = stmt.run(sessionId);

      if (result.changes > 0) {
        this.emit('session:deleted', { sessionId });
      }
    } catch (error) {
      this.emit('session:delete_error', { sessionId, error: (error as Error).message });
      throw error;
    }
  }

  async list(userId?: string): Promise<string[]> {
    await this.ensureInitialized();

    try {
      let stmt;
      if (userId) {
        stmt = this.db.prepare('SELECT id FROM sessions WHERE user_id = ? AND expires_at > datetime("now") ORDER BY last_activity DESC');
        const rows = stmt.all(userId);
        return rows.map((row: any) => row.id);
      } else {
        stmt = this.db.prepare('SELECT id FROM sessions WHERE expires_at > datetime("now") ORDER BY last_activity DESC');
        const rows = stmt.all();
        return rows.map((row: any) => row.id);
      }
    } catch (error) {
      this.emit('list:error', { userId, error: (error as Error).message });
      throw error;
    }
  }

  async cleanup(): Promise<void> {
    await this.ensureInitialized();

    try {
      const stmt = this.db.prepare('DELETE FROM sessions WHERE expires_at <= datetime("now")');
      const result = stmt.run();

      if (result.changes > 0) {
        this.emit('sessions:expired', { count: result.changes });
      }

      // Vacuum database to reclaim space
      this.db.exec('VACUUM');
    } catch (error) {
      this.emit('cleanup:error', { error: (error as Error).message });
      throw error;
    }
  }

  async backup(): Promise<string> {
    await this.ensureInitialized();

    try {
      const stmt = this.db.prepare('SELECT * FROM sessions ORDER BY created_at');
      const rows = stmt.all();

      const backup = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        sessions: rows.map((row: any) => JSON.parse(row.data))
      };

      return JSON.stringify(backup, null, 2);
    } catch (error) {
      this.emit('backup:error', { error: (error as Error).message });
      throw error;
    }
  }

  async restore(backupData: string): Promise<void> {
    await this.ensureInitialized();

    try {
      const backup = JSON.parse(backupData);
      
      if (!backup.version || !backup.sessions) {
        throw new Error('Invalid backup format');
      }

      // Start transaction
      this.db.exec('BEGIN TRANSACTION');

      try {
        // Clear existing sessions
        this.db.exec('DELETE FROM sessions');

        // Restore sessions
        for (const sessionData of backup.sessions) {
          await this.save(sessionData);
        }

        this.db.exec('COMMIT');
        
        this.emit('backup:restored', { 
          sessionCount: backup.sessions.length,
          backupDate: backup.timestamp 
        });
      } catch (error) {
        this.db.exec('ROLLBACK');
        throw error;
      }
    } catch (error) {
      this.emit('backup:error', { error: (error as Error).message });
      throw error;
    }
  }

  async getStats(): Promise<StorageStats> {
    await this.ensureInitialized();

    try {
      const totalQuery = this.db.prepare('SELECT COUNT(*) as count, SUM(message_count) as messages FROM sessions');
      const totalResult = totalQuery.get();

      const dateQuery = this.db.prepare('SELECT MIN(created_at) as oldest, MAX(created_at) as newest FROM sessions');
      const dateResult = dateQuery.get();

      const userQuery = this.db.prepare(`
        SELECT COALESCE(user_id, 'anonymous') as user_id, COUNT(*) as count 
        FROM sessions 
        GROUP BY user_id
      `);
      const userResults = userQuery.all();

      const stats: StorageStats = {
        totalSessions: totalResult.count || 0,
        totalMessages: totalResult.messages || 0,
        storageSize: 0, // Would need filesystem access to get actual file size
        userCounts: {}
      };

      if (dateResult.oldest) stats.oldestSession = new Date(dateResult.oldest);
      if (dateResult.newest) stats.newestSession = new Date(dateResult.newest);

      for (const row of userResults) {
        stats.userCounts[row.user_id] = row.count;
      }

      return stats;
    } catch (error) {
      this.emit('stats:error', { error: (error as Error).message });
      throw error;
    }
  }

  async close(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.initialized = false;
      this.emit('storage:closed');
    }
  }
}

// Factory functions
export function createMemorySessionStorage(): SessionStorage {
  return new MemorySessionStorage();
}

export function createSQLiteSessionStorage(dbPath?: string): SessionStorage {
  return new SQLiteSessionStorage(dbPath);
}

// Automatic storage selection based on environment
export function createSessionStorage(type?: 'memory' | 'file' | 'sqlite' | 'postgres' | 'mongodb' | 'redis', options?: { dbPath?: string }): SessionStorage {
  switch (type) {
    case 'sqlite':
    case 'postgres':
    case 'mongodb':
      return new SQLiteSessionStorage(options?.dbPath);
    case 'file':
    case 'redis':
    case 'memory':
    default:
      return new MemorySessionStorage();
  }
}