/**
 * Task Builder Implementation
 * 
 * Fluent API for building Task objects with validation, templates,
 * and support for complex task structures and workflows.
 */

import { v4 as uuidv4 } from 'uuid';
import { 
  Task, 
  TaskPriority, 
  TaskStatus, 
  TaskConstraints,
  ResourceRequirements,
  TaskDependency
} from './types.js';

/**
 * Task template for common task patterns
 */
export interface TaskTemplate {
  name: string;
  type: string;
  baseConfig: Partial<Task>;
  description: string;
  tags: string[];
  defaultConstraints?: TaskConstraints;
}

/**
 * Workflow configuration
 */
export interface WorkflowConfig {
  id?: string;
  name: string;
  description?: string;
  parallel?: boolean;
  failFast?: boolean;
  retryPolicy?: {
    maxRetries: number;
    delay: number;
  };
}

/**
 * Subtask configuration
 */
export interface SubtaskConfig {
  type: string;
  description: string;
  input?: any;
  dependencies?: string[];
  priority?: TaskPriority;
  constraints?: TaskConstraints;
}

/**
 * Task Builder Implementation
 */
export class TaskBuilder {
  private task: Partial<Task>;
  private templates: Map<string, TaskTemplate> = new Map();
  private validationRules: ValidationRule[] = [];

  constructor(type?: string) {
    this.task = {
      id: uuidv4(),
      type: type || 'generic',
      description: '',
      priority: 'medium',
      status: 'pending',
      dependencies: [],
      subtasks: [],
      createdAt: Date.now(),
      metadata: {}
    };

    this.initializeTemplates();
    this.initializeValidationRules();
  }

  /**
   * Set task ID
   */
  withId(id: string): TaskBuilder {
    this.task.id = id;
    return this;
  }

  /**
   * Set task type
   */
  withType(type: string): TaskBuilder {
    this.task.type = type;
    return this;
  }

  /**
   * Set task description
   */
  withDescription(description: string): TaskBuilder {
    this.task.description = description;
    return this;
  }

  /**
   * Set task priority
   */
  withPriority(priority: TaskPriority): TaskBuilder {
    this.task.priority = priority;
    return this;
  }

  /**
   * Set task status
   */
  withStatus(status: TaskStatus): TaskBuilder {
    this.task.status = status;
    return this;
  }

  /**
   * Set task input data
   */
  withInput(input: any): TaskBuilder {
    this.task.input = input;
    return this;
  }

  /**
   * Set task output data
   */
  withOutput(output: any): TaskBuilder {
    this.task.output = output;
    return this;
  }

  /**
   * Add task dependency
   */
  withDependency(taskId: string): TaskBuilder {
    if (!this.task.dependencies) {
      this.task.dependencies = [];
    }
    if (!this.task.dependencies.includes(taskId)) {
      this.task.dependencies.push(taskId);
    }
    return this;
  }

  /**
   * Add multiple task dependencies
   */
  withDependencies(taskIds: string[]): TaskBuilder {
    for (const taskId of taskIds) {
      this.withDependency(taskId);
    }
    return this;
  }

  /**
   * Set task constraints
   */
  withConstraints(constraints: TaskConstraints): TaskBuilder {
    this.task.constraints = { ...this.task.constraints, ...constraints };
    return this;
  }

  /**
   * Set required capabilities
   */
  withRequiredCapabilities(capabilities: string[]): TaskBuilder {
    if (!this.task.constraints) {
      this.task.constraints = {};
    }
    this.task.constraints.requiredCapabilities = capabilities;
    return this;
  }

  /**
   * Set maximum execution time
   */
  withMaxExecutionTime(maxTime: number): TaskBuilder {
    if (!this.task.constraints) {
      this.task.constraints = {};
    }
    this.task.constraints.maxExecutionTime = maxTime;
    return this;
  }

  /**
   * Set required resources
   */
  withRequiredResources(resources: ResourceRequirements): TaskBuilder {
    if (!this.task.constraints) {
      this.task.constraints = {};
    }
    this.task.constraints.requiredResources = resources;
    return this;
  }

  /**
   * Set preferred agent
   */
  withPreferredAgent(agentId: string): TaskBuilder {
    if (!this.task.constraints) {
      this.task.constraints = {};
    }
    this.task.constraints.preferredAgent = agentId;
    return this;
  }

  /**
   * Set parallelizable flag
   */
  withParallelizable(parallelizable: boolean): TaskBuilder {
    if (!this.task.constraints) {
      this.task.constraints = {};
    }
    this.task.constraints.parallelizable = parallelizable;
    return this;
  }

  /**
   * Set assigned agent
   */
  withAssignedAgent(agentId: string): TaskBuilder {
    this.task.assignedAgent = agentId;
    return this;
  }

  /**
   * Set parent task
   */
  withParentTask(parentTaskId: string): TaskBuilder {
    this.task.parentTask = parentTaskId;
    return this;
  }

  /**
   * Add subtask
   */
  withSubtask(subtaskId: string): TaskBuilder {
    if (!this.task.subtasks) {
      this.task.subtasks = [];
    }
    if (!this.task.subtasks.includes(subtaskId)) {
      this.task.subtasks.push(subtaskId);
    }
    return this;
  }

  /**
   * Add multiple subtasks
   */
  withSubtasks(subtaskIds: string[]): TaskBuilder {
    for (const subtaskId of subtaskIds) {
      this.withSubtask(subtaskId);
    }
    return this;
  }

  /**
   * Set task metadata
   */
  withMetadata(metadata: Record<string, any>): TaskBuilder {
    this.task.metadata = { ...this.task.metadata, ...metadata };
    return this;
  }

  /**
   * Add metadata property
   */
  withMetadataProperty(key: string, value: any): TaskBuilder {
    if (!this.task.metadata) {
      this.task.metadata = {};
    }
    this.task.metadata[key] = value;
    return this;
  }

  /**
   * Set task tags
   */
  withTags(tags: string[]): TaskBuilder {
    this.withMetadataProperty('tags', tags);
    return this;
  }

  /**
   * Add single tag
   */
  withTag(tag: string): TaskBuilder {
    const currentTags = (this.task.metadata?.tags as string[]) || [];
    if (!currentTags.includes(tag)) {
      currentTags.push(tag);
      this.withTags(currentTags);
    }
    return this;
  }

  /**
   * Set timeout
   */
  withTimeout(timeout: number): TaskBuilder {
    this.withMetadataProperty('timeout', timeout);
    return this;
  }

  /**
   * Set retry configuration
   */
  withRetry(maxRetries: number, delay: number = 1000): TaskBuilder {
    this.withMetadataProperty('retry', { maxRetries, delay });
    return this;
  }

  /**
   * Apply task template
   */
  fromTemplate(templateName: string, overrides: Partial<Task> = {}): TaskBuilder {
    const template = this.templates.get(templateName);
    if (!template) {
      throw new Error(`Task template '${templateName}' not found`);
    }

    // Apply template configuration
    this.task = {
      ...this.task,
      ...template.baseConfig,
      ...overrides,
      id: this.task.id, // Keep original ID
      createdAt: this.task.createdAt, // Keep original creation time
      metadata: {
        ...this.task.metadata,
        ...template.baseConfig.metadata,
        ...overrides.metadata,
        template: templateName,
        tags: [
          ...(this.task.metadata?.tags || []),
          ...(template.baseConfig.metadata?.tags || []),
          ...(overrides.metadata?.tags || []),
          ...template.tags
        ]
      }
    };

    // Apply default constraints if specified
    if (template.defaultConstraints) {
      this.task.constraints = {
        ...this.task.constraints,
        ...template.defaultConstraints
      };
    }

    return this;
  }

  /**
   * Build and validate the task
   */
  build(): Task {
    const task = this.task as Task;

    // Validate required fields
    if (!task.id) {
      throw new Error('Task ID is required');
    }
    if (!task.type) {
      throw new Error('Task type is required');
    }
    if (!task.description || task.description.trim() === '') {
      throw new Error('Task description is required');
    }

    // Run validation rules
    for (const rule of this.validationRules) {
      const result = rule.validate(task);
      if (!result.isValid) {
        throw new Error(`Validation failed: ${result.message}`);
      }
    }

    // Set timestamps
    if (!task.createdAt) {
      task.createdAt = Date.now();
    }

    // Initialize arrays if not set
    task.dependencies = task.dependencies || [];
    task.subtasks = task.subtasks || [];
    task.metadata = task.metadata || {};

    return { ...task };
  }

  /**
   * Build task and create subtasks
   */
  buildWithSubtasks(subtaskConfigs: SubtaskConfig[]): { parentTask: Task; subtasks: Task[] } {
    const parentTask = this.build();
    const subtasks: Task[] = [];

    for (const config of subtaskConfigs) {
      const subtaskBuilder = new TaskBuilder(config.type)
        .withDescription(config.description)
        .withParentTask(parentTask.id)
        .withPriority(config.priority || 'medium');

      if (config.input) {
        subtaskBuilder.withInput(config.input);
      }

      if (config.dependencies) {
        subtaskBuilder.withDependencies(config.dependencies);
      }

      if (config.constraints) {
        subtaskBuilder.withConstraints(config.constraints);
      }

      const subtask = subtaskBuilder.build();
      subtasks.push(subtask);
      
      // Add subtask ID to parent
      if (!parentTask.subtasks) {
        parentTask.subtasks = [];
      }
      parentTask.subtasks.push(subtask.id);
    }

    return { parentTask, subtasks };
  }

  /**
   * Clone the builder
   */
  clone(): TaskBuilder {
    const clonedBuilder = new TaskBuilder();
    clonedBuilder.task = JSON.parse(JSON.stringify(this.task));
    clonedBuilder.task.id = uuidv4(); // Generate new ID for clone
    return clonedBuilder;
  }

  /**
   * Reset the builder
   */
  reset(type?: string): TaskBuilder {
    this.task = {
      id: uuidv4(),
      type: type || 'generic',
      description: '',
      priority: 'medium',
      status: 'pending',
      dependencies: [],
      subtasks: [],
      createdAt: Date.now(),
      metadata: {}
    };
    return this;
  }

  /**
   * Register a task template
   */
  static registerTemplate(template: TaskTemplate): void {
    TaskBuilder.globalTemplates.set(template.name, template);
  }

  /**
   * Get all registered templates
   */
  static getTemplates(): TaskTemplate[] {
    return Array.from(TaskBuilder.globalTemplates.values());
  }

  /**
   * Get template by name
   */
  static getTemplate(name: string): TaskTemplate | undefined {
    return TaskBuilder.globalTemplates.get(name);
  }

  // Private properties and methods
  private static globalTemplates: Map<string, TaskTemplate> = new Map();

  /**
   * Initialize default templates
   */
  private initializeTemplates(): void {
    // Copy global templates to instance
    for (const [name, template] of Array.from(TaskBuilder.globalTemplates.entries())) {
      this.templates.set(name, template);
    }

    // Add default templates if not already present
    const defaultTemplates: TaskTemplate[] = [
      {
        name: 'data-processing',
        type: 'processing',
        baseConfig: {
          description: 'Data processing task',
          priority: 'medium',
          constraints: {
            requiredCapabilities: ['data-processing'],
            maxExecutionTime: 60000,
            parallelizable: true
          }
        },
        description: 'Template for data processing tasks',
        tags: ['data', 'processing']
      },
      {
        name: 'computation',
        type: 'computation',
        baseConfig: {
          description: 'Computational task',
          priority: 'high',
          constraints: {
            requiredCapabilities: ['computation'],
            maxExecutionTime: 120000,
            requiredResources: {
              cpu: 2,
              memory: 1024
            }
          }
        },
        description: 'Template for computational tasks',
        tags: ['computation', 'cpu-intensive']
      },
      {
        name: 'io-operation',
        type: 'io',
        baseConfig: {
          description: 'I/O operation task',
          priority: 'medium',
          constraints: {
            requiredCapabilities: ['io-operations'],
            maxExecutionTime: 30000,
            parallelizable: true
          }
        },
        description: 'Template for I/O operation tasks',
        tags: ['io', 'file-system']
      },
      {
        name: 'analysis',
        type: 'analysis',
        baseConfig: {
          description: 'Analysis task',
          priority: 'high',
          constraints: {
            requiredCapabilities: ['analysis', 'pattern-recognition'],
            maxExecutionTime: 180000,
            requiredResources: {
              cpu: 4,
              memory: 2048
            }
          }
        },
        description: 'Template for analysis tasks',
        tags: ['analysis', 'intelligence']
      },
      {
        name: 'validation',
        type: 'validation',
        baseConfig: {
          description: 'Validation task',
          priority: 'high',
          constraints: {
            requiredCapabilities: ['validation'],
            maxExecutionTime: 15000
          }
        },
        description: 'Template for validation tasks',
        tags: ['validation', 'quality-assurance']
      },
      {
        name: 'workflow-coordinator',
        type: 'coordination',
        baseConfig: {
          description: 'Workflow coordination task',
          priority: 'critical',
          constraints: {
            requiredCapabilities: ['coordination', 'workflow-management'],
            maxExecutionTime: 300000,
            parallelizable: false
          }
        },
        description: 'Template for workflow coordination tasks',
        tags: ['coordination', 'workflow']
      }
    ];

    for (const template of defaultTemplates) {
      if (!this.templates.has(template.name)) {
        this.templates.set(template.name, template);
      }
    }
  }

  /**
   * Initialize validation rules
   */
  private initializeValidationRules(): void {
    this.validationRules = [
      {
        name: 'priority-validation',
        validate: (task: Task) => {
          const validPriorities: TaskPriority[] = ['critical', 'high', 'medium', 'low'];
          if (!validPriorities.includes(task.priority)) {
            return {
              isValid: false,
              message: `Invalid priority: ${task.priority}. Must be one of: ${validPriorities.join(', ')}`
            };
          }
          return { isValid: true };
        }
      },
      {
        name: 'dependency-validation',
        validate: (task: Task) => {
          if (task.dependencies && task.dependencies.includes(task.id)) {
            return {
              isValid: false,
              message: 'Task cannot depend on itself'
            };
          }
          return { isValid: true };
        }
      },
      {
        name: 'execution-time-validation',
        validate: (task: Task) => {
          if (task.constraints?.maxExecutionTime && task.constraints.maxExecutionTime <= 0) {
            return {
              isValid: false,
              message: 'Maximum execution time must be positive'
            };
          }
          return { isValid: true };
        }
      },
      {
        name: 'resource-validation',
        validate: (task: Task) => {
          const resources = task.constraints?.requiredResources;
          if (resources) {
            if (resources.cpu && resources.cpu <= 0) {
              return {
                isValid: false,
                message: 'CPU requirement must be positive'
              };
            }
            if (resources.memory && resources.memory <= 0) {
              return {
                isValid: false,
                message: 'Memory requirement must be positive'
              };
            }
          }
          return { isValid: true };
        }
      }
    ];
  }
}

/**
 * Validation rule interface
 */
interface ValidationRule {
  name: string;
  validate: (task: Task) => ValidationResult;
}

/**
 * Validation result interface
 */
interface ValidationResult {
  isValid: boolean;
  message?: string;
}

/**
 * Workflow Builder for creating complex task workflows
 */
export class WorkflowBuilder {
  private config: WorkflowConfig;
  private tasks: Map<string, TaskBuilder> = new Map();
  private dependencies: TaskDependency[] = [];

  constructor(name: string, config: Partial<WorkflowConfig> = {}) {
    this.config = {
      id: config.id || uuidv4(),
      name,
      description: config.description || `Workflow: ${name}`,
      parallel: config.parallel || false,
      failFast: config.failFast || true,
      retryPolicy: config.retryPolicy
    };
  }

  /**
   * Add task to workflow
   */
  addTask(taskId: string, builder: TaskBuilder): WorkflowBuilder {
    this.tasks.set(taskId, builder);
    return this;
  }

  /**
   * Create and add task to workflow
   */
  createTask(taskId: string, type: string): TaskBuilder {
    const builder = new TaskBuilder(type)
      .withId(taskId)
      .withMetadataProperty('workflowId', this.config.id);
    
    this.tasks.set(taskId, builder);
    return builder;
  }

  /**
   * Add dependency between tasks
   */
  addDependency(fromTaskId: string, toTaskId: string, type: 'blocking' | 'soft' | 'optional' = 'blocking'): WorkflowBuilder {
    this.dependencies.push({
      from: fromTaskId,
      to: toTaskId,
      type
    });
    return this;
  }

  /**
   * Build workflow tasks
   */
  build(): { tasks: Task[]; dependencies: TaskDependency[] } {
    const tasks: Task[] = [];

    // Apply dependencies to task builders
    for (const dependency of this.dependencies) {
      const toBuilder = this.tasks.get(dependency.to);
      if (toBuilder && dependency.type === 'blocking') {
        toBuilder.withDependency(dependency.from);
      }
    }

    // Build all tasks
    for (const [taskId, builder] of Array.from(this.tasks.entries())) {
      builder.withMetadataProperty('workflowId', this.config.id);
      
      if (this.config.retryPolicy) {
        builder.withRetry(this.config.retryPolicy.maxRetries, this.config.retryPolicy.delay);
      }

      tasks.push(builder.build());
    }

    return { tasks, dependencies: this.dependencies };
  }

  /**
   * Build workflow with coordinator task
   */
  buildWithCoordinator(): { coordinatorTask: Task; tasks: Task[]; dependencies: TaskDependency[] } {
    const workflow = this.build();
    
    const coordinatorTask = new TaskBuilder('coordination')
      .withDescription(`Coordinator for workflow: ${this.config.name}`)
      .withPriority('critical')
      .withSubtasks(workflow.tasks.map(t => t.id))
      .withMetadata({
        workflowId: this.config.id,
        workflowName: this.config.name,
        workflowConfig: this.config,
        isCoordinator: true
      })
      .withConstraints({
        requiredCapabilities: ['coordination', 'workflow-management'],
        parallelizable: false
      })
      .build();

    return {
      coordinatorTask,
      tasks: workflow.tasks,
      dependencies: workflow.dependencies
    };
  }
}

/**
 * Helper functions for common task creation patterns
 */

/**
 * Create a simple task
 */
export function createTask(type: string, description: string): TaskBuilder {
  return new TaskBuilder(type).withDescription(description);
}

/**
 * Create a task from template
 */
export function createTaskFromTemplate(templateName: string, overrides: Partial<Task> = {}): TaskBuilder {
  return new TaskBuilder().fromTemplate(templateName, overrides);
}

/**
 * Create a batch of similar tasks
 */
export function createTaskBatch(
  count: number, 
  type: string, 
  baseDescription: string, 
  inputs: any[] = []
): TaskBuilder[] {
  const builders: TaskBuilder[] = [];

  for (let i = 0; i < count; i++) {
    const builder = new TaskBuilder(type)
      .withDescription(`${baseDescription} ${i + 1}`)
      .withMetadataProperty('batchIndex', i);

    if (inputs[i]) {
      builder.withInput(inputs[i]);
    }

    builders.push(builder);
  }

  return builders;
}

/**
 * Create a pipeline of dependent tasks
 */
export function createTaskPipeline(configs: { type: string; description: string; input?: any }[]): TaskBuilder[] {
  const builders: TaskBuilder[] = [];

  for (let i = 0; i < configs.length; i++) {
    const config = configs[i];
    const builder = new TaskBuilder(config.type)
      .withDescription(config.description)
      .withMetadataProperty('pipelineIndex', i);

    if (config.input) {
      builder.withInput(config.input);
    }

    // Add dependency on previous task
    if (i > 0) {
      builder.withDependency(builders[i - 1].build().id);
    }

    builders.push(builder);
  }

  return builders;
}

// Initialize default templates
TaskBuilder.registerTemplate({
  name: 'default',
  type: 'generic',
  baseConfig: {
    description: 'Default task',
    priority: 'medium'
  },
  description: 'Default task template',
  tags: ['default']
});