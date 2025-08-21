/**
 * Built-in Tools System - Extensible tool framework for ASI-Code
 * 
 * Provides a comprehensive set of built-in tools and an extensible framework
 * for creating custom tools that integrate with the Kenny Integration Pattern.
 */

export * from './tool-registry.js';
export * from './base-tool.js';
export * from './built-in-tools/index.js';

// Legacy exports for backward compatibility
import { EventEmitter } from 'eventemitter3';
import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { glob } from 'glob';

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required?: boolean;
  default?: any;
  enum?: any[];
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: ToolParameter[];
  category: 'file' | 'system' | 'network' | 'ai' | 'custom';
  version: string;
  author?: string;
}

export interface ToolExecutionContext {
  sessionId: string;
  userId?: string;
  permissions: string[];
  workingDirectory: string;
  environment: Record<string, string>;
}

export interface ToolResult {
  success: boolean;
  data?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export interface Tool extends EventEmitter {
  definition: ToolDefinition;
  execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult>;
  validate(parameters: Record<string, any>): boolean;
  cleanup(): Promise<void>;
}

export abstract class BaseTool extends EventEmitter implements Tool {
  public definition: ToolDefinition;

  constructor(definition: ToolDefinition) {
    super();
    this.definition = definition;
  }

  abstract execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult>;

  validate(parameters: Record<string, any>): boolean {
    for (const param of this.definition.parameters) {
      if (param.required && !(param.name in parameters)) {
        return false;
      }
      
      if (param.name in parameters) {
        const value = parameters[param.name];
        const expectedType = param.type;
        
        if (expectedType === 'string' && typeof value !== 'string') return false;
        if (expectedType === 'number' && typeof value !== 'number') return false;
        if (expectedType === 'boolean' && typeof value !== 'boolean') return false;
        if (expectedType === 'object' && (typeof value !== 'object' || Array.isArray(value))) return false;
        if (expectedType === 'array' && !Array.isArray(value)) return false;
        
        if (param.enum && !param.enum.includes(value)) return false;
      }
    }
    return true;
  }

  async cleanup(): Promise<void> {
    this.removeAllListeners();
  }
}

// Built-in File Tools
export class ReadFileTool extends BaseTool {
  constructor() {
    super({
      name: 'read_file',
      description: 'Read contents of a file',
      parameters: [
        { name: 'path', type: 'string', description: 'File path to read', required: true },
        { name: 'encoding', type: 'string', description: 'File encoding', default: 'utf8' }
      ],
      category: 'file',
      version: '1.0.0'
    });
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    try {
      const { path, encoding = 'utf8' } = parameters;
      
      if (!existsSync(path)) {
        return { success: false, error: `File not found: ${path}` };
      }

      const content = readFileSync(path, encoding);
      this.emit('executed', { tool: 'read_file', path, success: true });
      
      return {
        success: true,
        data: { content, path, encoding },
        metadata: { size: content.length }
      };
    } catch (error) {
      this.emit('error', { tool: 'read_file', error, parameters });
      return { success: false, error: (error as Error).message };
    }
  }
}

export class WriteFileTool extends BaseTool {
  constructor() {
    super({
      name: 'write_file',
      description: 'Write content to a file',
      parameters: [
        { name: 'path', type: 'string', description: 'File path to write', required: true },
        { name: 'content', type: 'string', description: 'Content to write', required: true },
        { name: 'encoding', type: 'string', description: 'File encoding', default: 'utf8' }
      ],
      category: 'file',
      version: '1.0.0'
    });
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    try {
      const { path, content, encoding = 'utf8' } = parameters;
      
      writeFileSync(path, content, encoding);
      this.emit('executed', { tool: 'write_file', path, success: true });
      
      return {
        success: true,
        data: { path, size: content.length },
        metadata: { encoding }
      };
    } catch (error) {
      this.emit('error', { tool: 'write_file', error, parameters });
      return { success: false, error: (error as Error).message };
    }
  }
}

export class GlobTool extends BaseTool {
  constructor() {
    super({
      name: 'glob',
      description: 'Find files matching a pattern',
      parameters: [
        { name: 'pattern', type: 'string', description: 'Glob pattern to match', required: true },
        { name: 'cwd', type: 'string', description: 'Working directory', default: '.' },
        { name: 'ignore', type: 'array', description: 'Patterns to ignore', default: [] }
      ],
      category: 'file',
      version: '1.0.0'
    });
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    try {
      const { pattern, cwd = context.workingDirectory, ignore = [] } = parameters;
      
      const files = await glob(pattern, { cwd, ignore });
      this.emit('executed', { tool: 'glob', pattern, found: files.length });
      
      return {
        success: true,
        data: { files, pattern, cwd },
        metadata: { count: files.length }
      };
    } catch (error) {
      this.emit('error', { tool: 'glob', error, parameters });
      return { success: false, error: (error as Error).message };
    }
  }
}

// Built-in System Tools
export class ExecuteCommandTool extends BaseTool {
  constructor() {
    super({
      name: 'execute_command',
      description: 'Execute a shell command',
      parameters: [
        { name: 'command', type: 'string', description: 'Command to execute', required: true },
        { name: 'cwd', type: 'string', description: 'Working directory' },
        { name: 'timeout', type: 'number', description: 'Timeout in milliseconds', default: 30000 }
      ],
      category: 'system',
      version: '1.0.0'
    });
  }

  async execute(parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    try {
      const { command, cwd = context.workingDirectory, timeout = 30000 } = parameters;
      
      // Check permissions
      if (!context.permissions.includes('execute_commands')) {
        return { success: false, error: 'Permission denied: execute_commands required' };
      }

      const output = execSync(command, { 
        cwd, 
        timeout, 
        encoding: 'utf8',
        env: { ...process.env, ...context.environment }
      });
      
      this.emit('executed', { tool: 'execute_command', command, success: true });
      
      return {
        success: true,
        data: { output, command, cwd },
        metadata: { executionTime: Date.now() }
      };
    } catch (error) {
      this.emit('error', { tool: 'execute_command', error, parameters });
      return { success: false, error: (error as Error).message };
    }
  }
}

// Tool Manager
export class ToolManager extends EventEmitter {
  private tools = new Map<string, Tool>();

  register(tool: Tool): void {
    this.tools.set(tool.definition.name, tool);
    this.emit('tool:registered', { name: tool.definition.name, category: tool.definition.category });
  }

  get(name: string): Tool | undefined {
    return this.tools.get(name);
  }

  list(): ToolDefinition[] {
    return Array.from(this.tools.values()).map(tool => tool.definition);
  }

  listByCategory(category: string): ToolDefinition[] {
    return this.list().filter(def => def.category === category);
  }

  async execute(name: string, parameters: Record<string, any>, context: ToolExecutionContext): Promise<ToolResult> {
    const tool = this.tools.get(name);
    if (!tool) {
      return { success: false, error: `Tool not found: ${name}` };
    }

    if (!tool.validate(parameters)) {
      return { success: false, error: `Invalid parameters for tool: ${name}` };
    }

    this.emit('tool:executing', { name, parameters, context });
    const result = await tool.execute(parameters, context);
    this.emit('tool:executed', { name, parameters, context, result });
    
    return result;
  }

  async unregister(name: string): Promise<void> {
    const tool = this.tools.get(name);
    if (tool) {
      await tool.cleanup();
      this.tools.delete(name);
      this.emit('tool:unregistered', { name });
    }
  }

  async cleanup(): Promise<void> {
    for (const tool of this.tools.values()) {
      await tool.cleanup();
    }
    this.tools.clear();
    this.removeAllListeners();
  }
}

// Built-in tools factory
export function createBuiltinTools(): Tool[] {
  return [
    new ReadFileTool(),
    new WriteFileTool(),
    new GlobTool(),
    new ExecuteCommandTool()
  ];
}

// Factory function
export function createToolManager(): ToolManager {
  const manager = new ToolManager();
  
  // Register built-in tools
  const builtinTools = createBuiltinTools();
  for (const tool of builtinTools) {
    manager.register(tool);
  }
  
  return manager;
}