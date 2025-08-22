#!/usr/bin/env bun
/**
 * ASI-Code Agent Orchestration Demonstration
 * 
 * This script demonstrates the complete agent orchestration system
 * with supervisor agents, task decomposition, and parallel execution.
 */

import { createOrchestrator, TaskBuilder, createAgent } from './src/orchestration/index.js';
import { Logger } from './src/logging/index.js';

const logger = new Logger({ component: 'OrchestrationDemo', level: 'info' });

async function main() {
  console.log('\n🚀 ASI-Code Agent Orchestration System Demo\n');
  console.log('=' .repeat(60));
  
  try {
    // 1. Create the orchestrator
    console.log('\n📋 Step 1: Initializing Orchestrator...');
    const orchestrator = createOrchestrator(logger);
    await new Promise(resolve => setTimeout(resolve, 1000)); // Give it time to initialize
    
    // 2. Get system status
    console.log('\n📊 Step 2: System Status');
    const status = orchestrator.getSystemStatus();
    console.log(`  ✓ Supervisors: ${status.supervisorCount}`);
    console.log(`  ✓ Agents: ${status.agentCount}`);
    console.log(`  ✓ System Health: ${status.healthy ? '✅ Healthy' : '❌ Unhealthy'}`);
    
    // 3. Deploy additional agents
    console.log('\n🤖 Step 3: Deploying Additional Agents...');
    const specialistAgent = await orchestrator.deployAgent({
      name: 'Data-Analyst',
      type: 'specialist',
      capabilities: ['data-analysis', 'pattern-recognition', 'reporting'],
      maxConcurrentTasks: 2
    });
    console.log(`  ✓ Deployed specialist agent: ${specialistAgent.id}`);
    
    // 4. Create and submit a simple task
    console.log('\n📝 Step 4: Submitting Simple Task...');
    const simpleTask = new TaskBuilder()
      .withDescription('Analyze system performance metrics')
      .withType('analysis')
      .withPriority('medium')
      .build();
    
    const simpleTaskId = await orchestrator.submitTask(simpleTask);
    console.log(`  ✓ Task submitted: ${simpleTaskId}`);
    
    // 5. Create and submit a complex task for decomposition
    console.log('\n🔧 Step 5: Submitting Complex Task for Decomposition...');
    const complexTask = new TaskBuilder()
      .withDescription('Build, test, and deploy the ASI-Code application')
      .withType('deployment')
      .withPriority('high')
      .withMetadata({ decompose: true })
      .build();
    
    const complexTaskId = await orchestrator.submitTask(complexTask);
    console.log(`  ✓ Complex task submitted for decomposition: ${complexTaskId}`);
    
    // 6. Submit parallel tasks
    console.log('\n⚡ Step 6: Submitting Parallel Tasks...');
    const parallelTasks = [
      new TaskBuilder().withDescription('Process dataset A').withType('processing').build(),
      new TaskBuilder().withDescription('Process dataset B').withType('processing').build(),
      new TaskBuilder().withDescription('Process dataset C').withType('processing').build()
    ];
    
    const parallelTaskIds = await Promise.all(
      parallelTasks.map(task => orchestrator.submitTask(task))
    );
    console.log(`  ✓ Submitted ${parallelTaskIds.length} parallel tasks`);
    
    // 7. Create a workflow with dependencies
    console.log('\n🔄 Step 7: Creating Workflow with Dependencies...');
    const workflowTasks = [
      new TaskBuilder()
        .withDescription('Step 1: Initialize environment')
        .withType('setup')
        .withPriority('critical')
        .build(),
      
      new TaskBuilder()
        .withDescription('Step 2: Run validation')
        .withType('validation')
        .withDependencies(['step-1'])
        .build(),
      
      new TaskBuilder()
        .withDescription('Step 3: Execute main process')
        .withType('processing')
        .withDependencies(['step-2'])
        .build()
    ];
    
    // Assign IDs for dependency tracking
    workflowTasks[0].id = 'step-1';
    workflowTasks[1].id = 'step-2';
    workflowTasks[2].id = 'step-3';
    
    for (const task of workflowTasks) {
      await orchestrator.submitTask(task);
      console.log(`  ✓ Workflow step submitted: ${task.description}`);
    }
    
    // 8. Monitor system metrics
    console.log('\n📈 Step 8: System Metrics');
    await new Promise(resolve => setTimeout(resolve, 2000)); // Let some tasks process
    
    const metrics = orchestrator.getMetrics();
    console.log(`  • Task Throughput: ${metrics.taskThroughput.toFixed(2)} tasks/sec`);
    console.log(`  • Agent Utilization: ${metrics.agentUtilization.toFixed(1)}%`);
    console.log(`  • Queue Depth: ${metrics.queueDepth} tasks`);
    console.log(`  • Success Rate: ${metrics.successRate.toFixed(1)}%`);
    
    // 9. Scale agents based on load
    console.log('\n📊 Step 9: Auto-Scaling Agents...');
    if (metrics.queueDepth > 5) {
      await orchestrator.scaleAgents(status.agentCount + 2, 'worker');
      console.log(`  ✓ Scaled up to handle queue depth of ${metrics.queueDepth}`);
    }
    
    // 10. Get final status
    console.log('\n✅ Step 10: Final System Status');
    const finalStatus = orchestrator.getSystemStatus();
    console.log(`  • Total Agents: ${finalStatus.agentCount}`);
    console.log(`  • Active Tasks: ${finalStatus.activeTasks}`);
    console.log(`  • Completed Tasks: ${finalStatus.completedTasks}`);
    console.log(`  • Failed Tasks: ${finalStatus.failedTasks}`);
    console.log(`  • System Load: ${finalStatus.systemLoad.toFixed(1)}%`);
    console.log(`  • Uptime: ${(finalStatus.uptime / 1000).toFixed(1)} seconds`);
    
    // Wait a bit to see some results
    console.log('\n⏳ Waiting for tasks to complete...');
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Get some task results (non-blocking check)
    console.log('\n📋 Task Results Sample:');
    try {
      const result = await Promise.race([
        orchestrator.getTaskResult(simpleTaskId),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 1000))
      ]);
      console.log(`  ✓ Simple task result:`, result);
    } catch (e) {
      console.log(`  ⏳ Simple task still processing...`);
    }
    
    // Demonstrate agent status
    console.log('\n🤖 Agent Status:');
    const agentStatuses = orchestrator.getAgentStatuses();
    let statusCounts = { idle: 0, working: 0, busy: 0, error: 0 };
    for (const [id, status] of agentStatuses) {
      statusCounts[status] = (statusCounts[status] || 0) + 1;
    }
    console.log(`  • Idle: ${statusCounts.idle}`);
    console.log(`  • Working: ${statusCounts.working}`);
    console.log(`  • Busy: ${statusCounts.busy}`);
    console.log(`  • Error: ${statusCounts.error}`);
    
    console.log('\n' + '=' .repeat(60));
    console.log('✨ Orchestration Demo Complete!');
    console.log('\nThe ASI-Code Agent Orchestration System is fully operational.');
    console.log('Features demonstrated:');
    console.log('  ✓ Supervisor agent management');
    console.log('  ✓ Dynamic agent deployment');
    console.log('  ✓ Task submission and decomposition');
    console.log('  ✓ Parallel task execution');
    console.log('  ✓ Workflow with dependencies');
    console.log('  ✓ Auto-scaling based on load');
    console.log('  ✓ System metrics and monitoring');
    
    // Cleanup
    console.log('\n🧹 Shutting down orchestrator...');
    await orchestrator.shutdown();
    console.log('✓ Orchestrator shutdown complete');
    
  } catch (error) {
    console.error('\n❌ Demo Error:', error);
    process.exit(1);
  }
}

// Run the demo
main().catch(console.error);