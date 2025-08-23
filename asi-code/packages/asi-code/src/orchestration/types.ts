/**
 * ASI-Code Agent Orchestration System Types
 *
 * Core type definitions for the agent orchestration framework
 * that enables supervisor agents, task decomposition, and
 * parallel agent deployment.
 */

import { EventEmitter } from 'eventemitter3';

// Agent Types
export type AgentType =
  | 'supervisor'
  | 'worker'
  | 'specialist'
  | 'coordinator'
  | 'analyzer'
  | 'executor'
  | 'monitor'
  | 'validator';

export type AgentStatus =
  | 'idle'
  | 'busy'
  | 'working'
  | 'waiting'
  | 'error'
  | 'terminated'
  | 'suspended';

export type TaskStatus =
  | 'pending'
  | 'assigned'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'decomposing';

export type TaskPriority = 'critical' | 'high' | 'medium' | 'low';

// Agent Configuration
export interface AgentConfig {
  id?: string;
  name: string;
  type: AgentType;
  capabilities: string[];
  maxConcurrentTasks: number;
  timeout?: number;
  retryPolicy?: RetryPolicy;
  resources?: ResourceRequirements;
  metadata?: Record<string, any>;
}

export interface RetryPolicy {
  maxRetries: number;
  backoffMultiplier: number;
  initialDelay: number;
  maxDelay: number;
}

export interface ResourceRequirements {
  cpu?: number;
  memory?: number;
  disk?: number;
  network?: boolean;
  gpu?: boolean;
}

// Task Definitions
export interface Task {
  id: string;
  type: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  dependencies?: string[];
  input?: any;
  output?: any;
  constraints?: TaskConstraints;
  assignedAgent?: string;
  parentTask?: string;
  subtasks?: string[];
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  error?: Error;
  metadata?: Record<string, any>;
}

export interface TaskConstraints {
  requiredCapabilities?: string[];
  maxExecutionTime?: number;
  requiredResources?: ResourceRequirements;
  preferredAgent?: string;
  parallelizable?: boolean;
}

export interface TaskDecomposition {
  originalTask: Task;
  subtasks: Task[];
  dependencies: TaskDependency[];
  executionPlan: ExecutionPlan;
}

export interface TaskDependency {
  from: string;
  to: string;
  type: 'blocking' | 'soft' | 'optional';
}

export interface ExecutionPlan {
  phases: ExecutionPhase[];
  estimatedDuration: number;
  parallelismLevel: number;
  criticalPath: string[];
}

export interface ExecutionPhase {
  id: string;
  tasks: string[];
  parallel: boolean;
  estimatedDuration: number;
}

// Agent Instance
export interface Agent extends EventEmitter {
  id: string;
  config: AgentConfig;
  status: AgentStatus;
  currentTasks: Set<string>;
  completedTasks: number;
  failedTasks: number;
  performance: AgentPerformance;

  // Core methods
  initialize(): Promise<void>;
  executeTask(task: Task): Promise<any>;
  suspend(): Promise<void>;
  resume(): Promise<void>;
  terminate(): Promise<void>;
  getCapabilities(): string[];
  canHandle(task: Task): boolean;
  getStatus(): AgentStatus;
  getMetrics(): AgentMetrics;
}

export interface AgentPerformance {
  averageTaskDuration: number;
  successRate: number;
  taskThroughput: number;
  lastTaskCompletedAt?: number;
  resourceUtilization: ResourceUtilization;
}

export interface ResourceUtilization {
  cpu: number;
  memory: number;
  activeConnections: number;
}

export interface AgentMetrics {
  tasksCompleted: number;
  tasksFailed: number;
  tasksInProgress: number;
  uptime: number;
  lastHealthCheck: number;
  performance: AgentPerformance;
}

// Supervisor Agent
export interface SupervisorAgent extends Agent {
  managedAgents: Map<string, Agent>;
  taskQueue: TaskQueue;

  deployAgent(config: AgentConfig): Promise<Agent>;
  decommissionAgent(agentId: string): Promise<void>;
  assignTask(task: Task, agentId?: string): Promise<void>;
  decomposeTask(task: Task): Promise<TaskDecomposition>;
  coordinateAgents(): Promise<void>;
  rebalanceTasks(): Promise<void>;
  handleAgentFailure(agentId: string): Promise<void>;
}

// Task Queue
export interface TaskQueue {
  add(task: Task): void;
  remove(taskId: string): boolean;
  get(taskId: string): Task | undefined;
  getNext(): Task | undefined;
  getPending(): Task[];
  getByPriority(priority: TaskPriority): Task[];
  size(): number;
  clear(): void;
}

// Communication Protocol
export interface AgentMessage {
  id: string;
  from: string;
  to: string;
  type: MessageType;
  payload: any;
  timestamp: number;
  correlationId?: string;
  replyTo?: string;
}

export type MessageType =
  | 'task_assignment'
  | 'task_result'
  | 'task_progress'
  | 'status_update'
  | 'capability_query'
  | 'coordination'
  | 'health_check'
  | 'resource_request'
  | 'error'
  | 'terminate';

// Orchestrator
export interface Orchestrator extends EventEmitter {
  supervisors: Map<string, SupervisorAgent>;
  agents: Map<string, Agent>;
  taskRegistry: Map<string, Task>;

  // Core orchestration methods
  createSupervisor(config: AgentConfig): Promise<SupervisorAgent>;
  submitTask(task: Task): Promise<string>;
  getTaskStatus(taskId: string): TaskStatus | undefined;
  getTaskResult(taskId: string): Promise<any>;
  cancelTask(taskId: string): Promise<boolean>;

  // Agent management
  deployAgent(config: AgentConfig, supervisorId?: string): Promise<Agent>;
  scaleAgents(targetCount: number, type?: AgentType): Promise<void>;
  terminateAgent(agentId: string): Promise<void>;

  // Monitoring
  getSystemStatus(): SystemStatus;
  getAgentStatuses(): Map<string, AgentStatus>;
  getTaskStatuses(): Map<string, TaskStatus>;
  getMetrics(): OrchestratorMetrics;
}

export interface SystemStatus {
  healthy: boolean;
  supervisorCount: number;
  agentCount: number;
  activeTasks: number;
  completedTasks: number;
  failedTasks: number;
  queuedTasks: number;
  systemLoad: number;
  uptime: number;
}

export interface OrchestratorMetrics {
  taskThroughput: number;
  averageTaskDuration: number;
  agentUtilization: number;
  queueDepth: number;
  successRate: number;
  errorRate: number;
}

// Agent Registry
export interface AgentRegistry {
  register(agent: Agent): void;
  unregister(agentId: string): void;
  get(agentId: string): Agent | undefined;
  findByCapability(capability: string): Agent[];
  findByType(type: AgentType): Agent[];
  findAvailable(): Agent[];
  getAll(): Agent[];
}

// Load Balancer
export interface LoadBalancer {
  selectAgent(task: Task, agents: Agent[]): Agent | undefined;
  getLoad(agent: Agent): number;
  rebalance(agents: Agent[], tasks: Task[]): Map<string, string[]>;
}

// Task Decomposer
export interface TaskDecomposer {
  canDecompose(task: Task): boolean;
  decompose(task: Task): Promise<TaskDecomposition>;
  analyzeDependencies(tasks: Task[]): TaskDependency[];
  createExecutionPlan(
    tasks: Task[],
    dependencies: TaskDependency[]
  ): ExecutionPlan;
  estimateDuration(task: Task): number;
}

// Coordination Protocol
export interface CoordinationProtocol {
  electLeader(agents: Agent[]): Agent;
  synchronize(agents: Agent[]): Promise<void>;
  broadcast(message: AgentMessage, agents: Agent[]): Promise<void>;
  consensus(proposal: any, agents: Agent[]): Promise<boolean>;
}

// Events
export interface OrchestrationEvents {
  'agent:deployed': (agent: Agent) => void;
  'agent:terminated': (agentId: string) => void;
  'agent:status_changed': (agentId: string, status: AgentStatus) => void;
  'task:submitted': (task: Task) => void;
  'task:assigned': (taskId: string, agentId: string) => void;
  'task:completed': (taskId: string, result: any) => void;
  'task:failed': (taskId: string, error: Error) => void;
  'task:decomposed': (taskId: string, subtasks: Task[]) => void;
  'supervisor:created': (supervisor: SupervisorAgent) => void;
  'system:overloaded': (load: number) => void;
  'system:recovered': () => void;
}
