/**
 * Business Metrics for ASI-Code Operations
 * 
 * Tracks business-specific metrics including:
 * - Session lifecycle metrics
 * - Tool usage patterns
 * - Provider performance
 * - Kenny subsystem operations
 * - User interaction metrics
 * - Resource utilization
 */

import { Counter, Histogram, Gauge } from 'prom-client';
import type { PrometheusMetrics } from '../metrics/index.js';

export interface BusinessMetrics {
  // Session Metrics
  trackSessionCreated(sessionType: string, provider: string, userId?: string): void;
  trackSessionClosed(sessionType: string, reason: string, duration: number): void;
  trackSessionActivity(sessionId: string, activityType: string): void;
  
  // Tool Metrics
  trackToolExecution(toolName: string, success: boolean, duration: number, sessionId: string): void;
  trackToolError(toolName: string, errorType: string, sessionId: string): void;
  trackToolUsagePattern(toolName: string, sequence: string[]): void;
  
  // Provider Metrics
  trackProviderRequest(provider: string, model: string, tokens: number, cost: number): void;
  trackProviderLatency(provider: string, model: string, latency: number): void;
  trackProviderError(provider: string, model: string, errorType: string): void;
  
  // Kenny Subsystem Metrics
  trackKennyOperation(subsystem: string, operation: string, success: boolean, duration: number): void;
  trackKennyIntegration(fromSubsystem: string, toSubsystem: string, messageType: string): void;
  trackKennyStateChange(subsystem: string, fromState: string, toState: string): void;
  
  // User Interaction Metrics
  trackUserCommand(command: string, userId?: string): void;
  trackUserSession(userId: string, sessionDuration: number, commandCount: number): void;
  trackUserError(userId: string, errorType: string, command?: string): void;
  
  // Resource Metrics
  trackResourceUsage(resourceType: string, amount: number, unit: string): void;
  trackConcurrency(metric: string, currentValue: number): void;
  trackThroughput(operation: string, count: number, timeWindow: number): void;
}

export class ASICodeBusinessMetrics implements BusinessMetrics {
  private metrics: PrometheusMetrics;
  
  // Additional business-specific metrics
  private sessionLifecycle: Histogram<string>;
  private toolChains: Counter<string>;
  private providerCosts: Counter<string>;
  private kennyCommunication: Counter<string>;
  private userEngagement: Histogram<string>;
  private resourceEfficiency: Gauge<string>;
  private activeConnections: Gauge<string>;
  private queueDepth: Gauge<string>;
  private cachehitRate: Gauge<string>;
  
  constructor(metrics: PrometheusMetrics) {
    this.metrics = metrics;
    this.initializeBusinessMetrics();
  }
  
  private initializeBusinessMetrics(): void {
    this.sessionLifecycle = new Histogram({
      name: 'asi_code_session_lifecycle_duration_seconds',
      help: 'Duration of session lifecycle phases',
      labelNames: ['phase', 'session_type'],
      buckets: [0.1, 0.5, 1, 5, 10, 30, 60, 300],
    });
    
    this.toolChains = new Counter({
      name: 'asi_code_tool_chains_total',
      help: 'Tool execution chains and patterns',
      labelNames: ['chain_pattern', 'chain_length', 'success'],
    });
    
    this.providerCosts = new Counter({
      name: 'asi_code_provider_costs_total',
      help: 'Provider API costs',
      labelNames: ['provider', 'model', 'cost_type'],
    });
    
    this.kennyCommunication = new Counter({
      name: 'asi_code_kenny_communication_total',
      help: 'Kenny subsystem communication patterns',
      labelNames: ['from_subsystem', 'to_subsystem', 'message_type', 'status'],
    });
    
    this.userEngagement = new Histogram({
      name: 'asi_code_user_engagement_duration_seconds',
      help: 'User engagement session duration',
      labelNames: ['user_type', 'engagement_type'],
      buckets: [60, 300, 600, 1800, 3600, 7200],
    });
    
    this.resourceEfficiency = new Gauge({
      name: 'asi_code_resource_efficiency_percent',
      help: 'Resource utilization efficiency',
      labelNames: ['resource_type', 'component'],
    });
    
    this.activeConnections = new Gauge({
      name: 'asi_code_active_connections_count',
      help: 'Number of active connections',
      labelNames: ['connection_type', 'protocol'],
    });
    
    this.queueDepth = new Gauge({
      name: 'asi_code_queue_depth_count',
      help: 'Depth of various queues',
      labelNames: ['queue_type', 'priority'],
    });
    
    this.cachehitRate = new Gauge({
      name: 'asi_code_cache_hit_rate_percent',
      help: 'Cache hit rate percentage',
      labelNames: ['cache_type', 'cache_name'],
    });
  }
  
  // Session Metrics Implementation
  trackSessionCreated(sessionType: string, provider: string, userId?: string): void {
    this.metrics.recordSessionCreated(sessionType, provider);
    
    // Track session creation phase
    this.sessionLifecycle.observe(
      { phase: 'creation', session_type: sessionType },
      Date.now() / 1000
    );
  }
  
  trackSessionClosed(sessionType: string, reason: string, duration: number): void {
    this.metrics.recordSessionClosed(sessionType, reason);
    this.metrics.recordSessionDuration(sessionType, 'all', duration);
    
    // Track session closure phase
    this.sessionLifecycle.observe(
      { phase: 'closure', session_type: sessionType },
      duration
    );
  }
  
  trackSessionActivity(sessionId: string, activityType: string): void {
    // Track session activity patterns
    this.sessionLifecycle.observe(
      { phase: 'activity', session_type: activityType },
      1
    );
  }
  
  // Tool Metrics Implementation
  trackToolExecution(toolName: string, success: boolean, duration: number, sessionId: string): void {
    const status = success ? 'success' : 'failure';
    this.metrics.recordToolExecution(toolName, status, sessionId, duration);
  }
  
  trackToolError(toolName: string, errorType: string, sessionId: string): void {
    this.metrics.recordError(errorType, 'tool', 'error');
    this.trackToolExecution(toolName, false, 0, sessionId);
  }
  
  trackToolUsagePattern(toolName: string, sequence: string[]): void {
    const chainPattern = sequence.join('->', );
    const chainLength = sequence.length.toString();
    
    this.toolChains.inc({
      chain_pattern: chainPattern,
      chain_length: chainLength,
      success: 'true'
    });
  }
  
  // Provider Metrics Implementation
  trackProviderRequest(provider: string, model: string, tokens: number, cost: number): void {
    this.metrics.recordProviderRequest(provider, model, 'success', 0);
    
    // Track costs
    this.providerCosts.inc({
      provider,
      model,
      cost_type: 'tokens'
    }, tokens);
    
    this.providerCosts.inc({
      provider,
      model,
      cost_type: 'cost'
    }, cost);
  }
  
  trackProviderLatency(provider: string, model: string, latency: number): void {
    this.metrics.recordProviderRequest(provider, model, 'success', latency);
  }
  
  trackProviderError(provider: string, model: string, errorType: string): void {
    this.metrics.recordProviderRequest(provider, model, 'error', 0);
    this.metrics.recordError(errorType, 'provider', 'error');
  }
  
  // Kenny Subsystem Metrics Implementation
  trackKennyOperation(subsystem: string, operation: string, success: boolean, duration: number): void {
    const status = success ? 'success' : 'failure';
    this.metrics.recordKennyOperation(operation, subsystem, status, duration);
  }
  
  trackKennyIntegration(fromSubsystem: string, toSubsystem: string, messageType: string): void {
    this.kennyCommunication.inc({
      from_subsystem: fromSubsystem,
      to_subsystem: toSubsystem,
      message_type: messageType,
      status: 'sent'
    });
  }
  
  trackKennyStateChange(subsystem: string, fromState: string, toState: string): void {
    this.kennyCommunication.inc({
      from_subsystem: fromState,
      to_subsystem: toState,
      message_type: 'state_change',
      status: 'completed'
    });
  }
  
  // User Interaction Metrics Implementation
  trackUserCommand(command: string, userId?: string): void {
    // Track command usage patterns
    this.userEngagement.observe(
      { user_type: userId ? 'authenticated' : 'anonymous', engagement_type: 'command' },
      1
    );
  }
  
  trackUserSession(userId: string, sessionDuration: number, commandCount: number): void {
    this.userEngagement.observe(
      { user_type: 'authenticated', engagement_type: 'session' },
      sessionDuration
    );
    
    // Track session productivity
    const productivity = commandCount / (sessionDuration / 60); // commands per minute
    this.resourceEfficiency.set(
      { resource_type: 'user', component: 'productivity' },
      productivity
    );
  }
  
  trackUserError(userId: string, errorType: string, command?: string): void {
    this.metrics.recordError(errorType, 'user', 'warning');
  }
  
  // Resource Metrics Implementation
  trackResourceUsage(resourceType: string, amount: number, unit: string): void {
    this.resourceEfficiency.set(
      { resource_type: resourceType, component: unit },
      amount
    );
  }
  
  trackConcurrency(metric: string, currentValue: number): void {
    this.activeConnections.set(
      { connection_type: metric, protocol: 'all' },
      currentValue
    );
  }
  
  trackThroughput(operation: string, count: number, timeWindow: number): void {
    const throughput = count / (timeWindow / 1000); // operations per second
    this.resourceEfficiency.set(
      { resource_type: 'throughput', component: operation },
      throughput
    );
  }
  
  // Advanced Business Metrics
  trackCachePerformance(cacheType: string, hits: number, total: number): void {
    const hitRate = total > 0 ? (hits / total) * 100 : 0;
    this.cachehitRate.set(
      { cache_type: cacheType, cache_name: 'default' },
      hitRate
    );
  }
  
  trackQueueMetrics(queueType: string, depth: number, priority: string = 'normal'): void {
    this.queueDepth.set(
      { queue_type: queueType, priority },
      depth
    );
  }
  
  trackBusinessKPI(kpiName: string, value: number, target: number): void {
    const achievement = target > 0 ? (value / target) * 100 : 0;
    this.resourceEfficiency.set(
      { resource_type: 'kpi', component: kpiName },
      achievement
    );
  }
  
  // Real-time metrics updates
  updateActiveConnectionCount(type: string, count: number): void {
    this.activeConnections.set(
      { connection_type: type, protocol: 'websocket' },
      count
    );
  }
  
  updateSystemLoad(component: string, load: number): void {
    this.resourceEfficiency.set(
      { resource_type: 'system', component },
      load
    );
  }
}

export function createBusinessMetrics(prometheusMetrics: PrometheusMetrics): BusinessMetrics {
  return new ASICodeBusinessMetrics(prometheusMetrics);
}