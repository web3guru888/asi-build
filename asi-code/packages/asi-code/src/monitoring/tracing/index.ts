/**
 * Distributed Tracing System with Jaeger
 * 
 * Provides comprehensive distributed tracing for ASI-Code including:
 * - OpenTelemetry integration
 * - Jaeger exporter setup
 * - Custom span creation and management
 * - Trace correlation across services
 * - Performance tracking
 */

import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { JaegerExporter } from '@opentelemetry/exporter-jaeger';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { 
  trace, 
  context, 
  SpanStatusCode, 
  SpanKind,
  Span,
  Tracer 
} from '@opentelemetry/api';
import type { MonitoringConfig } from '../index.js';
import { nanoid } from 'nanoid';

export interface TracingService {
  startSpan(name: string, attributes?: Record<string, any>): Span;
  finishSpan(span: Span, error?: Error): void;
  addSpanAttribute(span: Span, key: string, value: any): void;
  createChildSpan(parentSpan: Span, name: string, attributes?: Record<string, any>): Span;
  getTraceId(): string;
  getSpanId(): string;
  injectTraceContext(headers: Record<string, string>): void;
  extractTraceContext(headers: Record<string, string>): void;
}

export class JaegerTracingService implements TracingService {
  private sdk: NodeSDK;
  private tracer: Tracer;
  private config: MonitoringConfig['jaeger'];
  private serviceName: string;
  
  constructor(config: MonitoringConfig['jaeger']) {
    this.config = config;
    this.serviceName = config.serviceName;
    this.initializeTracing();
    this.tracer = trace.getTracer(this.serviceName);
  }
  
  private initializeTracing(): void {
    // Create Jaeger exporter
    const jaegerExporter = new JaegerExporter({
      endpoint: this.config.endpoint,
    });
    
    // Create SDK
    this.sdk = new NodeSDK({
      resource: new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: this.serviceName,
        [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
        [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: process.env.NODE_ENV || 'development',
      }),
      traceExporter: jaegerExporter,
      instrumentations: [getNodeAutoInstrumentations({
        // Disable some instrumentations if needed
        '@opentelemetry/instrumentation-fs': {
          enabled: false,
        },
      })],
    });
    
    // Initialize the SDK
    this.sdk.start();
    
    console.log('Jaeger tracing initialized');
  }
  
  startSpan(name: string, attributes?: Record<string, any>): Span {
    const span = this.tracer.startSpan(name, {
      kind: SpanKind.INTERNAL,
      attributes: {
        'service.name': this.serviceName,
        ...attributes,
      },
    });
    
    return span;
  }
  
  finishSpan(span: Span, error?: Error): void {
    if (error) {
      span.recordException(error);
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error.message,
      });
    } else {
      span.setStatus({ code: SpanStatusCode.OK });
    }
    
    span.end();
  }
  
  addSpanAttribute(span: Span, key: string, value: any): void {
    span.setAttributes({ [key]: value });
  }
  
  createChildSpan(parentSpan: Span, name: string, attributes?: Record<string, any>): Span {
    return this.tracer.startSpan(name, {
      parent: parentSpan,
      kind: SpanKind.INTERNAL,
      attributes: {
        'service.name': this.serviceName,
        ...attributes,
      },
    });
  }
  
  getTraceId(): string {
    const activeSpan = trace.getActiveSpan();
    return activeSpan ? activeSpan.spanContext().traceId : nanoid();
  }
  
  getSpanId(): string {
    const activeSpan = trace.getActiveSpan();
    return activeSpan ? activeSpan.spanContext().spanId : nanoid();
  }
  
  injectTraceContext(headers: Record<string, string>): void {
    // Inject current trace context into headers
    trace.setSpanContext(context.active(), trace.getActiveSpan()?.spanContext() || trace.setSpanContext(context.active(), trace.getActiveSpan()?.spanContext()!));
  }
  
  extractTraceContext(headers: Record<string, string>): void {
    // Extract trace context from headers
    // This would typically use OpenTelemetry's propagation API
  }
  
  // ASI-Code specific tracing methods
  traceSessionOperation<T>(operation: string, sessionId: string, fn: (span: Span) => Promise<T>): Promise<T> {
    return this.traceAsyncOperation(`session.${operation}`, {
      'session.id': sessionId,
      'operation.type': 'session',
    }, fn);
  }
  
  traceToolExecution<T>(toolName: string, sessionId: string, fn: (span: Span) => Promise<T>): Promise<T> {
    return this.traceAsyncOperation(`tool.${toolName}`, {
      'tool.name': toolName,
      'session.id': sessionId,
      'operation.type': 'tool',
    }, fn);
  }
  
  traceProviderRequest<T>(provider: string, model: string, fn: (span: Span) => Promise<T>): Promise<T> {
    return this.traceAsyncOperation(`provider.${provider}`, {
      'provider.name': provider,
      'provider.model': model,
      'operation.type': 'provider',
    }, fn);
  }
  
  traceKennyOperation<T>(subsystem: string, operation: string, fn: (span: Span) => Promise<T>): Promise<T> {
    return this.traceAsyncOperation(`kenny.${subsystem}.${operation}`, {
      'kenny.subsystem': subsystem,
      'kenny.operation': operation,
      'operation.type': 'kenny',
    }, fn);
  }
  
  private async traceAsyncOperation<T>(
    spanName: string, 
    attributes: Record<string, any>, 
    fn: (span: Span) => Promise<T>
  ): Promise<T> {
    const span = this.startSpan(spanName, attributes);
    
    try {
      const result = await context.with(trace.setSpan(context.active(), span), () => fn(span));
      this.finishSpan(span);
      return result;
    } catch (error) {
      this.finishSpan(span, error as Error);
      throw error;
    }
  }
  
  // Middleware for automatic HTTP tracing
  createMiddleware() {
    return async (c: any, next: any) => {
      const traceId = this.getTraceId();
      const spanName = `HTTP ${c.req.method} ${c.req.path}`;
      
      const span = this.startSpan(spanName, {
        'http.method': c.req.method,
        'http.url': c.req.url,
        'http.route': c.req.path,
        'trace.id': traceId,
      });
      
      // Add trace ID to response headers
      c.res.headers.set('X-Trace-Id', traceId);
      
      try {
        await context.with(trace.setSpan(context.active(), span), next);
        
        this.addSpanAttribute(span, 'http.status_code', c.res.status);
        this.finishSpan(span);
      } catch (error) {
        this.addSpanAttribute(span, 'http.status_code', c.res.status || 500);
        this.finishSpan(span, error as Error);
        throw error;
      }
    };
  }
  
  shutdown(): Promise<void> {
    return this.sdk.shutdown();
  }
}

// Trace sampling configuration
export class TraceSampler {
  private config: MonitoringConfig['jaeger'];
  
  constructor(config: MonitoringConfig['jaeger']) {
    this.config = config;
  }
  
  // Smart sampling based on operation type
  shouldSample(operationType: string, attributes?: Record<string, any>): boolean {
    const baseSamplingRate = this.config.samplingRate;
    
    // Higher sampling for errors
    if (attributes?.error === true) {
      return Math.random() < Math.min(baseSamplingRate * 5, 1.0);
    }
    
    // Higher sampling for critical operations
    const criticalOperations = ['session.create', 'session.close', 'tool.execute', 'provider.request'];
    if (criticalOperations.some(op => operationType.includes(op))) {
      return Math.random() < Math.min(baseSamplingRate * 2, 1.0);
    }
    
    // Lower sampling for health checks
    if (operationType.includes('health')) {
      return Math.random() < baseSamplingRate * 0.1;
    }
    
    return Math.random() < baseSamplingRate;
  }
}

// Trace enrichment utilities
export class TraceEnricher {
  static enrichSessionTrace(span: Span, sessionData: any): void {
    span.setAttributes({
      'session.type': sessionData.type,
      'session.provider': sessionData.provider,
      'session.user_id': sessionData.userId,
      'session.created_at': sessionData.createdAt,
    });
  }
  
  static enrichToolTrace(span: Span, toolData: any): void {
    span.setAttributes({
      'tool.name': toolData.name,
      'tool.version': toolData.version,
      'tool.parameters': JSON.stringify(toolData.parameters),
      'tool.execution_time': toolData.executionTime,
    });
  }
  
  static enrichProviderTrace(span: Span, providerData: any): void {
    span.setAttributes({
      'provider.name': providerData.name,
      'provider.model': providerData.model,
      'provider.tokens.input': providerData.inputTokens,
      'provider.tokens.output': providerData.outputTokens,
      'provider.cost': providerData.cost,
    });
  }
  
  static enrichKennyTrace(span: Span, kennyData: any): void {
    span.setAttributes({
      'kenny.subsystem': kennyData.subsystem,
      'kenny.operation': kennyData.operation,
      'kenny.state.from': kennyData.fromState,
      'kenny.state.to': kennyData.toState,
      'kenny.message_id': kennyData.messageId,
    });
  }
  
  static enrichErrorTrace(span: Span, error: Error): void {
    span.setAttributes({
      'error.type': error.constructor.name,
      'error.message': error.message,
      'error.stack': error.stack,
    });
  }
}

export function createTracingService(config: MonitoringConfig['jaeger']): TracingService {
  return new JaegerTracingService(config);
}