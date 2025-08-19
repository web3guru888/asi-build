"""
Hyperon/MORK Integration Module for Kenny AGI
============================================

This module provides comprehensive integration between Kenny AGI and:
- SingularityNET's hyperon symbolic AI framework
- MORK (Memory-Optimized Reasoning Kernel) data structures
- Ben Goertzel's PRIMUS architecture

Features:
- Atomspace integration for knowledge representation
- Probabilistic Logic Networks (PLN) interface
- MeTTa language support for symbolic AI
- Memory-mapped MORK storage
- Distributed reasoning cluster support
- Hybrid symbolic-neural architectures

Architecture:
┌─────────────────────────────────────────┐
│         Kenny AGI Core                   │
├─────────────────────────────────────────┤
│         Integration Bridge              │
├─────────────────────────────────────────┤
│    Hyperon      │       MORK           │
│  ┌─────────────┐│  ┌─────────────────┐ │
│  │ Atomspace   ││  │ Memory Storage  │ │
│  │ PLN Engine  ││  │ Graph Repr.     │ │
│  │ MeTTa Lang  ││  │ Query Engine    │ │
│  │ Pattern Mat.││  │ Distributed     │ │
│  └─────────────┘│  │ Cluster         │ │
└─────────────────┼──┤ Version Control │ │
                  │  └─────────────────┘ │
                  └─────────────────────┘

Created: August 2025
Version: 1.0.0
Author: Kenny AGI Research Team
Compatible with: SingularityNET hyperon, Ben Goertzel's PRIMUS
"""

__version__ = "1.0.0"
__author__ = "Kenny AGI Research Team"
__email__ = "kenny@agi-research.org"

# Core integration components
from .hyperon_compatibility.atomspace.atomspace_integration import AtomspaceIntegration
from .hyperon_compatibility.pln.pln_interface import PLNInterface
from .hyperon_compatibility.opencog_adapters.hyperon_adapter import HyperonAdapter
from .hyperon_compatibility.metta_support.metta_interpreter import MeTTaInterpreter
from .hyperon_compatibility.pattern_matcher.pattern_engine import PatternEngine

# MORK data structure interfaces
from .mork_interfaces.storage.memory_mapped_storage import MemoryMappedStorage
from .mork_interfaces.graph_representation.mork_graph import MORKGraph
from .mork_interfaces.query_engine.mork_query_engine import MORKQueryEngine
from .mork_interfaces.distributed_cluster.cluster_manager import ClusterManager
from .mork_interfaces.version_control.knowledge_versioning import KnowledgeVersioning

# Bridge components
from .bridge_components.kenny_hyperon_bridge import KennyHyperonBridge
from .bridge_components.mork_vector_converter import MORKVectorConverter
from .bridge_components.unified_query_language import UnifiedQueryLanguage
from .bridge_components.hybrid_reasoning_engine import HybridReasoningEngine
from .bridge_components.knowledge_graph_sync import KnowledgeGraphSync

# Main integration class
from .integration_manager import (
    HyperonMORKIntegrationManager,
    create_development_integration,
    create_production_integration,
    create_test_integration
)

# Test utilities
from .tests.test_framework import IntegrationTestFramework

__all__ = [
    # Core classes
    'HyperonMORKIntegrationManager',
    'IntegrationTestFramework',
    
    # Factory functions
    'create_development_integration',
    'create_production_integration',
    'create_test_integration',
    
    # Hyperon compatibility
    'AtomspaceIntegration',
    'PLNInterface',
    'HyperonAdapter',
    'MeTTaInterpreter',
    'PatternEngine',
    
    # MORK interfaces
    'MemoryMappedStorage',
    'MORKGraph',
    'MORKQueryEngine',
    'ClusterManager',
    'KnowledgeVersioning',
    
    # Bridge components
    'KennyHyperonBridge',
    'MORKVectorConverter',
    'UnifiedQueryLanguage',
    'HybridReasoningEngine',
    'KnowledgeGraphSync',
]

# Configuration
HYPERON_MORK_CONFIG = {
    'hyperon': {
        'atomspace_size': 1000000,
        'pln_enabled': True,
        'metta_interpreter': True,
        'pattern_matching': True,
    },
    'mork': {
        'memory_mapped': True,
        'cluster_enabled': True,
        'version_control': True,
        'distributed_nodes': 3,
    },
    'integration': {
        'sync_interval': 1.0,  # seconds
        'batch_size': 1000,
        'compression_enabled': True,
        'error_recovery': True,
    }
}

def get_integration_manager(**kwargs):
    """
    Factory function to create a properly configured integration manager.
    
    Args:
        **kwargs: Configuration overrides
    
    Returns:
        HyperonMORKIntegrationManager: Configured integration instance
    """
    config = HYPERON_MORK_CONFIG.copy()
    config.update(kwargs)
    return HyperonMORKIntegrationManager(config)