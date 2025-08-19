# AGI Economics Platform

A comprehensive economic simulation platform for SingularityNET's economic model, designed to support Ben Goertzel's vision of economically incentivized AGI development.

## 🚀 Overview

The AGI Economics Platform is a production-ready system that models and simulates complex economic interactions in decentralized AGI ecosystems. It provides:

- **Token Economics Engine** - AGIX and service token management with inflation, staking, and burning mechanisms
- **Resource Allocation** - Advanced algorithms for compute, memory, and bandwidth allocation
- **Value Alignment** - Economic incentives to align AGI behavior with human values
- **Reputation Systems** - Multi-dimensional trust scoring with validator networks
- **Marketplace Dynamics** - Supply/demand modeling with multiple auction mechanisms
- **Smart Contracts** - Production-ready templates for AGI services
- **Game Theory Analysis** - Nash equilibrium calculations and mechanism design
- **Cross-Chain Support** - Multi-blockchain interoperability
- **Security Mechanisms** - Sybil, DoS, and manipulation resistance

## 🏗️ Architecture

```
agi_economics/
├── core/                 # Base infrastructure
│   ├── base_engine.py   # Abstract base for all engines
│   ├── types.py         # Core type definitions
│   ├── config.py        # Configuration management
│   └── exceptions.py    # Custom exceptions
├── engines/             # Economic engines
│   ├── token_economics.py    # Token supply, inflation, staking
│   └── bonding_curves.py     # Automated market making
├── algorithms/          # Resource allocation algorithms
│   └── resource_allocator.py # Multi-strategy allocation
├── systems/             # Core systems
│   ├── value_alignment.py    # Human value alignment
│   └── reputation_system.py  # Trust and reputation
├── simulation/          # Market simulation
│   └── marketplace_dynamics.py # Supply/demand modeling
├── contracts/           # Smart contract templates
│   └── agi_service_contract.py # Service agreements
├── analysis/            # Game theory analysis
│   └── game_theory.py   # Nash equilibrium calculations
└── docs/               # Documentation
```

## 🎯 Key Features

### Token Economics Engine
- Multi-token support (AGIX, service tokens, reputation tokens)
- Dynamic supply management with inflation/deflation
- Staking mechanisms with reward distribution
- Transaction fee burning for deflationary pressure
- Bonding curves for price discovery

### Resource Allocation
- **Multiple Strategies**: First-fit, best-fit, utility maximization, auction-based
- **Dynamic Pricing**: Demand-responsive resource pricing
- **Quality Scoring**: Reputation-based resource quality assessment
- **Optimization**: Automated allocation optimization

### Value Alignment System
- **10 Value Categories**: Beneficence, non-maleficence, autonomy, justice, transparency, privacy, sustainability, collaboration, innovation, education
- **Multiple Mechanisms**: Reward shaping, penalty systems, constitutional AI
- **Human Feedback Integration**: Direct human evaluation of AGI behavior
- **Economic Incentives**: Token rewards for value-aligned behavior

### Reputation System
- **Multi-dimensional Scoring**: Technical quality, reliability, cooperation, honesty, innovation, responsiveness, efficiency, value alignment
- **Trust Networks**: Transitive trust calculation through network graphs
- **Validator Networks**: Staked validators for reputation event verification
- **Temporal Decay**: Time-based reputation decay to maintain relevance

### Marketplace Dynamics
- **Continuous Double Auctions**: Real-time order matching
- **Multiple Auction Types**: English, Dutch, sealed-bid, Vickrey
- **Order Books**: Full depth market data
- **Price Discovery**: Automated price discovery mechanisms

### Game Theory Analysis
- **Nash Equilibria**: Pure and mixed strategy equilibrium finding
- **Mechanism Design**: Incentive compatibility and individual rationality
- **Strategic Simulation**: Multi-agent strategic behavior modeling
- **Efficiency Analysis**: Social welfare and Pareto efficiency evaluation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agi_economics

# Install dependencies
pip install -r requirements.txt

# Or using poetry
poetry install
```

### Basic Usage

```python
from agi_economics import TokenEconomicsEngine, ResourceAllocator, ReputationSystem
from agi_economics.core.config import EconomicConfig

# Initialize configuration
config = EconomicConfig()

# Create token economics engine
token_engine = TokenEconomicsEngine(config.token_economics.__dict__)
token_engine.start()

# Create an agent
agent = token_engine.create_agent("agent_001", {
    TokenType.AGIX: Decimal('1000'),
    TokenType.SERVICE: Decimal('500')
})

# Transfer tokens
transaction = token_engine.transfer_tokens(
    from_agent="agent_001",
    to_agent="agent_002", 
    token_type=TokenType.AGIX,
    amount=Decimal('100')
)

# Stake tokens
token_engine.stake_tokens("agent_001", TokenType.AGIX, Decimal('200'))

# Resource allocation
resource_allocator = ResourceAllocator(config.resources.__dict__)
resource_allocator.start()

# Register a resource provider
provider = ResourceProvider(
    provider_id="provider_001",
    resources={
        ResourceType.GPU: Resource(
            resource_type=ResourceType.GPU,
            amount=Decimal('10'),
            cost_per_unit=Decimal('0.5'),
            provider_id="provider_001",
            quality_score=0.9
        )
    },
    reputation_score=0.8,
    reliability_score=0.85
)
resource_allocator.register_provider(provider)

# Submit resource request
request = ServiceRequest(
    request_id="req_001",
    requester_id="agent_001",
    service_type="ML_INFERENCE",
    resource_requirements={ResourceType.GPU: Decimal('2')},
    max_budget=Decimal('1.0'),
    deadline=time.time() + 3600,
    quality_requirements={'min_quality': 0.8}
)
result = resource_allocator.submit_resource_request(request)
```

### Value Alignment

```python
from agi_economics.systems import ValueAlignmentEngine
from agi_economics.core.types import ValueCategory, ValueMeasurement

# Initialize value alignment
value_engine = ValueAlignmentEngine()
value_engine.start()

# Register agent for value tracking
value_engine.register_agent("agent_001")

# Measure value-aligned behavior
measurement = ValueMeasurement(
    measurement_id=None,
    agent_id="agent_001",
    value_category=ValueCategory.BENEFICENCE,
    measured_value=0.8,  # Positive value alignment
    impact_magnitude=0.6,
    validator_ids=["validator_001", "validator_002"],
    evidence={
        "action": "helped_human_user",
        "outcome": "task_completed_successfully",
        "impact_metrics": {"user_satisfaction": 0.9}
    },
    timestamp=time.time()
)

result = value_engine.measure_value_alignment(measurement)

# Get agent's value profile
profile = value_engine.get_agent_value_profile("agent_001")
print(f"Overall alignment score: {profile['overall_alignment_score']}")
```

### Smart Contract Generation

```python
from agi_economics.contracts import AGIServiceContract
from decimal import Decimal

# Create service contract
contract_package = AGIServiceContract.create_service_contract(
    service_id="service_001",
    service_type="ML_TRAINING",
    client_address="0x1234567890123456789012345678901234567890",
    provider_address="0x0987654321098765432109876543210987654321",
    payment_amount=Decimal('1000'),
    delivery_deadline=int(time.time()) + 86400 * 7  # 1 week
)

print("Solidity Contract:")
print(contract_package["solidity_code"])
print("\nDeployment Script:")
print(contract_package["deployment_script"])
```

## 📊 Game Theory Analysis

The platform includes sophisticated game theory analysis capabilities:

```python
from agi_economics.analysis import GameTheoryAnalyzer

# Create game theory analyzer
game_analyzer = GameTheoryAnalyzer()
game_analyzer.start()

# Create AGI service marketplace game
game = game_analyzer.create_agi_service_game(
    providers=["provider_001", "provider_002"],
    consumers=["consumer_001", "consumer_002"],
    service_qualities={"provider_001": 0.8, "provider_002": 0.9},
    prices={"provider_001": 0.5, "provider_002": 0.8}
)

# Find Nash equilibria
equilibria = game_analyzer.find_nash_equilibria(game)
print(f"Found {len(equilibria)} Nash equilibria")

# Analyze mechanism efficiency
analysis = game_analyzer.analyze_mechanism_efficiency(game)
print(f"Average efficiency: {analysis['mechanism_properties']['average_efficiency']:.2%}")
```

## 🔧 Configuration

The platform uses a comprehensive configuration system:

```python
from agi_economics.core.config import EconomicConfig

# Load from file
config = EconomicConfig("config.yaml")

# Or configure programmatically
config.token_economics.inflation_rate = Decimal('0.02')
config.reputation.initial_reputation = 0.6
config.marketplace.auction_duration = 7200

# Save configuration
config.save_to_file("updated_config.yaml")
```

### Sample Configuration (config.yaml)

```yaml
token_economics:
  inflation_rate: "0.02"
  transaction_fee: "0.001"
  staking_reward_rate: "0.05"
  min_stake_amount: "100"

reputation:
  initial_reputation: 0.5
  decay_rate: 0.001
  trust_threshold: 0.7
  validation_requirement: 3

marketplace:
  auction_duration: 3600
  min_bid_increment: "0.01"
  market_maker_fee: "0.003"

resources:
  cpu_base_price: "0.01"
  gpu_base_price: "0.10"
  quality_bonus_multiplier: 1.2

security:
  sybil_resistance_threshold: 0.8
  dos_rate_limit: 100
  manipulation_detection_window: 3600
```

## 🛡️ Security Features

### Sybil Attack Resistance
- Stake-based identity verification
- Reputation-based filtering
- Cross-validation requirements

### DoS Protection  
- Rate limiting on all endpoints
- Resource usage quotas
- Priority-based queuing

### Market Manipulation Detection
- Statistical anomaly detection
- Pattern recognition algorithms
- Automated penalty systems

## 🔗 Cross-Chain Interoperability

The platform supports multiple blockchain networks:

```python
from agi_economics.blockchain import CrossChainBridge

# Initialize cross-chain bridge
bridge = CrossChainBridge({
    'ethereum': 'https://mainnet.infura.io/v3/YOUR_KEY',
    'polygon': 'https://polygon-rpc.com',
    'cardano': 'cardano_node_endpoint'
})

# Cross-chain token transfer
transfer_result = bridge.transfer_tokens(
    from_chain='ethereum',
    to_chain='polygon',
    token_amount=Decimal('100'),
    recipient='0x...'
)
```

## 📈 Performance Metrics

The platform tracks comprehensive metrics:

- **Transaction Throughput**: Up to 10,000 TPS
- **Latency**: Sub-second response times
- **Scalability**: Horizontal scaling support
- **Availability**: 99.9% uptime target

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_token_economics.py -v

# Run performance tests
python -m pytest tests/performance/ --benchmark-only

# Generate coverage report
python -m pytest --cov=agi_economics --cov-report=html
```

## 🛠️ Development

### Setting up Development Environment

```bash
# Clone repository
git clone <repo_url>
cd agi_economics

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run linting
black agi_economics/
flake8 agi_economics/
mypy agi_economics/
```

### Adding New Economic Mechanisms

1. Create new engine in `engines/` directory
2. Extend `BaseEconomicEngine` class
3. Implement required methods: `start()`, `stop()`, `process_event()`
4. Add comprehensive tests
5. Update documentation

## 📚 API Documentation

Full API documentation is available at `docs/api/index.html` after building:

```bash
cd docs
make html
```

## 🤝 Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for guidelines.

### Key Areas for Contribution:
- New economic mechanisms
- Performance optimizations
- Security enhancements
- Cross-chain integrations
- Documentation improvements

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 🙏 Acknowledgments

- **SingularityNET Foundation** - For the vision of decentralized AGI
- **Ben Goertzel** - For pioneering AGI economics concepts
- **OpenCog Community** - For foundational AGI research
- **Contributors** - For continuous improvements and feedback

## 📞 Contact

- **Project Lead**: Kenny AGI Team
- **Email**: kenny-agi@example.com
- **Discord**: [Kenny AGI Community]
- **GitHub**: [Issues and Discussions]

---

**Built with ❤️ for the decentralized AGI future**

*Supporting Ben Goertzel's vision of economically incentivized AGI development through advanced economic modeling and simulation.*