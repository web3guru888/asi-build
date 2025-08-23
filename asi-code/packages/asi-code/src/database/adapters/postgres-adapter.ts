/**
 * PostgreSQL Database Adapter
 *
 * Provides a unified interface for PostgreSQL operations using Knex.js
 * with additional ASI-Code specific functionality.
 */

import knex, { Knex } from 'knex';
import {
  ConnectionError,
  DatabaseAdapter,
  DatabaseConfig,
  PerformanceMetrics,
} from '../types';
import { Logger } from '../../logging';

export class PostgresAdapter implements DatabaseAdapter {
  public knex!: Knex;
  public config: DatabaseConfig;
  private readonly logger: Logger;
  private connected = false;
  private readonly metrics: {
    queriesExecuted: number;
    queriesFailed: number;
    transactionsStarted: number;
    transactionsCommitted: number;
    transactionsRolledBack: number;
    connectionCount: number;
  };

  constructor(config: DatabaseConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    this.metrics = {
      queriesExecuted: 0,
      queriesFailed: 0,
      transactionsStarted: 0,
      transactionsCommitted: 0,
      transactionsRolledBack: 0,
      connectionCount: 0,
    };

    this.initializeKnex();
  }

  /**
   * Initialize Knex instance with PostgreSQL configuration
   */
  private initializeKnex(): void {
    const knexConfig: Knex.Config = {
      client: 'postgresql',
      connection: {
        host: this.config.host,
        port: this.config.port,
        database: this.config.database,
        user: this.config.username,
        password: this.config.password,
        ssl: this.config.ssl?.enabled
          ? {
              rejectUnauthorized: this.config.ssl.rejectUnauthorized ?? true,
              ca: this.config.ssl.ca,
              cert: this.config.ssl.cert,
              key: this.config.ssl.key,
            }
          : false,
      },
      pool: {
        min: this.config.pool.min,
        max: this.config.pool.max,
        acquireTimeoutMillis: this.config.pool.acquireTimeoutMillis,
        createTimeoutMillis: this.config.pool.createTimeoutMillis,
        destroyTimeoutMillis: this.config.pool.destroyTimeoutMillis,
        idleTimeoutMillis: this.config.pool.idleTimeoutMillis,
        reapIntervalMillis: this.config.pool.reapIntervalMillis,
        createRetryIntervalMillis: this.config.pool.createRetryIntervalMillis,
        propagateCreateError: false,
      },
      migrations: {
        directory: this.config.migrations.directory,
        tableName: this.config.migrations.tableName,
        schemaName: this.config.migrations.schemaName,
        extension: this.config.migrations.extension,
        loadExtensions: this.config.migrations.loadExtensions,
        disableTransactions: this.config.migrations.disableTransactions,
        sortDirsSeparately: this.config.migrations.sortDirsSeparately,
      },
      seeds: {
        directory: this.config.seeds.directory,
        loadExtensions: this.config.seeds.loadExtensions,
        recursive: this.config.seeds.recursive,
      },
      debug: this.config.monitoring.logQueries,
      asyncStackTraces: true,
    };

    this.knex = knex(knexConfig);
    this.setupEventHandlers();
  }

  /**
   * Setup event handlers for Knex
   */
  private setupEventHandlers(): void {
    // Query event handling
    this.knex.on('query', queryData => {
      this.metrics.queriesExecuted++;

      if (this.config.monitoring.logQueries) {
        this.logger.debug('Executing query', {
          sql: queryData.sql,
          bindings: queryData.bindings,
          method: queryData.method,
        });
      }
    });

    this.knex.on('query-response', (response, queryData, builder) => {
      if (this.config.monitoring.logQueries) {
        this.logger.debug('Query completed', {
          sql: queryData.sql,
          rowCount: Array.isArray(response) ? response.length : 1,
          executionTime: queryData.__knexQueryUid
            ? Date.now() - queryData.__knexQueryStartTime
            : 0,
        });
      }
    });

    this.knex.on('query-error', (error, queryData) => {
      this.metrics.queriesFailed++;
      this.logger.error('Query failed', {
        error: error.message,
        sql: queryData.sql,
        bindings: queryData.bindings,
      });
    });

    // Pool event handling
    this.knex.client.pool.on('createSuccess', () => {
      this.metrics.connectionCount++;
      this.logger.debug('New database connection created');
    });

    this.knex.client.pool.on('createFail', (err: any) => {
      this.logger.error('Failed to create database connection', { error: err });
    });

    this.knex.client.pool.on('destroySuccess', () => {
      this.metrics.connectionCount--;
      this.logger.debug('Database connection destroyed');
    });
  }

  /**
   * Connect to the database
   */
  async connect(): Promise<void> {
    try {
      this.logger.info('Connecting to PostgreSQL database');

      // Test the connection
      await this.knex.raw('SELECT 1 as connection_test');
      this.connected = true;

      this.logger.info('Successfully connected to PostgreSQL database');
    } catch (error) {
      this.logger.error('Failed to connect to database', { error });
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      throw new ConnectionError(
        `Failed to connect to database: ${errorMessage}`,
        error instanceof Error ? error : undefined
      );
    }
  }

  /**
   * Disconnect from the database
   */
  async disconnect(): Promise<void> {
    try {
      this.logger.info('Disconnecting from PostgreSQL database');

      await this.knex.destroy();
      this.connected = false;

      this.logger.info('Successfully disconnected from PostgreSQL database');
    } catch (error) {
      this.logger.error('Error during database disconnection', { error });
      throw error;
    }
  }

  /**
   * Check if connected to the database
   */
  isConnected(): boolean {
    return this.connected;
  }

  /**
   * Execute a raw SQL query
   */
  async query(sql: string, params?: any[]): Promise<any> {
    try {
      const startTime = Date.now();
      const result = await this.knex.raw(sql, params || []);
      const executionTime = Date.now() - startTime;

      if (
        this.config.monitoring.slowQueryThreshold &&
        executionTime > this.config.monitoring.slowQueryThreshold
      ) {
        this.logger.warn('Slow query detected', {
          sql,
          params,
          executionTime,
          threshold: this.config.monitoring.slowQueryThreshold,
        });
      }

      return result;
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      this.logger.error('Query execution failed', {
        error: errorMessage,
        sql,
        params,
      });
      throw error;
    }
  }

  /**
   * Execute a transaction
   */
  async transaction<T>(
    callback: (trx: Knex.Transaction) => Promise<T>
  ): Promise<T> {
    this.metrics.transactionsStarted++;

    try {
      const result = await this.knex.transaction(callback);
      this.metrics.transactionsCommitted++;
      return result;
    } catch (error) {
      this.metrics.transactionsRolledBack++;
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      this.logger.error('Transaction rolled back', { error: errorMessage });
      throw error;
    }
  }

  /**
   * Perform health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const startTime = Date.now();
      await this.knex.raw('SELECT 1 as health_check');
      const responseTime = Date.now() - startTime;

      this.logger.debug('Database health check passed', { responseTime });
      return true;
    } catch (error) {
      this.logger.error('Database health check failed', { error });
      return false;
    }
  }

  /**
   * Get performance metrics
   */
  async getMetrics(): Promise<PerformanceMetrics> {
    try {
      // Get connection pool stats
      const poolStats = {
        active: this.knex.client.pool.numUsed(),
        idle: this.knex.client.pool.numFree(),
        waiting: this.knex.client.pool.numPendingAcquires(),
        max: this.knex.client.pool.max,
      };

      // Get database stats
      const dbStats = await this.knex.raw(`
        SELECT 
          (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
          (SELECT count(*) FROM pg_stat_activity) as total_connections,
          (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
      `);

      return {
        connectionPool: poolStats,
        queries: {
          total: this.metrics.queriesExecuted,
          successful: this.metrics.queriesExecuted - this.metrics.queriesFailed,
          failed: this.metrics.queriesFailed,
          averageExecutionTime: 0, // TODO: Calculate average
          slowQueries: 0, // TODO: Track slow queries
        },
        transactions: {
          active: 0, // TODO: Track active transactions
          committed: this.metrics.transactionsCommitted,
          rolledBack: this.metrics.transactionsRolledBack,
          deadlocks: 0, // TODO: Query pg_stat_database for deadlocks
        },
      };
    } catch (error) {
      this.logger.error('Failed to get database metrics', { error });
      throw error;
    }
  }

  /**
   * Check if table exists
   */
  async hasTable(tableName: string): Promise<boolean> {
    try {
      return await this.knex.schema.hasTable(tableName);
    } catch (error) {
      this.logger.error('Failed to check table existence', {
        error,
        tableName,
      });
      throw error;
    }
  }

  /**
   * Check if column exists in table
   */
  async hasColumn(tableName: string, columnName: string): Promise<boolean> {
    try {
      return await this.knex.schema.hasColumn(tableName, columnName);
    } catch (error) {
      this.logger.error('Failed to check column existence', {
        error,
        tableName,
        columnName,
      });
      throw error;
    }
  }

  /**
   * Get table information
   */
  async getTableInfo(tableName: string): Promise<any> {
    try {
      const result = await this.knex.raw(
        `
        SELECT 
          column_name,
          data_type,
          is_nullable,
          column_default,
          character_maximum_length,
          numeric_precision,
          numeric_scale
        FROM information_schema.columns 
        WHERE table_name = ? AND table_schema = current_schema()
        ORDER BY ordinal_position
      `,
        [tableName]
      );

      return result.rows;
    } catch (error) {
      this.logger.error('Failed to get table info', { error, tableName });
      throw error;
    }
  }

  /**
   * Escape a value for safe SQL usage
   */
  escape(value: any): string {
    return this.knex.raw('?', [value]).toString();
  }

  /**
   * Escape an identifier for safe SQL usage
   */
  escapeIdentifier(identifier: string): string {
    return this.knex.raw('??', [identifier]).toString();
  }

  /**
   * Get the underlying Knex instance
   */
  getKnex(): Knex {
    return this.knex;
  }

  /**
   * Execute a schema operation
   */
  async executeSchema(
    callback: (schema: Knex.SchemaBuilder) => void
  ): Promise<void> {
    try {
      await this.knex.schema.raw('BEGIN');
      await callback(this.knex.schema);
      await this.knex.schema.raw('COMMIT');
    } catch (error) {
      await this.knex.schema.raw('ROLLBACK');
      this.logger.error('Schema operation failed', { error });
      throw error;
    }
  }

  /**
   * Get database version information
   */
  async getVersion(): Promise<string> {
    try {
      const result = await this.knex.raw('SELECT version()');
      return result.rows[0].version;
    } catch (error) {
      this.logger.error('Failed to get database version', { error });
      throw error;
    }
  }

  /**
   * Get current schema name
   */
  async getCurrentSchema(): Promise<string> {
    try {
      const result = await this.knex.raw('SELECT current_schema()');
      return result.rows[0].current_schema;
    } catch (error) {
      this.logger.error('Failed to get current schema', { error });
      throw error;
    }
  }
}
