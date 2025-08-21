#!/bin/bash

# ASI-Code Security Hardening Script
# This script applies security hardening configurations for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KUBERNETES_DIR="$PROJECT_ROOT/k8s"

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
APPLY_KUBERNETES=${APPLY_KUBERNETES:-true}
APPLY_DOCKER=${APPLY_DOCKER:-true}
GENERATE_CERTS=${GENERATE_CERTS:-false}
SETUP_MONITORING=${SETUP_MONITORING:-true}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking security hardening prerequisites..."
    
    local missing_tools=()
    
    if [[ "$APPLY_KUBERNETES" == "true" ]]; then
        if ! command_exists kubectl; then
            missing_tools+=("kubectl")
        fi
        
        if ! command_exists helm; then
            missing_tools+=("helm")
        fi
    fi
    
    if [[ "$APPLY_DOCKER" == "true" ]]; then
        if ! command_exists docker; then
            missing_tools+=("docker")
        fi
    fi
    
    if [[ "$GENERATE_CERTS" == "true" ]]; then
        if ! command_exists openssl; then
            missing_tools+=("openssl")
        fi
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and run this script again."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to apply Kubernetes security policies
apply_kubernetes_security() {
    if [[ "$APPLY_KUBERNETES" != "true" ]]; then
        return
    fi
    
    print_status "Applying Kubernetes security hardening..."
    
    # Apply Pod Security Standards
    print_status "Applying Pod Security Standards..."
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: asi-code
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF
    
    # Apply Network Policies
    print_status "Applying Network Policies..."
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: asi-code-default-deny
  namespace: asi-code
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: asi-code-allow-ingress
  namespace: asi-code
spec:
  podSelector:
    matchLabels:
      app: asi-code
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: asi-code-allow-database
  namespace: asi-code
spec:
  podSelector:
    matchLabels:
      app: asi-code
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          component: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          component: cache
    ports:
    - protocol: TCP
      port: 6379
EOF
    
    # Apply Security Context Constraints
    print_status "Applying Security Contexts..."
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: SecurityContextConstraints
metadata:
  name: asi-code-scc
allowHostDirVolumePlugin: false
allowHostIPC: false
allowHostNetwork: false
allowHostPID: false
allowHostPorts: false
allowPrivilegeEscalation: false
allowPrivilegedContainer: false
allowedCapabilities: []
defaultAddCapabilities: []
requiredDropCapabilities:
- ALL
fsGroup:
  type: MustRunAs
  ranges:
  - min: 1001
    max: 1001
runAsUser:
  type: MustRunAs
  uid: 1001
seLinuxContext:
  type: MustRunAs
supplementalGroups:
  type: MustRunAs
  ranges:
  - min: 1001
    max: 1001
readOnlyRootFilesystem: true
volumes:
- configMap
- downwardAPI
- emptyDir
- persistentVolumeClaim
- projected
- secret
EOF
    
    # Apply Resource Quotas
    print_status "Applying Resource Quotas..."
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: asi-code-quota
  namespace: asi-code
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "20"
    persistentvolumeclaims: "10"
    services: "10"
    secrets: "20"
    configmaps: "20"
EOF
    
    # Apply Limit Ranges
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: LimitRange
metadata:
  name: asi-code-limits
  namespace: asi-code
spec:
  limits:
  - default:
      cpu: "500m"
      memory: "1Gi"
    defaultRequest:
      cpu: "100m"
      memory: "256Mi"
    type: Container
  - max:
      cpu: "2"
      memory: "4Gi"
    min:
      cpu: "50m"
      memory: "128Mi"
    type: Container
EOF
    
    print_success "Kubernetes security hardening applied"
}

# Function to apply Docker security hardening
apply_docker_security() {
    if [[ "$APPLY_DOCKER" != "true" ]]; then
        return
    fi
    
    print_status "Applying Docker security hardening..."
    
    # Create Docker daemon configuration
    print_status "Configuring Docker daemon security..."
    cat <<EOF > /tmp/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false,
  "icc": false,
  "userns-remap": "default",
  "no-new-privileges": true,
  "selinux-enabled": true,
  "disable-legacy-registry": true,
  "experimental": false,
  "metrics-addr": "127.0.0.1:9323",
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}
EOF
    
    # Apply Docker security scanning
    print_status "Setting up Docker security scanning..."
    cat <<'EOF' > /tmp/docker-security-scan.sh
#!/bin/bash
# Docker security scanning script

IMAGES=(
    "asi-code:latest"
    "postgres:16-alpine"
    "redis:7-alpine"
    "nginx:alpine"
    "prometheus/prometheus:latest"
    "grafana/grafana:latest"
)

for image in "${IMAGES[@]}"; do
    echo "Scanning image: $image"
    
    # Trivy scan
    if command -v trivy >/dev/null 2>&1; then
        trivy image --severity HIGH,CRITICAL "$image"
    fi
    
    # Docker Scout scan (if available)
    if docker scout version >/dev/null 2>&1; then
        docker scout cves "$image"
    fi
done
EOF
    
    chmod +x /tmp/docker-security-scan.sh
    
    print_success "Docker security hardening configured"
}

# Function to generate SSL certificates
generate_ssl_certificates() {
    if [[ "$GENERATE_CERTS" != "true" ]]; then
        return
    fi
    
    print_status "Generating SSL certificates..."
    
    SSL_DIR="$PROJECT_ROOT/ssl"
    mkdir -p "$SSL_DIR"
    
    # Generate CA certificate
    print_status "Generating Certificate Authority..."
    openssl genrsa -out "$SSL_DIR/ca-key.pem" 4096
    openssl req -new -x509 -days 3650 -key "$SSL_DIR/ca-key.pem" -out "$SSL_DIR/ca-cert.pem" \
        -subj "/C=US/ST=State/L=City/O=ASI-Code/CN=ASI-Code CA"
    
    # Generate server certificate
    print_status "Generating server certificate..."
    openssl genrsa -out "$SSL_DIR/server-key.pem" 4096
    openssl req -new -key "$SSL_DIR/server-key.pem" -out "$SSL_DIR/server-csr.pem" \
        -subj "/C=US/ST=State/L=City/O=ASI-Code/CN=asi-code.company.com"
    
    # Create certificate extensions
    cat > "$SSL_DIR/server-ext.cnf" <<EOF
subjectAltName = @alt_names
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = asi-code.company.com
DNS.2 = api.asi-code.company.com
DNS.3 = www.asi-code.company.com
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF
    
    # Sign server certificate
    openssl x509 -req -days 365 -in "$SSL_DIR/server-csr.pem" \
        -CA "$SSL_DIR/ca-cert.pem" -CAkey "$SSL_DIR/ca-key.pem" \
        -out "$SSL_DIR/server-cert.pem" -extensions v3_req \
        -extfile "$SSL_DIR/server-ext.cnf" -CAcreateserial
    
    # Set proper permissions
    chmod 600 "$SSL_DIR"/*.pem
    chmod 644 "$SSL_DIR"/*-cert.pem
    
    print_success "SSL certificates generated"
}

# Function to setup security monitoring
setup_security_monitoring() {
    if [[ "$SETUP_MONITORING" != "true" ]]; then
        return
    fi
    
    print_status "Setting up security monitoring..."
    
    # Create Falco security monitoring rules
    cat <<'EOF' > /tmp/falco-rules.yaml
- rule: Detect Shell in Container
  desc: Detect shell being spawned in a container
  condition: >
    spawned_process and container and
    (proc.name in (bash, sh, zsh, csh, ksh, ash) or
     proc.pname in (bash, sh, zsh, csh, ksh, ash))
  output: >
    Shell spawned in container (user=%user.name container_id=%container.id
    image=%container.image.repository:%container.image.tag proc=%proc.name
    pproc=%proc.pname gparent=%proc.aname[2] ggparent=%proc.aname[3])
  priority: WARNING
  tags: [container, shell]

- rule: Detect Privilege Escalation
  desc: Detect privilege escalation attempts
  condition: >
    spawned_process and container and
    (proc.name in (sudo, su, doas) or
     proc.args contains "chmod +s")
  output: >
    Privilege escalation detected (user=%user.name container_id=%container.id
    image=%container.image.repository:%container.image.tag proc=%proc.name
    args=%proc.args)
  priority: CRITICAL
  tags: [container, privilege_escalation]

- rule: Detect Network Activity by Unexpected Process
  desc: Detect network activity by processes that shouldn't normally do networking
  condition: >
    (inbound_outbound) and container and
    not proc.name in (asi-code, node, bun, nginx, postgres, redis-server)
  output: >
    Unexpected network activity (user=%user.name container_id=%container.id
    image=%container.image.repository:%container.image.tag proc=%proc.name
    direction=%evt.type)
  priority: WARNING
  tags: [container, network]
EOF
    
    # Create security monitoring alerts
    cat <<'EOF' > /tmp/security-alerts.yaml
groups:
- name: security
  rules:
  - alert: ContainerPrivilegeEscalation
    expr: increase(falco_events{rule_name="Detect Privilege Escalation"}[5m]) > 0
    labels:
      severity: critical
    annotations:
      summary: "Container privilege escalation detected"
      
  - alert: ShellInContainer
    expr: increase(falco_events{rule_name="Detect Shell in Container"}[5m]) > 0
    labels:
      severity: warning
    annotations:
      summary: "Shell detected in container"
      
  - alert: UnauthorizedNetworkActivity
    expr: increase(falco_events{rule_name="Detect Network Activity by Unexpected Process"}[5m]) > 0
    labels:
      severity: warning
    annotations:
      summary: "Unauthorized network activity detected"
      
  - alert: HighFailedLoginAttempts
    expr: rate(asi_code_failed_logins_total[5m]) > 0.5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High rate of failed login attempts"
      
  - alert: SuspiciousAPIActivity
    expr: rate(asi_code_http_requests_total{status=~"4.."}[5m]) > 10
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Suspicious API activity detected"
EOF
    
    print_success "Security monitoring configured"
}

# Function to apply file system security
apply_filesystem_security() {
    print_status "Applying filesystem security..."
    
    # Set secure permissions for configuration files
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        chmod 600 "$PROJECT_ROOT/.env"
        print_status "Secured .env file permissions"
    fi
    
    # Secure SSL directory
    if [[ -d "$PROJECT_ROOT/ssl" ]]; then
        chmod 700 "$PROJECT_ROOT/ssl"
        chmod 600 "$PROJECT_ROOT/ssl"/*.pem 2>/dev/null || true
        chmod 644 "$PROJECT_ROOT/ssl"/*-cert.pem 2>/dev/null || true
        print_status "Secured SSL directory permissions"
    fi
    
    # Secure log directory
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        chmod 755 "$PROJECT_ROOT/logs"
        print_status "Secured logs directory permissions"
    fi
    
    # Create security audit script
    cat <<'EOF' > /tmp/security-audit.sh
#!/bin/bash
# Security audit script for ASI-Code

echo "=== ASI-Code Security Audit ==="
echo "Date: $(date)"
echo

echo "1. File Permissions Audit:"
find . -type f -perm /o+w -not -path "./node_modules/*" -not -path "./.git/*" | head -20
echo

echo "2. Environment Variables Check:"
if [[ -f .env ]]; then
    echo "✓ .env file exists"
    ls -la .env
else
    echo "✗ .env file not found"
fi
echo

echo "3. SSL Certificate Check:"
if [[ -d ssl ]]; then
    echo "✓ SSL directory exists"
    ls -la ssl/
else
    echo "✗ SSL directory not found"
fi
echo

echo "4. Dependency Vulnerabilities:"
if command -v npm >/dev/null 2>&1; then
    npm audit --audit-level=moderate || true
fi
echo

echo "5. Docker Image Security:"
if command -v docker >/dev/null 2>&1; then
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "(asi-code|postgres|redis|nginx)"
fi
echo

echo "=== Security Audit Complete ==="
EOF
    
    chmod +x /tmp/security-audit.sh
    
    print_success "Filesystem security applied"
}

# Function to create security documentation
create_security_documentation() {
    print_status "Creating security documentation..."
    
    SECURITY_DIR="$PROJECT_ROOT/security"
    mkdir -p "$SECURITY_DIR"
    
    # Create security checklist
    cat <<'EOF' > "$SECURITY_DIR/security-checklist.md"
# ASI-Code Security Checklist

## Pre-deployment Security Checklist

### Authentication & Authorization
- [ ] JWT secrets are strong and unique
- [ ] API keys are properly configured
- [ ] RBAC is properly configured in Kubernetes
- [ ] Service accounts have minimal permissions

### Network Security
- [ ] Network policies are applied
- [ ] Ingress is properly configured with TLS
- [ ] Internal services are not exposed publicly
- [ ] Load balancer security groups are configured

### Data Protection
- [ ] Database passwords are strong and encrypted
- [ ] Data at rest encryption is enabled
- [ ] Data in transit encryption is enabled
- [ ] Backup encryption is configured

### Container Security
- [ ] Containers run as non-root user
- [ ] Read-only root filesystem is enabled
- [ ] Resource limits are set
- [ ] Security contexts are applied
- [ ] Images are scanned for vulnerabilities

### Monitoring & Logging
- [ ] Security monitoring is enabled
- [ ] Audit logging is configured
- [ ] Alert rules are set up
- [ ] Log retention policies are configured

### Compliance
- [ ] Security policies are documented
- [ ] Incident response procedures are in place
- [ ] Regular security reviews are scheduled
- [ ] Compliance requirements are met

## Post-deployment Security Checklist

### Operational Security
- [ ] Regular security scans are performed
- [ ] Secrets are rotated regularly
- [ ] Access reviews are conducted
- [ ] Security patches are applied

### Monitoring
- [ ] Security dashboards are functional
- [ ] Alerts are being received
- [ ] Log aggregation is working
- [ ] Incident response is tested

### Maintenance
- [ ] Documentation is up to date
- [ ] Security training is current
- [ ] Backup and recovery is tested
- [ ] Disaster recovery procedures are validated
EOF
    
    print_success "Security documentation created"
}

# Function to run security validation
run_security_validation() {
    print_status "Running security validation..."
    
    local validation_failed=false
    
    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        print_error "Environment file not found"
        validation_failed=true
    elif [[ $(stat -c "%a" "$PROJECT_ROOT/.env") != "600" ]]; then
        print_error "Environment file has incorrect permissions"
        validation_failed=true
    fi
    
    # Check SSL certificates (if they should exist)
    if [[ "$GENERATE_CERTS" == "true" ]]; then
        if [[ ! -f "$PROJECT_ROOT/ssl/server-cert.pem" ]]; then
            print_error "SSL certificate not found"
            validation_failed=true
        fi
    fi
    
    # Validate Kubernetes manifests
    if [[ "$APPLY_KUBERNETES" == "true" ]] && command_exists kubectl; then
        print_status "Validating Kubernetes manifests..."
        for manifest in "$KUBERNETES_DIR"/*.yaml; do
            if ! kubectl --dry-run=client apply -f "$manifest" >/dev/null 2>&1; then
                print_error "Invalid Kubernetes manifest: $(basename "$manifest")"
                validation_failed=true
            fi
        done
    fi
    
    if [[ "$validation_failed" == "true" ]]; then
        print_error "Security validation failed"
        exit 1
    else
        print_success "Security validation passed"
    fi
}

# Function to display security summary
display_security_summary() {
    print_status "Security Hardening Summary:"
    echo "=================================="
    echo "Environment: $ENVIRONMENT"
    echo "Kubernetes Security: $([ "$APPLY_KUBERNETES" == "true" ] && echo "Applied" || echo "Skipped")"
    echo "Docker Security: $([ "$APPLY_DOCKER" == "true" ] && echo "Applied" || echo "Skipped")"
    echo "SSL Certificates: $([ "$GENERATE_CERTS" == "true" ] && echo "Generated" || echo "Skipped")"
    echo "Security Monitoring: $([ "$SETUP_MONITORING" == "true" ] && echo "Configured" || echo "Skipped")"
    echo "=================================="
    echo
    print_success "Security hardening completed!"
    echo
    print_status "Next steps:"
    echo "1. Review security configurations"
    echo "2. Run security audit: ./scripts/security-audit.sh"
    echo "3. Test security controls"
    echo "4. Document any customizations"
    echo "5. Schedule regular security reviews"
}

# Main function
main() {
    echo "ASI-Code Security Hardening Script"
    echo "==================================="
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --skip-kubernetes)
                APPLY_KUBERNETES=false
                shift
                ;;
            --skip-docker)
                APPLY_DOCKER=false
                shift
                ;;
            --generate-certs)
                GENERATE_CERTS=true
                shift
                ;;
            --skip-monitoring)
                SETUP_MONITORING=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --environment ENV    Set environment (development, staging, production)"
                echo "  --skip-kubernetes    Skip Kubernetes security hardening"
                echo "  --skip-docker        Skip Docker security hardening"
                echo "  --generate-certs     Generate SSL certificates"
                echo "  --skip-monitoring    Skip security monitoring setup"
                echo "  --help               Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    print_status "Hardening ASI-Code security for $ENVIRONMENT environment..."
    echo
    
    # Run hardening steps
    check_prerequisites
    apply_kubernetes_security
    apply_docker_security
    generate_ssl_certificates
    setup_security_monitoring
    apply_filesystem_security
    create_security_documentation
    run_security_validation
    display_security_summary
}

# Run main function with all arguments
main "$@"