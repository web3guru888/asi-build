# Kenny AGI Blockchain Audit Trail

A comprehensive blockchain-based audit trail system that provides immutable, verifiable, and decentralized audit logging for Kenny AGI operations.

## 🌟 Features

### Core Capabilities
- **Immutable Audit Records**: Store audit records on blockchain with cryptographic signatures
- **Decentralized Storage**: Use IPFS for distributed data storage and content addressing
- **Multi-Network Support**: Deploy on Ethereum, Polygon, and other EVM-compatible networks
- **Cryptographic Security**: Digital signatures, encryption, and hash-based integrity verification
- **RESTful API**: Comprehensive REST API for audit record management and querying
- **Real-time Verification**: Instant verification of record authenticity and integrity

### Advanced Features
- **Smart Contract Integration**: Solidity contracts for on-chain audit trail management
- **Multiple Signature Algorithms**: Support for RSA, ECDSA, Ed25519, and Ethereum signatures
- **IPFS Pinning Services**: Integration with Pinata, Infura, and other pinning providers
- **Rate Limiting**: Built-in API rate limiting and authentication
- **Performance Monitoring**: Metrics collection and health monitoring
- **Batch Operations**: Efficient bulk operations for high-volume scenarios

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   REST API      │    │  Smart Contracts │    │   IPFS Network  │
│                 │    │                  │    │                 │
│ • Authentication│    │ • AuditTrail     │    │ • Data Storage  │
│ • Rate Limiting │    │ • AuditFactory   │    │ • Content Hash  │
│ • Validation    │    │ • Events         │    │ • Pinning       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────┐
         │            Core Services                    │
         │                                            │
         │ • Web3 Client     • Signature Manager      │
         │ • IPFS Client     • Hash Manager           │
         │ • Data Manager    • Key Management         │
         │ • Contract Mgr    • Encryption             │
         └─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kenny-agi/blockchain-audit-trail.git
   cd blockchain-audit-trail
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup_dev_environment.sh
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start services**
   ```bash
   docker-compose up -d
   ```

5. **Deploy smart contracts (testnet)**
   ```bash
   python scripts/deploy.py --network goerli --compile --setup
   ```

6. **Start the API server**
   ```bash
   source venv/bin/activate
   uvicorn src.main:app --reload
   ```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

## 📚 Usage Examples

### Creating an Audit Record

```python
import asyncio
from src.api.rest_api import AuditRecordRequest

# Create audit record
record_request = AuditRecordRequest(
    event_type="access",
    user_id="user123",
    action="login",
    resource="system",
    details={
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "timestamp": "2024-01-15T10:30:00Z"
    },
    encrypt=False
)

# The API will:
# 1. Store the record in IPFS
# 2. Generate cryptographic signature
# 3. Record transaction on blockchain
# 4. Return immutable reference
```

### Verifying Record Integrity

```bash
curl -X POST "http://localhost:8000/api/v1/audit/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "ipfs_hash": "QmYourIPFSHash",
    "blockchain_hash": "0xYourTransactionHash",
    "verify_signature": true,
    "verify_blockchain": true,
    "verify_ipfs": true
  }'
```

### Querying Audit Records

```bash
curl -X POST "http://localhost:8000/api/v1/audit/query" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "access",
    "user_id": "user123",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-31T23:59:59Z",
    "limit": 100
  }'
```

## 🔧 Configuration

### Network Configuration

Configure blockchain networks in `config/config.yaml`:

```yaml
blockchain:
  networks:
    ethereum:
      name: "Ethereum Mainnet"
      chain_id: 1
      rpc_urls:
        - "https://mainnet.infura.io/v3/YOUR_PROJECT_ID"
      private_key: "${ETHEREUM_PRIVATE_KEY}"
    
    polygon:
      name: "Polygon Mainnet"
      chain_id: 137
      rpc_urls:
        - "https://polygon-rpc.com/"
      private_key: "${POLYGON_PRIVATE_KEY}"
```

### IPFS Configuration

```yaml
ipfs:
  api_url: "/dns/localhost/tcp/5001/http"
  gateway_url: "https://gateway.pinata.cloud"
  pinning:
    enabled: true
    services:
      pinata:
        enabled: true
        api_key: "${PINATA_API_KEY}"
        secret_key: "${PINATA_SECRET_KEY}"
```

## 🧪 Testing

### Run All Tests
```bash
python scripts/test_system.py --network goerli
```

### Run Specific Test Suites
```bash
# Blockchain tests only
python scripts/test_system.py --network goerli --skip-ipfs --skip-crypto

# IPFS tests only  
python scripts/test_system.py --skip-blockchain --skip-crypto

# Performance benchmarks
python scripts/test_system.py --benchmark
```

### Smart Contract Tests
```bash
cd contracts
npx hardhat test
```

## 📋 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/audit/records` | Create new audit record |
| POST | `/api/v1/audit/query` | Query audit records |
| POST | `/api/v1/audit/verify` | Verify record integrity |
| GET | `/api/v1/system/status` | Get system status |
| GET | `/api/v1/system/metrics` | Get performance metrics |
| GET | `/api/v1/health` | Health check |

### Authentication

The API supports both API keys and JWT tokens:

```bash
# API Key authentication
curl -H "Authorization: Bearer kenny_your_api_key_here" \
  http://localhost:8000/api/v1/system/status

# JWT token authentication  
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8000/api/v1/system/status
```

## 🔐 Security

### Cryptographic Features
- **Digital Signatures**: RSA-PSS, ECDSA (P-256, P-384, secp256k1), Ed25519
- **Hash Functions**: SHA-256, SHA-512, SHA3, BLAKE2, Keccak-256
- **Encryption**: AES-256-GCM for sensitive data
- **Key Management**: Secure key generation and storage

### Security Best Practices
- Private keys are never exposed in logs or responses
- All API endpoints support HTTPS/TLS
- Rate limiting prevents abuse
- Input validation and sanitization
- Comprehensive audit logging

## 🚀 Deployment

### Docker Deployment
```bash
# Production deployment
docker-compose -f docker-compose.yml up -d

# With monitoring stack
docker-compose --profile monitoring up -d
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/
```

### Environment Variables
```bash
# Required
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_project_id
ETHEREUM_PRIVATE_KEY=0x...
IPFS_API_URL=/dns/localhost/tcp/5001/http

# Optional
PINATA_API_KEY=your_pinata_key
POSTGRES_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379
```

## 🔍 Monitoring

### Metrics Available
- API request rates and response times
- Blockchain transaction success rates  
- IPFS storage and retrieval performance
- Cryptographic operation performance
- System resource usage

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed system status
curl http://localhost:8000/api/v1/system/status

# Performance metrics
curl http://localhost:8000/api/v1/system/metrics
```

## 📈 Performance

### Benchmarks
- **IPFS Storage**: ~100ms average for small records
- **Signature Generation**: ~10ms for ECDSA operations
- **Blockchain Transactions**: Network-dependent (1-30 seconds)
- **API Throughput**: 1000+ requests/second (with caching)

### Optimization Features
- Connection pooling for Web3 and IPFS clients
- Automatic retry with exponential backoff
- Batch operations for bulk processing
- Caching for frequently accessed data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install pre-commit hooks
pre-commit install

# Run tests before committing
python scripts/test_system.py

# Code formatting
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [https://docs.kenny-agi.com/blockchain-audit-trail](https://docs.kenny-agi.com/blockchain-audit-trail)
- **Issues**: [GitHub Issues](https://github.com/kenny-agi/blockchain-audit-trail/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kenny-agi/blockchain-audit-trail/discussions)

## 🏆 Acknowledgments

- OpenZeppelin for secure smart contract libraries
- IPFS for decentralized storage infrastructure
- Web3.py for Ethereum interaction
- FastAPI for modern web API framework

---

Built with ❤️ by the Kenny AGI team for secure, transparent, and immutable audit trails.