/**
 * Unit tests for ASI1 Provider
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ASI1Provider, createASI1Provider } from '../../../src/provider/asi1.js';
import type { ASI1Config, ASI1Request, ASI1Response } from '../../../src/provider/asi1.js';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('ASI1Provider', () => {
  let provider: ASI1Provider;
  
  beforeEach(() => {
    vi.clearAllMocks();
    provider = new ASI1Provider();
    // Clear environment variables
    delete process.env.ASI1_API_KEY;
  });

  describe('Constructor and Configuration', () => {
    it('should create provider with default config', () => {
      const defaultProvider = new ASI1Provider();
      const config = defaultProvider.getConfig();
      
      expect(config).toMatchObject({
        apiKey: '',
        baseUrl: 'https://api.asi1.dev/v1',
        model: 'asi-1-turbo',
        temperature: 0.7,
        maxTokens: 4096,
        contextWindow: 128000
      });
    });

    it('should create provider with custom config', () => {
      const customConfig: ASI1Config = {
        apiKey: 'custom-key',
        baseUrl: 'https://custom.api.com',
        model: 'custom-model',
        temperature: 0.5,
        maxTokens: 2048,
        contextWindow: 64000
      };
      
      const customProvider = new ASI1Provider(customConfig);
      expect(customProvider.getConfig()).toEqual(customConfig);
    });

    it('should use environment variable for API key', () => {
      process.env.ASI1_API_KEY = 'env-api-key';
      
      const envProvider = new ASI1Provider();
      expect(envProvider.getConfig().apiKey).toBe('env-api-key');
    });

    it('should prioritize config API key over environment', () => {
      process.env.ASI1_API_KEY = 'env-key';
      
      const provider = new ASI1Provider({ apiKey: 'config-key' });
      expect(provider.getConfig().apiKey).toBe('config-key');
    });

    it('should update config', () => {
      provider.updateConfig({ temperature: 0.9, maxTokens: 8192 });
      
      const config = provider.getConfig();
      expect(config.temperature).toBe(0.9);
      expect(config.maxTokens).toBe(8192);
      expect(config.model).toBe('asi-1-turbo'); // Should preserve other values
    });
  });

  describe('Generation', () => {
    const mockResponse = {
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({
        choices: [{
          message: {
            content: 'Test response from ASI1'
          }
        }],
        usage: {
          prompt_tokens: 50,
          completion_tokens: 25,
          total_tokens: 75
        },
        model: 'asi-1-turbo'
      })
    };

    beforeEach(() => {
      process.env.ASI1_API_KEY = 'test-api-key';
      provider = new ASI1Provider();
      mockFetch.mockResolvedValue(mockResponse);
    });

    it('should generate response successfully', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'user', content: 'Hello, ASI1!' }
        ]
      };

      const response = await provider.generate(request);

      expect(response).toMatchObject({
        content: 'Test response from ASI1',
        usage: {
          promptTokens: 50,
          completionTokens: 25,
          totalTokens: 75
        },
        model: 'asi-1-turbo'
      });
      expect(response.timestamp).toBeInstanceOf(Date);
    });

    it('should make correct API call', async () => {
      const request: ASI1Request = {
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'Hello!' }
        ],
        temperature: 0.8,
        maxTokens: 1024
      };

      await provider.generate(request);

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.asi1.dev/v1/chat/completions',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-api-key',
            'User-Agent': 'asi-code/1.0.0'
          },
          body: JSON.stringify({
            model: 'asi-1-turbo',
            messages: request.messages,
            temperature: 0.8,
            max_tokens: 1024,
            tools: undefined
          })
        }
      );
    });

    it('should use default values for optional parameters', async () => {
      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Test' }]
      };

      await provider.generate(request);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.temperature).toBe(0.7); // Default from provider config
      expect(callBody.max_tokens).toBe(4096);
    });

    it('should include tools in request', async () => {
      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Use tools' }],
        tools: [
          {
            name: 'test_tool',
            description: 'A test tool',
            parameters: { type: 'object' }
          }
        ]
      };

      await provider.generate(request);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.tools).toEqual(request.tools);
    });

    it('should throw error when API key is missing', async () => {
      const providerWithoutKey = new ASI1Provider({ apiKey: '' });
      
      await expect(providerWithoutKey.generate({
        messages: [{ role: 'user', content: 'Test' }]
      })).rejects.toThrow('ASI1 API key is required');
    });

    it('should handle API errors', async () => {
      const errorResponse = {
        ok: false,
        status: 400,
        text: vi.fn().mockResolvedValue('Bad Request: Invalid parameters')
      };
      
      mockFetch.mockResolvedValue(errorResponse);

      await expect(provider.generate({
        messages: [{ role: 'user', content: 'Test' }]
      })).rejects.toThrow('ASI1 API error (400): Bad Request: Invalid parameters');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      await expect(provider.generate({
        messages: [{ role: 'user', content: 'Test' }]
      })).rejects.toThrow('Failed to generate response from ASI1: Network error');
    });

    it('should handle malformed API responses', async () => {
      const malformedResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({
          // Missing expected fields
          error: 'Invalid response format'
        })
      };
      
      mockFetch.mockResolvedValue(malformedResponse);

      const response = await provider.generate({
        messages: [{ role: 'user', content: 'Test' }]
      });

      expect(response.content).toBe('');
      expect(response.usage).toEqual({
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0
      });
    });
  });

  describe('Streaming Generation', () => {
    beforeEach(() => {
      process.env.ASI1_API_KEY = 'test-api-key';
      provider = new ASI1Provider();
    });

    it('should stream response chunks', async () => {
      const streamData = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
        'data: {"choices":[{"delta":{"content":" world"}}]}\n',
        'data: {"choices":[{"delta":{"content":"!"}}]}\n',
        'data: [DONE]\n'
      ];

      const mockStream = new ReadableStream({
        start(controller) {
          for (const chunk of streamData) {
            controller.enqueue(new TextEncoder().encode(chunk));
          }
          controller.close();
        }
      });

      const streamResponse = {
        ok: true,
        status: 200,
        body: mockStream
      };

      mockFetch.mockResolvedValue(streamResponse);

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Say hello' }]
      };

      const chunks: string[] = [];
      const stream = await provider.streamGenerate(request);

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Hello', ' world', '!']);
    });

    it('should make correct streaming API call', async () => {
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n'));
          controller.close();
        }
      });

      mockFetch.mockResolvedValue({
        ok: true,
        body: mockStream
      });

      const request: ASI1Request = {
        messages: [{ role: 'user', content: 'Test streaming' }],
        temperature: 0.5
      };

      await provider.streamGenerate(request);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody).toMatchObject({
        model: 'asi-1-turbo',
        stream: true,
        temperature: 0.5,
        max_tokens: 4096
      });
    });

    it('should handle streaming errors', async () => {
      const errorResponse = {
        ok: false,
        status: 500,
        text: vi.fn().mockResolvedValue('Server error')
      };

      mockFetch.mockResolvedValue(errorResponse);

      await expect(provider.streamGenerate({
        messages: [{ role: 'user', content: 'Test' }]
      })).rejects.toThrow('ASI1 API error (500): Server error');
    });

    it('should handle missing response body', async () => {
      const responseWithoutBody = {
        ok: true,
        body: null
      };

      mockFetch.mockResolvedValue(responseWithoutBody);

      await expect(provider.streamGenerate({
        messages: [{ role: 'user', content: 'Test' }]
      })).rejects.toThrow('No response body received from ASI1 API');
    });

    it('should handle malformed streaming data', async () => {
      const streamData = [
        'data: invalid json\n',
        'data: {"valid": "json", "choices":[{"delta":{"content":"Hello"}}]}\n',
        'data: [DONE]\n'
      ];

      const mockStream = new ReadableStream({
        start(controller) {
          for (const chunk of streamData) {
            controller.enqueue(new TextEncoder().encode(chunk));
          }
          controller.close();
        }
      });

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      mockFetch.mockResolvedValue({
        ok: true,
        body: mockStream
      });

      const chunks: string[] = [];
      const stream = await provider.streamGenerate({
        messages: [{ role: 'user', content: 'Test' }]
      });

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Hello']);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to parse streaming response line:',
        'data: invalid json'
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Utility Methods', () => {
    it('should return available models', () => {
      const models = provider.getAvailableModels();
      expect(models).toEqual(['asi1-mini', 'asi1-extended', 'asi1-thinking', 'asi1-graph']);
    });

    it('should test connection successfully', async () => {
      process.env.ASI1_API_KEY = 'test-key';
      provider = new ASI1Provider();

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          choices: [{ message: { content: 'OK' } }],
          usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
          model: 'asi-1-turbo'
        })
      };
      
      mockFetch.mockResolvedValue(mockResponse);

      const isConnected = await provider.testConnection();
      
      expect(isConnected).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.asi1.dev/v1/chat/completions',
        expect.objectContaining({
          body: expect.stringContaining('"temperature":0')
        })
      );
    });

    it('should handle connection test failure', async () => {
      process.env.ASI1_API_KEY = 'test-key';
      provider = new ASI1Provider();

      mockFetch.mockRejectedValue(new Error('Connection failed'));
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const isConnected = await provider.testConnection();
      
      expect(isConnected).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        'ASI1 connection test failed:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('should handle connection test with non-OK response', async () => {
      process.env.ASI1_API_KEY = 'test-key';
      provider = new ASI1Provider();

      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          choices: [{ message: { content: 'Error: Invalid request' } }],
          usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
          model: 'asi-1-turbo'
        })
      };
      
      mockFetch.mockResolvedValue(mockResponse);

      const isConnected = await provider.testConnection();
      expect(isConnected).toBe(false);
    });
  });

  describe('Factory Function', () => {
    it('should create provider using factory function', () => {
      const config: ASI1Config = {
        apiKey: 'factory-key',
        model: 'factory-model'
      };
      
      const factoryProvider = createASI1Provider(config);
      
      expect(factoryProvider).toBeInstanceOf(ASI1Provider);
      expect(factoryProvider.getConfig()).toMatchObject(config);
    });

    it('should create provider with default config using factory', () => {
      const factoryProvider = createASI1Provider();
      
      expect(factoryProvider).toBeInstanceOf(ASI1Provider);
      expect(factoryProvider.getConfig().baseUrl).toBe('https://api.asi1.dev/v1');
    });
  });

  describe('Edge Cases', () => {
    beforeEach(() => {
      process.env.ASI1_API_KEY = 'test-key';
      provider = new ASI1Provider();
    });

    it('should handle empty response content', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          choices: [{ message: { content: '' } }],
          usage: { prompt_tokens: 10, completion_tokens: 0, total_tokens: 10 },
          model: 'asi-1-turbo'
        })
      };
      
      mockFetch.mockResolvedValue(mockResponse);

      const response = await provider.generate({
        messages: [{ role: 'user', content: 'Empty response test' }]
      });

      expect(response.content).toBe('');
      expect(response.usage.completionTokens).toBe(0);
    });

    it('should handle response with missing usage data', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          choices: [{ message: { content: 'Response without usage' } }],
          model: 'asi-1-turbo'
          // Missing usage field
        })
      };
      
      mockFetch.mockResolvedValue(mockResponse);

      const response = await provider.generate({
        messages: [{ role: 'user', content: 'Test' }]
      });

      expect(response.content).toBe('Response without usage');
      expect(response.usage).toEqual({
        promptTokens: 0,
        completionTokens: 0,
        totalTokens: 0
      });
    });

    it('should handle multiple message roles', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          choices: [{ message: { content: 'Multi-role response' } }],
          usage: { prompt_tokens: 100, completion_tokens: 20, total_tokens: 120 },
          model: 'asi-1-turbo'
        })
      };
      
      mockFetch.mockResolvedValue(mockResponse);

      const request: ASI1Request = {
        messages: [
          { role: 'system', content: 'You are a helpful assistant.' },
          { role: 'user', content: 'Hello!' },
          { role: 'assistant', content: 'Hi there! How can I help?' },
          { role: 'user', content: 'Tell me a joke.' }
        ]
      };

      const response = await provider.generate(request);

      expect(response.content).toBe('Multi-role response');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"messages":[')
        })
      );
    });

    it('should preserve immutability of config', () => {
      const originalConfig = provider.getConfig();
      originalConfig.temperature = 999;
      
      expect(provider.getConfig().temperature).toBe(0.7);
    });
  });
});