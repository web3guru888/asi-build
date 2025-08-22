/**
 * Metric Aggregation System for ASI-Code
 * 
 * Provides real-time and historical metric aggregation:
 * - Time-series data aggregation
 * - Multi-dimensional metric rollups
 * - Statistical calculations (percentiles, averages, etc.)
 * - Metric downsampling for long-term storage
 * - Cross-component metric correlation
 * - Custom aggregation functions
 */

import { EventEmitter } from 'eventemitter3';
import type { PrometheusMetrics } from '../metrics/index.js';

export interface MetricPoint {
  timestamp: number;
  value: number;
  labels: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface AggregatedMetric {
  name: string;
  timeWindow: number;
  startTime: number;
  endTime: number;
  count: number;
  sum: number;
  min: number;
  max: number;
  avg: number;
  median: number;
  p95: number;
  p99: number;
  stdDev: number;
  rate: number;
  labels: Record<string, string>;
  metadata: Record<string, any>;
}

export interface AggregationRule {
  id: string;
  name: string;
  metricPattern: string; // Regex pattern to match metric names
  timeWindows: number[]; // Time windows in seconds
  aggregationFunctions: AggregationFunction[];
  groupBy: string[]; // Label names to group by
  enabled: boolean;
  retentionPeriod: number; // How long to keep aggregated data
  metadata?: Record<string, any>;
}

export type AggregationFunction = 
  | 'sum' 
  | 'avg' 
  | 'min' 
  | 'max' 
  | 'count' 
  | 'rate' 
  | 'median' 
  | 'p95' 
  | 'p99' 
  | 'stddev';

export interface TimeSeriesData {
  metricName: string;
  timeWindow: number;
  points: MetricPoint[];
  aggregations: Map<string, AggregatedMetric[]>; // groupBy key -> aggregated metrics
}

export interface MetricCorrelation {
  metric1: string;
  metric2: string;
  correlation: number;
  timeWindow: number;
  significance: number;
  timestamp: number;
}

export class MetricAggregator extends EventEmitter {
  private metrics: Map<string, TimeSeriesData> = new Map();
  private rules: Map<string, AggregationRule> = new Map();
  private correlations: Map<string, MetricCorrelation[]> = new Map();
  private prometheusMetrics: PrometheusMetrics;
  private maxDataPoints = 10000;
  private aggregationInterval = 60000; // 1 minute
  
  constructor(prometheusMetrics: PrometheusMetrics) {
    super();
    this.prometheusMetrics = prometheusMetrics;
    this.initializeDefaultRules();
    this.startAggregationLoop();
    this.startCleanupLoop();
  }
  
  private initializeDefaultRules(): void {
    // HTTP request aggregations
    this.addRule({
      id: 'http-requests-1m',
      name: 'HTTP Requests (1 minute)',
      metricPattern: 'asi_code_http_requests_total',
      timeWindows: [60], // 1 minute
      aggregationFunctions: ['sum', 'rate'],
      groupBy: ['method', 'status_code', 'route'],
      enabled: true,
      retentionPeriod: 86400, // 24 hours
    });
    
    this.addRule({
      id: 'http-requests-5m',
      name: 'HTTP Requests (5 minutes)',
      metricPattern: 'asi_code_http_requests_total',
      timeWindows: [300], // 5 minutes
      aggregationFunctions: ['sum', 'rate', 'avg'],
      groupBy: ['method', 'status_code'],
      enabled: true,
      retentionPeriod: 604800, // 7 days
    });
    
    // Response time aggregations
    this.addRule({
      id: 'response-time-1m',
      name: 'Response Time (1 minute)',
      metricPattern: 'asi_code_http_request_duration_seconds',
      timeWindows: [60],
      aggregationFunctions: ['avg', 'median', 'p95', 'p99', 'max'],
      groupBy: ['method', 'route'],
      enabled: true,
      retentionPeriod: 86400,
    });
    
    // Error rate aggregations
    this.addRule({
      id: 'error-rate-1m',
      name: 'Error Rate (1 minute)',
      metricPattern: 'asi_code_errors_total',
      timeWindows: [60, 300, 900], // 1m, 5m, 15m
      aggregationFunctions: ['sum', 'rate'],
      groupBy: ['error_type', 'component'],
      enabled: true,
      retentionPeriod: 604800,
    });
    
    // Business metrics aggregations
    this.addRule({
      id: 'session-metrics-5m',
      name: 'Session Metrics (5 minutes)',
      metricPattern: 'asi_code_sessions_.*',
      timeWindows: [300],
      aggregationFunctions: ['sum', 'rate', 'avg'],
      groupBy: ['session_type', 'provider'],
      enabled: true,
      retentionPeriod: 2592000, // 30 days
    });
    
    this.addRule({
      id: 'tool-metrics-1m',
      name: 'Tool Execution Metrics (1 minute)',
      metricPattern: 'asi_code_tool_.*',
      timeWindows: [60],
      aggregationFunctions: ['sum', 'rate', 'avg', 'median'],
      groupBy: ['tool_name', 'status'],
      enabled: true,
      retentionPeriod: 604800,
    });
    
    // System metrics aggregations
    this.addRule({
      id: 'system-metrics-1m',
      name: 'System Metrics (1 minute)',
      metricPattern: 'asi_code_system_.*',
      timeWindows: [60],
      aggregationFunctions: ['avg', 'max', 'min'],
      groupBy: ['instance'],
      enabled: true,
      retentionPeriod: 604800,
    });
    
    // Performance metrics aggregations
    this.addRule({
      id: 'performance-metrics-1m',
      name: 'Performance Metrics (1 minute)',
      metricPattern: 'performance_.*',
      timeWindows: [60, 300],
      aggregationFunctions: ['avg', 'max', 'p95'],
      groupBy: ['component'],
      enabled: true,
      retentionPeriod: 259200, // 3 days
    });
  }
  
  addRule(rule: AggregationRule): void {
    this.rules.set(rule.id, rule);
    this.emit('rule-added', rule);
  }
  
  removeRule(ruleId: string): boolean {
    const deleted = this.rules.delete(ruleId);
    if (deleted) {
      this.emit('rule-removed', ruleId);
    }
    return deleted;
  }
  
  // Core aggregation methods
  
  addMetricPoint(metricName: string, point: MetricPoint): void {
    let timeSeries = this.metrics.get(metricName);
    
    if (!timeSeries) {
      timeSeries = {
        metricName,
        timeWindow: 3600, // Default 1 hour window
        points: [],
        aggregations: new Map(),
      };
      this.metrics.set(metricName, timeSeries);
    }
    
    timeSeries.points.push(point);
    
    // Keep only recent points
    const cutoff = Date.now() - (timeSeries.timeWindow * 1000);
    timeSeries.points = timeSeries.points.filter(p => p.timestamp > cutoff);
    
    // Limit total points
    if (timeSeries.points.length > this.maxDataPoints) {
      timeSeries.points = timeSeries.points.slice(-this.maxDataPoints);
    }
    
    this.emit('metric-point-added', { metricName, point });
  }
  
  aggregateMetrics(timeWindow: number): Map<string, AggregatedMetric[]> {
    const results = new Map<string, AggregatedMetric[]>();
    const now = Date.now();
    const windowStart = now - (timeWindow * 1000);
    
    for (const [metricName, timeSeries] of this.metrics) {
      const applicableRules = this.getApplicableRules(metricName);
      
      for (const rule of applicableRules) {
        if (!rule.timeWindows.includes(timeWindow)) continue;
        
        const windowPoints = timeSeries.points.filter(p => 
          p.timestamp >= windowStart && p.timestamp <= now
        );
        
        if (windowPoints.length === 0) continue;
        
        // Group points by the specified labels
        const groupedPoints = this.groupPointsByLabels(windowPoints, rule.groupBy);
        
        const aggregatedMetrics: AggregatedMetric[] = [];
        
        for (const [groupKey, points] of groupedPoints) {
          const aggregated = this.calculateAggregations(
            metricName,
            points,
            timeWindow,
            windowStart,
            now,
            rule.aggregationFunctions,
            this.parseGroupKey(groupKey, rule.groupBy)
          );
          
          aggregatedMetrics.push(aggregated);
        }
        
        results.set(`${metricName}_${rule.id}`, aggregatedMetrics);
        
        // Store in time series for historical access
        timeSeries.aggregations.set(rule.id, aggregatedMetrics);
      }
    }
    
    return results;
  }
  
  private getApplicableRules(metricName: string): AggregationRule[] {
    return Array.from(this.rules.values()).filter(rule => {
      if (!rule.enabled) return false;
      
      const regex = new RegExp(rule.metricPattern);
      return regex.test(metricName);
    });
  }
  
  private groupPointsByLabels(
    points: MetricPoint[], 
    groupBy: string[]
  ): Map<string, MetricPoint[]> {
    const groups = new Map<string, MetricPoint[]>();
    
    for (const point of points) {
      const groupKey = groupBy
        .map(label => `${label}=${point.labels[label] || 'unknown'}`)
        .join(',');
      
      const group = groups.get(groupKey) || [];
      group.push(point);
      groups.set(groupKey, group);
    }
    
    return groups;
  }
  
  private parseGroupKey(groupKey: string, groupBy: string[]): Record<string, string> {
    const labels: Record<string, string> = {};
    const pairs = groupKey.split(',');
    
    pairs.forEach((pair, index) => {
      const [, value] = pair.split('=');
      if (groupBy[index]) {
        labels[groupBy[index]] = value;
      }
    });
    
    return labels;
  }
  
  private calculateAggregations(
    metricName: string,
    points: MetricPoint[],
    timeWindow: number,
    startTime: number,
    endTime: number,
    functions: AggregationFunction[],
    labels: Record<string, string>
  ): AggregatedMetric {
    const values = points.map(p => p.value).sort((a, b) => a - b);
    const count = values.length;
    const sum = values.reduce((acc, val) => acc + val, 0);
    const avg = count > 0 ? sum / count : 0;
    
    // Calculate percentiles
    const getPercentile = (p: number) => {
      if (count === 0) return 0;
      const index = Math.ceil((p / 100) * count) - 1;
      return values[Math.max(0, Math.min(index, count - 1))];
    };
    
    // Calculate standard deviation
    const variance = count > 0 
      ? values.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / count
      : 0;
    const stdDev = Math.sqrt(variance);
    
    // Calculate rate (per second)
    const timeSpanSeconds = (endTime - startTime) / 1000;
    const rate = timeSpanSeconds > 0 ? sum / timeSpanSeconds : 0;
    
    return {
      name: metricName,
      timeWindow,
      startTime,
      endTime,
      count,
      sum,
      min: count > 0 ? values[0] : 0,
      max: count > 0 ? values[count - 1] : 0,
      avg,
      median: getPercentile(50),
      p95: getPercentile(95),
      p99: getPercentile(99),
      stdDev,
      rate,
      labels,
      metadata: {
        calculatedAt: Date.now(),
        pointCount: count,
      },
    };
  }
  
  // Downsampling for long-term storage
  
  downsampleMetrics(
    metricName: string, 
    sourceWindow: number, 
    targetWindow: number,
    aggregationFunction: AggregationFunction = 'avg'
  ): AggregatedMetric[] | null {
    const timeSeries = this.metrics.get(metricName);
    if (!timeSeries) return null;
    
    const ratio = targetWindow / sourceWindow;
    if (ratio < 1) {
      throw new Error('Target window must be larger than source window');
    }
    
    // Get aggregated data for the source window
    const sourceAggregations = timeSeries.aggregations;
    const downsampled: AggregatedMetric[] = [];
    
    // Group source aggregations into target windows
    for (const [ruleId, aggregations] of sourceAggregations) {
      const grouped = this.groupAggregationsByTimeWindow(aggregations, targetWindow);
      
      for (const group of grouped) {
        const downsampledMetric = this.combineAggregations(group, aggregationFunction);
        downsampled.push(downsampledMetric);
      }
    }
    
    return downsampled;
  }
  
  private groupAggregationsByTimeWindow(
    aggregations: AggregatedMetric[], 
    targetWindow: number
  ): AggregatedMetric[][] {
    const groups: AggregatedMetric[][] = [];
    const windowMs = targetWindow * 1000;
    
    // Sort by start time
    const sorted = [...aggregations].sort((a, b) => a.startTime - b.startTime);
    
    let currentGroup: AggregatedMetric[] = [];
    let currentWindowStart = 0;
    
    for (const aggregation of sorted) {
      const windowStart = Math.floor(aggregation.startTime / windowMs) * windowMs;
      
      if (windowStart !== currentWindowStart) {
        if (currentGroup.length > 0) {
          groups.push(currentGroup);
        }
        currentGroup = [];
        currentWindowStart = windowStart;
      }
      
      currentGroup.push(aggregation);
    }
    
    if (currentGroup.length > 0) {
      groups.push(currentGroup);
    }
    
    return groups;
  }
  
  private combineAggregations(
    aggregations: AggregatedMetric[], 
    func: AggregationFunction
  ): AggregatedMetric {
    if (aggregations.length === 0) {
      throw new Error('Cannot combine empty aggregations');
    }
    
    const first = aggregations[0];
    const combined: AggregatedMetric = {
      name: first.name,
      timeWindow: first.timeWindow * aggregations.length,
      startTime: Math.min(...aggregations.map(a => a.startTime)),
      endTime: Math.max(...aggregations.map(a => a.endTime)),
      count: aggregations.reduce((sum, a) => sum + a.count, 0),
      sum: aggregations.reduce((sum, a) => sum + a.sum, 0),
      min: Math.min(...aggregations.map(a => a.min)),
      max: Math.max(...aggregations.map(a => a.max)),
      avg: 0, // Will be calculated
      median: 0, // Will be calculated
      p95: 0, // Will be calculated
      p99: 0, // Will be calculated
      stdDev: 0, // Will be calculated
      rate: 0, // Will be calculated
      labels: first.labels,
      metadata: {
        combinedFrom: aggregations.length,
        combinedAt: Date.now(),
      },
    };
    
    // Calculate combined statistics based on function
    switch (func) {
      case 'avg':
        combined.avg = combined.count > 0 ? combined.sum / combined.count : 0;
        combined.median = this.calculateWeightedMedian(aggregations);
        combined.p95 = this.calculateWeightedPercentile(aggregations, 95);
        combined.p99 = this.calculateWeightedPercentile(aggregations, 99);
        break;
      
      case 'sum':
        // Sum is already calculated
        break;
      
      case 'max':
        combined.avg = combined.max;
        combined.median = combined.max;
        combined.p95 = combined.max;
        combined.p99 = combined.max;
        break;
      
      case 'min':
        combined.avg = combined.min;
        combined.median = combined.min;
        combined.p95 = combined.min;
        combined.p99 = combined.min;
        break;
      
      // Add other functions as needed
    }
    
    // Calculate rate
    const timeSpanSeconds = (combined.endTime - combined.startTime) / 1000;
    combined.rate = timeSpanSeconds > 0 ? combined.sum / timeSpanSeconds : 0;
    
    return combined;
  }
  
  private calculateWeightedMedian(aggregations: AggregatedMetric[]): number {
    // Simplified weighted median calculation
    const values = aggregations.map(a => ({ value: a.median, weight: a.count }));
    values.sort((a, b) => a.value - b.value);
    
    const totalWeight = values.reduce((sum, v) => sum + v.weight, 0);
    const halfWeight = totalWeight / 2;
    
    let currentWeight = 0;
    for (const item of values) {
      currentWeight += item.weight;
      if (currentWeight >= halfWeight) {
        return item.value;
      }
    }
    
    return 0;
  }
  
  private calculateWeightedPercentile(aggregations: AggregatedMetric[], percentile: number): number {
    // Simplified calculation - in practice, you'd want more sophisticated percentile merging
    const values = aggregations.map(a => percentile === 95 ? a.p95 : a.p99);
    values.sort((a, b) => a - b);
    
    const index = Math.ceil((percentile / 100) * values.length) - 1;
    return values[Math.max(0, Math.min(index, values.length - 1))];
  }
  
  // Correlation analysis
  
  calculateCorrelations(timeWindow: number = 3600): MetricCorrelation[] {
    const correlations: MetricCorrelation[] = [];
    const metricNames = Array.from(this.metrics.keys());
    
    // Calculate pairwise correlations
    for (let i = 0; i < metricNames.length; i++) {
      for (let j = i + 1; j < metricNames.length; j++) {
        const metric1 = metricNames[i];
        const metric2 = metricNames[j];
        
        const correlation = this.calculatePairwiseCorrelation(metric1, metric2, timeWindow);
        if (correlation !== null) {
          correlations.push(correlation);
        }
      }
    }
    
    // Store correlations
    const key = `correlations_${timeWindow}`;
    this.correlations.set(key, correlations);
    
    return correlations;
  }
  
  private calculatePairwiseCorrelation(
    metric1: string, 
    metric2: string, 
    timeWindow: number
  ): MetricCorrelation | null {
    const timeSeries1 = this.metrics.get(metric1);
    const timeSeries2 = this.metrics.get(metric2);
    
    if (!timeSeries1 || !timeSeries2) return null;
    
    const now = Date.now();
    const cutoff = now - (timeWindow * 1000);
    
    const points1 = timeSeries1.points.filter(p => p.timestamp > cutoff);
    const points2 = timeSeries2.points.filter(p => p.timestamp > cutoff);
    
    if (points1.length < 2 || points2.length < 2) return null;
    
    // Align time series by timestamp (simplified approach)
    const alignedPairs = this.alignTimeSeries(points1, points2);
    
    if (alignedPairs.length < 2) return null;
    
    // Calculate Pearson correlation
    const correlation = this.pearsonCorrelation(
      alignedPairs.map(p => p[0]),
      alignedPairs.map(p => p[1])
    );
    
    // Calculate significance (simplified)
    const significance = this.calculateSignificance(correlation, alignedPairs.length);
    
    return {
      metric1,
      metric2,
      correlation,
      timeWindow,
      significance,
      timestamp: now,
    };
  }
  
  private alignTimeSeries(
    points1: MetricPoint[], 
    points2: MetricPoint[]
  ): [number, number][] {
    const aligned: [number, number][] = [];
    const tolerance = 30000; // 30 seconds tolerance
    
    for (const point1 of points1) {
      const matchingPoint = points2.find(point2 => 
        Math.abs(point1.timestamp - point2.timestamp) <= tolerance
      );
      
      if (matchingPoint) {
        aligned.push([point1.value, matchingPoint.value]);
      }
    }
    
    return aligned;
  }
  
  private pearsonCorrelation(x: number[], y: number[]): number {
    const n = x.length;
    if (n !== y.length || n === 0) return 0;
    
    const sumX = x.reduce((a, b) => a + b, 0);
    const sumY = y.reduce((a, b) => a + b, 0);
    const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
    const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
    const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);
    
    const numerator = n * sumXY - sumX * sumY;
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    
    return denominator === 0 ? 0 : numerator / denominator;
  }
  
  private calculateSignificance(correlation: number, sampleSize: number): number {
    // Simplified significance calculation
    const tStat = Math.abs(correlation) * Math.sqrt((sampleSize - 2) / (1 - correlation * correlation));
    
    // Convert to p-value (simplified approximation)
    // In practice, you'd use a proper t-distribution
    return Math.max(0, 1 - (tStat / 10));
  }
  
  // Cleanup and maintenance
  
  private startAggregationLoop(): void {
    setInterval(() => {
      try {
        // Aggregate metrics for all defined time windows
        const timeWindows = [60, 300, 900, 3600]; // 1m, 5m, 15m, 1h
        
        for (const window of timeWindows) {
          const aggregated = this.aggregateMetrics(window);
          this.emit('metrics-aggregated', { timeWindow: window, results: aggregated });
        }
        
        // Calculate correlations every hour
        if (Date.now() % 3600000 < this.aggregationInterval) {
          const correlations = this.calculateCorrelations();
          this.emit('correlations-calculated', correlations);
        }
        
      } catch (error) {
        console.error('Error in aggregation loop:', error);
        this.emit('aggregation-error', error);
      }
    }, this.aggregationInterval);
  }
  
  private startCleanupLoop(): void {
    setInterval(() => {
      this.cleanup();
    }, 300000); // Clean up every 5 minutes
  }
  
  private cleanup(): void {
    const now = Date.now();
    
    // Clean up old metric points
    for (const [metricName, timeSeries] of this.metrics) {
      const cutoff = now - (timeSeries.timeWindow * 1000);
      const initialCount = timeSeries.points.length;
      
      timeSeries.points = timeSeries.points.filter(p => p.timestamp > cutoff);
      
      if (timeSeries.points.length !== initialCount) {
        this.emit('metrics-cleaned', { 
          metricName, 
          removed: initialCount - timeSeries.points.length 
        });
      }
    }
    
    // Clean up old aggregations based on retention periods
    for (const rule of this.rules.values()) {
      const retentionCutoff = now - (rule.retentionPeriod * 1000);
      
      for (const timeSeries of this.metrics.values()) {
        const aggregations = timeSeries.aggregations.get(rule.id);
        if (aggregations) {
          const filtered = aggregations.filter(a => a.startTime > retentionCutoff);
          if (filtered.length !== aggregations.length) {
            timeSeries.aggregations.set(rule.id, filtered);
          }
        }
      }
    }
    
    // Clean up old correlations
    for (const [key, correlations] of this.correlations) {
      const cutoff = now - 86400000; // Keep correlations for 24 hours
      const filtered = correlations.filter(c => c.timestamp > cutoff);
      if (filtered.length !== correlations.length) {
        this.correlations.set(key, filtered);
      }
    }
  }
  
  // Query methods
  
  getAggregatedMetrics(
    metricName: string, 
    timeWindow: number,
    startTime?: number,
    endTime?: number
  ): AggregatedMetric[] {
    const timeSeries = this.metrics.get(metricName);
    if (!timeSeries) return [];
    
    const results: AggregatedMetric[] = [];
    
    for (const [ruleId, aggregations] of timeSeries.aggregations) {
      const rule = this.rules.get(ruleId);
      if (rule && rule.timeWindows.includes(timeWindow)) {
        let filtered = aggregations;
        
        if (startTime) {
          filtered = filtered.filter(a => a.endTime >= startTime);
        }
        
        if (endTime) {
          filtered = filtered.filter(a => a.startTime <= endTime);
        }
        
        results.push(...filtered);
      }
    }
    
    return results.sort((a, b) => a.startTime - b.startTime);
  }
  
  getMetricNames(): string[] {
    return Array.from(this.metrics.keys());
  }
  
  getCorrelations(timeWindow: number = 3600): MetricCorrelation[] {
    const key = `correlations_${timeWindow}`;
    return this.correlations.get(key) || [];
  }
  
  getHighCorrelations(
    threshold: number = 0.7, 
    timeWindow: number = 3600
  ): MetricCorrelation[] {
    return this.getCorrelations(timeWindow).filter(c => 
      Math.abs(c.correlation) >= threshold
    );
  }
  
  getStatistics(): {
    totalMetrics: number;
    totalDataPoints: number;
    totalAggregations: number;
    rulesEnabled: number;
    oldestDataPoint: number;
    newestDataPoint: number;
  } {
    let totalDataPoints = 0;
    let totalAggregations = 0;
    let oldestDataPoint = Date.now();
    let newestDataPoint = 0;
    
    for (const timeSeries of this.metrics.values()) {
      totalDataPoints += timeSeries.points.length;
      
      if (timeSeries.points.length > 0) {
        const oldest = Math.min(...timeSeries.points.map(p => p.timestamp));
        const newest = Math.max(...timeSeries.points.map(p => p.timestamp));
        
        oldestDataPoint = Math.min(oldestDataPoint, oldest);
        newestDataPoint = Math.max(newestDataPoint, newest);
      }
      
      for (const aggregations of timeSeries.aggregations.values()) {
        totalAggregations += aggregations.length;
      }
    }
    
    return {
      totalMetrics: this.metrics.size,
      totalDataPoints,
      totalAggregations,
      rulesEnabled: Array.from(this.rules.values()).filter(r => r.enabled).length,
      oldestDataPoint,
      newestDataPoint,
    };
  }
}

export function createMetricAggregator(prometheusMetrics: PrometheusMetrics): MetricAggregator {
  return new MetricAggregator(prometheusMetrics);
}