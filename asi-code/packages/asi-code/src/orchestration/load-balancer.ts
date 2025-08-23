/**
 * ASI-Code Load Balancer Implementation
 *
 * Intelligent task distribution and load balancing for agents.
 * Supports multiple balancing strategies and smart task-to-agent matching.
 */

import { EventEmitter } from 'eventemitter3';
import {
  Agent,
  AgentMetrics,
  AgentPerformance,
  LoadBalancer as ILoadBalancer,
  ResourceUtilization,
  Task,
} from './types.js';

export type LoadBalancingStrategy =
  | 'round_robin'
  | 'least_loaded'
  | 'capability_based'
  | 'performance_based'
  | 'resource_aware'
  | 'hybrid';

export interface LoadBalancerConfig {
  strategy: LoadBalancingStrategy;

  // Strategy-specific weights
  weights?: {
    performance?: number;
    capacity?: number;
    capability?: number;
    resource?: number;
  };

  // Load calculation parameters
  loadFactors?: {
    taskCount?: number;
    resourceUtilization?: number;
    responseTime?: number;
    errorRate?: number;
  };

  // Rebalancing thresholds
  rebalanceThresholds?: {
    maxLoadImbalance?: number;
    minIdleAgents?: number;
    maxQueueDepth?: number;
  };

  // Performance tracking
  trackingWindowMs?: number;
  minDataPoints?: number;
}

interface AgentLoad {
  agentId: string;
  totalLoad: number;
  taskCount: number;
  resourceLoad: number;
  performanceScore: number;
  capacity: number;
  utilizationRatio: number;
}

interface LoadStats {
  totalLoad: number;
  averageLoad: number;
  maxLoad: number;
  minLoad: number;
  loadVariance: number;
  imbalanceRatio: number;
}

export class LoadBalancer extends EventEmitter implements ILoadBalancer {
  private config: Required<LoadBalancerConfig>;
  private roundRobinIndex = 0;
  private readonly loadHistory = new Map<string, number[]>();
  private readonly performanceHistory = new Map<string, AgentPerformance[]>();
  private lastRebalanceTime = 0;

  constructor(config: Partial<LoadBalancerConfig> = {}) {
    super();

    this.config = {
      strategy: config.strategy || 'hybrid',
      weights: {
        performance: 0.3,
        capacity: 0.25,
        capability: 0.25,
        resource: 0.2,
        ...config.weights,
      },
      loadFactors: {
        taskCount: 0.4,
        resourceUtilization: 0.3,
        responseTime: 0.2,
        errorRate: 0.1,
        ...config.loadFactors,
      },
      rebalanceThresholds: {
        maxLoadImbalance: 0.3,
        minIdleAgents: 1,
        maxQueueDepth: 10,
        ...config.rebalanceThresholds,
      },
      trackingWindowMs: config.trackingWindowMs || 300000, // 5 minutes
      minDataPoints: config.minDataPoints || 10,
    };
  }

  /**
   * Select the best agent for a task using the configured strategy
   */
  selectAgent(task: Task, agents: Agent[]): Agent | undefined {
    if (agents.length === 0) {
      return undefined;
    }

    // Filter agents that can handle the task
    const capableAgents = agents.filter(agent => agent.canHandle(task));

    if (capableAgents.length === 0) {
      return undefined;
    }

    // Apply the configured strategy
    switch (this.config.strategy) {
      case 'round_robin':
        return this.selectRoundRobin(capableAgents);

      case 'least_loaded':
        return this.selectLeastLoaded(capableAgents);

      case 'capability_based':
        return this.selectByCapability(task, capableAgents);

      case 'performance_based':
        return this.selectByPerformance(capableAgents);

      case 'resource_aware':
        return this.selectByResourceAvailability(task, capableAgents);

      case 'hybrid':
        return this.selectHybrid(task, capableAgents);

      default:
        return this.selectHybrid(task, capableAgents);
    }
  }

  /**
   * Get current load for an agent
   */
  getLoad(agent: Agent): number {
    return this.calculateAgentLoad(agent).totalLoad;
  }

  /**
   * Rebalance tasks across agents
   */
  rebalance(agents: Agent[], tasks: Task[]): Map<string, string[]> {
    const rebalanceMap = new Map<string, string[]>();

    if (agents.length === 0 || tasks.length === 0) {
      return rebalanceMap;
    }

    // Calculate current loads
    const agentLoads = agents.map(agent => this.calculateAgentLoad(agent));
    const loadStats = this.calculateLoadStats(agentLoads);

    // Check if rebalancing is needed
    if (!this.shouldRebalance(loadStats, tasks.length)) {
      return rebalanceMap;
    }

    // Group tasks by priority and type
    const taskGroups = this.groupTasks(tasks);

    // Create optimal distribution
    const optimalDistribution = this.calculateOptimalDistribution(
      agentLoads,
      taskGroups,
      loadStats
    );

    // Generate rebalance assignments
    optimalDistribution.forEach((taskIds, agentId) => {
      if (taskIds.length > 0) {
        rebalanceMap.set(agentId, taskIds);
      }
    });

    this.lastRebalanceTime = Date.now();
    this.emit('rebalance:completed', rebalanceMap, loadStats);

    return rebalanceMap;
  }

  /**
   * Get load balancing statistics
   */
  getStats(): LoadStats & {
    strategyUsed: LoadBalancingStrategy;
    rebalanceCount: number;
    lastRebalanceTime: number;
  } {
    // This would typically be calculated from current agents
    // For now, return default stats
    return {
      totalLoad: 0,
      averageLoad: 0,
      maxLoad: 0,
      minLoad: 0,
      loadVariance: 0,
      imbalanceRatio: 0,
      strategyUsed: this.config.strategy,
      rebalanceCount: 0,
      lastRebalanceTime: this.lastRebalanceTime,
    };
  }

  /**
   * Update load balancer configuration
   */
  updateConfig(newConfig: Partial<LoadBalancerConfig>): void {
    this.config = {
      ...this.config,
      ...newConfig,
      weights: { ...this.config.weights, ...newConfig.weights },
      loadFactors: { ...this.config.loadFactors, ...newConfig.loadFactors },
      rebalanceThresholds: {
        ...this.config.rebalanceThresholds,
        ...newConfig.rebalanceThresholds,
      },
    };

    this.emit('config:updated', this.config);
  }

  // Strategy Implementations

  /**
   * Round-robin agent selection
   */
  private selectRoundRobin(agents: Agent[]): Agent {
    const agent = agents[this.roundRobinIndex % agents.length];
    this.roundRobinIndex++;
    return agent;
  }

  /**
   * Select agent with least load
   */
  private selectLeastLoaded(agents: Agent[]): Agent {
    const agentLoads = agents.map(agent => ({
      agent,
      load: this.calculateAgentLoad(agent).totalLoad,
    }));

    agentLoads.sort((a, b) => a.load - b.load);
    return agentLoads[0].agent;
  }

  /**
   * Select agent based on capability matching
   */
  private selectByCapability(task: Task, agents: Agent[]): Agent {
    const scored = agents.map(agent => ({
      agent,
      score: this.calculateCapabilityScore(task, agent),
    }));

    scored.sort((a, b) => b.score - a.score);
    return scored[0].agent;
  }

  /**
   * Select agent based on performance metrics
   */
  private selectByPerformance(agents: Agent[]): Agent {
    const scored = agents.map(agent => ({
      agent,
      score: this.calculatePerformanceScore(agent),
    }));

    scored.sort((a, b) => b.score - a.score);
    return scored[0].agent;
  }

  /**
   * Select agent based on resource availability
   */
  private selectByResourceAvailability(task: Task, agents: Agent[]): Agent {
    const scored = agents.map(agent => ({
      agent,
      score: this.calculateResourceScore(task, agent),
    }));

    scored.sort((a, b) => b.score - a.score);
    return scored[0].agent;
  }

  /**
   * Hybrid selection combining multiple factors
   */
  private selectHybrid(task: Task, agents: Agent[]): Agent {
    const scored = agents.map(agent => {
      const performanceScore = this.calculatePerformanceScore(agent);
      const capabilityScore = this.calculateCapabilityScore(task, agent);
      const resourceScore = this.calculateResourceScore(task, agent);
      const loadScore = 1 - this.calculateAgentLoad(agent).totalLoad / 100;

      const totalScore =
        performanceScore * this.config.weights.performance! +
        capabilityScore * this.config.weights.capability! +
        resourceScore * this.config.weights.resource! +
        loadScore * this.config.weights.capacity!;

      return {
        agent,
        score: totalScore,
        breakdown: {
          performance: performanceScore,
          capability: capabilityScore,
          resource: resourceScore,
          load: loadScore,
        },
      };
    });

    scored.sort((a, b) => b.score - a.score);

    // Emit selection details for monitoring
    this.emit('agent:selected', {
      task: task.id,
      agent: scored[0].agent.id,
      score: scored[0].score,
      breakdown: scored[0].breakdown,
      alternatives: scored.slice(1, 3).map(s => ({
        agent: s.agent.id,
        score: s.score,
      })),
    });

    return scored[0].agent;
  }

  // Load Calculation Methods

  /**
   * Calculate comprehensive load for an agent
   */
  private calculateAgentLoad(agent: Agent): AgentLoad {
    const metrics = agent.getMetrics();
    const config = agent.config;

    // Task count load (0-100)
    const taskLoad =
      (agent.currentTasks.size / config.maxConcurrentTasks) * 100;

    // Resource utilization load (0-100)
    const resourceUtil = metrics.performance.resourceUtilization;
    const resourceLoad = Math.max(resourceUtil.cpu, resourceUtil.memory) * 100;

    // Performance-based load adjustment
    const performanceMultiplier =
      metrics.performance.successRate > 0
        ? 1 / metrics.performance.successRate
        : 2; // Penalize agents with no success rate data

    // Response time factor
    const responseTimeFactor =
      metrics.performance.averageTaskDuration > 0
        ? Math.min(metrics.performance.averageTaskDuration / 1000, 10) // Cap at 10 seconds
        : 1;

    // Calculate weighted total load
    const totalLoad =
      taskLoad * this.config.loadFactors.taskCount! +
      resourceLoad * this.config.loadFactors.resourceUtilization! +
      responseTimeFactor * 10 * this.config.loadFactors.responseTime! +
      (1 - metrics.performance.successRate) *
        100 *
        this.config.loadFactors.errorRate!;

    return {
      agentId: agent.id,
      totalLoad: Math.min(totalLoad * performanceMultiplier, 100),
      taskCount: agent.currentTasks.size,
      resourceLoad,
      performanceScore: metrics.performance.successRate,
      capacity: config.maxConcurrentTasks,
      utilizationRatio: agent.currentTasks.size / config.maxConcurrentTasks,
    };
  }

  /**
   * Calculate capability match score for a task
   */
  private calculateCapabilityScore(task: Task, agent: Agent): number {
    const requiredCaps = task.constraints?.requiredCapabilities || [];
    const agentCaps = agent.getCapabilities();

    if (requiredCaps.length === 0) {
      return 1; // No specific requirements
    }

    const matchedCaps = requiredCaps.filter(cap => agentCaps.includes(cap));
    const matchRatio = matchedCaps.length / requiredCaps.length;

    // Bonus for exact capability matches
    const exactMatch = requiredCaps.every(cap => agentCaps.includes(cap));
    const bonus = exactMatch ? 0.2 : 0;

    // Penalty for over-qualification (having too many capabilities)
    const overQualificationPenalty = Math.max(
      0,
      (agentCaps.length - requiredCaps.length) * 0.01
    );

    return Math.min(1, matchRatio + bonus - overQualificationPenalty);
  }

  /**
   * Calculate performance score for an agent
   */
  private calculatePerformanceScore(agent: Agent): number {
    const metrics = agent.getMetrics();
    const performance = metrics.performance;

    // Base score from success rate
    let score = performance.successRate;

    // Factor in throughput (tasks per minute)
    const throughputBonus = Math.min(performance.taskThroughput / 10, 0.2);
    score += throughputBonus;

    // Factor in average response time (faster is better)
    if (performance.averageTaskDuration > 0) {
      const responseTimeBonus = Math.max(
        0,
        0.1 - performance.averageTaskDuration / 60000
      ); // Convert to minutes
      score += responseTimeBonus;
    }

    // Factor in uptime
    const uptimeBonus = (metrics.uptime / (24 * 60 * 60 * 1000)) * 0.05; // Days uptime * 5%
    score += Math.min(uptimeBonus, 0.1);

    return Math.min(score, 1);
  }

  /**
   * Calculate resource availability score
   */
  private calculateResourceScore(task: Task, agent: Agent): number {
    const metrics = agent.getMetrics();
    const resourceUtil = metrics.performance.resourceUtilization;
    const requiredResources = task.constraints?.requiredResources;

    // Base availability score (higher available resources = higher score)
    const availabilityScore =
      1 - Math.max(resourceUtil.cpu, resourceUtil.memory);

    // Check specific resource requirements
    let requirementScore = 1;
    if (requiredResources) {
      if (
        requiredResources.cpu &&
        resourceUtil.cpu > 1 - requiredResources.cpu
      ) {
        requirementScore *= 0.5; // Insufficient CPU
      }
      if (
        requiredResources.memory &&
        resourceUtil.memory > 1 - requiredResources.memory
      ) {
        requirementScore *= 0.5; // Insufficient memory
      }
    }

    return availabilityScore * requirementScore;
  }

  /**
   * Calculate load statistics for a set of agents
   */
  private calculateLoadStats(agentLoads: AgentLoad[]): LoadStats {
    if (agentLoads.length === 0) {
      return {
        totalLoad: 0,
        averageLoad: 0,
        maxLoad: 0,
        minLoad: 0,
        loadVariance: 0,
        imbalanceRatio: 0,
      };
    }

    const loads = agentLoads.map(al => al.totalLoad);
    const totalLoad = loads.reduce((sum, load) => sum + load, 0);
    const averageLoad = totalLoad / loads.length;
    const maxLoad = Math.max(...loads);
    const minLoad = Math.min(...loads);

    // Calculate variance
    const variance =
      loads.reduce((sum, load) => sum + Math.pow(load - averageLoad, 2), 0) /
      loads.length;

    // Calculate imbalance ratio (how far from perfect balance)
    const imbalanceRatio =
      averageLoad > 0 ? (maxLoad - minLoad) / averageLoad : 0;

    return {
      totalLoad,
      averageLoad,
      maxLoad,
      minLoad,
      loadVariance: variance,
      imbalanceRatio,
    };
  }

  /**
   * Determine if rebalancing is needed
   */
  private shouldRebalance(loadStats: LoadStats, taskCount: number): boolean {
    const { maxLoadImbalance, minIdleAgents, maxQueueDepth } =
      this.config.rebalanceThresholds;
    const timeSinceLastRebalance = Date.now() - this.lastRebalanceTime;

    // Don't rebalance too frequently (minimum 30 seconds)
    if (timeSinceLastRebalance < 30000) {
      return false;
    }

    // Rebalance if load imbalance is too high
    if (loadStats.imbalanceRatio > maxLoadImbalance!) {
      return true;
    }

    // Rebalance if queue depth is too high
    if (taskCount > maxQueueDepth!) {
      return true;
    }

    return false;
  }

  /**
   * Group tasks by characteristics for better distribution
   */
  private groupTasks(tasks: Task[]): Map<string, Task[]> {
    const groups = new Map<string, Task[]>();

    for (const task of tasks) {
      // Group by priority and type
      const groupKey = `${task.priority}_${task.type}`;

      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)!.push(task);
    }

    return groups;
  }

  /**
   * Calculate optimal task distribution
   */
  private calculateOptimalDistribution(
    agentLoads: AgentLoad[],
    taskGroups: Map<string, Task[]>,
    loadStats: LoadStats
  ): Map<string, string[]> {
    const distribution = new Map<string, string[]>();

    // Sort agents by current load (least loaded first)
    const sortedAgents = [...agentLoads].sort(
      (a, b) => a.totalLoad - b.totalLoad
    );

    // Distribute tasks starting with highest priority
    const priorityOrder = ['critical', 'high', 'medium', 'low'];

    for (const priority of priorityOrder) {
      taskGroups.forEach((tasks, groupKey) => {
        if (!groupKey.startsWith(priority)) return;

        for (const task of tasks) {
          // Find best agent for this task
          const bestAgent = this.findBestAgentForRebalance(task, sortedAgents);
          if (bestAgent) {
            if (!distribution.has(bestAgent.agentId)) {
              distribution.set(bestAgent.agentId, []);
            }
            distribution.get(bestAgent.agentId)!.push(task.id);

            // Update agent load for next iteration
            bestAgent.taskCount++;
            bestAgent.utilizationRatio =
              bestAgent.taskCount / bestAgent.capacity;
            bestAgent.totalLoad = this.estimateLoadWithNewTask(bestAgent, task);
          }
        }
      });
    }

    return distribution;
  }

  /**
   * Find best agent for rebalancing a specific task
   */
  private findBestAgentForRebalance(
    task: Task,
    agentLoads: AgentLoad[]
  ): AgentLoad | undefined {
    // Filter agents that aren't overloaded and can handle the task
    const availableAgents = agentLoads.filter(
      agent =>
        agent.utilizationRatio < 0.9 && // Not overloaded
        agent.totalLoad < 80 // Not at capacity
    );

    if (availableAgents.length === 0) {
      return undefined;
    }

    // Score agents based on load and capability
    const scoredAgents = availableAgents.map(agent => ({
      agent,
      score: this.calculateRebalanceScore(agent, task),
    }));

    scoredAgents.sort((a, b) => b.score - a.score);
    return scoredAgents[0]?.agent;
  }

  /**
   * Calculate rebalance score for an agent
   */
  private calculateRebalanceScore(agentLoad: AgentLoad, task: Task): number {
    // Lower load = higher score
    const loadScore = 1 - agentLoad.totalLoad / 100;

    // Lower utilization = higher score
    const utilizationScore = 1 - agentLoad.utilizationRatio;

    // Performance score
    const performanceScore = agentLoad.performanceScore;

    return loadScore * 0.4 + utilizationScore * 0.4 + performanceScore * 0.2;
  }

  /**
   * Estimate agent load after adding a new task
   */
  private estimateLoadWithNewTask(agentLoad: AgentLoad, task: Task): number {
    // Simple estimation - could be more sophisticated
    const taskLoadEstimate = 100 / agentLoad.capacity; // Each task adds this much load
    return Math.min(agentLoad.totalLoad + taskLoadEstimate, 100);
  }

  /**
   * Track agent performance over time
   */
  trackPerformance(agent: Agent): void {
    const metrics = agent.getMetrics();
    const agentId = agent.id;

    // Track load history
    if (!this.loadHistory.has(agentId)) {
      this.loadHistory.set(agentId, []);
    }
    const loadHistory = this.loadHistory.get(agentId)!;
    loadHistory.push(this.getLoad(agent));

    // Keep only recent data
    const maxDataPoints = Math.max(this.config.minDataPoints, 100);
    if (loadHistory.length > maxDataPoints) {
      loadHistory.shift();
    }

    // Track performance history
    if (!this.performanceHistory.has(agentId)) {
      this.performanceHistory.set(agentId, []);
    }
    const perfHistory = this.performanceHistory.get(agentId)!;
    perfHistory.push({ ...metrics.performance });

    if (perfHistory.length > maxDataPoints) {
      perfHistory.shift();
    }
  }

  /**
   * Get historical performance data for an agent
   */
  getPerformanceHistory(agentId: string): {
    loadHistory: number[];
    performanceHistory: AgentPerformance[];
  } {
    return {
      loadHistory: this.loadHistory.get(agentId) || [],
      performanceHistory: this.performanceHistory.get(agentId) || [],
    };
  }

  /**
   * Clear all historical data
   */
  clearHistory(): void {
    this.loadHistory.clear();
    this.performanceHistory.clear();
  }
}
