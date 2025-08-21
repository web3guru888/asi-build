/**
 * Write Tool - Secure file writing with validation and backup
 * 
 * Provides safe file writing functionality with path validation,
 * permission checking, atomic writes, and optional backup creation.
 */

import { writeFile, readFile, stat, access, mkdir, copyFile } from 'fs/promises';
import { constants } from 'fs';
import { resolve, normalize, dirname, extname } from 'path';
import { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from '../base-tool.js';

export interface WriteOptions {
  encoding?: BufferEncoding;
  mode?: string | number;
  createBackup?: boolean;
  atomic?: boolean;
  append?: boolean;
  createDirs?: boolean;
}

export class WriteTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly allowedExtensions: Set<string>;
  private readonly blockedPaths: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'write',
      description: 'Write content to files with security controls, atomic operations, and backup support',
      parameters: [
        {
          name: 'path',
          type: 'string',
          description: 'Path to the file to write',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Path cannot be empty';
              if (value.length > 500) return 'Path too long (max 500 characters)';
              return true;
            }
          }
        },
        {
          name: 'content',
          type: 'string',
          description: 'Content to write to the file',
          required: true,
          validation: {
            custom: (value: string) => {
              if (value.length > 5 * 1024 * 1024) return 'Content too large (max 5MB)';
              return true;
            }
          }
        },
        {
          name: 'encoding',
          type: 'string',
          description: 'File encoding to use for writing',
          default: 'utf8',
          enum: ['utf8', 'ascii', 'base64', 'hex', 'binary', 'latin1']
        },
        {
          name: 'mode',
          type: 'string',
          description: 'File permissions in octal format',
          default: '644',
          validation: {
            pattern: '^[0-7]{3}$'
          }
        },
        {
          name: 'createBackup',
          type: 'boolean',
          description: 'Create a backup of existing file before writing',
          default: false
        },
        {
          name: 'atomic',
          type: 'boolean',
          description: 'Use atomic write operation (write to temp file then rename)',
          default: true
        },
        {
          name: 'append',
          type: 'boolean',
          description: 'Append content instead of overwriting',
          default: false
        },
        {
          name: 'createDirs',
          type: 'boolean',
          description: 'Create parent directories if they do not exist',
          default: false
        }
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['write_files'],
      safetyLevel: 'moderate',
      tags: ['file', 'io', 'write'],
      examples: [
        {
          description: 'Write text to a file',
          parameters: {
            path: './output.txt',
            content: 'Hello, World!'
          }
        },
        {
          description: 'Append to a log file with backup',
          parameters: {
            path: './app.log',
            content: 'New log entry\n',
            append: true,
            createBackup: true
          }
        }
      ]
    };

    super(definition);

    this.maxFileSize = 5 * 1024 * 1024; // 5MB
    
    // Allowed file extensions for writing
    this.allowedExtensions = new Set([
      '.txt', '.md', '.json', '.js', '.ts', '.jsx', '.tsx', '.css', '.html',
      '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.py', '.rb',
      '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.php', '.sh', '.bat',
      '.sql', '.csv', '.log', '.env', '.dockerfile', '.makefile', '.properties',
      '.template', '.example', '.sample', '.backup', '.tmp'
    ]);

    // Blocked paths for writing
    this.blockedPaths = new Set([
      '/etc', '/sys', '/proc', '/dev', '/boot', '/root',
      '/var/log/auth.log', '/var/log/secure', '/var/log/messages',
      '/usr/bin', '/usr/sbin', '/bin', '/sbin'
    ]);
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    const {
      path: inputPath,
      content,
      encoding = 'utf8',
      mode = '644',
      createBackup = false,
      atomic = true,
      append = false,
      createDirs = false
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize and resolve path
      const normalizedPath = this.normalizePath(inputPath, context.workingDirectory);
      
      // Security checks
      const securityCheck = await this.performSecurityCheck(normalizedPath, content, context);
      if (!securityCheck.safe) {
        return {
          success: false,
          error: `Write denied: ${securityCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime
          }
        };
      }

      // Check parent directory
      const parentDir = dirname(normalizedPath);
      await this.ensureParentDirectory(parentDir, createDirs);

      let backupPath: string | undefined;
      let originalExists = false;

      // Check if file exists
      try {
        await access(normalizedPath, constants.F_OK);
        originalExists = true;

        // Create backup if requested
        if (createBackup) {
          backupPath = await this.createBackup(normalizedPath);
        }
      } catch (error) {
        // File doesn't exist, which is fine for writing
      }

      // Perform the write operation
      const writeResult = await this.performWrite(
        normalizedPath,
        content,
        { encoding, mode, atomic, append }
      );

      this.emit('executed', {
        path: normalizedPath,
        size: content.length,
        encoding,
        atomic,
        append,
        backupCreated: !!backupPath,
        success: true
      });

      return {
        success: true,
        data: {
          path: normalizedPath,
          bytesWritten: writeResult.bytesWritten,
          encoding,
          mode: parseInt(mode, 8),
          backupPath,
          originalExists,
          atomic,
          append
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: [normalizedPath, ...(backupPath ? [backupPath] : [])]
        }
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      this.emit('error', {
        path: inputPath,
        error: errorMessage,
        executionTime: Date.now() - startTime
      });

      return {
        success: false,
        error: `Failed to write file: ${errorMessage}`,
        performance: {
          executionTime: Date.now() - startTime
        }
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
    content: string, 
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

    // Check content size
    if (content.length > this.maxFileSize) {
      return { safe: false, reason: `Content too large (${content.length} bytes, max ${this.maxFileSize} bytes)` };
    }

    // Check file extension
    const ext = extname(filePath).toLowerCase();
    if (ext && !this.allowedExtensions.has(ext) && !context.permissions.includes('write_any_file')) {
      return { safe: false, reason: `File type '${ext}' not allowed without write_any_file permission` };
    }

    // Check for potentially dangerous content
    const dangerousPatterns = [
      /<script\s/i,
      /javascript:/i,
      /data:.*base64/i,
      /eval\s*\(/i,
      /exec\s*\(/i,
      /system\s*\(/i
    ];

    if (!context.permissions.includes('write_executable_content')) {
      for (const pattern of dangerousPatterns) {
        if (pattern.test(content)) {
          return { safe: false, reason: 'Content contains potentially dangerous code' };
        }
      }
    }

    // Check if path is within allowed directories (if specified in context)
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const isAllowed = allowedDirs.some(dir => filePath.startsWith(resolve(dir)));
      if (!isAllowed) {
        return { safe: false, reason: 'Path is outside allowed directories' };
      }
    }

    return { safe: true };
  }

  private async ensureParentDirectory(parentDir: string, createDirs: boolean): Promise<void> {
    try {
      await access(parentDir, constants.F_OK);
    } catch (error: unknown) {
      const err = error as any;
      if (err.code === 'ENOENT') {
        if (createDirs) {
          await mkdir(parentDir, { recursive: true });
        } else {
          throw new Error(`Parent directory does not exist: ${parentDir}`);
        }
      } else {
        throw new Error(`Cannot access parent directory: ${(error as Error).message}`);
      }
    }
  }

  private async createBackup(filePath: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = `${filePath}.backup-${timestamp}`;
    
    await copyFile(filePath, backupPath);
    return backupPath;
  }

  private async performWrite(
    filePath: string,
    content: string,
    options: {
      encoding: BufferEncoding;
      mode: string;
      atomic: boolean;
      append: boolean;
    }
  ): Promise<{ bytesWritten: number }> {
    const { encoding, mode, atomic, append } = options;
    const fileMode = parseInt(mode, 8);

    if (append && !atomic) {
      // Simple append operation
      const fs = await import('fs/promises');
      await fs.appendFile(filePath, content, { encoding, mode: fileMode });
      return { bytesWritten: Buffer.byteLength(content, encoding) };
    }

    if (append && atomic) {
      // Read existing content, combine, then write atomically
      let existingContent = '';
      try {
        existingContent = await readFile(filePath, encoding);
      } catch (error) {
        // File doesn't exist, which is fine
      }
      
      const combinedContent = existingContent + content;
      return this.performAtomicWrite(filePath, combinedContent, encoding, fileMode);
    }

    if (atomic) {
      return this.performAtomicWrite(filePath, content, encoding, fileMode);
    } else {
      // Direct write
      await writeFile(filePath, content, { encoding, mode: fileMode });
      return { bytesWritten: Buffer.byteLength(content, encoding) };
    }
  }

  private async performAtomicWrite(
    filePath: string,
    content: string,
    encoding: BufferEncoding,
    mode: number
  ): Promise<{ bytesWritten: number }> {
    const tempPath = `${filePath}.tmp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      // Write to temporary file
      await writeFile(tempPath, content, { encoding, mode });
      
      // Atomic rename
      const fs = await import('fs/promises');
      await fs.rename(tempPath, filePath);
      
      return { bytesWritten: Buffer.byteLength(content, encoding) };
    } catch (error) {
      // Clean up temp file if it exists
      try {
        const fs = await import('fs/promises');
        await fs.unlink(tempPath);
      } catch (cleanupError) {
        // Ignore cleanup errors
      }
      throw error;
    }
  }

  async beforeExecute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<void> {
    await super.beforeExecute(parameters, context);
    
    // Additional checks for file writing
    if (!context.permissions.includes('write_files')) {
      throw new Error('Write tool requires write_files permission');
    }

    // Log the write attempt
    const contentPreview = parameters.content.length > 100 
      ? `${parameters.content.substring(0, 97)}...`
      : parameters.content;
    
    console.log(`[WriteTool] Writing to file for user ${context.userId}: ${parameters.path} (${parameters.content.length} bytes)`);
  }
}

export default WriteTool;