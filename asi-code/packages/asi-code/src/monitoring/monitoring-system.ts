/**
 * Comprehensive Monitoring System Integration for ASI-Code
 * 
 * This module orchestrates all monitoring components:
 * - Prometheus metrics collection
 * - Distributed tracing with Jaeger
 * - Health checks and status monitoring
 * - Error tracking with Sentry
 * - SLO/SLI tracking and compliance
 * - Anomaly detection and alerting
 * - Performance monitoring and analysis
 * - Log correlation and tracing
 * - Automated reporting and notifications
 * - Runbook automation for incident response
 */

import { EventEmitter } from 'eventemitter3';
import type { Hono } from 'hono';
import type { MonitoringConfig } from './index.js';
import { createPrometheusMetrics } from './metrics/index.js';
import { createBusinessMetrics } from './business/index.js';
import { createTracingService } from './tracing/index.js';
import { createHealthService } from './health/index.js';
import { createPerformanceMonitor } from './performance/index.js';
import { createSentryErrorTracker } from './sentry/index.js';
import { createSLOTracker } from './slo/index.js';
import { createRunbookAutomation } from './runbooks/index.js';
import { createCorrelationTracker } from './correlation/index.js';
import { createTraceSampler } from './sampling/index.js';
import { createMetricAggregator } from './aggregation/index.js';
import { createAnomalyDetector } from './anomaly/index.js';
import { createReportingSystem } from './reporting/index.js';

export interface MonitoringSystemOptions {
  config: MonitoringConfig;
  reportDirectory?: string;
  runbookDirectory?: string;
}

export interface MonitoringSystemStatus {
  initialized: boolean;
  componentsStatus: Record<string, {
    enabled: boolean;
    healthy: boolean;
    lastCheck: number;
    errorCount: number;
  }>;
  metrics: {
    totalMetrics: number;
    metricsPerSecond: number;
    tracesPerSecond: number;
    alertsActive: number;
    anomaliesDetected: number;
  };
}

export class MonitoringSystem extends EventEmitter {
  private readonly config: MonitoringConfig;
  private initialized = false;
  
  // Core monitoring components
  public readonly prometheusMetrics;
  public readonly businessMetrics;
  public readonly tracingService;
  public readonly healthService;
  public readonly performanceMonitor;
  public readonly errorTracker;
  public readonly sloTracker;
  public readonly runbookAutomation;
  public readonly correlationTracker;
  public readonly traceSampler;
  public readonly metricAggregator;
  public readonly anomalyDetector;
  public readonly reportingSystem;
  
  private readonly componentStatus = new Map<string, {
    enabled: boolean;
    healthy: boolean;
    lastCheck: number;
    errorCount: number;
  }>();
  
  constructor(options: MonitoringSystemOptions) {
    super();
    this.config = options.config;
    
    // Initialize all monitoring components
    this.prometheusMetrics = createPrometheusMetrics(this.config.prometheus);
    this.businessMetrics = createBusinessMetrics(this.prometheusMetrics);
    this.tracingService = createTracingService(this.config.jaeger);
    this.healthService = createHealthService(this.config.health);
    this.performanceMonitor = createPerformanceMonitor(this.prometheusMetrics);
    this.errorTracker = createSentryErrorTracker(this.config.sentry);
    this.sloTracker = createSLOTracker(this.config.slo, this.prometheusMetrics);
    this.runbookAutomation = createRunbookAutomation(options.runbookDirectory);
    this.correlationTracker = createCorrelationTracker(this.config.correlation);
    this.traceSampler = createTraceSampler(this.config.jaeger);
    this.metricAggregator = createMetricAggregator(this.prometheusMetrics);
    this.anomalyDetector = createAnomalyDetector(this.config.anomaly, this.metricAggregator);
    this.reportingSystem = createReportingSystem(
      options.reportDirectory || './reports',
      this.prometheusMetrics,
      this.sloTracker,
      this.anomalyDetector,
      this.errorTracker,
      this.healthService,
      this.metricAggregator
    );
    
    this.initializeComponentStatus();
    this.setupEventListeners();
  }
  
  private initializeComponentStatus(): void {
    const components = [
      'prometheus', 'tracing', 'health', 'performance', 'errors',
      'slo', 'runbooks', 'correlation', 'sampling', 'aggregation',
      'anomaly', 'reporting'
    ];
    
    components.forEach(component => {
      this.componentStatus.set(component, {
        enabled: true,
        healthy: true,
        lastCheck: Date.now(),
        errorCount: 0,
      });
    });
  }
  
  private setupEventListeners(): void {
    // Error tracking integration
    this.errorTracker.on('error-tracked', (errorMetrics) => {
      this.emit('monitoring-event', {
        type: 'error',
        source: 'sentry',
        data: errorMetrics,
      });
    });
    
    // Anomaly detection integration
    this.anomalyDetector.on('anomalies-detected', (anomalies) => {
      this.emit('monitoring-event', {
        type: 'anomaly',
        source: 'anomaly-detector',
        data: anomalies,
      });
      
      // Trigger runbooks for critical anomalies
      const criticalAnomalies = anomalies.filter(a => a.severity === 'critical');
      if (criticalAnomalies.length > 0) {
        this.handleCriticalAnomalies(criticalAnomalies);
      }
    });
    
    // SLO violation integration
    this.sloTracker.on('slo-tracked', (compliance) => {
      if (compliance.status === 'violated') {
        this.emit('monitoring-event', {
          type: 'slo-violation',
          source: 'slo-tracker',
          data: compliance,
        });
        
        this.handleSLOViolation(compliance);
      }
    });
    
    // Health check integration
    this.healthService.on('health-check-completed', (healthStatus) => {
      this.emit('monitoring-event', {
        type: 'health-check',
        source: 'health-service',
        data: healthStatus,
      });
      
      if (healthStatus.status === 'unhealthy') {
        this.handleHealthIssue(healthStatus);
      }
    });
    
    // Performance monitoring integration
    this.performanceMonitor.on('performance-metric', (metric) => {
      // Forward performance metrics to aggregator
      this.metricAggregator.addMetricPoint(metric.name, {
        timestamp: metric.timestamp,
        value: metric.value,
        labels: metric.labels || {},
        metadata: metric.metadata,
      });
    });
    
    // Runbook execution integration
    this.runbookAutomation.on('runbook-completed', (execution) => {
      this.emit('monitoring-event', {
        type: 'runbook-execution',
        source: 'runbook-automation',
        data: execution,
      });
    });
    
    // Report generation integration
    this.reportingSystem.on('report-generated', (report) => {
      this.emit('monitoring-event', {
        type: 'report-generated',
        source: 'reporting-system',
        data: report,
      });
    });
  }
  
  async initialize(): Promise<void> {
    if (this.initialized) {
      console.warn('Monitoring system already initialized');
      return;
    }
    
    console.log('Initializing ASI-Code monitoring system...');
    
    try {
      // Initialize components that need async setup
      // Most components are initialized in constructor, but some may need async setup
      
      console.log('✓ Prometheus metrics initialized');
      console.log('✓ Distributed tracing initialized');
      console.log('✓ Health checks initialized');
      console.log('✓ Performance monitoring initialized');
      console.log('✓ Error tracking initialized');
      console.log('✓ SLO/SLI tracking initialized');
      console.log('✓ Runbook automation initialized');
      console.log('✓ Log correlation initialized');
      console.log('✓ Trace sampling initialized');
      console.log('✓ Metric aggregation initialized');
      console.log('✓ Anomaly detection initialized');
      console.log('✓ Reporting system initialized');
      
      this.initialized = true;
      this.emit('monitoring-system-initialized');
      
      console.log('ASI-Code monitoring system fully initialized');
      
    } catch (error) {
      console.error('Failed to initialize monitoring system:', error);
      this.emit('monitoring-system-error', error);
      throw error;
    }
  }
  
  setupMiddleware(app: Hono): void {
    if (!this.initialized) {
      throw new Error('Monitoring system must be initialized before setting up middleware');
    }
    
    // Set up all middleware in the correct order
    
    // 1. Correlation tracking (must be first to establish context)
    app.use('*', this.correlationTracker.createMiddleware());
    
    // 2. Distributed tracing
    app.use('*', this.tracingService.createMiddleware());
    
    // 3. Error tracking
    app.use('*', this.errorTracker.createMiddleware());
    
    // 4. Metrics collection (should be after correlation and tracing)
    this.prometheusMetrics.setupMiddleware(app);
    
    // 5. Health check endpoints
    this.healthService.setupRoutes(app);
    
    // 6. Performance monitoring endpoints
    app.get('/metrics/performance', async (c) => {
      const stats = this.performanceMonitor.getCurrentStats();
      return c.json(stats);
    });
    
    // 7. SLO status endpoints
    app.get('/metrics/slo', async (c) => {
      const sloStatus = this.sloTracker.getAllSLOCompliance();
      const sloArray = Array.from(sloStatus.entries()).map(([name, compliance]) => ({
        slo: name,
        ...compliance,
      }));
      return c.json(sloArray);
    });
    
    // 8. Anomaly endpoints
    app.get('/metrics/anomalies', async (c) => {
      const timeWindow = parseInt(c.req.query('timeWindow') || '3600000');
      const anomalies = this.anomalyDetector.getAnomalies(timeWindow);
      return c.json(anomalies);
    });
    
    // 9. Error tracking endpoints
    app.get('/metrics/errors', async (c) => {
      const errorMetrics = this.errorTracker.getErrorMetrics();
      return c.json(errorMetrics);
    });
    
    // 10. Reports endpoints
    app.get('/reports', async (c) => {
      const reports = this.reportingSystem.getReports();
      return c.json(reports);
    });
    
    app.get('/reports/:id', async (c) => {
      const reportId = c.req.param('id');
      const report = this.reportingSystem.getReport(reportId);
      
      if (!report) {
        return c.json({ error: 'Report not found' }, 404);
      }
      
      return c.json(report);
    });
    
    // 11. Monitoring system status endpoint
    app.get('/monitoring/status', async (c) => {
      const status = this.getSystemStatus();
      return c.json(status);
    });
    
    // 12. Force report generation endpoint
    app.post('/reports/generate/:configId', async (c) => {
      const configId = c.req.param('configId');
      
      try {
        const report = await this.reportingSystem.generateReport(configId);
        return c.json(report);
      } catch (error) {
        return c.json({ 
          error: 'Failed to generate report',
          message: error instanceof Error ? error.message : 'Unknown error'
        }, 500);
      }
    });
    
    console.log('Monitoring middleware configured');
  }
  
  private async handleCriticalAnomalies(anomalies: any[]): Promise<void> {
    console.log(`Handling ${anomalies.length} critical anomalies`);
    
    for (const anomaly of anomalies) {
      // Trigger appropriate runbook based on anomaly type
      const alertName = `CriticalAnomaly_${anomaly.detectionMethod}`;
      
      try {
        await this.runbookAutomation.handleAlert(alertName, {
          anomalyId: anomaly.id,
          metricName: anomaly.metricName,
          severity: anomaly.severity,
          value: anomaly.value,
          expectedValue: anomaly.expectedValue,
        });
        
        console.log(`Runbook triggered for anomaly: ${anomaly.id}`);
      } catch (error) {
        console.error(`Failed to trigger runbook for anomaly ${anomaly.id}:`, error);
      }
    }
  }
  
  private async handleSLOViolation(compliance: any): Promise<void> {
    console.log(`Handling SLO violation: ${compliance.sloName}`);
    
    const alertName = 'SLOViolation';
    
    try {
      await this.runbookAutomation.handleAlert(alertName, {
        sloName: compliance.sloName,
        target: compliance.target,
        actual: compliance.actual,
        compliance: compliance.compliance,
        errorBudget: compliance.errorBudget,
      });
      
      console.log(`Runbook triggered for SLO violation: ${compliance.sloName}`);
    } catch (error) {
      console.error(`Failed to trigger runbook for SLO violation ${compliance.sloName}:`, error);
    }
  }
  
  private async handleHealthIssue(healthStatus: any): Promise<void> {
    console.log(`Handling health issue: ${healthStatus.status}`);
    
    const alertName = 'HealthCheckFailure';
    
    try {
      await this.runbookAutomation.handleAlert(alertName, {
        status: healthStatus.status,
        checks: healthStatus.checks,
        summary: healthStatus.summary,
      });
      
      console.log('Runbook triggered for health check failure');
    } catch (error) {
      console.error('Failed to trigger runbook for health check failure:', error);
    }
  }
  
  // Monitoring system management methods
  
  getSystemStatus(): MonitoringSystemStatus {
    const componentsStatus: Record<string, any> = {};
    
    for (const [component, status] of this.componentStatus) {
      componentsStatus[component] = { ...status };
    }
    
    // Get metrics from various components
    const aggregatorStats = this.metricAggregator.getStatistics();
    const anomalyStats = this.anomalyDetector.getStatistics();
    const performanceStats = this.performanceMonitor.getCurrentStats();
    
    return {
      initialized: this.initialized,
      componentsStatus,
      metrics: {
        totalMetrics: aggregatorStats.totalMetrics,
        metricsPerSecond: aggregatorStats.totalDataPoints / 60, // Approximate
        tracesPerSecond: 0, // Would calculate from tracing service
        alertsActive: 0, // Would get from alerting system
        anomaliesDetected: anomalyStats.totalAnomalies,
      },
    };
  }
  
  async shutdown(): Promise<void> {
    console.log('Shutting down monitoring system...');
    
    try {
      // Shutdown tracing service
      await this.tracingService.shutdown();
      
      // Stop health checks
      this.healthService.stop();
      
      // Flush error tracker
      await this.errorTracker.flush();
      
      // Close error tracker
      await this.errorTracker.close();
      
      console.log('Monitoring system shutdown complete');
      
    } catch (error) {
      console.error('Error during monitoring system shutdown:', error);
    }
  }
  
  // Utility methods for instrumentation
  
  /**
   * Record a custom business metric
   */
  recordBusinessMetric(type: string, value: number, labels: Record<string, string> = {}): void {
    // Add business metric based on type
    const timestamp = Date.now();
    
    this.metricAggregator.addMetricPoint(`asi_code_business_${type}`, {
      timestamp,
      value,
      labels,
    });
  }
  
  /**
   * Record a session event
   */
  recordSessionEvent(sessionId: string, event: string, metadata: Record<string, any> = {}): void {
    switch (event) {
      case 'created':
        this.businessMetrics.trackSessionCreated(
          metadata.sessionType || 'default',
          metadata.provider || 'unknown',
          metadata.userId
        );
        break;
      case 'closed':
        this.businessMetrics.trackSessionClosed(
          metadata.sessionType || 'default',
          metadata.reason || 'completed',
          metadata.duration || 0
        );
        break;
    }
  }
  
  /**
   * Record a tool execution
   */
  recordToolExecution(toolName: string, success: boolean, duration: number, sessionId: string): void {
    this.businessMetrics.trackToolExecution(toolName, success, duration, sessionId);
  }
  
  /**
   * Record a provider request
   */
  recordProviderRequest(provider: string, model: string, tokens: number, cost: number): void {
    this.businessMetrics.trackProviderRequest(provider, model, tokens, cost);
  }
  
  /**
   * Record an error with context
   */
  recordError(error: Error, context: Record<string, any> = {}): string {
    return this.errorTracker.captureError(error, {
      tags: context.tags,
      extra: context.extra,
      level: context.level || 'error',
    });
  }
  
  /**
   * Start a performance profile
   */
  startPerformanceProfile(operation: string, metadata: Record<string, any> = {}): string {
    return this.performanceMonitor.startProfile(operation, metadata);
  }
  
  /**
   * End a performance profile
   */
  endPerformanceProfile(profileId: string): any {
    return this.performanceMonitor.endProfile(profileId);
  }
  
  isInitialized(): boolean {
    return this.initialized;
  }
}

export function createMonitoringSystem(options: MonitoringSystemOptions): MonitoringSystem {
  return new MonitoringSystem(options);
}