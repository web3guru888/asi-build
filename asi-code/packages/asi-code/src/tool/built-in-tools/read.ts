/**
 * Read Tool - Secure file reading with access controls
 *
 * Provides safe file reading functionality with path validation,
 * permission checking, and content filtering.
 */

import { access, readFile, stat } from 'fs/promises';
import { constants } from 'fs';
import { basename, dirname, extname, normalize, resolve } from 'path';
import {
  BaseTool,
  ToolDefinition,
  ToolExecutionContext,
  ToolResult,
} from '../base-tool.js';

export interface ReadOptions {
  encoding?: BufferEncoding;
  maxSize?: number;
  offset?: number;
  length?: number;
  validatePath?: boolean;
}

export class ReadTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly allowedExtensions: Set<string>;
  private readonly blockedPaths: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'read',
      description:
        'Read file contents with security controls and access validation',
      parameters: [
        {
          name: 'path',
          type: 'string',
          description: 'Path to the file to read',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Path cannot be empty';
              if (value.length > 500)
                return 'Path too long (max 500 characters)';
              return true;
            },
          },
        },
        {
          name: 'encoding',
          type: 'string',
          description: 'File encoding to use for reading',
          default: 'utf8',
          enum: ['utf8', 'ascii', 'base64', 'hex', 'binary', 'latin1'],
        },
        {
          name: 'maxSize',
          type: 'number',
          description: 'Maximum file size to read in bytes',
          default: 1048576, // 1MB
          validation: {
            min: 1,
            max: 10485760, // 10MB
          },
        },
        {
          name: 'offset',
          type: 'number',
          description: 'Byte offset to start reading from',
          default: 0,
          validation: {
            min: 0,
          },
        },
        {
          name: 'length',
          type: 'number',
          description: 'Number of bytes to read',
          validation: {
            min: 1,
          },
        },
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['read_files'],
      safetyLevel: 'safe',
      tags: ['file', 'io', 'read'],
      examples: [
        {
          description: 'Read a text file',
          parameters: {
            path: './example.txt',
          },
        },
        {
          description: 'Read first 100 bytes of a file',
          parameters: {
            path: './data.bin',
            length: 100,
            encoding: 'hex',
          },
        },
      ],
    };

    super(definition);

    this.maxFileSize = 10 * 1024 * 1024; // 10MB

    // Allowed file extensions (for security)
    this.allowedExtensions = new Set([
      '.txt',
      '.md',
      '.json',
      '.js',
      '.ts',
      '.jsx',
      '.tsx',
      '.css',
      '.html',
      '.xml',
      '.yaml',
      '.yml',
      '.toml',
      '.ini',
      '.cfg',
      '.conf',
      '.py',
      '.rb',
      '.java',
      '.c',
      '.cpp',
      '.h',
      '.hpp',
      '.go',
      '.rs',
      '.php',
      '.sh',
      '.bat',
      '.sql',
      '.csv',
      '.log',
      '.env',
      '.gitignore',
      '.dockerfile',
      '.makefile',
      '.readme',
      '.license',
      '.changelog',
      '.todo',
      '.notes',
      '.properties',
    ]);

    // Blocked paths (for security)
    this.blockedPaths = new Set([
      '/etc/passwd',
      '/etc/shadow',
      '/etc/group',
      '/etc/hosts',
      '/proc/cpuinfo',
      '/proc/meminfo',
      '/sys',
      '/dev',
      '/var/log/auth.log',
      '/var/log/secure',
      '/var/log/messages',
    ]);
  }

  async execute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    const {
      path: inputPath,
      encoding = 'utf8',
      maxSize = 1048576,
      offset = 0,
      length,
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize and resolve path
      const normalizedPath = this.normalizePath(
        inputPath,
        context.workingDirectory
      );

      // Security checks
      const securityCheck = await this.performSecurityCheck(
        normalizedPath,
        context
      );
      if (!securityCheck.safe) {
        return {
          success: false,
          error: `Access denied: ${securityCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Check file existence and permissions
      await this.checkFileAccess(normalizedPath);

      // Get file stats
      const fileStats = await stat(normalizedPath);

      if (!fileStats.isFile()) {
        return {
          success: false,
          error: 'Path is not a file',
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Check file size
      if (fileStats.size > this.maxFileSize) {
        return {
          success: false,
          error: `File too large (${fileStats.size} bytes, max ${this.maxFileSize} bytes)`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Read file content
      let content: string | Buffer;

      if (length !== undefined || offset > 0) {
        // Partial read
        content = await this.readPartial(
          normalizedPath,
          encoding,
          offset,
          length,
          maxSize
        );
      } else {
        // Full read with size limit
        const readLength = Math.min(fileStats.size, maxSize);
        const buffer = Buffer.alloc(readLength);

        const fileHandle = await import('fs/promises').then(fs =>
          fs.open(normalizedPath, 'r')
        );
        try {
          const { bytesRead } = await fileHandle.read(buffer, 0, readLength, 0);
          content =
            encoding === 'binary'
              ? buffer.subarray(0, bytesRead)
              : buffer.subarray(0, bytesRead).toString(encoding);
        } finally {
          await fileHandle.close();
        }
      }

      this.emit('executed', {
        path: normalizedPath,
        size: fileStats.size,
        encoding,
        success: true,
      });

      return {
        success: true,
        data: {
          content,
          path: normalizedPath,
          size: typeof content === 'string' ? content.length : content.length,
          fileSize: fileStats.size,
          encoding,
          mtime: fileStats.mtime,
          mode: fileStats.mode,
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: [normalizedPath],
        },
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      this.emit('error', {
        path: inputPath,
        error: errorMessage,
        executionTime: Date.now() - startTime,
      });

      return {
        success: false,
        error: `Failed to read file: ${errorMessage}`,
        performance: {
          executionTime: Date.now() - startTime,
        },
      };
    }
  }

  private normalizePath(inputPath: string, workingDirectory: string): string {
    // Handle relative paths
    if (!inputPath.startsWith('/')) {
      inputPath = resolve(workingDirectory, inputPath);
    }

    // Normalize to prevent path traversal
    return normalize(inputPath);
  }

  private async performSecurityCheck(
    filePath: string,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check blocked paths
    const normalizedPath = filePath.toLowerCase();
    for (const blockedPath of this.blockedPaths) {
      if (normalizedPath.startsWith(blockedPath.toLowerCase())) {
        return { safe: false, reason: 'Path is blocked for security reasons' };
      }
    }

    // Check for path traversal attempts
    if (filePath.includes('..') || filePath.includes('~')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check file extension for basic filtering
    const ext = extname(filePath).toLowerCase();
    if (
      ext &&
      !this.allowedExtensions.has(ext) &&
      !context.permissions.includes('read_any_file')
    ) {
      return {
        safe: false,
        reason: `File type '${ext}' not allowed without read_any_file permission`,
      };
    }

    // Check if path is within allowed directories (if specified in context)
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const isAllowed = allowedDirs.some(dir =>
        filePath.startsWith(resolve(dir))
      );
      if (!isAllowed) {
        return { safe: false, reason: 'Path is outside allowed directories' };
      }
    }

    return { safe: true };
  }

  private async checkFileAccess(filePath: string): Promise<void> {
    try {
      await access(filePath, constants.R_OK);
    } catch (error: unknown) {
      const err = error as any;
      if (err.code === 'ENOENT') {
        throw new Error('File not found');
      } else if (err.code === 'EACCES') {
        throw new Error('Permission denied');
      } else {
        throw new Error(
          `Cannot access file: ${err.message || 'Unknown error'}`
        );
      }
    }
  }

  private async readPartial(
    filePath: string,
    encoding: BufferEncoding,
    offset: number,
    length: number | undefined,
    maxSize: number
  ): Promise<string | Buffer> {
    const fileHandle = await import('fs/promises').then(fs =>
      fs.open(filePath, 'r')
    );

    try {
      const fileStats = await fileHandle.stat();
      const readLength =
        length !== undefined
          ? Math.min(length, maxSize, fileStats.size - offset)
          : Math.min(maxSize, fileStats.size - offset);

      if (readLength <= 0) {
        return encoding === 'binary' ? Buffer.alloc(0) : '';
      }

      const buffer = Buffer.alloc(readLength);
      const { bytesRead } = await fileHandle.read(
        buffer,
        0,
        readLength,
        offset
      );

      const actualBuffer = buffer.subarray(0, bytesRead);
      return encoding === 'binary'
        ? actualBuffer
        : actualBuffer.toString(encoding);
    } finally {
      await fileHandle.close();
    }
  }

  async beforeExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<void> {
    await super.beforeExecute(parameters, context);

    // Additional checks for file reading
    if (!context.permissions.includes('read_files')) {
      throw new Error('Read tool requires read_files permission');
    }

    // Log the read attempt
    console.log(
      `[ReadTool] Reading file for user ${context.userId}: ${parameters.path}`
    );
  }
}

export default ReadTool;
