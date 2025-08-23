/**
 * Kenny Integration Pattern - State Manager
 *
 * Provides global state management with watching, subscriptions,
 * persistence, and atomic updates for the Kenny integration system.
 */

import { EventEmitter } from 'eventemitter3';

// State change types
export interface StateChange<T = any> {
  id: string;
  timestamp: Date;
  path: string;
  oldValue: T;
  newValue: T;
  operation: 'set' | 'delete' | 'merge';
  source?: string;
}

// State watcher types
export interface StateWatcher {
  id: string;
  path: string | RegExp;
  callback: (change: StateChange) => void | Promise<void>;
  immediate?: boolean;
  deep?: boolean;
}

// State persistence options
export interface PersistenceOptions {
  key?: string;
  storage?: 'memory' | 'localStorage' | 'sessionStorage' | 'custom';
  customStorage?: {
    get: (key: string) => Promise<string | null>;
    set: (key: string, value: string) => Promise<void>;
    remove: (key: string) => Promise<void>;
  };
  debounceMs?: number;
}

// Atomic transaction types
export interface StateTransaction {
  id: string;
  operations: Array<{
    type: 'set' | 'delete' | 'merge';
    path: string;
    value?: any;
  }>;
  rollback: () => Promise<void>;
  commit: () => Promise<void>;
}

export class StateManager extends EventEmitter {
  private state: Record<string, any> = {};
  private readonly watchers = new Map<string, StateWatcher>();
  private changeHistory: StateChange[] = [];
  private readonly maxHistorySize = 500;
  private persistenceOptions: PersistenceOptions | null = null;
  private persistenceTimer: NodeJS.Timeout | null = null;
  private readonly transactions = new Map<string, StateTransaction>();

  constructor() {
    super();
  }

  /**
   * Initialize the state manager with optional persistence
   */
  async initialize(options?: {
    initialState?: Record<string, any>;
    persistence?: PersistenceOptions;
  }): Promise<void> {
    if (options?.initialState) {
      this.state = { ...options.initialState };
    }

    if (options?.persistence) {
      this.persistenceOptions = options.persistence;
      await this.loadPersistedState();
    }

    this.emit('initialized', { state: this.state });
  }

  /**
   * Get a value from the state by path
   */
  get<T = any>(path: string): T | undefined {
    return this.getValueByPath(this.state, path);
  }

  /**
   * Set a value in the state by path
   */
  async set<T = any>(path: string, value: T, source?: string): Promise<void> {
    const oldValue = this.get(path);

    if (oldValue === value) {
      return; // No change
    }

    this.setValueByPath(this.state, path, value);

    const change: StateChange<T> = {
      id: `chg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      path,
      oldValue,
      newValue: value,
      operation: 'set',
      source,
    };

    await this.processStateChange(change);
  }

  /**
   * Delete a value from the state by path
   */
  async delete(path: string, source?: string): Promise<void> {
    const oldValue = this.get(path);

    if (oldValue === undefined) {
      return; // Already doesn't exist
    }

    this.deleteValueByPath(this.state, path);

    const change: StateChange = {
      id: `chg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      path,
      oldValue,
      newValue: undefined,
      operation: 'delete',
      source,
    };

    await this.processStateChange(change);
  }

  /**
   * Merge an object into the state at the given path
   */
  async merge(
    path: string,
    value: Record<string, any>,
    source?: string
  ): Promise<void> {
    const oldValue = this.get(path);
    const newValue = { ...(oldValue || {}), ...value };

    this.setValueByPath(this.state, path, newValue);

    const change: StateChange = {
      id: `chg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      path,
      oldValue,
      newValue,
      operation: 'merge',
      source,
    };

    await this.processStateChange(change);
  }

  /**
   * Get the entire state
   */
  getState(): Record<string, any> {
    return JSON.parse(JSON.stringify(this.state));
  }

  /**
   * Replace the entire state
   */
  async setState(
    newState: Record<string, any>,
    source?: string
  ): Promise<void> {
    const oldState = this.getState();
    this.state = { ...newState };

    const change: StateChange = {
      id: `chg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      path: '',
      oldValue: oldState,
      newValue: newState,
      operation: 'set',
      source,
    };

    await this.processStateChange(change);
  }

  /**
   * Watch for changes to a specific path
   */
  watch(
    path: string | RegExp,
    callback: (change: StateChange) => void | Promise<void>,
    options: { immediate?: boolean; deep?: boolean } = {}
  ): string {
    const watcherId = `wtch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const watcher: StateWatcher = {
      id: watcherId,
      path,
      callback,
      immediate: options.immediate,
      deep: options.deep,
    };

    this.watchers.set(watcherId, watcher);

    // Call immediately if requested
    if (options.immediate && typeof path === 'string') {
      const currentValue = this.get(path);
      if (currentValue !== undefined) {
        const immediateChange: StateChange = {
          id: `imm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          path,
          oldValue: undefined,
          newValue: currentValue,
          operation: 'set',
          source: 'immediate',
        };
        setTimeout(() => callback(immediateChange), 0);
      }
    }

    return watcherId;
  }

  /**
   * Remove a watcher
   */
  unwatch(watcherId: string): boolean {
    return this.watchers.delete(watcherId);
  }

  /**
   * Start an atomic transaction
   */
  startTransaction(): StateTransaction {
    const transactionId = `txn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const snapshot = JSON.parse(JSON.stringify(this.state));
    const operations: StateTransaction['operations'] = [];

    const transaction: StateTransaction = {
      id: transactionId,
      operations,
      rollback: async () => {
        this.state = snapshot;
        this.transactions.delete(transactionId);

        const rollbackChange: StateChange = {
          id: `rb_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          path: '',
          oldValue: this.state,
          newValue: snapshot,
          operation: 'set',
          source: `transaction.rollback.${transactionId}`,
        };

        await this.processStateChange(rollbackChange);
      },
      commit: async () => {
        // Operations have already been applied to state
        this.transactions.delete(transactionId);

        const commitChange: StateChange = {
          id: `cm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date(),
          path: '',
          oldValue: snapshot,
          newValue: this.getState(),
          operation: 'set',
          source: `transaction.commit.${transactionId}`,
        };

        await this.processStateChange(commitChange);
      },
    };

    this.transactions.set(transactionId, transaction);
    return transaction;
  }

  /**
   * Get change history
   */
  getHistory(limit?: number): StateChange[] {
    if (limit && limit > 0) {
      return this.changeHistory.slice(-limit);
    }
    return [...this.changeHistory];
  }

  /**
   * Clear change history
   */
  clearHistory(): void {
    this.changeHistory = [];
  }

  /**
   * Get active watchers
   */
  getWatchers(): StateWatcher[] {
    return Array.from(this.watchers.values());
  }

  /**
   * Clear all watchers
   */
  clearWatchers(): void {
    this.watchers.clear();
  }

  /**
   * Process a state change and notify watchers
   */
  private async processStateChange(change: StateChange): Promise<void> {
    // Add to history
    this.changeHistory.push(change);
    if (this.changeHistory.length > this.maxHistorySize) {
      this.changeHistory = this.changeHistory.slice(-this.maxHistorySize);
    }

    // Notify watchers
    const matchingWatchers = Array.from(this.watchers.values()).filter(
      watcher => this.watcherMatches(watcher, change.path)
    );

    for (const watcher of matchingWatchers) {
      try {
        const result = watcher.callback(change);
        if (result instanceof Promise) {
          await result;
        }
      } catch (error) {
        console.error(`Error in state watcher ${watcher.id}:`, error);
        this.emit('watcher.error', { watcherId: watcher.id, change, error });
      }
    }

    // Emit change event
    this.emit('change', change);
    this.emit(`change:${change.path}`, change);

    // Trigger persistence
    await this.triggerPersistence();
  }

  /**
   * Check if a watcher matches a path
   */
  private watcherMatches(watcher: StateWatcher, path: string): boolean {
    if (typeof watcher.path === 'string') {
      return watcher.deep
        ? path.startsWith(watcher.path)
        : path === watcher.path;
    } else {
      return watcher.path.test(path);
    }
  }

  /**
   * Get a value by dot-separated path
   */
  private getValueByPath(obj: any, path: string): any {
    if (!path) return obj;

    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
      if (current === null || current === undefined) {
        return undefined;
      }
      current = current[key];
    }

    return current;
  }

  /**
   * Set a value by dot-separated path
   */
  private setValueByPath(obj: any, path: string, value: any): void {
    if (!path) return;

    const keys = path.split('.');
    const lastKey = keys.pop()!;

    let current = obj;
    for (const key of keys) {
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    current[lastKey] = value;
  }

  /**
   * Delete a value by dot-separated path
   */
  private deleteValueByPath(obj: any, path: string): void {
    if (!path) return;

    const keys = path.split('.');
    const lastKey = keys.pop()!;

    let current = obj;
    for (const key of keys) {
      if (!(key in current)) {
        return;
      }
      current = current[key];
    }

    delete current[lastKey];
  }

  /**
   * Load persisted state
   */
  private async loadPersistedState(): Promise<void> {
    if (!this.persistenceOptions) return;

    try {
      const key = this.persistenceOptions.key || 'kenny-state';
      let data: string | null = null;

      switch (this.persistenceOptions.storage) {
        case 'localStorage':
          if (typeof localStorage !== 'undefined') {
            data = localStorage.getItem(key);
          }
          break;
        case 'sessionStorage':
          if (typeof sessionStorage !== 'undefined') {
            data = sessionStorage.getItem(key);
          }
          break;
        case 'custom':
          if (this.persistenceOptions.customStorage) {
            data = await this.persistenceOptions.customStorage.get(key);
          }
          break;
        default:
          // Memory storage - no persistence
          break;
      }

      if (data) {
        const persistedState = JSON.parse(data);
        this.state = { ...this.state, ...persistedState };
      }
    } catch (error) {
      console.error('Failed to load persisted state:', error);
    }
  }

  /**
   * Trigger state persistence with debouncing
   */
  private async triggerPersistence(): Promise<void> {
    if (!this.persistenceOptions) return;

    const debounce = this.persistenceOptions.debounceMs || 1000;

    if (this.persistenceTimer) {
      clearTimeout(this.persistenceTimer);
    }

    this.persistenceTimer = setTimeout(async () => {
      await this.persistState();
      this.persistenceTimer = null;
    }, debounce);
  }

  /**
   * Persist the current state
   */
  private async persistState(): Promise<void> {
    if (!this.persistenceOptions) return;

    try {
      const key = this.persistenceOptions.key || 'kenny-state';
      const data = JSON.stringify(this.state);

      switch (this.persistenceOptions.storage) {
        case 'localStorage':
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem(key, data);
          }
          break;
        case 'sessionStorage':
          if (typeof sessionStorage !== 'undefined') {
            sessionStorage.setItem(key, data);
          }
          break;
        case 'custom':
          if (this.persistenceOptions.customStorage) {
            await this.persistenceOptions.customStorage.set(key, data);
          }
          break;
        default:
          // Memory storage - no persistence
          break;
      }
    } catch (error) {
      console.error('Failed to persist state:', error);
    }
  }
}

// Singleton instance
let stateManagerInstance: StateManager | null = null;

/**
 * Get the global state manager instance
 */
export function getStateManager(): StateManager {
  if (!stateManagerInstance) {
    stateManagerInstance = new StateManager();
  }
  return stateManagerInstance;
}

/**
 * Reset the global state manager instance (for testing)
 */
export function resetStateManager(): void {
  stateManagerInstance = null;
}
