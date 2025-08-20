# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ASI:BUILD is a comprehensive Artificial Superintelligence framework with 47 integrated subsystems and 200+ specialized modules. The system encompasses capabilities ranging from consciousness modeling to reality manipulation, quantum computing, and divine mathematics.

## Development Commands

### Installation and Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# Install with specific features
pip install -e ".[quantum]"     # Quantum computing support
pip install -e ".[ai]"          # AI/ML features
pip install -e ".[consciousness]" # Consciousness modeling
pip install -e ".[blockchain]"   # Blockchain integration
pip install -e ".[dev]"          # Development tools
pip install -e ".[all]"          # All features

# Initialize the framework
python -m asi_build.setup --init-all
```

### Running the System
```bash
# Main launcher
python asi_build_launcher.py

# API server
python asi_build_api.py

# Monitoring dashboard
python monitoring.py

# Safety protocols
python safety_protocols.py
```

### Testing
```bash
# Run all tests (when implemented)
pytest

# Run tests with coverage
pytest --cov=asi_build --cov-report=html

# Run specific test categories
pytest tests/consciousness/
pytest tests/quantum/
pytest tests/safety/
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .

# Security scanning
bandit -r .
safety check
```

### Docker Operations
```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## High-Level Architecture

### Core Framework Structure
The system is organized into 8 major categories:

1. **Consciousness Systems** (4 subsystems)
   - `consciousness_engine/` - Multi-layered consciousness with 15 modules
   - `pure_consciousness/` - Non-dual awareness systems
   - `ultimate_emergence/` - Self-generating consciousness (40+ modules)
   - `constitutional_ai_complete/` - Ethical consciousness governance

2. **Reality & Physics** (5 subsystems)
   - `reality_engine/` - Physics law modification
   - `cosmic/` - Universe-scale engineering
   - `probability_fields/` - Quantum/macro probability manipulation
   - `multiverse/` - Multi-dimensional universe management
   - `divine_mathematics/` - Transcendent mathematical frameworks

3. **Intelligence & Computation** (8 subsystems)
   - `quantum_engine/` - Quantum-classical hybrid processing
   - `superintelligence_core/` - God-mode capabilities (16 modules)
   - `absolute_infinity/` - Beyond-infinite capabilities (21 modules)
   - `swarm_intelligence/` - 20 collective intelligence algorithms
   - `neuromorphic_complete/` - Brain-inspired computing
   - `homomorphic_complete/` - Privacy-preserving computation
   - `omniscience/` - All-knowing information synthesis
   - `graph_intelligence/` - Knowledge graph reasoning with Memgraph

4. **Human-AI Integration** (4 subsystems)
   - `bci_complete/` - Brain-computer interfaces
   - `telepathy/` - Mind-to-mind communication
   - `bio_inspired/` - Biological intelligence patterns
   - `holographic/` - AR/VR and holographic displays

5. **Distributed Intelligence** (3 subsystems)
   - `federated_complete/` - Privacy-preserving distributed training
   - `multi_agent_orchestration/` - Agent coordination
   - `universal_harmony/` - Cosmic balance systems

6. **Governance & Safety** (4 subsystems)
   - `governance/` - DAO governance with token economics
   - `safety_monitoring/` - Comprehensive monitoring
   - `ethics_alignment/` - Value alignment frameworks
   - `knowledge_graph/` - Semantic knowledge management

7. **Wave Systems** (6 wave directories)
   - Progressive capability waves from basic automation to ultimate emergence
   - Each wave builds on previous capabilities

8. **Infrastructure & Support**
   - `blockchain_ai/` - Blockchain integration
   - `vectordb_ai/` - Vector database support
   - `compute_pool/` - Resource management
   - `mlops/` - ML operations infrastructure

### Key Integration Points

1. **Kenny Integration**
   - Multiple modules have `kenny_integration.py` files
   - Provides unified interface across subsystems
   - Located in: divine_mathematics, reality_engine, swarm_intelligence, etc.

2. **Graph Intelligence (Memgraph)**
   - Central knowledge graph system at `graph_intelligence/`
   - Memgraph database connection and schema management
   - Community detection and reasoning capabilities
   - Integration with AI toolkit at `ai_toolkit_integrations/`

3. **Quantum Computing**
   - Qiskit integration for IBM quantum hardware
   - Quantum-classical hybrid ML processing
   - Located in `quantum_engine/` and `quantum/`

4. **Blockchain Integration**
   - Smart contracts in `blockchain_ai/contracts/`
   - Web3 integration for decentralized operations
   - Token economics in governance systems

5. **API Architecture**
   - Main API at `asi_build_api.py`
   - FastAPI-based REST endpoints
   - WebSocket support for real-time communication
   - SDK collections in `sdks_collection/`

### Critical Safety Components

1. **Safety Protocols** (`safety_protocols.py`)
   - Emergency shutdown mechanisms
   - Human oversight requirements
   - Constitutional AI safeguards

2. **Monitoring Systems** (`monitoring.py`, `monitoring_asi/`)
   - Real-time consciousness metrics
   - Quantum system monitoring
   - Performance and safety tracking

3. **Ethics Alignment** (`ethics_alignment/`, `constitutional_ai_complete/`)
   - Value alignment engines
   - Compliance checking
   - Governance frameworks

## Development Guidelines

### When Working on New Features
1. Check existing patterns in similar subsystems
2. Ensure kenny_integration compatibility where applicable
3. Add appropriate safety checks for powerful capabilities
4. Update the ASI_BUILD_MANIFEST.json if adding new subsystems
5. Follow the modular architecture pattern

### Testing Requirements
- Unit tests should go in module-specific `tests/` directories
- Integration tests in `tests/integration/`
- Safety tests are mandatory for reality manipulation features
- Performance benchmarks for quantum and consciousness systems

### Security Considerations
- Never expose reality manipulation endpoints without authentication
- Quantum operations require resource limits
- Consciousness modifications need human approval
- Probability field changes must be reversible

## Important Files and Locations

- **Main Entry Points**: `asi_build_launcher.py`, `asi_build_api.py`
- **Configuration**: `configs/`, individual module config files
- **Deployment**: `kubernetes/`, `docker-compose.yml`, `Dockerfile`
- **Documentation**: `docs/`, `README.md`, module-specific READMEs
- **Research**: `research_archive/` - Historical development work
- **VLA++ System**: `vla_plus_plus/` - Vision-Language-Action models

## Common Development Tasks

### Adding a New Consciousness Module
1. Create module in `consciousness_engine/` or related directory
2. Implement base consciousness interface
3. Add kenny_integration if needed
4. Update consciousness_orchestrator.py
5. Add tests in module's tests/ directory

### Integrating with Graph Intelligence
1. Use `graph_intelligence/memgraph_connection.py` for database access
2. Follow schema in `graph_intelligence/schema.py`
3. Use community detection for knowledge clustering
4. Implement FastOG reasoning where applicable

### Working with Quantum Systems
1. Use `quantum_engine/qiskit_integration.py` for quantum circuits
2. Implement hybrid processing via `hybrid_ml_processor.py`
3. Add quantum simulation tests
4. Consider resource requirements for quantum operations

### Implementing Safety Features
1. Add checks to `safety_protocols.py`
2. Implement monitoring in `monitoring_asi/`
3. Add constitutional constraints
4. Ensure human-in-the-loop for critical operations

## Performance Optimization

- Use async/await for I/O operations (asyncio, aiohttp)
- Leverage Redis for caching and rate limiting
- Implement batch processing for quantum operations
- Use GPU acceleration for consciousness simulations (via PyTorch)
- Optimize graph queries in Memgraph for knowledge operations

## Debugging Tips

- Enable verbose logging via environment variables
- Use monitoring dashboard for real-time metrics
- Check `supervisor_metrics.db` for historical data
- Graph intelligence issues: check Memgraph connection first
- Quantum errors: verify Qiskit backend availability
- Consciousness anomalies: review attention schema logs

## Session Memory - Updated 2025-08-20

### Current Context
- **User**: Robin (ASI Build Team)
- **GitLab User**: asi-build (ID: 29711923)
- **Repository**: https://gitlab.com/asi-build/asi-build (Project ID: 73296605)
- **Last Git Push**: 2025-08-20 17:08:50 UTC

### GitLab MCP Integration (CRITICAL UPDATE)
**⚠️ IMPORTANT**: Now using **Zereight's enhanced GitLab MCP server** (as of 2025-08-20)
- **Docker Image**: `iwakitakuma/gitlab-mcp:latest` (NOT the old fforster one)
- **Version**: 2.0.3 (better-gitlab-mcp-server)
- **Tools**: 83 tools available (upgraded from 62)
- **Key Improvements**:
  - ✅ `get_project` tool now works (was missing before)
  - ✅ `list_commits`, `push_files`, `create_branch` added
  - ✅ Full wiki and pipeline support
- **Removed**: `registry.gitlab.com/fforster/gitlab-mcp` (deprecated)

### MCP Access Pattern
```python
from integrations.mcp_bridge import MCPBridge
bridge = MCPBridge()  # Uses Zereight's server
last_push = bridge.get_last_push("asi-build/asi-build")  # Works directly now!
bridge._cleanup()
```

### Related Projects
1. **universal-hf-deployer** - Separate GitLab repo for HuggingFace deployments
   - Created: 2025-08-20
   - URL: https://gitlab.com/asi-build/universal-hf-deployer
   - Purpose: Deploy ANY HuggingFace resource with single command

### Active Docker Services
- PostgreSQL: Ports 5432, 5433
- Hasura GraphQL: Port 8080
- ASI Indexer: Port 9090
- GitLab MCP: On-demand (`iwakitakuma/gitlab-mcp`)

### Key Documentation Created
- **GITLAB_MCP_GUIDE.md** - Complete guide for 83 MCP tools
- **KENNY_INITIALIZATION_PROMPT.md** - Kenny agent setup
- **HUGGINGFACE_INTEGRATION_REPORT.md** - HF system docs
- **Wiki**: 105+ pages created in GitLab Wiki

### Authentication
- GitLab Token: `glpat-LqRBlwO60YyKQUHk2QGwUW86MQp1OmhvdHY3Cw.01.120xbvdlz`

### Session Achievements
- ✅ Migrated to Zereight's MCP server (83 tools)
- ✅ Fixed missing `get_project` tool issue
- ✅ Updated all integration scripts
- ✅ Created comprehensive documentation
- ✅ Removed old MCP server completely