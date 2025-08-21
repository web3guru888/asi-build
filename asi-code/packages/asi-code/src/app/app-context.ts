/**
 * App Context - Application-wide context and state management
 * 
 * Manages the global application state, configuration, and context
 * that needs to be accessible across all ASI-Code components.
 */

import { EventEmitter } from 'eventemitter3';
import type { ASICodeConfig } from '../config/config-types.js';
import { DEFAULT_ASI_CONFIG } from '../config/default-config.js';
import type { KennyContext } from '../kenny/index.js';
import type { Provider } from '../provider/index.js';
import type { ToolRegistry } from '../tool/index.js';
import type { PermissionManager } from '../permission/index.js';
import type { ConsciousnessEngine } from '../consciousness/index.js';
import type { SATEngine } from '../sat/index.js';

export interface AppContext extends EventEmitter {
  config: ASICodeConfig;
  initialized: boolean;
  providers: Map<string, Provider>;
  toolRegistry?: ToolRegistry;
  permissionManager?: PermissionManager;
  consciousnessEngine?: ConsciousnessEngine;
  satEngine?: SATEngine;
  
  // Context management
  createKennyContext(sessionId: string, userId: string, metadata?: Record<string, any>): KennyContext;
  getKennyContext(contextId: string): KennyContext | null;
  updateKennyContext(contextId: string, updates: Partial<KennyContext>): Promise<void>;
  removeKennyContext(contextId: string): Promise<void>;
  
  // Provider management
  registerProvider(name: string, provider: Provider): Promise<void>;
  getProvider(name: string): Provider | null;
  removeProvider(name: string): Promise<void>;
  
  // Component registration
  setToolRegistry(registry: ToolRegistry): void;
  setPermissionManager(manager: PermissionManager): void;
  setConsciousnessEngine(engine: ConsciousnessEngine): void;
  setSATEngine(engine: SATEngine): void;
  
  // Lifecycle
  initialize(config?: Partial<ASICodeConfig>): Promise<void>;
  shutdown(): Promise<void>;
}

export class DefaultAppContext extends EventEmitter implements AppContext {
  public config: ASICodeConfig;
  public initialized: boolean = false;
  public providers = new Map<string, Provider>();
  public toolRegistry?: ToolRegistry;
  public permissionManager?: PermissionManager;
  public consciousnessEngine?: ConsciousnessEngine;
  public satEngine?: SATEngine;
  
  private kennyContexts = new Map<string, KennyContext>();
  private contextCounter = 0;

  constructor(initialConfig?: Partial<ASICodeConfig>) {
    super();
    
    // Use default configuration and merge with initial config
    this.config = {
      ...DEFAULT_ASI_CONFIG,
      ...initialConfig
    };
  }

  createKennyContext(sessionId: string, userId: string, metadata: Record<string, any> = {}): KennyContext {
    const id = `ctx_${++this.contextCounter}_${Date.now()}`;
    
    const context: KennyContext = {
      id,
      sessionId,
      userId,
      consciousness: {
        level: 1,
        state: 'active',
        lastActivity: new Date()
      },
      metadata: {
        createdAt: new Date().toISOString(),
        lastActive: new Date().toISOString(),
        ...metadata
      }
    };

    this.kennyContexts.set(id, context);
    this.emit('context:created', { context });
    
    return context;
  }

  getKennyContext(contextId: string): KennyContext | null {
    const context = this.kennyContexts.get(contextId);
    if (context) {
      // Update last active timestamp
      context.metadata.lastActive = new Date().toISOString();
    }
    return context || null;
  }

  async updateKennyContext(contextId: string, updates: Partial<KennyContext>): Promise<void> {
    const existing = this.kennyContexts.get(contextId);
    if (!existing) {
      throw new Error(`Context ${contextId} not found`);
    }

    const updated: KennyContext = {
      ...existing,
      ...updates,
      id: contextId, // Ensure ID doesn't change
      metadata: {
        ...existing.metadata,
        ...updates.metadata,
        lastActive: new Date().toISOString()
      }
    };

    this.kennyContexts.set(contextId, updated);
    this.emit('context:updated', { context: updated, changes: updates });
  }

  async removeKennyContext(contextId: string): Promise<void> {
    const context = this.kennyContexts.get(contextId);
    if (context) {
      this.kennyContexts.delete(contextId);
      this.emit('context:removed', { context });
    }
  }

  async registerProvider(name: string, provider: Provider): Promise<void> {
    this.providers.set(name, provider);
    this.emit('provider:registered', { name, provider });
  }

  getProvider(name: string): Provider | null {
    return this.providers.get(name) || null;
  }

  async removeProvider(name: string): Promise<void> {
    const provider = this.providers.get(name);
    if (provider) {
      this.providers.delete(name);
      this.emit('provider:removed', { name, provider });
    }
  }

  setToolRegistry(registry: ToolRegistry): void {
    this.toolRegistry = registry;
    this.emit('component:registered', { type: 'toolRegistry', component: registry });
  }

  setPermissionManager(manager: PermissionManager): void {
    this.permissionManager = manager;
    this.emit('component:registered', { type: 'permissionManager', component: manager });
  }

  setConsciousnessEngine(engine: ConsciousnessEngine): void {
    this.consciousnessEngine = engine;
    this.emit('component:registered', { type: 'consciousnessEngine', component: engine });
  }

  setSATEngine(engine: SATEngine): void {
    this.satEngine = engine;
    this.emit('component:registered', { type: 'satEngine', component: engine });
  }

  async initialize(config?: Partial<ASICodeConfig>): Promise<void> {
    if (this.initialized) {
      this.emit('app:already_initialized');
      return;
    }

    if (config) {
      this.config = { ...this.config, ...config };
    }

    this.emit('app:initializing', { config: this.config });

    try {
      // Initialize components in order
      if (this.toolRegistry) {
        await this.toolRegistry.initialize?.(this.config);
        this.emit('component:initialized', { type: 'toolRegistry' });
      }

      if (this.permissionManager) {
        await this.permissionManager.initialize({});
        this.emit('component:initialized', { type: 'permissionManager' });
      }

      if (this.consciousnessEngine) {
        // Initialize with first available provider
        const provider = Array.from(this.providers.values())[0];
        if (provider) {
          await this.consciousnessEngine.initialize(provider);
        }
        this.emit('component:initialized', { type: 'consciousnessEngine' });
      }

      if (this.satEngine) {
        // SAT engine typically doesn't need initialization with providers
        this.emit('component:initialized', { type: 'satEngine' });
      }

      this.initialized = true;
      this.emit('app:initialized', { config: this.config });

    } catch (error) {
      this.emit('app:initialization_failed', { error, config: this.config });
      throw error;
    }
  }

  async shutdown(): Promise<void> {
    if (!this.initialized) {
      return;
    }

    this.emit('app:shutting_down');

    try {
      // Shutdown components in reverse order
      if (this.consciousnessEngine) {
        await this.consciousnessEngine.cleanup();
        this.emit('component:shutdown', { type: 'consciousnessEngine' });
      }

      if (this.satEngine) {
        await this.satEngine.cleanup();
        this.emit('component:shutdown', { type: 'satEngine' });
      }

      if (this.permissionManager) {
        await this.permissionManager.shutdown();
        this.emit('component:shutdown', { type: 'permissionManager' });
      }

      if (this.toolRegistry) {
        await this.toolRegistry.shutdown();
        this.emit('component:shutdown', { type: 'toolRegistry' });
      }

      // Clean up providers
      for (const [name, provider] of this.providers) {
        try {
          await provider.cleanup?.();
          this.emit('provider:shutdown', { name, provider });
        } catch (error) {
          this.emit('provider:shutdown_error', { name, provider, error });
        }
      }

      // Clear contexts
      this.kennyContexts.clear();
      this.providers.clear();

      this.initialized = false;
      this.emit('app:shutdown_complete');

    } catch (error) {
      this.emit('app:shutdown_error', { error });
      throw error;
    }
  }
}

/**
 * Factory function to create an app context
 */
export function createAppContext(config?: Partial<ASICodeConfig>): AppContext {
  return new DefaultAppContext(config);
}

/**
 * Global app context instance (singleton pattern)
 */
let globalAppContext: AppContext | null = null;

/**
 * Get or create the global app context
 */
export function getGlobalAppContext(config?: Partial<ASICodeConfig>): AppContext {
  if (!globalAppContext) {
    globalAppContext = createAppContext(config);
  }
  return globalAppContext;
}

/**
 * Reset the global app context (mainly for testing)
 */
export function resetGlobalAppContext(): void {
  if (globalAppContext && globalAppContext.initialized) {
    globalAppContext.shutdown();
  }
  globalAppContext = null;
}