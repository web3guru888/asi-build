# ASI-Code Operational Runbooks

## Overview

This document contains operational runbooks for managing ASI-Code in production. These runbooks provide step-by-step procedures for common operational tasks, incident response, and troubleshooting.

## Table of Contents

1. [General Operations](#general-operations)
2. [Incident Response](#incident-response)
3. [Performance Issues](#performance-issues)
4. [Security Incidents](#security-incidents)
5. [Database Operations](#database-operations)
6. [Application Maintenance](#application-maintenance)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Backup and Recovery](#backup-and-recovery)

## General Operations

### Application Deployment

#### Standard Deployment Process

**Purpose**: Deploy a new version of ASI-Code to production

**Prerequisites**:
- New version tested in staging
- Database migrations (if any) tested
- Rollback plan prepared

**Steps**:
1. **Pre-deployment checks**
   ```bash
   # Check current application status
   kubectl get pods -n asi-code
   kubectl get deployment asi-code -n asi-code
   
   # Check resource usage
   kubectl top pods -n asi-code
   kubectl top nodes
   ```

2. **Deploy new version**
   ```bash
   # Update deployment image
   kubectl set image deployment/asi-code asi-code=ghcr.io/company/asi-code:v1.2.0 -n asi-code
   
   # Monitor rollout
   kubectl rollout status deployment/asi-code -n asi-code --timeout=600s
   ```

3. **Post-deployment verification**
   ```bash
   # Check pod status
   kubectl get pods -n asi-code -l app=asi-code
   
   # Test health endpoint
   curl -f https://asi-code.company.com/health
   
   # Check logs for errors
   kubectl logs -f deployment/asi-code -n asi-code --since=5m
   ```

4. **Rollback if needed**
   ```bash
   # Rollback to previous version
   kubectl rollout undo deployment/asi-code -n asi-code
   
   # Monitor rollback
   kubectl rollout status deployment/asi-code -n asi-code
   ```

#### Emergency Deployment

**Purpose**: Deploy critical fixes outside normal deployment windows

**Steps**:
1. **Assess criticality**
   - Confirm emergency status with incident commander
   - Document reason for emergency deployment

2. **Fast-track deployment**
   ```bash
   # Skip staging if confirmed emergency
   kubectl set image deployment/asi-code asi-code=ghcr.io/company/asi-code:hotfix-123 -n asi-code
   
   # Monitor closely
   watch kubectl get pods -n asi-code
   ```

3. **Immediate verification**
   ```bash
   # Test critical functionality
   curl -f https://asi-code.company.com/health
   curl -f https://asi-code.company.com/health
   
   # Check error rates
   # (Prometheus query in Grafana)
   ```

### Scaling Operations

#### Manual Scaling

**Purpose**: Manually scale application replicas based on load

**When to use**:
- Anticipated traffic spikes
- Performance degradation
- Maintenance operations

**Steps**:
1. **Current status check**
   ```bash
   kubectl get hpa -n asi-code
   kubectl get deployment asi-code -n asi-code
   ```

2. **Scale replicas**
   ```bash
   # Scale to desired number of replicas
   kubectl scale deployment asi-code --replicas=10 -n asi-code
   
   # Monitor scaling
   kubectl rollout status deployment/asi-code -n asi-code
   ```

3. **Verify scaling**
   ```bash
   # Check all pods are running
   kubectl get pods -n asi-code -l app=asi-code
   
   # Verify load distribution
   kubectl top pods -n asi-code
   ```

#### Auto-scaling Configuration

**Purpose**: Update HPA settings based on performance requirements

**Steps**:
1. **Review current HPA**
   ```bash
   kubectl describe hpa asi-code-hpa -n asi-code
   ```

2. **Update HPA configuration**
   ```bash
   kubectl patch hpa asi-code-hpa -n asi-code --patch='
   spec:
     minReplicas: 5
     maxReplicas: 25
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 60
   '
   ```

3. **Monitor HPA behavior**
   ```bash
   kubectl get hpa -w -n asi-code
   ```

## Incident Response

### Application Down

**Symptoms**:
- Health check failures
- 5xx errors from load balancer
- No response from application

**Immediate Actions**:
1. **Assess scope**
   ```bash
   # Check all pods
   kubectl get pods -n asi-code
   
   # Check events
   kubectl get events -n asi-code --sort-by='.lastTimestamp' | tail -20
   
   # Check ingress
   kubectl get ingress -n asi-code
   ```

2. **Check dependencies**
   ```bash
   # Database connectivity
   kubectl exec deployment/asi-code -n asi-code -- pg_isready -h postgres -U asicode
   
   # Redis connectivity
   kubectl exec deployment/asi-code -n asi-code -- redis-cli -h redis ping
   
   # External API connectivity
   kubectl exec deployment/asi-code -n asi-code -- curl -I https://api.anthropic.com
   ```

3. **Quick fixes**
   ```bash
   # Restart pods if needed
   kubectl rollout restart deployment/asi-code -n asi-code
   
   # Scale up if resource constrained
   kubectl scale deployment asi-code --replicas=6 -n asi-code
   ```

**Investigation**:
1. **Analyze logs**
   ```bash
   # Application logs
   kubectl logs deployment/asi-code -n asi-code --since=30m | grep -E "(ERROR|FATAL)"
   
   # Database logs
   kubectl logs deployment/postgres -n asi-code --since=30m
   
   # Ingress logs
   kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
   ```

2. **Check metrics**
   - CPU/Memory usage in Grafana
   - Request rates and error rates
   - Database connection pool status

3. **Root cause analysis**
   - Review recent deployments
   - Check configuration changes
   - Analyze error patterns

### High Error Rate

**Symptoms**:
- Increased 5xx responses
- Application errors in logs
- User complaints

**Immediate Actions**:
1. **Identify error patterns**
   ```bash
   # Check error rates by endpoint
   kubectl logs deployment/asi-code -n asi-code --since=10m | \
     grep -E "HTTP.*[45][0-9][0-9]" | \
     awk '{print $7}' | sort | uniq -c | sort -nr
   
   # Check error types
   kubectl logs deployment/asi-code -n asi-code --since=10m | grep ERROR
   ```

2. **Check system health**
   ```bash
   # Resource usage
   kubectl top pods -n asi-code
   
   # Database performance
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT pid, query, state, query_start FROM pg_stat_activity WHERE state != 'idle';"
   ```

3. **Temporary mitigation**
   ```bash
   # Increase resources if needed
   kubectl patch deployment asi-code -n asi-code --patch='
   spec:
     template:
       spec:
         containers:
         - name: asi-code
           resources:
             limits:
               cpu: "4000m"
               memory: "8Gi"
   '
   
   # Scale up replicas
   kubectl scale deployment asi-code --replicas=8 -n asi-code
   ```

### Database Connection Issues

**Symptoms**:
- Connection timeouts
- "too many connections" errors
- Slow database queries

**Immediate Actions**:
1. **Check database status**
   ```bash
   # Database pods
   kubectl get pods -n asi-code -l component=database
   
   # Connection count
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Long-running queries
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"
   ```

2. **Kill problematic connections**
   ```bash
   # Kill long-running queries
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes';"
   ```

3. **Scale database if needed**
   ```bash
   # Increase database resources
   kubectl patch statefulset postgres -n asi-code --patch='
   spec:
     template:
       spec:
         containers:
         - name: postgres
           resources:
             limits:
               cpu: "4000m"
               memory: "8Gi"
   '
   ```

### Memory Issues

**Symptoms**:
- OutOfMemory (OOM) kills
- High memory usage alerts
- Slow response times

**Immediate Actions**:
1. **Check memory usage**
   ```bash
   # Pod memory usage
   kubectl top pods -n asi-code
   
   # Node memory usage
   kubectl top nodes
   
   # Describe pod for OOM events
   kubectl describe pod -n asi-code -l app=asi-code
   ```

2. **Increase memory limits**
   ```bash
   kubectl patch deployment asi-code -n asi-code --patch='
   spec:
     template:
       spec:
         containers:
         - name: asi-code
           resources:
             limits:
               memory: "6Gi"
             requests:
               memory: "2Gi"
   '
   ```

3. **Force garbage collection**
   ```bash
   # Connect to application and trigger GC
   kubectl exec deployment/asi-code -n asi-code -- \
     node -e "global.gc && global.gc(); console.log('GC triggered');"
   ```

## Performance Issues

### High CPU Usage

**Investigation Steps**:
1. **Identify CPU hotspots**
   ```bash
   # Check CPU usage by pod
   kubectl top pods -n asi-code --sort-by=cpu
   
   # Profile application if needed
   kubectl exec -it deployment/asi-code -n asi-code -- \
     node --prof --prof-process app.js
   ```

2. **Check for CPU-intensive operations**
   ```bash
   # Look for compute-heavy operations in logs
   kubectl logs deployment/asi-code -n asi-code --since=30m | \
     grep -E "(processing|computation|analysis)"
   ```

3. **Scale horizontally**
   ```bash
   kubectl scale deployment asi-code --replicas=6 -n asi-code
   ```

### Slow Response Times

**Investigation Steps**:
1. **Check response time metrics**
   - Review Grafana dashboards
   - Check P95/P99 response times
   - Identify slow endpoints

2. **Database performance**
   ```bash
   # Check slow queries
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```

3. **Cache performance**
   ```bash
   # Redis hit ratio
   kubectl exec deployment/redis -n asi-code -- redis-cli info stats | grep hit
   ```

4. **Network latency**
   ```bash
   # Check network connectivity
   kubectl exec deployment/asi-code -n asi-code -- \
     curl -w "@/dev/stdout" -o /dev/null -s "https://api.anthropic.com" | \
     grep time_total
   ```

## Security Incidents

### Suspected Breach

**Immediate Actions**:
1. **Isolate affected systems**
   ```bash
   # Scale down to minimum replicas
   kubectl scale deployment asi-code --replicas=1 -n asi-code
   
   # Apply restrictive network policy
   kubectl apply -f - <<EOF
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: lockdown
     namespace: asi-code
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   EOF
   ```

2. **Collect evidence**
   ```bash
   # Export logs
   kubectl logs deployment/asi-code -n asi-code --since=24h > incident-logs.txt
   
   # Export pod descriptions
   kubectl describe pods -n asi-code > incident-pods.txt
   
   # Export events
   kubectl get events -n asi-code --sort-by='.lastTimestamp' > incident-events.txt
   ```

3. **Change credentials**
   ```bash
   # Rotate database password
   ./scripts/rotate-secrets.sh database
   
   # Rotate JWT secret
   ./scripts/rotate-secrets.sh jwt
   
   # Revoke API keys
   # (Manual process with providers)
   ```

### Unauthorized Access Attempts

**Investigation Steps**:
1. **Check access logs**
   ```bash
   # Failed authentication attempts
   kubectl logs deployment/asi-code -n asi-code | \
     grep -E "(401|403|authentication failed)"
   
   # Unusual access patterns
   kubectl logs deployment/asi-code -n asi-code | \
     grep -E "suspicious|blocked|rate.limit"
   ```

2. **Update security policies**
   ```bash
   # Temporarily tighten rate limits
   kubectl patch ingress asi-code-ingress -n asi-code --patch='
   metadata:
     annotations:
       nginx.ingress.kubernetes.io/rate-limit: "10"
       nginx.ingress.kubernetes.io/rate-limit-connections: "5"
   '
   ```

3. **Block malicious IPs**
   ```bash
   # Update ingress with IP blocklist
   kubectl patch ingress asi-code-ingress -n asi-code --patch='
   metadata:
     annotations:
       nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
   '
   ```

## Database Operations

### Database Maintenance

#### Vacuum and Reindex

**Purpose**: Maintain database performance and reclaim space

**Schedule**: Weekly during low-traffic hours

**Steps**:
1. **Check database size and fragmentation**
   ```bash
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "SELECT schemaname,tablename,attname,n_distinct,correlation FROM pg_stats;"
   ```

2. **Perform maintenance**
   ```bash
   # Vacuum analyze
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "VACUUM ANALYZE;"
   
   # Reindex if needed
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "REINDEX DATABASE asicode;"
   ```

3. **Update statistics**
   ```bash
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -c "ANALYZE;"
   ```

#### Database Backup Verification

**Purpose**: Ensure backups are valid and restorable

**Steps**:
1. **List recent backups**
   ```bash
   kubectl exec deployment/postgres -n asi-code -- \
     ls -la /backup/ | head -10
   ```

2. **Test restore process**
   ```bash
   # Create test database
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U postgres -c "CREATE DATABASE asicode_test;"
   
   # Restore latest backup
   kubectl exec deployment/postgres -n asi-code -- \
     pg_restore -U postgres -d asicode_test /backup/latest.sql
   
   # Verify restore
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U postgres -d asicode_test -c "SELECT COUNT(*) FROM sessions;"
   
   # Cleanup
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U postgres -c "DROP DATABASE asicode_test;"
   ```

### Database Recovery

#### Point-in-Time Recovery

**Purpose**: Recover database to specific point in time

**Prerequisites**:
- Valid backup before desired recovery point
- WAL logs available

**Steps**:
1. **Stop application**
   ```bash
   kubectl scale deployment asi-code --replicas=0 -n asi-code
   ```

2. **Create recovery instance**
   ```bash
   # Create new postgres instance for recovery
   kubectl apply -f - <<EOF
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: postgres-recovery
     namespace: asi-code
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: postgres-recovery
     template:
       metadata:
         labels:
           app: postgres-recovery
       spec:
         containers:
         - name: postgres
           image: postgres:16-alpine
           env:
           - name: POSTGRES_DB
             value: asicode
           - name: POSTGRES_USER
             value: asicode
           - name: POSTGRES_PASSWORD
             valueFrom:
               secretKeyRef:
                 name: asi-code-secrets
                 key: POSTGRES_PASSWORD
   EOF
   ```

3. **Restore from backup**
   ```bash
   # Copy backup to recovery instance
   kubectl cp backup.sql asi-code/postgres-recovery-pod:/tmp/
   
   # Restore database
   kubectl exec deployment/postgres-recovery -n asi-code -- \
     psql -U postgres -c "DROP DATABASE IF EXISTS asicode;"
   kubectl exec deployment/postgres-recovery -n asi-code -- \
     psql -U postgres -c "CREATE DATABASE asicode OWNER asicode;"
   kubectl exec deployment/postgres-recovery -n asi-code -- \
     psql -U asicode -d asicode -f /tmp/backup.sql
   ```

4. **Validate recovery**
   ```bash
   # Check data integrity
   kubectl exec deployment/postgres-recovery -n asi-code -- \
     psql -U asicode -c "SELECT COUNT(*) FROM sessions;"
   
   # Test application connectivity
   kubectl scale deployment asi-code --replicas=1 -n asi-code
   ```

## Application Maintenance

### Log Management

#### Log Rotation

**Purpose**: Manage log file sizes and disk usage

**Steps**:
1. **Check current log sizes**
   ```bash
   kubectl exec deployment/asi-code -n asi-code -- \
     du -sh /app/logs/*
   ```

2. **Rotate logs manually if needed**
   ```bash
   kubectl exec deployment/asi-code -n asi-code -- \
     bash -c 'cd /app/logs && for log in *.log; do mv "$log" "$log.$(date +%Y%m%d)"; done'
   
   # Restart application to create new log files
   kubectl rollout restart deployment/asi-code -n asi-code
   ```

3. **Cleanup old logs**
   ```bash
   kubectl exec deployment/asi-code -n asi-code -- \
     find /app/logs -name "*.log.*" -mtime +7 -delete
   ```

#### Log Analysis

**Purpose**: Analyze application logs for issues and patterns

**Steps**:
1. **Extract recent errors**
   ```bash
   kubectl logs deployment/asi-code -n asi-code --since=1h | \
     grep -E "(ERROR|FATAL)" | \
     sort | uniq -c | sort -rn
   ```

2. **Analyze performance logs**
   ```bash
   kubectl logs deployment/asi-code -n asi-code --since=1h | \
     grep "response_time" | \
     awk '{print $NF}' | \
     sort -n | tail -20
   ```

3. **Check for memory leaks**
   ```bash
   kubectl logs deployment/asi-code -n asi-code --since=6h | \
     grep "memory" | \
     grep -oE "[0-9]+MB"
   ```

### Configuration Management

#### Update Application Configuration

**Purpose**: Update application configuration without full deployment

**Steps**:
1. **Update ConfigMap**
   ```bash
   # Edit configuration
   kubectl edit configmap asi-code-config -n asi-code
   
   # Or apply new configuration file
   kubectl apply -f k8s/configmap.yaml
   ```

2. **Restart pods to pick up changes**
   ```bash
   kubectl rollout restart deployment/asi-code -n asi-code
   
   # Wait for rollout
   kubectl rollout status deployment/asi-code -n asi-code
   ```

3. **Verify configuration**
   ```bash
   # Check if new config is loaded
   kubectl exec deployment/asi-code -n asi-code -- \
     cat /app/config/production.yml | grep -A 5 "updated_setting"
   ```

#### Secret Rotation

**Purpose**: Regularly rotate sensitive credentials

**Steps**:
1. **Database password rotation**
   ```bash
   # Generate new password
   NEW_PASSWORD=$(openssl rand -base64 32)
   
   # Update database user
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U postgres -c "ALTER USER asicode PASSWORD '$NEW_PASSWORD';"
   
   # Update Kubernetes secret
   kubectl patch secret asi-code-secrets -n asi-code --patch="{
     \"data\": {
       \"POSTGRES_PASSWORD\": \"$(echo -n $NEW_PASSWORD | base64)\"
     }
   }"
   
   # Restart application
   kubectl rollout restart deployment/asi-code -n asi-code
   ```

2. **JWT secret rotation**
   ```bash
   # Generate new JWT secret
   NEW_JWT_SECRET=$(openssl rand -base64 32)
   
   # Update Kubernetes secret
   kubectl patch secret asi-code-secrets -n asi-code --patch="{
     \"data\": {
       \"JWT_SECRET\": \"$(echo -n $NEW_JWT_SECRET | base64)\"
     }
   }"
   
   # Restart application (this will invalidate existing sessions)
   kubectl rollout restart deployment/asi-code -n asi-code
   ```

## Monitoring and Alerting

### Alert Management

#### Acknowledge Alerts

**Purpose**: Acknowledge alerts during investigation

**Steps**:
1. **Check active alerts**
   ```bash
   # List active alerts in Prometheus
   curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/alerts
   ```

2. **Acknowledge in AlertManager**
   ```bash
   # Silence alert for 1 hour
   curl -X POST http://alertmanager.monitoring.svc.cluster.local:9093/api/v1/silences \
     -H "Content-Type: application/json" \
     -d '{
       "matchers": [
         {"name": "alertname", "value": "ASICodeHighErrorRate"}
       ],
       "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
       "endsAt": "'$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%S.000Z)'",
       "comment": "Investigating high error rate",
       "createdBy": "oncall-engineer"
     }'
   ```

#### Update Alert Rules

**Purpose**: Modify alert thresholds based on operational experience

**Steps**:
1. **Edit alert rules**
   ```bash
   kubectl edit configmap prometheus-rules -n monitoring
   ```

2. **Reload Prometheus configuration**
   ```bash
   curl -X POST http://prometheus.monitoring.svc.cluster.local:9090/-/reload
   ```

### Metrics Analysis

#### Custom Metrics Queries

**Common Prometheus queries for ASI-Code**:

```promql
# Request rate
rate(asi_code_http_requests_total[5m])

# Error rate
rate(asi_code_http_requests_total{status=~"5.."}[5m]) / rate(asi_code_http_requests_total[5m])

# Response time percentiles
histogram_quantile(0.95, rate(asi_code_http_request_duration_seconds_bucket[5m]))

# Memory usage
asi_code_process_resident_memory_bytes / 1024 / 1024

# Active sessions
asi_code_active_sessions_total

# Database connections
pg_stat_database_numbackends{datname="asicode"}
```

## Backup and Recovery

### Emergency Recovery

#### Complete System Recovery

**Purpose**: Recover entire ASI-Code system from backup

**Prerequisites**:
- Recent database backup
- Application configuration backup
- Container images available

**Steps**:
1. **Deploy fresh infrastructure**
   ```bash
   # Deploy clean Kubernetes manifests
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/rbac.yaml
   kubectl apply -f k8s/pv.yaml
   ```

2. **Restore database**
   ```bash
   # Deploy PostgreSQL
   kubectl apply -f k8s/postgres.yaml
   kubectl wait --for=condition=ready pod -l component=database -n asi-code --timeout=300s
   
   # Restore from backup
   kubectl cp backup.sql asi-code/postgres-pod:/tmp/
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U postgres -c "CREATE DATABASE asicode OWNER asicode;"
   kubectl exec deployment/postgres -n asi-code -- \
     psql -U asicode -d asicode -f /tmp/backup.sql
   ```

3. **Deploy application**
   ```bash
   # Apply configuration and secrets
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/configmap.yaml
   
   # Deploy application
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/ingress.yaml
   
   # Wait for application to be ready
   kubectl rollout status deployment/asi-code -n asi-code
   ```

4. **Verify recovery**
   ```bash
   # Test health endpoint
   curl -f https://asi-code.company.com/health
   
   # Test functionality
   curl -f https://asi-code.company.com/health
   
   # Check logs
   kubectl logs deployment/asi-code -n asi-code
   ```

## Conclusion

These runbooks provide standardized procedures for operating ASI-Code in production. They should be:

- **Regularly tested** through chaos engineering and drills
- **Updated** as the system evolves
- **Accessible** to all on-call engineers
- **Reviewed** after each incident for improvements

Keep these runbooks current and ensure all team members are familiar with the procedures. Regular practice of these procedures during non-incident times builds confidence and reduces mean time to resolution (MTTR) during actual incidents.