"""
Blackboard Adapters — Module-to-Blackboard bridges
====================================================

Each adapter wraps a specific ASI:BUILD module and connects it to the
``CognitiveBlackboard`` via the Producer/Consumer/Transformer protocols.

Quick Start
~~~~~~~~~~~

::

    from asi_build.integration import CognitiveBlackboard
    from asi_build.integration.adapters import (
        ConsciousnessAdapter,
        KnowledgeGraphAdapter,
        CognitiveSynergyAdapter,
        ReasoningAdapter,
        wire_all,
    )

    bb = CognitiveBlackboard()

    # Instantiate adapters with your module instances
    cons = ConsciousnessAdapter(gwt=my_gwt, iit=my_iit)
    kg   = KnowledgeGraphAdapter(kg=my_kg, pathfinder=my_pf)
    syn  = CognitiveSynergyAdapter(engine=my_engine, metrics=my_metrics)
    reas = ReasoningAdapter(engine=my_reasoning)

    # Register all with the blackboard and wire event subscriptions
    wire_all(bb, cons, kg, syn, reas)

Available Adapters
~~~~~~~~~~~~~~~~~~

Core:
- ``ConsciousnessAdapter``        — GWT, IIT, BaseConsciousness
- ``KnowledgeGraphAdapter``       — TemporalKG, KGPathfinder
- ``CognitiveSynergyAdapter``     — CognitiveSynergyEngine, SynergyMetrics
- ``ReasoningAdapter``            — HybridReasoningEngine

Infrastructure:
- ``ComputeBlackboardAdapter``    — JobScheduler, ResourceAllocator, MetricsCollector
- ``DistributedTrainingAdapter``  — FederatedOrchestrator, ByzantineTolerantAggregator
- ``VectorDBBlackboardAdapter``   — EmbeddingPipeline, SemanticSearchEngine, VectorDBConfig
- ``BlockchainBlackboardAdapter`` — HashManager, MerkleTree, HashChain, SignatureManager

Research & Optimization:
- ``ReproducibilityBlackboardAdapter`` — ExperimentTracker, VersionManager, PlatformConfig
- ``VLABlackboardAdapter``             — VLAPlusPlus, VLATrainer, VLAOptimizationPipeline

Quantum:
- ``QuantumBlackboardAdapter``         — QuantumSimulator, HybridMLProcessor, QAOA, VQE, KennyQuantumIntegration

Holographic:
- ``HolographicBlackboardAdapter``     — HolographicEngine, LightFieldProcessor, VolumetricDisplay

Neuromorphic & BCI:
- ``NeuromorphicBlackboardAdapter``    — NeuromorphicManager, EventProcessor, SpikeMonitor, STDPLearning
- ``BCIBlackboardAdapter``             — BCIManager, SignalProcessor, NeuralDecoder

AGI Communication & Economics:
- ``AGICommunicationBlackboardAdapter`` — AGICommunicationProtocol, GoalNegotiation, CollaborativeProblemSolver
- ``AGIEconomicsBlackboardAdapter``     — TokenEconomics, BondingCurves, Reputation, GameTheory, Marketplace

Federated Learning:
- ``FederatedLearningBlackboardAdapter`` — FederatedManager, FederatedServer, FedAvgAggregator, Metrics

Safety (CRITICAL):
- ``SafetyBlackboardAdapter``           — ConstitutionalAI, EthicalVerification, TheoremProver, Governance

Integration & Streaming:
- ``RingsNetworkAdapter``              — Rings P2P Network, DID, Reputation
- ``BioInspiredAdapter``               — Evolutionary Optimizer, Homeostatic Regulator
- ``KnowledgeManagementAdapter``       — KnowledgeEngine, PredictiveSynthesizer, ContextualLearner
- ``GraphIntelligenceAdapter``         — CommunityDetection, FastToG, SchemaManager
- ``KennyGraphBlackboardAdapter``      — SSE streaming for graph intelligence results
- ``IntegrationsBlackboardBridge``     — LangChain-Memgraph, SQL-to-Graph, HyGM, MCP-Memgraph

Utilities
~~~~~~~~~

- ``wire_all(bb, *adapters)`` — Register adapters and wire event subscriptions
- ``production_sweep(bb, *adapters)`` — Run a produce() sweep across all adapters
"""

from __future__ import annotations

import logging
from typing import Any, List, Sequence

from .cognitive_synergy_adapter import CognitiveSynergyAdapter
from .consciousness_adapter import ConsciousnessAdapter
from .knowledge_graph_adapter import KnowledgeGraphAdapter
from .reasoning_adapter import ReasoningAdapter
from .bio_inspired_adapter import BioInspiredAdapter
from .graph_intelligence_adapter import GraphIntelligenceAdapter
from .knowledge_management_adapter import KnowledgeManagementAdapter
from .quantum_adapter import QuantumBlackboardAdapter
from .holographic_adapter import HolographicBlackboardAdapter
from .neuromorphic_adapter import NeuromorphicBlackboardAdapter
from .bci_adapter import BCIBlackboardAdapter
from .rings_adapter import RingsNetworkAdapter
from .compute_adapter import ComputeBlackboardAdapter
from .distributed_training_adapter import DistributedTrainingAdapter
from .vectordb_adapter import VectorDBBlackboardAdapter
from .blockchain_adapter import BlockchainBlackboardAdapter
from .reproducibility_adapter import ReproducibilityBlackboardAdapter
from .vla_adapter import VLABlackboardAdapter
from .kenny_graph_adapter import KennyGraphBlackboardAdapter
from .integrations_bridge_adapter import IntegrationsBlackboardBridge
from .agi_communication_adapter import AGICommunicationBlackboardAdapter
from .agi_economics_adapter import AGIEconomicsBlackboardAdapter
from .federated_adapter import FederatedLearningBlackboardAdapter
from .safety_adapter import SafetyBlackboardAdapter
from .async_adapter_base import AsyncAdapterBase

logger = logging.getLogger(__name__)

__all__ = [
    # Core adapters
    "ConsciousnessAdapter",
    "KnowledgeGraphAdapter",
    "CognitiveSynergyAdapter",
    "ReasoningAdapter",
    # Infrastructure adapters
    "ComputeBlackboardAdapter",
    "DistributedTrainingAdapter",
    "VectorDBBlackboardAdapter",
    "BlockchainBlackboardAdapter",
    # Research & optimization adapters
    "ReproducibilityBlackboardAdapter",
    "VLABlackboardAdapter",
    # Quantum adapters
    "QuantumBlackboardAdapter",
    # Holographic adapters
    "HolographicBlackboardAdapter",
    # Neuromorphic & BCI adapters
    "NeuromorphicBlackboardAdapter",
    "BCIBlackboardAdapter",
    # AGI Communication & Economics adapters
    "AGICommunicationBlackboardAdapter",
    "AGIEconomicsBlackboardAdapter",
    # Federated Learning adapters
    "FederatedLearningBlackboardAdapter",
    # Safety adapters (CRITICAL)
    "SafetyBlackboardAdapter",
    # Integration & streaming adapters
    "RingsNetworkAdapter",
    "BioInspiredAdapter",
    "KnowledgeManagementAdapter",
    "GraphIntelligenceAdapter",
    "KennyGraphBlackboardAdapter",
    "IntegrationsBlackboardBridge",
    # Base classes
    "AsyncAdapterBase",
    # Utilities
    "wire_all",
    "production_sweep",
]


def wire_all(
    blackboard: Any,
    *adapters: Any,
) -> None:
    """Register adapters with the blackboard and wire event subscriptions.

    For each adapter:

    1. Calls ``blackboard.register_module(adapter)``
    2. Wires ``set_event_handler`` to ``blackboard.event_bus.emit``
    3. Subscribes the adapter's ``handle_event`` to relevant event patterns

    Parameters
    ----------
    blackboard : CognitiveBlackboard
        The shared blackboard instance.
    *adapters :
        Adapter instances to register.
    """
    bus = blackboard.event_bus

    for adapter in adapters:
        # 1. Register
        try:
            blackboard.register_module(adapter)
        except Exception:
            logger.warning(
                "Failed to register adapter %s",
                getattr(adapter, "MODULE_NAME", type(adapter).__name__),
                exc_info=True,
            )
            continue

        # 2. Wire event emitter (adapter → bus)
        if hasattr(adapter, "set_event_handler"):
            adapter.set_event_handler(bus.emit)

        # 3. Wire event listener (bus → adapter)
        if hasattr(adapter, "handle_event"):
            info = adapter.module_info
            # Subscribe to all topics this adapter consumes
            for topic in info.topics_consumed:
                bus.subscribe(
                    pattern=f"{topic}.*",
                    handler=adapter.handle_event,
                    source_filter=None,  # Listen to all sources
                )

        logger.info(
            "Wired adapter: %s",
            getattr(adapter, "MODULE_NAME", type(adapter).__name__),
        )


def production_sweep(
    blackboard: Any,
    *adapters: Any,
) -> List[str]:
    """Run a production sweep — call produce() on each adapter and post results.

    Returns a list of entry IDs posted.
    """
    all_ids: List[str] = []

    for adapter in adapters:
        if not hasattr(adapter, "produce"):
            continue

        try:
            entries = adapter.produce()
        except Exception:
            logger.warning(
                "produce() failed for %s",
                getattr(adapter, "MODULE_NAME", type(adapter).__name__),
                exc_info=True,
            )
            continue

        if entries:
            ids = blackboard.post_many(list(entries))
            all_ids.extend(ids)

    return all_ids
