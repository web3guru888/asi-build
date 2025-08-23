#!/usr/bin/env bun
/**
 * Test ASI:One-Powered Agent Orchestration and Task Decomposition
 * 
 * This demonstrates using ASI:One to intelligently decompose tasks
 * and orchestrate agent execution in ASI-Code.
 */

import { readFileSync } from 'fs';

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
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

// ASI:One client for orchestration
class ASI1Orchestrator {
  private apiKey: string;
  private baseUrl: string = 'https://api.asi1.ai';
  
  constructor() {
    // Load API key from .env
    try {
      const envContent = readFileSync('.env', 'utf-8');
      const match = envContent.match(/ASI1_API_KEY=(.+)/);
      this.apiKey = match ? match[1].trim() : '';
    } catch {
      this.apiKey = process.env.ASI1_API_KEY || '';
    }
    
    if (!this.apiKey) {
      throw new Error('ASI1_API_KEY not found in .env file');
    }
  }
  
  async decomposeTask(task: string): Promise<any> {
    log('\n🤖 Asking ASI:One to decompose the task...', colors.cyan);
    
    const prompt = `You are an expert software architect and project manager. 
    
    Decompose the following task into subtasks that can be executed in parallel where possible:
    "${task}"
    
    Return ONLY a JSON object with this exact structure (no additional text):
    {
      "mainTask": "task name",
      "estimatedHours": number,
      "subtasks": [
        {
          "id": "unique-id",
          "name": "subtask name",
          "description": "what needs to be done",
          "dependencies": ["id-of-prerequisite-task"],
          "estimatedHours": number,
          "canParallel": boolean,
          "assignedAgentType": "worker|specialist|supervisor"
        }
      ],
      "executionGroups": [
        {
          "groupId": "group-1",
          "parallel": true,
          "taskIds": ["task-id-1", "task-id-2"]
        }
      ]
    }`;
    
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'asi1-extended', // Use extended for complex reasoning
        messages: [
          { role: 'system', content: 'You are a task decomposition specialist. Always return valid JSON only.' },
          { role: 'user', content: prompt }
        ],
        temperature: 0.3, // Lower temperature for structured output
        max_tokens: 2000
      })
    });
    
    if (!response.ok) {
      throw new Error(`ASI:One API error: ${response.status}`);
    }
    
    const data = await response.json();
    const content = data.choices[0].message.content;
    
    // Parse JSON from response
    try {
      // Try to extract JSON if wrapped in markdown
      const jsonMatch = content.match(/```json\n?([\s\S]*?)\n?```/) || content.match(/\{[\s\S]*\}/);
      const jsonStr = jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : content;
      return JSON.parse(jsonStr);
    } catch (e) {
      log('Failed to parse JSON, raw response:', colors.yellow);
      console.log(content);
      throw new Error('Invalid JSON response from ASI:One');
    }
  }
  
  async orchestrateExecution(decomposition: any): Promise<string> {
    log('\n🎯 Asking ASI:One to create execution strategy...', colors.cyan);
    
    const prompt = `Given this task decomposition:
    ${JSON.stringify(decomposition, null, 2)}
    
    Create an optimal execution strategy that maximizes parallelism while respecting dependencies.
    Consider resource allocation, agent capabilities, and timing.
    
    Provide a brief execution plan in plain text (2-3 paragraphs).`;
    
    const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'asi1-mini',
        messages: [
          { role: 'system', content: 'You are an execution strategy specialist.' },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 500
      })
    });
    
    if (!response.ok) {
      throw new Error(`ASI:One API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.choices[0].message.content;
  }
}

// Main demonstration
async function demonstrateASI1Orchestration() {
  log('\n' + '='.repeat(70), colors.bright);
  log('ASI:One-Powered Task Decomposition & Agent Orchestration', colors.bright + colors.cyan);
  log('='.repeat(70) + '\n', colors.bright);
  
  try {
    const orchestrator = new ASI1Orchestrator();
    
    // ====================================
    // PHASE 1: Define Complex Task
    // ====================================
    log('📋 Phase 1: Defining Complex Task', colors.yellow);
    
    const complexTask = "Build a real-time collaborative code editor with syntax highlighting, " +
                       "WebSocket-based synchronization, user authentication, and PostgreSQL persistence. " +
                       "Include Docker deployment configuration and comprehensive testing.";
    
    log(`\nTask: "${complexTask}"`, colors.bright);
    
    // ====================================
    // PHASE 2: ASI:One Task Decomposition
    // ====================================
    log('\n🔨 Phase 2: Task Decomposition by ASI:One', colors.yellow);
    
    const decomposition = await orchestrator.decomposeTask(complexTask);
    
    log('\n✅ ASI:One decomposed the task:', colors.green);
    log(`\n  Main Task: ${decomposition.mainTask}`, colors.cyan);
    log(`  Estimated Hours: ${decomposition.estimatedHours}`, colors.cyan);
    log(`  Subtasks: ${decomposition.subtasks.length}`, colors.cyan);
    
    log('\n  Subtask Breakdown:', colors.bright);
    decomposition.subtasks.forEach((task: any, i: number) => {
      const deps = task.dependencies.length > 0 ? `deps: ${task.dependencies.join(', ')}` : 'no dependencies';
      const parallel = task.canParallel ? '⚡' : '📍';
      log(`    ${i + 1}. ${parallel} ${task.name} (${task.estimatedHours}h, ${deps})`, colors.blue);
    });
    
    // ====================================
    // PHASE 3: Execution Groups
    // ====================================
    log('\n⚡ Phase 3: Parallel Execution Groups', colors.yellow);
    
    if (decomposition.executionGroups) {
      log('\n  Execution Strategy:', colors.bright);
      decomposition.executionGroups.forEach((group: any, i: number) => {
        const type = group.parallel ? 'Parallel' : 'Sequential';
        log(`\n    Group ${i + 1} (${type}):`, colors.magenta);
        group.taskIds.forEach((taskId: string) => {
          const task = decomposition.subtasks.find((t: any) => t.id === taskId);
          if (task) {
            log(`      → ${task.name}`, colors.cyan);
          }
        });
      });
    }
    
    // ====================================
    // PHASE 4: Orchestration Strategy
    // ====================================
    log('\n🎯 Phase 4: ASI:One Orchestration Strategy', colors.yellow);
    
    const strategy = await orchestrator.orchestrateExecution(decomposition);
    
    log('\n  Strategy from ASI:One:', colors.bright);
    // Format the strategy with proper indentation
    const strategyLines = strategy.split('\n');
    strategyLines.forEach(line => {
      if (line.trim()) {
        log(`    ${line}`, colors.cyan);
      }
    });
    
    // ====================================
    // PHASE 5: Simulated Execution
    // ====================================
    log('\n🏃 Phase 5: Simulating Agent Execution', colors.yellow);
    
    // Create virtual agents
    const agents = {
      workers: ['worker-1', 'worker-2', 'worker-3'],
      specialists: ['specialist-db', 'specialist-ui'],
      supervisors: ['supervisor-main']
    };
    
    log('\n  Available Agents:', colors.bright);
    log(`    Workers: ${agents.workers.join(', ')}`, colors.blue);
    log(`    Specialists: ${agents.specialists.join(', ')}`, colors.blue);
    log(`    Supervisors: ${agents.supervisors.join(', ')}`, colors.blue);
    
    // Simulate execution based on groups
    if (decomposition.executionGroups) {
      for (const [index, group] of decomposition.executionGroups.entries()) {
        log(`\n  Executing Group ${index + 1}:`, colors.magenta);
        
        const tasks = group.taskIds.map((id: string) => 
          decomposition.subtasks.find((t: any) => t.id === id)
        ).filter(Boolean);
        
        if (group.parallel) {
          // Parallel execution
          await Promise.all(tasks.map(async (task: any, i: number) => {
            const agentType = task.assignedAgentType || 'worker';
            const agentPool = agentType === 'specialist' ? agents.specialists : 
                             agentType === 'supervisor' ? agents.supervisors : 
                             agents.workers;
            const agent = agentPool[i % agentPool.length];
            
            log(`    ⏳ ${task.name} → ${agent}`, colors.cyan);
            await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
            log(`    ✅ ${task.name} completed by ${agent}`, colors.green);
          }));
        } else {
          // Sequential execution
          for (const task of tasks) {
            const agentType = task.assignedAgentType || 'worker';
            const agentPool = agentType === 'specialist' ? agents.specialists : 
                             agentType === 'supervisor' ? agents.supervisors : 
                             agents.workers;
            const agent = agentPool[0];
            
            log(`    ⏳ ${task.name} → ${agent}`, colors.cyan);
            await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
            log(`    ✅ ${task.name} completed by ${agent}`, colors.green);
          }
        }
      }
    }
    
    // ====================================
    // PHASE 6: Results Summary
    // ====================================
    log('\n📊 Phase 6: Orchestration Results', colors.yellow);
    
    const parallelGroups = decomposition.executionGroups?.filter((g: any) => g.parallel).length || 0;
    const sequentialGroups = decomposition.executionGroups?.filter((g: any) => !g.parallel).length || 0;
    const totalSubtasks = decomposition.subtasks.length;
    const parallelTasks = decomposition.subtasks.filter((t: any) => t.canParallel).length;
    
    log('\n  Statistics:', colors.bright);
    log(`    • Total Subtasks: ${totalSubtasks}`, colors.cyan);
    log(`    • Parallel Tasks: ${parallelTasks} (${Math.round(parallelTasks/totalSubtasks*100)}%)`, colors.cyan);
    log(`    • Execution Groups: ${parallelGroups} parallel, ${sequentialGroups} sequential`, colors.cyan);
    log(`    • Estimated Time (sequential): ${decomposition.estimatedHours} hours`, colors.cyan);
    
    // Calculate parallel time savings
    const parallelTime = decomposition.executionGroups?.reduce((acc: number, group: any) => {
      const groupTasks = group.taskIds.map((id: string) => 
        decomposition.subtasks.find((t: any) => t.id === id)
      ).filter(Boolean);
      
      if (group.parallel) {
        // Parallel group takes as long as the longest task
        return acc + Math.max(...groupTasks.map((t: any) => t.estimatedHours || 0));
      } else {
        // Sequential group is sum of all tasks
        return acc + groupTasks.reduce((sum: number, t: any) => sum + (t.estimatedHours || 0), 0);
      }
    }, 0) || decomposition.estimatedHours;
    
    log(`    • Estimated Time (parallel): ${Math.round(parallelTime)} hours`, colors.green);
    log(`    • Time Saved: ${Math.round(decomposition.estimatedHours - parallelTime)} hours (${Math.round((decomposition.estimatedHours - parallelTime)/decomposition.estimatedHours*100)}% improvement)`, colors.bright + colors.green);
    
    log('\n✨ ASI:One-powered orchestration completed successfully!', colors.bright + colors.green);
    
  } catch (error) {
    log(`\n❌ Error: ${error}`, colors.red);
    console.error(error);
  }
}

// Run the demonstration
demonstrateASI1Orchestration()
  .then(() => {
    log('\n🎉 Demonstration completed!\n', colors.bright + colors.green);
    process.exit(0);
  })
  .catch((error) => {
    log(`\n💥 Fatal error: ${error}\n`, colors.bright + colors.red);
    process.exit(1);
  });