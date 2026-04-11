"""
Constitutional AI Module
========================

Implements constitutional AI frameworks for value alignment and governance.

Subpackages:
    governance  – DAO, smart contracts, Merkle audit ledger, consensus, overrides, rights
"""

try:
    from .framework import ConstitutionalAI
except (ImportError, ModuleNotFoundError, SyntaxError):
    ConstitutionalAI = None
try:
    from .value_engine import ValueAlignmentEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    ValueAlignmentEngine = None
try:
    from .constraints import BehavioralConstraints
except (ImportError, ModuleNotFoundError, SyntaxError):
    BehavioralConstraints = None
try:
    from .governance import GovernanceFramework  # legacy stub re-exported from governance pkg
except (ImportError, ModuleNotFoundError, SyntaxError):
    GovernanceFramework  # legacy stub re-exported from governance pkg = None
try:
    from .compliance import ComplianceChecker
except (ImportError, ModuleNotFoundError, SyntaxError):
    ComplianceChecker = None
try:
    from .formal_verification import (
        EthicalAxiom,
        EthicalVerificationEngine,
        TheoremProver,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    TheoremProver = None
    EthicalVerificationEngine = None
    EthicalAxiom = None

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
