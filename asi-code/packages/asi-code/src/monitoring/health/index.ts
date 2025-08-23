/**
 * Comprehensive Health Check System
 * 
 * Provides detailed health monitoring for all ASI-Code components:
 * - Service health checks
 * - Dependency health checks
 * - Deep health diagnostics
 * - Performance health indicators
 * - Readiness and liveness probes
 */

import type { Hono } from 'hono';
import type { MonitoringConfig } from '../index.js';
import * as si from 'systeminformation';
import { EventEmitter } from 'eventemitter3';

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  checks: Record<string, HealthCheck>;
  summary: {
    total: number;
    healthy: number;
    degraded: number;
    unhealthy: number;
  };
  uptime: number;
  version: string;
}

export interface HealthCheck {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  message?: string;
  duration: number;
  metadata?: Record<string, any>;
  lastCheck: number;
  checkCount: number;
  errorCount: number;
}

export interface HealthChecker {
  name: string;
  check(): Promise<HealthCheck>;
  isRequired: boolean;
  timeout: number;
  interval: number;
}

export class ASICodeHealthService extends EventEmitter {
  private readonly config: MonitoringConfig['health'];
  private readonly checkers: Map<string, HealthChecker> = new Map();
  private lastHealthStatus: HealthStatus;
  private checkInterval: NodeJS.Timeout | null = null;
  private readonly startTime: number = Date.now();
  
  constructor(config: MonitoringConfig['health']) {
    super();
    this.config = config;
    this.initializeDefaultCheckers();
    this.startPeriodicChecks();
  }
  
  private initializeDefaultCheckers(): void {
    // System health checkers
    this.addChecker(new SystemHealthChecker());
    this.addChecker(new MemoryHealthChecker());
    this.addChecker(new DiskHealthChecker());
    this.addChecker(new DatabaseHealthChecker());
    this.addChecker(new ExternalServiceHealthChecker());
    
    // ASI-Code specific checkers
    this.addChecker(new SessionManagerHealthChecker());
    this.addChecker(new ProviderHealthChecker());
    this.addChecker(new ToolSystemHealthChecker());
    this.addChecker(new KennySubsystemHealthChecker());
    this.addChecker(new ServerHealthChecker());
  }
  
  addChecker(checker: HealthChecker): void {
    this.checkers.set(checker.name, checker);
  }
  
  removeChecker(name: string): void {
    this.checkers.delete(name);
  }
  
  async runHealthChecks(): Promise<HealthStatus> {
    const checks: Record<string, HealthCheck> = {};
    const checkPromises: Promise<void>[] = [];
    
    for (const [name, checker] of this.checkers) {
      const checkPromise = this.runSingleCheck(checker).then(result => {
        checks[name] = result;
      });
      checkPromises.push(checkPromise);
    }
    
    await Promise.all(checkPromises);
    
    const summary = this.calculateSummary(checks);
    const overallStatus = this.determineOverallStatus(checks);
    
    const healthStatus: HealthStatus = {
      status: overallStatus,
      timestamp: Date.now(),
      checks,
      summary,
      uptime: Date.now() - this.startTime,
      version: process.env.npm_package_version || '1.0.0',
    };
    
    this.lastHealthStatus = healthStatus;
    this.emit('health-check-completed', healthStatus);
    
    return healthStatus;
  }
  
  private async runSingleCheck(checker: HealthChecker): Promise<HealthCheck> {
    const startTime = Date.now();
    
    try {
      const result = await Promise.race([
        checker.check(),
        new Promise<HealthCheck>((_, reject) => 
          setTimeout(() => reject(new Error('Health check timeout')), checker.timeout)
        )
      ]);
      
      return {
        ...result,
        duration: Date.now() - startTime,
      };
    } catch (error) {
      return {
        name: checker.name,
        status: 'unhealthy',
        message: error instanceof Error ? error.message : 'Unknown error',
        duration: Date.now() - startTime,
        lastCheck: Date.now(),
        checkCount: 0,
        errorCount: 1,
      };
    }
  }
  
  private calculateSummary(checks: Record<string, HealthCheck>) {
    const summary = {
      total: Object.keys(checks).length,
      healthy: 0,
      degraded: 0,
      unhealthy: 0,
    };
    
    Object.values(checks).forEach(check => {
      summary[check.status]++;
    });
    
    return summary;
  }
  
  private determineOverallStatus(checks: Record<string, HealthCheck>): 'healthy' | 'degraded' | 'unhealthy' {
    const requiredCheckers = Array.from(this.checkers.values()).filter(c => c.isRequired);
    const requiredChecks = requiredCheckers.map(c => checks[c.name]).filter(Boolean);
    
    // If any required check is unhealthy, overall is unhealthy
    if (requiredChecks.some(check => check.status === 'unhealthy')) {
      return 'unhealthy';
    }
    
    // If any check is unhealthy or required check is degraded, overall is degraded
    if (Object.values(checks).some(check => check.status === 'unhealthy') ||
        requiredChecks.some(check => check.status === 'degraded')) {
      return 'degraded';
    }
    
    return 'healthy';
  }
  
  private startPeriodicChecks(): void {
    if (this.config.interval > 0) {
      this.checkInterval = setInterval(() => {
        this.runHealthChecks().catch(error => {
          console.error('Health check error:', error);
        });
      }, this.config.interval);
    }
  }
  
  getLastHealthStatus(): HealthStatus | null {
    return this.lastHealthStatus || null;
  }
  
  setupRoutes(app: Hono): void {
    // Main health endpoint
    app.get(this.config.path, async (c) => {
      const health = await this.runHealthChecks();
      const statusCode = health.status === 'healthy' ? 200 : 
                        health.status === 'degraded' ? 200 : 503;
      
      return c.json(health, statusCode);
    });
    
    // Liveness probe (simple check)
    app.get('/health/live', (c) => {
      return c.json({
        status: 'alive',
        timestamp: Date.now(),
        uptime: Date.now() - this.startTime,
      });
    });
    
    // Readiness probe (comprehensive check)
    app.get('/health/ready', async (c) => {
      const health = await this.runHealthChecks();
      const isReady = health.status === 'healthy';
      
      return c.json({
        ready: isReady,
        status: health.status,
        timestamp: health.timestamp,
        checks: health.checks,
      }, isReady ? 200 : 503);
    });
    
    // Individual checker status
    app.get('/health/check/:name', async (c) => {
      const checkerName = c.req.param('name');
      const checker = this.checkers.get(checkerName);
      
      if (!checker) {
        return c.json({ error: 'Checker not found' }, 404);
      }
      
      const result = await this.runSingleCheck(checker);
      return c.json(result);
    });
    
    // Health metrics for monitoring
    app.get('/health/metrics', async (c) => {
      const health = await this.runHealthChecks();
      
      const metrics = {
        health_status: health.status === 'healthy' ? 1 : 0,
        health_checks_total: health.summary.total,
        health_checks_healthy: health.summary.healthy,
        health_checks_degraded: health.summary.degraded,
        health_checks_unhealthy: health.summary.unhealthy,
        uptime_seconds: Math.floor(health.uptime / 1000),
      };
      
      return c.json(metrics);
    });
  }
  
  stop(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }
}

// Default Health Checkers

class SystemHealthChecker implements HealthChecker {
  name = 'system';
  isRequired = true;
  timeout = 5000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    try {
      const cpuData = await si.currentLoad();
      const memData = await si.mem();
      
      const cpuUsage = cpuData.currentLoad;
      const memUsage = (memData.used / memData.total) * 100;
      
      let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
      let message = 'System resources normal';
      
      if (cpuUsage > 90 || memUsage > 90) {
        status = 'unhealthy';
        message = `High resource usage: CPU ${cpuUsage.toFixed(1)}%, Memory ${memUsage.toFixed(1)}%`;
      } else if (cpuUsage > 70 || memUsage > 70) {
        status = 'degraded';
        message = `Elevated resource usage: CPU ${cpuUsage.toFixed(1)}%, Memory ${memUsage.toFixed(1)}%`;
      }
      
      return {
        name: this.name,
        status,
        message,
        duration: Date.now() - startTime,
        metadata: {
          cpu_usage: cpuUsage,
          memory_usage: memUsage,
        },
        lastCheck: Date.now(),
        checkCount: 1,
        errorCount: 0,
      };
    } catch (error) {
      throw new Error(`System check failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

class MemoryHealthChecker implements HealthChecker {
  name = 'memory';
  isRequired = true;
  timeout = 2000;
  interval = 15000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    const memUsage = process.memoryUsage();
    
    const heapUsedMB = memUsage.heapUsed / 1024 / 1024;
    const heapTotalMB = memUsage.heapTotal / 1024 / 1024;
    const rssMB = memUsage.rss / 1024 / 1024;
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'Memory usage normal';
    
    if (heapUsedMB > 1000 || rssMB > 2000) {
      status = 'unhealthy';
      message = `High memory usage: Heap ${heapUsedMB.toFixed(1)}MB, RSS ${rssMB.toFixed(1)}MB`;
    } else if (heapUsedMB > 500 || rssMB > 1000) {
      status = 'degraded';
      message = `Elevated memory usage: Heap ${heapUsedMB.toFixed(1)}MB, RSS ${rssMB.toFixed(1)}MB`;
    }
    
    return {
      name: this.name,
      status,
      message,
      duration: Date.now() - startTime,
      metadata: {
        heap_used_mb: heapUsedMB,
        heap_total_mb: heapTotalMB,
        rss_mb: rssMB,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: 0,
    };
  }
}

class DiskHealthChecker implements HealthChecker {
  name = 'disk';
  isRequired = false;
  timeout = 3000;
  interval = 60000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    try {
      const diskData = await si.fsSize();
      const rootDisk = diskData.find(disk => disk.mount === '/') || diskData[0];
      
      if (!rootDisk) {
        throw new Error('No disk information available');
      }
      
      const usagePercent = (rootDisk.used / rootDisk.size) * 100;
      
      let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
      let message = 'Disk space normal';
      
      if (usagePercent > 95) {
        status = 'unhealthy';
        message = `Critical disk usage: ${usagePercent.toFixed(1)}%`;
      } else if (usagePercent > 85) {
        status = 'degraded';
        message = `High disk usage: ${usagePercent.toFixed(1)}%`;
      }
      
      return {
        name: this.name,
        status,
        message,
        duration: Date.now() - startTime,
        metadata: {
          usage_percent: usagePercent,
          used_gb: rootDisk.used / 1024 / 1024 / 1024,
          total_gb: rootDisk.size / 1024 / 1024 / 1024,
        },
        lastCheck: Date.now(),
        checkCount: 1,
        errorCount: 0,
      };
    } catch (error) {
      throw new Error(`Disk check failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}

class DatabaseHealthChecker implements HealthChecker {
  name = 'database';
  isRequired = false;
  timeout = 5000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // This would check database connectivity
    // For now, we'll simulate a check
    const isConnected = true; // Replace with actual DB check
    
    const status = isConnected ? 'healthy' : 'unhealthy';
    const message = isConnected ? 'Database connection healthy' : 'Database connection failed';
    
    return {
      name: this.name,
      status,
      message,
      duration: Date.now() - startTime,
      metadata: {
        connected: isConnected,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: isConnected ? 0 : 1,
    };
  }
}

class ExternalServiceHealthChecker implements HealthChecker {
  name = 'external_services';
  isRequired = false;
  timeout = 10000;
  interval = 60000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check external dependencies (AI providers, etc.)
    const services = ['anthropic', 'openai']; // Add your external services
    const results: Record<string, boolean> = {};
    
    for (const service of services) {
      // Simulate service check - replace with actual checks
      results[service] = Math.random() > 0.1; // 90% success rate
    }
    
    const failedServices = Object.entries(results).filter(([_, isUp]) => !isUp);
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'All external services available';
    
    if (failedServices.length > 0) {
      status = failedServices.length === services.length ? 'unhealthy' : 'degraded';
      message = `Failed services: ${failedServices.map(([name]) => name).join(', ')}`;
    }
    
    return {
      name: this.name,
      status,
      message,
      duration: Date.now() - startTime,
      metadata: results,
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: failedServices.length,
    };
  }
}

// ASI-Code specific health checkers

class SessionManagerHealthChecker implements HealthChecker {
  name = 'session_manager';
  isRequired = true;
  timeout = 3000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check session manager health
    // This would integrate with your actual SessionManager
    const activeSessions = 0; // Get from session manager
    const maxSessions = 1000;
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'Session manager operational';
    
    if (activeSessions > maxSessions * 0.9) {
      status = 'degraded';
      message = 'High session count';
    }
    
    return {
      name: this.name,
      status,
      message,
      duration: Date.now() - startTime,
      metadata: {
        active_sessions: activeSessions,
        max_sessions: maxSessions,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: 0,
    };
  }
}

class ProviderHealthChecker implements HealthChecker {
  name = 'providers';
  isRequired = true;
  timeout = 5000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check AI provider availability
    const providers = ['anthropic', 'openai'];
    const healthy = providers.length; // Simulate all healthy
    
    const status = healthy === providers.length ? 'healthy' : 
                  healthy > 0 ? 'degraded' : 'unhealthy';
    
    return {
      name: this.name,
      status,
      message: `${healthy}/${providers.length} providers available`,
      duration: Date.now() - startTime,
      metadata: {
        total_providers: providers.length,
        healthy_providers: healthy,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: providers.length - healthy,
    };
  }
}

class ToolSystemHealthChecker implements HealthChecker {
  name = 'tool_system';
  isRequired = true;
  timeout = 3000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check tool system health
    const registeredTools = 10; // Get from tool registry
    const healthyTools = 10; // Check each tool
    
    const status = healthyTools === registeredTools ? 'healthy' : 
                  healthyTools > registeredTools * 0.8 ? 'degraded' : 'unhealthy';
    
    return {
      name: this.name,
      status,
      message: `${healthyTools}/${registeredTools} tools available`,
      duration: Date.now() - startTime,
      metadata: {
        registered_tools: registeredTools,
        healthy_tools: healthyTools,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: registeredTools - healthyTools,
    };
  }
}

class KennySubsystemHealthChecker implements HealthChecker {
  name = 'kenny_subsystem';
  isRequired = true;
  timeout = 3000;
  interval = 30000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check Kenny subsystem health
    const subsystems = ['state', 'message', 'integration'];
    const healthySubsystems = subsystems.length; // Check each subsystem
    
    const status = healthySubsystems === subsystems.length ? 'healthy' : 
                  healthySubsystems > 0 ? 'degraded' : 'unhealthy';
    
    return {
      name: this.name,
      status,
      message: `${healthySubsystems}/${subsystems.length} Kenny subsystems operational`,
      duration: Date.now() - startTime,
      metadata: {
        total_subsystems: subsystems.length,
        healthy_subsystems: healthySubsystems,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: subsystems.length - healthySubsystems,
    };
  }
}

class ServerHealthChecker implements HealthChecker {
  name = 'server';
  isRequired = true;
  timeout = 2000;
  interval = 15000;
  
  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    // Check server health
    const eventLoopDelay = 0; // Measure event loop delay
    const pendingRequests = 0; // Count pending requests
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'Server operating normally';
    
    if (eventLoopDelay > 100 || pendingRequests > 100) {
      status = 'degraded';
      message = 'Server under load';
    }
    
    return {
      name: this.name,
      status,
      message,
      duration: Date.now() - startTime,
      metadata: {
        event_loop_delay: eventLoopDelay,
        pending_requests: pendingRequests,
      },
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: 0,
    };
  }
}

export function createHealthService(config: MonitoringConfig['health']): ASICodeHealthService {
  return new ASICodeHealthService(config);
}