/**
 * Base Agent Implementation
 * 
 * Core agent class that all agent types extend from.
 * Provides fundamental agent capabilities and lifecycle management.
 */

import { EventEmitter } from 'eventemitter3';
import { 
  Agent,
  AgentConfig,
  AgentStatus,
  AgentPerformance,
  AgentMetrics,
  Task,
  ResourceUtilization
} from './types.js';
import { v4 as uuidv4 } from 'uuid';
import { Logger } from '../logging/index.js';

export abstract class BaseAgent extends EventEmitter implements Agent {
  public readonly id: string;
  public config: AgentConfig;
  public status: AgentStatus;
  public currentTasks: Set<string>;
  public completedTasks: number;
  public failedTasks: number;
  public performance: AgentPerformance;
  
  protected logger: Logger;
  protected startTime: number;
  protected lastHealthCheck: number;
  protected taskHistory: Map<string, TaskExecution>;
  protected resourceMonitor: NodeJS.Timer | null = null;
  
  constructor(config: AgentConfig, logger?: Logger) {
    super();
    
    this.id = config.id || `agent-${uuidv4()}`;
    this.config = config;
    this.status = 'idle';
    this.currentTasks = new Set();
    this.completedTasks = 0;
    this.failedTasks = 0;
    this.taskHistory = new Map();
    
    this.logger = logger || new Logger({
      component: `Agent-${this.id}`,
      level: 'info'
    });
    
    this.startTime = Date.now();
    this.lastHealthCheck = Date.now();
    
    this.performance = {
      averageTaskDuration: 0,
      successRate: 100,
      taskThroughput: 0,
      resourceUtilization: {
        cpu: 0,
        memory: 0,
        activeConnections: 0
      }
    };
    
    this.setupEventHandlers();
  }
  
  /**
   * Initialize the agent
   */
  async initialize(): Promise<void> {
    this.logger.info(`Initializing agent ${this.id} of type ${this.config.type}`);
    
    try {
      // Start resource monitoring
      this.startResourceMonitoring();
      
      // Perform agent-specific initialization
      await this.onInitialize();
      
      this.status = 'idle';
      this.emit('initialized', this);
      
      this.logger.info(`Agent ${this.id} initialized successfully`);
    } catch (error) {
      this.logger.error(`Failed to initialize agent ${this.id}:`, error);
      this.status = 'error';
      throw error;
    }
  }
  
  /**
   * Execute a task
   */
  async executeTask(task: Task): Promise<any> {
    if (!this.canHandle(task)) {
      throw new Error(`Agent ${this.id} cannot handle task ${task.id}`);
    }
    
    if (this.currentTasks.size >= this.config.maxConcurrentTasks) {
      throw new Error(`Agent ${this.id} at maximum concurrent task capacity`);
    }
    
    this.logger.info(`Agent ${this.id} executing task ${task.id}`);
    
    const execution: TaskExecution = {
      taskId: task.id,
      startTime: Date.now(),
      status: 'running'
    };
    
    this.currentTasks.add(task.id);
    this.taskHistory.set(task.id, execution);
    this.status = 'working';
    
    this.emit('task:started', { agentId: this.id, taskId: task.id });
    
    try {
      // Apply retry policy if configured
      const result = await this.executeWithRetry(task);
      
      execution.endTime = Date.now();
      execution.status = 'completed';
      execution.result = result;
      
      this.completedTasks++;
      this.currentTasks.delete(task.id);
      
      if (this.currentTasks.size === 0) {
        this.status = 'idle';
      }
      
      this.updatePerformanceMetrics();
      
      this.emit('task:completed', { 
        agentId: this.id, 
        taskId: task.id, 
        result,
        duration: execution.endTime - execution.startTime
      });
      
      this.logger.info(`Agent ${this.id} completed task ${task.id}`);
      
      return result;
      
    } catch (error) {
      execution.endTime = Date.now();
      execution.status = 'failed';
      execution.error = error as Error;
      
      this.failedTasks++;
      this.currentTasks.delete(task.id);
      
      if (this.currentTasks.size === 0) {
        this.status = 'idle';
      }
      
      this.updatePerformanceMetrics();
      
      this.emit('task:failed', { 
        agentId: this.id, 
        taskId: task.id, 
        error,
        duration: execution.endTime - execution.startTime
      });
      
      this.logger.error(`Agent ${this.id} failed task ${task.id}:`, error);
      
      throw error;
    }
  }
  
  /**
   * Execute task with retry policy
   */
  private async executeWithRetry(task: Task): Promise<any> {
    const retryPolicy = this.config.retryPolicy || {
      maxRetries: 0,
      backoffMultiplier: 2,
      initialDelay: 1000,
      maxDelay: 30000
    };
    
    let lastError: Error | null = null;
    let delay = retryPolicy.initialDelay;
    
    for (let attempt = 0; attempt <= retryPolicy.maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          this.logger.info(`Retrying task ${task.id} (attempt ${attempt + 1})`);
          await this.sleep(delay);
        }
        
        return await this.onExecuteTask(task);
        
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < retryPolicy.maxRetries) {
          delay = Math.min(delay * retryPolicy.backoffMultiplier, retryPolicy.maxDelay);
        }
      }
    }
    
    throw lastError;
  }
  
  /**
   * Suspend the agent
   */
  async suspend(): Promise<void> {
    if (this.status === 'suspended' || this.status === 'terminated') {
      return;
    }
    
    this.logger.info(`Suspending agent ${this.id}`);
    
    const previousStatus = this.status;
    this.status = 'suspended';
    
    // Wait for current tasks to complete or timeout
    if (this.currentTasks.size > 0) {
      await this.waitForTaskCompletion(30000); // 30 second timeout
    }
    
    await this.onSuspend();
    
    this.emit('suspended', { agentId: this.id, previousStatus });
    
    this.logger.info(`Agent ${this.id} suspended`);
  }
  
  /**
   * Resume the agent
   */
  async resume(): Promise<void> {
    if (this.status !== 'suspended') {
      return;
    }
    
    this.logger.info(`Resuming agent ${this.id}`);
    
    await this.onResume();
    
    this.status = this.currentTasks.size > 0 ? 'working' : 'idle';
    
    this.emit('resumed', { agentId: this.id });
    
    this.logger.info(`Agent ${this.id} resumed`);
  }
  
  /**
   * Terminate the agent
   */
  async terminate(): Promise<void> {
    if (this.status === 'terminated') {
      return;
    }
    
    this.logger.info(`Terminating agent ${this.id}`);
    
    this.status = 'terminated';
    
    // Stop resource monitoring
    if (this.resourceMonitor) {
      clearInterval(this.resourceMonitor);
      this.resourceMonitor = null;
    }
    
    // Cancel current tasks
    for (const taskId of this.currentTasks) {
      this.emit('task:cancelled', { agentId: this.id, taskId });
    }
    this.currentTasks.clear();
    
    await this.onTerminate();
    
    this.emit('terminated', { agentId: this.id });
    
    this.logger.info(`Agent ${this.id} terminated`);
  }
  
  /**
   * Get agent capabilities
   */
  getCapabilities(): string[] {
    return this.config.capabilities;
  }
  
  /**
   * Check if agent can handle a task
   */
  canHandle(task: Task): boolean {
    // Check if agent is available
    if (this.status === 'terminated' || this.status === 'error') {
      return false;
    }
    
    // Check if agent has capacity
    if (this.currentTasks.size >= this.config.maxConcurrentTasks) {
      return false;
    }
    
    // Check required capabilities
    if (task.constraints?.requiredCapabilities) {
      const hasAllCapabilities = task.constraints.requiredCapabilities.every(cap =>
        this.config.capabilities.includes(cap)
      );
      
      if (!hasAllCapabilities) {
        return false;
      }
    }
    
    // Check resource requirements
    if (task.constraints?.requiredResources) {
      if (!this.hasRequiredResources(task.constraints.requiredResources)) {
        return false;
      }
    }
    
    // Agent-specific checks
    return this.onCanHandle(task);
  }
  
  /**
   * Get current status
   */
  getStatus(): AgentStatus {
    return this.status;
  }
  
  /**
   * Get agent metrics
   */
  getMetrics(): AgentMetrics {
    const uptime = Date.now() - this.startTime;
    
    return {
      tasksCompleted: this.completedTasks,
      tasksFailed: this.failedTasks,
      tasksInProgress: this.currentTasks.size,
      uptime,
      lastHealthCheck: this.lastHealthCheck,
      performance: { ...this.performance }
    };
  }
  
  /**
   * Update performance metrics
   */
  protected updatePerformanceMetrics(): void {
    const totalTasks = this.completedTasks + this.failedTasks;
    
    if (totalTasks === 0) return;
    
    // Calculate success rate
    this.performance.successRate = (this.completedTasks / totalTasks) * 100;
    
    // Calculate average task duration
    let totalDuration = 0;
    let taskCount = 0;
    
    for (const execution of this.taskHistory.values()) {
      if (execution.endTime) {
        totalDuration += execution.endTime - execution.startTime;
        taskCount++;
      }
    }
    
    if (taskCount > 0) {
      this.performance.averageTaskDuration = totalDuration / taskCount;
    }
    
    // Calculate throughput
    const uptime = (Date.now() - this.startTime) / 1000; // in seconds
    this.performance.taskThroughput = totalTasks / uptime;
    
    this.performance.lastTaskCompletedAt = Date.now();
  }
  
  /**
   * Start resource monitoring
   */
  protected startResourceMonitoring(): void {
    this.resourceMonitor = setInterval(() => {
      this.updateResourceUtilization();
    }, 5000); // Update every 5 seconds
  }
  
  /**
   * Update resource utilization
   */
  protected updateResourceUtilization(): void {
    // In a real implementation, this would use system metrics
    const memoryUsage = process.memoryUsage();
    const totalMemory = require('os').totalmem();
    
    this.performance.resourceUtilization = {
      cpu: Math.random() * 100, // Placeholder - would use real CPU metrics
      memory: (memoryUsage.heapUsed / totalMemory) * 100,
      activeConnections: this.currentTasks.size
    };
  }
  
  /**
   * Check if agent has required resources
   */
  protected hasRequiredResources(required: any): boolean {
    const available = this.config.resources || {};
    
    if (required.cpu && (!available.cpu || available.cpu < required.cpu)) {
      return false;
    }
    
    if (required.memory && (!available.memory || available.memory < required.memory)) {
      return false;
    }
    
    if (required.gpu && !available.gpu) {
      return false;
    }
    
    return true;
  }
  
  /**
   * Wait for task completion
   */
  protected async waitForTaskCompletion(timeout: number): Promise<void> {
    const startTime = Date.now();
    
    while (this.currentTasks.size > 0) {
      if (Date.now() - startTime > timeout) {
        this.logger.warn(`Timeout waiting for task completion in agent ${this.id}`);
        break;
      }
      
      await this.sleep(100);
    }
  }
  
  /**
   * Setup event handlers
   */
  protected setupEventHandlers(): void {
    // Handle uncaught errors
    this.on('error', (error) => {
      this.logger.error(`Agent ${this.id} error:`, error);
      this.status = 'error';
    });
  }
  
  /**
   * Sleep utility
   */
  protected sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // Abstract methods for subclasses to implement
  protected abstract onInitialize(): Promise<void>;
  protected abstract onExecuteTask(task: Task): Promise<any>;
  protected abstract onCanHandle(task: Task): boolean;
  protected abstract onSuspend(): Promise<void>;
  protected abstract onResume(): Promise<void>;
  protected abstract onTerminate(): Promise<void>;
}

/**
 * Task execution tracking
 */
interface TaskExecution {
  taskId: string;
  startTime: number;
  endTime?: number;
  status: 'running' | 'completed' | 'failed';
  result?: any;
  error?: Error;
}