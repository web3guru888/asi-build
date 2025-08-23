/**
 * WebSocket Connection Monitor
 * 
 * Advanced monitoring system for tracking and analyzing WebSocket connection
 * performance, health, and resource usage at scale (10K+ connections).
 */

import { EventEmitter } from 'eventemitter3';
import { performance } from 'perf_hooks';
import type { WSConnectionManager } from './connection-manager.js';

export interface ConnectionHealthMetrics {
  connectionId: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'critical';
  latency: number;
  messageRate: number;
  errorRate: number;
  memoryUsage: number;
  lastActivity: number;
  issues: string[];
}

export interface SystemHealthReport {
  timestamp: number;
  overallStatus: 'healthy' | 'degraded' | 'unhealthy' | 'critical';
  totalConnections: number;
  activeConnections: number;
  systemMetrics: {
    cpuUsage: number;
    memoryUsage: number;
    networkThroughput: number;
    averageLatency: number;
    errorRate: number;
  };
  connectionsByStatus: {
    healthy: number;
    degraded: number;
    unhealthy: number;
    critical: number;
  };
  alerts: {
    level: 'info' | 'warning' | 'error' | 'critical';
    message: string;
    timestamp: number;
  }[];
  recommendations: string[];
}

export interface MonitoringConfig {
  healthCheckInterval: number; // milliseconds
  metricsRetentionTime: number; // milliseconds
  alertThresholds: {
    latency: number;
    errorRate: number;
    memoryUsage: number;
    connectionCount: number;
  };
  enableDetailedLogging: boolean;
}

export class ConnectionMonitor extends EventEmitter {
  private readonly connectionManager: WSConnectionManager;
  private readonly config: MonitoringConfig;
  private readonly metricsHistory: Map<string, ConnectionHealthMetrics[]> = new Map();
  private readonly systemReports: SystemHealthReport[] = [];
  private healthCheckInterval?: NodeJS.Timeout;
  private startTime: number;

  constructor(
    connectionManager: WSConnectionManager,
    config: Partial<MonitoringConfig> = {}
  ) {
    super();
    this.connectionManager = connectionManager;
    this.startTime = Date.now();
    
    this.config = {
      healthCheckInterval: 5000, // 5 seconds
      metricsRetentionTime: 3600000, // 1 hour
      alertThresholds: {
        latency: 1000, // 1 second
        errorRate: 0.05, // 5%
        memoryUsage: 100 * 1024 * 1024, // 100MB per connection
        connectionCount: 8000, // 80% of 10K limit
      },
      enableDetailedLogging: false,
      ...config,
    };

    this.startMonitoring();
    this.setupEventListeners();
  }

  /**
   * Start the monitoring process
   */
  private startMonitoring(): void {
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck();
    }, this.config.healthCheckInterval);

    // Cleanup old metrics periodically
    setInterval(() => {
      this.cleanupOldMetrics();
    }, 60000); // Every minute
  }

  /**
   * Setup event listeners for real-time monitoring
   */
  private setupEventListeners(): void {
    // Listen to connection events
    this.connectionManager.on('connection:open', (connectionId) => {
      this.initializeConnectionMetrics(connectionId);
    });

    this.connectionManager.on('connection:close', (connectionId) => {
      this.finalizeConnectionMetrics(connectionId);
    });

    this.connectionManager.on('connection:error', (connectionId, error) => {
      this.recordConnectionError(connectionId, error);
    });

    this.connectionManager.on('rate:limited', (connectionId) => {
      this.recordRateLimitEvent(connectionId);
    });
  }

  /**
   * Initialize metrics tracking for a new connection
   */
  private initializeConnectionMetrics(connectionId: string): void {
    const initialMetrics: ConnectionHealthMetrics = {
      connectionId,
      status: 'healthy',
      latency: 0,
      messageRate: 0,
      errorRate: 0,
      memoryUsage: 0,
      lastActivity: Date.now(),
      issues: [],
    };

    this.metricsHistory.set(connectionId, [initialMetrics]);
  }

  /**
   * Finalize metrics when connection closes
   */
  private finalizeConnectionMetrics(connectionId: string): void {
    const metrics = this.metricsHistory.get(connectionId);
    if (metrics && this.config.enableDetailedLogging) {
      const connectionDuration = Date.now() - (metrics[0]?.lastActivity || Date.now());
      console.log(`Connection ${connectionId} closed after ${connectionDuration}ms`);
    }

    // Keep metrics for a short time after connection closes for analysis
    setTimeout(() => {
      this.metricsHistory.delete(connectionId);
    }, 300000); // 5 minutes
  }

  /**
   * Record connection error
   */
  private recordConnectionError(connectionId: string, error: Error): void {
    const metrics = this.metricsHistory.get(connectionId);
    if (!metrics || metrics.length === 0) return;

    const latestMetrics = metrics[metrics.length - 1];
    latestMetrics.issues.push(`Error: ${error.message}`);
    latestMetrics.errorRate += 0.1; // Increment error rate

    // Update status based on error severity
    if (latestMetrics.errorRate > 0.3) {
      latestMetrics.status = 'critical';
    } else if (latestMetrics.errorRate > 0.1) {
      latestMetrics.status = 'unhealthy';
    } else if (latestMetrics.errorRate > 0.05) {
      latestMetrics.status = 'degraded';
    }
  }

  /**
   * Record rate limit event
   */
  private recordRateLimitEvent(connectionId: string): void {
    const metrics = this.metricsHistory.get(connectionId);
    if (!metrics || metrics.length === 0) return;

    const latestMetrics = metrics[metrics.length - 1];
    latestMetrics.issues.push('Rate limited');
    latestMetrics.status = 'degraded';
  }

  /**
   * Perform comprehensive health check
   */
  private performHealthCheck(): void {
    const stats = this.connectionManager.getStats();
    const systemMetrics = this.collectSystemMetrics();
    const connectionHealthMetrics = this.analyzeConnections();

    const report: SystemHealthReport = {
      timestamp: Date.now(),
      overallStatus: this.determineOverallStatus(stats, connectionHealthMetrics),
      totalConnections: stats.connections,
      activeConnections: stats.connections, // Assuming all tracked connections are active
      systemMetrics,
      connectionsByStatus: this.categorizeConnectionsByStatus(connectionHealthMetrics),
      alerts: this.generateAlerts(stats, systemMetrics, connectionHealthMetrics),
      recommendations: this.generateRecommendations(stats, systemMetrics),
    };

    // Store report
    this.systemReports.push(report);
    
    // Limit report history
    if (this.systemReports.length > 720) { // ~1 hour at 5s intervals
      this.systemReports.shift();
    }

    // Emit events for different status levels
    this.emitStatusEvents(report);
  }

  /**
   * Collect system-level metrics
   */
  private collectSystemMetrics(): SystemHealthReport['systemMetrics'] {
    const memUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    const stats = this.connectionManager.getStats();

    return {
      cpuUsage: (cpuUsage.user + cpuUsage.system) / 1000000, // Convert to seconds
      memoryUsage: memUsage.heapUsed / 1024 / 1024, // Convert to MB
      networkThroughput: stats.performance.totalBytesPerSecond,
      averageLatency: this.calculateAverageLatency(),
      errorRate: this.calculateSystemErrorRate(),
    };
  }

  /**
   * Analyze individual connection health
   */
  private analyzeConnections(): ConnectionHealthMetrics[] {
    const healthMetrics: ConnectionHealthMetrics[] = [];

    for (const [connectionId, metricsList] of this.metricsHistory) {
      if (metricsList.length === 0) continue;

      const latestMetrics = metricsList[metricsList.length - 1];
      const stats = this.connectionManager.getStats();
      
      // Update metrics based on current connection state
      const updatedMetrics: ConnectionHealthMetrics = {
        ...latestMetrics,
        lastActivity: Date.now(),
        memoryUsage: stats.performance.totalMemoryUsage / stats.connections || 0,
        messageRate: stats.performance.totalMessagesPerSecond / stats.connections || 0,
      };

      // Determine health status
      updatedMetrics.status = this.determineConnectionHealth(updatedMetrics);
      
      // Update metrics history
      metricsList.push(updatedMetrics);
      
      // Limit history per connection
      if (metricsList.length > 100) {
        metricsList.shift();
      }

      healthMetrics.push(updatedMetrics);
    }

    return healthMetrics;
  }

  /**
   * Determine individual connection health status
   */
  private determineConnectionHealth(metrics: ConnectionHealthMetrics): 'healthy' | 'degraded' | 'unhealthy' | 'critical' {
    const issues = [];

    if (metrics.latency > this.config.alertThresholds.latency) {
      issues.push('High latency');
    }

    if (metrics.errorRate > this.config.alertThresholds.errorRate) {
      issues.push('High error rate');
    }

    if (metrics.memoryUsage > this.config.alertThresholds.memoryUsage) {
      issues.push('High memory usage');
    }

    const inactiveTime = Date.now() - metrics.lastActivity;
    if (inactiveTime > 300000) { // 5 minutes
      issues.push('Inactive connection');
    }

    metrics.issues = issues;

    if (issues.length >= 3) return 'critical';
    if (issues.length === 2) return 'unhealthy';
    if (issues.length === 1) return 'degraded';
    return 'healthy';
  }

  /**
   * Determine overall system health status
   */
  private determineOverallStatus(
    stats: any,
    connectionMetrics: ConnectionHealthMetrics[]
  ): 'healthy' | 'degraded' | 'unhealthy' | 'critical' {
    const totalConnections = stats.connections;
    const criticalConnections = connectionMetrics.filter(m => m.status === 'critical').length;
    const unhealthyConnections = connectionMetrics.filter(m => m.status === 'unhealthy').length;
    const degradedConnections = connectionMetrics.filter(m => m.status === 'degraded').length;

    const criticalRatio = criticalConnections / totalConnections;
    const unhealthyRatio = (criticalConnections + unhealthyConnections) / totalConnections;
    const degradedRatio = (criticalConnections + unhealthyConnections + degradedConnections) / totalConnections;

    if (criticalRatio > 0.1 || totalConnections > this.config.alertThresholds.connectionCount * 1.2) {
      return 'critical';
    } else if (unhealthyRatio > 0.2 || totalConnections > this.config.alertThresholds.connectionCount) {
      return 'unhealthy';
    } else if (degradedRatio > 0.3 || stats.performance.backpressureConnections > totalConnections * 0.1) {
      return 'degraded';
    }

    return 'healthy';
  }

  /**
   * Categorize connections by status
   */
  private categorizeConnectionsByStatus(metrics: ConnectionHealthMetrics[]): SystemHealthReport['connectionsByStatus'] {
    return {
      healthy: metrics.filter(m => m.status === 'healthy').length,
      degraded: metrics.filter(m => m.status === 'degraded').length,
      unhealthy: metrics.filter(m => m.status === 'unhealthy').length,
      critical: metrics.filter(m => m.status === 'critical').length,
    };
  }

  /**
   * Generate system alerts
   */
  private generateAlerts(
    stats: any,
    systemMetrics: SystemHealthReport['systemMetrics'],
    connectionMetrics: ConnectionHealthMetrics[]
  ): SystemHealthReport['alerts'] {
    const alerts: SystemHealthReport['alerts'] = [];
    const now = Date.now();

    // Connection count alerts
    if (stats.connections > this.config.alertThresholds.connectionCount) {
      alerts.push({
        level: stats.connections > this.config.alertThresholds.connectionCount * 1.2 ? 'critical' : 'warning',
        message: `High connection count: ${stats.connections} connections`,
        timestamp: now,
      });
    }

    // Memory usage alerts
    if (systemMetrics.memoryUsage > 1024) { // 1GB
      alerts.push({
        level: systemMetrics.memoryUsage > 2048 ? 'critical' : 'warning',
        message: `High memory usage: ${systemMetrics.memoryUsage.toFixed(2)}MB`,
        timestamp: now,
      });
    }

    // Backpressure alerts
    if (stats.performance.backpressureConnections > 0) {
      alerts.push({
        level: stats.performance.backpressureConnections > stats.connections * 0.1 ? 'error' : 'warning',
        message: `${stats.performance.backpressureConnections} connections experiencing backpressure`,
        timestamp: now,
      });
    }

    return alerts;
  }

  /**
   * Generate optimization recommendations
   */
  private generateRecommendations(stats: any, systemMetrics: SystemHealthReport['systemMetrics']): string[] {
    const recommendations: string[] = [];

    if (stats.connections > this.config.alertThresholds.connectionCount * 0.8) {
      recommendations.push('Consider implementing connection load balancing');
    }

    if (systemMetrics.memoryUsage > 512) {
      recommendations.push('Monitor memory usage closely and consider garbage collection optimization');
    }

    if (systemMetrics.averageLatency > 500) {
      recommendations.push('Investigate network latency issues and optimize message processing');
    }

    if (stats.performance.backpressureConnections > stats.connections * 0.05) {
      recommendations.push('Optimize message sending rate and implement better flow control');
    }

    return recommendations;
  }

  /**
   * Calculate average latency across all connections
   */
  private calculateAverageLatency(): number {
    let totalLatency = 0;
    let connectionCount = 0;

    for (const metricsList of this.metricsHistory.values()) {
      if (metricsList.length > 0) {
        totalLatency += metricsList[metricsList.length - 1].latency;
        connectionCount++;
      }
    }

    return connectionCount > 0 ? totalLatency / connectionCount : 0;
  }

  /**
   * Calculate system-wide error rate
   */
  private calculateSystemErrorRate(): number {
    let totalErrorRate = 0;
    let connectionCount = 0;

    for (const metricsList of this.metricsHistory.values()) {
      if (metricsList.length > 0) {
        totalErrorRate += metricsList[metricsList.length - 1].errorRate;
        connectionCount++;
      }
    }

    return connectionCount > 0 ? totalErrorRate / connectionCount : 0;
  }

  /**
   * Emit status-based events
   */
  private emitStatusEvents(report: SystemHealthReport): void {
    this.emit('health:report', report);

    if (report.overallStatus === 'critical') {
      this.emit('health:critical', report);
    } else if (report.overallStatus === 'unhealthy') {
      this.emit('health:unhealthy', report);
    } else if (report.overallStatus === 'degraded') {
      this.emit('health:degraded', report);
    }

    // Emit alerts
    for (const alert of report.alerts) {
      this.emit(`alert:${alert.level}`, alert);
    }
  }

  /**
   * Clean up old metrics data
   */
  private cleanupOldMetrics(): void {
    const cutoffTime = Date.now() - this.config.metricsRetentionTime;

    for (const [connectionId, metricsList] of this.metricsHistory) {
      // Remove old metrics
      const recentMetrics = metricsList.filter(m => m.lastActivity > cutoffTime);
      
      if (recentMetrics.length === 0) {
        this.metricsHistory.delete(connectionId);
      } else {
        this.metricsHistory.set(connectionId, recentMetrics);
      }
    }

    // Clean up old system reports
    const recentReports = this.systemReports.filter(r => r.timestamp > cutoffTime);
    this.systemReports.length = 0;
    this.systemReports.push(...recentReports);
  }

  /**
   * Get current system health report
   */
  getCurrentHealthReport(): SystemHealthReport | undefined {
    return this.systemReports[this.systemReports.length - 1];
  }

  /**
   * Get health history
   */
  getHealthHistory(timeRange?: number): SystemHealthReport[] {
    if (!timeRange) return [...this.systemReports];

    const cutoffTime = Date.now() - timeRange;
    return this.systemReports.filter(r => r.timestamp > cutoffTime);
  }

  /**
   * Get connection metrics for a specific connection
   */
  getConnectionMetrics(connectionId: string): ConnectionHealthMetrics[] {
    return this.metricsHistory.get(connectionId) || [];
  }

  /**
   * Get system uptime
   */
  getUptime(): number {
    return Date.now() - this.startTime;
  }

  /**
   * Stop monitoring and cleanup resources
   */
  stop(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    this.metricsHistory.clear();
    this.systemReports.length = 0;
    this.removeAllListeners();
  }
}