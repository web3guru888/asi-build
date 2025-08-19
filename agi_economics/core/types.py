"""
Core Types and Enums
====================

Fundamental types and enumerations used throughout the AGI Economics platform.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union, NamedTuple
from dataclasses import dataclass
from decimal import Decimal
import uuid

class TokenType(Enum):
    """Types of tokens in the ecosystem"""
    AGIX = "AGIX"  # SingularityNET native token
    SERVICE = "SERVICE"  # AGI service tokens
    REPUTATION = "REPUTATION"  # Reputation tokens
    GOVERNANCE = "GOVERNANCE"  # Governance tokens
    UTILITY = "UTILITY"  # Utility tokens
    STAKING = "STAKING"  # Staking rewards

class ResourceType(Enum):
    """Types of computational resources"""
    CPU = auto()
    GPU = auto()
    MEMORY = auto()
    STORAGE = auto()
    BANDWIDTH = auto()
    COMPUTE_CREDITS = auto()
    MODEL_INFERENCE = auto()

class AgentType(Enum):
    """Types of AGI agents in the ecosystem"""
    SERVICE_PROVIDER = auto()
    RESOURCE_CONSUMER = auto()
    VALIDATOR = auto()
    GOVERNANCE_PARTICIPANT = auto()
    MARKET_MAKER = auto()
    ORACLE = auto()

class TransactionType(Enum):
    """Types of economic transactions"""
    TOKEN_TRANSFER = auto()
    SERVICE_PAYMENT = auto()
    RESOURCE_ALLOCATION = auto()
    REPUTATION_UPDATE = auto()
    STAKING_REWARD = auto()
    GOVERNANCE_VOTE = auto()
    PENALTY = auto()
    BONUS = auto()

class MarketState(Enum):
    """Market states for dynamic pricing"""
    UNDER_SUPPLY = auto()
    BALANCED = auto()
    OVER_SUPPLY = auto()
    VOLATILE = auto()
    STABLE = auto()

@dataclass
class TokenBalance:
    """Represents a token balance for an agent"""
    token_type: TokenType
    amount: Decimal
    locked_amount: Decimal = Decimal('0')
    last_updated: float = None
    
    def __post_init__(self):
        if self.last_updated is None:
            import time
            self.last_updated = time.time()
    
    @property
    def available_amount(self) -> Decimal:
        return self.amount - self.locked_amount

@dataclass
class Resource:
    """Represents a computational resource"""
    resource_type: ResourceType
    amount: Decimal
    cost_per_unit: Decimal
    provider_id: str
    quality_score: float = 1.0
    availability: float = 1.0
    
    @property
    def total_cost(self) -> Decimal:
        return self.amount * self.cost_per_unit

@dataclass
class ServiceRequest:
    """Represents a request for AGI services"""
    request_id: str
    requester_id: str
    service_type: str
    resource_requirements: Dict[ResourceType, Decimal]
    max_budget: Decimal
    deadline: float
    quality_requirements: Dict[str, float]
    
    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())

@dataclass
class Agent:
    """Represents an AGI agent in the ecosystem"""
    agent_id: str
    agent_type: AgentType
    reputation_score: float
    trust_score: float
    token_balances: Dict[TokenType, TokenBalance]
    resources: List[Resource]
    stake_amount: Decimal = Decimal('0')
    is_active: bool = True
    
    def __post_init__(self):
        if self.agent_id is None:
            self.agent_id = str(uuid.uuid4())
        if self.token_balances is None:
            self.token_balances = {}
        if self.resources is None:
            self.resources = []

@dataclass
class EconomicTransaction:
    """Represents an economic transaction"""
    transaction_id: str
    transaction_type: TransactionType
    from_agent: str
    to_agent: str
    token_type: TokenType
    amount: Decimal
    timestamp: float
    gas_fee: Decimal = Decimal('0')
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.transaction_id is None:
            self.transaction_id = str(uuid.uuid4())
        if self.timestamp is None:
            import time
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}

class MarketData(NamedTuple):
    """Market data snapshot"""
    timestamp: float
    token_type: TokenType
    price: Decimal
    volume: Decimal
    market_cap: Decimal
    supply: Decimal
    demand: Decimal
    state: MarketState

@dataclass
class ReputationEvent:
    """Event that affects agent reputation"""
    event_id: str
    agent_id: str
    event_type: str
    impact: float  # Can be positive or negative
    validator_id: Optional[str]
    evidence: Dict[str, Any]
    timestamp: float
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        if self.timestamp is None:
            import time
            self.timestamp = time.time()
        if self.evidence is None:
            self.evidence = {}

@dataclass
class GovernanceProposal:
    """Governance proposal in the ecosystem"""
    proposal_id: str
    proposer_id: str
    title: str
    description: str
    proposal_type: str
    voting_power_required: Decimal
    execution_threshold: float
    created_at: float
    voting_ends_at: float
    votes_for: Decimal = Decimal('0')
    votes_against: Decimal = Decimal('0')
    status: str = 'ACTIVE'
    
    def __post_init__(self):
        if self.proposal_id is None:
            self.proposal_id = str(uuid.uuid4())
        if self.created_at is None:
            import time
            self.created_at = time.time()

# Type aliases for complex types
AgentID = str
TokenAmount = Decimal
Price = Decimal
Timestamp = float
QualityScore = float
TrustScore = float