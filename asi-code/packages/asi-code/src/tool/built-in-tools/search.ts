/**
 * Search Tool - Advanced code and text searching with pattern matching
 *
 * Provides sophisticated search capabilities including regex patterns,
 * file type filtering, and content analysis.
 */

import { access, readFile, stat } from 'fs/promises';
import { constants } from 'fs';
import { basename, dirname, extname, normalize, resolve } from 'path';
import { glob } from 'glob';
import {
  BaseTool,
  ToolDefinition,
  ToolExecutionContext,
  ToolResult,
} from '../base-tool.js';

export interface SearchOptions {
  pattern?: string | RegExp;
  filePattern?: string;
  includeHidden?: boolean;
  maxDepth?: number;
  ignoreCase?: boolean;
  wholeWord?: boolean;
  context?: number;
}

export interface SearchResult {
  file: string;
  matches: Array<{
    line: number;
    column: number;
    text: string;
    context?: {
      before: string[];
      after: string[];
    };
  }>;
  totalMatches: number;
}

export class SearchTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly allowedExtensions: Set<string>;
  private readonly blockedPaths: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'search',
      description:
        'Search for text patterns in files with advanced filtering and context',
      parameters: [
        {
          name: 'query',
          type: 'string',
          description: 'Text pattern to search for',
          required: true,
          validation: {
            custom: (value: string) => {
              if (!value.trim()) return 'Search query cannot be empty';
              if (value.length > 500)
                return 'Search query too long (max 500 characters)';
              return true;
            },
          },
        },
        {
          name: 'path',
          type: 'string',
          description: 'Directory or file to search in',
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
          name: 'filePattern',
          type: 'string',
          description: 'Glob pattern for files to include',
          default: '**/*',
        },
        {
          name: 'ignoreCase',
          type: 'boolean',
          description: 'Case-insensitive search',
          default: false,
        },
        {
          name: 'wholeWord',
          type: 'boolean',
          description: 'Match whole words only',
          default: false,
        },
        {
          name: 'useRegex',
          type: 'boolean',
          description: 'Treat query as regular expression',
          default: false,
        },
        {
          name: 'context',
          type: 'number',
          description: 'Number of context lines before and after matches',
          default: 0,
          validation: {
            min: 0,
            max: 10,
          },
        },
        {
          name: 'maxDepth',
          type: 'number',
          description: 'Maximum directory depth to search',
          default: 10,
          validation: {
            min: 1,
            max: 20,
          },
        },
        {
          name: 'includeHidden',
          type: 'boolean',
          description: 'Include hidden files and directories',
          default: false,
        },
        {
          name: 'maxResults',
          type: 'number',
          description: 'Maximum number of files to return results from',
          default: 100,
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
      tags: ['search', 'file', 'text', 'analysis'],
      examples: [
        {
          description: 'Search for function definitions in JavaScript files',
          parameters: {
            query: 'function\\s+\\w+',
            filePattern: '**/*.js',
            useRegex: true,
          },
        },
        {
          description: 'Case-insensitive search with context',
          parameters: {
            query: 'TODO',
            ignoreCase: true,
            context: 2,
          },
        },
      ],
    };

    super(definition);

    this.maxFileSize = 2 * 1024 * 1024; // 2MB per file

    // Allowed file extensions for searching
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
      '.properties',
      '.template',
      '.example',
      '.sample',
    ]);

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
      query,
      path = '.',
      filePattern = '**/*',
      ignoreCase = false,
      wholeWord = false,
      useRegex = false,
      context: contextLines = 0,
      maxDepth = 10,
      includeHidden = false,
      maxResults = 100,
    } = parameters;

    const startTime = Date.now();

    try {
      // Normalize path
      const normalizedPath = this.normalizePath(path, context.workingDirectory);

      // Security checks
      const securityCheck = await this.performSecurityCheck(
        normalizedPath,
        query,
        context
      );
      if (!securityCheck.safe) {
        return {
          success: false,
          error: `Search denied: ${securityCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Build search pattern
      const searchPattern = this.buildSearchPattern(query, {
        ignoreCase,
        wholeWord,
        useRegex,
      });

      // Find files to search
      const files = await this.findFiles(normalizedPath, filePattern, {
        includeHidden,
        maxDepth,
        maxResults,
      });

      // Perform search
      const results: SearchResult[] = [];
      let totalMatches = 0;
      let filesSearched = 0;

      for (const file of files.slice(0, maxResults)) {
        try {
          const searchResult = await this.searchInFile(
            file,
            searchPattern,
            contextLines
          );
          if (searchResult.totalMatches > 0) {
            results.push(searchResult);
            totalMatches += searchResult.totalMatches;
          }
          filesSearched++;
        } catch (error) {
          // Skip files that can't be read
          continue;
        }
      }

      this.emit('executed', {
        query,
        path: normalizedPath,
        filesSearched,
        totalMatches,
        success: true,
      });

      return {
        success: true,
        data: {
          query,
          path: normalizedPath,
          results,
          statistics: {
            filesFound: files.length,
            filesSearched,
            filesWithMatches: results.length,
            totalMatches,
            searchPattern: useRegex ? query : searchPattern.source,
          },
          options: {
            ignoreCase,
            wholeWord,
            useRegex,
            contextLines,
            filePattern,
          },
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: results.map(r => r.file),
        },
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      this.emit('error', {
        query,
        path,
        error: errorMessage,
        executionTime: Date.now() - startTime,
      });

      return {
        success: false,
        error: `Search failed: ${errorMessage}`,
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
    searchPath: string,
    query: string,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check for path traversal
    if (searchPath.includes('..')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check blocked paths
    const normalizedPath = searchPath.toLowerCase();
    for (const blockedPath of this.blockedPaths) {
      if (normalizedPath.startsWith(blockedPath.toLowerCase())) {
        return { safe: false, reason: 'Path is blocked for security reasons' };
      }
    }

    // Check for potentially dangerous regex patterns
    if (query.length > 500) {
      return { safe: false, reason: 'Query too long (potential ReDoS attack)' };
    }

    // Check for resource-intensive regex patterns
    const dangerousPatterns = [
      /\(\?\!\.\*\)\.\*/, // Negative lookahead with greedy quantifier
      /\\1|\\2|\\3|\\4|\\5|\\6|\\7|\\8|\\9/, // Backreferences without preceding capturing groups
      /\[\^\]\*\+/, // Character class with nested quantifiers
    ];

    try {
      const regex = new RegExp(query);
      for (const pattern of dangerousPatterns) {
        if (pattern.test(query)) {
          return {
            safe: false,
            reason: 'Query contains potentially dangerous regex pattern',
          };
        }
      }
    } catch (error) {
      // Invalid regex will be handled later
    }

    // Check if path is within allowed directories
    if (context.metadata?.allowedDirectories) {
      const allowedDirs = context.metadata.allowedDirectories as string[];
      const isAllowed = allowedDirs.some(dir =>
        searchPath.startsWith(resolve(dir))
      );
      if (!isAllowed) {
        return { safe: false, reason: 'Path is outside allowed directories' };
      }
    }

    return { safe: true };
  }

  private buildSearchPattern(
    query: string,
    options: {
      ignoreCase: boolean;
      wholeWord: boolean;
      useRegex: boolean;
    }
  ): RegExp {
    let pattern = query;
    let flags = '';

    if (options.ignoreCase) {
      flags += 'i';
    }

    if (!options.useRegex) {
      // Escape special regex characters
      pattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    if (options.wholeWord) {
      pattern = `\\b${pattern}\\b`;
    }

    flags += 'g'; // Always use global flag for finding all matches

    return new RegExp(pattern, flags);
  }

  private async findFiles(
    searchPath: string,
    filePattern: string,
    options: {
      includeHidden: boolean;
      maxDepth: number;
      maxResults: number;
    }
  ): Promise<string[]> {
    try {
      const stats = await stat(searchPath);

      if (stats.isFile()) {
        return [searchPath];
      }

      const globOptions: any = {
        cwd: searchPath,
        absolute: true,
        nodir: true,
        maxDepth: options.maxDepth,
      };

      if (!options.includeHidden) {
        globOptions.ignore = ['**/.*', '**/node_modules/**'];
      } else {
        globOptions.ignore = ['**/node_modules/**'];
      }

      const files = await glob(filePattern, globOptions);

      // Filter by allowed extensions and security checks
      const filteredFiles: string[] = [];

      for (const file of files.slice(0, options.maxResults * 2)) {
        // Get more to account for filtering
        const ext = extname(file).toLowerCase();

        // Skip if extension not allowed
        if (ext && !this.allowedExtensions.has(ext)) {
          continue;
        }

        // Check file size
        try {
          const fileStats = await stat(file);
          if (fileStats.size > this.maxFileSize) {
            continue;
          }

          // Check read permission
          await access(file, constants.R_OK);
          filteredFiles.push(file);

          if (filteredFiles.length >= options.maxResults) {
            break;
          }
        } catch (error) {
          // Skip files we can't access
          continue;
        }
      }

      return filteredFiles;
    } catch (error) {
      throw new Error(
        `Cannot access search path: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }

  private async searchInFile(
    filePath: string,
    pattern: RegExp,
    contextLines: number
  ): Promise<SearchResult> {
    const content = await readFile(filePath, 'utf8');
    const lines = content.split('\n');
    const matches: SearchResult['matches'] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineMatches = [...line.matchAll(pattern)];

      for (const match of lineMatches) {
        const matchInfo: SearchResult['matches'][0] = {
          line: i + 1,
          column: (match.index || 0) + 1,
          text: match[0],
        };

        // Add context if requested
        if (contextLines > 0) {
          const beforeStart = Math.max(0, i - contextLines);
          const afterEnd = Math.min(lines.length - 1, i + contextLines);

          matchInfo.context = {
            before: lines.slice(beforeStart, i),
            after: lines.slice(i + 1, afterEnd + 1),
          };
        }

        matches.push(matchInfo);
      }
    }

    return {
      file: filePath,
      matches,
      totalMatches: matches.length,
    };
  }

  async beforeExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<void> {
    await super.beforeExecute(parameters, context);

    if (!context.permissions.includes('read_files')) {
      throw new Error('Search tool requires read_files permission');
    }

    console.log(
      `[SearchTool] Searching for '${parameters.query}' for user ${context.userId} in ${parameters.path || '.'}`
    );
  }
}

export default SearchTool;
