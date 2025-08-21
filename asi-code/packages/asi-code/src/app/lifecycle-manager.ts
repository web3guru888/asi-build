/**
 * Lifecycle Manager - Manages component lifecycle and dependencies
 * 
 * Handles the startup, shutdown, and coordination of all ASI-Code components
 * with proper dependency resolution and error handling.
 */

import { EventEmitter } from 'eventemitter3';
import type { AppContext } from './app-context.js';
import type { ASICodeConfig } from '../index.js';

export type ComponentState = 'uninitialized' | 'initializing' | 'initialized' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error';

export interface ComponentInfo {
  name: string;
  state: ComponentState;
  dependencies: string[];
  instance?: any;
  error?: Error;
  startedAt?: Date;
  stoppedAt?: Date;
}

export interface LifecycleManager extends EventEmitter {
  appContext: AppContext;
  components: Map<string, ComponentInfo>;
  
  // Component registration
  registerComponent(name: string, dependencies: string[], factory: (appContext: AppContext) => Promise<any>): void;
  unregisterComponent(name: string): void;
  
  // Lifecycle operations
  startAll(config?: Partial<ASICodeConfig>): Promise<void>;
  stopAll(): Promise<void>;
  restartAll(config?: Partial<ASICodeConfig>): Promise<void>;
  
  // Individual component operations
  startComponent(name: string): Promise<void>;
  stopComponent(name: string): Promise<void>;
  restartComponent(name: string): Promise<void>;
  
  // State queries
  getComponentState(name: string): ComponentState | null;
  getComponentInfo(name: string): ComponentInfo | null;
  isComponentRunning(name: string): boolean;
  getAllComponents(): ComponentInfo[];
  
  // Health checks
  performHealthCheck(): Promise<Map<string, boolean>>;
  
  // Cleanup
  cleanup(): Promise<void>;
}

export class DefaultLifecycleManager extends EventEmitter implements LifecycleManager {
  public appContext: AppContext;
  public components = new Map<string, ComponentInfo>();
  
  private componentFactories = new Map<string, (appContext: AppContext) => Promise<any>>();
  private startupOrder: string[] = [];
  private isShuttingDown = false;

  constructor(appContext: AppContext) {
    super();
    this.appContext = appContext;
    
    // Register built-in components
    this.registerBuiltInComponents();
    
    // Listen to app context events
    this.appContext.on('app:shutdown', () => {
      this.isShuttingDown = true;
    });
  }

  private registerBuiltInComponents(): void {
    // Core components in dependency order
    
    this.registerComponent('eventBus', [], async (appContext) => {
      const { createEventBus } = await import('../bus/index.js');
      return createEventBus();
    });

    this.registerComponent('configManager', [], async (appContext) => {
      const { createConfigManager } = await import('../config/index.js');
      return createConfigManager();
    });

    this.registerComponent('permissionManager', ['eventBus'], async (appContext) => {
      const { createPermissionManager } = await import('../permission/index.js');
      return createPermissionManager();
    });

    this.registerComponent('toolManager', ['permissionManager'], async (appContext) => {
      const { createToolManager } = await import('../tool/index.js');
      return createToolManager();
    });

    this.registerComponent('providerManager', ['permissionManager'], async (appContext) => {
      const { createProviderManager } = await import('../provider/index.js');
      return createProviderManager();
    });

    this.registerComponent('sessionStorage', ['eventBus'], async (appContext) => {
      const { createSessionStorage } = await import('../session/index.js');
      return createSessionStorage(appContext.config.storage.provider);
    });

    this.registerComponent('sessionManager', ['sessionStorage', 'eventBus'], async (appContext) => {
      const { createSessionManager } = await import('../session/index.js');
      const sessionStorage = this.components.get('sessionStorage')?.instance;
      return createSessionManager(sessionStorage);
    });

    this.registerComponent('consciousnessEngine', ['providerManager'], async (appContext) => {
      const { createConsciousnessEngine, defaultConsciousnessConfig } = await import('../consciousness/index.js');
      return createConsciousnessEngine({
        ...defaultConsciousnessConfig,
        ...appContext.config.consciousness
      });
    });

    this.registerComponent('agentManager', ['providerManager', 'toolManager'], async (appContext) => {
      const { createAgentManager } = await import('../agent/index.js');
      return createAgentManager();
    });

    this.registerComponent('satEngine', [], async (appContext) => {
      const { createSATEngine } = await import('../sat/index.js');
      return createSATEngine();
    });

    this.registerComponent('kennyIntegration', ['eventBus', 'permissionManager', 'toolManager'], async (appContext) => {
      const { createKennyIntegration } = await import('../kenny/index.js');
      const kenny = createKennyIntegration();
      await kenny.initialize(appContext.config.kenny);
      return kenny;
    });

    this.registerComponent('server', ['sessionManager', 'providerManager', 'toolManager'], async (appContext) => {
      const { createASIServer, defaultServerConfig } = await import('../server/index.js');
      const sessionManager = this.components.get('sessionManager')?.instance;
      const providerManager = this.components.get('providerManager')?.instance;
      const toolManager = this.components.get('toolManager')?.instance;
      
      return createASIServer({
        ...defaultServerConfig,
        ...appContext.config.server
      }, sessionManager, providerManager, toolManager);
    });
  }

  registerComponent(name: string, dependencies: string[], factory: (appContext: AppContext) => Promise<any>): void {
    if (this.components.has(name)) {
      throw new Error(`Component ${name} already registered`);
    }

    this.components.set(name, {
      name,
      state: 'uninitialized',
      dependencies: [...dependencies]
    });

    this.componentFactories.set(name, factory);
    this.emit('component:registered', { name, dependencies });
  }

  unregisterComponent(name: string): void {
    this.components.delete(name);
    this.componentFactories.delete(name);
    this.emit('component:unregistered', { name });
  }

  async startAll(config?: Partial<ASICodeConfig>): Promise<void> {
    if (this.isShuttingDown) {
      throw new Error('Cannot start components during shutdown');
    }

    this.emit('lifecycle:starting_all');

    try {
      // Initialize app context first
      await this.appContext.initialize(config);

      // Calculate startup order
      this.calculateStartupOrder();

      // Start components in dependency order
      for (const componentName of this.startupOrder) {
        await this.startComponent(componentName);
      }

      this.emit('lifecycle:all_started');
    } catch (error) {
      this.emit('lifecycle:startup_failed', { error });
      throw error;
    }
  }

  async stopAll(): Promise<void> {
    this.emit('lifecycle:stopping_all');

    try {
      // Stop components in reverse order
      const stopOrder = [...this.startupOrder].reverse();
      
      for (const componentName of stopOrder) {
        try {
          await this.stopComponent(componentName);
        } catch (error) {
          this.emit('component:stop_error', { name: componentName, error });
          // Continue stopping other components
        }
      }

      // Shutdown app context
      await this.appContext.shutdown();

      this.emit('lifecycle:all_stopped');
    } catch (error) {
      this.emit('lifecycle:stop_failed', { error });
      throw error;
    }
  }

  async restartAll(config?: Partial<ASICodeConfig>): Promise<void> {
    await this.stopAll();
    await this.startAll(config);
  }

  async startComponent(name: string): Promise<void> {
    const component = this.components.get(name);
    if (!component) {
      throw new Error(`Component ${name} not found`);
    }

    if (component.state === 'running') {
      return; // Already running
    }

    if (component.state === 'starting') {
      throw new Error(`Component ${name} is already starting`);
    }

    component.state = 'starting';
    this.emit('component:starting', { name });

    try {
      // Ensure dependencies are running
      for (const depName of component.dependencies) {
        const dep = this.components.get(depName);
        if (!dep || dep.state !== 'running') {
          await this.startComponent(depName);
        }
      }

      // Create component instance if needed
      if (!component.instance) {
        component.state = 'initializing';
        const factory = this.componentFactories.get(name);
        if (!factory) {
          throw new Error(`No factory registered for component ${name}`);
        }
        
        component.instance = await factory(this.appContext);
        component.state = 'initialized';
      }

      // Start the component if it has a start method
      if (component.instance?.start && typeof component.instance.start === 'function') {
        await component.instance.start();
      }

      component.state = 'running';
      component.startedAt = new Date();
      component.error = undefined;

      // Register with app context
      this.registerComponentWithAppContext(name, component.instance);

      this.emit('component:started', { name, component });

    } catch (error) {
      component.state = 'error';
      component.error = error as Error;
      this.emit('component:error', { name, error, component });
      throw error;
    }
  }

  async stopComponent(name: string): Promise<void> {
    const component = this.components.get(name);
    if (!component || !component.instance) {
      return; // Nothing to stop
    }

    if (component.state === 'stopped') {
      return; // Already stopped
    }

    component.state = 'stopping';
    this.emit('component:stopping', { name });

    try {
      // Stop the component if it has a stop method
      if (component.instance?.stop && typeof component.instance.stop === 'function') {
        await component.instance.stop();
      }

      // Cleanup if it has a cleanup method
      if (component.instance?.cleanup && typeof component.instance.cleanup === 'function') {
        await component.instance.cleanup();
      }

      component.state = 'stopped';
      component.stoppedAt = new Date();
      component.error = undefined;

      this.emit('component:stopped', { name, component });

    } catch (error) {
      component.state = 'error';
      component.error = error as Error;
      this.emit('component:error', { name, error, component });
      throw error;
    }
  }

  async restartComponent(name: string): Promise<void> {
    await this.stopComponent(name);
    await this.startComponent(name);
  }

  getComponentState(name: string): ComponentState | null {
    return this.components.get(name)?.state || null;
  }

  getComponentInfo(name: string): ComponentInfo | null {
    return this.components.get(name) || null;
  }

  isComponentRunning(name: string): boolean {
    return this.getComponentState(name) === 'running';
  }

  getAllComponents(): ComponentInfo[] {
    return Array.from(this.components.values());
  }

  async performHealthCheck(): Promise<Map<string, boolean>> {
    const results = new Map<string, boolean>();

    for (const [name, component] of this.components) {
      if (component.state === 'running' && component.instance) {
        try {
          if (component.instance.healthCheck && typeof component.instance.healthCheck === 'function') {
            const isHealthy = await component.instance.healthCheck();
            results.set(name, isHealthy);
          } else {
            // If no health check method, assume healthy if running
            results.set(name, true);
          }
        } catch (error) {
          results.set(name, false);
          this.emit('component:health_check_failed', { name, error });
        }
      } else {
        results.set(name, false);
      }
    }

    this.emit('lifecycle:health_check_completed', { results });
    return results;
  }

  private calculateStartupOrder(): void {
    const visited = new Set<string>();
    const visiting = new Set<string>();
    const order: string[] = [];

    const visit = (componentName: string) => {
      if (visiting.has(componentName)) {
        throw new Error(`Circular dependency detected involving ${componentName}`);
      }
      
      if (visited.has(componentName)) {
        return;
      }

      const component = this.components.get(componentName);
      if (!component) {
        throw new Error(`Component ${componentName} not found`);
      }

      visiting.add(componentName);

      for (const dep of component.dependencies) {
        visit(dep);
      }

      visiting.delete(componentName);
      visited.add(componentName);
      order.push(componentName);
    };

    for (const componentName of this.components.keys()) {
      visit(componentName);
    }

    this.startupOrder = order;
    this.emit('lifecycle:startup_order_calculated', { order });
  }

  private registerComponentWithAppContext(name: string, instance: any): void {
    switch (name) {
      case 'toolManager':
        this.appContext.setToolRegistry(instance);
        break;
      case 'permissionManager':
        this.appContext.setPermissionManager(instance);
        break;
      case 'consciousnessEngine':
        this.appContext.setConsciousnessEngine(instance);
        break;
      case 'satEngine':
        this.appContext.setSATEngine(instance);
        break;
    }
  }

  async cleanup(): Promise<void> {
    try {
      await this.stopAll();
    } catch (error) {
      this.emit('lifecycle:cleanup_error', { error });
    }

    this.components.clear();
    this.componentFactories.clear();
    this.startupOrder = [];
    this.removeAllListeners();
  }
}

/**
 * Factory function to create a lifecycle manager
 */
export function createLifecycleManager(appContext: AppContext): LifecycleManager {
  return new DefaultLifecycleManager(appContext);
}