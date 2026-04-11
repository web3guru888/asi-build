"""
AGI Research Reproducibility Platform

A comprehensive platform for ensuring reproducible, verifiable, and shareable AGI research.
Addresses Ben Goertzel's concerns about validating AGI experiments at scale.

This platform provides:
- Experiment versioning and tracking
- Complete environment capture
- Deterministic replay capabilities  
- Result validation and comparison
- Automated replication across hardware
- Standardized AGI benchmarks
- Formal verification tools
- Hyperon/PRIMUS specific tooling
- Integration with research platforms

Author: Kenny AGI Team
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Kenny AGI Team"
__license__ = "MIT"

# Core modules
from .core.platform_manager import AGIReproducibilityPlatform
from .core.config import PlatformConfig
from .core.exceptions import *

# Experiment tracking
from .experiment_tracking.tracker import ExperimentTracker
from .experiment_tracking.versioning import VersionManager

# Environment capture
from .environment_capture.capturer import EnvironmentCapturer
from .environment_capture.containers import ContainerManager

# Replay system
from .replay_system.replay_engine import ReplayEngine
from .replay_system.deterministic_runner import DeterministicRunner

# Validation framework
from .validation.validator import ResultValidator
from .validation.comparator import ResultComparator

# Benchmarks
from .benchmarks.agi_benchmarks import AGIBenchmarkSuite
from .benchmarks.symbolic_reasoning import SymbolicReasoningBenchmarks

# Sharing platform
from .sharing_platform.experiment_package import ExperimentPackage
from .sharing_platform.peer_review import PeerReviewSystem

# Formal verification
from .formal_verification.theorem_prover import TheoremProver
from .formal_verification.safety_verifier import SafetyVerifier

# Hyperon tools
from .hyperon_tools.pln_validator import PLNValidator
from .hyperon_tools.metta_verifier import MeTTaVerifier

__all__ = [
    'AGIReproducibilityPlatform',
    'PlatformConfig', 
    'ExperimentTracker',
    'VersionManager',
    'EnvironmentCapturer',
    'ContainerManager',
    'ReplayEngine',
    'DeterministicRunner',
    'ResultValidator',
    'ResultComparator',
    'AGIBenchmarkSuite',
    'SymbolicReasoningBenchmarks',
    'ExperimentPackage',
    'PeerReviewSystem',
    'TheoremProver',
    'SafetyVerifier',
    'PLNValidator',
    'MeTTaVerifier',
]