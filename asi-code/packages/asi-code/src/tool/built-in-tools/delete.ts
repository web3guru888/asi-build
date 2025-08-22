/**
 * Delete Tool - Safe file and directory deletion with confirmations
 * 
 * Provides secure deletion functionality with backup options,
 * permission checks, and recovery mechanisms.
 */

import { unlink, rmdir, stat, access, readdir, copyFile, mkdir } from 'fs/promises';
import { constants } from 'fs';
import { resolve, normalize, dirname, basename, extname, join } from 'path';
import { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from '../base-tool.js';

export interface DeleteOptions {
  recursive?: boolean;
  force?: boolean;
  createBackup?: boolean;
  dryRun?: boolean;
  confirmDangerous?: boolean;
}

export interface DeleteResult {
  path: string;
  type: 'file' | 'directory';
  deleted: boolean;
  backupPath?: string;
  size?: number;
  itemsDeleted?: number;
}

export class DeleteTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly blockedPaths: Set<string>;
  private readonly dangerousExtensions: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'delete',
      description: 'Safely delete files and directories with backup and confirmation options',
      parameters: [
        {
          name: 'path',
          type: 'string',
          description: 'Path to the file or directory to delete',
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
          name: 'recursive',
          type: 'boolean',
          description: 'Delete directories recursively',
          default: false
        },
        {
          name: 'force',
          type: 'boolean',
          description: 'Force deletion without additional safety checks',
          default: false
        },
        {
          name: 'createBackup',
          type: 'boolean',
          description: 'Create backup before deletion',
          default: true
        },
        {
          name: 'dryRun',
          type: 'boolean',
          description: 'Preview what would be deleted without actually deleting',
          default: false
        },
        {
          name: 'confirmDangerous',
          type: 'boolean',
          description: 'Confirm deletion of potentially dangerous files',
          default: false
        }
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['delete_files'],
      safetyLevel: 'high-risk',
      tags: ['file', 'delete', 'cleanup', 'backup'],
      examples: [
        {
          description: 'Delete a file with backup',
          parameters: {
            path: './temp.txt',
            createBackup: true
          }
        },
        {
          description: 'Preview directory deletion',
          parameters: {
            path: './temp-folder',
            recursive: true,
            dryRun: true
          }
        }
      ]
    };

    super(definition);

    this.maxFileSize = 100 * 1024 * 1024; // 100MB
    
    // Critical system paths that should never be deleted
    this.blockedPaths = new Set([
      '/',
      '/bin',
      '/sbin',
      '/usr',
      '/etc',
      '/var',
      '/sys',
      '/proc',
      '/dev',
      '/boot',
      '/root',
      '/home',
      process.cwd(),
      dirname(process.execPath)
    ]);

    // File extensions that require extra confirmation
    this.dangerousExtensions = new Set([
      '.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm',
      '.sh', '.bat', '.cmd', '.ps1',
      '.db', '.sqlite', '.sql'
    ]);
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    const {
      path: inputPath,
      recursive = false,
      force = false,
      createBackup = true,
      dryRun = false,
      confirmDangerous = false
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize path
      const normalizedPath = this.normalizePath(inputPath, context.workingDirectory);
      
      // Security and safety checks
      const safetyCheck = await this.performSafetyCheck(normalizedPath, {
        recursive,
        force,
        confirmDangerous
      }, context);
      
      if (!safetyCheck.safe) {
        return {
          success: false,
          error: `Deletion denied: ${safetyCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime
          }
        };
      }

      // Check if path exists
      let pathStats;
      try {
        pathStats = await stat(normalizedPath);
      } catch (error: unknown) {
        const err = error as any;
        if (err.code === 'ENOENT') {
          return {
            success: false,
            error: 'Path does not exist',
            performance: {
              executionTime: Date.now() - startTime
            }
          };
        }
        throw error;
      }

      // Analyze what will be deleted
      const analysisResult = await this.analyzeDeleteTarget(normalizedPath, pathStats, recursive);
      
      if (dryRun) {
        return {
          success: true,
          data: {
            path: normalizedPath,
            dryRun: true,
            wouldDelete: analysisResult,
            analysis: {
              type: pathStats.isDirectory() ? 'directory' : 'file',
              size: analysisResult.totalSize,
              itemCount: analysisResult.itemCount,
              hasSubdirectories: analysisResult.hasSubdirectories
            }
          },
          performance: {
            executionTime: Date.now() - startTime
          }
        };
      }

      let backupPath: string | undefined;
      
      // Create backup if requested and not a dry run
      if (createBackup && !dryRun) {
        backupPath = await this.createBackup(normalizedPath, pathStats);
      }

      // Perform the deletion
      const deleteResult = await this.performDeletion(normalizedPath, pathStats, { recursive });

      this.emit('executed', {
        path: normalizedPath,
        type: deleteResult.type,
        backupCreated: !!backupPath,
        itemsDeleted: deleteResult.itemsDeleted,
        success: true
      });

      return {
        success: true,
        data: {
          ...deleteResult,
          backupPath,
          analysis: analysisResult
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
        error: `Deletion failed: ${errorMessage}`,
        performance: {
          executionTime: Date.now() - startTime
        }
      };
    }
  }

  private normalizePath(inputPath: string, workingDirectory: string): string {
    if (!inputPath.startsWith('/')) {
      inputPath = resolve(workingDirectory, inputPath);
    }
    return normalize(inputPath);
  }

  private async performSafetyCheck(
    targetPath: string,
    options: DeleteOptions,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check for critical system paths
    const normalizedPath = targetPath.toLowerCase();
    for (const blockedPath of this.blockedPaths) {
      if (normalizedPath === blockedPath.toLowerCase() || normalizedPath.startsWith(blockedPath.toLowerCase() + '/')) {
        return { safe: false, reason: 'Cannot delete system critical paths' };
      }
    }

    // Check for path traversal attempts
    if (targetPath.includes('..')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check if path is within allowed directories
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const isAllowed = allowedDirs.some(dir => targetPath.startsWith(resolve(dir)));
      if (!isAllowed) {
        return { safe: false, reason: 'Path is outside allowed directories' };
      }
    }

    // Check for dangerous file extensions
    const ext = extname(targetPath).toLowerCase();
    if (this.dangerousExtensions.has(ext) && !options.confirmDangerous) {
      return { safe: false, reason: `Dangerous file type '${ext}' requires confirmDangerous=true` };
    }

    // Check if trying to delete current working directory
    if (targetPath === context.workingDirectory) {
      return { safe: false, reason: 'Cannot delete current working directory' };
    }

    // Require dangerous_operations permission for certain operations
    if (!context.permissions.includes('dangerous_operations')) {
      // Check if it's a large directory deletion
      try {
        const stats = await stat(targetPath);
        if (stats.isDirectory() && options.recursive) {
          const items = await readdir(targetPath);
          if (items.length > 10) {
            return { safe: false, reason: 'Large directory deletion requires dangerous_operations permission' };
          }
        }
      } catch (error) {
        // If we can't stat, we'll fail later anyway
      }
    }

    return { safe: true };
  }

  private async analyzeDeleteTarget(
    targetPath: string,
    stats: any,
    recursive: boolean
  ): Promise<{
    itemCount: number;
    totalSize: number;
    hasSubdirectories: boolean;
    items: Array<{ path: string; type: 'file' | 'directory'; size: number }>;
  }> {
    const result = {
      itemCount: 0,
      totalSize: 0,
      hasSubdirectories: false,
      items: [] as Array<{ path: string; type: 'file' | 'directory'; size: number }>
    };

    if (stats.isFile()) {
      result.itemCount = 1;
      result.totalSize = stats.size;
      result.items.push({
        path: targetPath,
        type: 'file',
        size: stats.size
      });
    } else if (stats.isDirectory()) {
      await this.analyzeDirectory(targetPath, result, recursive, 0);
    }

    return result;
  }

  private async analyzeDirectory(
    dirPath: string,
    result: any,
    recursive: boolean,
    depth: number
  ): Promise<void> {
    if (depth > 10) return; // Prevent deep recursion

    try {
      const items = await readdir(dirPath);
      
      for (const item of items) {
        const itemPath = join(dirPath, item);
        try {
          const itemStats = await stat(itemPath);
          
          if (itemStats.isFile()) {
            result.itemCount++;
            result.totalSize += itemStats.size;
            result.items.push({
              path: itemPath,
              type: 'file',
              size: itemStats.size
            });
          } else if (itemStats.isDirectory()) {
            result.hasSubdirectories = true;
            result.itemCount++;
            result.items.push({
              path: itemPath,
              type: 'directory',
              size: 0
            });
            
            if (recursive) {
              await this.analyzeDirectory(itemPath, result, recursive, depth + 1);
            }
          }
        } catch (error) {
          // Skip items we can't access
          continue;
        }
      }
    } catch (error) {
      // Skip directories we can't read
    }
  }

  private async createBackup(targetPath: string, stats: any): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupDir = join(dirname(targetPath), '.asi-backups');
    const backupName = `${basename(targetPath)}.backup-${timestamp}`;
    const backupPath = join(backupDir, backupName);

    // Create backup directory if it doesn't exist
    try {
      await mkdir(backupDir, { recursive: true });
    } catch (error) {
      // Directory might already exist
    }

    if (stats.isFile()) {
      await copyFile(targetPath, backupPath);
    } else if (stats.isDirectory()) {
      await this.backupDirectory(targetPath, backupPath);
    }

    return backupPath;
  }

  private async backupDirectory(sourcePath: string, backupPath: string): Promise<void> {
    await mkdir(backupPath, { recursive: true });
    
    try {
      const items = await readdir(sourcePath);
      
      for (const item of items) {
        const sourceeItemPath = join(sourcePath, item);
        const backupItemPath = join(backupPath, item);
        
        try {
          const itemStats = await stat(sourceeItemPath);
          
          if (itemStats.isFile()) {
            await copyFile(sourceeItemPath, backupItemPath);
          } else if (itemStats.isDirectory()) {
            await this.backupDirectory(sourceeItemPath, backupItemPath);
          }
        } catch (error) {
          // Skip items we can't backup
          continue;
        }
      }
    } catch (error) {
      // If we can't read the directory, skip it
    }
  }

  private async performDeletion(
    targetPath: string,
    stats: any,
    options: { recursive: boolean }
  ): Promise<DeleteResult> {
    if (stats.isFile()) {
      await unlink(targetPath);
      return {
        path: targetPath,
        type: 'file',
        deleted: true,
        size: stats.size,
        itemsDeleted: 1
      };
    } else if (stats.isDirectory()) {
      const itemsDeleted = await this.deleteDirectory(targetPath, options.recursive);
      return {
        path: targetPath,
        type: 'directory',
        deleted: true,
        itemsDeleted
      };
    }

    throw new Error('Unknown file type');
  }

  private async deleteDirectory(dirPath: string, recursive: boolean): Promise<number> {
    let itemsDeleted = 0;

    if (!recursive) {
      // Try to delete empty directory
      await rmdir(dirPath);
      return 1;
    }

    try {
      const items = await readdir(dirPath);
      
      // Delete all contents first
      for (const item of items) {
        const itemPath = join(dirPath, item);
        try {
          const itemStats = await stat(itemPath);
          
          if (itemStats.isFile()) {
            await unlink(itemPath);
            itemsDeleted++;
          } else if (itemStats.isDirectory()) {
            const subItemsDeleted = await this.deleteDirectory(itemPath, true);
            itemsDeleted += subItemsDeleted;
          }
        } catch (error) {
          // Skip items we can't delete
          continue;
        }
      }
    } catch (error) {
      // Directory might already be empty or inaccessible
    }

    // Now delete the directory itself
    try {
      await rmdir(dirPath);
      itemsDeleted++;
    } catch (error) {
      // Directory might not be empty or inaccessible
    }

    return itemsDeleted;
  }

  async beforeExecute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<void> {
    await super.beforeExecute(parameters, context);
    
    if (!context.permissions.includes('delete_files')) {
      throw new Error('Delete tool requires delete_files permission');
    }

    console.log(`[DeleteTool] Deleting ${parameters.path} for user ${context.userId} (dryRun: ${parameters.dryRun || false})`);
  }
}

export default DeleteTool;