/**
 * Prometheus Metrics Collection System
 * 
 * Provides comprehensive metrics for ASI-Code including:
 * - HTTP request metrics
 * - Business logic metrics
 * - System performance metrics
 * - Custom application metrics
 */

import { Counter, Gauge, Histogram, Summary, collectDefaultMetrics, register } from 'prom-client';
import type { Hono } from 'hono';
import type { MonitoringConfig } from '../index.js';
import * as os from 'os';
import * as pidusage from 'pidusage';
import * as si from 'systeminformation';

export class PrometheusMetrics {
  private readonly config: MonitoringConfig['prometheus'];
  
  // HTTP Metrics
  private httpRequestsTotal: Counter<string>;
  private httpRequestDuration: Histogram<string>;
  private httpRequestSize: Histogram<string>;
  private httpResponseSize: Histogram<string>;
  
  // ASI-Code Business Metrics
  private sessionCreated: Counter<string>;
  private sessionClosed: Counter<string>;
  private sessionDuration: Histogram<string>;
  private toolExecutions: Counter<string>;
  private toolExecutionDuration: Histogram<string>;
  private providerRequests: Counter<string>;
  private providerRequestDuration: Histogram<string>;
  private kennyOperations: Counter<string>;
  private kennyOperationDuration: Histogram<string>;
  
  // System Performance Metrics
  private systemCpuUsage: Gauge<string>;
  private systemMemoryUsage: Gauge<string>;
  private systemDiskUsage: Gauge<string>;
  private systemNetworkIO: Gauge<string>;
  private processCpuUsage: Gauge<string>;
  private processMemoryUsage: Gauge<string>;
  private processUptime: Gauge<string>;
  
  // Error Metrics
  private errorRate: Counter<string>;
  private errorsByType: Counter<string>;
  
  // SLO/SLI Metrics
  private sliAvailability: Gauge<string>;
  private sliLatency: Summary<string>;
  private sliErrorRate: Gauge<string>;
  
  constructor(config: MonitoringConfig['prometheus']) {
    this.config = config;
    this.initializeMetrics();
    
    if (config.collectDefaultMetrics) {
      collectDefaultMetrics({ register });
    }
    
    this.startSystemMetricsCollection();
  }
  
  private initializeMetrics(): void {
    // HTTP Metrics
    this.httpRequestsTotal = new Counter({
      name: 'asi_code_http_requests_total',
      help: 'Total number of HTTP requests',
      labelNames: ['method', 'route', 'status_code', 'endpoint'],
      registers: [register],
    });
    
    this.httpRequestDuration = new Histogram({
      name: 'asi_code_http_request_duration_seconds',
      help: 'Duration of HTTP requests in seconds',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10],
      registers: [register],
    });
    
    this.httpRequestSize = new Histogram({
      name: 'asi_code_http_request_size_bytes',
      help: 'Size of HTTP requests in bytes',
      labelNames: ['method', 'route'],
      buckets: [100, 1000, 10000, 100000, 1000000],
      registers: [register],
    });
    
    this.httpResponseSize = new Histogram({
      name: 'asi_code_http_response_size_bytes',
      help: 'Size of HTTP responses in bytes',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [100, 1000, 10000, 100000, 1000000],
      registers: [register],
    });
    
    // ASI-Code Business Metrics
    this.sessionCreated = new Counter({
      name: 'asi_code_sessions_created_total',
      help: 'Total number of sessions created',
      labelNames: ['session_type', 'provider'],
      registers: [register],
    });
    
    this.sessionClosed = new Counter({
      name: 'asi_code_sessions_closed_total',
      help: 'Total number of sessions closed',
      labelNames: ['session_type', 'reason'],
      registers: [register],
    });
    
    this.sessionDuration = new Histogram({
      name: 'asi_code_session_duration_seconds',
      help: 'Duration of sessions in seconds',
      labelNames: ['session_type', 'provider'],
      buckets: [1, 5, 10, 30, 60, 300, 600, 1800, 3600],
      registers: [register],
    });
    
    this.toolExecutions = new Counter({
      name: 'asi_code_tool_executions_total',
      help: 'Total number of tool executions',
      labelNames: ['tool_name', 'status', 'session_id'],
      registers: [register],
    });
    
    this.toolExecutionDuration = new Histogram({
      name: 'asi_code_tool_execution_duration_seconds',
      help: 'Duration of tool executions in seconds',
      labelNames: ['tool_name', 'status'],
      buckets: [0.01, 0.1, 0.5, 1, 2, 5, 10, 30],
      registers: [register],
    });
    
    this.providerRequests = new Counter({
      name: 'asi_code_provider_requests_total',
      help: 'Total number of provider requests',
      labelNames: ['provider_name', 'model', 'status'],
      registers: [register],
    });
    
    this.providerRequestDuration = new Histogram({
      name: 'asi_code_provider_request_duration_seconds',
      help: 'Duration of provider requests in seconds',
      labelNames: ['provider_name', 'model'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60],
      registers: [register],
    });
    
    this.kennyOperations = new Counter({
      name: 'asi_code_kenny_operations_total',
      help: 'Total number of Kenny subsystem operations',
      labelNames: ['operation_type', 'subsystem', 'status'],
      registers: [register],
    });
    
    this.kennyOperationDuration = new Histogram({
      name: 'asi_code_kenny_operation_duration_seconds',
      help: 'Duration of Kenny operations in seconds',
      labelNames: ['operation_type', 'subsystem'],
      buckets: [0.001, 0.01, 0.1, 0.5, 1, 2, 5],
      registers: [register],
    });
    
    // System Performance Metrics
    this.systemCpuUsage = new Gauge({
      name: 'asi_code_system_cpu_usage_percent',
      help: 'System CPU usage percentage',
      registers: [register],
    });
    
    this.systemMemoryUsage = new Gauge({
      name: 'asi_code_system_memory_usage_bytes',
      help: 'System memory usage in bytes',
      labelNames: ['type'],
      registers: [register],
    });
    
    this.systemDiskUsage = new Gauge({
      name: 'asi_code_system_disk_usage_bytes',
      help: 'System disk usage in bytes',
      labelNames: ['filesystem', 'mount'],
      registers: [register],
    });
    
    this.systemNetworkIO = new Gauge({
      name: 'asi_code_system_network_io_bytes',
      help: 'System network I/O in bytes',
      labelNames: ['direction', 'interface'],
      registers: [register],
    });
    
    this.processCpuUsage = new Gauge({
      name: 'asi_code_process_cpu_usage_percent',
      help: 'Process CPU usage percentage',
      registers: [register],
    });
    
    this.processMemoryUsage = new Gauge({
      name: 'asi_code_process_memory_usage_bytes',
      help: 'Process memory usage in bytes',
      labelNames: ['type'],
      registers: [register],
    });
    
    this.processUptime = new Gauge({
      name: 'asi_code_process_uptime_seconds',
      help: 'Process uptime in seconds',
      registers: [register],
    });
    
    // Error Metrics
    this.errorRate = new Counter({
      name: 'asi_code_errors_total',
      help: 'Total number of errors',
      labelNames: ['error_type', 'component', 'severity'],
      registers: [register],
    });
    
    this.errorsByType = new Counter({
      name: 'asi_code_errors_by_type_total',
      help: 'Total number of errors by type',
      labelNames: ['error_class', 'error_message'],
      registers: [register],
    });
    
    // SLO/SLI Metrics
    this.sliAvailability = new Gauge({
      name: 'asi_code_sli_availability_percent',
      help: 'Service availability SLI',
      registers: [register],
    });
    
    this.sliLatency = new Summary({
      name: 'asi_code_sli_latency_seconds',
      help: 'Service latency SLI',
      percentiles: [0.5, 0.9, 0.95, 0.99],
      registers: [register],
    });
    
    this.sliErrorRate = new Gauge({
      name: 'asi_code_sli_error_rate_percent',
      help: 'Service error rate SLI',
      registers: [register],
    });
  }
  
  // HTTP Metrics Methods
  recordHttpRequest(method: string, route: string, statusCode: number, duration: number, endpoint: string): void {
    this.httpRequestsTotal.inc({ method, route, status_code: statusCode.toString(), endpoint });
    this.httpRequestDuration.observe({ method, route, status_code: statusCode.toString() }, duration);
  }
  
  recordHttpRequestSize(method: string, route: string, size: number): void {
    this.httpRequestSize.observe({ method, route }, size);
  }
  
  recordHttpResponseSize(method: string, route: string, statusCode: number, size: number): void {
    this.httpResponseSize.observe({ method, route, status_code: statusCode.toString() }, size);
  }
  
  // Business Metrics Methods
  recordSessionCreated(sessionType: string, provider: string): void {
    this.sessionCreated.inc({ session_type: sessionType, provider });
  }
  
  recordSessionClosed(sessionType: string, reason: string): void {
    this.sessionClosed.inc({ session_type: sessionType, reason });
  }
  
  recordSessionDuration(sessionType: string, provider: string, duration: number): void {
    this.sessionDuration.observe({ session_type: sessionType, provider }, duration);
  }
  
  recordToolExecution(toolName: string, status: string, sessionId: string, duration: number): void {
    this.toolExecutions.inc({ tool_name: toolName, status, session_id: sessionId });
    this.toolExecutionDuration.observe({ tool_name: toolName, status }, duration);
  }
  
  recordProviderRequest(providerName: string, model: string, status: string, duration: number): void {
    this.providerRequests.inc({ provider_name: providerName, model, status });
    this.providerRequestDuration.observe({ provider_name: providerName, model }, duration);
  }
  
  recordKennyOperation(operationType: string, subsystem: string, status: string, duration: number): void {
    this.kennyOperations.inc({ operation_type: operationType, subsystem, status });
    this.kennyOperationDuration.observe({ operation_type: operationType, subsystem }, duration);
  }
  
  // Error Metrics Methods
  recordError(errorType: string, component: string, severity: string): void {
    this.errorRate.inc({ error_type: errorType, component, severity });
  }
  
  recordErrorByType(errorClass: string, errorMessage: string): void {
    this.errorsByType.inc({ error_class: errorClass, error_message: errorMessage });
  }
  
  // SLI Methods
  updateAvailability(availability: number): void {
    this.sliAvailability.set(availability);
  }
  
  recordLatency(latency: number): void {
    this.sliLatency.observe(latency);
  }
  
  updateErrorRate(errorRate: number): void {
    this.sliErrorRate.set(errorRate);
  }
  
  private async startSystemMetricsCollection(): Promise<void> {
    setInterval(async () => {
      try {
        // System CPU
        const cpuData = await si.currentLoad();
        this.systemCpuUsage.set(cpuData.currentLoad);
        
        // System Memory
        const memData = await si.mem();
        this.systemMemoryUsage.set({ type: 'total' }, memData.total);
        this.systemMemoryUsage.set({ type: 'used' }, memData.used);
        this.systemMemoryUsage.set({ type: 'free' }, memData.free);
        
        // System Disk
        const diskData = await si.fsSize();
        diskData.forEach(disk => {
          this.systemDiskUsage.set({ filesystem: disk.fs, mount: disk.mount }, disk.used);
        });
        
        // Process metrics
        const processStats = await pidusage(process.pid);
        this.processCpuUsage.set(processStats.cpu);
        this.processMemoryUsage.set({ type: 'rss' }, process.memoryUsage().rss);
        this.processMemoryUsage.set({ type: 'heap_used' }, process.memoryUsage().heapUsed);
        this.processMemoryUsage.set({ type: 'heap_total' }, process.memoryUsage().heapTotal);
        this.processUptime.set(process.uptime());
        
      } catch (error) {
        console.error('Error collecting system metrics:', error);
      }
    }, 10000); // Collect every 10 seconds
  }
  
  setupMiddleware(app: Hono): void {
    // Metrics endpoint
    app.get(this.config.path, async (c) => {
      const metrics = await register.metrics();
      return c.text(metrics, 200, {
        'Content-Type': register.contentType,
      });
    });
    
    // Request metrics middleware
    app.use('*', async (c, next) => {
      const start = Date.now();
      const method = c.req.method;
      const route = c.req.path;
      
      await next();
      
      const duration = (Date.now() - start) / 1000;
      const statusCode = c.res.status;
      
      this.recordHttpRequest(method, route, statusCode, duration, route);
      
      // Record request/response sizes if available
      const requestSize = parseInt(c.req.header('content-length') || '0');
      const responseSize = c.res.headers.get('content-length') 
        ? parseInt(c.res.headers.get('content-length')!)
        : 0;
      
      if (requestSize > 0) {
        this.recordHttpRequestSize(method, route, requestSize);
      }
      
      if (responseSize > 0) {
        this.recordHttpResponseSize(method, route, statusCode, responseSize);
      }
    });
  }
  
  getRegistry() {
    return register;
  }
}

export function createPrometheusMetrics(config: MonitoringConfig['prometheus']): PrometheusMetrics {
  return new PrometheusMetrics(config);
}