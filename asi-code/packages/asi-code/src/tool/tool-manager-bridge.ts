/**
 * Tool Manager Bridge - Compatibility layer between legacy ToolManager and new ToolRegistry
 * 
 * Provides backward compatibility while enabling new features from the ToolRegistry system.
 * Bridges the gap between the existing server architecture and the new tool system.
 */

import { ToolRegistry } from './tool-registry.js';
import { ToolInitializer, ToolInitializerConfig, initializeToolSystem } from './tool-initializer.js';
import { BaseTool, ToolDefinition, ToolExecutionContext, ToolResult } from './base-tool.js';
import { EventEmitter } from 'eventemitter3';
import type { PermissionManager } from '../permission/permission-manager.js';

export interface EnhancedToolManagerConfig {
  permissionManager?: PermissionManager;
  enableMetrics?: boolean;
  enableCaching?: boolean;
  maxConcurrentExecutions?: number;
  defaultTimeout?: number;
  autoRegisterBuiltIns?: boolean;
  enableToolValidation?: boolean;
  enableVersioning?: boolean;
}

/**
 * Enhanced Tool Manager that bridges legacy ToolManager interface with new ToolRegistry
 * Maintains backward compatibility while providing new capabilities
 */
export class EnhancedToolManager extends EventEmitter {
  private toolRegistry: ToolRegistry;
  private toolInitializer: ToolInitializer;
  private initialized = false;

  constructor(config: EnhancedToolManagerConfig = {}) {
    super();

    // Create tool initializer with configuration
    const initializerConfig: ToolInitializerConfig = {
      permissionManager: config.permissionManager,
      enableMetrics: config.enableMetrics ?? true,
      enableCaching: config.enableCaching ?? true,
      maxConcurrentExecutions: config.maxConcurrentExecutions ?? 10,
      defaultTimeout: config.defaultTimeout ?? 300000,
      autoRegisterBuiltIns: config.autoRegisterBuiltIns ?? true,
      enableToolValidation: config.enableToolValidation ?? true,
      enableVersioning: config.enableVersioning ?? true
    };

    this.toolInitializer = new ToolInitializer(initializerConfig);
    this.toolRegistry = this.toolInitializer.getRegistry();

    // Forward events from registry
    this.setupEventForwarding();
  }

  /**
   * Initialize the tool system
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      const result = await this.toolInitializer.initialize();
      
      console.log(`[EnhancedToolManager] Initialized with ${result.toolsRegistered} tools`);
      console.log(`[EnhancedToolManager] Categories: ${Object.keys(result.categoryCounts).join(', ')}`);

      if (result.errors.length > 0) {
        console.warn(`[EnhancedToolManager] ${result.errors.length} tool registration errors:`, 
          result.errors.map(e => `${e.toolName}: ${e.error}`));
      }

      this.initialized = true;
      this.emit('initialized', { result });

    } catch (error) {
      console.error('[EnhancedToolManager] Initialization failed:', error);
      throw error;
    }
  }

  // ========================================
  // Legacy ToolManager Interface (Backward Compatibility)
  // ========================================

  /**
   * Register a tool (legacy interface)
   */
  register(tool: BaseTool): void {
    this.toolRegistry.register(tool, []);
    this.emit('tool:registered', { name: tool.definition.name, category: tool.definition.category });
  }

  /**
   * Get a tool by name (legacy interface)
   */
  get(name: string): BaseTool | null {
    return this.toolRegistry.get(name);
  }

  /**
   * List all tools (legacy interface)
   */
  list(): ToolDefinition[] {
    return this.toolRegistry.list();
  }

  /**
   * List tools by category (legacy interface)
   */
  listByCategory(category: string): ToolDefinition[] {
    return this.toolRegistry.list({ category });
  }

  /**
   * Execute a tool (legacy interface)
   */
  async execute(name: string, parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    if (!this.initialized) {
      await this.initialize();
    }

    const result = await this.toolRegistry.execute(name, parameters, context);
    this.emit('tool:executing', { name, parameters, context });
    this.emit('tool:executed', { name, parameters, context, result });
    return result;
  }

  /**
   * Unregister a tool (legacy interface)
   */
  async unregister(name: string): Promise<void> {
    await this.toolRegistry.unregister(name);
    this.emit('tool:unregistered', { name });
  }

  /**
   * Cleanup (legacy interface)
   */
  async cleanup(): Promise<void> {
    await this.toolRegistry.shutdown();
    this.removeAllListeners();
  }

  // ========================================
  // Enhanced Interface (New Features)
  // ========================================

  /**
   * Get tool discovery information
   */
  discoverTools() {
    return this.toolInitializer.discoverTools();
  }

  /**
   * Get system information
   */
  getSystemInfo() {
    return this.toolInitializer.getSystemInfo();
  }

  /**
   * Get tool execution metrics
   */
  getMetrics(toolName?: string) {
    return this.toolRegistry.getMetrics(toolName);
  }

  /**
   * Get running executions
   */
  getRunningExecutions() {
    return this.toolRegistry.getRunningExecutions();
  }

  /**
   * Cancel a running execution
   */
  async cancelExecution(executionId: string): Promise<boolean> {
    return await this.toolRegistry.cancelExecution(executionId);
  }

  /**
   * Get health status
   */
  async healthCheck() {
    return await this.toolRegistry.healthCheck();
  }

  /**
   * Enhanced list with filtering
   */
  listEnhanced(filters?: {
    category?: string;
    tags?: string[];
    status?: 'active' | 'disabled' | 'deprecated';
  }) {
    return this.toolRegistry.list(filters);
  }

  /**
   * Validate tool parameters
   */
  validateToolParameters(toolName: string, parameters: Record<string, any>) {
    const tool = this.toolRegistry.get(toolName);
    if (!tool) {
      return {
        isValid: false,
        errors: [`Tool '${toolName}' not found`],
        warnings: []
      };
    }

    return tool.validate(parameters);
  }

  /**
   * Get the underlying tool registry
   */
  getToolRegistry(): ToolRegistry {
    return this.toolRegistry;
  }

  /**
   * Get initialization status
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  // ========================================
  // Private Methods
  // ========================================

  private setupEventForwarding(): void {
    // Forward tool registry events
    const eventsToForward = [
      'tool.registered',
      'tool.unregistered',
      'execution.start',
      'execution.complete',
      'execution.error',
      'execution.cancelled'
    ];

    eventsToForward.forEach(eventName => {
      this.toolRegistry.on(eventName, (data) => {
        this.emit(eventName, data);
      });
    });

    // Forward tool initializer events (if any)
    // The initializer primarily works during startup, but we can forward system events
  }
}

/**
 * Factory function to create an enhanced tool manager
 */
export async function createEnhancedToolManager(config?: EnhancedToolManagerConfig): Promise<EnhancedToolManager> {
  const manager = new EnhancedToolManager(config);
  await manager.initialize();
  return manager;
}

/**
 * Backward compatibility: Create a tool manager that looks like the legacy one
 */
export async function createCompatibleToolManager(config?: EnhancedToolManagerConfig): Promise<any> {
  const enhancedManager = await createEnhancedToolManager(config);

  // Return an object that matches the legacy interface exactly
  return {
    register: (tool: BaseTool) => enhancedManager.register(tool),
    get: (name: string) => enhancedManager.get(name),
    list: () => enhancedManager.list(),
    listByCategory: (category: string) => enhancedManager.listByCategory(category),
    execute: (name: string, parameters: Record<string, any>, context: ToolExecutionContext) => 
      enhancedManager.execute(name, parameters, context),
    unregister: (name: string) => enhancedManager.unregister(name),
    cleanup: () => enhancedManager.cleanup(),
    
    // Enhanced features (backward compatible extensions)
    discoverTools: () => enhancedManager.discoverTools(),
    getSystemInfo: () => enhancedManager.getSystemInfo(),
    getMetrics: (toolName?: string) => enhancedManager.getMetrics(toolName),
    getRunningExecutions: () => enhancedManager.getRunningExecutions(),
    cancelExecution: (executionId: string) => enhancedManager.cancelExecution(executionId),
    healthCheck: () => enhancedManager.healthCheck(),
    
    // Event emitter functionality
    on: (event: string, listener: (...args: any[]) => void) => enhancedManager.on(event, listener),
    off: (event: string, listener: (...args: any[]) => void) => enhancedManager.off(event, listener),
    emit: (event: string, ...args: any[]) => enhancedManager.emit(event, ...args)
  };
}