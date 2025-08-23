/**
 * Mock Generators - Advanced mocking utilities for comprehensive testing
 */

import { vi } from 'vitest';
import { EventEmitter } from 'events';
import type { Mock } from 'vitest';

// =============================================================================
// FILE SYSTEM MOCKS
// =============================================================================

export class MockFileSystem {
  private files = new Map<string, string>();
  private directories = new Set<string>();

  constructor() {
    // Initialize with some default directories
    this.directories.add('/');
    this.directories.add('/tmp');
    this.directories.add('/home');
    this.directories.add('/usr');
  }

  // Mock fs/promises
  createMockFs() {
    return {
      readFile: vi.fn(async (path: string, encoding?: string) => {
        if (!this.files.has(path)) {
          throw new Error(`ENOENT: no such file or directory, open '${path}'`);
        }
        const content = this.files.get(path)!;
        return encoding === 'utf8' ? content : Buffer.from(content);
      }),

      writeFile: vi.fn(async (path: string, content: string) => {
        this.files.set(path, content);
      }),

      access: vi.fn(async (path: string) => {
        if (!this.files.has(path) && !this.directories.has(path)) {
          throw new Error(`ENOENT: no such file or directory, access '${path}'`);
        }
      }),

      stat: vi.fn(async (path: string) => {
        if (!this.files.has(path) && !this.directories.has(path)) {
          throw new Error(`ENOENT: no such file or directory, stat '${path}'`);
        }
        
        return {
          isFile: () => this.files.has(path),
          isDirectory: () => this.directories.has(path),
          size: this.files.get(path)?.length || 0,
          mtime: new Date(),
          ctime: new Date(),
          atime: new Date()
        };
      }),

      mkdir: vi.fn(async (path: string) => {
        this.directories.add(path);
      }),

      rmdir: vi.fn(async (path: string) => {
        this.directories.delete(path);
      }),

      unlink: vi.fn(async (path: string) => {
        if (!this.files.has(path)) {
          throw new Error(`ENOENT: no such file or directory, unlink '${path}'`);
        }
        this.files.delete(path);
      }),

      readdir: vi.fn(async (path: string) => {
        if (!this.directories.has(path)) {
          throw new Error(`ENOENT: no such file or directory, scandir '${path}'`);
        }
        
        const entries: string[] = [];
        
        // Add subdirectories
        for (const dir of this.directories) {
          if (dir.startsWith(path + '/') && dir !== path) {
            const relativePath = dir.substring(path.length + 1);
            if (!relativePath.includes('/')) {
              entries.push(relativePath);
            }
          }
        }
        
        // Add files
        for (const file of this.files.keys()) {
          if (file.startsWith(path + '/')) {
            const relativePath = file.substring(path.length + 1);
            if (!relativePath.includes('/')) {
              entries.push(relativePath);
            }
          }
        }
        
        return entries;
      })
    };
  }

  // Add files and directories for testing
  addFile(path: string, content: string) {
    this.files.set(path, content);
    // Ensure parent directories exist
    const parts = path.split('/');
    let currentPath = '';
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath += (i === 0 ? '' : '/') + parts[i];
      if (currentPath) {
        this.directories.add(currentPath);
      }
    }
  }

  addDirectory(path: string) {
    this.directories.add(path);
  }

  clear() {
    this.files.clear();
    this.directories.clear();
    this.directories.add('/');
  }

  getFiles() {
    return new Map(this.files);
  }

  getDirectories() {
    return new Set(this.directories);
  }
}

// =============================================================================
// DATABASE MOCKS
// =============================================================================

export class MockDatabase {
  private tables = new Map<string, any[]>();
  private queryLog: Array<{ query: string; params?: any[]; timestamp: Date }> = [];

  constructor() {
    this.createTable('users');
    this.createTable('sessions');
    this.createTable('messages');
    this.createTable('permissions');
  }

  createTable(tableName: string, initialData: any[] = []) {
    this.tables.set(tableName, [...initialData]);
  }

  createMockKnex() {
    const self = this;
    
    const mockQuery = {
      select: vi.fn().mockReturnThis(),
      where: vi.fn().mockReturnThis(),
      whereIn: vi.fn().mockReturnThis(),
      whereNot: vi.fn().mockReturnThis(),
      join: vi.fn().mockReturnThis(),
      leftJoin: vi.fn().mockReturnThis(),
      orderBy: vi.fn().mockReturnThis(),
      limit: vi.fn().mockReturnThis(),
      offset: vi.fn().mockReturnThis(),
      insert: vi.fn(async (data: any) => {
        const tableName = mockQuery._tableName || 'unknown';
        const table = self.tables.get(tableName) || [];
        const record = Array.isArray(data) ? data : [data];
        record.forEach(item => {
          if (!item.id) {
            item.id = `${tableName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          }
          table.push(item);
        });
        return record.map(r => r.id);
      }),
      update: vi.fn(async (data: any) => {
        return 1; // Affected rows
      }),
      del: vi.fn(async () => {
        return 1; // Affected rows
      }),
      first: vi.fn(async () => {
        const tableName = mockQuery._tableName || 'unknown';
        const table = self.tables.get(tableName) || [];
        return table[0] || null;
      }),
      then: vi.fn(async (callback: Function) => {
        const tableName = mockQuery._tableName || 'unknown';
        const table = self.tables.get(tableName) || [];
        return callback(table);
      }),
      _tableName: ''
    };

    const knex = vi.fn((tableName: string) => {
      mockQuery._tableName = tableName;
      return mockQuery;
    }) as any;

    // Add transaction support
    knex.transaction = vi.fn(async (callback: Function) => {
      return callback(knex);
    });

    // Add raw query support
    knex.raw = vi.fn(async (query: string, params?: any[]) => {
      self.queryLog.push({ query, params, timestamp: new Date() });
      return { rows: [] };
    });

    // Add schema builder
    knex.schema = {
      hasTable: vi.fn(async (tableName: string) => self.tables.has(tableName)),
      createTable: vi.fn(async (tableName: string, callback: Function) => {
        self.createTable(tableName);
        callback({
          increments: vi.fn(),
          string: vi.fn(),
          text: vi.fn(),
          integer: vi.fn(),
          boolean: vi.fn(),
          timestamp: vi.fn(),
          timestamps: vi.fn(),
          primary: vi.fn(),
          index: vi.fn(),
          foreign: vi.fn()
        });
      }),
      dropTable: vi.fn(async (tableName: string) => {
        self.tables.delete(tableName);
      })
    };

    return knex;
  }

  // Helper methods for testing
  insertData(tableName: string, data: any[]) {
    if (!this.tables.has(tableName)) {
      this.createTable(tableName);
    }
    this.tables.get(tableName)!.push(...data);
  }

  getData(tableName: string) {
    return this.tables.get(tableName) || [];
  }

  clearTable(tableName: string) {
    this.tables.set(tableName, []);
  }

  clearAll() {
    for (const tableName of this.tables.keys()) {
      this.clearTable(tableName);
    }
    this.queryLog = [];
  }

  getQueryLog() {
    return [...this.queryLog];
  }
}

// =============================================================================
// HTTP CLIENT MOCKS
// =============================================================================

export class MockHttpClient {
  private responses = new Map<string, any>();
  private requests: Array<{
    method: string;
    url: string;
    headers?: any;
    body?: any;
    timestamp: Date;
  }> = [];

  constructor() {
    this.setupDefaults();
  }

  setupDefaults() {
    // Default responses for common endpoints
    this.addResponse('GET', '/health', { status: 'ok', timestamp: new Date().toISOString() });
    this.addResponse('GET', '/api/status', { status: 'running', version: '1.0.0' });
  }

  addResponse(method: string, url: string, response: any, statusCode = 200) {
    const key = `${method.toUpperCase()} ${url}`;
    this.responses.set(key, { data: response, status: statusCode });
  }

  addErrorResponse(method: string, url: string, error: Error, statusCode = 500) {
    const key = `${method.toUpperCase()} ${url}`;
    this.responses.set(key, { error, status: statusCode });
  }

  createMockAxios() {
    const axios = vi.fn(async (config: any) => {
      const method = (config.method || 'GET').toUpperCase();
      const url = config.url;
      const key = `${method} ${url}`;
      
      // Log the request
      this.requests.push({
        method,
        url,
        headers: config.headers,
        body: config.data,
        timestamp: new Date()
      });

      // Find matching response
      const response = this.responses.get(key);
      if (!response) {
        throw new Error(`No mock response configured for ${key}`);
      }

      if (response.error) {
        throw response.error;
      }

      return {
        data: response.data,
        status: response.status,
        statusText: response.status === 200 ? 'OK' : 'Error',
        headers: { 'content-type': 'application/json' },
        config
      };
    }) as any;

    // Add convenience methods
    axios.get = vi.fn(async (url: string, config?: any) => 
      axios({ method: 'GET', url, ...config }));
    
    axios.post = vi.fn(async (url: string, data?: any, config?: any) => 
      axios({ method: 'POST', url, data, ...config }));
    
    axios.put = vi.fn(async (url: string, data?: any, config?: any) => 
      axios({ method: 'PUT', url, data, ...config }));
    
    axios.delete = vi.fn(async (url: string, config?: any) => 
      axios({ method: 'DELETE', url, ...config }));

    // Add interceptors support
    axios.interceptors = {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() }
    };

    return axios;
  }

  createMockFetch() {
    return vi.fn(async (url: string, options?: any) => {
      const method = (options?.method || 'GET').toUpperCase();
      const key = `${method} ${url}`;
      
      // Log the request
      this.requests.push({
        method,
        url,
        headers: options?.headers,
        body: options?.body,
        timestamp: new Date()
      });

      // Find matching response
      const response = this.responses.get(key);
      if (!response) {
        throw new Error(`No mock response configured for ${key}`);
      }

      if (response.error) {
        throw response.error;
      }

      return {
        ok: response.status >= 200 && response.status < 300,
        status: response.status,
        statusText: response.status === 200 ? 'OK' : 'Error',
        headers: new Map([['content-type', 'application/json']]),
        json: async () => response.data,
        text: async () => JSON.stringify(response.data),
        blob: async () => new Blob([JSON.stringify(response.data)]),
        arrayBuffer: async () => new ArrayBuffer(0)
      };
    });
  }

  getRequests() {
    return [...this.requests];
  }

  clearRequests() {
    this.requests = [];
  }

  getLastRequest() {
    return this.requests[this.requests.length - 1];
  }
}

// =============================================================================
// WEBSOCKET MOCKS
// =============================================================================

export class MockWebSocket extends EventEmitter {
  public readyState: number = 1; // OPEN
  public url: string;
  private messages: string[] = [];

  constructor(url: string) {
    super();
    this.url = url;
    
    // Simulate connection
    setTimeout(() => {
      this.emit('open');
    }, 10);
  }

  send(data: string) {
    this.messages.push(data);
    
    // Simulate echo response
    setTimeout(() => {
      this.emit('message', { data: `Echo: ${data}` });
    }, 10);
  }

  close(code?: number, reason?: string) {
    this.readyState = 3; // CLOSED
    this.emit('close', { code: code || 1000, reason: reason || 'Normal closure' });
  }

  // Simulate server message
  simulateMessage(data: string) {
    setTimeout(() => {
      this.emit('message', { data });
    }, 10);
  }

  // Simulate connection error
  simulateError(error: Error) {
    setTimeout(() => {
      this.emit('error', error);
    }, 10);
  }

  getMessages() {
    return [...this.messages];
  }

  static create() {
    return vi.fn((url: string) => new MockWebSocket(url));
  }
}

// =============================================================================
// PROCESS MOCKS
// =============================================================================

export class MockChildProcess extends EventEmitter {
  public stdout = new EventEmitter();
  public stderr = new EventEmitter();
  public stdin = {
    write: vi.fn(),
    end: vi.fn()
  };
  
  private killed = false;
  private exitCode: number | null = null;

  constructor(
    private command: string,
    private args: string[] = [],
    private options: any = {}
  ) {
    super();
  }

  kill(signal?: string) {
    this.killed = true;
    this.exitCode = signal === 'SIGKILL' ? 137 : 143;
    
    setTimeout(() => {
      this.emit('exit', this.exitCode, signal || 'SIGTERM');
    }, 10);
    
    return true;
  }

  // Simulate command execution
  simulateOutput(output: string, stream: 'stdout' | 'stderr' = 'stdout') {
    setTimeout(() => {
      this[stream].emit('data', output);
    }, 10);
  }

  simulateExit(code: number = 0, signal?: string) {
    this.exitCode = code;
    setTimeout(() => {
      this.emit('exit', code, signal);
    }, 50);
  }

  simulateError(error: Error) {
    setTimeout(() => {
      this.emit('error', error);
    }, 10);
  }

  static createSpawn() {
    return vi.fn((command: string, args?: string[], options?: any) => {
      return new MockChildProcess(command, args, options);
    });
  }

  static createExec() {
    return vi.fn((command: string, options?: any, callback?: Function) => {
      const proc = new MockChildProcess(command);
      
      if (callback) {
        setTimeout(() => {
          callback(null, 'Command output', '');
        }, 50);
      }
      
      return proc;
    });
  }
}

// =============================================================================
// TIMER MOCKS
// =============================================================================

export class MockTimers {
  private timers = new Map<number, {
    callback: Function;
    delay: number;
    interval: boolean;
    created: number;
  }>();
  
  private nextId = 1;
  private currentTime = Date.now();

  setTimeout(callback: Function, delay: number = 0) {
    const id = this.nextId++;
    this.timers.set(id, {
      callback,
      delay,
      interval: false,
      created: this.currentTime
    });
    return id;
  }

  setInterval(callback: Function, delay: number = 0) {
    const id = this.nextId++;
    this.timers.set(id, {
      callback,
      delay,
      interval: true,
      created: this.currentTime
    });
    return id;
  }

  clearTimeout(id: number) {
    this.timers.delete(id);
  }

  clearInterval(id: number) {
    this.timers.delete(id);
  }

  advanceTime(ms: number) {
    this.currentTime += ms;
    
    for (const [id, timer] of this.timers.entries()) {
      const elapsed = this.currentTime - timer.created;
      
      if (elapsed >= timer.delay) {
        timer.callback();
        
        if (timer.interval) {
          // Update creation time for next interval
          timer.created = this.currentTime;
        } else {
          // Remove one-time timers
          this.timers.delete(id);
        }
      }
    }
  }

  runAllTimers() {
    const maxTime = Math.max(...Array.from(this.timers.values()).map(t => t.delay));
    this.advanceTime(maxTime + 1);
  }

  getActiveTimers() {
    return Array.from(this.timers.keys());
  }

  clearAllTimers() {
    this.timers.clear();
  }
}

// =============================================================================
// ENVIRONMENT MOCKS
// =============================================================================

export class MockEnvironment {
  private originalEnv: Record<string, string | undefined>;
  private mockEnv: Record<string, string> = {};

  constructor() {
    this.originalEnv = { ...process.env };
  }

  set(key: string, value: string) {
    this.mockEnv[key] = value;
    process.env[key] = value;
  }

  unset(key: string) {
    delete this.mockEnv[key];
    delete process.env[key];
  }

  setMultiple(env: Record<string, string>) {
    Object.entries(env).forEach(([key, value]) => {
      this.set(key, value);
    });
  }

  restore() {
    // Clear all mock env vars
    Object.keys(this.mockEnv).forEach(key => {
      delete process.env[key];
    });
    
    // Restore original values
    Object.entries(this.originalEnv).forEach(([key, value]) => {
      if (value !== undefined) {
        process.env[key] = value;
      }
    });
    
    this.mockEnv = {};
  }

  createTestEnv() {
    return {
      NODE_ENV: 'test',
      LOG_LEVEL: 'error',
      DATABASE_URL: 'postgresql://test:test@localhost:5432/test_db',
      REDIS_URL: 'redis://localhost:6379/0',
      ANTHROPIC_API_KEY: 'test-anthropic-key',
      OPENAI_API_KEY: 'test-openai-key',
      JWT_SECRET: 'test-jwt-secret-very-long-and-secure',
      ENCRYPTION_KEY: 'test-encryption-key-32-chars-long',
      SESSION_SECRET: 'test-session-secret',
      CORS_ORIGIN: 'http://localhost:3000',
      RATE_LIMIT_WINDOW: '900000',
      RATE_LIMIT_MAX: '100'
    };
  }
}

// =============================================================================
// EXPORTS
// =============================================================================

export const Mocks = {
  FileSystem: MockFileSystem,
  Database: MockDatabase,
  HttpClient: MockHttpClient,
  WebSocket: MockWebSocket,
  ChildProcess: MockChildProcess,
  Timers: MockTimers,
  Environment: MockEnvironment
};

export default Mocks;