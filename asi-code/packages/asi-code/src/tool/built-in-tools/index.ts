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
export { default as SearchTool } from './search.js';
export { default as DeleteTool } from './delete.js';
export { default as MoveTool } from './move.js';
export { default as ListTool } from './list.js';

// Re-export types from individual tools
export type { BashExecutionOptions } from './bash.js';
export type { ReadOptions } from './read.js';
export type { WriteOptions } from './write.js';
export type { EditOperation, EditDiff } from './edit.js';
export type { SearchOptions, SearchResult } from './search.js';
export type { DeleteOptions, DeleteResult } from './delete.js';
export type { MoveOptions, MoveResult } from './move.js';
export type { ListOptions, FileInfo, ListResult } from './list.js';

import BashTool from './bash.js';
import ReadTool from './read.js';
import WriteTool from './write.js';
import EditTool from './edit.js';
import SearchTool from './search.js';
import DeleteTool from './delete.js';
import MoveTool from './move.js';
import ListTool from './list.js';
import type { BaseTool } from '../base-tool.js';

/**
 * Factory function to create all built-in tools
 */
export function createBuiltInTools(): BaseTool[] {
  return [
    new BashTool(),
    new ReadTool(),
    new WriteTool(),
    new EditTool(),
    new SearchTool(),
    new DeleteTool(),
    new MoveTool(),
    new ListTool()
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
    case 'search':
      return new SearchTool();
    case 'delete':
      return new DeleteTool();
    case 'move':
      return new MoveTool();
    case 'list':
      return new ListTool();
    default:
      return null;
  }
}

/**
 * Get list of available built-in tool names
 */
export function getBuiltInToolNames(): string[] {
  return ['bash', 'read', 'write', 'edit', 'search', 'delete', 'move', 'list'];
}

/**
 * Get built-in tool categories
 */
export function getBuiltInToolCategories(): Record<string, string[]> {
  return {
    file: ['read', 'write', 'edit', 'search', 'delete', 'move', 'list'],
    system: ['bash']
  };
}