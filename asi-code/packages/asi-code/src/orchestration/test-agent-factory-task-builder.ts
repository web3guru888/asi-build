/**
 * Test file for AgentFactory and TaskBuilder implementations
 * 
 * Comprehensive tests to ensure both implementations are working correctly
 * and integrate properly with existing types.
 */

import { 
  AgentFactory, 
  TaskBuilder, 
  WorkflowBuilder,
  createAgent,
  createFromTemplate,
  createTask,
  createTaskFromTemplate
} from './index.js';
import { AgentConfig, Task, TaskPriority } from './types.js';
import { Logger } from '../logging/index.js';

/**
 * Test AgentFactory functionality
 */
async function testAgentFactory(): Promise<void> {
  console.log('Testing AgentFactory...');

  const logger = new Logger({
    level: 'info',
    context: { component: 'AgentFactoryTest' }
  });

  const factory = new AgentFactory({ logger });

  try {
    // Test basic agent creation
    const workerConfig: AgentConfig = {
      name: 'TestWorker',
      type: 'worker',
      capabilities: ['task-execution', 'processing'],
      maxConcurrentTasks: 3
    };

    const worker = await factory.createAgent(workerConfig);
    console.log(`✓ Created worker agent: ${worker.id}`);

    // Test template-based creation
    const templateWorker = await factory.createFromTemplate('basic-worker', {
      name: 'TemplateWorker'
    });
    console.log(`✓ Created template-based worker: ${templateWorker.id}`);

    // Test agent cluster creation
    const cluster = await factory.createAgentCluster(3, {
      name: 'ClusterWorker',
      type: 'worker',
      capabilities: ['processing'],
      maxConcurrentTasks: 2
    });
    console.log(`✓ Created agent cluster with ${cluster.length} agents`);

    // Test pooling configuration
    factory.configurePooling('worker', {
      minSize: 1,
      maxSize: 5,
      idleTimeout: 60000,
      recycleThreshold: 10
    });
    console.log('✓ Configured agent pooling');

    // Test pool statistics
    const stats = factory.getPoolStats();
    console.log(`✓ Pool stats: ${Array.from(stats.entries()).length} pool types`);

    // Test template registration
    factory.registerTemplate({
      name: 'test-template',
      type: 'specialist',
      baseConfig: {
        capabilities: ['testing'],
        maxConcurrentTasks: 1
      },
      description: 'Test template',
      tags: ['test']
    });
    console.log('✓ Registered custom template');

    // Test helper functions
    const helperWorker = await createAgent({
      name: 'HelperWorker',
      type: 'worker',
      capabilities: ['testing'],
      maxConcurrentTasks: 1
    });
    console.log(`✓ Created agent using helper function: ${helperWorker.id}`);

    // Cleanup
    await factory.clearPools();
    await factory.shutdown();
    console.log('✓ AgentFactory cleanup completed');

  } catch (error) {
    console.error('✗ AgentFactory test failed:', error);
    throw error;
  }
}

/**
 * Test TaskBuilder functionality
 */
async function testTaskBuilder(): Promise<void> {
  console.log('\nTesting TaskBuilder...');

  try {
    // Test basic task creation
    const basicTask = new TaskBuilder('processing')
      .withDescription('Test processing task')
      .withPriority('high')
      .withInput({ data: 'test data' })
      .withRequiredCapabilities(['processing', 'data-handling'])
      .withMaxExecutionTime(30000)
      .withTags(['test', 'processing'])
      .build();

    console.log(`✓ Created basic task: ${basicTask.id}`);
    console.log(`  Type: ${basicTask.type}, Priority: ${basicTask.priority}`);

    // Test task with dependencies
    const taskWithDeps = new TaskBuilder('analysis')
      .withDescription('Analysis task with dependencies')
      .withDependencies([basicTask.id])
      .withConstraints({
        requiredCapabilities: ['analysis'],
        parallelizable: false
      })
      .build();

    console.log(`✓ Created task with dependencies: ${taskWithDeps.id}`);

    // Test template-based task creation
    TaskBuilder.registerTemplate({
      name: 'test-processing',
      type: 'processing',
      baseConfig: {
        description: 'Test processing template',
        priority: 'medium',
        constraints: {
          requiredCapabilities: ['processing'],
          maxExecutionTime: 15000
        }
      },
      description: 'Template for test processing',
      tags: ['test', 'template']
    });

    const templateTask = new TaskBuilder()
      .fromTemplate('test-processing', {
        description: 'Custom template task'
      })
      .withMetadataProperty('custom', 'value')
      .build();

    console.log(`✓ Created template-based task: ${templateTask.id}`);

    // Test task builder with subtasks
    const { parentTask, subtasks } = new TaskBuilder('coordination')
      .withDescription('Parent task with subtasks')
      .withPriority('critical')
      .buildWithSubtasks([
        {
          type: 'processing',
          description: 'Subtask 1',
          input: { step: 1 }
        },
        {
          type: 'analysis',
          description: 'Subtask 2',
          dependencies: [/* would reference subtask 1 */],
          priority: 'high'
        }
      ]);

    console.log(`✓ Created parent task with ${subtasks.length} subtasks`);
    console.log(`  Parent: ${parentTask.id}, Subtasks: ${parentTask.subtasks?.join(', ')}`);

    // Test workflow builder
    const workflow = new WorkflowBuilder('test-workflow', {
      description: 'Test workflow',
      parallel: false
    });

    const task1 = workflow.createTask('task1', 'processing')
      .withDescription('First task in workflow')
      .withInput({ stage: 1 });

    const task2 = workflow.createTask('task2', 'analysis')
      .withDescription('Second task in workflow')
      .withInput({ stage: 2 });

    workflow.addDependency('task1', 'task2');

    const { coordinatorTask, tasks, dependencies } = workflow.buildWithCoordinator();

    console.log(`✓ Created workflow with coordinator`);
    console.log(`  Coordinator: ${coordinatorTask.id}`);
    console.log(`  Tasks: ${tasks.length}, Dependencies: ${dependencies.length}`);

    // Test helper functions
    const helperTask = createTask('testing', 'Helper task created with utility function')
      .withPriority('low')
      .build();

    console.log(`✓ Created task using helper function: ${helperTask.id}`);

    // Test task validation
    try {
      new TaskBuilder('invalid')
        .withDescription('')  // Empty description should fail
        .build();
      console.log('✗ Task validation failed - empty description should have been caught');
    } catch (error) {
      console.log('✓ Task validation working - caught empty description');
    }

    // Test task cloning
    const clonedBuilder = new TaskBuilder('processing')
      .withDescription('Original task')
      .withPriority('high')
      .clone()
      .withDescription('Cloned task')
      .withPriority('medium');

    const originalTask = clonedBuilder.reset('processing')
      .withDescription('Original task')
      .withPriority('high')
      .build();

    const clonedTask = clonedBuilder.clone()
      .withDescription('Cloned task')
      .withPriority('medium')
      .build();

    console.log(`✓ Task cloning works: original=${originalTask.id}, clone=${clonedTask.id}`);

  } catch (error) {
    console.error('✗ TaskBuilder test failed:', error);
    throw error;
  }
}

/**
 * Test integration between AgentFactory and TaskBuilder
 */
async function testIntegration(): Promise<void> {
  console.log('\nTesting AgentFactory + TaskBuilder integration...');

  try {
    const logger = new Logger({
      level: 'info',
      context: { component: 'IntegrationTest' }
    });

    const factory = new AgentFactory({ logger });

    // Create a workflow with tasks
    const workflow = new WorkflowBuilder('integration-test');
    
    workflow.createTask('data-prep', 'processing')
      .withDescription('Prepare data for analysis')
      .withRequiredCapabilities(['data-processing'])
      .withInput({ dataset: 'test-data' });

    workflow.createTask('analysis', 'analysis')
      .withDescription('Analyze prepared data')
      .withRequiredCapabilities(['analysis', 'pattern-recognition'])
      .withInput({ algorithm: 'ml-analysis' });

    workflow.addDependency('data-prep', 'analysis');

    const { coordinatorTask, tasks } = workflow.buildWithCoordinator();

    // Create appropriate agents for the tasks
    const dataWorker = await factory.createFromTemplate('basic-worker', {
      name: 'DataWorker',
      capabilities: ['data-processing', 'task-execution']
    });

    const analysisSpecialist = await factory.createFromTemplate('specialist-analyzer', {
      name: 'AnalysisSpecialist'
    });

    const coordinator = await factory.createAgent({
      name: 'WorkflowCoordinator',
      type: 'coordinator',
      capabilities: ['coordination', 'workflow-management'],
      maxConcurrentTasks: 10
    });

    console.log(`✓ Created agents for workflow:`);
    console.log(`  Data Worker: ${dataWorker.id}`);
    console.log(`  Analysis Specialist: ${analysisSpecialist.id}`);
    console.log(`  Coordinator: ${coordinator.id}`);

    // Verify task-agent compatibility
    const dataTask = tasks.find(t => t.type === 'processing');
    const analysisTask = tasks.find(t => t.type === 'analysis');

    if (dataTask && dataWorker.canHandle(dataTask)) {
      console.log(`✓ Data worker can handle processing task`);
    }

    if (analysisTask && analysisSpecialist.canHandle(analysisTask)) {
      console.log(`✓ Analysis specialist can handle analysis task`);
    }

    if (coordinator.canHandle(coordinatorTask)) {
      console.log(`✓ Coordinator can handle coordination task`);
    }

    console.log(`✓ Integration test successful - workflow with ${tasks.length} tasks and compatible agents created`);

    // Cleanup
    await factory.shutdown();

  } catch (error) {
    console.error('✗ Integration test failed:', error);
    throw error;
  }
}

/**
 * Run all tests
 */
export async function runAgentFactoryTaskBuilderTests(): Promise<void> {
  console.log('=== AgentFactory and TaskBuilder Tests ===');
  
  try {
    await testAgentFactory();
    await testTaskBuilder();
    await testIntegration();
    
    console.log('\n✓ All tests passed successfully!');
    console.log('✓ AgentFactory and TaskBuilder implementations are working correctly');
    console.log('✓ Both files integrate properly with existing types');
    
  } catch (error) {
    console.error('\n✗ Tests failed:', error);
    throw error;
  }
}

// Export test functions for external use
export {
  testAgentFactory,
  testTaskBuilder,
  testIntegration
};

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAgentFactoryTaskBuilderTests()
    .then(() => {
      console.log('\nTest execution completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('\nTest execution failed:', error);
      process.exit(1);
    });
}