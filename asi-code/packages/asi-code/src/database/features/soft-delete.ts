/**
 * Soft Delete Implementation
 *
 * Provides comprehensive soft delete functionality with:
 * - Automatic soft delete column management
 * - Query filtering for soft deleted records
 * - Restore functionality
 * - Cascade soft delete for related records
 * - Cleanup of old soft deleted records
 * - Audit trail integration
 */

import { Knex } from 'knex';
import { DatabaseAdapter, SoftDeleteOptions, SoftDeleteQuery } from '../types';
import { Logger } from '../../logging';

export interface SoftDeleteConfig {
  enabled: boolean;
  columnName: string;
  defaultValue: null;
  deletedValue: Date | string | number;
  cascadeDeletes: boolean;
  retentionPeriod?: number; // Days to keep soft deleted records
}

export interface SoftDeleteRelation {
  table: string;
  foreignKey: string;
  cascade: boolean;
}

export interface SoftDeleteMetrics {
  totalSoftDeleted: number;
  restoredRecords: number;
  permanentlyDeleted: number;
  cascadeDeletes: number;
  cleanupOperations: number;
}

export class SoftDeleteManager {
  private readonly adapter: DatabaseAdapter;
  private readonly logger: Logger;
  private readonly config: SoftDeleteConfig;
  private readonly relations = new Map<string, SoftDeleteRelation[]>();
  private metrics: SoftDeleteMetrics = {
    totalSoftDeleted: 0,
    restoredRecords: 0,
    permanentlyDeleted: 0,
    cascadeDeletes: 0,
    cleanupOperations: 0,
  };

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
    this.config = {
      enabled: adapter.config.softDelete.enabled,
      columnName: adapter.config.softDelete.columnName,
      defaultValue: adapter.config.softDelete.defaultValue,
      deletedValue: adapter.config.softDelete.deletedValue,
      cascadeDeletes: true,
      retentionPeriod: 90, // 90 days default
    };
  }

  /**
   * Initialize soft delete system
   */
  async initialize(): Promise<void> {
    if (!this.config.enabled) {
      this.logger.info('Soft delete is disabled');
      return;
    }

    try {
      this.logger.info('Initializing soft delete system', {
        columnName: this.config.columnName,
        deletedValue: this.config.deletedValue,
      });

      // Ensure all tables have soft delete column
      await this.ensureSoftDeleteColumns();

      // Load table relations
      await this.loadTableRelations();

      this.logger.info('Soft delete system initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize soft delete system', { error });
      throw error;
    }
  }

  /**
   * Ensure all tables have the soft delete column
   */
  private async ensureSoftDeleteColumns(): Promise<void> {
    try {
      // Get all tables
      const tables = await this.getAllTables();

      for (const tableName of tables) {
        const hasColumn = await this.adapter.hasColumn(
          tableName,
          this.config.columnName
        );

        if (!hasColumn) {
          this.logger.debug('Adding soft delete column to table', {
            table: tableName,
            column: this.config.columnName,
          });

          await this.adapter.knex.schema.alterTable(tableName, table => {
            if (this.config.deletedValue instanceof Date) {
              table.timestamp(this.config.columnName).nullable();
            } else if (typeof this.config.deletedValue === 'string') {
              table.string(this.config.columnName).nullable();
            } else if (typeof this.config.deletedValue === 'number') {
              table.integer(this.config.columnName).nullable();
            } else {
              table.timestamp(this.config.columnName).nullable();
            }

            // Add index for performance
            table.index([this.config.columnName]);
          });
        }
      }
    } catch (error) {
      this.logger.error('Failed to ensure soft delete columns', { error });
      throw error;
    }
  }

  /**
   * Get all table names from the database
   */
  private async getAllTables(): Promise<string[]> {
    try {
      const result = await this.adapter.knex.raw(`
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = current_schema() 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'knex_%'
      `);

      return result.rows.map(row => row.table_name);
    } catch (error) {
      this.logger.error('Failed to get table names', { error });
      return [];
    }
  }

  /**
   * Load table relations for cascade deletes
   */
  private async loadTableRelations(): Promise<void> {
    try {
      const result = await this.adapter.knex.raw(`
        SELECT 
          tc.table_name,
          kcu.column_name,
          ccu.table_name AS foreign_table_name,
          ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = current_schema()
      `);

      for (const row of result.rows) {
        const parentTable = row.foreign_table_name;
        const childTable = row.table_name;
        const foreignKey = row.column_name;

        if (!this.relations.has(parentTable)) {
          this.relations.set(parentTable, []);
        }

        this.relations.get(parentTable)!.push({
          table: childTable,
          foreignKey,
          cascade: true,
        });
      }

      this.logger.debug('Loaded table relations for cascade deletes', {
        relations: this.relations.size,
      });
    } catch (error) {
      this.logger.error('Failed to load table relations', { error });
    }
  }

  /**
   * Apply soft delete filter to query
   */
  applySoftDeleteFilter(
    query: Knex.QueryBuilder,
    tableName: string,
    options: SoftDeleteQuery = {}
  ): Knex.QueryBuilder {
    if (!this.config.enabled) {
      return query;
    }

    const columnName = `${tableName}.${this.config.columnName}`;

    if (options.onlyDeleted) {
      return query.whereNotNull(columnName);
    } else if (!options.includeDeleted) {
      return query.whereNull(columnName);
    }

    return query;
  }

  /**
   * Soft delete records
   */
  async softDelete(
    tableName: string,
    whereConditions: any,
    options: SoftDeleteOptions = {}
  ): Promise<number> {
    if (!this.config.enabled || options.force) {
      // Hard delete if soft delete is disabled or force is specified
      return await this.hardDelete(tableName, whereConditions);
    }

    const startTime = Date.now();

    try {
      this.logger.debug('Performing soft delete', {
        table: tableName,
        conditions: whereConditions,
      });

      // Get records to be deleted for cascade operations
      const recordsToDelete = await this.adapter
        .knex(tableName)
        .where(whereConditions)
        .whereNull(this.config.columnName);

      if (recordsToDelete.length === 0) {
        return 0;
      }

      // Perform soft delete
      const deletedValue =
        this.config.deletedValue instanceof Date
          ? new Date()
          : this.config.deletedValue;

      const result = await this.adapter
        .knex(tableName)
        .where(whereConditions)
        .whereNull(this.config.columnName)
        .update({
          [this.config.columnName]: deletedValue,
          updated_at: new Date(),
        });

      // Cascade soft delete to related records
      if (this.config.cascadeDeletes) {
        await this.cascadeSoftDelete(tableName, recordsToDelete);
      }

      const executionTime = Date.now() - startTime;
      this.metrics.totalSoftDeleted += result;

      this.logger.info('Soft delete completed', {
        table: tableName,
        recordsDeleted: result,
        executionTime,
      });

      return result;
    } catch (error) {
      this.logger.error('Soft delete failed', {
        table: tableName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Hard delete records
   */
  async hardDelete(tableName: string, whereConditions: any): Promise<number> {
    const startTime = Date.now();

    try {
      this.logger.debug('Performing hard delete', {
        table: tableName,
        conditions: whereConditions,
      });

      const result = await this.adapter
        .knex(tableName)
        .where(whereConditions)
        .del();

      const executionTime = Date.now() - startTime;
      this.metrics.permanentlyDeleted += result;

      this.logger.info('Hard delete completed', {
        table: tableName,
        recordsDeleted: result,
        executionTime,
      });

      return result;
    } catch (error) {
      this.logger.error('Hard delete failed', {
        table: tableName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Restore soft deleted records
   */
  async restore(tableName: string, whereConditions: any): Promise<number> {
    if (!this.config.enabled) {
      throw new Error('Soft delete is not enabled');
    }

    const startTime = Date.now();

    try {
      this.logger.debug('Restoring soft deleted records', {
        table: tableName,
        conditions: whereConditions,
      });

      const result = await this.adapter
        .knex(tableName)
        .where(whereConditions)
        .whereNotNull(this.config.columnName)
        .update({
          [this.config.columnName]: this.config.defaultValue,
          updated_at: new Date(),
        });

      const executionTime = Date.now() - startTime;
      this.metrics.restoredRecords += result;

      this.logger.info('Restore completed', {
        table: tableName,
        recordsRestored: result,
        executionTime,
      });

      return result;
    } catch (error) {
      this.logger.error('Restore failed', {
        table: tableName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Cascade soft delete to related records
   */
  private async cascadeSoftDelete(
    parentTable: string,
    parentRecords: any[]
  ): Promise<void> {
    const relations = this.relations.get(parentTable);
    if (!relations || relations.length === 0) {
      return;
    }

    for (const relation of relations) {
      if (!relation.cascade) continue;

      try {
        const parentIds = parentRecords
          .map(record => record.id)
          .filter(Boolean);
        if (parentIds.length === 0) continue;

        this.logger.debug('Cascade soft deleting related records', {
          parentTable,
          childTable: relation.table,
          foreignKey: relation.foreignKey,
          parentIds: parentIds.length,
        });

        const deletedValue =
          this.config.deletedValue instanceof Date
            ? new Date()
            : this.config.deletedValue;

        const result = await this.adapter
          .knex(relation.table)
          .whereIn(relation.foreignKey, parentIds)
          .whereNull(this.config.columnName)
          .update({
            [this.config.columnName]: deletedValue,
            updated_at: new Date(),
          });

        this.metrics.cascadeDeletes += result;

        this.logger.debug('Cascade soft delete completed', {
          childTable: relation.table,
          recordsDeleted: result,
        });
      } catch (error) {
        this.logger.error('Cascade soft delete failed', {
          parentTable,
          childTable: relation.table,
          error: error.message,
        });
      }
    }
  }

  /**
   * Get soft deleted records
   */
  async getSoftDeleted(
    tableName: string,
    limit = 100,
    offset = 0
  ): Promise<{ data: any[]; total: number }> {
    if (!this.config.enabled) {
      return { data: [], total: 0 };
    }

    try {
      const [data, countResult] = await Promise.all([
        this.adapter
          .knex(tableName)
          .whereNotNull(this.config.columnName)
          .limit(limit)
          .offset(offset)
          .orderBy(this.config.columnName, 'desc'),

        this.adapter
          .knex(tableName)
          .whereNotNull(this.config.columnName)
          .count('* as total')
          .first(),
      ]);

      return {
        data,
        total: parseInt(countResult.total, 10),
      };
    } catch (error) {
      this.logger.error('Failed to get soft deleted records', {
        table: tableName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Cleanup old soft deleted records
   */
  async cleanup(
    tableName?: string,
    olderThanDays?: number
  ): Promise<{ [tableName: string]: number }> {
    if (!this.config.enabled) {
      return {};
    }

    const retentionDays = olderThanDays || this.config.retentionPeriod || 90;
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

    this.logger.info('Starting soft delete cleanup', {
      retentionDays,
      cutoffDate,
      specificTable: tableName,
    });

    const results: { [tableName: string]: number } = {};

    try {
      const tablesToClean = tableName ? [tableName] : await this.getAllTables();

      for (const table of tablesToClean) {
        try {
          // Check if table has soft delete column
          const hasColumn = await this.adapter.hasColumn(
            table,
            this.config.columnName
          );
          if (!hasColumn) continue;

          let query = this.adapter
            .knex(table)
            .whereNotNull(this.config.columnName);

          // Add date filter based on deleted value type
          if (this.config.deletedValue instanceof Date) {
            query = query.where(this.config.columnName, '<', cutoffDate);
          } else {
            // For non-date values, we can't filter by date
            // Skip cleanup for this table or implement custom logic
            continue;
          }

          const deletedCount = await query.del();
          results[table] = deletedCount;

          if (deletedCount > 0) {
            this.logger.info('Cleaned up soft deleted records', {
              table,
              recordsDeleted: deletedCount,
            });
          }

          this.metrics.cleanupOperations++;
        } catch (error) {
          this.logger.error('Cleanup failed for table', {
            table,
            error: error.message,
          });
          results[table] = 0;
        }
      }

      this.logger.info('Soft delete cleanup completed', {
        tablesProcessed: Object.keys(results).length,
        totalRecordsDeleted: Object.values(results).reduce(
          (sum, count) => sum + count,
          0
        ),
      });

      return results;
    } catch (error) {
      this.logger.error('Soft delete cleanup failed', { error });
      throw error;
    }
  }

  /**
   * Get soft delete statistics
   */
  async getStatistics(tableName?: string): Promise<{
    table?: string;
    totalRecords: number;
    activeRecords: number;
    softDeletedRecords: number;
    deletionRate: number;
  }> {
    if (!this.config.enabled) {
      return {
        table: tableName,
        totalRecords: 0,
        activeRecords: 0,
        softDeletedRecords: 0,
        deletionRate: 0,
      };
    }

    try {
      if (tableName) {
        return await this.getTableStatistics(tableName);
      } else {
        // Get aggregated statistics across all tables
        const tables = await this.getAllTables();
        let totalRecords = 0;
        let activeRecords = 0;
        let softDeletedRecords = 0;

        for (const table of tables) {
          const hasColumn = await this.adapter.hasColumn(
            table,
            this.config.columnName
          );
          if (!hasColumn) continue;

          const stats = await this.getTableStatistics(table);
          totalRecords += stats.totalRecords;
          activeRecords += stats.activeRecords;
          softDeletedRecords += stats.softDeletedRecords;
        }

        const deletionRate =
          totalRecords > 0 ? (softDeletedRecords / totalRecords) * 100 : 0;

        return {
          totalRecords,
          activeRecords,
          softDeletedRecords,
          deletionRate,
        };
      }
    } catch (error) {
      this.logger.error('Failed to get soft delete statistics', { error });
      throw error;
    }
  }

  /**
   * Get statistics for a specific table
   */
  private async getTableStatistics(tableName: string): Promise<{
    table: string;
    totalRecords: number;
    activeRecords: number;
    softDeletedRecords: number;
    deletionRate: number;
  }> {
    const hasColumn = await this.adapter.hasColumn(
      tableName,
      this.config.columnName
    );

    if (!hasColumn) {
      const totalResult = await this.adapter
        .knex(tableName)
        .count('* as total')
        .first();
      const total = parseInt(totalResult.total, 10);

      return {
        table: tableName,
        totalRecords: total,
        activeRecords: total,
        softDeletedRecords: 0,
        deletionRate: 0,
      };
    }

    const [totalResult, activeResult, deletedResult] = await Promise.all([
      this.adapter.knex(tableName).count('* as total').first(),
      this.adapter
        .knex(tableName)
        .whereNull(this.config.columnName)
        .count('* as active')
        .first(),
      this.adapter
        .knex(tableName)
        .whereNotNull(this.config.columnName)
        .count('* as deleted')
        .first(),
    ]);

    const totalRecords = parseInt(totalResult.total, 10);
    const activeRecords = parseInt(activeResult.active, 10);
    const softDeletedRecords = parseInt(deletedResult.deleted, 10);
    const deletionRate =
      totalRecords > 0 ? (softDeletedRecords / totalRecords) * 100 : 0;

    return {
      table: tableName,
      totalRecords,
      activeRecords,
      softDeletedRecords,
      deletionRate,
    };
  }

  /**
   * Register a table relation for cascade deletes
   */
  registerRelation(parentTable: string, relation: SoftDeleteRelation): void {
    if (!this.relations.has(parentTable)) {
      this.relations.set(parentTable, []);
    }

    this.relations.get(parentTable)!.push(relation);

    this.logger.debug('Registered soft delete relation', {
      parentTable,
      childTable: relation.table,
      foreignKey: relation.foreignKey,
      cascade: relation.cascade,
    });
  }

  /**
   * Get soft delete metrics
   */
  getMetrics(): SoftDeleteMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    this.metrics = {
      totalSoftDeleted: 0,
      restoredRecords: 0,
      permanentlyDeleted: 0,
      cascadeDeletes: 0,
      cleanupOperations: 0,
    };
  }

  /**
   * Check if soft delete is enabled
   */
  isEnabled(): boolean {
    return this.config.enabled;
  }

  /**
   * Get soft delete configuration
   */
  getConfig(): SoftDeleteConfig {
    return { ...this.config };
  }
}
