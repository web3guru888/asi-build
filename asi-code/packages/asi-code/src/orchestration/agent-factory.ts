/**
 * Agent Factory Implementation
 *
 * Factory pattern for creating different agent types with support for templates,
 * dependency injection, agent pooling, and recycling capabilities.
 */

import { v4 as uuidv4 } from 'uuid';
import {
  Agent,
  AgentConfig,
  AgentType,
  ResourceRequirements,
  RetryPolicy,
  SupervisorAgent,
} from './types.js';
import { BaseAgent } from './base-agent.js';
import { WorkerAgent } from './worker-agent.js';
import { SupervisorAgent as SupervisorAgentImpl } from './supervisor-agent.js';
import { Logger } from '../logging/index.js';

/**
 * Agent template for common configurations
 */
export interface AgentTemplate {
  name: string;
  type: AgentType;
  baseConfig: Partial<AgentConfig>;
  description: string;
  tags: string[];
}

/**
 * Agent pool configuration
 */
export interface AgentPoolConfig {
  minSize: number;
  maxSize: number;
  idleTimeout: number; // milliseconds
  recycleThreshold: number; // max tasks before recycling
}

/**
 * Dependency injection container
 */
export interface DependencyContainer {
  logger?: Logger;
  [key: string]: any;
}

/**
 * Agent creation options
 */
export interface AgentCreationOptions {
  template?: string;
  dependencies?: DependencyContainer;
  pooled?: boolean;
  tags?: string[];
  metadata?: Record<string, any>;
}

/**
 * Pooled agent wrapper
 */
interface PooledAgent {
  agent: Agent;
  createdAt: number;
  lastUsed: number;
  taskCount: number;
  inUse: boolean;
}

/**
 * Agent Factory Implementation
 */
export class AgentFactory {
  private readonly templates: Map<string, AgentTemplate> = new Map();
  private readonly pools: Map<AgentType, PooledAgent[]> = new Map();
  private readonly poolConfigs: Map<AgentType, AgentPoolConfig> = new Map();
  private dependencies: DependencyContainer = {};
  private readonly logger: Logger;
  private cleanupInterval: NodeJS.Timer | null = null;

  constructor(dependencies?: DependencyContainer) {
    this.dependencies = dependencies || {};
    this.logger =
      dependencies?.logger ||
      new Logger({
        level: 'info',
        context: { component: 'AgentFactory' },
      });

    this.initializeTemplates();
    this.initializePoolConfigs();
    this.startCleanupProcess();
  }

  /**
   * Create an agent based on configuration and options
   */
  async createAgent(
    config: AgentConfig,
    options: AgentCreationOptions = {}
  ): Promise<Agent> {
    this.logger.info(
      `Creating agent of type ${config.type} with name ${config.name}`
    );

    try {
      // Apply template if specified
      let finalConfig = { ...config };
      if (options.template) {
        finalConfig = this.applyTemplate(finalConfig, options.template);
      }

      // Add default values
      finalConfig = this.applyDefaults(finalConfig);

      // Add metadata and tags
      if (options.metadata) {
        finalConfig.metadata = { ...finalConfig.metadata, ...options.metadata };
      }

      if (options.tags) {
        finalConfig.metadata = {
          ...finalConfig.metadata,
          tags: [...(finalConfig.metadata?.tags || []), ...options.tags],
        };
      }

      // Check if pooled agent is requested and available
      if (options.pooled && this.isPoolingEnabled(finalConfig.type)) {
        const pooledAgent = await this.getPooledAgent(finalConfig.type);
        if (pooledAgent) {
          this.logger.info(
            `Reusing pooled agent ${pooledAgent.id} for type ${finalConfig.type}`
          );
          return pooledAgent;
        }
      }

      // Create new agent instance
      const agent = await this.instantiateAgent(
        finalConfig,
        options.dependencies
      );

      // Initialize the agent
      await agent.initialize();

      // Add to pool if pooling is enabled
      if (this.isPoolingEnabled(finalConfig.type)) {
        this.addToPool(agent);
      }

      this.logger.info(
        `Successfully created agent ${agent.id} of type ${finalConfig.type}`
      );
      return agent;
    } catch (error) {
      this.logger.error(
        `Failed to create agent of type ${config.type}:`,
        error
      );
      throw error;
    }
  }

  /**
   * Create agent from template
   */
  async createFromTemplate(
    templateName: string,
    overrides: Partial<AgentConfig> = {},
    options: AgentCreationOptions = {}
  ): Promise<Agent> {
    const template = this.templates.get(templateName);
    if (!template) {
      throw new Error(`Template '${templateName}' not found`);
    }

    const config: AgentConfig = {
      ...template.baseConfig,
      ...overrides,
      type: template.type,
      name: overrides.name || `${template.name}-${uuidv4().slice(0, 8)}`,
    } as AgentConfig;

    return this.createAgent(config, { ...options, template: templateName });
  }

  /**
   * Create multiple agents with load balancing
   */
  async createAgentCluster(
    count: number,
    config: AgentConfig,
    options: AgentCreationOptions = {}
  ): Promise<Agent[]> {
    this.logger.info(
      `Creating agent cluster of ${count} agents of type ${config.type}`
    );

    const agents: Agent[] = [];
    const promises: Promise<Agent>[] = [];

    for (let i = 0; i < count; i++) {
      const agentConfig: AgentConfig = {
        ...config,
        name: `${config.name}-${i + 1}`,
        id: `${config.id || 'cluster'}-${i + 1}-${uuidv4().slice(0, 8)}`,
      };

      promises.push(this.createAgent(agentConfig, options));
    }

    try {
      const createdAgents = await Promise.all(promises);
      agents.push(...createdAgents);

      this.logger.info(
        `Successfully created agent cluster of ${agents.length} agents`
      );
      return agents;
    } catch (error) {
      this.logger.error(`Failed to create agent cluster:`, error);

      // Cleanup any successfully created agents
      for (const agent of agents) {
        try {
          await agent.terminate();
        } catch (cleanupError) {
          this.logger.warn(
            `Failed to cleanup agent ${agent.id}:`,
            cleanupError
          );
        }
      }

      throw error;
    }
  }

  /**
   * Register an agent template
   */
  registerTemplate(template: AgentTemplate): void {
    this.templates.set(template.name, template);
    this.logger.info(`Registered agent template: ${template.name}`);
  }

  /**
   * Get available templates
   */
  getTemplates(): AgentTemplate[] {
    return Array.from(this.templates.values());
  }

  /**
   * Get template by name
   */
  getTemplate(name: string): AgentTemplate | undefined {
    return this.templates.get(name);
  }

  /**
   * Configure agent pooling for a specific type
   */
  configurePooling(type: AgentType, config: AgentPoolConfig): void {
    this.poolConfigs.set(type, config);
    if (!this.pools.has(type)) {
      this.pools.set(type, []);
    }
    this.logger.info(`Configured pooling for agent type ${type}`);
  }

  /**
   * Get pool statistics
   */
  getPoolStats(): Map<
    AgentType,
    { total: number; inUse: number; idle: number }
  > {
    const stats = new Map();

    for (const [type, pool] of Array.from(this.pools.entries())) {
      const total = pool.length;
      const inUse = pool.filter(p => p.inUse).length;
      const idle = total - inUse;

      stats.set(type, { total, inUse, idle });
    }

    return stats;
  }

  /**
   * Recycle an agent back to the pool
   */
  async recycleAgent(agent: Agent): Promise<boolean> {
    const pool = this.pools.get(agent.config.type);
    if (!pool) {
      return false;
    }

    const pooledAgent = pool.find(p => p.agent.id === agent.id);
    if (!pooledAgent) {
      return false;
    }

    // Reset agent state
    try {
      if (agent.status === 'working' || agent.status === 'busy') {
        await agent.suspend();
        await agent.resume();
      }

      pooledAgent.inUse = false;
      pooledAgent.lastUsed = Date.now();
      pooledAgent.taskCount++;

      // Check if agent should be retired
      const config = this.poolConfigs.get(agent.config.type);
      if (config && pooledAgent.taskCount >= config.recycleThreshold) {
        await this.retirePooledAgent(pooledAgent);
        return false;
      }

      this.logger.debug(`Recycled agent ${agent.id} back to pool`);
      return true;
    } catch (error) {
      this.logger.error(`Failed to recycle agent ${agent.id}:`, error);
      await this.retirePooledAgent(pooledAgent);
      return false;
    }
  }

  /**
   * Clear all pools and terminate agents
   */
  async clearPools(): Promise<void> {
    this.logger.info('Clearing all agent pools');

    for (const [type, pool] of Array.from(this.pools.entries())) {
      const agents = pool.map(p => p.agent);
      await Promise.all(agents.map(agent => agent.terminate()));
      pool.length = 0;
    }
  }

  /**
   * Set dependency injection container
   */
  setDependencies(dependencies: DependencyContainer): void {
    this.dependencies = { ...this.dependencies, ...dependencies };
  }

  /**
   * Get dependency injection container
   */
  getDependencies(): DependencyContainer {
    return { ...this.dependencies };
  }

  /**
   * Shutdown the factory and cleanup resources
   */
  async shutdown(): Promise<void> {
    this.logger.info('Shutting down AgentFactory');

    // Stop cleanup process
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Clear all pools
    await this.clearPools();

    this.logger.info('AgentFactory shutdown complete');
  }

  // Private methods

  /**
   * Initialize default templates
   */
  private initializeTemplates(): void {
    const defaultTemplates: AgentTemplate[] = [
      {
        name: 'basic-worker',
        type: 'worker',
        baseConfig: {
          capabilities: ['task-execution', 'basic-processing'],
          maxConcurrentTasks: 3,
          retryPolicy: {
            maxRetries: 2,
            backoffMultiplier: 2,
            initialDelay: 1000,
            maxDelay: 10000,
          },
        },
        description: 'Basic worker agent for general task execution',
        tags: ['worker', 'basic', 'general'],
      },
      {
        name: 'high-performance-worker',
        type: 'worker',
        baseConfig: {
          capabilities: ['task-execution', 'computation', 'analysis'],
          maxConcurrentTasks: 5,
          resources: {
            cpu: 2,
            memory: 1024,
            network: true,
          },
          retryPolicy: {
            maxRetries: 1,
            backoffMultiplier: 1.5,
            initialDelay: 500,
            maxDelay: 5000,
          },
        },
        description: 'High-performance worker for compute-intensive tasks',
        tags: ['worker', 'high-performance', 'computation'],
      },
      {
        name: 'specialist-analyzer',
        type: 'specialist',
        baseConfig: {
          capabilities: ['analysis', 'pattern-recognition', 'data-mining'],
          maxConcurrentTasks: 2,
          resources: {
            cpu: 4,
            memory: 2048,
            network: true,
          },
        },
        description:
          'Specialist agent for data analysis and pattern recognition',
        tags: ['specialist', 'analysis', 'data'],
      },
      {
        name: 'coordinator',
        type: 'coordinator',
        baseConfig: {
          capabilities: ['coordination', 'task-management', 'monitoring'],
          maxConcurrentTasks: 10,
          resources: {
            cpu: 1,
            memory: 512,
            network: true,
          },
        },
        description: 'Coordinator agent for managing task workflows',
        tags: ['coordinator', 'management', 'workflow'],
      },
      {
        name: 'supervisor',
        type: 'supervisor',
        baseConfig: {
          capabilities: ['supervision', 'agent-management', 'load-balancing'],
          maxConcurrentTasks: 20,
          resources: {
            cpu: 2,
            memory: 1024,
            network: true,
          },
        },
        description: 'Supervisor agent for managing other agents',
        tags: ['supervisor', 'management', 'orchestration'],
      },
    ];

    for (const template of defaultTemplates) {
      this.registerTemplate(template);
    }
  }

  /**
   * Initialize default pool configurations
   */
  private initializePoolConfigs(): void {
    const defaultPoolConfigs: [AgentType, AgentPoolConfig][] = [
      [
        'worker',
        { minSize: 2, maxSize: 10, idleTimeout: 300000, recycleThreshold: 100 },
      ],
      [
        'specialist',
        { minSize: 1, maxSize: 5, idleTimeout: 600000, recycleThreshold: 50 },
      ],
      [
        'coordinator',
        { minSize: 1, maxSize: 3, idleTimeout: 900000, recycleThreshold: 200 },
      ],
    ];

    for (const [type, config] of defaultPoolConfigs) {
      this.configurePooling(type, config);
    }
  }

  /**
   * Apply template to configuration
   */
  private applyTemplate(
    config: AgentConfig,
    templateName: string
  ): AgentConfig {
    const template = this.templates.get(templateName);
    if (!template) {
      throw new Error(`Template '${templateName}' not found`);
    }

    return {
      ...template.baseConfig,
      ...config,
      type: template.type,
      capabilities: [
        ...(template.baseConfig.capabilities || []),
        ...(config.capabilities || []),
      ],
    } as AgentConfig;
  }

  /**
   * Apply default values to configuration
   */
  private applyDefaults(config: AgentConfig): AgentConfig {
    return {
      id: config.id || `agent-${uuidv4()}`,
      timeout: config.timeout || 30000,
      ...config,
      capabilities: config.capabilities || [],
      metadata: config.metadata || {},
    };
  }

  /**
   * Instantiate agent based on type
   */
  private async instantiateAgent(
    config: AgentConfig,
    dependencies?: DependencyContainer
  ): Promise<Agent> {
    const mergedDeps = { ...this.dependencies, ...dependencies };
    const logger = mergedDeps.logger || this.logger;

    switch (config.type) {
      case 'worker':
        return new WorkerAgent(config, logger);

      case 'supervisor':
        return new SupervisorAgentImpl(config, logger);

      case 'specialist':
      case 'coordinator':
      case 'analyzer':
      case 'executor':
      case 'monitor':
      case 'validator':
        // For now, use WorkerAgent as base for specialized types
        // In a full implementation, these would have their own classes
        return new WorkerAgent(
          {
            ...config,
            capabilities: [...config.capabilities, config.type],
          },
          logger
        );

      default:
        throw new Error(`Unsupported agent type: ${config.type}`);
    }
  }

  /**
   * Check if pooling is enabled for agent type
   */
  private isPoolingEnabled(type: AgentType): boolean {
    return this.poolConfigs.has(type);
  }

  /**
   * Get pooled agent if available
   */
  private async getPooledAgent(type: AgentType): Promise<Agent | null> {
    const pool = this.pools.get(type);
    if (!pool) {
      return null;
    }

    const available = pool.find(p => !p.inUse);
    if (!available) {
      return null;
    }

    available.inUse = true;
    available.lastUsed = Date.now();

    return available.agent;
  }

  /**
   * Add agent to pool
   */
  private addToPool(agent: Agent): void {
    const type = agent.config.type;
    const pool = this.pools.get(type);

    if (!pool) {
      return;
    }

    const config = this.poolConfigs.get(type);
    if (!config || pool.length >= config.maxSize) {
      return;
    }

    const pooledAgent: PooledAgent = {
      agent,
      createdAt: Date.now(),
      lastUsed: Date.now(),
      taskCount: 0,
      inUse: true,
    };

    pool.push(pooledAgent);
    this.logger.debug(`Added agent ${agent.id} to ${type} pool`);
  }

  /**
   * Retire a pooled agent
   */
  private async retirePooledAgent(pooledAgent: PooledAgent): Promise<void> {
    const type = pooledAgent.agent.config.type;
    const pool = this.pools.get(type);

    if (!pool) {
      return;
    }

    const index = pool.indexOf(pooledAgent);
    if (index !== -1) {
      pool.splice(index, 1);

      try {
        await pooledAgent.agent.terminate();
        this.logger.debug(
          `Retired agent ${pooledAgent.agent.id} from ${type} pool`
        );
      } catch (error) {
        this.logger.error(
          `Error retiring agent ${pooledAgent.agent.id}:`,
          error
        );
      }
    }
  }

  /**
   * Start cleanup process for idle agents
   */
  private startCleanupProcess(): void {
    this.cleanupInterval = setInterval(() => {
      this.cleanupIdleAgents();
    }, 60000); // Run every minute
  }

  /**
   * Cleanup idle agents from pools
   */
  private cleanupIdleAgents(): void {
    for (const [type, pool] of Array.from(this.pools.entries())) {
      const config = this.poolConfigs.get(type);
      if (!config) {
        continue;
      }

      const now = Date.now();
      const idleAgents = pool.filter(
        p => !p.inUse && now - p.lastUsed > config.idleTimeout
      );

      // Keep minimum pool size
      const toRemove = Math.max(
        0,
        idleAgents.length - (config.minSize - (pool.length - idleAgents.length))
      );

      for (let i = 0; i < toRemove; i++) {
        this.retirePooledAgent(idleAgents[i]);
      }

      if (toRemove > 0) {
        this.logger.debug(
          `Cleaned up ${toRemove} idle agents from ${type} pool`
        );
      }
    }
  }
}

/**
 * Default agent factory instance
 */
export const defaultAgentFactory = new AgentFactory();

/**
 * Helper function to create agent
 */
export async function createAgent(
  config: AgentConfig,
  options?: AgentCreationOptions
): Promise<Agent> {
  return defaultAgentFactory.createAgent(config, options);
}

/**
 * Helper function to create agent from template
 */
export async function createFromTemplate(
  templateName: string,
  overrides?: Partial<AgentConfig>,
  options?: AgentCreationOptions
): Promise<Agent> {
  return defaultAgentFactory.createFromTemplate(
    templateName,
    overrides,
    options
  );
}
