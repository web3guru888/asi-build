/**
 * ASI-Code Agent Orchestrator
 * 
 * Main orchestration system that manages supervisors, agents, and tasks.
 * This is the primary interface for the agent orchestration framework.
 */

import { EventEmitter } from 'eventemitter3';
import {
  Orchestrator as IOrchestrator,
  SupervisorAgent,
  Agent,
  AgentConfig,
  AgentType,
  AgentStatus,
  Task,
  TaskStatus,
  SystemStatus,
  OrchestratorMetrics,
  OrchestrationEvents
} from './types.js';
import { SupervisorAgent as SupervisorAgentImpl } from './supervisor-agent.js';
import { WorkerAgent } from './worker-agent.js';
import { AgentRegistry } from './agent-registry.js';
import { Logger } from '../logging/index.js';
import { v4 as uuidv4 } from 'uuid';

export class Orchestrator extends EventEmitter<OrchestrationEvents> implements IOrchestrator {
  public supervisors: Map<string, SupervisorAgent>;
  public agents: Map<string, Agent>;
  public taskRegistry: Map<string, Task>;
  
  private agentRegistry: AgentRegistry;
  private logger: Logger;
  private startTime: number;
  private completedTasks: number = 0;
  private failedTasks: number = 0;
  private systemMonitor: NodeJS.Timer | null = null;
  
  constructor(logger?: Logger) {
    super();
    
    this.supervisors = new Map();
    this.agents = new Map();
    this.taskRegistry = new Map();
    this.agentRegistry = new AgentRegistry();
    
    this.logger = logger || new Logger({
      component: 'Orchestrator',
      level: 'info'
    });
    
    this.startTime = Date.now();
    this.initialize();
  }
  
  /**
   * Initialize orchestrator
   */
  private async initialize(): Promise<void> {
    this.logger.info('Initializing ASI-Code Agent Orchestrator');
    
    // Create default supervisor
    await this.createDefaultSupervisor();
    
    // Start system monitoring
    this.startSystemMonitoring();
    
    // Setup event handlers
    this.setupEventHandlers();
    
    this.logger.info('Agent Orchestrator initialized successfully');
  }
  
  /**
   * Create a new supervisor agent
   */
  async createSupervisor(config: AgentConfig): Promise<SupervisorAgent> {
    this.logger.info(`Creating supervisor with config:`, config);
    
    const supervisorConfig = {
      ...config,
      id: config.id || `supervisor-${uuidv4()}`,
      type: 'supervisor' as AgentType
    };
    
    const supervisor = new SupervisorAgentImpl(supervisorConfig, this.logger);
    await supervisor.initialize();
    
    // Register supervisor
    this.supervisors.set(supervisor.id, supervisor);
    this.agents.set(supervisor.id, supervisor);
    this.agentRegistry.register(supervisor);
    
    // Setup supervisor event handlers
    this.setupSupervisorEventHandlers(supervisor);
    
    this.emit('supervisor:created', supervisor);
    this.logger.info(`Supervisor ${supervisor.id} created successfully`);
    
    return supervisor;
  }
  
  /**
   * Submit a task for execution
   */
  async submitTask(task: Task): Promise<string> {
    // Ensure task has an ID
    if (!task.id) {
      task.id = `task-${uuidv4()}`;
    }
    
    this.logger.info(`Submitting task ${task.id}: ${task.description}`);
    
    // Register task
    task.status = 'pending';
    task.createdAt = Date.now();
    this.taskRegistry.set(task.id, task);
    
    // Find best supervisor for task
    const supervisor = this.selectSupervisor(task);
    
    if (!supervisor) {
      throw new Error('No supervisor available to handle task');
    }
    
    // Submit task to supervisor
    try {
      // Check if task needs decomposition
      if (await this.shouldDecompose(task)) {
        await supervisor.decomposeTask(task);
      } else {
        await supervisor.assignTask(task);
      }
      
      this.emit('task:submitted', task);
      
      return task.id;
      
    } catch (error) {
      task.status = 'failed';
      task.error = error as Error;
      this.failedTasks++;
      
      this.logger.error(`Failed to submit task ${task.id}:`, error);
      throw error;
    }
  }
  
  /**
   * Get task status
   */
  getTaskStatus(taskId: string): TaskStatus | undefined {
    const task = this.taskRegistry.get(taskId);
    return task?.status;
  }
  
  /**
   * Get task result
   */
  async getTaskResult(taskId: string): Promise<any> {
    const task = this.taskRegistry.get(taskId);
    
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }
    
    // Wait for task completion if still pending
    if (task.status === 'pending' || task.status === 'assigned' || task.status === 'in_progress') {
      return await this.waitForTask(taskId);
    }
    
    if (task.status === 'failed') {
      throw task.error || new Error(`Task ${taskId} failed`);
    }
    
    return task.output;
  }
  
  /**
   * Cancel a task
   */
  async cancelTask(taskId: string): Promise<boolean> {
    const task = this.taskRegistry.get(taskId);
    
    if (!task) {
      return false;
    }
    
    if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
      return false;
    }
    
    this.logger.info(`Cancelling task ${taskId}`);
    
    // Find assigned agent and cancel
    if (task.assignedAgent) {
      const agent = this.agents.get(task.assignedAgent);
      if (agent && agent.currentTasks.has(taskId)) {
        // Agent doesn't have direct cancel, so we mark task as cancelled
        task.status = 'cancelled';
        task.completedAt = Date.now();
        
        this.emit('task:cancelled', taskId);
        return true;
      }
    }
    
    // Cancel subtasks if decomposed
    if (task.subtasks) {
      for (const subtaskId of task.subtasks) {
        await this.cancelTask(subtaskId);
      }
    }
    
    task.status = 'cancelled';
    task.completedAt = Date.now();
    
    return true;
  }
  
  /**
   * Deploy a new agent
   */
  async deployAgent(config: AgentConfig, supervisorId?: string): Promise<Agent> {
    this.logger.info(`Deploying agent with config:`, config);
    
    // Select supervisor
    let supervisor: SupervisorAgent | undefined;
    
    if (supervisorId) {
      supervisor = this.supervisors.get(supervisorId);
      if (!supervisor) {
        throw new Error(`Supervisor ${supervisorId} not found`);
      }
    } else {
      supervisor = this.selectSupervisorForDeployment();
      if (!supervisor) {
        throw new Error('No supervisor available for agent deployment');
      }
    }
    
    // Deploy agent through supervisor
    const agent = await supervisor.deployAgent(config);
    
    // Register globally
    this.agents.set(agent.id, agent);
    this.agentRegistry.register(agent);
    
    this.emit('agent:deployed', agent);
    
    return agent;
  }
  
  /**
   * Scale agents to target count
   */
  async scaleAgents(targetCount: number, type?: AgentType): Promise<void> {
    this.logger.info(`Scaling ${type || 'all'} agents to ${targetCount}`);
    
    const currentAgents = type 
      ? this.agentRegistry.findByType(type)
      : this.agentRegistry.getAll();
    
    const currentCount = currentAgents.length;
    
    if (currentCount < targetCount) {
      // Scale up
      const toAdd = targetCount - currentCount;
      
      for (let i = 0; i < toAdd; i++) {
        const config: AgentConfig = {
          name: `${type || 'Worker'}-${uuidv4().slice(0, 8)}`,
          type: type || 'worker',
          capabilities: this.getDefaultCapabilities(type || 'worker'),
          maxConcurrentTasks: 3
        };
        
        await this.deployAgent(config);
      }
      
    } else if (currentCount > targetCount) {
      // Scale down
      const toRemove = currentCount - targetCount;
      const agentsToRemove = currentAgents.slice(0, toRemove);
      
      for (const agent of agentsToRemove) {
        await this.terminateAgent(agent.id);
      }
    }
    
    this.logger.info(`Scaling complete: ${currentCount} -> ${targetCount} agents`);
  }
  
  /**
   * Terminate an agent
   */
  async terminateAgent(agentId: string): Promise<void> {
    this.logger.info(`Terminating agent ${agentId}`);
    
    const agent = this.agents.get(agentId);
    if (!agent) {
      throw new Error(`Agent ${agentId} not found`);
    }
    
    // Find managing supervisor
    let managingSupervisor: SupervisorAgent | undefined;
    
    for (const supervisor of this.supervisors.values()) {
      if (supervisor.managedAgents.has(agentId)) {
        managingSupervisor = supervisor;
        break;
      }
    }
    
    if (managingSupervisor) {
      await managingSupervisor.decommissionAgent(agentId);
    } else {
      await agent.terminate();
    }
    
    // Remove from registries
    this.agents.delete(agentId);
    this.agentRegistry.unregister(agentId);
    
    this.emit('agent:terminated', agentId);
  }
  
  /**
   * Get system status
   */
  getSystemStatus(): SystemStatus {
    const agents = this.agentRegistry.getAll();
    const activeTasks = Array.from(this.taskRegistry.values())
      .filter(t => t.status === 'in_progress' || t.status === 'assigned');
    const queuedTasks = Array.from(this.taskRegistry.values())
      .filter(t => t.status === 'pending');
    
    // Calculate system load
    let totalCapacity = 0;
    let totalUsed = 0;
    
    for (const agent of agents) {
      totalCapacity += agent.config.maxConcurrentTasks;
      totalUsed += agent.currentTasks.size;
    }
    
    const systemLoad = totalCapacity > 0 ? (totalUsed / totalCapacity) * 100 : 0;
    
    return {
      healthy: this.isSystemHealthy(),
      supervisorCount: this.supervisors.size,
      agentCount: this.agents.size,
      activeTasks: activeTasks.length,
      completedTasks: this.completedTasks,
      failedTasks: this.failedTasks,
      queuedTasks: queuedTasks.length,
      systemLoad,
      uptime: Date.now() - this.startTime
    };
  }
  
  /**
   * Get agent statuses
   */
  getAgentStatuses(): Map<string, AgentStatus> {
    const statuses = new Map<string, AgentStatus>();
    
    for (const [id, agent] of this.agents) {
      statuses.set(id, agent.status);
    }
    
    return statuses;
  }
  
  /**
   * Get task statuses
   */
  getTaskStatuses(): Map<string, TaskStatus> {
    const statuses = new Map<string, TaskStatus>();
    
    for (const [id, task] of this.taskRegistry) {
      statuses.set(id, task.status);
    }
    
    return statuses;
  }
  
  /**
   * Get orchestrator metrics
   */
  getMetrics(): OrchestratorMetrics {
    const totalTasks = this.completedTasks + this.failedTasks;
    const uptime = (Date.now() - this.startTime) / 1000; // in seconds
    
    // Calculate average task duration
    let totalDuration = 0;
    let taskCount = 0;
    
    for (const task of this.taskRegistry.values()) {
      if (task.completedAt && task.startedAt) {
        totalDuration += task.completedAt - task.startedAt;
        taskCount++;
      }
    }
    
    const averageTaskDuration = taskCount > 0 ? totalDuration / taskCount : 0;
    
    // Calculate agent utilization
    const agents = this.agentRegistry.getAll();
    let totalUtilization = 0;
    
    for (const agent of agents) {
      const capacity = agent.config.maxConcurrentTasks;
      const used = agent.currentTasks.size;
      totalUtilization += (used / capacity) * 100;
    }
    
    const agentUtilization = agents.length > 0 ? totalUtilization / agents.length : 0;
    
    // Queue depth
    const queueDepth = Array.from(this.taskRegistry.values())
      .filter(t => t.status === 'pending').length;
    
    return {
      taskThroughput: totalTasks / uptime,
      averageTaskDuration,
      agentUtilization,
      queueDepth,
      successRate: totalTasks > 0 ? (this.completedTasks / totalTasks) * 100 : 100,
      errorRate: totalTasks > 0 ? (this.failedTasks / totalTasks) * 100 : 0
    };
  }
  
  /**
   * Shutdown orchestrator
   */
  async shutdown(): Promise<void> {
    this.logger.info('Shutting down Agent Orchestrator');
    
    // Stop system monitoring
    if (this.systemMonitor) {
      clearInterval(this.systemMonitor);
      this.systemMonitor = null;
    }
    
    // Terminate all agents
    for (const agent of this.agents.values()) {
      await agent.terminate();
    }
    
    // Clear registries
    this.supervisors.clear();
    this.agents.clear();
    this.taskRegistry.clear();
    
    this.logger.info('Agent Orchestrator shutdown complete');
  }
  
  // Private helper methods
  
  private async createDefaultSupervisor(): Promise<void> {
    const config: AgentConfig = {
      name: 'Default-Supervisor',
      type: 'supervisor',
      capabilities: ['task-decomposition', 'agent-management', 'coordination'],
      maxConcurrentTasks: 100,
      metadata: {
        initialWorkers: 3
      }
    };
    
    await this.createSupervisor(config);
  }
  
  private startSystemMonitoring(): void {
    this.systemMonitor = setInterval(() => {
      this.monitorSystem();
    }, 10000); // Monitor every 10 seconds
  }
  
  private monitorSystem(): void {
    const status = this.getSystemStatus();
    const metrics = this.getMetrics();
    
    // Check for system overload
    if (status.systemLoad > 90) {
      this.emit('system:overloaded', status.systemLoad);
      this.handleSystemOverload();
    } else if (status.systemLoad < 50 && this.wasOverloaded) {
      this.emit('system:recovered');
      this.wasOverloaded = false;
    }
    
    // Log metrics periodically
    if (Math.random() < 0.1) { // 10% chance to log
      this.logger.info('System metrics:', metrics);
    }
  }
  
  private wasOverloaded = false;
  
  private handleSystemOverload(): void {
    this.wasOverloaded = true;
    this.logger.warn('System overloaded, initiating auto-scaling');
    
    // Auto-scale workers
    this.scaleAgents(this.agents.size + 2, 'worker').catch(error => {
      this.logger.error('Failed to auto-scale:', error);
    });
  }
  
  private setupEventHandlers(): void {
    this.on('task:completed', (data) => {
      this.completedTasks++;
      const task = this.taskRegistry.get(data.taskId);
      if (task) {
        task.status = 'completed';
        task.completedAt = Date.now();
      }
    });
    
    this.on('task:failed', (data) => {
      this.failedTasks++;
      const task = this.taskRegistry.get(data.taskId);
      if (task) {
        task.status = 'failed';
        task.completedAt = Date.now();
      }
    });
  }
  
  private setupSupervisorEventHandlers(supervisor: SupervisorAgent): void {
    supervisor.on('agent:deployed', (agent) => {
      this.agents.set(agent.id, agent);
      this.agentRegistry.register(agent);
    });
    
    supervisor.on('agent:decommissioned', (agentId) => {
      this.agents.delete(agentId);
      this.agentRegistry.unregister(agentId);
    });
    
    supervisor.on('task:completed', (data) => {
      this.emit('task:completed', data);
    });
    
    supervisor.on('task:failed', (data) => {
      this.emit('task:failed', data);
    });
  }
  
  private selectSupervisor(task: Task): SupervisorAgent | undefined {
    // Select supervisor with lowest load
    let bestSupervisor: SupervisorAgent | undefined;
    let lowestLoad = Infinity;
    
    for (const supervisor of this.supervisors.values()) {
      if (supervisor.status === 'terminated' || supervisor.status === 'error') {
        continue;
      }
      
      const load = supervisor.currentTasks.size;
      if (load < lowestLoad) {
        lowestLoad = load;
        bestSupervisor = supervisor;
      }
    }
    
    return bestSupervisor;
  }
  
  private selectSupervisorForDeployment(): SupervisorAgent | undefined {
    // Select supervisor with fewest managed agents
    let bestSupervisor: SupervisorAgent | undefined;
    let fewestAgents = Infinity;
    
    for (const supervisor of this.supervisors.values()) {
      if (supervisor.status === 'terminated' || supervisor.status === 'error') {
        continue;
      }
      
      const agentCount = supervisor.managedAgents.size;
      if (agentCount < fewestAgents) {
        fewestAgents = agentCount;
        bestSupervisor = supervisor;
      }
    }
    
    return bestSupervisor;
  }
  
  private async shouldDecompose(task: Task): Promise<boolean> {
    // Check task metadata
    if (task.metadata?.decompose === true) {
      return true;
    }
    
    // Check task complexity
    const complexityIndicators = [
      task.description.length > 200,
      task.description.includes(' and '),
      task.description.includes(' then '),
      task.dependencies && task.dependencies.length > 2
    ];
    
    const complexityScore = complexityIndicators.filter(Boolean).length;
    return complexityScore >= 2;
  }
  
  private async waitForTask(taskId: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        const task = this.taskRegistry.get(taskId);
        
        if (!task) {
          clearInterval(checkInterval);
          reject(new Error(`Task ${taskId} not found`));
          return;
        }
        
        if (task.status === 'completed') {
          clearInterval(checkInterval);
          resolve(task.output);
        } else if (task.status === 'failed') {
          clearInterval(checkInterval);
          reject(task.error || new Error(`Task ${taskId} failed`));
        } else if (task.status === 'cancelled') {
          clearInterval(checkInterval);
          reject(new Error(`Task ${taskId} was cancelled`));
        }
      }, 1000);
      
      // Add timeout
      setTimeout(() => {
        clearInterval(checkInterval);
        reject(new Error(`Task ${taskId} timed out`));
      }, 300000); // 5 minute timeout
    });
  }
  
  private getDefaultCapabilities(type: AgentType): string[] {
    const capabilityMap: Record<AgentType, string[]> = {
      'supervisor': ['task-decomposition', 'agent-management', 'coordination'],
      'worker': ['processing', 'computation', 'io'],
      'specialist': ['analysis', 'optimization', 'validation'],
      'coordinator': ['scheduling', 'routing', 'aggregation'],
      'analyzer': ['data-analysis', 'pattern-recognition', 'reporting'],
      'executor': ['execution', 'scripting', 'automation'],
      'monitor': ['monitoring', 'alerting', 'metrics'],
      'validator': ['validation', 'testing', 'verification']
    };
    
    return capabilityMap[type] || ['general'];
  }
  
  private isSystemHealthy(): boolean {
    // Check if we have at least one active supervisor
    const activeSupervisors = Array.from(this.supervisors.values())
      .filter(s => s.status !== 'terminated' && s.status !== 'error');
    
    if (activeSupervisors.length === 0) {
      return false;
    }
    
    // Check error rate
    const metrics = this.getMetrics();
    if (metrics.errorRate > 50) {
      return false;
    }
    
    return true;
  }
}

/**
 * Create and export a singleton orchestrator instance
 */
export function createOrchestrator(logger?: Logger): Orchestrator {
  return new Orchestrator(logger);
}