/**
 * Comprehensive Monitoring and Observability System for ASI-Code
 * 
 * This module provides:
 * - Prometheus metrics collection
 * - Distributed tracing with Jaeger
 * - Health checks
 * - Performance monitoring
 * - Error tracking with Sentry
 * - SLO/SLI tracking
 * - Anomaly detection
 * - Log correlation
 */

export * from './metrics/index.js';
export * from './tracing/index.js';
export * from './health/index.js';
export * from './performance/index.js';
export * from './sentry/index.js';
export * from './slo/index.js';
export * from './anomaly/index.js';
export * from './correlation/index.js';
export * from './sampling/index.js';
export * from './aggregation/index.js';
export * from './reporting/index.js';
export * from './alerting/index.js';
export * from './runbooks/index.js';

export interface MonitoringConfig {
  prometheus: {
    enabled: boolean;
    port: number;
    path: string;
    collectDefaultMetrics: boolean;
    customMetrics: boolean;
  };
  jaeger: {
    enabled: boolean;
    endpoint: string;
    serviceName: string;
    samplingRate: number;
  };
  sentry: {
    enabled: boolean;
    dsn: string;
    environment: string;
    tracesSampleRate: number;
  };
  health: {
    enabled: boolean;
    path: string;
    interval: number;
  };
  slo: {
    enabled: boolean;
    targets: Record<string, number>;
  };
  anomaly: {
    enabled: boolean;
    thresholds: Record<string, number>;
  };
  correlation: {
    enabled: boolean;
    headerName: string;
  };
}

export const defaultMonitoringConfig: MonitoringConfig = {
  prometheus: {
    enabled: true,
    port: 9090,
    path: '/metrics',
    collectDefaultMetrics: true,
    customMetrics: true,
  },
  jaeger: {
    enabled: true,
    endpoint: 'http://localhost:14268',
    serviceName: 'asi-code',
    samplingRate: 0.1,
  },
  sentry: {
    enabled: true,
    dsn: process.env.SENTRY_DSN || '',
    environment: process.env.NODE_ENV || 'development',
    tracesSampleRate: 0.1,
  },
  health: {
    enabled: true,
    path: '/health',
    interval: 30000,
  },
  slo: {
    enabled: true,
    targets: {
      availability: 99.9,
      latency_p95: 200,
      error_rate: 0.1,
    },
  },
  anomaly: {
    enabled: true,
    thresholds: {
      memory_usage: 0.8,
      cpu_usage: 0.8,
      response_time: 5000,
    },
  },
  correlation: {
    enabled: true,
    headerName: 'x-correlation-id',
  },
};