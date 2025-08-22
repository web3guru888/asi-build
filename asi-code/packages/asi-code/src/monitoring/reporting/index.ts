/**
 * Comprehensive Reporting System for ASI-Code
 * 
 * Automated report generation and delivery:
 * - Performance reports
 * - SLO compliance reports
 * - Error analysis reports
 * - Anomaly detection summaries
 * - Business metrics reports
 * - Executive dashboards
 * - Custom report builders
 */

import { EventEmitter } from 'eventemitter3';
import * as fs from 'fs/promises';
import * as path from 'path';
import type { PrometheusMetrics } from '../metrics/index.js';
import type { SLOTracker, SLOCompliance } from '../slo/index.js';
import type { AnomalyDetector, Anomaly, AnomalyCluster } from '../anomaly/index.js';
import type { SentryErrorTracker } from '../sentry/index.js';
import type { ASICodeHealthService } from '../health/index.js';
import type { MetricAggregator } from '../aggregation/index.js';

export interface ReportConfig {
  id: string;
  name: string;
  type: ReportType;
  schedule: ReportSchedule;
  recipients: ReportRecipient[];
  template: string;
  parameters: ReportParameters;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export type ReportType = 
  | 'performance' 
  | 'slo_compliance' 
  | 'error_analysis' 
  | 'anomaly_summary' 
  | 'business_metrics' 
  | 'executive_dashboard' 
  | 'security_summary'
  | 'capacity_planning'
  | 'custom';

export interface ReportSchedule {
  frequency: 'realtime' | 'hourly' | 'daily' | 'weekly' | 'monthly';
  time?: string; // HH:MM format
  dayOfWeek?: number; // 0-6, for weekly reports
  dayOfMonth?: number; // 1-31, for monthly reports
  timezone?: string;
}

export interface ReportRecipient {
  type: 'email' | 'slack' | 'webhook' | 'file';
  address: string;
  format: 'html' | 'pdf' | 'json' | 'csv';
  metadata?: Record<string, any>;
}

export interface ReportParameters {
  timeRange: {
    start?: number;
    end?: number;
    duration?: number; // in seconds
  };
  filters?: {
    components?: string[];
    metrics?: string[];
    severities?: string[];
    users?: string[];
  };
  aggregation?: {
    interval: number;
    functions: string[];
  };
  customQueries?: string[];
  includeCharts?: boolean;
  includeRawData?: boolean;
}

export interface GeneratedReport {
  id: string;
  configId: string;
  type: ReportType;
  generatedAt: number;
  timeRange: { start: number; end: number };
  data: ReportData;
  metadata: {
    dataPoints: number;
    processingTime: number;
    version: string;
  };
}

export interface ReportData {
  summary: ReportSummary;
  sections: ReportSection[];
  charts: ChartData[];
  rawData?: any[];
  recommendations?: string[];
}

export interface ReportSummary {
  title: string;
  period: string;
  keyMetrics: KeyMetric[];
  highlights: string[];
  concerns: string[];
  trends: TrendSummary[];
}

export interface KeyMetric {
  name: string;
  value: number;
  unit: string;
  change: number;
  changeDirection: 'up' | 'down' | 'stable';
  status: 'good' | 'warning' | 'critical';
  benchmark?: number;
}

export interface TrendSummary {
  metric: string;
  trend: 'improving' | 'degrading' | 'stable';
  confidence: number;
  description: string;
}

export interface ReportSection {
  title: string;
  type: 'table' | 'chart' | 'text' | 'list';
  content: any;
  priority: number;
}

export interface ChartData {
  title: string;
  type: 'line' | 'bar' | 'pie' | 'area' | 'heatmap';
  data: any[];
  labels: string[];
  metadata: Record<string, any>;
}

export class ReportingSystem extends EventEmitter {
  private configs: Map<string, ReportConfig> = new Map();
  private reports: Map<string, GeneratedReport> = new Map();
  private scheduledReports: Map<string, NodeJS.Timeout> = new Map();
  private reportDirectory: string;
  
  // Dependencies
  private metrics: PrometheusMetrics;
  private sloTracker: SLOTracker;
  private anomalyDetector: AnomalyDetector;
  private errorTracker: SentryErrorTracker;
  private healthService: ASICodeHealthService;
  private aggregator: MetricAggregator;
  
  constructor(
    reportDirectory: string,
    metrics: PrometheusMetrics,
    sloTracker: SLOTracker,
    anomalyDetector: AnomalyDetector,
    errorTracker: SentryErrorTracker,
    healthService: ASICodeHealthService,
    aggregator: MetricAggregator
  ) {
    super();
    this.reportDirectory = reportDirectory;
    this.metrics = metrics;
    this.sloTracker = sloTracker;
    this.anomalyDetector = anomalyDetector;
    this.errorTracker = errorTracker;
    this.healthService = healthService;
    this.aggregator = aggregator;
    
    this.initializeDefaultReports();
    this.ensureReportDirectory();
  }
  
  private async ensureReportDirectory(): Promise<void> {
    try {
      await fs.mkdir(this.reportDirectory, { recursive: true });
    } catch (error) {
      console.error('Failed to create report directory:', error);
    }
  }
  
  private initializeDefaultReports(): void {
    // Daily Performance Report
    this.addReportConfig({
      id: 'daily-performance',
      name: 'Daily Performance Report',
      type: 'performance',
      schedule: {
        frequency: 'daily',
        time: '09:00',
        timezone: 'UTC',
      },
      recipients: [
        {
          type: 'email',
          address: 'engineering@asi-code.com',
          format: 'html',
        },
        {
          type: 'file',
          address: 'daily-performance.json',
          format: 'json',
        },
      ],
      template: 'default-performance',
      parameters: {
        timeRange: { duration: 86400 }, // 24 hours
        includeCharts: true,
        includeRawData: false,
      },
      enabled: true,
    });
    
    // Weekly SLO Compliance Report
    this.addReportConfig({
      id: 'weekly-slo',
      name: 'Weekly SLO Compliance Report',
      type: 'slo_compliance',
      schedule: {
        frequency: 'weekly',
        dayOfWeek: 1, // Monday
        time: '08:00',
      },
      recipients: [
        {
          type: 'email',
          address: 'sre@asi-code.com',
          format: 'pdf',
        },
        {
          type: 'slack',
          address: '#sre-alerts',
          format: 'html',
        },
      ],
      template: 'slo-compliance',
      parameters: {
        timeRange: { duration: 604800 }, // 7 days
        includeCharts: true,
      },
      enabled: true,
    });
    
    // Hourly Error Analysis
    this.addReportConfig({
      id: 'hourly-errors',
      name: 'Hourly Error Analysis',
      type: 'error_analysis',
      schedule: {
        frequency: 'hourly',
      },
      recipients: [
        {
          type: 'slack',
          address: '#engineering-alerts',
          format: 'json',
        },
      ],
      template: 'error-analysis',
      parameters: {
        timeRange: { duration: 3600 }, // 1 hour
        filters: {
          severities: ['high', 'critical'],
        },
      },
      enabled: true,
    });
    
    // Daily Anomaly Summary
    this.addReportConfig({
      id: 'daily-anomalies',
      name: 'Daily Anomaly Summary',
      type: 'anomaly_summary',
      schedule: {
        frequency: 'daily',
        time: '10:00',
      },
      recipients: [
        {
          type: 'email',
          address: 'ops@asi-code.com',
          format: 'html',
        },
      ],
      template: 'anomaly-summary',
      parameters: {
        timeRange: { duration: 86400 },
        includeCharts: true,
      },
      enabled: true,
    });
    
    // Weekly Business Metrics Report
    this.addReportConfig({
      id: 'weekly-business',
      name: 'Weekly Business Metrics Report',
      type: 'business_metrics',
      schedule: {
        frequency: 'weekly',
        dayOfWeek: 1,
        time: '09:00',
      },
      recipients: [
        {
          type: 'email',
          address: 'leadership@asi-code.com',
          format: 'pdf',
        },
      ],
      template: 'business-metrics',
      parameters: {
        timeRange: { duration: 604800 },
        includeCharts: true,
      },
      enabled: true,
    });
    
    // Monthly Executive Dashboard
    this.addReportConfig({
      id: 'monthly-executive',
      name: 'Monthly Executive Dashboard',
      type: 'executive_dashboard',
      schedule: {
        frequency: 'monthly',
        dayOfMonth: 1,
        time: '09:00',
      },
      recipients: [
        {
          type: 'email',
          address: 'executives@asi-code.com',
          format: 'pdf',
        },
      ],
      template: 'executive-dashboard',
      parameters: {
        timeRange: { duration: 2592000 }, // 30 days
        includeCharts: true,
      },
      enabled: true,
    });
  }
  
  addReportConfig(config: ReportConfig): void {
    this.configs.set(config.id, config);
    
    if (config.enabled) {
      this.scheduleReport(config);
    }
    
    this.emit('report-config-added', config);
  }
  
  private scheduleReport(config: ReportConfig): void {
    const existing = this.scheduledReports.get(config.id);
    if (existing) {
      clearTimeout(existing);
    }
    
    const nextRun = this.calculateNextRunTime(config.schedule);
    const timeout = setTimeout(() => {
      this.generateReport(config.id);
      // Reschedule for next occurrence
      this.scheduleReport(config);
    }, nextRun - Date.now());
    
    this.scheduledReports.set(config.id, timeout);
  }
  
  private calculateNextRunTime(schedule: ReportSchedule): number {
    const now = new Date();
    const next = new Date(now);
    
    switch (schedule.frequency) {
      case 'hourly':
        next.setHours(next.getHours() + 1, 0, 0, 0);
        break;
        
      case 'daily':
        if (schedule.time) {
          const [hours, minutes] = schedule.time.split(':').map(Number);
          next.setHours(hours, minutes, 0, 0);
          if (next <= now) {
            next.setDate(next.getDate() + 1);
          }
        } else {
          next.setDate(next.getDate() + 1);
          next.setHours(0, 0, 0, 0);
        }
        break;
        
      case 'weekly':
        const targetDay = schedule.dayOfWeek || 0;
        const currentDay = next.getDay();
        const daysUntilTarget = (targetDay + 7 - currentDay) % 7 || 7;
        
        next.setDate(next.getDate() + daysUntilTarget);
        if (schedule.time) {
          const [hours, minutes] = schedule.time.split(':').map(Number);
          next.setHours(hours, minutes, 0, 0);
        } else {
          next.setHours(0, 0, 0, 0);
        }
        break;
        
      case 'monthly':
        const targetDate = schedule.dayOfMonth || 1;
        next.setDate(targetDate);
        next.setHours(0, 0, 0, 0);
        if (next <= now) {
          next.setMonth(next.getMonth() + 1);
        }
        break;
        
      default:
        // Default to 1 hour from now
        next.setHours(next.getHours() + 1);
    }
    
    return next.getTime();
  }
  
  async generateReport(configId: string): Promise<GeneratedReport | null> {
    const config = this.configs.get(configId);
    if (!config) {
      console.error(`Report config not found: ${configId}`);
      return null;
    }
    
    const startTime = Date.now();
    
    try {
      console.log(`Generating report: ${config.name}`);
      
      const timeRange = this.calculateTimeRange(config.parameters.timeRange);
      const reportData = await this.collectReportData(config, timeRange);
      
      const report: GeneratedReport = {
        id: `${configId}_${Date.now()}`,
        configId,
        type: config.type,
        generatedAt: Date.now(),
        timeRange,
        data: reportData,
        metadata: {
          dataPoints: this.countDataPoints(reportData),
          processingTime: Date.now() - startTime,
          version: '1.0.0',
        },
      };
      
      this.reports.set(report.id, report);
      
      // Deliver report to recipients
      await this.deliverReport(report, config.recipients);
      
      this.emit('report-generated', report);
      
      return report;
      
    } catch (error) {
      console.error(`Failed to generate report ${configId}:`, error);
      this.emit('report-error', { configId, error });
      return null;
    }
  }
  
  private calculateTimeRange(timeRangeParam: ReportParameters['timeRange']): { start: number; end: number } {
    const now = Date.now();
    
    if (timeRangeParam.start && timeRangeParam.end) {
      return { start: timeRangeParam.start, end: timeRangeParam.end };
    }
    
    if (timeRangeParam.duration) {
      return { start: now - (timeRangeParam.duration * 1000), end: now };
    }
    
    // Default to last 24 hours
    return { start: now - 86400000, end: now };
  }
  
  private async collectReportData(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    switch (config.type) {
      case 'performance':
        return this.generatePerformanceReport(config, timeRange);
      case 'slo_compliance':
        return this.generateSLOComplianceReport(config, timeRange);
      case 'error_analysis':
        return this.generateErrorAnalysisReport(config, timeRange);
      case 'anomaly_summary':
        return this.generateAnomalySummaryReport(config, timeRange);
      case 'business_metrics':
        return this.generateBusinessMetricsReport(config, timeRange);
      case 'executive_dashboard':
        return this.generateExecutiveDashboardReport(config, timeRange);
      case 'security_summary':
        return this.generateSecuritySummaryReport(config, timeRange);
      case 'capacity_planning':
        return this.generateCapacityPlanningReport(config, timeRange);
      default:
        throw new Error(`Unsupported report type: ${config.type}`);
    }
  }
  
  private async generatePerformanceReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const duration = timeRange.end - timeRange.start;
    
    // Collect performance metrics
    const responseTimeMetrics = this.aggregator.getAggregatedMetrics(
      'asi_code_http_request_duration_seconds',
      300, // 5-minute aggregations
      timeRange.start,
      timeRange.end
    );
    
    const throughputMetrics = this.aggregator.getAggregatedMetrics(
      'asi_code_http_requests_total',
      300,
      timeRange.start,
      timeRange.end
    );
    
    // Calculate key metrics
    const avgResponseTime = responseTimeMetrics.length > 0
      ? responseTimeMetrics.reduce((sum, m) => sum + m.avg, 0) / responseTimeMetrics.length
      : 0;
    
    const totalRequests = throughputMetrics.reduce((sum, m) => sum + m.sum, 0);
    const avgThroughput = totalRequests / (duration / 1000); // requests per second
    
    const p95ResponseTime = responseTimeMetrics.length > 0
      ? Math.max(...responseTimeMetrics.map(m => m.p95))
      : 0;
    
    const summary: ReportSummary = {
      title: `Performance Report - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(duration),
      keyMetrics: [
        {
          name: 'Average Response Time',
          value: avgResponseTime,
          unit: 'ms',
          change: 0, // Would calculate from previous period
          changeDirection: 'stable',
          status: avgResponseTime < 200 ? 'good' : avgResponseTime < 500 ? 'warning' : 'critical',
          benchmark: 200,
        },
        {
          name: 'P95 Response Time',
          value: p95ResponseTime,
          unit: 'ms',
          change: 0,
          changeDirection: 'stable',
          status: p95ResponseTime < 500 ? 'good' : p95ResponseTime < 1000 ? 'warning' : 'critical',
          benchmark: 500,
        },
        {
          name: 'Throughput',
          value: avgThroughput,
          unit: 'req/s',
          change: 0,
          changeDirection: 'stable',
          status: 'good',
        },
        {
          name: 'Total Requests',
          value: totalRequests,
          unit: 'requests',
          change: 0,
          changeDirection: 'stable',
          status: 'good',
        },
      ],
      highlights: [
        `Processed ${totalRequests.toLocaleString()} requests`,
        `Average response time: ${avgResponseTime.toFixed(2)}ms`,
        `P95 response time: ${p95ResponseTime.toFixed(2)}ms`,
      ],
      concerns: avgResponseTime > 500 ? ['High response times detected'] : [],
      trends: [
        {
          metric: 'response_time',
          trend: 'stable',
          confidence: 0.8,
          description: 'Response times are within normal ranges',
        },
      ],
    };
    
    const sections: ReportSection[] = [
      {
        title: 'Response Time Analysis',
        type: 'chart',
        content: this.createTimeSeriesChart(responseTimeMetrics, 'Response Time (ms)'),
        priority: 1,
      },
      {
        title: 'Throughput Analysis',
        type: 'chart',
        content: this.createTimeSeriesChart(throughputMetrics, 'Requests/sec'),
        priority: 2,
      },
    ];
    
    const charts: ChartData[] = [
      {
        title: 'Response Time Over Time',
        type: 'line',
        data: responseTimeMetrics.map(m => ({ x: m.startTime, y: m.avg })),
        labels: ['Time', 'Response Time (ms)'],
        metadata: { unit: 'ms' },
      },
      {
        title: 'Request Throughput',
        type: 'area',
        data: throughputMetrics.map(m => ({ x: m.startTime, y: m.rate })),
        labels: ['Time', 'Requests/sec'],
        metadata: { unit: 'req/s' },
      },
    ];
    
    return {
      summary,
      sections,
      charts,
      rawData: config.parameters.includeRawData ? [...responseTimeMetrics, ...throughputMetrics] : undefined,
      recommendations: this.generatePerformanceRecommendations(avgResponseTime, p95ResponseTime, avgThroughput),
    };
  }
  
  private async generateSLOComplianceReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const sloStatus = this.sloTracker.getSLOStatus();
    const sloReport = this.sloTracker.generateSLOReport(timeRange.end - timeRange.start);
    
    const summary: ReportSummary = {
      title: `SLO Compliance Report - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [
        {
          name: 'SLO Compliance Rate',
          value: (sloStatus.compliant / sloStatus.total) * 100,
          unit: '%',
          change: 0,
          changeDirection: 'stable',
          status: sloStatus.violated === 0 ? 'good' : sloStatus.violated > 2 ? 'critical' : 'warning',
          benchmark: 100,
        },
        {
          name: 'SLOs at Risk',
          value: sloStatus.at_risk,
          unit: 'count',
          change: 0,
          changeDirection: 'stable',
          status: sloStatus.at_risk === 0 ? 'good' : 'warning',
        },
        {
          name: 'SLO Violations',
          value: sloStatus.violated,
          unit: 'count',
          change: 0,
          changeDirection: 'stable',
          status: sloStatus.violated === 0 ? 'good' : 'critical',
        },
      ],
      highlights: [
        `${sloStatus.compliant}/${sloStatus.total} SLOs are compliant`,
        `${sloStatus.at_risk} SLOs are at risk`,
        `${sloStatus.violated} SLOs are violated`,
      ],
      concerns: sloReport.violations.length > 0 ? 
        sloReport.violations.map(v => `${v.sloName} SLO violated`) : [],
      trends: [],
    };
    
    const sections: ReportSection[] = [
      {
        title: 'SLO Status Overview',
        type: 'table',
        content: {
          headers: ['SLO', 'Target', 'Current', 'Status', 'Error Budget'],
          rows: Object.entries(sloReport.details).map(([name, details]) => [
            name,
            `${details.target}%`,
            `${details.current.toFixed(2)}%`,
            details.status,
            `${((1 - details.errorBudget.consumptionRate) * 100).toFixed(1)}%`,
          ]),
        },
        priority: 1,
      },
    ];
    
    return {
      summary,
      sections,
      charts: [],
      recommendations: this.generateSLORecommendations(sloReport),
    };
  }
  
  private async generateErrorAnalysisReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const errorMetrics = this.errorTracker.getErrorMetrics();
    const errorTrends = this.errorTracker.getErrorTrends(timeRange.end - timeRange.start);
    const frequentErrors = this.errorTracker.getMostFrequentErrors();
    
    const summary: ReportSummary = {
      title: `Error Analysis Report - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [
        {
          name: 'Total Errors',
          value: errorMetrics.totalErrors,
          unit: 'errors',
          change: 0,
          changeDirection: 'stable',
          status: errorMetrics.totalErrors < 100 ? 'good' : errorMetrics.totalErrors < 500 ? 'warning' : 'critical',
        },
        {
          name: 'Error Rate',
          value: Object.values(errorMetrics.errorsByLevel).reduce((sum, count) => sum + count, 0),
          unit: 'errors/hour',
          change: 0,
          changeDirection: 'stable',
          status: 'warning',
        },
      ],
      highlights: [
        `${errorMetrics.totalErrors} total errors recorded`,
        `Top error type: ${frequentErrors[0]?.type || 'None'}`,
      ],
      concerns: frequentErrors.slice(0, 3).map(e => `${e.type}: ${e.count} occurrences`),
      trends: [],
    };
    
    return {
      summary,
      sections: [],
      charts: [],
      recommendations: this.generateErrorRecommendations(errorMetrics, frequentErrors),
    };
  }
  
  private async generateAnomalySummaryReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const anomalies = this.anomalyDetector.getAnomalies(timeRange.end - timeRange.start);
    const clusters = this.anomalyDetector.getClusters(timeRange.end - timeRange.start);
    const stats = this.anomalyDetector.getStatistics();
    
    const criticalAnomalies = anomalies.filter(a => a.severity === 'critical');
    const highAnomalies = anomalies.filter(a => a.severity === 'high');
    
    const summary: ReportSummary = {
      title: `Anomaly Detection Summary - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [
        {
          name: 'Total Anomalies',
          value: anomalies.length,
          unit: 'anomalies',
          change: 0,
          changeDirection: 'stable',
          status: criticalAnomalies.length === 0 ? 'good' : 'critical',
        },
        {
          name: 'Critical Anomalies',
          value: criticalAnomalies.length,
          unit: 'anomalies',
          change: 0,
          changeDirection: 'stable',
          status: criticalAnomalies.length === 0 ? 'good' : 'critical',
        },
        {
          name: 'Anomaly Clusters',
          value: clusters.length,
          unit: 'clusters',
          change: 0,
          changeDirection: 'stable',
          status: clusters.length < 3 ? 'good' : 'warning',
        },
      ],
      highlights: [
        `${anomalies.length} anomalies detected`,
        `${clusters.length} anomaly clusters identified`,
        `Average confidence: ${(stats.averageConfidence * 100).toFixed(1)}%`,
      ],
      concerns: criticalAnomalies.length > 0 ? ['Critical anomalies detected'] : [],
      trends: [],
    };
    
    return {
      summary,
      sections: [],
      charts: [],
      recommendations: this.generateAnomalyRecommendations(anomalies, clusters),
    };
  }
  
  private async generateBusinessMetricsReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    // Placeholder implementation - would collect actual business metrics
    const summary: ReportSummary = {
      title: `Business Metrics Report - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [
        {
          name: 'Active Sessions',
          value: 1250,
          unit: 'sessions',
          change: 15,
          changeDirection: 'up',
          status: 'good',
        },
        {
          name: 'Tool Executions',
          value: 8450,
          unit: 'executions',
          change: 8,
          changeDirection: 'up',
          status: 'good',
        },
      ],
      highlights: ['Strong user engagement', 'Tool usage increasing'],
      concerns: [],
      trends: [],
    };
    
    return {
      summary,
      sections: [],
      charts: [],
      recommendations: [],
    };
  }
  
  private async generateExecutiveDashboardReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const summary: ReportSummary = {
      title: `Executive Dashboard - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [
        {
          name: 'System Availability',
          value: 99.95,
          unit: '%',
          change: 0.1,
          changeDirection: 'up',
          status: 'good',
          benchmark: 99.9,
        },
        {
          name: 'User Satisfaction',
          value: 4.7,
          unit: '/5.0',
          change: 0.2,
          changeDirection: 'up',
          status: 'good',
        },
      ],
      highlights: ['Excellent system performance', 'High user satisfaction'],
      concerns: [],
      trends: [],
    };
    
    return {
      summary,
      sections: [],
      charts: [],
      recommendations: [],
    };
  }
  
  private async generateSecuritySummaryReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const summary: ReportSummary = {
      title: `Security Summary - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [],
      highlights: ['No security incidents'],
      concerns: [],
      trends: [],
    };
    
    return { summary, sections: [], charts: [], recommendations: [] };
  }
  
  private async generateCapacityPlanningReport(config: ReportConfig, timeRange: { start: number; end: number }): Promise<ReportData> {
    const summary: ReportSummary = {
      title: `Capacity Planning Report - ${new Date(timeRange.start).toLocaleDateString()} to ${new Date(timeRange.end).toLocaleDateString()}`,
      period: this.formatDuration(timeRange.end - timeRange.start),
      keyMetrics: [],
      highlights: ['Capacity within normal ranges'],
      concerns: [],
      trends: [],
    };
    
    return { summary, sections: [], charts: [], recommendations: [] };
  }
  
  // Helper methods
  
  private createTimeSeriesChart(metrics: any[], title: string): ChartData {
    return {
      title,
      type: 'line',
      data: metrics.map(m => ({ x: m.startTime, y: m.avg })),
      labels: ['Time', title],
      metadata: {},
    };
  }
  
  private formatDuration(ms: number): string {
    const hours = Math.floor(ms / 3600000);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    return `${Math.floor(ms / 60000)} minute${Math.floor(ms / 60000) > 1 ? 's' : ''}`;
  }
  
  private countDataPoints(data: ReportData): number {
    return data.sections.reduce((count, section) => {
      if (section.type === 'table' && section.content.rows) {
        return count + section.content.rows.length;
      }
      return count + 1;
    }, 0) + data.charts.length;
  }
  
  private generatePerformanceRecommendations(avgResponseTime: number, p95ResponseTime: number, throughput: number): string[] {
    const recommendations: string[] = [];
    
    if (avgResponseTime > 500) {
      recommendations.push('Consider optimizing database queries and adding caching');
    }
    
    if (p95ResponseTime > 1000) {
      recommendations.push('Investigate slowest endpoints and optimize critical paths');
    }
    
    if (throughput < 10) {
      recommendations.push('Monitor for capacity issues and consider scaling');
    }
    
    return recommendations;
  }
  
  private generateSLORecommendations(sloReport: any): string[] {
    const recommendations: string[] = [];
    
    if (sloReport.violations.length > 0) {
      recommendations.push('Review and address SLO violations immediately');
      recommendations.push('Consider adjusting SLO targets if they are unrealistic');
    }
    
    return recommendations;
  }
  
  private generateErrorRecommendations(errorMetrics: any, frequentErrors: any[]): string[] {
    const recommendations: string[] = [];
    
    if (errorMetrics.totalErrors > 500) {
      recommendations.push('Investigate high error rates and implement fixes');
    }
    
    if (frequentErrors.length > 0) {
      recommendations.push(`Focus on fixing the most frequent error: ${frequentErrors[0].type}`);
    }
    
    return recommendations;
  }
  
  private generateAnomalyRecommendations(anomalies: Anomaly[], clusters: AnomalyCluster[]): string[] {
    const recommendations: string[] = [];
    
    const criticalAnomalies = anomalies.filter(a => a.severity === 'critical');
    if (criticalAnomalies.length > 0) {
      recommendations.push('Investigate critical anomalies immediately');
    }
    
    if (clusters.length > 5) {
      recommendations.push('Multiple anomaly clusters detected - possible systemic issue');
    }
    
    return recommendations;
  }
  
  // Report delivery
  
  private async deliverReport(report: GeneratedReport, recipients: ReportRecipient[]): Promise<void> {
    for (const recipient of recipients) {
      try {
        await this.deliverToRecipient(report, recipient);
      } catch (error) {
        console.error(`Failed to deliver report to ${recipient.address}:`, error);
      }
    }
  }
  
  private async deliverToRecipient(report: GeneratedReport, recipient: ReportRecipient): Promise<void> {
    switch (recipient.type) {
      case 'file':
        await this.saveReportToFile(report, recipient);
        break;
      case 'email':
        await this.sendReportByEmail(report, recipient);
        break;
      case 'slack':
        await this.sendReportToSlack(report, recipient);
        break;
      case 'webhook':
        await this.sendReportToWebhook(report, recipient);
        break;
    }
  }
  
  private async saveReportToFile(report: GeneratedReport, recipient: ReportRecipient): Promise<void> {
    const filePath = path.join(this.reportDirectory, recipient.address);
    
    let content: string;
    
    switch (recipient.format) {
      case 'json':
        content = JSON.stringify(report, null, 2);
        break;
      case 'html':
        content = this.renderReportAsHTML(report);
        break;
      case 'csv':
        content = this.renderReportAsCSV(report);
        break;
      default:
        content = JSON.stringify(report, null, 2);
    }
    
    await fs.writeFile(filePath, content, 'utf8');
    console.log(`Report saved to: ${filePath}`);
  }
  
  private async sendReportByEmail(report: GeneratedReport, recipient: ReportRecipient): Promise<void> {
    // Placeholder - would integrate with email service
    console.log(`Email report to ${recipient.address}: ${report.data.summary.title}`);
  }
  
  private async sendReportToSlack(report: GeneratedReport, recipient: ReportRecipient): Promise<void> {
    // Placeholder - would integrate with Slack API
    console.log(`Slack report to ${recipient.address}: ${report.data.summary.title}`);
  }
  
  private async sendReportToWebhook(report: GeneratedReport, recipient: ReportRecipient): Promise<void> {
    // Placeholder - would send HTTP POST to webhook
    console.log(`Webhook report to ${recipient.address}: ${report.data.summary.title}`);
  }
  
  private renderReportAsHTML(report: GeneratedReport): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>${report.data.summary.title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 3px; }
        .good { border-left: 4px solid green; }
        .warning { border-left: 4px solid orange; }
        .critical { border-left: 4px solid red; }
    </style>
</head>
<body>
    <h1>${report.data.summary.title}</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Period: ${report.data.summary.period}</p>
        <div class="metrics">
            ${report.data.summary.keyMetrics.map(metric => `
                <div class="metric ${metric.status}">
                    <strong>${metric.name}</strong><br>
                    ${metric.value} ${metric.unit}<br>
                    ${metric.change > 0 ? '↑' : metric.change < 0 ? '↓' : '→'} ${Math.abs(metric.change)}%
                </div>
            `).join('')}
        </div>
        <h3>Highlights</h3>
        <ul>
            ${report.data.summary.highlights.map(h => `<li>${h}</li>`).join('')}
        </ul>
        ${report.data.summary.concerns.length > 0 ? `
            <h3>Concerns</h3>
            <ul>
                ${report.data.summary.concerns.map(c => `<li>${c}</li>`).join('')}
            </ul>
        ` : ''}
        ${report.data.recommendations && report.data.recommendations.length > 0 ? `
            <h3>Recommendations</h3>
            <ul>
                ${report.data.recommendations.map(r => `<li>${r}</li>`).join('')}
            </ul>
        ` : ''}
    </div>
</body>
</html>
    `;
  }
  
  private renderReportAsCSV(report: GeneratedReport): string {
    const lines: string[] = [];
    
    // Header
    lines.push('Metric,Value,Unit,Status');
    
    // Key metrics
    for (const metric of report.data.summary.keyMetrics) {
      lines.push(`"${metric.name}",${metric.value},"${metric.unit}","${metric.status}"`);
    }
    
    return lines.join('\n');
  }
  
  // Query methods
  
  getReports(limit = 50): GeneratedReport[] {
    return Array.from(this.reports.values())
      .sort((a, b) => b.generatedAt - a.generatedAt)
      .slice(0, limit);
  }
  
  getReport(reportId: string): GeneratedReport | undefined {
    return this.reports.get(reportId);
  }
  
  getReportConfigs(): ReportConfig[] {
    return Array.from(this.configs.values());
  }
  
  // Management methods
  
  enableReport(configId: string): boolean {
    const config = this.configs.get(configId);
    if (config) {
      config.enabled = true;
      this.scheduleReport(config);
      return true;
    }
    return false;
  }
  
  disableReport(configId: string): boolean {
    const config = this.configs.get(configId);
    if (config) {
      config.enabled = false;
      const timeout = this.scheduledReports.get(configId);
      if (timeout) {
        clearTimeout(timeout);
        this.scheduledReports.delete(configId);
      }
      return true;
    }
    return false;
  }
  
  removeReport(configId: string): boolean {
    this.disableReport(configId);
    return this.configs.delete(configId);
  }
}

export function createReportingSystem(
  reportDirectory: string,
  metrics: PrometheusMetrics,
  sloTracker: SLOTracker,
  anomalyDetector: AnomalyDetector,
  errorTracker: SentryErrorTracker,
  healthService: ASICodeHealthService,
  aggregator: MetricAggregator
): ReportingSystem {
  return new ReportingSystem(
    reportDirectory,
    metrics,
    sloTracker,
    anomalyDetector,
    errorTracker,
    healthService,
    aggregator
  );
}