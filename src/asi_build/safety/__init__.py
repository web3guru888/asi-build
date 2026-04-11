"""
Constitutional AI Module
========================

Implements constitutional AI frameworks for value alignment and governance.

Subpackages:
    governance  – DAO, smart contracts, Merkle audit ledger, consensus, overrides, rights
"""

from .framework import ConstitutionalAI
from .value_engine import ValueAlignmentEngine
from .constraints import BehavioralConstraints
from .governance import GovernanceFramework  # legacy stub re-exported from governance pkg
from .compliance import ComplianceChecker
from .formal_verification import (
    TheoremProver,
    EthicalVerificationEngine,
    EthicalAxiom,
)

__all__ = [
    "ConstitutionalAI",
    "ValueAlignmentEngine",
    "BehavioralConstraints",
    "GovernanceFramework",
    "ComplianceChecker",
    # formal verification
    "TheoremProver",
    "EthicalVerificationEngine",
    "EthicalAxiom",
    # governance subpackage accessible as safety.governance.*
    "governance",
]