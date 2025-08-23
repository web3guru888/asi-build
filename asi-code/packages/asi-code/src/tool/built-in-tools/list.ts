/**
 * List Tool - Advanced directory listing with filtering and analysis
 *
 * Provides comprehensive directory listing capabilities with metadata,
 * filtering options, and file analysis features.
 */

import { access, readdir, stat } from 'fs/promises';
import { constants } from 'fs';
import { basename, dirname, extname, join, normalize, resolve } from 'path';
import {
  BaseTool,
  ToolDefinition,
  ToolExecutionContext,
  ToolResult,
} from '../base-tool.js';

export interface ListOptions {
  recursive?: boolean;
  showHidden?: boolean;
  includeStats?: boolean;
  sortBy?: 'name' | 'size' | 'modified' | 'created' | 'type';
  sortOrder?: 'asc' | 'desc';
  filter?: {
    extensions?: string[];
    sizeMin?: number;
    sizeMax?: number;
    typeFilter?: 'files' | 'directories' | 'all';
  };
  maxDepth?: number;
  maxResults?: number;
}

export interface FileInfo {
  name: string;
  path: string;
  type: 'file' | 'directory' | 'symlink' | 'other';
  size: number;
  modified: Date;
  created: Date;
  permissions: {
    readable: boolean;
    writable: boolean;
    executable: boolean;
  };
  extension?: string;
  isHidden: boolean;
  depth: number;
}

export interface ListResult {
  path: string;
  items: FileInfo[];
  statistics: {
    totalItems: number;
    files: number;
    directories: number;
    totalSize: number;
    largestFile: { name: string; size: number } | null;
    extensions: Record<string, number>;
  };
  options: ListOptions;
}

export class ListTool extends BaseTool {
  private readonly blockedPaths: Set<string>;
  private readonly maxDepth: number = 20;
  private readonly maxResults: number = 1000;

  constructor() {
    const definition: ToolDefinition = {
      name: 'list',
      description:
        'List directory contents with advanced filtering, sorting, and metadata analysis',
      parameters: [
        {
          name: 'path',
          type: 'string',
          description: 'Directory path to list',
          default: '.',
          validation: {
            custom: (value: string) => {
              if (value.length > 500)
                return 'Path too long (max 500 characters)';
              return true;
            },
          },
        },
        {
          name: 'recursive',
          type: 'boolean',
          description: 'List contents recursively',
          default: false,
        },
        {
          name: 'showHidden',
          type: 'boolean',
          description: 'Include hidden files and directories',
          default: false,
        },
        {
          name: 'includeStats',
          type: 'boolean',
          description: 'Include detailed file statistics',
          default: true,
        },
        {
          name: 'sortBy',
          type: 'string',
          description: 'Sort results by field',
          default: 'name',
          enum: ['name', 'size', 'modified', 'created', 'type'],
        },
        {
          name: 'sortOrder',
          type: 'string',
          description: 'Sort order',
          default: 'asc',
          enum: ['asc', 'desc'],
        },
        {
          name: 'typeFilter',
          type: 'string',
          description: 'Filter by item type',
          default: 'all',
          enum: ['files', 'directories', 'all'],
        },
        {
          name: 'extensions',
          type: 'array',
          description: 'Filter by file extensions (e.g., [".js", ".ts"])',
        },
        {
          name: 'sizeMin',
          type: 'number',
          description: 'Minimum file size in bytes',
          validation: {
            min: 0,
          },
        },
        {
          name: 'sizeMax',
          type: 'number',
          description: 'Maximum file size in bytes',
          validation: {
            min: 0,
          },
        },
        {
          name: 'maxDepth',
          type: 'number',
          description: 'Maximum recursion depth',
          default: 5,
          validation: {
            min: 1,
            max: 20,
          },
        },
        {
          name: 'maxResults',
          type: 'number',
          description: 'Maximum number of results to return',
          default: 500,
          validation: {
            min: 1,
            max: 1000,
          },
        },
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['read_files'],
      safetyLevel: 'safe',
      tags: ['file', 'directory', 'list', 'analysis'],
      examples: [
        {
          description: 'List current directory with details',
          parameters: {
            path: '.',
            includeStats: true,
          },
        },
        {
          description: 'Recursively list JavaScript files',
          parameters: {
            path: './src',
            recursive: true,
            extensions: ['.js', '.ts'],
            sortBy: 'size',
            sortOrder: 'desc',
          },
        },
      ],
    };

    super(definition);

    // Blocked paths for security
    this.blockedPaths = new Set([
      '/etc/passwd',
      '/etc/shadow',
      '/etc/group',
      '/etc/hosts',
      '/proc',
      '/sys',
      '/dev',
      '/var/log/auth.log',
      '/var/log/secure',
    ]);
  }

  async execute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    const {
      path: inputPath = '.',
      recursive = false,
      showHidden = false,
      includeStats = true,
      sortBy = 'name',
      sortOrder = 'asc',
      typeFilter = 'all',
      extensions,
      sizeMin,
      sizeMax,
      maxDepth = 5,
      maxResults = 500,
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize path
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
          error: `List denied: ${securityCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Check if path exists and is accessible
      try {
        await access(normalizedPath, constants.R_OK);
        const pathStats = await stat(normalizedPath);

        if (!pathStats.isDirectory()) {
          return {
            success: false,
            error: 'Path is not a directory',
            performance: {
              executionTime: Date.now() - startTime,
            },
          };
        }
      } catch (error: unknown) {
        const err = error as any;
        if (err.code === 'ENOENT') {
          return {
            success: false,
            error: 'Directory not found',
            performance: {
              executionTime: Date.now() - startTime,
            },
          };
        } else if (err.code === 'EACCES') {
          return {
            success: false,
            error: 'Permission denied',
            performance: {
              executionTime: Date.now() - startTime,
            },
          };
        }
        throw error;
      }

      // Build filter options
      const filterOptions = {
        extensions: extensions
          ? extensions.map((ext: string) => ext.toLowerCase())
          : undefined,
        sizeMin,
        sizeMax,
        typeFilter,
      };

      const listOptions: ListOptions = {
        recursive,
        showHidden,
        includeStats,
        sortBy,
        sortOrder,
        filter: filterOptions,
        maxDepth: Math.min(maxDepth, this.maxDepth),
        maxResults: Math.min(maxResults, this.maxResults),
      };

      // List directory contents
      const items = await this.listDirectory(normalizedPath, listOptions, 0);

      // Apply sorting
      const sortedItems = this.sortItems(items, sortBy, sortOrder);

      // Calculate statistics
      const statistics = this.calculateStatistics(sortedItems);

      this.emit('executed', {
        path: normalizedPath,
        itemsFound: sortedItems.length,
        success: true,
      });

      return {
        success: true,
        data: {
          path: normalizedPath,
          items: sortedItems.slice(0, listOptions.maxResults!),
          statistics,
          options: listOptions,
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
        error: `List operation failed: ${errorMessage}`,
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

  private async performSecurityCheck(
    listPath: string,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check for path traversal
    if (listPath.includes('..')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check blocked paths
    const normalizedPath = listPath.toLowerCase();
    for (const blockedPath of this.blockedPaths) {
      if (normalizedPath.startsWith(blockedPath.toLowerCase())) {
        return { safe: false, reason: 'Path is blocked for security reasons' };
      }
    }

    // Check if path is within allowed directories
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const isAllowed = allowedDirs.some(dir =>
        listPath.startsWith(resolve(dir))
      );
      if (!isAllowed) {
        return { safe: false, reason: 'Path is outside allowed directories' };
      }
    }

    return { safe: true };
  }

  private async listDirectory(
    dirPath: string,
    options: ListOptions,
    currentDepth: number
  ): Promise<FileInfo[]> {
    const items: FileInfo[] = [];

    if (currentDepth >= (options.maxDepth || this.maxDepth)) {
      return items;
    }

    try {
      const entries = await readdir(dirPath);

      for (const entry of entries) {
        // Check if we've reached the maximum results
        if (items.length >= (options.maxResults || this.maxResults)) {
          break;
        }

        const itemPath = join(dirPath, entry);

        // Skip hidden files if not requested
        if (!options.showHidden && entry.startsWith('.')) {
          continue;
        }

        try {
          const itemInfo = await this.getFileInfo(
            itemPath,
            currentDepth,
            options.includeStats || false
          );

          // Apply filters
          if (!this.passesFilter(itemInfo, options.filter)) {
            continue;
          }

          items.push(itemInfo);

          // Recurse into directories if requested
          if (options.recursive && itemInfo.type === 'directory') {
            const subItems = await this.listDirectory(
              itemPath,
              options,
              currentDepth + 1
            );
            items.push(...subItems);
          }
        } catch (error) {
          // Skip items we can't access
          continue;
        }
      }
    } catch (error) {
      // Skip directories we can't read
    }

    return items;
  }

  private async getFileInfo(
    itemPath: string,
    depth: number,
    includeStats: boolean
  ): Promise<FileInfo> {
    const stats = await stat(itemPath);
    const name = basename(itemPath);
    const ext = extname(name);

    let type: FileInfo['type'];
    if (stats.isFile()) {
      type = 'file';
    } else if (stats.isDirectory()) {
      type = 'directory';
    } else if (stats.isSymbolicLink()) {
      type = 'symlink';
    } else {
      type = 'other';
    }

    const permissions = {
      readable: false,
      writable: false,
      executable: false,
    };

    if (includeStats) {
      try {
        await access(itemPath, constants.R_OK);
        permissions.readable = true;
      } catch {}

      try {
        await access(itemPath, constants.W_OK);
        permissions.writable = true;
      } catch {}

      try {
        await access(itemPath, constants.X_OK);
        permissions.executable = true;
      } catch {}
    }

    return {
      name,
      path: itemPath,
      type,
      size: stats.size,
      modified: stats.mtime,
      created: stats.ctime,
      permissions,
      extension: ext || undefined,
      isHidden: name.startsWith('.'),
      depth,
    };
  }

  private passesFilter(
    item: FileInfo,
    filter?: ListOptions['filter']
  ): boolean {
    if (!filter) return true;

    // Type filter
    if (filter.typeFilter === 'files' && item.type !== 'file') return false;
    if (filter.typeFilter === 'directories' && item.type !== 'directory')
      return false;

    // Extension filter (only for files)
    if (filter.extensions && item.type === 'file') {
      if (
        !item.extension ||
        !filter.extensions.includes(item.extension.toLowerCase())
      ) {
        return false;
      }
    }

    // Size filters (only for files)
    if (item.type === 'file') {
      if (filter.sizeMin !== undefined && item.size < filter.sizeMin)
        return false;
      if (filter.sizeMax !== undefined && item.size > filter.sizeMax)
        return false;
    }

    return true;
  }

  private sortItems(
    items: FileInfo[],
    sortBy: string,
    sortOrder: string
  ): FileInfo[] {
    const sorted = [...items];

    sorted.sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'size':
          comparison = a.size - b.size;
          break;
        case 'modified':
          comparison = a.modified.getTime() - b.modified.getTime();
          break;
        case 'created':
          comparison = a.created.getTime() - b.created.getTime();
          break;
        case 'type':
          comparison = a.type.localeCompare(b.type);
          break;
        default:
          comparison = a.name.localeCompare(b.name);
      }

      return sortOrder === 'desc' ? -comparison : comparison;
    });

    return sorted;
  }

  private calculateStatistics(items: FileInfo[]): ListResult['statistics'] {
    const stats = {
      totalItems: items.length,
      files: 0,
      directories: 0,
      totalSize: 0,
      largestFile: null as { name: string; size: number } | null,
      extensions: {} as Record<string, number>,
    };

    let largestSize = 0;

    for (const item of items) {
      if (item.type === 'file') {
        stats.files++;
        stats.totalSize += item.size;

        if (item.size > largestSize) {
          largestSize = item.size;
          stats.largestFile = { name: item.name, size: item.size };
        }

        if (item.extension) {
          const ext = item.extension.toLowerCase();
          stats.extensions[ext] = (stats.extensions[ext] || 0) + 1;
        }
      } else if (item.type === 'directory') {
        stats.directories++;
      }
    }

    return stats;
  }

  async beforeExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<void> {
    await super.beforeExecute(parameters, context);

    if (!context.permissions.includes('read_files')) {
      throw new Error('List tool requires read_files permission');
    }

    console.log(
      `[ListTool] Listing directory ${parameters.path || '.'} for user ${context.userId} (recursive: ${parameters.recursive || false})`
    );
  }
}

export default ListTool;
