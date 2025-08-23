/**
 * Move Tool - Safe file and directory moving/renaming operations
 *
 * Provides secure file and directory moving with conflict resolution,
 * backup options, and atomic operations.
 */

import {
  access,
  copyFile,
  mkdir,
  readdir,
  rename,
  rmdir,
  stat,
  unlink,
} from 'fs/promises';
import { constants } from 'fs';
import { basename, dirname, extname, join, normalize, resolve } from 'path';
import {
  BaseTool,
  ToolDefinition,
  ToolExecutionContext,
  ToolResult,
} from '../base-tool.js';

export interface MoveOptions {
  overwrite?: boolean;
  createBackup?: boolean;
  atomic?: boolean;
  createDirs?: boolean;
  dryRun?: boolean;
}

export interface MoveResult {
  sourcePath: string;
  destinationPath: string;
  operation: 'move' | 'rename' | 'copy';
  backupPath?: string;
  conflictResolved?: boolean;
  itemsMoved?: number;
}

export class MoveTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly blockedPaths: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'move',
      description:
        'Move or rename files and directories with conflict resolution and backup options',
      parameters: [
        {
          name: 'source',
          type: 'string',
          description: 'Source path (file or directory to move)',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Source path cannot be empty';
              if (value.length > 500)
                return 'Source path too long (max 500 characters)';
              return true;
            },
          },
        },
        {
          name: 'destination',
          type: 'string',
          description: 'Destination path',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Destination path cannot be empty';
              if (value.length > 500)
                return 'Destination path too long (max 500 characters)';
              return true;
            },
          },
        },
        {
          name: 'overwrite',
          type: 'boolean',
          description: 'Overwrite destination if it exists',
          default: false,
        },
        {
          name: 'createBackup',
          type: 'boolean',
          description: 'Create backup of destination if it exists',
          default: true,
        },
        {
          name: 'atomic',
          type: 'boolean',
          description:
            'Use atomic operations (copy then delete for cross-device moves)',
          default: true,
        },
        {
          name: 'createDirs',
          type: 'boolean',
          description: 'Create destination directories if they do not exist',
          default: false,
        },
        {
          name: 'dryRun',
          type: 'boolean',
          description: 'Preview the move operation without executing it',
          default: false,
        },
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['write_files', 'read_files'],
      safetyLevel: 'moderate',
      tags: ['file', 'move', 'rename', 'organize'],
      examples: [
        {
          description: 'Rename a file',
          parameters: {
            source: './old-name.txt',
            destination: './new-name.txt',
          },
        },
        {
          description: 'Move directory with backup',
          parameters: {
            source: './temp-folder',
            destination: './archive/temp-folder',
            createDirs: true,
            createBackup: true,
          },
        },
      ],
    };

    super(definition);

    this.maxFileSize = 100 * 1024 * 1024; // 100MB

    // Critical system paths that should not be moved
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
    ]);
  }

  async execute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    const {
      source: sourceInput,
      destination: destinationInput,
      overwrite = false,
      createBackup = true,
      atomic = true,
      createDirs = false,
      dryRun = false,
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize paths
      const sourcePath = this.normalizePath(
        sourceInput,
        context.workingDirectory
      );
      const destinationPath = this.normalizePath(
        destinationInput,
        context.workingDirectory
      );

      // Security and safety checks
      const safetyCheck = await this.performSafetyCheck(
        sourcePath,
        destinationPath,
        context
      );
      if (!safetyCheck.safe) {
        return {
          success: false,
          error: `Move denied: ${safetyCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Check if source exists
      let sourceStats;
      try {
        sourceStats = await stat(sourcePath);
      } catch (error: unknown) {
        const err = error as any;
        if (err.code === 'ENOENT') {
          return {
            success: false,
            error: 'Source path does not exist',
            performance: {
              executionTime: Date.now() - startTime,
            },
          };
        }
        throw error;
      }

      // Analyze the move operation
      const analysis = await this.analyzeMoveOperation(
        sourcePath,
        destinationPath,
        sourceStats
      );

      if (dryRun) {
        return {
          success: true,
          data: {
            sourcePath,
            destinationPath,
            dryRun: true,
            analysis,
            wouldOverwrite: analysis.destinationExists,
            operation: analysis.operationType,
          },
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Handle destination conflicts
      let backupPath: string | undefined;
      if (analysis.destinationExists) {
        if (!overwrite) {
          return {
            success: false,
            error: 'Destination exists and overwrite is false',
            data: {
              sourcePath,
              destinationPath,
              destinationExists: true,
            },
            performance: {
              executionTime: Date.now() - startTime,
            },
          };
        }

        if (createBackup) {
          backupPath = await this.createBackup(destinationPath);
        }
      }

      // Create destination directories if needed
      if (createDirs) {
        const destDir = dirname(destinationPath);
        await mkdir(destDir, { recursive: true });
      }

      // Perform the move operation
      const moveResult = await this.performMove(
        sourcePath,
        destinationPath,
        sourceStats,
        { atomic }
      );

      this.emit('executed', {
        source: sourcePath,
        destination: destinationPath,
        operation: moveResult.operation,
        backupCreated: !!backupPath,
        itemsMoved: moveResult.itemsMoved,
        success: true,
      });

      return {
        success: true,
        data: {
          ...moveResult,
          sourcePath,
          destinationPath,
          backupPath,
          analysis,
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: [
            sourcePath,
            destinationPath,
            ...(backupPath ? [backupPath] : []),
          ],
        },
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      this.emit('error', {
        source: sourceInput,
        destination: destinationInput,
        error: errorMessage,
        executionTime: Date.now() - startTime,
      });

      return {
        success: false,
        error: `Move operation failed: ${errorMessage}`,
        performance: {
          executionTime: Date.now() - startTime,
        },
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
    sourcePath: string,
    destinationPath: string,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check for critical system paths
    const normalizedSource = sourcePath.toLowerCase();
    const normalizedDest = destinationPath.toLowerCase();

    for (const blockedPath of this.blockedPaths) {
      if (
        normalizedSource.startsWith(blockedPath.toLowerCase()) ||
        normalizedDest.startsWith(blockedPath.toLowerCase())
      ) {
        return { safe: false, reason: 'Cannot move system critical paths' };
      }
    }

    // Check for path traversal attempts
    if (sourcePath.includes('..') || destinationPath.includes('..')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check if trying to move a directory into itself
    if (destinationPath.startsWith(sourcePath + '/')) {
      return { safe: false, reason: 'Cannot move directory into itself' };
    }

    // Check if source and destination are the same
    if (sourcePath === destinationPath) {
      return { safe: false, reason: 'Source and destination are the same' };
    }

    // Check if paths are within allowed directories
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const sourceAllowed = allowedDirs.some(dir =>
        sourcePath.startsWith(resolve(dir))
      );
      const destAllowed = allowedDirs.some(dir =>
        destinationPath.startsWith(resolve(dir))
      );

      if (!sourceAllowed || !destAllowed) {
        return {
          safe: false,
          reason: 'Source or destination is outside allowed directories',
        };
      }
    }

    // Check if trying to move current working directory
    if (sourcePath === context.workingDirectory) {
      return { safe: false, reason: 'Cannot move current working directory' };
    }

    return { safe: true };
  }

  private async analyzeMoveOperation(
    sourcePath: string,
    destinationPath: string,
    sourceStats: any
  ): Promise<{
    operationType: 'move' | 'rename';
    destinationExists: boolean;
    destinationStats?: any;
    sameDevice: boolean;
    isDirectory: boolean;
    estimatedSize: number;
    itemCount: number;
  }> {
    const sourceDir = dirname(sourcePath);
    const destDir = dirname(destinationPath);
    const operationType = sourceDir === destDir ? 'rename' : 'move';

    let destinationExists = false;
    let destinationStats;

    try {
      destinationStats = await stat(destinationPath);
      destinationExists = true;
    } catch (error: unknown) {
      const err = error as any;
      if (err.code !== 'ENOENT') {
        throw error;
      }
    }

    // Simple device check (might not be perfect across all platforms)
    const sameDevice = sourceDir.split('/')[1] === destDir.split('/')[1];

    let estimatedSize = sourceStats.size || 0;
    let itemCount = 1;

    if (sourceStats.isDirectory()) {
      const analysis = await this.analyzeDirectory(sourcePath);
      estimatedSize = analysis.totalSize;
      itemCount = analysis.itemCount;
    }

    return {
      operationType,
      destinationExists,
      destinationStats,
      sameDevice,
      isDirectory: sourceStats.isDirectory(),
      estimatedSize,
      itemCount,
    };
  }

  private async analyzeDirectory(
    dirPath: string
  ): Promise<{ totalSize: number; itemCount: number }> {
    let totalSize = 0;
    let itemCount = 0;

    try {
      const items = await readdir(dirPath);

      for (const item of items) {
        const itemPath = join(dirPath, item);
        try {
          const itemStats = await stat(itemPath);
          itemCount++;

          if (itemStats.isFile()) {
            totalSize += itemStats.size;
          } else if (itemStats.isDirectory()) {
            const subAnalysis = await this.analyzeDirectory(itemPath);
            totalSize += subAnalysis.totalSize;
            itemCount += subAnalysis.itemCount;
          }
        } catch (error) {
          // Skip items we can't access
          continue;
        }
      }
    } catch (error) {
      // Skip directories we can't read
    }

    return { totalSize, itemCount };
  }

  private async createBackup(destinationPath: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupDir = join(dirname(destinationPath), '.asi-backups');
    const backupName = `${basename(destinationPath)}.backup-${timestamp}`;
    const backupPath = join(backupDir, backupName);

    // Create backup directory
    await mkdir(backupDir, { recursive: true });

    try {
      const destStats = await stat(destinationPath);

      if (destStats.isFile()) {
        await copyFile(destinationPath, backupPath);
      } else if (destStats.isDirectory()) {
        await this.backupDirectory(destinationPath, backupPath);
      }
    } catch (error) {
      // If backup fails, we'll continue without it
      throw new Error(
        `Failed to create backup: ${error instanceof Error ? error.message : String(error)}`
      );
    }

    return backupPath;
  }

  private async backupDirectory(
    sourcePath: string,
    backupPath: string
  ): Promise<void> {
    await mkdir(backupPath, { recursive: true });

    try {
      const items = await readdir(sourcePath);

      for (const item of items) {
        const sourceItemPath = join(sourcePath, item);
        const backupItemPath = join(backupPath, item);

        try {
          const itemStats = await stat(sourceItemPath);

          if (itemStats.isFile()) {
            await copyFile(sourceItemPath, backupItemPath);
          } else if (itemStats.isDirectory()) {
            await this.backupDirectory(sourceItemPath, backupItemPath);
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

  private async performMove(
    sourcePath: string,
    destinationPath: string,
    sourceStats: any,
    options: { atomic: boolean }
  ): Promise<{ operation: 'move'; itemsMoved: number }> {
    let itemsMoved = 0;

    try {
      // Try atomic rename first (works if on same device)
      await rename(sourcePath, destinationPath);

      if (sourceStats.isDirectory()) {
        const analysis = await this.analyzeDirectory(destinationPath);
        itemsMoved = analysis.itemCount;
      } else {
        itemsMoved = 1;
      }
    } catch (error: unknown) {
      const err = error as any;

      // If rename fails (e.g., cross-device), use copy + delete
      if (err.code === 'EXDEV' || !options.atomic) {
        if (sourceStats.isFile()) {
          await copyFile(sourcePath, destinationPath);
          await unlink(sourcePath);
          itemsMoved = 1;
        } else if (sourceStats.isDirectory()) {
          itemsMoved = await this.copyDirectory(sourcePath, destinationPath);
          await this.removeDirectory(sourcePath);
        }
      } else {
        throw error;
      }
    }

    return {
      operation: 'move',
      itemsMoved,
    };
  }

  private async copyDirectory(
    sourcePath: string,
    destinationPath: string
  ): Promise<number> {
    let itemsCopied = 0;

    await mkdir(destinationPath, { recursive: true });
    itemsCopied++;

    try {
      const items = await readdir(sourcePath);

      for (const item of items) {
        const sourceItemPath = join(sourcePath, item);
        const destItemPath = join(destinationPath, item);

        try {
          const itemStats = await stat(sourceItemPath);

          if (itemStats.isFile()) {
            await copyFile(sourceItemPath, destItemPath);
            itemsCopied++;
          } else if (itemStats.isDirectory()) {
            const subItemsCopied = await this.copyDirectory(
              sourceItemPath,
              destItemPath
            );
            itemsCopied += subItemsCopied;
          }
        } catch (error) {
          // Skip items we can't copy
          continue;
        }
      }
    } catch (error) {
      // Skip directories we can't read
    }

    return itemsCopied;
  }

  private async removeDirectory(dirPath: string): Promise<void> {
    try {
      const items = await readdir(dirPath);

      // Remove all contents first
      for (const item of items) {
        const itemPath = join(dirPath, item);
        try {
          const itemStats = await stat(itemPath);

          if (itemStats.isFile()) {
            await unlink(itemPath);
          } else if (itemStats.isDirectory()) {
            await this.removeDirectory(itemPath);
          }
        } catch (error) {
          // Skip items we can't remove
          continue;
        }
      }

      // Remove the directory itself
      await rmdir(dirPath);
    } catch (error) {
      // Directory might already be empty or inaccessible
    }
  }

  async beforeExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<void> {
    await super.beforeExecute(parameters, context);

    if (
      !context.permissions.includes('write_files') ||
      !context.permissions.includes('read_files')
    ) {
      throw new Error(
        'Move tool requires both read_files and write_files permissions'
      );
    }

    console.log(
      `[MoveTool] Moving ${parameters.source} to ${parameters.destination} for user ${context.userId} (dryRun: ${parameters.dryRun || false})`
    );
  }
}

export default MoveTool;
