/**
 * Log Correlation System for ASI-Code
 * 
 * Provides correlation IDs across all systems for distributed tracing and debugging:
 * - Request correlation ID generation and propagation
 * - Session correlation tracking
 * - Tool execution correlation
 * - Provider request correlation
 * - Kenny subsystem correlation
 * - Cross-service correlation
 */

import { AsyncLocalStorage } from 'async_hooks';
import { nanoid } from 'nanoid';
import type { MonitoringConfig } from '../index.js';

export interface CorrelationContext {
  correlationId: string;
  sessionId?: string;
  userId?: string;
  requestId?: string;
  traceId?: string;
  spanId?: string;
  parentCorrelationId?: string;
  metadata: Record<string, any>;
  startTime: number;
}

export interface CorrelationMetadata {
  component: string;
  operation: string;
  version?: string;
  environment?: string;
  tags?: Record<string, string>;
}

export class CorrelationTracker {
  private readonly config: MonitoringConfig['correlation'];
  private readonly asyncStorage = new AsyncLocalStorage<CorrelationContext>();
  private readonly correlationMap = new Map<string, CorrelationContext>();
  private readonly correlationIndex = new Map<string, Set<string>>(); // sessionId -> correlationIds
  
  constructor(config: MonitoringConfig['correlation']) {
    this.config = config;
  }
  
  // Core correlation methods
  
  generateCorrelationId(): string {
    return nanoid(16);
  }
  
  createContext(
    correlationId?: string,
    metadata: Partial<CorrelationContext> = {}
  ): CorrelationContext {
    const context: CorrelationContext = {
      correlationId: correlationId || this.generateCorrelationId(),
      startTime: Date.now(),
      metadata: metadata.metadata || {},
      ...metadata,
    };
    
    this.correlationMap.set(context.correlationId, context);
    
    // Index by session ID if available
    if (context.sessionId) {
      const sessionCorrelations = this.correlationIndex.get(context.sessionId) || new Set();
      sessionCorrelations.add(context.correlationId);
      this.correlationIndex.set(context.sessionId, sessionCorrelations);
    }
    
    return context;
  }
  
  getCurrentContext(): CorrelationContext | undefined {
    return this.asyncStorage.getStore();
  }
  
  getCurrentCorrelationId(): string | undefined {
    return this.getCurrentContext()?.correlationId;
  }
  
  withCorrelation<T>(
    context: CorrelationContext,
    fn: () => T
  ): T {
    return this.asyncStorage.run(context, fn);
  }
  
  async withCorrelationAsync<T>(
    context: CorrelationContext,
    fn: () => Promise<T>
  ): Promise<T> {
    return this.asyncStorage.run(context, fn);
  }
  
  // Context creation helpers
  
  createRequestContext(
    requestId: string,
    headers: Record<string, string>,
    metadata: CorrelationMetadata
  ): CorrelationContext {
    const parentCorrelationId = headers[this.config.headerName];
    const traceId = headers['x-trace-id'] || headers['traceparent'];
    
    const context = this.createContext(undefined, {
      requestId,
      parentCorrelationId,
      traceId,
      metadata: {
        ...metadata,
        userAgent: headers['user-agent'],
        ip: headers['x-forwarded-for'] || headers['x-real-ip'],
      },
    });
    
    return context;
  }
  
  createSessionContext(
    sessionId: string,
    userId?: string,
    provider?: string
  ): CorrelationContext {
    const parentContext = this.getCurrentContext();
    
    const context = this.createContext(undefined, {
      sessionId,
      userId,
      parentCorrelationId: parentContext?.correlationId,
      metadata: {
        component: 'session',
        operation: 'create',
        provider,
        sessionType: 'user',
      },
    });
    
    return context;
  }
  
  createToolContext(
    toolName: string,
    sessionId?: string,
    parameters?: Record<string, any>
  ): CorrelationContext {
    const parentContext = this.getCurrentContext();
    
    const context = this.createContext(undefined, {
      sessionId: sessionId || parentContext?.sessionId,
      parentCorrelationId: parentContext?.correlationId,
      metadata: {
        component: 'tool',
        operation: 'execute',
        toolName,
        parameters,
      },
    });
    
    return context;
  }
  
  createProviderContext(
    provider: string,
    model: string,
    requestData?: any
  ): CorrelationContext {
    const parentContext = this.getCurrentContext();
    
    const context = this.createContext(undefined, {
      sessionId: parentContext?.sessionId,
      parentCorrelationId: parentContext?.correlationId,
      metadata: {
        component: 'provider',
        operation: 'request',
        provider,
        model,
        requestData: this.sanitizeRequestData(requestData),
      },
    });
    
    return context;
  }
  
  createKennyContext(
    subsystem: string,
    operation: string,
    metadata: Record<string, any> = {}
  ): CorrelationContext {
    const parentContext = this.getCurrentContext();
    
    const context = this.createContext(undefined, {
      sessionId: parentContext?.sessionId,
      parentCorrelationId: parentContext?.correlationId,
      metadata: {
        component: 'kenny',
        operation,
        subsystem,
        ...metadata,
      },
    });
    
    return context;
  }
  
  // Context updating
  
  updateContext(updates: Partial<CorrelationContext>): void {
    const current = this.getCurrentContext();
    if (current) {
      Object.assign(current, updates);
      if (updates.metadata) {
        Object.assign(current.metadata, updates.metadata);
      }
    }
  }
  
  addMetadata(key: string, value: any): void {
    const current = this.getCurrentContext();
    if (current) {
      current.metadata[key] = value;
    }
  }
  
  // Header injection/extraction
  
  injectHeaders(headers: Record<string, string> = {}): Record<string, string> {
    const context = this.getCurrentContext();
    if (context) {
      headers[this.config.headerName] = context.correlationId;
      
      if (context.traceId) {
        headers['x-trace-id'] = context.traceId;
      }
      
      if (context.sessionId) {
        headers['x-session-id'] = context.sessionId;
      }
      
      if (context.userId) {
        headers['x-user-id'] = context.userId;
      }
    }
    
    return headers;
  }
  
  extractFromHeaders(headers: Record<string, string>): {
    correlationId?: string;
    sessionId?: string;
    userId?: string;
    traceId?: string;
  } {
    return {
      correlationId: headers[this.config.headerName],
      sessionId: headers['x-session-id'],
      userId: headers['x-user-id'],
      traceId: headers['x-trace-id'] || headers['traceparent'],
    };
  }
  
  // Middleware creation
  
  createMiddleware() {
    return async (c: any, next: any) => {
      const headers = c.req.header() || {};
      const extracted = this.extractFromHeaders(headers);
      
      const context = this.createRequestContext(
        c.req.header('x-request-id') || this.generateCorrelationId(),
        headers,
        {
          component: 'server',
          operation: 'request',
          environment: process.env.NODE_ENV || 'development',
          tags: {
            method: c.req.method,
            path: c.req.path,
          },
        }
      );
      
      // Merge extracted correlation info
      if (extracted.correlationId) {
        context.parentCorrelationId = extracted.correlationId;
      }
      if (extracted.sessionId) {
        context.sessionId = extracted.sessionId;
      }
      if (extracted.userId) {
        context.userId = extracted.userId;
      }
      if (extracted.traceId) {
        context.traceId = extracted.traceId;
      }
      
      // Inject correlation headers into response
      c.res.headers.set(this.config.headerName, context.correlationId);
      c.res.headers.set('x-request-id', context.requestId || context.correlationId);
      
      await this.withCorrelationAsync(context, next);
    };
  }
  
  // Utility methods
  
  private sanitizeRequestData(data: any): any {
    if (!data) return undefined;
    
    // Remove sensitive information
    const sanitized = JSON.parse(JSON.stringify(data));
    
    // Remove common sensitive fields
    const sensitiveFields = ['password', 'token', 'key', 'secret', 'auth'];
    
    const sanitizeObject = (obj: any): void => {
      if (typeof obj === 'object' && obj !== null) {
        for (const key in obj) {
          if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
            obj[key] = '[REDACTED]';
          } else if (typeof obj[key] === 'object') {
            sanitizeObject(obj[key]);
          }
        }
      }
    };
    
    sanitizeObject(sanitized);
    return sanitized;
  }
  
  // Query and retrieval methods
  
  getContext(correlationId: string): CorrelationContext | undefined {
    return this.correlationMap.get(correlationId);
  }
  
  getSessionCorrelations(sessionId: string): CorrelationContext[] {
    const correlationIds = this.correlationIndex.get(sessionId) || new Set();
    return Array.from(correlationIds)
      .map(id => this.correlationMap.get(id))
      .filter(Boolean) as CorrelationContext[];
  }
  
  getCorrelationChain(correlationId: string): CorrelationContext[] {
    const chain: CorrelationContext[] = [];
    let current = this.getContext(correlationId);
    
    while (current) {
      chain.unshift(current);
      current = current.parentCorrelationId 
        ? this.getContext(current.parentCorrelationId)
        : undefined;
    }
    
    return chain;
  }
  
  findCorrelations(filter: {
    sessionId?: string;
    userId?: string;
    component?: string;
    operation?: string;
    startTime?: number;
    endTime?: number;
  }): CorrelationContext[] {
    const results: CorrelationContext[] = [];
    
    for (const context of this.correlationMap.values()) {
      let matches = true;
      
      if (filter.sessionId && context.sessionId !== filter.sessionId) {
        matches = false;
      }
      
      if (filter.userId && context.userId !== filter.userId) {
        matches = false;
      }
      
      if (filter.component && context.metadata.component !== filter.component) {
        matches = false;
      }
      
      if (filter.operation && context.metadata.operation !== filter.operation) {
        matches = false;
      }
      
      if (filter.startTime && context.startTime < filter.startTime) {
        matches = false;
      }
      
      if (filter.endTime && context.startTime > filter.endTime) {
        matches = false;
      }
      
      if (matches) {
        results.push(context);
      }
    }
    
    return results.sort((a, b) => a.startTime - b.startTime);
  }
  
  // Logging integration
  
  getLogContext(): Record<string, any> {
    const context = this.getCurrentContext();
    if (!context) return {};
    
    return {
      correlationId: context.correlationId,
      sessionId: context.sessionId,
      userId: context.userId,
      requestId: context.requestId,
      traceId: context.traceId,
      component: context.metadata.component,
      operation: context.metadata.operation,
    };
  }
  
  formatLogMessage(message: string, level: string = 'info'): string {
    const logContext = this.getLogContext();
    const contextStr = Object.entries(logContext)
      .filter(([_, value]) => value !== undefined)
      .map(([key, value]) => `${key}=${value}`)
      .join(' ');
    
    return contextStr ? `[${contextStr}] ${message}` : message;
  }
  
  // Cleanup methods
  
  cleanup(maxAge: number = 3600000): void { // Default: 1 hour
    const cutoff = Date.now() - maxAge;
    const toDelete: string[] = [];
    
    for (const [id, context] of this.correlationMap) {
      if (context.startTime < cutoff) {
        toDelete.push(id);
      }
    }
    
    for (const id of toDelete) {
      const context = this.correlationMap.get(id);
      if (context?.sessionId) {
        const sessionCorrelations = this.correlationIndex.get(context.sessionId);
        if (sessionCorrelations) {
          sessionCorrelations.delete(id);
          if (sessionCorrelations.size === 0) {
            this.correlationIndex.delete(context.sessionId);
          }
        }
      }
      this.correlationMap.delete(id);
    }
  }
  
  // Statistics
  
  getStatistics(): {
    totalContexts: number;
    activeSessions: number;
    averageChainLength: number;
    topComponents: Array<{ component: string; count: number }>;
    topOperations: Array<{ operation: string; count: number }>;
  } {
    const contexts = Array.from(this.correlationMap.values());
    
    // Calculate average chain length
    const chainLengths = contexts.map(context => {
      let length = 1;
      let current = context.parentCorrelationId;
      while (current && this.correlationMap.has(current)) {
        length++;
        const parent = this.correlationMap.get(current);
        current = parent?.parentCorrelationId;
      }
      return length;
    });
    
    const averageChainLength = chainLengths.length > 0 
      ? chainLengths.reduce((sum, len) => sum + len, 0) / chainLengths.length
      : 0;
    
    // Count components and operations
    const componentCounts = new Map<string, number>();
    const operationCounts = new Map<string, number>();
    
    contexts.forEach(context => {
      const component = context.metadata.component;
      const operation = context.metadata.operation;
      
      if (component) {
        componentCounts.set(component, (componentCounts.get(component) || 0) + 1);
      }
      
      if (operation) {
        operationCounts.set(operation, (operationCounts.get(operation) || 0) + 1);
      }
    });
    
    return {
      totalContexts: contexts.length,
      activeSessions: this.correlationIndex.size,
      averageChainLength,
      topComponents: Array.from(componentCounts.entries())
        .map(([component, count]) => ({ component, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
      topOperations: Array.from(operationCounts.entries())
        .map(([operation, count]) => ({ operation, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10),
    };
  }
}

// Higher-level convenience functions

export function withRequestCorrelation<T>(
  requestId: string,
  headers: Record<string, string>,
  metadata: CorrelationMetadata,
  fn: () => T,
  tracker: CorrelationTracker
): T {
  const context = tracker.createRequestContext(requestId, headers, metadata);
  return tracker.withCorrelation(context, fn);
}

export async function withRequestCorrelationAsync<T>(
  requestId: string,
  headers: Record<string, string>,
  metadata: CorrelationMetadata,
  fn: () => Promise<T>,
  tracker: CorrelationTracker
): Promise<T> {
  const context = tracker.createRequestContext(requestId, headers, metadata);
  return tracker.withCorrelationAsync(context, fn);
}

export function withSessionCorrelation<T>(
  sessionId: string,
  userId: string | undefined,
  provider: string | undefined,
  fn: () => T,
  tracker: CorrelationTracker
): T {
  const context = tracker.createSessionContext(sessionId, userId, provider);
  return tracker.withCorrelation(context, fn);
}

export async function withSessionCorrelationAsync<T>(
  sessionId: string,
  userId: string | undefined,
  provider: string | undefined,
  fn: () => Promise<T>,
  tracker: CorrelationTracker
): Promise<T> {
  const context = tracker.createSessionContext(sessionId, userId, provider);
  return tracker.withCorrelationAsync(context, fn);
}

export function createCorrelationTracker(config: MonitoringConfig['correlation']): CorrelationTracker {
  return new CorrelationTracker(config);
}