/**
 * Log Manager
 *
 * Central logging management system that coordinates multiple loggers,
 * manages log routing, handles configuration changes, and provides
 * system-wide logging services.
 */

import { EventEmitter } from 'eventemitter3';
import {
  LogContext,
  LogLevel,
  LogTransport,
  Logger,
  createLogger,
  createTransportsFromConfig,
} from './logger';
import { LogOutput, LoggingConfig } from '../config/config-types';
import { BaseSubsystem } from '../kenny/base-subsystem';

// Log manager configuration
export interface LogManagerConfig extends LoggingConfig {
  subsystemLoggers?: Record<string, Partial<LoggingConfig>>;
  globalContext?: LogContext;
  routingRules?: LogRoutingRule[];
  archivalConfig?: LogArchivalConfig;
}

// Log routing rule
export interface LogRoutingRule {
  readonly name: string;
  readonly condition: (entry: any) => boolean;
  readonly actions: LogRoutingAction[];
  readonly enabled: boolean;
}

export interface LogRoutingAction {
  readonly type: 'redirect' | 'duplicate' | 'filter' | 'transform';
  readonly target?: string;
  readonly transformer?: (entry: any) => any;
  readonly filter?: (entry: any) => boolean;
}

// Log archival configuration
export interface LogArchivalConfig {
  readonly enabled: boolean;
  readonly retentionPeriod: number; // days
  readonly compressionEnabled: boolean;
  readonly archivePath: string;
  readonly schedule: 'daily' | 'weekly' | 'monthly';
}

// Log metrics
export interface LogMetrics {
  readonly totalLogs: number;
  readonly logsByLevel: Record<LogLevel, number>;
  readonly logsBySubsystem: Record<string, number>;
  readonly errorRate: number;
  readonly averageLogsPerMinute: number;
  readonly transportMetrics: Record<string, any>;
  readonly uptime: number;
}

/**
 * Log Manager - Central logging coordination system
 */
export class LogManager extends EventEmitter {
  private config: LogManagerConfig;
  private rootLogger: Logger;
  private readonly subsystemLoggers = new Map<string, Logger>();
  private routingRules: LogRoutingRule[] = [];
  private metrics: LogMetrics;
  private metricsTimer?: NodeJS.Timeout;
  private archivalTimer?: NodeJS.Timeout;
  private readonly startTime: Date;

  constructor(config: LogManagerConfig) {
    super();

    this.config = { ...config };
    this.startTime = new Date();
    this.metrics = this.initializeMetrics();

    // Create root logger
    this.rootLogger = createLogger(config, config.globalContext);

    // Setup routing rules
    if (config.routingRules) {
      this.routingRules = [...config.routingRules];
    }

    // Setup metrics collection
    this.startMetricsCollection();

    // Setup log archival if enabled
    if (config.archivalConfig?.enabled) {
      this.startArchivalScheduler();
    }

    // Setup event handlers
    this.setupEventHandlers();
  }

  /**
   * Get or create a logger for a specific subsystem
   */
  getLogger(subsystemId: string, additionalContext?: LogContext): Logger {
    if (!this.subsystemLoggers.has(subsystemId)) {
      const subsystemConfig = this.config.subsystemLoggers?.[subsystemId];
      const mergedConfig = this.mergeConfigs(this.config, subsystemConfig);

      const context: LogContext = {
        ...this.config.globalContext,
        ...additionalContext,
        subsystem: subsystemId,
        metadata: {
          ...this.config.globalContext?.metadata,
          ...additionalContext?.metadata,
          subsystemId,
        },
      };

      const logger = createLogger(mergedConfig, context);
      this.subsystemLoggers.set(subsystemId, logger);

      // Setup logger event forwarding
      this.setupLoggerEventForwarding(logger, subsystemId);

      this.emit('logger.created', { subsystemId, logger });
    }

    return this.subsystemLoggers.get(subsystemId)!;
  }

  /**
   * Get the root logger
   */
  getRootLogger(): Logger {
    return this.rootLogger;
  }

  /**
   * Update logging configuration
   */
  async updateConfig(config: Partial<LogManagerConfig>): Promise<void> {
    const oldConfig = { ...this.config };
    this.config = { ...this.config, ...config };

    try {
      // Update root logger if main config changed
      if (this.hasMainConfigChanged(oldConfig, this.config)) {
        await this.rootLogger.close();
        this.rootLogger = createLogger(this.config, this.config.globalContext);
        this.setupLoggerEventForwarding(this.rootLogger, 'root');
      }

      // Update subsystem loggers if their configs changed
      if (config.subsystemLoggers) {
        for (const [subsystemId, subsystemConfig] of Object.entries(
          config.subsystemLoggers
        )) {
          if (this.subsystemLoggers.has(subsystemId)) {
            const logger = this.subsystemLoggers.get(subsystemId)!;
            await logger.close();

            const mergedConfig = this.mergeConfigs(
              this.config,
              subsystemConfig
            );
            const context: LogContext = {
              ...this.config.globalContext,
              subsystem: subsystemId,
              metadata: {
                ...this.config.globalContext?.metadata,
                subsystemId,
              },
            };

            const newLogger = createLogger(mergedConfig, context);
            this.subsystemLoggers.set(subsystemId, newLogger);
            this.setupLoggerEventForwarding(newLogger, subsystemId);
          }
        }
      }

      // Update routing rules
      if (config.routingRules) {
        this.routingRules = [...config.routingRules];
      }

      // Update archival configuration
      if (config.archivalConfig) {
        this.updateArchivalScheduler();
      }

      this.emit('config.updated', { oldConfig, newConfig: this.config });
    } catch (error) {
      // Rollback on error
      this.config = oldConfig;
      this.emit('config.error', { error });
      throw error;
    }
  }

  /**
   * Add a routing rule
   */
  addRoutingRule(rule: LogRoutingRule): void {
    this.routingRules.push(rule);
    this.emit('routing.rule.added', { rule });
  }

  /**
   * Remove a routing rule
   */
  removeRoutingRule(name: string): void {
    const index = this.routingRules.findIndex(rule => rule.name === name);
    if (index >= 0) {
      const removedRule = this.routingRules.splice(index, 1)[0];
      this.emit('routing.rule.removed', { rule: removedRule });
    }
  }

  /**
   * Get current metrics
   */
  getMetrics(): LogMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    this.metrics = this.initializeMetrics();

    // Reset logger metrics
    this.rootLogger.resetMetrics();
    this.subsystemLoggers.forEach(logger => logger.resetMetrics());

    this.emit('metrics.reset');
  }

  /**
   * Flush all loggers
   */
  async flush(): Promise<void> {
    const flushPromises = [
      this.rootLogger.flush(),
      ...Array.from(this.subsystemLoggers.values()).map(logger =>
        logger.flush()
      ),
    ];

    await Promise.allSettled(flushPromises);
    this.emit('flushed');
  }

  /**
   * Archive old logs
   */
  async archiveLogs(): Promise<void> {
    if (!this.config.archivalConfig?.enabled) {
      return;
    }

    try {
      // Implementation would depend on specific archival requirements
      // For now, emit event for external handling
      this.emit('archival.started', { config: this.config.archivalConfig });

      // Simulate archival process
      await new Promise(resolve => setTimeout(resolve, 1000));

      this.emit('archival.completed', { config: this.config.archivalConfig });
    } catch (error) {
      this.emit('archival.error', { error });
      throw error;
    }
  }

  /**
   * Cleanup and close all loggers
   */
  async cleanup(): Promise<void> {
    // Stop timers
    if (this.metricsTimer) {
      clearInterval(this.metricsTimer);
      this.metricsTimer = undefined;
    }

    if (this.archivalTimer) {
      clearInterval(this.archivalTimer);
      this.archivalTimer = undefined;
    }

    // Close all loggers
    const closePromises = [
      this.rootLogger.close(),
      ...Array.from(this.subsystemLoggers.values()).map(logger =>
        logger.close()
      ),
    ];

    await Promise.allSettled(closePromises);

    // Clear maps
    this.subsystemLoggers.clear();
    this.routingRules.length = 0;

    // Remove all listeners
    this.removeAllListeners();

    this.emit('cleanup.completed');
  }

  /**
   * Initialize metrics object
   */
  private initializeMetrics(): LogMetrics {
    return {
      totalLogs: 0,
      logsByLevel: {
        debug: 0,
        info: 0,
        warn: 0,
        error: 0,
        silent: 0,
      },
      logsBySubsystem: {},
      errorRate: 0,
      averageLogsPerMinute: 0,
      transportMetrics: {},
      uptime: 0,
    };
  }

  /**
   * Start metrics collection
   */
  private startMetricsCollection(): void {
    if (this.metricsTimer) {
      clearInterval(this.metricsTimer);
    }

    this.metricsTimer = setInterval(() => {
      this.updateMetrics();
    }, 60000); // Update every minute
  }

  /**
   * Update metrics from all loggers
   */
  private updateMetrics(): void {
    const rootMetrics = this.rootLogger.getMetrics();
    const subsystemMetrics = Array.from(this.subsystemLoggers.entries()).map(
      ([id, logger]) => ({ id, metrics: logger.getMetrics() })
    );

    // Aggregate metrics
    let totalLogs = rootMetrics.total;
    const logsByLevel: Record<LogLevel, number> = { ...rootMetrics };
    delete logsByLevel.total;

    const logsBySubsystem: Record<string, number> = {};

    for (const { id, metrics } of subsystemMetrics) {
      totalLogs += metrics.total;
      logsBySubsystem[id] = metrics.total;

      // Aggregate by level
      for (const level of Object.keys(logsByLevel) as LogLevel[]) {
        logsByLevel[level] += metrics[level] || 0;
      }
    }

    // Calculate rates
    const uptime = Date.now() - this.startTime.getTime();
    const uptimeMinutes = uptime / (1000 * 60);
    const errorRate = totalLogs > 0 ? (logsByLevel.error / totalLogs) * 100 : 0;
    const averageLogsPerMinute =
      uptimeMinutes > 0 ? totalLogs / uptimeMinutes : 0;

    this.metrics = {
      totalLogs,
      logsByLevel,
      logsBySubsystem,
      errorRate,
      averageLogsPerMinute,
      transportMetrics: {}, // TODO: Collect transport-specific metrics
      uptime,
    };

    this.emit('metrics.updated', this.metrics);
  }

  /**
   * Start archival scheduler
   */
  private startArchivalScheduler(): void {
    if (!this.config.archivalConfig?.enabled) {
      return;
    }

    const schedule = this.config.archivalConfig.schedule;
    let interval: number;

    switch (schedule) {
      case 'daily':
        interval = 24 * 60 * 60 * 1000; // 24 hours
        break;
      case 'weekly':
        interval = 7 * 24 * 60 * 60 * 1000; // 7 days
        break;
      case 'monthly':
        interval = 30 * 24 * 60 * 60 * 1000; // 30 days
        break;
      default:
        interval = 24 * 60 * 60 * 1000; // Default to daily
    }

    this.archivalTimer = setInterval(() => {
      this.archiveLogs().catch(error => {
        this.emit('archival.error', { error });
      });
    }, interval);
  }

  /**
   * Update archival scheduler
   */
  private updateArchivalScheduler(): void {
    if (this.archivalTimer) {
      clearInterval(this.archivalTimer);
      this.archivalTimer = undefined;
    }

    if (this.config.archivalConfig?.enabled) {
      this.startArchivalScheduler();
    }
  }

  /**
   * Setup event handlers
   */
  private setupEventHandlers(): void {
    // Handle log routing
    this.on('log.entry', (entry: any) => {
      this.processRoutingRules(entry);
    });
  }

  /**
   * Setup logger event forwarding
   */
  private setupLoggerEventForwarding(logger: Logger, loggerId: string): void {
    logger.on('log', entry => {
      this.emit('log.entry', { loggerId, entry });
    });

    logger.on('transport.error', error => {
      this.emit('transport.error', { loggerId, error });
    });
  }

  /**
   * Process routing rules for log entry
   */
  private processRoutingRules(data: { loggerId: string; entry: any }): void {
    for (const rule of this.routingRules) {
      if (!rule.enabled || !rule.condition(data.entry)) {
        continue;
      }

      for (const action of rule.actions) {
        try {
          this.executeRoutingAction(action, data);
        } catch (error) {
          this.emit('routing.error', { rule: rule.name, action, error });
        }
      }
    }
  }

  /**
   * Execute a routing action
   */
  private executeRoutingAction(
    action: LogRoutingAction,
    data: { loggerId: string; entry: any }
  ): void {
    switch (action.type) {
      case 'redirect':
        if (action.target) {
          const targetLogger = this.getLogger(action.target);
          // Re-emit log through target logger
          targetLogger.info(
            data.entry.message,
            data.entry.metadata,
            data.entry.error
          );
        }
        break;

      case 'duplicate':
        if (action.target) {
          const targetLogger = this.getLogger(action.target);
          targetLogger.info(
            data.entry.message,
            data.entry.metadata,
            data.entry.error
          );
        }
        break;

      case 'filter':
        if (action.filter && !action.filter(data.entry)) {
          // Log entry is filtered out
          return;
        }
        break;

      case 'transform':
        if (action.transformer) {
          data.entry = action.transformer(data.entry);
        }
        break;
    }
  }

  /**
   * Check if main configuration has changed
   */
  private hasMainConfigChanged(
    oldConfig: LogManagerConfig,
    newConfig: LogManagerConfig
  ): boolean {
    return (
      oldConfig.level !== newConfig.level ||
      oldConfig.format !== newConfig.format ||
      oldConfig.enabled !== newConfig.enabled ||
      JSON.stringify(oldConfig.outputs) !== JSON.stringify(newConfig.outputs)
    );
  }

  /**
   * Merge logging configurations
   */
  private mergeConfigs(
    baseConfig: LoggingConfig,
    overrideConfig?: Partial<LoggingConfig>
  ): LoggingConfig {
    if (!overrideConfig) {
      return baseConfig;
    }

    return {
      ...baseConfig,
      ...overrideConfig,
      outputs: overrideConfig.outputs || baseConfig.outputs,
      metadata: {
        ...baseConfig.metadata,
        ...overrideConfig.metadata,
      },
    };
  }
}

/**
 * Log Manager Subsystem - Kenny Integration
 */
export class LogManagerSubsystem extends BaseSubsystem {
  private logManager?: LogManager;

  constructor() {
    super({
      id: 'log-manager',
      name: 'Log Manager',
      version: '1.0.0',
      description: 'Central logging management system',
    });
  }

  async initialize(config: LogManagerConfig): Promise<void> {
    // Call parent initialize which will call our onInitialize
    await super.initialize(config);
  }

  async start(): Promise<void> {
    // Call parent start which will call our onStart
    await super.start();
  }

  async stop(): Promise<void> {
    // Call parent stop which will call our onStop
    await super.stop();
  }

  async shutdown(): Promise<void> {
    if (this.logManager) {
      await this.logManager.cleanup();
      this.logManager = undefined;
    }

    this.status = 'uninitialized';
    this.emit('shutdown');
  }

  async healthCheck() {
    if (!this.logManager) {
      return {
        status: 'unhealthy' as const,
        message: 'Log Manager not initialized',
        timestamp: new Date(),
      };
    }

    try {
      const metrics = this.logManager.getMetrics();
      return {
        status: 'healthy' as const,
        message: `Log Manager running - ${metrics.totalLogs} logs processed`,
        timestamp: new Date(),
        details: metrics,
      };
    } catch (error) {
      return {
        status: 'unhealthy' as const,
        message: `Log Manager error: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date(),
      };
    }
  }

  getLogManager(): LogManager | undefined {
    return this.logManager;
  }

  // Abstract method implementations required by BaseSubsystem
  protected async onInitialize(config: any): Promise<void> {
    this.logManager = new LogManager(config);

    // Forward events
    this.logManager.on('error', error => this.emit('error', error));
    this.logManager.on('config.updated', data =>
      this.emit('config.updated', data)
    );
    this.logManager.on('metrics.updated', metrics =>
      this.emit('metrics.updated', metrics)
    );
  }

  protected async onStart(): Promise<void> {
    // Log manager doesn't need special start logic
  }

  protected async onStop(): Promise<void> {
    if (this.logManager) {
      await this.logManager.flush();
    }
  }
}

/**
 * Factory function to create log manager
 */
export function createLogManager(config: LogManagerConfig): LogManager {
  return new LogManager(config);
}

/**
 * Factory function to create log manager subsystem
 */
export function createLogManagerSubsystem(): LogManagerSubsystem {
  return new LogManagerSubsystem();
}
