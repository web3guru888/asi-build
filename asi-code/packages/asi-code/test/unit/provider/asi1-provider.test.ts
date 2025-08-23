/**
 * Unit tests for ASI1 Provider
 * 
 * Tests the ASI1 AI model provider including:
 * - Configuration management
 * - Message generation
 * - Streaming support
 * - Error handling
 * - Connection testing
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  ASI1Provider,
  createASI1Provider,
  type ASI1Config,
  type ASI1Request,
  type ASI1Response
} from '../../../src/provider/asi1.js';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('ASI1Provider', () => {
  let provider: ASI1Provider;
  let config: ASI1Config;

  beforeEach(() => {
    config = {
      apiKey: 'test-asi1-key',
      baseUrl: 'https://api.asi1.test/v1',
      model: 'asi1-test',
      temperature: 0.7,
      maxTokens: 2000,
      contextWindow: 64000
    };
    provider = new ASI1Provider(config);
    
    // Reset all mocks
    vi.clearAllMocks();
  });

  describe('constructor and configuration', () => {
    it('should initialize with provided config', () => {
      expect(provider.getConfig()).toEqual({
        apiKey: 'test-asi1-key',
        baseUrl: 'https://api.asi1.test/v1',
        model: 'asi1-test',
        temperature: 0.7,
        maxTokens: 2000,
        contextWindow: 64000
      });
    });

    it('should use defaults when config is empty', () => {
      const defaultProvider = new ASI1Provider();
      const defaultConfig = defaultProvider.getConfig();
      
      expect(defaultConfig).toEqual({
        apiKey: '',
        baseUrl: 'https://api.asi1.dev/v1',
        model: 'asi-1-turbo',
        temperature: 0.7,
        maxTokens: 4096,
        contextWindow: 128000
      });
    });

    it('should use environment variable for API key when not provided', () => {
      // Mock environment variable
      const originalEnv = process.env.ASI1_API_KEY;
      process.env.ASI1_API_KEY = 'env-test-key';
      
      const envProvider = new ASI1Provider({});
      expect(envProvider.getConfig().apiKey).toBe('env-test-key');
      
      // Restore environment
      process.env.ASI1_API_KEY = originalEnv;
    });

    it('should merge partial config with defaults', () => {
      const partialConfig: ASI1Config = {
        model: 'asi1-custom',
        temperature: 0.5
      };
      
      const partialProvider = new ASI1Provider(partialConfig);
      const resultConfig = partialProvider.getConfig();
      
      expect(resultConfig.model).toBe('asi1-custom');
      expect(resultConfig.temperature).toBe(0.5);
      expect(resultConfig.baseUrl).toBe('https://api.asi1.dev/v1'); // Default
      expect(resultConfig.maxTokens).toBe(4096); // Default
    });
  });

  describe('updateConfig', () => {
    it('should update configuration', () => {
      const updates: Partial<ASI1Config> = {
        temperature: 0.9,
        maxTokens: 8000,
        model: 'asi1-updated'
      };
      
      provider.updateConfig(updates);
      const updatedConfig = provider.getConfig();
      
      expect(updatedConfig.temperature).toBe(0.9);
      expect(updatedConfig.maxTokens).toBe(8000);
      expect(updatedConfig.model).toBe('asi1-updated');
      expect(updatedConfig.apiKey).toBe('test-asi1-key'); // Unchanged
    });

    it('should preserve existing config when updating', () => {
      const originalConfig = provider.getConfig();
      
      provider.updateConfig({ temperature: 0.3 });
      const updatedConfig = provider.getConfig();
      
      expect(updatedConfig.temperature).toBe(0.3);
      expect(updatedConfig.apiKey).toBe(originalConfig.apiKey);
      expect(updatedConfig.model).toBe(originalConfig.model);
    });
  });

  describe('generate', () => {
    const mockSuccessResponse = {
      choices: [{
        message: {
          content: 'Test response from ASI1'
        }
      }],
      usage: {
        prompt_tokens: 15,
        completion_tokens: 25,
        total_tokens: 40
      },
      model: 'asi1-test'
    };

    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSuccessResponse)
      });
    });

    it('should generate response from messages', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'user', content: 'Hello ASI1' }
        ]
      };

      const response = await provider.generate(request);

      expect(response).toEqual({
        content: 'Test response from ASI1',
        usage: {
          promptTokens: 15,
          completionTokens: 25,
          totalTokens: 40
        },
        model: 'asi1-test',
        timestamp: expect.any(Date)
      });
    });

    it('should use request-specific parameters', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'user', content: 'Hello' }
        ],
        temperature: 0.3,
        maxTokens: 1000,
        tools: [{
          name: 'test-tool',
          description: 'A test tool',
          parameters: { type: 'object' }
        }]
      };

      await provider.generate(request);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.asi1.test/v1/chat/completions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-asi1-key',
            'User-Agent': 'asi-code/1.0.0'
          },
          body: JSON.stringify({
            model: 'asi1-test',
            messages: request.messages,
            temperature: 0.3,
            max_tokens: 1000,
            tools: request.tools
          })
        }
      );
    });

    it('should use default config when request parameters not provided', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'user', content: 'Hello' }
        ]
      };

      await provider.generate(request);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.asi1.test/v1/chat/completions',
        expect.objectContaining({
          body: JSON.stringify({
            model: 'asi1-test',
            messages: request.messages,
            temperature: 0.7, // From config
            max_tokens: 2000, // From config
            tools: undefined
          })
        })
      );
    });

    it('should throw error when API key is missing', async () => {
      const noKeyProvider = new ASI1Provider({ apiKey: '' });
      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(noKeyProvider.generate(request))
        .rejects.toThrow('ASI1 API key is required');
    });

    it('should handle API error responses', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        text: () => Promise.resolve('Unauthorized')
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.generate(request))
        .rejects.toThrow('ASI1 API error (401): Unauthorized');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.generate(request))
        .rejects.toThrow('Failed to generate response from ASI1: Network error');
    });

    it('should handle missing response content', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          choices: [],
          usage: { prompt_tokens: 10, completion_tokens: 0, total_tokens: 10 },
          model: 'asi1-test'
        })
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      const response = await provider.generate(request);
      expect(response.content).toBe('');
    });

    it('should handle missing usage data', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          choices: [{ message: { content: 'Response' } }],
          model: 'asi1-test'
        })
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      const response = await provider.generate(request);
      expect(response.usage).toEqual({
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0
      });
    });

    it('should include system messages in request', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'system', content: 'You are a helpful assistant' },
          { role: 'user', content: 'Hello' },
          { role: 'assistant', content: 'Hi there!' },
          { role: 'user', content: 'How are you?' }
        ]
      };

      await provider.generate(request);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('You are a helpful assistant')
        })
      );
    });
  });

  describe('streamGenerate', () => {
    it('should throw error when API key is missing', async () => {
      const noKeyProvider = new ASI1Provider({ apiKey: '' });
      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(noKeyProvider.streamGenerate(request))
        .rejects.toThrow('ASI1 API key is required');
    });

    it('should make streaming request with correct parameters', async () => {
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'));
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.close();
        }
      });

      mockFetch.mockResolvedValue({
        ok: true,
        body: mockStream
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }],
        temperature: 0.5,
        maxTokens: 1500
      };

      const stream = await provider.streamGenerate(request);
      
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.asi1.test/v1/chat/completions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-asi1-key',
            'User-Agent': 'asi-code/1.0.0'
          },
          body: JSON.stringify({
            messages: request.messages,
            model: 'asi1-test',
            stream: true,
            temperature: 0.5,
            max_tokens: 1500
          })
        }
      );
    });

    it('should handle streaming API errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        text: () => Promise.resolve('Bad Request')
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.streamGenerate(request))
        .rejects.toThrow('ASI1 API error (400): Bad Request');
    });

    it('should parse streaming response correctly', async () => {
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'));
          controller.enqueue(new TextEncoder().encode('data: {"choices":[{"delta":{"content":" world"}}]}\n\n'));
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.close();
        }
      });

      mockFetch.mockResolvedValue({
        ok: true,
        body: mockStream
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      const stream = await provider.streamGenerate(request);
      const chunks: string[] = [];
      
      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Hello', ' world']);
    });

    it('should handle malformed streaming data gracefully', async () => {
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: {"invalid":"json"\n\n'));
          controller.enqueue(new TextEncoder().encode('data: {"choices":[{"delta":{"content":"Valid"}}]}\n\n'));
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.close();
        }
      });

      mockFetch.mockResolvedValue({
        ok: true,
        body: mockStream
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      const stream = await provider.streamGenerate(request);
      const chunks: string[] = [];
      
      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Valid']); // Only valid content should be yielded
    });

    it('should handle empty response body', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        body: null
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.streamGenerate(request))
        .rejects.toThrow('No response body received from ASI1 API');
    });
  });

  describe('getAvailableModels', () => {
    it('should return list of available models', () => {
      const models = provider.getAvailableModels();
      expect(models).toEqual(['asi1-mini', 'asi1-extended', 'asi1-thinking', 'asi1-graph']);
    });
  });

  describe('testConnection', () => {
    it('should return true for successful connection test', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          choices: [{ message: { content: 'OK' } }],
          usage: { prompt_tokens: 5, completion_tokens: 1, total_tokens: 6 },
          model: 'asi1-test'
        })
      });

      const result = await provider.testConnection();
      expect(result).toBe(true);

      // Verify the test request was made correctly
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            model: 'asi1-test',
            messages: [{ role: 'user', content: 'Test connection. Respond with "OK".' }],
            temperature: 0,
            max_tokens: 10,
            tools: undefined
          })
        })
      );
    });

    it('should return true for response containing "ok" (case insensitive)', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          choices: [{ message: { content: 'Response: ok' } }],
          usage: { prompt_tokens: 5, completion_tokens: 1, total_tokens: 6 },
          model: 'asi1-test'
        })
      });

      const result = await provider.testConnection();
      expect(result).toBe(true);
    });

    it('should return false for connection test failure', async () => {
      mockFetch.mockRejectedValue(new Error('Connection failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const result = await provider.testConnection();
      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith('ASI1 connection test failed:', expect.any(Error));
      
      consoleSpy.mockRestore();
    });

    it('should return false for unexpected response content', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          choices: [{ message: { content: 'Unexpected response' } }],
          usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
          model: 'asi1-test'
        })
      });

      const result = await provider.testConnection();
      expect(result).toBe(false);
    });

    it('should handle missing API key in connection test', async () => {
      const noKeyProvider = new ASI1Provider({ apiKey: '' });
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const result = await noKeyProvider.testConnection();
      expect(result).toBe(false);
      expect(consoleSpy).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });

  describe('factory function', () => {
    it('should create new instance with config', () => {
      const testConfig: ASI1Config = {
        model: 'asi1-factory-test',
        temperature: 0.8
      };
      
      const factoryProvider = createASI1Provider(testConfig);
      
      expect(factoryProvider).toBeInstanceOf(ASI1Provider);
      expect(factoryProvider.getConfig().model).toBe('asi1-factory-test');
      expect(factoryProvider.getConfig().temperature).toBe(0.8);
    });

    it('should create new instance without config', () => {
      const factoryProvider = createASI1Provider();
      
      expect(factoryProvider).toBeInstanceOf(ASI1Provider);
      expect(factoryProvider.getConfig().model).toBe('asi-1-turbo'); // Default
    });

    it('should create different instances each time', () => {
      const provider1 = createASI1Provider();
      const provider2 = createASI1Provider();
      
      expect(provider1).not.toBe(provider2);
    });
  });

  describe('error handling edge cases', () => {
    it('should handle non-Error exceptions in generate', async () => {
      mockFetch.mockRejectedValue('String error');

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.generate(request))
        .rejects.toThrow('Failed to generate response from ASI1: String error');
    });

    it('should handle fetch throwing non-Error in streamGenerate', async () => {
      mockFetch.mockRejectedValue('Network failure');

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Hello' }]
      };

      await expect(provider.streamGenerate(request))
        .rejects.toThrow('Network failure');
    });
  });
});
