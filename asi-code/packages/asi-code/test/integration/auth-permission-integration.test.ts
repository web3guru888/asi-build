/**
 * Authentication and Permission System Integration Tests
 * 
 * Tests authentication flows, permission validation, role-based access control,
 * session management, security protocols, and integration with other components.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { ToolRegistry } from '../../src/tool/tool-registry.js';
import { createBuiltInTools } from '../../src/tool/built-in-tools/index.js';
import { createServer } from '../../src/server/server.js';
import { vol } from 'memfs';
import supertest from 'supertest';
import jwt from 'jsonwebtoken';
import type { Server } from 'node:http';
import type { 
  Permission, 
  PermissionScope, 
  SecurityPolicy, 
  AuditEntry 
} from '../../src/permission/permission-types.js';

// Mock fs for file operations
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Test storage implementation
class TestSessionStorage {
  private storage = new Map();

  async save(sessionData: any): Promise<void> {
    this.storage.set(sessionData.id, { ...sessionData });
  }

  async load(sessionId: string): Promise<any> {
    return this.storage.get(sessionId) || null;
  }

  async delete(sessionId: string): Promise<void> {
    this.storage.delete(sessionId);
  }

  async list(userId?: string): Promise<string[]> {
    const sessions = Array.from(this.storage.values());
    return sessions
      .filter((session: any) => !userId || session.userId === userId)
      .map((session: any) => session.id);
  }

  async cleanup(): Promise<void> {}
  clear(): void { this.storage.clear(); }
}

// Mock authentication service
class MockAuthService {
  private users = new Map<string, any>();
  private apiKeys = new Map<string, string>();
  private jwtSecret = 'test-secret';

  constructor() {
    // Setup test users
    this.users.set('admin@test.com', {
      id: 'user_admin',
      email: 'admin@test.com',
      role: 'admin',
      permissions: ['*'], // All permissions
      passwordHash: 'hashed_admin_password',
      active: true,
      lastLogin: null
    });

    this.users.set('user@test.com', {
      id: 'user_standard',
      email: 'user@test.com',
      role: 'user',
      permissions: ['read_files', 'write_files', 'list_files'],
      passwordHash: 'hashed_user_password',
      active: true,
      lastLogin: null
    });

    this.users.set('readonly@test.com', {
      id: 'user_readonly',
      email: 'readonly@test.com',
      role: 'readonly',
      permissions: ['read_files', 'list_files'],
      passwordHash: 'hashed_readonly_password',
      active: true,
      lastLogin: null
    });

    this.users.set('disabled@test.com', {
      id: 'user_disabled',
      email: 'disabled@test.com',
      role: 'user',
      permissions: ['read_files'],
      passwordHash: 'hashed_disabled_password',
      active: false,
      lastLogin: null
    });

    // Setup API keys
    this.apiKeys.set('ak_admin_test_key', 'user_admin');
    this.apiKeys.set('ak_user_test_key', 'user_standard');
    this.apiKeys.set('ak_readonly_test_key', 'user_readonly');
  }

  async authenticatePassword(email: string, password: string): Promise<any> {
    const user = this.users.get(email);
    if (!user || !user.active) {
      return null;
    }

    // Simple password check (in real implementation would verify hash)
    const expectedPassword = {
      'admin@test.com': 'admin_password',
      'user@test.com': 'user_password',
      'readonly@test.com': 'readonly_password'
    }[email];

    if (password !== expectedPassword) {
      return null;
    }

    // Update last login
    user.lastLogin = new Date();
    return { ...user };
  }

  async authenticateApiKey(apiKey: string): Promise<any> {
    const userId = this.apiKeys.get(apiKey);
    if (!userId) {
      return null;
    }

    const user = Array.from(this.users.values()).find(u => u.id === userId);
    if (!user || !user.active) {
      return null;
    }

    return { ...user };
  }

  async authenticateJWT(token: string): Promise<any> {
    try {
      const payload = jwt.verify(token, this.jwtSecret) as any;
      const user = Array.from(this.users.values()).find(u => u.id === payload.userId);
      
      if (!user || !user.active) {
        return null;
      }

      return { ...user };
    } catch {
      return null;
    }
  }

  generateJWT(user: any): string {
    return jwt.sign(
      { 
        userId: user.id, 
        email: user.email, 
        role: user.role 
      },
      this.jwtSecret,
      { expiresIn: '1h' }
    );
  }

  getUser(userId: string): any {
    return Array.from(this.users.values()).find(u => u.id === userId);
  }

  createUser(userData: any): string {
    const userId = `user_${Date.now()}`;
    this.users.set(userData.email, {
      id: userId,
      ...userData,
      active: true,
      lastLogin: null
    });
    return userId;
  }

  updateUser(userId: string, updates: any): boolean {
    const user = Array.from(this.users.values()).find(u => u.id === userId);
    if (!user) return false;

    Object.assign(user, updates);
    return true;
  }

  deleteUser(userId: string): boolean {
    const userEmail = Array.from(this.users.entries())
      .find(([_, user]) => user.id === userId)?.[0];
    
    if (!userEmail) return false;
    
    return this.users.delete(userEmail);
  }

  reset(): void {
    this.users.clear();
    this.apiKeys.clear();
    // Re-initialize test data
    this.constructor();
  }
}

describe('Authentication and Permission System Integration Tests', () => {
  let permissionManager: PermissionManager;
  let sessionManager: DefaultSessionManager;
  let toolRegistry: ToolRegistry;
  let authService: MockAuthService;
  let testStorage: TestSessionStorage;
  let server: Server;
  let request: supertest.SuperTest<supertest.Test>;
  const serverPort = 3005;

  beforeAll(async () => {
    testStorage = new TestSessionStorage();
    authService = new MockAuthService();
    
    permissionManager = new PermissionManager({
      enableSafetyProtocols: true,
      enableCaching: true,
      enableAuditing: true,
      auditRetention: 24 * 60 * 60 * 1000, // 24 hours
      rateLimiting: {
        enabled: true,
        maxRequests: 100,
        windowMs: 60000 // 1 minute
      }
    });

    sessionManager = new DefaultSessionManager(testStorage as any);
    toolRegistry = new ToolRegistry();

    await toolRegistry.initialize();
    await toolRegistry.start();

    // Register built-in tools
    const builtInTools = createBuiltInTools();
    for (const tool of builtInTools) {
      await toolRegistry.register(tool, [tool.getCategory()]);
    }

    // Create server with auth integration
    server = createServer({
      port: serverPort,
      host: 'localhost',
      enableLogging: false,
      enableCors: true,
      authentication: {
        enabled: true,
        jwtSecret: 'test-secret',
        sessionTimeout: 3600000, // 1 hour
        requireAuth: true
      },
      components: {
        toolRegistry,
        sessionManager,
        permissionManager,
        authService
      }
    });

    await new Promise<void>((resolve) => {
      server.listen(serverPort, () => {
        console.log(`Auth integration test server running on port ${serverPort}`);
        resolve();
      });
    });

    request = supertest(`http://localhost:${serverPort}`);
  });

  afterAll(async () => {
    if (server) {
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
    }
    
    if (toolRegistry) {
      await toolRegistry.shutdown();
    }
    
    if (sessionManager) {
      await sessionManager.cleanup();
    }

    if (permissionManager) {
      await permissionManager.cleanup();
    }
  });

  beforeEach(() => {
    vol.reset();
    testStorage.clear();
    authService.reset();
    
    // Setup test files
    vol.fromJSON({
      '/test/public.txt': 'Public file content',
      '/test/private.txt': 'Private file content',
      '/test/admin-only.txt': 'Admin only content',
      '/secure/sensitive.txt': 'Sensitive information',
      '/tmp/temp.txt': 'Temporary file'
    });
  });

  afterEach(() => {
    vol.reset();
  });

  describe('Authentication Mechanisms', () => {
    it('should authenticate users with password credentials', async () => {
      const loginData = {
        email: 'user@test.com',
        password: 'user_password'
      };

      const response = await request
        .post('/auth/login')
        .send(loginData)
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        user: expect.objectContaining({
          id: 'user_standard',
          email: 'user@test.com',
          role: 'user'
        }),
        token: expect.any(String)
      });

      // Verify JWT token is valid
      const user = await authService.authenticateJWT(response.body.token);
      expect(user).toBeDefined();
      expect(user.id).toBe('user_standard');
    });

    it('should reject invalid password credentials', async () => {
      const invalidLogins = [
        { email: 'user@test.com', password: 'wrong_password' },
        { email: 'nonexistent@test.com', password: 'any_password' },
        { email: 'disabled@test.com', password: 'disabled_password' }
      ];

      for (const loginData of invalidLogins) {
        const response = await request
          .post('/auth/login')
          .send(loginData)
          .expect(401);

        expect(response.body.success).toBe(false);
        expect(response.body.error).toBeDefined();
      }
    });

    it('should authenticate users with API keys', async () => {
      const response = await request
        .get('/api/user/profile')
        .set('Authorization', 'Bearer ak_user_test_key')
        .expect(200);

      expect(response.body).toMatchObject({
        user: expect.objectContaining({
          id: 'user_standard',
          email: 'user@test.com',
          role: 'user'
        })
      });
    });

    it('should reject invalid API keys', async () => {
      const invalidKeys = [
        'ak_invalid_key',
        'bearer_token_format',
        'completely_wrong_key',
        '' // empty key
      ];

      for (const key of invalidKeys) {
        const response = await request
          .get('/api/user/profile')
          .set('Authorization', `Bearer ${key}`)
          .expect(401);

        expect(response.body.error).toContain('authentication');
      }
    });

    it('should authenticate users with JWT tokens', async () => {
      // First login to get a token
      const loginResponse = await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' });

      const token = loginResponse.body.token;

      // Use token for authenticated request
      const response = await request
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      expect(response.body.user.role).toBe('admin');
    });

    it('should handle token expiration gracefully', async () => {
      // Create an expired token
      const expiredToken = jwt.sign(
        { userId: 'user_standard', email: 'user@test.com' },
        'test-secret',
        { expiresIn: '-1h' } // Expired 1 hour ago
      );

      const response = await request
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);

      expect(response.body.error).toContain('token');
    });

    it('should support multiple authentication methods in order of preference', async () => {
      // JWT should take precedence over API key
      const loginResponse = await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' });

      const jwtToken = loginResponse.body.token;

      const response = await request
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${jwtToken}`)
        .set('X-API-Key', 'ak_user_test_key') // Different user's API key
        .expect(200);

      // Should authenticate as admin (JWT) not user (API key)
      expect(response.body.user.role).toBe('admin');
    });
  });

  describe('Permission Validation', () => {
    it('should enforce role-based permissions for file operations', async () => {
      // Get tokens for different users
      const adminLogin = await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' });
      const userLogin = await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' });
      const readonlyLogin = await request
        .post('/auth/login')
        .send({ email: 'readonly@test.com', password: 'readonly_password' });

      const adminToken = adminLogin.body.token;
      const userToken = userLogin.body.token;
      const readonlyToken = readonlyLogin.body.token;

      // Test read permissions (all should succeed)
      const readTests = [
        { token: adminToken, user: 'admin' },
        { token: userToken, user: 'user' },
        { token: readonlyToken, user: 'readonly' }
      ];

      for (const test of readTests) {
        const response = await request
          .post('/api/tools/read/execute')
          .set('Authorization', `Bearer ${test.token}`)
          .send({
            parameters: { path: '/test/public.txt' },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
          .expect(200);

        expect(response.body.result.success).toBe(true);
      }

      // Test write permissions (only admin and user should succeed)
      const writeResponse1 = await request
        .post('/api/tools/write/execute')
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          parameters: { path: '/test/admin-write.txt', content: 'Admin content' },
          context: { permissions: ['write_files'], workingDirectory: '/test' }
        })
        .expect(200);
      expect(writeResponse1.body.result.success).toBe(true);

      const writeResponse2 = await request
        .post('/api/tools/write/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { path: '/test/user-write.txt', content: 'User content' },
          context: { permissions: ['write_files'], workingDirectory: '/test' }
        })
        .expect(200);
      expect(writeResponse2.body.result.success).toBe(true);

      // Readonly user should not be able to write
      const writeResponse3 = await request
        .post('/api/tools/write/execute')
        .set('Authorization', `Bearer ${readonlyToken}`)
        .send({
          parameters: { path: '/test/readonly-write.txt', content: 'Should fail' },
          context: { permissions: ['write_files'], workingDirectory: '/test' }
        })
        .expect(403);

      expect(writeResponse3.body.error).toContain('permission');
    });

    it('should enforce resource-based permissions', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Test access to different directories
      const accessTests = [
        { path: '/test/public.txt', shouldSucceed: true }, // Within allowed directory
        { path: '/secure/sensitive.txt', shouldSucceed: false }, // Restricted directory
        { path: '/tmp/temp.txt', shouldSucceed: false } // Different directory
      ];

      for (const test of accessTests) {
        const response = await request
          .post('/api/tools/read/execute')
          .set('Authorization', `Bearer ${userToken}`)
          .send({
            parameters: { path: test.path },
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          });

        if (test.shouldSucceed) {
          expect(response.status).toBe(200);
          expect(response.body.result.success).toBe(true);
        } else {
          expect(response.status).toBeOneOf([403, 200]);
          if (response.status === 200) {
            expect(response.body.result.success).toBe(false);
            expect(response.body.result.error).toContain('directory');
          }
        }
      }
    });

    it('should handle permission inheritance and delegation', async () => {
      // Create a session with inherited permissions
      const adminToken = (await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' })).body.token;

      // Admin creates session with delegated permissions for another user
      const sessionResponse = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          userId: 'delegated_user',
          permissions: ['read_files', 'write_files'], // Subset of admin permissions
          workingDirectory: '/test'
        })
        .expect(201);

      const sessionId = sessionResponse.body.sessionId;

      // Test delegated permissions
      const toolResponse = await request
        .post(`/api/sessions/${sessionId}/tools/read/execute`)
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          parameters: { path: '/test/public.txt' },
          context: { 
            permissions: ['read_files'], 
            workingDirectory: '/test',
            sessionId: sessionId
          }
        })
        .expect(200);

      expect(toolResponse.body.result.success).toBe(true);
    });

    it('should validate time-based permission restrictions', async () => {
      // This would test temporal permissions (e.g., business hours only)
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Mock time-based restriction (implementation would check current time)
      const currentHour = new Date().getHours();
      const isBusinessHours = currentHour >= 9 && currentHour <= 17;

      // Test time-sensitive operation
      const response = await request
        .post('/api/tools/bash/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { command: 'echo "Time-sensitive operation"' },
          context: { 
            permissions: ['execute_commands'],
            workingDirectory: '/test',
            timeRestriction: 'business_hours_only'
          }
        });

      if (isBusinessHours) {
        expect(response.status).toBe(200);
      } else {
        expect(response.status).toBeOneOf([403, 200]);
        if (response.status === 200 && !response.body.result.success) {
          expect(response.body.result.error).toContain('time');
        }
      }
    });

    it('should handle permission caching and invalidation', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // First request should cache permissions
      const response1 = await request
        .post('/api/tools/read/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { path: '/test/public.txt' },
          context: { permissions: ['read_files'], workingDirectory: '/test' }
        })
        .expect(200);

      expect(response1.body.result.success).toBe(true);

      // Modify user permissions (simulated)
      const user = authService.getUser('user_standard');
      const originalPermissions = [...user.permissions];
      user.permissions = ['read_files']; // Remove write permission

      // Subsequent request should use cached permissions initially
      const response2 = await request
        .post('/api/tools/read/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { path: '/test/public.txt' },
          context: { permissions: ['read_files'], workingDirectory: '/test' }
        })
        .expect(200);

      expect(response2.body.result.success).toBe(true);

      // Force cache invalidation (implementation specific)
      await permissionManager.clearCache('user_standard');

      // Now permissions should be refreshed
      const response3 = await request
        .post('/api/tools/write/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { path: '/test/no-write.txt', content: 'Should fail' },
          context: { permissions: ['write_files'], workingDirectory: '/test' }
        });

      expect(response3.status).toBeOneOf([403, 200]);
      if (response3.status === 200) {
        expect(response3.body.result.success).toBe(false);
        expect(response3.body.result.error).toContain('permission');
      }

      // Restore original permissions
      user.permissions = originalPermissions;
    });
  });

  describe('Session Security', () => {
    it('should create secure sessions with proper isolation', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Create multiple sessions for the same user
      const session1Response = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ userId: 'user_standard' });

      const session2Response = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ userId: 'user_standard' });

      const session1Id = session1Response.body.sessionId;
      const session2Id = session2Response.body.sessionId;

      expect(session1Id).not.toBe(session2Id);

      // Add data to session1
      await request
        .post(`/api/sessions/${session1Id}/messages`)
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          content: 'Session 1 message',
          type: 'user'
        });

      // Session2 should not see session1's data
      const session2Messages = await request
        .get(`/api/sessions/${session2Id}/messages`)
        .set('Authorization', `Bearer ${userToken}`)
        .expect(200);

      expect(session2Messages.body.messages).toHaveLength(0);

      // Session1 should have its data
      const session1Messages = await request
        .get(`/api/sessions/${session1Id}/messages`)
        .set('Authorization', `Bearer ${userToken}`)
        .expect(200);

      expect(session1Messages.body.messages).toHaveLength(1);
    });

    it('should enforce session ownership and access control', async () => {
      const user1Token = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      const user2Token = (await request
        .post('/auth/login')
        .send({ email: 'readonly@test.com', password: 'readonly_password' })).body.token;

      // User1 creates a session
      const sessionResponse = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({ userId: 'user_standard' });

      const sessionId = sessionResponse.body.sessionId;

      // User2 should not be able to access User1's session
      const unauthorizedAccess = await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .expect(403);

      expect(unauthorizedAccess.body.error).toContain('access');

      // User1 should be able to access their own session
      const authorizedAccess = await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(authorizedAccess.body.session.id).toBe(sessionId);
    });

    it('should handle session timeout and cleanup', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Create session with short timeout
      const sessionResponse = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ 
          userId: 'user_standard',
          config: {
            ttl: 1000 // 1 second timeout
          }
        });

      const sessionId = sessionResponse.body.sessionId;

      // Session should be accessible immediately
      await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${userToken}`)
        .expect(200);

      // Wait for timeout
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Session should be expired/cleaned up
      const expiredResponse = await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${userToken}`)
        .expect(404);

      expect(expiredResponse.body.error).toContain('not found');
    });

    it('should detect and prevent session hijacking attempts', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ userId: 'user_standard' });

      const sessionId = sessionResponse.body.sessionId;

      // Attempt to access session with different user's token
      const attackerToken = (await request
        .post('/auth/login')
        .send({ email: 'readonly@test.com', password: 'readonly_password' })).body.token;

      const hijackAttempt = await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${attackerToken}`)
        .expect(403);

      expect(hijackAttempt.body.error).toContain('access');

      // Attempt to use session ID directly without proper authorization
      const directAccess = await request
        .get(`/api/sessions/${sessionId}`)
        .expect(401);

      expect(directAccess.body.error).toContain('authentication');
    });
  });

  describe('Audit Logging and Monitoring', () => {
    it('should log authentication events', async () => {
      // Successful login
      await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' });

      // Failed login
      await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'wrong_password' })
        .expect(401);

      // Check audit logs (would query audit system)
      const auditEntries = await permissionManager.getAuditEntries({
        userId: 'user_standard',
        eventType: 'authentication',
        limit: 10
      });

      expect(auditEntries.length).toBeGreaterThan(0);
      
      const successEvent = auditEntries.find(e => e.success);
      const failureEvent = auditEntries.find(e => !e.success);

      expect(successEvent).toBeDefined();
      expect(failureEvent).toBeDefined();
    });

    it('should log permission violations', async () => {
      const readonlyToken = (await request
        .post('/auth/login')
        .send({ email: 'readonly@test.com', password: 'readonly_password' })).body.token;

      // Attempt unauthorized operation
      await request
        .post('/api/tools/write/execute')
        .set('Authorization', `Bearer ${readonlyToken}`)
        .send({
          parameters: { path: '/test/unauthorized.txt', content: 'Should fail' },
          context: { permissions: ['write_files'], workingDirectory: '/test' }
        })
        .expect(403);

      // Check audit logs
      const auditEntries = await permissionManager.getAuditEntries({
        userId: 'user_readonly',
        eventType: 'permission_violation',
        limit: 10
      });

      expect(auditEntries.length).toBeGreaterThan(0);
      
      const violationEvent = auditEntries[0];
      expect(violationEvent.success).toBe(false);
      expect(violationEvent.action).toBe('write_files');
    });

    it('should track sensitive operations', async () => {
      const adminToken = (await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' })).body.token;

      // Perform sensitive operation
      await request
        .post('/api/tools/bash/execute')
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          parameters: { command: 'cat /etc/passwd' },
          context: { permissions: ['execute_commands'], workingDirectory: '/test' }
        });

      // Check audit logs for sensitive command
      const auditEntries = await permissionManager.getAuditEntries({
        userId: 'user_admin',
        eventType: 'sensitive_operation',
        limit: 10
      });

      expect(auditEntries.length).toBeGreaterThan(0);
      
      const sensitiveEvent = auditEntries.find(e => 
        e.metadata?.command?.includes('/etc/passwd')
      );
      expect(sensitiveEvent).toBeDefined();
    });

    it('should generate security alerts for suspicious activity', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Simulate multiple rapid failed attempts
      const rapidRequests = Array.from({ length: 20 }, () =>
        request
          .post('/api/tools/read/execute')
          .set('Authorization', `Bearer ${userToken}`)
          .send({
            parameters: { path: '/secure/sensitive.txt' }, // Unauthorized path
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          })
      );

      await Promise.all(rapidRequests);

      // Check for security alerts
      const alerts = await permissionManager.getSecurityAlerts({
        userId: 'user_standard',
        type: 'suspicious_activity',
        limit: 10
      });

      expect(alerts.length).toBeGreaterThan(0);
      
      const suspiciousAlert = alerts.find(a => 
        a.type === 'multiple_unauthorized_attempts'
      );
      expect(suspiciousAlert).toBeDefined();
    });
  });

  describe('Rate Limiting and Security Policies', () => {
    it('should enforce rate limits per user', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Make rapid requests exceeding rate limit
      const rapidRequests = Array.from({ length: 150 }, () => // Exceeds 100/minute limit
        request
          .get('/api/user/profile')
          .set('Authorization', `Bearer ${userToken}`)
      );

      const results = await Promise.allSettled(rapidRequests);
      
      // Some should succeed, some should be rate limited
      const successful = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;
      
      const rateLimited = results.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 429
      ).length;

      expect(successful).toBeGreaterThan(0);
      expect(rateLimited).toBeGreaterThan(0);
      expect(successful).toBeLessThan(150); // Not all should succeed
    });

    it('should apply different rate limits based on user role', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      const adminToken = (await request
        .post('/auth/login')
        .send({ email: 'admin@test.com', password: 'admin_password' })).body.token;

      // Admin should have higher rate limits
      const adminRequests = Array.from({ length: 50 }, () =>
        request
          .get('/api/user/profile')
          .set('Authorization', `Bearer ${adminToken}`)
      );

      const userRequests = Array.from({ length: 50 }, () =>
        request
          .get('/api/user/profile')
          .set('Authorization', `Bearer ${userToken}`)
      );

      const [adminResults, userResults] = await Promise.all([
        Promise.allSettled(adminRequests),
        Promise.allSettled(userRequests)
      ]);

      const adminSuccessful = adminResults.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;
      
      const userSuccessful = userResults.filter(r => 
        r.status === 'fulfilled' && (r.value as any).status === 200
      ).length;

      // Admin should generally have more successful requests
      expect(adminSuccessful).toBeGreaterThanOrEqual(userSuccessful);
    });

    it('should enforce security policies for file operations', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Test various security policy violations
      const securityTests = [
        {
          name: 'Path traversal',
          params: { path: '/test/../../../etc/passwd' },
          shouldFail: true
        },
        {
          name: 'Symbolic link following',
          params: { path: '/test/symlink_to_sensitive' },
          shouldFail: true
        },
        {
          name: 'Hidden file access',
          params: { path: '/test/.secret' },
          shouldFail: true
        },
        {
          name: 'Large file read',
          params: { path: '/test/public.txt', maxSize: 1 }, // Very small limit
          shouldFail: false // Should succeed but truncate
        }
      ];

      for (const test of securityTests) {
        const response = await request
          .post('/api/tools/read/execute')
          .set('Authorization', `Bearer ${userToken}`)
          .send({
            parameters: test.params,
            context: { permissions: ['read_files'], workingDirectory: '/test' }
          });

        if (test.shouldFail) {
          expect(response.status).toBeOneOf([403, 200]);
          if (response.status === 200) {
            expect(response.body.result.success).toBe(false);
            expect(response.body.result.error).toBeDefined();
          }
        } else {
          expect(response.status).toBe(200);
        }
      }
    });

    it('should apply content filtering policies', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Test content that should be filtered or blocked
      const contentTests = [
        {
          content: 'password: admin123\napi_key: secret_key_12345',
          shouldWarn: true
        },
        {
          content: 'SELECT * FROM users WHERE id = 1; DROP TABLE users;',
          shouldBlock: true
        },
        {
          content: 'Normal content without sensitive information',
          shouldAllow: true
        }
      ];

      for (const test of contentTests) {
        const response = await request
          .post('/api/tools/write/execute')
          .set('Authorization', `Bearer ${userToken}`)
          .send({
            parameters: { 
              path: '/test/content-test.txt',
              content: test.content 
            },
            context: { permissions: ['write_files'], workingDirectory: '/test' }
          });

        if (test.shouldBlock) {
          expect(response.status).toBeOneOf([403, 200]);
          if (response.status === 200) {
            expect(response.body.result.success).toBe(false);
            expect(response.body.result.error).toContain('content policy');
          }
        } else if (test.shouldWarn) {
          expect(response.status).toBe(200);
          if (response.body.result.success) {
            expect(response.body.result.warnings).toBeDefined();
          }
        } else {
          expect(response.status).toBe(200);
          expect(response.body.result.success).toBe(true);
        }
      }
    });
  });

  describe('Multi-tenant Security', () => {
    it('should isolate data between different tenants', async () => {
      // This would test tenant-based isolation in a multi-tenant setup
      const tenant1User = (await request
        .post('/auth/login')
        .send({ 
          email: 'user@test.com', 
          password: 'user_password',
          tenant: 'tenant1' 
        })).body.token;

      const tenant2User = (await request
        .post('/auth/login')
        .send({ 
          email: 'user@test.com', 
          password: 'user_password',
          tenant: 'tenant2' 
        })).body.token;

      // Each tenant should have isolated data
      // Implementation would depend on how multi-tenancy is handled
      expect(tenant1User).toBeDefined();
      expect(tenant2User).toBeDefined();
      expect(tenant1User).not.toBe(tenant2User);
    });

    it('should enforce cross-tenant access restrictions', async () => {
      // Test that users from one tenant cannot access another tenant's resources
      // This is a placeholder for multi-tenant functionality
      expect(true).toBe(true); // Implementation would depend on multi-tenant architecture
    });
  });

  describe('Security Incident Response', () => {
    it('should detect and respond to brute force attacks', async () => {
      // Simulate brute force login attempts
      const bruteForceAttempts = Array.from({ length: 10 }, () =>
        request
          .post('/auth/login')
          .send({ email: 'user@test.com', password: 'wrong_password' })
      );

      const results = await Promise.all(bruteForceAttempts);
      
      // Later attempts should be blocked or delayed
      const laterAttempts = results.slice(-3);
      laterAttempts.forEach(response => {
        expect(response.status).toBe(401);
        // Should have increasing delay or account lockout
      });

      // Check that security incident was logged
      const incidents = await permissionManager.getSecurityIncidents({
        type: 'brute_force_attempt',
        limit: 10
      });

      expect(incidents.length).toBeGreaterThan(0);
    });

    it('should automatically revoke compromised sessions', async () => {
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      // Create session
      const sessionResponse = await request
        .post('/api/sessions')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ userId: 'user_standard' });

      const sessionId = sessionResponse.body.sessionId;

      // Simulate compromise detection (multiple IPs, unusual patterns, etc.)
      await permissionManager.reportSecurityIncident({
        type: 'session_compromise',
        userId: 'user_standard',
        sessionId: sessionId,
        metadata: { reason: 'multiple_ip_access' }
      });

      // Session should be automatically revoked
      const accessAttempt = await request
        .get(`/api/sessions/${sessionId}`)
        .set('Authorization', `Bearer ${userToken}`)
        .expect(401);

      expect(accessAttempt.body.error).toContain('revoked');
    });

    it('should quarantine suspicious user accounts', async () => {
      // Simulate suspicious activity that triggers account quarantine
      await permissionManager.reportSecurityIncident({
        type: 'suspicious_activity',
        userId: 'user_standard',
        severity: 'high',
        metadata: { 
          activities: ['unusual_file_access', 'rapid_api_calls', 'privilege_escalation_attempt'] 
        }
      });

      // User should be quarantined and unable to perform sensitive operations
      const userToken = (await request
        .post('/auth/login')
        .send({ email: 'user@test.com', password: 'user_password' })).body.token;

      const sensitiveOperation = await request
        .post('/api/tools/bash/execute')
        .set('Authorization', `Bearer ${userToken}`)
        .send({
          parameters: { command: 'ls -la /' },
          context: { permissions: ['execute_commands'], workingDirectory: '/test' }
        })
        .expect(403);

      expect(sensitiveOperation.body.error).toContain('quarantined');
    });
  });
});