/**
 * Kenny Integration Pattern - Core Integration
 *
 * Provides the main KennyIntegration singleton class, subsystem registry,
 * and lifecycle management for the entire Kenny integration system.
 */

import { EventEmitter } from 'eventemitter3';
import {
  type KennyEvent,
  type MessageBus,
  getMessageBus,
} from './message-bus.js';
import { type StateManager, getStateManager } from './state-manager.js';
import {
  BaseSubsystem,
  type HealthCheckResult,
  type SubsystemMetadata,
} from './base-subsystem.js';

// Integration configuration
export interface KennyIntegrationConfig {
  systemId?: string;
  systemName?: string;
  version?: string;
  environment?: 'development' | 'staging' | 'production';
  logging?: {
    level?: 'debug' | 'info' | 'warn' | 'error';
    enabled?: boolean;
  };
  persistence?: {
    enabled?: boolean;
    storage?: 'memory' | 'localStorage' | 'sessionStorage' | 'custom';
    key?: string;
  };
  health?: {
    checkInterval?: number;
    enabled?: boolean;
  };
}

// Subsystem registry entry
export interface SubsystemRegistryEntry {
  instance: BaseSubsystem;
  metadata: SubsystemMetadata;
  registeredAt: Date;
  status: string;
  health?: HealthCheckResult;
  lastHealthCheck?: Date;
}

// System health information
export interface SystemHealth {
  status: 'healthy' | 'unhealthy' | 'degraded';
  uptime: number;
  subsystems: Record<string, HealthCheckResult>;
  timestamp: Date;
  details?: Record<string, any>;
}

/**
 * Main Kenny Integration Pattern class - Singleton
 */
export class KennyIntegration extends EventEmitter {
  private static instance: KennyIntegration | null = null;

  private readonly messageBus: MessageBus;
  private readonly stateManager: StateManager;
  private readonly subsystemRegistry = new Map<
    string,
    SubsystemRegistryEntry
  >();

  private config: KennyIntegrationConfig = {};
  private initialized = false;
  private startTime: Date | null = null;
  private healthCheckTimer: NodeJS.Timeout | null = null;

  private constructor() {
    super();
    this.messageBus = getMessageBus();
    this.stateManager = getStateManager();

    // Setup internal event handlers
    this.setupInternalHandlers();
  }

  /**
   * Get the singleton instance
   */
  static getInstance(): KennyIntegration {
    if (!KennyIntegration.instance) {
      KennyIntegration.instance = new KennyIntegration();
    }
    return KennyIntegration.instance;
  }

  /**
   * Reset the singleton instance (for testing)
   */
  static reset(): void {
    if (KennyIntegration.instance) {
      KennyIntegration.instance.shutdown();
      KennyIntegration.instance = null;
    }
  }

  /**
   * Initialize the Kenny Integration system
   */
  async initialize(config: KennyIntegrationConfig = {}): Promise<void> {
    if (this.initialized) {
      throw new Error('Kenny Integration is already initialized');
    }

    try {
      this.config = {
        systemId: 'kenny-system',
        systemName: 'Kenny Integration System',
        version: '1.0.0',
        environment: 'development',
        logging: { level: 'info', enabled: true },
        persistence: { enabled: false },
        health: { checkInterval: 30000, enabled: true },
        ...config,
      };

      // Initialize state manager
      await this.stateManager.initialize({
        initialState: {
          system: {
            id: this.config.systemId,
            name: this.config.systemName,
            version: this.config.version,
            environment: this.config.environment,
            startTime: new Date().toISOString(),
            status: 'initializing',
          },
          subsystems: {},
        },
        persistence: this.config.persistence?.enabled
          ? {
              storage: this.config.persistence.storage,
              key: this.config.persistence.key || 'kenny-integration-state',
            }
          : undefined,
      });

      // Publish system startup event
      await this.messageBus.publishSystem('system.startup', {
        systemId: this.config.systemId,
        version: this.config.version,
        environment: this.config.environment,
      });

      // Start health monitoring if enabled
      if (this.config.health?.enabled) {
        this.startHealthMonitoring();
      }

      this.initialized = true;
      this.startTime = new Date();

      // Update system state
      await this.stateManager.set('system.status', 'ready');
      await this.stateManager.set(
        'system.startTime',
        this.startTime.toISOString()
      );

      this.emit('initialized', { config: this.config });

      // Log initialization
      if (this.config.logging?.enabled) {
        console.log(
          `[Kenny Integration] System initialized: ${this.config.systemName} v${this.config.version}`
        );
      }
    } catch (error) {
      await this.messageBus.publishSystem('system.error', {
        error: error instanceof Error ? error.message : String(error),
        phase: 'initialization',
      });
      throw error;
    }
  }

  /**
   * Register a subsystem
   */
  async registerSubsystem(subsystem: BaseSubsystem): Promise<void> {
    if (!this.initialized) {
      throw new Error(
        'Kenny Integration must be initialized before registering subsystems'
      );
    }

    const subsystemId = subsystem.metadata.id;

    if (this.subsystemRegistry.has(subsystemId)) {
      throw new Error(`Subsystem ${subsystemId} is already registered`);
    }

    try {
      // Create registry entry
      const entry: SubsystemRegistryEntry = {
        instance: subsystem,
        metadata: subsystem.metadata,
        registeredAt: new Date(),
        status: subsystem.status,
      };

      this.subsystemRegistry.set(subsystemId, entry);

      // Update state
      await this.stateManager.set(`subsystems.${subsystemId}`, {
        ...subsystem.metadata,
        status: subsystem.status,
        registeredAt: entry.registeredAt.toISOString(),
      });

      // Publish registration event
      await this.messageBus.publishSubsystem('subsystem.register', 'system', {
        subsystemId,
        subsystemName: subsystem.metadata.name,
        version: subsystem.metadata.version,
      });

      // Setup subsystem event forwarding
      this.setupSubsystemEventForwarding(subsystem);

      this.emit('subsystem.registered', { subsystem: subsystem.metadata });

      if (this.config.logging?.enabled) {
        console.log(
          `[Kenny Integration] Registered subsystem: ${subsystem.metadata.name} v${subsystem.metadata.version}`
        );
      }
    } catch (error) {
      await this.messageBus.publishSystem('system.error', {
        error: error instanceof Error ? error.message : String(error),
        phase: 'subsystem.registration',
        subsystemId,
      });
      throw error;
    }
  }

  /**
   * Unregister a subsystem
   */
  async unregisterSubsystem(subsystemId: string): Promise<void> {
    const entry = this.subsystemRegistry.get(subsystemId);
    if (!entry) {
      return; // Already unregistered
    }

    try {
      // Stop the subsystem if it's running
      if (
        entry.instance.status !== 'stopped' &&
        entry.instance.status !== 'uninitialized'
      ) {
        await entry.instance.shutdown();
      }

      // Remove from registry
      this.subsystemRegistry.delete(subsystemId);

      // Update state
      await this.stateManager.delete(`subsystems.${subsystemId}`);

      // Publish unregistration event
      await this.messageBus.publishSubsystem('subsystem.unregister', 'system', {
        subsystemId,
        subsystemName: entry.metadata.name,
        version: entry.metadata.version,
      });

      this.emit('subsystem.unregistered', { subsystem: entry.metadata });

      if (this.config.logging?.enabled) {
        console.log(
          `[Kenny Integration] Unregistered subsystem: ${entry.metadata.name}`
        );
      }
    } catch (error) {
      await this.messageBus.publishSystem('system.error', {
        error: error instanceof Error ? error.message : String(error),
        phase: 'subsystem.unregistration',
        subsystemId,
      });
      throw error;
    }
  }

  /**
   * Get a registered subsystem
   */
  getSubsystem<T extends BaseSubsystem = BaseSubsystem>(
    subsystemId: string
  ): T | null {
    const entry = this.subsystemRegistry.get(subsystemId);
    return entry ? (entry.instance as T) : null;
  }

  /**
   * Get all registered subsystems
   */
  getSubsystems(): SubsystemRegistryEntry[] {
    return Array.from(this.subsystemRegistry.values());
  }

  /**
   * Initialize all registered subsystems
   */
  async initializeSubsystems(config: Record<string, any> = {}): Promise<void> {
    const subsystems = Array.from(this.subsystemRegistry.values());

    for (const entry of subsystems) {
      if (entry.instance.status === 'uninitialized') {
        try {
          const subsystemConfig = config[entry.metadata.id] || {};
          await entry.instance.initialize(subsystemConfig);
          entry.status = entry.instance.status;

          await this.stateManager.set(
            `subsystems.${entry.metadata.id}.status`,
            entry.status
          );
        } catch (error) {
          console.error(
            `Failed to initialize subsystem ${entry.metadata.id}:`,
            error
          );
        }
      }
    }
  }

  /**
   * Start all ready subsystems
   */
  async startSubsystems(): Promise<void> {
    const subsystems = Array.from(this.subsystemRegistry.values());

    for (const entry of subsystems) {
      if (entry.instance.status === 'ready') {
        try {
          await entry.instance.start();
          entry.status = entry.instance.status;

          await this.stateManager.set(
            `subsystems.${entry.metadata.id}.status`,
            entry.status
          );
        } catch (error) {
          console.error(
            `Failed to start subsystem ${entry.metadata.id}:`,
            error
          );
        }
      }
    }
  }

  /**
   * Stop all running subsystems
   */
  async stopSubsystems(): Promise<void> {
    const subsystems = Array.from(this.subsystemRegistry.values());

    // Stop in reverse order
    for (let i = subsystems.length - 1; i >= 0; i--) {
      const entry = subsystems[i];
      if (
        entry.instance.status === 'running' ||
        entry.instance.status === 'paused'
      ) {
        try {
          await entry.instance.stop();
          entry.status = entry.instance.status;

          await this.stateManager.set(
            `subsystems.${entry.metadata.id}.status`,
            entry.status
          );
        } catch (error) {
          console.error(
            `Failed to stop subsystem ${entry.metadata.id}:`,
            error
          );
        }
      }
    }
  }

  /**
   * Perform system health check
   */
  async performHealthCheck(): Promise<SystemHealth> {
    const subsystemHealth: Record<string, HealthCheckResult> = {};
    let overallStatus: SystemHealth['status'] = 'healthy';

    // Check each subsystem
    for (const [id, entry] of Array.from(this.subsystemRegistry.entries())) {
      try {
        const health = await entry.instance.healthCheck();
        subsystemHealth[id] = health;
        entry.health = health;
        entry.lastHealthCheck = new Date();

        // Update overall status
        if (health.status === 'unhealthy') {
          overallStatus = 'unhealthy';
        } else if (
          health.status === 'degraded' &&
          overallStatus !== 'unhealthy'
        ) {
          overallStatus = 'degraded';
        }
      } catch (error) {
        const unhealthyResult: HealthCheckResult = {
          status: 'unhealthy',
          message: `Health check failed: ${error instanceof Error ? error.message : String(error)}`,
          timestamp: new Date(),
        };

        subsystemHealth[id] = unhealthyResult;
        entry.health = unhealthyResult;
        entry.lastHealthCheck = new Date();
        overallStatus = 'unhealthy';
      }
    }

    const systemHealth: SystemHealth = {
      status: overallStatus,
      uptime: this.getUptime(),
      subsystems: subsystemHealth,
      timestamp: new Date(),
      details: {
        systemId: this.config.systemId,
        version: this.config.version,
        environment: this.config.environment,
        subsystemCount: this.subsystemRegistry.size,
      },
    };

    // Update state
    await this.stateManager.set('system.health', systemHealth);

    // Publish health event
    await this.messageBus.publishSystem('system.health', systemHealth);

    this.emit('health.check', systemHealth);

    return systemHealth;
  }

  /**
   * Get system uptime in milliseconds
   */
  getUptime(): number {
    return this.startTime ? Date.now() - this.startTime.getTime() : 0;
  }

  /**
   * Get message bus instance
   */
  getMessageBus(): MessageBus {
    return this.messageBus;
  }

  /**
   * Get state manager instance
   */
  getStateManager(): StateManager {
    return this.stateManager;
  }

  /**
   * Get system configuration
   */
  getConfig(): KennyIntegrationConfig {
    return { ...this.config };
  }

  /**
   * Shutdown the entire system
   */
  async shutdown(): Promise<void> {
    if (!this.initialized) {
      return;
    }

    try {
      // Publish shutdown event
      await this.messageBus.publishSystem('system.shutdown');

      // Stop health monitoring
      if (this.healthCheckTimer) {
        clearInterval(this.healthCheckTimer);
        this.healthCheckTimer = null;
      }

      // Stop all subsystems
      await this.stopSubsystems();

      // Unregister all subsystems
      const subsystemIds = Array.from(this.subsystemRegistry.keys());
      for (const id of subsystemIds) {
        await this.unregisterSubsystem(id);
      }

      // Update system state
      await this.stateManager.set('system.status', 'shutdown');

      this.initialized = false;
      this.startTime = null;

      this.emit('shutdown');

      if (this.config.logging?.enabled) {
        console.log('[Kenny Integration] System shutdown complete');
      }
    } catch (error) {
      console.error('[Kenny Integration] Error during shutdown:', error);
      throw error;
    }
  }

  /**
   * Setup internal event handlers
   */
  private setupInternalHandlers(): void {
    // Handle subsystem events
    this.messageBus.subscribeToType('subsystem.ready', async event => {
      const subsystemId = event.data?.subsystemId;
      if (subsystemId) {
        const entry = this.subsystemRegistry.get(subsystemId);
        if (entry) {
          entry.status = 'ready';
          await this.stateManager.set(
            `subsystems.${subsystemId}.status`,
            'ready'
          );
        }
      }
    });

    // Handle system health requests
    this.messageBus.subscribeToType('system.health.request', async () => {
      await this.performHealthCheck();
    });
  }

  /**
   * Setup event forwarding for a subsystem
   */
  private setupSubsystemEventForwarding(subsystem: BaseSubsystem): void {
    const events = ['started', 'stopped', 'paused', 'resumed', 'error'];

    events.forEach(eventName => {
      subsystem.on(eventName, async data => {
        const entry = this.subsystemRegistry.get(subsystem.metadata.id);
        if (entry) {
          entry.status = subsystem.status;
          await this.stateManager.set(
            `subsystems.${subsystem.metadata.id}.status`,
            subsystem.status
          );
        }

        this.emit(`subsystem.${eventName}`, {
          subsystem: subsystem.metadata,
          data,
        });
      });
    });
  }

  /**
   * Start health monitoring
   */
  private startHealthMonitoring(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
    }

    const interval = this.config.health?.checkInterval || 30000;

    this.healthCheckTimer = setInterval(async () => {
      try {
        await this.performHealthCheck();
      } catch (error) {
        console.error('[Kenny Integration] Health check failed:', error);
      }
    }, interval);
  }
}

// Export singleton getter
export function getKennyIntegration(): KennyIntegration {
  return KennyIntegration.getInstance();
}
