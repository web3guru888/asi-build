/**
 * ASI-Code HTTP/SSE Server - Main server exports
 * 
 * Exports server components, middleware, routes, and utilities
 * for the ASI-Code system.
 */

// Core server components
export * from './server.js';
export * from './routes.js';
export * from './middleware.js';

// Legacy exports for backward compatibility
export { 
  createASIServer, 
  defaultServerConfig,
  DefaultASIServer,
  SSEConnectionManager 
} from './server.js';

// Re-export types
import type { SessionManager } from '../session/index.js';
import type { ProviderManager } from '../provider/index.js';
import type { ToolManager } from '../tool/index.js';
import type { KennyMessage } from '../kenny/index.js';

export type { SessionManager, ProviderManager, ToolManager, KennyMessage };