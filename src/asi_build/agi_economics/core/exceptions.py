"""
AGI Economics Exceptions
=======================

Custom exception classes for the AGI Economics platform.
"""

class AGIEconomicsError(Exception):
    """Base exception for all AGI Economics errors"""
    pass

class ConfigurationError(AGIEconomicsError):
    """Raised when there's an error in configuration"""
    pass

class TokenError(AGIEconomicsError):
    """Raised when there's an error with token operations"""
    pass

class InsufficientFundsError(TokenError):
    """Raised when an agent has insufficient funds for a transaction"""
    pass

class InvalidTokenError(TokenError):
    """Raised when an invalid token type is used"""
    pass

class ResourceError(AGIEconomicsError):
    """Raised when there's an error with resource operations"""
    pass

class ResourceUnavailableError(ResourceError):
    """Raised when a requested resource is not available"""
    pass

class ResourceAllocationError(ResourceError):
    """Raised when resource allocation fails"""
    pass

class ReputationError(AGIEconomicsError):
    """Raised when there's an error with reputation operations"""
    pass

class InvalidReputationScoreError(ReputationError):
    """Raised when an invalid reputation score is provided"""
    pass

class TrustThresholdError(ReputationError):
    """Raised when an agent doesn't meet trust requirements"""
    pass

class MarketplaceError(AGIEconomicsError):
    """Raised when there's an error with marketplace operations"""
    pass

class AuctionError(MarketplaceError):
    """Raised when there's an error with auction operations"""
    pass

class PriceDiscoveryError(MarketplaceError):
    """Raised when price discovery fails"""
    pass

class GovernanceError(AGIEconomicsError):
    """Raised when there's an error with governance operations"""
    pass

class InsufficientVotingPowerError(GovernanceError):
    """Raised when an agent has insufficient voting power"""
    pass

class ProposalError(GovernanceError):
    """Raised when there's an error with proposal operations"""
    pass

class SecurityError(AGIEconomicsError):
    """Raised when there's a security-related error"""
    pass

class SybilAttackError(SecurityError):
    """Raised when a potential Sybil attack is detected"""
    pass

class DoSAttackError(SecurityError):
    """Raised when a DoS attack is detected"""
    pass

class ManipulationError(SecurityError):
    """Raised when market manipulation is detected"""
    pass

class BlockchainError(AGIEconomicsError):
    """Raised when there's an error with blockchain operations"""
    pass

class TransactionError(BlockchainError):
    """Raised when a blockchain transaction fails"""
    pass

class SmartContractError(BlockchainError):
    """Raised when there's an error with smart contract operations"""
    pass

class CrossChainError(BlockchainError):
    """Raised when there's an error with cross-chain operations"""
    pass

class ValidationError(AGIEconomicsError):
    """Raised when validation fails"""
    pass

class AgentError(AGIEconomicsError):
    """Raised when there's an error with agent operations"""
    pass

class AgentNotFoundError(AgentError):
    """Raised when an agent is not found"""
    pass

class AgentInactiveError(AgentError):
    """Raised when an inactive agent tries to perform operations"""
    pass