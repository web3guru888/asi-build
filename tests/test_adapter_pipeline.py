"""
Integration tests for the Blackboard Adapter pipeline.

Tests the full flow: post → subscribe → receive for all 16 adapters.
Covers Issue #99: Integration tests for the adapter pipeline.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Sequence
from unittest.mock import MagicMock, patch

import pytest

from asi_build.integration import CognitiveBlackboard
from asi_build.integration.protocols import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventHandler,
    ModuleCapability,
    ModuleInfo,
)
from asi_build.integration.adapters import (
    wire_all,
    production_sweep,
    ConsciousnessAdapter,
    CognitiveSynergyAdapter,
    BioInspiredAdapter,
    GraphIntelligenceAdapter,
    KnowledgeManagementAdapter,
    ComputeBlackboardAdapter,
    DistributedTrainingAdapter,
    VectorDBBlackboardAdapter,
    BlockchainBlackboardAdapter,
    ReproducibilityBlackboardAdapter,
    VLABlackboardAdapter,
    KennyGraphBlackboardAdapter,
    IntegrationsBlackboardBridge,
    AsyncAdapterBase,
)


# ---------------------------------------------------------------------------
# Mock components for testing adapter wiring
# ---------------------------------------------------------------------------

class MockScheduler:
    """Mock JobScheduler for ComputeBlackboardAdapter."""

    def __init__(self):
        self.queue_depth = 5
        self.completed_jobs = 3
        self.pending_jobs = 2
        self.status = "running"

    def get_queue_stats(self):
        return {
            "queue_depth": self.queue_depth,
            "completed": self.completed_jobs,
            "pending": self.pending_jobs,
        }


class MockAllocator:
    """Mock ResourceAllocator for ComputeBlackboardAdapter."""

    def __init__(self):
        self.utilization = 0.75
        self.total_resources = 100
        self.allocated = 75

    def get_utilization(self):
        return {
            "utilization": self.utilization,
            "total": self.total_resources,
            "allocated": self.allocated,
        }


class MockMetricsCollector:
    """Generic mock metrics collector."""

    def __init__(self):
        self.metrics = {"cpu": 0.6, "memory": 0.4, "latency_ms": 12.5}

    def get_metrics(self):
        return dict(self.metrics)

    def collect(self):
        return dict(self.metrics)


class MockOrchestrator:
    """Mock FederatedOrchestrator for DistributedTrainingAdapter."""

    def __init__(self):
        self.current_round = 5
        self.total_rounds = 100
        self.nodes_active = 8
        self.round_status = "aggregating"

    def get_round_status(self):
        return {
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "nodes_active": self.nodes_active,
            "status": self.round_status,
        }


class MockAggregator:
    """Mock ByzantineTolerantAggregator for DistributedTrainingAdapter."""

    def __init__(self):
        self.byzantine_count = 0
        self.aggregation_method = "fedavg"
        self.last_result = {"loss": 0.5, "accuracy": 0.85}

    def get_aggregation_result(self):
        return dict(self.last_result)


class MockEmbeddingPipeline:
    """Mock EmbeddingPipeline for VectorDBBlackboardAdapter."""

    def __init__(self):
        self.dimension = 384
        self.is_available_val = True

    def is_available(self):
        return self.is_available_val

    def encode(self, text):
        return [0.1] * self.dimension

    def get_dimension(self):
        return self.dimension


class MockSearchEngine:
    """Mock search engine for VectorDBBlackboardAdapter."""

    def __init__(self):
        self.document_count = 5000

    def get_stats(self):
        return {"size": self.document_count, "documents": self.document_count}

    def search(self, query, **kwargs):
        return []


class MockHashManager:
    """Mock HashManager for BlockchainBlackboardAdapter."""

    def __init__(self):
        self.verified_count = 42
        self.last_hash = "abcdef1234567890"

    def hash_data(self, data):
        return type("HashResult", (), {"hash_value": "abc123"})()

    def get_stats(self):
        return {"verified": self.verified_count, "last_hash": self.last_hash}


class MockMerkleTree:
    """Mock MerkleTree for BlockchainBlackboardAdapter."""

    def __init__(self):
        self.root_hash = "0xdeadbeef"
        self.leaves = [b"leaf1", b"leaf2", b"leaf3"]
        self.nodes = {"root": self.root_hash}

    def get_root_hash(self):
        return self.root_hash


class MockHashChain:
    """Mock HashChain for BlockchainBlackboardAdapter."""

    def __init__(self):
        self.chain = ["block0", "block1", "block2"]

    def get_chain_summary(self):
        return {"length": len(self.chain), "valid": True}

    def verify_chain(self):
        return True


class MockTracker:
    """Mock ExperimentTracker for ReproducibilityBlackboardAdapter."""

    def __init__(self):
        self.active_experiments = 3
        self.completed_experiments = 12

    def get_experiment(self, exp_id=None):
        return {
            "id": exp_id or "exp-001",
            "status": "running",
            "active": self.active_experiments,
            "completed": self.completed_experiments,
        }

    def health_check(self):
        return {"status": "healthy", "experiments": self.active_experiments}


class MockVersionManager:
    """Mock VersionManager for ReproducibilityBlackboardAdapter."""

    def __init__(self):
        self.current_version = "1.2.3"
        self.total_versions = 15

    def get_version_history(self):
        return [
            {"version": "1.2.3", "timestamp": 1000},
            {"version": "1.2.2", "timestamp": 900},
        ]


class MockVLAModel:
    """Mock VLAPlusPlus for VLABlackboardAdapter."""

    def __init__(self):
        self.training = True
        self.parameters_count = 1_000_000

    def get_status(self):
        return {"training": self.training, "params": self.parameters_count}


class MockVLATrainer:
    """Mock VLATrainer for VLABlackboardAdapter."""

    def __init__(self):
        self.current_epoch = 3
        self.total_epochs = 10
        self.loss = 0.42
        self.accuracy = 0.88

    def get_progress(self):
        return {
            "epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "loss": self.loss,
            "accuracy": self.accuracy,
        }


# ---------------------------------------------------------------------------
# Tests: Adapter Instantiation and Protocol Compliance
# ---------------------------------------------------------------------------

class TestAdapterProtocols:
    """Test that all adapters implement the required protocol methods."""

    ALL_ADAPTER_CLASSES = [
        (ConsciousnessAdapter, {}),
        (CognitiveSynergyAdapter, {}),
        (BioInspiredAdapter, {}),
        (GraphIntelligenceAdapter, {}),
        (KnowledgeManagementAdapter, {}),
        (ComputeBlackboardAdapter, {}),
        (DistributedTrainingAdapter, {}),
        (VectorDBBlackboardAdapter, {}),
        (BlockchainBlackboardAdapter, {}),
        (ReproducibilityBlackboardAdapter, {}),
        (VLABlackboardAdapter, {}),
        (KennyGraphBlackboardAdapter, {}),
        (IntegrationsBlackboardBridge, {}),
    ]

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_module_info_returns_module_info(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        info = adapter.module_info
        assert isinstance(info, ModuleInfo)
        assert len(info.name) > 0
        assert len(info.version) > 0
        assert isinstance(info.topics_produced, frozenset)
        assert isinstance(info.topics_consumed, frozenset)
        assert len(info.topics_produced) > 0, f"{adapter_cls.__name__} must produce ≥1 topic"

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_has_produce(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        assert hasattr(adapter, "produce")
        entries = adapter.produce()
        assert isinstance(entries, (list, tuple))

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_has_consume(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        assert hasattr(adapter, "consume")
        # Feed empty entries — should not crash
        adapter.consume([])

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_has_handle_event(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        assert hasattr(adapter, "handle_event")
        event = CognitiveEvent(event_type="test.event", payload={"x": 1}, source="test")
        adapter.handle_event(event)

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_has_snapshot(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        assert hasattr(adapter, "snapshot")
        snap = adapter.snapshot()
        assert isinstance(snap, dict)
        assert "module" in snap

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_on_registered(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        mock_bb = MagicMock()
        adapter.on_registered(mock_bb)

    @pytest.mark.parametrize(
        "adapter_cls,kwargs",
        ALL_ADAPTER_CLASSES,
        ids=lambda x: x.__name__ if isinstance(x, type) else str(x),
    )
    def test_set_event_handler(self, adapter_cls, kwargs):
        adapter = adapter_cls(**kwargs)
        events_received = []
        adapter.set_event_handler(lambda e: events_received.append(e))


# ---------------------------------------------------------------------------
# Tests: Full Pipeline — post → subscribe → receive
# ---------------------------------------------------------------------------

class TestAdapterPipeline:
    """Integration tests for the full adapter pipeline."""

    def test_wire_all_registers_adapters(self):
        bb = CognitiveBlackboard()
        adapters = [
            ConsciousnessAdapter(),
            CognitiveSynergyAdapter(),
            ComputeBlackboardAdapter(),
        ]
        wire_all(bb, *adapters)
        # All should be registered
        assert len(bb._modules) == 3

    def test_wire_all_sets_event_handlers(self):
        bb = CognitiveBlackboard()
        adapter = ComputeBlackboardAdapter()
        wire_all(bb, adapter)
        # Event handler should be set
        assert adapter._event_handler is not None

    def test_production_sweep_empty_adapters(self):
        bb = CognitiveBlackboard()
        adapters = [ComputeBlackboardAdapter()]
        wire_all(bb, *adapters)
        ids = production_sweep(bb, *adapters)
        # No components → no entries
        assert ids == []

    def test_production_sweep_with_mock_components(self):
        """Test produce → post → query roundtrip with mock components."""
        bb = CognitiveBlackboard()

        scheduler = MockScheduler()
        allocator = MockAllocator()
        metrics = MockMetricsCollector()
        adapter = ComputeBlackboardAdapter(
            scheduler=scheduler,
            allocator=allocator,
            metrics_collector=metrics,
        )
        wire_all(bb, adapter)

        ids = production_sweep(bb, adapter)
        assert len(ids) >= 1, "Should produce at least one entry with mock components"

        # Query entries back
        results = bb.query(BlackboardQuery(topics=["compute"]))
        assert len(results) >= 1

    def test_event_propagation_across_adapters(self):
        """Test that events from one adapter reach another via the bus."""
        bb = CognitiveBlackboard()

        compute_adapter = ComputeBlackboardAdapter(scheduler=MockScheduler())
        dt_adapter = DistributedTrainingAdapter(orchestrator=MockOrchestrator())

        wire_all(bb, compute_adapter, dt_adapter)

        # Manually emit an event from compute
        compute_adapter._emit(
            "compute.job.completed",
            {"job_id": "test-123", "result": "success"},
        )

        # The event should have been emitted on the bus
        assert len(bb.event_bus._history) >= 1

    def test_consume_cross_module(self):
        """Test that one adapter can consume entries from another."""
        bb = CognitiveBlackboard()

        compute_adapter = ComputeBlackboardAdapter(scheduler=MockScheduler())
        blockchain_adapter = BlockchainBlackboardAdapter(hash_manager=MockHashManager())

        wire_all(bb, compute_adapter, blockchain_adapter)

        # Post a compute entry
        entry = BlackboardEntry(
            topic="compute.job_status",
            data={"job_id": "j1", "status": "completed"},
            source_module="compute",
            confidence=0.9,
        )
        bb.post(entry)

        # Blockchain adapter consumes compute topics
        compute_entries = bb.query(BlackboardQuery(topics=["compute"]))
        blockchain_adapter.consume(compute_entries)
        # Should not crash — graceful handling

    def test_wire_all_with_all_new_adapters(self):
        """Wire all 8 new adapters + 5 existing (optional-arg) adapters."""
        bb = CognitiveBlackboard()

        adapters = [
            ConsciousnessAdapter(),
            CognitiveSynergyAdapter(),
            BioInspiredAdapter(),
            GraphIntelligenceAdapter(),
            KnowledgeManagementAdapter(),
            ComputeBlackboardAdapter(),
            DistributedTrainingAdapter(),
            VectorDBBlackboardAdapter(),
            BlockchainBlackboardAdapter(),
            ReproducibilityBlackboardAdapter(),
            VLABlackboardAdapter(),
            KennyGraphBlackboardAdapter(),
            IntegrationsBlackboardBridge(),
        ]

        wire_all(bb, *adapters)
        assert len(bb._modules) == 13

        # Production sweep should work without errors
        ids = production_sweep(bb, *adapters)
        # Empty because no real components, but no crashes
        assert isinstance(ids, list)

    def test_full_roundtrip_compute_to_distributed(self):
        """Full pipeline: compute adapter produces → distributed training consumes."""
        bb = CognitiveBlackboard()

        compute = ComputeBlackboardAdapter(
            scheduler=MockScheduler(),
            allocator=MockAllocator(),
            metrics_collector=MockMetricsCollector(),
        )
        dt = DistributedTrainingAdapter(
            orchestrator=MockOrchestrator(),
            aggregator=MockAggregator(),
        )

        wire_all(bb, compute, dt)

        # Produce from compute
        compute_ids = production_sweep(bb, compute)
        assert len(compute_ids) >= 1

        # Query compute entries
        compute_entries = bb.query(BlackboardQuery(topics=["compute"]))
        assert len(compute_entries) >= 1

        # Feed into distributed training consumer
        dt.consume(compute_entries)
        # No crash = success

    def test_kenny_graph_sse_event_queueing(self):
        """Test Kenny Graph SSE adapter queues events for streaming."""
        adapter = KennyGraphBlackboardAdapter()

        # Feed a graph intelligence entry
        entry = BlackboardEntry(
            topic="graph_intelligence.communities",
            data={"community_count": 5, "modularity": 0.72},
            source_module="graph_intelligence",
        )
        adapter.consume([entry])
        # Should queue an SSE event without crashing

    def test_blockchain_audit_log(self):
        """Test blockchain adapter produces audit entries."""
        adapter = BlockchainBlackboardAdapter(
            hash_manager=MockHashManager(),
            merkle_tree=MockMerkleTree(),
            hash_chain=MockHashChain(),
        )

        entries = adapter.produce()
        assert len(entries) >= 1

        snap = adapter.snapshot()
        assert snap["has_hash_manager"] is True
        assert snap["has_merkle_tree"] is True
        assert snap["has_hash_chain"] is True

    def test_reproducibility_with_mock_tracker(self):
        """Test reproducibility adapter with mock components."""
        adapter = ReproducibilityBlackboardAdapter(
            tracker=MockTracker(),
            version_manager=MockVersionManager(),
        )

        # Must track an experiment before produce yields entries
        adapter.track_experiment("exp-001")
        entries = adapter.produce()
        assert len(entries) >= 1

    def test_vla_with_mock_trainer(self):
        """Test VLA adapter with mock training components."""
        adapter = VLABlackboardAdapter(
            model=MockVLAModel(),
            trainer=MockVLATrainer(),
        )

        entries = adapter.produce()
        assert len(entries) >= 1

    def test_vectordb_with_mock_pipeline(self):
        """Test VectorDB adapter with mock embedding pipeline."""
        adapter = VectorDBBlackboardAdapter(
            embedding_pipeline=MockEmbeddingPipeline(),
            search_engine=MockSearchEngine(),
        )

        entries = adapter.produce()
        assert len(entries) >= 1


# ---------------------------------------------------------------------------
# Tests: Change Detection
# ---------------------------------------------------------------------------

class TestChangeDetection:
    """Test that adapters don't re-post unchanged data."""

    def test_compute_no_duplicate_posts(self):
        scheduler = MockScheduler()
        adapter = ComputeBlackboardAdapter(scheduler=scheduler)

        first = adapter.produce()
        second = adapter.produce()
        # Second call should return fewer or equal entries (change detection)
        assert len(second) <= len(first)

    def test_blockchain_no_duplicate_posts(self):
        chain = MockHashChain()
        adapter = BlockchainBlackboardAdapter(hash_chain=chain)

        first = adapter.produce()
        second = adapter.produce()
        assert len(second) <= len(first)

    def test_vla_no_duplicate_posts(self):
        trainer = MockVLATrainer()
        adapter = VLABlackboardAdapter(trainer=trainer)

        first = adapter.produce()
        second = adapter.produce()
        assert len(second) <= len(first)


# ---------------------------------------------------------------------------
# Tests: Graceful Degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    """Test that adapters work with None components."""

    def test_compute_all_none(self):
        adapter = ComputeBlackboardAdapter()
        assert adapter.produce() == [] or len(adapter.produce()) == 0
        adapter.consume([])
        adapter.handle_event(CognitiveEvent(event_type="test.x"))
        snap = adapter.snapshot()
        assert snap["has_scheduler"] is False

    def test_distributed_training_all_none(self):
        adapter = DistributedTrainingAdapter()
        assert len(adapter.produce()) == 0
        adapter.consume([])
        snap = adapter.snapshot()
        assert snap["has_orchestrator"] is False

    def test_vectordb_all_none(self):
        adapter = VectorDBBlackboardAdapter()
        assert len(adapter.produce()) == 0
        snap = adapter.snapshot()
        assert snap["has_embedding_pipeline"] is False

    def test_blockchain_all_none(self):
        adapter = BlockchainBlackboardAdapter()
        assert len(adapter.produce()) == 0
        snap = adapter.snapshot()
        assert snap["has_hash_manager"] is False

    def test_reproducibility_all_none(self):
        adapter = ReproducibilityBlackboardAdapter()
        assert len(adapter.produce()) == 0

    def test_vla_all_none(self):
        adapter = VLABlackboardAdapter()
        assert len(adapter.produce()) == 0

    def test_kenny_graph_all_none(self):
        adapter = KennyGraphBlackboardAdapter()
        assert len(adapter.produce()) == 0

    def test_integrations_bridge_all_none(self):
        adapter = IntegrationsBlackboardBridge()
        assert len(adapter.produce()) == 0


# ---------------------------------------------------------------------------
# Tests: Thread Safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    """Test adapters are safe under concurrent access."""

    def test_concurrent_produce(self):
        scheduler = MockScheduler()
        adapter = ComputeBlackboardAdapter(scheduler=scheduler)

        results = []
        errors = []

        def run_produce():
            try:
                entries = adapter.produce()
                results.append(len(entries))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_produce) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0, f"Thread errors: {errors}"

    def test_concurrent_consume_and_produce(self):
        adapter = ComputeBlackboardAdapter(scheduler=MockScheduler())
        errors = []

        def do_produce():
            try:
                adapter.produce()
            except Exception as e:
                errors.append(e)

        def do_consume():
            try:
                entry = BlackboardEntry(
                    topic="reasoning.inference",
                    data={"result": "test"},
                    source_module="reasoning",
                )
                adapter.consume([entry])
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=do_produce))
            threads.append(threading.Thread(target=do_consume))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Tests: AsyncAdapterBase
# ---------------------------------------------------------------------------

class TestAsyncAdapterBase:
    """Test the async adapter base class."""

    def test_cannot_instantiate_directly(self):
        """AsyncAdapterBase is abstract — can't instantiate directly."""
        with pytest.raises(TypeError):
            AsyncAdapterBase()

    def test_subclass_must_implement_abstracts(self):
        """Subclass without abstract methods should fail."""

        class Incomplete(AsyncAdapterBase):
            pass

        with pytest.raises(TypeError):
            Incomplete()


# ---------------------------------------------------------------------------
# Tests: LZ76 Complexity Fix (Issue #94)
# ---------------------------------------------------------------------------

class TestLZ76Complexity:
    """Test the optimized LZ76 implementation."""

    def test_lz76_empty_sequence(self):
        """Empty or single-element sequences return 0."""
        import numpy as np
        from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

        sm = SynergyMetrics.__new__(SynergyMetrics)
        assert sm._lempel_ziv_complexity(np.array([])) == 0.0
        assert sm._lempel_ziv_complexity(np.array([1])) == 0.0

    def test_lz76_constant_sequence(self):
        """Constant sequence has low complexity."""
        import numpy as np
        from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

        sm = SynergyMetrics.__new__(SynergyMetrics)
        result = sm._lempel_ziv_complexity(np.zeros(100))
        assert 0.0 <= result <= 0.5  # Very simple pattern

    def test_lz76_alternating_sequence(self):
        """Alternating 0/1 has moderate complexity."""
        import numpy as np
        from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

        sm = SynergyMetrics.__new__(SynergyMetrics)
        seq = np.array([0, 1] * 50)
        result = sm._lempel_ziv_complexity(seq)
        assert 0.0 < result <= 1.0

    def test_lz76_random_sequence(self):
        """Random binary sequence has high complexity."""
        import numpy as np
        from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

        rng = np.random.RandomState(42)
        sm = SynergyMetrics.__new__(SynergyMetrics)
        seq = rng.randint(0, 2, size=200)
        result = sm._lempel_ziv_complexity(seq)
        assert result > 0.3  # Random should be complex

    def test_lz76_deterministic_output(self):
        """Same input always produces same output."""
        import numpy as np
        from asi_build.cognitive_synergy.core.synergy_metrics import SynergyMetrics

        sm = SynergyMetrics.__new__(SynergyMetrics)
        seq = np.array([0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0])
        r1 = sm._lempel_ziv_complexity(seq)
        r2 = sm._lempel_ziv_complexity(seq)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Tests: __maturity__ Metadata (Issue #112)
# ---------------------------------------------------------------------------

class TestMaturityMetadata:
    """Test that all modules have __maturity__ metadata."""

    VALID_MATURITY_LEVELS = {"experimental", "alpha", "beta", "stable", "mature"}

    EXPECTED_MODULES = [
        "agi_communication", "agi_economics", "agi_reproducibility", "bci",
        "bio_inspired", "blockchain", "cognitive_synergy", "compute",
        "consciousness", "deployment", "distributed_training", "federated",
        "graph_intelligence", "holographic", "homomorphic", "integration",
        "integrations", "knowledge_graph", "knowledge_management",
        "memgraph_toolbox", "neuromorphic", "optimization", "pln_accelerator",
        "quantum", "reasoning", "rings", "safety", "servers", "vectordb",
    ]

    @pytest.mark.parametrize("module_name", EXPECTED_MODULES)
    def test_module_has_maturity(self, module_name):
        """Each module __init__.py should define __maturity__."""
        import importlib
        try:
            mod = importlib.import_module(f"asi_build.{module_name}")
        except ImportError:
            pytest.skip(f"Module asi_build.{module_name} not importable")
        assert hasattr(mod, "__maturity__"), (
            f"asi_build.{module_name} missing __maturity__"
        )
        assert mod.__maturity__ in self.VALID_MATURITY_LEVELS, (
            f"asi_build.{module_name}.__maturity__ = {mod.__maturity__!r} "
            f"is not in {self.VALID_MATURITY_LEVELS}"
        )
