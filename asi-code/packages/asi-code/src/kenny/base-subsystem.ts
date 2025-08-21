/**
 * Kenny Integration Pattern - Base Subsystem
 * 
 * Abstract base class for all subsystems in the Kenny integration system.
 * Provides common properties, lifecycle hooks, and message handling.
 */

import { EventEmitter } from 'eventemitter3';
import { getMessageBus, type KennyEvent, type EventFilter } from './message-bus.js';
import { getStateManager } from './state-manager.js';

// Subsystem metadata
export interface SubsystemMetadata {
  id: string;
  name: string;
  version: string;
  description?: string;
  author?: string;
  tags?: string[];
  capabilities?: string[];
}

// Subsystem dependency
export interface SubsystemDependency {
  id: string;
  version?: string;
  optional?: boolean;
  minVersion?: string;
  maxVersion?: string;
}

// Subsystem status
export type SubsystemStatus = 
  | 'uninitialized'
  | 'initializing' 
  | 'ready'
  | 'running'
  | 'paused'
  | 'stopping'
  | 'stopped'
  | 'error';

// Subsystem configuration
export interface SubsystemConfig {
  [key: string]: any;
}

// Health check result
export interface HealthCheckResult {
  status: 'healthy' | 'unhealthy' | 'degraded';
  message?: string;
  details?: Record<string, any>;
  timestamp: Date;
}

/**
 * Abstract base class for all Kenny subsystems
 */
export abstract class BaseSubsystem extends EventEmitter {
  protected messageBus = getMessageBus();
  protected stateManager = getStateManager();
  private subscriptions: string[] = [];

  public readonly metadata: SubsystemMetadata;
  public readonly dependencies: SubsystemDependency[];
  public status: SubsystemStatus = 'uninitialized';
  public config: SubsystemConfig = {};
  public lastError: Error | null = null;
  public startTime: Date | null = null;

  constructor(
    metadata: SubsystemMetadata,
    dependencies: SubsystemDependency[] = []
  ) {
    super();
    this.metadata = metadata;
    this.dependencies = dependencies;
  }

  /**
   * Initialize the subsystem
   */
  async initialize(config: SubsystemConfig = {}): Promise<void> {
    if (this.status !== 'uninitialized') {
      throw new Error(`Subsystem ${this.metadata.id} is already initialized`);
    }

    try {
      this.status = 'initializing';
      this.config = { ...config };
      this.lastError = null;

      // Publish initialization start event
      await this.publishSubsystemEvent('subsystem.initialize.start');

      // Check dependencies
      await this.checkDependencies();

      // Call custom initialization
      await this.onInitialize(config);

      // Subscribe to system events
      this.setupSystemEventHandlers();

      this.status = 'ready';
      this.startTime = new Date();

      // Publish ready event
      await this.publishSubsystemEvent('subsystem.ready');

      this.emit('initialized', { subsystem: this.metadata.id, config });
    } catch (error) {
      this.status = 'error';
      this.lastError = error instanceof Error ? error : new Error(String(error));
      
      await this.publishSubsystemEvent('subsystem.error', {
        error: this.lastError.message,
        stack: this.lastError.stack
      });

      throw error;
    }
  }

  /**
   * Start the subsystem
   */
  async start(): Promise<void> {
    if (this.status !== 'ready') {
      throw new Error(`Subsystem ${this.metadata.id} is not ready to start`);
    }

    try {
      this.status = 'running';
      
      // Publish start event
      await this.publishSubsystemEvent('subsystem.start');

      // Call custom start logic
      await this.onStart();

      this.emit('started', { subsystem: this.metadata.id });
    } catch (error) {
      this.status = 'error';
      this.lastError = error instanceof Error ? error : new Error(String(error));
      
      await this.publishSubsystemEvent('subsystem.error', {
        error: this.lastError.message,
        stack: this.lastError.stack
      });

      throw error;
    }
  }

  /**
   * Pause the subsystem
   */
  async pause(): Promise<void> {
    if (this.status !== 'running') {
      throw new Error(`Subsystem ${this.metadata.id} is not running`);
    }

    try {
      this.status = 'paused';
      
      // Call custom pause logic
      await this.onPause();

      // Publish pause event
      await this.publishSubsystemEvent('subsystem.pause');

      this.emit('paused', { subsystem: this.metadata.id });
    } catch (error) {
      this.status = 'error';
      this.lastError = error instanceof Error ? error : new Error(String(error));
      throw error;
    }
  }

  /**
   * Resume the subsystem
   */
  async resume(): Promise<void> {
    if (this.status !== 'paused') {
      throw new Error(`Subsystem ${this.metadata.id} is not paused`);
    }

    try {
      this.status = 'running';
      
      // Call custom resume logic
      await this.onResume();

      // Publish resume event
      await this.publishSubsystemEvent('subsystem.resume');

      this.emit('resumed', { subsystem: this.metadata.id });
    } catch (error) {
      this.status = 'error';
      this.lastError = error instanceof Error ? error : new Error(String(error));
      throw error;
    }
  }

  /**
   * Stop the subsystem
   */
  async stop(): Promise<void> {
    if (this.status === 'stopped' || this.status === 'uninitialized') {
      return;
    }

    try {
      this.status = 'stopping';
      
      // Publish stopping event
      await this.publishSubsystemEvent('subsystem.stopping');

      // Call custom stop logic
      await this.onStop();

      // Cleanup subscriptions
      this.cleanup();

      this.status = 'stopped';

      // Publish stopped event
      await this.publishSubsystemEvent('subsystem.stopped');

      this.emit('stopped', { subsystem: this.metadata.id });
    } catch (error) {
      this.status = 'error';
      this.lastError = error instanceof Error ? error : new Error(String(error));
      throw error;
    }
  }

  /**
   * Shutdown the subsystem (complete cleanup)
   */
  async shutdown(): Promise<void> {
    await this.stop();
    this.removeAllListeners();
  }

  /**
   * Perform a health check
   */
  async healthCheck(): Promise<HealthCheckResult> {
    try {
      const customResult = await this.onHealthCheck();
      const defaultStatus = this.status === 'error' ? 'unhealthy' : 'healthy';
      const defaultMessage = `Subsystem ${this.metadata.id} is ${this.status}`;
      
      // Handle case where onHealthCheck returns void
      const resultStatus = customResult && typeof customResult === 'object' ? customResult.status : undefined;
      const resultMessage = customResult && typeof customResult === 'object' ? customResult.message : undefined;
      const resultDetails = customResult && typeof customResult === 'object' ? customResult.details : undefined;
      
      return {
        status: resultStatus || defaultStatus,
        message: resultMessage || defaultMessage,
        details: {
          ...(resultDetails || {}),
          subsystemId: this.metadata.id,
          status: this.status,
          uptime: this.getUptime(),
          lastError: this.lastError?.message
        },
        timestamp: new Date()
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        message: `Health check failed: ${error instanceof Error ? error.message : String(error)}`,
        details: {
          subsystemId: this.metadata.id,
          error: error instanceof Error ? error.message : String(error)
        },
        timestamp: new Date()
      };
    }
  }

  /**
   * Get subsystem uptime in milliseconds
   */
  getUptime(): number | null {
    return this.startTime ? Date.now() - this.startTime.getTime() : null;
  }

  /**
   * Subscribe to message bus events with automatic cleanup
   */
  protected subscribe(
    filter: EventFilter,
    callback: (event: KennyEvent) => void | Promise<void>,
    options?: { once?: boolean; priority?: number }
  ): string {
    const subscriptionId = this.messageBus.subscribe(filter, callback, options);
    if (!options?.once) {
      this.subscriptions.push(subscriptionId);
    }
    return subscriptionId;
  }

  /**
   * Subscribe to events by type
   */
  protected subscribeToType(
    eventType: string,
    callback: (event: KennyEvent) => void | Promise<void>,
    options?: { once?: boolean; priority?: number }
  ): string {
    return this.subscribe({ type: eventType }, callback, options);
  }

  /**
   * Subscribe to events from a specific source
   */
  protected subscribeToSource(
    source: string,
    callback: (event: KennyEvent) => void | Promise<void>,
    options?: { once?: boolean; priority?: number }
  ): string {
    return this.subscribe({ source }, callback, options);
  }

  /**
   * Unsubscribe from a specific subscription
   */
  protected unsubscribe(subscriptionId: string): boolean {
    const success = this.messageBus.unsubscribe(subscriptionId);
    if (success) {
      this.subscriptions = this.subscriptions.filter(id => id !== subscriptionId);
    }
    return success;
  }

  /**
   * Publish an event to the message bus
   */
  protected async publish(event: Omit<KennyEvent, 'id' | 'timestamp' | 'source'>): Promise<void> {
    await this.messageBus.publish({
      ...event,
      source: this.metadata.id
    });
  }

  /**
   * Publish a subsystem-specific event
   */
  protected async publishSubsystemEvent(
    type: string,
    data?: any,
    target?: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    await this.messageBus.publishSubsystem(
      type as any,
      this.metadata.id,
      {
        subsystemId: this.metadata.id,
        subsystemName: this.metadata.name,
        version: this.metadata.version,
        ...data
      },
      metadata
    );
  }

  /**
   * Get state from the state manager
   */
  protected getState<T = any>(path: string): T | undefined {
    return this.stateManager.get<T>(path);
  }

  /**
   * Set state in the state manager
   */
  protected async setState<T = any>(path: string, value: T): Promise<void> {
    await this.stateManager.set(path, value, this.metadata.id);
  }

  /**
   * Watch for state changes
   */
  protected watchState(
    path: string | RegExp,
    callback: (change: any) => void | Promise<void>,
    options?: { immediate?: boolean; deep?: boolean }
  ): string {
    return this.stateManager.watch(path, callback, options);
  }

  // Abstract methods to be implemented by subclasses
  protected abstract onInitialize(config: SubsystemConfig): Promise<void>;
  protected abstract onStart(): Promise<void>;
  protected abstract onStop(): Promise<void>;

  // Optional lifecycle hooks
  protected async onPause(): Promise<void> {
    // Default: no-op
  }

  protected async onResume(): Promise<void> {
    // Default: no-op
  }

  protected async onHealthCheck(): Promise<Partial<HealthCheckResult> | void> {
    // Default: no additional checks
  }

  /**
   * Check if all dependencies are available
   */
  private async checkDependencies(): Promise<void> {
    // This would typically check with a subsystem registry
    // For now, we'll just emit an event that dependencies are being checked
    await this.publishSubsystemEvent('subsystem.dependencies.check', {
      dependencies: this.dependencies
    });
  }

  /**
   * Setup handlers for system events
   */
  private setupSystemEventHandlers(): void {
    // Handle system shutdown
    this.subscribe(
      { type: 'system.shutdown' },
      async () => {
        await this.shutdown();
      }
    );

    // Handle health check requests
    this.subscribe(
      { 
        type: 'subsystem.health.request',
        target: this.metadata.id
      },
      async (event) => {
        const result = await this.healthCheck();
        await this.publish({
          type: 'subsystem.health.response',
          target: event.source,
          data: result
        });
      }
    );
  }

  /**
   * Cleanup subscriptions and resources
   */
  private cleanup(): void {
    // Unsubscribe from all message bus subscriptions
    this.subscriptions.forEach(id => {
      this.messageBus.unsubscribe(id);
    });
    this.subscriptions = [];
  }
}