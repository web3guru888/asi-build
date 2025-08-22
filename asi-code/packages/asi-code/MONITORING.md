# ASI-Code Comprehensive Monitoring and Observability System

This document provides a complete guide to the monitoring and observability capabilities implemented for ASI-Code.

## Overview

The ASI-Code monitoring system provides enterprise-grade observability with:

- **Prometheus Metrics**: Real-time metrics collection and alerting
- **Distributed Tracing**: Full request tracing with Jaeger integration
- **Health Monitoring**: Comprehensive health checks and status reporting
- **Error Tracking**: Intelligent error tracking and analysis with Sentry
- **SLO/SLI Tracking**: Service level objectives and compliance monitoring
- **Anomaly Detection**: AI-powered anomaly detection and correlation
- **Performance Monitoring**: Detailed performance analysis and optimization
- **Log Correlation**: Request correlation across all system components
- **Automated Reporting**: Scheduled reports and executive dashboards
- **Runbook Automation**: Automated incident response and remediation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASI-Code Application                          │
├─────────────────────────────────────────────────────────────────┤
│                   Monitoring System                             │
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┤
│ Prometheus │ Jaeger │ Health │ Sentry │ SLO │ Anomaly │ Reports │
│  Metrics   │ Tracing│ Checks │ Errors │Track│Detection│ System  │
├─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┤
│              Correlation & Aggregation Layer                    │
├─────────────────────────────────────────────────────────────────┤
│                    Data Storage Layer                           │
│            (Prometheus, Jaeger, File System)                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Install monitoring dependencies
bun install prom-client @sentry/node jaeger-client @opentelemetry/api
```

### 2. Basic Setup

```typescript
import { createMonitoringSystem, defaultMonitoringConfig } from './src/monitoring';

// Initialize monitoring system
const monitoring = createMonitoringSystem({
  config: {
    ...defaultMonitoringConfig,
    prometheus: { enabled: true, port: 9090 },
    sentry: { 
      enabled: true, 
      dsn: 'your-sentry-dsn',
      environment: 'production'
    },
    jaeger: {
      enabled: true,
      endpoint: 'http://localhost:14268',
      serviceName: 'asi-code'
    }
  },
  reportDirectory: './reports',
  runbookDirectory: './runbooks'
});

// Initialize the system
await monitoring.initialize();

// Set up middleware in your Hono app
monitoring.setupMiddleware(app);
```

### 3. Basic Usage

```typescript
// Record business metrics
monitoring.recordBusinessMetric('session_created', 1, { provider: 'anthropic' });

// Track tool execution
monitoring.recordToolExecution('bash', true, 1500, 'session-123');

// Record errors with context
monitoring.recordError(new Error('Database connection failed'), {
  tags: { component: 'database' },
  level: 'critical'
});
```

## Component Details

### 1. Prometheus Metrics

Comprehensive metrics collection for:

- **HTTP Requests**: Response times, status codes, throughput
- **Business Logic**: Sessions, tool executions, provider requests
- **System Performance**: CPU, memory, disk, network
- **Error Rates**: Error counts by type and component
- **SLI Metrics**: Availability, latency, error rate

#### Key Metrics

```typescript
// HTTP metrics
asi_code_http_requests_total{method, route, status_code}
asi_code_http_request_duration_seconds{method, route}

// Business metrics
asi_code_sessions_created_total{session_type, provider}
asi_code_tool_executions_total{tool_name, status}
asi_code_provider_requests_total{provider_name, model}

// System metrics
asi_code_system_cpu_usage_percent
asi_code_system_memory_usage_bytes
asi_code_process_uptime_seconds
```

#### Access

- Metrics endpoint: `http://localhost:3000/metrics`
- Performance dashboard: `http://localhost:3000/metrics/performance`

### 2. Distributed Tracing

OpenTelemetry-based tracing with Jaeger backend:

- **Request Tracing**: Full request lifecycle tracking
- **Cross-Service Correlation**: Service boundary tracing
- **Performance Analysis**: Operation timing and bottleneck identification
- **Error Context**: Error propagation and root cause analysis

#### Usage

```typescript
// Automatic tracing (via middleware)
// Manual tracing
await tracingService.traceSessionOperation('create', sessionId, async (span) => {
  // Your operation here
  span.setAttributes({ userId, provider });
  return result;
});
```

#### Access

- Jaeger UI: `http://localhost:16686`
- Trace correlation in logs via correlation IDs

### 3. Health Monitoring

Multi-level health checks:

- **Liveness Probe**: Basic service availability
- **Readiness Probe**: Service ready to handle requests
- **Deep Health Checks**: Component-specific diagnostics
- **Dependency Checks**: External service availability

#### Health Check Types

- System resources (CPU, memory, disk)
- Database connectivity
- External API availability
- Component-specific health (sessions, tools, providers)

#### Endpoints

- Main health: `GET /health`
- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`
- Component health: `GET /health/check/:name`

### 4. Error Tracking (Sentry)

Intelligent error tracking and analysis:

- **Automatic Error Capture**: Unhandled exceptions and errors
- **Custom Error Context**: User, session, and operation context
- **Error Grouping**: Similar errors grouped automatically
- **Performance Impact**: Error impact on system performance
- **Alert Integration**: Configurable error rate alerting

#### Usage

```typescript
// Automatic error capture (via middleware)

// Manual error tracking
errorTracker.captureToolError(error, 'bash', sessionId, parameters);
errorTracker.captureProviderError(error, 'anthropic', 'claude-3', requestData);
```

### 5. SLO/SLI Tracking

Service Level Objective monitoring:

- **Availability SLO**: 99.9% uptime target
- **Latency SLO**: P95 < 200ms target
- **Error Rate SLO**: < 0.1% error rate target
- **Error Budget**: Burn rate tracking and alerting
- **Historical Compliance**: Long-term SLO compliance analysis

#### Default SLOs

- **Availability**: 99.9% (error budget: 8.64 minutes/day)
- **Latency**: 95% of requests < 200ms
- **Error Rate**: < 0.1% of total requests
- **Session Success**: 95% successful session completion
- **Tool Success**: 98% successful tool executions

#### Access

- SLO dashboard: `GET /metrics/slo`
- Compliance reports: Generated automatically

### 6. Anomaly Detection

AI-powered anomaly detection:

- **Statistical Methods**: Z-score, IQR, percentile-based detection
- **Machine Learning**: Isolation forest for complex patterns
- **Seasonal Detection**: Time-based pattern recognition
- **Correlation Analysis**: Multi-metric anomaly correlation
- **Severity Classification**: Low, medium, high, critical severity levels

#### Detection Methods

- **Z-Score**: Statistical deviation detection
- **IQR**: Interquartile range outlier detection
- **Rate Change**: Sudden rate changes
- **Seasonal**: Seasonal pattern deviations
- **Composite**: Multiple method combination

#### Access

- Anomalies endpoint: `GET /metrics/anomalies`
- Real-time alerts for critical anomalies

### 7. Performance Monitoring

Detailed performance analysis:

- **Response Time Analysis**: Request timing breakdowns
- **Throughput Monitoring**: Request rate and capacity analysis
- **Resource Utilization**: CPU, memory, and I/O monitoring
- **Event Loop Monitoring**: Node.js event loop lag detection
- **Garbage Collection**: GC pressure and impact analysis

#### Key Performance Indicators

- Response time percentiles (P50, P95, P99)
- Request throughput (requests/second)
- Error rates by endpoint
- Resource utilization trends
- Performance bottleneck identification

### 8. Log Correlation

Request correlation across all system components:

- **Correlation IDs**: Unique request tracking
- **Cross-Service Tracing**: Service boundary correlation
- **Session Correlation**: User session tracking
- **Error Correlation**: Error context and causation
- **Performance Correlation**: Performance impact analysis

#### Usage

```typescript
// Automatic correlation (via middleware)

// Manual correlation
correlationTracker.withSessionCorrelation(sessionId, userId, provider, () => {
  // All logs in this context will have correlation info
  logger.info('Session operation completed');
});
```

### 9. Automated Reporting

Scheduled and on-demand reporting:

- **Performance Reports**: Daily/weekly performance summaries
- **SLO Compliance Reports**: SLO adherence and violations
- **Error Analysis Reports**: Error trends and patterns
- **Anomaly Summaries**: Anomaly detection results
- **Executive Dashboards**: High-level business metrics

#### Report Types

- **Daily Performance**: 24-hour performance summary
- **Weekly SLO**: 7-day SLO compliance report
- **Monthly Executive**: Business metrics and trends
- **Incident Reports**: Post-incident analysis
- **Custom Reports**: Configurable report generation

#### Delivery Methods

- Email (HTML/PDF)
- Slack notifications
- File export (JSON/CSV)
- Webhook integration

### 10. Runbook Automation

Automated incident response:

- **Trigger-Based Execution**: Alert-triggered runbook execution
- **Remediation Scripts**: Automated fix attempts
- **Escalation Procedures**: Automatic escalation workflows
- **Diagnostic Collection**: Automated diagnostic data gathering
- **Recovery Procedures**: Service recovery automation

#### Default Runbooks

- **High CPU Usage**: Resource analysis and service restart
- **Service Down**: Health checks and service recovery
- **High Error Rate**: Error analysis and mitigation
- **Memory Leaks**: Memory analysis and cleanup
- **SLO Violations**: SLO breach response

## Configuration

### Environment Variables

```bash
# Sentry configuration
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production

# Jaeger configuration
JAEGER_ENDPOINT=http://localhost:14268
JAEGER_SERVICE_NAME=asi-code

# Prometheus configuration
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics

# Report configuration
REPORT_DIRECTORY=./reports
RUNBOOK_DIRECTORY=./runbooks
```

### Configuration File

```yaml
# asi-code-monitoring.yml
monitoring:
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
    collectDefaultMetrics: true
    
  jaeger:
    enabled: true
    endpoint: http://localhost:14268
    serviceName: asi-code
    samplingRate: 0.1
    
  sentry:
    enabled: true
    dsn: ${SENTRY_DSN}
    environment: ${NODE_ENV}
    tracesSampleRate: 0.1
    
  health:
    enabled: true
    path: /health
    interval: 30000
    
  slo:
    enabled: true
    targets:
      availability: 99.9
      latency_p95: 200
      error_rate: 0.1
      
  anomaly:
    enabled: true
    thresholds:
      memory_usage: 0.8
      cpu_usage: 0.8
      response_time: 5000
```

## Dashboards

### Grafana Dashboard Configurations

Pre-configured Grafana dashboards are provided:

1. **ASI-Code Overview**: `monitoring/grafana/provisioning/dashboards/asi-code-overview.json`
2. **Performance Dashboard**: `monitoring/grafana/provisioning/dashboards/asi-code-performance.json`
3. **Business Metrics**: `monitoring/grafana/provisioning/dashboards/asi-code-business.json`
4. **SLO Dashboard**: `monitoring/grafana/provisioning/dashboards/asi-code-slo.json`

### Import Instructions

1. Copy dashboard JSON files to Grafana provisioning directory
2. Restart Grafana or reload provisioning
3. Configure Prometheus data source
4. Dashboards will be automatically loaded

## Alerting

### Prometheus Alerting Rules

Comprehensive alerting rules in `monitoring/alerting-rules-comprehensive.yml`:

- **Infrastructure Alerts**: CPU, memory, disk usage
- **Performance Alerts**: Response time, throughput
- **Error Rate Alerts**: Application and business errors
- **SLO Violation Alerts**: SLO breach notifications
- **Health Check Alerts**: Component health issues
- **Security Alerts**: Unusual traffic patterns

### Alert Configuration

```yaml
# prometheus.yml
rule_files:
  - "alerting-rules-comprehensive.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## Troubleshooting

### Common Issues

1. **Metrics Not Appearing**
   - Check Prometheus scrape configuration
   - Verify metrics endpoint accessibility
   - Ensure metrics are being generated

2. **Traces Not Showing**
   - Verify Jaeger endpoint configuration
   - Check sampling rate settings
   - Ensure OpenTelemetry is properly initialized

3. **Health Checks Failing**
   - Review health check logs
   - Verify dependent services are running
   - Check network connectivity

4. **Anomaly Detection Not Working**
   - Ensure sufficient historical data
   - Check detection rule configuration
   - Verify metric data quality

### Debug Endpoints

- System status: `GET /monitoring/status`
- Component health: `GET /health/check/:component`
- Error metrics: `GET /metrics/errors`
- Performance stats: `GET /metrics/performance`

## Best Practices

### 1. Metric Naming

```typescript
// Good
asi_code_tool_execution_duration_seconds{tool_name="bash", status="success"}

// Bad
tool_time{tool="bash"}
```

### 2. Alert Fatigue Prevention

- Set appropriate thresholds
- Use alert grouping and deduplication
- Implement alert escalation
- Regular alert review and tuning

### 3. Performance Impact

- Use appropriate sampling rates
- Monitor monitoring system resource usage
- Optimize metric cardinality
- Regular performance review

### 4. Data Retention

- Configure appropriate retention periods
- Implement data downsampling
- Monitor storage usage
- Regular cleanup procedures

## Integration Examples

### Custom Metrics

```typescript
// Business metric tracking
monitoring.recordBusinessMetric('user_satisfaction', 4.8, {
  survey_type: 'nps',
  user_segment: 'enterprise'
});

// Performance profiling
const profileId = monitoring.startPerformanceProfile('complex_operation', {
  user_id: userId,
  operation_type: 'data_processing'
});

try {
  await performComplexOperation();
} finally {
  monitoring.endPerformanceProfile(profileId);
}
```

### Error Context

```typescript
try {
  await riskyOperation();
} catch (error) {
  monitoring.recordError(error, {
    tags: {
      component: 'data_processor',
      severity: 'high',
      user_id: userId
    },
    extra: {
      operation_context: operationData,
      user_session: sessionData
    }
  });
  throw error;
}
```

### Health Check Extension

```typescript
// Add custom health checker
healthService.addChecker({
  name: 'external_api',
  check: async () => {
    const response = await fetch('https://api.external.com/health');
    return {
      name: 'external_api',
      status: response.ok ? 'healthy' : 'unhealthy',
      message: response.ok ? 'API responding' : 'API unreachable',
      duration: response.time,
      lastCheck: Date.now(),
      checkCount: 1,
      errorCount: response.ok ? 0 : 1
    };
  },
  isRequired: false,
  timeout: 5000,
  interval: 30000
});
```

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review component logs
3. Use debug endpoints for diagnostics
4. Contact the platform team

## Contributing

When adding new monitoring capabilities:

1. Follow existing patterns and conventions
2. Add appropriate tests
3. Update documentation
4. Consider performance impact
5. Add relevant alerts and dashboards

This monitoring system provides comprehensive observability for ASI-Code, enabling proactive issue detection, rapid troubleshooting, and continuous performance optimization.