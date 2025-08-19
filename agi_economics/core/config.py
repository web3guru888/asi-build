"""
Economic Configuration
=====================

Configuration management for the AGI Economics platform.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from decimal import Decimal
import os
import json
import yaml
from pathlib import Path

@dataclass
class TokenEconomicsConfig:
    """Configuration for token economics"""
    initial_supply: Dict[str, Decimal] = field(default_factory=dict)
    inflation_rate: Decimal = Decimal('0.02')
    burn_rate: Decimal = Decimal('0.01')
    transaction_fee: Decimal = Decimal('0.001')
    staking_reward_rate: Decimal = Decimal('0.05')
    min_stake_amount: Decimal = Decimal('100')
    max_supply: Dict[str, Decimal] = field(default_factory=dict)

@dataclass
class ReputationConfig:
    """Configuration for reputation system"""
    initial_reputation: float = 0.5
    max_reputation: float = 1.0
    min_reputation: float = 0.0
    decay_rate: float = 0.001
    boost_multiplier: float = 1.5
    penalty_multiplier: float = 2.0
    trust_threshold: float = 0.7
    validation_requirement: int = 3

@dataclass
class MarketplaceConfig:
    """Configuration for marketplace dynamics"""
    price_discovery_algorithm: str = "dutch_auction"
    min_bid_increment: Decimal = Decimal('0.01')
    auction_duration: int = 3600  # seconds
    market_maker_fee: Decimal = Decimal('0.003')
    slippage_tolerance: Decimal = Decimal('0.05')
    liquidity_pool_fee: Decimal = Decimal('0.003')
    bonding_curve_formula: str = "bancor"

@dataclass 
class ResourceConfig:
    """Configuration for resource allocation"""
    cpu_base_price: Decimal = Decimal('0.01')
    gpu_base_price: Decimal = Decimal('0.10')
    memory_base_price: Decimal = Decimal('0.001')
    storage_base_price: Decimal = Decimal('0.0001')
    bandwidth_base_price: Decimal = Decimal('0.001')
    quality_bonus_multiplier: float = 1.2
    availability_penalty: float = 0.8
    resource_lock_duration: int = 300  # seconds

@dataclass
class GovernanceConfig:
    """Configuration for governance system"""
    min_voting_power: Decimal = Decimal('1000')
    voting_duration: int = 604800  # 1 week
    execution_threshold: float = 0.6
    quorum_requirement: float = 0.15
    proposal_deposit: Decimal = Decimal('100')
    delegation_enabled: bool = True

@dataclass
class SecurityConfig:
    """Configuration for security and attack resistance"""
    sybil_resistance_threshold: float = 0.8
    dos_rate_limit: int = 100
    manipulation_detection_window: int = 3600
    penalty_escalation_factor: float = 1.5
    blacklist_duration: int = 86400  # 24 hours
    reputation_recovery_period: int = 604800  # 1 week

@dataclass
class BlockchainConfig:
    """Configuration for blockchain integration"""
    ethereum_rpc_url: str = "https://mainnet.infura.io/v3/YOUR-PROJECT-ID"
    contract_addresses: Dict[str, str] = field(default_factory=dict)
    gas_price: Decimal = Decimal('20')  # gwei
    gas_limit: int = 500000
    confirmation_blocks: int = 6
    cross_chain_bridges: List[str] = field(default_factory=list)

class EconomicConfig:
    """Main configuration class for AGI Economics platform"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Default configurations
        self.token_economics = TokenEconomicsConfig()
        self.reputation = ReputationConfig()
        self.marketplace = MarketplaceConfig()
        self.resources = ResourceConfig()
        self.governance = GovernanceConfig()
        self.security = SecurityConfig()
        self.blockchain = BlockchainConfig()
        
        # Load from file if provided
        if config_path:
            self.load_from_file(config_path)
        
        # Override with environment variables
        self._load_from_env()
    
    def load_from_file(self, config_path: str):
        """Load configuration from JSON or YAML file"""
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r') as f:
            if path.suffix.lower() == '.yaml' or path.suffix.lower() == '.yml':
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        self._update_from_dict(data)
    
    def _update_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary"""
        for section, config in data.items():
            if hasattr(self, section):
                section_obj = getattr(self, section)
                for key, value in config.items():
                    if hasattr(section_obj, key):
                        # Convert strings to Decimal for financial values
                        if key.endswith('_price') or key.endswith('_amount') or key.endswith('_rate'):
                            if isinstance(value, (str, int, float)):
                                value = Decimal(str(value))
                        setattr(section_obj, key, value)
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_mappings = {
            'AGI_ECONOMICS_ETHEREUM_RPC': ('blockchain', 'ethereum_rpc_url'),
            'AGI_ECONOMICS_GAS_PRICE': ('blockchain', 'gas_price'),
            'AGI_ECONOMICS_INITIAL_REPUTATION': ('reputation', 'initial_reputation'),
            'AGI_ECONOMICS_TRANSACTION_FEE': ('token_economics', 'transaction_fee'),
            'AGI_ECONOMICS_STAKING_REWARD': ('token_economics', 'staking_reward_rate'),
        }
        
        for env_key, (section, config_key) in env_mappings.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                section_obj = getattr(self, section)
                
                # Type conversion
                if config_key.endswith('_rate') or config_key.endswith('_price') or config_key.endswith('_amount'):
                    value = Decimal(value)
                elif config_key.endswith('_duration') or config_key.endswith('_limit'):
                    value = int(value)
                elif config_key.endswith('_threshold') or config_key.endswith('_multiplier'):
                    value = float(value)
                
                setattr(section_obj, config_key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        for attr_name in ['token_economics', 'reputation', 'marketplace', 
                         'resources', 'governance', 'security', 'blockchain']:
            attr = getattr(self, attr_name)
            result[attr_name] = {}
            for field_name, field_value in attr.__dict__.items():
                if isinstance(field_value, Decimal):
                    result[attr_name][field_name] = str(field_value)
                else:
                    result[attr_name][field_name] = field_value
        return result
    
    def save_to_file(self, config_path: str):
        """Save configuration to file"""
        path = Path(config_path)
        data = self.to_dict()
        
        with open(path, 'w') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(data, f, indent=2)
            else:
                json.dump(data, f, indent=2)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Token economics validation
        if self.token_economics.inflation_rate < 0:
            errors.append("Inflation rate cannot be negative")
        
        if self.token_economics.transaction_fee < 0:
            errors.append("Transaction fee cannot be negative")
        
        # Reputation validation
        if not (0 <= self.reputation.initial_reputation <= 1):
            errors.append("Initial reputation must be between 0 and 1")
        
        if self.reputation.decay_rate < 0:
            errors.append("Reputation decay rate cannot be negative")
        
        # Marketplace validation
        if self.marketplace.min_bid_increment <= 0:
            errors.append("Minimum bid increment must be positive")
        
        # Governance validation
        if not (0 < self.governance.execution_threshold <= 1):
            errors.append("Execution threshold must be between 0 and 1")
        
        if not (0 < self.governance.quorum_requirement <= 1):
            errors.append("Quorum requirement must be between 0 and 1")
        
        return errors