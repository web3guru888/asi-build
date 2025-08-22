#!/usr/bin/env bun
/**
 * Simple test of the orchestration system without logging issues
 */

console.log('\n🚀 Testing ASI-Code Agent Orchestration System\n');
console.log('=' .repeat(60));

// Import orchestration components directly
import { Orchestrator } from './src/orchestration/orchestrator.js';
import { TaskBuilder } from './src/orchestration/task-builder.js';

async function test() {
  try {
    // Create orchestrator without logger
    console.log('Creating orchestrator...');
    const orchestrator = new Orchestrator();
    
    // Give it time to initialize
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Get status
    console.log('\n📊 System Status:');
    const status = orchestrator.getSystemStatus();
    console.log('  Supervisors:', status.supervisorCount);
    console.log('  Agents:', status.agentCount);
    console.log('  Healthy:', status.healthy);
    
    // Create a simple task
    console.log('\n📝 Creating task...');
    const task = new TaskBuilder()
      .withDescription('Test task for orchestration system')
      .withType('processing')
      .withPriority('medium')
      .build();
    
    // Submit task
    console.log('Submitting task...');
    const taskId = await orchestrator.submitTask(task);
    console.log('  Task ID:', taskId);
    
    // Get metrics
    console.log('\n📈 System Metrics:');
    const metrics = orchestrator.getMetrics();
    console.log('  Queue Depth:', metrics.queueDepth);
    console.log('  Agent Utilization:', metrics.agentUtilization + '%');
    console.log('  Success Rate:', metrics.successRate + '%');
    
    // Shutdown
    console.log('\n🧹 Shutting down...');
    await orchestrator.shutdown();
    console.log('✅ Complete!');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

test();