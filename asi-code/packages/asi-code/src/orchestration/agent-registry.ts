/**
 * ASI-Code Agent Registry Implementation
 *
 * Manages agent registration, discovery, and health monitoring.
 * Provides thread-safe operations for agent lifecycle management.
 */

import { EventEmitter } from 'eventemitter3';
import {
  Agent,
  AgentMetrics,
  AgentStatus,
  AgentType,
  AgentRegistry as IAgentRegistry,
  Task,
} from './types.js';

interface AgentRecord {
  agent: Agent;
  registeredAt: number;
  lastHealthCheck: number;
  healthStatus: 'healthy' | 'unhealthy' | 'unknown';
  consecutiveHealthFailures: number;
}

export class AgentRegistry extends EventEmitter implements IAgentRegistry {
  private readonly agents = new Map<string, AgentRecord>();
  private readonly capabilityIndex = new Map<string, Set<string>>();
  private readonly typeIndex = new Map<AgentType, Set<string>>();
  private readonly statusIndex = new Map<AgentStatus, Set<string>>();
  private readonly lock = new Map<string, Promise<void>>();

  // Health monitoring configuration
  private healthCheckInterval: NodeJS.Timer | null = null;
  private readonly healthCheckIntervalMs = 30000; // 30 seconds
  private readonly maxConsecutiveFailures = 3;
  private readonly healthCheckTimeoutMs = 5000; // 5 seconds

  constructor() {
    super();
    this.startHealthMonitoring();
  }

  /**
   * Register an agent in the registry
   */
  register(agent: Agent): void {
    this.withLock(agent.id, async () => {
      // Remove any existing registration
      if (this.agents.has(agent.id)) {
        this.unregister(agent.id);
      }

      const record: AgentRecord = {
        agent,
        registeredAt: Date.now(),
        lastHealthCheck: Date.now(),
        healthStatus: 'unknown',
        consecutiveHealthFailures: 0,
      };

      this.agents.set(agent.id, record);
      this.updateIndices(agent, 'add');

      // Set up agent event listeners
      this.setupAgentListeners(agent);

      this.emit('agent:registered', agent.id, agent);
    });
  }

  /**
   * Unregister an agent from the registry
   */
  unregister(agentId: string): void {
    this.withLock(agentId, async () => {
      const record = this.agents.get(agentId);
      if (!record) {
        return;
      }

      this.updateIndices(record.agent, 'remove');
      this.agents.delete(agentId);

      // Remove agent event listeners
      this.removeAgentListeners(record.agent);

      this.emit('agent:unregistered', agentId);
    });
  }

  /**
   * Get an agent by ID
   */
  get(agentId: string): Agent | undefined {
    const record = this.agents.get(agentId);
    return record?.agent;
  }

  /**
   * Find agents by capability
   */
  findByCapability(capability: string): Agent[] {
    const agentIds = this.capabilityIndex.get(capability) || new Set();
    return Array.from(agentIds)
      .map(id => this.agents.get(id)?.agent)
      .filter((agent): agent is Agent => agent !== undefined);
  }

  /**
   * Find agents by type
   */
  findByType(type: AgentType): Agent[] {
    const agentIds = this.typeIndex.get(type) || new Set();
    return Array.from(agentIds)
      .map(id => this.agents.get(id)?.agent)
      .filter((agent): agent is Agent => agent !== undefined);
  }

  /**
   * Find available agents (idle status and healthy)
   */
  findAvailable(): Agent[] {
    const idleAgents = this.statusIndex.get('idle') || new Set();
    return Array.from(idleAgents)
      .map(id => this.agents.get(id))
      .filter(
        (record): record is AgentRecord =>
          record !== undefined &&
          record.healthStatus === 'healthy' &&
          record.agent.currentTasks.size <
            record.agent.config.maxConcurrentTasks
      )
      .map(record => record.agent);
  }

  /**
   * Get all registered agents
   */
  getAll(): Agent[] {
    return Array.from(this.agents.values()).map(record => record.agent);
  }

  /**
   * Find best agent for a specific task
   */
  findBestAgent(task: Task): Agent | undefined {
    const candidates = this.findAvailable();

    // Filter by required capabilities
    const capableAgents = candidates.filter(agent => agent.canHandle(task));

    if (capableAgents.length === 0) {
      return undefined;
    }

    // Score agents based on performance and load
    const scoredAgents = capableAgents.map(agent => ({
      agent,
      score: this.calculateAgentScore(agent, task),
    }));

    // Sort by score (higher is better)
    scoredAgents.sort((a, b) => b.score - a.score);

    return scoredAgents[0]?.agent;
  }

  /**
   * Get agent health status
   */
  getAgentHealth(
    agentId: string
  ): 'healthy' | 'unhealthy' | 'unknown' | undefined {
    return this.agents.get(agentId)?.healthStatus;
  }

  /**
   * Get registry statistics
   */
  getStats(): {
    totalAgents: number;
    agentsByType: Record<AgentType, number>;
    agentsByStatus: Record<AgentStatus, number>;
    healthyAgents: number;
    availableAgents: number;
  } {
    const stats = {
      totalAgents: this.agents.size,
      agentsByType: {} as Record<AgentType, number>,
      agentsByStatus: {} as Record<AgentStatus, number>,
      healthyAgents: 0,
      availableAgents: 0,
    };

    // Initialize counts
    const agentTypes: AgentType[] = [
      'supervisor',
      'worker',
      'specialist',
      'coordinator',
      'analyzer',
      'executor',
      'monitor',
      'validator',
    ];
    const agentStatuses: AgentStatus[] = [
      'idle',
      'busy',
      'working',
      'waiting',
      'error',
      'terminated',
      'suspended',
    ];

    agentTypes.forEach(type => (stats.agentsByType[type] = 0));
    agentStatuses.forEach(status => (stats.agentsByStatus[status] = 0));

    // Count agents
    this.agents.forEach(record => {
      const agent = record.agent;
      stats.agentsByType[agent.config.type]++;
      stats.agentsByStatus[agent.status]++;

      if (record.healthStatus === 'healthy') {
        stats.healthyAgents++;
      }
    });

    stats.availableAgents = this.findAvailable().length;

    return stats;
  }

  /**
   * Start health monitoring for all agents
   */
  private startHealthMonitoring(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.healthCheckInterval = setInterval(() => {
      this.performHealthChecks();
    }, this.healthCheckIntervalMs);
  }

  /**
   * Stop health monitoring
   */
  stopHealthMonitoring(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  /**
   * Perform health checks on all agents
   */
  private async performHealthChecks(): Promise<void> {
    const healthCheckPromises = Array.from(this.agents.entries()).map(
      ([agentId, record]) => this.checkAgentHealth(agentId, record)
    );

    await Promise.allSettled(healthCheckPromises);
  }

  /**
   * Check health of a specific agent
   */
  private async checkAgentHealth(
    agentId: string,
    record: AgentRecord
  ): Promise<void> {
    try {
      const healthCheckStart = Date.now();

      // Create a timeout promise
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(
          () => reject(new Error('Health check timeout')),
          this.healthCheckTimeoutMs
        );
      });

      // Get agent metrics with timeout
      const metricsPromise = record.agent.getMetrics();
      const metrics = await Promise.race([metricsPromise, timeoutPromise]);

      // Check if agent is responding and healthy
      const isHealthy = this.evaluateAgentHealth(metrics, record.agent);

      record.lastHealthCheck = Date.now();

      if (isHealthy) {
        if (record.healthStatus !== 'healthy') {
          record.healthStatus = 'healthy';
          record.consecutiveHealthFailures = 0;
          this.emit('agent:health_recovered', agentId);
        }
      } else {
        record.consecutiveHealthFailures++;
        if (record.consecutiveHealthFailures >= this.maxConsecutiveFailures) {
          record.healthStatus = 'unhealthy';
          this.emit(
            'agent:health_failed',
            agentId,
            record.consecutiveHealthFailures
          );
        }
      }
    } catch (error) {
      record.consecutiveHealthFailures++;
      record.lastHealthCheck = Date.now();

      if (record.consecutiveHealthFailures >= this.maxConsecutiveFailures) {
        record.healthStatus = 'unhealthy';
        this.emit(
          'agent:health_failed',
          agentId,
          record.consecutiveHealthFailures
        );
      }
    }
  }

  /**
   * Evaluate if an agent is healthy based on its metrics
   */
  private evaluateAgentHealth(metrics: AgentMetrics, agent: Agent): boolean {
    // Agent is unhealthy if:
    // 1. Status is error or terminated
    // 2. Last health check was too long ago
    // 3. Resource utilization is extremely high
    // 4. Success rate is too low

    if (agent.status === 'error' || agent.status === 'terminated') {
      return false;
    }

    const now = Date.now();
    const timeSinceLastCheck = now - metrics.lastHealthCheck;
    if (timeSinceLastCheck > this.healthCheckIntervalMs * 2) {
      return false;
    }

    // Check resource utilization
    const { cpu, memory } = metrics.performance.resourceUtilization;
    if (cpu > 0.95 || memory > 0.95) {
      return false;
    }

    // Check success rate (if agent has completed tasks)
    if (metrics.tasksCompleted > 0 && metrics.performance.successRate < 0.5) {
      return false;
    }

    return true;
  }

  /**
   * Calculate agent score for task assignment
   */
  private calculateAgentScore(agent: Agent, task: Task): number {
    const metrics = agent.getMetrics();
    let score = 100; // Base score

    // Factor in success rate
    score *= metrics.performance.successRate;

    // Factor in current load (lower load = higher score)
    const loadFactor =
      agent.currentTasks.size / agent.config.maxConcurrentTasks;
    score *= 1 - loadFactor;

    // Factor in performance (faster = higher score)
    if (metrics.performance.averageTaskDuration > 0) {
      const performanceFactor =
        1 / (metrics.performance.averageTaskDuration / 1000); // Convert to seconds
      score *= Math.min(performanceFactor, 2); // Cap at 2x multiplier
    }

    // Preferred agent bonus
    if (task.constraints?.preferredAgent === agent.id) {
      score *= 1.5;
    }

    return score;
  }

  /**
   * Update internal indices when agent is added/removed
   */
  private updateIndices(agent: Agent, operation: 'add' | 'remove'): void {
    const agentId = agent.id;

    if (operation === 'add') {
      // Update capability index
      agent.getCapabilities().forEach(capability => {
        if (!this.capabilityIndex.has(capability)) {
          this.capabilityIndex.set(capability, new Set());
        }
        this.capabilityIndex.get(capability)!.add(agentId);
      });

      // Update type index
      if (!this.typeIndex.has(agent.config.type)) {
        this.typeIndex.set(agent.config.type, new Set());
      }
      this.typeIndex.get(agent.config.type)!.add(agentId);

      // Update status index
      if (!this.statusIndex.has(agent.status)) {
        this.statusIndex.set(agent.status, new Set());
      }
      this.statusIndex.get(agent.status)!.add(agentId);
    } else {
      // Remove from capability index
      agent.getCapabilities().forEach(capability => {
        this.capabilityIndex.get(capability)?.delete(agentId);
        if (this.capabilityIndex.get(capability)?.size === 0) {
          this.capabilityIndex.delete(capability);
        }
      });

      // Remove from type index
      this.typeIndex.get(agent.config.type)?.delete(agentId);
      if (this.typeIndex.get(agent.config.type)?.size === 0) {
        this.typeIndex.delete(agent.config.type);
      }

      // Remove from status index
      this.statusIndex.get(agent.status)?.delete(agentId);
      if (this.statusIndex.get(agent.status)?.size === 0) {
        this.statusIndex.delete(agent.status);
      }
    }
  }

  /**
   * Set up event listeners for an agent
   */
  private setupAgentListeners(agent: Agent): void {
    // Listen for status changes to update indices
    agent.on(
      'status:changed',
      (oldStatus: AgentStatus, newStatus: AgentStatus) => {
        this.statusIndex.get(oldStatus)?.delete(agent.id);
        if (this.statusIndex.get(oldStatus)?.size === 0) {
          this.statusIndex.delete(oldStatus);
        }

        if (!this.statusIndex.has(newStatus)) {
          this.statusIndex.set(newStatus, new Set());
        }
        this.statusIndex.get(newStatus)!.add(agent.id);

        this.emit('agent:status_changed', agent.id, newStatus);
      }
    );

    // Listen for task completion
    agent.on('task:completed', (taskId: string) => {
      this.emit('agent:task_completed', agent.id, taskId);
    });

    // Listen for task failure
    agent.on('task:failed', (taskId: string, error: Error) => {
      this.emit('agent:task_failed', agent.id, taskId, error);
    });
  }

  /**
   * Remove event listeners for an agent
   */
  private removeAgentListeners(agent: Agent): void {
    agent.removeAllListeners('status:changed');
    agent.removeAllListeners('task:completed');
    agent.removeAllListeners('task:failed');
  }

  /**
   * Thread-safe operation execution
   */
  private async withLock<T>(
    key: string,
    operation: () => Promise<T> | T
  ): Promise<T> {
    // Wait for any existing lock
    while (this.lock.has(key)) {
      await this.lock.get(key);
    }

    // Create new lock
    let resolveLock: () => void;
    const lockPromise = new Promise<void>(resolve => {
      resolveLock = resolve;
    });
    this.lock.set(key, lockPromise);

    try {
      const result = await operation();
      return result;
    } finally {
      // Release lock
      this.lock.delete(key);
      resolveLock!();
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopHealthMonitoring();
    this.agents.clear();
    this.capabilityIndex.clear();
    this.typeIndex.clear();
    this.statusIndex.clear();
    this.removeAllListeners();
  }
}
