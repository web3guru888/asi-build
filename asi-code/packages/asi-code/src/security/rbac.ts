import { Context, Next } from 'hono';
import { logger } from '../logging/logger.js';

export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description?: string;
  conditions?: PermissionCondition[];
}

export interface PermissionCondition {
  field: string;
  operator: 'eq' | 'ne' | 'in' | 'nin' | 'gt' | 'lt' | 'gte' | 'lte' | 'regex';
  value: any;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: string[]; // Permission IDs
  inherits?: string[]; // Parent role IDs
  isSystem?: boolean; // System roles cannot be deleted
}

export interface User {
  id: string;
  roles: string[]; // Role IDs
  permissions?: string[]; // Direct permissions (override role permissions)
  attributes?: Record<string, any>; // For condition evaluation
}

export interface AuthorizationResult {
  allowed: boolean;
  reason?: string;
  requiredPermissions?: string[];
  userPermissions?: string[];
}

export interface AuthorizationContext {
  user: User;
  resource: string;
  action: string;
  resourceData?: any;
  environment?: Record<string, any>;
}

/**
 * Role-Based Access Control (RBAC) Manager
 */
export class RBACManager {
  private permissions: Map<string, Permission> = new Map();
  private roles: Map<string, Role> = new Map();
  private userRoleCache: Map<string, Set<string>> = new Map();
  private auditLog: Array<{
    userId: string;
    action: string;
    resource: string;
    allowed: boolean;
    timestamp: Date;
    context?: any;
  }> = [];

  constructor() {
    this.initializeSystemRoles();
    this.scheduleCleanup();
  }

  /**
   * Initialize system roles and permissions
   */
  private initializeSystemRoles(): void {
    // System permissions
    const systemPermissions: Permission[] = [
      {
        id: 'system.admin',
        name: 'System Administration',
        resource: '*',
        action: '*',
        description: 'Full system access'
      },
      {
        id: 'user.read',
        name: 'Read Users',
        resource: 'user',
        action: 'read'
      },
      {
        id: 'user.write',
        name: 'Write Users',
        resource: 'user',
        action: 'write'
      },
      {
        id: 'user.delete',
        name: 'Delete Users',
        resource: 'user',
        action: 'delete'
      },
      {
        id: 'session.read',
        name: 'Read Sessions',
        resource: 'session',
        action: 'read'
      },
      {
        id: 'session.write',
        name: 'Write Sessions',
        resource: 'session',
        action: 'write'
      },
      {
        id: 'session.delete',
        name: 'Delete Sessions',
        resource: 'session',
        action: 'delete'
      },
      {
        id: 'tool.execute',
        name: 'Execute Tools',
        resource: 'tool',
        action: 'execute'
      },
      {
        id: 'file.read',
        name: 'Read Files',
        resource: 'file',
        action: 'read'
      },
      {
        id: 'file.write',
        name: 'Write Files',
        resource: 'file',
        action: 'write'
      },
      {
        id: 'api.access',
        name: 'API Access',
        resource: 'api',
        action: 'access'
      }
    ];

    systemPermissions.forEach(permission => {
      this.addPermission(permission);
    });

    // System roles
    const systemRoles: Role[] = [
      {
        id: 'super_admin',
        name: 'Super Administrator',
        description: 'Full system access',
        permissions: ['system.admin'],
        isSystem: true
      },
      {
        id: 'admin',
        name: 'Administrator',
        description: 'Administrative access',
        permissions: [
          'user.read', 'user.write', 'user.delete',
          'session.read', 'session.write', 'session.delete',
          'tool.execute', 'file.read', 'file.write',
          'api.access'
        ],
        isSystem: true
      },
      {
        id: 'developer',
        name: 'Developer',
        description: 'Development access',
        permissions: [
          'session.read', 'session.write',
          'tool.execute', 'file.read', 'file.write',
          'api.access'
        ],
        isSystem: true
      },
      {
        id: 'user',
        name: 'Regular User',
        description: 'Basic user access',
        permissions: [
          'session.read', 'session.write',
          'tool.execute', 'file.read',
          'api.access'
        ],
        isSystem: true
      },
      {
        id: 'readonly',
        name: 'Read Only',
        description: 'Read-only access',
        permissions: [
          'session.read', 'file.read', 'api.access'
        ],
        isSystem: true
      }
    ];

    systemRoles.forEach(role => {
      this.addRole(role);
    });

    logger.info('RBAC system initialized with system roles and permissions');
  }

  /**
   * Add a permission
   */
  addPermission(permission: Permission): void {
    this.permissions.set(permission.id, permission);
    logger.debug('Permission added', { permissionId: permission.id, permission });
  }

  /**
   * Add a role
   */
  addRole(role: Role): void {
    // Validate permissions exist
    for (const permissionId of role.permissions) {
      if (!this.permissions.has(permissionId)) {
        throw new Error(`Permission '${permissionId}' not found`);
      }
    }

    // Validate parent roles exist
    if (role.inherits) {
      for (const parentRoleId of role.inherits) {
        if (!this.roles.has(parentRoleId)) {
          throw new Error(`Parent role '${parentRoleId}' not found`);
        }
      }
    }

    this.roles.set(role.id, role);
    this.invalidateUserRoleCache();
    logger.debug('Role added', { roleId: role.id, role });
  }

  /**
   * Get all permissions for a user (including inherited)
   */
  getUserPermissions(user: User): Set<string> {
    const permissions = new Set<string>();

    // Add direct permissions
    if (user.permissions) {
      user.permissions.forEach(permissionId => {
        permissions.add(permissionId);
      });
    }

    // Add role permissions (including inherited)
    user.roles.forEach(roleId => {
      const rolePermissions = this.getRolePermissions(roleId);
      rolePermissions.forEach(permissionId => {
        permissions.add(permissionId);
      });
    });

    return permissions;
  }

  /**
   * Get all permissions for a role (including inherited)
   */
  getRolePermissions(roleId: string): Set<string> {
    if (this.userRoleCache.has(roleId)) {
      return this.userRoleCache.get(roleId)!;
    }

    const permissions = new Set<string>();
    const visitedRoles = new Set<string>();

    const collectPermissions = (currentRoleId: string) => {
      if (visitedRoles.has(currentRoleId)) {
        logger.warn('Circular role inheritance detected', { roleId: currentRoleId });
        return;
      }

      visitedRoles.add(currentRoleId);
      const role = this.roles.get(currentRoleId);
      
      if (!role) {
        logger.warn('Role not found', { roleId: currentRoleId });
        return;
      }

      // Add direct permissions
      role.permissions.forEach(permissionId => {
        permissions.add(permissionId);
      });

      // Add inherited permissions
      if (role.inherits) {
        role.inherits.forEach(parentRoleId => {
          collectPermissions(parentRoleId);
        });
      }
    };

    collectPermissions(roleId);
    this.userRoleCache.set(roleId, permissions);

    return permissions;
  }

  /**
   * Check if user has specific permission
   */
  hasPermission(user: User, permissionId: string): boolean {
    const userPermissions = this.getUserPermissions(user);
    
    // Check for exact permission
    if (userPermissions.has(permissionId)) {
      return true;
    }

    // Check for wildcard permissions
    if (userPermissions.has('system.admin')) {
      return true;
    }

    // Check for resource wildcard
    const permission = this.permissions.get(permissionId);
    if (permission) {
      const resourceWildcard = `${permission.resource}.*`;
      if (userPermissions.has(resourceWildcard)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Authorize user action
   */
  authorize(context: AuthorizationContext): AuthorizationResult {
    const { user, resource, action, resourceData, environment } = context;
    
    try {
      // Find matching permissions
      const matchingPermissions = this.findMatchingPermissions(resource, action);
      const userPermissions = this.getUserPermissions(user);
      
      // Check if user has any matching permission
      for (const permission of matchingPermissions) {
        if (this.hasPermission(user, permission.id)) {
          // Check conditions if any
          if (permission.conditions && permission.conditions.length > 0) {
            const conditionResult = this.evaluateConditions(
              permission.conditions,
              user,
              resourceData,
              environment
            );
            
            if (!conditionResult.allowed) {
              this.logAuthorizationAttempt(user.id, action, resource, false, {
                reason: conditionResult.reason,
                permission: permission.id
              });
              
              return {
                allowed: false,
                reason: conditionResult.reason,
                requiredPermissions: [permission.id],
                userPermissions: Array.from(userPermissions)
              };
            }
          }

          // Permission granted
          this.logAuthorizationAttempt(user.id, action, resource, true, {
            permission: permission.id
          });

          return {
            allowed: true,
            requiredPermissions: [permission.id],
            userPermissions: Array.from(userPermissions)
          };
        }
      }

      // No matching permissions found
      this.logAuthorizationAttempt(user.id, action, resource, false, {
        reason: 'No matching permissions',
        requiredPermissions: matchingPermissions.map(p => p.id)
      });

      return {
        allowed: false,
        reason: 'Insufficient permissions',
        requiredPermissions: matchingPermissions.map(p => p.id),
        userPermissions: Array.from(userPermissions)
      };

    } catch (error) {
      logger.error('Authorization error', { user: user.id, resource, action, error });
      
      this.logAuthorizationAttempt(user.id, action, resource, false, {
        reason: 'Authorization error',
        error: error.message
      });

      return {
        allowed: false,
        reason: 'Authorization error'
      };
    }
  }

  /**
   * Find permissions matching resource and action
   */
  private findMatchingPermissions(resource: string, action: string): Permission[] {
    const matches: Permission[] = [];

    this.permissions.forEach(permission => {
      // Check for exact match
      if (permission.resource === resource && permission.action === action) {
        matches.push(permission);
        return;
      }

      // Check for wildcards
      if (permission.resource === '*' || permission.action === '*') {
        matches.push(permission);
        return;
      }

      // Check for resource match with wildcard action
      if (permission.resource === resource && permission.action === '*') {
        matches.push(permission);
        return;
      }

      // Check for action match with wildcard resource
      if (permission.resource === '*' && permission.action === action) {
        matches.push(permission);
        return;
      }
    });

    return matches;
  }

  /**
   * Evaluate permission conditions
   */
  private evaluateConditions(
    conditions: PermissionCondition[],
    user: User,
    resourceData?: any,
    environment?: Record<string, any>
  ): { allowed: boolean; reason?: string } {
    
    for (const condition of conditions) {
      const result = this.evaluateCondition(condition, user, resourceData, environment);
      if (!result.allowed) {
        return result;
      }
    }

    return { allowed: true };
  }

  /**
   * Evaluate single condition
   */
  private evaluateCondition(
    condition: PermissionCondition,
    user: User,
    resourceData?: any,
    environment?: Record<string, any>
  ): { allowed: boolean; reason?: string } {
    
    // Get field value from context
    let fieldValue: any;
    
    if (condition.field.startsWith('user.')) {
      const field = condition.field.replace('user.', '');
      fieldValue = user.attributes?.[field] ?? user[field as keyof User];
    } else if (condition.field.startsWith('resource.')) {
      const field = condition.field.replace('resource.', '');
      fieldValue = resourceData?.[field];
    } else if (condition.field.startsWith('env.')) {
      const field = condition.field.replace('env.', '');
      fieldValue = environment?.[field];
    } else {
      fieldValue = resourceData?.[condition.field];
    }

    // Evaluate condition
    const allowed = this.evaluateOperator(fieldValue, condition.operator, condition.value);
    
    return {
      allowed,
      reason: allowed ? undefined : `Condition failed: ${condition.field} ${condition.operator} ${condition.value}`
    };
  }

  /**
   * Evaluate operator
   */
  private evaluateOperator(fieldValue: any, operator: string, conditionValue: any): boolean {
    switch (operator) {
      case 'eq':
        return fieldValue === conditionValue;
      case 'ne':
        return fieldValue !== conditionValue;
      case 'in':
        return Array.isArray(conditionValue) && conditionValue.includes(fieldValue);
      case 'nin':
        return Array.isArray(conditionValue) && !conditionValue.includes(fieldValue);
      case 'gt':
        return fieldValue > conditionValue;
      case 'lt':
        return fieldValue < conditionValue;
      case 'gte':
        return fieldValue >= conditionValue;
      case 'lte':
        return fieldValue <= conditionValue;
      case 'regex':
        return new RegExp(conditionValue).test(String(fieldValue));
      default:
        logger.warn('Unknown operator', { operator });
        return false;
    }
  }

  /**
   * Create authorization middleware
   */
  middleware(resource: string, action: string) {
    return async (c: Context, next: Next) => {
      const user = c.get('user') || c.get('currentUser');
      
      if (!user) {
        return c.json({ error: 'Authentication required' }, 401);
      }

      const authResult = this.authorize({
        user,
        resource,
        action,
        resourceData: c.get('resourceData'),
        environment: {
          method: c.req.method,
          path: c.req.path,
          userAgent: c.req.header('user-agent'),
          ip: c.req.header('x-forwarded-for') || c.env?.remoteAddr
        }
      });

      if (!authResult.allowed) {
        return c.json({
          error: 'Forbidden',
          message: authResult.reason || 'Insufficient permissions',
          requiredPermissions: authResult.requiredPermissions
        }, 403);
      }

      // Store authorization result for potential use in handlers
      c.set('authResult', authResult);
      
      await next();
    };
  }

  /**
   * Log authorization attempt
   */
  private logAuthorizationAttempt(
    userId: string,
    action: string,
    resource: string,
    allowed: boolean,
    context?: any
  ): void {
    const logEntry = {
      userId,
      action,
      resource,
      allowed,
      timestamp: new Date(),
      context
    };

    this.auditLog.push(logEntry);

    // Keep only last 10000 entries
    if (this.auditLog.length > 10000) {
      this.auditLog = this.auditLog.slice(-5000);
    }

    if (allowed) {
      logger.debug('Authorization granted', logEntry);
    } else {
      logger.warn('Authorization denied', logEntry);
    }
  }

  /**
   * Get audit log for user
   */
  getUserAuditLog(userId: string): typeof this.auditLog {
    return this.auditLog.filter(entry => entry.userId === userId);
  }

  /**
   * Invalidate user role cache
   */
  private invalidateUserRoleCache(): void {
    this.userRoleCache.clear();
  }

  /**
   * Schedule cleanup of old audit logs
   */
  private scheduleCleanup(): void {
    setInterval(() => {
      const cutoff = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000); // 30 days
      this.auditLog = this.auditLog.filter(entry => entry.timestamp > cutoff);
      
      logger.debug('RBAC audit log cleanup completed', { 
        remainingEntries: this.auditLog.length 
      });
    }, 24 * 60 * 60 * 1000); // Daily
  }

  /**
   * Export permissions and roles for backup
   */
  exportConfiguration(): { permissions: Permission[]; roles: Role[] } {
    return {
      permissions: Array.from(this.permissions.values()),
      roles: Array.from(this.roles.values())
    };
  }

  /**
   * Import permissions and roles from backup
   */
  importConfiguration(config: { permissions: Permission[]; roles: Role[] }): void {
    // Clear existing non-system data
    const systemPermissions = Array.from(this.permissions.values()).filter(p => p.id.startsWith('system.') || p.id.includes('.'));
    const systemRoles = Array.from(this.roles.values()).filter(r => r.isSystem);

    this.permissions.clear();
    this.roles.clear();

    // Restore system data
    systemPermissions.forEach(p => this.permissions.set(p.id, p));
    systemRoles.forEach(r => this.roles.set(r.id, r));

    // Import new data
    config.permissions.forEach(p => this.addPermission(p));
    config.roles.forEach(r => this.addRole(r));

    logger.info('RBAC configuration imported', {
      permissions: config.permissions.length,
      roles: config.roles.length
    });
  }
}

// Singleton instance
let rbacManagerInstance: RBACManager | null = null;

export function getRBACManager(): RBACManager {
  if (!rbacManagerInstance) {
    rbacManagerInstance = new RBACManager();
  }
  return rbacManagerInstance;
}

/**
 * Convenience function to check permissions
 */
export function requirePermission(resource: string, action: string) {
  return getRBACManager().middleware(resource, action);
}

export default RBACManager;