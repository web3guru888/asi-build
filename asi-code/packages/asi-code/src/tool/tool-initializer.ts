/**
 * Tool Initializer - Central tool registration and initialization system
 *
 * Provides automated registration of all built-in tools with the Tool Registry,
 * handles tool discovery, validation, and startup initialization.
 */

import { ToolRegistry, ToolRegistryConfig } from './tool-registry.js';
import {
  createBuiltInTools,
  getBuiltInToolCategories,
  getBuiltInToolNames,
} from './built-in-tools/index.js';
import { BaseTool, ToolDefinition } from './base-tool.js';
import { getKennyIntegration } from '../kenny/integration.js';
import type { PermissionManager } from '../permission/permission-manager.js';

export interface ToolInitializerConfig {
  permissionManager?: PermissionManager;
  enableMetrics?: boolean;
  enableCaching?: boolean;
  maxConcurrentExecutions?: number;
  defaultTimeout?: number;
  autoRegisterBuiltIns?: boolean;
  enableToolValidation?: boolean;
  enableVersioning?: boolean;
}

export interface ToolInitializationResult {
  registry: ToolRegistry;
  toolsRegistered: number;
  categoryCounts: Record<string, number>;
  errors: Array<{
    toolName: string;
    error: string;
  }>;
  initializationTime: number;
}

export interface ToolDiscoveryInfo {
  name: string;
  version: string;
  category: string;
  description: string;
  permissions: string[];
  safetyLevel: string;
  tags: string[];
  status: 'active' | 'disabled' | 'deprecated';
  registeredAt?: Date;
}

/**
 * Central tool initialization and management system
 * Integrates with Kenny Integration Pattern for event-driven operations
 */
export class ToolInitializer {
  private readonly registry: ToolRegistry;
  private readonly config: Required<
    Omit<ToolInitializerConfig, 'permissionManager'>
  > & { permissionManager?: PermissionManager };
  private initializationTime?: number;

  constructor(config: ToolInitializerConfig = {}) {
    this.config = {
      permissionManager: config.permissionManager,
      enableMetrics: config.enableMetrics ?? true,
      enableCaching: config.enableCaching ?? true,
      maxConcurrentExecutions: config.maxConcurrentExecutions ?? 10,
      defaultTimeout: config.defaultTimeout ?? 300000,
      autoRegisterBuiltIns: config.autoRegisterBuiltIns ?? true,
      enableToolValidation: config.enableToolValidation ?? true,
      enableVersioning: config.enableVersioning ?? true,
    };

    // Create tool registry with configuration
    const registryConfig: ToolRegistryConfig = {
      permissionManager: this.config.permissionManager,
      enableMetrics: this.config.enableMetrics,
      enableCaching: this.config.enableCaching,
      maxConcurrentExecutions: this.config.maxConcurrentExecutions,
      defaultTimeout: this.config.defaultTimeout,
    };

    this.registry = new ToolRegistry(registryConfig);
  }

  /**
   * Initialize the tool system with all built-in tools
   */
  async initialize(): Promise<ToolInitializationResult> {
    const startTime = Date.now();
    const errors: Array<{ toolName: string; error: string }> = [];
    let toolsRegistered = 0;
    const categoryCounts: Record<string, number> = {};

    try {
      // Initialize the tool registry
      await this.registry.initialize({
        permissionManager: this.config.permissionManager,
      });

      // Start the registry
      await this.registry.start();

      // Auto-register built-in tools if enabled
      if (this.config.autoRegisterBuiltIns) {
        const registrationResult = await this.registerBuiltInTools();
        toolsRegistered += registrationResult.toolsRegistered;
        errors.push(...registrationResult.errors);

        // Update category counts
        for (const [category, count] of Object.entries(
          registrationResult.categoryCounts
        )) {
          categoryCounts[category] = (categoryCounts[category] || 0) + count;
        }
      }

      this.initializationTime = Date.now() - startTime;

      // Emit initialization event
      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('tool.system.initialized', 'tool-registry', {
          toolsRegistered,
          categoryCounts,
          initializationTime: this.initializationTime,
          hasErrors: errors.length > 0,
        });

      return {
        registry: this.registry,
        toolsRegistered,
        categoryCounts,
        errors,
        initializationTime: this.initializationTime,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      errors.push({ toolName: 'system', error: errorMessage });

      // Emit error event
      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('tool.system.error', 'tool-registry', {
          error: errorMessage,
          initializationTime: Date.now() - startTime,
        });

      throw error;
    }
  }

  /**
   * Register all built-in tools with the registry
   */
  async registerBuiltInTools(): Promise<{
    toolsRegistered: number;
    categoryCounts: Record<string, number>;
    errors: Array<{ toolName: string; error: string }>;
  }> {
    const errors: Array<{ toolName: string; error: string }> = [];
    const categoryCounts: Record<string, number> = {};
    let toolsRegistered = 0;

    try {
      // Get all built-in tools
      const tools = createBuiltInTools();
      const categories = getBuiltInToolCategories();

      // Register each tool
      for (const tool of tools) {
        try {
          // Validate tool if validation is enabled
          if (this.config.enableToolValidation) {
            const validation = await this.validateTool(tool);
            if (!validation.isValid) {
              errors.push({
                toolName: tool.definition.name,
                error: `Validation failed: ${validation.errors.join(', ')}`,
              });
              continue;
            }
          }

          // Determine tool tags based on category
          const toolTags = this.generateToolTags(tool, categories);

          // Initialize the tool
          await tool.initialize();

          // Register with the registry
          await this.registry.register(tool, toolTags);

          toolsRegistered++;

          // Update category count
          const category = tool.definition.category;
          categoryCounts[category] = (categoryCounts[category] || 0) + 1;

          console.log(
            `[ToolInitializer] Registered tool: ${tool.definition.name} (${category})`
          );
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : String(error);
          errors.push({ toolName: tool.definition.name, error: errorMessage });
          console.error(
            `[ToolInitializer] Failed to register tool ${tool.definition.name}:`,
            errorMessage
          );
        }
      }

      return { toolsRegistered, categoryCounts, errors };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      errors.push({ toolName: 'bulk_registration', error: errorMessage });
      return { toolsRegistered, categoryCounts, errors };
    }
  }

  /**
   * Validate a tool before registration
   */
  async validateTool(tool: BaseTool): Promise<{
    isValid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      const definition = tool.definition;

      // Validate required fields
      if (!definition.name || definition.name.trim().length === 0) {
        errors.push('Tool name is required');
      }

      if (
        !definition.description ||
        definition.description.trim().length === 0
      ) {
        errors.push('Tool description is required');
      }

      if (!definition.version || definition.version.trim().length === 0) {
        errors.push('Tool version is required');
      }

      if (!definition.category) {
        errors.push('Tool category is required');
      }

      // Validate parameters
      if (!Array.isArray(definition.parameters)) {
        errors.push('Tool parameters must be an array');
      } else {
        for (const param of definition.parameters) {
          if (!param.name || param.name.trim().length === 0) {
            errors.push(`Parameter missing name: ${JSON.stringify(param)}`);
          }
          if (!param.type) {
            errors.push(`Parameter '${param.name}' missing type`);
          }
          if (!param.description || param.description.trim().length === 0) {
            warnings.push(`Parameter '${param.name}' missing description`);
          }
        }
      }

      // Validate safety level
      const validSafetyLevels = ['safe', 'moderate', 'high-risk', 'dangerous'];
      if (
        definition.safetyLevel &&
        !validSafetyLevels.includes(definition.safetyLevel)
      ) {
        errors.push(`Invalid safety level: ${definition.safetyLevel}`);
      }

      // Validate category
      const validCategories = [
        'file',
        'system',
        'network',
        'ai',
        'custom',
        'analysis',
        'generation',
      ];
      if (
        definition.category &&
        !validCategories.includes(definition.category)
      ) {
        errors.push(`Invalid category: ${definition.category}`);
      }

      // Version format validation
      if (this.config.enableVersioning && definition.version) {
        const versionRegex = /^\d+\.\d+\.\d+(-\w+)?$/;
        if (!versionRegex.test(definition.version)) {
          warnings.push(
            `Tool version '${definition.version}' doesn't follow semantic versioning`
          );
        }
      }

      // Check for method implementations
      if (typeof tool.execute !== 'function') {
        errors.push('Tool must implement execute method');
      }

      if (typeof tool.validate !== 'function') {
        errors.push('Tool must implement validate method');
      }

      return {
        isValid: errors.length === 0,
        errors,
        warnings,
      };
    } catch (error) {
      errors.push(
        `Validation error: ${error instanceof Error ? error.message : String(error)}`
      );
      return { isValid: false, errors, warnings };
    }
  }

  /**
   * Generate appropriate tags for a tool
   */
  private generateToolTags(
    tool: BaseTool,
    categories: Record<string, string[]>
  ): string[] {
    const tags = new Set<string>();

    // Add category-based tags
    tags.add(tool.definition.category);

    // Add built-in tag
    tags.add('built-in');

    // Add version-based tag
    if (this.config.enableVersioning) {
      const version = tool.definition.version;
      const majorVersion = version.split('.')[0];
      tags.add(`v${majorVersion}`);
    }

    // Add safety level tag
    if (tool.definition.safetyLevel) {
      tags.add(tool.definition.safetyLevel.replace('-', '_'));
    }

    // Add custom tags from tool definition
    if (tool.definition.tags) {
      for (const tag of tool.definition.tags) {
        tags.add(tag);
      }
    }

    // Add functional tags based on tool name
    const toolName = tool.definition.name.toLowerCase();
    if (toolName.includes('read') || toolName.includes('get')) {
      tags.add('read-operation');
    }
    if (toolName.includes('write') || toolName.includes('create')) {
      tags.add('write-operation');
    }
    if (toolName.includes('delete') || toolName.includes('remove')) {
      tags.add('destructive-operation');
    }

    return Array.from(tags);
  }

  /**
   * Discover all registered tools and their metadata
   */
  discoverTools(): ToolDiscoveryInfo[] {
    const toolDefinitions = this.registry.list();
    const discoveryInfo: ToolDiscoveryInfo[] = [];

    for (const definition of toolDefinitions) {
      // Get additional metadata from the registry if available
      const tool = this.registry.get(definition.name);
      const toolInfo = tool?.getInfo();

      discoveryInfo.push({
        name: definition.name,
        version: definition.version,
        category: definition.category,
        description: definition.description,
        permissions: definition.permissions || [],
        safetyLevel: definition.safetyLevel || 'safe',
        tags: definition.tags || [],
        status: 'active', // Could be enhanced to check actual tool status
        registeredAt: toolInfo ? undefined : new Date(), // Would need registry metadata
      });
    }

    return discoveryInfo.sort((a, b) => a.name.localeCompare(b.name));
  }

  /**
   * Get comprehensive tool system information
   */
  getSystemInfo(): {
    totalTools: number;
    categoryCounts: Record<string, number>;
    safetyLevelCounts: Record<string, number>;
    initializationTime?: number;
    registryHealth: any;
    builtInTools: string[];
    customTools: string[];
  } {
    const discovery = this.discoverTools();
    const categoryCounts: Record<string, number> = {};
    const safetyLevelCounts: Record<string, number> = {};
    const builtInTools: string[] = [];
    const customTools: string[] = [];

    for (const tool of discovery) {
      // Category counts
      categoryCounts[tool.category] = (categoryCounts[tool.category] || 0) + 1;

      // Safety level counts
      safetyLevelCounts[tool.safetyLevel] =
        (safetyLevelCounts[tool.safetyLevel] || 0) + 1;

      // Built-in vs custom classification
      if (tool.tags.includes('built-in')) {
        builtInTools.push(tool.name);
      } else {
        customTools.push(tool.name);
      }
    }

    return {
      totalTools: discovery.length,
      categoryCounts,
      safetyLevelCounts,
      initializationTime: this.initializationTime,
      registryHealth: this.registry.healthCheck(),
      builtInTools,
      customTools,
    };
  }

  /**
   * Get the tool registry instance
   */
  getRegistry(): ToolRegistry {
    return this.registry;
  }

  /**
   * Shutdown the tool system
   */
  async shutdown(): Promise<void> {
    await this.registry.shutdown();

    // Emit shutdown event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('tool.system.shutdown', 'tool-registry', {
        shutdownTime: new Date(),
      });
  }
}

/**
 * Factory function to create and initialize the tool system
 */
export async function initializeToolSystem(
  config?: ToolInitializerConfig
): Promise<ToolInitializationResult> {
  const initializer = new ToolInitializer(config);
  return await initializer.initialize();
}

/**
 * Create a configured tool initializer instance
 */
export function createToolInitializer(
  config?: ToolInitializerConfig
): ToolInitializer {
  return new ToolInitializer(config);
}
