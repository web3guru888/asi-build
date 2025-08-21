/**
 * Unit tests for Session Manager
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { DefaultSessionManager, createSessionManager } from '../../../src/session/session-manager.js';
import { DefaultSession } from '../../../src/session/session.js';
import type { SessionStorage, SessionData } from '../../../src/session/storage.js';
import type { KennyContext } from '../../../src/kenny/index.js';

// Mock session storage implementation
class MockSessionStorage implements SessionStorage {
  private storage = new Map<string, SessionData>();

  async save(sessionData: SessionData): Promise<void> {
    this.storage.set(sessionData.id, { ...sessionData });
  }

  async load(sessionId: string): Promise<SessionData | null> {
    return this.storage.get(sessionId) || null;
  }

  async delete(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }

  async list(userId?: string): Promise<string[]> {
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter(session => !userId || session.userId === userId)
      .map(session => session.id);
  }

  async cleanup(): Promise<void> {
    // Find expired sessions
    const now = Date.now();
    const expiredIds: string[] = [];
    
    for (const [id, session] of this.storage.entries()) {
      const expiry = session.lastActivity.getTime() + session.config.ttl;
      if (now > expiry) {
        expiredIds.push(id);
      }
    }
    
    // Remove expired sessions
    expiredIds.forEach(id => this.storage.delete(id));
  }

  // Test helper methods
  clear(): void {
    this.storage.clear();
  }

  size(): number {
    return this.storage.size;
  }

  has(sessionId: string): boolean {
    return this.storage.has(sessionId);
  }
}

describe('SessionManager', () => {
  let sessionManager: DefaultSessionManager;
  let mockStorage: MockSessionStorage;
  
  beforeEach(() => {
    mockStorage = new MockSessionStorage();
    sessionManager = new DefaultSessionManager(mockStorage);
  });
  
  afterEach(async () => {
    await sessionManager.cleanup();
    mockStorage.clear();
  });

  describe('Session Creation', () => {
    it('should create session with default config', async () => {
      const session = await sessionManager.createSession();
      
      expect(session).toBeInstanceOf(DefaultSession);
      expect(session.data.id).toBeDefined();
      expect(session.data.id).toMatch(/^[A-Za-z0-9_-]{21}$/); // nanoid format
      expect(session.data.config).toMatchObject({
        maxMessages: 100,
        ttl: 24 * 60 * 60 * 1000,
        persistHistory: true,
        storageProvider: 'sqlite'
      });
    });

    it('should create session with user ID', async () => {
      const userId = 'test-user-123';
      const session = await sessionManager.createSession(userId);
      
      expect(session.data.userId).toBe(userId);
      expect(session.data.kennyContext.userId).toBe(userId);
    });

    it('should create session with custom config', async () => {
      const customConfig = {
        maxMessages: 50,
        ttl: 12 * 60 * 60 * 1000, // 12 hours
        persistHistory: false
      };
      
      const session = await sessionManager.createSession('user123', customConfig);
      
      expect(session.data.config).toMatchObject(customConfig);
      expect(session.data.config.storageProvider).toBe('sqlite'); // Default preserved
    });

    it('should generate unique session IDs', async () => {
      const session1 = await sessionManager.createSession();
      const session2 = await sessionManager.createSession();
      
      expect(session1.data.id).not.toBe(session2.data.id);
    });

    it('should create Kenny context for session', async () => {
      const session = await sessionManager.createSession('test-user');
      const context = session.data.kennyContext;
      
      expect(context).toBeDefined();
      expect(context.id).toMatch(/^ctx_/);
      expect(context.sessionId).toBe(session.data.id);
      expect(context.userId).toBe('test-user');
      expect(context.metadata.createdAt).toBeDefined();
      expect(context.consciousness.state).toBe('active');
    });

    it('should save session to storage when persistence enabled', async () => {
      const session = await sessionManager.createSession('user123', { persistHistory: true });
      
      expect(mockStorage.has(session.data.id)).toBe(true);
      
      const storedData = await mockStorage.load(session.data.id);
      expect(storedData).toBeDefined();
      expect(storedData?.userId).toBe('user123');
    });

    it('should not save to storage when persistence disabled', async () => {
      const session = await sessionManager.createSession('user123', { persistHistory: false });
      
      // Should still be tracked in memory but storage might not be called
      expect(sessionManager.getActiveSessionCount()).toBe(1);
    });

    it('should emit session created event', async () => {
      const createdSpy = vi.fn();
      sessionManager.on('session:created', createdSpy);
      
      const session = await sessionManager.createSession('test-user');
      
      expect(createdSpy).toHaveBeenCalledWith({
        sessionId: session.data.id,
        userId: 'test-user',
        kennyContextId: session.data.kennyContext.id
      });
    });

    it('should handle storage save errors gracefully', async () => {
      const failingStorage = new MockSessionStorage();
      failingStorage.save = vi.fn().mockRejectedValue(new Error('Storage error'));
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const manager = new DefaultSessionManager(failingStorage);
      const session = await manager.createSession();
      
      expect(session).toBeDefined();
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save session'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
      await manager.cleanup();
    });
  });

  describe('Session Retrieval', () => {
    it('should retrieve existing session from memory', async () => {
      const originalSession = await sessionManager.createSession('test-user');
      
      const retrievedSession = await sessionManager.getSession(originalSession.data.id);
      
      expect(retrievedSession).toBe(originalSession);
      expect(retrievedSession?.data.userId).toBe('test-user');
    });

    it('should update last activity when retrieving session', async () => {
      const session = await sessionManager.createSession();
      const originalActivity = session.data.lastActivity;
      
      // Wait a bit to ensure timestamp difference
      await new Promise(resolve => setTimeout(resolve, 10));
      
      await sessionManager.getSession(session.data.id);
      
      expect(session.data.lastActivity.getTime()).toBeGreaterThan(originalActivity.getTime());
    });

    it('should load session from storage if not in memory', async () => {
      const session = await sessionManager.createSession('stored-user');
      const sessionId = session.data.id;
      
      // Create new manager to simulate restart
      const newManager = new DefaultSessionManager(mockStorage);
      
      const loadedSession = await newManager.getSession(sessionId);
      
      expect(loadedSession).toBeDefined();
      expect(loadedSession?.data.userId).toBe('stored-user');
      expect(loadedSession?.data.id).toBe(sessionId);
      
      await newManager.cleanup();
    });

    it('should return null for non-existent session', async () => {
      const session = await sessionManager.getSession('non-existent-id');
      expect(session).toBeNull();
    });

    it('should emit session restored event when loading from storage', async () => {
      const session = await sessionManager.createSession('test-user');
      const sessionId = session.data.id;
      
      const newManager = new DefaultSessionManager(mockStorage);
      const restoredSpy = vi.fn();
      newManager.on('session:restored', restoredSpy);
      
      await newManager.getSession(sessionId);
      
      expect(restoredSpy).toHaveBeenCalledWith({ sessionId });
      
      await newManager.cleanup();
    });

    it('should handle expired sessions', async () => {
      const expiredConfig = { ttl: 100 }; // 100ms
      const session = await sessionManager.createSession('user', expiredConfig);
      const sessionId = session.data.id;
      
      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 150));
      
      const expiredSpy = vi.fn();
      sessionManager.on('session:expired', expiredSpy);
      
      const retrievedSession = await sessionManager.getSession(sessionId);
      
      expect(retrievedSession).toBeNull();
      expect(expiredSpy).toHaveBeenCalledWith({ sessionId });
    });

    it('should handle storage load errors', async () => {
      const errorStorage = new MockSessionStorage();
      errorStorage.load = vi.fn().mockRejectedValue(new Error('Load error'));
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const errorSpy = vi.fn();
      
      const manager = new DefaultSessionManager(errorStorage);
      manager.on('session:load_error', errorSpy);
      
      const session = await manager.getSession('test-id');
      
      expect(session).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();
      expect(errorSpy).toHaveBeenCalledWith({
        sessionId: 'test-id',
        error: 'Load error'
      });
      
      consoleSpy.mockRestore();
      await manager.cleanup();
    });
  });

  describe('Session Deletion', () => {
    it('should delete session from memory and storage', async () => {
      const session = await sessionManager.createSession('test-user');
      const sessionId = session.data.id;
      
      expect(sessionManager.getActiveSessionCount()).toBe(1);
      expect(mockStorage.has(sessionId)).toBe(true);
      
      await sessionManager.deleteSession(sessionId);
      
      expect(sessionManager.getActiveSessionCount()).toBe(0);
      expect(mockStorage.has(sessionId)).toBe(false);
    });

    it('should emit session deleted event', async () => {
      const session = await sessionManager.createSession();
      const sessionId = session.data.id;
      
      const deletedSpy = vi.fn();
      sessionManager.on('session:deleted', deletedSpy);
      
      await sessionManager.deleteSession(sessionId);
      
      expect(deletedSpy).toHaveBeenCalledWith({ sessionId });
    });

    it('should handle deleting non-existent session', async () => {
      await expect(sessionManager.deleteSession('non-existent'))
        .resolves.toBeUndefined();
    });

    it('should cleanup session before deletion', async () => {
      const session = await sessionManager.createSession();
      const cleanupSpy = vi.spyOn(session, 'cleanup').mockResolvedValue();
      
      await sessionManager.deleteSession(session.data.id);
      
      expect(cleanupSpy).toHaveBeenCalled();
    });

    it('should handle session cleanup errors', async () => {
      const session = await sessionManager.createSession();
      const sessionId = session.data.id;
      
      vi.spyOn(session, 'cleanup').mockRejectedValue(new Error('Cleanup error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await sessionManager.deleteSession(sessionId);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error cleaning up session'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });

    it('should handle storage deletion errors', async () => {
      const session = await sessionManager.createSession();
      const sessionId = session.data.id;
      
      mockStorage.delete = vi.fn().mockRejectedValue(new Error('Delete error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await sessionManager.deleteSession(sessionId);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to delete session'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('Session Listing', () => {
    beforeEach(async () => {
      await sessionManager.createSession('user1');
      await sessionManager.createSession('user2');
      await sessionManager.createSession('user1'); // Same user, different session
      await sessionManager.createSession(); // Anonymous session
    });

    it('should list all sessions', async () => {
      const allSessions = await sessionManager.listSessions();
      expect(allSessions).toHaveLength(4);
    });

    it('should filter sessions by user ID', async () => {
      const user1Sessions = await sessionManager.listSessions('user1');
      const user2Sessions = await sessionManager.listSessions('user2');
      
      expect(user1Sessions).toHaveLength(2);
      expect(user2Sessions).toHaveLength(1);
    });

    it('should handle storage list errors by falling back to memory', async () => {
      mockStorage.list = vi.fn().mockRejectedValue(new Error('List error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const sessions = await sessionManager.listSessions();
      
      // Should still return sessions from memory
      expect(sessions.length).toBeGreaterThan(0);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to list sessions:',
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('Session Persistence', () => {
    it('should save session manually', async () => {
      const session = await sessionManager.createSession('test-user', { persistHistory: true });
      
      // Modify session data
      session.data.metadata.testValue = 'updated';
      const originalActivity = session.data.lastActivity;
      
      const savedSpy = vi.fn();
      sessionManager.on('session:saved', savedSpy);
      
      await sessionManager.saveSession(session.data.id);
      
      expect(savedSpy).toHaveBeenCalledWith({ sessionId: session.data.id });
      expect(session.data.lastActivity.getTime()).toBeGreaterThan(originalActivity.getTime());
      
      // Verify data was saved
      const storedData = await mockStorage.load(session.data.id);
      expect(storedData?.metadata.testValue).toBe('updated');
    });

    it('should not save session with persistence disabled', async () => {
      const session = await sessionManager.createSession('test-user', { persistHistory: false });
      
      await expect(sessionManager.saveSession(session.data.id))
        .resolves.toBeUndefined();
    });

    it('should not save non-existent session', async () => {
      await expect(sessionManager.saveSession('non-existent'))
        .resolves.toBeUndefined();
    });

    it('should handle save errors', async () => {
      const session = await sessionManager.createSession('test-user');
      
      mockStorage.save = vi.fn().mockRejectedValue(new Error('Save error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const errorSpy = vi.fn();
      sessionManager.on('session:save_error', errorSpy);
      
      await expect(sessionManager.saveSession(session.data.id))
        .rejects.toThrow('Save error');
      
      expect(consoleSpy).toHaveBeenCalled();
      expect(errorSpy).toHaveBeenCalledWith({
        sessionId: session.data.id,
        error: 'Save error'
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Session Statistics', () => {
    beforeEach(async () => {
      await sessionManager.createSession('user1');
      await sessionManager.createSession('user2');
      await sessionManager.createSession('user1');
      await sessionManager.createSession(); // Anonymous
    });

    it('should provide session statistics', async () => {
      const stats = await sessionManager.getSessionStats();
      
      expect(stats).toMatchObject({
        total: 4,
        active: 4,
        expired: 0,
        byUser: {
          user1: 2,
          user2: 1,
          anonymous: 1
        }
      });
    });

    it('should count expired sessions', async () => {
      // Create expired session
      const expiredConfig = { ttl: 10 }; // 10ms
      await sessionManager.createSession('expired-user', expiredConfig);
      
      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 50));
      
      const stats = await sessionManager.getSessionStats();
      
      expect(stats.expired).toBe(1);
    });

    it('should handle storage errors in stats', async () => {
      mockStorage.list = vi.fn().mockRejectedValue(new Error('List error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const stats = await sessionManager.getSessionStats();
      
      expect(stats.total).toBe(0); // Can't get from storage
      expect(stats.active).toBeGreaterThan(0); // But memory sessions are counted
      expect(consoleSpy).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });

    it('should get active session count', () => {
      const count = sessionManager.getActiveSessionCount();
      expect(count).toBe(4);
    });
  });

  describe('Session Events', () => {
    it('should forward session events with session ID', async () => {
      const messageAddedSpy = vi.fn();
      const contextUpdatedSpy = vi.fn();
      const metadataUpdatedSpy = vi.fn();
      
      sessionManager.on('session:message_added', messageAddedSpy);
      sessionManager.on('session:context_updated', contextUpdatedSpy);
      sessionManager.on('session:metadata_updated', metadataUpdatedSpy);
      
      const session = await sessionManager.createSession();
      
      // Simulate session events
      session.emit('message:added', { messageId: 'msg-123' });
      session.emit('context:updated', { field: 'state' });
      session.emit('metadata:updated', { key: 'value' });
      
      expect(messageAddedSpy).toHaveBeenCalledWith({
        messageId: 'msg-123',
        sessionId: session.data.id
      });
      
      expect(contextUpdatedSpy).toHaveBeenCalledWith({
        field: 'state',
        sessionId: session.data.id
      });
      
      expect(metadataUpdatedSpy).toHaveBeenCalledWith({
        key: 'value',
        sessionId: session.data.id
      });
    });
  });

  describe('Cleanup and Lifecycle', () => {
    it('should perform periodic cleanup of expired sessions', async () => {
      vi.useFakeTimers();
      
      const manager = new DefaultSessionManager(mockStorage);
      
      // Create sessions with different expiration times
      await manager.createSession('user1', { ttl: 100 }); // Short-lived
      await manager.createSession('user2', { ttl: 300000 }); // Long-lived
      
      expect(manager.getActiveSessionCount()).toBe(2);
      
      // Fast forward past first session's expiration
      vi.advanceTimersByTime(5 * 60 * 1000 + 150); // 5 minutes + buffer
      
      // Allow cleanup to run
      await new Promise(resolve => setImmediate(resolve));
      
      expect(manager.getActiveSessionCount()).toBe(1);
      
      vi.useRealTimers();
      await manager.cleanup();
    });

    it('should cleanup all sessions on shutdown', async () => {
      const session1 = await sessionManager.createSession();
      const session2 = await sessionManager.createSession();
      
      const cleanup1Spy = vi.spyOn(session1, 'cleanup').mockResolvedValue();
      const cleanup2Spy = vi.spyOn(session2, 'cleanup').mockResolvedValue();
      const storageCleanupSpy = vi.spyOn(mockStorage, 'cleanup').mockResolvedValue();
      
      await sessionManager.cleanup();
      
      expect(cleanup1Spy).toHaveBeenCalled();
      expect(cleanup2Spy).toHaveBeenCalled();
      expect(storageCleanupSpy).toHaveBeenCalled();
      expect(sessionManager.getActiveSessionCount()).toBe(0);
    });

    it('should handle session cleanup errors during shutdown', async () => {
      const session = await sessionManager.createSession();
      vi.spyOn(session, 'cleanup').mockRejectedValue(new Error('Cleanup error'));
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await sessionManager.cleanup();
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error cleaning up session'),
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });

    it('should emit cleanup events', async () => {
      const cleanedSpy = vi.fn();
      const managerCleanupSpy = vi.fn();
      
      sessionManager.on('sessions:cleaned', cleanedSpy);
      sessionManager.on('manager:cleanup', managerCleanupSpy);
      
      // Create expired session
      await sessionManager.createSession('test', { ttl: 10 });
      
      // Wait for expiration and trigger cleanup
      await new Promise(resolve => setTimeout(resolve, 50));
      
      await sessionManager.cleanup();
      
      expect(managerCleanupSpy).toHaveBeenCalled();
    });

    it('should remove event listeners on cleanup', async () => {
      const testListener = vi.fn();
      sessionManager.on('test-event', testListener);
      
      expect(sessionManager.listenerCount('test-event')).toBe(1);
      
      await sessionManager.cleanup();
      
      expect(sessionManager.listenerCount('test-event')).toBe(0);
    });
  });

  describe('Factory Function', () => {
    it('should create session manager using factory function', () => {
      const storage = new MockSessionStorage();
      const manager = createSessionManager(storage);
      
      expect(manager).toBeInstanceOf(DefaultSessionManager);
    });
  });

  describe('Error Recovery', () => {
    it('should handle storage cleanup errors', async () => {
      mockStorage.cleanup = vi.fn().mockRejectedValue(new Error('Cleanup failed'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await sessionManager.cleanup();
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error during final storage cleanup:',
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });

    it('should continue operation when periodic cleanup fails', async () => {
      vi.useFakeTimers();
      
      const cleanupSpy = vi.spyOn(mockStorage, 'cleanup')
        .mockRejectedValue(new Error('Periodic cleanup failed'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const manager = new DefaultSessionManager(mockStorage);
      
      // Trigger periodic cleanup
      vi.advanceTimersByTime(5 * 60 * 1000);
      await new Promise(resolve => setImmediate(resolve));
      
      // Should still be able to create sessions
      const session = await manager.createSession();
      expect(session).toBeDefined();
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error during scheduled cleanup:',
        expect.any(Error)
      );
      
      vi.useRealTimers();
      consoleSpy.mockRestore();
      await manager.cleanup();
    });
  });
});