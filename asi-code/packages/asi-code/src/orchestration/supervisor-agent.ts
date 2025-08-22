/**
 * Supervisor Agent Implementation
 * 
 * Advanced supervisor agent that manages other agents, decomposes tasks,
 * and coordinates complex multi-agent workflows.
 */

import { BaseAgent } from './base-agent.js';
import { TaskDecomposer } from './task-decomposer.js';
import { LoadBalancer } from './load-balancer.js';
import { TaskQueue } from './task-queue.js';
import { AgentRegistry } from './agent-registry.js';
import { WorkerAgent } from './worker-agent.js';
import {
  SupervisorAgent as ISupervisorAgent,
  Agent,
  AgentConfig,
  Task,
  TaskDecomposition,
  TaskStatus,
  AgentStatus,
  AgentType
} from './types.js';
import { Logger } from '../logging/index.js';
import { v4 as uuidv4 } from 'uuid';

export class SupervisorAgent extends BaseAgent implements ISupervisorAgent {
  public managedAgents: Map<string, Agent>;
  public taskQueue: TaskQueue;
  
  private decomposer: TaskDecomposer;
  private loadBalancer: LoadBalancer;
  private agentRegistry: AgentRegistry;
  private taskAssignments: Map<string, string>; // taskId -> agentId
  private decomposedTasks: Map<string, TaskDecomposition>; // parentTaskId -> decomposition
  private coordinationInterval: NodeJS.Timer | null = null;
  
  constructor(config: AgentConfig, logger?: Logger) {
    // Ensure supervisor has proper type and capabilities
    const supervisorConfig = {
      ...config,
      type: 'supervisor' as AgentType,
      capabilities: [
        ...config.capabilities,
        'task-decomposition',
        'agent-management',
        'coordination'
      ]
    };
    
    super(supervisorConfig, logger);
    
    this.managedAgents = new Map();
    this.taskQueue = new TaskQueue();
    this.decomposer = new TaskDecomposer();
    this.loadBalancer = new LoadBalancer();
    this.agentRegistry = new AgentRegistry();
    this.taskAssignments = new Map();
    this.decomposedTasks = new Map();
  }
  
  /**
   * Initialize supervisor
   */
  protected async onInitialize(): Promise<void> {
    this.logger.info(`Initializing supervisor agent ${this.id}`);
    
    // Start coordination loop
    this.startCoordinationLoop();
    
    // Deploy initial worker agents based on configuration
    const initialWorkerCount = this.config.metadata?.initialWorkers || 3;
    for (let i = 0; i < initialWorkerCount; i++) {
      await this.deployDefaultWorker();
    }
  }
  
  /**
   * Deploy a new agent
   */
  async deployAgent(config: AgentConfig): Promise<Agent> {
    this.logger.info(`Deploying new agent with config:`, config);
    
    // Create agent instance based on type
    let agent: Agent;
    
    switch (config.type) {
      case 'worker':
        agent = new WorkerAgent(config, this.logger);
        break;
      case 'specialist':
        agent = await this.createSpecialistAgent(config);
        break;
      case 'coordinator':
        agent = await this.createCoordinatorAgent(config);
        break;
      default:
        agent = new WorkerAgent(config, this.logger);
    }
    
    // Initialize the agent
    await agent.initialize();
    
    // Register and manage the agent
    this.managedAgents.set(agent.id, agent);
    this.agentRegistry.register(agent);
    
    // Setup agent event handlers
    this.setupAgentEventHandlers(agent);
    
    this.emit('agent:deployed', agent);
    this.logger.info(`Successfully deployed agent ${agent.id}`);
    
    return agent;
  }
  
  /**
   * Decommission an agent
   */
  async decommissionAgent(agentId: string): Promise<void> {
    const agent = this.managedAgents.get(agentId);
    
    if (!agent) {
      throw new Error(`Agent ${agentId} not found`);
    }
    
    this.logger.info(`Decommissioning agent ${agentId}`);
    
    // Reassign any active tasks
    const activeTasks = Array.from(agent.currentTasks);
    for (const taskId of activeTasks) {
      await this.reassignTask(taskId);
    }
    
    // Terminate the agent
    await agent.terminate();
    
    // Remove from management
    this.managedAgents.delete(agentId);
    this.agentRegistry.unregister(agentId);
    
    this.emit('agent:decommissioned', agentId);
    this.logger.info(`Successfully decommissioned agent ${agentId}`);
  }
  
  /**
   * Assign a task to an agent
   */
  async assignTask(task: Task, agentId?: string): Promise<void> {
    this.logger.info(`Assigning task ${task.id} to ${agentId || 'best available agent'}`);
    
    let agent: Agent | undefined;
    
    if (agentId) {
      agent = this.managedAgents.get(agentId);
      if (!agent) {
        throw new Error(`Agent ${agentId} not found`);
      }
      if (!agent.canHandle(task)) {
        throw new Error(`Agent ${agentId} cannot handle task ${task.id}`);
      }
    } else {
      // Use load balancer to find best agent
      const availableAgents = this.agentRegistry.findAvailable();
      agent = this.loadBalancer.selectAgent(task, availableAgents);
      
      if (!agent) {
        // No suitable agent found, queue the task
        this.taskQueue.add(task);
        this.logger.info(`No suitable agent found for task ${task.id}, queued`);
        return;
      }
    }
    
    // Assign task to agent
    this.taskAssignments.set(task.id, agent.id);
    task.assignedAgent = agent.id;
    task.status = 'assigned';
    
    // Execute task on agent
    agent.executeTask(task)
      .then(result => {
        this.handleTaskCompletion(task.id, result);
      })
      .catch(error => {
        this.handleTaskFailure(task.id, error);
      });
    
    this.emit('task:assigned', { taskId: task.id, agentId: agent.id });
  }
  
  /**
   * Decompose a complex task
   */
  async decomposeTask(task: Task): Promise<TaskDecomposition> {
    this.logger.info(`Decomposing task ${task.id}`);
    
    if (!this.decomposer.canDecompose(task)) {
      throw new Error(`Task ${task.id} cannot be decomposed`);
    }
    
    const decomposition = await this.decomposer.decompose(task);
    this.decomposedTasks.set(task.id, decomposition);
    
    // Add subtasks to queue
    for (const subtask of decomposition.subtasks) {
      this.taskQueue.add(subtask);
    }
    
    this.emit('task:decomposed', { 
      taskId: task.id, 
      subtaskCount: decomposition.subtasks.length 
    });
    
    this.logger.info(`Task ${task.id} decomposed into ${decomposition.subtasks.length} subtasks`);
    
    return decomposition;
  }
  
  /**
   * Coordinate managed agents
   */
  async coordinateAgents(): Promise<void> {
    // Check agent health
    await this.checkAgentHealth();
    
    // Process task queue
    await this.processTaskQueue();
    
    // Rebalance tasks if needed
    await this.rebalanceIfNeeded();
    
    // Scale agents based on load
    await this.autoScale();
  }
  
  /**
   * Rebalance tasks across agents
   */
  async rebalanceTasks(): Promise<void> {
    this.logger.info('Rebalancing tasks across agents');
    
    const agents = Array.from(this.managedAgents.values());
    const tasks: Task[] = [];
    
    // Collect all pending and assigned tasks
    this.taskQueue.getPending().forEach(task => tasks.push(task));
    
    // Get tasks from agents
    for (const agent of agents) {
      for (const taskId of agent.currentTasks) {
        const task = this.getTask(taskId);
        if (task) tasks.push(task);
      }
    }
    
    // Use load balancer to rebalance
    const newAssignments = this.loadBalancer.rebalance(agents, tasks);
    
    // Apply new assignments
    for (const [agentId, taskIds] of newAssignments) {
      const agent = this.managedAgents.get(agentId);
      if (!agent) continue;
      
      for (const taskId of taskIds) {
        const task = this.getTask(taskId);
        if (task && task.assignedAgent !== agentId) {
          await this.reassignTask(taskId, agentId);
        }
      }
    }
    
    this.logger.info('Task rebalancing complete');
  }
  
  /**
   * Handle agent failure
   */
  async handleAgentFailure(agentId: string): Promise<void> {
    this.logger.error(`Handling failure of agent ${agentId}`);
    
    const agent = this.managedAgents.get(agentId);
    if (!agent) return;
    
    // Get all tasks assigned to failed agent
    const failedTasks = Array.from(agent.currentTasks);
    
    // Mark agent as failed
    agent.status = 'error';
    
    // Reassign all tasks
    for (const taskId of failedTasks) {
      try {
        await this.reassignTask(taskId);
      } catch (error) {
        this.logger.error(`Failed to reassign task ${taskId}:`, error);
      }
    }
    
    // Try to recover agent or replace it
    try {
      await this.recoverAgent(agentId);
    } catch (error) {
      this.logger.error(`Failed to recover agent ${agentId}, replacing:`, error);
      await this.replaceAgent(agentId);
    }
    
    this.emit('agent:failure:handled', agentId);
  }
  
  /**
   * Execute task (supervisor delegates to managed agents)
   */
  protected async onExecuteTask(task: Task): Promise<any> {
    // Check if task needs decomposition
    if (this.decomposer.canDecompose(task)) {
      const decomposition = await this.decomposeTask(task);
      
      // Wait for all subtasks to complete
      const results = await this.executeSubtasks(decomposition);
      
      // Aggregate results
      return this.aggregateResults(results, decomposition);
    } else {
      // Assign to an agent
      await this.assignTask(task);
      
      // Wait for completion
      return await this.waitForTaskCompletion(task.id);
    }
  }
  
  /**
   * Check if supervisor can handle task
   */
  protected onCanHandle(task: Task): boolean {
    // Supervisor can handle any task by delegation
    return true;
  }
  
  /**
   * Suspend supervisor
   */
  protected async onSuspend(): Promise<void> {
    // Suspend all managed agents
    for (const agent of this.managedAgents.values()) {
      await agent.suspend();
    }
    
    // Stop coordination loop
    if (this.coordinationInterval) {
      clearInterval(this.coordinationInterval);
      this.coordinationInterval = null;
    }
  }
  
  /**
   * Resume supervisor
   */
  protected async onResume(): Promise<void> {
    // Resume all managed agents
    for (const agent of this.managedAgents.values()) {
      await agent.resume();
    }
    
    // Restart coordination loop
    this.startCoordinationLoop();
  }
  
  /**
   * Terminate supervisor
   */
  protected async onTerminate(): Promise<void> {
    // Terminate all managed agents
    for (const agent of this.managedAgents.values()) {
      await agent.terminate();
    }
    
    // Clear all data structures
    this.managedAgents.clear();
    this.taskQueue.clear();
    this.taskAssignments.clear();
    this.decomposedTasks.clear();
    
    // Stop coordination loop
    if (this.coordinationInterval) {
      clearInterval(this.coordinationInterval);
      this.coordinationInterval = null;
    }
  }
  
  // Private helper methods
  
  private startCoordinationLoop(): void {
    this.coordinationInterval = setInterval(async () => {
      try {
        await this.coordinateAgents();
      } catch (error) {
        this.logger.error('Error in coordination loop:', error);
      }
    }, 5000); // Coordinate every 5 seconds
  }
  
  private async deployDefaultWorker(): Promise<Agent> {
    const config: AgentConfig = {
      name: `Worker-${uuidv4().slice(0, 8)}`,
      type: 'worker',
      capabilities: ['processing', 'computation', 'io'],
      maxConcurrentTasks: 3,
      timeout: 30000,
      retryPolicy: {
        maxRetries: 2,
        backoffMultiplier: 2,
        initialDelay: 1000,
        maxDelay: 10000
      }
    };
    
    return await this.deployAgent(config);
  }
  
  private async createSpecialistAgent(config: AgentConfig): Promise<Agent> {
    // Create specialized agent based on capabilities
    return new WorkerAgent(config, this.logger);
  }
  
  private async createCoordinatorAgent(config: AgentConfig): Promise<Agent> {
    // Create coordinator agent for sub-coordination
    return new WorkerAgent(config, this.logger);
  }
  
  private setupAgentEventHandlers(agent: Agent): void {
    agent.on('task:completed', (data) => {
      this.emit('agent:task:completed', data);
    });
    
    agent.on('task:failed', (data) => {
      this.emit('agent:task:failed', data);
    });
    
    agent.on('error', (error) => {
      this.logger.error(`Agent ${agent.id} error:`, error);
      this.handleAgentFailure(agent.id);
    });
  }
  
  private async checkAgentHealth(): Promise<void> {
    for (const agent of this.managedAgents.values()) {
      const metrics = agent.getMetrics();
      
      // Check if agent is responsive
      if (Date.now() - metrics.lastHealthCheck > 60000) {
        this.logger.warn(`Agent ${agent.id} not responsive`);
        await this.handleAgentFailure(agent.id);
      }
      
      // Check performance degradation
      if (metrics.performance.successRate < 50 && metrics.tasksCompleted > 10) {
        this.logger.warn(`Agent ${agent.id} has low success rate: ${metrics.performance.successRate}%`);
      }
    }
  }
  
  private async processTaskQueue(): Promise<void> {
    while (this.taskQueue.size() > 0) {
      const task = this.taskQueue.getNext();
      if (!task) break;
      
      // Try to assign task
      const availableAgents = this.agentRegistry.findAvailable();
      const agent = this.loadBalancer.selectAgent(task, availableAgents);
      
      if (agent) {
        this.taskQueue.remove(task.id);
        await this.assignTask(task, agent.id);
      } else {
        // No available agent, keep in queue
        break;
      }
    }
  }
  
  private async rebalanceIfNeeded(): Promise<void> {
    const agents = Array.from(this.managedAgents.values());
    if (agents.length < 2) return;
    
    // Calculate load variance
    const loads = agents.map(a => this.loadBalancer.getLoad(a));
    const avgLoad = loads.reduce((a, b) => a + b, 0) / loads.length;
    const variance = loads.reduce((sum, load) => sum + Math.pow(load - avgLoad, 2), 0) / loads.length;
    
    // Rebalance if variance is high
    if (variance > 10) {
      await this.rebalanceTasks();
    }
  }
  
  private async autoScale(): Promise<void> {
    const queueSize = this.taskQueue.size();
    const agentCount = this.managedAgents.size;
    
    // Scale up if queue is growing
    if (queueSize > agentCount * 5) {
      this.logger.info('Auto-scaling up: deploying new agent');
      await this.deployDefaultWorker();
    }
    
    // Scale down if agents are idle
    const idleAgents = this.agentRegistry.findByStatus('idle');
    if (idleAgents.length > agentCount / 2 && agentCount > 1) {
      this.logger.info('Auto-scaling down: decommissioning idle agent');
      const agentToRemove = idleAgents[0];
      await this.decommissionAgent(agentToRemove.id);
    }
  }
  
  private async reassignTask(taskId: string, newAgentId?: string): Promise<void> {
    const currentAgentId = this.taskAssignments.get(taskId);
    
    if (currentAgentId) {
      this.taskAssignments.delete(taskId);
    }
    
    const task = this.getTask(taskId);
    if (task) {
      await this.assignTask(task, newAgentId);
    }
  }
  
  private async recoverAgent(agentId: string): Promise<void> {
    const agent = this.managedAgents.get(agentId);
    if (!agent) return;
    
    // Try to reinitialize
    await agent.initialize();
  }
  
  private async replaceAgent(agentId: string): Promise<void> {
    const oldAgent = this.managedAgents.get(agentId);
    if (!oldAgent) return;
    
    // Deploy replacement with similar config
    const newConfig = { ...oldAgent.config, id: undefined };
    const newAgent = await this.deployAgent(newConfig);
    
    // Decommission old agent
    await this.decommissionAgent(agentId);
    
    this.logger.info(`Replaced agent ${agentId} with ${newAgent.id}`);
  }
  
  private async executeSubtasks(decomposition: TaskDecomposition): Promise<any[]> {
    const results: any[] = [];
    
    for (const phase of decomposition.executionPlan.phases) {
      const phaseResults = await Promise.all(
        phase.tasks.map(taskId => {
          const task = decomposition.subtasks.find(t => t.id === taskId);
          if (!task) throw new Error(`Subtask ${taskId} not found`);
          return this.onExecuteTask(task);
        })
      );
      
      results.push(...phaseResults);
    }
    
    return results;
  }
  
  private aggregateResults(results: any[], decomposition: TaskDecomposition): any {
    // Default aggregation - can be customized
    return {
      originalTask: decomposition.originalTask.id,
      subtaskResults: results,
      executionPlan: decomposition.executionPlan,
      summary: `Completed ${results.length} subtasks`
    };
  }
  
  private async waitForTaskCompletion(taskId: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        const task = this.getTask(taskId);
        
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
        }
      }, 1000);
    });
  }
  
  private handleTaskCompletion(taskId: string, result: any): void {
    const task = this.getTask(taskId);
    if (task) {
      task.status = 'completed';
      task.output = result;
      task.completedAt = Date.now();
    }
    
    this.taskAssignments.delete(taskId);
    this.emit('task:completed', { taskId, result });
  }
  
  private handleTaskFailure(taskId: string, error: Error): void {
    const task = this.getTask(taskId);
    if (task) {
      task.status = 'failed';
      task.error = error;
      task.completedAt = Date.now();
    }
    
    this.taskAssignments.delete(taskId);
    this.emit('task:failed', { taskId, error });
  }
  
  private getTask(taskId: string): Task | undefined {
    // Look in queue
    let task = this.taskQueue.get(taskId);
    if (task) return task;
    
    // Look in decomposed tasks
    for (const decomposition of this.decomposedTasks.values()) {
      task = decomposition.subtasks.find(t => t.id === taskId);
      if (task) return task;
    }
    
    return undefined;
  }
}