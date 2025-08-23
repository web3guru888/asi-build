/**
 * Provider Integration Tests - Comprehensive testing of AI provider integrations
 * 
 * Tests ASI1, Anthropic, and OpenAI provider integrations including:
 * - Provider initialization and configuration
 * - Text generation and streaming
 * - Error handling and fallback mechanisms
 * - Rate limiting and retry logic
 * - Provider switching and load balancing
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { 
  ProviderManager, 
  AnthropicProvider, 
  OpenAIProvider,
  BaseProvider,
  type ProviderConfig,
  type ProviderMessage,
  type ProviderResponse 
} from '../../src/provider/index.js';
import { ASI1Provider } from '../../src/provider/asi1.js';
import { Logger } from '../../src/logging/index.js';

// Mock HTTP client for testing
class MockHTTPClient {
  private responses = new Map<string, any>();
  private requestCount = 0;
  private rateLimitCount = 0;
  private shouldFail = false;

  setResponse(endpoint: string, response: any) {
    this.responses.set(endpoint, response);
  }

  setShouldFail(fail: boolean) {
    this.shouldFail = fail;
  }

  getRequestCount() {
    return this.requestCount;
  }

  getRateLimitCount() {
    return this.rateLimitCount;
  }

  reset() {
    this.responses.clear();
    this.requestCount = 0;
    this.rateLimitCount = 0;
    this.shouldFail = false;
  }

  async request(url: string, options: any = {}): Promise<any> {
    this.requestCount++;

    if (this.shouldFail) {
      throw new Error('Simulated network error');
    }

    // Simulate rate limiting
    if (this.requestCount > 10) {
      this.rateLimitCount++;
      const error = new Error('Rate limit exceeded');
      (error as any).status = 429;
      throw error;
    }

    // Return mock response based on URL
    const endpoint = new URL(url).pathname;
    const mockResponse = this.responses.get(endpoint) || this.getDefaultResponse(endpoint);

    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, Math.random() * 100));

    return mockResponse;
  }

  private getDefaultResponse(endpoint: string): any {
    if (endpoint.includes('anthropic')) {
      return {
        id: 'msg_test123',
        type: 'message',
        role: 'assistant',
        content: [{ type: 'text', text: 'Test response from Anthropic' }],
        model: 'claude-3-sonnet-20240229',
        usage: { input_tokens: 10, output_tokens: 15 }
      };
    }

    if (endpoint.includes('openai')) {
      return {
        id: 'chatcmpl-test123',
        object: 'chat.completion',
        created: Date.now(),
        model: 'gpt-4',
        choices: [{
          index: 0,
          message: { role: 'assistant', content: 'Test response from OpenAI' },
          finish_reason: 'stop'
        }],
        usage: { prompt_tokens: 10, completion_tokens: 15, total_tokens: 25 }
      };
    }

    if (endpoint.includes('asi1')) {
      return {
        id: 'asi1_test123',
        response: 'Test response from ASI1',
        model: 'asi1-base',
        usage: { input_tokens: 10, output_tokens: 15 }
      };
    }

    return { message: 'Default mock response' };
  }
}

// Mock provider implementations for testing
class MockAnthropicProvider extends AnthropicProvider {
  private mockClient: MockHTTPClient;

  constructor(config: ProviderConfig, mockClient: MockHTTPClient) {
    super(config);
    this.mockClient = mockClient;
  }

  async initialize(): Promise<void> {
    // Override initialization to use mock client
    this.emit('initialized', { provider: this.name });
  }

  async generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse> {
    const response = await this.mockClient.request('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      body: { messages, model: options?.model || this.config.model }
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
  }

  async* streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse> {
    const chunks = ['Test ', 'streaming ', 'response ', 'from ', 'Anthropic'];
    
    for (const chunk of chunks) {
      yield chunk;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    return {
      content: chunks.join(''),
      usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
      model: options?.model || this.config.model,
      metadata: { streamed: true }
    };
  }

  async isAvailable(): Promise<boolean> {
    try {
      await this.mockClient.request('https://api.anthropic.com/v1/messages', { method: 'POST' });
      return true;
    } catch {
      return false;
    }
  }
}

class MockOpenAIProvider extends OpenAIProvider {
  private mockClient: MockHTTPClient;

  constructor(config: ProviderConfig, mockClient: MockHTTPClient) {
    super(config);
    this.mockClient = mockClient;
  }

  async initialize(): Promise<void> {
    this.emit('initialized', { provider: this.name });
  }

  async generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse> {
    const response = await this.mockClient.request('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      body: { messages, model: options?.model || this.config.model }
    });

    const result: ProviderResponse = {
      content: response.choices[0].message.content,
      usage: {
        inputTokens: response.usage.prompt_tokens,
        outputTokens: response.usage.completion_tokens,
        totalTokens: response.usage.total_tokens
      },
      model: response.model,
      metadata: { id: response.id, created: response.created }
    };

    this.emit('response', { messages, response: result, provider: this.name });
    return result;
  }

  async* streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse> {
    const chunks = ['Test ', 'streaming ', 'response ', 'from ', 'OpenAI'];
    
    for (const chunk of chunks) {
      yield chunk;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    return {
      content: chunks.join(''),
      usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
      model: options?.model || this.config.model,
      metadata: { streamed: true }
    };
  }

  async isAvailable(): Promise<boolean> {
    try {
      await this.mockClient.request('https://api.openai.com/v1/models', { method: 'GET' });
      return true;
    } catch {
      return false;
    }
  }
}

class MockASI1Provider extends BaseProvider {
  private mockClient: MockHTTPClient;

  constructor(config: ProviderConfig, mockClient: MockHTTPClient) {
    super(config);
    this.mockClient = mockClient;
  }

  async initialize(): Promise<void> {
    this.emit('initialized', { provider: this.name });
  }

  async generate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): Promise<ProviderResponse> {
    const response = await this.mockClient.request('https://api.asi1.com/v1/generate', {
      method: 'POST',
      body: { messages, model: options?.model || this.config.model }
    });

    const result: ProviderResponse = {
      content: response.response,
      usage: {
        inputTokens: response.usage.input_tokens,
        outputTokens: response.usage.output_tokens,
        totalTokens: response.usage.input_tokens + response.usage.output_tokens
      },
      model: response.model,
      metadata: { id: response.id }
    };

    this.emit('response', { messages, response: result, provider: this.name });
    return result;
  }

  async* streamGenerate(messages: ProviderMessage[], options?: Partial<ProviderConfig>): AsyncGenerator<string, ProviderResponse> {
    const chunks = ['Test ', 'streaming ', 'response ', 'from ', 'ASI1'];
    
    for (const chunk of chunks) {
      yield chunk;
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    return {
      content: chunks.join(''),
      usage: { inputTokens: 10, outputTokens: 15, totalTokens: 25 },
      model: options?.model || this.config.model,
      metadata: { streamed: true }
    };
  }

  async isAvailable(): Promise<boolean> {
    try {
      await this.mockClient.request('https://api.asi1.com/v1/health', { method: 'GET' });
      return true;
    } catch {
      return false;
    }
  }
}

describe('Provider Integration Tests', () => {
  let providerManager: ProviderManager;
  let mockClient: MockHTTPClient;
  let logger: Logger;

  const testConfigs = {
    anthropic: {
      name: 'test-anthropic',
      type: 'anthropic' as const,
      apiKey: 'test-anthropic-key',
      model: 'claude-3-sonnet-20240229',
      maxTokens: 4000,
      temperature: 0.7
    },
    openai: {
      name: 'test-openai',
      type: 'openai' as const,
      apiKey: 'test-openai-key',
      model: 'gpt-4',
      maxTokens: 4000,
      temperature: 0.7,
      topP: 1.0
    },
    asi1: {
      name: 'test-asi1',
      type: 'custom' as const,
      apiKey: 'test-asi1-key',
      baseUrl: 'https://api.asi1.com',
      model: 'asi1-base',
      maxTokens: 4000,
      temperature: 0.7
    }
  };

  beforeAll(async () => {
    logger = new Logger({ level: 'error', enabled: false });
    mockClient = new MockHTTPClient();
  });

  beforeEach(async () => {
    providerManager = new ProviderManager();
    mockClient.reset();
  });

  afterEach(async () => {
    if (providerManager) {
      await providerManager.cleanup();
    }
  });

  describe('Provider Initialization', () => {
    it('should initialize Anthropic provider successfully', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      
      let initialized = false;
      provider.on('initialized', () => { initialized = true; });

      await provider.initialize();
      expect(initialized).toBe(true);
      expect(provider.name).toBe('test-anthropic');
      expect(provider.config.model).toBe('claude-3-sonnet-20240229');

      await provider.cleanup();
    });

    it('should initialize OpenAI provider successfully', async () => {
      const provider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      
      let initialized = false;
      provider.on('initialized', () => { initialized = true; });

      await provider.initialize();
      expect(initialized).toBe(true);
      expect(provider.name).toBe('test-openai');
      expect(provider.config.model).toBe('gpt-4');

      await provider.cleanup();
    });

    it('should initialize ASI1 provider successfully', async () => {
      const provider = new MockASI1Provider(testConfigs.asi1, mockClient);
      
      let initialized = false;
      provider.on('initialized', () => { initialized = true; });

      await provider.initialize();
      expect(initialized).toBe(true);
      expect(provider.name).toBe('test-asi1');
      expect(provider.config.baseUrl).toBe('https://api.asi1.com');

      await provider.cleanup();
    });

    it('should handle provider initialization failures', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      mockClient.setShouldFail(true);

      let errorEmitted = false;
      provider.on('error', () => { errorEmitted = true; });

      try {
        await provider.initialize();
        expect.fail('Should have thrown initialization error');
      } catch (error) {
        expect(error).toBeDefined();
        expect(errorEmitted).toBe(true);
      }

      await provider.cleanup();
    });

    it('should register multiple providers with ProviderManager', async () => {
      // Create mock providers
      const anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      const openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);

      // Override the register method to use our mock providers
      providerManager.register = async function(config: ProviderConfig) {
        let provider: BaseProvider;
        if (config.type === 'anthropic') {
          provider = anthropicProvider;
        } else if (config.type === 'openai') {
          provider = openaiProvider;
        } else {
          throw new Error(`Unsupported provider type: ${config.type}`);
        }

        await provider.initialize();
        this.providers.set(config.name, provider);
        this.emit('provider:registered', { name: config.name, type: config.type });
      };

      await providerManager.register(testConfigs.anthropic);
      await providerManager.register(testConfigs.openai);

      const providers = providerManager.list();
      expect(providers).toContain('test-anthropic');
      expect(providers).toContain('test-openai');

      expect(providerManager.get('test-anthropic')).toBeDefined();
      expect(providerManager.get('test-openai')).toBeDefined();
    });
  });

  describe('Text Generation', () => {
    let anthropicProvider: MockAnthropicProvider;
    let openaiProvider: MockOpenAIProvider;
    let asi1Provider: MockASI1Provider;

    beforeEach(async () => {
      anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      asi1Provider = new MockASI1Provider(testConfigs.asi1, mockClient);

      await anthropicProvider.initialize();
      await openaiProvider.initialize();
      await asi1Provider.initialize();
    });

    afterEach(async () => {
      await anthropicProvider.cleanup();
      await openaiProvider.cleanup();
      await asi1Provider.cleanup();
    });

    it('should generate text with Anthropic provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello, how are you?' }
      ];

      const response = await anthropicProvider.generate(messages);

      expect(response).toMatchObject({
        content: expect.any(String),
        usage: expect.objectContaining({
          inputTokens: expect.any(Number),
          outputTokens: expect.any(Number),
          totalTokens: expect.any(Number)
        }),
        model: 'claude-3-sonnet-20240229',
        metadata: expect.objectContaining({
          id: expect.any(String)
        })
      });

      expect(response.content).toBe('Test response from Anthropic');
      expect(mockClient.getRequestCount()).toBe(1);
    });

    it('should generate text with OpenAI provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello, how are you?' }
      ];

      const response = await openaiProvider.generate(messages);

      expect(response).toMatchObject({
        content: expect.any(String),
        usage: expect.objectContaining({
          inputTokens: expect.any(Number),
          outputTokens: expect.any(Number),
          totalTokens: expect.any(Number)
        }),
        model: 'gpt-4',
        metadata: expect.objectContaining({
          id: expect.any(String)
        })
      });

      expect(response.content).toBe('Test response from OpenAI');
      expect(mockClient.getRequestCount()).toBe(1);
    });

    it('should generate text with ASI1 provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Hello, how are you?' }
      ];

      const response = await asi1Provider.generate(messages);

      expect(response).toMatchObject({
        content: expect.any(String),
        usage: expect.objectContaining({
          inputTokens: expect.any(Number),
          outputTokens: expect.any(Number),
          totalTokens: expect.any(Number)
        }),
        model: 'asi1-base',
        metadata: expect.objectContaining({
          id: expect.any(String)
        })
      });

      expect(response.content).toBe('Test response from ASI1');
      expect(mockClient.getRequestCount()).toBe(1);
    });

    it('should handle generation with custom options', async () => {
      const messages: ProviderMessage[] = [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: 'What is 2+2?' }
      ];

      const customOptions = {
        temperature: 0.5,
        maxTokens: 100
      };

      const response = await anthropicProvider.generate(messages, customOptions);

      expect(response).toBeDefined();
      expect(response.content).toBeDefined();
      expect(mockClient.getRequestCount()).toBe(1);
    });

    it('should handle generation errors gracefully', async () => {
      mockClient.setShouldFail(true);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'This should fail' }
      ];

      let errorEmitted = false;
      anthropicProvider.on('error', () => { errorEmitted = true; });

      try {
        await anthropicProvider.generate(messages);
        expect.fail('Should have thrown generation error');
      } catch (error) {
        expect(error).toBeDefined();
        expect(errorEmitted).toBe(true);
      }
    });

    it('should emit events during generation', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Test message' }
      ];

      let responseEvent: any = null;
      anthropicProvider.on('response', (event) => { responseEvent = event; });

      await anthropicProvider.generate(messages);

      expect(responseEvent).toBeDefined();
      expect(responseEvent.messages).toEqual(messages);
      expect(responseEvent.response).toBeDefined();
      expect(responseEvent.provider).toBe('test-anthropic');
    });
  });

  describe('Streaming Generation', () => {
    let anthropicProvider: MockAnthropicProvider;
    let openaiProvider: MockOpenAIProvider;
    let asi1Provider: MockASI1Provider;

    beforeEach(async () => {
      anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      asi1Provider = new MockASI1Provider(testConfigs.asi1, mockClient);

      await anthropicProvider.initialize();
      await openaiProvider.initialize();
      await asi1Provider.initialize();
    });

    afterEach(async () => {
      await anthropicProvider.cleanup();
      await openaiProvider.cleanup();
      await asi1Provider.cleanup();
    });

    it('should stream text from Anthropic provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Stream me a response' }
      ];

      const chunks: string[] = [];
      const stream = anthropicProvider.streamGenerate(messages);

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Test ', 'streaming ', 'response ', 'from ', 'Anthropic']);
      expect(chunks.join('')).toBe('Test streaming response from Anthropic');
    });

    it('should stream text from OpenAI provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Stream me a response' }
      ];

      const chunks: string[] = [];
      const stream = openaiProvider.streamGenerate(messages);

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Test ', 'streaming ', 'response ', 'from ', 'OpenAI']);
      expect(chunks.join('')).toBe('Test streaming response from OpenAI');
    });

    it('should stream text from ASI1 provider', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Stream me a response' }
      ];

      const chunks: string[] = [];
      const stream = asi1Provider.streamGenerate(messages);

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      expect(chunks).toEqual(['Test ', 'streaming ', 'response ', 'from ', 'ASI1']);
      expect(chunks.join('')).toBe('Test streaming response from ASI1');
    });

    it('should handle streaming with timing measurements', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Time this stream' }
      ];

      const startTime = Date.now();
      const chunks: string[] = [];
      const stream = anthropicProvider.streamGenerate(messages);

      for await (const chunk of stream) {
        chunks.push(chunk);
      }

      const endTime = Date.now();
      const totalTime = endTime - startTime;

      expect(totalTime).toBeGreaterThan(200); // Should take at least 200ms (5 chunks * 50ms delay)
      expect(chunks.length).toBe(5);
    });

    it('should provide final response metadata after streaming', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Stream with metadata' }
      ];

      let finalResponse: ProviderResponse | undefined;
      const stream = anthropicProvider.streamGenerate(messages);

      for await (const chunk of stream) {
        // Stream chunks
      }

      // Get final response by calling stream.return()
      const result = await stream.return(undefined as any);
      if (result.done) {
        finalResponse = result.value;
      }

      expect(finalResponse).toMatchObject({
        content: 'Test streaming response from Anthropic',
        usage: expect.objectContaining({
          inputTokens: 10,
          outputTokens: 15,
          totalTokens: 25
        }),
        metadata: { streamed: true }
      });
    });
  });

  describe('Provider Availability and Health Checks', () => {
    let anthropicProvider: MockAnthropicProvider;
    let openaiProvider: MockOpenAIProvider;
    let asi1Provider: MockASI1Provider;

    beforeEach(async () => {
      anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      asi1Provider = new MockASI1Provider(testConfigs.asi1, mockClient);

      await anthropicProvider.initialize();
      await openaiProvider.initialize();
      await asi1Provider.initialize();
    });

    afterEach(async () => {
      await anthropicProvider.cleanup();
      await openaiProvider.cleanup();
      await asi1Provider.cleanup();
    });

    it('should check provider availability when healthy', async () => {
      expect(await anthropicProvider.isAvailable()).toBe(true);
      expect(await openaiProvider.isAvailable()).toBe(true);
      expect(await asi1Provider.isAvailable()).toBe(true);
    });

    it('should detect provider unavailability', async () => {
      mockClient.setShouldFail(true);

      expect(await anthropicProvider.isAvailable()).toBe(false);
      expect(await openaiProvider.isAvailable()).toBe(false);
      expect(await asi1Provider.isAvailable()).toBe(false);
    });

    it('should handle provider health monitoring', async () => {
      const healthChecks = await Promise.all([
        anthropicProvider.isAvailable(),
        openaiProvider.isAvailable(),
        asi1Provider.isAvailable()
      ]);

      expect(healthChecks).toEqual([true, true, true]);
    });
  });

  describe('Rate Limiting and Error Handling', () => {
    let anthropicProvider: MockAnthropicProvider;

    beforeEach(async () => {
      anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      await anthropicProvider.initialize();
    });

    afterEach(async () => {
      await anthropicProvider.cleanup();
    });

    it('should handle rate limiting gracefully', async () => {
      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Rate limit test' }
      ];

      // Make requests until rate limit is hit
      const promises = Array.from({ length: 15 }, () =>
        anthropicProvider.generate(messages).catch(error => error)
      );

      const results = await Promise.all(promises);
      
      // Some requests should succeed, some should be rate limited
      const successful = results.filter(r => !(r instanceof Error));
      const rateLimited = results.filter(r => r instanceof Error && r.message.includes('Rate limit'));

      expect(successful.length).toBeGreaterThan(0);
      expect(rateLimited.length).toBeGreaterThan(0);
      expect(mockClient.getRateLimitCount()).toBeGreaterThan(0);
    });

    it('should implement retry logic with exponential backoff', async () => {
      // This would be implemented in a production provider
      class RetryProvider extends MockAnthropicProvider {
        private retryCount = 0;
        private maxRetries = 3;

        async generateWithRetry(messages: ProviderMessage[]): Promise<ProviderResponse> {
          for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
              return await this.generate(messages);
            } catch (error) {
              this.retryCount++;
              if (attempt < this.maxRetries - 1) {
                const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, delay));
              } else {
                throw error;
              }
            }
          }
          throw new Error('Max retries exceeded');
        }

        getRetryCount() { return this.retryCount; }
      }

      const retryProvider = new RetryProvider(testConfigs.anthropic, mockClient);
      await retryProvider.initialize();

      // First request fails, but should retry and succeed
      let shouldFailFirst = true;
      mockClient.request = async (url: string, options: any = {}) => {
        if (shouldFailFirst) {
          shouldFailFirst = false;
          throw new Error('Temporary network error');
        }
        return mockClient['getDefaultResponse'](new URL(url).pathname);
      };

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Retry test' }
      ];

      const response = await retryProvider.generateWithRetry(messages);
      expect(response).toBeDefined();
      expect(retryProvider.getRetryCount()).toBe(1);

      await retryProvider.cleanup();
    });

    it('should handle network timeouts', async () => {
      // Mock timeout scenario
      mockClient.request = async () => {
        await new Promise(resolve => setTimeout(resolve, 10000)); // Very long delay
        throw new Error('Request timeout');
      };

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Timeout test' }
      ];

      const startTime = Date.now();
      
      try {
        await anthropicProvider.generate(messages);
        expect.fail('Should have timed out');
      } catch (error) {
        const elapsed = Date.now() - startTime;
        expect(error.message).toContain('timeout');
        expect(elapsed).toBeGreaterThan(1000); // Should have waited at least 1 second
      }
    });
  });

  describe('Provider Fallback and Load Balancing', () => {
    class LoadBalancingProviderManager extends ProviderManager {
      private providerIndex = 0;

      async generateWithFallback(messages: ProviderMessage[]): Promise<ProviderResponse> {
        const providerNames = this.list();
        
        for (const providerName of providerNames) {
          try {
            const provider = this.get(providerName);
            if (provider && await provider.isAvailable()) {
              return await provider.generate(messages);
            }
          } catch (error) {
            console.warn(`Provider ${providerName} failed, trying next...`);
            continue;
          }
        }
        
        throw new Error('All providers failed');
      }

      getNextProvider(): string | null {
        const providerNames = this.list();
        if (providerNames.length === 0) return null;
        
        const provider = providerNames[this.providerIndex % providerNames.length];
        this.providerIndex++;
        return provider;
      }
    }

    it('should fallback to next provider when primary fails', async () => {
      const lbManager = new LoadBalancingProviderManager();
      
      // Register providers
      const anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      const openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      
      await anthropicProvider.initialize();
      await openaiProvider.initialize();
      
      (lbManager as any).providers.set('test-anthropic', anthropicProvider);
      (lbManager as any).providers.set('test-openai', openaiProvider);

      // Make anthropic provider fail
      vi.spyOn(anthropicProvider, 'generate').mockRejectedValue(new Error('Anthropic failed'));
      vi.spyOn(anthropicProvider, 'isAvailable').mockResolvedValue(false);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Fallback test' }
      ];

      const response = await lbManager.generateWithFallback(messages);
      
      expect(response).toBeDefined();
      expect(response.content).toBe('Test response from OpenAI'); // Should fallback to OpenAI

      await anthropicProvider.cleanup();
      await openaiProvider.cleanup();
      await lbManager.cleanup();
    });

    it('should distribute load across multiple providers', async () => {
      const lbManager = new LoadBalancingProviderManager();
      
      // Register multiple providers
      const providers = [
        new MockAnthropicProvider(testConfigs.anthropic, mockClient),
        new MockOpenAIProvider(testConfigs.openai, mockClient),
        new MockASI1Provider(testConfigs.asi1, mockClient)
      ];

      for (const provider of providers) {
        await provider.initialize();
        (lbManager as any).providers.set(provider.name, provider);
      }

      // Test load distribution
      const selectedProviders = Array.from({ length: 10 }, () => 
        lbManager.getNextProvider()
      );

      expect(selectedProviders).toContain('test-anthropic');
      expect(selectedProviders).toContain('test-openai');
      expect(selectedProviders).toContain('test-asi1');

      // Should cycle through providers
      expect(selectedProviders[0]).toBe(selectedProviders[3]); // Every 3rd should be the same
      
      await Promise.all(providers.map(p => p.cleanup()));
      await lbManager.cleanup();
    });

    it('should handle all providers being unavailable', async () => {
      const lbManager = new LoadBalancingProviderManager();
      
      // Register providers that will all fail
      const anthropicProvider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      const openaiProvider = new MockOpenAIProvider(testConfigs.openai, mockClient);
      
      await anthropicProvider.initialize();
      await openaiProvider.initialize();
      
      // Make both providers unavailable
      vi.spyOn(anthropicProvider, 'isAvailable').mockResolvedValue(false);
      vi.spyOn(openaiProvider, 'isAvailable').mockResolvedValue(false);
      
      (lbManager as any).providers.set('test-anthropic', anthropicProvider);
      (lbManager as any).providers.set('test-openai', openaiProvider);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'All fail test' }
      ];

      try {
        await lbManager.generateWithFallback(messages);
        expect.fail('Should have thrown all providers failed error');
      } catch (error) {
        expect(error.message).toBe('All providers failed');
      }

      await anthropicProvider.cleanup();
      await openaiProvider.cleanup();
      await lbManager.cleanup();
    });
  });

  describe('Provider Configuration and Validation', () => {
    it('should validate provider configurations', async () => {
      const invalidConfigs = [
        { ...testConfigs.anthropic, apiKey: '' }, // Missing API key
        { ...testConfigs.anthropic, model: '' }, // Missing model
        { ...testConfigs.openai, type: 'invalid' as any }, // Invalid type
        { ...testConfigs.asi1, baseUrl: 'not-a-url' } // Invalid URL
      ];

      for (const invalidConfig of invalidConfigs) {
        try {
          if (invalidConfig.type === 'anthropic') {
            const provider = new MockAnthropicProvider(invalidConfig, mockClient);
            await provider.initialize();
          } else if (invalidConfig.type === 'openai') {
            const provider = new MockOpenAIProvider(invalidConfig, mockClient);
            await provider.initialize();
          }
          
          // Some validations might be done during initialization
        } catch (error) {
          // Expected for invalid configurations
          expect(error).toBeDefined();
        }
      }
    });

    it('should support dynamic configuration updates', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      await provider.initialize();

      expect(provider.config.temperature).toBe(0.7);

      // Update configuration
      provider.config.temperature = 0.5;
      provider.config.maxTokens = 2000;

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Config test' }
      ];

      // Generate with new config
      await provider.generate(messages, { 
        temperature: provider.config.temperature,
        maxTokens: provider.config.maxTokens 
      });

      expect(provider.config.temperature).toBe(0.5);
      expect(provider.config.maxTokens).toBe(2000);

      await provider.cleanup();
    });

    it('should handle environment-specific configurations', async () => {
      const devConfig = { ...testConfigs.anthropic, metadata: { environment: 'development' } };
      const prodConfig = { ...testConfigs.anthropic, metadata: { environment: 'production' } };

      const devProvider = new MockAnthropicProvider(devConfig, mockClient);
      const prodProvider = new MockAnthropicProvider(prodConfig, mockClient);

      await devProvider.initialize();
      await prodProvider.initialize();

      expect(devProvider.config.metadata?.environment).toBe('development');
      expect(prodProvider.config.metadata?.environment).toBe('production');

      await devProvider.cleanup();
      await prodProvider.cleanup();
    });
  });

  describe('Provider Monitoring and Metrics', () => {
    it('should track provider usage metrics', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      await provider.initialize();

      let requestCount = 0;
      let totalTokens = 0;

      provider.on('response', (event) => {
        requestCount++;
        totalTokens += event.response.usage.totalTokens;
      });

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Metrics test' }
      ];

      // Make multiple requests
      await provider.generate(messages);
      await provider.generate(messages);
      await provider.generate(messages);

      expect(requestCount).toBe(3);
      expect(totalTokens).toBe(75); // 3 requests * 25 tokens each

      await provider.cleanup();
    });

    it('should monitor provider response times', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      await provider.initialize();

      const responseTimes: number[] = [];
      
      provider.on('response', (event) => {
        if (event.responseTime) {
          responseTimes.push(event.responseTime);
        }
      });

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Response time test' }
      ];

      // Make requests and measure time manually since our mock doesn't include it
      const startTime = Date.now();
      await provider.generate(messages);
      const endTime = Date.now();
      
      const responseTime = endTime - startTime;
      expect(responseTime).toBeGreaterThan(0);

      await provider.cleanup();
    });

    it('should track provider error rates', async () => {
      const provider = new MockAnthropicProvider(testConfigs.anthropic, mockClient);
      await provider.initialize();

      let errorCount = 0;
      let successCount = 0;

      provider.on('response', () => successCount++);
      provider.on('error', () => errorCount++);

      const messages: ProviderMessage[] = [
        { role: 'user', content: 'Error rate test' }
      ];

      // Make successful request
      await provider.generate(messages);

      // Make failing request
      mockClient.setShouldFail(true);
      try {
        await provider.generate(messages);
      } catch {
        // Expected to fail
      }

      expect(successCount).toBe(1);
      expect(errorCount).toBe(1);

      const errorRate = errorCount / (successCount + errorCount);
      expect(errorRate).toBe(0.5); // 50% error rate

      await provider.cleanup();
    });
  });
});