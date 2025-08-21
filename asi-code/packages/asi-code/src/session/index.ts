/**
 * Session Management System - Main session exports
 * 
 * Exports session management components, storage systems,
 * and utilities for the ASI-Code system.
 */

// Core session components
export * from './session.js';
export * from './session-manager.js';
export * from './storage.js';

// Legacy exports for backward compatibility  
export {
  DefaultSession
} from './session.js';

export {
  DefaultSessionManager,
  createSessionManager
} from './session-manager.js';

export {
  MemorySessionStorage,
  SQLiteSessionStorage,
  createMemorySessionStorage,
  createSQLiteSessionStorage,
  createSessionStorage
} from './storage.js';

// Re-export types
import type { KennyContext, KennyMessage } from '../kenny/index.js';

export type { KennyContext, KennyMessage };