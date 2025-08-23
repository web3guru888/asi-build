/**
 * API Testing Framework
 * Comprehensive API testing utilities with Supertest integration
 */

import request from 'supertest';
import { vi } from 'vitest';
import type { Express } from 'express';
import { DatabaseTestHelpers } from '../database/index.js';
import { KennyFixtures, ProviderFixtures } from '../fixtures/index.js';

// =============================================================================
// API TEST CLIENT
// =============================================================================

export class ApiTestClient {
  private app: Express;
  private baseURL: string;
  private defaultHeaders: Record<string, string> = {};
  private authToken?: string;

  constructor(app: Express, baseURL = '') {
    this.app = app;
    this.baseURL = baseURL;
  }

  /**
   * Set default headers for all requests
   */
  setDefaultHeaders(headers: Record<string, string>) {
    this.defaultHeaders = { ...this.defaultHeaders, ...headers };
    return this;
  }

  /**
   * Set authentication token
   */
  setAuth(token: string) {
    this.authToken = token;
    this.setDefaultHeaders({ Authorization: `Bearer ${token}` });
    return this;
  }

  /**
   * Clear authentication
   */
  clearAuth() {
    this.authToken = undefined;
    delete this.defaultHeaders.Authorization;
    return this;
  }

  /**
   * Create a request with default headers
   */
  private createRequest(method: string, path: string) {
    const fullPath = this.baseURL + path;
    let req = request(this.app)[method.toLowerCase() as keyof typeof request](fullPath);
    
    // Apply default headers
    Object.entries(this.defaultHeaders).forEach(([key, value]) => {
      req = req.set(key, value);
    });

    return req;
  }

  // HTTP Methods

  get(path: string) {
    return this.createRequest('GET', path);
  }

  post(path: string, data?: any) {
    const req = this.createRequest('POST', path);
    return data ? req.send(data) : req;
  }

  put(path: string, data?: any) {
    const req = this.createRequest('PUT', path);
    return data ? req.send(data) : req;
  }

  patch(path: string, data?: any) {
    const req = this.createRequest('PATCH', path);
    return data ? req.send(data) : req;
  }

  delete(path: string) {
    return this.createRequest('DELETE', path);
  }

  // Convenience methods for common API patterns

  /**
   * Test health endpoint
   */
  async checkHealth() {
    return await this.get('/health').expect(200);
  }

  /**
   * Test authentication endpoint
   */
  async authenticate(credentials: { username: string; password: string }) {
    return await this.post('/auth/login', credentials);
  }

  /**
   * Test session creation
   */
  async createSession(userId: string) {
    return await this.post('/sessions', { userId });
  }

  /**
   * Test message sending
   */
  async sendMessage(sessionId: string, content: string) {
    return await this.post(`/sessions/${sessionId}/messages`, {
      type: 'user',
      content
    });
  }

  /**
   * Test tool execution
   */
  async executeTool(toolName: string, parameters: any, sessionId?: string) {
    return await this.post('/tools/execute', {
      tool: toolName,
      parameters,
      sessionId
    });
  }

  /**
   * Test provider interaction
   */
  async queryProvider(provider: string, messages: any[]) {
    return await this.post('/providers/query', {
      provider,
      messages
    });
  }
}

// =============================================================================
// API TEST SUITE BUILDER
// =============================================================================

export class ApiTestSuite {
  private client: ApiTestClient;
  private setup: (() => Promise<void>) | null = null;
  private cleanup: (() => Promise<void>) | null = null;
  private beforeEachHook: (() => Promise<void>) | null = null;
  private afterEachHook: (() => Promise<void>) | null = null;

  constructor(app: Express, baseURL = '') {
    this.client = new ApiTestClient(app, baseURL);
  }

  /**
   * Set setup hook
   */
  onSetup(hook: () => Promise<void>) {
    this.setup = hook;
    return this;
  }

  /**
   * Set cleanup hook
   */
  onCleanup(hook: () => Promise<void>) {
    this.cleanup = hook;
    return this;
  }

  /**
   * Set before each test hook
   */
  beforeEach(hook: () => Promise<void>) {
    this.beforeEachHook = hook;
    return this;
  }

  /**
   * Set after each test hook
   */
  afterEach(hook: () => Promise<void>) {
    this.afterEachHook = hook;
    return this;
  }

  /**
   * Run setup
   */
  async runSetup() {
    if (this.setup) {
      await this.setup();
    }
  }

  /**
   * Run cleanup
   */
  async runCleanup() {
    if (this.cleanup) {
      await this.cleanup();
    }
  }

  /**
   * Run before each hook
   */
  async runBeforeEach() {
    if (this.beforeEachHook) {
      await this.beforeEachHook();
    }
  }

  /**
   * Run after each hook
   */
  async runAfterEach() {
    if (this.afterEachHook) {
      await this.afterEachHook();
    }
  }

  /**
   * Get the API client
   */
  getClient() {
    return this.client;
  }

  // Test builders for common scenarios

  /**
   * Build CRUD tests for a resource
   */
  buildCrudTests(resource: string, sampleData: any, updateData: any) {
    const resourcePath = `/${resource}`;
    let createdId: string;

    return {
      testCreate: async () => {
        const response = await this.client.post(resourcePath, sampleData)
          .expect(201);
        
        expect(response.body).toHaveProperty('id');
        createdId = response.body.id;
        return response;
      },

      testRead: async () => {
        const response = await this.client.get(`${resourcePath}/${createdId}`)
          .expect(200);
        
        expect(response.body.id).toBe(createdId);
        return response;
      },

      testUpdate: async () => {
        const response = await this.client.put(`${resourcePath}/${createdId}`, updateData)
          .expect(200);
        
        expect(response.body.id).toBe(createdId);
        return response;
      },

      testDelete: async () => {
        return await this.client.delete(`${resourcePath}/${createdId}`)
          .expect(204);
      },

      testList: async () => {
        return await this.client.get(resourcePath)
          .expect(200);
      },

      getCreatedId: () => createdId
    };
  }

  /**
   * Build authentication tests
   */
  buildAuthTests(validCredentials: any, invalidCredentials: any) {
    return {
      testValidLogin: async () => {
        const response = await this.client.post('/auth/login', validCredentials)
          .expect(200);
        
        expect(response.body).toHaveProperty('token');
        expect(response.body).toHaveProperty('user');
        return response;
      },

      testInvalidLogin: async () => {
        return await this.client.post('/auth/login', invalidCredentials)
          .expect(401);
      },

      testProtectedRoute: async (token: string, path: string) => {
        // Test without token
        await this.client.get(path).expect(401);
        
        // Test with token
        this.client.setAuth(token);
        return await this.client.get(path).expect(200);
      },

      testLogout: async () => {
        return await this.client.post('/auth/logout').expect(200);
      }
    };
  }

  /**
   * Build error handling tests
   */
  buildErrorTests() {
    return {
      testNotFound: async (path: string) => {
        const response = await this.client.get(path).expect(404);
        expect(response.body).toHaveProperty('error');
        return response;
      },

      testValidationError: async (path: string, invalidData: any) => {
        const response = await this.client.post(path, invalidData).expect(400);
        expect(response.body).toHaveProperty('error');
        expect(response.body).toHaveProperty('details');
        return response;
      },

      testUnauthorized: async (path: string) => {
        this.client.clearAuth();
        const response = await this.client.get(path).expect(401);
        expect(response.body).toHaveProperty('error');
        return response;
      },

      testForbidden: async (path: string, insufficientToken: string) => {
        this.client.setAuth(insufficientToken);
        const response = await this.client.get(path).expect(403);
        expect(response.body).toHaveProperty('error');
        return response;
      }
    };
  }
}

// =============================================================================
// API RESPONSE VALIDATORS
// =============================================================================

export class ApiResponseValidator {
  static validateSuccess(response: any, expectedStatus = 200) {
    expect(response.status).toBe(expectedStatus);
    expect(response.body).toBeDefined();
    return response.body;
  }

  static validateError(response: any, expectedStatus: number, expectedErrorCode?: string) {
    expect(response.status).toBe(expectedStatus);
    expect(response.body).toHaveProperty('error');
    
    if (expectedErrorCode) {
      expect(response.body.error).toHaveProperty('code', expectedErrorCode);
    }
    
    return response.body.error;
  }

  static validatePagination(response: any) {
    const body = this.validateSuccess(response);
    expect(body).toHaveProperty('data');
    expect(body).toHaveProperty('pagination');
    expect(body.pagination).toHaveProperty('page');
    expect(body.pagination).toHaveProperty('limit');
    expect(body.pagination).toHaveProperty('total');
    
    return body;
  }

  static validateCreated(response: any, expectedProperties: string[] = ['id']) {
    const body = this.validateSuccess(response, 201);
    
    expectedProperties.forEach(prop => {
      expect(body).toHaveProperty(prop);
    });
    
    return body;
  }

  static validateDeleted(response: any) {
    expect(response.status).toBe(204);
    return true;
  }

  static validateKennyResponse(response: any) {
    const body = this.validateSuccess(response);
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('type');
    expect(body).toHaveProperty('content');
    expect(body).toHaveProperty('timestamp');
    
    return body;
  }

  static validateToolResult(response: any) {
    const body = this.validateSuccess(response);
    expect(body).toHaveProperty('success');
    expect(body).toHaveProperty('data');
    expect(body).toHaveProperty('metadata');
    
    return body;
  }

  static validateProviderResponse(response: any) {
    const body = this.validateSuccess(response);
    expect(body).toHaveProperty('content');
    expect(body).toHaveProperty('model');
    expect(body).toHaveProperty('usage');
    
    return body;
  }
}

// =============================================================================
// API MOCK SERVER
// =============================================================================

export class ApiMockServer {
  private routes = new Map<string, any>();
  private middleware: any[] = [];
  
  constructor() {
    this.setupDefaultRoutes();
  }

  private setupDefaultRoutes() {
    // Health check
    this.addRoute('GET', '/health', (req: any, res: any) => {
      res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });

    // Status endpoint
    this.addRoute('GET', '/api/status', (req: any, res: any) => {
      res.json({ status: 'running', version: '1.0.0-test' });
    });
  }

  addRoute(method: string, path: string, handler: any) {
    const key = `${method.toUpperCase()} ${path}`;
    this.routes.set(key, handler);
  }

  addMiddleware(middleware: any) {
    this.middleware.push(middleware);
  }

  createMockApp() {
    const express = require('express');
    const app = express();

    app.use(express.json());
    
    // Apply middleware
    this.middleware.forEach(mw => app.use(mw));

    // Add routes
    for (const [route, handler] of this.routes.entries()) {
      const [method, path] = route.split(' ');
      app[method.toLowerCase()](path, handler);
    }

    return app;
  }

  // Predefined mock handlers

  mockKennyEndpoints() {
    this.addRoute('POST', '/kenny/message', (req: any, res: any) => {
      const message = KennyFixtures.assistantMessage(
        `Response to: ${req.body.content}`,
        req.body.context
      );
      res.json(message);
    });

    this.addRoute('GET', '/kenny/context/:id', (req: any, res: any) => {
      const context = KennyFixtures.defaultContext();
      context.id = req.params.id;
      res.json(context);
    });
  }

  mockProviderEndpoints() {
    this.addRoute('POST', '/providers/query', (req: any, res: any) => {
      const { messages } = req.body;
      const lastMessage = messages[messages.length - 1];
      
      const response = ProviderFixtures.response(
        `Mock response to: ${lastMessage.content}`
      );
      res.json(response);
    });

    this.addRoute('GET', '/providers/:name/status', (req: any, res: any) => {
      res.json({
        name: req.params.name,
        status: 'available',
        model: 'mock-model'
      });
    });
  }

  mockToolEndpoints() {
    this.addRoute('POST', '/tools/execute', (req: any, res: any) => {
      const { tool, parameters } = req.body;
      
      res.json({
        success: true,
        data: {
          tool,
          parameters,
          result: `Mock execution of ${tool} with parameters: ${JSON.stringify(parameters)}`
        },
        metadata: {
          executedAt: new Date().toISOString(),
          duration: Math.floor(Math.random() * 1000)
        }
      });
    });

    this.addRoute('GET', '/tools', (req: any, res: any) => {
      res.json({
        data: [
          { name: 'read', category: 'file-system' },
          { name: 'write', category: 'file-system' },
          { name: 'bash', category: 'system' }
        ]
      });
    });
  }

  mockSessionEndpoints() {
    this.addRoute('POST', '/sessions', (req: any, res: any) => {
      const session = {
        id: `session_${Date.now()}`,
        userId: req.body.userId,
        createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 3600000).toISOString()
      };
      res.status(201).json(session);
    });

    this.addRoute('GET', '/sessions/:id', (req: any, res: any) => {
      res.json({
        id: req.params.id,
        userId: 'test-user',
        data: { preferences: { theme: 'dark' } },
        createdAt: new Date().toISOString()
      });
    });
  }

  mockErrorEndpoints() {
    this.addRoute('GET', '/error/400', (req: any, res: any) => {
      res.status(400).json({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          details: { field: 'test' }
        }
      });
    });

    this.addRoute('GET', '/error/401', (req: any, res: any) => {
      res.status(401).json({
        error: {
          code: 'UNAUTHORIZED',
          message: 'Authentication required'
        }
      });
    });

    this.addRoute('GET', '/error/500', (req: any, res: any) => {
      res.status(500).json({
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Internal server error'
        }
      });
    });
  }
}

// =============================================================================
// API TEST HELPERS
// =============================================================================

export const ApiTestHelpers = {
  /**
   * Create an API test client
   */
  createClient: (app: Express, baseURL = '') => new ApiTestClient(app, baseURL),

  /**
   * Create an API test suite
   */
  createSuite: (app: Express, baseURL = '') => new ApiTestSuite(app, baseURL),

  /**
   * Create a mock server
   */
  createMockServer: () => new ApiMockServer(),

  /**
   * Validate response helper
   */
  validate: ApiResponseValidator,

  /**
   * Wait for server to be ready
   */
  async waitForServer(client: ApiTestClient, maxAttempts = 30, interval = 100) {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        await client.checkHealth();
        return true;
      } catch (error) {
        if (i === maxAttempts - 1) throw error;
        await new Promise(resolve => setTimeout(resolve, interval));
      }
    }
    return false;
  },

  /**
   * Generate test data for common scenarios
   */
  generateTestData: {
    user: () => ({
      username: `testuser_${Date.now()}`,
      email: `test_${Date.now()}@example.com`,
      password: 'TestPassword123!'
    }),

    session: () => ({
      userId: `user_${Date.now()}`,
      metadata: { test: true }
    }),

    message: () => ({
      type: 'user',
      content: `Test message ${Date.now()}`
    }),

    invalidData: {
      missingRequired: {},
      invalidFormat: { email: 'not-an-email' },
      tooLong: { name: 'a'.repeat(1000) }
    }
  }
};

export default {
  ApiTestClient,
  ApiTestSuite,
  ApiResponseValidator,
  ApiMockServer,
  ApiTestHelpers
};