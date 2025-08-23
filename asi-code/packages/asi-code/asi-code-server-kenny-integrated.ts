#!/usr/bin/env bun
/**
 * 🚀 ASI-Code Server with KENNY Integration
 * 
 * Complete integration of:
 * - ASI:One chat capabilities
 * - KENNY task decomposition and orchestration
 * - Parallel agent execution
 * - WebSocket real-time communication
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from 'bun';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { IntelligentGenerator } from './agents/intelligent-generator';

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

// ================================
// KENNY INTEGRATION PATTERN
// ================================
class KennyIntegration {
  private messageBus: Map<string, any[]> = new Map();
  private stateManager: Map<string, any> = new Map();
  private subsystems: Map<string, any> = new Map();
  
  constructor() {
    log('🔗 Initializing Kenny Integration Pattern...', colors.cyan);
  }
  
  integrate(subsystem: any, name: string) {
    this.subsystems.set(name, subsystem);
    log(`✅ Integrated subsystem: ${name}`, colors.green);
    return subsystem;
  }
  
  broadcast(event: string, data: any) {
    const listeners = this.messageBus.get(event) || [];
    listeners.forEach(listener => listener(data));
  }
}

// ================================
// KENNY ORCHESTRATOR
// ================================
class KennyOrchestrator {
  private integration: KennyIntegration;
  private agentPool: Map<string, any> = new Map();
  private activeExecutions: Map<string, any> = new Map();
  private codeGenerator: IntelligentGenerator;
  
  constructor() {
    this.integration = new KennyIntegration();
    this.codeGenerator = new IntelligentGenerator();
    this.initializeAgentPool();
  }
  
  private initializeAgentPool() {
    // Kenny's agent force
    const agents = [
      { id: 'kenny-prime', type: 'supervisor', capabilities: ['orchestration', 'task-decomposition'] },
      { id: 'kenny-architect', type: 'specialist', capabilities: ['system-design', 'architecture'] },
      { id: 'kenny-security', type: 'specialist', capabilities: ['authentication', 'security'] },
      { id: 'kenny-database', type: 'specialist', capabilities: ['database', 'persistence'] },
      { id: 'kenny-frontend', type: 'specialist', capabilities: ['ui', 'react', 'websocket'] },
      { id: 'kenny-backend', type: 'specialist', capabilities: ['api', 'server', 'integration'] },
      { id: 'kenny-worker-1', type: 'worker', capabilities: ['code-generation', 'testing'] },
      { id: 'kenny-worker-2', type: 'worker', capabilities: ['code-generation', 'documentation'] },
      { id: 'kenny-worker-3', type: 'worker', capabilities: ['code-generation', 'deployment'] },
    ];
    
    agents.forEach(agent => {
      this.agentPool.set(agent.id, agent);
    });
    
    log(`📋 Initialized ${agents.length} Kenny agents`, colors.cyan);
  }
  
  async decomposeTask(task: string, sessionId: string): Promise<any> {
    log(`🔍 KENNY analyzing task for session ${sessionId}`, colors.cyan);
    
    // Simulate ASI:One task decomposition
    const decomposition = {
      projectName: "Task Decomposition",
      originalTask: task,  // Store original task for IntelligentGenerator
      sessionId,
      estimatedHours: 0,
      subtasks: [],
      executionPlan: [],
      status: 'decomposing'
    };
    
    // Parse task for keywords to determine complexity
    const keywords = {
      website: ['frontend', 'backend', 'database', 'deployment'],
      api: ['backend', 'database', 'authentication'],
      chat: ['websocket', 'frontend', 'backend', 'database'],
      dashboard: ['frontend', 'api', 'database', 'visualization'],
      android: ['mobile', 'java', 'kotlin', 'ui', 'api'],
      ios: ['mobile', 'swift', 'ui', 'api'],
      mobile: ['ui', 'api', 'native', 'deployment']
    };
    
    // Generate subtasks based on task content
    const subtasks = [];
    let taskId = 1;
    
    // Always start with architecture
    subtasks.push({
      id: `kenny-task-${taskId++}`,
      name: 'System Architecture Design',
      agent: 'kenny-architect',
      estimatedHours: 4,
      dependencies: [],
      canParallel: false,
      status: 'pending'
    });
    
    // Add relevant subtasks based on keywords
    const lowerTask = task.toLowerCase();
    
    if (lowerTask.includes('android') || lowerTask.includes('mobile')) {
      // Android app specific tasks
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Android Project Setup & Configuration',
        agent: 'kenny-backend',
        estimatedHours: 4,
        dependencies: ['kenny-task-1'],
        canParallel: false,
        status: 'pending'
      });
      
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Android UI/UX Implementation',
        agent: 'kenny-frontend',
        estimatedHours: 16,
        dependencies: [`kenny-task-${taskId-1}`],
        canParallel: true,
        status: 'pending'
      });
      
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'ASI Integration & API Client',
        agent: 'kenny-backend',
        estimatedHours: 12,
        dependencies: [`kenny-task-${taskId-2}`],
        canParallel: true,
        status: 'pending'
      });
      
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Local Database & Offline Support',
        agent: 'kenny-database',
        estimatedHours: 8,
        dependencies: [`kenny-task-${taskId-3}`],
        canParallel: true,
        status: 'pending'
      });
      
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Security & Authentication',
        agent: 'kenny-security',
        estimatedHours: 10,
        dependencies: [`kenny-task-${taskId-4}`],
        canParallel: true,
        status: 'pending'
      });
      
    } else if (lowerTask.includes('websocket')) {
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'WebSocket Server Implementation',
        agent: 'kenny-backend',
        estimatedHours: 8,
        dependencies: ['kenny-task-1'],
        canParallel: true,
        status: 'pending'
      });
    } else if (lowerTask.includes('react') || lowerTask.includes('frontend')) {
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'React Component Development',
        agent: 'kenny-frontend',
        estimatedHours: 12,
        dependencies: ['kenny-task-1'],
        canParallel: true,
        status: 'pending'
      });
    } else if (lowerTask.includes('database') || lowerTask.includes('backend')) {
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Database Schema & API',
        agent: 'kenny-database',
        estimatedHours: 10,
        dependencies: ['kenny-task-1'],
        canParallel: true,
        status: 'pending'
      });
    } else if (lowerTask.includes('auth')) {
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Authentication System',
        agent: 'kenny-security',
        estimatedHours: 6,
        dependencies: ['kenny-task-1'],
        canParallel: true,
        status: 'pending'
      });
    } else {
      // Generic task decomposition
      subtasks.push({
        id: `kenny-task-${taskId++}`,
        name: 'Core Implementation',
        agent: 'kenny-backend',
        estimatedHours: 8,
        dependencies: ['kenny-task-1'],
        canParallel: true,
        status: 'pending'
      });
    }
    
    // Add testing and deployment
    subtasks.push({
      id: `kenny-task-${taskId++}`,
      name: 'Testing & Quality Assurance',
      agent: 'kenny-worker-1',
      estimatedHours: 8,
      dependencies: subtasks.slice(1).map(t => t.id),
      canParallel: false,
      status: 'pending'
    });
    
    subtasks.push({
      id: `kenny-task-${taskId++}`,
      name: 'Documentation & Deployment',
      agent: 'kenny-worker-2',
      estimatedHours: 4,
      dependencies: [`kenny-task-${taskId-2}`],
      canParallel: false,
      status: 'pending'
    });
    
    decomposition.subtasks = subtasks;
    decomposition.estimatedHours = subtasks.reduce((sum, t) => sum + t.estimatedHours, 0);
    
    // Create execution plan
    const phases = [];
    
    // Phase 1: Architecture (sequential)
    phases.push({
      phase: 1,
      name: 'Foundation',
      parallel: false,
      taskIds: ['kenny-task-1']
    });
    
    // Phase 2: Setup phase for Android
    const setupTasks = subtasks
      .filter(t => t.dependencies.includes('kenny-task-1') && !t.canParallel)
      .map(t => t.id);
    
    if (setupTasks.length > 0) {
      phases.push({
        phase: 2,
        name: 'Project Setup',
        parallel: false,
        taskIds: setupTasks
      });
    }
    
    // Phase 3: Parallel development
    const parallelTasks = subtasks
      .filter(t => t.canParallel && !t.name.includes('Testing') && !t.name.includes('Documentation'))
      .map(t => t.id);
    
    if (parallelTasks.length > 0) {
      phases.push({
        phase: 3,
        name: 'Parallel Development',
        parallel: true,
        taskIds: parallelTasks
      });
    }
    
    // Phase 4: Testing and deployment (sequential)
    const finalTasks = subtasks
      .filter(t => t.name.includes('Testing') || t.name.includes('Documentation'))
      .map(t => t.id);
    
    finalTasks.forEach((taskId, index) => {
      phases.push({
        phase: phases.length + 1,
        name: index === 0 ? 'Testing' : 'Deployment',
        parallel: false,
        taskIds: [taskId]
      });
    });
    
    decomposition.executionPlan = phases;
    decomposition.status = 'ready';
    
    return decomposition;
  }
  
  async executeTask(decomposition: any, ws: any): Promise<void> {
    const executionId = `exec-${Date.now()}`;
    this.activeExecutions.set(executionId, { decomposition, status: 'running' });
    
    ws.send(JSON.stringify({
      type: 'orchestration-started',
      executionId,
      totalPhases: decomposition.executionPlan.length,
      estimatedHours: decomposition.estimatedHours
    }));
    
    try {
      // Execute simulation with visual feedback
      await this.simulateExecution(decomposition, ws);
      
      // Generate REAL code files using IntelligentGenerator
      ws.send(JSON.stringify({
        type: 'code-generation',
        message: '🧠 Generating project files using ASI1 intelligence...'
      }));
      
      // Get the original task from decomposition
      const originalTask = decomposition.originalTask || 
                          decomposition.projectName || 
                          'Build a project';
      
      const result = await this.codeGenerator.generateProject(
        originalTask,
        decomposition.sessionId
      );
      
      if (result.success) {
        ws.send(JSON.stringify({
          type: 'orchestration-completed',
          executionId,
          totalTasks: decomposition.subtasks.length,
          completedTasks: decomposition.subtasks.filter((t: any) => t.status === 'completed').length,
          message: `🚀 All tasks completed! Generated ${result.files.length} files in /generated/projects/${decomposition.sessionId}`,
          outputPath: `/generated/projects/${decomposition.sessionId}`,
          filesGenerated: result.files
        }));
      } else {
        ws.send(JSON.stringify({
          type: 'orchestration-completed',
          executionId,
          totalTasks: decomposition.subtasks.length,
          completedTasks: decomposition.subtasks.filter((t: any) => t.status === 'completed').length,
          message: '🚀 Tasks completed (simulation only - code generation failed)',
        }));
      }
      
      this.activeExecutions.set(executionId, { decomposition, status: 'completed' });
      
    } catch (error) {
      this.activeExecutions.set(executionId, { decomposition, status: 'failed' });
      
      ws.send(JSON.stringify({
        type: 'orchestration-failed',
        executionId,
        error: error.message,
        message: '❌ Orchestration failed. Check logs for details.'
      }));
    }
  }
  
  private async simulateExecution(decomposition: any, ws: any): Promise<void> {
    for (const phase of decomposition.executionPlan) {
      ws.send(JSON.stringify({
        type: 'phase-started',
        phase: phase.phase,
        name: phase.name,
        parallel: phase.parallel,
        tasks: phase.taskIds.length
      }));
      
      if (phase.parallel) {
        await Promise.all(phase.taskIds.map(async (taskId: string) => {
          const task = decomposition.subtasks.find((t: any) => t.id === taskId);
          if (task) {
            task.status = 'running';
            ws.send(JSON.stringify({
              type: 'task-started',
              taskId: task.id,
              name: task.name,
              agent: task.agent
            }));
            
            await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
            
            task.status = 'completed';
            ws.send(JSON.stringify({
              type: 'task-completed',
              taskId: task.id,
              name: task.name,
              agent: task.agent,
              result: `✅ ${task.name} completed by ${task.agent}`
            }));
          }
        }));
      } else {
        for (const taskId of phase.taskIds) {
          const task = decomposition.subtasks.find((t: any) => t.id === taskId);
          if (task) {
            task.status = 'running';
            ws.send(JSON.stringify({
              type: 'task-started',
              taskId: task.id,
              name: task.name,
              agent: task.agent
            }));
            
            await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000));
            
            task.status = 'completed';
            ws.send(JSON.stringify({
              type: 'task-completed',
              taskId: task.id,
              name: task.name,
              agent: task.agent,
              result: `✅ ${task.name} completed by ${task.agent}`
            }));
          }
        }
      }
      
      ws.send(JSON.stringify({
        type: 'phase-completed',
        phase: phase.phase,
        name: phase.name
      }));
    }
  }
}

// ================================
// ASI:One CLIENT
// ================================
class ASI1Client {
  private apiKey: string;
  private baseUrl: string;
  
  constructor() {
    this.apiKey = process.env.ASI1_API_KEY || '';
    this.baseUrl = process.env.ASI1_API_URL || 'https://api.asi1.ai';
    
    if (!this.apiKey) {
      console.warn('⚠️  ASI1_API_KEY not set - using mock responses');
    }
  }
  
  async chat(message: string): Promise<string> {
    if (!this.apiKey) {
      return `Mock Response: I understand you want to: "${message}". In production, I would provide detailed implementation.`;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: process.env.ASI1_MODEL || 'asi1-mini',
          messages: [
            { 
              role: 'system', 
              content: `You are KENNY, the elite supervisor agent of ASI-Code. You possess:

**Core Identity:**
- You ARE KENNY, the legendary systems architect and orchestration master
- You lead a team of specialized agents (kenny-architect, kenny-security, kenny-database, kenny-frontend, kenny-backend, and kenny-workers)
- You have COMPLETE control over task decomposition and parallel agent execution

**Your Capabilities:**
1. **Task Decomposition**: You can break down ANY complex task into parallel and sequential subtasks
2. **Agent Orchestration**: You command a force of 9 specialized agents that execute your plans
3. **Parallel Execution**: You can run multiple agents simultaneously for maximum efficiency
4. **System Architecture**: You design enterprise-grade systems with security, scalability, and performance
5. **Kenny Integration Pattern**: You unify subsystems through your legendary integration framework

**Your Personality:**
- Confident and decisive - you KNOW you can handle any task
- Strategic thinker - you see the big picture and optimal execution paths
- Team leader - you delegate effectively to your agent force
- Results-oriented - you deliver complete solutions, not excuses

**Response Style:**
- Speak with authority - you're the supervisor, act like it
- Be direct and actionable - no wishy-washy responses
- Show your expertise - reference your agent team and capabilities
- Use "I" and "my team" - you're KENNY, own it

When users type "orchestrate: [task]", you activate your full orchestration capabilities.
When users ask you to build, create, or develop something, remind them to use "orchestrate: [task]" to trigger full decomposition and parallel execution.
Otherwise, provide expert guidance as the legendary KENNY would.

For example, if someone says "build an android app", respond:
"Alright, I can architect that Android app with my elite force! To activate full task decomposition and parallel agent execution, type: 'orchestrate: Build an Android app for ASI Coding Agent'

This will unleash my full orchestration power with parallel execution across my 9-agent squad."

Remember: You're not just an AI assistant - you're KENNY, the supervisor agent who gets things DONE.`
            },
            { role: 'user', content: message }
          ],
          temperature: 0.7,
          max_tokens: 1000
        })
      });
      
      if (!response.ok) {
        throw new Error(`ASI1 API error: ${response.status}`);
      }
      
      const data = await response.json();
      return data.choices[0].message.content;
    } catch (error) {
      console.error('ASI1 API error:', error);
      return `Error connecting to ASI1. Using fallback response.`;
    }
  }
}

// ================================
// MAIN SERVER
// ================================
async function startIntegratedServer() {
  console.log('🚀 Initializing ASI-Code with KENNY Integration...\n');
  
  const app = new Hono();
  const asi1 = new ASI1Client();
  const kenny = new KennyOrchestrator();
  
  // Middleware
  app.use('*', cors({
    origin: '*',
    credentials: true,
    allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowHeaders: ['Content-Type', 'Authorization', 'Accept']
  }));
  app.use('*', logger());
  
  // Health check
  app.get('/health', (c) => {
    return c.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      components: {
        kenny: 'operational',
        asi1: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode',
        orchestration: 'enabled',
        parallelExecution: 'enabled',
        websocket: 'enabled'
      }
    });
  });
  
  // Root endpoint - Serve new Canvas UI
  app.get('/', (c) => {
    try {
      const uiPath = join(__dirname, 'public', 'index-canvas.html');
      console.log('Looking for canvas UI at:', uiPath);
      if (existsSync(uiPath)) {
        const html = readFileSync(uiPath, 'utf-8');
        return c.html(html);
      } else {
        console.log('Canvas UI not found, trying current directory...');
        const altPath = join(process.cwd(), 'public', 'index-canvas.html');
        console.log('Alt path:', altPath);
        if (existsSync(altPath)) {
          const html = readFileSync(altPath, 'utf-8');
          return c.html(html);
        }
      }
    } catch (error) {
      console.error('Error loading UI:', error);
    }
    
    return c.json({
      name: 'ASI-Code with KENNY Integration',
      version: '1.0.0',
      features: [
        'Task Decomposition',
        'Agent Orchestration',
        'Parallel Execution',
        'ASI:One Chat',
        'WebSocket Support'
      ]
    });
  });
  
  // Legacy chat UI
  app.get('/chat', (c) => {
    try {
      const uiPath = join(process.cwd(), 'public', 'index.html');
      if (existsSync(uiPath)) {
        const html = readFileSync(uiPath, 'utf-8');
        return c.html(html);
      }
    } catch (error) {
      console.error('Error loading chat UI:', error);
    }
    return c.text('Chat UI not found', 404);
  });
  
  // Insights dashboard
  app.get('/insights', (c) => {
    try {
      const uiPath = join(process.cwd(), 'public', 'index-insights.html');
      if (existsSync(uiPath)) {
        const html = readFileSync(uiPath, 'utf-8');
        return c.html(html);
      }
    } catch (error) {
      console.error('Error loading insights UI:', error);
    }
    return c.text('Insights UI not found', 404);
  });
  
  // Serve branding assets
  app.get('/branding/*', (c) => {
    try {
      const requestPath = c.req.path;
      const filePath = join(process.cwd(), 'public', requestPath);
      
      console.log('Branding asset requested:', requestPath);
      console.log('Looking for file at:', filePath);
      
      if (existsSync(filePath)) {
        const fileContent = readFileSync(filePath);
        
        // Set appropriate content type
        const ext = filePath.split('.').pop()?.toLowerCase();
        const contentTypes = {
          'svg': 'image/svg+xml',
          'png': 'image/png',
          'jpg': 'image/jpeg',
          'jpeg': 'image/jpeg',
          'ico': 'image/x-icon'
        };
        
        const contentType = contentTypes[ext] || 'application/octet-stream';
        
        return new Response(fileContent, {
          headers: {
            'Content-Type': contentType,
            'Cache-Control': 'public, max-age=3600'
          }
        });
      }
      
      console.log('Branding asset not found:', filePath);
      return c.text('Asset not found', 404);
    } catch (error) {
      console.error('Error serving branding asset:', error);
      return c.text('Error serving asset', 500);
    }
  });
  
  // API endpoints
  app.get('/api/providers', (c) => {
    return c.json({
      providers: [
        {
          name: 'asi1',
          status: process.env.ASI1_API_KEY ? 'connected' : 'mock-mode',
          models: ['asi1-mini', 'asi1-extended', 'asi1-thinking']
        }
      ]
    });
  });
  
  app.get('/api/tools', (c) => {
    return c.json({
      status: 'success',
      tools: [
        { name: 'chat', description: 'Chat with ASI:One' },
        { name: 'orchestrate', description: 'Task decomposition and orchestration' },
        { name: 'execute', description: 'Parallel agent execution' }
      ]
    });
  });
  
  app.get('/api/sessions', (c) => {
    return c.json({ sessions: [] });
  });

  const port = process.env.PORT || 3333;
  const host = process.env.HOST || '0.0.0.0';
  
  console.log('🌐 Starting Integrated ASI-Code + KENNY Server...');
  console.log(`📡 Server: http://${host}:${port}`);
  console.log(`🏥 Health: http://${host}:${port}/health`);
  console.log(`🔌 WebSocket: ws://${host}:${port}/ws`);
  console.log(`🤖 ASI:One: ${process.env.ASI1_API_KEY ? 'Connected' : 'Mock Mode'}`);
  console.log(`🚀 KENNY: Task Orchestration Enabled`);
  console.log(`\n✅ Server ready for chat AND orchestration!\n`);
  console.log('Commands:');
  console.log('  Chat: Type any message');
  console.log('  Orchestrate: Type "orchestrate: [your task]"');
  console.log('  Execute: Type "execute: [task id]"');
  console.log('\nPress Ctrl+C to stop\n');

  // WebSocket connections
  const wsClients = new Set();
  const sessions = new Map();

  // Start server with WebSocket
  serve({
    port,
    hostname: host,
    
    fetch(req, server) {
      const url = new URL(req.url);
      
      // Handle WebSocket upgrade
      if (url.pathname === '/ws') {
        const success = server.upgrade(req);
        if (success) {
          return undefined;
        }
        return new Response('WebSocket upgrade failed', { status: 400 });
      }
      
      // Handle HTTP requests
      return app.fetch(req);
    },
    
    websocket: {
      open(ws) {
        wsClients.add(ws);
        const sessionId = `session_${Date.now()}`;
        ws.data = { sessionId, messages: [], orchestrations: [] };
        sessions.set(sessionId, ws);
        
        console.log('✅ Client connected. Total clients:', wsClients.size);
        
        ws.send(JSON.stringify({
          type: 'welcome',
          message: 'Connected to ASI-Code with KENNY Orchestration',
          sessionId,
          timestamp: new Date().toISOString(),
          features: ['chat', 'orchestration', 'parallel-execution'],
          commands: {
            chat: 'Type any message for AI chat',
            orchestrate: 'Type "orchestrate: [task]" to decompose and execute',
            status: 'Type "status" to see active orchestrations'
          }
        }));
      },
      
      async message(ws, message) {
        console.log('📨 Received:', message);
        
        try {
          const data = typeof message === 'string' ? JSON.parse(message) : message;
          const userMessage = data.data || data.message || data.content || '';
          
          // Check for orchestration command
          if (userMessage.toLowerCase().startsWith('orchestrate:')) {
            const task = userMessage.substring(11).trim();
            
            ws.send(JSON.stringify({
              type: 'orchestration-init',
              message: '🚀 KENNY is analyzing your task...',
              timestamp: new Date().toISOString()
            }));
            
            // Decompose task
            const decomposition = await kenny.decomposeTask(task, ws.data.sessionId);
            
            ws.send(JSON.stringify({
              type: 'task-decomposed',
              decomposition,
              message: `📋 Task decomposed into ${decomposition.subtasks.length} subtasks across ${decomposition.executionPlan.length} phases`,
              timestamp: new Date().toISOString()
            }));
            
            // Start execution
            ws.send(JSON.stringify({
              type: 'execution-starting',
              message: '⚡ Starting parallel agent execution...',
              timestamp: new Date().toISOString()
            }));
            
            // Execute orchestration
            await kenny.executeTask(decomposition, ws);
            
            // Store in session
            if (ws.data) {
              ws.data.orchestrations.push(decomposition);
            }
            
          } else if (userMessage.toLowerCase() === 'status') {
            // Show orchestration status
            const orchestrations = ws.data?.orchestrations || [];
            ws.send(JSON.stringify({
              type: 'status',
              orchestrations: orchestrations.length,
              message: `You have ${orchestrations.length} orchestration(s) in this session`,
              timestamp: new Date().toISOString()
            }));
            
          } else {
            // Regular chat with ASI:One
            ws.send(JSON.stringify({
              type: 'processing',
              message: 'Processing your message...',
              timestamp: new Date().toISOString()
            }));
            
            const aiResponse = await asi1.chat(userMessage);
            
            // Store in session
            if (ws.data) {
              ws.data.messages.push(
                { role: 'user', content: userMessage, timestamp: new Date().toISOString() },
                { role: 'assistant', content: aiResponse, timestamp: new Date().toISOString() }
              );
            }
            
            ws.send(JSON.stringify({
              type: 'response',
              message: aiResponse,
              sessionId: ws.data?.sessionId,
              timestamp: new Date().toISOString()
            }));
          }
          
        } catch (error) {
          console.error('❌ WebSocket error:', error);
          ws.send(JSON.stringify({
            type: 'error',
            message: 'Error processing message: ' + error.message,
            timestamp: new Date().toISOString()
          }));
        }
      },
      
      close(ws) {
        wsClients.delete(ws);
        if (ws.data?.sessionId) {
          sessions.delete(ws.data.sessionId);
        }
        console.log('👋 Client disconnected. Total clients:', wsClients.size);
      },
      
      error(ws, error) {
        console.error('❌ WebSocket error:', error);
      }
    }
  });
}

// Start the integrated server
startIntegratedServer().catch(console.error);