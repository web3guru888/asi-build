/**
 * Logging System - Main Export
 * 
 * Central export point for the ASI-Code logging system with Kenny Integration Pattern support.
 * Provides factory functions, utilities, and easy-to-use interfaces for structured logging.
 */

// Core logging exports
export {
  Logger,
  LogLevel,
  LogContext,
  LogTransport,
  ConsoleTransport,
  FileTransport,
  StreamTransport,
  HTTPTransport,
  createLogger,
  createTransportsFromConfig,
  LOG_LEVELS
} from './logger.js';

// Log manager exports
export {
  LogManager,
  LogManagerSubsystem,
  LogManagerConfig,
  LogRoutingRule,
  LogRoutingAction,
  LogArchivalConfig,
  LogMetrics,
  createLogManager,
  createLogManagerSubsystem
} from './log-manager.js';

// Formatter exports
export {
  BaseFormatter,
  ConsoleFormatter,
  JSONFormatter,
  SimpleFormatter,
  FileFormatter,
  AuditFormatter,
  FormatterFactory,
  LogEntry,
  FormatterOptions,
  DEFAULT_FORMATTERS,
  createFormatter
} from './formatters.js';

// Configuration types
export {
  LoggingConfig,
  LogOutput
} from '../config/config-types.js';

import { LogManager, LogManagerConfig, createLogManager } from './log-manager.js';
import { Logger, LogContext, LogLevel, createLogger } from './logger.js';
import { BaseSubsystem } from '../kenny/base-subsystem.js';
import { KennyIntegration } from '../kenny/integration.js';

/**
 * Global logging instance
 */
let globalLogManager: LogManager | null = null;
let globalRootLogger: Logger | null = null;

/**
 * Initialize global logging system
 */
export function initializeLogging(config: LogManagerConfig): LogManager {
  if (globalLogManager) {
    throw new Error('Logging system is already initialized');
  }

  globalLogManager = createLogManager(config);
  globalRootLogger = globalLogManager.getRootLogger();
  
  return globalLogManager;
}

/**
 * Get global log manager
 */
export function getLogManager(): LogManager {
  if (!globalLogManager) {
    throw new Error('Logging system not initialized. Call initializeLogging() first.');
  }
  return globalLogManager;
}

/**
 * Get global root logger
 */
export function getRootLogger(): Logger {
  if (!globalRootLogger) {
    throw new Error('Logging system not initialized. Call initializeLogging() first.');
  }
  return globalRootLogger;
}

/**
 * Get logger for subsystem (convenience function)
 */
export function getLogger(subsystemId: string, context?: LogContext): Logger {
  return getLogManager().getLogger(subsystemId, context);
}

/**
 * Cleanup global logging system
 */
export async function cleanupLogging(): Promise<void> {
  if (globalLogManager) {
    await globalLogManager.cleanup();
    globalLogManager = null;
    globalRootLogger = null;
  }
}

/**
 * Logging System Factory - Integrated with Kenny Pattern
 */
export class LoggingSystemFactory {
  /**
   * Create and register logging subsystem with Kenny Integration
   */
  static async createAndRegister(
    kennyIntegration: KennyIntegration,
    config: LogManagerConfig
  ): Promise<LogManager> {
    // Create log manager subsystem
    const logManagerSubsystem = createLogManagerSubsystem();
    
    // Register with Kenny Integration
    await kennyIntegration.registerSubsystem(logManagerSubsystem);
    
    // Initialize the subsystem
    await logManagerSubsystem.initialize(config);
    await logManagerSubsystem.start();
    
    // Get the log manager instance
    const logManager = logManagerSubsystem.getLogManager();
    if (!logManager) {
      throw new Error('Failed to create log manager instance');
    }

    // Set as global instance if not already set
    if (!globalLogManager) {
      globalLogManager = logManager;
      globalRootLogger = logManager.getRootLogger();
    }

    return logManager;
  }

  /**
   * Create standalone logging system (without Kenny Integration)
   */
  static createStandalone(config: LogManagerConfig): LogManager {
    return createLogManager(config);
  }

  /**
   * Create basic logger with minimal configuration
   */
  static createBasicLogger(level: LogLevel = 'info', context?: LogContext): Logger {
    const config: LogManagerConfig = {
      level,
      format: 'pretty',
      enabled: true,
      outputs: [
        {
          type: 'console',
          enabled: true,
          level,
          format: 'pretty',
          options: {}
        }
      ],
      includeTimestamp: true,
      colorize: true
    };

    return createLogger(config, context);
  }

  /**
   * Create production logger with file output
   */
  static createProductionLogger(
    logFile: string, 
    level: LogLevel = 'info',
    context?: LogContext
  ): Logger {
    const config: LogManagerConfig = {
      level,
      format: 'json',
      enabled: true,
      outputs: [
        {
          type: 'console',
          enabled: false,
          level: 'error',
          format: 'simple',
          options: {}
        },
        {
          type: 'file',
          enabled: true,
          level,
          format: 'json',
          options: {
            filename: logFile
          }
        }
      ],
      includeTimestamp: true,
      includeStack: true,
      colorize: false
    };

    return createLogger(config, context);
  }

  /**
   * Create development logger with console output
   */
  static createDevelopmentLogger(level: LogLevel = 'debug', context?: LogContext): Logger {
    const config: LogManagerConfig = {
      level,
      format: 'pretty',
      enabled: true,
      outputs: [
        {
          type: 'console',
          enabled: true,
          level,
          format: 'pretty',
          options: {}
        }
      ],
      includeTimestamp: true,
      colorize: true,
      includeStack: true
    };

    return createLogger(config, context);
  }
}

/**
 * Utility functions
 */

/**
 * Create logger with automatic subsystem detection
 */
export function createContextualLogger(context: LogContext): Logger {
  if (globalLogManager && context.subsystem) {
    return globalLogManager.getLogger(context.subsystem, context);
  }
  
  // Fallback to basic logger
  return LoggingSystemFactory.createBasicLogger('info', context);
}

/**
 * Create audit logger for security and compliance logging
 */
export function createAuditLogger(auditFile?: string): Logger {
  const outputs: LogOutput[] = [
    {
      type: 'console',
      enabled: false,
      options: {}
    }
  ];

  if (auditFile) {
    outputs.push({
      type: 'file',
      enabled: true,
      level: 'info',
      format: 'audit',
      options: {
        filename: auditFile
      }
    });
  }

  const config: LogManagerConfig = {
    level: 'info',
    format: 'json',
    enabled: true,
    outputs,
    includeTimestamp: true,
    includeStack: false
  };

  return createLogger(config, { context: 'audit' });
}

/**
 * Quick logging utilities (convenience functions)
 */
export const log = {
  debug: (message: string, metadata?: any, error?: Error) => {
    getRootLogger().debug(message, metadata, error);
  },
  info: (message: string, metadata?: any, error?: Error) => {
    getRootLogger().info(message, metadata, error);
  },
  warn: (message: string, metadata?: any, error?: Error) => {
    getRootLogger().warn(message, metadata, error);
  },
  error: (message: string, metadata?: any, error?: Error) => {
    getRootLogger().error(message, metadata, error);
  }
};

/**
 * Default configurations for different environments
 */
export const LOGGING_CONFIGS = {
  development: {
    level: 'debug' as LogLevel,
    format: 'pretty',
    enabled: true,
    outputs: [
      {
        type: 'console',
        enabled: true,
        level: 'debug' as LogLevel,
        format: 'pretty',
        options: {}
      }
    ],
    includeTimestamp: true,
    colorize: true,
    includeStack: true
  } as LogManagerConfig,

  production: {
    level: 'info' as LogLevel,
    format: 'json',
    enabled: true,
    outputs: [
      {
        type: 'console',
        enabled: false,
        options: {}
      },
      {
        type: 'file',
        enabled: true,
        level: 'info' as LogLevel,
        format: 'json',
        options: {
          filename: '/var/log/asi-code/asi-code.log'
        }
      },
      {
        type: 'file',
        enabled: true,
        level: 'error' as LogLevel,
        format: 'json',
        options: {
          filename: '/var/log/asi-code/error.log'
        }
      }
    ],
    maxFileSize: 100,
    maxFiles: 10,
    includeTimestamp: true,
    includeStack: true,
    colorize: false,
    archivalConfig: {
      enabled: true,
      retentionPeriod: 30,
      compressionEnabled: true,
      archivePath: '/var/log/asi-code/archive',
      schedule: 'daily'
    }
  } as LogManagerConfig,

  test: {
    level: 'silent' as LogLevel,
    format: 'simple',
    enabled: false,
    outputs: [],
    includeTimestamp: false,
    colorize: false
  } as LogManagerConfig
};

// Export the factory as default
export default LoggingSystemFactory;

// All exports are already handled above