/**
 * Task Decomposition Engine
 *
 * Intelligent task decomposition system that analyzes complex tasks
 * and breaks them down into manageable subtasks with dependencies.
 */

import {
  ExecutionPhase,
  ExecutionPlan,
  TaskDecomposer as ITaskDecomposer,
  Task,
  TaskDecomposition,
  TaskDependency,
  TaskPriority,
} from './types.js';
import { v4 as uuidv4 } from 'uuid';

export class TaskDecomposer implements ITaskDecomposer {
  private readonly decompositionStrategies: Map<string, DecompositionStrategy>;
  private readonly taskTemplates: Map<string, TaskTemplate>;

  constructor() {
    this.decompositionStrategies = new Map();
    this.taskTemplates = new Map();
    this.registerDefaultStrategies();
    this.registerDefaultTemplates();
  }

  /**
   * Check if a task can be decomposed
   */
  canDecompose(task: Task): boolean {
    // Check if task type supports decomposition
    if (this.decompositionStrategies.has(task.type)) {
      return true;
    }

    // Check if task has explicit subtasks defined
    if (task.metadata?.decomposable === true) {
      return true;
    }

    // Check task complexity indicators
    const complexityScore = this.calculateComplexity(task);
    return complexityScore > 5; // Threshold for decomposition
  }

  /**
   * Decompose a complex task into subtasks
   */
  async decompose(task: Task): Promise<TaskDecomposition> {
    // Get appropriate decomposition strategy
    const strategy = this.getStrategy(task.type) || this.getDefaultStrategy();

    // Apply strategy to decompose task
    const subtasks = await strategy.decompose(task);

    // Analyze dependencies between subtasks
    const dependencies = this.analyzeDependencies(subtasks);

    // Create execution plan
    const executionPlan = this.createExecutionPlan(subtasks, dependencies);

    // Link subtasks to parent
    subtasks.forEach(subtask => {
      subtask.parentTask = task.id;
    });

    // Update parent task with subtask IDs
    task.subtasks = subtasks.map(st => st.id);
    task.status = 'decomposing';

    return {
      originalTask: task,
      subtasks,
      dependencies,
      executionPlan,
    };
  }

  /**
   * Analyze dependencies between tasks
   */
  analyzeDependencies(tasks: Task[]): TaskDependency[] {
    const dependencies: TaskDependency[] = [];

    // Check explicit dependencies
    tasks.forEach(task => {
      if (task.dependencies) {
        task.dependencies.forEach(depId => {
          if (tasks.find(t => t.id === depId)) {
            dependencies.push({
              from: depId,
              to: task.id,
              type: 'blocking',
            });
          }
        });
      }
    });

    // Infer dependencies based on data flow
    this.inferDataDependencies(tasks, dependencies);

    // Detect resource conflicts
    this.detectResourceConflicts(tasks, dependencies);

    // Validate no circular dependencies
    if (this.hasCircularDependencies(dependencies)) {
      throw new Error('Circular dependencies detected in task decomposition');
    }

    return dependencies;
  }

  /**
   * Create execution plan for tasks
   */
  createExecutionPlan(
    tasks: Task[],
    dependencies: TaskDependency[]
  ): ExecutionPlan {
    const phases: ExecutionPhase[] = [];
    const scheduled = new Set<string>();
    const taskMap = new Map(tasks.map(t => [t.id, t]));

    // Build dependency graph
    const dependencyGraph = this.buildDependencyGraph(dependencies);

    // Topological sort to determine execution order
    const executionOrder = this.topologicalSort(tasks, dependencyGraph);

    // Group tasks into phases
    let currentPhase: ExecutionPhase | null = null;
    let phaseIndex = 0;

    for (const taskGroup of executionOrder) {
      currentPhase = {
        id: `phase-${phaseIndex++}`,
        tasks: taskGroup,
        parallel: taskGroup.length > 1,
        estimatedDuration: Math.max(
          ...taskGroup.map(id => this.estimateDuration(taskMap.get(id)!))
        ),
      };
      phases.push(currentPhase);
      taskGroup.forEach(id => scheduled.add(id));
    }

    // Calculate critical path
    const criticalPath = this.calculateCriticalPath(tasks, dependencies);

    // Calculate total estimated duration
    const estimatedDuration = phases.reduce(
      (sum, phase) => sum + phase.estimatedDuration,
      0
    );

    // Determine parallelism level
    const parallelismLevel = Math.max(...phases.map(p => p.tasks.length));

    return {
      phases,
      estimatedDuration,
      parallelismLevel,
      criticalPath,
    };
  }

  /**
   * Estimate task duration
   */
  estimateDuration(task: Task): number {
    // Check if task has explicit duration estimate
    if (task.constraints?.maxExecutionTime) {
      return task.constraints.maxExecutionTime * 0.7; // Conservative estimate
    }

    // Use historical data if available
    const historicalDuration = this.getHistoricalDuration(task.type);
    if (historicalDuration) {
      return historicalDuration;
    }

    // Default estimates based on task type
    const typeEstimates: Record<string, number> = {
      analysis: 5000,
      processing: 10000,
      validation: 3000,
      computation: 15000,
      io: 2000,
      network: 8000,
      default: 5000,
    };

    return typeEstimates[task.type] || typeEstimates.default;
  }

  /**
   * Calculate task complexity score
   */
  private calculateComplexity(task: Task): number {
    let score = 0;

    // Check description length
    if (task.description.length > 200) score += 2;
    if (task.description.length > 500) score += 3;

    // Check for multiple operations
    const operations = task.description.match(
      /\b(and|then|after|before|while)\b/gi
    );
    if (operations) score += operations.length;

    // Check for dependencies
    if (task.dependencies && task.dependencies.length > 0) {
      score += task.dependencies.length * 2;
    }

    // Check input complexity
    if (task.input) {
      const inputSize = JSON.stringify(task.input).length;
      if (inputSize > 1000) score += 3;
      if (inputSize > 5000) score += 5;
    }

    // Check constraints
    if (task.constraints?.requiredCapabilities) {
      score += task.constraints.requiredCapabilities.length;
    }

    return score;
  }

  /**
   * Infer data dependencies between tasks
   */
  private inferDataDependencies(
    tasks: Task[],
    dependencies: TaskDependency[]
  ): void {
    tasks.forEach((task, i) => {
      tasks.slice(i + 1).forEach(otherTask => {
        // Check if output of one task feeds into another
        if (this.hasDataFlow(task, otherTask)) {
          dependencies.push({
            from: task.id,
            to: otherTask.id,
            type: 'blocking',
          });
        }
      });
    });
  }

  /**
   * Detect resource conflicts between tasks
   */
  private detectResourceConflicts(
    tasks: Task[],
    dependencies: TaskDependency[]
  ): void {
    tasks.forEach((task, i) => {
      tasks.slice(i + 1).forEach(otherTask => {
        if (this.hasResourceConflict(task, otherTask)) {
          // Add soft dependency to prevent concurrent execution
          dependencies.push({
            from: task.id,
            to: otherTask.id,
            type: 'soft',
          });
        }
      });
    });
  }

  /**
   * Check for circular dependencies
   */
  private hasCircularDependencies(dependencies: TaskDependency[]): boolean {
    const graph = this.buildDependencyGraph(dependencies);
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    for (const node of graph.keys()) {
      if (this.hasCycle(node, graph, visited, recursionStack)) {
        return true;
      }
    }

    return false;
  }

  private hasCycle(
    node: string,
    graph: Map<string, Set<string>>,
    visited: Set<string>,
    recursionStack: Set<string>
  ): boolean {
    visited.add(node);
    recursionStack.add(node);

    const neighbors = graph.get(node) || new Set();
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (this.hasCycle(neighbor, graph, visited, recursionStack)) {
          return true;
        }
      } else if (recursionStack.has(neighbor)) {
        return true;
      }
    }

    recursionStack.delete(node);
    return false;
  }

  /**
   * Build dependency graph
   */
  private buildDependencyGraph(
    dependencies: TaskDependency[]
  ): Map<string, Set<string>> {
    const graph = new Map<string, Set<string>>();

    dependencies.forEach(dep => {
      if (!graph.has(dep.from)) {
        graph.set(dep.from, new Set());
      }
      graph.get(dep.from)!.add(dep.to);
    });

    return graph;
  }

  /**
   * Topological sort for execution order
   */
  private topologicalSort(
    tasks: Task[],
    dependencyGraph: Map<string, Set<string>>
  ): string[][] {
    const result: string[][] = [];
    const inDegree = new Map<string, number>();
    const taskIds = tasks.map(t => t.id);

    // Initialize in-degree
    taskIds.forEach(id => inDegree.set(id, 0));

    // Calculate in-degrees
    for (const [_, deps] of dependencyGraph) {
      for (const dep of deps) {
        inDegree.set(dep, (inDegree.get(dep) || 0) + 1);
      }
    }

    // Process tasks level by level
    while (inDegree.size > 0) {
      // Find all tasks with in-degree 0
      const currentLevel: string[] = [];
      for (const [id, degree] of inDegree) {
        if (degree === 0) {
          currentLevel.push(id);
        }
      }

      if (currentLevel.length === 0 && inDegree.size > 0) {
        throw new Error('Circular dependency detected');
      }

      // Remove processed tasks and update in-degrees
      currentLevel.forEach(id => {
        inDegree.delete(id);
        const deps = dependencyGraph.get(id) || new Set();
        for (const dep of deps) {
          if (inDegree.has(dep)) {
            inDegree.set(dep, inDegree.get(dep)! - 1);
          }
        }
      });

      if (currentLevel.length > 0) {
        result.push(currentLevel);
      }
    }

    return result;
  }

  /**
   * Calculate critical path
   */
  private calculateCriticalPath(
    tasks: Task[],
    dependencies: TaskDependency[]
  ): string[] {
    const taskMap = new Map(tasks.map(t => [t.id, t]));
    const graph = this.buildDependencyGraph(dependencies);
    const reverseGraph = this.buildReverseGraph(dependencies);

    // Find tasks with no dependencies (start nodes)
    const startNodes = tasks
      .filter(t => !dependencies.some(d => d.to === t.id))
      .map(t => t.id);

    // Find tasks with no dependents (end nodes)
    const endNodes = tasks
      .filter(t => !dependencies.some(d => d.from === t.id))
      .map(t => t.id);

    // Calculate earliest start times
    const earliestStart = new Map<string, number>();
    const calculateEarliestStart = (nodeId: string): number => {
      if (earliestStart.has(nodeId)) {
        return earliestStart.get(nodeId)!;
      }

      const deps = Array.from(reverseGraph.get(nodeId) || []);
      if (deps.length === 0) {
        earliestStart.set(nodeId, 0);
        return 0;
      }

      const maxPredecessor = Math.max(
        ...deps.map(depId => {
          const predStart = calculateEarliestStart(depId);
          const predDuration = this.estimateDuration(taskMap.get(depId)!);
          return predStart + predDuration;
        })
      );

      earliestStart.set(nodeId, maxPredecessor);
      return maxPredecessor;
    };

    // Calculate all earliest start times
    tasks.forEach(t => calculateEarliestStart(t.id));

    // Find the critical path
    let maxDuration = 0;
    let criticalEndNode = '';

    endNodes.forEach(nodeId => {
      const duration =
        earliestStart.get(nodeId)! +
        this.estimateDuration(taskMap.get(nodeId)!);
      if (duration > maxDuration) {
        maxDuration = duration;
        criticalEndNode = nodeId;
      }
    });

    // Trace back critical path
    const criticalPath: string[] = [];
    let currentNode = criticalEndNode;

    while (currentNode) {
      criticalPath.unshift(currentNode);

      const predecessors = Array.from(reverseGraph.get(currentNode) || []);
      if (predecessors.length === 0) break;

      // Find predecessor on critical path
      currentNode =
        predecessors.find(predId => {
          const predStart = earliestStart.get(predId)!;
          const predDuration = this.estimateDuration(taskMap.get(predId)!);
          const currentStart = earliestStart.get(currentNode)!;
          return predStart + predDuration === currentStart;
        }) || '';
    }

    return criticalPath;
  }

  /**
   * Build reverse dependency graph
   */
  private buildReverseGraph(
    dependencies: TaskDependency[]
  ): Map<string, Set<string>> {
    const graph = new Map<string, Set<string>>();

    dependencies.forEach(dep => {
      if (!graph.has(dep.to)) {
        graph.set(dep.to, new Set());
      }
      graph.get(dep.to)!.add(dep.from);
    });

    return graph;
  }

  /**
   * Check if there's data flow between tasks
   */
  private hasDataFlow(task1: Task, task2: Task): boolean {
    // Check if task2 mentions needing output from task1
    if (task2.description.includes(`output of ${task1.id}`)) {
      return true;
    }

    // Check metadata for data dependencies
    if (task2.metadata?.inputs?.includes(task1.id)) {
      return true;
    }

    return false;
  }

  /**
   * Check for resource conflicts
   */
  private hasResourceConflict(task1: Task, task2: Task): boolean {
    const res1 = task1.constraints?.requiredResources;
    const res2 = task2.constraints?.requiredResources;

    if (!res1 || !res2) return false;

    // Check for exclusive resource requirements
    if (res1.gpu && res2.gpu) return true;
    if (res1.network && res2.network) {
      // Network resources might conflict
      return Math.random() > 0.5; // Simplified check
    }

    return false;
  }

  /**
   * Get historical duration for task type
   */
  private getHistoricalDuration(taskType: string): number | null {
    // In production, this would query historical execution data
    const historicalData: Record<string, number> = {
      code_analysis: 8000,
      test_execution: 12000,
      compilation: 15000,
      deployment: 20000,
    };

    return historicalData[taskType] || null;
  }

  /**
   * Get decomposition strategy
   */
  private getStrategy(taskType: string): DecompositionStrategy | null {
    return this.decompositionStrategies.get(taskType) || null;
  }

  /**
   * Get default decomposition strategy
   */
  private getDefaultStrategy(): DecompositionStrategy {
    return this.decompositionStrategies.get('default')!;
  }

  /**
   * Register default decomposition strategies
   */
  private registerDefaultStrategies(): void {
    // Default strategy
    this.decompositionStrategies.set(
      'default',
      new DefaultDecompositionStrategy()
    );

    // Specialized strategies
    this.decompositionStrategies.set('build', new BuildDecompositionStrategy());
    this.decompositionStrategies.set('test', new TestDecompositionStrategy());
    this.decompositionStrategies.set(
      'deploy',
      new DeployDecompositionStrategy()
    );
    this.decompositionStrategies.set(
      'analysis',
      new AnalysisDecompositionStrategy()
    );
  }

  /**
   * Register default task templates
   */
  private registerDefaultTemplates(): void {
    // Task templates for common patterns
    this.taskTemplates.set('sequential', {
      pattern: 'sequential',
      decompose: (task: Task) => this.decomposeSequential(task),
    });

    this.taskTemplates.set('parallel', {
      pattern: 'parallel',
      decompose: (task: Task) => this.decomposeParallel(task),
    });

    this.taskTemplates.set('map-reduce', {
      pattern: 'map-reduce',
      decompose: (task: Task) => this.decomposeMapReduce(task),
    });
  }

  private decomposeSequential(task: Task): Task[] {
    // Implementation for sequential decomposition
    return [];
  }

  private decomposeParallel(task: Task): Task[] {
    // Implementation for parallel decomposition
    return [];
  }

  private decomposeMapReduce(task: Task): Task[] {
    // Implementation for map-reduce decomposition
    return [];
  }
}

// Decomposition Strategy Interface
interface DecompositionStrategy {
  decompose(task: Task): Promise<Task[]>;
}

// Default Decomposition Strategy
class DefaultDecompositionStrategy implements DecompositionStrategy {
  async decompose(task: Task): Promise<Task[]> {
    const subtasks: Task[] = [];

    // Analyze task description for action words
    const actions = this.extractActions(task.description);

    actions.forEach((action, index) => {
      subtasks.push({
        id: `${task.id}-sub-${index}`,
        type: this.inferType(action),
        description: action,
        priority: task.priority,
        status: 'pending',
        dependencies: index > 0 ? [`${task.id}-sub-${index - 1}`] : undefined,
        parentTask: task.id,
        createdAt: Date.now(),
        metadata: {
          ...task.metadata,
          subtaskIndex: index,
        },
      });
    });

    return subtasks;
  }

  private extractActions(description: string): string[] {
    // Simple extraction based on sentence structure
    const sentences = description.split(/[.!?]+/);
    return sentences.filter(s => s.trim().length > 0);
  }

  private inferType(action: string): string {
    if (action.includes('test')) return 'test';
    if (action.includes('build')) return 'build';
    if (action.includes('deploy')) return 'deploy';
    if (action.includes('analyze')) return 'analysis';
    return 'processing';
  }
}

// Build Decomposition Strategy
class BuildDecompositionStrategy implements DecompositionStrategy {
  async decompose(task: Task): Promise<Task[]> {
    return [
      this.createSubtask(task, 'clean', 'Clean build directory'),
      this.createSubtask(task, 'compile', 'Compile source code'),
      this.createSubtask(task, 'test', 'Run unit tests'),
      this.createSubtask(task, 'package', 'Package application'),
      this.createSubtask(task, 'verify', 'Verify build artifacts'),
    ];
  }

  private createSubtask(parent: Task, type: string, description: string): Task {
    return {
      id: `${parent.id}-${type}`,
      type,
      description,
      priority: parent.priority,
      status: 'pending',
      parentTask: parent.id,
      createdAt: Date.now(),
      metadata: parent.metadata,
    };
  }
}

// Test Decomposition Strategy
class TestDecompositionStrategy implements DecompositionStrategy {
  async decompose(task: Task): Promise<Task[]> {
    return [
      this.createSubtask(task, 'unit', 'Run unit tests'),
      this.createSubtask(task, 'integration', 'Run integration tests'),
      this.createSubtask(task, 'e2e', 'Run end-to-end tests'),
      this.createSubtask(task, 'performance', 'Run performance tests'),
      this.createSubtask(task, 'report', 'Generate test report'),
    ];
  }

  private createSubtask(parent: Task, type: string, description: string): Task {
    return {
      id: `${parent.id}-${type}`,
      type: `test-${type}`,
      description,
      priority: parent.priority,
      status: 'pending',
      parentTask: parent.id,
      createdAt: Date.now(),
      metadata: parent.metadata,
    };
  }
}

// Deploy Decomposition Strategy
class DeployDecompositionStrategy implements DecompositionStrategy {
  async decompose(task: Task): Promise<Task[]> {
    return [
      this.createSubtask(task, 'validate', 'Validate deployment configuration'),
      this.createSubtask(task, 'backup', 'Backup current state'),
      this.createSubtask(task, 'prepare', 'Prepare deployment environment'),
      this.createSubtask(task, 'deploy', 'Deploy application'),
      this.createSubtask(task, 'healthcheck', 'Run health checks'),
      this.createSubtask(task, 'rollback', 'Prepare rollback plan'),
    ];
  }

  private createSubtask(parent: Task, type: string, description: string): Task {
    return {
      id: `${parent.id}-${type}`,
      type: `deploy-${type}`,
      description,
      priority: parent.priority,
      status: 'pending',
      parentTask: parent.id,
      createdAt: Date.now(),
      metadata: parent.metadata,
    };
  }
}

// Analysis Decomposition Strategy
class AnalysisDecompositionStrategy implements DecompositionStrategy {
  async decompose(task: Task): Promise<Task[]> {
    return [
      this.createSubtask(task, 'collect', 'Collect data'),
      this.createSubtask(task, 'preprocess', 'Preprocess data'),
      this.createSubtask(task, 'analyze', 'Perform analysis'),
      this.createSubtask(task, 'visualize', 'Create visualizations'),
      this.createSubtask(task, 'report', 'Generate report'),
    ];
  }

  private createSubtask(parent: Task, type: string, description: string): Task {
    return {
      id: `${parent.id}-${type}`,
      type: `analysis-${type}`,
      description,
      priority: parent.priority,
      status: 'pending',
      parentTask: parent.id,
      createdAt: Date.now(),
      metadata: parent.metadata,
    };
  }
}

// Task Template Interface
interface TaskTemplate {
  pattern: string;
  decompose: (task: Task) => Task[];
}
