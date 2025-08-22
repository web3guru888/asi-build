/**
 * Trace Sampling Configuration for ASI-Code
 * 
 * Intelligent sampling strategies for traces and metrics:
 * - Adaptive sampling based on system load
 * - Priority-based sampling for critical operations
 * - Error-biased sampling for debugging
 * - Cost-optimized sampling for high-volume systems
 * - Custom sampling rules and policies
 */

import { EventEmitter } from 'eventemitter3';
import type { MonitoringConfig } from '../index.js';

export interface SamplingRule {
  id: string;
  name: string;
  description: string;
  condition: SamplingCondition;
  action: SamplingAction;
  priority: number;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface SamplingCondition {
  type: 'always' | 'never' | 'probability' | 'rate_limit' | 'error_only' | 'custom';
  value?: number;
  customFunction?: (context: SamplingContext) => boolean;
  filters?: {
    component?: string[];
    operation?: string[];
    statusCode?: number[];
    userAgent?: string[];
    sessionType?: string[];
    errorType?: string[];
  };
}

export interface SamplingAction {
  type: 'sample' | 'drop' | 'prioritize';
  sampleRate?: number; // 0.0 to 1.0
  priority?: number;
  metadata?: Record<string, any>;
}

export interface SamplingContext {
  operationType: string;
  component: string;
  sessionId?: string;
  userId?: string;
  statusCode?: number;
  duration?: number;
  errorType?: string;
  userAgent?: string;
  requestSize?: number;
  responseSize?: number;
  isError: boolean;
  timestamp: number;
  metadata: Record<string, any>;
}

export interface SamplingDecision {
  shouldSample: boolean;
  sampleRate: number;
  priority: number;
  matchedRules: string[];
  metadata: Record<string, any>;
}

export interface SamplingStatistics {
  totalRequests: number;
  sampledRequests: number;
  droppedRequests: number;
  overallSampleRate: number;
  ruleStats: Record<string, {
    matchCount: number;
    sampleCount: number;
    dropCount: number;
    sampleRate: number;
  }>;
  componentStats: Record<string, {
    requests: number;
    sampled: number;
    sampleRate: number;
  }>;
  errorSamplingStats: {
    totalErrors: number;
    sampledErrors: number;
    errorSampleRate: number;
  };
}

export class TraceSampler extends EventEmitter {
  private config: MonitoringConfig['jaeger'];
  private rules: Map<string, SamplingRule> = new Map();
  private statistics: SamplingStatistics = {
    totalRequests: 0,
    sampledRequests: 0,
    droppedRequests: 0,
    overallSampleRate: 0,
    ruleStats: {},
    componentStats: {},
    errorSamplingStats: {
      totalErrors: 0,
      sampledErrors: 0,
      errorSampleRate: 0,
    },
  };
  private adaptiveSettings = {
    cpuThreshold: 80,
    memoryThreshold: 85,
    errorRateThreshold: 5,
    baselineRate: 0.1,
    minRate: 0.01,
    maxRate: 1.0,
  };
  
  constructor(config: MonitoringConfig['jaeger']) {
    super();
    this.config = config;
    this.initializeDefaultRules();
    this.startStatisticsReporting();
  }
  
  private initializeDefaultRules(): void {
    // High-priority operations (always sample)
    this.addRule({
      id: 'critical-operations',
      name: 'Critical Operations',
      description: 'Always sample critical operations',
      priority: 1,
      enabled: true,
      condition: {
        type: 'always',
        filters: {
          operation: ['session.create', 'session.close', 'auth.login', 'auth.logout'],
        },
      },
      action: {
        type: 'sample',
        sampleRate: 1.0,
        priority: 10,
      },
    });
    
    // Error operations (high sample rate)
    this.addRule({
      id: 'error-traces',
      name: 'Error Traces',
      description: 'High sample rate for error traces',
      priority: 2,
      enabled: true,
      condition: {
        type: 'error_only',
      },
      action: {
        type: 'sample',
        sampleRate: 0.8,
        priority: 8,
      },
    });
    
    // High-latency operations
    this.addRule({
      id: 'high-latency',
      name: 'High Latency Operations',
      description: 'Sample operations with high latency',
      priority: 3,
      enabled: true,
      condition: {
        type: 'custom',
        customFunction: (context) => (context.duration || 0) > 5000, // > 5 seconds
      },
      action: {
        type: 'sample',
        sampleRate: 0.5,
        priority: 7,
      },
    });
    
    // Provider operations (medium sample rate)
    this.addRule({
      id: 'provider-operations',
      name: 'Provider Operations',
      description: 'Sample provider requests',
      priority: 4,
      enabled: true,
      condition: {
        type: 'probability',
        value: 0.3,
        filters: {
          component: ['provider'],
        },
      },
      action: {
        type: 'sample',
        sampleRate: 0.3,
        priority: 5,
      },
    });
    
    // Tool executions (adaptive sampling)
    this.addRule({
      id: 'tool-executions',
      name: 'Tool Executions',
      description: 'Adaptive sampling for tool executions',
      priority: 5,
      enabled: true,
      condition: {
        type: 'custom',
        filters: {
          component: ['tool'],
        },
        customFunction: (context) => this.adaptiveSampleDecision(context),
      },
      action: {
        type: 'sample',
        sampleRate: this.config.samplingRate,
        priority: 4,
      },
    });
    
    // Health checks (low sample rate)
    this.addRule({
      id: 'health-checks',
      name: 'Health Checks',
      description: 'Low sample rate for health checks',
      priority: 6,
      enabled: true,
      condition: {
        type: 'probability',
        value: 0.01,
        filters: {
          operation: ['health.check', 'health.readiness', 'health.liveness'],
        },
      },
      action: {
        type: 'sample',
        sampleRate: 0.01,
        priority: 1,
      },
    });
    
    // Bot traffic (very low sample rate)
    this.addRule({
      id: 'bot-traffic',
      name: 'Bot Traffic',
      description: 'Very low sample rate for bot traffic',
      priority: 7,
      enabled: true,
      condition: {
        type: 'custom',
        customFunction: (context) => this.isBotTraffic(context),
      },
      action: {
        type: 'sample',
        sampleRate: 0.001,
        priority: 1,
      },
    });
    
    // Default rule (fallback)
    this.addRule({
      id: 'default',
      name: 'Default Sampling',
      description: 'Default sampling for all other requests',
      priority: 1000,
      enabled: true,
      condition: {
        type: 'probability',
        value: this.config.samplingRate,
      },
      action: {
        type: 'sample',
        sampleRate: this.config.samplingRate,
        priority: 2,
      },
    });
  }
  
  addRule(rule: SamplingRule): void {
    this.rules.set(rule.id, rule);
    this.statistics.ruleStats[rule.id] = {
      matchCount: 0,
      sampleCount: 0,
      dropCount: 0,
      sampleRate: 0,
    };
    this.emit('rule-added', rule);
  }
  
  removeRule(ruleId: string): boolean {
    const deleted = this.rules.delete(ruleId);
    if (deleted) {
      delete this.statistics.ruleStats[ruleId];
      this.emit('rule-removed', ruleId);
    }
    return deleted;
  }
  
  enableRule(ruleId: string): boolean {
    const rule = this.rules.get(ruleId);
    if (rule) {
      rule.enabled = true;
      this.emit('rule-enabled', rule);
      return true;
    }
    return false;
  }
  
  disableRule(ruleId: string): boolean {
    const rule = this.rules.get(ruleId);
    if (rule) {
      rule.enabled = false;
      this.emit('rule-disabled', rule);
      return true;
    }
    return false;
  }
  
  // Main sampling decision method
  shouldSample(context: SamplingContext): SamplingDecision {
    this.updateStatistics(context);
    
    // Get applicable rules sorted by priority
    const applicableRules = this.getApplicableRules(context);
    
    let shouldSample = false;
    let finalSampleRate = 0;
    let finalPriority = 0;
    const matchedRules: string[] = [];
    const metadata: Record<string, any> = {};
    
    // Apply rules in priority order
    for (const rule of applicableRules) {
      if (this.evaluateCondition(rule.condition, context)) {
        matchedRules.push(rule.id);
        this.statistics.ruleStats[rule.id].matchCount++;
        
        if (rule.action.type === 'sample') {
          shouldSample = true;
          finalSampleRate = Math.max(finalSampleRate, rule.action.sampleRate || 0);
          finalPriority = Math.max(finalPriority, rule.action.priority || 0);
          
          if (rule.action.metadata) {
            Object.assign(metadata, rule.action.metadata);
          }
          
          this.statistics.ruleStats[rule.id].sampleCount++;
        } else if (rule.action.type === 'drop') {
          shouldSample = false;
          finalSampleRate = 0;
          this.statistics.ruleStats[rule.id].dropCount++;
          break; // Drop rules are final
        }
      }
    }
    
    // Apply final sampling probability
    if (shouldSample && finalSampleRate < 1.0) {
      shouldSample = Math.random() < finalSampleRate;
    }
    
    // Update component statistics
    this.updateComponentStats(context, shouldSample);
    
    if (shouldSample) {
      this.statistics.sampledRequests++;
      if (context.isError) {
        this.statistics.errorSamplingStats.sampledErrors++;
      }
    } else {
      this.statistics.droppedRequests++;
    }
    
    const decision: SamplingDecision = {
      shouldSample,
      sampleRate: finalSampleRate,
      priority: finalPriority,
      matchedRules,
      metadata,
    };
    
    this.emit('sampling-decision', { context, decision });
    
    return decision;
  }
  
  private getApplicableRules(context: SamplingContext): SamplingRule[] {
    return Array.from(this.rules.values())
      .filter(rule => rule.enabled)
      .sort((a, b) => a.priority - b.priority);
  }
  
  private evaluateCondition(condition: SamplingCondition, context: SamplingContext): boolean {
    // Check filters first
    if (condition.filters) {
      if (!this.matchesFilters(condition.filters, context)) {
        return false;
      }
    }
    
    switch (condition.type) {
      case 'always':
        return true;
      
      case 'never':
        return false;
      
      case 'probability':
        return Math.random() < (condition.value || 0);
      
      case 'rate_limit':
        // Implement rate limiting logic here
        return this.rateLimitCheck(condition.value || 10);
      
      case 'error_only':
        return context.isError;
      
      case 'custom':
        return condition.customFunction ? condition.customFunction(context) : false;
      
      default:
        return false;
    }
  }
  
  private matchesFilters(filters: SamplingCondition['filters'], context: SamplingContext): boolean {
    if (filters?.component && !filters.component.includes(context.component)) {
      return false;
    }
    
    if (filters?.operation && !filters.operation.includes(context.operationType)) {
      return false;
    }
    
    if (filters?.statusCode && context.statusCode && !filters.statusCode.includes(context.statusCode)) {
      return false;
    }
    
    if (filters?.userAgent && context.userAgent && !filters.userAgent.some(ua => 
      context.userAgent!.toLowerCase().includes(ua.toLowerCase())
    )) {
      return false;
    }
    
    if (filters?.sessionType && context.metadata.sessionType && 
        !filters.sessionType.includes(context.metadata.sessionType)) {
      return false;
    }
    
    if (filters?.errorType && context.errorType && !filters.errorType.includes(context.errorType)) {
      return false;
    }
    
    return true;
  }
  
  private rateLimitCheck(maxPerSecond: number): boolean {
    // Simple rate limiting implementation
    const now = Date.now();
    const windowStart = Math.floor(now / 1000) * 1000;
    const key = `rate_limit_${windowStart}`;
    
    // In a real implementation, you'd use a proper rate limiter with Redis or similar
    // For now, we'll use a simple in-memory approach
    if (!this.rateLimitCounters) {
      this.rateLimitCounters = new Map();
    }
    
    const currentCount = this.rateLimitCounters.get(key) || 0;
    if (currentCount < maxPerSecond) {
      this.rateLimitCounters.set(key, currentCount + 1);
      return true;
    }
    
    return false;
  }
  
  private rateLimitCounters = new Map<string, number>();
  
  private adaptiveSampleDecision(context: SamplingContext): boolean {
    // Adaptive sampling based on system load and error rates
    const systemLoad = this.getCurrentSystemLoad();
    const errorRate = this.getCurrentErrorRate();
    
    let adaptedRate = this.adaptiveSettings.baselineRate;
    
    // Reduce sampling under high system load
    if (systemLoad.cpu > this.adaptiveSettings.cpuThreshold) {
      adaptedRate *= 0.5;
    }
    
    if (systemLoad.memory > this.adaptiveSettings.memoryThreshold) {
      adaptedRate *= 0.5;
    }
    
    // Increase sampling during high error rates
    if (errorRate > this.adaptiveSettings.errorRateThreshold) {
      adaptedRate *= 2;
    }
    
    // Apply bounds
    adaptedRate = Math.max(this.adaptiveSettings.minRate, adaptedRate);
    adaptedRate = Math.min(this.adaptiveSettings.maxRate, adaptedRate);
    
    return Math.random() < adaptedRate;
  }
  
  private getCurrentSystemLoad(): { cpu: number; memory: number } {
    // In a real implementation, this would get actual system metrics
    // For now, return simulated values
    return {
      cpu: Math.random() * 100,
      memory: Math.random() * 100,
    };
  }
  
  private getCurrentErrorRate(): number {
    // Calculate error rate from recent statistics
    const totalRequests = this.statistics.totalRequests;
    const totalErrors = this.statistics.errorSamplingStats.totalErrors;
    
    return totalRequests > 0 ? (totalErrors / totalRequests) * 100 : 0;
  }
  
  private isBotTraffic(context: SamplingContext): boolean {
    if (!context.userAgent) return false;
    
    const botPatterns = [
      'googlebot',
      'bingbot',
      'slackbot',
      'twitterbot',
      'facebookexternalhit',
      'linkedinbot',
      'whatsapp',
      'crawler',
      'spider',
      'bot',
    ];
    
    const userAgent = context.userAgent.toLowerCase();
    return botPatterns.some(pattern => userAgent.includes(pattern));
  }
  
  private updateStatistics(context: SamplingContext): void {
    this.statistics.totalRequests++;
    
    if (context.isError) {
      this.statistics.errorSamplingStats.totalErrors++;
    }
    
    // Update overall sample rate
    this.statistics.overallSampleRate = this.statistics.totalRequests > 0 
      ? this.statistics.sampledRequests / this.statistics.totalRequests
      : 0;
    
    // Update error sample rate
    this.statistics.errorSamplingStats.errorSampleRate = 
      this.statistics.errorSamplingStats.totalErrors > 0
        ? this.statistics.errorSamplingStats.sampledErrors / this.statistics.errorSamplingStats.totalErrors
        : 0;
  }
  
  private updateComponentStats(context: SamplingContext, sampled: boolean): void {
    const component = context.component;
    
    if (!this.statistics.componentStats[component]) {
      this.statistics.componentStats[component] = {
        requests: 0,
        sampled: 0,
        sampleRate: 0,
      };
    }
    
    const stats = this.statistics.componentStats[component];
    stats.requests++;
    
    if (sampled) {
      stats.sampled++;
    }
    
    stats.sampleRate = stats.requests > 0 ? stats.sampled / stats.requests : 0;
  }
  
  private startStatisticsReporting(): void {
    setInterval(() => {
      this.updateRuleStatistics();
      this.emit('statistics-updated', this.statistics);
    }, 60000); // Update every minute
  }
  
  private updateRuleStatistics(): void {
    for (const [ruleId, stats] of Object.entries(this.statistics.ruleStats)) {
      const totalMatches = stats.sampleCount + stats.dropCount;
      stats.sampleRate = totalMatches > 0 ? stats.sampleCount / totalMatches : 0;
    }
  }
  
  // Configuration methods
  
  updateAdaptiveSettings(settings: Partial<typeof this.adaptiveSettings>): void {
    Object.assign(this.adaptiveSettings, settings);
    this.emit('adaptive-settings-updated', this.adaptiveSettings);
  }
  
  updateRule(ruleId: string, updates: Partial<SamplingRule>): boolean {
    const rule = this.rules.get(ruleId);
    if (rule) {
      Object.assign(rule, updates);
      this.emit('rule-updated', rule);
      return true;
    }
    return false;
  }
  
  // Query methods
  
  getRules(): SamplingRule[] {
    return Array.from(this.rules.values());
  }
  
  getRule(ruleId: string): SamplingRule | undefined {
    return this.rules.get(ruleId);
  }
  
  getStatistics(): SamplingStatistics {
    return JSON.parse(JSON.stringify(this.statistics));
  }
  
  getComponentStatistics(): Record<string, { requests: number; sampled: number; sampleRate: number }> {
    return JSON.parse(JSON.stringify(this.statistics.componentStats));
  }
  
  getRuleStatistics(): Record<string, { matchCount: number; sampleCount: number; dropCount: number; sampleRate: number }> {
    return JSON.parse(JSON.stringify(this.statistics.ruleStats));
  }
  
  // Testing and debugging methods
  
  testSampling(context: SamplingContext): {
    decision: SamplingDecision;
    ruleEvaluations: Array<{
      ruleId: string;
      ruleName: string;
      matched: boolean;
      action?: SamplingAction;
    }>;
  } {
    const ruleEvaluations: any[] = [];
    
    for (const rule of this.getApplicableRules(context)) {
      const matched = this.evaluateCondition(rule.condition, context);
      ruleEvaluations.push({
        ruleId: rule.id,
        ruleName: rule.name,
        matched,
        action: matched ? rule.action : undefined,
      });
    }
    
    const decision = this.shouldSample(context);
    
    return { decision, ruleEvaluations };
  }
  
  resetStatistics(): void {
    this.statistics = {
      totalRequests: 0,
      sampledRequests: 0,
      droppedRequests: 0,
      overallSampleRate: 0,
      ruleStats: {},
      componentStats: {},
      errorSamplingStats: {
        totalErrors: 0,
        sampledErrors: 0,
        errorSampleRate: 0,
      },
    };
    
    // Reset rule stats
    for (const ruleId of this.rules.keys()) {
      this.statistics.ruleStats[ruleId] = {
        matchCount: 0,
        sampleCount: 0,
        dropCount: 0,
        sampleRate: 0,
      };
    }
    
    this.emit('statistics-reset');
  }
}

export function createTraceSampler(config: MonitoringConfig['jaeger']): TraceSampler {
  return new TraceSampler(config);
}