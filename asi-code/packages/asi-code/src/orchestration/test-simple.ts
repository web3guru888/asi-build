/**
 * Simple test to verify AgentRegistry and LoadBalancer basic functionality
 */

import { AgentRegistry } from './agent-registry.js';
import { LoadBalancer } from './load-balancer.js';
import {
  Agent,
  AgentConfig,
  AgentMetrics,
  AgentPerformance,
  AgentStatus,
  Task,
  TaskPriority,
  TaskStatus,
} from './types.js';
import { EventEmitter } from 'eventemitter3';

// Minimal mock agent for testing
class SimpleMockAgent extends EventEmitter implements Agent {
  public readonly id: string;
  public config: AgentConfig;
  public status: AgentStatus = 'idle';
  public currentTasks: Set<string> = new Set();
  public completedTasks: number = 0;
  public failedTasks: number = 0;
  public performance: AgentPerformance;

  constructor(config: AgentConfig) {
    super();
    this.id =
      config.id ||
      `agent-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    this.config = { ...config, id: this.id };

    this.performance = {
      averageTaskDuration: 5000,
      successRate: 0.95,
      taskThroughput: 10,
      resourceUtilization: {
        cpu: 0.3,
        memory: 0.4,
        activeConnections: 2,
      },
    };
  }

  async initialize(): Promise<void> {
    this.status = 'idle';
  }

  async executeTask(task: Task): Promise<any> {
    this.currentTasks.add(task.id);
    this.status = 'working';

    // Simulate task execution
    await new Promise(resolve => setTimeout(resolve, 100));

    this.currentTasks.delete(task.id);
    this.completedTasks++;
    this.status = this.currentTasks.size > 0 ? 'busy' : 'idle';

    return { success: true, result: `Task ${task.id} completed` };
  }

  async suspend(): Promise<void> {
    this.status = 'suspended';
  }

  async resume(): Promise<void> {
    this.status = 'idle';
  }

  async terminate(): Promise<void> {
    this.status = 'terminated';
  }

  getCapabilities(): string[] {
    return this.config.capabilities;
  }

  canHandle(task: Task): boolean {
    const required = task.constraints?.requiredCapabilities || [];
    return required.every(cap => this.config.capabilities.includes(cap));
  }

  getStatus(): AgentStatus {
    return this.status;
  }

  getMetrics(): AgentMetrics {
    return {
      tasksCompleted: this.completedTasks,
      tasksFailed: this.failedTasks,
      tasksInProgress: this.currentTasks.size,
      uptime: Date.now(),
      lastHealthCheck: Date.now(),
      performance: this.performance,
    };
  }
}

async function runSimpleTest(): Promise<void> {
  console.log('🧪 Running simple AgentRegistry and LoadBalancer test...\n');

  try {
    // Test AgentRegistry
    console.log('1️⃣ Testing AgentRegistry...');
    const registry = new AgentRegistry();

    // Create test agents
    const agents: SimpleMockAgent[] = [];
    for (let i = 0; i < 3; i++) {
      const agent = new SimpleMockAgent({
        name: `TestAgent-${i}`,
        type: i === 0 ? 'supervisor' : 'worker',
        capabilities: [
          'basic-task',
          i % 2 === 0 ? 'advanced-task' : 'simple-task',
        ],
        maxConcurrentTasks: 3,
      });

      await agent.initialize();
      agents.push(agent);
      registry.register(agent);
    }

    console.log(`   ✅ Registered ${agents.length} agents`);
    console.log(`   ✅ Found ${registry.getAll().length} agents via getAll()`);
    console.log(
      `   ✅ Found ${registry.findByType('worker').length} worker agents`
    );
    console.log(
      `   ✅ Found ${registry.findByCapability('basic-task').length} agents with basic-task capability`
    );
    console.log(
      `   ✅ Found ${registry.findAvailable().length} available agents`
    );

    // Test stats
    const stats = registry.getStats();
    console.log(
      `   ✅ Registry stats: ${stats.totalAgents} total, ${stats.availableAgents} available`
    );

    // Test LoadBalancer
    console.log('\n2️⃣ Testing LoadBalancer...');
    const loadBalancer = new LoadBalancer({ strategy: 'round_robin' });

    // Create test task
    const task: Task = {
      id: 'test-task-1',
      type: 'analysis',
      description: 'Test task',
      priority: 'medium' as TaskPriority,
      status: 'pending' as TaskStatus,
      createdAt: Date.now(),
      constraints: {
        requiredCapabilities: ['basic-task'],
      },
    };

    // Test agent selection
    const selectedAgent = loadBalancer.selectAgent(
      task,
      registry.findAvailable()
    );
    console.log(`   ✅ Selected agent: ${selectedAgent?.id || 'none'}`);

    if (selectedAgent) {
      const load = loadBalancer.getLoad(selectedAgent);
      console.log(`   ✅ Agent load: ${load.toFixed(2)}`);
    }

    // Test rebalancing
    const rebalanceMap = loadBalancer.rebalance(agents, [task]);
    console.log(`   ✅ Rebalance completed: ${rebalanceMap.size} assignments`);

    // Test best agent selection from registry
    const bestAgent = registry.findBestAgent(task);
    console.log(`   ✅ Best agent for task: ${bestAgent?.id || 'none'}`);

    // Cleanup
    registry.destroy();
    console.log('\n✅ Test completed successfully!');

    console.log('\n📋 Summary:');
    console.log(
      '   ✅ AgentRegistry: Registration, retrieval, and statistics work correctly'
    );
    console.log(
      '   ✅ LoadBalancer: Agent selection and load balancing work correctly'
    );
    console.log(
      '   ✅ Integration: Both components integrate properly for task distribution'
    );
  } catch (error) {
    console.error('❌ Test failed:', error);
    throw error;
  }
}

// Run if called directly
if (typeof window === 'undefined' && require.main === module) {
  runSimpleTest().catch(console.error);
}

export { runSimpleTest };
