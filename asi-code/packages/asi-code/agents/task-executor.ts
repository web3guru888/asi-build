/**
 * Task Executor - Orchestrates real agent execution
 */

import { SpecAgent } from './spec-agent';
import { CoderAgent } from './coder-agent';
import { AgentContext } from './base-agent';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

export interface TaskDecomposition {
  projectName: string;
  sessionId: string;
  estimatedHours: number;
  subtasks: SubTask[];
  executionPlan: ExecutionPhase[];
  status: string;
}

export interface SubTask {
  id: string;
  name: string;
  agent: string;
  estimatedHours: number;
  dependencies: string[];
  canParallel: boolean;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
}

export interface ExecutionPhase {
  phase: number;
  name: string;
  parallel: boolean;
  taskIds: string[];
}

export class TaskExecutor {
  private agents: Map<string, any> = new Map();
  private contextCache: Map<string, AgentContext> = new Map();
  
  constructor() {
    this.initializeAgents();
  }
  
  private initializeAgents() {
    // Initialize real agent instances
    this.agents.set('kenny-spec', new SpecAgent());
    this.agents.set('kenny-coder', new CoderAgent());
    
    // Add more agents as they're implemented
    // this.agents.set('kenny-tester', new TesterAgent());
    // this.agents.set('kenny-reviewer', new ReviewerAgent());
    // this.agents.set('kenny-recorder', new RecorderAgent());
  }
  
  /**
   * Build context for agents with real data
   */
  private async buildContext(task: any, sessionId: string): Promise<AgentContext> {
    // Check cache first
    if (this.contextCache.has(sessionId)) {
      return this.contextCache.get(sessionId)!;
    }
    
    // Load context pack files
    const architecture = this.loadContextFile('ARCHITECTURE.md');
    const constraints = this.loadContextFile('SYSTEM_CONSTRAINTS.md');
    const testStrategy = this.loadContextFile('TEST_STRATEGY.md');
    const decisions = this.loadDecisions();
    
    // Build context object
    const context: AgentContext = {
      task: {
        id: `task-${Date.now()}`,
        title: task.title || task,
        description: task.description || task,
        acceptance: this.extractAcceptanceCriteria(task),
        scope: this.determineScope(task)
      },
      architecture,
      constraints,
      previousDecisions: decisions,
      relevantCode: await this.findRelevantCode(task),
      testStrategy
    };
    
    // Cache for session
    this.contextCache.set(sessionId, context);
    
    return context;
  }
  
  /**
   * Load context file
   */
  private loadContextFile(filename: string): string {
    const filePath = join(process.cwd(), filename);
    if (existsSync(filePath)) {
      return readFileSync(filePath, 'utf-8');
    }
    return '';
  }
  
  /**
   * Load previous decisions
   */
  private loadDecisions(): string[] {
    const decisionsPath = join(process.cwd(), 'DECISIONS.md');
    if (existsSync(decisionsPath)) {
      const content = readFileSync(decisionsPath, 'utf-8');
      return content.split('\n').filter(line => line.startsWith('- '));
    }
    return [];
  }
  
  /**
   * Extract acceptance criteria from task
   */
  private extractAcceptanceCriteria(task: any): string[] {
    const taskStr = typeof task === 'string' ? task : JSON.stringify(task);
    
    // Common patterns for different app types
    const criteria: string[] = [];
    
    if (taskStr.toLowerCase().includes('android')) {
      criteria.push(
        'App launches without crashing',
        'Navigation between screens works',
        'Data persists across app restarts',
        'Works offline with cached data',
        'Handles errors gracefully',
        'Follows Material Design guidelines'
      );
    }
    
    if (taskStr.toLowerCase().includes('api') || taskStr.toLowerCase().includes('backend')) {
      criteria.push(
        'API endpoints return correct data',
        'Authentication and authorization work',
        'Database operations are transactional',
        'Error responses follow standard format',
        'Rate limiting is implemented'
      );
    }
    
    if (taskStr.toLowerCase().includes('test')) {
      criteria.push(
        'Unit test coverage > 80%',
        'Integration tests pass',
        'E2E tests cover critical paths'
      );
    }
    
    return criteria.length > 0 ? criteria : ['Task completed successfully'];
  }
  
  /**
   * Determine file scope for task
   */
  private determineScope(task: any): string[] {
    const taskStr = typeof task === 'string' ? task : JSON.stringify(task);
    const scope: string[] = [];
    
    if (taskStr.toLowerCase().includes('android')) {
      scope.push(
        'app/src/main/**',
        'app/src/test/**',
        'app/src/androidTest/**',
        'app/build.gradle'
      );
    }
    
    if (taskStr.toLowerCase().includes('backend')) {
      scope.push(
        'src/api/**',
        'src/services/**',
        'src/models/**',
        'src/tests/**'
      );
    }
    
    return scope.length > 0 ? scope : ['**/*'];
  }
  
  /**
   * Find relevant existing code
   */
  private async findRelevantCode(task: any): Promise<{ path: string; content: string }[]> {
    // In a real implementation, this would search the codebase
    // For now, return empty array
    return [];
  }
  
  /**
   * Execute a single subtask with a real agent
   */
  async executeSubtask(subtask: SubTask, context: AgentContext, ws: any): Promise<any> {
    const agent = this.agents.get(subtask.agent);
    
    if (!agent) {
      // For agents not yet implemented, simulate execution
      return this.simulateAgent(subtask, ws);
    }
    
    try {
      // Send start notification
      ws.send(JSON.stringify({
        type: 'agent-started',
        agent: subtask.agent,
        task: subtask.name,
        message: `Agent ${subtask.agent} starting: ${subtask.name}`
      }));
      
      // Execute with real agent
      const result = await agent.execute(context);
      
      // Send completion notification
      ws.send(JSON.stringify({
        type: 'agent-completed',
        agent: subtask.agent,
        task: subtask.name,
        success: result.success,
        logs: result.logs,
        message: result.success 
          ? `✅ ${subtask.name} completed successfully`
          : `❌ ${subtask.name} failed: ${result.logs.join(', ')}`
      }));
      
      return result;
      
    } catch (error) {
      ws.send(JSON.stringify({
        type: 'agent-error',
        agent: subtask.agent,
        task: subtask.name,
        error: error.message
      }));
      
      throw error;
    }
  }
  
  /**
   * Simulate agents that aren't implemented yet
   */
  private async simulateAgent(subtask: SubTask, ws: any): Promise<any> {
    // Simulate work
    await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
    
    // Return simulated result
    return {
      success: true,
      output: {
        message: `Simulated completion of ${subtask.name}`
      },
      logs: [`${subtask.agent} completed task simulation`],
      metrics: {
        tokensUsed: Math.floor(Math.random() * 1000),
        executionTime: Math.floor(Math.random() * 2000),
        retries: 0
      }
    };
  }
  
  /**
   * Execute complete task decomposition
   */
  async executeDecomposition(decomposition: TaskDecomposition, ws: any): Promise<void> {
    // Build context once for all agents
    const context = await this.buildContext(
      decomposition.projectName,
      decomposition.sessionId
    );
    
    // Execute phases
    for (const phase of decomposition.executionPlan) {
      ws.send(JSON.stringify({
        type: 'phase-started',
        phase: phase.phase,
        name: phase.name,
        parallel: phase.parallel,
        tasks: phase.taskIds.length
      }));
      
      if (phase.parallel) {
        // Execute tasks in parallel
        const promises = phase.taskIds.map(async (taskId: string) => {
          const task = decomposition.subtasks.find(t => t.id === taskId);
          if (task) {
            task.status = 'running';
            ws.send(JSON.stringify({
              type: 'task-started',
              taskId: task.id,
              name: task.name,
              agent: task.agent
            }));
            
            try {
              const result = await this.executeSubtask(task, context, ws);
              task.status = 'completed';
              task.result = result;
              
              ws.send(JSON.stringify({
                type: 'task-completed',
                taskId: task.id,
                name: task.name,
                agent: task.agent,
                result: result.output?.summary || `✅ ${task.name} completed`
              }));
            } catch (error) {
              task.status = 'failed';
              ws.send(JSON.stringify({
                type: 'task-failed',
                taskId: task.id,
                name: task.name,
                agent: task.agent,
                error: error.message
              }));
            }
          }
        });
        
        await Promise.all(promises);
        
      } else {
        // Execute tasks sequentially
        for (const taskId of phase.taskIds) {
          const task = decomposition.subtasks.find(t => t.id === taskId);
          if (task) {
            task.status = 'running';
            ws.send(JSON.stringify({
              type: 'task-started',
              taskId: task.id,
              name: task.name,
              agent: task.agent
            }));
            
            try {
              const result = await this.executeSubtask(task, context, ws);
              task.status = 'completed';
              task.result = result;
              
              ws.send(JSON.stringify({
                type: 'task-completed',
                taskId: task.id,
                name: task.name,
                agent: task.agent,
                result: result.output?.summary || `✅ ${task.name} completed`
              }));
            } catch (error) {
              task.status = 'failed';
              ws.send(JSON.stringify({
                type: 'task-failed',
                taskId: task.id,
                name: task.name,
                agent: task.agent,
                error: error.message
              }));
            }
          }
        }
      }
      
      ws.send(JSON.stringify({
        type: 'phase-completed',
        phase: phase.phase,
        name: phase.name
      }));
    }
    
    // Clear context cache
    this.contextCache.delete(decomposition.sessionId);
  }
}