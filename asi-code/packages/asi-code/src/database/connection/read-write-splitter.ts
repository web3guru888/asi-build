/**
 * Read/Write Database Splitter
 * 
 * Provides intelligent read/write splitting for database scalability:
 * - Automatic routing of read queries to read replicas
 * - Write queries always go to primary database
 * - Load balancing across multiple read replicas
 * - Health monitoring and failover
 * - Connection pooling for each replica
 * - Lag monitoring and replica promotion
 */

import { Pool, PoolClient } from 'pg';
import { DatabaseConfig, PerformanceMetrics } from '../types';
import { Logger } from '../../logging';

export interface ReadReplicaConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  weight: number;
}

export interface ReplicaStatus {
  id: string;
  config: ReadReplicaConfig;
  pool: Pool;
  isHealthy: boolean;
  lastHealthCheck: Date;
  responseTime: number;
  lagMs: number;
  connectionCount: number;
  totalQueries: number;
  failedQueries: number;
  lastError?: Error;
}

export interface ReadWriteStats {
  readQueries: number;
  writeQueries: number;
  readErrors: number;
  writeErrors: number;
  averageReadTime: number;
  averageWriteTime: number;
  replicaDistribution: { [replicaId: string]: number };
}

export class ReadWriteSplitter {
  private config: DatabaseConfig;
  private logger: Logger;
  private primaryPool: Pool;
  private replicas: Map<string, ReplicaStatus> = new Map();
  private stats: ReadWriteStats;
  private healthCheckInterval?: NodeJS.Timeout;
  private isInitialized = false;

  constructor(config: DatabaseConfig, logger: Logger) {
    this.config = config;
    this.logger = logger;
    this.stats = {
      readQueries: 0,
      writeQueries: 0,
      readErrors: 0,
      writeErrors: 0,
      averageReadTime: 0,
      averageWriteTime: 0,
      replicaDistribution: {}
    };
  }

  /**
   * Initialize the read/write splitter
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      this.logger.warn('Read/write splitter already initialized');
      return;
    }

    try {
      this.logger.info('Initializing read/write splitter');

      // Initialize primary pool
      await this.initializePrimaryPool();

      // Initialize read replicas
      if (this.config.readReplicas && this.config.readReplicas.length > 0) {
        await this.initializeReadReplicas();
      }

      // Start health monitoring
      this.startHealthMonitoring();

      this.isInitialized = true;
      this.logger.info('Read/write splitter initialized successfully', {
        replicas: this.replicas.size
      });
    } catch (error) {
      this.logger.error('Failed to initialize read/write splitter', { error });
      throw error;
    }
  }

  /**
   * Initialize primary database pool
   */
  private async initializePrimaryPool(): Promise<void> {
    const primaryConfig = {
      host: this.config.host,
      port: this.config.port,
      database: this.config.database,
      user: this.config.username,
      password: this.config.password,
      min: this.config.pool.min,
      max: this.config.pool.max,
      acquireTimeoutMillis: this.config.pool.acquireTimeoutMillis,
      createTimeoutMillis: this.config.pool.createTimeoutMillis,
      destroyTimeoutMillis: this.config.pool.destroyTimeoutMillis,
      idleTimeoutMillis: this.config.pool.idleTimeoutMillis,
      ssl: this.config.ssl?.enabled ? {
        rejectUnauthorized: this.config.ssl.rejectUnauthorized ?? true,
        ca: this.config.ssl.ca,
        cert: this.config.ssl.cert,
        key: this.config.ssl.key
      } : false
    };

    this.primaryPool = new Pool(primaryConfig);
    
    // Test primary connection
    const client = await this.primaryPool.connect();
    await client.query('SELECT 1');
    client.release();

    this.logger.info('Primary database pool initialized');
  }

  /**
   * Initialize read replica pools
   */
  private async initializeReadReplicas(): Promise<void> {
    if (!this.config.readReplicas) return;

    const replicaPromises = this.config.readReplicas.map(async (replicaConfig, index) => {
      const replicaId = `replica_${index}`;
      
      try {
        const poolConfig = {
          host: replicaConfig.host,
          port: replicaConfig.port,
          database: replicaConfig.database,
          user: replicaConfig.username,
          password: replicaConfig.password,
          min: Math.floor(this.config.pool.min / this.config.readReplicas!.length),
          max: Math.floor(this.config.pool.max / this.config.readReplicas!.length),
          acquireTimeoutMillis: this.config.pool.acquireTimeoutMillis,
          createTimeoutMillis: this.config.pool.createTimeoutMillis,
          destroyTimeoutMillis: this.config.pool.destroyTimeoutMillis,
          idleTimeoutMillis: this.config.pool.idleTimeoutMillis,
          ssl: this.config.ssl?.enabled ? {
            rejectUnauthorized: this.config.ssl.rejectUnauthorized ?? true,
            ca: this.config.ssl.ca,
            cert: this.config.ssl.cert,
            key: this.config.ssl.key
          } : false
        };

        const pool = new Pool(poolConfig);
        
        // Test replica connection
        const client = await pool.connect();
        await client.query('SELECT 1');
        client.release();

        const replicaStatus: ReplicaStatus = {
          id: replicaId,
          config: {
            ...replicaConfig,
            weight: replicaConfig.weight || 1
          },
          pool,
          isHealthy: true,
          lastHealthCheck: new Date(),
          responseTime: 0,
          lagMs: 0,
          connectionCount: 0,
          totalQueries: 0,
          failedQueries: 0
        };

        this.replicas.set(replicaId, replicaStatus);
        this.stats.replicaDistribution[replicaId] = 0;

        this.logger.info('Read replica initialized', {
          replicaId,
          host: replicaConfig.host,
          port: replicaConfig.port
        });
      } catch (error) {
        this.logger.error('Failed to initialize read replica', {
          replicaId,
          error: error.message,
          host: replicaConfig.host,
          port: replicaConfig.port
        });
      }
    });

    await Promise.allSettled(replicaPromises);
    
    this.logger.info('Read replicas initialization completed', {
      totalReplicas: this.config.readReplicas.length,
      healthyReplicas: this.getHealthyReplicas().length
    });
  }

  /**
   * Execute a query with automatic read/write routing
   */
  async executeQuery(sql: string, params?: any[], forceWrite = false): Promise<any> {
    const isWriteQuery = this.isWriteQuery(sql) || forceWrite;
    const startTime = Date.now();

    try {
      let result: any;
      
      if (isWriteQuery) {
        result = await this.executeWriteQuery(sql, params);
        this.stats.writeQueries++;
        this.updateAverageTime('write', Date.now() - startTime);
      } else {
        result = await this.executeReadQuery(sql, params);
        this.stats.readQueries++;
        this.updateAverageTime('read', Date.now() - startTime);
      }

      return result;
    } catch (error) {
      if (isWriteQuery) {
        this.stats.writeErrors++;
      } else {
        this.stats.readErrors++;
      }
      throw error;
    }
  }

  /**
   * Execute write query on primary database
   */
  private async executeWriteQuery(sql: string, params?: any[]): Promise<any> {
    const client = await this.primaryPool.connect();
    
    try {
      const result = await client.query(sql, params);
      return result;
    } finally {
      client.release();
    }
  }

  /**
   * Execute read query on best available replica
   */
  private async executeReadQuery(sql: string, params?: any[]): Promise<any> {
    const replica = this.selectBestReplica();
    
    if (!replica) {
      // Fallback to primary if no healthy replicas
      this.logger.warn('No healthy replicas available, falling back to primary');
      return await this.executeWriteQuery(sql, params);
    }

    const client = await replica.pool.connect();
    
    try {
      const result = await client.query(sql, params);
      replica.totalQueries++;
      this.stats.replicaDistribution[replica.id]++;
      return result;
    } catch (error) {
      replica.failedQueries++;
      replica.lastError = error;
      this.logger.error('Read query failed on replica', {
        replicaId: replica.id,
        error: error.message
      });
      
      // Mark replica as unhealthy if too many failures
      if (replica.failedQueries > 5) {
        replica.isHealthy = false;
      }
      
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Select the best replica based on health, lag, and load balancing
   */
  private selectBestReplica(): ReplicaStatus | null {
    const healthyReplicas = this.getHealthyReplicas();
    
    if (healthyReplicas.length === 0) {
      return null;
    }

    if (healthyReplicas.length === 1) {
      return healthyReplicas[0];
    }

    // Weighted selection based on replica weight and current load
    const totalWeight = healthyReplicas.reduce((sum, replica) => {
      const loadFactor = 1 / (replica.connectionCount + 1);
      const lagPenalty = Math.max(0, 1 - (replica.lagMs / 1000));
      return sum + (replica.config.weight * loadFactor * lagPenalty);
    }, 0);

    const random = Math.random() * totalWeight;
    let currentWeight = 0;

    for (const replica of healthyReplicas) {
      const loadFactor = 1 / (replica.connectionCount + 1);
      const lagPenalty = Math.max(0, 1 - (replica.lagMs / 1000));
      currentWeight += replica.config.weight * loadFactor * lagPenalty;
      
      if (random <= currentWeight) {
        return replica;
      }
    }

    // Fallback to first healthy replica
    return healthyReplicas[0];
  }

  /**
   * Get healthy replicas
   */
  private getHealthyReplicas(): ReplicaStatus[] {
    return Array.from(this.replicas.values()).filter(replica => replica.isHealthy);
  }

  /**
   * Check if query is a write operation
   */
  private isWriteQuery(sql: string): boolean {
    const trimmed = sql.trim().toUpperCase();
    const writeOperations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE'];
    
    return writeOperations.some(op => trimmed.startsWith(op));
  }

  /**
   * Start health monitoring for all replicas
   */
  private startHealthMonitoring(): void {
    this.healthCheckInterval = setInterval(async () => {
      await this.performHealthChecks();
    }, 30000); // Health check every 30 seconds
  }

  /**
   * Perform health checks on all replicas
   */
  private async performHealthChecks(): Promise<void> {
    const healthCheckPromises = Array.from(this.replicas.values()).map(async (replica) => {
      try {
        const startTime = Date.now();
        const client = await replica.pool.connect();
        
        try {
          // Health check query
          await client.query('SELECT 1');
          
          // Check replication lag
          const lagResult = await client.query(`
            SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000 as lag_ms
          `);
          
          const responseTime = Date.now() - startTime;
          const lagMs = parseFloat(lagResult.rows[0]?.lag_ms) || 0;
          
          replica.isHealthy = true;
          replica.lastHealthCheck = new Date();
          replica.responseTime = responseTime;
          replica.lagMs = lagMs;
          replica.connectionCount = replica.pool.totalCount;
          
          this.logger.debug('Replica health check passed', {
            replicaId: replica.id,
            responseTime,
            lagMs,
            connections: replica.connectionCount
          });
        } finally {
          client.release();
        }
      } catch (error) {
        replica.isHealthy = false;
        replica.lastError = error;
        replica.lastHealthCheck = new Date();
        
        this.logger.warn('Replica health check failed', {
          replicaId: replica.id,
          error: error.message
        });
      }
    });

    await Promise.allSettled(healthCheckPromises);
  }

  /**
   * Update average execution time
   */
  private updateAverageTime(type: 'read' | 'write', executionTime: number): void {
    if (type === 'read') {
      const total = this.stats.averageReadTime * (this.stats.readQueries - 1) + executionTime;
      this.stats.averageReadTime = total / this.stats.readQueries;
    } else {
      const total = this.stats.averageWriteTime * (this.stats.writeQueries - 1) + executionTime;
      this.stats.averageWriteTime = total / this.stats.writeQueries;
    }
  }

  /**
   * Get read/write statistics
   */
  getStats(): ReadWriteStats {
    return { ...this.stats };
  }

  /**
   * Get replica statuses
   */
  getReplicaStatuses(): ReplicaStatus[] {
    return Array.from(this.replicas.values());
  }

  /**
   * Perform health check on all connections
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Check primary
      const primaryClient = await this.primaryPool.connect();
      await primaryClient.query('SELECT 1');
      primaryClient.release();

      // Check at least one replica is healthy
      const healthyReplicas = this.getHealthyReplicas();
      
      return healthyReplicas.length > 0 || this.replicas.size === 0;
    } catch (error) {
      this.logger.error('Health check failed', { error });
      return false;
    }
  }

  /**
   * Get performance metrics
   */
  async getMetrics(): Promise<PerformanceMetrics> {
    const primaryStats = {
      active: this.primaryPool.totalCount - this.primaryPool.idleCount,
      idle: this.primaryPool.idleCount,
      waiting: this.primaryPool.waitingCount,
      max: this.config.pool.max
    };

    const replicaStats = Array.from(this.replicas.values()).reduce(
      (acc, replica) => ({
        active: acc.active + (replica.pool.totalCount - replica.pool.idleCount),
        idle: acc.idle + replica.pool.idleCount,
        waiting: acc.waiting + replica.pool.waitingCount,
        max: acc.max + Math.floor(this.config.pool.max / this.replicas.size)
      }),
      { active: 0, idle: 0, waiting: 0, max: 0 }
    );

    return {
      connectionPool: {
        active: primaryStats.active + replicaStats.active,
        idle: primaryStats.idle + replicaStats.idle,
        waiting: primaryStats.waiting + replicaStats.waiting,
        max: primaryStats.max + replicaStats.max
      },
      queries: {
        total: this.stats.readQueries + this.stats.writeQueries,
        successful: this.stats.readQueries + this.stats.writeQueries - this.stats.readErrors - this.stats.writeErrors,
        failed: this.stats.readErrors + this.stats.writeErrors,
        averageExecutionTime: (this.stats.averageReadTime + this.stats.averageWriteTime) / 2,
        slowQueries: 0 // TODO: Track slow queries
      },
      transactions: {
        active: 0, // TODO: Track active transactions
        committed: 0, // TODO: Track committed transactions
        rolledBack: 0, // TODO: Track rolled back transactions
        deadlocks: 0 // TODO: Track deadlocks
      },
      replication: {
        lag: Math.max(...Array.from(this.replicas.values()).map(r => r.lagMs)),
        status: this.getHealthyReplicas().length > 0 ? 'active' : 'inactive'
      }
    };
  }

  /**
   * Shutdown the read/write splitter
   */
  async shutdown(): Promise<void> {
    this.logger.info('Shutting down read/write splitter');

    try {
      // Stop health monitoring
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = undefined;
      }

      // Close replica pools
      const replicaPromises = Array.from(this.replicas.values()).map(async (replica) => {
        try {
          await replica.pool.end();
          this.logger.debug('Replica pool closed', { replicaId: replica.id });
        } catch (error) {
          this.logger.error('Error closing replica pool', {
            replicaId: replica.id,
            error: error.message
          });
        }
      });

      await Promise.allSettled(replicaPromises);

      // Close primary pool
      await this.primaryPool.end();

      this.replicas.clear();
      this.isInitialized = false;

      this.logger.info('Read/write splitter shutdown completed');
    } catch (error) {
      this.logger.error('Error during read/write splitter shutdown', { error });
      throw error;
    }
  }

  /**
   * Force failover to a specific replica (promote to primary)
   */
  async promoteReplica(replicaId: string): Promise<void> {
    const replica = this.replicas.get(replicaId);
    if (!replica) {
      throw new Error(`Replica ${replicaId} not found`);
    }

    this.logger.warn('Promoting replica to primary', { replicaId });

    try {
      // This is a simplified implementation
      // In practice, this would involve complex orchestration
      // with the database cluster management system
      
      // For now, we'll just update our internal routing
      const oldPrimary = this.primaryPool;
      this.primaryPool = replica.pool;
      
      // Remove from replicas
      this.replicas.delete(replicaId);
      
      // Clean up old primary
      await oldPrimary.end();
      
      this.logger.info('Replica promoted to primary', { replicaId });
    } catch (error) {
      this.logger.error('Failed to promote replica', {
        replicaId,
        error: error.message
      });
      throw error;
    }
  }
}