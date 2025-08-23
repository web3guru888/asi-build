/**
 * Storage Abstraction Layer
 *
 * Provides unified storage interface for various backends (memory, file, database).
 */

import { EventEmitter } from 'eventemitter3';

export interface StorageAdapter extends EventEmitter {
  get(key: string): Promise<any>;
  set(key: string, value: any, ttl?: number): Promise<void>;
  delete(key: string): Promise<void>;
  list(prefix?: string): Promise<string[]>;
  clear(): Promise<void>;
  cleanup(): Promise<void>;
}

export class MemoryStorageAdapter
  extends EventEmitter
  implements StorageAdapter
{
  private readonly data = new Map<string, { value: any; expiresAt?: number }>();

  async get(key: string): Promise<any> {
    const item = this.data.get(key);
    if (!item) return undefined;

    if (item.expiresAt && Date.now() > item.expiresAt) {
      this.data.delete(key);
      return undefined;
    }

    return item.value;
  }

  async set(key: string, value: any, ttl?: number): Promise<void> {
    const expiresAt = ttl ? Date.now() + ttl : undefined;
    this.data.set(key, { value, expiresAt });
    this.emit('storage:set', { key });
  }

  async delete(key: string): Promise<void> {
    this.data.delete(key);
    this.emit('storage:delete', { key });
  }

  async list(prefix?: string): Promise<string[]> {
    const keys = Array.from(this.data.keys());
    return prefix ? keys.filter(k => k.startsWith(prefix)) : keys;
  }

  async clear(): Promise<void> {
    this.data.clear();
    this.emit('storage:cleared');
  }

  async cleanup(): Promise<void> {
    // Remove expired items
    const now = Date.now();
    for (const [key, item] of this.data.entries()) {
      if (item.expiresAt && now > item.expiresAt) {
        this.data.delete(key);
      }
    }
    this.removeAllListeners();
  }
}

export function createMemoryStorage(): StorageAdapter {
  return new MemoryStorageAdapter();
}
