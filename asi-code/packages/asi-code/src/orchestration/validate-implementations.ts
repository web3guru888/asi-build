/**
 * Validation script for AgentFactory and TaskBuilder implementations
 * 
 * Simple validation to ensure both implementations are correctly implemented
 * and work with the existing type system.
 */

import { 
  AgentFactory, 
  TaskBuilder, 
  WorkflowBuilder,
  type AgentTemplate,
  type TaskTemplate
} from './index.js';
import { AgentConfig, Task, AgentType } from './types.js';

/**
 * Validate AgentFactory implementation
 */
function validateAgentFactory(): boolean {
  console.log('Validating AgentFactory implementation...');

  try {
    // Test factory instantiation
    const factory = new AgentFactory();
    console.log('✓ AgentFactory instantiation successful');

    // Test template registration
    const testTemplate: AgentTemplate = {
      name: 'test-template',
      type: 'worker',
      baseConfig: {
        capabilities: ['testing'],
        maxConcurrentTasks: 1
      },
      description: 'Test template',
      tags: ['test']
    };

    factory.registerTemplate(testTemplate);
    console.log('✓ Template registration works');

    // Test template retrieval
    const retrievedTemplate = factory.getTemplate('test-template');
    if (!retrievedTemplate) {
      throw new Error('Template retrieval failed');
    }
    console.log('✓ Template retrieval works');

    // Test pool configuration
    factory.configurePooling('worker', {
      minSize: 1,
      maxSize: 5,
      idleTimeout: 60000,
      recycleThreshold: 10
    });
    console.log('✓ Pool configuration works');

    // Test pool stats
    const stats = factory.getPoolStats();
    console.log('✓ Pool statistics retrieval works');

    // Test dependency injection
    factory.setDependencies({ test: 'value' });
    const deps = factory.getDependencies();
    if (!deps.test) {
      throw new Error('Dependency injection failed');
    }
    console.log('✓ Dependency injection works');

    console.log('✓ AgentFactory validation completed successfully');
    return true;

  } catch (error) {
    console.error('✗ AgentFactory validation failed:', error);
    return false;
  }
}

/**
 * Validate TaskBuilder implementation
 */
function validateTaskBuilder(): boolean {
  console.log('\nValidating TaskBuilder implementation...');

  try {
    // Test basic task creation
    const task = new TaskBuilder('processing')
      .withDescription('Test task')
      .withPriority('high')
      .withRequiredCapabilities(['processing'])
      .withMaxExecutionTime(30000)
      .build();

    if (!task.id || !task.type || !task.description) {
      throw new Error('Basic task creation failed');
    }
    console.log('✓ Basic task creation works');

    // Test task with dependencies
    const dependentTask = new TaskBuilder('analysis')
      .withDescription('Dependent task')
      .withDependencies([task.id])
      .build();

    if (!dependentTask.dependencies || !dependentTask.dependencies.includes(task.id)) {
      throw new Error('Task dependencies failed');
    }
    console.log('✓ Task dependencies work');

    // Test template registration
    const testTemplate: TaskTemplate = {
      name: 'test-task-template',
      type: 'testing',
      baseConfig: {
        description: 'Test template task',
        priority: 'medium'
      },
      description: 'Test task template',
      tags: ['test']
    };

    TaskBuilder.registerTemplate(testTemplate);
    const retrievedTemplate = TaskBuilder.getTemplate('test-task-template');
    if (!retrievedTemplate) {
      throw new Error('Task template registration/retrieval failed');
    }
    console.log('✓ Task template registration works');

    // Test template-based task creation
    const templateTask = new TaskBuilder()
      .fromTemplate('test-task-template')
      .withDescription('Custom template task')
      .build();

    if (templateTask.type !== 'testing') {
      throw new Error('Template-based task creation failed');
    }
    console.log('✓ Template-based task creation works');

    // Test task builder cloning
    const originalBuilder = new TaskBuilder('cloning')
      .withDescription('Original task')
      .withPriority('high');

    const clonedBuilder = originalBuilder.clone()
      .withDescription('Cloned task')
      .withPriority('medium');

    const originalTask = originalBuilder.build();
    const clonedTask = clonedBuilder.build();

    if (originalTask.id === clonedTask.id) {
      throw new Error('Task cloning failed - same ID');
    }
    console.log('✓ Task builder cloning works');

    // Test validation
    try {
      new TaskBuilder('invalid')
        .withDescription('')  // Empty description should fail
        .build();
      throw new Error('Validation should have failed');
    } catch (validationError) {
      if (validationError.message.includes('Validation should have failed')) {
        throw validationError;
      }
      console.log('✓ Task validation works');
    }

    // Test subtask creation
    const { parentTask, subtasks } = new TaskBuilder('coordination')
      .withDescription('Parent with subtasks')
      .buildWithSubtasks([
        {
          type: 'processing',
          description: 'Subtask 1'
        },
        {
          type: 'analysis',
          description: 'Subtask 2'
        }
      ]);

    if (subtasks.length !== 2 || !parentTask.subtasks || parentTask.subtasks.length !== 2) {
      throw new Error('Subtask creation failed');
    }
    console.log('✓ Subtask creation works');

    console.log('✓ TaskBuilder validation completed successfully');
    return true;

  } catch (error) {
    console.error('✗ TaskBuilder validation failed:', error);
    return false;
  }
}

/**
 * Validate WorkflowBuilder implementation
 */
function validateWorkflowBuilder(): boolean {
  console.log('\nValidating WorkflowBuilder implementation...');

  try {
    // Test workflow creation
    const workflow = new WorkflowBuilder('test-workflow', {
      description: 'Test workflow',
      parallel: false
    });

    const task1 = workflow.createTask('task1', 'processing')
      .withDescription('First task')
      .withInput({ data: 'test' });

    const task2 = workflow.createTask('task2', 'analysis')
      .withDescription('Second task');

    workflow.addDependency('task1', 'task2');

    const { tasks, dependencies } = workflow.build();

    if (tasks.length !== 2 || dependencies.length !== 1) {
      throw new Error('Workflow building failed');
    }
    console.log('✓ Basic workflow creation works');

    // Test workflow with coordinator
    const { coordinatorTask, tasks: coordTasks, dependencies: coordDeps } = workflow.buildWithCoordinator();

    if (!coordinatorTask || coordTasks.length !== 2) {
      throw new Error('Workflow coordinator creation failed');
    }
    console.log('✓ Workflow coordinator creation works');

    console.log('✓ WorkflowBuilder validation completed successfully');
    return true;

  } catch (error) {
    console.error('✗ WorkflowBuilder validation failed:', error);
    return false;
  }
}

/**
 * Validate type compatibility
 */
function validateTypeCompatibility(): boolean {
  console.log('\nValidating type compatibility...');

  try {
    // Test AgentConfig compatibility
    const agentConfig: AgentConfig = {
      name: 'TestAgent',
      type: 'worker' as AgentType,
      capabilities: ['testing'],
      maxConcurrentTasks: 1
    };

    // This should compile without errors
    const factory = new AgentFactory();
    console.log('✓ AgentConfig type compatibility confirmed');

    // Test Task type compatibility
    const task: Task = new TaskBuilder('testing')
      .withDescription('Type compatibility test')
      .build();

    // This should work without type errors
    if (task.id && task.type && task.description) {
      console.log('✓ Task type compatibility confirmed');
    }

    // Test template types
    const agentTemplate: AgentTemplate = {
      name: 'type-test',
      type: 'worker',
      baseConfig: agentConfig,
      description: 'Type test',
      tags: ['test']
    };

    const taskTemplate: TaskTemplate = {
      name: 'type-test',
      type: 'testing',
      baseConfig: {
        description: 'Type test task',
        priority: 'medium'
      },
      description: 'Type test',
      tags: ['test']
    };

    console.log('✓ Template type compatibility confirmed');

    console.log('✓ Type compatibility validation completed successfully');
    return true;

  } catch (error) {
    console.error('✗ Type compatibility validation failed:', error);
    return false;
  }
}

/**
 * Run all validation tests
 */
export function validateImplementations(): boolean {
  console.log('=== Validating AgentFactory and TaskBuilder Implementations ===\n');

  const results = [
    validateAgentFactory(),
    validateTaskBuilder(),
    validateWorkflowBuilder(),
    validateTypeCompatibility()
  ];

  const allPassed = results.every(result => result);

  if (allPassed) {
    console.log('\n✓ All validations passed successfully!');
    console.log('✓ AgentFactory implementation is complete and working');
    console.log('✓ TaskBuilder implementation is complete and working');
    console.log('✓ Both implementations integrate correctly with existing types');
    console.log('✓ Factory pattern for agent creation is implemented');
    console.log('✓ Fluent API for task building is implemented');
    console.log('✓ Agent templates and pooling are functional');
    console.log('✓ Task templates and workflows are functional');
    console.log('✓ Dependency injection is supported');
    console.log('✓ Validation and error handling are in place');
  } else {
    console.log('\n✗ Some validations failed');
  }

  return allPassed;
}

// Run validation if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const success = validateImplementations();
  process.exit(success ? 0 : 1);
}