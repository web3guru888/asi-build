/**
 * Database Type Definitions
 *
 * Comprehensive type definitions for the ASI-Code database layer.
 */

import { Knex } from 'knex';

// Base database configuration
export interface DatabaseConfig {
  // Primary database connection
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;

  // Connection pool settings
  pool: {
    min: number;
    max: number;
    acquireTimeoutMillis: number;
    createTimeoutMillis: number;
    destroyTimeoutMillis: number;
    idleTimeoutMillis: number;
    reapIntervalMillis: number;
    createRetryIntervalMillis: number;
  };

  // Connection retry logic
  retry: {
    maxAttempts: number;
    initialDelayMs: number;
    maxDelayMs: number;
    exponentialBackoff: boolean;
  };

  // Read replicas for read/write splitting
  readReplicas?: Array<{
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    weight?: number; // Load balancing weight
  }>;

  // SSL configuration
  ssl?: {
    enabled: boolean;
    rejectUnauthorized?: boolean;
    ca?: string;
    cert?: string;
    key?: string;
  };

  // Migration settings
  migrations: {
    directory: string;
    tableName: string;
    schemaName?: string;
    extension: string;
    loadExtensions: string[];
    disableTransactions: boolean;
    sortDirsSeparately: boolean;
  };

  // Seeding settings
  seeds: {
    directory: string;
    loadExtensions: string[];
    recursive: boolean;
  };

  // Audit logging configuration
  audit: {
    enabled: boolean;
    tableName: string;
    trackChanges: boolean;
    trackDeletes: boolean;
    excludeTables: string[];
  };

  // Soft delete configuration
  softDelete: {
    enabled: boolean;
    columnName: string;
    defaultValue: null;
    deletedValue: Date | string | number;
  };

  // Performance monitoring
  monitoring: {
    enabled: boolean;
    slowQueryThreshold: number; // milliseconds
    logQueries: boolean;
    trackMetrics: boolean;
  };

  // Backup configuration
  backup: {
    enabled: boolean;
    schedule: string; // cron expression
    retention: number; // days
    location: string;
    compression: boolean;
  };

  // Cleanup jobs configuration
  cleanup: {
    enabled: boolean;
    schedule: string; // cron expression
    retentionPeriods: {
      [tableName: string]: number; // days
    };
  };
}

// Query types
export type QueryType =
  | 'SELECT'
  | 'INSERT'
  | 'UPDATE'
  | 'DELETE'
  | 'DDL'
  | 'OTHER';

export interface QueryMetrics {
  query: string;
  type: QueryType;
  executionTime: number;
  rowsAffected?: number;
  timestamp: Date;
  success: boolean;
  error?: string;
}

// Transaction types
export interface TransactionOptions {
  isolationLevel?:
    | 'READ_UNCOMMITTED'
    | 'READ_COMMITTED'
    | 'REPEATABLE_READ'
    | 'SERIALIZABLE';
  timeout?: number; // milliseconds
  readOnly?: boolean;
}

export interface TransactionContext {
  id: string;
  startTime: Date;
  queries: QueryMetrics[];
  options: TransactionOptions;
}

// Migration types
export interface MigrationInfo {
  id: string;
  name: string;
  filename: string;
  version: string;
  executedAt?: Date;
  executionTime?: number;
  checksum: string;
  success?: boolean;
  error?: string;
}

export interface MigrationStatus {
  currentVersion: string;
  pendingMigrations: MigrationInfo[];
  appliedMigrations: MigrationInfo[];
  pendingCount: number;
  appliedCount: number;
}

// Seeding types
export interface SeedInfo {
  id: string;
  name: string;
  filename: string;
  executedAt?: Date;
  executionTime?: number;
  success?: boolean;
  error?: string;
}

// Audit logging types
export interface AuditLogEntry {
  id: string;
  tableName: string;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  recordId: string | number;
  oldValues?: Record<string, any>;
  newValues?: Record<string, any>;
  changedFields?: string[];
  userId?: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

// Soft delete types
export interface SoftDeleteOptions {
  force?: boolean; // Hard delete
  restore?: boolean; // Restore soft deleted record
}

export interface SoftDeleteQuery {
  includeDeleted?: boolean;
  onlyDeleted?: boolean;
}

// Health check types
export interface HealthCheckResult {
  status: 'healthy' | 'degraded' | 'unhealthy';
  responseTime: number;
  timestamp: Date;
  details?: {
    connection: boolean;
    queries: boolean;
    replication?: boolean;
    diskSpace?: number;
    activeConnections?: number;
    maxConnections?: number;
  };
}

// Backup types
export interface BackupInfo {
  id: string;
  filename: string;
  size: number;
  createdAt: Date;
  type: 'full' | 'incremental';
  compressed: boolean;
  checksum: string;
  metadata?: Record<string, any>;
}

export interface BackupOptions {
  type: 'full' | 'incremental';
  compression: boolean;
  excludeTables?: string[];
  includeTables?: string[];
  schemaOnly?: boolean;
  dataOnly?: boolean;
}

// Index types
export interface IndexInfo {
  name: string;
  tableName: string;
  columns: string[];
  unique: boolean;
  type: 'btree' | 'hash' | 'gin' | 'gist' | 'spgist' | 'brin';
  condition?: string;
  size?: number;
  usage?: {
    scans: number;
    tuples: number;
    lastUsed?: Date;
  };
}

// Performance monitoring types
export interface PerformanceMetrics {
  connectionPool: {
    active: number;
    idle: number;
    waiting: number;
    max: number;
  };
  queries: {
    total: number;
    successful: number;
    failed: number;
    averageExecutionTime: number;
    slowQueries: number;
  };
  transactions: {
    active: number;
    committed: number;
    rolledBack: number;
    deadlocks: number;
  };
  replication?: {
    lag: number; // milliseconds
    status: 'active' | 'inactive' | 'error';
  };
}

// Query builder types
export interface QueryBuilderOptions {
  table: string;
  schema?: string;
  softDelete?: SoftDeleteQuery;
  audit?: boolean;
  timeout?: number;
}

// Database adapter interface
export interface DatabaseAdapter {
  knex: Knex;
  config: DatabaseConfig;

  // Connection management
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  isConnected(): boolean;

  // Query execution
  query(sql: string, params?: any[]): Promise<any>;
  transaction<T>(callback: (trx: Knex.Transaction) => Promise<T>): Promise<T>;

  // Health checks
  healthCheck(): Promise<boolean>;
  getMetrics(): Promise<PerformanceMetrics>;

  // Schema operations
  hasTable(tableName: string): Promise<boolean>;
  hasColumn(tableName: string, columnName: string): Promise<boolean>;
  getTableInfo(tableName: string): Promise<any>;

  // Utility methods
  escape(value: any): string;
  escapeIdentifier(identifier: string): string;
}

// Event types
export interface DatabaseEvent {
  type: 'query' | 'transaction' | 'migration' | 'backup' | 'error' | 'health';
  timestamp: Date;
  data: any;
  metadata?: Record<string, any>;
}

// Error types
export class DatabaseError extends Error {
  public readonly code: string;
  public readonly query?: string;
  public readonly params?: any[];

  constructor(message: string, code: string, query?: string, params?: any[]) {
    super(message);
    this.name = 'DatabaseError';
    this.code = code;
    this.query = query;
    this.params = params;
  }
}

export class ConnectionError extends DatabaseError {
  constructor(message: string, originalError?: Error) {
    super(message, 'CONNECTION_ERROR');
    this.stack = originalError?.stack;
  }
}

export class QueryError extends DatabaseError {
  constructor(
    message: string,
    query: string,
    params?: any[],
    originalError?: Error
  ) {
    super(message, 'QUERY_ERROR', query, params);
    this.stack = originalError?.stack;
  }
}

export class TransactionError extends DatabaseError {
  constructor(message: string, originalError?: Error) {
    super(message, 'TRANSACTION_ERROR');
    this.stack = originalError?.stack;
  }
}

export class MigrationError extends DatabaseError {
  public readonly migrationName: string;

  constructor(message: string, migrationName: string, originalError?: Error) {
    super(message, 'MIGRATION_ERROR');
    this.migrationName = migrationName;
    this.stack = originalError?.stack;
  }
}

// Table schema types for type safety
export interface BaseTableSchema {
  id: string;
  created_at: Date;
  updated_at: Date;
  deleted_at?: Date | null;
}

export interface UserTableSchema extends BaseTableSchema {
  username: string;
  email: string;
  password_hash: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  last_login?: Date;
  metadata?: Record<string, any>;
}

export interface SessionTableSchema extends BaseTableSchema {
  user_id: string;
  session_token: string;
  expires_at: Date;
  ip_address?: string;
  user_agent?: string;
  metadata?: Record<string, any>;
}

export interface AuditLogTableSchema extends BaseTableSchema {
  table_name: string;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  record_id: string;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  changed_fields?: string[];
  user_id?: string;
  metadata?: Record<string, any>;
}
