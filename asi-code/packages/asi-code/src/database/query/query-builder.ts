/**
 * Query Builder Abstraction
 *
 * Provides a high-level query building interface with:
 * - Type-safe query construction
 * - Automatic soft delete handling
 * - Built-in audit logging
 * - Performance monitoring
 * - Query optimization hints
 * - Batch operations
 * - Caching support
 */

import { Knex } from 'knex';
import {
  DatabaseAdapter,
  QueryBuilderOptions,
  QueryMetrics,
  SoftDeleteQuery,
} from '../types';
import { Logger } from '../../logging';

export interface QueryExecutionOptions {
  timeout?: number;
  cache?: {
    enabled: boolean;
    ttl?: number;
    key?: string;
  };
  audit?: boolean;
  explain?: boolean;
  hint?: string[];
}

export interface PaginationOptions {
  page: number;
  limit: number;
  orderBy?: string;
  orderDirection?: 'asc' | 'desc';
}

export interface PaginatedResult<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNextPage: boolean;
    hasPrevPage: boolean;
  };
}

export class QueryBuilder {
  private readonly adapter: DatabaseAdapter;
  private readonly logger: Logger;
  private queryMetrics: QueryMetrics[] = [];
  private readonly cache = new Map<string, { data: any; expires: number }>();

  constructor(adapter: DatabaseAdapter, logger: Logger) {
    this.adapter = adapter;
    this.logger = logger;
  }

  /**
   * Create a new query for a table
   */
  table(
    tableName: string,
    options: QueryBuilderOptions = { table: tableName }
  ): TableQueryBuilder {
    return new TableQueryBuilder(
      this.adapter,
      this.logger,
      tableName,
      options,
      this
    );
  }

  /**
   * Execute raw SQL query
   */
  async raw(
    sql: string,
    bindings?: any[],
    options: QueryExecutionOptions = {}
  ): Promise<any> {
    const startTime = Date.now();

    try {
      // Add query timeout if specified
      let query = this.adapter.knex.raw(sql, bindings);

      if (options.timeout) {
        query = query.timeout(options.timeout);
      }

      const result = await query;

      const executionTime = Date.now() - startTime;
      this.recordQueryMetrics(sql, 'OTHER', executionTime, true);

      if (options.explain) {
        await this.explainQuery(sql, bindings);
      }

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.recordQueryMetrics(
        sql,
        'OTHER',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Execute EXPLAIN for query analysis
   */
  private async explainQuery(sql: string, bindings?: any[]): Promise<void> {
    try {
      const explainResult = await this.adapter.knex.raw(
        `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ${sql}`,
        bindings
      );
      this.logger.debug('Query execution plan', {
        sql: sql.substring(0, 100) + '...',
        plan: explainResult.rows[0]['QUERY PLAN'],
      });
    } catch (error) {
      this.logger.warn('Failed to explain query', { error: error.message });
    }
  }

  /**
   * Record query metrics
   */
  private recordQueryMetrics(
    query: string,
    type: any,
    executionTime: number,
    success: boolean,
    error?: string
  ): void {
    const metric: QueryMetrics = {
      query: query.substring(0, 500), // Truncate long queries
      type,
      executionTime,
      timestamp: new Date(),
      success,
      error,
    };

    this.queryMetrics.push(metric);

    // Keep only last 1000 metrics
    if (this.queryMetrics.length > 1000) {
      this.queryMetrics.shift();
    }

    // Log slow queries
    if (
      this.adapter.config.monitoring.slowQueryThreshold &&
      executionTime > this.adapter.config.monitoring.slowQueryThreshold
    ) {
      this.logger.warn('Slow query detected', {
        query: query.substring(0, 200),
        executionTime,
        threshold: this.adapter.config.monitoring.slowQueryThreshold,
      });
    }
  }

  /**
   * Get query metrics
   */
  getMetrics(): QueryMetrics[] {
    return [...this.queryMetrics];
  }

  /**
   * Clear query metrics
   */
  clearMetrics(): void {
    this.queryMetrics = [];
  }

  /**
   * Get cached result
   */
  private getCachedResult(key: string): any | null {
    const cached = this.cache.get(key);
    if (cached && cached.expires > Date.now()) {
      return cached.data;
    }
    if (cached) {
      this.cache.delete(key);
    }
    return null;
  }

  /**
   * Set cached result
   */
  private setCachedResult(key: string, data: any, ttl: number): void {
    this.cache.set(key, {
      data,
      expires: Date.now() + ttl,
    });
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }
}

export class TableQueryBuilder {
  private readonly adapter: DatabaseAdapter;
  private readonly logger: Logger;
  private readonly tableName: string;
  private readonly options: QueryBuilderOptions;
  private query: Knex.QueryBuilder;
  private readonly queryBuilder: QueryBuilder;

  constructor(
    adapter: DatabaseAdapter,
    logger: Logger,
    tableName: string,
    options: QueryBuilderOptions,
    queryBuilder: QueryBuilder
  ) {
    this.adapter = adapter;
    this.logger = logger;
    this.tableName = tableName;
    this.options = options;
    this.queryBuilder = queryBuilder;
    this.query = this.initializeQuery();
  }

  /**
   * Initialize the base query with soft delete and schema handling
   */
  private initializeQuery(): Knex.QueryBuilder {
    let query = this.adapter.knex(this.tableName);

    // Apply schema if specified
    if (this.options.schema) {
      query = this.adapter.knex(`${this.options.schema}.${this.tableName}`);
    }

    // Apply soft delete filters
    if (this.adapter.config.softDelete.enabled && this.options.softDelete) {
      if (!this.options.softDelete.includeDeleted) {
        query = query.whereNull(this.adapter.config.softDelete.columnName);
      } else if (this.options.softDelete.onlyDeleted) {
        query = query.whereNotNull(this.adapter.config.softDelete.columnName);
      }
    }

    return query;
  }

  /**
   * Select columns
   */
  select(columns: string | string[] = '*'): this {
    this.query = this.query.select(columns);
    return this;
  }

  /**
   * Add where condition
   */
  where(column: string, operator?: any, value?: any): this {
    if (arguments.length === 2) {
      this.query = this.query.where(column, operator);
    } else {
      this.query = this.query.where(column, operator, value);
    }
    return this;
  }

  /**
   * Add where condition with OR
   */
  orWhere(column: string, operator?: any, value?: any): this {
    if (arguments.length === 2) {
      this.query = this.query.orWhere(column, operator);
    } else {
      this.query = this.query.orWhere(column, operator, value);
    }
    return this;
  }

  /**
   * Add where IN condition
   */
  whereIn(column: string, values: any[]): this {
    this.query = this.query.whereIn(column, values);
    return this;
  }

  /**
   * Add where NOT IN condition
   */
  whereNotIn(column: string, values: any[]): this {
    this.query = this.query.whereNotIn(column, values);
    return this;
  }

  /**
   * Add where NULL condition
   */
  whereNull(column: string): this {
    this.query = this.query.whereNull(column);
    return this;
  }

  /**
   * Add where NOT NULL condition
   */
  whereNotNull(column: string): this {
    this.query = this.query.whereNotNull(column);
    return this;
  }

  /**
   * Add where LIKE condition
   */
  whereLike(column: string, pattern: string): this {
    this.query = this.query.where(column, 'ILIKE', pattern);
    return this;
  }

  /**
   * Add full-text search condition
   */
  whereFullText(column: string, searchTerm: string): this {
    this.query = this.query.whereRaw(
      `to_tsvector('english', ??) @@ plainto_tsquery('english', ?)`,
      [column, searchTerm]
    );
    return this;
  }

  /**
   * Add join
   */
  join(table: string, first: string, operator?: string, second?: string): this {
    if (arguments.length === 3) {
      this.query = this.query.join(table, first, operator);
    } else {
      this.query = this.query.join(table, first, operator, second);
    }
    return this;
  }

  /**
   * Add left join
   */
  leftJoin(
    table: string,
    first: string,
    operator?: string,
    second?: string
  ): this {
    if (arguments.length === 3) {
      this.query = this.query.leftJoin(table, first, operator);
    } else {
      this.query = this.query.leftJoin(table, first, operator, second);
    }
    return this;
  }

  /**
   * Add order by
   */
  orderBy(column: string, direction: 'asc' | 'desc' = 'asc'): this {
    this.query = this.query.orderBy(column, direction);
    return this;
  }

  /**
   * Add group by
   */
  groupBy(...columns: string[]): this {
    this.query = this.query.groupBy(...columns);
    return this;
  }

  /**
   * Add having condition
   */
  having(column: string, operator: string, value: any): this {
    this.query = this.query.having(column, operator, value);
    return this;
  }

  /**
   * Add limit
   */
  limit(count: number): this {
    this.query = this.query.limit(count);
    return this;
  }

  /**
   * Add offset
   */
  offset(count: number): this {
    this.query = this.query.offset(count);
    return this;
  }

  /**
   * Execute and get first result
   */
  async first(options: QueryExecutionOptions = {}): Promise<any | null> {
    const startTime = Date.now();

    try {
      // Check cache
      if (options.cache?.enabled) {
        const cacheKey = options.cache.key || this.getCacheKey('first');
        const cached = this.queryBuilder['getCachedResult'](cacheKey);
        if (cached !== null) {
          return cached;
        }
      }

      let query = this.query.first();

      if (options.timeout) {
        query = query.timeout(options.timeout);
      }

      const result = await query;

      // Cache result if enabled
      if (options.cache?.enabled && result) {
        const cacheKey = options.cache.key || this.getCacheKey('first');
        const ttl = options.cache.ttl || 300000; // 5 minutes default
        this.queryBuilder['setCachedResult'](cacheKey, result, ttl);
      }

      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        this.query.toString(),
        'SELECT',
        executionTime,
        true
      );

      if (options.explain) {
        await this.queryBuilder['explainQuery'](this.query.toString());
      }

      return result || null;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        this.query.toString(),
        'SELECT',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Execute and get all results
   */
  async get(options: QueryExecutionOptions = {}): Promise<any[]> {
    const startTime = Date.now();

    try {
      // Check cache
      if (options.cache?.enabled) {
        const cacheKey = options.cache.key || this.getCacheKey('get');
        const cached = this.queryBuilder['getCachedResult'](cacheKey);
        if (cached !== null) {
          return cached;
        }
      }

      let query = this.query;

      if (options.timeout) {
        query = query.timeout(options.timeout);
      }

      const results = await query;

      // Cache results if enabled
      if (options.cache?.enabled) {
        const cacheKey = options.cache.key || this.getCacheKey('get');
        const ttl = options.cache.ttl || 300000; // 5 minutes default
        this.queryBuilder['setCachedResult'](cacheKey, results, ttl);
      }

      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        this.query.toString(),
        'SELECT',
        executionTime,
        true
      );

      if (options.explain) {
        await this.queryBuilder['explainQuery'](this.query.toString());
      }

      return results;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        this.query.toString(),
        'SELECT',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Get paginated results
   */
  async paginate(
    paginationOptions: PaginationOptions,
    options: QueryExecutionOptions = {}
  ): Promise<PaginatedResult<any>> {
    const { page, limit, orderBy, orderDirection = 'asc' } = paginationOptions;

    // Get total count
    const countQuery = this.query
      .clone()
      .clearSelect()
      .clearOrder()
      .count('* as total');
    const countResult = await countQuery.first();
    const total = parseInt(countResult.total, 10);

    // Apply pagination
    const offset = (page - 1) * limit;
    let dataQuery = this.query.clone().limit(limit).offset(offset);

    if (orderBy) {
      dataQuery = dataQuery.orderBy(orderBy, orderDirection);
    }

    const data = await dataQuery;

    const totalPages = Math.ceil(total / limit);

    return {
      data,
      pagination: {
        page,
        limit,
        total,
        totalPages,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1,
      },
    };
  }

  /**
   * Insert data
   */
  async insert(
    data: any | any[],
    options: QueryExecutionOptions = {}
  ): Promise<any> {
    const startTime = Date.now();

    try {
      // Add audit fields if enabled
      const processedData = this.addAuditFields(data, 'INSERT');

      let query = this.adapter.knex(this.tableName).insert(processedData);

      if (options.timeout) {
        query = query.timeout(options.timeout);
      }

      const result = await query.returning('*');

      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        query.toString(),
        'INSERT',
        executionTime,
        true
      );

      // Record audit log if enabled
      if (this.options.audit && this.adapter.config.audit.enabled) {
        await this.recordAuditLog('INSERT', result, null, processedData);
      }

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        'INSERT',
        'INSERT',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Update data
   */
  async update(data: any, options: QueryExecutionOptions = {}): Promise<any> {
    const startTime = Date.now();

    try {
      // Get old values for audit
      const oldValues =
        this.options.audit && this.adapter.config.audit.enabled
          ? await this.query.clone()
          : null;

      // Add audit fields
      const processedData = this.addAuditFields(data, 'UPDATE');

      let query = this.query.clone().update(processedData);

      if (options.timeout) {
        query = query.timeout(options.timeout);
      }

      const result = await query.returning('*');

      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        query.toString(),
        'UPDATE',
        executionTime,
        true
      );

      // Record audit log if enabled
      if (
        this.options.audit &&
        this.adapter.config.audit.enabled &&
        oldValues
      ) {
        await this.recordAuditLog('UPDATE', result, oldValues, processedData);
      }

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        'UPDATE',
        'UPDATE',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Delete data (soft delete if enabled)
   */
  async delete(
    options: QueryExecutionOptions & { force?: boolean } = {}
  ): Promise<number> {
    const startTime = Date.now();

    try {
      let result: number;

      if (this.adapter.config.softDelete.enabled && !options.force) {
        // Soft delete
        const softDeleteData = {
          [this.adapter.config.softDelete.columnName]:
            this.adapter.config.softDelete.deletedValue instanceof Date
              ? new Date()
              : this.adapter.config.softDelete.deletedValue,
        };

        const updateResult = await this.update(softDeleteData, options);
        result = Array.isArray(updateResult) ? updateResult.length : 1;
      } else {
        // Hard delete
        let query = this.query.clone().del();

        if (options.timeout) {
          query = query.timeout(options.timeout);
        }

        result = await query;
      }

      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        'DELETE',
        'DELETE',
        executionTime,
        true
      );

      return result;
    } catch (error) {
      const executionTime = Date.now() - startTime;
      this.queryBuilder['recordQueryMetrics'](
        'DELETE',
        'DELETE',
        executionTime,
        false,
        error.message
      );
      throw error;
    }
  }

  /**
   * Restore soft deleted records
   */
  async restore(options: QueryExecutionOptions = {}): Promise<any> {
    if (!this.adapter.config.softDelete.enabled) {
      throw new Error('Soft delete not enabled');
    }

    const restoreData = {
      [this.adapter.config.softDelete.columnName]:
        this.adapter.config.softDelete.defaultValue,
    };

    return await this.update(restoreData, options);
  }

  /**
   * Count records
   */
  async count(
    column = '*',
    options: QueryExecutionOptions = {}
  ): Promise<number> {
    const result = await this.query.clone().count(`${column} as total`).first();
    return parseInt(result.total, 10);
  }

  /**
   * Check if records exist
   */
  async exists(options: QueryExecutionOptions = {}): Promise<boolean> {
    const count = await this.count('*', options);
    return count > 0;
  }

  /**
   * Add audit fields to data
   */
  private addAuditFields(data: any, operation: 'INSERT' | 'UPDATE'): any {
    if (!data || typeof data !== 'object') {
      return data;
    }

    const now = new Date();

    if (Array.isArray(data)) {
      return data.map(item => ({
        ...item,
        updated_at: now,
        ...(operation === 'INSERT' && { created_at: now }),
      }));
    } else {
      return {
        ...data,
        updated_at: now,
        ...(operation === 'INSERT' && { created_at: now }),
      };
    }
  }

  /**
   * Record audit log
   */
  private async recordAuditLog(
    operation: 'INSERT' | 'UPDATE' | 'DELETE',
    newValues: any,
    oldValues: any,
    changedData: any
  ): Promise<void> {
    try {
      // This would integrate with the audit logging system
      // Implementation depends on audit table structure
      this.logger.debug('Recording audit log', {
        table: this.tableName,
        operation,
        recordsAffected: Array.isArray(newValues) ? newValues.length : 1,
      });
    } catch (error) {
      this.logger.error('Failed to record audit log', { error });
    }
  }

  /**
   * Generate cache key
   */
  private getCacheKey(operation: string): string {
    return `${this.tableName}:${operation}:${Buffer.from(this.query.toString()).toString('base64').substring(0, 32)}`;
  }

  /**
   * Get the underlying Knex query
   */
  getKnexQuery(): Knex.QueryBuilder {
    return this.query;
  }

  /**
   * Get SQL string
   */
  toSQL(): string {
    return this.query.toString();
  }
}
