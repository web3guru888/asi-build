/**
 * SLO/SLI Tracking System for ASI-Code
 * 
 * Implements comprehensive Service Level Objectives (SLO) and Service Level Indicators (SLI) tracking:
 * - Availability tracking
 * - Latency percentile monitoring
 * - Error rate calculations
 * - Error budget management
 * - Burn rate alerting
 * - Historical SLO compliance reporting
 */

import { EventEmitter } from 'eventemitter3';
import type { PrometheusMetrics } from '../metrics/index.js';
import type { MonitoringConfig } from '../index.js';

export interface SLOTarget {
  name: string;
  description: string;
  target: number; // Target percentage (e.g., 99.9 for 99.9%)
  timeWindow: number; // Time window in seconds (e.g., 2592000 for 30 days)
  errorBudget: number; // Calculated based on target
}

export interface SLI {
  name: string;
  description: string;
  query: string; // Prometheus query to calculate the SLI
  unit: string;
  goodEvents: string; // Query for good events
  totalEvents: string; // Query for total events
}

export interface SLOCompliance {
  sloName: string;
  target: number;
  actual: number;
  compliance: number; // Percentage compliance
  errorBudget: {
    total: number;
    consumed: number;
    remaining: number;
    consumptionRate: number;
  };
  status: 'compliant' | 'at_risk' | 'violated';
  timeWindow: number;
  timestamp: number;
}

export interface BurnRateAlert {
  sloName: string;
  severity: 'warning' | 'critical';
  burnRate: number;
  threshold: number;
  timeToExhaustion: number; // Hours until error budget is exhausted
  timestamp: number;
}

export class SLOTracker extends EventEmitter {
  private config: MonitoringConfig['slo'];
  private metrics: PrometheusMetrics;
  private slos: Map<string, SLOTarget> = new Map();
  private slis: Map<string, SLI> = new Map();
  private complianceHistory: Map<string, SLOCompliance[]> = new Map();
  private burnRateThresholds: Map<string, number[]> = new Map();
  
  constructor(config: MonitoringConfig['slo'], metrics: PrometheusMetrics) {
    super();
    this.config = config;
    this.metrics = metrics;
    this.initializeDefaultSLOs();
    this.initializeDefaultSLIs();
    this.startPeriodicTracking();
  }
  
  private initializeDefaultSLOs(): void {
    // Availability SLO
    this.addSLO({
      name: 'availability',
      description: 'Service availability',
      target: this.config.targets.availability || 99.9,
      timeWindow: 2592000, // 30 days
      errorBudget: 0, // Will be calculated
    });
    
    // Latency SLO
    this.addSLO({
      name: 'latency',
      description: 'Response latency P95',
      target: 95.0, // 95% of requests under threshold
      timeWindow: 2592000, // 30 days
      errorBudget: 0,
    });
    
    // Error Rate SLO
    this.addSLO({
      name: 'error_rate',
      description: 'Error rate',
      target: 99.9, // 99.9% success rate
      timeWindow: 2592000, // 30 days
      errorBudget: 0,
    });
    
    // Session Success Rate SLO
    this.addSLO({
      name: 'session_success_rate',
      description: 'Session completion success rate',
      target: 95.0,
      timeWindow: 604800, // 7 days
      errorBudget: 0,
    });
    
    // Tool Execution Success Rate SLO
    this.addSLO({
      name: 'tool_success_rate',
      description: 'Tool execution success rate',
      target: 98.0,
      timeWindow: 604800, // 7 days
      errorBudget: 0,
    });
  }
  
  private initializeDefaultSLIs(): void {
    // Availability SLI
    this.addSLI({
      name: 'availability',
      description: 'Percentage of successful requests',
      query: 'rate(asi_code_http_requests_total{status_code!~"5.."}[5m]) / rate(asi_code_http_requests_total[5m]) * 100',
      unit: 'percent',
      goodEvents: 'asi_code_http_requests_total{status_code!~"5.."}',
      totalEvents: 'asi_code_http_requests_total',
    });
    
    // Latency SLI
    this.addSLI({
      name: 'latency',
      description: 'P95 response time under threshold',
      query: 'histogram_quantile(0.95, rate(asi_code_http_request_duration_seconds_bucket[5m]))',
      unit: 'seconds',
      goodEvents: 'asi_code_http_requests_total{le="0.2"}',
      totalEvents: 'asi_code_http_requests_total',
    });
    
    // Error Rate SLI
    this.addSLI({
      name: 'error_rate',
      description: 'Percentage of requests that result in errors',
      query: 'rate(asi_code_errors_total[5m]) / rate(asi_code_http_requests_total[5m]) * 100',
      unit: 'percent',
      goodEvents: 'asi_code_http_requests_total{status_code!~"[45].."}',
      totalEvents: 'asi_code_http_requests_total',
    });
    
    // Session Success Rate SLI
    this.addSLI({
      name: 'session_success_rate',
      description: 'Percentage of successfully completed sessions',
      query: 'rate(asi_code_sessions_closed_total{reason="completed"}[5m]) / rate(asi_code_sessions_closed_total[5m]) * 100',
      unit: 'percent',
      goodEvents: 'asi_code_sessions_closed_total{reason="completed"}',
      totalEvents: 'asi_code_sessions_closed_total',
    });
    
    // Tool Success Rate SLI
    this.addSLI({
      name: 'tool_success_rate',
      description: 'Percentage of successful tool executions',
      query: 'rate(asi_code_tool_executions_total{status="success"}[5m]) / rate(asi_code_tool_executions_total[5m]) * 100',
      unit: 'percent',
      goodEvents: 'asi_code_tool_executions_total{status="success"}',
      totalEvents: 'asi_code_tool_executions_total',
    });
  }
  
  addSLO(slo: SLOTarget): void {
    // Calculate error budget
    slo.errorBudget = this.calculateErrorBudget(slo.target, slo.timeWindow);
    
    this.slos.set(slo.name, slo);
    this.complianceHistory.set(slo.name, []);
    
    // Set burn rate thresholds
    this.setBurnRateThresholds(slo.name, [
      1,    // 1x burn rate - budget exhausted in 30 days
      2,    // 2x burn rate - budget exhausted in 15 days
      5,    // 5x burn rate - budget exhausted in 6 days
      10,   // 10x burn rate - budget exhausted in 3 days
      14.4, // 14.4x burn rate - budget exhausted in 2 days
    ]);
    
    this.emit('slo-added', slo);
  }
  
  addSLI(sli: SLI): void {
    this.slis.set(sli.name, sli);
    this.emit('sli-added', sli);
  }
  
  private calculateErrorBudget(target: number, timeWindow: number): number {
    // Error budget = (100 - target) / 100 * timeWindow
    return ((100 - target) / 100) * timeWindow;
  }
  
  private setBurnRateThresholds(sloName: string, thresholds: number[]): void {
    this.burnRateThresholds.set(sloName, thresholds);
  }
  
  private startPeriodicTracking(): void {
    // Track SLO compliance every minute
    setInterval(() => {
      this.trackAllSLOs().catch(error => {
        console.error('Error tracking SLOs:', error);
      });
    }, 60000);
    
    // Check burn rates every 30 seconds
    setInterval(() => {
      this.checkBurnRates().catch(error => {
        console.error('Error checking burn rates:', error);
      });
    }, 30000);
  }
  
  async trackAllSLOs(): Promise<void> {
    const promises = Array.from(this.slos.keys()).map(sloName => 
      this.trackSLO(sloName)
    );
    
    await Promise.all(promises);
  }
  
  async trackSLO(sloName: string): Promise<SLOCompliance | null> {
    const slo = this.slos.get(sloName);
    const sli = this.slis.get(sloName);
    
    if (!slo || !sli) {
      console.warn(`SLO or SLI not found for: ${sloName}`);
      return null;
    }
    
    try {
      // Calculate current SLI value
      const actualValue = await this.calculateSLIValue(sli);
      
      // Calculate compliance
      const compliance = this.calculateCompliance(slo, actualValue);
      
      // Track in history
      this.addComplianceRecord(sloName, compliance);
      
      // Update Prometheus metrics
      this.updateSLOMetrics(sloName, compliance);
      
      this.emit('slo-tracked', compliance);
      
      return compliance;
    } catch (error) {
      console.error(`Error tracking SLO ${sloName}:`, error);
      return null;
    }
  }
  
  private async calculateSLIValue(sli: SLI): Promise<number> {
    // In a real implementation, this would query Prometheus
    // For now, we'll simulate the calculation
    
    // Simulate different SLI values based on the SLI name
    switch (sli.name) {
      case 'availability':
        return 99.95; // 99.95% availability
      case 'latency':
        return 0.15; // 150ms P95 latency
      case 'error_rate':
        return 0.05; // 0.05% error rate
      case 'session_success_rate':
        return 96.2; // 96.2% session success rate
      case 'tool_success_rate':
        return 98.8; // 98.8% tool success rate
      default:
        return Math.random() * 100; // Random value for unknown SLIs
    }
  }
  
  private calculateCompliance(slo: SLOTarget, actualValue: number): SLOCompliance {
    const target = slo.target;
    let compliance: number;
    let status: 'compliant' | 'at_risk' | 'violated';
    
    // For availability and success rates (higher is better)
    if (slo.name.includes('availability') || slo.name.includes('success')) {
      compliance = (actualValue / target) * 100;
      status = actualValue >= target ? 'compliant' : 
               actualValue >= target * 0.95 ? 'at_risk' : 'violated';
    }
    // For error rates and latency (lower is better)
    else {
      const threshold = slo.name === 'latency' ? 0.2 : (100 - target); // 200ms for latency, error threshold for others
      compliance = actualValue <= threshold ? 100 : ((threshold / actualValue) * 100);
      status = actualValue <= threshold ? 'compliant' : 
               actualValue <= threshold * 1.2 ? 'at_risk' : 'violated';
    }
    
    // Calculate error budget consumption
    const errorBudget = this.calculateErrorBudgetStatus(slo, actualValue);
    
    return {
      sloName: slo.name,
      target,
      actual: actualValue,
      compliance: Math.min(compliance, 100),
      errorBudget,
      status,
      timeWindow: slo.timeWindow,
      timestamp: Date.now(),
    };
  }
  
  private calculateErrorBudgetStatus(slo: SLOTarget, actualValue: number): SLOCompliance['errorBudget'] {
    const totalBudget = slo.errorBudget;
    let consumed: number;
    
    // Calculate consumption based on SLO type
    if (slo.name.includes('availability') || slo.name.includes('success')) {
      const errorRate = 100 - actualValue;
      consumed = (errorRate / (100 - slo.target)) * totalBudget;
    } else {
      // For error rate SLOs
      consumed = (actualValue / (100 - slo.target)) * totalBudget;
    }
    
    consumed = Math.max(0, Math.min(consumed, totalBudget));
    const remaining = totalBudget - consumed;
    const consumptionRate = consumed / totalBudget;
    
    return {
      total: totalBudget,
      consumed,
      remaining,
      consumptionRate,
    };
  }
  
  private addComplianceRecord(sloName: string, compliance: SLOCompliance): void {
    const history = this.complianceHistory.get(sloName) || [];
    history.push(compliance);
    
    // Keep only the last 1000 records
    if (history.length > 1000) {
      history.splice(0, history.length - 1000);
    }
    
    this.complianceHistory.set(sloName, history);
  }
  
  private updateSLOMetrics(sloName: string, compliance: SLOCompliance): void {
    // Update availability metric
    if (sloName === 'availability') {
      this.metrics.updateAvailability(compliance.actual);
    }
    
    // Update latency metric
    if (sloName === 'latency') {
      this.metrics.recordLatency(compliance.actual);
    }
    
    // Update error rate metric
    if (sloName === 'error_rate') {
      this.metrics.updateErrorRate(compliance.actual);
    }
  }
  
  private async checkBurnRates(): Promise<void> {
    for (const [sloName, slo] of this.slos) {
      const thresholds = this.burnRateThresholds.get(sloName) || [];
      
      for (const threshold of thresholds) {
        const burnRate = await this.calculateBurnRate(sloName, threshold);
        
        if (burnRate > threshold) {
          const alert: BurnRateAlert = {
            sloName,
            severity: threshold > 10 ? 'critical' : 'warning',
            burnRate,
            threshold,
            timeToExhaustion: this.calculateTimeToExhaustion(burnRate, slo.timeWindow),
            timestamp: Date.now(),
          };
          
          this.emit('burn-rate-alert', alert);
        }
      }
    }
  }
  
  private async calculateBurnRate(sloName: string, timeWindow: number): Promise<number> {
    // In a real implementation, this would calculate the actual burn rate
    // For now, we'll simulate based on current error rate
    
    const recentCompliance = this.getRecentCompliance(sloName, 5); // Last 5 minutes
    if (recentCompliance.length === 0) return 0;
    
    const avgCompliance = recentCompliance.reduce((sum, c) => sum + c.compliance, 0) / recentCompliance.length;
    const burnRate = (100 - avgCompliance) / 100;
    
    return burnRate * timeWindow;
  }
  
  private calculateTimeToExhaustion(burnRate: number, timeWindow: number): number {
    // Calculate hours until error budget is exhausted at current burn rate
    return (timeWindow / burnRate) / 3600; // Convert to hours
  }
  
  // Public API methods
  
  getSLOCompliance(sloName: string): SLOCompliance | null {
    const history = this.complianceHistory.get(sloName);
    return history && history.length > 0 ? history[history.length - 1] : null;
  }
  
  getAllSLOCompliance(): Map<string, SLOCompliance | null> {
    const result = new Map<string, SLOCompliance | null>();
    
    for (const sloName of this.slos.keys()) {
      result.set(sloName, this.getSLOCompliance(sloName));
    }
    
    return result;
  }
  
  getComplianceHistory(sloName: string, timeWindow?: number): SLOCompliance[] {
    const history = this.complianceHistory.get(sloName) || [];
    
    if (!timeWindow) return [...history];
    
    const cutoff = Date.now() - timeWindow;
    return history.filter(c => c.timestamp > cutoff);
  }
  
  private getRecentCompliance(sloName: string, minutes: number): SLOCompliance[] {
    return this.getComplianceHistory(sloName, minutes * 60 * 1000);
  }
  
  getSLOStatus(): { total: number; compliant: number; at_risk: number; violated: number } {
    const statuses = Array.from(this.slos.keys())
      .map(name => this.getSLOCompliance(name))
      .filter(Boolean) as SLOCompliance[];
    
    return {
      total: statuses.length,
      compliant: statuses.filter(s => s.status === 'compliant').length,
      at_risk: statuses.filter(s => s.status === 'at_risk').length,
      violated: statuses.filter(s => s.status === 'violated').length,
    };
  }
  
  getErrorBudgetSummary(): Record<string, { remaining: number; consumptionRate: number; status: string }> {
    const summary: Record<string, { remaining: number; consumptionRate: number; status: string }> = {};
    
    for (const sloName of this.slos.keys()) {
      const compliance = this.getSLOCompliance(sloName);
      if (compliance) {
        const { remaining, consumptionRate } = compliance.errorBudget;
        const status = consumptionRate > 0.8 ? 'critical' : 
                      consumptionRate > 0.5 ? 'warning' : 'healthy';
        
        summary[sloName] = { remaining, consumptionRate, status };
      }
    }
    
    return summary;
  }
  
  // Configuration methods
  
  updateSLOTarget(sloName: string, newTarget: number): boolean {
    const slo = this.slos.get(sloName);
    if (!slo) return false;
    
    slo.target = newTarget;
    slo.errorBudget = this.calculateErrorBudget(newTarget, slo.timeWindow);
    
    this.emit('slo-updated', slo);
    return true;
  }
  
  getSLOs(): SLOTarget[] {
    return Array.from(this.slos.values());
  }
  
  getSLIs(): SLI[] {
    return Array.from(this.slis.values());
  }
  
  // Reporting methods
  
  generateSLOReport(timeWindow: number = 2592000): {
    summary: any;
    details: Record<string, any>;
    violations: SLOCompliance[];
    burnRateAlerts: BurnRateAlert[];
  } {
    const summary = this.getSLOStatus();
    const details: Record<string, any> = {};
    const violations: SLOCompliance[] = [];
    
    for (const sloName of this.slos.keys()) {
      const history = this.getComplianceHistory(sloName, timeWindow);
      const current = this.getSLOCompliance(sloName);
      
      if (current) {
        details[sloName] = {
          current: current.compliance,
          target: current.target,
          status: current.status,
          errorBudget: current.errorBudget,
          avgCompliance: history.length > 0 ? 
            history.reduce((sum, c) => sum + c.compliance, 0) / history.length : 0,
        };
        
        if (current.status === 'violated') {
          violations.push(current);
        }
      }
    }
    
    return {
      summary,
      details,
      violations,
      burnRateAlerts: [], // Would include recent burn rate alerts
    };
  }
}

export function createSLOTracker(config: MonitoringConfig['slo'], metrics: PrometheusMetrics): SLOTracker {
  return new SLOTracker(config, metrics);
}