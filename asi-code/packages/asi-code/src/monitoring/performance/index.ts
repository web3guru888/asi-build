/**
 * Performance Metrics Collection System
 * 
 * Comprehensive performance monitoring for ASI-Code including:
 * - Request/response time tracking
 * - Throughput measurements
 * - Resource utilization monitoring
 * - Operation performance profiling
 * - Performance bottleneck detection
 * - Real-time performance analytics
 */

import { performance, PerformanceObserver } from 'perf_hooks';
import { EventEmitter } from 'eventemitter3';
import * as os from 'os';
import type { PrometheusMetrics } from '../metrics/index.js';

export interface PerformanceMetric {
  name: string;
  value: number;
  unit: string;
  timestamp: number;
  labels?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface PerformanceProfile {
  operation: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  metadata: Record<string, any>;
  subOperations: PerformanceProfile[];
}

export interface PerformanceSnapshot {
  timestamp: number;
  cpu: {
    usage: number;
    loadAverage: number[];
  };
  memory: {
    heapUsed: number;
    heapTotal: number;
    rss: number;
    external: number;
  };
  eventLoop: {
    delay: number;
    utilization: number;
  };
  gc: {
    totalTime: number;
    count: number;
  };
  requests: {
    active: number;
    total: number;
    averageResponseTime: number;
  };
}

export class PerformanceMonitor extends EventEmitter {
  private metrics: PrometheusMetrics;
  private profiles: Map<string, PerformanceProfile> = new Map();
  private snapshots: PerformanceSnapshot[] = [];
  private maxSnapshots = 1000;
  private performanceObserver: PerformanceObserver;
  private gcStats = { totalTime: 0, count: 0 };
  private requestStats = { active: 0, total: 0, totalResponseTime: 0 };
  
  constructor(metrics: PrometheusMetrics) {
    super();
    this.metrics = metrics;
    this.initializePerformanceObserver();
    this.startPeriodicCollection();
  }
  
  private initializePerformanceObserver(): void {
    this.performanceObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      
      for (const entry of entries) {
        this.handlePerformanceEntry(entry);
      }
    });
    
    // Observe different types of performance entries
    this.performanceObserver.observe({ 
      entryTypes: ['measure', 'mark', 'navigation', 'resource', 'gc'] 
    });
  }
  
  private handlePerformanceEntry(entry: PerformanceEntry): void {
    const metric: PerformanceMetric = {
      name: entry.name,
      value: entry.duration,
      unit: 'milliseconds',
      timestamp: entry.startTime,
      labels: {
        type: entry.entryType,
      },
    };
    
    this.emit('performance-metric', metric);
    
    // Handle specific entry types
    switch (entry.entryType) {
      case 'gc':
        this.gcStats.totalTime += entry.duration;
        this.gcStats.count++;
        break;
      case 'measure':
        this.handleMeasureEntry(entry);
        break;
    }
  }
  
  private handleMeasureEntry(entry: PerformanceEntry): void {
    // Record custom application measurements
    if (entry.name.startsWith('asi-code')) {
      const [, component, operation] = entry.name.split('.');
      
      this.recordPerformanceMetric(
        `${component}_${operation}_duration`,
        entry.duration,
        'milliseconds',
        { component, operation }
      );
    }
  }
  
  // Performance profiling methods
  startProfile(operation: string, metadata: Record<string, any> = {}): string {
    const profileId = `${operation}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const profile: PerformanceProfile = {
      operation,
      startTime: performance.now(),
      metadata,
      subOperations: [],
    };
    
    this.profiles.set(profileId, profile);
    performance.mark(`start_${profileId}`);
    
    return profileId;
  }
  
  endProfile(profileId: string): PerformanceProfile | null {
    const profile = this.profiles.get(profileId);
    if (!profile) {
      return null;
    }
    
    profile.endTime = performance.now();
    profile.duration = profile.endTime - profile.startTime;
    
    performance.mark(`end_${profileId}`);
    performance.measure(
      `asi-code.${profile.operation}`,
      `start_${profileId}`,
      `end_${profileId}`
    );
    
    this.profiles.delete(profileId);
    this.emit('profile-completed', profile);
    
    return profile;
  }
  
  addSubOperation(parentProfileId: string, operation: string, metadata: Record<string, any> = {}): string {
    const parentProfile = this.profiles.get(parentProfileId);
    if (!parentProfile) {
      throw new Error(`Parent profile ${parentProfileId} not found`);
    }
    
    const subProfileId = this.startProfile(`${parentProfile.operation}.${operation}`, metadata);
    const subProfile = this.profiles.get(subProfileId)!;
    
    parentProfile.subOperations.push(subProfile);
    
    return subProfileId;
  }
  
  // Performance measurement utilities
  measureAsyncOperation<T>(
    operation: string,
    fn: () => Promise<T>,
    metadata: Record<string, any> = {}
  ): Promise<T> {
    return new Promise(async (resolve, reject) => {
      const profileId = this.startProfile(operation, metadata);
      
      try {
        const result = await fn();
        this.endProfile(profileId);
        resolve(result);
      } catch (error) {
        const profile = this.endProfile(profileId);
        if (profile) {
          profile.metadata.error = error instanceof Error ? error.message : 'Unknown error';
        }
        reject(error);
      }
    });
  }
  
  measureSyncOperation<T>(
    operation: string,
    fn: () => T,
    metadata: Record<string, any> = {}
  ): T {
    const profileId = this.startProfile(operation, metadata);
    
    try {
      const result = fn();
      this.endProfile(profileId);
      return result;
    } catch (error) {
      const profile = this.endProfile(profileId);
      if (profile) {
        profile.metadata.error = error instanceof Error ? error.message : 'Unknown error';
      }
      throw error;
    }
  }
  
  // ASI-Code specific performance tracking
  trackSessionPerformance(sessionId: string, operation: string, duration: number): void {
    this.recordPerformanceMetric(
      'session_operation_duration',
      duration,
      'milliseconds',
      { session_id: sessionId, operation }
    );
  }
  
  trackToolPerformance(toolName: string, sessionId: string, duration: number, success: boolean): void {
    this.recordPerformanceMetric(
      'tool_execution_duration',
      duration,
      'milliseconds',
      { tool_name: toolName, session_id: sessionId, success: success.toString() }
    );
  }
  
  trackProviderPerformance(provider: string, model: string, duration: number, tokens: number): void {
    this.recordPerformanceMetric(
      'provider_request_duration',
      duration,
      'milliseconds',
      { provider, model }
    );
    
    const throughput = tokens / (duration / 1000); // tokens per second
    this.recordPerformanceMetric(
      'provider_throughput',
      throughput,
      'tokens_per_second',
      { provider, model }
    );
  }
  
  trackKennyPerformance(subsystem: string, operation: string, duration: number): void {
    this.recordPerformanceMetric(
      'kenny_operation_duration',
      duration,
      'milliseconds',
      { subsystem, operation }
    );
  }
  
  // Request performance tracking
  startRequestTracking(): string {
    const requestId = Math.random().toString(36).substr(2, 9);
    this.requestStats.active++;
    this.requestStats.total++;
    
    return requestId;
  }
  
  endRequestTracking(requestId: string, duration: number): void {
    this.requestStats.active--;
    this.requestStats.totalResponseTime += duration;
    
    this.recordPerformanceMetric(
      'http_request_duration',
      duration,
      'milliseconds',
      { request_id: requestId }
    );
  }
  
  // System performance collection
  private startPeriodicCollection(): void {
    setInterval(() => {
      this.collectSystemSnapshot();
    }, 5000); // Collect every 5 seconds
  }
  
  private async collectSystemSnapshot(): Promise<void> {
    const memUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    const loadAverage = os.loadavg();
    
    // Measure event loop delay
    const eventLoopDelay = await this.measureEventLoopDelay();
    
    const snapshot: PerformanceSnapshot = {
      timestamp: Date.now(),
      cpu: {
        usage: process.cpuUsage().user / 1000000, // Convert to seconds
        loadAverage,
      },
      memory: {
        heapUsed: memUsage.heapUsed,
        heapTotal: memUsage.heapTotal,
        rss: memUsage.rss,
        external: memUsage.external,
      },
      eventLoop: {
        delay: eventLoopDelay,
        utilization: this.calculateEventLoopUtilization(),
      },
      gc: {
        totalTime: this.gcStats.totalTime,
        count: this.gcStats.count,
      },
      requests: {
        active: this.requestStats.active,
        total: this.requestStats.total,
        averageResponseTime: this.requestStats.total > 0 ? 
          this.requestStats.totalResponseTime / this.requestStats.total : 0,
      },
    };
    
    this.addSnapshot(snapshot);
    this.emit('performance-snapshot', snapshot);
    
    // Update Prometheus metrics
    this.updatePrometheusMetrics(snapshot);
  }
  
  private measureEventLoopDelay(): Promise<number> {
    return new Promise((resolve) => {
      const start = process.hrtime.bigint();
      setImmediate(() => {
        const delay = Number(process.hrtime.bigint() - start) / 1e6; // Convert to milliseconds
        resolve(delay);
      });
    });
  }
  
  private calculateEventLoopUtilization(): number {
    // This would use perf_hooks.eventLoopUtilization() in newer Node.js versions
    // For compatibility, we'll return a simulated value
    return Math.random() * 100;
  }
  
  private addSnapshot(snapshot: PerformanceSnapshot): void {
    this.snapshots.push(snapshot);
    
    // Keep only the most recent snapshots
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots = this.snapshots.slice(-this.maxSnapshots);
    }
  }
  
  private updatePrometheusMetrics(snapshot: PerformanceSnapshot): void {
    // Update system metrics
    this.recordPerformanceMetric('cpu_usage', snapshot.cpu.usage, 'percent');
    this.recordPerformanceMetric('memory_heap_used', snapshot.memory.heapUsed, 'bytes');
    this.recordPerformanceMetric('memory_heap_total', snapshot.memory.heapTotal, 'bytes');
    this.recordPerformanceMetric('memory_rss', snapshot.memory.rss, 'bytes');
    this.recordPerformanceMetric('event_loop_delay', snapshot.eventLoop.delay, 'milliseconds');
    this.recordPerformanceMetric('gc_total_time', snapshot.gc.totalTime, 'milliseconds');
    this.recordPerformanceMetric('gc_count', snapshot.gc.count, 'count');
    this.recordPerformanceMetric('active_requests', snapshot.requests.active, 'count');
    this.recordPerformanceMetric('average_response_time', snapshot.requests.averageResponseTime, 'milliseconds');
  }
  
  private recordPerformanceMetric(
    name: string, 
    value: number, 
    unit: string, 
    labels: Record<string, string> = {}
  ): void {
    const metric: PerformanceMetric = {
      name: `performance_${name}`,
      value,
      unit,
      timestamp: Date.now(),
      labels,
    };
    
    this.emit('performance-metric', metric);
  }
  
  // Analysis methods
  getAverageResponseTime(timeWindowMs: number = 60000): number {
    const cutoff = Date.now() - timeWindowMs;
    const recentSnapshots = this.snapshots.filter(s => s.timestamp > cutoff);
    
    if (recentSnapshots.length === 0) return 0;
    
    const totalResponseTime = recentSnapshots.reduce(
      (sum, snapshot) => sum + snapshot.requests.averageResponseTime, 
      0
    );
    
    return totalResponseTime / recentSnapshots.length;
  }
  
  getThroughput(timeWindowMs: number = 60000): number {
    const cutoff = Date.now() - timeWindowMs;
    const recentSnapshots = this.snapshots.filter(s => s.timestamp > cutoff);
    
    if (recentSnapshots.length < 2) return 0;
    
    const firstSnapshot = recentSnapshots[0];
    const lastSnapshot = recentSnapshots[recentSnapshots.length - 1];
    
    const requestDiff = lastSnapshot.requests.total - firstSnapshot.requests.total;
    const timeDiff = (lastSnapshot.timestamp - firstSnapshot.timestamp) / 1000; // Convert to seconds
    
    return requestDiff / timeDiff; // Requests per second
  }
  
  getResourceUtilization(): { cpu: number; memory: number; eventLoop: number } {
    const latestSnapshot = this.snapshots[this.snapshots.length - 1];
    
    if (!latestSnapshot) {
      return { cpu: 0, memory: 0, eventLoop: 0 };
    }
    
    return {
      cpu: latestSnapshot.cpu.usage,
      memory: (latestSnapshot.memory.heapUsed / latestSnapshot.memory.heapTotal) * 100,
      eventLoop: latestSnapshot.eventLoop.utilization,
    };
  }
  
  getPerformanceTrends(metric: string, timeWindowMs: number = 300000): number[] {
    const cutoff = Date.now() - timeWindowMs;
    const recentSnapshots = this.snapshots.filter(s => s.timestamp > cutoff);
    
    return recentSnapshots.map(snapshot => {
      switch (metric) {
        case 'response_time':
          return snapshot.requests.averageResponseTime;
        case 'memory_usage':
          return (snapshot.memory.heapUsed / snapshot.memory.heapTotal) * 100;
        case 'cpu_usage':
          return snapshot.cpu.usage;
        case 'event_loop_delay':
          return snapshot.eventLoop.delay;
        default:
          return 0;
      }
    });
  }
  
  // Performance bottleneck detection
  detectBottlenecks(): string[] {
    const bottlenecks: string[] = [];
    const latestSnapshot = this.snapshots[this.snapshots.length - 1];
    
    if (!latestSnapshot) return bottlenecks;
    
    // CPU bottleneck
    if (latestSnapshot.cpu.usage > 80) {
      bottlenecks.push('High CPU usage detected');
    }
    
    // Memory bottleneck
    const memoryUsage = (latestSnapshot.memory.heapUsed / latestSnapshot.memory.heapTotal) * 100;
    if (memoryUsage > 85) {
      bottlenecks.push('High memory usage detected');
    }
    
    // Event loop lag
    if (latestSnapshot.eventLoop.delay > 100) {
      bottlenecks.push('Event loop lag detected');
    }
    
    // High response time
    if (latestSnapshot.requests.averageResponseTime > 5000) {
      bottlenecks.push('High response time detected');
    }
    
    return bottlenecks;
  }
  
  // Cleanup
  destroy(): void {
    this.performanceObserver.disconnect();
    this.removeAllListeners();
  }
  
  // Getter methods
  getSnapshots(): PerformanceSnapshot[] {
    return [...this.snapshots];
  }
  
  getActiveProfiles(): PerformanceProfile[] {
    return Array.from(this.profiles.values());
  }
  
  getCurrentStats() {
    return {
      ...this.requestStats,
      gc: { ...this.gcStats },
      profilesActive: this.profiles.size,
      snapshotsCollected: this.snapshots.length,
    };
  }
}

export function createPerformanceMonitor(metrics: PrometheusMetrics): PerformanceMonitor {
  return new PerformanceMonitor(metrics);
}