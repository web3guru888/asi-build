/**
 * ASI1 Provider - Core AI model provider for ASI-Code
 * 
 * Implements the ASI1 model interface with advanced capabilities for
 * code generation, analysis, and intelligent automation.
 */

export interface ASI1Config {
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  contextWindow?: number;
}

export interface ASI1Response {
  content: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  model: string;
  timestamp: Date;
}

export interface ASI1Request {
  messages: Array<{
    role: 'system' | 'user' | 'assistant';
    content: string;
  }>;
  temperature?: number;
  maxTokens?: number;
  tools?: Array<{
    name: string;
    description: string;
    parameters: Record<string, any>;
  }>;
}

export class ASI1Provider {
  private config: Required<ASI1Config>;

  constructor(config: ASI1Config = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.ASI1_API_KEY || '',
      baseUrl: config.baseUrl || 'https://api.asi1.dev/v1',
      model: config.model || 'asi-1-turbo',
      temperature: config.temperature ?? 0.7,
      maxTokens: config.maxTokens || 4096,
      contextWindow: config.contextWindow || 128000,
    };
  }

  async generate(request: ASI1Request): Promise<ASI1Response> {
    if (!this.config.apiKey) {
      throw new Error('ASI1 API key is required. Set ASI1_API_KEY environment variable or provide in config.');
    }

    const payload = {
      model: this.config.model,
      messages: request.messages,
      temperature: request.temperature ?? this.config.temperature,
      max_tokens: request.maxTokens ?? this.config.maxTokens,
      tools: request.tools,
    };

    try {
      const response = await fetch(`${this.config.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
          'User-Agent': 'asi-code/1.0.0',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`ASI1 API error (${response.status}): ${error}`);
      }

      const data = await response.json();
      
      return {
        content: data.choices[0]?.message?.content || '',
        usage: {
          promptTokens: data.usage?.prompt_tokens || 0,
          completionTokens: data.usage?.completion_tokens || 0,
          totalTokens: data.usage?.total_tokens || 0,
        },
        model: data.model || this.config.model,
        timestamp: new Date(),
      };
    } catch (error) {
      throw new Error(`Failed to generate response from ASI1: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async streamGenerate(request: ASI1Request): Promise<AsyncIterable<string>> {
    if (!this.config.apiKey) {
      throw new Error('ASI1 API key is required. Set ASI1_API_KEY environment variable or provide in config.');
    }

    const payload = {
      ...request,
      model: this.config.model,
      stream: true,
      temperature: request.temperature ?? this.config.temperature,
      max_tokens: request.maxTokens ?? this.config.maxTokens,
    };

    const response = await fetch(`${this.config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.config.apiKey}`,
        'User-Agent': 'asi-code/1.0.0',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`ASI1 API error (${response.status}): ${error}`);
    }

    return this.parseStreamResponse(response);
  }

  private async *parseStreamResponse(response: Response): AsyncIterable<string> {
    if (!response.body) {
      throw new Error('No response body received from ASI1 API');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') return;
            
            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices?.[0]?.delta?.content;
              if (content) {
                yield content;
              }
            } catch (error) {
              console.warn('Failed to parse streaming response line:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  getConfig(): ASI1Config {
    return { ...this.config };
  }

  updateConfig(updates: Partial<ASI1Config>): void {
    this.config = { ...this.config, ...updates } as Required<ASI1Config>;
  }
  
  getAvailableModels(): string[] {
    return ['asi1-mini', 'asi1-extended', 'asi1-thinking', 'asi1-graph'];
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await this.generate({
        messages: [
          { role: 'user', content: 'Test connection. Respond with "OK".' }
        ],
        maxTokens: 10,
        temperature: 0,
      });
      return response.content.trim().toLowerCase().includes('ok');
    } catch (error) {
      console.error('ASI1 connection test failed:', error);
      return false;
    }
  }
}

// Factory function for creating ASI1 provider instances
export function createASI1Provider(config?: ASI1Config): ASI1Provider {
  return new ASI1Provider(config);
}

// Default export
export default ASI1Provider;