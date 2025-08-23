/**
 * Permission Manager - Advanced permission checking and management system
 *
 * Integrates with Kenny Integration Pattern to provide comprehensive
 * permission management with caching, auditing, and safety protocols.
 */

import { EventEmitter } from 'eventemitter3';
import { nanoid } from 'nanoid';
import { getKennyIntegration } from '../kenny/integration.js';
import { BaseSubsystem } from '../kenny/base-subsystem.js';
import { SafetyProtocolManager } from './safety-protocols.js';
import type {
  BUILT_IN_PERMISSIONS,
  BUILT_IN_ROLES,
  Permission,
  PermissionAuditInfo,
  PermissionCache,
  PermissionContext,
  PermissionLevel,
  PermissionRequest,
  PermissionResult,
  PermissionStats,
  ResourceType,
  Role,
  SafetyLevel,
  SecurityPolicy,
  User,
  UserSession,
} from './permission-types.js';
import {
  PermissionError,
  SecurityViolationError,
  SessionStatus,
  UserStatus,
} from './permission-types.js';

export interface PermissionManagerConfig {
  enableCaching?: boolean;
  cacheMaxSize?: number;
  cacheTTL?: number;
  enableAuditing?: boolean;
  auditMaxEntries?: number;
  enableSafetyProtocols?: boolean;
  rateLimit?: {
    maxRequestsPerMinute: number;
    maxRequestsPerHour: number;
  };
  storage?: {
    type: 'memory' | 'database' | 'file';
    connectionString?: string;
    options?: Record<string, any>;
  };
}

/**
 * Advanced permission manager with Kenny Integration
 */
export class PermissionManager extends BaseSubsystem {
  private readonly permissions = new Map<string, Permission>();
  private readonly roles = new Map<string, Role>();
  private readonly users = new Map<string, User>();
  private readonly sessions = new Map<string, UserSession>();
  private readonly securityPolicies = new Map<string, SecurityPolicy>();

  private readonly permissionCache = new Map<string, PermissionCache>();
  private readonly auditLog: PermissionAuditInfo[] = [];
  private readonly stats: PermissionStats;

  private readonly safetyProtocols: SafetyProtocolManager;
  private readonly config: Required<PermissionManagerConfig>;

  private readonly rateLimitTracking = new Map<
    string,
    { count: number; resetTime: number }
  >();

  constructor(config: PermissionManagerConfig = {}) {
    super({
      id: 'permission-manager',
      name: 'Permission Manager',
      description: 'Advanced permission checking and management system',
      version: '1.0.0',
    });

    this.config = {
      enableCaching: config.enableCaching ?? true,
      cacheMaxSize: config.cacheMaxSize ?? 10000,
      cacheTTL: config.cacheTTL ?? 300000, // 5 minutes
      enableAuditing: config.enableAuditing ?? true,
      auditMaxEntries: config.auditMaxEntries ?? 100000,
      enableSafetyProtocols: config.enableSafetyProtocols ?? true,
      rateLimit: config.rateLimit ?? {
        maxRequestsPerMinute: 1000,
        maxRequestsPerHour: 10000,
      },
      storage: config.storage ?? {
        type: 'memory',
      },
    };

    this.safetyProtocols = new SafetyProtocolManager();
    this.stats = this.createEmptyStats();

    // Setup cleanup timers
    this.setupCleanupTimers();
  }

  /**
   * BaseSubsystem lifecycle methods
   */
  protected async onInitialize(config: Record<string, any>): Promise<void> {
    await this.initializeBuiltInData();

    // Initialize safety protocols if enabled
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.initialize();
    }

    // Setup storage if configured
    if (this.config.storage.type !== 'memory') {
      await this.initializeStorage();
    }

    this.emit('initialized', { config: this.config });
  }

  protected async onStart(): Promise<void> {
    // Start safety protocols
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.start();
    }
    this.emit('started');
  }

  protected async onStop(): Promise<void> {
    // Stop safety protocols
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.stop();
    }

    // Cleanup resources
    this.cleanup();
    this.emit('stopped');
  }

  async initialize(config: Record<string, any> = {}): Promise<void> {
    try {
      // Initialize built-in permissions and roles
      await this.initializeBuiltInData();

      // Initialize safety protocols if enabled
      if (this.config.enableSafetyProtocols) {
        await this.safetyProtocols.initialize();
      }

      // Setup storage if configured
      if (this.config.storage.type !== 'memory') {
        await this.initializeStorage();
      }

      // Status is managed by BaseSubsystem
      this.emit('initialized', { config: this.config });

      // Publish initialization event
      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('permission-manager.initialized', this.metadata.id, {
          permissionCount: this.permissions.size,
          roleCount: this.roles.size,
        });
    } catch (error) {
      // Error status is managed by BaseSubsystem
      throw error;
    }
  }

  async start(): Promise<void> {
    // Status is managed by BaseSubsystem
    this.emit('started');

    // Start safety protocols
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.start();
    }
  }

  async stop(): Promise<void> {
    // Stop safety protocols
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.stop();
    }

    // Status is managed by BaseSubsystem
    this.emit('stopped');
  }

  async shutdown(): Promise<void> {
    await this.stop();

    // Clear all data
    this.permissions.clear();
    this.roles.clear();
    this.users.clear();
    this.sessions.clear();
    this.securityPolicies.clear();
    this.permissionCache.clear();
    this.auditLog.length = 0;
    this.rateLimitTracking.clear();

    // Shutdown safety protocols
    if (this.config.enableSafetyProtocols) {
      await this.safetyProtocols.shutdown();
    }

    // Status is managed by BaseSubsystem
    this.emit('shutdown');
  }

  /**
   * Add a new permission
   */
  async addPermission(
    permission: Omit<Permission, 'createdAt' | 'updatedAt'>
  ): Promise<void> {
    const fullPermission: Permission = {
      ...permission,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.permissions.set(permission.id, fullPermission);

    // Clear related cache entries
    this.clearCacheForPermission(permission.id);

    // Publish event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('permission.added', this.metadata.id, {
        permissionId: permission.id,
        name: permission.name,
      });

    this.emit('permission.added', { permission: fullPermission });
  }

  /**
   * Add a new role
   */
  async addRole(role: Omit<Role, 'createdAt' | 'updatedAt'>): Promise<void> {
    // Validate role permissions exist
    for (const permissionId of role.permissions) {
      if (!this.permissions.has(permissionId)) {
        throw new PermissionError(
          `Permission ${permissionId} does not exist`,
          'INVALID_PERMISSION'
        );
      }
    }

    const fullRole: Role = {
      ...role,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.roles.set(role.id, fullRole);

    // Clear related cache entries
    this.clearCacheForRole(role.id);

    // Publish event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('role.added', this.metadata.id, {
        roleId: role.id,
        name: role.name,
        permissionCount: role.permissions.length,
      });

    this.emit('role.added', { role: fullRole });
  }

  /**
   * Create a new user
   */
  async createUser(
    userData: Omit<User, 'createdAt' | 'updatedAt' | 'sessions'>
  ): Promise<User> {
    // Validate roles exist
    for (const roleId of userData.roles) {
      if (!this.roles.has(roleId)) {
        throw new PermissionError(
          `Role ${roleId} does not exist`,
          'INVALID_ROLE'
        );
      }
    }

    const user: User = {
      ...userData,
      sessions: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    this.users.set(user.id, user);

    // Clear related cache entries
    this.clearCacheForUser(user.id);

    // Publish event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('user.created', this.metadata.id, {
        userId: user.id,
        username: user.username,
        roleCount: user.roles.length,
      });

    this.emit('user.created', { user });
    return user;
  }

  /**
   * Create a new session
   */
  async createSession(
    userId: string,
    sessionData: Omit<
      UserSession,
      'id' | 'userId' | 'startTime' | 'lastActivity'
    >
  ): Promise<UserSession> {
    const user = this.users.get(userId);
    if (!user) {
      throw new PermissionError(
        `User ${userId} does not exist`,
        'USER_NOT_FOUND'
      );
    }

    if (user.status !== UserStatus.ACTIVE) {
      throw new PermissionError(
        `User ${userId} is not active`,
        'USER_INACTIVE'
      );
    }

    // Check session limits
    const activeSessions = user.sessions.filter(
      s => s.status === SessionStatus.ACTIVE
    );
    const maxSessions = user.constraints?.maxSessions || 10;

    if (activeSessions.length >= maxSessions) {
      throw new PermissionError(
        `User ${userId} has reached maximum session limit`,
        'SESSION_LIMIT_EXCEEDED'
      );
    }

    const session: UserSession = {
      id: nanoid(),
      userId,
      startTime: new Date(),
      lastActivity: new Date(),
      status: SessionStatus.ACTIVE,
      ...sessionData,
    };

    // Add session to user
    user.sessions.push(session);
    this.sessions.set(session.id, session);

    // Clear user cache
    this.clearCacheForUser(userId);

    // Publish event
    const kenny = getKennyIntegration();
    await kenny
      .getMessageBus()
      .publishSubsystem('session.created', this.metadata.id, {
        sessionId: session.id,
        userId,
        ipAddress: session.ipAddress,
      });

    this.emit('session.created', { session });
    return session;
  }

  /**
   * Check permission for a given context
   */
  async checkPermission(request: PermissionRequest): Promise<PermissionResult> {
    const startTime = Date.now();
    const checkId = nanoid();

    try {
      // Rate limiting
      if (
        !this.checkRateLimit(
          request.context.userId || request.context.sessionId
        )
      ) {
        throw new SecurityViolationError(
          'Rate limit exceeded',
          'medium',
          request.context
        );
      }

      // Check cache first
      const cacheKey = this.generateCacheKey(request);
      if (this.config.enableCaching) {
        const cachedResult = this.getCachedResult(cacheKey);
        if (cachedResult) {
          this.stats.cacheHits++;
          return cachedResult.result;
        }
        this.stats.cacheMisses++;
      }

      // Get user and session
      const session = this.sessions.get(request.context.sessionId);
      const user = session ? this.users.get(session.userId) : undefined;

      // Perform permission check
      const result = await this.performPermissionCheck(request, user, session);

      // Update statistics
      this.updateStats(result);

      // Cache result if enabled
      if (this.config.enableCaching && result.granted) {
        this.cacheResult(cacheKey, result, request);
      }

      // Audit logging
      if (this.config.enableAuditing) {
        const auditInfo: PermissionAuditInfo = {
          checkId,
          userId: user?.id,
          sessionId: request.context.sessionId,
          resource: request.context.resource,
          operation: request.context.operation,
          permissionId: request.permissionId,
          result: result.granted ? 'granted' : 'denied',
          reason: result.reason,
          timestamp: new Date(),
          duration: Date.now() - startTime,
          ipAddress: request.context.ipAddress,
          userAgent: request.context.userAgent,
          metadata: request.context.metadata,
        };

        this.addAuditEntry(auditInfo);
        result.auditInfo = auditInfo;
      }

      // Safety protocol checks
      if (this.config.enableSafetyProtocols) {
        await this.safetyProtocols.checkPermissionRequest(request, result);
      }

      // Publish event
      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('permission.checked', this.metadata.id, {
          checkId,
          permissionId: request.permissionId,
          result: result.granted ? 'granted' : 'denied',
          userId: user?.id,
          duration: Date.now() - startTime,
        });

      this.emit('permission.checked', { request, result });

      return result;
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      const errorResult: PermissionResult = {
        granted: false,
        reason: `Permission check failed: ${errorMessage}`,
        auditInfo: {
          checkId,
          sessionId: request.context.sessionId,
          resource: request.context.resource,
          operation: request.context.operation,
          permissionId: request.permissionId,
          result: 'error',
          reason: errorMessage,
          timestamp: new Date(),
          duration: Date.now() - startTime,
        },
      };

      this.updateStats(errorResult);

      if (this.config.enableAuditing) {
        this.addAuditEntry(errorResult.auditInfo);
      }

      this.emit('permission.error', { request, error: errorMessage });

      if (error instanceof SecurityViolationError) {
        // Handle security violations specially
        const kenny = getKennyIntegration();
        await kenny
          .getMessageBus()
          .publishSubsystem('security.violation', this.metadata.id, {
            severity: error.severity,
            message: error.message,
            userId: request.context.userId,
            sessionId: request.context.sessionId,
            resource: request.context.resource,
          });
      }

      return errorResult;
    }
  }

  /**
   * Get user permissions (including role permissions)
   */
  async getUserPermissions(userId: string): Promise<Permission[]> {
    const user = this.users.get(userId);
    if (!user) {
      throw new PermissionError(
        `User ${userId} does not exist`,
        'USER_NOT_FOUND'
      );
    }

    const userPermissions = new Set<Permission>();

    // Add role permissions
    for (const roleId of user.roles) {
      const role = this.roles.get(roleId);
      if (role) {
        // Handle role inheritance
        const allRolePermissions = await this.getRolePermissions(role);
        for (const permission of allRolePermissions) {
          userPermissions.add(permission);
        }
      }
    }

    // Add direct permissions
    if (user.directPermissions) {
      for (const permissionId of user.directPermissions) {
        const permission = this.permissions.get(permissionId);
        if (permission) {
          userPermissions.add(permission);
        }
      }
    }

    return Array.from(userPermissions);
  }

  /**
   * Get permission statistics
   */
  getStats(): PermissionStats {
    return { ...this.stats };
  }

  /**
   * Get audit log entries
   */
  getAuditLog(filter?: {
    userId?: string;
    sessionId?: string;
    permissionId?: string;
    result?: 'granted' | 'denied' | 'error';
    startTime?: Date;
    endTime?: Date;
    limit?: number;
  }): PermissionAuditInfo[] {
    let filteredLog = this.auditLog;

    if (filter) {
      filteredLog = filteredLog.filter(entry => {
        if (filter.userId && entry.userId !== filter.userId) return false;
        if (filter.sessionId && entry.sessionId !== filter.sessionId)
          return false;
        if (filter.permissionId && entry.permissionId !== filter.permissionId)
          return false;
        if (filter.result && entry.result !== filter.result) return false;
        if (filter.startTime && entry.timestamp < filter.startTime)
          return false;
        if (filter.endTime && entry.timestamp > filter.endTime) return false;
        return true;
      });

      if (filter.limit) {
        filteredLog = filteredLog.slice(-filter.limit);
      }
    }

    return filteredLog;
  }

  /**
   * Health check for the permission manager
   */
  protected async onHealthCheck() {
    const activeUsers = Array.from(this.users.values()).filter(
      u => u.status === UserStatus.ACTIVE
    ).length;
    const activeSessions = Array.from(this.sessions.values()).filter(
      s => s.status === SessionStatus.ACTIVE
    ).length;
    const cacheSize = this.permissionCache.size;

    return {
      status: this.status === 'running' ? 'healthy' : ('unhealthy' as const),
      message: `${this.permissions.size} permissions, ${activeUsers} active users, ${activeSessions} active sessions`,
      details: {
        permissions: this.permissions.size,
        roles: this.roles.size,
        users: this.users.size,
        activeUsers,
        sessions: this.sessions.size,
        activeSessions,
        cacheSize,
        auditEntries: this.auditLog.length,
        stats: this.stats,
      },
    };
  }

  private async initializeBuiltInData(): Promise<void> {
    // Import built-in permissions and roles
    const { BUILT_IN_PERMISSIONS, BUILT_IN_ROLES } = await import(
      './permission-types.js'
    );

    // Add built-in permissions
    for (const permissionData of BUILT_IN_PERMISSIONS) {
      await this.addPermission(permissionData);
    }

    // Add built-in roles
    for (const roleData of BUILT_IN_ROLES) {
      await this.addRole(roleData);
    }
  }

  private async initializeStorage(): Promise<void> {
    // TODO: Implement database/file storage initialization
    console.log(
      `[PermissionManager] Storage type '${this.config.storage.type}' not yet implemented`
    );
  }

  private async performPermissionCheck(
    request: PermissionRequest,
    user?: User,
    session?: UserSession
  ): Promise<PermissionResult> {
    const permission = this.permissions.get(request.permissionId);
    if (!permission) {
      return {
        granted: false,
        reason: `Permission ${request.permissionId} does not exist`,
        auditInfo: {} as any, // Will be filled by caller
      };
    }

    // Check if user exists and is active
    if (!user || user.status !== UserStatus.ACTIVE) {
      return {
        granted: false,
        reason: user ? `User is ${user.status}` : 'User not found',
        auditInfo: {} as any,
      };
    }

    // Check session status
    if (!session || session.status !== SessionStatus.ACTIVE) {
      return {
        granted: false,
        reason: session ? `Session is ${session.status}` : 'Session not found',
        auditInfo: {} as any,
      };
    }

    // Update session activity
    session.lastActivity = new Date();

    // Check user permissions
    const userPermissions = await this.getUserPermissions(user.id);
    const hasPermission = userPermissions.some(
      p => p.id === request.permissionId
    );

    if (!hasPermission) {
      return {
        granted: false,
        reason: 'User does not have required permission',
        auditInfo: {} as any,
      };
    }

    // Check constraints
    const constraintResult = await this.checkConstraints(
      permission,
      request.context,
      user,
      session
    );
    if (!constraintResult.passed) {
      return {
        granted: false,
        reason: `Constraint violation: ${constraintResult.reason}`,
        constraints: permission.constraints,
        auditInfo: {} as any,
      };
    }

    // Check security policies
    const policyResult = await this.checkSecurityPolicies(
      request,
      user,
      session
    );
    if (!policyResult.allowed) {
      return {
        granted: false,
        reason: `Policy violation: ${policyResult.reason}`,
        warnings: policyResult.warnings,
        auditInfo: {} as any,
      };
    }

    return {
      granted: true,
      reason: 'Permission granted',
      constraints: permission.constraints,
      warnings: constraintResult.warnings,
      auditInfo: {} as any,
    };
  }

  private async checkConstraints(
    permission: Permission,
    context: PermissionContext,
    user: User,
    session: UserSession
  ): Promise<{ passed: boolean; reason?: string; warnings?: string[] }> {
    const warnings: string[] = [];

    if (!permission.constraints) {
      return { passed: true, warnings };
    }

    const constraints = permission.constraints;

    // Time restrictions
    if (constraints.timeRestrictions) {
      const now = new Date();
      const hour = now.getHours();
      const day = now.getDay();

      if (constraints.timeRestrictions.allowedHours) {
        const [start, end] = constraints.timeRestrictions.allowedHours;
        if (hour < start || hour > end) {
          return {
            passed: false,
            reason: `Access not allowed at this time (${hour}:xx)`,
          };
        }
      }

      if (constraints.timeRestrictions.allowedDays) {
        if (!constraints.timeRestrictions.allowedDays.includes(day)) {
          return { passed: false, reason: `Access not allowed on this day` };
        }
      }
    }

    // Rate limiting
    if (constraints.rateLimit) {
      const key = `${user.id}:${permission.id}`;
      const now = Date.now();
      const tracker = this.rateLimitTracking.get(key);

      if (tracker) {
        if (now < tracker.resetTime) {
          if (tracker.count >= constraints.rateLimit.maxRequests) {
            return { passed: false, reason: 'Rate limit exceeded' };
          }
        } else {
          // Reset window
          this.rateLimitTracking.set(key, {
            count: 1,
            resetTime: now + constraints.rateLimit.windowMs,
          });
        }
      } else {
        this.rateLimitTracking.set(key, {
          count: 1,
          resetTime: now + constraints.rateLimit.windowMs,
        });
      }
    }

    // IP restrictions
    if (constraints.ipRestrictions && context.ipAddress) {
      const ip = context.ipAddress;

      if (constraints.ipRestrictions.blockedIPs?.includes(ip)) {
        return { passed: false, reason: 'IP address is blocked' };
      }

      if (
        constraints.ipRestrictions.allowedIPs &&
        !constraints.ipRestrictions.allowedIPs.includes(ip)
      ) {
        return { passed: false, reason: 'IP address not in allowed list' };
      }
    }

    return { passed: true, warnings };
  }

  private async checkSecurityPolicies(
    request: PermissionRequest,
    user: User,
    session: UserSession
  ): Promise<{ allowed: boolean; reason?: string; warnings?: string[] }> {
    // TODO: Implement security policy checking
    return { allowed: true };
  }

  private async getRolePermissions(role: Role): Promise<Permission[]> {
    const permissions = new Set<Permission>();

    // Add direct permissions
    for (const permissionId of role.permissions) {
      const permission = this.permissions.get(permissionId);
      if (permission) {
        permissions.add(permission);
      }
    }

    // Handle inheritance
    if (role.inheritsFrom) {
      for (const inheritedRoleId of role.inheritsFrom) {
        const inheritedRole = this.roles.get(inheritedRoleId);
        if (inheritedRole) {
          const inheritedPermissions =
            await this.getRolePermissions(inheritedRole);
          for (const permission of inheritedPermissions) {
            permissions.add(permission);
          }
        }
      }
    }

    return Array.from(permissions);
  }

  private generateCacheKey(request: PermissionRequest): string {
    return `${request.context.userId || request.context.sessionId}:${request.permissionId}:${request.context.resource}:${request.context.operation}`;
  }

  private getCachedResult(key: string): PermissionCache | null {
    const cached = this.permissionCache.get(key);
    if (cached && cached.expiresAt > new Date()) {
      cached.hitCount++;
      return cached;
    }
    if (cached) {
      this.permissionCache.delete(key);
    }
    return null;
  }

  private cacheResult(
    key: string,
    result: PermissionResult,
    request: PermissionRequest
  ): void {
    if (this.permissionCache.size >= this.config.cacheMaxSize) {
      // Remove oldest entries
      const entries = Array.from(this.permissionCache.entries());
      entries.sort(
        (a, b) => a[1].createdAt.getTime() - b[1].createdAt.getTime()
      );
      const toRemove = entries.slice(
        0,
        Math.floor(this.config.cacheMaxSize * 0.1)
      );
      for (const [k] of toRemove) {
        this.permissionCache.delete(k);
      }
    }

    const cacheEntry: PermissionCache = {
      key,
      userId: request.context.userId,
      sessionId: request.context.sessionId,
      permissionId: request.permissionId,
      result,
      createdAt: new Date(),
      expiresAt: new Date(Date.now() + this.config.cacheTTL),
      hitCount: 0,
      metadata: request.context.metadata,
    };

    this.permissionCache.set(key, cacheEntry);
  }

  private checkRateLimit(identifier: string): boolean {
    const now = Date.now();
    const minuteKey = `${identifier}:minute`;
    const hourKey = `${identifier}:hour`;

    // Check minute limit
    const minuteTracker = this.rateLimitTracking.get(minuteKey);
    if (minuteTracker) {
      if (now < minuteTracker.resetTime) {
        if (minuteTracker.count >= this.config.rateLimit.maxRequestsPerMinute) {
          return false;
        }
        minuteTracker.count++;
      } else {
        this.rateLimitTracking.set(minuteKey, {
          count: 1,
          resetTime: now + 60000,
        });
      }
    } else {
      this.rateLimitTracking.set(minuteKey, {
        count: 1,
        resetTime: now + 60000,
      });
    }

    // Check hour limit
    const hourTracker = this.rateLimitTracking.get(hourKey);
    if (hourTracker) {
      if (now < hourTracker.resetTime) {
        if (hourTracker.count >= this.config.rateLimit.maxRequestsPerHour) {
          return false;
        }
        hourTracker.count++;
      } else {
        this.rateLimitTracking.set(hourKey, {
          count: 1,
          resetTime: now + 3600000,
        });
      }
    } else {
      this.rateLimitTracking.set(hourKey, {
        count: 1,
        resetTime: now + 3600000,
      });
    }

    return true;
  }

  private addAuditEntry(entry: PermissionAuditInfo): void {
    this.auditLog.push(entry);

    if (this.auditLog.length > this.config.auditMaxEntries) {
      this.auditLog.shift();
    }
  }

  private updateStats(result: PermissionResult): void {
    this.stats.totalChecks++;

    if (result.granted) {
      this.stats.grantedCount++;
    } else {
      this.stats.deniedCount++;
    }

    if (result.auditInfo && result.auditInfo.result === 'error') {
      this.stats.errorCount++;
    }

    // Update average check duration
    if (result.auditInfo) {
      const totalTime =
        this.stats.averageCheckDuration * (this.stats.totalChecks - 1) +
        result.auditInfo.duration;
      this.stats.averageCheckDuration = totalTime / this.stats.totalChecks;
    }
  }

  private clearCacheForPermission(permissionId: string): void {
    const keysToRemove = Array.from(this.permissionCache.keys()).filter(key =>
      key.includes(permissionId)
    );
    keysToRemove.forEach(key => this.permissionCache.delete(key));
  }

  private clearCacheForRole(roleId: string): void {
    // Clear cache for users with this role
    const usersWithRole = Array.from(this.users.values()).filter(user =>
      user.roles.includes(roleId)
    );
    usersWithRole.forEach(user => this.clearCacheForUser(user.id));
  }

  private clearCacheForUser(userId: string): void {
    const keysToRemove = Array.from(this.permissionCache.keys()).filter(key =>
      key.startsWith(userId)
    );
    keysToRemove.forEach(key => this.permissionCache.delete(key));
  }

  private createEmptyStats(): PermissionStats {
    return {
      totalChecks: 0,
      grantedCount: 0,
      deniedCount: 0,
      errorCount: 0,
      cacheHits: 0,
      cacheMisses: 0,
      averageCheckDuration: 0,
      topPermissions: [],
      topUsers: [],
      timeRange: {
        start: new Date(),
        end: new Date(),
      },
    };
  }

  private setupCleanupTimers(): void {
    // Clean up expired cache entries every 5 minutes
    setInterval(() => {
      const now = new Date();
      const keysToRemove: string[] = [];

      for (const [key, entry] of this.permissionCache.entries()) {
        if (entry.expiresAt <= now) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach(key => this.permissionCache.delete(key));
    }, 300000);

    // Clean up rate limit tracking every hour
    setInterval(() => {
      const now = Date.now();
      const keysToRemove: string[] = [];

      for (const [key, tracker] of this.rateLimitTracking.entries()) {
        if (tracker.resetTime <= now) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach(key => this.rateLimitTracking.delete(key));
    }, 3600000);
  }

  // Legacy compatibility methods
  async assignRole(userId: string, roleId: string): Promise<void> {
    const user = this.users.get(userId);
    if (!user) {
      throw new PermissionError(
        `User ${userId} does not exist`,
        'USER_NOT_FOUND'
      );
    }

    if (!this.roles.has(roleId)) {
      throw new PermissionError(
        `Role ${roleId} does not exist`,
        'ROLE_NOT_FOUND'
      );
    }

    if (!user.roles.includes(roleId)) {
      user.roles.push(roleId);
      user.updatedAt = new Date();
      this.clearCacheForUser(userId);

      const kenny = getKennyIntegration();
      await kenny
        .getMessageBus()
        .publishSubsystem('role.assigned', this.metadata.id, {
          userId,
          roleId,
        });

      this.emit('role.assigned', { userId, roleId });
    }
  }

  async cleanup(): Promise<void> {
    await this.shutdown();
  }
}

/**
 * Factory function to create a permission manager
 */
export function createPermissionManager(
  config?: PermissionManagerConfig
): PermissionManager {
  return new PermissionManager(config);
}
