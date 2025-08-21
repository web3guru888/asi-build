/**
 * Structured Logger
 * 
 * Advanced logging system with multiple levels, structured output,
 * context management, and integration with the ASI-Code system.
 */

import { EventEmitter } from 'eventemitter3';
import { writeFileSync, appendFileSync, existsSync, mkdirSync } from 'fs';
import { dirname, resolve } from 'path';
import { LogEntry, BaseFormatter, DEFAULT_FORMATTERS } from './formatters.js';
import { LoggingConfig, LogOutput } from '../config/config-types.js';

// Log levels with numeric values for filtering
export const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  silent: 4
} as const;

export type LogLevel = keyof typeof LOG_LEVELS;

// Log context interface
export interface LogContext {
  subsystem?: string;
  component?: string;
  context?: string;
  requestId?: string;
  userId?: string;
  metadata?: Record<string, any>;
}

// Log transport interface
export interface LogTransport {
  readonly name: string;
  readonly level: LogLevel;
  readonly formatter: BaseFormatter;
  write(entry: LogEntry): Promise<void> | void;
  flush?(): Promise<void> | void;
  close?(): Promise<void> | void;
}

// Logger options
export interface LoggerOptions {
  level?: LogLevel;
  context?: LogContext;
  transports?: LogTransport[];
  enableMetrics?: boolean;
  bufferSize?: number;
  flushInterval?: number;
}

/**
 * Console Transport - Outputs to console/stdout
 */
export class ConsoleTransport implements LogTransport {
  readonly name = 'console';
  readonly level: LogLevel;
  readonly formatter: BaseFormatter;

  constructor(level: LogLevel = 'info', formatter?: BaseFormatter) {
    this.level = level;
    this.formatter = formatter || DEFAULT_FORMATTERS.console;
  }

  write(entry: LogEntry): void {
    const formatted = this.formatter.format(entry);
    
    if (entry.level === 'error') {
      console.error(formatted);
    } else if (entry.level === 'warn') {
      console.warn(formatted);
    } else {
      console.log(formatted);
    }
  }
}

/**
 * File Transport - Outputs to file with rotation support
 */
export class FileTransport implements LogTransport {
  readonly name = 'file';
  readonly level: LogLevel;
  readonly formatter: BaseFormatter;
  private readonly filePath: string;
  private readonly maxFileSize: number;
  private readonly maxFiles: number;
  private currentFileSize = 0;

  constructor(
    filePath: string,
    level: LogLevel = 'info',
    formatter?: BaseFormatter,
    maxFileSize = 100 * 1024 * 1024, // 100MB
    maxFiles = 5
  ) {
    this.level = level;
    this.formatter = formatter || DEFAULT_FORMATTERS.file;
    this.filePath = resolve(filePath);
    this.maxFileSize = maxFileSize;
    this.maxFiles = maxFiles;

    // Ensure directory exists
    const dir = dirname(this.filePath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    // Get current file size if it exists
    if (existsSync(this.filePath)) {
      try {
        const stats = require('fs').statSync(this.filePath);
        this.currentFileSize = stats.size;
      } catch (error) {
        this.currentFileSize = 0;
      }
    }
  }

  write(entry: LogEntry): void {
    const formatted = this.formatter.format(entry) + '\n';
    const data = Buffer.from(formatted, 'utf8');

    // Check if rotation is needed
    if (this.currentFileSize + data.length > this.maxFileSize) {
      this.rotate();
    }

    try {
      appendFileSync(this.filePath, data);
      this.currentFileSize += data.length;
    } catch (error) {
      console.error(`Failed to write to log file ${this.filePath}:`, error);
    }
  }

  private rotate(): void {
    try {
      // Move existing files
      for (let i = this.maxFiles - 1; i >= 1; i--) {
        const oldFile = `${this.filePath}.${i}`;
        const newFile = `${this.filePath}.${i + 1}`;
        
        if (existsSync(oldFile)) {
          if (i === this.maxFiles - 1) {
            // Delete the oldest file
            require('fs').unlinkSync(oldFile);
          } else {
            require('fs').renameSync(oldFile, newFile);
          }
        }
      }

      // Move current file to .1
      if (existsSync(this.filePath)) {
        require('fs').renameSync(this.filePath, `${this.filePath}.1`);
      }

      this.currentFileSize = 0;
    } catch (error) {
      console.error('Failed to rotate log files:', error);
    }
  }

  flush(): void {
    // File system automatically flushes, but we could implement buffering here
  }

  close(): void {
    // Nothing to close for file transport
  }
}

/**
 * Stream Transport - Outputs to a writable stream
 */
export class StreamTransport implements LogTransport {
  readonly name = 'stream';
  readonly level: LogLevel;
  readonly formatter: BaseFormatter;
  private readonly stream: NodeJS.WritableStream;

  constructor(stream: NodeJS.WritableStream, level: LogLevel = 'info', formatter?: BaseFormatter) {
    this.level = level;
    this.formatter = formatter || DEFAULT_FORMATTERS.json;
    this.stream = stream;
  }

  write(entry: LogEntry): void {
    const formatted = this.formatter.format(entry) + '\n';
    
    if (this.stream.writable) {
      this.stream.write(formatted);
    }
  }

  flush(): Promise<void> {
    return new Promise((resolve, reject) => {
      if ('flush' in this.stream && typeof this.stream.flush === 'function') {
        this.stream.flush((error: any) => {
          if (error) reject(error);
          else resolve();
        });
      } else {
        resolve();
      }
    });
  }

  close(): Promise<void> {
    return new Promise((resolve) => {
      if (this.stream.writable) {
        this.stream.end(() => resolve());
      } else {
        resolve();
      }
    });
  }
}

/**
 * HTTP Transport - Sends logs to HTTP endpoint
 */
export class HTTPTransport implements LogTransport {
  readonly name = 'http';
  readonly level: LogLevel;
  readonly formatter: BaseFormatter;
  private readonly url: string;
  private readonly headers: Record<string, string>;
  private readonly batchSize: number;
  private readonly flushInterval: number;
  private batch: LogEntry[] = [];
  private flushTimer?: NodeJS.Timeout;

  constructor(
    url: string,
    level: LogLevel = 'info',
    formatter?: BaseFormatter,
    headers: Record<string, string> = { 'Content-Type': 'application/json' },
    batchSize = 10,
    flushInterval = 5000
  ) {
    this.level = level;
    this.formatter = formatter || DEFAULT_FORMATTERS.json;
    this.url = url;
    this.headers = headers;
    this.batchSize = batchSize;
    this.flushInterval = flushInterval;

    // Start flush timer
    this.startFlushTimer();
  }

  write(entry: LogEntry): void {
    this.batch.push(entry);
    
    if (this.batch.length >= this.batchSize) {
      this.flush();
    }
  }

  async flush(): Promise<void> {
    if (this.batch.length === 0) {
      return;
    }

    const entries = this.batch.splice(0);
    const payload = entries.map(entry => this.formatter.format(entry));

    try {
      const response = await fetch(this.url, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ logs: payload })
      });

      if (!response.ok) {
        console.error(`HTTP transport failed: ${response.status} ${response.statusText}`);
        // Re-add entries to batch for retry (simple strategy)
        this.batch.unshift(...entries);
      }
    } catch (error) {
      console.error('HTTP transport error:', error);
      // Re-add entries to batch for retry
      this.batch.unshift(...entries);
    }
  }

  close(): Promise<void> {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = undefined;
    }
    return this.flush();
  }

  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flush().catch(error => {
        console.error('Failed to flush HTTP transport:', error);
      });
    }, this.flushInterval);
  }
}

/**
 * Main Logger class
 */
export class Logger extends EventEmitter {
  private readonly level: LogLevel;
  private readonly context: LogContext;
  private readonly transports: LogTransport[];
  private readonly enableMetrics: boolean;
  private readonly metrics: Record<string, number> = {
    debug: 0,
    info: 0,
    warn: 0,
    error: 0,
    total: 0
  };

  constructor(options: LoggerOptions = {}) {
    super();
    
    this.level = options.level || 'info';
    this.context = { ...options.context };
    this.transports = options.transports || [new ConsoleTransport()];
    this.enableMetrics = options.enableMetrics !== false;

    // Validate transports
    this.transports.forEach(transport => {
      if (!transport.name || !transport.write) {
        throw new Error('Invalid transport: must have name and write method');
      }
    });
  }

  /**
   * Create child logger with additional context
   */
  child(context: LogContext): Logger {
    return new Logger({
      level: this.level,
      context: {
        ...this.context,
        ...context,
        metadata: {
          ...this.context.metadata,
          ...context.metadata
        }
      },
      transports: this.transports,
      enableMetrics: this.enableMetrics
    });
  }

  /**
   * Debug level logging
   */
  debug(message: string, metadata?: Record<string, any>, error?: Error): void {
    this.log('debug', message, metadata, error);
  }

  /**
   * Info level logging
   */
  info(message: string, metadata?: Record<string, any>, error?: Error): void {
    this.log('info', message, metadata, error);
  }

  /**
   * Warning level logging
   */
  warn(message: string, metadata?: Record<string, any>, error?: Error): void {
    this.log('warn', message, metadata, error);
  }

  /**
   * Error level logging
   */
  error(message: string, metadata?: Record<string, any>, error?: Error): void {
    this.log('error', message, metadata, error);
  }

  /**
   * Core logging method
   */
  private log(level: LogLevel, message: string, metadata?: Record<string, any>, error?: Error): void {
    // Check if this log level should be processed
    if (LOG_LEVELS[level] < LOG_LEVELS[this.level]) {
      return;
    }

    // Update metrics
    if (this.enableMetrics) {
      this.metrics[level]++;
      this.metrics.total++;
    }

    // Create log entry
    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      message,
      context: this.context.context,
      requestId: this.context.requestId,
      userId: this.context.userId,
      subsystem: this.context.subsystem,
      component: this.context.component,
      metadata: {
        ...this.context.metadata,
        ...metadata
      },
      error
    };

    // Write to all transports that accept this log level
    this.transports.forEach(transport => {
      if (LOG_LEVELS[level] >= LOG_LEVELS[transport.level]) {
        try {
          const result = transport.write(entry);
          // Handle async transports
          if (result && typeof result.catch === 'function') {
            result.catch(error => {
              console.error(`Transport ${transport.name} failed:`, error);
              this.emit('transport.error', { transport: transport.name, error });
            });
          }
        } catch (error) {
          console.error(`Transport ${transport.name} failed:`, error);
          this.emit('transport.error', { transport: transport.name, error });
        }
      }
    });

    // Emit log event
    this.emit('log', entry);
    this.emit(level, entry);
  }

  /**
   * Get current metrics
   */
  getMetrics(): Record<string, number> {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    Object.keys(this.metrics).forEach(key => {
      this.metrics[key] = 0;
    });
  }

  /**
   * Add transport
   */
  addTransport(transport: LogTransport): void {
    this.transports.push(transport);
  }

  /**
   * Remove transport by name
   */
  removeTransport(name: string): void {
    const index = this.transports.findIndex(t => t.name === name);
    if (index >= 0) {
      const transport = this.transports[index];
      this.transports.splice(index, 1);
      
      // Close transport if it supports it
      if (transport.close) {
        const closeResult = transport.close();
        if (closeResult && typeof closeResult.catch === 'function') {
          closeResult.catch(error => {
            console.error(`Failed to close transport ${name}:`, error);
          });
        }
      }
    }
  }

  /**
   * Flush all transports
   */
  async flush(): Promise<void> {
    const flushPromises = this.transports
      .filter(transport => transport.flush)
      .map(transport => transport.flush!());

    await Promise.allSettled(flushPromises);
  }

  /**
   * Close all transports and cleanup
   */
  async close(): Promise<void> {
    await this.flush();

    const closePromises = this.transports
      .filter(transport => transport.close)
      .map(transport => transport.close!());

    await Promise.allSettled(closePromises);
    
    this.removeAllListeners();
  }

  /**
   * Set log level
   */
  setLevel(level: LogLevel): void {
    (this as any).level = level;
  }

  /**
   * Get current log level
   */
  getLevel(): LogLevel {
    return this.level;
  }

  /**
   * Check if level is enabled
   */
  isLevelEnabled(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[this.level];
  }
}

/**
 * Create transports from configuration
 */
export function createTransportsFromConfig(outputs: LogOutput[]): LogTransport[] {
  const transports: LogTransport[] = [];

  for (const output of outputs) {
    if (!output.enabled) {
      continue;
    }

    const level = output.level || 'info';
    const formatter = output.format ? DEFAULT_FORMATTERS[output.format as keyof typeof DEFAULT_FORMATTERS] : undefined;

    switch (output.type) {
      case 'console':
        transports.push(new ConsoleTransport(level, formatter));
        break;

      case 'file':
        if (output.options?.filename) {
          transports.push(new FileTransport(
            output.options.filename,
            level,
            formatter,
            output.options.maxFileSize,
            output.options.maxFiles
          ));
        }
        break;

      case 'http':
        if (output.options?.url) {
          transports.push(new HTTPTransport(
            output.options.url,
            level,
            formatter,
            output.options.headers,
            output.options.batchSize,
            output.options.flushInterval
          ));
        }
        break;

      case 'stream':
        if (output.options?.stream) {
          transports.push(new StreamTransport(
            output.options.stream,
            level,
            formatter
          ));
        }
        break;

      default:
        console.warn(`Unknown log output type: ${output.type}`);
    }
  }

  return transports;
}

/**
 * Create logger from configuration
 */
export function createLogger(config: LoggingConfig, context?: LogContext): Logger {
  const transports = createTransportsFromConfig(config.outputs);
  
  return new Logger({
    level: config.level,
    context,
    transports,
    enableMetrics: true
  });
}