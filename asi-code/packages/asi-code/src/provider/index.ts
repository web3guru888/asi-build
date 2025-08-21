/**
 * AI Provider System - Unified interface for various AI providers
 * 
 * Supports Anthropic Claude, OpenAI GPT, and other providers through
 * a standardized interface for the ASI-Code system.
 */

import { EventEmitter } from 'eventemitter3';

export interface ProviderConfig {
  name: string;
  type: 'anthropic' | 'openai' | 'custom';
  apiKey: string;
  baseUrl?: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  metadata?: Record<string, any>;
}

export interface ProviderMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, any>;
}

export interface ProviderResponse {
  content: string;
  usage?: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
  model: string;
  metadata?: Record<string, any>;
}

export interface Provider extends EventEmitter {
  name: string;
  config: ProviderConfig;
  initialize(): Promise<void>;
  generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse>;
  streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse>;
  isAvailable(): Promise<boolean>;
  cleanup(): Promise<void>;
}

export abstract class BaseProvider extends EventEmitter implements Provider {
  public name: string;
  public config: ProviderConfig;

  constructor(config: ProviderConfig) {
    super();
    this.name = config.name;
    this.config = config;
  }

  abstract initialize(): Promise<void>;
  abstract generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse>;
  abstract streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse>;
  abstract isAvailable(): Promise<boolean>;

  async cleanup(): Promise<void> {
    this.removeAllListeners();
  }
}

// Anthropic Claude Provider
export class AnthropicProvider extends BaseProvider {
  private client: any = null;

  async initialize(): Promise<void> {
    try {
      // Dynamic import to avoid bundling issues
      const { Anthropic } = await import('@anthropic-ai/sdk');
      this.client = new Anthropic({
        apiKey: this.config.apiKey,
        baseURL: this.config.baseUrl
      });
      this.emit('initialized', { provider: this.name });
    } catch (error) {
      this.emit('error', { error, provider: this.name });
      throw error;
    }
  }

  async generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse> {
    if (!this.client) {
      throw new Error('Provider not initialized');
    }

    try {
      const response = await this.client.messages.create({
        model: options?.model || this.config.model,
        max_tokens: options?.maxTokens || this.config.maxTokens || 4000,
        temperature: options?.temperature || this.config.temperature || 0.7,
        messages: messages.map(m => ({ role: m.role, content: m.content }))
      });

      const result: ProviderResponse = {
        content: response.content[0].text,
        usage: {
          inputTokens: response.usage.input_tokens,
          outputTokens: response.usage.output_tokens,
          totalTokens: response.usage.input_tokens + response.usage.output_tokens
        },
        model: response.model,
        metadata: { id: response.id, type: response.type }
      };

      this.emit('response', { messages, response: result, provider: this.name });
      return result;
    } catch (error) {
      this.emit('error', { error, messages, provider: this.name });
      throw error;
    }
  }

  async* streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse> {
    if (!this.client) {
      throw new Error('Provider not initialized');
    }

    try {
      const stream = await this.client.messages.create({
        model: options?.model || this.config.model,
        max_tokens: options?.maxTokens || this.config.maxTokens || 4000,
        temperature: options?.temperature || this.config.temperature || 0.7,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        stream: true
      });

      let fullContent = '';
      let usage = { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
      let model = '';

      for await (const chunk of stream) {
        if (chunk.type === 'content_block_delta') {
          const text = chunk.delta.text;
          fullContent += text;
          yield text;
        } else if (chunk.type === 'message_start') {
          usage.inputTokens = chunk.message.usage.input_tokens;
          model = chunk.message.model;
        } else if (chunk.type === 'message_delta') {
          usage.outputTokens = chunk.usage.output_tokens;
          usage.totalTokens = usage.inputTokens + usage.outputTokens;
        }
      }

      return {
        content: fullContent,
        usage,
        model,
        metadata: { streamed: true }
      };
    } catch (error) {
      this.emit('error', { error, messages, provider: this.name });
      throw error;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      if (!this.client) return false;
      // Simple test call
      await this.client.messages.create({
        model: this.config.model,
        max_tokens: 1,
        messages: [{ role: 'user', content: 'test' }]
      });
      return true;
    } catch {
      return false;
    }
  }
}

// OpenAI Provider
export class OpenAIProvider extends BaseProvider {
  private client: any = null;

  async initialize(): Promise<void> {
    try {
      const { OpenAI } = await import('openai');
      this.client = new OpenAI({
        apiKey: this.config.apiKey,
        baseURL: this.config.baseUrl
      });
      this.emit('initialized', { provider: this.name });
    } catch (error) {
      this.emit('error', { error, provider: this.name });
      throw error;
    }
  }

  async generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse> {
    if (!this.client) {
      throw new Error('Provider not initialized');
    }

    try {
      const response = await this.client.chat.completions.create({
        model: options?.model || this.config.model,
        max_tokens: options?.maxTokens || this.config.maxTokens || 4000,
        temperature: options?.temperature || this.config.temperature || 0.7,
        top_p: options?.topP || this.config.topP || 1,
        messages: messages.map(m => ({ role: m.role, content: m.content }))
      });

      const result: ProviderResponse = {
        content: response.choices[0].message.content || '',
        usage: {
          inputTokens: response.usage?.prompt_tokens || 0,
          outputTokens: response.usage?.completion_tokens || 0,
          totalTokens: response.usage?.total_tokens || 0
        },
        model: response.model,
        metadata: { id: response.id, created: response.created }
      };

      this.emit('response', { messages, response: result, provider: this.name });
      return result;
    } catch (error) {
      this.emit('error', { error, messages, provider: this.name });
      throw error;
    }
  }

  async* streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse> {
    if (!this.client) {
      throw new Error('Provider not initialized');
    }

    try {
      const stream = await this.client.chat.completions.create({
        model: options?.model || this.config.model,
        max_tokens: options?.maxTokens || this.config.maxTokens || 4000,
        temperature: options?.temperature || this.config.temperature || 0.7,
        top_p: options?.topP || this.config.topP || 1,
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        stream: true
      });

      let fullContent = '';
      let usage = { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
      let model = '';

      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta;
        if (delta?.content) {
          fullContent += delta.content;
          yield delta.content;
        }
        if (chunk.model) {
          model = chunk.model;
        }
        if (chunk.usage) {
          usage = {
            inputTokens: chunk.usage.prompt_tokens || 0,
            outputTokens: chunk.usage.completion_tokens || 0,
            totalTokens: chunk.usage.total_tokens || 0
          };
        }
      }

      return {
        content: fullContent,
        usage,
        model,
        metadata: { streamed: true }
      };
    } catch (error) {
      this.emit('error', { error, messages, provider: this.name });
      throw error;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      if (!this.client) return false;
      await this.client.models.list();
      return true;
    } catch {
      return false;
    }
  }
}

// Provider Manager
export class ProviderManager extends EventEmitter {
  private providers = new Map<string, Provider>();

  async register(config: ProviderConfig): Promise<void> {
    let provider: Provider;

    switch (config.type) {
      case 'anthropic':
        provider = new AnthropicProvider(config);
        break;
      case 'openai':
        provider = new OpenAIProvider(config);
        break;
      default:
        throw new Error(`Unsupported provider type: ${config.type}`);
    }

    await provider.initialize();
    this.providers.set(config.name, provider);
    this.emit('provider:registered', { name: config.name, type: config.type });
  }

  get(name: string): Provider | undefined {
    return this.providers.get(name);
  }

  list(): string[] {
    return Array.from(this.providers.keys());
  }

  async unregister(name: string): Promise<void> {
    const provider = this.providers.get(name);
    if (provider) {
      await provider.cleanup();
      this.providers.delete(name);
      this.emit('provider:unregistered', { name });
    }
  }

  async cleanup(): Promise<void> {
    for (const provider of this.providers.values()) {
      await provider.cleanup();
    }
    this.providers.clear();
    this.removeAllListeners();
  }
}

// Factory function
export function createProviderManager(): ProviderManager {
  return new ProviderManager();
}