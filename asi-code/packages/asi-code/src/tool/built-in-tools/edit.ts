/**
 * Edit Tool - Advanced file editing with diff tracking and validation
 *
 * Provides sophisticated file editing capabilities with change tracking,
 * backup creation, validation, and rollback functionality.
 */

import { access, readFile, stat, writeFile } from 'fs/promises';
import { constants } from 'fs';
import { dirname, extname, normalize, resolve } from 'path';
import {
  BaseTool,
  ToolDefinition,
  ToolExecutionContext,
  ToolResult,
} from '../base-tool.js';

export interface EditOperation {
  type: 'replace' | 'insert' | 'delete' | 'append' | 'prepend';
  search?: string | RegExp;
  replacement?: string;
  position?: number;
  content?: string;
  lineNumber?: number;
  validateMatch?: boolean;
}

export interface EditDiff {
  oldContent: string;
  newContent: string;
  changes: Array<{
    type: 'added' | 'removed' | 'modified';
    lineNumber: number;
    oldLine?: string;
    newLine?: string;
  }>;
  statistics: {
    linesAdded: number;
    linesRemoved: number;
    linesModified: number;
  };
}

export class EditTool extends BaseTool {
  private readonly maxFileSize: number;
  private readonly allowedExtensions: Set<string>;

  constructor() {
    const definition: ToolDefinition = {
      name: 'edit',
      description:
        'Advanced file editing with diff tracking, validation, and rollback capabilities',
      parameters: [
        {
          name: 'path',
          type: 'string',
          description: 'Path to the file to edit',
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
          name: 'operation',
          type: 'object',
          description: 'Edit operation to perform',
          required: true,
          validation: {
            custom: (value: any) => {
              if (!value || typeof value !== 'object')
                return 'Operation must be an object';
              if (!value.type) return 'Operation type is required';
              const validTypes = [
                'replace',
                'insert',
                'delete',
                'append',
                'prepend',
              ];
              if (!validTypes.includes(value.type)) {
                return `Invalid operation type. Must be one of: ${validTypes.join(', ')}`;
              }
              return true;
            },
          },
        },
        {
          name: 'encoding',
          type: 'string',
          description: 'File encoding to use',
          default: 'utf8',
          enum: ['utf8', 'ascii', 'latin1'],
        },
        {
          name: 'createBackup',
          type: 'boolean',
          description: 'Create a backup before editing',
          default: true,
        },
        {
          name: 'validateSyntax',
          type: 'boolean',
          description:
            'Validate syntax after editing (for supported file types)',
          default: true,
        },
        {
          name: 'dryRun',
          type: 'boolean',
          description: 'Preview changes without applying them',
          default: false,
        },
      ],
      category: 'file',
      version: '1.0.0',
      author: 'ASI Team',
      permissions: ['write_files', 'read_files'],
      safetyLevel: 'moderate',
      tags: ['file', 'edit', 'diff', 'validation'],
      examples: [
        {
          description: 'Replace text in a file',
          parameters: {
            path: './config.json',
            operation: {
              type: 'replace',
              search: '"debug": false',
              replacement: '"debug": true',
            },
          },
        },
        {
          description: 'Insert content at specific line',
          parameters: {
            path: './script.js',
            operation: {
              type: 'insert',
              lineNumber: 10,
              content: 'console.log("Debug point");',
            },
          },
        },
      ],
    };

    super(definition);

    this.maxFileSize = 5 * 1024 * 1024; // 5MB

    // File extensions that support syntax validation
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
      '.sql',
    ]);
  }

  async execute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    const {
      path: inputPath,
      operation,
      encoding = 'utf8',
      createBackup = true,
      validateSyntax = true,
      dryRun = false,
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
        operation,
        context
      );
      if (!securityCheck.safe) {
        return {
          success: false,
          error: `Edit denied: ${securityCheck.reason}`,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Check file access
      await this.checkFileAccess(normalizedPath);

      // Read original content
      const originalContent = await readFile(normalizedPath, encoding);

      // Apply edit operation
      const editResult = await this.applyEditOperation(
        originalContent.toString(),
        operation
      );
      if (!editResult.success) {
        return {
          success: false,
          error: editResult.error,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      const newContent = editResult.content!;

      // Generate diff
      const diff = this.generateDiff(originalContent.toString(), newContent);

      // Validate syntax if requested
      let syntaxValid = true;
      let syntaxError = '';

      if (validateSyntax && this.supportsSyntaxValidation(normalizedPath)) {
        const validation = await this.validateSyntax(
          normalizedPath,
          newContent
        );
        syntaxValid = validation.valid;
        syntaxError = validation.error;
      }

      // If dry run, return preview without making changes
      if (dryRun) {
        return {
          success: true,
          data: {
            path: normalizedPath,
            operation,
            diff,
            syntaxValid,
            syntaxError: syntaxError || undefined,
            preview: true,
            changes: diff.changes,
            statistics: diff.statistics,
          },
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Don't proceed if syntax validation failed
      if (!syntaxValid) {
        return {
          success: false,
          error: `Syntax validation failed: ${syntaxError}`,
          warnings: ['Changes were not applied due to syntax errors'],
          data: {
            diff,
            syntaxError,
          },
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      let backupPath: string | undefined;

      // Create backup if requested
      if (createBackup) {
        backupPath = await this.createBackup(
          normalizedPath,
          originalContent.toString()
        );
      }

      // Write the edited content
      await writeFile(normalizedPath, newContent, { encoding });

      this.emit('executed', {
        path: normalizedPath,
        operation: operation.type,
        linesChanged:
          diff.statistics.linesAdded +
          diff.statistics.linesRemoved +
          diff.statistics.linesModified,
        backupCreated: !!backupPath,
        success: true,
      });

      return {
        success: true,
        data: {
          path: normalizedPath,
          operation,
          diff,
          backupPath,
          syntaxValid,
          changes: diff.changes,
          statistics: diff.statistics,
          originalSize: originalContent.length,
          newSize: newContent.length,
        },
        performance: {
          executionTime: Date.now() - startTime,
          resourcesAccessed: [
            normalizedPath,
            ...(backupPath ? [backupPath] : []),
          ],
        },
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      this.emit('error', {
        path: inputPath,
        operation: operation?.type,
        error: errorMessage,
        executionTime: Date.now() - startTime,
      });

      return {
        success: false,
        error: `Failed to edit file: ${errorMessage}`,
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
    filePath: string,
    operation: EditOperation,
    context: ToolExecutionContext
  ): Promise<{ safe: boolean; reason?: string }> {
    // Check for path traversal
    if (filePath.includes('..')) {
      return { safe: false, reason: 'Path traversal detected' };
    }

    // Check file extension
    const ext = extname(filePath).toLowerCase();
    if (
      ext &&
      !this.allowedExtensions.has(ext) &&
      !context.permissions.includes('edit_any_file')
    ) {
      return {
        safe: false,
        reason: `File type '${ext}' not allowed without edit_any_file permission`,
      };
    }

    // Check operation content for dangerous patterns
    const content = operation.replacement || operation.content || '';
    const dangerousPatterns = [
      /<script\s/i,
      /javascript:/i,
      /eval\s*\(/i,
      /exec\s*\(/i,
      /system\s*\(/i,
      /rm\s+-rf/i,
      /sudo\s/i,
    ];

    if (!context.permissions.includes('edit_dangerous_content')) {
      for (const pattern of dangerousPatterns) {
        if (pattern.test(content)) {
          return {
            safe: false,
            reason: 'Operation contains potentially dangerous content',
          };
        }
      }
    }

    return { safe: true };
  }

  private async checkFileAccess(filePath: string): Promise<void> {
    try {
      await access(filePath, constants.R_OK | constants.W_OK);
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

    const fileStats = await stat(filePath);
    if (fileStats.size > this.maxFileSize) {
      throw new Error(
        `File too large (${fileStats.size} bytes, max ${this.maxFileSize} bytes)`
      );
    }
  }

  private async applyEditOperation(
    content: string,
    operation: EditOperation
  ): Promise<{ success: boolean; content?: string; error?: string }> {
    try {
      switch (operation.type) {
        case 'replace':
          return this.applyReplace(content, operation);
        case 'insert':
          return this.applyInsert(content, operation);
        case 'delete':
          return this.applyDelete(content, operation);
        case 'append':
          return this.applyAppend(content, operation);
        case 'prepend':
          return this.applyPrepend(content, operation);
        default:
          return {
            success: false,
            error: `Unknown operation type: ${operation.type}`,
          };
      }
    } catch (error) {
      return {
        success: false,
        error: `Operation failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  private applyReplace(
    content: string,
    operation: EditOperation
  ): { success: boolean; content?: string; error?: string } {
    if (!operation.search || operation.replacement === undefined) {
      return {
        success: false,
        error: 'Replace operation requires search and replacement parameters',
      };
    }

    let newContent: string;
    let matchFound = false;

    if (typeof operation.search === 'string') {
      matchFound = content.includes(operation.search);
      newContent = content.replace(operation.search, operation.replacement);
    } else if (operation.search instanceof RegExp) {
      matchFound = operation.search.test(content);
      newContent = content.replace(operation.search, operation.replacement);
    } else {
      return {
        success: false,
        error: 'Search parameter must be a string or RegExp',
      };
    }

    if (operation.validateMatch && !matchFound) {
      return { success: false, error: 'Search pattern not found in file' };
    }

    return { success: true, content: newContent };
  }

  private applyInsert(
    content: string,
    operation: EditOperation
  ): { success: boolean; content?: string; error?: string } {
    if (!operation.content) {
      return {
        success: false,
        error: 'Insert operation requires content parameter',
      };
    }

    if (operation.lineNumber !== undefined) {
      const lines = content.split('\n');
      const lineIndex = operation.lineNumber - 1;

      if (lineIndex < 0 || lineIndex > lines.length) {
        return {
          success: false,
          error: `Invalid line number: ${operation.lineNumber}`,
        };
      }

      lines.splice(lineIndex, 0, operation.content);
      return { success: true, content: lines.join('\n') };
    } else if (operation.position !== undefined) {
      if (operation.position < 0 || operation.position > content.length) {
        return {
          success: false,
          error: `Invalid position: ${operation.position}`,
        };
      }

      const newContent =
        content.slice(0, operation.position) +
        operation.content +
        content.slice(operation.position);
      return { success: true, content: newContent };
    }

    return {
      success: false,
      error: 'Insert operation requires lineNumber or position parameter',
    };
  }

  private applyDelete(
    content: string,
    operation: EditOperation
  ): { success: boolean; content?: string; error?: string } {
    if (operation.search) {
      let newContent: string;
      if (typeof operation.search === 'string') {
        newContent = content.replace(operation.search, '');
      } else if (operation.search instanceof RegExp) {
        newContent = content.replace(operation.search, '');
      } else {
        return {
          success: false,
          error: 'Search parameter must be a string or RegExp',
        };
      }
      return { success: true, content: newContent };
    } else if (operation.lineNumber !== undefined) {
      const lines = content.split('\n');
      const lineIndex = operation.lineNumber - 1;

      if (lineIndex < 0 || lineIndex >= lines.length) {
        return {
          success: false,
          error: `Invalid line number: ${operation.lineNumber}`,
        };
      }

      lines.splice(lineIndex, 1);
      return { success: true, content: lines.join('\n') };
    }

    return {
      success: false,
      error: 'Delete operation requires search or lineNumber parameter',
    };
  }

  private applyAppend(
    content: string,
    operation: EditOperation
  ): { success: boolean; content?: string; error?: string } {
    if (!operation.content) {
      return {
        success: false,
        error: 'Append operation requires content parameter',
      };
    }

    return { success: true, content: content + operation.content };
  }

  private applyPrepend(
    content: string,
    operation: EditOperation
  ): { success: boolean; content?: string; error?: string } {
    if (!operation.content) {
      return {
        success: false,
        error: 'Prepend operation requires content parameter',
      };
    }

    return { success: true, content: operation.content + content };
  }

  private generateDiff(oldContent: string, newContent: string): EditDiff {
    const oldLines = oldContent.split('\n');
    const newLines = newContent.split('\n');

    const changes: EditDiff['changes'] = [];
    let linesAdded = 0;
    let linesRemoved = 0;
    let linesModified = 0;

    // Simple diff algorithm (can be enhanced with more sophisticated algorithms)
    const maxLines = Math.max(oldLines.length, newLines.length);

    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i];
      const newLine = newLines[i];

      if (oldLine === undefined && newLine !== undefined) {
        // Line added
        changes.push({
          type: 'added',
          lineNumber: i + 1,
          newLine,
        });
        linesAdded++;
      } else if (oldLine !== undefined && newLine === undefined) {
        // Line removed
        changes.push({
          type: 'removed',
          lineNumber: i + 1,
          oldLine,
        });
        linesRemoved++;
      } else if (oldLine !== newLine) {
        // Line modified
        changes.push({
          type: 'modified',
          lineNumber: i + 1,
          oldLine,
          newLine,
        });
        linesModified++;
      }
    }

    return {
      oldContent,
      newContent,
      changes,
      statistics: {
        linesAdded,
        linesRemoved,
        linesModified,
      },
    };
  }

  private async createBackup(
    filePath: string,
    content: string
  ): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = `${filePath}.backup-${timestamp}`;

    await writeFile(backupPath, content, 'utf8');
    return backupPath;
  }

  private supportsSyntaxValidation(filePath: string): boolean {
    const ext = extname(filePath).toLowerCase();
    return ['.json', '.js', '.ts', '.jsx', '.tsx', '.yaml', '.yml'].includes(
      ext
    );
  }

  private async validateSyntax(
    filePath: string,
    content: string
  ): Promise<{ valid: boolean; error: string }> {
    const ext = extname(filePath).toLowerCase();

    try {
      switch (ext) {
        case '.json':
          JSON.parse(content);
          return { valid: true, error: '' };

        case '.yaml':
        case '.yml':
          // Basic YAML validation (would need yaml parser for full validation)
          if (content.includes('\t')) {
            return { valid: false, error: 'YAML should not contain tabs' };
          }
          return { valid: true, error: '' };

        case '.js':
        case '.jsx':
        case '.ts':
        case '.tsx':
          // Basic syntax check for obvious errors
          const jsErrors = this.validateJavaScriptBasic(content);
          return jsErrors.length > 0
            ? { valid: false, error: jsErrors.join(', ') }
            : { valid: true, error: '' };

        default:
          return { valid: true, error: '' };
      }
    } catch (error) {
      return {
        valid: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  private validateJavaScriptBasic(content: string): string[] {
    const errors: string[] = [];

    // Check for unmatched braces
    const braceCount =
      (content.match(/\{/g) || []).length - (content.match(/\}/g) || []).length;
    if (braceCount !== 0) {
      errors.push('Unmatched braces');
    }

    // Check for unmatched parentheses
    const parenCount =
      (content.match(/\(/g) || []).length - (content.match(/\)/g) || []).length;
    if (parenCount !== 0) {
      errors.push('Unmatched parentheses');
    }

    // Check for unmatched brackets
    const bracketCount =
      (content.match(/\[/g) || []).length - (content.match(/\]/g) || []).length;
    if (bracketCount !== 0) {
      errors.push('Unmatched brackets');
    }

    return errors;
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
        'Edit tool requires both read_files and write_files permissions'
      );
    }

    console.log(
      `[EditTool] Editing file for user ${context.userId}: ${parameters.path} (${parameters.operation.type})`
    );
  }
}

export default EditTool;
