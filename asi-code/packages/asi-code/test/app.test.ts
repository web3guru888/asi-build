/**
 * App Context and Lifecycle Manager Tests
 */

import { describe, it, expect, beforeEach, afterEach, mock } from 'bun:test';
import { 
  createAppContext, 
  createLifecycleManager,
  type AppContext,
  type LifecycleManager,
  type ASICodeConfig 
} from '../src/app/index.js';

describe('App Context', () => {
  let appContext: AppContext;

  beforeEach(() => {
    appContext = createAppContext();
  });

  afterEach(async () => {
    if (appContext.initialized) {
      await appContext.shutdown();
    }
  });

  it('should create app context with default config', () => {
    expect(appContext).toBeDefined();
    expect(appContext.config).toBeDefined();
    expect(appContext.initialized).toBe(false);
    expect(appContext.providers.size).toBe(0);
  });

  it('should create Kenny context', () => {
    const context = appContext.createKennyContext('test-session', 'test-user');
    
    expect(context).toBeDefined();
    expect(context.id).toMatch(/^ctx_/);
    expect(context.sessionId).toBe('test-session');
    expect(context.userId).toBe('test-user');
    expect(context.consciousness).toBeDefined();
    expect(context.permissions).toBeDefined();
    expect(context.metadata).toBeDefined();
  });

  it('should manage Kenny contexts', async () => {
    const context = appContext.createKennyContext('session1', 'user1');
    
    // Should be able to retrieve the context
    const retrieved = appContext.getKennyContext(context.id);
    expect(retrieved).toEqual(context);
    
    // Should be able to update the context
    await appContext.updateKennyContext(context.id, {
      metadata: { ...context.metadata, updated: true }
    });
    
    const updated = appContext.getKennyContext(context.id);
    expect(updated!.metadata.updated).toBe(true);
    expect(updated!.metadata.lastActive).toBeDefined();
    
    // Should be able to remove the context
    await appContext.removeKennyContext(context.id);
    const removed = appContext.getKennyContext(context.id);
    expect(removed).toBeNull();
  });

  it('should manage providers', async () => {
    const mockProvider = {
      name: 'test-provider',
      config: { name: 'test-provider', type: 'anthropic', apiKey: 'test', model: 'test' },
      cleanup: mock(async () => {})
    } as any;

    await appContext.registerProvider('test', mockProvider);
    
    expect(appContext.providers.size).toBe(1);
    expect(appContext.getProvider('test')).toBe(mockProvider);
    
    await appContext.removeProvider('test');
    expect(appContext.providers.size).toBe(0);
    expect(appContext.getProvider('test')).toBeNull();
  });

  it('should register components', () => {
    const mockToolRegistry = { name: 'test-registry' } as any;
    const mockPermissionManager = { name: 'test-permissions' } as any;
    const mockConsciousnessEngine = { name: 'test-consciousness' } as any;
    const mockSATEngine = { name: 'test-sat' } as any;

    appContext.setToolRegistry(mockToolRegistry);
    appContext.setPermissionManager(mockPermissionManager);
    appContext.setConsciousnessEngine(mockConsciousnessEngine);
    appContext.setSATEngine(mockSATEngine);

    expect(appContext.toolRegistry).toBe(mockToolRegistry);
    expect(appContext.permissionManager).toBe(mockPermissionManager);
    expect(appContext.consciousnessEngine).toBe(mockConsciousnessEngine);
    expect(appContext.satEngine).toBe(mockSATEngine);
  });

  it('should initialize and shutdown', async () => {
    let initializationEvents: string[] = [];
    
    appContext.on('app:initializing', () => initializationEvents.push('initializing'));
    appContext.on('app:initialized', () => initializationEvents.push('initialized'));
    appContext.on('app:shutting_down', () => initializationEvents.push('shutting_down'));
    appContext.on('app:shutdown_complete', () => initializationEvents.push('shutdown_complete'));

    const customConfig: Partial<ASICodeConfig> = {
      server: { port: 4000, host: '0.0.0.0' }
    };

    await appContext.initialize(customConfig);
    
    expect(appContext.initialized).toBe(true);
    expect(appContext.config.server.port).toBe(4000);
    expect(initializationEvents).toContain('initializing');
    expect(initializationEvents).toContain('initialized');

    await appContext.shutdown();
    
    expect(appContext.initialized).toBe(false);
    expect(initializationEvents).toContain('shutting_down');
    expect(initializationEvents).toContain('shutdown_complete');
  });

  it('should emit events for context operations', async () => {
    let events: any[] = [];
    
    appContext.on('context:created', (e) => events.push({ type: 'created', ...e }));
    appContext.on('context:updated', (e) => events.push({ type: 'updated', ...e }));
    appContext.on('context:removed', (e) => events.push({ type: 'removed', ...e }));

    const context = appContext.createKennyContext('session1', 'user1');
    await appContext.updateKennyContext(context.id, { metadata: { test: true } });
    await appContext.removeKennyContext(context.id);

    expect(events).toHaveLength(3);
    expect(events[0].type).toBe('created');
    expect(events[1].type).toBe('updated');
    expect(events[2].type).toBe('removed');
  });
});

describe('Lifecycle Manager', () => {
  let appContext: AppContext;
  let lifecycleManager: LifecycleManager;

  beforeEach(() => {
    appContext = createAppContext();
    lifecycleManager = createLifecycleManager(appContext);
  });

  afterEach(async () => {
    await lifecycleManager.cleanup();
  });

  it('should create lifecycle manager', () => {
    expect(lifecycleManager).toBeDefined();
    expect(lifecycleManager.appContext).toBe(appContext);
    expect(lifecycleManager.components.size).toBeGreaterThan(0); // Built-in components
  });

  it('should register custom components', () => {
    const mockFactory = mock(async (appContext) => ({ name: 'test-component' }));
    
    lifecycleManager.registerComponent('testComponent', ['eventBus'], mockFactory);
    
    const componentInfo = lifecycleManager.getComponentInfo('testComponent');
    expect(componentInfo).toBeDefined();
    expect(componentInfo!.name).toBe('testComponent');
    expect(componentInfo!.dependencies).toEqual(['eventBus']);
    expect(componentInfo!.state).toBe('uninitialized');
  });

  it('should start and stop components', async () => {
    let componentInstance: any = null;
    const mockFactory = mock(async (appContext) => {
      componentInstance = {
        name: 'test-component',
        start: mock(async () => {}),
        stop: mock(async () => {}),
        cleanup: mock(async () => {})
      };
      return componentInstance;
    });

    lifecycleManager.registerComponent('testComponent', [], mockFactory);
    
    // Start component
    await lifecycleManager.startComponent('testComponent');
    
    expect(lifecycleManager.getComponentState('testComponent')).toBe('running');
    expect(mockFactory).toHaveBeenCalledWith(appContext);
    expect(componentInstance.start).toHaveBeenCalled();

    // Stop component  
    await lifecycleManager.stopComponent('testComponent');
    
    expect(lifecycleManager.getComponentState('testComponent')).toBe('stopped');
    expect(componentInstance.stop).toHaveBeenCalled();
    expect(componentInstance.cleanup).toHaveBeenCalled();
  });

  it('should handle component dependencies', async () => {
    const instances: any[] = [];
    
    // Create dependency chain: A -> B -> C
    lifecycleManager.registerComponent('componentA', [], async () => {
      const instance = { name: 'A', start: mock(async () => {}) };
      instances.push(instance);
      return instance;
    });
    
    lifecycleManager.registerComponent('componentB', ['componentA'], async () => {
      const instance = { name: 'B', start: mock(async () => {}) };
      instances.push(instance);
      return instance;
    });
    
    lifecycleManager.registerComponent('componentC', ['componentB'], async () => {
      const instance = { name: 'C', start: mock(async () => {}) };
      instances.push(instance);
      return instance;
    });

    // Starting C should start A and B first
    await lifecycleManager.startComponent('componentC');
    
    expect(lifecycleManager.isComponentRunning('componentA')).toBe(true);
    expect(lifecycleManager.isComponentRunning('componentB')).toBe(true);
    expect(lifecycleManager.isComponentRunning('componentC')).toBe(true);
    
    // All components should be created and started
    expect(instances).toHaveLength(3);
    instances.forEach(instance => {
      expect(instance.start).toHaveBeenCalled();
    });
  });

  it('should detect circular dependencies', () => {
    lifecycleManager.registerComponent('compA', ['compB'], async () => ({}));
    lifecycleManager.registerComponent('compB', ['compC'], async () => ({}));
    lifecycleManager.registerComponent('compC', ['compA'], async () => ({}));

    expect(lifecycleManager.startComponent('compA')).rejects.toThrow('Circular dependency');
  });

  it('should start all components in correct order', async () => {
    const startOrder: string[] = [];
    
    // Create components with various dependencies
    lifecycleManager.registerComponent('root', [], async () => {
      startOrder.push('root');
      return { start: mock(async () => {}) };
    });
    
    lifecycleManager.registerComponent('child1', ['root'], async () => {
      startOrder.push('child1');
      return { start: mock(async () => {}) };
    });
    
    lifecycleManager.registerComponent('child2', ['root'], async () => {
      startOrder.push('child2');
      return { start: mock(async () => {}) };
    });
    
    lifecycleManager.registerComponent('grandchild', ['child1', 'child2'], async () => {
      startOrder.push('grandchild');
      return { start: mock(async () => {}) };
    });

    await lifecycleManager.startAll();
    
    // Root should start first
    expect(startOrder[0]).toBe('root');
    
    // Grandchild should start last
    expect(startOrder[startOrder.length - 1]).toBe('grandchild');
    
    // All components should be running
    expect(lifecycleManager.isComponentRunning('root')).toBe(true);
    expect(lifecycleManager.isComponentRunning('child1')).toBe(true);
    expect(lifecycleManager.isComponentRunning('child2')).toBe(true);
    expect(lifecycleManager.isComponentRunning('grandchild')).toBe(true);
  });

  it('should perform health checks', async () => {
    const healthyComponent = {
      start: mock(async () => {}),
      healthCheck: mock(async () => true)
    };
    
    const unhealthyComponent = {
      start: mock(async () => {}),
      healthCheck: mock(async () => false)
    };
    
    lifecycleManager.registerComponent('healthy', [], async () => healthyComponent);
    lifecycleManager.registerComponent('unhealthy', [], async () => unhealthyComponent);
    
    await lifecycleManager.startComponent('healthy');
    await lifecycleManager.startComponent('unhealthy');
    
    const healthResults = await lifecycleManager.performHealthCheck();
    
    expect(healthResults.get('healthy')).toBe(true);
    expect(healthResults.get('unhealthy')).toBe(false);
    expect(healthyComponent.healthCheck).toHaveBeenCalled();
    expect(unhealthyComponent.healthCheck).toHaveBeenCalled();
  });

  it('should emit lifecycle events', async () => {
    const events: any[] = [];
    
    lifecycleManager.on('lifecycle:starting_all', (e) => events.push({ type: 'starting_all', ...e }));
    lifecycleManager.on('lifecycle:all_started', (e) => events.push({ type: 'all_started', ...e }));
    lifecycleManager.on('component:started', (e) => events.push({ type: 'component_started', ...e }));

    await lifecycleManager.startAll();
    
    expect(events.some(e => e.type === 'starting_all')).toBe(true);
    expect(events.some(e => e.type === 'all_started')).toBe(true);
    expect(events.some(e => e.type === 'component_started')).toBe(true);
  });

  it('should handle component errors gracefully', async () => {
    const errorFactory = mock(async () => {
      throw new Error('Component initialization failed');
    });

    lifecycleManager.registerComponent('errorComponent', [], errorFactory);
    
    await expect(lifecycleManager.startComponent('errorComponent')).rejects.toThrow('Component initialization failed');
    
    const componentInfo = lifecycleManager.getComponentInfo('errorComponent');
    expect(componentInfo!.state).toBe('error');
    expect(componentInfo!.error).toBeDefined();
  });

  it('should restart components', async () => {
    let restartCount = 0;
    const restartableComponent = {
      start: mock(async () => { restartCount++; }),
      stop: mock(async () => {}),
      cleanup: mock(async () => {})
    };

    lifecycleManager.registerComponent('restartable', [], async () => restartableComponent);
    
    await lifecycleManager.startComponent('restartable');
    expect(restartCount).toBe(1);
    
    await lifecycleManager.restartComponent('restartable');
    expect(restartCount).toBe(2);
    expect(restartableComponent.stop).toHaveBeenCalled();
    expect(restartableComponent.cleanup).toHaveBeenCalled();
  });

  it('should get component information', () => {
    const allComponents = lifecycleManager.getAllComponents();
    expect(allComponents.length).toBeGreaterThan(0);
    
    const eventBusInfo = lifecycleManager.getComponentInfo('eventBus');
    expect(eventBusInfo).toBeDefined();
    expect(eventBusInfo!.name).toBe('eventBus');
    expect(eventBusInfo!.dependencies).toEqual([]);
  });
});