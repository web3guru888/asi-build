"""
ASI:BUILD Governance — DAO, formal verification, smart contracts, Merkle audit.

Submodules:
    engine      – GovernanceEngine, proposal lifecycle, ethical frameworks
    dao         – DAOGovernance, QuadraticVoting, ReputationSystem, treasury
    contracts   – SmartContract hierarchy, ContractRegistry, token/proposal/ethics contracts
    ledger      – PublicLedger, MerkleTree, CryptographicVerifier, AuditLogger
    consensus   – MultiStakeholderConsensus, LiquidDemocracy, QuadraticVotingSystem
    override    – DemocraticOverrideSystem, HumanInTheLoopController
    rights      – RightsManager, ConsentManager, Human/AGI rights frameworks
"""


# ---------------------------------------------------------------------------
# Backwards-compatible stub: ``GovernanceFramework`` used to live in the
# now-shadowed ``safety/governance.py``.  Re-export it here so that
# ``from .governance import GovernanceFramework`` in safety/__init__.py
# keeps working.
# ---------------------------------------------------------------------------
class GovernanceFramework:
    """Minimal governance policy container (legacy stub)."""

    def __init__(self):
        self.policies = []


# ---------------------------------------------------------------------------
# Lazy public imports – heavy deps stay out of module-load time.
# ---------------------------------------------------------------------------


def __getattr__(name: str):
    """Lazy-import main classes on first access."""
    _lazy = {
        # engine.py
        "GovernanceEngine": ".engine",
        "Proposal": ".engine",
        "Stakeholder": ".engine",
        "ProposalStatus": ".engine",
        "VoteType": ".engine",
        "GovernanceDecision": ".engine",
        "EthicalFramework": ".engine",
        "UtilitarianFramework": ".engine",
        "DeontologicalFramework": ".engine",
        "VirtueEthicsFramework": ".engine",
        # dao.py
        "DAOGovernance": ".dao",
        "DAOTreasury": ".dao",
        "QuadraticVoting": ".dao",
        "ReputationSystem": ".dao",
        "DAOToken": ".dao",
        "DAOProposal": ".dao",
        # contracts.py
        "ContractRegistry": ".contracts",
        "SmartContract": ".contracts",
        "GovernanceTokenContract": ".contracts",
        "ProposalContract": ".contracts",
        "EthicsEnforcementContract": ".contracts",
        "deploy_governance_contracts": ".contracts",
        # ledger.py
        "PublicLedger": ".ledger",
        "MerkleTree": ".ledger",
        "CryptographicVerifier": ".ledger",
        "AuditLogger": ".ledger",
        "PrivacyPreserver": ".ledger",
        # consensus.py
        "MultiStakeholderConsensus": ".consensus",
        "LiquidDemocracy": ".consensus",
        "QuadraticVotingSystem": ".consensus",
        # override.py
        "DemocraticOverrideSystem": ".override",
        "HumanInTheLoopController": ".override",
        # rights.py
        "RightsManager": ".rights",
        "ConsentManager": ".rights",
        "HumanRightsFramework": ".rights",
        "AGIRightsFramework": ".rights",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name], __name__)
        val = getattr(mod, name)
        # Cache on the module so future accesses skip __getattr__
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Legacy stub
    "GovernanceFramework",
    # engine
    "GovernanceEngine",
    "Proposal",
    "Stakeholder",
    "ProposalStatus",
    "VoteType",
    "GovernanceDecision",
    "EthicalFramework",
    "UtilitarianFramework",
    "DeontologicalFramework",
    "VirtueEthicsFramework",
    # dao
    "DAOGovernance",
    "DAOTreasury",
    "QuadraticVoting",
    "ReputationSystem",
    "DAOToken",
    "DAOProposal",
    # contracts
    "ContractRegistry",
    "SmartContract",
    "GovernanceTokenContract",
    "ProposalContract",
    "EthicsEnforcementContract",
    "deploy_governance_contracts",
    # ledger
    "PublicLedger",
    "MerkleTree",
    "CryptographicVerifier",
    "AuditLogger",
    "PrivacyPreserver",
    # consensus
    "MultiStakeholderConsensus",
    "LiquidDemocracy",
    "QuadraticVotingSystem",
    # override
    "DemocraticOverrideSystem",
    "HumanInTheLoopController",
    # rights
    "RightsManager",
    "ConsentManager",
    "HumanRightsFramework",
    "AGIRightsFramework",
]
