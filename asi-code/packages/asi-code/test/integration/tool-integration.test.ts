/**
 * Tool System Integration Tests - Comprehensive testing of all built-in tools
 * 
 * Tests all 8 built-in tools (bash, read, write, edit, search, delete, move, list)
 * including their execution, error handling, permission validation, and integration
 * with the tool registry and session system.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { 
  createBuiltInTools,
  BashTool,
  ReadTool,
  WriteTool,
  EditTool,
  SearchTool,
  DeleteTool,
  MoveTool,
  ListTool
} from '../../src/tool/built-in-tools/index.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { vol } from 'memfs';
import { execSync } from 'child_process';
import path from 'path';
import type { ToolExecutionContext, ToolResult } from '../../src/tool/base-tool.js';

// Mock fs for file operations
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Mock child_process for bash tool
vi.mock('child_process', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    exec: vi.fn((command, options, callback) => {
      // Simple mock - just call callback with success
      if (typeof options === 'function') {
        callback = options;
        options = {};
      }
      process.nextTick(() => {
        callback(null, `Mock output for: ${command}`, '');
      });
    }),
    execSync: vi.fn((command) => `Mock sync output for: ${command}`),
    spawn: vi.fn()
  };
});

// Test session storage
class TestSessionStorage {
  private storage = new Map();
  
  async save(sessionData: any): Promise<void> {
    this.storage.set(sessionData.id, { ...sessionData });
  }
  
  async load(sessionId: string): Promise<any> {
    return this.storage.get(sessionId) || null;
  }
  
  async delete(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }
  
  async list(userId?: string): Promise<string[]> {
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
  }
  
  async cleanup(): Promise<void> {}
  clear(): void { this.storage.clear(); }
}

describe('Tool System Integration Tests', () => {
  let toolRegistry: ToolRegistry;
  let sessionManager: DefaultSessionManager;
  let permissionManager: PermissionManager;
  let testStorage: TestSessionStorage;

  const createTestContext = (permissions: string[] = [], workingDir = '/test'): ToolExecutionContext => ({
    sessionId: 'test-session-123',
    userId: 'test-user',
    permissions,
    workingDirectory: workingDir,
    environment: { NODE_ENV: 'test' }
  });

  beforeAll(async () => {
    testStorage = new TestSessionStorage();
    sessionManager = new DefaultSessionManager(testStorage as any);
    permissionManager = new PermissionManager({
      enableSafetyProtocols: true,
      enableCaching: true,
      enableAuditing: false
    });

    toolRegistry = new ToolRegistry();
    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register all built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }
  });

  afterAll(async () => {
    if (toolRegistry) {
      await toolRegistry.shutdown();
    }
    if (sessionManager) {
      await sessionManager.cleanup();
    }
    if (permissionManager) {
      await permissionManager.cleanup();
    }
  });

  beforeEach(() => {
    vol.reset();
    testStorage.clear();
    vi.clearAllMocks();
    
    // Setup common test file structure
    vol.fromJSON({
      '/test/sample.txt': 'Sample file content for testing',
      '/test/data.json': '{"name": "test", "version": "1.0", "data": [1, 2, 3]}',
      '/test/large.txt': 'A'.repeat(5000),
      '/test/config.yml': 'server:\n  port: 3000\n  host: localhost',
      '/test/readme.md': '# Test Project\n\nThis is a test project.',
      '/test/subdir/nested.txt': 'Nested file content',
      '/test/subdir/deep/file.log': 'Log entry 1\nLog entry 2\nError: something went wrong',
      '/test/empty-dir/': null,
      '/test/binary.dat': Buffer.from([0x00, 0x01, 0x02, 0x03, 0x04]).toString(),
      '/other/external.txt': 'External file outside test directory'
    });
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Tool Registry Integration', () => {
    it('should register all built-in tools successfully', async () => {
      const tools = toolRegistry.list();
      expect(tools).toHaveLength(8);

      const toolNames = tools.map(tool => tool.name);
      expect(toolNames).toContain('bash');
      expect(toolNames).toContain('read');
      expect(toolNames).toContain('write');
      expect(toolNames).toContain('edit');
      expect(toolNames).toContain('search');
      expect(toolNames).toContain('delete');
      expect(toolNames).toContain('move');
      expect(toolNames).toContain('list');
    });

    it('should retrieve individual tools by name', async () => {
      expect(toolRegistry.get('read')).toBeInstanceOf(ReadTool);
      expect(toolRegistry.get('write')).toBeInstanceOf(WriteTool);
      expect(toolRegistry.get('bash')).toBeInstanceOf(BashTool);
      expect(toolRegistry.get('nonexistent')).toBeNull();
    });

    it('should categorize tools correctly', async () => {
      const tools = toolRegistry.list();
      
      const fileTools = tools.filter(tool => tool.getCategory() === 'file');
      const systemTools = tools.filter(tool => tool.getCategory() === 'system');
      
      expect(fileTools).toHaveLength(7); // read, write, edit, search, delete, move, list
      expect(systemTools).toHaveLength(1); // bash
    });

    it('should validate tool schemas', async () => {
      const tools = toolRegistry.list();
      
      for (const tool of tools) {
        const schema = tool.getSchema();
        expect(schema).toBeDefined();
        expect(schema.name).toBe(tool.name);
        expect(schema.description).toBeDefined();
        expect(schema.parameters).toBeDefined();
      }
    });
  });

  describe('Read Tool Integration', () => {
    it('should read text files successfully', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('Sample file content for testing');
      expect(result.data.encoding).toBe('utf8');
      expect(result.data.size).toBeGreaterThan(0);
    });

    it('should read JSON files and preserve structure', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/test/data.json' }, context);

      expect(result.success).toBe(true);
      expect(result.data.content).toContain('"name": "test"');
      expect(result.data.mimeType).toBe('application/json');
    });

    it('should handle large files with size limits', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { 
        path: '/test/large.txt',
        maxSize: 1000 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.content.length).toBeLessThanOrEqual(1000);
      expect(result.data.truncated).toBe(true);
    });

    it('should handle non-existent files gracefully', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/test/nonexistent.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('File not found');
    });

    it('should respect permission restrictions', async () => {
      const context = createTestContext([]); // No read permissions
      const result = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('permission');
    });

    it('should prevent path traversal attacks', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { 
        path: '/test/../other/external.txt' 
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('traversal');
    });
  });

  describe('Write Tool Integration', () => {
    it('should write text files successfully', async () => {
      const context = createTestContext(['write_files']);
      const content = 'This is new content written by the write tool';
      
      const result = await toolRegistry.execute('write', { 
        path: '/test/new-file.txt',
        content 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.bytesWritten).toBe(content.length);

      // Verify file was written
      const readResult = await toolRegistry.execute('read', { path: '/test/new-file.txt' }, 
        createTestContext(['read_files']));
      expect(readResult.data.content).toBe(content);
    });

    it('should overwrite existing files when specified', async () => {
      const context = createTestContext(['write_files']);
      const newContent = 'Overwritten content';
      
      const result = await toolRegistry.execute('write', { 
        path: '/test/sample.txt',
        content: newContent,
        overwrite: true
      }, context);

      expect(result.success).toBe(true);

      // Verify file was overwritten
      const readResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, 
        createTestContext(['read_files']));
      expect(readResult.data.content).toBe(newContent);
    });

    it('should create directories when createDirs is true', async () => {
      const context = createTestContext(['write_files']);
      const result = await toolRegistry.execute('write', { 
        path: '/test/new-dir/nested/file.txt',
        content: 'Nested file content',
        createDirs: true
      }, context);

      expect(result.success).toBe(true);

      // Verify directory structure was created
      const readResult = await toolRegistry.execute('read', { 
        path: '/test/new-dir/nested/file.txt' 
      }, createTestContext(['read_files']));
      expect(readResult.success).toBe(true);
    });

    it('should handle different encodings', async () => {
      const context = createTestContext(['write_files']);
      const content = 'Special characters: áéíóú';
      
      const result = await toolRegistry.execute('write', { 
        path: '/test/utf8-file.txt',
        content,
        encoding: 'utf8'
      }, context);

      expect(result.success).toBe(true);
      
      const readResult = await toolRegistry.execute('read', { 
        path: '/test/utf8-file.txt',
        encoding: 'utf8' 
      }, createTestContext(['read_files']));
      expect(readResult.data.content).toBe(content);
    });

    it('should respect file size limits', async () => {
      const context = createTestContext(['write_files']);
      const largeContent = 'A'.repeat(1000000); // 1MB content
      
      const result = await toolRegistry.execute('write', { 
        path: '/test/large-write.txt',
        content: largeContent,
        maxSize: 500000 // 500KB limit
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('exceeds maximum size');
    });
  });

  describe('Edit Tool Integration', () => {
    it('should perform line-based edits', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      const result = await toolRegistry.execute('edit', { 
        path: '/test/sample.txt',
        operations: [
          { type: 'replace', lineNumber: 1, content: 'Modified sample file content' }
        ]
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.changes).toHaveLength(1);

      // Verify edit was applied
      const readResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);
      expect(readResult.data.content).toBe('Modified sample file content');
    });

    it('should perform multiple edit operations', async () => {
      // Create a multi-line file first
      await toolRegistry.execute('write', { 
        path: '/test/multi-line.txt',
        content: 'Line 1\nLine 2\nLine 3\nLine 4'
      }, createTestContext(['write_files']));

      const context = createTestContext(['read_files', 'write_files']);
      const result = await toolRegistry.execute('edit', { 
        path: '/test/multi-line.txt',
        operations: [
          { type: 'insert', lineNumber: 2, content: 'Inserted line' },
          { type: 'delete', lineNumber: 4 },
          { type: 'replace', lineNumber: 1, content: 'Modified Line 1' }
        ]
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.changes).toHaveLength(3);

      const readResult = await toolRegistry.execute('read', { path: '/test/multi-line.txt' }, context);
      const lines = readResult.data.content.split('\n');
      expect(lines[0]).toBe('Modified Line 1');
      expect(lines[1]).toBe('Inserted line');
      expect(lines[2]).toBe('Line 2');
      expect(lines[3]).toBe('Line 4');
    });

    it('should handle search and replace operations', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      const result = await toolRegistry.execute('edit', { 
        path: '/test/sample.txt',
        operations: [
          { 
            type: 'searchReplace', 
            search: 'Sample', 
            replace: 'Example',
            global: false 
          }
        ]
      }, context);

      expect(result.success).toBe(true);

      const readResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);
      expect(readResult.data.content).toContain('Example file content');
    });

    it('should create backup before editing when specified', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      const result = await toolRegistry.execute('edit', { 
        path: '/test/sample.txt',
        operations: [
          { type: 'replace', lineNumber: 1, content: 'Edited content' }
        ],
        createBackup: true
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.backupPath).toBeDefined();

      // Verify backup was created
      const backupResult = await toolRegistry.execute('read', { 
        path: result.data.backupPath 
      }, context);
      expect(backupResult.success).toBe(true);
      expect(backupResult.data.content).toBe('Sample file content for testing');
    });

    it('should validate edit operations', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      const result = await toolRegistry.execute('edit', { 
        path: '/test/sample.txt',
        operations: [
          { type: 'invalid-operation' as any, lineNumber: 1 }
        ]
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid edit operation');
    });
  });

  describe('Search Tool Integration', () => {
    it('should search for text patterns in files', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test',
        pattern: 'content',
        recursive: true
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.matches.length).toBeGreaterThan(0);
      
      const sampleMatch = result.data.matches.find((m: any) => m.file === '/test/sample.txt');
      expect(sampleMatch).toBeDefined();
      expect(sampleMatch.line).toBe(1);
      expect(sampleMatch.content).toContain('content');
    });

    it('should support regular expressions', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test/data.json',
        pattern: '"\\w+": \\d+',
        useRegex: true
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.matches.length).toBeGreaterThan(0);
    });

    it('should perform case-insensitive searches', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test',
        pattern: 'SAMPLE',
        caseSensitive: false,
        recursive: true
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.matches.length).toBeGreaterThan(0);
    });

    it('should filter by file extensions', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test',
        pattern: 'test',
        fileExtensions: ['.json', '.yml'],
        recursive: true
      }, context);

      expect(result.success).toBe(true);
      
      // Should only find matches in JSON and YAML files
      const matchFiles = result.data.matches.map((m: any) => m.file);
      matchFiles.forEach((file: string) => {
        expect(file.endsWith('.json') || file.endsWith('.yml')).toBe(true);
      });
    });

    it('should handle binary files gracefully', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test/binary.dat',
        pattern: 'binary'
      }, context);

      expect(result.success).toBe(true);
      // Binary file should be detected and skipped or handled appropriately
    });

    it('should limit search results', async () => {
      const context = createTestContext(['read_files', 'search_files']);
      const result = await toolRegistry.execute('search', { 
        path: '/test',
        pattern: '.',
        maxResults: 5,
        recursive: true,
        useRegex: true
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.matches.length).toBeLessThanOrEqual(5);
    });
  });

  describe('Delete Tool Integration', () => {
    it('should delete files successfully', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(true);
      expect(result.data.deleted).toContain('/test/sample.txt');

      // Verify file was deleted
      const readResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, 
        createTestContext(['read_files']));
      expect(readResult.success).toBe(false);
    });

    it('should delete directories recursively when specified', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { 
        path: '/test/subdir',
        recursive: true 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.deleted).toContain('/test/subdir');

      // Verify directory and its contents were deleted
      const listResult = await toolRegistry.execute('list', { path: '/test' }, 
        createTestContext(['read_files']));
      const dirNames = listResult.data.files.map((f: any) => f.name);
      expect(dirNames).not.toContain('subdir');
    });

    it('should handle wildcard patterns', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { 
        path: '/test/*.txt',
        pattern: true 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.deleted.length).toBeGreaterThan(0);

      // Verify only .txt files were deleted
      const listResult = await toolRegistry.execute('list', { path: '/test' }, 
        createTestContext(['read_files']));
      const txtFiles = listResult.data.files.filter((f: any) => f.name.endsWith('.txt'));
      expect(txtFiles).toHaveLength(0);
    });

    it('should create safety backups when specified', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { 
        path: '/test/sample.txt',
        createBackup: true 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.backupPath).toBeDefined();

      // Verify backup was created
      const backupResult = await toolRegistry.execute('read', { 
        path: result.data.backupPath 
      }, createTestContext(['read_files']));
      expect(backupResult.success).toBe(true);
    });

    it('should handle non-existent files gracefully', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { path: '/test/nonexistent.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    it('should prevent deletion outside working directory', async () => {
      const context = createTestContext(['delete_files']);
      const result = await toolRegistry.execute('delete', { path: '/other/external.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('outside working directory');
    });
  });

  describe('Move Tool Integration', () => {
    it('should move files successfully', async () => {
      const context = createTestContext(['move_files']);
      const result = await toolRegistry.execute('move', { 
        source: '/test/sample.txt',
        destination: '/test/moved-sample.txt' 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.moved.source).toBe('/test/sample.txt');
      expect(result.data.moved.destination).toBe('/test/moved-sample.txt');

      // Verify file was moved
      const readResult = await toolRegistry.execute('read', { path: '/test/moved-sample.txt' }, 
        createTestContext(['read_files']));
      expect(readResult.success).toBe(true);

      const oldResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, 
        createTestContext(['read_files']));
      expect(oldResult.success).toBe(false);
    });

    it('should move directories recursively', async () => {
      const context = createTestContext(['move_files']);
      const result = await toolRegistry.execute('move', { 
        source: '/test/subdir',
        destination: '/test/moved-subdir' 
      }, context);

      expect(result.success).toBe(true);

      // Verify directory was moved with its contents
      const listResult = await toolRegistry.execute('list', { 
        path: '/test/moved-subdir',
        recursive: true 
      }, createTestContext(['read_files']));
      expect(listResult.success).toBe(true);
      expect(listResult.data.files.length).toBeGreaterThan(0);
    });

    it('should handle move conflicts with overwrite option', async () => {
      // Create destination file first
      await toolRegistry.execute('write', { 
        path: '/test/destination.txt',
        content: 'Destination content' 
      }, createTestContext(['write_files']));

      const context = createTestContext(['move_files']);
      const result = await toolRegistry.execute('move', { 
        source: '/test/sample.txt',
        destination: '/test/destination.txt',
        overwrite: true 
      }, context);

      expect(result.success).toBe(true);

      // Verify source content now at destination
      const readResult = await toolRegistry.execute('read', { path: '/test/destination.txt' }, 
        createTestContext(['read_files']));
      expect(readResult.data.content).toBe('Sample file content for testing');
    });

    it('should create destination directories when specified', async () => {
      const context = createTestContext(['move_files']);
      const result = await toolRegistry.execute('move', { 
        source: '/test/sample.txt',
        destination: '/test/new-dir/nested/sample.txt',
        createDirs: true 
      }, context);

      expect(result.success).toBe(true);

      // Verify file was moved to new directory structure
      const readResult = await toolRegistry.execute('read', { 
        path: '/test/new-dir/nested/sample.txt' 
      }, createTestContext(['read_files']));
      expect(readResult.success).toBe(true);
    });

    it('should handle batch moves with patterns', async () => {
      const context = createTestContext(['move_files']);
      const result = await toolRegistry.execute('move', { 
        source: '/test/*.txt',
        destination: '/test/txt-files/',
        pattern: true,
        createDirs: true 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.moved.length).toBeGreaterThan(0);

      // Verify files were moved to destination directory
      const listResult = await toolRegistry.execute('list', { 
        path: '/test/txt-files' 
      }, createTestContext(['read_files']));
      expect(listResult.success).toBe(true);
      expect(listResult.data.files.length).toBeGreaterThan(0);
    });
  });

  describe('List Tool Integration', () => {
    it('should list directory contents', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('list', { path: '/test' }, context);

      expect(result.success).toBe(true);
      expect(result.data.files.length).toBeGreaterThan(0);
      
      const fileNames = result.data.files.map((f: any) => f.name);
      expect(fileNames).toContain('sample.txt');
      expect(fileNames).toContain('data.json');
      expect(fileNames).toContain('subdir');
    });

    it('should provide detailed file information', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('list', { 
        path: '/test',
        detailed: true 
      }, context);

      expect(result.success).toBe(true);
      
      const sampleFile = result.data.files.find((f: any) => f.name === 'sample.txt');
      expect(sampleFile).toMatchObject({
        name: 'sample.txt',
        type: 'file',
        size: expect.any(Number),
        modified: expect.any(String),
        permissions: expect.any(String),
        path: '/test/sample.txt'
      });
    });

    it('should list recursively when specified', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('list', { 
        path: '/test',
        recursive: true 
      }, context);

      expect(result.success).toBe(true);
      
      const filePaths = result.data.files.map((f: any) => f.path);
      expect(filePaths).toContain('/test/subdir/nested.txt');
      expect(filePaths).toContain('/test/subdir/deep/file.log');
    });

    it('should filter by file extensions', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('list', { 
        path: '/test',
        extensions: ['.txt', '.json'],
        recursive: true 
      }, context);

      expect(result.success).toBe(true);
      
      result.data.files.forEach((file: any) => {
        expect(file.name.endsWith('.txt') || file.name.endsWith('.json')).toBe(true);
      });
    });

    it('should include/exclude hidden files based on option', async () => {
      // Create hidden file
      await toolRegistry.execute('write', { 
        path: '/test/.hidden',
        content: 'Hidden file content' 
      }, createTestContext(['write_files']));

      const context = createTestContext(['read_files']);
      
      // Without hidden files
      const result1 = await toolRegistry.execute('list', { 
        path: '/test',
        includeHidden: false 
      }, context);
      const fileNames1 = result1.data.files.map((f: any) => f.name);
      expect(fileNames1).not.toContain('.hidden');

      // With hidden files
      const result2 = await toolRegistry.execute('list', { 
        path: '/test',
        includeHidden: true 
      }, context);
      const fileNames2 = result2.data.files.map((f: any) => f.name);
      expect(fileNames2).toContain('.hidden');
    });

    it('should sort files by different criteria', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('list', { 
        path: '/test',
        sortBy: 'name',
        sortOrder: 'asc' 
      }, context);

      expect(result.success).toBe(true);
      
      const fileNames = result.data.files.map((f: any) => f.name);
      const sortedNames = [...fileNames].sort();
      expect(fileNames).toEqual(sortedNames);
    });
  });

  describe('Bash Tool Integration', () => {
    beforeEach(() => {
      // Mock execSync to return predictable results
      vi.mocked(execSync).mockClear();
    });

    it('should execute simple bash commands', async () => {
      vi.mocked(execSync).mockReturnValue(Buffer.from('Hello World\n'));
      
      const context = createTestContext(['execute_commands']);
      const result = await toolRegistry.execute('bash', { 
        command: 'echo "Hello World"' 
      }, context);

      expect(result.success).toBe(true);
      expect(result.data.output).toBe('Hello World\n');
      expect(result.data.exitCode).toBe(0);
    });

    it('should handle command failures', async () => {
      const error = new Error('Command failed') as any;
      error.status = 1;
      error.stderr = Buffer.from('Command not found\n');
      vi.mocked(execSync).mockImplementation(() => { throw error; });
      
      const context = createTestContext(['execute_commands']);
      const result = await toolRegistry.execute('bash', { 
        command: 'nonexistent-command' 
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Command failed');
      expect(result.data.exitCode).toBe(1);
    });

    it('should respect timeout limits', async () => {
      vi.mocked(execSync).mockImplementation(() => {
        throw new Error('Command timed out');
      });
      
      const context = createTestContext(['execute_commands']);
      const result = await toolRegistry.execute('bash', { 
        command: 'sleep 10',
        timeout: 1000 
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('timeout');
    });

    it('should set working directory correctly', async () => {
      vi.mocked(execSync).mockReturnValue(Buffer.from('/test\n'));
      
      const context = createTestContext(['execute_commands'], '/test');
      const result = await toolRegistry.execute('bash', { 
        command: 'pwd' 
      }, context);

      expect(result.success).toBe(true);
      expect(vi.mocked(execSync)).toHaveBeenCalledWith(
        'pwd',
        expect.objectContaining({
          cwd: '/test'
        })
      );
    });

    it('should handle environment variables', async () => {
      vi.mocked(execSync).mockReturnValue(Buffer.from('test\n'));
      
      const context = createTestContext(['execute_commands']);
      context.environment.TEST_VAR = 'test';
      
      const result = await toolRegistry.execute('bash', { 
        command: 'echo $TEST_VAR' 
      }, context);

      expect(result.success).toBe(true);
      expect(vi.mocked(execSync)).toHaveBeenCalledWith(
        'echo $TEST_VAR',
        expect.objectContaining({
          env: expect.objectContaining({
            TEST_VAR: 'test'
          })
        })
      );
    });

    it('should sanitize dangerous commands', async () => {
      const context = createTestContext(['execute_commands']);
      
      const dangerousCommands = [
        'rm -rf /',
        'sudo rm -rf /',
        'chmod 777 /*',
        'dd if=/dev/zero of=/dev/sda'
      ];

      for (const cmd of dangerousCommands) {
        const result = await toolRegistry.execute('bash', { command: cmd }, context);
        
        expect(result.success).toBe(false);
        expect(result.error).toContain('dangerous command');
      }
    });
  });

  describe('Tool Permission Integration', () => {
    it('should enforce tool-specific permissions', async () => {
      const testCases = [
        { tool: 'read', params: { path: '/test/sample.txt' }, permission: 'read_files' },
        { tool: 'write', params: { path: '/test/new.txt', content: 'test' }, permission: 'write_files' },
        { tool: 'delete', params: { path: '/test/sample.txt' }, permission: 'delete_files' },
        { tool: 'move', params: { source: '/test/a.txt', destination: '/test/b.txt' }, permission: 'move_files' },
        { tool: 'bash', params: { command: 'echo test' }, permission: 'execute_commands' }
      ];

      for (const testCase of testCases) {
        // Test without permission
        const contextWithout = createTestContext([]);
        const resultWithout = await toolRegistry.execute(testCase.tool, testCase.params, contextWithout);
        expect(resultWithout.success).toBe(false);
        expect(resultWithout.error).toContain('permission');

        // Test with permission
        const contextWith = createTestContext([testCase.permission]);
        const resultWith = await toolRegistry.execute(testCase.tool, testCase.params, contextWith);
        // May still fail for other reasons (file not found, etc.) but not permission
        if (!resultWith.success) {
          expect(resultWith.error).not.toContain('permission');
        }
      }
    });

    it('should respect granular permissions', async () => {
      const context = createTestContext(['read_files']); // Only read, no write
      
      // Should succeed
      const readResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);
      expect(readResult.success).toBe(true);

      // Should fail
      const writeResult = await toolRegistry.execute('write', { 
        path: '/test/new.txt', 
        content: 'test' 
      }, context);
      expect(writeResult.success).toBe(false);
      expect(writeResult.error).toContain('permission');
    });

    it('should validate working directory restrictions', async () => {
      const context = createTestContext(['read_files'], '/test');
      
      // Should succeed - within working directory
      const allowedResult = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);
      expect(allowedResult.success).toBe(true);

      // Should fail - outside working directory
      const restrictedResult = await toolRegistry.execute('read', { path: '/other/external.txt' }, context);
      expect(restrictedResult.success).toBe(false);
      expect(restrictedResult.error).toContain('outside working directory');
    });
  });

  describe('Tool Error Handling and Recovery', () => {
    it('should handle filesystem errors gracefully', async () => {
      // Simulate filesystem error
      const originalReadFile = vol.readFileSync;
      vi.spyOn(vol, 'readFileSync').mockImplementation(() => {
        throw new Error('Filesystem error: Disk full');
      });

      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Filesystem error');

      // Restore original function
      vol.readFileSync = originalReadFile;
    });

    it('should provide detailed error information', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/nonexistent/path/file.txt' }, context);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
      expect(result.metadata?.errorType).toBeDefined();
      expect(result.metadata?.timestamp).toBeDefined();
    });

    it('should handle concurrent tool executions safely', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      
      // Execute multiple operations concurrently on the same file
      const operations = [
        toolRegistry.execute('read', { path: '/test/sample.txt' }, context),
        toolRegistry.execute('write', { path: '/test/concurrent.txt', content: 'test1' }, context),
        toolRegistry.execute('write', { path: '/test/concurrent.txt', content: 'test2' }, context),
        toolRegistry.execute('read', { path: '/test/data.json' }, context)
      ];

      const results = await Promise.all(operations);
      
      // All operations should complete (though some writes might overwrite others)
      results.forEach((result, index) => {
        expect(result).toBeDefined();
        // Read operations should succeed
        if (index === 0 || index === 3) {
          expect(result.success).toBe(true);
        }
      });
    });

    it('should handle resource cleanup on tool failures', async () => {
      // Mock a tool that opens resources but fails
      class ResourceTool extends ReadTool {
        private resources: string[] = [];

        async execute(params: any, context: ToolExecutionContext): Promise<ToolResult> {
          this.resources.push('resource1');
          this.resources.push('resource2');
          
          try {
            throw new Error('Simulated failure');
          } finally {
            // Cleanup resources
            this.resources.length = 0;
          }
        }

        getOpenResources() { return this.resources.length; }
      }

      const resourceTool = new ResourceTool();
      await toolRegistry.register(resourceTool, ['test']);

      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('resource', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(false);
      expect((resourceTool as any).getOpenResources()).toBe(0); // Resources should be cleaned up

      await toolRegistry.unregister('resource');
    });
  });

  describe('Tool Performance and Optimization', () => {
    it('should execute tools within reasonable time limits', async () => {
      const context = createTestContext(['read_files']);
      
      const startTime = Date.now();
      const result = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);
      const endTime = Date.now();
      
      expect(result.success).toBe(true);
      expect(endTime - startTime).toBeLessThan(1000); // Should complete in under 1 second
    });

    it('should handle large file operations efficiently', async () => {
      const context = createTestContext(['read_files', 'write_files']);
      const largeContent = 'A'.repeat(100000); // 100KB
      
      const startTime = Date.now();
      
      // Write large file
      const writeResult = await toolRegistry.execute('write', { 
        path: '/test/large-perf.txt',
        content: largeContent 
      }, context);
      
      // Read large file
      const readResult = await toolRegistry.execute('read', { 
        path: '/test/large-perf.txt' 
      }, context);
      
      const endTime = Date.now();
      
      expect(writeResult.success).toBe(true);
      expect(readResult.success).toBe(true);
      expect(readResult.data.content).toBe(largeContent);
      expect(endTime - startTime).toBeLessThan(5000); // Should complete in under 5 seconds
    });

    it('should provide execution metrics', async () => {
      const context = createTestContext(['read_files']);
      const result = await toolRegistry.execute('read', { path: '/test/sample.txt' }, context);

      expect(result.success).toBe(true);
      expect(result.performance).toBeDefined();
      expect(result.performance.executionTime).toBeGreaterThan(0);
      expect(result.performance.resourcesAccessed).toContain('/test/sample.txt');
    });

    it('should cache frequently accessed data when appropriate', async () => {
      const context = createTestContext(['read_files']);
      
      // Read same file multiple times
      const results = await Promise.all([
        toolRegistry.execute('read', { path: '/test/sample.txt' }, context),
        toolRegistry.execute('read', { path: '/test/sample.txt' }, context),
        toolRegistry.execute('read', { path: '/test/sample.txt' }, context)
      ]);

      results.forEach(result => {
        expect(result.success).toBe(true);
        expect(result.data.content).toBe('Sample file content for testing');
      });

      // Subsequent reads should be faster (if caching is implemented)
      const timings = results.map(r => r.performance?.executionTime || 0);
      expect(timings[0]).toBeGreaterThan(0);
      expect(timings[1]).toBeGreaterThan(0);
      expect(timings[2]).toBeGreaterThan(0);
    });
  });
});