/**
 * Anomaly Detection System for ASI-Code
 * 
 * Intelligent anomaly detection for metrics and system behavior:
 * - Statistical anomaly detection (z-score, IQR)
 * - Machine learning-based detection
 * - Seasonal pattern recognition
 * - Multi-metric correlation anomalies
 * - Dynamic threshold adaptation
 * - Anomaly scoring and ranking
 */

import { EventEmitter } from 'eventemitter3';
import type { MetricAggregator, AggregatedMetric } from '../aggregation/index.js';
import type { MonitoringConfig } from '../index.js';

export interface AnomalyDetectionRule {
  id: string;
  name: string;
  metricPattern: string;
  detectionMethod: DetectionMethod;
  sensitivity: number; // 0.0 to 1.0
  timeWindow: number;
  minDataPoints: number;
  enabled: boolean;
  thresholds: AnomalyThresholds;
  metadata?: Record<string, any>;
}

export interface AnomalyThresholds {
  zscore?: number; // Standard deviations from mean
  iqr?: number; // IQR multiplier
  percentile?: { upper: number; lower: number };
  absolute?: { max: number; min: number };
  rate?: { increase: number; decrease: number };
}

export type DetectionMethod = 
  | 'zscore'
  | 'iqr'
  | 'percentile'
  | 'rate_change'
  | 'seasonal'
  | 'isolation_forest'
  | 'correlation'
  | 'composite';

export interface Anomaly {
  id: string;
  metricName: string;
  timestamp: number;
  value: number;
  expectedValue: number;
  deviationScore: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  detectionMethod: DetectionMethod;
  confidence: number;
  context: AnomalyContext;
  metadata: Record<string, any>;
}

export interface AnomalyContext {
  historicalMean: number;
  historicalStdDev: number;
  historicalMedian: number;
  recentTrend: 'increasing' | 'decreasing' | 'stable';
  seasonalPattern?: SeasonalPattern;
  correlatedAnomalies: string[]; // Other anomaly IDs
  impactAssessment: ImpactAssessment;
}

export interface SeasonalPattern {
  period: number; // in seconds
  amplitude: number;
  phase: number;
  confidence: number;
}

export interface ImpactAssessment {
  userImpact: 'none' | 'low' | 'medium' | 'high';
  businessImpact: 'none' | 'low' | 'medium' | 'high';
  systemImpact: 'none' | 'low' | 'medium' | 'high';
  downstreamMetrics: string[];
  estimatedDuration: number; // seconds
}

export interface AnomalyCluster {
  id: string;
  anomalies: Anomaly[];
  startTime: number;
  endTime: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  rootCause?: string;
  affectedComponents: string[];
  correlationScore: number;
}

export class AnomalyDetector extends EventEmitter {
  private config: MonitoringConfig['anomaly'];
  private aggregator: MetricAggregator;
  private rules: Map<string, AnomalyDetectionRule> = new Map();
  private anomalies: Map<string, Anomaly> = new Map();
  private clusters: Map<string, AnomalyCluster> = new Map();
  private historicalData: Map<string, number[]> = new Map();
  private seasonalPatterns: Map<string, SeasonalPattern> = new Map();
  private detectionInterval = 60000; // 1 minute
  private maxHistorySize = 10080; // 1 week of minutes
  
  constructor(config: MonitoringConfig['anomaly'], aggregator: MetricAggregator) {
    super();
    this.config = config;
    this.aggregator = aggregator;
    this.initializeDefaultRules();
    this.startDetectionLoop();
  }
  
  private initializeDefaultRules(): void {
    // HTTP Response Time Anomalies
    this.addRule({
      id: 'response-time-zscore',
      name: 'Response Time Z-Score Anomalies',
      metricPattern: 'asi_code_http_request_duration_seconds',
      detectionMethod: 'zscore',
      sensitivity: 0.7,
      timeWindow: 3600, // 1 hour
      minDataPoints: 30,
      enabled: true,
      thresholds: {
        zscore: 2.5,
      },
    });
    
    // Error Rate Anomalies
    this.addRule({
      id: 'error-rate-percentile',
      name: 'Error Rate Percentile Anomalies',
      metricPattern: 'asi_code_errors_total',
      detectionMethod: 'percentile',
      sensitivity: 0.8,
      timeWindow: 1800, // 30 minutes
      minDataPoints: 20,
      enabled: true,
      thresholds: {
        percentile: { upper: 95, lower: 5 },
      },
    });
    
    // Request Rate Anomalies
    this.addRule({
      id: 'request-rate-change',
      name: 'Request Rate Change Anomalies',
      metricPattern: 'asi_code_http_requests_total',
      detectionMethod: 'rate_change',
      sensitivity: 0.6,
      timeWindow: 900, // 15 minutes
      minDataPoints: 15,
      enabled: true,
      thresholds: {
        rate: { increase: 2.0, decrease: 0.5 },
      },
    });
    
    // System Resource Anomalies
    this.addRule({
      id: 'system-resource-iqr',
      name: 'System Resource IQR Anomalies',
      metricPattern: 'asi_code_system_.*',
      detectionMethod: 'iqr',
      sensitivity: 0.8,
      timeWindow: 2700, // 45 minutes
      minDataPoints: 25,
      enabled: true,
      thresholds: {
        iqr: 1.5,
      },
    });
    
    // Session Metrics Anomalies
    this.addRule({
      id: 'session-seasonal',
      name: 'Session Metrics Seasonal Anomalies',
      metricPattern: 'asi_code_sessions_.*',
      detectionMethod: 'seasonal',
      sensitivity: 0.7,
      timeWindow: 7200, // 2 hours
      minDataPoints: 50,
      enabled: true,
      thresholds: {
        zscore: 2.0,
      },
    });
    
    // Tool Execution Anomalies
    this.addRule({
      id: 'tool-execution-composite',
      name: 'Tool Execution Composite Anomalies',
      metricPattern: 'asi_code_tool_.*',
      detectionMethod: 'composite',
      sensitivity: 0.6,
      timeWindow: 1800,
      minDataPoints: 20,
      enabled: true,
      thresholds: {
        zscore: 2.0,
        iqr: 1.5,
        rate: { increase: 1.5, decrease: 0.7 },
      },
    });
    
    // Provider Performance Anomalies
    this.addRule({
      id: 'provider-correlation',
      name: 'Provider Performance Correlation Anomalies',
      metricPattern: 'asi_code_provider_.*',
      detectionMethod: 'correlation',
      sensitivity: 0.8,
      timeWindow: 3600,
      minDataPoints: 30,
      enabled: true,
      thresholds: {
        zscore: 2.5,
      },
    });
  }
  
  addRule(rule: AnomalyDetectionRule): void {
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
  
  // Core detection methods
  
  detectAnomalies(): Anomaly[] {
    const detectedAnomalies: Anomaly[] = [];
    const metricNames = this.aggregator.getMetricNames();
    
    for (const metricName of metricNames) {
      const applicableRules = this.getApplicableRules(metricName);
      
      for (const rule of applicableRules) {
        const ruleAnomalies = this.detectAnomaliesForRule(metricName, rule);
        detectedAnomalies.push(...ruleAnomalies);
      }
    }
    
    // Store detected anomalies
    for (const anomaly of detectedAnomalies) {
      this.anomalies.set(anomaly.id, anomaly);
    }
    
    // Cluster related anomalies
    const clusters = this.clusterAnomalies(detectedAnomalies);
    for (const cluster of clusters) {
      this.clusters.set(cluster.id, cluster);
    }
    
    this.emit('anomalies-detected', detectedAnomalies);
    
    return detectedAnomalies;
  }
  
  private getApplicableRules(metricName: string): AnomalyDetectionRule[] {
    return Array.from(this.rules.values()).filter(rule => {
      if (!rule.enabled) return false;
      
      const regex = new RegExp(rule.metricPattern);
      return regex.test(metricName);
    });
  }
  
  private detectAnomaliesForRule(metricName: string, rule: AnomalyDetectionRule): Anomaly[] {
    const anomalies: Anomaly[] = [];
    
    // Get recent aggregated metrics
    const aggregatedMetrics = this.aggregator.getAggregatedMetrics(
      metricName,
      60, // 1 minute aggregations
      Date.now() - (rule.timeWindow * 1000),
      Date.now()
    );
    
    if (aggregatedMetrics.length < rule.minDataPoints) {
      return anomalies;
    }
    
    // Update historical data
    this.updateHistoricalData(metricName, aggregatedMetrics);
    
    // Apply detection method
    switch (rule.detectionMethod) {
      case 'zscore':
        anomalies.push(...this.detectZScoreAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'iqr':
        anomalies.push(...this.detectIQRAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'percentile':
        anomalies.push(...this.detectPercentileAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'rate_change':
        anomalies.push(...this.detectRateChangeAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'seasonal':
        anomalies.push(...this.detectSeasonalAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'isolation_forest':
        anomalies.push(...this.detectIsolationForestAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'correlation':
        anomalies.push(...this.detectCorrelationAnomalies(metricName, aggregatedMetrics, rule));
        break;
      case 'composite':
        anomalies.push(...this.detectCompositeAnomalies(metricName, aggregatedMetrics, rule));
        break;
    }
    
    return anomalies;
  }
  
  private detectZScoreAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    const anomalies: Anomaly[] = [];
    const values = metrics.map(m => m.avg);
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const stdDev = Math.sqrt(
      values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length
    );
    
    const threshold = rule.thresholds.zscore || 2.0;
    
    for (let i = 0; i < metrics.length; i++) {
      const metric = metrics[i];
      const zscore = stdDev > 0 ? Math.abs(metric.avg - mean) / stdDev : 0;
      
      if (zscore > threshold) {
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          mean,
          zscore,
          'zscore',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectIQRAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    const anomalies: Anomaly[] = [];
    const values = metrics.map(m => m.avg).sort((a, b) => a - b);
    
    const q1Index = Math.floor(values.length * 0.25);
    const q3Index = Math.floor(values.length * 0.75);
    const q1 = values[q1Index];
    const q3 = values[q3Index];
    const iqr = q3 - q1;
    
    const multiplier = rule.thresholds.iqr || 1.5;
    const lowerBound = q1 - (multiplier * iqr);
    const upperBound = q3 + (multiplier * iqr);
    
    for (const metric of metrics) {
      if (metric.avg < lowerBound || metric.avg > upperBound) {
        const expectedValue = (q1 + q3) / 2;
        const deviationScore = Math.abs(metric.avg - expectedValue) / (iqr > 0 ? iqr : 1);
        
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          expectedValue,
          deviationScore,
          'iqr',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectPercentileAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    const anomalies: Anomaly[] = [];
    const values = metrics.map(m => m.avg).sort((a, b) => a - b);
    
    const thresholds = rule.thresholds.percentile!;
    const lowerIndex = Math.floor((thresholds.lower / 100) * values.length);
    const upperIndex = Math.floor((thresholds.upper / 100) * values.length);
    const lowerBound = values[lowerIndex];
    const upperBound = values[upperIndex];
    
    for (const metric of metrics) {
      if (metric.avg < lowerBound || metric.avg > upperBound) {
        const expectedValue = (lowerBound + upperBound) / 2;
        const deviationScore = Math.abs(metric.avg - expectedValue) / 
          (Math.abs(upperBound - lowerBound) > 0 ? Math.abs(upperBound - lowerBound) : 1);
        
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          expectedValue,
          deviationScore,
          'percentile',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectRateChangeAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    const anomalies: Anomaly[] = [];
    
    if (metrics.length < 2) return anomalies;
    
    const thresholds = rule.thresholds.rate!;
    
    for (let i = 1; i < metrics.length; i++) {
      const current = metrics[i];
      const previous = metrics[i - 1];
      
      if (previous.avg === 0) continue;
      
      const rateChange = current.avg / previous.avg;
      
      if (rateChange > thresholds.increase || rateChange < thresholds.decrease) {
        const anomaly = this.createAnomaly(
          metricName,
          current,
          previous.avg,
          Math.abs(1 - rateChange),
          'rate_change',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectSeasonalAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    const anomalies: Anomaly[] = [];
    
    // Get or create seasonal pattern
    let pattern = this.seasonalPatterns.get(metricName);
    if (!pattern) {
      pattern = this.identifySeasonalPattern(metricName, metrics);
      if (pattern) {
        this.seasonalPatterns.set(metricName, pattern);
      }
    }
    
    if (!pattern || pattern.confidence < 0.7) {
      // Fall back to z-score if no reliable seasonal pattern
      return this.detectZScoreAnomalies(metricName, metrics, rule);
    }
    
    const threshold = rule.thresholds.zscore || 2.0;
    
    for (const metric of metrics) {
      const expectedValue = this.calculateSeasonalExpectedValue(metric.startTime, pattern);
      const residual = metric.avg - expectedValue;
      const normalizedResidual = Math.abs(residual) / (pattern.amplitude > 0 ? pattern.amplitude : 1);
      
      if (normalizedResidual > threshold) {
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          expectedValue,
          normalizedResidual,
          'seasonal',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectIsolationForestAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    // Simplified isolation forest implementation
    // In practice, you'd use a proper ML library
    const anomalies: Anomaly[] = [];
    
    const features = metrics.map(m => [m.avg, m.max, m.min, m.stdDev]);
    const scores = this.calculateIsolationScores(features);
    
    const threshold = 0.6; // Anomaly score threshold
    
    for (let i = 0; i < metrics.length; i++) {
      if (scores[i] > threshold) {
        const metric = metrics[i];
        const expectedValue = metrics.reduce((sum, m) => sum + m.avg, 0) / metrics.length;
        
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          expectedValue,
          scores[i],
          'isolation_forest',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectCorrelationAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    // Detect anomalies based on correlation with other metrics
    const anomalies: Anomaly[] = [];
    
    // Get correlations for this metric
    const correlations = this.aggregator.getCorrelations(rule.timeWindow);
    const relatedMetrics = correlations
      .filter(c => (c.metric1 === metricName || c.metric2 === metricName) && Math.abs(c.correlation) > 0.7)
      .map(c => c.metric1 === metricName ? c.metric2 : c.metric1);
    
    if (relatedMetrics.length === 0) {
      // Fall back to z-score if no correlations
      return this.detectZScoreAnomalies(metricName, metrics, rule);
    }
    
    // Check if anomalies in correlated metrics should predict anomalies here
    for (const metric of metrics) {
      const correlationScore = this.calculateCorrelationAnomalyScore(
        metricName,
        metric,
        relatedMetrics
      );
      
      if (correlationScore > 0.7) {
        const expectedValue = this.predictValueFromCorrelations(metric, relatedMetrics);
        
        const anomaly = this.createAnomaly(
          metricName,
          metric,
          expectedValue,
          correlationScore,
          'correlation',
          rule
        );
        anomalies.push(anomaly);
      }
    }
    
    return anomalies;
  }
  
  private detectCompositeAnomalies(
    metricName: string,
    metrics: AggregatedMetric[],
    rule: AnomalyDetectionRule
  ): Anomaly[] {
    // Combine multiple detection methods
    const allAnomalies: Anomaly[] = [];
    
    // Apply each method with adjusted sensitivity
    const methods: DetectionMethod[] = ['zscore', 'iqr', 'rate_change'];
    
    for (const method of methods) {
      const tempRule = { ...rule, detectionMethod: method };
      let methodAnomalies: Anomaly[] = [];
      
      switch (method) {
        case 'zscore':
          methodAnomalies = this.detectZScoreAnomalies(metricName, metrics, tempRule);
          break;
        case 'iqr':
          methodAnomalies = this.detectIQRAnomalies(metricName, metrics, tempRule);
          break;
        case 'rate_change':
          methodAnomalies = this.detectRateChangeAnomalies(metricName, metrics, tempRule);
          break;
      }
      
      allAnomalies.push(...methodAnomalies);
    }
    
    // Combine overlapping anomalies
    return this.combineOverlappingAnomalies(allAnomalies);
  }
  
  private createAnomaly(
    metricName: string,
    metric: AggregatedMetric,
    expectedValue: number,
    deviationScore: number,
    detectionMethod: DetectionMethod,
    rule: AnomalyDetectionRule
  ): Anomaly {
    const anomalyId = `${metricName}_${metric.startTime}_${detectionMethod}`;
    
    const severity = this.calculateSeverity(deviationScore, rule.sensitivity);
    const confidence = this.calculateConfidence(deviationScore, metric.count);
    
    const context = this.buildAnomalyContext(metricName, metric, expectedValue);
    
    return {
      id: anomalyId,
      metricName,
      timestamp: metric.endTime,
      value: metric.avg,
      expectedValue,
      deviationScore,
      severity,
      detectionMethod,
      confidence,
      context,
      metadata: {
        ruleId: rule.id,
        timeWindow: rule.timeWindow,
        dataPoints: metric.count,
        labels: metric.labels,
      },
    };
  }
  
  private calculateSeverity(deviationScore: number, sensitivity: number): 'low' | 'medium' | 'high' | 'critical' {
    const adjustedScore = deviationScore * sensitivity;
    
    if (adjustedScore > 4) return 'critical';
    if (adjustedScore > 3) return 'high';
    if (adjustedScore > 2) return 'medium';
    return 'low';
  }
  
  private calculateConfidence(deviationScore: number, dataPoints: number): number {
    // Higher confidence with more data points and higher deviation
    const dataConfidence = Math.min(dataPoints / 50, 1); // Max confidence at 50+ points
    const deviationConfidence = Math.min(deviationScore / 5, 1); // Max confidence at 5+ std devs
    
    return (dataConfidence + deviationConfidence) / 2;
  }
  
  private buildAnomalyContext(
    metricName: string,
    metric: AggregatedMetric,
    expectedValue: number
  ): AnomalyContext {
    const historicalData = this.historicalData.get(metricName) || [];
    
    const historicalMean = historicalData.length > 0 
      ? historicalData.reduce((sum, val) => sum + val, 0) / historicalData.length
      : metric.avg;
    
    const historicalStdDev = this.calculateStandardDeviation(historicalData);
    const historicalMedian = this.calculateMedian(historicalData);
    const recentTrend = this.calculateTrend(historicalData.slice(-10));
    
    return {
      historicalMean,
      historicalStdDev,
      historicalMedian,
      recentTrend,
      seasonalPattern: this.seasonalPatterns.get(metricName),
      correlatedAnomalies: [],
      impactAssessment: this.assessImpact(metricName, metric),
    };
  }
  
  private assessImpact(metricName: string, metric: AggregatedMetric): ImpactAssessment {
    // Simplified impact assessment
    let userImpact: ImpactAssessment['userImpact'] = 'none';
    let businessImpact: ImpactAssessment['businessImpact'] = 'none';
    let systemImpact: ImpactAssessment['systemImpact'] = 'none';
    
    // Assess based on metric type
    if (metricName.includes('error') || metricName.includes('failure')) {
      userImpact = 'high';
      businessImpact = 'medium';
      systemImpact = 'medium';
    } else if (metricName.includes('latency') || metricName.includes('duration')) {
      userImpact = 'medium';
      businessImpact = 'low';
      systemImpact = 'low';
    } else if (metricName.includes('cpu') || metricName.includes('memory')) {
      userImpact = 'low';
      businessImpact = 'low';
      systemImpact = 'high';
    }
    
    return {
      userImpact,
      businessImpact,
      systemImpact,
      downstreamMetrics: [],
      estimatedDuration: 300, // 5 minutes default
    };
  }
  
  // Helper methods
  
  private updateHistoricalData(metricName: string, metrics: AggregatedMetric[]): void {
    let history = this.historicalData.get(metricName) || [];
    
    const newValues = metrics.map(m => m.avg);
    history.push(...newValues);
    
    // Keep only recent history
    if (history.length > this.maxHistorySize) {
      history = history.slice(-this.maxHistorySize);
    }
    
    this.historicalData.set(metricName, history);
  }
  
  private identifySeasonalPattern(metricName: string, metrics: AggregatedMetric[]): SeasonalPattern | null {
    // Simplified seasonal pattern detection
    // In practice, you'd use FFT or other sophisticated methods
    
    if (metrics.length < 48) return null; // Need at least 48 data points
    
    const values = metrics.map(m => m.avg);
    const timestamps = metrics.map(m => m.startTime);
    
    // Try different periods (hourly, daily, weekly patterns)
    const candidatePeriods = [3600, 86400, 604800]; // 1 hour, 1 day, 1 week
    
    let bestPattern: SeasonalPattern | null = null;
    let bestScore = 0;
    
    for (const period of candidatePeriods) {
      const pattern = this.detectPeriodicity(values, timestamps, period);
      if (pattern && pattern.confidence > bestScore) {
        bestPattern = pattern;
        bestScore = pattern.confidence;
      }
    }
    
    return bestScore > 0.6 ? bestPattern : null;
  }
  
  private detectPeriodicity(
    values: number[], 
    timestamps: number[], 
    period: number
  ): SeasonalPattern | null {
    // Simplified periodicity detection
    const cycles = Math.floor(timestamps.length * 60 / period); // Assuming 1-minute intervals
    
    if (cycles < 2) return null;
    
    const cycleLength = Math.floor(values.length / cycles);
    const cycleMeans: number[] = [];
    
    for (let c = 0; c < cycles; c++) {
      const start = c * cycleLength;
      const end = Math.min((c + 1) * cycleLength, values.length);
      const cycleValues = values.slice(start, end);
      const mean = cycleValues.reduce((sum, val) => sum + val, 0) / cycleValues.length;
      cycleMeans.push(mean);
    }
    
    // Calculate amplitude and confidence
    const amplitude = Math.max(...cycleMeans) - Math.min(...cycleMeans);
    const meanOfMeans = cycleMeans.reduce((sum, val) => sum + val, 0) / cycleMeans.length;
    const variance = cycleMeans.reduce((sum, val) => sum + Math.pow(val - meanOfMeans, 2), 0) / cycleMeans.length;
    const confidence = amplitude > 0 ? Math.min(variance / (amplitude * amplitude), 1) : 0;
    
    return {
      period,
      amplitude,
      phase: 0, // Simplified - would calculate actual phase
      confidence,
    };
  }
  
  private calculateSeasonalExpectedValue(timestamp: number, pattern: SeasonalPattern): number {
    const timeInPeriod = (timestamp / 1000) % pattern.period;
    const phase = (timeInPeriod / pattern.period) * 2 * Math.PI + pattern.phase;
    
    return pattern.amplitude * Math.sin(phase);
  }
  
  private calculateIsolationScores(features: number[][]): number[] {
    // Simplified isolation forest - returns random scores for demo
    // In practice, you'd implement proper isolation forest algorithm
    return features.map(() => Math.random());
  }
  
  private calculateCorrelationAnomalyScore(
    metricName: string,
    metric: AggregatedMetric,
    relatedMetrics: string[]
  ): number {
    // Simplified correlation-based anomaly scoring
    return Math.random(); // Placeholder implementation
  }
  
  private predictValueFromCorrelations(
    metric: AggregatedMetric,
    relatedMetrics: string[]
  ): number {
    // Simplified prediction based on correlated metrics
    return metric.avg; // Placeholder implementation
  }
  
  private combineOverlappingAnomalies(anomalies: Anomaly[]): Anomaly[] {
    // Group anomalies by timestamp and metric
    const groups = new Map<string, Anomaly[]>();
    
    for (const anomaly of anomalies) {
      const key = `${anomaly.metricName}_${anomaly.timestamp}`;
      const group = groups.get(key) || [];
      group.push(anomaly);
      groups.set(key, group);
    }
    
    const combined: Anomaly[] = [];
    
    for (const group of groups.values()) {
      if (group.length === 1) {
        combined.push(group[0]);
      } else {
        // Combine multiple detections into one with higher confidence
        const best = group.reduce((max, current) => 
          current.deviationScore > max.deviationScore ? current : max
        );
        
        best.confidence = Math.min(best.confidence * group.length, 1);
        best.detectionMethod = 'composite';
        best.metadata.combinedMethods = group.map(a => a.detectionMethod);
        
        combined.push(best);
      }
    }
    
    return combined;
  }
  
  private clusterAnomalies(anomalies: Anomaly[]): AnomalyCluster[] {
    // Simple time-based clustering
    const clusters: AnomalyCluster[] = [];
    const timeWindow = 300000; // 5 minutes
    
    const sortedAnomalies = [...anomalies].sort((a, b) => a.timestamp - b.timestamp);
    
    let currentCluster: Anomaly[] = [];
    let clusterStart = 0;
    
    for (const anomaly of sortedAnomalies) {
      if (currentCluster.length === 0) {
        currentCluster = [anomaly];
        clusterStart = anomaly.timestamp;
      } else if (anomaly.timestamp - clusterStart <= timeWindow) {
        currentCluster.push(anomaly);
      } else {
        // Create cluster for current group
        if (currentCluster.length > 1) {
          clusters.push(this.createCluster(currentCluster));
        }
        
        currentCluster = [anomaly];
        clusterStart = anomaly.timestamp;
      }
    }
    
    // Handle last cluster
    if (currentCluster.length > 1) {
      clusters.push(this.createCluster(currentCluster));
    }
    
    return clusters;
  }
  
  private createCluster(anomalies: Anomaly[]): AnomalyCluster {
    const startTime = Math.min(...anomalies.map(a => a.timestamp));
    const endTime = Math.max(...anomalies.map(a => a.timestamp));
    
    // Calculate cluster severity
    const maxSeverity = anomalies.reduce((max, a) => {
      const severityLevels = { low: 1, medium: 2, high: 3, critical: 4 };
      const currentLevel = severityLevels[a.severity];
      const maxLevel = severityLevels[max];
      return currentLevel > maxLevel ? a.severity : max;
    }, 'low' as const);
    
    const affectedComponents = Array.from(new Set(
      anomalies.map(a => a.metricName.split('_')[1] || 'unknown')
    ));
    
    return {
      id: `cluster_${startTime}_${anomalies.length}`,
      anomalies,
      startTime,
      endTime,
      severity: maxSeverity,
      affectedComponents,
      correlationScore: anomalies.length > 1 ? 0.8 : 0,
    };
  }
  
  // Utility functions
  
  private calculateStandardDeviation(values: number[]): number {
    if (values.length === 0) return 0;
    
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    
    return Math.sqrt(variance);
  }
  
  private calculateMedian(values: number[]): number {
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    
    return sorted.length % 2 === 0 
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];
  }
  
  private calculateTrend(values: number[]): 'increasing' | 'decreasing' | 'stable' {
    if (values.length < 2) return 'stable';
    
    const first = values[0];
    const last = values[values.length - 1];
    const diff = last - first;
    const threshold = Math.abs(first) * 0.1; // 10% threshold
    
    if (Math.abs(diff) < threshold) return 'stable';
    return diff > 0 ? 'increasing' : 'decreasing';
  }
  
  // Detection loop
  
  private startDetectionLoop(): void {
    setInterval(() => {
      try {
        const anomalies = this.detectAnomalies();
        
        if (anomalies.length > 0) {
          console.log(`Detected ${anomalies.length} anomalies`);
          
          // Emit high-severity anomalies immediately
          const criticalAnomalies = anomalies.filter(a => 
            a.severity === 'critical' || a.severity === 'high'
          );
          
          if (criticalAnomalies.length > 0) {
            this.emit('critical-anomalies', criticalAnomalies);
          }
        }
        
      } catch (error) {
        console.error('Error in anomaly detection loop:', error);
        this.emit('detection-error', error);
      }
    }, this.detectionInterval);
  }
  
  // Query methods
  
  getAnomalies(timeWindow?: number): Anomaly[] {
    let anomalies = Array.from(this.anomalies.values());
    
    if (timeWindow) {
      const cutoff = Date.now() - timeWindow;
      anomalies = anomalies.filter(a => a.timestamp > cutoff);
    }
    
    return anomalies.sort((a, b) => b.timestamp - a.timestamp);
  }
  
  getClusters(timeWindow?: number): AnomalyCluster[] {
    let clusters = Array.from(this.clusters.values());
    
    if (timeWindow) {
      const cutoff = Date.now() - timeWindow;
      clusters = clusters.filter(c => c.endTime > cutoff);
    }
    
    return clusters.sort((a, b) => b.endTime - a.endTime);
  }
  
  getAnomaliesByMetric(metricName: string, timeWindow?: number): Anomaly[] {
    return this.getAnomalies(timeWindow).filter(a => a.metricName === metricName);
  }
  
  getAnomaliesBySeverity(severity: Anomaly['severity'], timeWindow?: number): Anomaly[] {
    return this.getAnomalies(timeWindow).filter(a => a.severity === severity);
  }
  
  getStatistics(): {
    totalAnomalies: number;
    anomaliesByMethod: Record<string, number>;
    anomaliesBySeverity: Record<string, number>;
    clustersDetected: number;
    averageConfidence: number;
  } {
    const anomalies = this.getAnomalies();
    
    const byMethod: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};
    let totalConfidence = 0;
    
    for (const anomaly of anomalies) {
      byMethod[anomaly.detectionMethod] = (byMethod[anomaly.detectionMethod] || 0) + 1;
      bySeverity[anomaly.severity] = (bySeverity[anomaly.severity] || 0) + 1;
      totalConfidence += anomaly.confidence;
    }
    
    return {
      totalAnomalies: anomalies.length,
      anomaliesByMethod: byMethod,
      anomaliesBySeverity: bySeverity,
      clustersDetected: this.clusters.size,
      averageConfidence: anomalies.length > 0 ? totalConfidence / anomalies.length : 0,
    };
  }
}

export function createAnomalyDetector(
  config: MonitoringConfig['anomaly'], 
  aggregator: MetricAggregator
): AnomalyDetector {
  return new AnomalyDetector(config, aggregator);
}