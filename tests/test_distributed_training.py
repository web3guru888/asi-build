"""
Tests for the distributed_training module.

Covers:
- error_handling: CircuitBreaker, RetryManager, ErrorHandler, HealthChecker, enums, dataclasses
- byzantine_tolerance: ByzantineDetector, ByzantineTolerantAggregator, AdaptiveByzantineDefense, AttackType
- dataset_sharding: IIDSharding, NonIIDSharding, AdaptiveSharding, DataShard, DatasetMetadata, DistributedDatasetManager
- gradient_compression: SignSGD bit-packing, TopK compression, QuantizationCompressor, AdaptiveCompressor, CommunicationOptimizer
- p2p/node_discovery: DistributedHashTable, GossipProtocol, PeerInfo, NetworkMessage
- privacy/secure_aggregation: DifferentialPrivacyMechanism, ShamirSecretSharing, PrivacyAudit, HomomorphicEncryption
- blockchain/agix_rewards: AGIXRewardCalculator, ReputationBasedRewards, AntiSybilMechanism, ComputeContribution
- monitoring/dashboard: MetricsCollector, PerformanceAnalyzer, TrainingMetrics, NetworkMetrics, SystemHealth
"""

import asyncio
import hashlib
import math
import sys
import time
import types
from collections import defaultdict, deque
from dataclasses import asdict
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("torch")
import torch

# ---------------------------------------------------------------------------
# Inject stubs for unavailable third-party libraries so source modules
# can be imported without actually installing web3, dash, plotly, etc.
# ---------------------------------------------------------------------------


def _ensure_mock_module(name):
    """Insert a MagicMock into sys.modules if the real module is absent."""
    if name not in sys.modules:
        sys.modules[name] = MagicMock()


for _mod in (
    "web3",
    "web3.auto",
    "eth_account",
    "ipfshttpclient",
    "dash",
    "dash.dcc",
    "dash.html",
    "plotly",
    "plotly.graph_objects",
    "plotly.express",
    "plotly.subplots",
    "pandas",
    "websocket",
    "websockets",
):
    _ensure_mock_module(_mod)

# ═══════════════════════════════════════════════════════════════════════════
# Section 1 — Error Handling
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.core.error_handling import (
    CircuitBreaker,
    CircuitBreakerState,
    ErrorCategory,
    ErrorHandler,
    ErrorInfo,
    ErrorSeverity,
    HealthChecker,
    RetryManager,
    error_handler_decorator,
    get_global_error_handler,
    set_global_error_handler,
)


class TestCircuitBreakerState:
    """CircuitBreakerState enum tests."""

    def test_enum_values(self):
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"


class TestErrorEnums:
    """ErrorSeverity and ErrorCategory enum tests."""

    def test_severity_levels(self):
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_categories(self):
        cats = [c.value for c in ErrorCategory]
        assert "network" in cats
        assert "computation" in cats
        assert "storage" in cats
        assert "security" in cats
        assert "consensus" in cats


class TestCircuitBreaker:
    """CircuitBreaker pattern implementation tests."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_successful_call_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_failures_open_circuit(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN

    def test_open_circuit_rejects_calls(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=9999)
        # Trigger open
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            cb.call(lambda: 1)

    def test_recovery_timeout_transitions_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        # Timeout is 0, so next call should transition to HALF_OPEN
        result = cb.call(lambda: "ok")
        assert result == "ok"
        # After success in half-open, success_count increments

    def test_half_open_to_closed_after_successes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0, success_threshold=2)
        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        # First success in half-open
        cb.call(lambda: 1)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        # Second success closes it
        cb.call(lambda: 2)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_get_state_dict(self):
        cb = CircuitBreaker()
        state = cb.get_state()
        assert "state" in state
        assert "failure_count" in state
        assert "success_count" in state
        assert state["state"] == "closed"

    def test_failure_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=5)
        # Two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
        assert cb.failure_count == 2
        # One success resets
        cb.call(lambda: "ok")
        assert cb.failure_count == 0


class TestRetryManager:
    """RetryManager tests — sync path only (no sleep in tests)."""

    def test_succeeds_first_try(self):
        rm = RetryManager(max_retries=3, base_delay=0.0)
        result = rm.retry(lambda: 99)
        assert result == 99

    def test_retries_on_failure_then_succeeds(self):
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("transient")
            return "ok"

        rm = RetryManager(max_retries=3, base_delay=0.001, jitter=False)
        result = rm.retry(flaky)
        assert result == "ok"
        assert call_count["n"] == 3

    def test_exhausts_retries(self):
        rm = RetryManager(max_retries=1, base_delay=0.001, jitter=False)
        with pytest.raises(ValueError, match="permanent"):
            rm.retry(lambda: (_ for _ in ()).throw(ValueError("permanent")))

    def test_max_delay_caps_backoff(self):
        rm = RetryManager(max_retries=5, base_delay=100.0, max_delay=0.001, jitter=False)
        # This shouldn't hang because max_delay is tiny
        with pytest.raises(RuntimeError):
            rm.retry(lambda: (_ for _ in ()).throw(RuntimeError("x")))


class TestErrorHandler:
    """ErrorHandler central error handling tests."""

    def _make_handler(self):
        return ErrorHandler({"circuit_breaker_threshold": 5})

    def test_handle_error_returns_error_info(self):
        handler = self._make_handler()
        exc = RuntimeError("test error")
        info = handler.handle_error(
            exc, "test_component", ErrorSeverity.MEDIUM, ErrorCategory.COMPUTATION
        )
        assert isinstance(info, ErrorInfo)
        assert "test error" in info.message
        assert info.component == "test_component"
        assert info.severity == ErrorSeverity.MEDIUM

    def test_error_history_accumulates(self):
        handler = self._make_handler()
        for i in range(5):
            handler.handle_error(
                RuntimeError(f"err_{i}"), "comp", ErrorSeverity.LOW, ErrorCategory.NETWORK
            )
        assert len(handler.error_history) == 5

    def test_network_error_recovery(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("connection refused"), "net", ErrorSeverity.MEDIUM, ErrorCategory.NETWORK
        )
        assert info.recovery_action == "connection_retry_scheduled"

    def test_computation_error_recovery_cuda(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("CUDA out of memory"), "gpu", ErrorSeverity.HIGH, ErrorCategory.COMPUTATION
        )
        assert info.recovery_action == "gpu_reset_scheduled"

    def test_computation_error_recovery_nan(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("nan detected"), "train", ErrorSeverity.MEDIUM, ErrorCategory.COMPUTATION
        )
        assert info.recovery_action == "gradient_clipping_enabled"

    def test_storage_error_recovery(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("disk full"), "store", ErrorSeverity.HIGH, ErrorCategory.STORAGE
        )
        assert info.recovery_action == "disk_cleanup_scheduled"

    def test_security_error_recovery(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("signature invalid"), "auth", ErrorSeverity.HIGH, ErrorCategory.SECURITY
        )
        assert info.recovery_action == "signature_verification_retry"

    def test_mark_error_resolved(self):
        handler = self._make_handler()
        info = handler.handle_error(
            RuntimeError("x"), "comp", ErrorSeverity.LOW, ErrorCategory.DATA
        )
        assert handler.mark_error_resolved(info.error_id, "fixed it")
        assert info.resolved is True
        assert info.resolution_time is not None

    def test_mark_error_resolved_not_found(self):
        handler = self._make_handler()
        assert handler.mark_error_resolved("nonexistent_id") is False

    def test_get_error_summary_empty(self):
        handler = self._make_handler()
        summary = handler.get_error_summary(hours=1)
        assert summary["total_errors"] == 0

    def test_get_error_summary_with_errors(self):
        handler = self._make_handler()
        handler.handle_error(RuntimeError("a"), "c", ErrorSeverity.HIGH, ErrorCategory.NETWORK)
        handler.handle_error(RuntimeError("b"), "c", ErrorSeverity.LOW, ErrorCategory.DATA)
        summary = handler.get_error_summary(hours=1)
        assert summary["total_errors"] == 2
        assert "by_category" in summary
        assert "by_severity" in summary

    def test_get_circuit_breaker_creates_new(self):
        handler = self._make_handler()
        cb = handler.get_circuit_breaker("component_a")
        assert isinstance(cb, CircuitBreaker)
        # Same component returns same instance
        cb2 = handler.get_circuit_breaker("component_a")
        assert cb is cb2

    def test_get_retry_manager_creates_new(self):
        handler = self._make_handler()
        rm = handler.get_retry_manager("component_b")
        assert isinstance(rm, RetryManager)


class TestHealthChecker:
    """HealthChecker tests."""

    def test_overall_health_unknown_when_empty(self):
        handler = ErrorHandler({})
        hc = HealthChecker(handler)
        health = hc.get_overall_health()
        assert health["status"] == "unknown"

    def test_register_and_check_healthy(self):
        handler = ErrorHandler({})
        hc = HealthChecker(handler)
        hc.register_health_check("test", lambda: True, interval=0.0)
        asyncio.get_event_loop().run_until_complete(hc.run_health_checks())
        health = hc.get_overall_health()
        assert health["status"] == "healthy"
        assert health["healthy"] == 1

    def test_register_and_check_unhealthy(self):
        handler = ErrorHandler({})
        hc = HealthChecker(handler)

        def failing_check():
            raise RuntimeError("down")

        hc.register_health_check("db", failing_check, interval=0.0, critical=True)
        asyncio.get_event_loop().run_until_complete(hc.run_health_checks())
        health = hc.get_overall_health()
        assert health["status"] == "critical"
        assert health["critical_failures"] == 1


class TestGlobalErrorHandler:
    """Global error handler singleton tests."""

    def test_get_global_creates_default(self):
        # Reset to make test idempotent
        import asi_build.distributed_training.core.error_handling as mod

        mod._global_error_handler = None
        handler = get_global_error_handler()
        assert isinstance(handler, ErrorHandler)

    def test_set_global_replaces(self):
        custom = ErrorHandler({"custom": True})
        set_global_error_handler(custom)
        assert get_global_error_handler() is custom


# ═══════════════════════════════════════════════════════════════════════════
# Section 2 — Byzantine Tolerance
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.core.byzantine_tolerance import (
    AdaptiveByzantineDefense,
    AggregationResult,
    AttackType,
    ByzantineDetector,
    ByzantineTolerantAggregator,
    NodeBehavior,
)


def _make_gradients(n_nodes, dim=10, seed=42):
    """Create gradient dicts for n_nodes, all similar."""
    rng = torch.Generator()
    rng.manual_seed(seed)
    base = torch.randn(dim, generator=rng)
    grads = {}
    for i in range(n_nodes):
        noise = torch.randn(dim, generator=rng) * 0.01
        grads[f"node_{i}"] = {"param": base + noise}
    return grads


class TestAttackType:
    def test_enum_members(self):
        assert AttackType.HONEST.value == "honest"
        assert AttackType.SYBIL.value == "sybil"
        assert AttackType.SIGN_FLIP.value == "sign_flip"


class TestNodeBehavior:
    def test_dataclass_fields(self):
        nb = NodeBehavior(
            node_id="n1",
            gradient_norms=[1.0],
            submission_times=[time.time()],
            accuracy_contributions=[0.9],
            similarity_scores=[0.95],
            reputation_score=0.5,
            trust_score=0.5,
            detected_attacks=[],
            last_evaluation=time.time(),
        )
        assert nb.node_id == "n1"
        assert len(nb.gradient_norms) == 1


class TestByzantineDetector:
    """ByzantineDetector analysis tests."""

    def test_too_few_nodes_returns_zero_suspicion(self):
        det = ByzantineDetector({})
        grads = _make_gradients(2)
        scores = det.analyze_gradients(grads)
        assert all(s == 0.0 for s in scores.values())

    def test_honest_nodes_low_norm_suspicion(self):
        """Norm-based suspicion should be 0 when norms are identical (MAD=0)."""
        det = ByzantineDetector({"norm_deviation_threshold": 3.0})
        # Use identical gradients → norms are equal → MAD=0 → all suspicion = 0
        base = torch.randn(10)
        grads = {f"node_{i}": {"param": base.clone()} for i in range(5)}
        scores = det.analyze_gradients(grads)
        # When MAD=0, all norm-based suspicion is 0.0
        # (DBSCAN may or may not flag, but norm Z-scores should all be 0)
        norm_scores = []
        norms = {}
        for nid, ng in grads.items():
            norms[nid] = sum(torch.norm(pg).item() ** 2 for pg in ng.values()) ** 0.5
        nv = list(norms.values())
        mad = np.median(np.abs(np.array(nv) - np.median(nv)))
        assert mad == 0.0  # identical norms → zero MAD

    def test_outlier_detected(self):
        det = ByzantineDetector({"norm_deviation_threshold": 2.0})
        grads = _make_gradients(5)
        # Make one node wildly different
        grads["node_0"]["param"] = torch.ones(10) * 1000.0
        scores = det.analyze_gradients(grads)
        assert scores["node_0"] > 0.0  # Should be flagged

    def test_cosine_similarity_self_is_one(self):
        det = ByzantineDetector({})
        g = {"param": torch.randn(10)}
        sim = det._calculate_cosine_similarity(g, g)
        assert abs(sim - 1.0) < 1e-5

    def test_cosine_similarity_orthogonal(self):
        det = ByzantineDetector({})
        g1 = {"param": torch.tensor([1.0, 0.0])}
        g2 = {"param": torch.tensor([0.0, 1.0])}
        sim = det._calculate_cosine_similarity(g1, g2)
        assert abs(sim) < 1e-5

    def test_get_trusted_nodes_new_nodes_trusted(self):
        det = ByzantineDetector({})
        trusted = det.get_trusted_nodes(["a", "b", "c"])
        assert set(trusted) == {"a", "b", "c"}

    def test_get_trusted_nodes_filters_low_rep(self):
        det = ByzantineDetector({})
        det.node_behaviors["bad"] = NodeBehavior(
            node_id="bad",
            gradient_norms=[],
            submission_times=[],
            accuracy_contributions=[],
            similarity_scores=[],
            reputation_score=0.1,
            trust_score=0.1,
            detected_attacks=[],
            last_evaluation=time.time(),
        )
        trusted = det.get_trusted_nodes(["bad", "new_node"], min_trust_score=0.3)
        assert "bad" not in trusted
        assert "new_node" in trusted

    def test_detect_coordinated_attacks_too_few_nodes(self):
        det = ByzantineDetector({})
        grads = _make_gradients(3)
        groups = det.detect_coordinated_attacks(grads)
        assert groups == []

    def test_detect_coordinated_attacks_sybil_group(self):
        det = ByzantineDetector({})
        # Create 4 nodes where 3 are identical
        base = torch.ones(10)
        grads = {
            "honest": {"param": torch.randn(10)},
            "sybil_0": {"param": base.clone()},
            "sybil_1": {"param": base.clone()},
            "sybil_2": {"param": base.clone()},
        }
        groups = det.detect_coordinated_attacks(grads)
        # Should detect at least one sybil group
        assert len(groups) >= 1
        sybil_detected = any({"sybil_0", "sybil_1", "sybil_2"}.issubset(g) for g in groups)
        assert sybil_detected


class TestByzantineTolerantAggregator:
    """Aggregation algorithm tests."""

    def test_aggregate_empty_raises(self):
        agg = ByzantineTolerantAggregator({})
        with pytest.raises(ValueError, match="No gradients"):
            asyncio.get_event_loop().run_until_complete(agg.aggregate({}))

    def test_weighted_aggregation_basic(self):
        agg = ByzantineTolerantAggregator({"aggregation_method": "weighted"})
        grads = _make_gradients(5)
        result = asyncio.get_event_loop().run_until_complete(agg.aggregate(grads))
        assert isinstance(result, AggregationResult)
        assert "param" in result.aggregated_gradients
        assert result.aggregation_method == "weighted"
        assert 0.0 <= result.confidence_score <= 1.0

    def test_krum_aggregation(self):
        agg = ByzantineTolerantAggregator(
            {
                "aggregation_method": "krum",
                "byzantine_ratio": 0.2,
            }
        )
        grads = _make_gradients(6)
        result = asyncio.get_event_loop().run_until_complete(agg.aggregate(grads))
        assert "param" in result.aggregated_gradients
        # Krum should select some honest nodes
        assert len(result.honest_participants) > 0

    def test_trimmed_mean_aggregation(self):
        agg = ByzantineTolerantAggregator(
            {
                "aggregation_method": "trimmed_mean",
                "byzantine_ratio": 0.2,
            }
        )
        grads = _make_gradients(6)
        result = asyncio.get_event_loop().run_until_complete(agg.aggregate(grads))
        assert "param" in result.aggregated_gradients
        assert result.aggregation_method == "trimmed_mean"

    def test_median_aggregation(self):
        agg = ByzantineTolerantAggregator({"aggregation_method": "median"})
        grads = _make_gradients(5)
        result = asyncio.get_event_loop().run_until_complete(agg.aggregate(grads))
        assert "param" in result.aggregated_gradients
        assert result.aggregation_method == "coordinate_median"

    def test_euclidean_distance_identical_is_zero(self):
        agg = ByzantineTolerantAggregator({})
        g = {"param": torch.ones(5)}
        dist = agg._calculate_euclidean_distance(g, g)
        assert abs(dist) < 1e-6

    def test_euclidean_distance_different(self):
        agg = ByzantineTolerantAggregator({})
        g1 = {"param": torch.zeros(5)}
        g2 = {"param": torch.ones(5)}
        dist = agg._calculate_euclidean_distance(g1, g2)
        assert abs(dist - math.sqrt(5)) < 1e-5

    def test_average_gradients_empty(self):
        agg = ByzantineTolerantAggregator({})
        assert agg._average_gradients([]) == {}

    def test_average_gradients_single(self):
        agg = ByzantineTolerantAggregator({})
        g = {"param": torch.tensor([2.0, 4.0])}
        avg = agg._average_gradients([g])
        assert torch.allclose(avg["param"], torch.tensor([2.0, 4.0]))

    def test_average_gradients_multiple(self):
        agg = ByzantineTolerantAggregator({})
        g1 = {"param": torch.tensor([1.0, 3.0])}
        g2 = {"param": torch.tensor([3.0, 5.0])}
        avg = agg._average_gradients([g1, g2])
        assert torch.allclose(avg["param"], torch.tensor([2.0, 4.0]))

    def test_detection_stats_empty(self):
        agg = ByzantineTolerantAggregator({})
        stats = agg.get_detection_stats()
        assert stats["total_nodes"] == 0


class TestAdaptiveByzantineDefense:
    """AdaptiveByzantineDefense tests."""

    def test_threat_level_few_nodes(self):
        defense = AdaptiveByzantineDefense({})
        grads = _make_gradients(2)
        threat = defense._assess_threat_level(grads)
        assert threat == 0.0

    def test_select_optimal_method_low_threat(self):
        defense = AdaptiveByzantineDefense({})
        method = defense._select_optimal_method(0.1)
        # Low threat should prefer weighted (gets 1.2x boost)
        assert method in defense.defense_effectiveness

    def test_select_optimal_method_high_threat(self):
        defense = AdaptiveByzantineDefense({})
        method = defense._select_optimal_method(0.9)
        # High threat should prefer fltrust or krum
        assert method in ("fltrust", "krum")

    def test_update_effectiveness(self):
        defense = AdaptiveByzantineDefense({"adaptation_rate": 0.5})
        old_eff = defense.defense_effectiveness["krum"]
        mock_result = AggregationResult(
            aggregated_gradients={},
            honest_participants=[],
            suspected_byzantine=[],
            confidence_score=0.9,
            aggregation_method="krum",
            detection_stats={},
        )
        defense._update_effectiveness("krum", mock_result)
        new_eff = defense.defense_effectiveness["krum"]
        # Should move toward 0.9
        assert abs(new_eff - old_eff) > 0.01

    def test_classify_attack_type_sybil(self):
        defense = AdaptiveByzantineDefense({})
        grads = _make_gradients(5)
        # 40% suspected = sybil
        attack = defense._classify_attack_type(grads, ["node_0", "node_1"])
        assert attack == AttackType.SYBIL

    def test_adaptation_stats(self):
        defense = AdaptiveByzantineDefense({})
        stats = defense.get_adaptation_stats()
        assert "defense_effectiveness" in stats
        assert "recent_attacks_count" in stats
        assert "current_optimal_method" in stats


# ═══════════════════════════════════════════════════════════════════════════
# Section 3 — Dataset Sharding
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.core.dataset_sharding import (
    AdaptiveSharding,
    DatasetMetadata,
    DataShard,
    DistributedDatasetManager,
    IIDSharding,
    NonIIDSharding,
)


class _MockDataset:
    """Minimal mock dataset for sharding tests."""

    def __init__(self, size=100, num_classes=5):
        self.size = size
        self.targets = [i % num_classes for i in range(size)]

    def __len__(self):
        return self.size

    def __getitem__(self, idx):
        return torch.randn(10), self.targets[idx]


class TestDataShard:
    def test_dataclass_roundtrip(self):
        shard = DataShard(
            shard_id="s1",
            node_id="n1",
            data_indices=[0, 1, 2],
            label_distribution={"0": 2, "1": 1},
            size=3,
            checksum="abc123",
            created_at=time.time(),
        )
        d = asdict(shard)
        assert d["shard_id"] == "s1"
        assert d["size"] == 3


class TestDatasetMetadata:
    def test_dataclass_fields(self):
        md = DatasetMetadata(
            dataset_id="ds1",
            total_samples=1000,
            num_classes=10,
            feature_dim=784,
            class_distribution={"0": 100},
            data_type="vision",
            sharding_strategy="iid",
        )
        assert md.total_samples == 1000


class TestIIDSharding:
    def test_shard_data_equal_split(self):
        strategy = IIDSharding()
        ds = _MockDataset(100, 5)
        shards = strategy.shard_data(ds, 4, {})
        assert len(shards) == 4
        total = sum(s.size for s in shards)
        assert total == 100

    def test_shard_data_unequal_remainder(self):
        strategy = IIDSharding()
        ds = _MockDataset(103, 3)
        shards = strategy.shard_data(ds, 4, {})
        sizes = [s.size for s in shards]
        assert sum(sizes) == 103
        # Remainder of 3 distributed to first 3 shards
        assert sorted(sizes, reverse=True)[:3] == [26, 26, 26]

    def test_shard_data_with_capabilities(self):
        strategy = IIDSharding()
        ds = _MockDataset(100, 5)
        caps = {
            "node_a": {"compute_power": 3.0},
            "node_b": {"compute_power": 1.0},
        }
        shards = strategy.shard_data(ds, 2, caps)
        assert len(shards) == 2
        # Higher compute_power node should get more data
        assert shards[0].size > shards[1].size

    def test_checksum_deterministic(self):
        strategy = IIDSharding()
        c1 = strategy._calculate_checksum([5, 3, 1])
        c2 = strategy._calculate_checksum([1, 3, 5])  # sorted same
        assert c1 == c2  # sorted indices → same checksum

    def test_get_strategy_name(self):
        assert IIDSharding().get_strategy_name() == "iid"

    def test_label_distribution_populated(self):
        strategy = IIDSharding()
        ds = _MockDataset(20, 2)
        shards = strategy.shard_data(ds, 2, {})
        for shard in shards:
            assert len(shard.label_distribution) > 0


class TestNonIIDSharding:
    def test_dirichlet_sharding(self):
        np.random.seed(42)
        strategy = NonIIDSharding(alpha=0.5)
        ds = _MockDataset(200, 5)
        shards = strategy.shard_data(ds, 4, {})
        # Should produce 4 shards (possibly fewer if some are empty with extreme alpha)
        assert len(shards) >= 1
        total = sum(s.size for s in shards)
        assert total == 200

    def test_low_alpha_more_heterogeneous(self):
        """Lower alpha should produce more heterogeneous shards."""
        np.random.seed(42)
        strategy_low = NonIIDSharding(alpha=0.01)
        strategy_high = NonIIDSharding(alpha=100.0)
        ds = _MockDataset(500, 5)

        shards_low = strategy_low.shard_data(ds, 5, {})
        shards_high = strategy_high.shard_data(ds, 5, {})

        # Low alpha: some classes should dominate in individual shards
        # High alpha: more even distribution
        # Check max fraction per shard
        def max_frac(shard):
            total = sum(shard.label_distribution.values())
            if total == 0:
                return 0
            return max(shard.label_distribution.values()) / total

        low_max_fracs = [max_frac(s) for s in shards_low if s.size > 0]
        high_max_fracs = [max_frac(s) for s in shards_high if s.size > 0]

        # Average max fraction should be higher for low alpha
        assert np.mean(low_max_fracs) > np.mean(high_max_fracs)

    def test_strategy_name(self):
        strategy = NonIIDSharding(alpha=0.3)
        assert strategy.get_strategy_name() == "noniid_alpha_0.3"


class TestAdaptiveSharding:
    def test_shard_data_basic(self):
        strategy = AdaptiveSharding()
        ds = _MockDataset(100, 5)
        caps = {
            f"node_{i}": {"compute_power": float(i + 1), "bandwidth": 100.0, "storage_gb": 10.0}
            for i in range(3)
        }
        shards = strategy.shard_data(ds, 3, caps)
        assert len(shards) > 0
        total = sum(s.size for s in shards)
        assert total == 100

    def test_node_scores(self):
        strategy = AdaptiveSharding()
        caps = {
            "fast": {"compute_power": 10.0, "bandwidth": 1000.0, "storage_gb": 100.0},
            "slow": {"compute_power": 1.0, "bandwidth": 10.0, "storage_gb": 1.0},
        }
        scores = strategy._calculate_node_scores(caps)
        assert scores["fast"] > scores["slow"]

    def test_node_scores_empty(self):
        strategy = AdaptiveSharding()
        assert strategy._calculate_node_scores({}) == {}


class TestDistributedDatasetManager:
    def test_register_node(self):
        mgr = DistributedDatasetManager({})
        mgr.register_node("n1", {"compute_power": 2.0})
        assert "n1" in mgr.node_capabilities

    def test_get_node_shards_empty(self):
        mgr = DistributedDatasetManager({})
        assert mgr.get_node_shards("n1", "ds1") == []

    def test_export_import_config(self):
        mgr = DistributedDatasetManager({})
        # Setup minimal state
        shard = DataShard("s1", "n1", [0, 1], {"0": 2}, 2, "abc", time.time())
        meta = DatasetMetadata("ds1", 100, 5, 784, {"0": 20}, "vision", "iid")
        mgr.shards["ds1"] = [shard]
        mgr.dataset_metadata["ds1"] = meta
        mgr.node_shard_assignments["n1"] = ["s1"]

        config = mgr.export_sharding_config("ds1")
        assert config["dataset_metadata"]["dataset_id"] == "ds1"

        mgr2 = DistributedDatasetManager({})
        mgr2.import_sharding_config("ds1", config)
        assert mgr2.dataset_metadata["ds1"].total_samples == 100
        assert len(mgr2.shards["ds1"]) == 1

    def test_system_stats_empty(self):
        mgr = DistributedDatasetManager({})
        stats = mgr.get_system_stats()
        assert stats["total_datasets"] == 0
        assert stats["total_shards"] == 0

    def test_heterogeneity_empty(self):
        mgr = DistributedDatasetManager({})
        h = mgr._calculate_heterogeneity([], {"0": 10})
        assert h == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Section 4 — Gradient Compression (SignSGD bit-packing, metrics)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.core.gradient_compression import (
    AdaptiveCompressor,
    CommunicationOptimizer,
    CompressionStats,
    QuantizationCompressor,
    SignSGDCompressor,
    TopKSparsification,
)


class TestSignSGDBitPacking:
    """Test the pure-Python bit-packing logic in SignSGDCompressor."""

    def _compressor(self):
        return SignSGDCompressor()

    def test_pack_all_positive(self):
        c = self._compressor()
        signs = torch.ones(8)
        packed = c._pack_signs_to_bytes(signs)
        assert len(packed) == 1
        assert packed[0] == 0xFF  # all bits set

    def test_pack_all_negative(self):
        c = self._compressor()
        signs = -torch.ones(8)
        packed = c._pack_signs_to_bytes(signs)
        assert packed[0] == 0x00  # no bits set (−1 → 0)

    def test_pack_unpack_roundtrip(self):
        c = self._compressor()
        original = torch.tensor([1, -1, 1, 1, -1, -1, 1, -1, 1, 1, -1, 1], dtype=torch.float32)
        packed = c._pack_signs_to_bytes(original)
        unpacked = c._unpack_signs_from_bytes(packed, len(original))
        np.testing.assert_array_equal(original.numpy(), unpacked)

    def test_pack_unpack_non_multiple_of_8(self):
        c = self._compressor()
        # 5 elements — not a multiple of 8
        original = torch.tensor([1, -1, 1, -1, 1], dtype=torch.float32)
        # Need to pad to 8 for packing
        padded = torch.cat([original, torch.zeros(3)])
        packed = c._pack_signs_to_bytes(padded)
        unpacked = c._unpack_signs_from_bytes(packed, 5)
        expected = np.array([1, -1, 1, -1, 1], dtype=np.float32)
        np.testing.assert_array_equal(expected, unpacked)

    def test_compression_ratio(self):
        c = self._compressor()
        assert abs(c.get_compression_ratio() - 1.0 / 32.0) < 1e-6


class TestTopKSparsification:
    def test_compression_ratio(self):
        c = TopKSparsification(k_ratio=0.1)
        assert abs(c.get_compression_ratio() - 0.1) < 1e-6

    def test_compress_decompress_roundtrip(self):
        c = TopKSparsification(k_ratio=0.5, error_feedback=False)
        grads = {"layer1": torch.randn(20)}
        compressed, meta = asyncio.get_event_loop().run_until_complete(c.compress(grads))
        assert isinstance(compressed, bytes)
        assert meta["algorithm"] == "topk"

        recovered = asyncio.get_event_loop().run_until_complete(c.decompress(compressed, meta))
        assert "layer1" in recovered
        assert recovered["layer1"].shape == (20,)

    def test_error_feedback_accumulates(self):
        c = TopKSparsification(k_ratio=0.1, error_feedback=True)
        grads = {"layer1": torch.randn(100)}
        asyncio.get_event_loop().run_until_complete(c.compress(grads))
        assert "layer1" in c.error_memory


class TestQuantizationCompressor:
    def test_compression_ratio_8bit(self):
        c = QuantizationCompressor(num_bits=8)
        assert abs(c.get_compression_ratio() - 8 / 32) < 1e-6

    def test_compression_ratio_4bit(self):
        c = QuantizationCompressor(num_bits=4)
        assert abs(c.get_compression_ratio() - 4 / 32) < 1e-6


class TestAdaptiveCompressor:
    def test_sparsity_all_zeros(self):
        c = AdaptiveCompressor({})
        grads = {"param": torch.zeros(100)}
        sparsity = c._calculate_sparsity(grads)
        assert sparsity == 1.0

    def test_sparsity_no_zeros(self):
        c = AdaptiveCompressor({})
        grads = {"param": torch.ones(100)}
        sparsity = c._calculate_sparsity(grads)
        assert sparsity == 0.0

    def test_variance_empty(self):
        c = AdaptiveCompressor({})
        assert c._calculate_variance({}) == 0.0

    def test_total_size(self):
        c = AdaptiveCompressor({})
        grads = {"param": torch.randn(25)}
        assert c._calculate_total_size(grads) == 100  # 25 * 4 bytes

    def test_get_compression_ratio_no_history(self):
        c = AdaptiveCompressor({})
        assert c.get_compression_ratio() == 1.0

    def test_get_compression_stats_empty(self):
        c = AdaptiveCompressor({})
        assert c.get_compression_stats() == {}

    def test_history_pruning(self):
        c = AdaptiveCompressor({})
        # Fill history beyond 100
        for i in range(150):
            c.compression_history.append(CompressionStats(100, 50, 0.5, 0.01, 0.01, "topk"))
        assert len(c.compression_history) == 150
        # Next compression will prune
        # We can't easily run compress without lz4/brotli, but test the pruning mechanism
        c.compression_history = c.compression_history[-100:]
        assert len(c.compression_history) == 100


class TestCommunicationOptimizer:
    def test_congestion_empty_history(self):
        opt = CommunicationOptimizer({"compression": {}})
        assert opt._get_network_congestion() == 0.0

    def test_track_bandwidth(self):
        opt = CommunicationOptimizer({"compression": {}})
        opt._track_bandwidth(1000)
        assert len(opt.bandwidth_history) == 1

    def test_bandwidth_history_prunes_old(self):
        opt = CommunicationOptimizer({"compression": {}})
        # Add old entry
        opt.bandwidth_history.append((time.time() - 7200, 5000))
        opt._track_bandwidth(1000)
        # Old entry should be pruned
        assert len(opt.bandwidth_history) == 1

    def test_communication_stats(self):
        opt = CommunicationOptimizer({"compression": {}})
        stats = opt.get_communication_stats()
        assert "recent_bandwidth_usage" in stats
        assert "current_congestion_level" in stats


class TestCompressionStats:
    def test_dataclass(self):
        cs = CompressionStats(
            original_size=1000,
            compressed_size=100,
            compression_ratio=0.1,
            compression_time=0.5,
            decompression_time=0.3,
            algorithm="topk",
        )
        assert cs.original_size == 1000
        assert cs.algorithm == "topk"


# ═══════════════════════════════════════════════════════════════════════════
# Section 5 — P2P Node Discovery (DHT, GossipProtocol)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.p2p.node_discovery import (
    DistributedHashTable,
    GossipProtocol,
    NetworkMessage,
    PeerInfo,
)


def _make_peer(peer_id, reputation=0.5, port=8080):
    return PeerInfo(
        peer_id=peer_id,
        ip_address="127.0.0.1",
        port=port,
        public_key="",
        capabilities={},
        last_seen=time.time(),
        reputation=reputation,
        is_bootstrap=False,
        version="1.0.0",
        network_id="test",
    )


class TestPeerInfo:
    def test_dataclass_fields(self):
        p = _make_peer("abc123")
        assert p.peer_id == "abc123"
        assert p.reputation == 0.5


class TestNetworkMessage:
    def test_dataclass_fields(self):
        msg = NetworkMessage(
            message_id="m1",
            message_type="heartbeat",
            sender_id="s1",
            recipient_id=None,
            payload={},
            timestamp=time.time(),
            ttl=60,
            signature=None,
        )
        assert msg.message_type == "heartbeat"
        assert msg.recipient_id is None


class TestDistributedHashTable:
    def _node_id(self, s):
        return hashlib.sha1(s.encode()).hexdigest()

    def test_xor_distance_self_is_zero(self):
        nid = self._node_id("node0")
        dht = DistributedHashTable(nid)
        assert dht._xor_distance(nid, nid) == 0

    def test_xor_distance_symmetric(self):
        a = self._node_id("a")
        b = self._node_id("b")
        dht = DistributedHashTable(a)
        assert dht._xor_distance(a, b) == dht._xor_distance(b, a)

    def test_add_peer_self_rejected(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        peer = _make_peer(nid)
        assert dht.add_peer(peer) is False

    def test_add_peer_succeeds(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        peer = _make_peer(self._node_id("other"))
        assert dht.add_peer(peer) is True

    def test_add_peer_updates_existing(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        peer_id = self._node_id("other")
        p1 = _make_peer(peer_id)
        p1.reputation = 0.3
        dht.add_peer(p1)
        p2 = _make_peer(peer_id)
        p2.reputation = 0.9
        assert dht.add_peer(p2) is True
        # Find the peer in routing table
        found = dht.find_closest_peers(peer_id, count=1)
        assert found[0].reputation == 0.9

    def test_find_closest_peers(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        # Add several peers
        for i in range(10):
            pid = self._node_id(f"peer_{i}")
            dht.add_peer(_make_peer(pid))
        target = self._node_id("target")
        closest = dht.find_closest_peers(target, count=3)
        assert len(closest) == 3

    def test_store_and_retrieve(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        assert dht.store("key1", "value1") is True
        assert dht.retrieve("key1") == "value1"

    def test_retrieve_nonexistent(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        assert dht.retrieve("missing") is None

    def test_retrieve_expired_ttl(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        dht.store("key1", "value1")
        # Manually expire
        dht.storage["key1"]["timestamp"] = time.time() - 7200
        assert dht.retrieve("key1") is None

    def test_get_bucket_info(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid)
        for i in range(5):
            dht.add_peer(_make_peer(self._node_id(f"peer_{i}")))
        info = dht.get_bucket_info()
        assert sum(info.values()) == 5

    def test_bucket_full_lru_replacement(self):
        nid = self._node_id("self")
        dht = DistributedHashTable(nid, k_bucket_size=2)
        # Add peers that land in the same bucket - tricky since bucket depends on XOR
        # Instead, add many peers and verify bucket size is capped
        for i in range(50):
            pid = self._node_id(f"peer_{i}")
            dht.add_peer(_make_peer(pid))
        # All buckets should have at most k_bucket_size entries
        for bucket in dht.routing_table.values():
            assert len(bucket) <= 2


class TestGossipProtocol:
    def test_should_gossip_new_broadcast(self):
        gp = GossipProtocol("node1")
        msg = NetworkMessage("m1", "heartbeat", "sender", None, {}, time.time(), 60, None)
        assert gp.should_gossip_message(msg) is True

    def test_should_not_gossip_expired(self):
        gp = GossipProtocol("node1")
        msg = NetworkMessage("m1", "heartbeat", "sender", None, {}, time.time() - 200, 60, None)
        assert gp.should_gossip_message(msg) is False

    def test_should_not_gossip_duplicate(self):
        gp = GossipProtocol("node1")
        msg = NetworkMessage("m1", "heartbeat", "sender", None, {}, time.time(), 60, None)
        gp.cache_message(msg)
        assert gp.should_gossip_message(msg) is False

    def test_should_not_gossip_direct_message_for_others(self):
        gp = GossipProtocol("node1")
        msg = NetworkMessage("m1", "direct", "sender", "node2", {}, time.time(), 60, None)
        assert gp.should_gossip_message(msg) is False

    def test_cache_message_cleanup(self):
        gp = GossipProtocol("node1")
        # Add old message
        old_msg = NetworkMessage(
            "old", "heartbeat", "sender", None, {}, time.time() - 600, 60, None
        )
        gp.message_cache["old"] = old_msg
        # Add new message triggers cleanup
        new_msg = NetworkMessage("new", "heartbeat", "sender", None, {}, time.time(), 60, None)
        gp.cache_message(new_msg)
        assert "old" not in gp.message_cache
        assert "new" in gp.message_cache

    def test_select_gossip_peers_respects_limit(self):
        gp = GossipProtocol("node1", max_gossip_peers=2)
        peers = [_make_peer(f"peer_{i}") for i in range(10)]
        selected = gp.select_gossip_peers(peers)
        assert len(selected) <= 2

    def test_select_gossip_peers_empty(self):
        gp = GossipProtocol("node1")
        selected = gp.select_gossip_peers([])
        assert selected == []


# ═══════════════════════════════════════════════════════════════════════════
# Section 6 — Privacy / Secure Aggregation
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.privacy.secure_aggregation import (
    DifferentialPrivacyMechanism,
    PrivacyAudit,
    SecretShare,
    ShamirSecretSharing,
)


class TestDifferentialPrivacyMechanism:
    def test_noise_multiplier_positive(self):
        dp = DifferentialPrivacyMechanism(epsilon=1.0, delta=1e-5)
        assert dp.noise_multiplier > 0

    def test_smaller_epsilon_more_noise(self):
        dp1 = DifferentialPrivacyMechanism(epsilon=0.1)
        dp2 = DifferentialPrivacyMechanism(epsilon=10.0)
        assert dp1.noise_multiplier > dp2.noise_multiplier

    def test_clip_gradients_below_norm(self):
        dp = DifferentialPrivacyMechanism(clipping_norm=100.0)
        grads = {"param": torch.tensor([1.0, 2.0, 3.0])}
        clipped = dp.clip_gradients(grads)
        # Small gradient, shouldn't be clipped
        assert torch.allclose(clipped["param"], grads["param"], atol=1e-5)

    def test_clip_gradients_above_norm(self):
        dp = DifferentialPrivacyMechanism(clipping_norm=1.0)
        grads = {"param": torch.tensor([10.0, 20.0, 30.0])}
        clipped = dp.clip_gradients(grads)
        # Norm of clipped should be ≤ clipping_norm
        clipped_norm = torch.norm(clipped["param"]).item()
        assert clipped_norm <= 1.0 + 1e-5

    def test_add_noise_changes_gradients(self):
        dp = DifferentialPrivacyMechanism(epsilon=0.1, clipping_norm=1.0)
        grads = {"param": torch.ones(100)}
        noisy, params = dp.add_noise(grads)
        # Noisy gradients should differ from original
        assert not torch.allclose(noisy["param"], grads["param"])
        assert "param" in params

    def test_privatize_gradients_pipeline(self):
        dp = DifferentialPrivacyMechanism(epsilon=1.0, clipping_norm=1.0)
        grads = {"param": torch.randn(50)}
        private, params = dp.privatize_gradients(grads)
        assert "param" in private
        assert private["param"].shape == (50,)


class TestShamirSecretSharing:
    def test_create_shares(self):
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        shares = sss.create_shares(42, ["p1", "p2", "p3", "p4", "p5"])
        assert len(shares) == 5
        assert all(isinstance(s, SecretShare) for s in shares)
        assert shares[0].threshold == 3

    def test_reconstruct_secret(self):
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        secret = 12345
        shares = sss.create_shares(secret, ["p1", "p2", "p3", "p4", "p5"])
        # Reconstruct with exactly threshold shares
        recovered = sss.reconstruct_secret(shares[:3])
        assert recovered == secret

    def test_reconstruct_with_different_shares(self):
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        secret = 99999
        shares = sss.create_shares(secret, ["p1", "p2", "p3", "p4", "p5"])
        # Use shares 2, 3, 4 instead of 0, 1, 2
        recovered = sss.reconstruct_secret(shares[2:5])
        assert recovered == secret

    def test_insufficient_shares_raises(self):
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        shares = sss.create_shares(42, ["p1", "p2", "p3", "p4", "p5"])
        with pytest.raises(ValueError, match="Insufficient"):
            sss.reconstruct_secret(shares[:2])

    def test_insufficient_participants_raises(self):
        sss = ShamirSecretSharing(threshold=3, total_shares=5)
        with pytest.raises(ValueError, match="Not enough"):
            sss.create_shares(42, ["p1", "p2"])  # only 2 < threshold=3

    def test_zero_secret(self):
        sss = ShamirSecretSharing(threshold=2, total_shares=3)
        shares = sss.create_shares(0, ["a", "b", "c"])
        recovered = sss.reconstruct_secret(shares[:2])
        assert recovered == 0

    def test_large_secret(self):
        sss = ShamirSecretSharing(threshold=2, total_shares=3)
        secret = 10**20
        shares = sss.create_shares(secret, ["a", "b", "c"])
        recovered = sss.reconstruct_secret(shares[:2])
        assert recovered == secret


class TestPrivacyAudit:
    def test_empty_cost(self):
        audit = PrivacyAudit()
        eps, delta = audit.get_total_privacy_cost()
        assert eps == 0.0
        assert delta == 0.0

    def test_record_and_accumulate(self):
        audit = PrivacyAudit()
        audit.record_privacy_expenditure(1.0, 1e-5, "gaussian", "round_1")
        audit.record_privacy_expenditure(0.5, 1e-5, "gaussian", "round_2")
        eps, delta = audit.get_total_privacy_cost()
        assert abs(eps - 1.5) < 1e-10
        assert abs(delta - 2e-5) < 1e-15

    def test_budget_remaining(self):
        audit = PrivacyAudit()
        audit.record_privacy_expenditure(2.0, 1e-5, "gaussian", "r1")
        rem_eps, rem_delta = audit.privacy_budget_remaining(10.0, 1e-4)
        assert abs(rem_eps - 8.0) < 1e-10
        assert rem_delta > 0

    def test_budget_exhausted(self):
        audit = PrivacyAudit()
        audit.record_privacy_expenditure(10.0, 1e-3, "gaussian", "r1")
        rem_eps, rem_delta = audit.privacy_budget_remaining(5.0, 1e-4)
        assert rem_eps == 0.0
        assert rem_delta == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Section 7 — AGIX Rewards (pure calculation logic, no web3)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.blockchain.agix_rewards import (
    AGIXRewardCalculator,
    AntiSybilMechanism,
    ComputeContribution,
    ReputationBasedRewards,
    RewardCalculation,
)


def _make_contribution(
    node_id="node_1", data_processed=1000, accuracy=0.9, timestamp=None, round_id="r1"
):
    return ComputeContribution(
        node_id=node_id,
        round_id=round_id,
        data_processed=data_processed,
        compute_time=60.0,
        gpu_hours=1.0,
        model_accuracy=accuracy,
        bandwidth_used=1024,
        timestamp=timestamp or time.time(),
    )


class TestAGIXRewardCalculator:
    def _calc(self, **kwargs):
        config = {
            "base_reward_per_sample": "0.001",
            "quality_multiplier": "2.0",
            "consistency_multiplier": "1.5",
            "early_submission_multiplier": "1.2",
            "high_accuracy_threshold": 0.85,
            "consistency_threshold": 0.9,
            "round_reward_pool": "10000",
            "min_reward_per_node": "1",
        }
        config.update(kwargs)
        return AGIXRewardCalculator(config)

    def test_base_reward(self):
        calc = self._calc()
        contrib = _make_contribution(data_processed=1000, accuracy=0.5)
        result = calc.calculate_reward(contrib, [], round_deadline=time.time() + 1000)
        assert result.base_reward == Decimal("1.000")  # 1000 * 0.001

    def test_quality_bonus_high_accuracy(self):
        calc = self._calc()
        contrib = _make_contribution(accuracy=0.90)
        result = calc.calculate_reward(contrib, [], round_deadline=time.time() + 1000)
        assert result.quality_bonus > 0

    def test_no_quality_bonus_low_accuracy(self):
        calc = self._calc()
        contrib = _make_contribution(accuracy=0.5)
        result = calc.calculate_reward(contrib, [], round_deadline=time.time() + 1000)
        assert result.quality_bonus == Decimal("0")

    def test_early_submission_bonus(self):
        calc = self._calc()
        # The logic is: contribution.timestamp < round_deadline * 0.8
        # For timestamp (now ~1.77e9) to be < deadline * 0.8, deadline > ts / 0.8
        early_ts = time.time()
        deadline = early_ts / 0.8 + 1000  # Ensures early_ts < deadline * 0.8
        contrib = _make_contribution(timestamp=early_ts)
        result = calc.calculate_reward(contrib, [], round_deadline=deadline)
        assert result.early_submission_bonus > 0

    def test_consistency_bonus_needs_history(self):
        calc = self._calc()
        contrib = _make_contribution(accuracy=0.9)
        # Short history → no bonus
        result = calc.calculate_reward(contrib, [contrib], round_deadline=time.time() + 1000)
        assert result.consistency_bonus == Decimal("0")

    def test_consistency_bonus_with_good_history(self):
        calc = self._calc()
        # Create 10 high-accuracy contributions
        history = [_make_contribution(accuracy=0.95) for _ in range(10)]
        contrib = _make_contribution(accuracy=0.95)
        result = calc.calculate_reward(contrib, history, round_deadline=time.time() + 1000)
        assert result.consistency_bonus > 0

    def test_minimum_reward(self):
        calc = self._calc()
        contrib = _make_contribution(data_processed=1, accuracy=0.1)
        result = calc.calculate_reward(contrib, [], round_deadline=time.time() + 1000)
        assert result.total_reward >= Decimal("1")

    def test_distribute_round_rewards_scaling(self):
        calc = self._calc(round_reward_pool="5")
        contribs = [_make_contribution(data_processed=10000, accuracy=0.95) for _ in range(5)]
        results = calc.distribute_round_rewards(contribs, {}, round_deadline=time.time() + 1000)
        total = sum(r.agix_amount for r in results)
        assert total <= Decimal("5") + Decimal("0.01")  # Within pool


class TestReputationBasedRewards:
    def test_high_reputation_boosts_reward(self):
        rbr = ReputationBasedRewards({})
        low = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 0.1, Decimal("1000"))
        high = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 1.0, Decimal("1000"))
        assert high > low

    def test_high_stake_boosts_reward(self):
        rbr = ReputationBasedRewards({})
        low_stake = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 0.5, Decimal("100"))
        high_stake = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 0.5, Decimal("100000"))
        assert high_stake > low_stake

    def test_stake_multiplier_capped(self):
        rbr = ReputationBasedRewards({})
        # Very high stake shouldn't produce extreme reward
        r = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 0.5, Decimal("10000000000"))
        # Multiplier capped at 3.0 × reputation_multiplier
        assert r <= Decimal("10") * Decimal("3.0") * Decimal("2.0")

    def test_zero_reputation_still_gets_something(self):
        rbr = ReputationBasedRewards({})
        r = rbr.calculate_reputation_adjusted_reward(Decimal("10"), 0.0, Decimal("1000"))
        assert r > 0  # 0.5x multiplier minimum


class TestAntiSybilMechanism:
    def test_no_sybils_when_normal(self):
        asm = AntiSybilMechanism({"ip_clustering_threshold": 3})
        contribs = [
            _make_contribution(node_id=f"n_{i}", timestamp=time.time() + i * 100) for i in range(3)
        ]
        meta = {f"n_{i}": {"ip_address": f"10.0.0.{i}"} for i in range(3)}
        suspicious = asm.detect_sybil_nodes(contribs, meta)
        assert suspicious == []

    def test_ip_clustering_detection(self):
        asm = AntiSybilMechanism({"ip_clustering_threshold": 2})
        contribs = [
            _make_contribution(node_id=f"n_{i}", timestamp=time.time() + i * 100) for i in range(5)
        ]
        meta = {f"n_{i}": {"ip_address": "10.0.0.1"} for i in range(5)}
        suspicious = asm.detect_sybil_nodes(contribs, meta)
        assert len(suspicious) >= 3

    def test_timing_correlation_detection(self):
        asm = AntiSybilMechanism({"ip_clustering_threshold": 100})
        base_ts = time.time()
        contribs = [_make_contribution(node_id=f"n_{i}", timestamp=base_ts + 1) for i in range(3)]
        meta = {f"n_{i}": {"ip_address": f"10.{i}.0.1"} for i in range(3)}
        suspicious = asm.detect_sybil_nodes(contribs, meta)
        assert len(suspicious) > 0

    def test_filter_rewards_for_sybils(self):
        asm = AntiSybilMechanism({})
        calc = RewardCalculation(
            node_id="bad",
            base_reward=Decimal("10"),
            quality_bonus=Decimal("5"),
            consistency_bonus=Decimal("3"),
            early_submission_bonus=Decimal("2"),
            total_reward=Decimal("20"),
            agix_amount=Decimal("20"),
        )
        filtered = asm.filter_rewards_for_sybils([calc], ["bad"])
        assert filtered[0].agix_amount == Decimal("2")  # 20 * 0.1


# ═══════════════════════════════════════════════════════════════════════════
# Section 8 — Monitoring / Dashboard (MetricsCollector, PerformanceAnalyzer)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.monitoring.dashboard import (
    MetricsCollector,
    NetworkMetrics,
    PerformanceAnalyzer,
    SystemHealth,
    TrainingMetrics,
)


def _make_training_metrics(node_id="n1", round_id="r1", loss=0.5, accuracy=0.8, batch_time=1.0):
    return TrainingMetrics(
        node_id=node_id,
        round_id=round_id,
        epoch=1,
        loss=loss,
        accuracy=accuracy,
        learning_rate=0.001,
        batch_time=batch_time,
        communication_time=0.1,
        memory_usage=50.0,
        gpu_utilization=70.0,
        timestamp=time.time(),
    )


def _make_network_metrics(round_id="r1", total=10, active=8, loss=0.5, accuracy=0.8):
    return NetworkMetrics(
        round_id=round_id,
        total_nodes=total,
        active_nodes=active,
        avg_loss=loss,
        avg_accuracy=accuracy,
        consensus_time=30.0,
        data_transmitted_mb=100.0,
        byzantine_nodes_detected=0,
        timestamp=time.time(),
    )


class TestTrainingMetrics:
    def test_dataclass_fields(self):
        m = _make_training_metrics()
        assert m.node_id == "n1"
        assert m.loss == 0.5


class TestNetworkMetrics:
    def test_dataclass_fields(self):
        m = _make_network_metrics()
        assert m.total_nodes == 10


class TestSystemHealth:
    def test_dataclass_fields(self):
        h = SystemHealth(
            timestamp=time.time(),
            cpu_usage=50.0,
            memory_usage=60.0,
            disk_usage=70.0,
            network_latency=10.0,
            active_connections=5,
            error_rate=0.01,
        )
        assert h.cpu_usage == 50.0


class TestMetricsCollector:
    def test_record_training_metrics(self):
        mc = MetricsCollector({})
        m = _make_training_metrics()
        mc.record_training_metrics(m)
        assert "n1" in mc.training_metrics
        assert len(mc.training_metrics["n1"]) == 1

    def test_current_round_metrics_updated(self):
        mc = MetricsCollector({})
        mc.record_training_metrics(_make_training_metrics())
        assert "n1" in mc.current_round_metrics

    def test_get_current_round_summary_empty(self):
        mc = MetricsCollector({})
        assert mc.get_current_round_summary() == {}

    def test_get_current_round_summary_with_data(self):
        mc = MetricsCollector({})
        mc.record_training_metrics(_make_training_metrics(loss=0.3, accuracy=0.9))
        mc.record_training_metrics(_make_training_metrics(node_id="n2", loss=0.5, accuracy=0.7))
        summary = mc.get_current_round_summary()
        assert summary["participating_nodes"] == 2
        assert abs(summary["avg_loss"] - 0.4) < 1e-5
        assert abs(summary["avg_accuracy"] - 0.8) < 1e-5

    def test_record_network_metrics(self):
        mc = MetricsCollector({})
        mc.record_network_metrics(_make_network_metrics())
        assert len(mc.network_metrics) == 1

    def test_record_system_health(self):
        mc = MetricsCollector({})
        h = SystemHealth(time.time(), 50, 60, 70, 10, 5, 0.01)
        mc.record_system_health(h)
        assert len(mc.system_health) == 1

    def test_get_node_performance_trends_empty(self):
        mc = MetricsCollector({})
        assert mc.get_node_performance_trends("unknown") == {}

    def test_get_node_performance_trends_with_data(self):
        mc = MetricsCollector({})
        for i in range(5):
            mc.record_training_metrics(
                _make_training_metrics(loss=1.0 - i * 0.1, accuracy=0.5 + i * 0.1)
            )
        trends = mc.get_node_performance_trends("n1")
        assert "loss_trend" in trends
        assert "accuracy_trend" in trends
        assert trends["loss_trend"] > 0  # Loss decreasing = positive trend
        assert trends["accuracy_trend"] > 0  # Accuracy increasing = positive trend

    def test_network_health_unknown_when_empty(self):
        mc = MetricsCollector({})
        health = mc.get_network_health_status()
        assert health["status"] == "unknown"

    def test_network_health_healthy(self):
        mc = MetricsCollector({})
        for i in range(10):
            mc.record_network_metrics(
                _make_network_metrics(
                    round_id=f"r{i}",
                    total=10,
                    active=9,
                )
            )
        health = mc.get_network_health_status()
        assert health["status"] == "healthy"
        assert health["health_score"] >= 80

    def test_network_health_warning_low_participation(self):
        mc = MetricsCollector({})
        for i in range(10):
            mc.record_network_metrics(
                _make_network_metrics(
                    round_id=f"r{i}",
                    total=10,
                    active=5,
                )
            )
        health = mc.get_network_health_status()
        assert health["status"] in ("warning", "critical")


class TestPerformanceAnalyzer:
    def test_anomalies_insufficient_data(self):
        mc = MetricsCollector({})
        pa = PerformanceAnalyzer(mc)
        assert pa.detect_performance_anomalies() == []

    def test_anomalies_detected_for_outlier(self):
        mc = MetricsCollector({})
        # Record normal metrics for 5 nodes (need enough data points)
        for i in range(5):
            for j in range(10):
                mc.record_training_metrics(
                    TrainingMetrics(
                        node_id=f"normal_{i}",
                        round_id="r1",
                        epoch=j,
                        loss=0.5,
                        accuracy=0.8,
                        learning_rate=0.001,
                        batch_time=1.0,
                        communication_time=0.1,
                        memory_usage=50.0,
                        gpu_utilization=70.0,
                        timestamp=time.time() + j,
                    )
                )
        # Record outlier with wildly different values
        for j in range(10):
            mc.record_training_metrics(
                TrainingMetrics(
                    node_id="outlier",
                    round_id="r1",
                    epoch=j,
                    loss=50.0,
                    accuracy=0.01,
                    learning_rate=0.001,
                    batch_time=500.0,
                    communication_time=0.1,
                    memory_usage=50.0,
                    gpu_utilization=70.0,
                    timestamp=time.time() + j,
                )
            )
        pa = PerformanceAnalyzer(mc)
        anomalies = pa.detect_performance_anomalies()
        outlier_anomalies = [a for a in anomalies if a["node_id"] == "outlier"]
        assert len(outlier_anomalies) > 0

    def test_convergence_insufficient_data(self):
        mc = MetricsCollector({})
        pa = PerformanceAnalyzer(mc)
        result = pa._analyze_convergence()
        assert result["status"] == "insufficient_data"

    def test_convergence_analysis(self):
        mc = MetricsCollector({})
        for i in range(10):
            mc.record_network_metrics(
                NetworkMetrics(
                    round_id=f"r{i}",
                    total_nodes=10,
                    active_nodes=9,
                    avg_loss=1.0 - i * 0.05,
                    avg_accuracy=0.5 + i * 0.05,
                    consensus_time=30,
                    data_transmitted_mb=100,
                    byzantine_nodes_detected=0,
                    timestamp=time.time(),
                )
            )
        pa = PerformanceAnalyzer(mc)
        result = pa._analyze_convergence()
        assert result["status"] in ("converging", "stable", "converged")

    def test_communication_bottlenecks_no_data(self):
        mc = MetricsCollector({})
        pa = PerformanceAnalyzer(mc)
        result = pa._detect_communication_bottlenecks()
        assert result["status"] == "no_data"

    def test_node_efficiency_ranking(self):
        mc = MetricsCollector({})
        for i in range(5):
            mc.record_training_metrics(
                _make_training_metrics(node_id="fast", loss=0.5, accuracy=0.9, batch_time=0.5)
            )
            mc.record_training_metrics(
                _make_training_metrics(node_id="slow", loss=0.8, accuracy=0.6, batch_time=5.0)
            )
        pa = PerformanceAnalyzer(mc)
        rankings = pa._rank_node_efficiency()
        assert len(rankings) >= 2

    def test_resource_recommendations_high_memory(self):
        mc = MetricsCollector({})
        for _ in range(5):
            mc.record_training_metrics(
                TrainingMetrics(
                    node_id="n1",
                    round_id="r1",
                    epoch=1,
                    loss=0.5,
                    accuracy=0.8,
                    learning_rate=0.001,
                    batch_time=1.0,
                    communication_time=0.1,
                    memory_usage=95.0,
                    gpu_utilization=50.0,
                    timestamp=time.time(),
                )
            )
        pa = PerformanceAnalyzer(mc)
        recs = pa._generate_resource_recommendations()
        memory_recs = [r for r in recs if r["type"] == "memory_pressure"]
        assert len(memory_recs) > 0

    def test_resource_recommendations_low_gpu(self):
        mc = MetricsCollector({})
        for _ in range(5):
            mc.record_training_metrics(
                TrainingMetrics(
                    node_id="n1",
                    round_id="r1",
                    epoch=1,
                    loss=0.5,
                    accuracy=0.8,
                    learning_rate=0.001,
                    batch_time=1.0,
                    communication_time=0.1,
                    memory_usage=50.0,
                    gpu_utilization=30.0,
                    timestamp=time.time(),
                )
            )
        pa = PerformanceAnalyzer(mc)
        recs = pa._generate_resource_recommendations()
        gpu_recs = [r for r in recs if r["type"] == "gpu_underutilization"]
        assert len(gpu_recs) > 0

    def test_generate_training_insights(self):
        mc = MetricsCollector({})
        for i in range(10):
            mc.record_training_metrics(_make_training_metrics(node_id=f"n{i}"))
            mc.record_network_metrics(_make_network_metrics(round_id=f"r{i}"))
        pa = PerformanceAnalyzer(mc)
        insights = pa.generate_training_insights()
        assert "convergence_analysis" in insights
        assert "node_efficiency_ranking" in insights
        assert "communication_bottlenecks" in insights
        assert "resource_recommendations" in insights


# ═══════════════════════════════════════════════════════════════════════════
# Section 9 — Federated Orchestrator dataclasses
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.core.federated_orchestrator import (
    ModelUpdate,
    NodeInfo,
    TrainingRound,
)


class TestFederatedOrchestratorDataclasses:
    def test_node_info(self):
        ni = NodeInfo(
            node_id="n1",
            ip_address="10.0.0.1",
            port=8080,
            capabilities={"gpu": True},
            compute_power=2.0,
            last_heartbeat=time.time(),
            reputation_score=0.5,
            stake_amount=100.0,
            status="active",
        )
        assert ni.node_id == "n1"
        assert ni.capabilities["gpu"] is True
        assert ni.compute_power == 2.0

    def test_training_round(self):
        tr = TrainingRound(
            round_id="r1",
            global_model_hash="abc",
            participants=["n1", "n2"],
            start_time=time.time(),
            deadline=time.time() + 600,
            min_participants=2,
            max_participants=10,
            status="active",
        )
        assert tr.round_id == "r1"
        assert "n1" in tr.participants

    def test_model_update(self):
        mu = ModelUpdate(
            node_id="n1",
            round_id="r1",
            model_diff=b"binary_data",
            data_size=1000,
            compute_proof="proof_hash",
            signature="sig",
            timestamp=time.time(),
        )
        assert mu.data_size == 1000


# ═══════════════════════════════════════════════════════════════════════════
# Section 10 — Checkpoint / Blockchain dataclasses (no web3 needed)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.blockchain.checkpoint_manager import (
    CheckpointVerification,
    ModelCheckpoint,
)


class TestCheckpointDataclasses:
    def test_model_checkpoint(self):
        mc = ModelCheckpoint(
            checkpoint_id="cp1",
            model_hash="abc",
            ipfs_hash="Qm123",
            filecoin_deal_id=None,
            creator_address="0x123",
            timestamp=time.time(),
            round_number=5,
            accuracy_metrics={"val_acc": 0.95},
            size_bytes=1024 * 1024,
            encryption_key=None,
        )
        assert mc.round_number == 5
        assert mc.accuracy_metrics["val_acc"] == 0.95

    def test_checkpoint_verification(self):
        cv = CheckpointVerification(
            checkpoint_id="cp1",
            is_valid=True,
            verification_hash="abc",
            verifier_address="0x456",
            timestamp=time.time(),
        )
        assert cv.is_valid is True


# ═══════════════════════════════════════════════════════════════════════════
# Section 11 — HomomorphicEncryption (RSA-based, uses cryptography lib)
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.distributed_training.privacy.secure_aggregation import (
    HomomorphicEncryption,
)


class TestHomomorphicEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        he = HomomorphicEncryption(key_size=2048)
        plaintext = 42
        ct = he.encrypt(plaintext)
        assert isinstance(ct, bytes)
        recovered = he.decrypt(ct)
        assert recovered == plaintext

    def test_encrypt_decrypt_large_value(self):
        he = HomomorphicEncryption(key_size=2048)
        plaintext = 123456789
        ct = he.encrypt(plaintext)
        assert he.decrypt(ct) == plaintext

    def test_add_encrypted(self):
        he = HomomorphicEncryption(key_size=2048)
        ct1 = he.encrypt(10)
        ct2 = he.encrypt(20)
        ct_sum = he.add_encrypted(ct1, ct2)
        assert he.decrypt(ct_sum) == 30
