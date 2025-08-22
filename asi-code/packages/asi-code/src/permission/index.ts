/**
 * Permission System - Fine-grained access control and security
 * 
 * Manages permissions for users, sessions, and operations within the ASI-Code system.
 */

export * from './permission-types.js';
export * from './permission-manager.js';
export * from './safety-protocols.js';

// Legacy exports for backward compatibility
import { EventEmitter } from 'eventemitter3';

export interface Permission {
  id: string;
  name: string;
  description: string;
  category: string;
  level: 'read' | 'write' | 'execute' | 'admin';
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
}

export interface PermissionContext {
  userId?: string;
  sessionId: string;
  resource: string;
  operation: string;
  metadata?: Record<string, any>;
}

export interface PermissionManager extends EventEmitter {
  addPermission(permission: Permission): Promise<void>;
  addRole(role: Role): Promise<void>;
  assignRole(userId: string, roleId: string): Promise<void>;
  checkPermission(context: PermissionContext, permissionId: string): Promise<boolean>;
  getUserPermissions(userId: string): Promise<Permission[]>;
  initialize(config?: Record<string, any>): Promise<void>;
  shutdown(): Promise<void>;
  cleanup(): Promise<void>;
}

export class DefaultPermissionManager extends EventEmitter implements PermissionManager {
  private permissions = new Map<string, Permission>();
  private roles = new Map<string, Role>();
  private userRoles = new Map<string, Set<string>>();

  async addPermission(permission: Permission): Promise<void> {
    this.permissions.set(permission.id, permission);
    this.emit('permission:added', { permission });
  }

  async addRole(role: Role): Promise<void> {
    this.roles.set(role.id, role);
    this.emit('role:added', { role });
  }

  async assignRole(userId: string, roleId: string): Promise<void> {
    if (!this.userRoles.has(userId)) {
      this.userRoles.set(userId, new Set());
    }
    this.userRoles.get(userId)!.add(roleId);
    this.emit('role:assigned', { userId, roleId });
  }

  async checkPermission(context: PermissionContext, permissionId: string): Promise<boolean> {
    if (!context.userId) {
      return false; // No user, no permissions
    }

    const userRoles = this.userRoles.get(context.userId) || new Set();
    for (const roleId of userRoles) {
      const role = this.roles.get(roleId);
      if (role && role.permissions.includes(permissionId)) {
        this.emit('permission:granted', { context, permissionId });
        return true;
      }
    }

    this.emit('permission:denied', { context, permissionId });
    return false;
  }

  async getUserPermissions(userId: string): Promise<Permission[]> {
    const userPermissions: Permission[] = [];
    const userRoles = this.userRoles.get(userId) || new Set();

    for (const roleId of userRoles) {
      const role = this.roles.get(roleId);
      if (role) {
        for (const permissionId of role.permissions) {
          const permission = this.permissions.get(permissionId);
          if (permission) {
            userPermissions.push(permission);
          }
        }
      }
    }

    return userPermissions;
  }

  async initialize(config?: Record<string, any>): Promise<void> {
    // Basic initialization - no complex setup needed
    this.emit('initialized', { config });
  }

  async shutdown(): Promise<void> {
    await this.cleanup();
    this.emit('shutdown');
  }

  async cleanup(): Promise<void> {
    this.permissions.clear();
    this.roles.clear();
    this.userRoles.clear();
    this.removeAllListeners();
  }
}

// Built-in permissions
export const builtinPermissions: Permission[] = [
  { id: 'read_files', name: 'Read Files', description: 'Read file contents', category: 'file', level: 'read' },
  { id: 'write_files', name: 'Write Files', description: 'Write file contents', category: 'file', level: 'write' },
  { id: 'execute_commands', name: 'Execute Commands', description: 'Execute system commands', category: 'system', level: 'execute' },
  { id: 'manage_sessions', name: 'Manage Sessions', description: 'Create and manage sessions', category: 'session', level: 'admin' }
];

// Built-in roles
export const builtinRoles: Role[] = [
  { id: 'user', name: 'User', description: 'Basic user role', permissions: ['read_files'] },
  { id: 'developer', name: 'Developer', description: 'Developer role', permissions: ['read_files', 'write_files'] },
  { id: 'admin', name: 'Admin', description: 'Administrator role', permissions: ['read_files', 'write_files', 'execute_commands', 'manage_sessions'] }
];

export function createPermissionManager(): PermissionManager {
  const manager = new DefaultPermissionManager();
  
  // Add built-in permissions and roles
  builtinPermissions.forEach(p => manager.addPermission(p));
  builtinRoles.forEach(r => manager.addRole(r));
  
  return manager;
}