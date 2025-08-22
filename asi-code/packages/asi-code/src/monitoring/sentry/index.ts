/**
 * Error Tracking and Monitoring with Sentry
 * 
 * Comprehensive error tracking for ASI-Code including:
 * - Automatic error capture and reporting
 * - Performance monitoring
 * - Custom error contexts and tags
 * - Error grouping and filtering
 * - Release tracking
 * - User and session tracking
 */

import * as Sentry from '@sentry/node';
import { ProfilingIntegration } from '@sentry/profiling-node';
import type { MonitoringConfig } from '../index.js';
import type { Hono } from 'hono';
import { EventEmitter } from 'eventemitter3';

export interface ErrorContext {
  user?: {
    id?: string;
    email?: string;
    username?: string;
  };
  session?: {
    id: string;
    type: string;
    provider?: string;
  };
  request?: {
    url: string;
    method: string;
    headers: Record<string, string>;
    body?: any;
  };
  tags?: Record<string, string>;
  extra?: Record<string, any>;
  level?: 'fatal' | 'error' | 'warning' | 'info' | 'debug';
  fingerprint?: string[];
}

export interface ErrorMetrics {
  totalErrors: number;
  errorsByType: Record<string, number>;
  errorsByComponent: Record<string, number>;
  errorsByLevel: Record<string, number>;
  recentErrors: Array<{
    id: string;
    message: string;
    timestamp: number;
    level: string;
    component: string;
  }>;
}

export class SentryErrorTracker extends EventEmitter {
  private config: MonitoringConfig['sentry'];
  private initialized = false;
  private errorMetrics: ErrorMetrics = {
    totalErrors: 0,
    errorsByType: {},
    errorsByComponent: {},
    errorsByLevel: {},
    recentErrors: [],
  };
  
  constructor(config: MonitoringConfig['sentry']) {
    super();
    this.config = config;
    
    if (config.enabled && config.dsn) {
      this.initializeSentry();
    }
  }
  
  private initializeSentry(): void {
    Sentry.init({
      dsn: this.config.dsn,
      environment: this.config.environment,
      tracesSampleRate: this.config.tracesSampleRate,
      
      // Add profiling integration
      integrations: [
        new ProfilingIntegration(),
      ],
      
      // Performance monitoring
      profilesSampleRate: 0.1,
      
      // Release tracking
      release: process.env.npm_package_version || '1.0.0',
      
      // Error filtering
      beforeSend: (event, hint) => {
        return this.filterError(event, hint);
      },
      
      // Breadcrumb filtering
      beforeBreadcrumb: (breadcrumb) => {
        return this.filterBreadcrumb(breadcrumb);
      },
      
      // Configure tags
      initialScope: {
        tags: {
          service: 'asi-code',
          component: 'main',
        },
      },
    });
    
    this.initialized = true;
    console.log('Sentry error tracking initialized');
  }
  
  private filterError(event: Sentry.Event, hint: Sentry.EventHint): Sentry.Event | null {
    // Filter out certain errors that shouldn't be reported
    const error = hint.originalException;
    
    if (error instanceof Error) {
      // Don't report certain types of errors
      const ignoredErrors = [
        'AbortError',
        'NetworkError',
        'ConnectionError',
      ];
      
      if (ignoredErrors.some(ignored => error.message.includes(ignored))) {
        return null;
      }
      
      // Add custom context
      this.updateErrorMetrics(event);
    }
    
    return event;
  }
  
  private filterBreadcrumb(breadcrumb: Sentry.Breadcrumb): Sentry.Breadcrumb | null {
    // Filter sensitive information from breadcrumbs
    if (breadcrumb.data && breadcrumb.data.url) {
      // Remove sensitive query parameters
      const url = new URL(breadcrumb.data.url);
      url.searchParams.delete('api_key');
      url.searchParams.delete('token');
      breadcrumb.data.url = url.toString();
    }
    
    return breadcrumb;
  }
  
  private updateErrorMetrics(event: Sentry.Event): void {
    this.errorMetrics.totalErrors++;
    
    // Update error counts by type
    const errorType = event.exception?.[0]?.type || 'Unknown';
    this.errorMetrics.errorsByType[errorType] = (this.errorMetrics.errorsByType[errorType] || 0) + 1;
    
    // Update error counts by component
    const component = event.tags?.component || 'unknown';
    this.errorMetrics.errorsByComponent[component] = (this.errorMetrics.errorsByComponent[component] || 0) + 1;
    
    // Update error counts by level
    const level = event.level || 'error';
    this.errorMetrics.errorsByLevel[level] = (this.errorMetrics.errorsByLevel[level] || 0) + 1;
    
    // Add to recent errors
    this.errorMetrics.recentErrors.unshift({
      id: event.event_id || 'unknown',
      message: event.message || event.exception?.[0]?.value || 'Unknown error',
      timestamp: Date.now(),
      level: level,
      component: component,
    });
    
    // Keep only the most recent 100 errors
    if (this.errorMetrics.recentErrors.length > 100) {
      this.errorMetrics.recentErrors = this.errorMetrics.recentErrors.slice(0, 100);
    }
    
    this.emit('error-tracked', this.errorMetrics);
  }
  
  // Core error tracking methods
  captureError(error: Error, context?: ErrorContext): string {
    if (!this.initialized) {
      console.error('Sentry not initialized:', error);
      return 'not-initialized';
    }
    
    return Sentry.withScope((scope) => {
      if (context) {
        this.applyContext(scope, context);
      }
      
      return Sentry.captureException(error);
    });
  }
  
  captureMessage(message: string, level: 'fatal' | 'error' | 'warning' | 'info' | 'debug' = 'info', context?: ErrorContext): string {
    if (!this.initialized) {
      console.log('Sentry not initialized:', message);
      return 'not-initialized';
    }
    
    return Sentry.withScope((scope) => {
      if (context) {
        this.applyContext(scope, context);
      }
      
      scope.setLevel(level);
      return Sentry.captureMessage(message);
    });
  }
  
  private applyContext(scope: Sentry.Scope, context: ErrorContext): void {
    if (context.user) {
      scope.setUser(context.user);
    }
    
    if (context.tags) {
      Object.entries(context.tags).forEach(([key, value]) => {
        scope.setTag(key, value);
      });
    }
    
    if (context.extra) {
      Object.entries(context.extra).forEach(([key, value]) => {
        scope.setExtra(key, value);
      });
    }
    
    if (context.level) {
      scope.setLevel(context.level);
    }
    
    if (context.fingerprint) {
      scope.setFingerprint(context.fingerprint);
    }
    
    if (context.session) {
      scope.setContext('session', context.session);
    }
    
    if (context.request) {
      scope.setContext('request', context.request);
    }
  }
  
  // ASI-Code specific error tracking
  captureSessionError(error: Error, sessionId: string, sessionType: string, provider?: string): string {
    return this.captureError(error, {
      tags: {
        component: 'session',
        session_type: sessionType,
        provider: provider || 'unknown',
      },
      session: {
        id: sessionId,
        type: sessionType,
        provider,
      },
      extra: {
        session_id: sessionId,
      },
    });
  }
  
  captureToolError(error: Error, toolName: string, sessionId: string, parameters?: any): string {
    return this.captureError(error, {
      tags: {
        component: 'tool',
        tool_name: toolName,
      },
      session: {
        id: sessionId,
        type: 'tool_execution',
      },
      extra: {
        tool_name: toolName,
        parameters,
      },
    });
  }
  
  captureProviderError(error: Error, provider: string, model: string, requestData?: any): string {
    return this.captureError(error, {
      tags: {
        component: 'provider',
        provider_name: provider,
        provider_model: model,
      },
      extra: {
        provider,
        model,
        request_data: requestData,
      },
    });
  }
  
  captureKennyError(error: Error, subsystem: string, operation: string, state?: any): string {
    return this.captureError(error, {
      tags: {
        component: 'kenny',
        kenny_subsystem: subsystem,
        kenny_operation: operation,
      },
      extra: {
        subsystem,
        operation,
        state,
      },
    });
  }
  
  captureServerError(error: Error, request?: any): string {
    const requestContext = request ? {
      url: request.url,
      method: request.method,
      headers: this.sanitizeHeaders(request.headers),
    } : undefined;
    
    return this.captureError(error, {
      tags: {
        component: 'server',
      },
      request: requestContext,
    });
  }
  
  private sanitizeHeaders(headers: Record<string, string>): Record<string, string> {
    const sanitized = { ...headers };
    
    // Remove sensitive headers
    const sensitiveHeaders = ['authorization', 'cookie', 'x-api-key', 'x-auth-token'];
    sensitiveHeaders.forEach(header => {
      if (sanitized[header]) {
        sanitized[header] = '[Filtered]';
      }
    });
    
    return sanitized;
  }
  
  // Performance tracking
  startTransaction(name: string, operation: string): Sentry.Transaction {
    return Sentry.startTransaction({
      name,
      op: operation,
    });
  }
  
  // User tracking
  setUser(user: { id?: string; email?: string; username?: string }): void {
    if (!this.initialized) return;
    
    Sentry.setUser(user);
  }
  
  clearUser(): void {
    if (!this.initialized) return;
    
    Sentry.setUser(null);
  }
  
  // Context management
  setContext(key: string, context: any): void {
    if (!this.initialized) return;
    
    Sentry.setContext(key, context);
  }
  
  setTag(key: string, value: string): void {
    if (!this.initialized) return;
    
    Sentry.setTag(key, value);
  }
  
  setExtra(key: string, extra: any): void {
    if (!this.initialized) return;
    
    Sentry.setExtra(key, extra);
  }
  
  // Breadcrumb tracking
  addBreadcrumb(breadcrumb: {
    message?: string;
    category?: string;
    level?: 'fatal' | 'error' | 'warning' | 'info' | 'debug';
    data?: any;
  }): void {
    if (!this.initialized) return;
    
    Sentry.addBreadcrumb(breadcrumb);
  }
  
  // Middleware for automatic error tracking
  createMiddleware() {
    return async (c: any, next: any) => {
      // Set request context
      this.setContext('request', {
        url: c.req.url,
        method: c.req.method,
        headers: this.sanitizeHeaders(c.req.header() || {}),
        path: c.req.path,
      });
      
      // Add breadcrumb for request
      this.addBreadcrumb({
        message: `${c.req.method} ${c.req.path}`,
        category: 'http',
        level: 'info',
        data: {
          url: c.req.url,
          method: c.req.method,
        },
      });
      
      try {
        await next();
        
        // Add successful response breadcrumb
        this.addBreadcrumb({
          message: `Response ${c.res.status}`,
          category: 'http',
          level: 'info',
          data: {
            status_code: c.res.status,
          },
        });
        
      } catch (error) {
        // Capture the error with full context
        this.captureServerError(error as Error, c.req);
        throw error;
      }
    };
  }
  
  // Error metrics and reporting
  getErrorMetrics(): ErrorMetrics {
    return { ...this.errorMetrics };
  }
  
  getErrorTrends(timeWindowMs: number = 3600000): Array<{ timestamp: number; count: number }> {
    const cutoff = Date.now() - timeWindowMs;
    const recentErrors = this.errorMetrics.recentErrors.filter(e => e.timestamp > cutoff);
    
    // Group errors by hour
    const hourlyErrors: Record<number, number> = {};
    recentErrors.forEach(error => {
      const hour = Math.floor(error.timestamp / 3600000) * 3600000;
      hourlyErrors[hour] = (hourlyErrors[hour] || 0) + 1;
    });
    
    return Object.entries(hourlyErrors)
      .map(([timestamp, count]) => ({ timestamp: parseInt(timestamp), count }))
      .sort((a, b) => a.timestamp - b.timestamp);
  }
  
  getMostFrequentErrors(limit = 10): Array<{ type: string; count: number; percentage: number }> {
    const total = this.errorMetrics.totalErrors;
    
    return Object.entries(this.errorMetrics.errorsByType)
      .map(([type, count]) => ({
        type,
        count,
        percentage: total > 0 ? (count / total) * 100 : 0,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }
  
  getErrorsByComponent(): Array<{ component: string; count: number; percentage: number }> {
    const total = this.errorMetrics.totalErrors;
    
    return Object.entries(this.errorMetrics.errorsByComponent)
      .map(([component, count]) => ({
        component,
        count,
        percentage: total > 0 ? (count / total) * 100 : 0,
      }))
      .sort((a, b) => b.count - a.count);
  }
  
  // Health check for error tracking
  getHealthStatus(): { status: 'healthy' | 'degraded' | 'unhealthy'; message: string; metrics: any } {
    if (!this.initialized) {
      return {
        status: 'unhealthy',
        message: 'Sentry not initialized',
        metrics: this.errorMetrics,
      };
    }
    
    // Check error rate
    const recentErrors = this.errorMetrics.recentErrors.filter(
      e => e.timestamp > Date.now() - 300000 // Last 5 minutes
    );
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'Error tracking operational';
    
    if (recentErrors.length > 50) {
      status = 'unhealthy';
      message = 'High error rate detected';
    } else if (recentErrors.length > 20) {
      status = 'degraded';
      message = 'Elevated error rate';
    }
    
    return {
      status,
      message,
      metrics: {
        ...this.errorMetrics,
        recent_errors_5min: recentErrors.length,
      },
    };
  }
  
  // Cleanup
  async flush(timeout = 2000): Promise<boolean> {
    if (!this.initialized) return true;
    
    return Sentry.flush(timeout);
  }
  
  close(): Promise<boolean> {
    if (!this.initialized) return Promise.resolve(true);
    
    return Sentry.close(2000);
  }
}

export function createSentryErrorTracker(config: MonitoringConfig['sentry']): SentryErrorTracker {
  return new SentryErrorTracker(config);
}