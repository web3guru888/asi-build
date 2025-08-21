/**
 * Unit tests for Kenny State Manager
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { StateManager, resetStateManager, getStateManager } from '../../../src/kenny/state-manager.js';
import type { StateChange, StateWatcher } from '../../../src/kenny/state-manager.js';

describe('StateManager', () => {
  let stateManager: StateManager;
  
  beforeEach(async () => {
    resetStateManager();
    stateManager = new StateManager();
    await stateManager.initialize();
  });
  
  afterEach(() => {
    stateManager.clearWatchers();
    stateManager.clearHistory();
  });

  describe('Initialization', () => {
    it('should initialize with empty state', async () => {
      const manager = new StateManager();
      await manager.initialize();
      
      expect(manager.getState()).toEqual({});
    });

    it('should initialize with provided state', async () => {
      const initialState = { user: { name: 'John' }, settings: { theme: 'dark' } };
      const manager = new StateManager();
      await manager.initialize({ initialState });
      
      expect(manager.getState()).toEqual(initialState);
    });

    it('should emit initialization event', async () => {
      const manager = new StateManager();
      const initSpy = vi.fn();
      manager.on('initialized', initSpy);
      
      await manager.initialize({ initialState: { test: true } });
      
      expect(initSpy).toHaveBeenCalledWith({ state: { test: true } });
    });
  });

  describe('Basic Operations', () => {
    describe('get/set', () => {
      it('should set and get simple values', async () => {
        await stateManager.set('name', 'John Doe');
        expect(stateManager.get('name')).toBe('John Doe');
      });

      it('should set and get nested values', async () => {
        await stateManager.set('user.profile.name', 'Alice');
        expect(stateManager.get('user.profile.name')).toBe('Alice');
        expect(stateManager.get('user')).toEqual({ profile: { name: 'Alice' } });
      });

      it('should return undefined for non-existent paths', () => {
        expect(stateManager.get('nonexistent')).toBeUndefined();
        expect(stateManager.get('user.nonexistent')).toBeUndefined();
      });

      it('should not emit change if value is the same', async () => {
        await stateManager.set('name', 'John');
        
        const changeSpy = vi.fn();
        stateManager.on('change', changeSpy);
        
        await stateManager.set('name', 'John');
        expect(changeSpy).not.toHaveBeenCalled();
      });

      it('should handle null and undefined values', async () => {
        await stateManager.set('nullValue', null);
        await stateManager.set('undefinedValue', undefined);
        
        expect(stateManager.get('nullValue')).toBeNull();
        expect(stateManager.get('undefinedValue')).toBeUndefined();
      });
    });

    describe('delete', () => {
      it('should delete existing values', async () => {
        await stateManager.set('user.name', 'John');
        await stateManager.set('user.age', 30);
        
        await stateManager.delete('user.name');
        
        expect(stateManager.get('user.name')).toBeUndefined();
        expect(stateManager.get('user.age')).toBe(30);
      });

      it('should not emit change if value does not exist', async () => {
        const changeSpy = vi.fn();
        stateManager.on('change', changeSpy);
        
        await stateManager.delete('nonexistent');
        expect(changeSpy).not.toHaveBeenCalled();
      });
    });

    describe('merge', () => {
      it('should merge objects', async () => {
        await stateManager.set('user', { name: 'John', age: 30 });
        await stateManager.merge('user', { age: 31, city: 'New York' });
        
        expect(stateManager.get('user')).toEqual({
          name: 'John',
          age: 31,
          city: 'New York'
        });
      });

      it('should merge into non-existent path', async () => {
        await stateManager.merge('newUser', { name: 'Alice', age: 25 });
        
        expect(stateManager.get('newUser')).toEqual({ name: 'Alice', age: 25 });
      });
    });

    describe('setState/getState', () => {
      it('should replace entire state', async () => {
        await stateManager.set('old', 'value');
        
        const newState = { new: 'state', user: { name: 'John' } };
        await stateManager.setState(newState);
        
        expect(stateManager.getState()).toEqual(newState);
        expect(stateManager.get('old')).toBeUndefined();
      });

      it('should return immutable state copy', () => {
        const state = stateManager.getState();
        state.modified = true;
        
        expect(stateManager.getState()).not.toHaveProperty('modified');
      });
    });
  });

  describe('Watchers', () => {
    it('should watch for changes to specific paths', async () => {
      const watcher = vi.fn();
      const watcherId = stateManager.watch('user.name', watcher);
      
      await stateManager.set('user.name', 'John');
      
      expect(watcher).toHaveBeenCalledOnce();
      const change = watcher.mock.calls[0][0] as StateChange;
      expect(change).toMatchObject({
        path: 'user.name',
        oldValue: undefined,
        newValue: 'John',
        operation: 'set'
      });
      
      expect(typeof watcherId).toBe('string');
      expect(watcherId).toMatch(/^wtch_\d+_/);
    });

    it('should watch with regex patterns', async () => {
      const watcher = vi.fn();
      stateManager.watch(/^user\./, watcher);
      
      await stateManager.set('user.name', 'John');
      await stateManager.set('user.age', 30);
      await stateManager.set('settings.theme', 'dark');
      
      expect(watcher).toHaveBeenCalledTimes(2);
    });

    it('should support deep watching', async () => {
      const watcher = vi.fn();
      stateManager.watch('user', watcher, { deep: true });
      
      await stateManager.set('user.name', 'John');
      await stateManager.set('user.profile.age', 30);
      await stateManager.set('other', 'value');
      
      expect(watcher).toHaveBeenCalledTimes(2);
    });

    it('should support immediate watching', async () => {
      await stateManager.set('existing', 'value');
      
      const watcher = vi.fn();
      stateManager.watch('existing', watcher, { immediate: true });
      
      // Should be called asynchronously
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(watcher).toHaveBeenCalledOnce();
      const change = watcher.mock.calls[0][0] as StateChange;
      expect(change.newValue).toBe('value');
      expect(change.source).toBe('immediate');
    });

    it('should remove watchers', async () => {
      const watcher = vi.fn();
      const watcherId = stateManager.watch('test', watcher);
      
      expect(stateManager.getWatchers()).toHaveLength(1);
      
      const removed = stateManager.unwatch(watcherId);
      expect(removed).toBe(true);
      expect(stateManager.getWatchers()).toHaveLength(0);
      
      await stateManager.set('test', 'value');
      expect(watcher).not.toHaveBeenCalled();
    });

    it('should handle async watchers', async () => {
      const asyncWatcher = vi.fn().mockResolvedValue(undefined);
      stateManager.watch('async', asyncWatcher);
      
      await stateManager.set('async', 'value');
      
      expect(asyncWatcher).toHaveBeenCalledOnce();
    });

    it('should handle watcher errors gracefully', async () => {
      const errorWatcher = vi.fn().mockImplementation(() => {
        throw new Error('Watcher error');
      });
      
      const errorSpy = vi.fn();
      stateManager.on('watcher.error', errorSpy);
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      stateManager.watch('error', errorWatcher);
      await stateManager.set('error', 'trigger');
      
      expect(errorWatcher).toHaveBeenCalled();
      expect(errorSpy).toHaveBeenCalledWith({
        watcherId: expect.stringMatching(/^wtch_\d+_/),
        change: expect.any(Object),
        error: expect.any(Error)
      });
      expect(consoleSpy).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });

    it('should clear all watchers', async () => {
      const watcher1 = vi.fn();
      const watcher2 = vi.fn();
      
      stateManager.watch('path1', watcher1);
      stateManager.watch('path2', watcher2);
      
      expect(stateManager.getWatchers()).toHaveLength(2);
      
      stateManager.clearWatchers();
      expect(stateManager.getWatchers()).toHaveLength(0);
      
      await stateManager.set('path1', 'value');
      expect(watcher1).not.toHaveBeenCalled();
      expect(watcher2).not.toHaveBeenCalled();
    });
  });

  describe('Transactions', () => {
    it('should create transactions', () => {
      const transaction = stateManager.startTransaction();
      
      expect(transaction).toMatchObject({
        id: expect.stringMatching(/^txn_\d+_/),
        operations: expect.any(Array),
        rollback: expect.any(Function),
        commit: expect.any(Function)
      });
    });

    it('should rollback transactions', async () => {
      await stateManager.set('counter', 5);
      
      const transaction = stateManager.startTransaction();
      
      await stateManager.set('counter', 10);
      await stateManager.set('name', 'John');
      
      expect(stateManager.get('counter')).toBe(10);
      expect(stateManager.get('name')).toBe('John');
      
      await transaction.rollback();
      
      expect(stateManager.get('counter')).toBe(5);
      expect(stateManager.get('name')).toBeUndefined();
    });

    it('should commit transactions', async () => {
      await stateManager.set('counter', 5);
      
      const changeSpy = vi.fn();
      stateManager.on('change', changeSpy);
      
      const transaction = stateManager.startTransaction();
      
      await stateManager.set('counter', 10);
      
      // Clear spy to focus on commit event
      changeSpy.mockClear();
      
      await transaction.commit();
      
      expect(stateManager.get('counter')).toBe(10);
      expect(changeSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          source: expect.stringContaining('transaction.commit.')
        })
      );
    });
  });

  describe('Change History', () => {
    it('should track change history', async () => {
      await stateManager.set('name', 'John');
      await stateManager.set('age', 30);
      await stateManager.delete('name');
      
      const history = stateManager.getHistory();
      
      expect(history).toHaveLength(3);
      expect(history[0]).toMatchObject({
        path: 'name',
        operation: 'set',
        newValue: 'John'
      });
      expect(history[1]).toMatchObject({
        path: 'age',
        operation: 'set',
        newValue: 30
      });
      expect(history[2]).toMatchObject({
        path: 'name',
        operation: 'delete',
        oldValue: 'John'
      });
    });

    it('should limit history size', async () => {
      // Access private property for testing
      (stateManager as any).maxHistorySize = 3;
      
      for (let i = 0; i < 5; i++) {
        await stateManager.set(`key${i}`, i);
      }
      
      const history = stateManager.getHistory();
      expect(history).toHaveLength(3);
      expect(history.map(h => h.newValue)).toEqual([2, 3, 4]);
    });

    it('should get limited history', async () => {
      await stateManager.set('a', 1);
      await stateManager.set('b', 2);
      await stateManager.set('c', 3);
      
      const limitedHistory = stateManager.getHistory(2);
      expect(limitedHistory).toHaveLength(2);
      expect(limitedHistory.map(h => h.newValue)).toEqual([2, 3]);
    });

    it('should clear history', async () => {
      await stateManager.set('test', 'value');
      expect(stateManager.getHistory()).toHaveLength(1);
      
      stateManager.clearHistory();
      expect(stateManager.getHistory()).toHaveLength(0);
    });
  });

  describe('Events', () => {
    it('should emit change events', async () => {
      const changeSpy = vi.fn();
      const pathChangeSpy = vi.fn();
      
      stateManager.on('change', changeSpy);
      stateManager.on('change:user.name', pathChangeSpy);
      
      await stateManager.set('user.name', 'John');
      
      expect(changeSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          path: 'user.name',
          newValue: 'John'
        })
      );
      
      expect(pathChangeSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          path: 'user.name',
          newValue: 'John'
        })
      );
    });

    it('should include source in changes', async () => {
      const changeSpy = vi.fn();
      stateManager.on('change', changeSpy);
      
      await stateManager.set('test', 'value', 'test-source');
      
      const change = changeSpy.mock.calls[0][0] as StateChange;
      expect(change.source).toBe('test-source');
    });
  });

  describe('Singleton Pattern', () => {
    it('should return same instance from getStateManager', () => {
      const instance1 = getStateManager();
      const instance2 = getStateManager();
      
      expect(instance1).toBe(instance2);
    });

    it('should reset singleton instance', () => {
      const instance1 = getStateManager();
      resetStateManager();
      const instance2 = getStateManager();
      
      expect(instance1).not.toBe(instance2);
    });
  });

  describe('Path Utilities', () => {
    it('should handle empty paths', async () => {
      await stateManager.set('', { root: 'value' });
      expect(stateManager.get('')).toEqual({ root: 'value' });
    });

    it('should handle complex nested paths', async () => {
      await stateManager.set('a.b.c.d.e', 'deep value');
      expect(stateManager.get('a.b.c.d.e')).toBe('deep value');
      expect(stateManager.get('a.b.c')).toEqual({ d: { e: 'deep value' } });
    });

    it('should overwrite non-object intermediate values', async () => {
      await stateManager.set('path', 'string value');
      await stateManager.set('path.nested', 'nested value');
      
      expect(stateManager.get('path')).toEqual({ nested: 'nested value' });
    });

    it('should handle array indices in paths', async () => {
      await stateManager.set('users.0.name', 'First User');
      await stateManager.set('users.1.name', 'Second User');
      
      expect(stateManager.get('users')).toEqual({
        0: { name: 'First User' },
        1: { name: 'Second User' }
      });
    });
  });

  describe('Persistence', () => {
    it('should initialize with custom storage', async () => {
      const mockStorage = {
        get: vi.fn().mockResolvedValue('{"persisted": "data"}'),
        set: vi.fn().mockResolvedValue(undefined),
        remove: vi.fn().mockResolvedValue(undefined)
      };
      
      const manager = new StateManager();
      await manager.initialize({
        initialState: { initial: 'state' },
        persistence: {
          storage: 'custom',
          customStorage: mockStorage,
          key: 'test-key'
        }
      });
      
      expect(mockStorage.get).toHaveBeenCalledWith('test-key');
      expect(manager.get('persisted')).toBe('data');
      expect(manager.get('initial')).toBe('state');
    });

    it('should handle persistence errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const mockStorage = {
        get: vi.fn().mockRejectedValue(new Error('Storage error')),
        set: vi.fn().mockResolvedValue(undefined),
        remove: vi.fn().mockResolvedValue(undefined)
      };
      
      const manager = new StateManager();
      await manager.initialize({
        persistence: {
          storage: 'custom',
          customStorage: mockStorage
        }
      });
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to load persisted state:', expect.any(Error));
      
      consoleSpy.mockRestore();
    });

    it('should debounce persistence writes', async () => {
      vi.useFakeTimers();
      
      const mockStorage = {
        get: vi.fn().mockResolvedValue(null),
        set: vi.fn().mockResolvedValue(undefined),
        remove: vi.fn().mockResolvedValue(undefined)
      };
      
      const manager = new StateManager();
      await manager.initialize({
        persistence: {
          storage: 'custom',
          customStorage: mockStorage,
          debounceMs: 500
        }
      });
      
      await manager.set('key1', 'value1');
      await manager.set('key2', 'value2');
      await manager.set('key3', 'value3');
      
      // Should not have persisted yet due to debouncing
      expect(mockStorage.set).not.toHaveBeenCalled();
      
      // Fast forward through debounce period
      vi.advanceTimersByTime(500);
      await Promise.resolve(); // Allow async operations to complete
      
      // Should now have persisted once
      expect(mockStorage.set).toHaveBeenCalledOnce();
      
      vi.useRealTimers();
    });
  });
});