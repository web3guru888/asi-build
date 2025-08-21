/**
 * Tool Registry - Central management system for tools in ASI-Code
 * 
 * Integrates with the Kenny Integration Pattern to provide a comprehensive
 * tool management system with permission checking, lifecycle management,
 * and event-driven architecture.
 */

import { EventEmitter } from 'eventemitter3';
import { getKennyIntegration } from '../kenny/integration.js';
import { BaseSubsystem } from '../kenny/base-subsystem.js';
import { ResourceType } from '../permission/permission-types.js';
import type { PermissionManager } from '../permission/permission-manager.js';
import type { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from './base-tool.js';

export interface ToolRegistryConfig {
  permissionManager?: PermissionManager;
  enableMetrics?: boolean;
  enableCaching?: boolean;
  maxConcurrentExecutions?: number;
  defaultTimeout?: number;
}

export interface ToolExecutionMetrics {
  toolName: string;
  executionCount: number;
  totalExecutionTime: number;
  averageExecutionTime: number;
  successCount: number;
  errorCount: number;
  lastExecuted: Date;
  lastError?: string;
}

export interface ToolRegistryEntry {
  tool: BaseTool;
  definition: ToolDefinition;
  registeredAt: Date;
  metrics: ToolExecutionMetrics;
  status: 'active' | 'disabled' | 'deprecated';
  tags: string[];
}

export interface ToolExecutionInfo {
  id: string;
  toolName: string;
  parameters: Record<string, any>;
  context: ToolExecutionContext;
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed' | 'timeout';
  result?: ToolResult;
  error?: string;
}

/**
 * Central registry and manager for all tools in the ASI-Code system
 * Integrates with Kenny Integration Pattern as a subsystem
 */
export class ToolRegistry extends BaseSubsystem {
  private tools = new Map<string, ToolRegistryEntry>();
  private executions = new Map<string, ToolExecutionInfo>();
  private executionQueue: Array<() => Promise<void>> = [];
  private runningExecutions = new Set<string>();
  
  private permissionManager?: PermissionManager;
  public config: Required<Omit<ToolRegistryConfig, 'permissionManager'>> & { permissionManager?: PermissionManager };
  private executionId = 0;

  constructor(config: ToolRegistryConfig = {}) {
    super({
      id: 'tool-registry',
      name: 'Tool Registry',
      description: 'Central management system for tools',
      version: '1.0.0'
    }, []);

    this.config = {
      permissionManager: config.permissionManager,
      enableMetrics: config.enableMetrics ?? true,
      enableCaching: config.enableCaching ?? true,
      maxConcurrentExecutions: config.maxConcurrentExecutions ?? 10,
      defaultTimeout: config.defaultTimeout ?? 300000 // 5 minutes
    };
  }

  async initialize(config: Record<string, any> = {}): Promise<void> {
    try {
      // Get permission manager if not provided
      if (!this.permissionManager && config.permissionManager) {
        this.permissionManager = config.permissionManager || undefined;
      }

      this.status = 'running';
      this.emit('initialized', { config: this.config });
    } catch (error) {
      this.status = 'error';
      throw error;
    }
  }

  async start(): Promise<void> {
    this.status = 'running';
    this.emit('started');
  }

  async stop(): Promise<void> {
    // Wait for all running executions to complete or timeout
    const timeoutPromise = new Promise<void>(resolve => 
      setTimeout(resolve, 30000) // 30 second graceful shutdown timeout
    );
    
    const executionsPromise = Promise.all(
      Array.from(this.runningExecutions).map(id => {
        const execution = this.executions.get(id);
        if (execution?.status === 'running') {
          return this.waitForExecution(id);
        }
        return Promise.resolve();
      })
    );

    await Promise.race([executionsPromise, timeoutPromise]);
    
    this.status = 'stopped';
    this.emit('stopped');
  }

  async shutdown(): Promise<void> {
    await this.stop();
    
    // Clean up all tools
    for (const entry of this.tools.values()) {
      try {
        await entry.tool.cleanup();
      } catch (error) {
        console.error(`Error cleaning up tool ${entry.definition.name}:`, error);
      }
    }

    this.tools.clear();
    this.executions.clear();
    this.executionQueue.length = 0;
    this.runningExecutions.clear();
    
    this.status = 'stopped';
    this.emit('shutdown');
  }

  /**
   * Register a tool with the registry
   */
  async register(tool: BaseTool, tags: string[] = []): Promise<void> {
    const toolName = tool.definition.name;
    
    if (this.tools.has(toolName)) {
      throw new Error(`Tool ${toolName} is already registered`);
    }

    const entry: ToolRegistryEntry = {
      tool,
      definition: tool.definition,
      registeredAt: new Date(),
      metrics: {
        toolName,
        executionCount: 0,
        totalExecutionTime: 0,
        averageExecutionTime: 0,
        successCount: 0,
        errorCount: 0,
        lastExecuted: new Date(),
      },
      status: 'active',
      tags
    };

    this.tools.set(toolName, entry);

    // Setup tool event forwarding
    this.setupToolEventForwarding(tool);

    // Emit registration event to Kenny Integration
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'tool.registered',
      this.metadata.id,
      {
        toolName,
        definition: tool.definition,
        tags
      }
    );

    this.emit('tool.registered', { tool: entry });
  }

  /**
   * Unregister a tool from the registry
   */
  async unregister(toolName: string): Promise<void> {
    const entry = this.tools.get(toolName);
    if (!entry) {
      return;
    }

    // Cancel any running executions for this tool
    for (const [id, execution] of this.executions.entries()) {
      if (execution.toolName === toolName && execution.status === 'running') {
        execution.status = 'failed';
        execution.error = 'Tool unregistered';
        execution.endTime = new Date();
        this.runningExecutions.delete(id);
      }
    }

    // Cleanup tool
    try {
      await entry.tool.cleanup();
    } catch (error) {
      console.error(`Error cleaning up tool ${toolName}:`, error);
    }

    this.tools.delete(toolName);

    // Emit unregistration event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'tool.unregistered',
      this.metadata.id,
      { toolName }
    );

    this.emit('tool.unregistered', { toolName });
  }

  /**
   * Get a tool by name
   */
  get(toolName: string): BaseTool | null {
    const entry = this.tools.get(toolName);
    return entry?.status === 'active' ? entry.tool : null;
  }

  /**
   * List all registered tools
   */
  list(filters?: {
    category?: string;
    tags?: string[];
    status?: 'active' | 'disabled' | 'deprecated';
  }): ToolDefinition[] {
    const entries = Array.from(this.tools.values());
    
    let filteredEntries = entries;
    
    if (filters?.category) {
      filteredEntries = filteredEntries.filter(entry => 
        entry.definition.category === filters.category
      );
    }
    
    if (filters?.tags?.length) {
      filteredEntries = filteredEntries.filter(entry =>
        filters.tags!.some(tag => entry.tags.includes(tag))
      );
    }
    
    if (filters?.status) {
      filteredEntries = filteredEntries.filter(entry =>
        entry.status === filters.status
      );
    }
    
    return filteredEntries.map(entry => entry.definition);
  }

  /**
   * Execute a tool with permission checking and monitoring
   */
  async execute(
    toolName: string, 
    parameters: Record<string, any>, 
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    const entry = this.tools.get(toolName);
    if (!entry || entry.status !== 'active') {
      return {
        success: false,
        error: `Tool ${toolName} not found or not active`
      };
    }

    // Check permissions if permission manager is available
    if (this.permissionManager && context.userId) {
      const permissionResult = await this.permissionManager.checkPermission({
        context: {
          userId: context.userId,
          sessionId: context.sessionId,
          resource: `tool.${toolName}`,
          operation: 'execute',
          resourceType: ResourceType.TOOL,
          timestamp: new Date(),
          metadata: {
            toolName,
            category: entry.definition.category
          }
        },
        permissionId: 'tool_execution'
      });
      const hasPermission = permissionResult.granted;

      if (!hasPermission) {
        return {
          success: false,
          error: `Permission denied for tool ${toolName}`
        };
      }
    }

    // Validate parameters
    if (!entry.tool.validate(parameters)) {
      return {
        success: false,
        error: `Invalid parameters for tool ${toolName}`
      };
    }

    // Check execution limits
    if (this.runningExecutions.size >= this.config.maxConcurrentExecutions) {
      return {
        success: false,
        error: 'Maximum concurrent executions reached'
      };
    }

    // Create execution info
    const executionId = `exec_${++this.executionId}_${Date.now()}`;
    const executionInfo: ToolExecutionInfo = {
      id: executionId,
      toolName,
      parameters,
      context,
      startTime: new Date(),
      status: 'running'
    };

    this.executions.set(executionId, executionInfo);
    this.runningExecutions.add(executionId);

    try {
      // Emit execution start event
      const kenny = getKennyIntegration();
      await kenny.getMessageBus().publishSubsystem(
        'tool.execution.start',
        this.metadata.id,
        { executionId, toolName, parameters: Object.keys(parameters) }
      );

      this.emit('execution.start', { executionId, toolName, parameters });

      // Execute the tool with timeout
      const timeoutPromise = new Promise<ToolResult>((_, reject) => 
        setTimeout(() => reject(new Error('Execution timeout')), this.config.defaultTimeout)
      );

      const executionPromise = entry.tool.execute(parameters, context);
      const result = await Promise.race([executionPromise, timeoutPromise]);

      // Update execution info
      executionInfo.status = 'completed';
      executionInfo.endTime = new Date();
      executionInfo.result = result;

      // Update metrics
      if (this.config.enableMetrics) {
        this.updateMetrics(entry, executionInfo, result.success);
      }

      // Emit completion event
      await kenny.getMessageBus().publishSubsystem(
        'tool.execution.complete',
        this.metadata.id,
        { 
          executionId, 
          toolName, 
          success: result.success,
          executionTime: executionInfo.endTime.getTime() - executionInfo.startTime.getTime()
        }
      );

      this.emit('execution.complete', { executionId, toolName, result });

      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Update execution info
      executionInfo.status = error.message === 'Execution timeout' ? 'timeout' : 'failed';
      executionInfo.endTime = new Date();
      executionInfo.error = errorMessage;

      // Update metrics
      if (this.config.enableMetrics) {
        this.updateMetrics(entry, executionInfo, false);
      }

      // Emit error event
      const kenny = getKennyIntegration();
      await kenny.getMessageBus().publishSubsystem(
        'tool.execution.error',
        this.metadata.id,
        { executionId, toolName, error: errorMessage }
      );

      this.emit('execution.error', { executionId, toolName, error: errorMessage });

      return {
        success: false,
        error: errorMessage
      };

    } finally {
      this.runningExecutions.delete(executionId);
    }
  }

  /**
   * Get tool execution metrics
   */
  getMetrics(toolName?: string): ToolExecutionMetrics | ToolExecutionMetrics[] {
    if (toolName) {
      const entry = this.tools.get(toolName);
      return entry ? entry.metrics : null as any;
    }
    
    return Array.from(this.tools.values()).map(entry => entry.metrics);
  }

  /**
   * Get running executions
   */
  getRunningExecutions(): ToolExecutionInfo[] {
    return Array.from(this.runningExecutions)
      .map(id => this.executions.get(id))
      .filter((exec): exec is ToolExecutionInfo => exec !== undefined);
  }

  /**
   * Cancel a running execution
   */
  async cancelExecution(executionId: string): Promise<boolean> {
    const execution = this.executions.get(executionId);
    if (!execution || execution.status !== 'running') {
      return false;
    }

    execution.status = 'failed';
    execution.error = 'Execution cancelled';
    execution.endTime = new Date();
    this.runningExecutions.delete(executionId);

    // Emit cancellation event
    const kenny = getKennyIntegration();
    await kenny.getMessageBus().publishSubsystem(
      'tool.execution.cancelled',
      this.metadata.id,
      { executionId, toolName: execution.toolName }
    );

    this.emit('execution.cancelled', { executionId });
    return true;
  }

  /**
   * Health check for the tool registry
   */
  async healthCheck() {
    const healthyTools = Array.from(this.tools.values())
      .filter(entry => entry.status === 'active').length;
    
    const runningExecutions = this.runningExecutions.size;
    
    return {
      status: (this.status === 'running' ? 'healthy' : 'unhealthy') as 'healthy' | 'unhealthy' | 'degraded',
      message: `${healthyTools} active tools, ${runningExecutions} running executions`,
      timestamp: new Date(),
      details: {
        totalTools: this.tools.size,
        activeTools: healthyTools,
        runningExecutions,
        queuedExecutions: this.executionQueue.length
      }
    };
  }

  private setupToolEventForwarding(tool: BaseTool): void {
    const events = ['executed', 'error'];
    
    events.forEach(eventName => {
      tool.on(eventName, (data) => {
        this.emit(`tool.${eventName}`, {
          toolName: tool.definition.name,
          data
        });
      });
    });
  }

  private updateMetrics(entry: ToolRegistryEntry, execution: ToolExecutionInfo, success: boolean): void {
    const metrics = entry.metrics;
    const executionTime = execution.endTime
      ? execution.endTime.getTime() - execution.startTime.getTime()
      : 0;

    metrics.executionCount++;
    metrics.totalExecutionTime += executionTime;
    metrics.averageExecutionTime = metrics.totalExecutionTime / metrics.executionCount;
    metrics.lastExecuted = execution.startTime;

    if (success) {
      metrics.successCount++;
    } else {
      metrics.errorCount++;
      if (execution.error) {
        metrics.lastError = execution.error;
      }
    }
  }

  private async waitForExecution(executionId: string): Promise<void> {
    return new Promise<void>((resolve) => {
      const checkStatus = () => {
        const execution = this.executions.get(executionId);
        if (!execution || execution.status !== 'running') {
          resolve();
        } else {
          setTimeout(checkStatus, 100);
        }
      };
      checkStatus();
    });
  }

  // Implement required BaseSubsystem abstract methods
  protected async onInitialize(config: any): Promise<void> {
    this.config = { ...this.config, ...config };
    // Tool registry is initialized in constructor
  }

  protected async onStart(): Promise<void> {
    // Tool registry is always ready to accept registrations and executions
    // No additional startup needed
  }

  protected async onStop(): Promise<void> {
    // Cancel all running executions
    for (const executionId of this.runningExecutions) {
      await this.cancelExecution(executionId);
    }
  }
}

/**
 * Factory function to create a tool registry instance
 */
export function createToolRegistry(config?: ToolRegistryConfig): ToolRegistry {
  return new ToolRegistry(config);
}