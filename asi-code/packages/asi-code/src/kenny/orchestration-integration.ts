/**
 * Kenny Integration with Agent Orchestration System
 * 
 * Connects the Kenny Integration Pattern with the Agent Orchestration System
 * to enable intelligent task decomposition and parallel agent execution.
 */

import { KennyIntegration } from './integration.js';
import { BaseSubsystem } from './base-subsystem.js';
import { createOrchestrationSystem, Orchestrator, Task, TaskPriority } from '../orchestration/index.js';
import { Logger } from '../logging/index.js';
import { EventEmitter } from 'eventemitter3';

/**
 * Orchestration Subsystem for Kenny Integration
 */
export class OrchestrationSubsystem extends BaseSubsystem {
  private orchestrator: Orchestrator | null = null;
  private taskMapping: Map<string, string> = new Map(); // internal task ID -> orchestrator task ID
  
  constructor(kenny: KennyIntegration, logger?: Logger) {
    super('orchestration', kenny, logger);
  }
  
  async initialize(): Promise<void> {
    this.logger.info('Initializing Orchestration Subsystem');
    
    // Create orchestration system
    this.orchestrator = await createOrchestrationSystem({
      supervisors: 2,
      workersPerSupervisor: 3,
      logger: this.logger
    });
    
    // Setup event handlers
    this.setupOrchestrationEvents();
    
    this.initialized = true;
    this.emit('subsystem:initialized', { name: this.name });
  }
  
  /**
   * Submit a task for orchestrated execution
   */
  async submitTask(description: string, options?: {
    type?: string;
    priority?: TaskPriority;
    decompose?: boolean;
    capabilities?: string[];
    metadata?: Record<string, any>;
  }): Promise<string> {
    if (!this.orchestrator) {
      throw new Error('Orchestration system not initialized');
    }
    
    const task: Task = {
      id: '',
      type: options?.type || 'general',
      description,
      priority: options?.priority || 'medium',
      status: 'pending',
      createdAt: Date.now(),
      constraints: options?.capabilities ? {
        requiredCapabilities: options.capabilities
      } : undefined,
      metadata: {
        ...options?.metadata,
        decompose: options?.decompose,
        source: 'kenny-integration'
      }
    };
    
    const taskId = await this.orchestrator.submitTask(task);
    
    // Store mapping for tracking
    const internalId = `kenny-${Date.now()}`;
    this.taskMapping.set(internalId, taskId);
    
    this.logger.info(`Submitted orchestrated task ${taskId}: ${description}`);
    
    return internalId;
  }
  
  /**
   * Get task result
   */
  async getTaskResult(internalId: string): Promise<any> {
    const orchestratorTaskId = this.taskMapping.get(internalId);
    
    if (!orchestratorTaskId) {
      throw new Error(`Task ${internalId} not found`);
    }
    
    if (!this.orchestrator) {
      throw new Error('Orchestration system not initialized');
    }
    
    return await this.orchestrator.getTaskResult(orchestratorTaskId);
  }
  
  /**
   * Submit complex workflow for decomposition and execution
   */
  async executeWorkflow(workflow: {
    name: string;
    steps: Array<{
      description: string;
      type?: string;
      dependencies?: string[];
    }>;
    parallel?: boolean;
  }): Promise<any> {
    this.logger.info(`Executing workflow: ${workflow.name}`);
    
    const results: any[] = [];
    const stepTasks = new Map<string, string>();
    
    for (const step of workflow.steps) {
      // Wait for dependencies
      if (step.dependencies) {
        for (const dep of step.dependencies) {
          const depTaskId = stepTasks.get(dep);
          if (depTaskId) {
            await this.getTaskResult(depTaskId);
          }
        }
      }
      
      // Submit step as task
      const taskId = await this.submitTask(step.description, {
        type: step.type,
        decompose: true,
        metadata: {
          workflow: workflow.name,
          step: step.description
        }
      });
      
      stepTasks.set(step.description, taskId);
      
      if (!workflow.parallel) {
        // Wait for step to complete before continuing
        const result = await this.getTaskResult(taskId);
        results.push(result);
      }
    }
    
    // If parallel, wait for all tasks
    if (workflow.parallel) {
      for (const taskId of stepTasks.values()) {
        const result = await this.getTaskResult(taskId);
        results.push(result);
      }
    }
    
    return {
      workflow: workflow.name,
      results,
      summary: `Completed ${results.length} steps`
    };
  }
  
  /**
   * Scale agents based on load
   */
  async scaleAgents(factor: number): Promise<void> {
    if (!this.orchestrator) {
      throw new Error('Orchestration system not initialized');
    }
    
    const status = this.orchestrator.getSystemStatus();
    const targetCount = Math.ceil(status.agentCount * factor);
    
    await this.orchestrator.scaleAgents(targetCount, 'worker');
    
    this.logger.info(`Scaled agents from ${status.agentCount} to ${targetCount}`);
  }
  
  /**
   * Get orchestration system status
   */
  getSystemStatus(): any {
    if (!this.orchestrator) {
      return { error: 'Orchestration system not initialized' };
    }
    
    return this.orchestrator.getSystemStatus();
  }
  
  /**
   * Get orchestration metrics
   */
  getMetrics(): any {
    if (!this.orchestrator) {
      return { error: 'Orchestration system not initialized' };
    }
    
    return this.orchestrator.getMetrics();
  }
  
  private setupOrchestrationEvents(): void {
    if (!this.orchestrator) return;
    
    this.orchestrator.on('task:completed', (data) => {
      this.emit('orchestration:task:completed', data);
      this.kenny.emit('orchestration:task:completed', data);
    });
    
    this.orchestrator.on('task:failed', (data) => {
      this.emit('orchestration:task:failed', data);
      this.kenny.emit('orchestration:task:failed', data);
    });
    
    this.orchestrator.on('agent:deployed', (agent) => {
      this.emit('orchestration:agent:deployed', agent);
      this.kenny.emit('orchestration:agent:deployed', {
        id: agent.id,
        type: agent.config.type,
        capabilities: agent.config.capabilities
      });
    });
    
    this.orchestrator.on('system:overloaded', (load) => {
      this.logger.warn(`Orchestration system overloaded: ${load}%`);
      this.emit('orchestration:overload', load);
      
      // Auto-scale
      this.scaleAgents(1.5).catch(error => {
        this.logger.error('Failed to auto-scale on overload:', error);
      });
    });
  }
  
  async shutdown(): Promise<void> {
    if (this.orchestrator) {
      await this.orchestrator.shutdown();
    }
    
    this.taskMapping.clear();
    await super.shutdown();
  }
}

/**
 * Kenny Agent Orchestration Interface
 * 
 * High-level interface for using agent orchestration through Kenny
 */
export class KennyOrchestration {
  private kenny: KennyIntegration;
  private orchestrationSubsystem: OrchestrationSubsystem;
  private logger: Logger;
  
  constructor(kenny: KennyIntegration) {
    this.kenny = kenny;
    this.logger = new Logger({ component: 'KennyOrchestration' });
    
    // Create and register orchestration subsystem
    this.orchestrationSubsystem = new OrchestrationSubsystem(kenny, this.logger);
    kenny.registerSubsystem(this.orchestrationSubsystem);
  }
  
  /**
   * Initialize orchestration
   */
  async initialize(): Promise<void> {
    await this.orchestrationSubsystem.initialize();
  }
  
  /**
   * Execute a complex task with automatic decomposition
   */
  async executeComplexTask(description: string, options?: {
    priority?: TaskPriority;
    timeout?: number;
  }): Promise<any> {
    this.logger.info(`Executing complex task: ${description}`);
    
    const taskId = await this.orchestrationSubsystem.submitTask(description, {
      decompose: true,
      priority: options?.priority || 'medium',
      metadata: {
        timeout: options?.timeout
      }
    });
    
    return await this.orchestrationSubsystem.getTaskResult(taskId);
  }
  
  /**
   * Execute multiple tasks in parallel
   */
  async executeParallelTasks(tasks: Array<{
    description: string;
    type?: string;
  }>): Promise<any[]> {
    this.logger.info(`Executing ${tasks.length} tasks in parallel`);
    
    const taskIds = await Promise.all(
      tasks.map(task => 
        this.orchestrationSubsystem.submitTask(task.description, {
          type: task.type
        })
      )
    );
    
    const results = await Promise.all(
      taskIds.map(id => this.orchestrationSubsystem.getTaskResult(id))
    );
    
    return results;
  }
  
  /**
   * Execute a workflow with dependencies
   */
  async executeWorkflow(workflow: {
    name: string;
    steps: Array<{
      id: string;
      description: string;
      dependencies?: string[];
    }>;
  }): Promise<any> {
    this.logger.info(`Executing workflow: ${workflow.name}`);
    
    const stepResults = new Map<string, any>();
    const stepTasks = new Map<string, string>();
    
    // Process steps in dependency order
    const processed = new Set<string>();
    
    while (processed.size < workflow.steps.length) {
      // Find steps ready to execute
      const readySteps = workflow.steps.filter(step => {
        if (processed.has(step.id)) return false;
        
        if (!step.dependencies) return true;
        
        return step.dependencies.every(dep => processed.has(dep));
      });
      
      if (readySteps.length === 0) {
        throw new Error('Circular dependency detected in workflow');
      }
      
      // Execute ready steps in parallel
      const taskPromises = readySteps.map(async step => {
        const taskId = await this.orchestrationSubsystem.submitTask(step.description, {
          metadata: {
            workflow: workflow.name,
            stepId: step.id
          }
        });
        
        stepTasks.set(step.id, taskId);
        return { stepId: step.id, taskId };
      });
      
      const taskInfos = await Promise.all(taskPromises);
      
      // Wait for results
      const resultPromises = taskInfos.map(async ({ stepId, taskId }) => {
        const result = await this.orchestrationSubsystem.getTaskResult(taskId);
        stepResults.set(stepId, result);
        processed.add(stepId);
      });
      
      await Promise.all(resultPromises);
    }
    
    return {
      workflow: workflow.name,
      steps: Object.fromEntries(stepResults),
      summary: `Completed ${workflow.steps.length} steps`
    };
  }
  
  /**
   * Get orchestration status
   */
  getStatus(): any {
    return {
      system: this.orchestrationSubsystem.getSystemStatus(),
      metrics: this.orchestrationSubsystem.getMetrics()
    };
  }
  
  /**
   * Scale the agent pool
   */
  async scale(factor: number): Promise<void> {
    await this.orchestrationSubsystem.scaleAgents(factor);
  }
}

/**
 * Create Kenny with Orchestration
 */
export async function createKennyWithOrchestration(): Promise<{
  kenny: KennyIntegration;
  orchestration: KennyOrchestration;
}> {
  const kenny = KennyIntegration.getInstance();
  const orchestration = new KennyOrchestration(kenny);
  
  await orchestration.initialize();
  
  return { kenny, orchestration };
}