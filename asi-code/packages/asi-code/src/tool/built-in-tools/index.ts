/**
 * Built-in Tools - Export all built-in tools for ASI-Code
 * 
 * Provides easy access to all built-in tools and factory functions
 * for creating tool instances.
 */

export { default as BashTool } from './bash.js';
export { default as ReadTool } from './read.js';
export { default as WriteTool } from './write.js';
export { default as EditTool } from './edit.js';

// Re-export types from individual tools
export type { BashExecutionOptions } from './bash.js';
export type { ReadOptions } from './read.js';
export type { WriteOptions } from './write.js';
export type { EditOperation, EditDiff } from './edit.js';

import BashTool from './bash.js';
import ReadTool from './read.js';
import WriteTool from './write.js';
import EditTool from './edit.js';
import type { BaseTool } from '../base-tool.js';

/**
 * Factory function to create all built-in tools
 */
export function createBuiltInTools(): BaseTool[] {
  return [
    new BashTool(),
    new ReadTool(),
    new WriteTool(),
    new EditTool()
  ];
}

/**
 * Factory function to create a specific built-in tool by name
 */
export function createBuiltInTool(name: string): BaseTool | null {
  switch (name) {
    case 'bash':
      return new BashTool();
    case 'read':
      return new ReadTool();
    case 'write':
      return new WriteTool();
    case 'edit':
      return new EditTool();
    default:
      return null;
  }
}

/**
 * Get list of available built-in tool names
 */
export function getBuiltInToolNames(): string[] {
  return ['bash', 'read', 'write', 'edit'];
}

/**
 * Get built-in tool categories
 */
export function getBuiltInToolCategories(): Record<string, string[]> {
  return {
    file: ['read', 'write', 'edit'],
    system: ['bash']
  };
}