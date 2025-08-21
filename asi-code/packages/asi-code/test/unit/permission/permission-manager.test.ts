/**
 * Unit tests for Permission Manager
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { PermissionManager, createPermissionManager } from '../../../src/permission/permission-manager.js';
import { PermissionError, SecurityViolationError } from '../../../src/permission/permission-types.js';

// Mock Kenny Integration
vi.mock('../../../src/kenny/integration.js', () => ({
  getKennyIntegration: () => ({
    getMessageBus: () => ({
      publishSubsystem: vi.fn().mockResolvedValue(undefined)
    })
  })
}));

// Mock Safety Protocols
vi.mock('../../../src/permission/safety-protocols.js', () => ({
  SafetyProtocolManager: class MockSafetyProtocolManager {
    async initialize() {}
    async start() {}
    async stop() {}
    async shutdown() {}
    async checkPermissionRequest() {}
  }
}));

describe('PermissionManager', () => {
  let permissionManager: PermissionManager;
  
  beforeEach(async () => {
    permissionManager = new PermissionManager({
      enableCaching: true,
      enableAuditing: true,
      enableSafetyProtocols: false // Disable for simpler testing
    });
    await permissionManager.initialize();
  });
  
  afterEach(async () => {
    await permissionManager.shutdown();
  });

  describe('Initialization', () => {
    it('should initialize successfully', async () => {
      const manager = new PermissionManager();
      await manager.initialize();
      
      expect(manager.status).toBe('running');
      await manager.shutdown();
    });

    it('should initialize with custom config', async () => {
      const config = {
        enableCaching: false,
        enableAuditing: false,
        cacheMaxSize: 5000,
        cacheTTL: 600000
      };
      
      const manager = new PermissionManager(config);
      await manager.initialize();
      
      expect(manager).toBeInstanceOf(PermissionManager);
      await manager.shutdown();
    });

    it('should load built-in permissions and roles', async () => {
      const manager = new PermissionManager();
      await manager.initialize();
      
      // Should have some built-in permissions loaded
      expect(manager).toBeInstanceOf(PermissionManager);
      
      await manager.shutdown();
    });
  });

  describe('Permission Management', () => {
    it('should add new permission', async () => {
      const permission = {
        id: 'test_permission',
        name: 'Test Permission',
        description: 'A permission for testing',
        category: 'test' as const,
        safetyLevel: 'safe' as const,
        resourceTypes: ['test_resource' as const]
      };

      await expect(permissionManager.addPermission(permission)).resolves.toBeUndefined();
    });

    it('should add new role', async () => {
      // First add a permission
      await permissionManager.addPermission({
        id: 'test_perm',
        name: 'Test Permission',
        description: 'Test',
        category: 'test',
        safetyLevel: 'safe',
        resourceTypes: ['test']
      });

      const role = {
        id: 'test_role',
        name: 'Test Role',
        description: 'A role for testing',
        permissions: ['test_perm'],
        level: 'user' as const
      };

      await expect(permissionManager.addRole(role)).resolves.toBeUndefined();
    });

    it('should reject role with invalid permission', async () => {
      const role = {
        id: 'invalid_role',
        name: 'Invalid Role',
        description: 'Role with invalid permission',
        permissions: ['nonexistent_permission'],
        level: 'user' as const
      };

      await expect(permissionManager.addRole(role)).rejects.toThrow(PermissionError);
    });
  });

  describe('User Management', () => {
    beforeEach(async () => {
      // Add test permission and role
      await permissionManager.addPermission({
        id: 'read_files',
        name: 'Read Files',
        description: 'Permission to read files',
        category: 'file',
        safetyLevel: 'safe',
        resourceTypes: ['file']
      });

      await permissionManager.addRole({
        id: 'file_reader',
        name: 'File Reader',
        description: 'Can read files',
        permissions: ['read_files'],
        level: 'user'
      });
    });

    it('should create user with valid roles', async () => {
      const userData = {
        id: 'test_user',
        username: 'testuser',
        email: 'test@example.com',
        roles: ['file_reader'],
        status: 'active' as const
      };

      const user = await permissionManager.createUser(userData);
      
      expect(user).toMatchObject({
        id: 'test_user',
        username: 'testuser',
        email: 'test@example.com',
        roles: ['file_reader'],
        status: 'active'
      });
      expect(user.createdAt).toBeInstanceOf(Date);
      expect(user.sessions).toEqual([]);
    });

    it('should reject user with invalid role', async () => {
      const userData = {
        id: 'invalid_user',
        username: 'invalid',
        email: 'invalid@example.com',
        roles: ['nonexistent_role'],
        status: 'active' as const
      };

      await expect(permissionManager.createUser(userData)).rejects.toThrow(PermissionError);
    });

    it('should get user permissions including role permissions', async () => {
      const user = await permissionManager.createUser({
        id: 'test_user',
        username: 'testuser',
        email: 'test@example.com',
        roles: ['file_reader'],
        status: 'active'
      });

      const permissions = await permissionManager.getUserPermissions(user.id);
      
      expect(permissions).toHaveLength(1);
      expect(permissions[0].id).toBe('read_files');
    });
  });

  describe('Session Management', () => {
    let testUser: any;

    beforeEach(async () => {
      await permissionManager.addRole({
        id: 'basic_role',
        name: 'Basic Role',
        description: 'Basic role',
        permissions: [],
        level: 'user'
      });

      testUser = await permissionManager.createUser({
        id: 'session_user',
        username: 'sessionuser',
        email: 'session@example.com',
        roles: ['basic_role'],
        status: 'active'
      });
    });

    it('should create session for valid user', async () => {
      const sessionData = {
        ipAddress: '127.0.0.1',
        userAgent: 'Test Agent',
        status: 'active' as const
      };

      const session = await permissionManager.createSession(testUser.id, sessionData);
      
      expect(session).toMatchObject({
        userId: testUser.id,
        ipAddress: '127.0.0.1',
        userAgent: 'Test Agent',
        status: 'active'
      });
      expect(session.id).toBeDefined();
      expect(session.startTime).toBeInstanceOf(Date);
    });

    it('should reject session for inactive user', async () => {
      const inactiveUser = await permissionManager.createUser({
        id: 'inactive_user',
        username: 'inactive',
        email: 'inactive@example.com',
        roles: ['basic_role'],
        status: 'inactive'
      });

      await expect(permissionManager.createSession(inactiveUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test',
        status: 'active'
      })).rejects.toThrow(PermissionError);
    });

    it('should enforce session limits', async () => {
      const userWithLimits = await permissionManager.createUser({
        id: 'limited_user',
        username: 'limited',
        email: 'limited@example.com',
        roles: ['basic_role'],
        status: 'active',
        constraints: { maxSessions: 1 }
      });

      // First session should succeed
      await permissionManager.createSession(userWithLimits.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test1',
        status: 'active'
      });

      // Second session should fail
      await expect(permissionManager.createSession(userWithLimits.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test2',
        status: 'active'
      })).rejects.toThrow('SESSION_LIMIT_EXCEEDED');
    });
  });

  describe('Permission Checking', () => {
    let testUser: any;
    let testSession: any;

    beforeEach(async () => {
      // Setup test data
      await permissionManager.addPermission({
        id: 'test_action',
        name: 'Test Action',
        description: 'Permission for testing',
        category: 'test',
        safetyLevel: 'safe',
        resourceTypes: ['test_resource']
      });

      await permissionManager.addRole({
        id: 'test_role',
        name: 'Test Role',
        description: 'Role for testing',
        permissions: ['test_action'],
        level: 'user'
      });

      testUser = await permissionManager.createUser({
        id: 'check_user',
        username: 'checkuser',
        email: 'check@example.com',
        roles: ['test_role'],
        status: 'active'
      });

      testSession = await permissionManager.createSession(testUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test',
        status: 'active'
      });
    });

    it('should grant permission for valid request', async () => {
      const request = {
        permissionId: 'test_action',
        context: {
          userId: testUser.id,
          sessionId: testSession.id,
          resource: 'test_resource',
          operation: 'read',
          ipAddress: '127.0.0.1'
        }
      };

      const result = await permissionManager.checkPermission(request);
      
      expect(result.granted).toBe(true);
      expect(result.reason).toBe('Permission granted');
      expect(result.auditInfo).toBeDefined();
    });

    it('should deny permission for invalid permission ID', async () => {
      const request = {
        permissionId: 'nonexistent_permission',
        context: {
          userId: testUser.id,
          sessionId: testSession.id,
          resource: 'test_resource',
          operation: 'read',
          ipAddress: '127.0.0.1'
        }
      };

      const result = await permissionManager.checkPermission(request);
      
      expect(result.granted).toBe(false);
      expect(result.reason).toContain('does not exist');
    });

    it('should deny permission for user without required permission', async () => {
      const userWithoutPermission = await permissionManager.createUser({
        id: 'no_perm_user',
        username: 'noperm',
        email: 'noperm@example.com',
        roles: [], // No roles = no permissions
        status: 'active'
      });

      const session = await permissionManager.createSession(userWithoutPermission.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test',
        status: 'active'
      });

      const request = {
        permissionId: 'test_action',
        context: {
          userId: userWithoutPermission.id,
          sessionId: session.id,
          resource: 'test_resource',
          operation: 'read'
        }
      };

      const result = await permissionManager.checkPermission(request);
      
      expect(result.granted).toBe(false);
      expect(result.reason).toContain('does not have required permission');
    });

    it('should use cache for repeated requests', async () => {
      const request = {
        permissionId: 'test_action',
        context: {
          userId: testUser.id,
          sessionId: testSession.id,
          resource: 'test_resource',
          operation: 'read'
        }
      };

      // First request
      const result1 = await permissionManager.checkPermission(request);
      expect(result1.granted).toBe(true);

      // Second request should hit cache
      const result2 = await permissionManager.checkPermission(request);
      expect(result2.granted).toBe(true);

      const stats = permissionManager.getStats();
      expect(stats.cacheHits).toBe(1);
      expect(stats.cacheMisses).toBe(1);
    });
  });

  describe('Statistics and Auditing', () => {
    it('should track statistics', async () => {
      const initialStats = permissionManager.getStats();
      expect(initialStats.totalChecks).toBe(0);
      expect(initialStats.grantedCount).toBe(0);
      expect(initialStats.deniedCount).toBe(0);
    });

    it('should provide audit log', async () => {
      const auditLog = permissionManager.getAuditLog();
      expect(Array.isArray(auditLog)).toBe(true);
    });

    it('should filter audit log', async () => {
      const filteredLog = permissionManager.getAuditLog({
        result: 'granted',
        limit: 10
      });
      expect(Array.isArray(filteredLog)).toBe(true);
    });
  });

  describe('Health Check', () => {
    it('should provide health status', async () => {
      const health = await (permissionManager as any).onHealthCheck();
      
      expect(health).toMatchObject({
        status: 'healthy',
        message: expect.stringContaining('permissions'),
        timestamp: expect.any(Date),
        details: expect.objectContaining({
          permissions: expect.any(Number),
          roles: expect.any(Number),
          users: expect.any(Number),
          sessions: expect.any(Number)
        })
      });
    });
  });

  describe('Rate Limiting', () => {
    it('should enforce rate limits', async () => {
      const limitedManager = new PermissionManager({
        rateLimit: {
          maxRequestsPerMinute: 2,
          maxRequestsPerHour: 10
        },
        enableSafetyProtocols: false
      });
      await limitedManager.initialize();

      // Setup test data
      await limitedManager.addPermission({
        id: 'rate_test',
        name: 'Rate Test',
        description: 'For rate limit testing',
        category: 'test',
        safetyLevel: 'safe',
        resourceTypes: ['test']
      });

      await limitedManager.addRole({
        id: 'rate_role',
        name: 'Rate Role',
        description: 'Role for rate testing',
        permissions: ['rate_test'],
        level: 'user'
      });

      const user = await limitedManager.createUser({
        id: 'rate_user',
        username: 'rateuser',
        email: 'rate@example.com',
        roles: ['rate_role'],
        status: 'active'
      });

      const session = await limitedManager.createSession(user.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test',
        status: 'active'
      });

      const request = {
        permissionId: 'rate_test',
        context: {
          userId: user.id,
          sessionId: session.id,
          resource: 'test',
          operation: 'read'
        }
      };

      // First two requests should succeed
      const result1 = await limitedManager.checkPermission(request);
      const result2 = await limitedManager.checkPermission(request);
      
      expect(result1.granted).toBe(true);
      expect(result2.granted).toBe(true);

      // Third request should fail due to rate limit
      const result3 = await limitedManager.checkPermission(request);
      expect(result3.granted).toBe(false);
      expect(result3.reason).toContain('Rate limit exceeded');

      await limitedManager.shutdown();
    });
  });

  describe('Factory Function', () => {
    it('should create permission manager using factory', () => {
      const manager = createPermissionManager({
        enableCaching: false,
        enableAuditing: true
      });
      
      expect(manager).toBeInstanceOf(PermissionManager);
    });
  });

  describe('Error Handling', () => {
    it('should handle permission check errors gracefully', async () => {
      const request = {
        permissionId: 'test_permission',
        context: {
          sessionId: 'invalid_session',
          resource: 'test',
          operation: 'read'
        }
      };

      const result = await permissionManager.checkPermission(request);
      
      expect(result.granted).toBe(false);
      expect(result.auditInfo?.result).toBe('error');
    });

    it('should handle missing user gracefully', async () => {
      await expect(permissionManager.getUserPermissions('nonexistent_user'))
        .rejects.toThrow(PermissionError);
    });
  });

  describe('Cleanup', () => {
    it('should cleanup resources on shutdown', async () => {
      const manager = new PermissionManager();
      await manager.initialize();
      
      expect(manager.status).toBe('running');
      
      await manager.shutdown();
      
      expect(manager.status).toBe('stopped');
    });
  });
});