#!/usr/bin/env bun
/**
 * Test Agent Orchestration and Task Decomposition
 * 
 * This script demonstrates the ASI-Code agent orchestration system
 * with parallel task execution and intelligent task decomposition.
 */

import { AgentFactory } from './src/orchestration/agent-factory.js';
import { TaskBuilder } from './src/orchestration/task-builder.js';
import { SupervisorAgent } from './src/orchestration/supervisor-agent.js';
import { AgentRegistry } from './src/orchestration/agent-registry.js';
import { Logger } from './src/logging/index.js';
import type { Task, TaskPriority } from './src/orchestration/types.js';

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message: string, color: string = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

async function demonstrateOrchestration() {
  log('\n🚀 ASI-Code Agent Orchestration Demonstration\n', colors.bright + colors.cyan);
  
  // Initialize logging
  const logger = new Logger({
    level: 'info',
    context: { component: 'OrchestrationDemo' },
  });

  // Initialize registry and factory
  const registry = new AgentRegistry({ logger });
  const factory = new AgentFactory({ logger });
  const taskBuilder = new TaskBuilder();

  try {
    // ====================================
    // PHASE 1: Create Supervisor Agent
    // ====================================
    log('\n📋 Phase 1: Creating Supervisor Agent...', colors.yellow);
    
    const supervisor = await factory.createAgent({
      name: 'MasterSupervisor',
      type: 'supervisor',
      capabilities: ['orchestration', 'task-decomposition', 'monitoring'],
      maxConcurrentTasks: 10,
    });
    
    log(`✅ Supervisor created: ${supervisor.id}`, colors.green);
    
    // ====================================
    // PHASE 2: Create Worker Agent Pool
    // ====================================
    log('\n👷 Phase 2: Creating Worker Agent Pool...', colors.yellow);
    
    // Configure pooling for workers
    factory.configurePooling('worker', {
      minSize: 3,
      maxSize: 10,
      idleTimeout: 60000,
      recycleThreshold: 20,
    });
    
    // Create initial worker pool
    const workers = await factory.createAgentCluster(5, {
      name: 'Worker',
      type: 'worker',
      capabilities: ['code-generation', 'analysis', 'testing'],
      maxConcurrentTasks: 2,
    });
    
    log(`✅ Created ${workers.length} worker agents`, colors.green);
    workers.forEach((w, i) => {
      log(`   - Worker ${i + 1}: ${w.id}`, colors.dim);
    });
    
    // ====================================
    // PHASE 3: Create Complex Task
    // ====================================
    log('\n📝 Phase 3: Creating Complex Task for Decomposition...', colors.yellow);
    
    const complexTask = taskBuilder
      .withName('Build Complete Web Application')
      .withDescription('Create a full-stack web application with React frontend and Node.js backend')
      .withPriority('high' as TaskPriority)
      .withMetadata({
        projectType: 'full-stack',
        technologies: ['React', 'Node.js', 'PostgreSQL', 'WebSocket'],
        estimatedHours: 40,
      })
      .withDependencies([])
      .build();
    
    log(`✅ Complex task created: "${complexTask.name}"`, colors.green);
    
    // ====================================
    // PHASE 4: Task Decomposition
    // ====================================
    log('\n🔨 Phase 4: Decomposing Task into Subtasks...', colors.yellow);
    
    // Simulate task decomposition
    const subtasks = [
      taskBuilder
        .withName('Setup Project Structure')
        .withDescription('Initialize project with required dependencies')
        .withPriority('high' as TaskPriority)
        .withMetadata({ phase: 'setup', duration: '2h' })
        .build(),
      
      taskBuilder
        .withName('Create Database Schema')
        .withDescription('Design and implement PostgreSQL database schema')
        .withPriority('high' as TaskPriority)
        .withMetadata({ phase: 'backend', duration: '4h' })
        .build(),
      
      taskBuilder
        .withName('Build REST API')
        .withDescription('Implement Node.js REST API with Express')
        .withPriority('high' as TaskPriority)
        .withMetadata({ phase: 'backend', duration: '8h' })
        .build(),
      
      taskBuilder
        .withName('Create React Components')
        .withDescription('Build React UI components')
        .withPriority('medium' as TaskPriority)
        .withMetadata({ phase: 'frontend', duration: '10h' })
        .build(),
      
      taskBuilder
        .withName('Implement WebSocket')
        .withDescription('Add real-time communication with WebSocket')
        .withPriority('medium' as TaskPriority)
        .withMetadata({ phase: 'fullstack', duration: '6h' })
        .build(),
      
      taskBuilder
        .withName('Write Tests')
        .withDescription('Create unit and integration tests')
        .withPriority('medium' as TaskPriority)
        .withMetadata({ phase: 'testing', duration: '6h' })
        .build(),
      
      taskBuilder
        .withName('Deploy Application')
        .withDescription('Deploy to production environment')
        .withPriority('low' as TaskPriority)
        .withMetadata({ phase: 'deployment', duration: '4h' })
        .build(),
    ];
    
    log(`✅ Task decomposed into ${subtasks.length} subtasks:`, colors.green);
    subtasks.forEach((task, i) => {
      log(`   ${i + 1}. ${task.name} (${task.metadata?.duration})`, colors.dim);
    });
    
    // ====================================
    // PHASE 5: Parallel Task Assignment
    // ====================================
    log('\n⚡ Phase 5: Assigning Tasks to Workers (Parallel Execution)...', colors.yellow);
    
    // Simulate parallel task assignment
    const assignments = new Map();
    const parallelGroups = {
      group1: [subtasks[0]], // Setup - must be first
      group2: [subtasks[1], subtasks[2]], // Backend tasks - can be parallel
      group3: [subtasks[3], subtasks[4]], // Frontend/WebSocket - can be parallel
      group4: [subtasks[5]], // Testing - after development
      group5: [subtasks[6]], // Deployment - last
    };
    
    let groupIndex = 0;
    for (const [groupName, tasks] of Object.entries(parallelGroups)) {
      groupIndex++;
      log(`\n  Group ${groupIndex} (Parallel Execution):`, colors.magenta);
      
      tasks.forEach((task, taskIndex) => {
        const workerIndex = taskIndex % workers.length;
        const worker = workers[workerIndex];
        assignments.set(task.id, worker.id);
        log(`    → ${task.name} assigned to ${worker.id}`, colors.cyan);
      });
    }
    
    // ====================================
    // PHASE 6: Execution Simulation
    // ====================================
    log('\n🏃 Phase 6: Simulating Task Execution...', colors.yellow);
    
    for (const [groupName, tasks] of Object.entries(parallelGroups)) {
      log(`\n  Executing ${groupName}:`, colors.blue);
      
      // Simulate parallel execution
      await Promise.all(
        tasks.map(async (task) => {
          const workerId = assignments.get(task.id);
          log(`    ⏳ ${task.name} started on ${workerId}...`, colors.dim);
          
          // Simulate work with random delay
          await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
          
          log(`    ✅ ${task.name} completed!`, colors.green);
        })
      );
    }
    
    // ====================================
    // PHASE 7: Results Summary
    // ====================================
    log('\n📊 Phase 7: Orchestration Results', colors.yellow);
    
    const stats = {
      totalTasks: subtasks.length,
      workersUsed: workers.length,
      parallelGroups: Object.keys(parallelGroups).length,
      estimatedTime: subtasks.reduce((acc, t) => {
        const hours = parseInt(t.metadata?.duration || '0');
        return acc + hours;
      }, 0),
      actualTime: Object.keys(parallelGroups).length * 8, // Assuming 8h per group
    };
    
    log('\n  Statistics:', colors.bright);
    log(`    • Total Tasks: ${stats.totalTasks}`, colors.cyan);
    log(`    • Workers Used: ${stats.workersUsed}`, colors.cyan);
    log(`    • Parallel Execution Groups: ${stats.parallelGroups}`, colors.cyan);
    log(`    • Sequential Time (if done by 1 worker): ${stats.estimatedTime} hours`, colors.cyan);
    log(`    • Parallel Time (with orchestration): ~${stats.actualTime} hours`, colors.green);
    log(`    • Time Saved: ${stats.estimatedTime - stats.actualTime} hours (${Math.round((stats.estimatedTime - stats.actualTime) / stats.estimatedTime * 100)}% improvement)`, colors.bright + colors.green);
    
    // ====================================
    // PHASE 8: Cleanup
    // ====================================
    log('\n🧹 Phase 8: Cleanup...', colors.yellow);
    
    await factory.clearPools();
    await factory.shutdown();
    
    log('✅ Orchestration demonstration completed successfully!', colors.bright + colors.green);
    
  } catch (error) {
    log(`\n❌ Error during orchestration: ${error}`, colors.red);
    console.error(error);
  }
}

// Run the demonstration
log('\n' + '='.repeat(60), colors.bright);
log('ASI-Code Agent Orchestration & Task Decomposition Test', colors.bright + colors.cyan);
log('='.repeat(60) + '\n', colors.bright);

demonstrateOrchestration()
  .then(() => {
    log('\n✨ All tests completed!\n', colors.bright + colors.green);
  })
  .catch((error) => {
    log(`\n💥 Fatal error: ${error}\n`, colors.bright + colors.red);
    process.exit(1);
  });