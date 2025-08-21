/**
 * App Module - Application context and lifecycle management
 * 
 * Provides centralized application state management and component lifecycle
 * coordination for the ASI-Code system.
 */

export * from './app-context.js';
export * from './lifecycle-manager.js';

// Convenience re-exports
export type {
  AppContext
} from './app-context.js';

export type {
  ASICodeConfig
} from '../config/config-types.js';

export type {
  LifecycleManager,
  ComponentState,
  ComponentInfo
} from './lifecycle-manager.js';

export {
  createAppContext,
  getGlobalAppContext,
  resetGlobalAppContext
} from './app-context.js';

export {
  createLifecycleManager
} from './lifecycle-manager.js';