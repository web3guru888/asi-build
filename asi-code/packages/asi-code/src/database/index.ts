/**
 * Database Module - ASI-Code Production Database Layer
 *
 * Comprehensive database layer providing:
 * - PostgreSQL connection pooling with retry logic
 * - Migration system with zero-downtime deployments
 * - Schema versioning and tracking
 * - Transaction support with rollback capabilities
 * - Query builder abstraction
 * - Read/write splitting
 * - Database seeding
 * - Soft deletes
 * - Audit logging
 * - Performance optimization
 * - Backup and monitoring
 */

export * from './connection/pool-manager';
export * from './connection/read-write-splitter';
export * from './migrations/migration-runner';
export * from './migrations/schema-versioning';
export * from './query/query-builder';
export * from './query/transaction-manager';
export * from './seeding/seeder';
export * from './features/soft-delete';
export * from './features/audit-logging';
export * from './monitoring/health-check';
export * from './monitoring/query-monitor';
export * from './backup/backup-manager';
export * from './cleanup/retention-jobs';
export * from './adapters/postgres-adapter';
export * from './types';

import { DatabaseConfig } from './types';
import { PostgresAdapter } from './adapters/postgres-adapter';
import { PoolManager } from './connection/pool-manager';
import { ReadWriteSplitter } from './connection/read-write-splitter';
import { MigrationRunner } from './migrations/migration-runner';
import { QueryBuilder } from './query/query-builder';
import { TransactionManager } from './query/transaction-manager';
import { Logger } from '../logging';

/**
 * Main Database class - Orchestrates all database functionality
 */
export class Database {
  private readonly adapter: PostgresAdapter;
  private readonly poolManager: PoolManager;
  private readonly readWriteSplitter?: ReadWriteSplitter;
  private readonly migrationRunner: MigrationRunner;
  private readonly queryBuilder: QueryBuilder;
  private readonly transactionManager: TransactionManager;
  private readonly logger: Logger;

  constructor(config: DatabaseConfig, logger: Logger) {
    this.logger = logger;
    this.adapter = new PostgresAdapter(config, logger);
    this.poolManager = new PoolManager(config, logger);

    if (config.readReplicas && config.readReplicas.length > 0) {
      this.readWriteSplitter = new ReadWriteSplitter(config, logger);
    }

    this.migrationRunner = new MigrationRunner(this.adapter, logger);
    this.queryBuilder = new QueryBuilder(this.adapter, logger);
    this.transactionManager = new TransactionManager(this.adapter, logger);
  }

  /**
   * Initialize the database system
   */
  async initialize(): Promise<void> {
    this.logger.info('Initializing database system');

    try {
      // Initialize connection pool
      await this.poolManager.initialize();

      // Initialize read/write splitter if configured
      if (this.readWriteSplitter) {
        await this.readWriteSplitter.initialize();
      }

      // Run pending migrations
      await this.migrationRunner.runPendingMigrations();

      this.logger.info('Database system initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize database system', { error });
      throw error;
    }
  }

  /**
   * Get query builder instance
   */
  query(): QueryBuilder {
    return this.queryBuilder;
  }

  /**
   * Get transaction manager instance
   */
  transaction(): TransactionManager {
    return this.transactionManager;
  }

  /**
   * Get migration runner instance
   */
  migrations(): MigrationRunner {
    return this.migrationRunner;
  }

  /**
   * Shutdown the database system gracefully
   */
  async shutdown(): Promise<void> {
    this.logger.info('Shutting down database system');

    try {
      if (this.readWriteSplitter) {
        await this.readWriteSplitter.shutdown();
      }

      await this.poolManager.shutdown();

      this.logger.info('Database system shutdown completed');
    } catch (error) {
      this.logger.error('Error during database shutdown', { error });
      throw error;
    }
  }

  /**
   * Get health status of the database system
   */
  async getHealthStatus(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy';
    checks: Array<{
      name: string;
      status: 'pass' | 'fail';
      details?: any;
    }>;
  }> {
    const checks = [];

    try {
      // Check primary connection
      const primaryHealth = await this.poolManager.healthCheck();
      checks.push({
        name: 'primary_connection',
        status: primaryHealth ? 'pass' : 'fail',
      });

      // Check read replicas if configured
      if (this.readWriteSplitter) {
        const replicaHealth = await this.readWriteSplitter.healthCheck();
        checks.push({
          name: 'read_replicas',
          status: replicaHealth ? 'pass' : 'fail',
        });
      }

      // Check migrations status
      const migrationStatus = await this.migrationRunner.getStatus();
      checks.push({
        name: 'migrations',
        status: migrationStatus.pendingCount === 0 ? 'pass' : 'fail',
        details: migrationStatus,
      });

      const failedChecks = checks.filter(c => c.status === 'fail');
      const status =
        failedChecks.length === 0
          ? 'healthy'
          : failedChecks.length < checks.length
            ? 'degraded'
            : 'unhealthy';

      return { status, checks };
    } catch (error) {
      this.logger.error('Health check failed', { error });
      return {
        status: 'unhealthy',
        checks: [
          {
            name: 'health_check',
            status: 'fail',
            details: error.message,
          },
        ],
      };
    }
  }
}

/**
 * Factory function to create and initialize a Database instance
 */
export async function createDatabase(
  config: DatabaseConfig,
  logger: Logger
): Promise<Database> {
  const database = new Database(config, logger);
  await database.initialize();
  return database;
}
