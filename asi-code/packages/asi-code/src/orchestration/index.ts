/**
 * ASI-Code Agent Orchestration System
 * 
 * Export main orchestration components and utilities
 */

// Core Orchestrator
export { Orchestrator, createOrchestrator } from './orchestrator.js';

// Agents
export { BaseAgent } from './base-agent.js';
export { SupervisorAgent } from './supervisor-agent.js';
export { WorkerAgent } from './worker-agent.js';

// Task Management
export { TaskDecomposer } from './task-decomposer.js';
export { TaskQueue } from './task-queue.js';

// Agent Management
export { AgentRegistry } from './agent-registry.js';
export { LoadBalancer } from './load-balancer.js';

// Agent Factory
export { 
  AgentFactory, 
  defaultAgentFactory, 
  createAgent, 
  createFromTemplate,
  type AgentTemplate,
  type AgentPoolConfig,
  type DependencyContainer,
  type AgentCreationOptions
} from './agent-factory.js';

// Task Builder
export { 
  TaskBuilder, 
  WorkflowBuilder,
  createTask,
  createTaskFromTemplate,
  createTaskBatch,
  createTaskPipeline,
  type TaskTemplate,
  type WorkflowConfig,
  type SubtaskConfig
} from './task-builder.js';

// Communication & Coordination
export { MessageBus, getOrchestrationMessageBus, resetOrchestrationMessageBus } from './message-bus.js';
export { OrchestrationCoordinationProtocol, getCoordinationProtocol, resetCoordinationProtocol } from './coordination-protocol.js';

// Types
export * from './types.js';

/**
 * Quick start function to create a fully configured orchestration system
 */
export async function createOrchestrationSystem(config?: {
  supervisors?: number;
  workersPerSupervisor?: number;
  logger?: any;
}) {
  const { Orchestrator } = await import('./orchestrator.js');
  const orchestrator = new Orchestrator(config?.logger);
  
  // Create additional supervisors if requested
  const supervisorCount = config?.supervisors || 1;
  for (let i = 1; i < supervisorCount; i++) {
    await orchestrator.createSupervisor({
      name: `Supervisor-${i}`,
      type: 'supervisor',
      capabilities: ['task-decomposition', 'agent-management'],
      maxConcurrentTasks: 100,
      metadata: {
        initialWorkers: config?.workersPerSupervisor || 3
      }
    });
  }
  
  return orchestrator;
}

/**
 * Example usage of the orchestration system
 */
export const ORCHESTRATION_EXAMPLE = `
import { createOrchestrationSystem } from './orchestration';

// Create orchestration system
const orchestrator = await createOrchestrationSystem({
  supervisors: 2,
  workersPerSupervisor: 5
});

// Submit a complex task
const taskId = await orchestrator.submitTask({
  id: 'build-project',
  type: 'build',
  description: 'Build the entire ASI-Code project',
  priority: 'high',
  status: 'pending',
  createdAt: Date.now(),
  metadata: {
    decompose: true // Will be broken down into subtasks
  }
});

// Get task result
const result = await orchestrator.getTaskResult(taskId);
console.log('Build result:', result);

// Scale agents based on load
await orchestrator.scaleAgents(10, 'worker');

// Get system status
const status = orchestrator.getSystemStatus();
console.log('System status:', status);

// Deploy specialized agent
const specialist = await orchestrator.deployAgent({
  name: 'Code-Analyzer',
  type: 'specialist',
  capabilities: ['code-analysis', 'optimization'],
  maxConcurrentTasks: 2
});

// Submit task directly to specialist
const analysisTaskId = await orchestrator.submitTask({
  type: 'analysis',
  description: 'Analyze codebase for optimization opportunities',
  priority: 'medium',
  status: 'pending',
  createdAt: Date.now(),
  constraints: {
    preferredAgent: specialist.id,
    requiredCapabilities: ['code-analysis']
  }
});
`;