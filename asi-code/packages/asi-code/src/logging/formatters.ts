/**
 * Log Formatters
 *
 * Comprehensive log formatting system supporting multiple output formats
 * including console, file, and JSON formats with customizable options.
 */

import { inspect } from 'util';

// Log entry interface
export interface LogEntry {
  readonly timestamp: Date;
  readonly level: 'debug' | 'info' | 'warn' | 'error';
  readonly message: string;
  readonly metadata?: Record<string, any>;
  readonly error?: Error;
  readonly context?: string;
  readonly requestId?: string;
  readonly userId?: string;
  readonly subsystem?: string;
  readonly component?: string;
}

// Formatter options
export interface FormatterOptions {
  readonly includeTimestamp?: boolean;
  readonly includeLevel?: boolean;
  readonly includeContext?: boolean;
  readonly includeMetadata?: boolean;
  readonly includeStackTrace?: boolean;
  readonly colorize?: boolean;
  readonly dateFormat?: string;
  readonly maxMetadataDepth?: number;
  readonly prettyPrint?: boolean;
  readonly indent?: string | number;
}

// Color mappings for console output
const LEVEL_COLORS = {
  debug: '\x1b[36m', // Cyan
  info: '\x1b[32m', // Green
  warn: '\x1b[33m', // Yellow
  error: '\x1b[31m', // Red
  reset: '\x1b[0m', // Reset
} as const;

const COMPONENT_COLOR = '\x1b[35m'; // Magenta
const TIMESTAMP_COLOR = '\x1b[90m'; // Bright black (gray)
const CONTEXT_COLOR = '\x1b[94m'; // Bright blue

/**
 * Base formatter class
 */
export abstract class BaseFormatter {
  protected options: Required<FormatterOptions>;

  constructor(options: FormatterOptions = {}) {
    this.options = {
      includeTimestamp: true,
      includeLevel: true,
      includeContext: true,
      includeMetadata: true,
      includeStackTrace: true,
      colorize: false,
      dateFormat: 'YYYY-MM-DD HH:mm:ss.SSS',
      maxMetadataDepth: 3,
      prettyPrint: false,
      indent: 2,
      ...options,
    };
  }

  abstract format(entry: LogEntry): string;

  protected formatTimestamp(timestamp: Date): string {
    // Simple ISO format since we don't have moment.js
    const year = timestamp.getFullYear();
    const month = String(timestamp.getMonth() + 1).padStart(2, '0');
    const day = String(timestamp.getDate()).padStart(2, '0');
    const hours = String(timestamp.getHours()).padStart(2, '0');
    const minutes = String(timestamp.getMinutes()).padStart(2, '0');
    const seconds = String(timestamp.getSeconds()).padStart(2, '0');
    const ms = String(timestamp.getMilliseconds()).padStart(3, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}.${ms}`;
  }

  protected colorize(text: string, color: string): string {
    return this.options.colorize
      ? `${color}${text}${LEVEL_COLORS.reset}`
      : text;
  }

  protected formatMetadata(metadata: any): string {
    if (!metadata || typeof metadata !== 'object') {
      return String(metadata);
    }

    if (this.options.prettyPrint) {
      return inspect(metadata, {
        depth: this.options.maxMetadataDepth,
        colors: this.options.colorize,
        compact: false,
        breakLength: 80,
      });
    }

    return JSON.stringify(
      metadata,
      null,
      typeof this.options.indent === 'number' ? this.options.indent : undefined
    );
  }

  protected formatError(error: Error): string {
    if (!this.options.includeStackTrace) {
      return error.message;
    }

    return `${error.name}: ${error.message}\n${error.stack || 'No stack trace available'}`;
  }
}

/**
 * Console formatter - Human-readable format for console output
 */
export class ConsoleFormatter extends BaseFormatter {
  constructor(options: FormatterOptions = {}) {
    super({
      colorize: true,
      prettyPrint: true,
      ...options,
    });
  }

  format(entry: LogEntry): string {
    const parts: string[] = [];

    // Timestamp
    if (this.options.includeTimestamp) {
      const timestamp = this.formatTimestamp(entry.timestamp);
      parts.push(this.colorize(`[${timestamp}]`, TIMESTAMP_COLOR));
    }

    // Level
    if (this.options.includeLevel) {
      const levelColor = LEVEL_COLORS[entry.level];
      const level = entry.level.toUpperCase().padEnd(5);
      parts.push(this.colorize(`[${level}]`, levelColor));
    }

    // Context/Component
    if (this.options.includeContext) {
      const contextParts: string[] = [];

      if (entry.subsystem) {
        contextParts.push(entry.subsystem);
      }

      if (entry.component) {
        contextParts.push(entry.component);
      }

      if (entry.context) {
        contextParts.push(entry.context);
      }

      if (contextParts.length > 0) {
        const context = contextParts.join('.');
        parts.push(this.colorize(`[${context}]`, CONTEXT_COLOR));
      }
    }

    // Request ID
    if (entry.requestId) {
      parts.push(
        this.colorize(`(${entry.requestId.slice(0, 8)}...)`, COMPONENT_COLOR)
      );
    }

    // Message
    parts.push(entry.message);

    let result = parts.join(' ');

    // Error details
    if (entry.error) {
      result +=
        '\n' + this.colorize(this.formatError(entry.error), LEVEL_COLORS.error);
    }

    // Metadata
    if (
      this.options.includeMetadata &&
      entry.metadata &&
      Object.keys(entry.metadata).length > 0
    ) {
      const metadataStr = this.formatMetadata(entry.metadata);
      result +=
        '\n' + this.colorize('Metadata:', COMPONENT_COLOR) + '\n' + metadataStr;
    }

    return result;
  }
}

/**
 * JSON formatter - Structured JSON format for machine processing
 */
export class JSONFormatter extends BaseFormatter {
  constructor(options: FormatterOptions = {}) {
    super({
      colorize: false,
      prettyPrint: false,
      ...options,
    });
  }

  format(entry: LogEntry): string {
    const logObject: Record<string, any> = {
      timestamp: entry.timestamp.toISOString(),
      level: entry.level,
      message: entry.message,
    };

    // Add optional fields
    if (entry.context) {
      logObject.context = entry.context;
    }

    if (entry.subsystem) {
      logObject.subsystem = entry.subsystem;
    }

    if (entry.component) {
      logObject.component = entry.component;
    }

    if (entry.requestId) {
      logObject.requestId = entry.requestId;
    }

    if (entry.userId) {
      logObject.userId = entry.userId;
    }

    if (entry.error) {
      logObject.error = {
        name: entry.error.name,
        message: entry.error.message,
        stack: this.options.includeStackTrace ? entry.error.stack : undefined,
      };
    }

    if (entry.metadata && Object.keys(entry.metadata).length > 0) {
      logObject.metadata = entry.metadata;
    }

    return JSON.stringify(
      logObject,
      null,
      this.options.prettyPrint ? 2 : undefined
    );
  }
}

/**
 * Simple formatter - Minimal format for basic logging
 */
export class SimpleFormatter extends BaseFormatter {
  constructor(options: FormatterOptions = {}) {
    super({
      includeTimestamp: false,
      includeContext: false,
      includeMetadata: false,
      colorize: false,
      ...options,
    });
  }

  format(entry: LogEntry): string {
    const parts: string[] = [];

    // Level
    if (this.options.includeLevel) {
      parts.push(`[${entry.level.toUpperCase()}]`);
    }

    // Timestamp
    if (this.options.includeTimestamp) {
      parts.push(`[${this.formatTimestamp(entry.timestamp)}]`);
    }

    // Message
    parts.push(entry.message);

    let result = parts.join(' ');

    // Error (simplified)
    if (entry.error) {
      result += ` - Error: ${entry.error.message}`;
    }

    return result;
  }
}

/**
 * File formatter - Optimized format for file logging
 */
export class FileFormatter extends BaseFormatter {
  constructor(options: FormatterOptions = {}) {
    super({
      colorize: false,
      prettyPrint: false,
      includeStackTrace: true,
      ...options,
    });
  }

  format(entry: LogEntry): string {
    const parts: string[] = [];

    // Timestamp
    if (this.options.includeTimestamp) {
      parts.push(`[${this.formatTimestamp(entry.timestamp)}]`);
    }

    // Level
    if (this.options.includeLevel) {
      parts.push(`[${entry.level.toUpperCase().padEnd(5)}]`);
    }

    // Context
    if (
      this.options.includeContext &&
      (entry.subsystem || entry.component || entry.context)
    ) {
      const contextParts = [
        entry.subsystem,
        entry.component,
        entry.context,
      ].filter(Boolean);
      parts.push(`[${contextParts.join('.')}]`);
    }

    // Request ID
    if (entry.requestId) {
      parts.push(`[${entry.requestId}]`);
    }

    // Message
    parts.push(entry.message);

    let result = parts.join(' ');

    // Error details
    if (entry.error) {
      result += '\n  Error: ' + this.formatError(entry.error);
    }

    // Metadata (compact format for files)
    if (
      this.options.includeMetadata &&
      entry.metadata &&
      Object.keys(entry.metadata).length > 0
    ) {
      const metadataStr = JSON.stringify(entry.metadata);
      result += '\n  Metadata: ' + metadataStr;
    }

    return result;
  }
}

/**
 * Audit formatter - Specialized format for audit logging
 */
export class AuditFormatter extends BaseFormatter {
  constructor(options: FormatterOptions = {}) {
    super({
      includeTimestamp: true,
      includeLevel: false,
      includeContext: true,
      includeMetadata: true,
      colorize: false,
      prettyPrint: false,
      ...options,
    });
  }

  format(entry: LogEntry): string {
    const auditObject: Record<string, any> = {
      timestamp: entry.timestamp.toISOString(),
      event: entry.message,
      level: entry.level,
    };

    // Add audit-specific fields
    if (entry.userId) {
      auditObject.userId = entry.userId;
    }

    if (entry.requestId) {
      auditObject.requestId = entry.requestId;
    }

    if (entry.subsystem) {
      auditObject.subsystem = entry.subsystem;
    }

    if (entry.component) {
      auditObject.component = entry.component;
    }

    // Include all metadata as audit details
    if (entry.metadata) {
      auditObject.details = entry.metadata;
    }

    if (entry.error) {
      auditObject.error = {
        type: entry.error.name,
        message: entry.error.message,
      };
    }

    return JSON.stringify(auditObject);
  }
}

/**
 * Formatter factory
 */
export class FormatterFactory {
  private static readonly formatters = new Map<string, typeof BaseFormatter>([
    ['console', ConsoleFormatter],
    ['json', JSONFormatter],
    ['simple', SimpleFormatter],
    ['file', FileFormatter],
    ['audit', AuditFormatter],
  ]);

  /**
   * Create a formatter instance
   */
  static create(type: string, options: FormatterOptions = {}): BaseFormatter {
    const FormatterClass = this.formatters.get(type.toLowerCase());

    if (!FormatterClass) {
      throw new Error(
        `Unknown formatter type: ${type}. Available types: ${Array.from(this.formatters.keys()).join(', ')}`
      );
    }

    return new FormatterClass(options);
  }

  /**
   * Register a custom formatter
   */
  static register(name: string, formatterClass: typeof BaseFormatter): void {
    this.formatters.set(name.toLowerCase(), formatterClass);
  }

  /**
   * Get available formatter types
   */
  static getAvailableTypes(): string[] {
    return Array.from(this.formatters.keys());
  }
}

/**
 * Default formatter configurations
 */
export const DEFAULT_FORMATTERS = {
  console: new ConsoleFormatter({
    colorize: true,
    includeTimestamp: true,
    includeContext: true,
    prettyPrint: true,
  }),

  file: new FileFormatter({
    colorize: false,
    includeTimestamp: true,
    includeContext: true,
    includeStackTrace: true,
  }),

  json: new JSONFormatter({
    prettyPrint: false,
    includeStackTrace: true,
  }),

  simple: new SimpleFormatter({
    includeLevel: true,
    colorize: false,
  }),

  audit: new AuditFormatter({
    includeTimestamp: true,
    includeMetadata: true,
  }),
} as const;

/**
 * Utility function to create formatter from configuration
 */
export function createFormatter(
  type: string,
  options: FormatterOptions = {}
): BaseFormatter {
  return FormatterFactory.create(type, options);
}
