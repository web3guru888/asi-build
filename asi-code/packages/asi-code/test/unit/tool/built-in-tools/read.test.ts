/**
 * Unit tests for Read Tool
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { vol } from 'memfs';
import { ReadTool } from '../../../../src/tool/built-in-tools/read.js';
import { BaseTool } from '../../../../src/tool/base-tool.js';
import { createMockToolExecutionContext } from '../../../test-utils.js';

// Mock fs/promises to use memfs
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

describe('ReadTool', () => {
  let readTool: ReadTool;
  
  beforeEach(() => {
    vol.reset();
    readTool = new ReadTool();
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Tool Definition', () => {
    it('should have correct tool definition', () => {
      const definition = readTool.definition;
      
      expect(definition.name).toBe('read');
      expect(definition.category).toBe('file');
      expect(definition.permissions).toContain('read_files');
      expect(definition.safetyLevel).toBe('safe');
      expect(definition.parameters).toHaveLength(5);
      
      const pathParam = definition.parameters.find(p => p.name === 'path');
      expect(pathParam).toBeDefined();
      expect(pathParam?.required).toBe(true);
    });

    it('should be instance of BaseTool', () => {
      expect(readTool).toBeInstanceOf(BaseTool);
    });
  });

  describe('File Reading', () => {
    beforeEach(() => {
      // Create test files in virtual filesystem
      vol.fromJSON({
        '/test/file.txt': 'Hello, World!',
        '/test/data.json': '{"key": "value"}',
        '/test/large.txt': 'A'.repeat(5000),
        '/test/binary.dat': Buffer.from([0x01, 0x02, 0x03, 0x04]).toString('binary'),
        '/test/empty.txt': '',
        '/test/readonly.txt': 'readonly content'
      });
    });

    it('should read text file successfully', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/file.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('Hello, World!');
      expect(result.data.path).toBe('/test/file.txt');
      expect(result.data.encoding).toBe('utf8');
      expect(result.data.size).toBe(13);
      expect(result.performance?.executionTime).toBeGreaterThan(0);
    });

    it('should read file with relative path', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: 'file.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('Hello, World!');
      expect(result.data.path).toBe('/test/file.txt');
    });

    it('should read file with different encoding', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/file.txt', encoding: 'base64' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe(Buffer.from('Hello, World!').toString('base64'));
      expect(result.data.encoding).toBe('base64');
    });

    it('should read partial file content', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/file.txt', offset: 7, length: 5 },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('World');
    });

    it('should respect maxSize parameter', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/large.txt', maxSize: 100 },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toHaveLength(100);
      expect(result.data.content).toBe('A'.repeat(100));
    });

    it('should read empty file', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/empty.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('');
      expect(result.data.size).toBe(0);
    });

    it('should read binary file', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Create binary file
      vol.writeFileSync('/test/binary.bin', Buffer.from([0x01, 0x02, 0x03, 0x04]));

      const result = await readTool.execute(
        { path: '/test/binary.bin', encoding: 'hex' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('01020304');
      expect(result.data.encoding).toBe('hex');
    });
  });

  describe('Security and Validation', () => {
    beforeEach(() => {
      vol.fromJSON({
        '/allowed/file.txt': 'allowed content',
        '/blocked/file.txt': 'blocked content',
        '/test/script.js': 'console.log("test");',
        '/test/executable.exe': 'binary data',
        '/etc/passwd': 'system file',
        '/proc/cpuinfo': 'cpu info'
      });
    });

    it('should reject access without read_files permission', async () => {
      const context = createMockToolExecutionContext({
        permissions: [],
        workingDirectory: '/test'
      });

      await expect(readTool.executeWithLifecycle(
        { path: '/test/file.txt' },
        context
      )).rejects.toThrow('Read tool requires read_files permission');
    });

    it('should block dangerous system paths', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/etc/passwd' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Access denied');
      expect(result.error).toContain('blocked for security reasons');
    });

    it('should detect path traversal attempts', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '../../../etc/passwd' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Path traversal detected');
    });

    it('should block unauthorized file extensions', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'], // No read_any_file permission
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/executable.exe' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('File type \'.exe\' not allowed');
    });

    it('should allow unauthorized extensions with read_any_file permission', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files', 'read_any_file'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/executable.exe' },
        context
      );

      // Should succeed with the permission, even though we don't have the actual file
      // The error will be about file not found, not extension blocked
      expect(result.error).not.toContain('File type');
    });

    it('should respect allowed directories restriction', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test',
        metadata: {
          allowedDirectories: ['/allowed']
        }
      });

      // Try to read from blocked directory
      const blockedResult = await readTool.execute(
        { path: '/blocked/file.txt' },
        context
      );

      expect(blockedResult.success).toBe(false);
      expect(blockedResult.error).toContain('outside allowed directories');

      // Try to read from allowed directory
      const allowedResult = await readTool.execute(
        { path: '/allowed/file.txt' },
        context
      );

      expect(allowedResult.success).toBe(true);
    });

    it('should validate path parameter', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Empty path
      const emptyResult = await readTool.executeWithLifecycle(
        { path: '' },
        context
      );

      expect(emptyResult.success).toBe(false);
      expect(emptyResult.error).toContain('Parameter validation failed');

      // Path too long
      const longPath = 'a'.repeat(501);
      const longResult = await readTool.executeWithLifecycle(
        { path: longPath },
        context
      );

      expect(longResult.success).toBe(false);
      expect(longResult.error).toContain('Parameter validation failed');
    });

    it('should validate encoding parameter', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/file.txt', 'test content');

      const result = await readTool.executeWithLifecycle(
        { path: '/test/file.txt', encoding: 'invalid' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Parameter validation failed');
    });

    it('should validate numeric parameters', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/file.txt', 'test content');

      // Negative offset
      const negativeOffsetResult = await readTool.executeWithLifecycle(
        { path: '/test/file.txt', offset: -1 },
        context
      );

      expect(negativeOffsetResult.success).toBe(false);
      expect(negativeOffsetResult.error).toContain('Parameter validation failed');

      // Invalid maxSize
      const invalidMaxSizeResult = await readTool.executeWithLifecycle(
        { path: '/test/file.txt', maxSize: 20000000 }, // Too large
        context
      );

      expect(invalidMaxSizeResult.success).toBe(false);
      expect(invalidMaxSizeResult.error).toContain('Parameter validation failed');
    });
  });

  describe('Error Handling', () => {
    it('should handle file not found', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/nonexistent.txt' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('File not found');
    });

    it('should handle directory instead of file', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.mkdirSync('/test/directory');

      const result = await readTool.execute(
        { path: '/test/directory' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toBe('Path is not a file');
    });

    it('should handle file too large error', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Create a large file that exceeds the tool's max file size
      const largeContent = 'A'.repeat(11 * 1024 * 1024); // 11MB
      vol.writeFileSync('/test/huge.txt', largeContent);

      const result = await readTool.execute(
        { path: '/test/huge.txt' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('File too large');
    });

    it('should handle permission errors', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Mock fs to throw permission error
      const originalAccess = require('fs/promises').access;
      vi.mocked(require('fs/promises')).access = vi.fn().mockRejectedValue({
        code: 'EACCES',
        message: 'Permission denied'
      });

      const result = await readTool.execute(
        { path: '/test/file.txt' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Permission denied');

      // Restore original function
      vi.mocked(require('fs/promises')).access = originalAccess;
    });

    it('should handle read errors gracefully', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/file.txt', 'test content');

      // Mock file open to throw error
      const originalOpen = require('fs/promises').open;
      vi.mocked(require('fs/promises')).open = vi.fn().mockRejectedValue(new Error('IO Error'));

      const result = await readTool.execute(
        { path: '/test/file.txt' },
        context
      );

      expect(result.success).toBe(false);
      expect(result.error).toContain('Failed to read file: IO Error');

      // Restore original function
      vi.mocked(require('fs/promises')).open = originalOpen;
    });
  });

  describe('Events', () => {
    beforeEach(() => {
      vol.fromJSON({
        '/test/file.txt': 'Hello, World!'
      });
    });

    it('should emit executed event on successful read', async () => {
      const executedSpy = vi.fn();
      readTool.on('executed', executedSpy);

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      await readTool.execute(
        { path: '/test/file.txt' },
        context
      );

      expect(executedSpy).toHaveBeenCalledWith({
        path: '/test/file.txt',
        size: 13,
        encoding: 'utf8',
        success: true
      });
    });

    it('should emit error event on failure', async () => {
      const errorSpy = vi.fn();
      readTool.on('error', errorSpy);

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      await readTool.execute(
        { path: '/test/nonexistent.txt' },
        context
      );

      expect(errorSpy).toHaveBeenCalledWith({
        path: '/test/nonexistent.txt',
        error: expect.stringContaining('File not found'),
        executionTime: expect.any(Number)
      });
    });
  });

  describe('Performance and Limits', () => {
    it('should include performance metrics', async () => {
      vol.writeFileSync('/test/file.txt', 'test content');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/file.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.performance).toBeDefined();
      expect(result.performance?.executionTime).toBeGreaterThan(0);
      expect(result.performance?.resourcesAccessed).toContain('/test/file.txt');
    });

    it('should handle offset beyond file size', async () => {
      vol.writeFileSync('/test/small.txt', 'tiny');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/small.txt', offset: 100 },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('');
    });

    it('should handle length parameter correctly', async () => {
      vol.writeFileSync('/test/content.txt', '0123456789');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/content.txt', offset: 2, length: 3 },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('234');
    });
  });

  describe('Logging and Debugging', () => {
    it('should log read attempts in beforeExecute', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      vol.writeFileSync('/test/file.txt', 'test');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        userId: 'test-user',
        workingDirectory: '/test'
      });

      await readTool.executeWithLifecycle(
        { path: '/test/file.txt' },
        context
      );

      expect(consoleSpy).toHaveBeenCalledWith(
        '[ReadTool] Reading file for user test-user: /test/file.txt'
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    it('should handle file with no extension', async () => {
      vol.writeFileSync('/test/README', 'readme content');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/README' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe('readme content');
    });

    it('should handle unicode content correctly', async () => {
      const unicodeContent = 'Hello 世界! 🌍';
      vol.writeFileSync('/test/unicode.txt', unicodeContent);

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/unicode.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.content).toBe(unicodeContent);
    });

    it('should normalize paths correctly', async () => {
      vol.writeFileSync('/test/file.txt', 'content');

      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      const result = await readTool.execute(
        { path: '/test/./file.txt' },
        context
      );

      expect(result.success).toBe(true);
      expect(result.data.path).toBe('/test/file.txt');
    });
  });
});