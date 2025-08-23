# Monitoring and Observability

This guide covers monitoring, logging, and observability practices for ASI-Code in production environments.

## Table of Contents

- [Overview](#overview)
- [Metrics Collection](#metrics-collection)
- [Logging Strategy](#logging-strategy)
- [Health Checks](#health-checks)
- [Performance Monitoring](#performance-monitoring)
- [Alerting](#alerting)
- [Dashboards](#dashboards)
- [Troubleshooting](#troubleshooting)

## Overview

ASI-Code provides comprehensive monitoring capabilities to ensure system reliability, performance, and security in production environments.

### Key Monitoring Areas

- **System Health**: Component status and availability
- **Performance**: Response times, throughput, resource usage
- **Consciousness**: AI awareness levels and processing metrics
- **Security**: Authentication, authorization, and threat detection
- **Business Metrics**: Usage patterns and user satisfaction

### Monitoring Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Grafana Dashboards                   │
├─────────────────────────────────────────────────────────┤
│  Prometheus  │  Elasticsearch  │  Custom Metrics  │    │
├─────────────────────────────────────────────────────────┤
│    Alertmanager    │      Kibana      │    Jaeger     │
├─────────────────────────────────────────────────────────┤
│                   ASI-Code Metrics                      │
│  Health │ Performance │ Consciousness │ Security │      │
└─────────────────────────────────────────────────────────┘
```

## Metrics Collection

### Built-in Metrics

ASI-Code exposes metrics through the `/metrics` endpoint:

```bash
# View metrics
curl http://localhost:3000/metrics

# Prometheus format
curl -H "Accept: application/openmetrics-text" http://localhost:3000/metrics
```

### Core Metrics

#### System Metrics

```typescript
// Health and availability
asi_code_health{component="kenny"} 1
asi_code_health{component="consciousness"} 1
asi_code_health{component="provider"} 1

// Uptime
asi_code_uptime_seconds 3600

// Version information
asi_code_info{version="1.0.0", node_version="18.17.0"} 1
```

#### Performance Metrics

```typescript
// Request metrics
asi_code_http_requests_total{method="POST", endpoint="/api/sessions/*/messages", status="200"} 1234
asi_code_http_request_duration_seconds{method="POST", endpoint="/api/sessions/*/messages"} 0.245

// Session metrics
asi_code_sessions_active 45
asi_code_sessions_total 1567
asi_code_session_duration_seconds{status="completed"} 1847.3

// Message processing
asi_code_messages_processed_total{type="user"} 2341
asi_code_messages_processed_total{type="assistant"} 2340
asi_code_message_processing_duration_seconds 1.234
```

#### Consciousness Metrics

```typescript
// Consciousness levels
asi_code_consciousness_level{context_id="ctx_123"} 75
asi_code_consciousness_awareness{context_id="ctx_123"} 82
asi_code_consciousness_engagement{context_id="ctx_123"} 78

// Memory usage
asi_code_consciousness_memories_total 1247
asi_code_consciousness_memories_active 234
asi_code_consciousness_memory_retrievals_total 5678
```

#### Provider Metrics

```typescript
// Provider health
asi_code_provider_health{name="anthropic", model="claude-3-sonnet"} 1
asi_code_provider_requests_total{name="anthropic", status="success"} 987
asi_code_provider_request_duration_seconds{name="anthropic"} 1.456

// Token usage
asi_code_provider_tokens_input_total{name="anthropic"} 125467
asi_code_provider_tokens_output_total{name="anthropic"} 87234
asi_code_provider_cost_total{name="anthropic"} 12.45
```

#### Tool Metrics

```typescript
// Tool execution
asi_code_tool_executions_total{name="bash", status="success"} 456
asi_code_tool_execution_duration_seconds{name="bash"} 0.123
asi_code_tool_errors_total{name="bash", error_type="permission_denied"} 3
```

### Custom Metrics

#### Implementing Custom Metrics

```typescript
import { MetricsCollector } from '../monitoring/metrics.js';

class CustomMetrics {
  private metrics: MetricsCollector;
  
  constructor() {
    this.metrics = new MetricsCollector('asi_code');
  }
  
  // Counter metric
  incrementUserAction(action: string, userId: string): void {
    this.metrics.increment('user_actions_total', {
      action,
      user_id: userId
    });
  }
  
  // Histogram metric
  recordProcessingTime(operation: string, duration: number): void {
    this.metrics.histogram('operation_duration_seconds', duration, {
      operation
    });
  }
  
  // Gauge metric
  setActiveConnections(count: number): void {
    this.metrics.gauge('websocket_connections_active', count);
  }
  
  // Business metrics
  recordUserSatisfaction(score: number, sessionId: string): void {
    this.metrics.histogram('user_satisfaction_score', score, {
      session_id: sessionId
    });
  }
}
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "asi_code_rules.yml"

scrape_configs:
  - job_name: 'asi-code'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s

  - job_name: 'asi-code-nodes'
    consul_sd_configs:
      - server: 'localhost:8500'
        services: ['asi-code']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## Logging Strategy

### Log Levels

ASI-Code uses structured logging with the following levels:

```typescript
enum LogLevel {
  ERROR = 'error',     // System errors, failures
  WARN = 'warn',       // Warnings, degraded performance
  INFO = 'info',       // General information, important events
  DEBUG = 'debug',     // Detailed debugging information
  TRACE = 'trace'      // Very detailed tracing
}
```

### Log Configuration

```yaml
# asi-code.config.yml
logging:
  level: info
  format: json
  outputs:
    - type: console
      level: info
    - type: file
      path: /var/log/asi-code/app.log
      level: debug
      maxSize: 100MB
      maxFiles: 10
      compress: true
    - type: elasticsearch
      host: elasticsearch:9200
      index: asi-code-logs
      level: warn

  # Component-specific logging
  components:
    kenny:
      level: debug
    consciousness:
      level: info
    provider:
      level: warn
```

### Structured Logging

```typescript
import { createLogger } from '../logging/logger.js';

const logger = createLogger('kenny');

// Standard log entry
logger.info('Message processed successfully', {
  messageId: 'msg_123',
  sessionId: 'session_456',
  processingTime: 1234,
  consciousnessLevel: 75,
  metadata: {
    provider: 'anthropic',
    model: 'claude-3-sonnet',
    tokens: { input: 45, output: 234 }
  }
});

// Error logging
logger.error('Provider request failed', {
  error: error.message,
  stack: error.stack,
  provider: 'anthropic',
  requestId: 'req_789',
  context: {
    messageId: 'msg_123',
    sessionId: 'session_456'
  }
});

// Performance logging
logger.debug('Consciousness state updated', {
  contextId: 'ctx_123',
  previousLevel: 70,
  newLevel: 75,
  factors: {
    complexity: 85,
    engagement: 80,
    adaptability: 70
  },
  processingTime: 45
});
```

### Log Correlation

```typescript
// Request correlation
class RequestLogger {
  constructor(private correlationId: string) {}
  
  info(message: string, meta: any = {}): void {
    logger.info(message, {
      ...meta,
      correlationId: this.correlationId,
      timestamp: new Date().toISOString()
    });
  }
  
  error(message: string, error: Error, meta: any = {}): void {
    logger.error(message, {
      ...meta,
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      correlationId: this.correlationId,
      timestamp: new Date().toISOString()
    });
  }
}

// Usage
const requestLogger = new RequestLogger(`req_${nanoid()}`);
requestLogger.info('Processing user message', { messageId: 'msg_123' });
```

### Log Aggregation

#### ELK Stack Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
```

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
  
  http {
    port => 8080
    codec => json
  }
}

filter {
  if [fields][service] == "asi-code" {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
    
    if [level] == "error" {
      mutate {
        add_tag => [ "error" ]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "asi-code-logs-%{+YYYY.MM.dd}"
  }
  
  if "error" in [tags] {
    email {
      to => "alerts@asi-code.dev"
      subject => "ASI-Code Error Alert"
      body => "Error detected: %{message}"
    }
  }
}
```

## Health Checks

### Health Check Endpoints

```typescript
// Health check implementation
class HealthChecker {
  async checkHealth(): Promise<HealthStatus> {
    const checks = await Promise.allSettled([
      this.checkKenny(),
      this.checkConsciousness(),
      this.checkProviders(),
      this.checkTools(),
      this.checkDatabase(),
      this.checkRedis()
    ]);
    
    const results = checks.map((check, index) => ({
      component: ['kenny', 'consciousness', 'providers', 'tools', 'database', 'redis'][index],
      status: check.status === 'fulfilled' ? check.value : 'unhealthy',
      details: check.status === 'rejected' ? check.reason : undefined
    }));
    
    const overall = results.every(r => r.status === 'healthy') ? 'healthy' : 'unhealthy';
    
    return {
      status: overall,
      timestamp: new Date().toISOString(),
      version: process.env.npm_package_version,
      uptime: process.uptime(),
      components: results
    };
  }
  
  private async checkKenny(): Promise<'healthy' | 'unhealthy'> {
    // Check Kenny Integration Pattern
    return 'healthy';
  }
  
  private async checkConsciousness(): Promise<'healthy' | 'unhealthy'> {
    // Check Consciousness Engine
    return 'healthy';
  }
  
  private async checkProviders(): Promise<'healthy' | 'unhealthy'> {
    // Check AI providers
    return 'healthy';
  }
}
```

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:3000/health

# Detailed health check
curl http://localhost:3000/health

# Component-specific health (via main health endpoint)
curl http://localhost:3000/health | jq '.components.kenny'
curl http://localhost:3000/health | jq '.components.consciousness'
curl http://localhost:3000/health | jq '.components.providers'
```

### Kubernetes Health Checks

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asi-code
spec:
  template:
    spec:
      containers:
      - name: asi-code
        image: asi-code:latest
        ports:
        - containerPort: 3000
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health/startup
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
```

## Performance Monitoring

### Application Performance Monitoring (APM)

#### Performance Metrics

```typescript
class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics = new Map<string, PerformanceMetric>();
  
  static getInstance(): PerformanceMonitor {
    if (!this.instance) {
      this.instance = new PerformanceMonitor();
    }
    return this.instance;
  }
  
  startTimer(operation: string, metadata?: any): string {
    const timerId = `${operation}_${Date.now()}_${Math.random()}`;
    this.metrics.set(timerId, {
      operation,
      startTime: performance.now(),
      metadata
    });
    return timerId;
  }
  
  endTimer(timerId: string): number {
    const metric = this.metrics.get(timerId);
    if (!metric) return 0;
    
    const duration = performance.now() - metric.startTime;
    this.metrics.delete(timerId);
    
    // Record metric
    metricsCollector.histogram('operation_duration_seconds', duration / 1000, {
      operation: metric.operation,
      ...metric.metadata
    });
    
    return duration;
  }
  
  measureAsync<T>(operation: string, fn: () => Promise<T>, metadata?: any): Promise<T> {
    const timerId = this.startTimer(operation, metadata);
    return fn().finally(() => this.endTimer(timerId));
  }
}

// Usage
const monitor = PerformanceMonitor.getInstance();

// Manual timing
const timerId = monitor.startTimer('message_processing', { userId: 'user123' });
// ... do work ...
const duration = monitor.endTimer(timerId);

// Automatic timing
const result = await monitor.measureAsync('consciousness_processing', async () => {
  return await consciousness.processMessage(message, context);
}, { sessionId: context.sessionId });
```

#### Memory Monitoring

```typescript
class MemoryMonitor {
  private static readonly COLLECTION_INTERVAL = 60000; // 1 minute
  
  constructor() {
    setInterval(() => this.collectMemoryMetrics(), MemoryMonitor.COLLECTION_INTERVAL);
  }
  
  private collectMemoryMetrics(): void {
    const usage = process.memoryUsage();
    
    metricsCollector.gauge('memory_usage_bytes', usage.rss, { type: 'rss' });
    metricsCollector.gauge('memory_usage_bytes', usage.heapUsed, { type: 'heap_used' });
    metricsCollector.gauge('memory_usage_bytes', usage.heapTotal, { type: 'heap_total' });
    metricsCollector.gauge('memory_usage_bytes', usage.external, { type: 'external' });
    
    // V8 heap statistics
    const v8HeapStats = v8.getHeapStatistics();
    metricsCollector.gauge('v8_heap_size_bytes', v8HeapStats.total_heap_size, { type: 'total' });
    metricsCollector.gauge('v8_heap_size_bytes', v8HeapStats.used_heap_size, { type: 'used' });
    metricsCollector.gauge('v8_heap_size_bytes', v8HeapStats.heap_size_limit, { type: 'limit' });
    
    // Garbage collection metrics
    const gcStats = this.getGCStats();
    Object.entries(gcStats).forEach(([type, stats]) => {
      metricsCollector.counter('gc_runs_total', stats.count, { type });
      metricsCollector.histogram('gc_duration_seconds', stats.duration / 1000, { type });
    });
  }
  
  private getGCStats(): Record<string, { count: number; duration: number }> {
    // Implementation depends on Node.js version and GC tracking
    return {
      scavenge: { count: 0, duration: 0 },
      mark_sweep_compact: { count: 0, duration: 0 },
      incremental_marking: { count: 0, duration: 0 }
    };
  }
}
```

### Database Performance

```typescript
// Database query monitoring
class DatabaseMonitor {
  static wrapQuery<T>(query: () => Promise<T>, operation: string): Promise<T> {
    const startTime = performance.now();
    
    return query()
      .then(result => {
        const duration = performance.now() - startTime;
        metricsCollector.histogram('database_query_duration_seconds', duration / 1000, {
          operation,
          status: 'success'
        });
        return result;
      })
      .catch(error => {
        const duration = performance.now() - startTime;
        metricsCollector.histogram('database_query_duration_seconds', duration / 1000, {
          operation,
          status: 'error'
        });
        metricsCollector.increment('database_errors_total', { operation, error: error.name });
        throw error;
      });
  }
}

// Usage
const users = await DatabaseMonitor.wrapQuery(
  () => db.users.findMany(),
  'users_find_many'
);
```

## Alerting

### Alert Rules

```yaml
# asi_code_rules.yml
groups:
- name: asi-code-alerts
  rules:
  
  # High error rate
  - alert: HighErrorRate
    expr: rate(asi_code_http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  # High response time
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(asi_code_http_request_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  # Provider failures
  - alert: ProviderDown
    expr: asi_code_provider_health == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "AI Provider {{ $labels.name }} is down"
      description: "Provider {{ $labels.name }} has been unhealthy for more than 1 minute"

  # Consciousness degradation
  - alert: ConsciousnessLevelLow
    expr: avg(asi_code_consciousness_level) < 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Average consciousness level is low"
      description: "Average consciousness level is {{ $value }}, indicating degraded AI performance"

  # Memory usage
  - alert: HighMemoryUsage
    expr: (asi_code_memory_usage_bytes{type="rss"} / 1024 / 1024 / 1024) > 8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
      description: "Memory usage is {{ $value }}GB"

  # Disk space
  - alert: DiskSpaceLow
    expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.1
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Disk space critically low"
      description: "Only {{ $value | humanizePercentage }} disk space remaining"
```

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@asi-code.dev'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/'

- name: 'critical-alerts'
  email_configs:
  - to: 'oncall@asi-code.dev'
    subject: '[CRITICAL] ASI-Code Alert'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#asi-code-alerts'
    title: 'Critical ASI-Code Alert'
    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

- name: 'warning-alerts'
  email_configs:
  - to: 'team@asi-code.dev'
    subject: '[WARNING] ASI-Code Alert'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

### Custom Alert Handlers

```typescript
class AlertHandler {
  private webhookUrl: string;
  
  constructor(webhookUrl: string) {
    this.webhookUrl = webhookUrl;
  }
  
  async handleAlert(alert: Alert): Promise<void> {
    switch (alert.severity) {
      case 'critical':
        await this.handleCriticalAlert(alert);
        break;
      case 'warning':
        await this.handleWarningAlert(alert);
        break;
      default:
        await this.handleInfoAlert(alert);
    }
  }
  
  private async handleCriticalAlert(alert: Alert): Promise<void> {
    // Page on-call engineer
    await this.sendPagerDutyAlert(alert);
    
    // Send Slack notification
    await this.sendSlackAlert(alert, '#asi-code-critical');
    
    // Log alert
    logger.error('Critical alert triggered', {
      alert: alert.name,
      description: alert.description,
      labels: alert.labels
    });
  }
  
  private async handleWarningAlert(alert: Alert): Promise<void> {
    // Send email to team
    await this.sendEmailAlert(alert, 'team@asi-code.dev');
    
    // Send Slack notification
    await this.sendSlackAlert(alert, '#asi-code-warnings');
    
    // Log alert
    logger.warn('Warning alert triggered', {
      alert: alert.name,
      description: alert.description,
      labels: alert.labels
    });
  }
  
  private async sendSlackAlert(alert: Alert, channel: string): Promise<void> {
    const payload = {
      channel,
      username: 'ASI-Code Monitor',
      icon_emoji: ':warning:',
      attachments: [{
        color: alert.severity === 'critical' ? 'danger' : 'warning',
        title: alert.name,
        text: alert.description,
        fields: Object.entries(alert.labels).map(([key, value]) => ({
          title: key,
          value,
          short: true
        })),
        ts: Math.floor(Date.now() / 1000)
      }]
    };
    
    await fetch(this.webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  }
}
```

## Dashboards

### Grafana Dashboards

#### System Overview Dashboard

```json
{
  "dashboard": {
    "title": "ASI-Code System Overview",
    "panels": [
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "asi_code_health",
            "legendFormat": "{{ component }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "color": "red", "value": 0 },
                { "color": "green", "value": 1 }
              ]
            }
          }
        }
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(asi_code_http_requests_total[5m])",
            "legendFormat": "{{ method }} {{ endpoint }}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(asi_code_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(asi_code_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.99, rate(asi_code_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "99th percentile"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "type": "stat",
        "targets": [
          {
            "expr": "asi_code_sessions_active",
            "legendFormat": "Active Sessions"
          }
        ]
      },
      {
        "title": "Consciousness Levels",
        "type": "heatmap",
        "targets": [
          {
            "expr": "asi_code_consciousness_level",
            "legendFormat": "{{ context_id }}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "asi_code_memory_usage_bytes{type=\"rss\"} / 1024 / 1024",
            "legendFormat": "RSS Memory (MB)"
          },
          {
            "expr": "asi_code_memory_usage_bytes{type=\"heap_used\"} / 1024 / 1024",
            "legendFormat": "Heap Used (MB)"
          }
        ]
      }
    ]
  }
}
```

#### Consciousness Dashboard

```json
{
  "dashboard": {
    "title": "ASI-Code Consciousness Engine",
    "panels": [
      {
        "title": "Average Consciousness Level",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(asi_code_consciousness_level)",
            "legendFormat": "Average Level"
          }
        ]
      },
      {
        "title": "Consciousness Distribution",
        "type": "histogram",
        "targets": [
          {
            "expr": "asi_code_consciousness_level",
            "legendFormat": "{{ context_id }}"
          }
        ]
      },
      {
        "title": "Memory Operations",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(asi_code_consciousness_memory_retrievals_total[5m])",
            "legendFormat": "Memory Retrievals/sec"
          },
          {
            "expr": "rate(asi_code_consciousness_memories_total[5m])",
            "legendFormat": "Memory Creation/sec"
          }
        ]
      },
      {
        "title": "Awareness vs Engagement",
        "type": "scatterplot",
        "targets": [
          {
            "expr": "asi_code_consciousness_awareness",
            "legendFormat": "Awareness"
          },
          {
            "expr": "asi_code_consciousness_engagement",
            "legendFormat": "Engagement"
          }
        ]
      }
    ]
  }
}
```

### Custom Dashboards

```typescript
// Dashboard builder
class DashboardBuilder {
  static buildSystemDashboard(): Dashboard {
    return {
      title: 'ASI-Code System Metrics',
      panels: [
        this.createHealthPanel(),
        this.createPerformancePanel(),
        this.createResourcePanel(),
        this.createErrorPanel()
      ]
    };
  }
  
  private static createHealthPanel(): Panel {
    return {
      title: 'Component Health',
      type: 'stat',
      queries: [
        'asi_code_health{component="kenny"}',
        'asi_code_health{component="consciousness"}',
        'asi_code_health{component="provider"}'
      ],
      thresholds: [
        { value: 0, color: 'red' },
        { value: 1, color: 'green' }
      ]
    };
  }
  
  private static createPerformancePanel(): Panel {
    return {
      title: 'Performance Metrics',
      type: 'timeseries',
      queries: [
        'rate(asi_code_http_requests_total[5m])',
        'histogram_quantile(0.95, rate(asi_code_http_request_duration_seconds_bucket[5m]))'
      ]
    };
  }
}
```

## Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check memory usage
curl http://localhost:3000/metrics | grep memory

# Heap dump for analysis
kill -USR2 $(pgrep -f asi-code)

# Memory profiling
node --inspect=0.0.0.0:9229 dist/index.js
```

#### Slow Response Times

```bash
# Check response time metrics
curl http://localhost:3000/metrics | grep duration

# Enable detailed timing
DEBUG=asi-code:performance asi-code start

# Profile specific requests
curl -w "%{time_total}" http://localhost:3000/api/sessions
```

#### Provider Issues

```bash
# Check provider health
curl http://localhost:3000/api/providers

# Test provider connectivity
asi-code provider test anthropic --verbose

# Check provider metrics
curl http://localhost:3000/metrics | grep provider
```

### Debug Procedures

#### Performance Investigation

1. **Identify Bottleneck**
   ```bash
   # Check metrics
   curl http://localhost:3000/metrics | grep -E "(duration|rate)"
   
   # Check logs
   grep -i "slow\|timeout\|error" /var/log/asi-code/app.log
   ```

2. **Enable Profiling**
   ```bash
   # CPU profiling
   node --prof dist/index.js
   
   # Memory profiling
   node --inspect dist/index.js
   ```

3. **Analyze Results**
   ```bash
   # Process CPU profile
   node --prof-process isolate-*.log > profile.txt
   
   # Analyze in Chrome DevTools
   # Go to chrome://inspect
   ```

#### Error Investigation

1. **Check Error Logs**
   ```bash
   # Recent errors
   grep -i error /var/log/asi-code/app.log | tail -20
   
   # Error patterns
   grep -i error /var/log/asi-code/app.log | cut -d' ' -f5- | sort | uniq -c | sort -nr
   ```

2. **Correlation Analysis**
   ```bash
   # Find related events
   grep "correlation_id_123" /var/log/asi-code/app.log
   
   # Time-based analysis
   grep "2024-01-15T10:3" /var/log/asi-code/app.log
   ```

---

Effective monitoring and observability are crucial for maintaining reliable ASI-Code deployments. Use these guidelines to implement comprehensive monitoring that provides visibility into system health, performance, and user experience.