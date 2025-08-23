/**
 * Base Tool - Abstract foundation for all tools in ASI-Code
 *
 * Provides the base interface and common functionality that all tools must implement.
 * Integrates with the Kenny Integration Pattern and permission system.
 */

import { EventEmitter } from 'eventemitter3';
import { getKennyIntegration } from '../kenny/integration.js';

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required?: boolean;
  default?: any;
  enum?: any[];
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    custom?: (value: any) => boolean | string;
  };
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: ToolParameter[];
  category:
    | 'file'
    | 'system'
    | 'network'
    | 'ai'
    | 'custom'
    | 'analysis'
    | 'generation';
  version: string;
  author?: string;
  permissions?: string[];
  safetyLevel?: 'safe' | 'moderate' | 'high-risk' | 'dangerous';
  tags?: string[];
  examples?: Array<{
    description: string;
    parameters: Record<string, any>;
    expectedResult?: any;
  }>;
}

export interface ToolExecutionContext {
  sessionId: string;
  userId?: string;
  permissions: string[];
  workingDirectory: string;
  environment: Record<string, string>;
  metadata?: Record<string, any>;
  limits?: {
    maxExecutionTime?: number;
    maxMemoryUsage?: number;
    maxFileSize?: number;
  };
}

export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
  warnings?: string[];
  metadata?: Record<string, any>;
  performance?: {
    executionTime: number;
    memoryUsage?: number;
    resourcesAccessed?: string[];
  };
}

export interface ToolValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Abstract base class for all tools in the ASI-Code system
 */
export abstract class BaseTool extends EventEmitter {
  public readonly definition: ToolDefinition;
  private initialized = false;
  private disposed = false;

  constructor(definition: ToolDefinition) {
    super();
    this.definition = {
      safetyLevel: 'safe',
      tags: [],
      permissions: [],
      ...definition,
    };
  }

  /**
   * Initialize the tool (optional override)
   */
  async initialize(config?: Record<string, any>): Promise<void> {
    if (this.initialized) {
      return;
    }

    // Publish initialization event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('tool.initialize', 'tool-registry', {
        toolName: this.definition.name,
        config: config ? Object.keys(config) : [],
      });

    this.initialized = true;
    this.emit('initialized', { config });
  }

  /**
   * Main execution method - must be implemented by all tools
   */
  abstract execute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult>;

  /**
   * Validate parameters against the tool definition
   */
  validate(parameters: Record<string, any>): ToolValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check required parameters
    for (const param of this.definition.parameters) {
      if (param.required && !(param.name in parameters)) {
        errors.push(`Required parameter '${param.name}' is missing`);
        continue;
      }

      if (param.name in parameters) {
        const value = parameters[param.name];
        const validationResult = this.validateParameter(param, value);

        if (!validationResult.isValid) {
          errors.push(...validationResult.errors);
        }
        warnings.push(...validationResult.warnings);
      }
    }

    // Check for unexpected parameters
    for (const paramName in parameters) {
      if (!this.definition.parameters.find(p => p.name === paramName)) {
        warnings.push(`Unexpected parameter '${paramName}' provided`);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Pre-execution hook - can be overridden for custom validation/preparation
   */
  async beforeExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<void> {
    // Check safety level against context
    if (
      this.definition.safetyLevel === 'dangerous' &&
      !context.permissions.includes('dangerous_operations')
    ) {
      throw new Error(
        `Tool ${this.definition.name} requires dangerous_operations permission`
      );
    }

    // Check specific tool permissions
    if (this.definition.permissions) {
      for (const permission of this.definition.permissions) {
        if (!context.permissions.includes(permission)) {
          throw new Error(
            `Tool ${this.definition.name} requires permission: ${permission}`
          );
        }
      }
    }

    this.emit('beforeExecute', { parameters, context });
  }

  /**
   * Post-execution hook - can be overridden for cleanup/logging
   */
  async afterExecute(
    parameters: Record<string, any>,
    context: ToolExecutionContext,
    result: ToolResult
  ): Promise<void> {
    // Publish execution event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('tool.execute', 'tool-registry', {
        toolName: this.definition.name,
        success: result.success,
        executionTime: result.performance?.executionTime || 0,
        parametersCount: Object.keys(parameters).length,
      });

    this.emit('afterExecute', { parameters, context, result });
  }

  /**
   * Execute the tool with full lifecycle management
   */
  async executeWithLifecycle(
    parameters: Record<string, any>,
    context: ToolExecutionContext
  ): Promise<ToolResult> {
    if (this.disposed) {
      return {
        success: false,
        error: `Tool ${this.definition.name} has been disposed`,
      };
    }

    const startTime = Date.now();
    let result: ToolResult;

    try {
      // Pre-execution
      await this.beforeExecute(parameters, context);

      // Validate parameters
      const validation = this.validate(parameters);
      if (!validation.isValid) {
        return {
          success: false,
          error: `Parameter validation failed: ${validation.errors.join(', ')}`,
          warnings: validation.warnings,
          performance: {
            executionTime: Date.now() - startTime,
          },
        };
      }

      // Execute
      result = await this.execute(parameters, context);

      // Add performance data if not already present
      if (!result.performance) {
        result.performance = {
          executionTime: Date.now() - startTime,
        };
      } else if (!result.performance.executionTime) {
        result.performance.executionTime = Date.now() - startTime;
      }

      // Add warnings from validation if any
      if (validation.warnings.length > 0) {
        result.warnings = [...(result.warnings || []), ...validation.warnings];
      }
    } catch (error) {
      result = {
        success: false,
        error: error instanceof Error ? error.message : String(error),
        performance: {
          executionTime: Date.now() - startTime,
        },
      };
    }

    try {
      // Post-execution
      await this.afterExecute(parameters, context, result);
    } catch (error) {
      console.error(
        `Error in afterExecute for tool ${this.definition.name}:`,
        error
      );
    }

    return result;
  }

  /**
   * Get tool information including current status
   */
  getInfo(): ToolDefinition & { initialized: boolean; disposed: boolean } {
    return {
      ...this.definition,
      initialized: this.initialized,
      disposed: this.disposed,
    };
  }

  /**
   * Check if the tool can execute with given permissions
   */
  canExecute(permissions: string[]): boolean {
    // Check safety level
    if (
      this.definition.safetyLevel === 'dangerous' &&
      !permissions.includes('dangerous_operations')
    ) {
      return false;
    }

    // Check specific permissions
    if (this.definition.permissions) {
      for (const permission of this.definition.permissions) {
        if (!permissions.includes(permission)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Cleanup resources and dispose the tool
   */
  async cleanup(): Promise<void> {
    if (this.disposed) {
      return;
    }

    // Publish cleanup event
    try {
      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('tool.cleanup', 'tool-registry', {
          toolName: this.definition.name,
        });
    } catch (error) {
      console.error(
        `Error publishing cleanup event for tool ${this.definition.name}:`,
        error
      );
    }

    this.disposed = true;
    this.initialized = false;
    this.removeAllListeners();
    this.emit('disposed');
  }

  /**
   * Create a safe execution context for testing
   */
  static createTestContext(
    overrides: Partial<ToolExecutionContext> = {}
  ): ToolExecutionContext {
    return {
      sessionId: 'test-session',
      userId: 'test-user',
      permissions: ['read_files', 'write_files'],
      workingDirectory: process.cwd(),
      environment: {},
      ...overrides,
    };
  }

  private validateParameter(
    param: ToolParameter,
    value: any
  ): ToolValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Type validation
    const expectedType = param.type;
    const actualType = Array.isArray(value) ? 'array' : typeof value;

    if (
      expectedType === 'object' &&
      (actualType !== 'object' || Array.isArray(value))
    ) {
      errors.push(
        `Parameter '${param.name}' must be an object, got ${actualType}`
      );
      return { isValid: false, errors, warnings };
    } else if (expectedType !== 'object' && actualType !== expectedType) {
      errors.push(
        `Parameter '${param.name}' must be ${expectedType}, got ${actualType}`
      );
      return { isValid: false, errors, warnings };
    }

    // Enum validation
    if (param.enum && !param.enum.includes(value)) {
      errors.push(
        `Parameter '${param.name}' must be one of: ${param.enum.join(', ')}`
      );
    }

    // Additional validation if specified
    if (param.validation) {
      const validation = param.validation;

      // Min/max validation for numbers
      if (expectedType === 'number' && typeof value === 'number') {
        if (validation.min !== undefined && value < validation.min) {
          errors.push(`Parameter '${param.name}' must be >= ${validation.min}`);
        }
        if (validation.max !== undefined && value > validation.max) {
          errors.push(`Parameter '${param.name}' must be <= ${validation.max}`);
        }
      }

      // Pattern validation for strings
      if (
        expectedType === 'string' &&
        typeof value === 'string' &&
        validation.pattern
      ) {
        const regex = new RegExp(validation.pattern);
        if (!regex.test(value)) {
          errors.push(
            `Parameter '${param.name}' does not match required pattern`
          );
        }
      }

      // Custom validation
      if (validation.custom) {
        try {
          const customResult = validation.custom(value);
          if (typeof customResult === 'string') {
            errors.push(`Parameter '${param.name}': ${customResult}`);
          } else if (!customResult) {
            errors.push(`Parameter '${param.name}' failed custom validation`);
          }
        } catch (error) {
          errors.push(`Parameter '${param.name}' validation error: ${error}`);
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }
}

/**
 * Decorator for tool methods to add automatic logging and error handling
 */
export function toolMethod(
  target: any,
  propertyKey: string,
  descriptor: PropertyDescriptor
) {
  const originalMethod = descriptor.value;

  descriptor.value = async function (this: BaseTool, ...args: any[]) {
    const methodName = `${this.definition.name}.${propertyKey}`;

    this.emit('methodCall', {
      method: methodName,
      args: args.map(arg => typeof arg),
    });

    try {
      const result = await originalMethod.apply(this, args);
      this.emit('methodComplete', { method: methodName, success: true });
      return result;
    } catch (error) {
      this.emit('methodError', {
        method: methodName,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  };

  return descriptor;
}
