/**
 * Agent Orchestration Performance Benchmarks
 * 
 * Tests the scalability and performance of the agent orchestration system
 * under various load conditions.
 */

import { bench, describe, beforeAll, afterAll } from 'vitest';
import { Orchestrator } from '../../src/orchestration/orchestrator.js';
import { Logger } from '../../src/logging/index.js';
import type { Task, AgentConfig } from '../../src/orchestration/types.js';

describe('Agent Orchestration Performance Benchmarks', () => {
  let orchestrator: Orchestrator;
  let logger: Logger;

  beforeAll(async () => {
    // Create logger with minimal output for benchmarks
    logger = new Logger({
      component: 'OrchestrationBenchmark',
      level: 'error' // Only show errors during benchmarks
    });

    // Create orchestrator
    orchestrator = new Orchestrator(logger);
    
    // Wait for initialization
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  afterAll(async () => {
    await orchestrator?.shutdown();
  });

  describe('Task Submission and Processing', () => {
    bench('Submit single task', async () => {
      const task: Task = {
        description: 'Process simple calculation',
        type: 'compute',
        priority: 'normal',
        input: { operation: 'add', values: [1, 2] }
      };

      const taskId = await orchestrator.submitTask(task);
      // Don't wait for completion in benchmark
    });

    bench('Submit 10 tasks concurrently', async () => {
      const tasks = Array.from({ length: 10 }, (_, i) => ({
        description: `Batch task ${i}`,
        type: 'compute',
        priority: 'normal' as const,
        input: { operation: 'multiply', values: [i, 2] }
      }));

      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });

    bench('Submit 50 tasks with mixed priorities', async () => {
      const priorities = ['low', 'normal', 'high', 'critical'] as const;
      
      const tasks = Array.from({ length: 50 }, (_, i) => ({
        description: `Mixed priority task ${i}`,
        type: 'process',
        priority: priorities[i % priorities.length],
        input: { data: `payload-${i}` }
      }));

      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });

    bench('Complex task decomposition', async () => {
      const complexTask: Task = {
        description: 'Analyze large dataset and generate report then send notifications and archive results',
        type: 'analysis',
        priority: 'normal',
        input: {
          dataset: Array.from({ length: 1000 }, (_, i) => ({ id: i, value: Math.random() }))
        },
        metadata: {
          decompose: true
        }
      };

      await orchestrator.submitTask(complexTask);
    });
  });

  describe('Agent Management and Scaling', () => {
    bench('Deploy single agent', async () => {
      const config: AgentConfig = {
        name: `Worker-${Date.now()}`,
        type: 'worker',
        capabilities: ['processing', 'computation'],
        maxConcurrentTasks: 3
      };

      const agent = await orchestrator.deployAgent(config);
      // Keep agent for other tests
    });

    bench('Deploy 5 agents concurrently', async () => {
      const configs = Array.from({ length: 5 }, (_, i) => ({
        name: `ConcurrentWorker-${i}-${Date.now()}`,
        type: 'worker' as const,
        capabilities: ['processing', 'io'],
        maxConcurrentTasks: 2
      }));

      const promises = configs.map(config => orchestrator.deployAgent(config));
      await Promise.all(promises);
    });

    bench('Scale agents to target count', async () => {
      const currentAgents = orchestrator.agentRegistry.findByType('worker');
      const targetCount = currentAgents.length + 3;
      
      await orchestrator.scaleAgents(targetCount, 'worker');
    });

    bench('Auto-scaling simulation', async () => {
      // Simulate system overload condition
      const overloadTasks = Array.from({ length: 20 }, (_, i) => ({
        description: `Overload task ${i}`,
        type: 'heavy-compute',
        priority: 'normal' as const,
        input: { load: 'high' }
      }));

      // Submit all tasks to trigger auto-scaling
      const promises = overloadTasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });
  });

  describe('System Monitoring and Metrics', () => {
    bench('Get system status', async () => {
      const status = orchestrator.getSystemStatus();
      // Status should include health, counts, load, etc.
    });

    bench('Get orchestrator metrics', async () => {
      const metrics = orchestrator.getMetrics();
      // Metrics include throughput, utilization, etc.
    });

    bench('Get agent statuses (bulk)', async () => {
      const statuses = orchestrator.getAgentStatuses();
      // Should return status for all agents
    });

    bench('Get task statuses (bulk)', async () => {
      const statuses = orchestrator.getTaskStatuses();
      // Should return status for all tasks
    });

    bench('Monitor system health', async () => {
      const isHealthy = orchestrator.getSystemStatus().healthy;
      const metrics = orchestrator.getMetrics();
      
      // Simulate health check logic
      const healthCheck = {
        system: isHealthy,
        errorRate: metrics.errorRate < 10,
        utilization: metrics.agentUtilization < 90,
        queueDepth: metrics.queueDepth < 100
      };
    });
  });

  describe('Supervisor Operations', () => {
    bench('Create supervisor', async () => {
      const config: AgentConfig = {
        name: `Supervisor-${Date.now()}`,
        type: 'supervisor',
        capabilities: ['task-decomposition', 'agent-management'],
        maxConcurrentTasks: 50,
        metadata: {
          initialWorkers: 2
        }
      };

      await orchestrator.createSupervisor(config);
    });

    bench('Supervisor task assignment', async () => {
      const tasks = Array.from({ length: 10 }, (_, i) => ({
        description: `Supervisor task ${i}`,
        type: 'coordinate',
        priority: 'normal' as const,
        input: { coordination: true }
      }));

      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });
  });

  describe('Load Testing Scenarios', () => {
    bench('Sustained load test (100 tasks)', async () => {
      const tasks = Array.from({ length: 100 }, (_, i) => ({
        description: `Load test task ${i}`,
        type: 'standard',
        priority: 'normal' as const,
        input: { index: i, timestamp: Date.now() }
      }));

      const batchSize = 10;
      const batches = [];
      
      for (let i = 0; i < tasks.length; i += batchSize) {
        batches.push(tasks.slice(i, i + batchSize));
      }

      // Submit in batches to avoid overwhelming the system
      for (const batch of batches) {
        const promises = batch.map(task => orchestrator.submitTask(task));
        await Promise.all(promises);
        
        // Small delay between batches
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    });

    bench('Burst load test (50 concurrent)', async () => {
      const tasks = Array.from({ length: 50 }, (_, i) => ({
        description: `Burst task ${i}`,
        type: 'burst',
        priority: 'high' as const,
        input: { burst: true, index: i }
      }));

      // Submit all at once
      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });

    bench('Mixed workload simulation', async () => {
      const taskTypes = ['compute', 'io', 'analysis', 'coordination', 'validation'];
      const priorities = ['low', 'normal', 'high'] as const;
      
      const tasks = Array.from({ length: 30 }, (_, i) => ({
        description: `Mixed workload task ${i}`,
        type: taskTypes[i % taskTypes.length],
        priority: priorities[i % priorities.length],
        input: {
          type: taskTypes[i % taskTypes.length],
          complexity: Math.random() > 0.7 ? 'high' : 'normal',
          data: `payload-${i}`
        }
      }));

      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });
  });

  describe('Edge Cases and Stress Tests', () => {
    bench('Task cancellation under load', async () => {
      // Submit several tasks
      const tasks = Array.from({ length: 5 }, (_, i) => ({
        description: `Cancellation test task ${i}`,
        type: 'long-running',
        priority: 'normal' as const,
        input: { duration: 5000 }
      }));

      const taskIds = await Promise.all(
        tasks.map(task => orchestrator.submitTask(task))
      );

      // Cancel some tasks
      await orchestrator.cancelTask(taskIds[0]);
      await orchestrator.cancelTask(taskIds[2]);
    });

    bench('Agent termination during load', async () => {
      // Deploy a temporary agent
      const tempAgent = await orchestrator.deployAgent({
        name: `TempAgent-${Date.now()}`,
        type: 'worker',
        capabilities: ['testing'],
        maxConcurrentTasks: 1
      });

      // Submit task
      await orchestrator.submitTask({
        description: 'Task for temporary agent',
        type: 'test',
        priority: 'normal',
        input: { test: true }
      });

      // Terminate agent
      await orchestrator.terminateAgent(tempAgent.id);
    });

    bench('System recovery after supervisor failure', async () => {
      // Get current supervisor count
      const initialSupervisors = orchestrator.supervisors.size;

      // Create additional supervisor
      const backupSupervisor = await orchestrator.createSupervisor({
        name: `BackupSupervisor-${Date.now()}`,
        type: 'supervisor',
        capabilities: ['task-decomposition', 'agent-management'],
        maxConcurrentTasks: 20
      });

      // Submit tasks to test system resilience
      const tasks = Array.from({ length: 10 }, (_, i) => ({
        description: `Recovery test task ${i}`,
        type: 'resilience',
        priority: 'normal' as const,
        input: { test: 'recovery' }
      }));

      const promises = tasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });

    bench('Memory pressure simulation', async () => {
      // Create many small tasks to test memory usage
      const memoryTasks = Array.from({ length: 200 }, (_, i) => ({
        description: `Memory test task ${i}`,
        type: 'memory-test',
        priority: 'low' as const,
        input: {
          data: Array.from({ length: 100 }, (_, j) => `item-${j}`),
          index: i
        }
      }));

      // Submit in small batches
      const batchSize = 20;
      for (let i = 0; i < memoryTasks.length; i += batchSize) {
        const batch = memoryTasks.slice(i, i + batchSize);
        const promises = batch.map(task => orchestrator.submitTask(task));
        await Promise.all(promises);
        
        // Brief pause
        await new Promise(resolve => setTimeout(resolve, 5));
      }
    });
  });

  describe('Performance Optimization Tests', () => {
    bench('Task queue optimization', async () => {
      // Submit tasks with various priorities to test queue management
      const highPriorityTasks = Array.from({ length: 5 }, (_, i) => ({
        description: `High priority task ${i}`,
        type: 'urgent',
        priority: 'critical' as const,
        input: { urgent: true }
      }));

      const normalTasks = Array.from({ length: 15 }, (_, i) => ({
        description: `Normal task ${i}`,
        type: 'standard',
        priority: 'normal' as const,
        input: { standard: true }
      }));

      // Submit normal tasks first
      await Promise.all(normalTasks.map(task => orchestrator.submitTask(task)));
      
      // Then submit high priority (should be processed first)
      await Promise.all(highPriorityTasks.map(task => orchestrator.submitTask(task)));
    });

    bench('Agent utilization optimization', async () => {
      // Get current system metrics
      const initialMetrics = orchestrator.getMetrics();
      
      // Calculate optimal agent count based on current load
      const currentUtilization = initialMetrics.agentUtilization;
      const targetUtilization = 75; // Target 75% utilization
      
      if (currentUtilization < targetUtilization - 10) {
        // Scale down if underutilized
        const currentAgents = orchestrator.agentRegistry.findByType('worker');
        const targetCount = Math.max(1, Math.floor(currentAgents.length * 0.8));
        await orchestrator.scaleAgents(targetCount, 'worker');
      } else if (currentUtilization > targetUtilization + 10) {
        // Scale up if overutilized
        const currentAgents = orchestrator.agentRegistry.findByType('worker');
        const targetCount = Math.ceil(currentAgents.length * 1.2);
        await orchestrator.scaleAgents(targetCount, 'worker');
      }
    });

    bench('Parallel task processing', async () => {
      // Create tasks that can be processed in parallel
      const parallelTasks = Array.from({ length: 20 }, (_, i) => ({
        description: `Parallel task ${i}`,
        type: 'parallel',
        priority: 'normal' as const,
        input: {
          canParallelize: true,
          index: i,
          data: `parallel-${i}`
        }
      }));

      // Submit all tasks simultaneously for maximum parallelism
      const promises = parallelTasks.map(task => orchestrator.submitTask(task));
      await Promise.all(promises);
    });
  });
});