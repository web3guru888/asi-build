/**
 * Base Agent Class - Foundation for all specialized agents
 * Implements context engineering and prompt engineering methodologies
 */

export interface AgentContext {
  task: {
    id: string;
    title: string;
    description: string;
    acceptance: string[];
    scope: string[];
  };
  architecture: string;
  constraints: string;
  previousDecisions: string[];
  relevantCode: { path: string; content: string }[];
  testStrategy: string;
}

export interface AgentResult {
  success: boolean;
  output: any;
  logs: string[];
  metrics: {
    tokensUsed: number;
    executionTime: number;
    retries: number;
  };
}

export abstract class BaseAgent {
  protected name: string;
  protected capabilities: string[];
  protected maxRetries: number = 3;
  protected timeout: number = 30000; // 30 seconds
  
  constructor(name: string, capabilities: string[]) {
    this.name = name;
    this.capabilities = capabilities;
  }
  
  /**
   * Build dynamic prompt with context engineering
   */
  protected buildPrompt(context: AgentContext, specificInstructions: string): string {
    // Compress context to fit token limits
    const compressedContext = this.compressContext(context);
    
    return `You are ${this.name}, a specialized agent in KENNY's force.
Your capabilities: ${this.capabilities.join(', ')}

TASK: ${context.task.title}
${context.task.description}

ACCEPTANCE CRITERIA:
${context.task.acceptance.map(c => `- ${c}`).join('\n')}

SCOPE (files you can modify):
${context.task.scope.map(s => `- ${s}`).join('\n')}

ARCHITECTURE CONTEXT:
${compressedContext.architecture}

SYSTEM CONSTRAINTS:
${compressedContext.constraints}

RELEVANT CODE:
${compressedContext.code}

PREVIOUS DECISIONS:
${compressedContext.decisions}

SPECIFIC INSTRUCTIONS:
${specificInstructions}

IMPORTANT RULES:
1. Generate production-ready code only
2. Include comprehensive error handling
3. Follow TypeScript strict mode
4. Add JSDoc comments for all functions
5. Ensure all acceptance criteria are met
6. Stay within the defined scope
7. Output valid, runnable code

OUTPUT FORMAT: Provide your response as valid JSON with the following structure:
{
  "files": [
    {
      "path": "relative/path/to/file",
      "content": "full file content",
      "action": "create|modify|delete"
    }
  ],
  "tests": [
    {
      "path": "test/file/path",
      "content": "test file content"
    }
  ],
  "summary": "Brief summary of what was done",
  "nextSteps": ["Any follow-up tasks needed"]
}`;
  }
  
  /**
   * Compress context to fit within token limits
   */
  protected compressContext(context: AgentContext): any {
    // Smart compression: keep most relevant parts
    const compressed = {
      architecture: this.extractRelevant(context.architecture, 500),
      constraints: this.extractRelevant(context.constraints, 300),
      code: this.compressCode(context.relevantCode, 1000),
      decisions: context.previousDecisions.slice(-5).join('\n')
    };
    
    return compressed;
  }
  
  /**
   * Extract most relevant parts of text
   */
  protected extractRelevant(text: string, maxTokens: number): string {
    if (!text) return '';
    
    // Simple heuristic: take first and last parts, prioritize headers
    const lines = text.split('\n');
    const headers = lines.filter(l => l.startsWith('#'));
    const important = lines.filter(l => 
      l.includes('IMPORTANT') || 
      l.includes('REQUIRED') || 
      l.includes('MUST')
    );
    
    const relevant = [...headers, ...important].join('\n');
    return relevant.substring(0, maxTokens * 4); // Rough token estimate
  }
  
  /**
   * Compress code snippets
   */
  protected compressCode(code: { path: string; content: string }[], maxTokens: number): string {
    if (!code || code.length === 0) return 'No relevant code found';
    
    // Prioritize interfaces, types, and function signatures
    const compressed = code.map(file => {
      const lines = file.content.split('\n');
      const signatures = lines.filter(l => 
        l.includes('interface') ||
        l.includes('type') ||
        l.includes('function') ||
        l.includes('class') ||
        l.includes('export')
      );
      
      return `// ${file.path}\n${signatures.slice(0, 20).join('\n')}`;
    }).join('\n\n');
    
    return compressed.substring(0, maxTokens * 4);
  }
  
  /**
   * Execute agent task with retries and timeout
   */
  async execute(context: AgentContext): Promise<AgentResult> {
    const startTime = Date.now();
    let retries = 0;
    let lastError: any;
    
    while (retries < this.maxRetries) {
      try {
        // Set timeout
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Agent timeout')), this.timeout)
        );
        
        // Execute with timeout
        const result = await Promise.race([
          this.performTask(context),
          timeoutPromise
        ]) as AgentResult;
        
        // Add metrics
        result.metrics = {
          tokensUsed: this.estimateTokens(context),
          executionTime: Date.now() - startTime,
          retries
        };
        
        return result;
        
      } catch (error) {
        lastError = error;
        retries++;
        
        if (retries < this.maxRetries) {
          // Exponential backoff
          await new Promise(resolve => 
            setTimeout(resolve, Math.pow(2, retries) * 1000)
          );
        }
      }
    }
    
    // Failed after retries
    return {
      success: false,
      output: null,
      logs: [`Failed after ${retries} retries: ${lastError}`],
      metrics: {
        tokensUsed: 0,
        executionTime: Date.now() - startTime,
        retries
      }
    };
  }
  
  /**
   * Estimate token usage
   */
  protected estimateTokens(context: AgentContext): number {
    const contextStr = JSON.stringify(context);
    return Math.ceil(contextStr.length / 4); // Rough estimate
  }
  
  /**
   * Abstract method - must be implemented by each agent
   */
  protected abstract performTask(context: AgentContext): Promise<AgentResult>;
}