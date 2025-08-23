/**
 * PostgreSQL Connection Pool Manager
 *
 * Provides robust connection pooling with:
 * - Automatic connection retry with exponential backoff
 * - Health monitoring and recovery
 * - Connection lifecycle management
 * - Performance metrics tracking
 */

import { Pool, PoolClient, PoolConfig } from 'pg';
import { ConnectionError, DatabaseConfig, PerformanceMetrics } from '../types';
import { Logger } from '../../logging';

export class PoolManager {
  private pool: Pool | null = null;
  private readonly config: DatabaseConfig;
  private readonly logger: Logger;
  private readonly metrics: {
    totalConnections: number;
    activeConnections: number;
    idleConnections: number;
    waitingClients: number;
    totalQueries: number;
    failedQueries: number;
    connectionErrors: number;
    lastError?: Error;
    lastErrorTime?: Date;
  };
  private healthCheckInterval?: NodeJS.Timeout;
  private isShuttingDown = false;

  constructor(config: DatabaseConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    this.metrics = {
      totalConnections: 0,
      activeConnections: 0,
      idleConnections: 0,
      waitingClients: 0,
      totalQueries: 0,
      failedQueries: 0,
      connectionErrors: 0,
    };
  }

  /**
   * Initialize the connection pool
   */
  async initialize(): Promise<void> {
    if (this.pool) {
      this.logger.warn('Pool already initialized');
      return;
    }

    try {
      this.logger.info('Initializing PostgreSQL connection pool', {
        host: this.config.host,
        port: this.config.port,
        database: this.config.database,
        poolMin: this.config.pool.min,
        poolMax: this.config.pool.max,
      });

      const poolConfig: PoolConfig = {
        host: this.config.host,
        port: this.config.port,
        database: this.config.database,
        user: this.config.username,
        password: this.config.password,
        min: this.config.pool.min,
        max: this.config.pool.max,
        idleTimeoutMillis: this.config.pool.idleTimeoutMillis,
        ssl: this.config.ssl?.enabled
          ? {
              rejectUnauthorized: this.config.ssl.rejectUnauthorized ?? true,
              ca: this.config.ssl.ca,
              cert: this.config.ssl.cert,
              key: this.config.ssl.key,
            }
          : false,
      };

      this.pool = new Pool(poolConfig);
      this.setupEventHandlers();

      // Test initial connection with retry logic
      await this.testConnection();

      // Start health monitoring
      this.startHealthMonitoring();

      this.logger.info('PostgreSQL connection pool initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize connection pool', { error });
      throw new ConnectionError(
        `Failed to initialize connection pool: ${error.message}`,
        error
      );
    }
  }

  /**
   * Setup event handlers for the pool
   */
  private setupEventHandlers(): void {
    if (!this.pool) return;

    this.pool.on('connect', (client: PoolClient) => {
      this.metrics.totalConnections++;
      this.logger.debug('New client connected to pool', {
        totalConnections: this.pool?.totalCount,
        idleConnections: this.pool?.idleCount,
        waitingClients: this.pool?.waitingCount,
      });
    });

    this.pool.on('acquire', (client: PoolClient) => {
      this.metrics.activeConnections++;
      this.logger.debug('Client acquired from pool');
    });

    this.pool.on('release', (client: PoolClient) => {
      this.metrics.activeConnections--;
      this.logger.debug('Client released back to pool');
    });

    this.pool.on('remove', (client: PoolClient) => {
      this.metrics.totalConnections--;
      this.logger.debug('Client removed from pool');
    });

    this.pool.on('error', (error: Error, client: PoolClient) => {
      this.metrics.connectionErrors++;
      this.metrics.lastError = error;
      this.metrics.lastErrorTime = new Date();
      this.logger.error('Pool client error', { error });
    });
  }

  /**
   * Test connection with retry logic
   */
  private async testConnection(): Promise<void> {
    const { maxAttempts, initialDelayMs, maxDelayMs, exponentialBackoff } =
      this.config.retry;
    let attempt = 0;
    let delay = initialDelayMs;

    while (attempt < maxAttempts) {
      try {
        const client = await this.pool!.connect();
        const result = await client.query('SELECT 1 as test');
        client.release();

        this.logger.info('Database connection test successful');
        return;
      } catch (error) {
        attempt++;
        this.logger.warn(
          `Connection test failed (attempt ${attempt}/${maxAttempts})`,
          {
            error: error.message,
            nextRetryIn: attempt < maxAttempts ? delay : 'no more retries',
          }
        );

        if (attempt >= maxAttempts) {
          throw new ConnectionError(
            `Failed to connect after ${maxAttempts} attempts: ${error.message}`,
            error
          );
        }

        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, delay));

        // Exponential backoff
        if (exponentialBackoff) {
          delay = Math.min(delay * 2, maxDelayMs);
        }
      }
    }
  }

  /**
   * Start health monitoring
   */
  private startHealthMonitoring(): void {
    this.healthCheckInterval = setInterval(async () => {
      if (this.isShuttingDown) return;

      try {
        await this.healthCheck();
      } catch (error) {
        this.logger.error('Health check failed', { error });
      }
    }, 30000); // Health check every 30 seconds
  }

  /**
   * Perform health check
   */
  async healthCheck(): Promise<boolean> {
    if (!this.pool) {
      return false;
    }

    try {
      const startTime = Date.now();
      const client = await this.pool.connect();

      try {
        await client.query('SELECT 1');
        const responseTime = Date.now() - startTime;

        this.logger.debug('Health check passed', {
          responseTime,
          totalCount: this.pool.totalCount,
          idleCount: this.pool.idleCount,
          waitingCount: this.pool.waitingCount,
        });

        return true;
      } finally {
        client.release();
      }
    } catch (error) {
      this.logger.error('Health check failed', { error });
      return false;
    }
  }

  /**
   * Get a client from the pool
   */
  async getClient(): Promise<PoolClient> {
    if (!this.pool) {
      throw new ConnectionError('Pool not initialized');
    }

    try {
      const client = await this.pool.connect();
      return client;
    } catch (error) {
      this.metrics.connectionErrors++;
      this.logger.error('Failed to get client from pool', { error });
      throw new ConnectionError(
        `Failed to acquire database connection: ${error.message}`,
        error
      );
    }
  }

  /**
   * Execute a query using the pool
   */
  async query(text: string, params?: any[]): Promise<any> {
    if (!this.pool) {
      throw new ConnectionError('Pool not initialized');
    }

    const startTime = Date.now();
    let client: PoolClient | null = null;

    try {
      client = await this.getClient();
      const result = await client.query(text, params);

      this.metrics.totalQueries++;
      const executionTime = Date.now() - startTime;

      this.logger.debug('Query executed successfully', {
        executionTime,
        rowCount: result.rowCount,
      });

      return result;
    } catch (error) {
      this.metrics.failedQueries++;
      this.logger.error('Query execution failed', {
        error,
        query: text,
        params,
        executionTime: Date.now() - startTime,
      });
      throw error;
    } finally {
      if (client) {
        client.release();
      }
    }
  }

  /**
   * Get pool performance metrics
   */
  getMetrics(): PerformanceMetrics {
    return {
      connectionPool: {
        active: this.pool?.totalCount - this.pool?.idleCount || 0,
        idle: this.pool?.idleCount || 0,
        waiting: this.pool?.waitingCount || 0,
        max: this.config.pool.max,
      },
      queries: {
        total: this.metrics.totalQueries,
        successful: this.metrics.totalQueries - this.metrics.failedQueries,
        failed: this.metrics.failedQueries,
        averageExecutionTime: 0, // TODO: Implement average calculation
        slowQueries: 0, // TODO: Implement slow query tracking
      },
      transactions: {
        active: 0, // TODO: Track active transactions
        committed: 0, // TODO: Track committed transactions
        rolledBack: 0, // TODO: Track rolled back transactions
        deadlocks: 0, // TODO: Track deadlocks
      },
    };
  }

  /**
   * Get pool status information
   */
  getStatus(): {
    isConnected: boolean;
    totalConnections: number;
    idleConnections: number;
    waitingClients: number;
    lastError?: Error;
    lastErrorTime?: Date;
  } {
    return {
      isConnected: this.pool !== null,
      totalConnections: this.pool?.totalCount || 0,
      idleConnections: this.pool?.idleCount || 0,
      waitingClients: this.pool?.waitingCount || 0,
      lastError: this.metrics.lastError,
      lastErrorTime: this.metrics.lastErrorTime,
    };
  }

  /**
   * Shutdown the pool gracefully
   */
  async shutdown(): Promise<void> {
    if (!this.pool) {
      this.logger.warn('Pool not initialized, nothing to shutdown');
      return;
    }

    this.isShuttingDown = true;

    try {
      this.logger.info('Shutting down connection pool gracefully');

      // Stop health monitoring
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = undefined;
      }

      // Close all connections
      await this.pool.end();
      this.pool = null;

      this.logger.info('Connection pool shutdown completed');
    } catch (error) {
      this.logger.error('Error during pool shutdown', { error });
      throw error;
    } finally {
      this.isShuttingDown = false;
    }
  }
}
