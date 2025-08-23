/**
 * Audit Logging System
 *
 * Provides comprehensive audit trail functionality with:
 * - Automatic change tracking for all tables
 * - Before/after value capture
 * - User context tracking
 * - Operation metadata
 * - Configurable audit levels
 * - Efficient storage and querying
 * - Data retention management
 * - Compliance reporting
 */

import { Knex } from 'knex';
import { nanoid } from 'nanoid';
import { AuditLogEntry, DatabaseAdapter } from '../types';
import { Logger } from '../../logging';

export interface AuditConfig {
  enabled: boolean;
  tableName: string;
  trackChanges: boolean;
  trackDeletes: boolean;
  excludeTables: string[];
  retentionDays: number;
  compressOldEntries: boolean;
  batchSize: number;
  maxFieldLength: number;
}

export interface AuditContext {
  userId?: string;
  userAgent?: string;
  ipAddress?: string;
  sessionId?: string;
  requestId?: string;
  source?: string;
  metadata?: Record<string, any>;
}

export interface AuditQueryOptions {
  tableName?: string;
  operation?: 'INSERT' | 'UPDATE' | 'DELETE';
  userId?: string;
  dateRange?: {
    from: Date;
    to: Date;
  };
  recordId?: string | number;
  limit?: number;
  offset?: number;
}

export interface AuditStatistics {
  totalEntries: number;
  entriesByOperation: { [operation: string]: number };
  entriesByTable: { [table: string]: number };
  entriesByUser: { [userId: string]: number };
  oldestEntry?: Date;
  newestEntry?: Date;
  averageEntriesPerDay: number;
  storageSize: number;
}

export class AuditLogger {
  private readonly adapter: DatabaseAdapter;
  private readonly logger: Logger;
  private readonly config: AuditConfig;
  private context: AuditContext = {};
  private readonly triggerCache = new Map<string, boolean>();
  private pendingEntries: AuditLogEntry[] = [];
  private flushInterval?: NodeJS.Timeout;

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
    this.config = {
      enabled: adapter.config.audit.enabled,
      tableName: adapter.config.audit.tableName || 'audit_log',
      trackChanges: adapter.config.audit.trackChanges,
      trackDeletes: adapter.config.audit.trackDeletes,
      excludeTables: adapter.config.audit.excludeTables || [],
      retentionDays: 365, // 1 year default
      compressOldEntries: true,
      batchSize: 1000,
      maxFieldLength: 10000,
    };
  }

  /**
   * Initialize audit logging system
   */
  async initialize(): Promise<void> {
    if (!this.config.enabled) {
      this.logger.info('Audit logging is disabled');
      return;
    }

    try {
      this.logger.info('Initializing audit logging system');

      // Create audit log table
      await this.createAuditTable();

      // Create audit triggers for all tables
      await this.createAuditTriggers();

      // Start batch processing
      this.startBatchProcessing();

      this.logger.info('Audit logging system initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize audit logging system', { error });
      throw error;
    }
  }

  /**
   * Create audit log table
   */
  private async createAuditTable(): Promise<void> {
    const hasTable = await this.adapter.hasTable(this.config.tableName);

    if (!hasTable) {
      await this.adapter.knex.schema.createTable(
        this.config.tableName,
        table => {
          table
            .uuid('id')
            .primary()
            .defaultTo(this.adapter.knex.raw('gen_random_uuid()'));
          table.string('table_name', 100).notNullable();
          table.enum('operation', ['INSERT', 'UPDATE', 'DELETE']).notNullable();
          table.string('record_id', 100).notNullable();
          table.jsonb('old_values').nullable();
          table.jsonb('new_values').nullable();
          table.specificType('changed_fields', 'text[]').nullable();
          table.string('user_id', 100).nullable();
          table.string('user_agent', 500).nullable();
          table.string('ip_address', 45).nullable();
          table.string('session_id', 100).nullable();
          table.string('request_id', 100).nullable();
          table.string('source', 100).nullable();
          table
            .timestamp('timestamp')
            .defaultTo(this.adapter.knex.fn.now())
            .notNullable();
          table.jsonb('metadata').nullable();
          table.boolean('compressed').defaultTo(false);
          table.text('checksum').nullable();

          // Indexes for performance
          table.index(['table_name']);
          table.index(['operation']);
          table.index(['record_id']);
          table.index(['user_id']);
          table.index(['timestamp']);
          table.index(['table_name', 'record_id']);
          table.index(['user_id', 'timestamp']);
          table.index(['compressed']);

          // Composite index for common queries
          table.index(['table_name', 'operation', 'timestamp']);
        }
      );

      this.logger.info('Created audit log table', {
        tableName: this.config.tableName,
      });
    }
  }

  /**
   * Create audit triggers for all tables
   */
  private async createAuditTriggers(): Promise<void> {
    const tables = await this.getAllTables();

    for (const tableName of tables) {
      if (this.shouldExcludeTable(tableName)) {
        continue;
      }

      await this.createTableAuditTrigger(tableName);
    }
  }

  /**
   * Create audit trigger for a specific table
   */
  private async createTableAuditTrigger(tableName: string): Promise<void> {
    try {
      // Check if trigger already exists
      const triggerExists = await this.checkTriggerExists(tableName);
      if (triggerExists) {
        this.logger.debug('Audit trigger already exists', { table: tableName });
        return;
      }

      // Create trigger function
      const functionName = `audit_${tableName}_func`;
      const triggerName = `audit_${tableName}_trigger`;

      const createFunctionSQL = `
        CREATE OR REPLACE FUNCTION ${functionName}()
        RETURNS TRIGGER AS $$
        DECLARE
          audit_row RECORD;
          old_values JSONB DEFAULT NULL;
          new_values JSONB DEFAULT NULL;
          changed_fields TEXT[] DEFAULT ARRAY[]::TEXT[];
          rec_id TEXT;
        BEGIN
          -- Determine record ID
          IF TG_OP = 'DELETE' THEN
            rec_id := COALESCE(OLD.id::TEXT, OLD.uuid::TEXT, 'unknown');
            old_values := to_jsonb(OLD);
          ELSE
            rec_id := COALESCE(NEW.id::TEXT, NEW.uuid::TEXT, 'unknown');
            new_values := to_jsonb(NEW);
          END IF;

          -- For UPDATE operations, capture old values and changed fields
          IF TG_OP = 'UPDATE' THEN
            old_values := to_jsonb(OLD);
            
            -- Find changed fields
            SELECT array_agg(key) INTO changed_fields
            FROM (
              SELECT key 
              FROM jsonb_each(old_values) old_kv
              FULL OUTER JOIN jsonb_each(new_values) new_kv USING (key)
              WHERE old_kv.value IS DISTINCT FROM new_kv.value
            ) changed;
          END IF;

          -- Insert audit log entry
          INSERT INTO ${this.config.tableName} (
            table_name,
            operation,
            record_id,
            old_values,
            new_values,
            changed_fields,
            user_id,
            session_id,
            request_id,
            source,
            metadata
          ) VALUES (
            TG_TABLE_NAME,
            TG_OP,
            rec_id,
            old_values,
            new_values,
            changed_fields,
            current_setting('audit.user_id', true),
            current_setting('audit.session_id', true),
            current_setting('audit.request_id', true),
            current_setting('audit.source', true),
            (
              SELECT jsonb_build_object(
                'user_agent', current_setting('audit.user_agent', true),
                'ip_address', current_setting('audit.ip_address', true)
              )
            )
          );

          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          ELSE
            RETURN NEW;
          END IF;
        END;
        $$ LANGUAGE plpgsql;
      `;

      await this.adapter.knex.raw(createFunctionSQL);

      // Create trigger
      const createTriggerSQL = `
        CREATE TRIGGER ${triggerName}
        AFTER INSERT OR UPDATE OR DELETE ON ${tableName}
        FOR EACH ROW EXECUTE FUNCTION ${functionName}();
      `;

      await this.adapter.knex.raw(createTriggerSQL);

      this.triggerCache.set(tableName, true);

      this.logger.debug('Created audit trigger', {
        table: tableName,
        trigger: triggerName,
        function: functionName,
      });
    } catch (error) {
      this.logger.error('Failed to create audit trigger', {
        table: tableName,
        error: error.message,
      });
    }
  }

  /**
   * Check if audit trigger exists for table
   */
  private async checkTriggerExists(tableName: string): Promise<boolean> {
    if (this.triggerCache.has(tableName)) {
      return this.triggerCache.get(tableName)!;
    }

    try {
      const result = await this.adapter.knex.raw(
        `
        SELECT EXISTS (
          SELECT 1 FROM information_schema.triggers 
          WHERE trigger_name = ? AND event_object_table = ?
        ) as exists
      `,
        [`audit_${tableName}_trigger`, tableName]
      );

      const exists = result.rows[0].exists;
      this.triggerCache.set(tableName, exists);
      return exists;
    } catch (error) {
      this.logger.error('Failed to check trigger existence', {
        table: tableName,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get all table names
   */
  private async getAllTables(): Promise<string[]> {
    try {
      const result = await this.adapter.knex.raw(
        `
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = current_schema() 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'knex_%'
        AND table_name != ?
      `,
        [this.config.tableName]
      );

      return result.rows.map(row => row.table_name);
    } catch (error) {
      this.logger.error('Failed to get table names', { error });
      return [];
    }
  }

  /**
   * Check if table should be excluded from auditing
   */
  private shouldExcludeTable(tableName: string): boolean {
    return (
      this.config.excludeTables.includes(tableName) ||
      tableName === this.config.tableName ||
      tableName.startsWith('knex_')
    );
  }

  /**
   * Set audit context for subsequent operations
   */
  setContext(context: AuditContext): void {
    this.context = { ...this.context, ...context };
  }

  /**
   * Clear audit context
   */
  clearContext(): void {
    this.context = {};
  }

  /**
   * Execute operation with audit context
   */
  async withContext<T>(
    context: AuditContext,
    operation: () => Promise<T>
  ): Promise<T> {
    const oldContext = { ...this.context };
    this.setContext(context);

    try {
      // Set PostgreSQL session variables for trigger access
      if (context.userId) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.user_id',
          context.userId,
        ]);
      }
      if (context.sessionId) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.session_id',
          context.sessionId,
        ]);
      }
      if (context.requestId) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.request_id',
          context.requestId,
        ]);
      }
      if (context.source) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.source',
          context.source,
        ]);
      }
      if (context.userAgent) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.user_agent',
          context.userAgent,
        ]);
      }
      if (context.ipAddress) {
        await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
          'audit.ip_address',
          context.ipAddress,
        ]);
      }

      const result = await operation();
      return result;
    } finally {
      this.context = oldContext;

      // Clear session variables
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.user_id',
        '',
      ]);
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.session_id',
        '',
      ]);
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.request_id',
        '',
      ]);
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.source',
        '',
      ]);
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.user_agent',
        '',
      ]);
      await this.adapter.knex.raw('SELECT set_config(?, ?, false)', [
        'audit.ip_address',
        '',
      ]);
    }
  }

  /**
   * Manually log an audit entry
   */
  async logEntry(
    entry: Omit<AuditLogEntry, 'id' | 'timestamp'>
  ): Promise<void> {
    const auditEntry: AuditLogEntry = {
      id: nanoid(),
      timestamp: new Date(),
      ...entry,
    };

    if (this.config.batchSize > 1) {
      this.pendingEntries.push(auditEntry);

      if (this.pendingEntries.length >= this.config.batchSize) {
        await this.flushPendingEntries();
      }
    } else {
      await this.insertAuditEntry(auditEntry);
    }
  }

  /**
   * Start batch processing for audit entries
   */
  private startBatchProcessing(): void {
    if (this.config.batchSize <= 1) return;

    this.flushInterval = setInterval(async () => {
      if (this.pendingEntries.length > 0) {
        await this.flushPendingEntries();
      }
    }, 5000); // Flush every 5 seconds
  }

  /**
   * Flush pending audit entries
   */
  private async flushPendingEntries(): Promise<void> {
    if (this.pendingEntries.length === 0) return;

    const entries = [...this.pendingEntries];
    this.pendingEntries = [];

    try {
      await this.adapter.knex(this.config.tableName).insert(
        entries.map(entry => ({
          id: entry.id,
          table_name: entry.tableName,
          operation: entry.operation,
          record_id: entry.recordId,
          old_values: entry.oldValues ? JSON.stringify(entry.oldValues) : null,
          new_values: entry.newValues ? JSON.stringify(entry.newValues) : null,
          changed_fields: entry.changedFields,
          user_id: entry.userId,
          timestamp: entry.timestamp,
          metadata: entry.metadata ? JSON.stringify(entry.metadata) : null,
        }))
      );

      this.logger.debug('Flushed audit entries', { count: entries.length });
    } catch (error) {
      this.logger.error('Failed to flush audit entries', {
        error: error.message,
        entriesLost: entries.length,
      });
    }
  }

  /**
   * Insert single audit entry
   */
  private async insertAuditEntry(entry: AuditLogEntry): Promise<void> {
    try {
      await this.adapter.knex(this.config.tableName).insert({
        id: entry.id,
        table_name: entry.tableName,
        operation: entry.operation,
        record_id: entry.recordId,
        old_values: entry.oldValues ? JSON.stringify(entry.oldValues) : null,
        new_values: entry.newValues ? JSON.stringify(entry.newValues) : null,
        changed_fields: entry.changedFields,
        user_id: entry.userId,
        timestamp: entry.timestamp,
        metadata: entry.metadata ? JSON.stringify(entry.metadata) : null,
      });
    } catch (error) {
      this.logger.error('Failed to insert audit entry', {
        error: error.message,
        entry: entry.id,
      });
    }
  }

  /**
   * Query audit log entries
   */
  async queryAuditLog(options: AuditQueryOptions = {}): Promise<{
    entries: AuditLogEntry[];
    total: number;
    hasMore: boolean;
  }> {
    try {
      let query = this.adapter.knex(this.config.tableName).select('*');

      // Apply filters
      if (options.tableName) {
        query = query.where('table_name', options.tableName);
      }

      if (options.operation) {
        query = query.where('operation', options.operation);
      }

      if (options.userId) {
        query = query.where('user_id', options.userId);
      }

      if (options.recordId) {
        query = query.where('record_id', options.recordId);
      }

      if (options.dateRange) {
        query = query.whereBetween('timestamp', [
          options.dateRange.from,
          options.dateRange.to,
        ]);
      }

      // Get total count
      const countQuery = query.clone().count('* as total').first();
      const countResult = await countQuery;
      const total = parseInt(countResult.total, 10);

      // Apply pagination
      const limit = options.limit || 100;
      const offset = options.offset || 0;

      query = query.orderBy('timestamp', 'desc').limit(limit).offset(offset);

      const rows = await query;

      const entries: AuditLogEntry[] = rows.map(row => ({
        id: row.id,
        tableName: row.table_name,
        operation: row.operation,
        recordId: row.record_id,
        oldValues: row.old_values ? JSON.parse(row.old_values) : undefined,
        newValues: row.new_values ? JSON.parse(row.new_values) : undefined,
        changedFields: row.changed_fields,
        userId: row.user_id,
        timestamp: row.timestamp,
        metadata: row.metadata ? JSON.parse(row.metadata) : undefined,
      }));

      return {
        entries,
        total,
        hasMore: offset + entries.length < total,
      };
    } catch (error) {
      this.logger.error('Failed to query audit log', { error, options });
      throw error;
    }
  }

  /**
   * Get audit statistics
   */
  async getStatistics(): Promise<AuditStatistics> {
    try {
      const [
        totalResult,
        operationStats,
        tableStats,
        userStats,
        dateStats,
        sizeResult,
      ] = await Promise.all([
        this.adapter.knex(this.config.tableName).count('* as total').first(),

        this.adapter
          .knex(this.config.tableName)
          .select('operation')
          .count('* as count')
          .groupBy('operation'),

        this.adapter
          .knex(this.config.tableName)
          .select('table_name')
          .count('* as count')
          .groupBy('table_name')
          .orderBy('count', 'desc')
          .limit(10),

        this.adapter
          .knex(this.config.tableName)
          .select('user_id')
          .count('* as count')
          .whereNotNull('user_id')
          .groupBy('user_id')
          .orderBy('count', 'desc')
          .limit(10),

        this.adapter
          .knex(this.config.tableName)
          .select(
            this.adapter.knex.raw('MIN(timestamp) as oldest'),
            this.adapter.knex.raw('MAX(timestamp) as newest')
          )
          .first(),

        this.adapter.knex.raw(
          `
          SELECT pg_total_relation_size(?) as size
        `,
          [this.config.tableName]
        ),
      ]);

      const total = parseInt(totalResult.total, 10);

      const entriesByOperation = operationStats.reduce((acc, row) => {
        acc[row.operation] = parseInt(row.count, 10);
        return acc;
      }, {});

      const entriesByTable = tableStats.reduce((acc, row) => {
        acc[row.table_name] = parseInt(row.count, 10);
        return acc;
      }, {});

      const entriesByUser = userStats.reduce((acc, row) => {
        acc[row.user_id] = parseInt(row.count, 10);
        return acc;
      }, {});

      const oldestEntry = dateStats.oldest;
      const newestEntry = dateStats.newest;

      let averageEntriesPerDay = 0;
      if (oldestEntry && newestEntry) {
        const daysDiff = Math.max(
          1,
          Math.ceil(
            (newestEntry.getTime() - oldestEntry.getTime()) /
              (1000 * 60 * 60 * 24)
          )
        );
        averageEntriesPerDay = total / daysDiff;
      }

      const storageSize = parseInt(sizeResult.rows[0].size, 10);

      return {
        totalEntries: total,
        entriesByOperation,
        entriesByTable,
        entriesByUser,
        oldestEntry,
        newestEntry,
        averageEntriesPerDay,
        storageSize,
      };
    } catch (error) {
      this.logger.error('Failed to get audit statistics', { error });
      throw error;
    }
  }

  /**
   * Cleanup old audit entries
   */
  async cleanup(olderThanDays?: number): Promise<number> {
    const retentionDays = olderThanDays || this.config.retentionDays;
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    this.logger.info('Starting audit log cleanup', {
      retentionDays,
      cutoffDate,
    });

    try {
      const deletedCount = await this.adapter
        .knex(this.config.tableName)
        .where('timestamp', '<', cutoffDate)
        .delete();

      this.logger.info('Audit log cleanup completed', {
        deletedEntries: deletedCount,
      });

      return deletedCount;
    } catch (error) {
      this.logger.error('Audit log cleanup failed', { error });
      throw error;
    }
  }

  /**
   * Shutdown audit logger
   */
  async shutdown(): Promise<void> {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
      this.flushInterval = undefined;
    }

    if (this.pendingEntries.length > 0) {
      await this.flushPendingEntries();
    }

    this.logger.info('Audit logger shutdown completed');
  }

  /**
   * Get audit configuration
   */
  getConfig(): AuditConfig {
    return { ...this.config };
  }

  /**
   * Check if audit logging is enabled
   */
  isEnabled(): boolean {
    return this.config.enabled;
  }
}
