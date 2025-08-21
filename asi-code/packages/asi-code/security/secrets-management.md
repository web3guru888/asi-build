# ASI-Code Secrets Management Guide

## Overview

This document provides comprehensive guidance on managing secrets for the ASI-Code application across different environments and deployment methods.

## Secret Types and Classification

### Classification Levels

#### Critical Secrets (Tier 1)
- Database passwords
- Encryption keys
- JWT signing keys
- Root API keys
- SSL/TLS private keys

**Rotation Frequency**: 90 days or immediately upon compromise

#### Sensitive Secrets (Tier 2)
- Service API keys
- Third-party integration tokens
- Redis passwords
- Monitoring credentials

**Rotation Frequency**: 180 days

#### Internal Secrets (Tier 3)
- Session secrets
- Internal service tokens
- Development credentials

**Rotation Frequency**: 365 days

## Secret Storage Solutions

### Production Environment

#### AWS Secrets Manager (Recommended)
```yaml
# Example Kubernetes secret provider class
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: asi-code-secrets
  namespace: asi-code
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "asi-code/database/password"
        objectType: "secretsmanager"
        jmesPath:
          - path: "password"
            objectAlias: "DATABASE_PASSWORD"
      - objectName: "asi-code/jwt/secret"
        objectType: "secretsmanager"
        jmesPath:
          - path: "secret"
            objectAlias: "JWT_SECRET"
```

#### HashiCorp Vault (Alternative)
```bash
# Store secrets in Vault
vault kv put secret/asi-code/database password=supersecret
vault kv put secret/asi-code/jwt secret=jwtsecret

# Create policy for ASI-Code
vault policy write asi-code-policy - <<EOF
path "secret/data/asi-code/*" {
  capabilities = ["read"]
}
EOF
```

#### Azure Key Vault (Azure)
```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: asi-code-secrets
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: "client-id"
    keyvaultName: "asi-code-kv"
    objects: |
      array:
        - |
          objectName: database-password
          objectType: secret
        - |
          objectName: jwt-secret
          objectType: secret
```

### Development/Staging Environment

#### Kubernetes Secrets (Acceptable for non-production)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: asi-code-secrets
  namespace: asi-code
type: Opaque
data:
  DATABASE_PASSWORD: <base64-encoded-password>
  JWT_SECRET: <base64-encoded-secret>
  REDIS_PASSWORD: <base64-encoded-password>
```

#### Docker Secrets
```bash
# Create secrets
echo "supersecret" | docker secret create db_password -
echo "jwtsecret" | docker secret create jwt_secret -

# Use in docker-compose
version: '3.8'
services:
  asi-code:
    image: asi-code:latest
    secrets:
      - db_password
      - jwt_secret
    environment:
      - DATABASE_PASSWORD_FILE=/run/secrets/db_password
      - JWT_SECRET_FILE=/run/secrets/jwt_secret

secrets:
  db_password:
    external: true
  jwt_secret:
    external: true
```

## Secret Generation

### Strong Password Generation
```bash
# Generate cryptographically secure passwords
openssl rand -base64 32

# Generate hex passwords
openssl rand -hex 32

# Using pwgen (if available)
pwgen -s 32 1

# Using Python
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for i in range(32)))"
```

### JWT Secret Generation
```bash
# Generate JWT secret (256-bit)
openssl rand -base64 32

# Generate with specific charset for JWT
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(64)))"
```

### Encryption Key Generation
```bash
# AES-256 key (32 bytes = 256 bits)
openssl rand -hex 32

# Using Node.js crypto
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Certificate Generation
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Generate CA and signed certificate
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem
openssl genrsa -out server-key.pem 4096
openssl req -new -key server-key.pem -out server-csr.pem
openssl x509 -req -days 365 -in server-csr.pem -CA ca-cert.pem -CAkey ca-key.pem -out server-cert.pem
```

## Secret Injection Methods

### Environment Variables (Not Recommended for Production)
```bash
# .env file (development only)
DATABASE_PASSWORD=supersecret
JWT_SECRET=jwtsecret
```

### File-based Secrets (Recommended)
```javascript
// Read secrets from files
const fs = require('fs');

const readSecret = (secretPath) => {
  try {
    return fs.readFileSync(secretPath, 'utf8').trim();
  } catch (error) {
    console.error(`Failed to read secret from ${secretPath}:`, error);
    process.exit(1);
  }
};

const databasePassword = readSecret('/run/secrets/database_password');
const jwtSecret = readSecret('/run/secrets/jwt_secret');
```

### Kubernetes Secrets CSI Driver
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asi-code
spec:
  template:
    spec:
      serviceAccountName: asi-code
      containers:
      - name: asi-code
        image: asi-code:latest
        volumeMounts:
        - name: secrets-store
          mountPath: "/mnt/secrets-store"
          readOnly: true
        env:
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: secrets-store
              key: DATABASE_PASSWORD
      volumes:
      - name: secrets-store
        csi:
          driver: secrets-store.csi.k8s.io
          readOnly: true
          volumeAttributes:
            secretProviderClass: "asi-code-secrets"
```

## Secret Rotation

### Automated Rotation Script
```bash
#!/bin/bash
# rotate-secrets.sh

set -euo pipefail

NAMESPACE="asi-code"
VAULT_ADDR="https://vault.company.com"

rotate_database_password() {
    echo "Rotating database password..."
    
    # Generate new password
    NEW_PASSWORD=$(openssl rand -base64 32)
    
    # Update in Vault
    vault kv put secret/asi-code/database password="$NEW_PASSWORD"
    
    # Update database
    kubectl exec -n "$NAMESPACE" deployment/postgres -- psql -U postgres -c "ALTER USER asicode PASSWORD '$NEW_PASSWORD';"
    
    # Restart application to pick up new secret
    kubectl rollout restart -n "$NAMESPACE" deployment/asi-code
    
    echo "Database password rotated successfully"
}

rotate_jwt_secret() {
    echo "Rotating JWT secret..."
    
    # Generate new secret
    NEW_SECRET=$(openssl rand -base64 32)
    
    # Update in Vault
    vault kv put secret/asi-code/jwt secret="$NEW_SECRET"
    
    # Restart application
    kubectl rollout restart -n "$NAMESPACE" deployment/asi-code
    
    echo "JWT secret rotated successfully"
}

# Main rotation logic
case "${1:-}" in
    "database")
        rotate_database_password
        ;;
    "jwt")
        rotate_jwt_secret
        ;;
    "all")
        rotate_database_password
        rotate_jwt_secret
        ;;
    *)
        echo "Usage: $0 [database|jwt|all]"
        exit 1
        ;;
esac
```

### Rotation Schedule
```yaml
# Kubernetes CronJob for automated rotation
apiVersion: batch/v1
kind: CronJob
metadata:
  name: secret-rotation
  namespace: asi-code
spec:
  schedule: "0 2 1 */3 *"  # Every 3 months at 2 AM on the 1st
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: secret-rotator
          containers:
          - name: rotator
            image: asi-code/secret-rotator:latest
            command: ["/scripts/rotate-secrets.sh", "all"]
            volumeMounts:
            - name: scripts
              mountPath: /scripts
          volumes:
          - name: scripts
            configMap:
              name: rotation-scripts
              defaultMode: 0755
          restartPolicy: OnFailure
```

## Security Best Practices

### Do's ✅

1. **Use dedicated secret management services**
   - AWS Secrets Manager, HashiCorp Vault, Azure Key Vault
   - Centralized management and auditing

2. **Implement least privilege access**
   - Grant minimal required permissions
   - Use role-based access control

3. **Rotate secrets regularly**
   - Automated rotation where possible
   - Document rotation procedures

4. **Encrypt secrets at rest and in transit**
   - Use strong encryption algorithms
   - Manage encryption keys separately

5. **Monitor secret access**
   - Log all secret retrievals
   - Alert on unusual access patterns

6. **Use short-lived tokens**
   - Implement token refresh mechanisms
   - Minimize exposure window

### Don'ts ❌

1. **Never commit secrets to version control**
   - Use .gitignore for secret files
   - Scan repositories for leaked secrets

2. **Don't use default or weak passwords**
   - Generate cryptographically secure passwords
   - Avoid dictionary words

3. **Don't share secrets via insecure channels**
   - No email, Slack, or other messaging platforms
   - Use secure sharing mechanisms

4. **Don't hardcode secrets in applications**
   - Use environment variables or files
   - External configuration management

5. **Don't log sensitive information**
   - Sanitize logs and error messages
   - Use structured logging with filters

## Emergency Procedures

### Secret Compromise Response
1. **Immediate Actions (Within 1 hour)**
   - Rotate compromised secrets
   - Revoke access tokens
   - Monitor for unauthorized access

2. **Short-term Actions (Within 24 hours)**
   - Investigate compromise source
   - Update affected systems
   - Notify stakeholders

3. **Long-term Actions (Within 1 week)**
   - Review and update security policies
   - Implement additional controls
   - Conduct post-incident review

### Emergency Rotation Script
```bash
#!/bin/bash
# emergency-rotation.sh

set -euo pipefail

echo "EMERGENCY SECRET ROTATION - $(date)"
echo "This will rotate ALL secrets immediately!"

read -p "Are you sure? (yes/no): " confirm
if [[ "$confirm" != "yes" ]]; then
    echo "Aborted"
    exit 1
fi

# Rotate all critical secrets
./rotate-secrets.sh all

# Force restart all services
kubectl rollout restart -n asi-code deployment/asi-code
kubectl rollout restart -n asi-code deployment/postgres
kubectl rollout restart -n asi-code deployment/redis

echo "Emergency rotation completed - $(date)"
```

## Monitoring and Alerting

### Secret Access Monitoring
```yaml
# Prometheus alert rules
groups:
- name: secrets
  rules:
  - alert: UnauthorizedSecretAccess
    expr: increase(vault_secret_access_total{unauthorized="true"}[5m]) > 0
    labels:
      severity: critical
    annotations:
      summary: "Unauthorized secret access detected"
      
  - alert: SecretRotationOverdue
    expr: (time() - secret_last_rotation_timestamp) > 7776000  # 90 days
    labels:
      severity: warning
    annotations:
      summary: "Secret rotation overdue"
```

### Audit Logging
```javascript
// Example audit logging for secret access
const auditLogger = require('./audit-logger');

function getSecret(secretName, userId) {
    auditLogger.log({
        action: 'SECRET_ACCESS',
        secret: secretName,
        user: userId,
        timestamp: new Date().toISOString(),
        source: 'asi-code-application'
    });
    
    return secretManager.getSecret(secretName);
}
```

## Development Guidelines

### Local Development
```bash
# Use development-specific secrets
cp .env.development.example .env.development

# Generate development secrets
./scripts/generate-dev-secrets.sh

# Never use production secrets in development
export NODE_ENV=development
```

### Testing
```javascript
// Use mock secrets in tests
const mockSecrets = {
    DATABASE_PASSWORD: 'test-password',
    JWT_SECRET: 'test-jwt-secret',
    REDIS_PASSWORD: 'test-redis-password'
};

// Override secret provider in tests
jest.mock('./secret-manager', () => ({
    getSecret: (name) => mockSecrets[name] || 'test-default'
}));
```

## Compliance and Auditing

### Compliance Requirements
- SOC 2 Type II
- PCI DSS (if handling payment data)
- GDPR (for EU users)
- Industry-specific regulations

### Audit Trail
- All secret access logged
- Retention period: 7 years
- Regular audit reviews
- Compliance reporting

### Documentation
- Secret inventory maintenance
- Access control documentation
- Rotation procedures
- Incident response plans

This secrets management guide should be reviewed quarterly and updated as needed to reflect changes in infrastructure, compliance requirements, or security best practices.