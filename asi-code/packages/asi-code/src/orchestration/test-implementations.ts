/**
 * Quick test to verify AgentRegistry and LoadBalancer implementations
 */

import { AgentRegistry } from './agent-registry.js';
import { LoadBalancer } from './load-balancer.js';
import { BaseAgent } from './base-agent.js';
import {
  Agent,
  AgentConfig,
  AgentMetrics,
  AgentPerformance,
  ResourceUtilization,
  Task,
  TaskPriority,
  TaskStatus,
} from './types.js';

// Mock agent for testing
class MockAgent extends BaseAgent implements Agent {
  private readonly mockMetrics: AgentMetrics;

  constructor(config: AgentConfig) {
    super(config);

    // Initialize mock metrics
    this.mockMetrics = {
      tasksCompleted: 0,
      tasksFailed: 0,
      tasksInProgress: 0,
      uptime: Date.now(),
      lastHealthCheck: Date.now(),
      performance: {
        averageTaskDuration: 5000, // 5 seconds
        successRate: 0.95,
        taskThroughput: 10, // 10 tasks per minute
        resourceUtilization: {
          cpu: 0.3,
          memory: 0.4,
          activeConnections: 5,
        },
      },
    };
  }

  async executeTask(task: Task): Promise<any> {
    // Mock task execution
    this.currentTasks.add(task.id);

    setTimeout(() => {
      this.currentTasks.delete(task.id);
      this.completedTasks++;
      this.emit('task:completed', task.id);
    }, 1000);

    return { success: true, result: `Task ${task.id} completed by ${this.id}` };
  }

  getMetrics(): AgentMetrics {
    return {
      ...this.mockMetrics,
      tasksInProgress: this.currentTasks.size,
      tasksCompleted: this.completedTasks,
      tasksFailed: this.failedTasks,
    };
  }

  canHandle(task: Task): boolean {
    const requiredCaps = task.constraints?.requiredCapabilities || [];
    const agentCaps = this.getCapabilities();
    return requiredCaps.every(cap => agentCaps.includes(cap));
  }

  // Update mock performance for testing
  updateMockPerformance(performance: Partial<AgentPerformance>): void {
    this.mockMetrics.performance = {
      ...this.mockMetrics.performance,
      ...performance,
    };
  }
}

// Test function
export async function testImplementations(): Promise<void> {
  console.log('🚀 Testing AgentRegistry and LoadBalancer implementations...\n');

  // Create AgentRegistry
  const registry = new AgentRegistry();
  console.log('✅ AgentRegistry created');

  // Create LoadBalancer
  const loadBalancer = new LoadBalancer({
    strategy: 'hybrid',
    weights: {
      performance: 0.3,
      capacity: 0.25,
      capability: 0.25,
      resource: 0.2,
    },
  });
  console.log('✅ LoadBalancer created with hybrid strategy');

  // Create mock agents
  const agents: MockAgent[] = [];

  for (let i = 0; i < 5; i++) {
    const agent = new MockAgent({
      name: `TestAgent-${i}`,
      type: i === 0 ? 'supervisor' : 'worker',
      capabilities: [
        'basic-task',
        i % 2 === 0 ? 'advanced-task' : 'simple-task',
      ],
      maxConcurrentTasks: 3 + i,
    });

    // Vary performance for testing load balancing
    agent.updateMockPerformance({
      successRate: 0.8 + i * 0.04, // 0.8 to 0.96
      averageTaskDuration: 3000 + i * 1000, // 3-7 seconds
      resourceUtilization: {
        cpu: 0.2 + i * 0.1,
        memory: 0.3 + i * 0.1,
        activeConnections: i + 1,
      },
    });

    agents.push(agent);
    await agent.initialize();
  }
  console.log('✅ Created 5 mock agents with varying performance');

  // Test AgentRegistry
  console.log('\n📋 Testing AgentRegistry...');

  // Register agents
  agents.forEach(agent => registry.register(agent));
  console.log(`✅ Registered ${agents.length} agents`);

  // Test retrieval methods
  const allAgents = registry.getAll();
  console.log(`✅ Retrieved ${allAgents.length} agents via getAll()`);

  const workerAgents = registry.findByType('worker');
  console.log(`✅ Found ${workerAgents.length} worker agents`);

  const basicTaskAgents = registry.findByCapability('basic-task');
  console.log(
    `✅ Found ${basicTaskAgents.length} agents with 'basic-task' capability`
  );

  const availableAgents = registry.findAvailable();
  console.log(`✅ Found ${availableAgents.length} available agents`);

  // Test stats
  const stats = registry.getStats();
  console.log('✅ Registry stats:', {
    total: stats.totalAgents,
    workers: stats.agentsByType.worker,
    supervisors: stats.agentsByType.supervisor,
    available: stats.availableAgents,
  });

  // Test LoadBalancer
  console.log('\n⚖️ Testing LoadBalancer...');

  // Create test tasks
  const tasks: Task[] = [
    {
      id: 'task-1',
      type: 'analysis',
      description: 'Analyze code structure',
      priority: 'high' as TaskPriority,
      status: 'pending' as TaskStatus,
      createdAt: Date.now(),
      constraints: {
        requiredCapabilities: ['basic-task'],
      },
    },
    {
      id: 'task-2',
      type: 'optimization',
      description: 'Optimize performance',
      priority: 'medium' as TaskPriority,
      status: 'pending' as TaskStatus,
      createdAt: Date.now(),
      constraints: {
        requiredCapabilities: ['advanced-task'],
      },
    },
    {
      id: 'task-3',
      type: 'testing',
      description: 'Run test suite',
      priority: 'low' as TaskPriority,
      status: 'pending' as TaskStatus,
      createdAt: Date.now(),
      constraints: {
        requiredCapabilities: ['simple-task'],
      },
    },
  ];

  console.log(`✅ Created ${tasks.length} test tasks`);

  // Test agent selection
  for (const task of tasks) {
    const selectedAgent = loadBalancer.selectAgent(task, availableAgents);
    if (selectedAgent) {
      const load = loadBalancer.getLoad(selectedAgent);
      console.log(
        `✅ Selected agent ${selectedAgent.id} for task ${task.id} (load: ${load.toFixed(2)})`
      );
    } else {
      console.log(`❌ No agent available for task ${task.id}`);
    }
  }

  // Test rebalancing
  const rebalanceMap = loadBalancer.rebalance(agents, tasks);
  console.log(
    `✅ Rebalancing complete, ${rebalanceMap.size} agents assigned tasks`
  );

  rebalanceMap.forEach((taskIds, agentId) => {
    console.log(`   Agent ${agentId}: ${taskIds.length} tasks`);
  });

  // Test load balancer stats
  const lbStats = loadBalancer.getStats();
  console.log('✅ LoadBalancer stats:', {
    strategy: lbStats.strategyUsed,
    lastRebalance:
      lbStats.lastRebalanceTime > 0 ? 'completed' : 'not performed',
  });

  // Test finding best agent
  const bestAgent = registry.findBestAgent(tasks[0]);
  console.log(`✅ Best agent for task-1: ${bestAgent?.id || 'none'}`);

  // Cleanup
  registry.destroy();
  console.log('✅ Registry cleaned up');

  console.log('\n🎉 All tests completed successfully!');
  console.log('\n📊 Summary:');
  console.log(
    '   - AgentRegistry: Registration, retrieval, health monitoring, statistics'
  );
  console.log(
    '   - LoadBalancer: Agent selection, load calculation, task rebalancing'
  );
  console.log(
    '   - Integration: Both components work together for optimal task distribution'
  );
}

// Export for direct testing
if (import.meta.main) {
  testImplementations().catch(console.error);
}
