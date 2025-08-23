/**
 * Query Monitor - Database query performance monitoring
 * 
 * Monitors and tracks database query performance, slow queries,
 * and provides insights for optimization.
 */

import { Logger } from '../../logging/index.js';

export interface QueryMetrics {
  queryText: string;
  duration: number;
  timestamp: Date;
  parameters?: any[];
  resultCount?: number;
  error?: string;
  connectionId?: string;
  userId?: string;
}

export interface QueryStats {
  totalQueries: number;
  averageDuration: number;
  slowQueries: QueryMetrics[];
  errorCount: number;
  queryPatterns: Map<string, {
    count: number;
    totalDuration: number;
    averageDuration: number;
    lastExecuted: Date;
  }>;
}

export class QueryMonitor {
  private readonly logger: Logger;
  private readonly metrics: QueryMetrics[] = [];
  private readonly slowQueryThreshold: number;
  private readonly maxMetricsRetention: number;
  
  constructor(
    logger: Logger,
    slowQueryThreshold = 1000, // 1 second
    maxMetricsRetention = 10000 // Keep last 10k queries
  ) {
    this.logger = logger;
    this.slowQueryThreshold = slowQueryThreshold;
    this.maxMetricsRetention = maxMetricsRetention;
  }

  /**
   * Record a query execution
   */
  recordQuery(metrics: QueryMetrics): void {
    this.metrics.push(metrics);
    
    // Log slow queries
    if (metrics.duration > this.slowQueryThreshold) {
      this.logger.warn('Slow query detected', {
        duration: metrics.duration,
        query: metrics.queryText.substring(0, 200),
        parameters: metrics.parameters
      });
    }

    // Log query errors
    if (metrics.error) {
      this.logger.error('Query execution error', {
        query: metrics.queryText.substring(0, 200),
        error: metrics.error,
        parameters: metrics.parameters
      });
    }

    // Cleanup old metrics
    if (this.metrics.length > this.maxMetricsRetention) {
      this.metrics.shift();
    }
  }

  /**
   * Get query statistics
   */
  getStats(): QueryStats {
    const totalQueries = this.metrics.length;
    const averageDuration = totalQueries > 0 
      ? this.metrics.reduce((sum, m) => sum + m.duration, 0) / totalQueries 
      : 0;
    
    const slowQueries = this.metrics.filter(m => m.duration > this.slowQueryThreshold);
    const errorCount = this.metrics.filter(m => m.error).length;
    
    // Analyze query patterns
    const queryPatterns = new Map<string, {
      count: number;
      totalDuration: number;
      averageDuration: number;
      lastExecuted: Date;
    }>();

    this.metrics.forEach(metric => {
      // Normalize query for pattern matching (remove values, keep structure)
      const pattern = this.normalizeQuery(metric.queryText);
      
      const existing = queryPatterns.get(pattern) || {
        count: 0,
        totalDuration: 0,
        averageDuration: 0,
        lastExecuted: new Date(0)
      };

      existing.count++;
      existing.totalDuration += metric.duration;
      existing.averageDuration = existing.totalDuration / existing.count;
      existing.lastExecuted = metric.timestamp > existing.lastExecuted 
        ? metric.timestamp 
        : existing.lastExecuted;

      queryPatterns.set(pattern, existing);
    });

    return {
      totalQueries,
      averageDuration,
      slowQueries,
      errorCount,
      queryPatterns
    };
  }

  /**
   * Get slow queries over a time period
   */
  getSlowQueries(sinceMinutes = 60): QueryMetrics[] {
    const since = new Date(Date.now() - (sinceMinutes * 60 * 1000));
    return this.metrics.filter(m => 
      m.duration > this.slowQueryThreshold && 
      m.timestamp >= since
    );
  }

  /**
   * Get most frequent queries
   */
  getMostFrequentQueries(limit = 10): Array<{
    pattern: string;
    count: number;
    averageDuration: number;
    lastExecuted: Date;
  }> {
    const stats = this.getStats();
    return Array.from(stats.queryPatterns.entries())
      .map(([pattern, data]) => ({ pattern, ...data }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics.length = 0;
  }

  /**
   * Normalize query for pattern matching
   */
  private normalizeQuery(query: string): string {
    return query
      .replace(/\$\d+/g, '?')  // Replace parameter placeholders
      .replace(/'[^']*'/g, '?') // Replace string literals
      .replace(/\b\d+\b/g, '?') // Replace numbers
      .replace(/\s+/g, ' ')     // Normalize whitespace
      .trim()
      .toLowerCase();
  }
}

export default QueryMonitor;