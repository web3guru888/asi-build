/**
 * Unit tests for Provider Manager
 * 
 * Tests the AI provider management system including:
 * - Provider registration and management
 * - Multiple provider support (Anthropic, OpenAI)
 * - Provider lifecycle management
 * - Error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  ProviderManager,
  createProviderManager,
  AnthropicProvider,
  OpenAIProvider,
  type ProviderConfig,
  type ProviderMessage,
  type Provider
} from '../../../src/provider/index.js';

// Mock external dependencies
vi.mock('@anthropic-ai/sdk', () => ({
  Anthropic: vi.fn().mockImplementation(() => ({
    messages: {
      create: vi.fn().mockResolvedValue({
        content: [{ text: 'Mock Anthropic response' }],
        usage: { input_tokens: 10, output_tokens: 20 },
        model: 'claude-3',
        id: 'msg_123',
        type: 'message'
      })
    }
  }))
}));

vi.mock('openai', () => ({
  OpenAI: vi.fn().mockImplementation(() => ({
    chat: {
      completions: {
        create: vi.fn().mockResolvedValue({
          choices: [{ message: { content: 'Mock OpenAI response' } }],
          usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30 },
          model: 'gpt-4',
          id: 'chatcmpl_123',
          created: 1234567890
        })
      }
    },
    models: {
      list: vi.fn().mockResolvedValue({ data: [] })
    }
  }))
}));

describe('ProviderManager', () => {
  let manager: ProviderManager;

  beforeEach(() => {
    manager = createProviderManager();
  });

  afterEach(async () => {
    await manager.cleanup();
  });

  describe('provider registration', () => {
    it('should register Anthropic provider', async () => {
      const eventSpy = vi.fn();
      manager.on('provider:registered', eventSpy);

      const config: ProviderConfig = {
        name: 'claude',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };

      await manager.register(config);

      expect(eventSpy).toHaveBeenCalledWith({
        name: 'claude',
        type: 'anthropic'
      });
      expect(manager.get('claude')).toBeInstanceOf(AnthropicProvider);
    });

    it('should register OpenAI provider', async () => {
      const eventSpy = vi.fn();
      manager.on('provider:registered', eventSpy);

      const config: ProviderConfig = {
        name: 'gpt4',
        type: 'openai',
        apiKey: 'test-key',
        model: 'gpt-4'
      };

      await manager.register(config);

      expect(eventSpy).toHaveBeenCalledWith({
        name: 'gpt4',
        type: 'openai'
      });
      expect(manager.get('gpt4')).toBeInstanceOf(OpenAIProvider);
    });

    it('should throw error for unsupported provider type', async () => {
      const config: ProviderConfig = {
        name: 'unsupported',
        type: 'custom' as any,
        apiKey: 'test-key',
        model: 'test-model'
      };

      await expect(manager.register(config)).rejects.toThrow('Unsupported provider type: custom');
    });

    it('should register multiple providers', async () => {
      const anthropicConfig: ProviderConfig = {
        name: 'claude',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };

      const openaiConfig: ProviderConfig = {
        name: 'gpt4',
        type: 'openai',
        apiKey: 'test-key',
        model: 'gpt-4'
      };

      await manager.register(anthropicConfig);
      await manager.register(openaiConfig);

      expect(manager.list()).toEqual(['claude', 'gpt4']);
      expect(manager.get('claude')).toBeInstanceOf(AnthropicProvider);
      expect(manager.get('gpt4')).toBeInstanceOf(OpenAIProvider);
    });
  });

  describe('provider retrieval', () => {
    beforeEach(async () => {
      const config: ProviderConfig = {
        name: 'test-provider',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };
      await manager.register(config);
    });

    it('should retrieve registered provider', () => {
      const provider = manager.get('test-provider');
      expect(provider).toBeInstanceOf(AnthropicProvider);
      expect(provider!.name).toBe('test-provider');
    });

    it('should return undefined for non-existent provider', () => {
      const provider = manager.get('non-existent');
      expect(provider).toBeUndefined();
    });

    it('should list all registered providers', () => {
      const providers = manager.list();
      expect(providers).toEqual(['test-provider']);
    });
  });

  describe('provider unregistration', () => {
    beforeEach(async () => {
      const config: ProviderConfig = {
        name: 'test-provider',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };
      await manager.register(config);
    });

    it('should unregister provider', async () => {
      const eventSpy = vi.fn();
      manager.on('provider:unregistered', eventSpy);

      await manager.unregister('test-provider');

      expect(manager.get('test-provider')).toBeUndefined();
      expect(manager.list()).toEqual([]);
      expect(eventSpy).toHaveBeenCalledWith({ name: 'test-provider' });
    });

    it('should handle unregistering non-existent provider', async () => {
      await expect(manager.unregister('non-existent')).resolves.not.toThrow();
    });
  });

  describe('cleanup', () => {
    it('should cleanup all providers and remove listeners', async () => {
      const anthropicConfig: ProviderConfig = {
        name: 'claude',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };

      const openaiConfig: ProviderConfig = {
        name: 'gpt4',
        type: 'openai',
        apiKey: 'test-key',
        model: 'gpt-4'
      };

      await manager.register(anthropicConfig);
      await manager.register(openaiConfig);

      const eventSpy = vi.fn();
      manager.on('test', eventSpy);

      await manager.cleanup();

      expect(manager.list()).toEqual([]);
      expect(manager.get('claude')).toBeUndefined();
      expect(manager.get('gpt4')).toBeUndefined();
      expect(manager.listenerCount('test')).toBe(0);
    });
  });

  describe('factory function', () => {
    it('should create new instance each time', () => {
      const manager1 = createProviderManager();
      const manager2 = createProviderManager();
      
      expect(manager1).not.toBe(manager2);
      expect(manager1).toBeInstanceOf(ProviderManager);
      expect(manager2).toBeInstanceOf(ProviderManager);
    });
  });

  describe('event handling', () => {
    it('should emit registration events in correct order', async () => {
      const events: string[] = [];
      
      manager.on('provider:registered', () => events.push('registered'));
      manager.on('provider:unregistered', () => events.push('unregistered'));

      const config: ProviderConfig = {
        name: 'test-provider',
        type: 'anthropic',
        apiKey: 'test-key',
        model: 'claude-3-sonnet'
      };

      await manager.register(config);
      await manager.unregister('test-provider');

      expect(events).toEqual(['registered', 'unregistered']);
    });
  });
});

describe('AnthropicProvider', () => {
  let provider: AnthropicProvider;
  let config: ProviderConfig;

  beforeEach(() => {
    config = {
      name: 'claude',
      type: 'anthropic',
      apiKey: 'test-key',
      model: 'claude-3-sonnet',
      maxTokens: 1000,
      temperature: 0.7
    };
    provider = new AnthropicProvider(config);
  });

  afterEach(async () => {
    await provider.cleanup();
  });

  describe('initialization', () => {
    it('should initialize with valid config', async () => {
      const eventSpy = vi.fn();
      provider.on('initialized', eventSpy);

      await provider.initialize();

      expect(eventSpy).toHaveBeenCalledWith({ provider: 'claude' });
    });

    it('should handle initialization errors', async () => {
      // Mock the import to fail
      vi.doMock('@anthropic-ai/sdk', () => {
        throw new Error('Failed to import');
      });

      const errorSpy = vi.fn();
      provider.on('error', errorSpy);

      await expect(provider.initialize()).rejects.toThrow();
      expect(errorSpy).toHaveBeenCalled();
    });
  });

  describe('message generation', () => {
    beforeEach(async () => {
      await provider.initialize();
    });

    it('should generate response from messages', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const eventSpy = vi.fn();
      provider.on('response', eventSpy);

      const response = await provider.generate(messages);

      expect(response).toMatchObject({
        content: 'Mock Anthropic response',
        usage: {
          inputTokens: 10,
          outputTokens: 20,
          totalTokens: 30
        },
        model: 'claude-3',
        metadata: {
          id: 'msg_123',
          type: 'message'
        }
      });

      expect(eventSpy).toHaveBeenCalledWith({
        messages,
        response,
        provider: 'claude'
      });
    });

    it('should use custom options when provided', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const options = {
        maxTokens: 500,
        temperature: 0.5,
        model: 'claude-3-opus'
      };

      await provider.generate(messages, options);

      // Check that the mocked client was called with correct parameters
      const mockClient = (provider as any).client;
      expect(mockClient.messages.create).toHaveBeenCalledWith({
        model: 'claude-3-opus',
        max_tokens: 500,
        temperature: 0.5,
        messages: [{ role: 'user', content: 'Hello' }]
      });
    });

    it('should throw error when not initialized', async () => {
      const uninitializedProvider = new AnthropicProvider(config);
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      await expect(uninitializedProvider.generate(messages))
        .rejects.toThrow('Provider not initialized');
    });

    it('should handle API errors', async () => {
      // Mock the client to throw an error
      const mockClient = (provider as any).client;
      mockClient.messages.create.mockRejectedValueOnce(new Error('API Error'));

      const errorSpy = vi.fn();
      provider.on('error', errorSpy);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      await expect(provider.generate(messages)).rejects.toThrow('API Error');
      expect(errorSpy).toHaveBeenCalled();
    });
  });

  describe('streaming generation', () => {
    beforeEach(async () => {
      await provider.initialize();
    });

    it('should handle streaming generation', async () => {
      // Mock streaming response
      const mockStream = {
        async *[Symbol.asyncIterator]() {
          yield { type: 'message_start', message: { usage: { input_tokens: 10 }, model: 'claude-3' } };
          yield { type: 'content_block_delta', delta: { text: 'Hello' } };
          yield { type: 'content_block_delta', delta: { text: ' world' } };
          yield { type: 'message_delta', usage: { output_tokens: 5 } };
        }
      };

      const mockClient = (provider as any).client;
      mockClient.messages.create.mockResolvedValueOnce(mockStream);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const chunks: string[] = [];
      const generator = provider.streamGenerate(messages);
      
      for await (const chunk of generator) {
        if (typeof chunk === 'string') {
          chunks.push(chunk);
        } else {
          // Final response
          expect(chunk).toMatchObject({
            content: 'Hello world',
            usage: { inputTokens: 10, outputTokens: 5, totalTokens: 15 },
            model: 'claude-3',
            metadata: { streamed: true }
          });
        }
      }

      expect(chunks).toEqual(['Hello', ' world']);
    });

    it('should throw error when streaming not initialized', async () => {
      const uninitializedProvider = new AnthropicProvider(config);
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const generator = uninitializedProvider.streamGenerate(messages);
      await expect(generator.next()).rejects.toThrow('Provider not initialized');
    });
  });

  describe('availability check', () => {
    it('should return false when not initialized', async () => {
      const available = await provider.isAvailable();
      expect(available).toBe(false);
    });

    it('should return true when initialized and API is available', async () => {
      await provider.initialize();
      
      const available = await provider.isAvailable();
      expect(available).toBe(true);
    });

    it('should return false when API call fails', async () => {
      await provider.initialize();
      
      // Mock the client to throw an error
      const mockClient = (provider as any).client;
      mockClient.messages.create.mockRejectedValueOnce(new Error('API Error'));
      
      const available = await provider.isAvailable();
      expect(available).toBe(false);
    });
  });
});

describe('OpenAIProvider', () => {
  let provider: OpenAIProvider;
  let config: ProviderConfig;

  beforeEach(() => {
    config = {
      name: 'gpt4',
      type: 'openai',
      apiKey: 'test-key',
      model: 'gpt-4',
      maxTokens: 1000,
      temperature: 0.7,
      topP: 0.9
    };
    provider = new OpenAIProvider(config);
  });

  afterEach(async () => {
    await provider.cleanup();
  });

  describe('initialization', () => {
    it('should initialize with valid config', async () => {
      const eventSpy = vi.fn();
      provider.on('initialized', eventSpy);

      await provider.initialize();

      expect(eventSpy).toHaveBeenCalledWith({ provider: 'gpt4' });
    });
  });

  describe('message generation', () => {
    beforeEach(async () => {
      await provider.initialize();
    });

    it('should generate response from messages', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const response = await provider.generate(messages);

      expect(response).toMatchObject({
        content: 'Mock OpenAI response',
        usage: {
          inputTokens: 10,
          outputTokens: 20,
          totalTokens: 30
        },
        model: 'gpt-4',
        metadata: {
          id: 'chatcmpl_123',
          created: 1234567890
        }
      });
    });

    it('should use custom options including topP', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello' }
      ];

      const options = {
        maxTokens: 500,
        temperature: 0.5,
        topP: 0.8,
        model: 'gpt-3.5-turbo'
      };

      await provider.generate(messages, options);

      const mockClient = (provider as any).client;
      expect(mockClient.chat.completions.create).toHaveBeenCalledWith({
        model: 'gpt-3.5-turbo',
        max_tokens: 500,
        temperature: 0.5,
        top_p: 0.8,
        messages: [{ role: 'user', content: 'Hello' }]
      });
    });
  });

  describe('availability check', () => {
    it('should return true when models list is accessible', async () => {
      await provider.initialize();
      
      const available = await provider.isAvailable();
      expect(available).toBe(true);
    });

    it('should return false when models list fails', async () => {
      await provider.initialize();
      
      const mockClient = (provider as any).client;
      mockClient.models.list.mockRejectedValueOnce(new Error('API Error'));
      
      const available = await provider.isAvailable();
      expect(available).toBe(false);
    });
  });
});
