/**
 * Enhanced Tool Routes - Advanced tool execution and management endpoints
 * 
 * Provides comprehensive tool API endpoints with enhanced features like:
 * - Batch execution
 * - Parameter validation
 * - Tool discovery
 * - Health monitoring
 * - Execution metrics
 */

import type { Hono } from 'hono';
import type { DefaultASIServer } from './server.js';

/**
 * Setup enhanced tool routes with new API endpoints
 */
export function setupEnhancedToolRoutes(app: Hono, server: DefaultASIServer): void {
  const toolManager = server.getToolManager();

  // List available tools with enhanced filtering
  app.get('/api/tools', (c) => {
    try {
      const category = c.req.query('category');
      const tags = c.req.query('tags')?.split(',').map(t => t.trim());
      const status = c.req.query('status') as 'active' | 'disabled' | 'deprecated' | undefined;

      // Check if toolManager has the new registry-based list method
      let tools;
      if ('list' in toolManager && typeof toolManager.list === 'function') {
        tools = (toolManager as any).list({ category, tags, status });
      } else {
        tools = toolManager.list();
        
        // Apply client-side filtering for legacy tool manager
        if (category) {
          tools = tools.filter((tool: any) => tool.category === category);
        }
      }

      return c.json({ 
        tools,
        count: tools.length,
        categories: tools.reduce((acc: Record<string, number>, tool: any) => {
          acc[tool.category] = (acc[tool.category] || 0) + 1;
          return acc;
        }, {})
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get tool discovery information
  app.get('/api/tools/discover', (c) => {
    try {
      // If toolManager supports discovery, use it
      if ('discoverTools' in toolManager && typeof (toolManager as any).discoverTools === 'function') {
        const discoveryInfo = (toolManager as any).discoverTools();
        return c.json({ 
          tools: discoveryInfo,
          systemInfo: (toolManager as any).getSystemInfo?.() || {}
        });
      } else {
        // Fallback for legacy tool manager
        const tools = toolManager.list();
        return c.json({ 
          tools: tools.map((tool: any) => ({
            name: tool.name,
            version: tool.version || '1.0.0',
            category: tool.category,
            description: tool.description,
            permissions: tool.permissions || [],
            safetyLevel: 'safe',
            tags: tool.tags || [],
            status: 'active'
          }))
        });
      }
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Execute a tool with enhanced context and error handling
  app.post('/api/tools/:name/execute', async (c) => {
    try {
      const toolName = c.req.param('name');
      const body = await c.req.json();
      const { parameters = {}, context = {} } = body;

      // Build execution context with defaults
      const executionContext = {
        sessionId: context.sessionId || `session_${Date.now()}`,
        userId: context.userId || 'anonymous',
        permissions: context.permissions || ['read_files', 'write_files', 'execute_commands', 'delete_files'],
        workingDirectory: context.workingDirectory || process.cwd(),
        environment: context.environment || {},
        metadata: context.metadata || {},
        limits: context.limits || {},
        ...context
      };

      const result = await toolManager.execute(toolName, parameters, executionContext);
      
      // Enhanced event emission
      server.emit('tool:executed', { 
        tool: toolName, 
        result,
        parameters: Object.keys(parameters),
        success: result.success,
        executionTime: result.performance?.executionTime,
        userId: executionContext.userId
      });
      
      return c.json({ 
        result,
        metadata: {
          toolName,
          executedAt: new Date().toISOString(),
          executionId: `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        }
      });
    } catch (error) {
      return c.json({ 
        error: (error as Error).message,
        type: 'execution_error',
        timestamp: new Date().toISOString()
      }, 400);
    }
  });

  // Execute multiple tools in sequence
  app.post('/api/tools/execute-batch', async (c) => {
    try {
      const body = await c.req.json();
      const { tools, context = {}, stopOnError = true } = body;

      if (!Array.isArray(tools)) {
        return c.json({ error: 'Tools must be an array' }, 400);
      }

      const results = [];
      const executionContext = {
        sessionId: context.sessionId || `session_${Date.now()}`,
        userId: context.userId || 'anonymous',
        permissions: context.permissions || ['read_files', 'write_files', 'execute_commands', 'delete_files'],
        workingDirectory: context.workingDirectory || process.cwd(),
        environment: context.environment || {},
        metadata: context.metadata || {},
        ...context
      };

      for (const toolExecution of tools) {
        const { name, parameters = {} } = toolExecution;
        
        try {
          const result = await toolManager.execute(name, parameters, executionContext);
          results.push({
            toolName: name,
            result,
            success: result.success
          });

          if (!result.success && stopOnError) {
            break;
          }
        } catch (error) {
          const errorResult = {
            toolName: name,
            result: { success: false, error: (error as Error).message },
            success: false
          };
          results.push(errorResult);

          if (stopOnError) {
            break;
          }
        }
      }

      return c.json({
        results,
        batchId: `batch_${Date.now()}`,
        executedAt: new Date().toISOString(),
        totalTools: tools.length,
        successfulTools: results.filter(r => r.success).length
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get tool definition and schema
  app.get('/api/tools/:name', (c) => {
    try {
      const toolName = c.req.param('name');
      const tool = toolManager.get(toolName);
      
      if (!tool) {
        return c.json({ error: 'Tool not found' }, 404);
      }

      // Get tool definition (enhanced)
      const definition = (tool as any).definition || {};
      const info = (tool as any).getInfo?.() || definition;

      return c.json({
        name: toolName,
        definition: info,
        schema: {
          name: definition.name,
          description: definition.description,
          parameters: definition.parameters || [],
          category: definition.category,
          version: definition.version || '1.0.0',
          permissions: definition.permissions || [],
          safetyLevel: definition.safetyLevel || 'safe',
          tags: definition.tags || [],
          examples: definition.examples || []
        },
        capabilities: (tool as any).getCapabilities?.() || {},
        status: 'active'
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Validate tool parameters without executing
  app.post('/api/tools/:name/validate', async (c) => {
    try {
      const toolName = c.req.param('name');
      const body = await c.req.json();
      const { parameters = {} } = body;

      const tool = toolManager.get(toolName);
      if (!tool) {
        return c.json({ error: 'Tool not found' }, 404);
      }

      // Use enhanced validation if available
      let validationResult;
      if ('validate' in tool && typeof tool.validate === 'function') {
        if (tool.validate.length > 1) {
          // New validation method that returns detailed results
          validationResult = tool.validate(parameters);
        } else {
          // Legacy validation method that returns boolean
          const isValid = tool.validate(parameters);
          validationResult = {
            isValid,
            errors: isValid ? [] : ['Parameter validation failed'],
            warnings: []
          };
        }
      } else {
        validationResult = {
          isValid: true,
          errors: [],
          warnings: ['Tool does not support validation']
        };
      }

      return c.json({
        toolName,
        parameters: Object.keys(parameters),
        validation: validationResult,
        validatedAt: new Date().toISOString()
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get tool execution metrics (if available)
  app.get('/api/tools/:name/metrics', (c) => {
    try {
      const toolName = c.req.param('name');

      // Check if tool manager supports metrics
      if ('getMetrics' in toolManager && typeof (toolManager as any).getMetrics === 'function') {
        const metrics = (toolManager as any).getMetrics(toolName);
        
        if (!metrics) {
          return c.json({ error: 'Tool not found or no metrics available' }, 404);
        }

        return c.json({
          toolName,
          metrics,
          retrievedAt: new Date().toISOString()
        });
      } else {
        return c.json({ 
          error: 'Metrics not supported by this tool manager',
          toolName
        }, 501);
      }
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get running tool executions (if available)
  app.get('/api/tools/executions', (c) => {
    try {
      if ('getRunningExecutions' in toolManager && typeof (toolManager as any).getRunningExecutions === 'function') {
        const executions = (toolManager as any).getRunningExecutions();
        
        return c.json({
          executions,
          count: executions.length,
          retrievedAt: new Date().toISOString()
        });
      } else {
        return c.json({ 
          error: 'Execution tracking not supported by this tool manager'
        }, 501);
      }
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Cancel a running tool execution (if available)
  app.delete('/api/tools/executions/:id', async (c) => {
    try {
      const executionId = c.req.param('id');

      if ('cancelExecution' in toolManager && typeof (toolManager as any).cancelExecution === 'function') {
        const cancelled = await (toolManager as any).cancelExecution(executionId);
        
        if (!cancelled) {
          return c.json({ error: 'Execution not found or already completed' }, 404);
        }

        return c.json({
          executionId,
          cancelled: true,
          cancelledAt: new Date().toISOString()
        });
      } else {
        return c.json({ 
          error: 'Execution cancellation not supported by this tool manager'
        }, 501);
      }
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });

  // Get tool system health and statistics
  app.get('/api/tools/health', async (c) => {
    try {
      let health = { status: 'ok', timestamp: new Date().toISOString() };

      if ('healthCheck' in toolManager && typeof (toolManager as any).healthCheck === 'function') {
        health = await (toolManager as any).healthCheck();
      }

      return c.json({
        health,
        system: {
          totalTools: toolManager.list().length,
          categories: toolManager.list().reduce((acc: Record<string, number>, tool: any) => {
            acc[tool.category] = (acc[tool.category] || 0) + 1;
            return acc;
          }, {})
        }
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 500);
    }
  });

  // Get detailed documentation for all tools
  app.get('/api/tools/documentation', (c) => {
    try {
      const tools = toolManager.list();
      const documentation = tools.map((toolDef: any) => {
        const tool = toolManager.get(toolDef.name);
        const definition = (tool as any).definition || toolDef;
        
        return {
          name: definition.name,
          description: definition.description,
          category: definition.category,
          version: definition.version || '1.0.0',
          parameters: definition.parameters || [],
          permissions: definition.permissions || [],
          safetyLevel: definition.safetyLevel || 'safe',
          tags: definition.tags || [],
          examples: definition.examples || [],
          author: definition.author || 'ASI Team'
        };
      });

      return c.json({
        documentation,
        totalTools: documentation.length,
        categories: documentation.reduce((acc: Record<string, number>, tool: any) => {
          acc[tool.category] = (acc[tool.category] || 0) + 1;
          return acc;
        }, {}),
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      return c.json({ error: (error as Error).message }, 400);
    }
  });
}