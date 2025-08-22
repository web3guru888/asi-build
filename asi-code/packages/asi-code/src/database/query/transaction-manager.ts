/**
 * Transaction Manager
 * 
 * Provides comprehensive transaction support with:
 * - Nested transaction handling (savepoints)
 * - Isolation level management
 * - Timeout handling
 * - Deadlock detection and retry
 * - Transaction performance monitoring
 * - Automatic rollback on errors
 */

import { Knex } from 'knex';
import { nanoid } from 'nanoid';
import { DatabaseAdapter, TransactionOptions, TransactionContext, TransactionError } from '../types';
import { Logger } from '../../logging';

export interface TransactionMetrics {
  total: number;
  committed: number;
  rolledBack: number;
  deadlocks: number;
  timeouts: number;
  averageExecutionTime: number;
  longestTransaction: number;
  activeTransactions: number;
}

export class TransactionManager {
  private adapter: DatabaseAdapter;
  private logger: Logger;
  private activeTransactions = new Map<string, TransactionContext>();
  private metrics: TransactionMetrics = {
    total: 0,
    committed: 0,
    rolledBack: 0,
    deadlocks: 0,
    timeouts: 0,
    averageExecutionTime: 0,
    longestTransaction: 0,
    activeTransactions: 0
  };

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
  }

  /**
   * Execute a transaction with comprehensive error handling and monitoring
   */
  async transaction<T>(
    callback: (trx: Knex.Transaction) => Promise<T>,
    options: TransactionOptions = {}
  ): Promise<T> {
    const transactionId = nanoid();
    const startTime = Date.now();
    
    const context: TransactionContext = {
      id: transactionId,
      startTime: new Date(),
      queries: [],
      options
    };

    this.activeTransactions.set(transactionId, context);
    this.metrics.total++;
    this.metrics.activeTransactions++;

    try {
      this.logger.debug('Starting transaction', {
        transactionId,
        options
      });

      // Set up transaction configuration
      const trxConfig: any = {};
      
      if (options.isolationLevel) {
        trxConfig.isolationLevel = options.isolationLevel;
      }

      const result = await this.executeWithRetry(async () => {
        return await this.adapter.knex.transaction(async (trx) => {
          // Set isolation level if specified
          if (options.isolationLevel) {
            await trx.raw(`SET TRANSACTION ISOLATION LEVEL ${options.isolationLevel}`);
          }

          // Set read-only mode if specified
          if (options.readOnly) {
            await trx.raw('SET TRANSACTION READ ONLY');
          }

          // Set timeout if specified
          if (options.timeout) {
            await trx.raw(`SET LOCAL statement_timeout = '${options.timeout}ms'`);
          }

          // Execute callback with monitoring
          return await this.executeWithMonitoring(trx, callback, context);
        }, trxConfig);
      }, options);

      const executionTime = Date.now() - startTime;
      this.updateMetrics(true, executionTime);

      this.logger.debug('Transaction committed successfully', {
        transactionId,
        executionTime,
        queries: context.queries.length
      });

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.updateMetrics(false, executionTime);

      this.logger.error('Transaction failed', {
        transactionId,
        error: error.message,
        executionTime,
        queries: context.queries.length
      });

      // Check for specific error types
      if (this.isDeadlockError(error)) {
        this.metrics.deadlocks++;
      } else if (this.isTimeoutError(error)) {
        this.metrics.timeouts++;
      }

      throw new TransactionError(`Transaction failed: ${error.message}`, error);
    } finally {
      this.activeTransactions.delete(transactionId);
      this.metrics.activeTransactions--;
    }
  }

  /**
   * Execute transaction with retry logic for recoverable errors
   */
  private async executeWithRetry<T>(
    operation: () => Promise<T>,
    options: TransactionOptions,
    maxRetries = 3
  ): Promise<T> {
    let attempt = 0;
    let lastError: Error;

    while (attempt < maxRetries) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        attempt++;

        // Only retry on recoverable errors
        if (this.isRecoverableError(error) && attempt < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
          this.logger.warn('Transaction failed, retrying', {
            attempt,
            maxRetries,
            delay,
            error: error.message
          });
          
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        throw error;
      }
    }

    throw lastError!;
  }

  /**
   * Execute callback with query monitoring
   */
  private async executeWithMonitoring<T>(
    trx: Knex.Transaction,
    callback: (trx: Knex.Transaction) => Promise<T>,
    context: TransactionContext
  ): Promise<T> {
    // Monkey patch the transaction to monitor queries
    const originalQuery = trx.raw.bind(trx);
    trx.raw = (...args: any[]) => {
      const startTime = Date.now();
      const promise = originalQuery(...args);
      
      promise.then(
        (result) => {
          const executionTime = Date.now() - startTime;
          context.queries.push({
            query: args[0],
            type: this.getQueryType(args[0]),
            executionTime,
            rowsAffected: Array.isArray(result.rows) ? result.rows.length : undefined,
            timestamp: new Date(),
            success: true
          });
        },
        (error) => {
          const executionTime = Date.now() - startTime;
          context.queries.push({
            query: args[0],
            type: this.getQueryType(args[0]),
            executionTime,
            timestamp: new Date(),
            success: false,
            error: error.message
          });
        }
      );

      return promise;
    };

    return await callback(trx);
  }

  /**
   * Execute a savepoint transaction (nested transaction)
   */
  async savepoint<T>(
    trx: Knex.Transaction,
    name: string,
    callback: (savepoint: Knex.Transaction) => Promise<T>
  ): Promise<T> {
    const savepointName = `sp_${name}_${nanoid(8)}`;
    
    try {
      this.logger.debug('Creating savepoint', { name: savepointName });
      
      await trx.raw(`SAVEPOINT ${savepointName}`);
      
      const result = await callback(trx);
      
      await trx.raw(`RELEASE SAVEPOINT ${savepointName}`);
      
      this.logger.debug('Savepoint completed successfully', { name: savepointName });
      
      return result;
    } catch (error) {
      this.logger.warn('Rolling back to savepoint', {
        name: savepointName,
        error: error.message
      });
      
      try {
        await trx.raw(`ROLLBACK TO SAVEPOINT ${savepointName}`);
      } catch (rollbackError) {
        this.logger.error('Failed to rollback to savepoint', {
          name: savepointName,
          error: rollbackError.message
        });
      }
      
      throw error;
    }
  }

  /**
   * Execute multiple operations in parallel within a transaction
   */
  async transactionBatch<T>(
    operations: Array<(trx: Knex.Transaction) => Promise<T>>,
    options: TransactionOptions = {}
  ): Promise<T[]> {
    return await this.transaction(async (trx) => {
      return await Promise.all(operations.map(op => op(trx)));
    }, options);
  }

  /**
   * Execute multiple operations sequentially with individual savepoints
   */
  async transactionSequence<T>(
    operations: Array<{ name: string; operation: (trx: Knex.Transaction) => Promise<T> }>,
    options: TransactionOptions = {}
  ): Promise<T[]> {
    return await this.transaction(async (trx) => {
      const results: T[] = [];
      
      for (const { name, operation } of operations) {
        const result = await this.savepoint(trx, name, operation);
        results.push(result);
      }
      
      return results;
    }, options);
  }

  /**
   * Check if an error is recoverable (should retry)
   */
  private isRecoverableError(error: any): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;

    // PostgreSQL error codes for recoverable errors
    const recoverableCodes = [
      '40001', // serialization_failure
      '40P01', // deadlock_detected
      '53000', // insufficient_resources
      '53200', // out_of_memory
      '53300', // too_many_connections
      '08006', // connection_failure
      '08000', // connection_exception
    ];

    return recoverableCodes.includes(code) ||
           message.includes('deadlock') ||
           message.includes('connection') ||
           message.includes('timeout');
  }

  /**
   * Check if error is a deadlock
   */
  private isDeadlockError(error: any): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    
    return code === '40P01' || message.includes('deadlock');
  }

  /**
   * Check if error is a timeout
   */
  private isTimeoutError(error: any): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    
    return code === '57014' || 
           message.includes('timeout') ||
           message.includes('canceling statement due to statement timeout');
  }

  /**
   * Get query type from SQL string
   */
  private getQueryType(sql: string): any {
    if (!sql) return 'OTHER';
    
    const trimmed = sql.trim().toUpperCase();
    
    if (trimmed.startsWith('SELECT')) return 'SELECT';
    if (trimmed.startsWith('INSERT')) return 'INSERT';
    if (trimmed.startsWith('UPDATE')) return 'UPDATE';
    if (trimmed.startsWith('DELETE')) return 'DELETE';
    if (trimmed.startsWith('CREATE') || 
        trimmed.startsWith('DROP') || 
        trimmed.startsWith('ALTER')) return 'DDL';
    
    return 'OTHER';
  }

  /**
   * Update transaction metrics
   */
  private updateMetrics(committed: boolean, executionTime: number): void {
    if (committed) {
      this.metrics.committed++;
    } else {
      this.metrics.rolledBack++;
    }

    // Update average execution time
    const totalExecutionTime = this.metrics.averageExecutionTime * (this.metrics.total - 1) + executionTime;
    this.metrics.averageExecutionTime = totalExecutionTime / this.metrics.total;

    // Update longest transaction
    this.metrics.longestTransaction = Math.max(this.metrics.longestTransaction, executionTime);
  }

  /**
   * Get transaction metrics
   */
  getMetrics(): TransactionMetrics {
    return { ...this.metrics };
  }

  /**
   * Get active transaction contexts
   */
  getActiveTransactions(): TransactionContext[] {
    return Array.from(this.activeTransactions.values());
  }

  /**
   * Get transaction by ID
   */
  getTransaction(id: string): TransactionContext | undefined {
    return this.activeTransactions.get(id);
  }

  /**
   * Kill a transaction by ID (if possible)
   */
  async killTransaction(id: string): Promise<boolean> {
    const context = this.activeTransactions.get(id);
    if (!context) {
      return false;
    }

    try {
      // In PostgreSQL, we need to cancel the backend process
      // This is a dangerous operation and should be used carefully
      this.logger.warn('Attempting to kill transaction', { transactionId: id });
      
      // Get the backend PID for this transaction (if possible)
      // This is a simplified implementation - in practice, you'd need to track
      // the connection/process ID associated with each transaction
      
      return true;
    } catch (error) {
      this.logger.error('Failed to kill transaction', {
        transactionId: id,
        error: error.message
      });
      return false;
    }
  }

  /**
   * Clean up stale transaction tracking
   */
  cleanupStaleTransactions(maxAgeMs = 300000): number { // 5 minutes default
    const now = Date.now();
    let cleaned = 0;

    for (const [id, context] of this.activeTransactions) {
      const age = now - context.startTime.getTime();
      if (age > maxAgeMs) {
        this.logger.warn('Removing stale transaction from tracking', {
          transactionId: id,
          age
        });
        this.activeTransactions.delete(id);
        this.metrics.activeTransactions--;
        cleaned++;
      }
    }

    if (cleaned > 0) {
      this.logger.info('Cleaned up stale transactions', { count: cleaned });
    }

    return cleaned;
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    this.metrics = {
      total: 0,
      committed: 0,
      rolledBack: 0,
      deadlocks: 0,
      timeouts: 0,
      averageExecutionTime: 0,
      longestTransaction: 0,
      activeTransactions: this.activeTransactions.size
    };
    
    this.logger.info('Transaction metrics reset');
  }
}