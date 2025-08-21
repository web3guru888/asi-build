/**
 * Permission Types - Comprehensive type definitions for the permission system
 * 
 * Defines all types, interfaces, and enums used throughout the permission
 * and security system in ASI-Code.
 */

export enum PermissionLevel {
  READ = 'read',
  WRITE = 'write',
  EXECUTE = 'execute',
  ADMIN = 'admin',
  SUPER_ADMIN = 'super_admin'
}

export enum SafetyLevel {
  SAFE = 'safe',
  LOW_RISK = 'low-risk',
  MODERATE = 'moderate',
  HIGH_RISK = 'high-risk',
  DANGEROUS = 'dangerous',
  CRITICAL = 'critical'
}

export enum ResourceType {
  FILE = 'file',
  DIRECTORY = 'directory',
  NETWORK = 'network',
  SYSTEM = 'system',
  DATABASE = 'database',
  API = 'api',
  TOOL = 'tool',
  SESSION = 'session',
  USER = 'user',
  CONFIGURATION = 'configuration'
}

export interface Permission {
  id: string;
  name: string;
  description: string;
  category: string;
  level: PermissionLevel;
  safetyLevel: SafetyLevel;
  resourceType: ResourceType;
  scope?: string[];
  constraints?: PermissionConstraints;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  version: string;
}

export interface PermissionConstraints {
  timeRestrictions?: {
    allowedHours?: [number, number]; // [start, end] in 24-hour format
    allowedDays?: number[]; // 0-6, Sunday to Saturday
    timezone?: string;
  };
  rateLimit?: {
    maxRequests: number;
    windowMs: number;
    resetOnWindowEnd?: boolean;
  };
  ipRestrictions?: {
    allowedIPs?: string[];
    blockedIPs?: string[];
    allowedCIDR?: string[];
    blockedCIDR?: string[];
  };
  pathRestrictions?: {
    allowedPaths?: string[];
    blockedPaths?: string[];
    pathPatterns?: string[];
    caseSensitive?: boolean;
  };
  sizeRestrictions?: {
    maxFileSize?: number;
    maxTotalSize?: number;
    maxItems?: number;
  };
  contentRestrictions?: {
    allowedExtensions?: string[];
    blockedExtensions?: string[];
    allowedMimeTypes?: string[];
    blockedMimeTypes?: string[];
    scanContent?: boolean;
  };
  sessionRestrictions?: {
    maxSessionDuration?: number;
    maxConcurrentSessions?: number;
    requireReauth?: boolean;
    idleTimeout?: number;
  };
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  inheritsFrom?: string[];
  safetyLevel: SafetyLevel;
  isBuiltIn: boolean;
  constraints?: RoleConstraints;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  version: string;
}

export interface RoleConstraints {
  maxUsers?: number;
  requireApproval?: boolean;
  autoExpire?: {
    enabled: boolean;
    duration: number; // in milliseconds
    warningPeriod?: number; // warn before expiration
  };
  escalationRequired?: {
    permissions: string[];
    approvers: string[];
    timeout: number;
  };
}

export interface User {
  id: string;
  username: string;
  email?: string;
  displayName?: string;
  roles: string[];
  directPermissions?: string[];
  safetyLevel: SafetyLevel;
  status: UserStatus;
  profile?: UserProfile;
  constraints?: UserConstraints;
  sessions: UserSession[];
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt?: Date;
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING_APPROVAL = 'pending_approval',
  LOCKED = 'locked',
  ARCHIVED = 'archived'
}

export interface UserProfile {
  department?: string;
  team?: string;
  manager?: string;
  location?: string;
  timezone?: string;
  preferences?: Record<string, any>;
  tags?: string[];
}

export interface UserConstraints {
  maxSessions?: number;
  sessionTimeout?: number;
  requireMFA?: boolean;
  passwordPolicy?: {
    minLength: number;
    requireUppercase: boolean;
    requireLowercase: boolean;
    requireNumbers: boolean;
    requireSymbols: boolean;
    maxAge: number; // in days
  };
  accessSchedule?: {
    allowedDays: number[];
    allowedHours: [number, number];
    timezone: string;
  };
}

export interface UserSession {
  id: string;
  userId: string;
  startTime: Date;
  lastActivity: Date;
  ipAddress?: string;
  userAgent?: string;
  location?: string;
  status: SessionStatus;
  permissions?: string[];
  constraints?: SessionConstraints;
  metadata?: Record<string, any>;
}

export enum SessionStatus {
  ACTIVE = 'active',
  IDLE = 'idle',
  EXPIRED = 'expired',
  TERMINATED = 'terminated',
  SUSPENDED = 'suspended'
}

export interface SessionConstraints {
  maxDuration?: number;
  idleTimeout?: number;
  requireReauth?: string[]; // permissions requiring re-authentication
  elevatedUntil?: Date; // temporary elevation expiry
}

export interface PermissionContext {
  userId?: string;
  sessionId: string;
  resource: string;
  operation: string;
  resourceType: ResourceType;
  ipAddress?: string;
  userAgent?: string;
  timestamp: Date;
  metadata?: Record<string, any>;
  requestId?: string;
  parentContext?: string; // for nested operations
}

export interface PermissionRequest {
  context: PermissionContext;
  permissionId: string;
  justification?: string;
  urgency?: 'low' | 'medium' | 'high' | 'critical';
  temporaryElevation?: {
    duration: number;
    reason: string;
    approver?: string;
  };
}

export interface PermissionResult {
  granted: boolean;
  reason?: string;
  constraints?: PermissionConstraints;
  warnings?: string[];
  auditInfo: PermissionAuditInfo;
  temporaryElevation?: {
    granted: boolean;
    expiresAt?: Date;
    restrictions?: string[];
  };
}

export interface PermissionAuditInfo {
  checkId: string;
  userId?: string;
  sessionId: string;
  resource: string;
  operation: string;
  permissionId: string;
  result: 'granted' | 'denied' | 'error';
  reason?: string;
  timestamp: Date;
  duration: number; // check duration in milliseconds
  ipAddress?: string;
  userAgent?: string;
  metadata?: Record<string, any>;
}

export interface SecurityPolicy {
  id: string;
  name: string;
  description: string;
  rules: SecurityRule[];
  priority: number;
  enabled: boolean;
  safetyLevel: SafetyLevel;
  scope: SecurityScope;
  enforcement: EnforcementLevel;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  version: string;
}

export interface SecurityRule {
  id: string;
  name: string;
  condition: RuleCondition;
  action: RuleAction;
  priority: number;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface RuleCondition {
  type: 'permission' | 'role' | 'user' | 'resource' | 'time' | 'rate' | 'content' | 'custom';
  field?: string;
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'regex' | 'greater_than' | 'less_than' | 'in' | 'not_in';
  value: any;
  caseSensitive?: boolean;
  negate?: boolean;
}

export interface RuleAction {
  type: 'allow' | 'deny' | 'require_approval' | 'log_warning' | 'rate_limit' | 'elevate' | 'custom';
  parameters?: Record<string, any>;
  message?: string;
  severity?: 'info' | 'warning' | 'error' | 'critical';
}

export interface SecurityScope {
  users?: string[];
  roles?: string[];
  resources?: string[];
  resourceTypes?: ResourceType[];
  operations?: string[];
  timeRange?: {
    start?: Date;
    end?: Date;
  };
}

export enum EnforcementLevel {
  ADVISORY = 'advisory',
  WARNING = 'warning',
  BLOCKING = 'blocking',
  CRITICAL = 'critical'
}

export interface SafetyProtocol {
  id: string;
  name: string;
  description: string;
  safetyLevel: SafetyLevel;
  triggers: SafetyTrigger[];
  actions: SafetyAction[];
  enabled: boolean;
  priority: number;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface SafetyTrigger {
  type: 'permission_escalation' | 'multiple_failures' | 'suspicious_pattern' | 'resource_threshold' | 'time_anomaly' | 'custom';
  conditions: RuleCondition[];
  threshold?: number;
  timeWindow?: number;
  enabled: boolean;
}

export interface SafetyAction {
  type: 'block_user' | 'suspend_session' | 'require_approval' | 'notify_admin' | 'log_incident' | 'rate_limit' | 'custom';
  parameters?: Record<string, any>;
  priority: number;
  enabled: boolean;
}

export interface PermissionCache {
  key: string;
  userId?: string;
  sessionId: string;
  permissionId: string;
  result: PermissionResult;
  createdAt: Date;
  expiresAt: Date;
  hitCount: number;
  metadata?: Record<string, any>;
}

export interface PermissionStats {
  totalChecks: number;
  grantedCount: number;
  deniedCount: number;
  errorCount: number;
  cacheHits: number;
  cacheMisses: number;
  averageCheckDuration: number;
  topPermissions: Array<{
    permissionId: string;
    count: number;
    grantedRate: number;
  }>;
  topUsers: Array<{
    userId: string;
    checkCount: number;
    grantedRate: number;
  }>;
  timeRange: {
    start: Date;
    end: Date;
  };
}

// Built-in permission definitions
export const BUILT_IN_PERMISSIONS: Readonly<Omit<Permission, 'createdAt' | 'updatedAt'>[]> = [
  {
    id: 'read_files',
    name: 'Read Files',
    description: 'Read file contents and metadata',
    category: 'file',
    level: PermissionLevel.READ,
    safetyLevel: SafetyLevel.SAFE,
    resourceType: ResourceType.FILE,
    version: '1.0.0'
  },
  {
    id: 'write_files',
    name: 'Write Files',
    description: 'Create, modify, and delete files',
    category: 'file',
    level: PermissionLevel.WRITE,
    safetyLevel: SafetyLevel.MODERATE,
    resourceType: ResourceType.FILE,
    version: '1.0.0'
  },
  {
    id: 'execute_commands',
    name: 'Execute Commands',
    description: 'Execute system commands and scripts',
    category: 'system',
    level: PermissionLevel.EXECUTE,
    safetyLevel: SafetyLevel.HIGH_RISK,
    resourceType: ResourceType.SYSTEM,
    version: '1.0.0'
  },
  {
    id: 'manage_users',
    name: 'Manage Users',
    description: 'Create, modify, and delete user accounts',
    category: 'user',
    level: PermissionLevel.ADMIN,
    safetyLevel: SafetyLevel.HIGH_RISK,
    resourceType: ResourceType.USER,
    version: '1.0.0'
  },
  {
    id: 'manage_permissions',
    name: 'Manage Permissions',
    description: 'Create, modify, and assign permissions and roles',
    category: 'security',
    level: PermissionLevel.ADMIN,
    safetyLevel: SafetyLevel.DANGEROUS,
    resourceType: ResourceType.CONFIGURATION,
    version: '1.0.0'
  },
  {
    id: 'network_access',
    name: 'Network Access',
    description: 'Make network requests and connections',
    category: 'network',
    level: PermissionLevel.EXECUTE,
    safetyLevel: SafetyLevel.MODERATE,
    resourceType: ResourceType.NETWORK,
    version: '1.0.0'
  },
  {
    id: 'tool_execution',
    name: 'Tool Execution',
    description: 'Execute tools and utilities',
    category: 'tool',
    level: PermissionLevel.EXECUTE,
    safetyLevel: SafetyLevel.MODERATE,
    resourceType: ResourceType.TOOL,
    version: '1.0.0'
  },
  {
    id: 'dangerous_operations',
    name: 'Dangerous Operations',
    description: 'Perform potentially dangerous system operations',
    category: 'system',
    level: PermissionLevel.ADMIN,
    safetyLevel: SafetyLevel.DANGEROUS,
    resourceType: ResourceType.SYSTEM,
    version: '1.0.0'
  }
];

// Built-in role definitions
export const BUILT_IN_ROLES: Readonly<Omit<Role, 'createdAt' | 'updatedAt'>[]> = [
  {
    id: 'guest',
    name: 'Guest',
    description: 'Limited access for unauthenticated users',
    permissions: [],
    safetyLevel: SafetyLevel.SAFE,
    isBuiltIn: true,
    version: '1.0.0'
  },
  {
    id: 'user',
    name: 'User',
    description: 'Basic user with read access',
    permissions: ['read_files'],
    safetyLevel: SafetyLevel.SAFE,
    isBuiltIn: true,
    version: '1.0.0'
  },
  {
    id: 'developer',
    name: 'Developer',
    description: 'Developer with file and tool access',
    permissions: ['read_files', 'write_files', 'tool_execution'],
    safetyLevel: SafetyLevel.MODERATE,
    isBuiltIn: true,
    version: '1.0.0'
  },
  {
    id: 'power_user',
    name: 'Power User',
    description: 'Advanced user with system access',
    permissions: ['read_files', 'write_files', 'tool_execution', 'execute_commands', 'network_access'],
    safetyLevel: SafetyLevel.HIGH_RISK,
    isBuiltIn: true,
    version: '1.0.0'
  },
  {
    id: 'admin',
    name: 'Administrator',
    description: 'System administrator with full access',
    permissions: ['read_files', 'write_files', 'tool_execution', 'execute_commands', 'network_access', 'manage_users', 'dangerous_operations'],
    safetyLevel: SafetyLevel.DANGEROUS,
    isBuiltIn: true,
    version: '1.0.0'
  },
  {
    id: 'super_admin',
    name: 'Super Administrator',
    description: 'Super administrator with unrestricted access',
    permissions: ['read_files', 'write_files', 'tool_execution', 'execute_commands', 'network_access', 'manage_users', 'manage_permissions', 'dangerous_operations'],
    safetyLevel: SafetyLevel.CRITICAL,
    isBuiltIn: true,
    version: '1.0.0'
  }
];

// Error types
export class PermissionError extends Error {
  constructor(
    message: string,
    public code: string,
    public context?: PermissionContext,
    public metadata?: Record<string, any>
  ) {
    super(message);
    this.name = 'PermissionError';
  }
}

export class SecurityViolationError extends PermissionError {
  constructor(
    message: string,
    public severity: 'low' | 'medium' | 'high' | 'critical',
    context?: PermissionContext,
    metadata?: Record<string, any>
  ) {
    super(message, 'SECURITY_VIOLATION', context, metadata);
    this.name = 'SecurityViolationError';
  }
}

export class SafetyProtocolViolationError extends PermissionError {
  constructor(
    message: string,
    public protocol: string,
    context?: PermissionContext,
    metadata?: Record<string, any>
  ) {
    super(message, 'SAFETY_VIOLATION', context, metadata);
    this.name = 'SafetyProtocolViolationError';
  }
}