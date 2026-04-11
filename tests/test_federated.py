"""
Tests for asi_build.federated — Federated Learning Framework

Heavy pre-import mocking is required because:
  - tensorflow is not installed
  - scipy/sklearn may be missing
  - Several sub-modules referenced by __init__.py files don't exist
    (fedprox, scaffold, fednova, communication.*, privacy_accountant,
     noise_mechanisms, secure_computation, anonymization, data_utils, visualization)
  - Python processes __init__.py on ANY submodule import, causing cascade failures

Strategy: register stubs in sys.modules for everything missing BEFORE any
asi_build.federated import.
"""

import math
import sys
import types

import numpy as np
import pytest

# ============================================================================
# Phase 1: Pre-import mocking
# ============================================================================

_SRC = "/shared/asi-build/src"
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _ensure_module(name, attrs=None):
    """Register a stub module if not already in sys.modules."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        if attrs:
            for k, v in attrs.items():
                setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


def _stub_class(name="Stub"):
    """Create a harmless stub class."""
    return type(name, (), {"__init__": lambda self, *a, **kw: None})


# --- 1a. tensorflow ---
_ensure_module("tensorflow")
_ensure_module("tensorflow.data", {"Dataset": _stub_class("Dataset")})
_ensure_module("tensorflow.keras", {"Model": _stub_class("Model")})
_ensure_module("tensorflow.keras.models", {"load_model": lambda x: None})
_ensure_module("tensorflow.keras.layers")
_ensure_module("tensorflow.keras.optimizers")
# Wire parent→child refs
sys.modules["tensorflow"].data = sys.modules["tensorflow.data"]
sys.modules["tensorflow"].keras = sys.modules["tensorflow.keras"]
sys.modules["tensorflow.keras"].models = sys.modules["tensorflow.keras.models"]
sys.modules["tensorflow.keras"].layers = sys.modules["tensorflow.keras.layers"]
sys.modules["tensorflow.keras"].optimizers = sys.modules["tensorflow.keras.optimizers"]

# --- 1b. scipy ---
_ensure_module("scipy")
_ensure_module(
    "scipy.stats",
    {
        "norm": type("norm", (), {"cdf": staticmethod(lambda x: 0.5)}),
    },
)
sys.modules["scipy"].stats = sys.modules["scipy.stats"]

# --- 1c. sklearn ---
_ensure_module("sklearn")
_ensure_module("sklearn.cluster", {"DBSCAN": _stub_class("DBSCAN")})
_ensure_module("sklearn.preprocessing", {"StandardScaler": _stub_class("StandardScaler")})
sys.modules["sklearn"].cluster = sys.modules["sklearn.cluster"]
sys.modules["sklearn"].preprocessing = sys.modules["sklearn.preprocessing"]

# --- 1d. cryptography (needed by secure_aggregation.py) ---
_ensure_module("cryptography")
_ensure_module("cryptography.hazmat")
_ensure_module("cryptography.hazmat.primitives")
_ensure_module("cryptography.hazmat.primitives.hashes")
_ensure_module("cryptography.hazmat.primitives.serialization")
_ensure_module("cryptography.hazmat.primitives.asymmetric")
_ensure_module("cryptography.hazmat.primitives.asymmetric.rsa")
_ensure_module("cryptography.hazmat.primitives.asymmetric.padding")
_ensure_module(
    "cryptography.hazmat.primitives.ciphers",
    {
        "Cipher": _stub_class("Cipher"),
        "algorithms": types.ModuleType("algorithms"),
        "modes": types.ModuleType("modes"),
    },
)
_ensure_module(
    "cryptography.hazmat.backends",
    {
        "default_backend": lambda: None,
    },
)

# Wire cryptography hierarchy
sys.modules["cryptography"].hazmat = sys.modules["cryptography.hazmat"]
sys.modules["cryptography.hazmat"].primitives = sys.modules["cryptography.hazmat.primitives"]
sys.modules["cryptography.hazmat.primitives"].hashes = sys.modules[
    "cryptography.hazmat.primitives.hashes"
]
sys.modules["cryptography.hazmat.primitives"].serialization = sys.modules[
    "cryptography.hazmat.primitives.serialization"
]
sys.modules["cryptography.hazmat.primitives"].asymmetric = sys.modules[
    "cryptography.hazmat.primitives.asymmetric"
]
sys.modules["cryptography.hazmat.primitives.asymmetric"].rsa = sys.modules[
    "cryptography.hazmat.primitives.asymmetric.rsa"
]
sys.modules["cryptography.hazmat.primitives.asymmetric"].padding = sys.modules[
    "cryptography.hazmat.primitives.asymmetric.padding"
]
sys.modules["cryptography.hazmat.primitives"].ciphers = sys.modules[
    "cryptography.hazmat.primitives.ciphers"
]
sys.modules["cryptography.hazmat"].backends = sys.modules["cryptography.hazmat.backends"]

# --- 1e. Missing federated sub-modules ---

# aggregation: fedprox, scaffold, fednova
for _name in ["fedprox", "scaffold", "fednova"]:
    _full = f"asi_build.federated.aggregation.{_name}"
    _ensure_module(
        _full,
        {
            "FedProxAggregator": _stub_class("FedProxAggregator"),
            "SCAFFOLDAggregator": _stub_class("SCAFFOLDAggregator"),
            "FedNovaAggregator": _stub_class("FedNovaAggregator"),
        },
    )

# privacy: privacy_accountant, noise_mechanisms, secure_computation, anonymization
_ensure_module(
    "asi_build.federated.privacy.privacy_accountant",
    {
        "PrivacyAccountant": _stub_class("PrivacyAccountant"),
        "RDPAccountant": _stub_class("RDPAccountant"),
    },
)
_ensure_module(
    "asi_build.federated.privacy.noise_mechanisms",
    {
        "AdaptiveNoiseManager": _stub_class("AdaptiveNoiseManager"),
        "PrivacyBudgetTracker": _stub_class("PrivacyBudgetTracker"),
    },
)
_ensure_module(
    "asi_build.federated.privacy.secure_computation",
    {
        "SecureComputationManager": _stub_class("SecureComputationManager"),
    },
)
_ensure_module(
    "asi_build.federated.privacy.anonymization",
    {
        "DataAnonymizer": _stub_class("DataAnonymizer"),
        "KAnonymity": _stub_class("KAnonymity"),
    },
)

# utils: data_utils, visualization
_ensure_module(
    "asi_build.federated.utils.data_utils",
    {
        "DataPartitioner": _stub_class("DataPartitioner"),
        "IIDPartitioner": _stub_class("IIDPartitioner"),
        "NonIIDPartitioner": _stub_class("NonIIDPartitioner"),
    },
)
_ensure_module(
    "asi_build.federated.utils.visualization",
    {
        "FederatedVisualizer": _stub_class("FederatedVisualizer"),
    },
)

# communication package (entire directory missing)
_ensure_module(
    "asi_build.federated.communication",
    {
        "FederatedCommunicationProtocol": _stub_class("FederatedCommunicationProtocol"),
    },
)
_ensure_module(
    "asi_build.federated.communication.protocols",
    {
        "FederatedCommunicationProtocol": _stub_class("FederatedCommunicationProtocol"),
    },
)

# ============================================================================
# Phase 2: Actual imports
# ============================================================================

from asi_build.federated.aggregation.base_aggregator import BaseAggregator  # noqa: E402
from asi_build.federated.aggregation.fedavg import FedAvgAggregator  # noqa: E402
from asi_build.federated.aggregation.secure_aggregation import SecretSharing  # noqa: E402
from asi_build.federated.core.config import (  # noqa: E402
    DEFAULT_CONFIG,
    SECURE_CONFIG,
    AggregationType,
    ClientConfig,
    CommunicationProtocol,
    CompressionConfig,
    FederatedConfig,
    PrivacyConfig,
    PrivacyMechanism,
    SecurityConfig,
    ServerConfig,
)
from asi_build.federated.core.exceptions import (  # noqa: E402
    AggregationError,
    CommunicationError,
    FederatedLearningError,
    PrivacyError,
    SecurityError,
    ValidationError,
)
from asi_build.federated.privacy.differential_privacy import (  # noqa: E402
    DifferentialPrivacyManager,
    GaussianMechanism,
    LaplaceMechanism,
    RenyiDifferentialPrivacy,
)
from asi_build.federated.utils.metrics import (  # noqa: E402
    ConvergenceTracker,
    FederatedMetrics,
    PerformanceTracker,
)
from asi_build.federated.utils.model_compression import (  # noqa: E402
    CompressionManager,
    PruningCompressor,
    QuantizationCompressor,
    create_compressor,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_client_update(client_id, weights, data_size=100, metrics=None):
    """Build a client-update dict for aggregator tests."""
    upd = {"client_id": client_id, "weights": weights, "data_size": data_size}
    if metrics is not None:
        upd["metrics"] = metrics
    return upd


def _rand_weights(shapes=((4, 3), (3,)), seed=None):
    """Create a list of random numpy weight arrays."""
    rng = np.random.RandomState(seed)
    return [rng.randn(*s).astype(np.float32) for s in shapes]


# ############################################################################
# 1. Config — 13 tests
# ############################################################################


class TestEnums:
    def test_aggregation_type_values(self):
        assert AggregationType.FEDAVG.value == "fedavg"
        assert AggregationType.SCAFFOLD.value == "scaffold"

    def test_privacy_mechanism_values(self):
        assert PrivacyMechanism.NONE.value == "none"
        assert PrivacyMechanism.DIFFERENTIAL_PRIVACY.value == "differential_privacy"

    def test_communication_protocol_values(self):
        assert CommunicationProtocol.HTTP.value == "http"
        assert CommunicationProtocol.GRPC.value == "grpc"


class TestPrivacyConfig:
    def test_defaults(self):
        cfg = PrivacyConfig()
        assert cfg.mechanism == PrivacyMechanism.NONE
        assert cfg.epsilon == 1.0
        assert cfg.delta == 1e-5


class TestSecurityConfig:
    def test_defaults(self):
        cfg = SecurityConfig()
        assert cfg.enable_tls is True
        assert cfg.authentication_required is True
        assert cfg.max_requests_per_minute == 100


class TestCompressionConfig:
    def test_defaults(self):
        cfg = CompressionConfig()
        assert cfg.enable_compression is False
        assert cfg.quantization_bits == 8


class TestClientConfig:
    def test_auto_creates_nested(self):
        cc = ClientConfig(client_id="c1")
        assert isinstance(cc.privacy, PrivacyConfig)
        assert isinstance(cc.compression, CompressionConfig)


class TestServerConfig:
    def test_auto_creates_nested(self):
        sc = ServerConfig()
        assert isinstance(sc.privacy, PrivacyConfig)
        assert isinstance(sc.security, SecurityConfig)


class TestFederatedConfig:
    def test_construction_defaults(self):
        fc = FederatedConfig()
        assert fc.experiment_name == "federated_experiment"
        assert fc.client is not None
        assert fc.server is not None

    def test_validate_passes(self):
        assert FederatedConfig().validate() is True

    def test_validate_min_gt_max_fails(self):
        fc = FederatedConfig()
        fc.server.min_clients = 200
        fc.server.max_clients = 10
        with pytest.raises(ValueError, match="min_clients"):
            fc.validate()

    def test_validate_bad_client_fraction(self):
        fc = FederatedConfig()
        fc.server.client_fraction = 0.0
        with pytest.raises(ValueError, match="client_fraction"):
            fc.validate()

    def test_to_dict_from_dict_roundtrip(self):
        fc = FederatedConfig(experiment_name="roundtrip")
        d = fc.to_dict()
        fc2 = FederatedConfig.from_dict(d)
        assert fc2.experiment_name == "roundtrip"
        assert fc2.server.aggregation_type == AggregationType.FEDAVG

    def test_default_config_constant(self):
        assert DEFAULT_CONFIG.experiment_name == "default_federated_experiment"

    def test_secure_config_constant(self):
        assert SECURE_CONFIG.server.privacy.mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY


# ############################################################################
# 2. Exceptions — 8 tests
# ############################################################################


class TestExceptions:
    def test_base_with_details(self):
        e = FederatedLearningError("boom", details={"k": "v"})
        assert e.message == "boom"
        assert e.details == {"k": "v"}

    def test_base_str_includes_details(self):
        e = FederatedLearningError("boom", details={"x": 1})
        assert "Details" in str(e)

    def test_communication_error_fields(self):
        e = CommunicationError("timeout", client_id="c1", error_code="E001")
        assert e.client_id == "c1"
        assert e.error_code == "E001"

    def test_aggregation_error_fields(self):
        e = AggregationError("fail", aggregator_type="fedavg", client_count=3)
        assert e.aggregator_type == "fedavg"
        assert e.client_count == 3

    def test_privacy_error_fields(self):
        e = PrivacyError("budget", privacy_mechanism="gaussian", privacy_budget=0.5)
        assert e.privacy_mechanism == "gaussian"
        assert e.privacy_budget == 0.5

    def test_security_error_fields(self):
        e = SecurityError("bad", security_level="high", threat_type="poison")
        assert e.security_level == "high"
        assert e.threat_type == "poison"

    def test_isinstance_chain(self):
        assert isinstance(AggregationError("x"), FederatedLearningError)

    def test_validation_error_fields(self):
        e = ValidationError("bad", validation_type="shape", expected_value=10, actual_value=5)
        assert e.validation_type == "shape"
        assert e.expected_value == 10
        assert e.actual_value == 5


# ############################################################################
# 3. BaseAggregator — 8 tests (via FedAvgAggregator as concrete subclass)
# ############################################################################


class TestBaseAggregator:
    def test_validate_passes(self):
        agg = FedAvgAggregator()
        updates = [
            _make_client_update("c1", _rand_weights()),
            _make_client_update("c2", _rand_weights()),
        ]
        assert agg.validate_updates(updates) is True

    def test_validate_too_few(self):
        agg = FedAvgAggregator(config={"min_clients": 3})
        with pytest.raises(AggregationError, match="Insufficient"):
            agg.validate_updates([_make_client_update("c1", _rand_weights())])

    def test_validate_missing_field(self):
        agg = FedAvgAggregator()
        bad = [
            {"client_id": "c1", "weights": _rand_weights()},  # no data_size
            _make_client_update("c2", _rand_weights()),
        ]
        with pytest.raises(AggregationError, match="missing required field"):
            agg.validate_updates(bad)

    def test_clip_weights_reduces_norm(self):
        agg = FedAvgAggregator(config={"clip_norm": 1.0})
        big = [np.ones((10,), dtype=np.float32) * 100]
        clipped = agg.clip_weights(big)
        assert np.linalg.norm(clipped[0]) <= 1.0 + 1e-6

    def test_clip_noop_small(self):
        agg = FedAvgAggregator(config={"clip_norm": 1000.0})
        small = [np.ones((3,), dtype=np.float32)]
        np.testing.assert_array_almost_equal(agg.clip_weights(small)[0], small[0])

    def test_add_noise_nonzero(self):
        agg = FedAvgAggregator(config={"noise_multiplier": 0.5})
        w = [np.zeros((50,), dtype=np.float32)]
        assert not np.allclose(agg.add_noise(w)[0], 0.0)

    def test_equal_weights(self):
        agg = FedAvgAggregator(config={"weight_by_samples": False})
        updates = [_make_client_update(f"c{i}", _rand_weights()) for i in range(4)]
        np.testing.assert_allclose(agg.compute_client_weights(updates), [0.25] * 4, atol=1e-8)

    def test_proportional_weights(self):
        agg = FedAvgAggregator(config={"weight_by_samples": True})
        updates = [
            _make_client_update("c1", _rand_weights(), data_size=300),
            _make_client_update("c2", _rand_weights(), data_size=100),
        ]
        np.testing.assert_allclose(agg.compute_client_weights(updates), [0.75, 0.25], atol=1e-8)


# ############################################################################
# 4. FedAvg — 8 tests
# ############################################################################


class TestFedAvg:
    def _updates(self, n=3, data_size=100, seed=42):
        rng = np.random.RandomState(seed)
        return [
            _make_client_update(
                f"c{i}",
                [rng.randn(4, 3).astype(np.float32), rng.randn(3).astype(np.float32)],
                data_size=data_size,
            )
            for i in range(n)
        ]

    def test_aggregate_basic(self):
        result = FedAvgAggregator().aggregate(self._updates())
        assert "aggregated_weights" in result
        assert len(result["aggregated_weights"]) == 2
        assert result["num_clients"] == 3

    def test_aggregate_weighted(self):
        agg = FedAvgAggregator(config={"weight_by_samples": True})
        w_big = _rand_weights(seed=7)
        updates = [
            _make_client_update("c1", [w.copy() for w in w_big], data_size=10000),
            _make_client_update("c2", _rand_weights(seed=8), data_size=1),
        ]
        result = agg.aggregate(updates)
        for a, o in zip(result["aggregated_weights"], w_big):
            np.testing.assert_allclose(a, o, atol=0.01)

    def test_adaptive_weights(self):
        agg = FedAvgAggregator(config={"adaptive_weighting": True})
        updates = [
            _make_client_update(
                "c1", _rand_weights(seed=1), 100, metrics={"loss": 0.1, "accuracy": 0.95}
            ),
            _make_client_update(
                "c2", _rand_weights(seed=2), 100, metrics={"loss": 5.0, "accuracy": 0.1}
            ),
        ]
        w = agg._compute_adaptive_weights(updates)
        assert w[0] > w[1]

    def test_weighted_averaging_known(self):
        agg = FedAvgAggregator()
        result = agg._weighted_averaging(
            [[np.array([1.0, 0.0])], [np.array([0.0, 1.0])]],
            [0.3, 0.7],
        )
        np.testing.assert_allclose(result[0], [0.3, 0.7])

    def test_server_momentum(self):
        agg = FedAvgAggregator(config={"momentum": 0.9, "server_learning_rate": 1.0})
        w = [np.array([1.0, 2.0, 3.0])]
        # First call — no previous → lr * weights
        out1 = agg._apply_server_optimization(w)
        np.testing.assert_allclose(out1[0], w[0])
        # Second call with previous = zeros
        agg.previous_global_weights = [np.zeros(3)]
        out2 = agg._apply_server_optimization(w)
        np.testing.assert_allclose(out2[0], [0.1, 0.2, 0.3], atol=1e-6)

    def test_specific_stats(self):
        stats = FedAvgAggregator(config={"momentum": 0.5}).get_fedavg_specific_stats()
        assert stats["algorithm"] == "FedAvg"
        assert stats["momentum"] == 0.5

    def test_reset_server_state(self):
        agg = FedAvgAggregator()
        agg.server_momentum_buffer = [np.zeros(3)]
        agg.previous_global_weights = [np.ones(3)]
        agg.reset_server_state()
        assert agg.server_momentum_buffer is None
        assert agg.previous_global_weights is None

    def test_weighted_average_base_method(self):
        agg = FedAvgAggregator()
        w1 = [np.array([1.0, 2.0])]
        w2 = [np.array([3.0, 4.0])]
        avg = agg.weighted_average([w1, w2], [0.5, 0.5])
        np.testing.assert_allclose(avg[0], [2.0, 3.0])


# ############################################################################
# 5. Metrics — 8 tests
# ############################################################################


class TestFederatedMetrics:
    def test_record_and_summary(self):
        fm = FederatedMetrics()
        for i in range(10):
            fm.record_round_metric(i, "loss", 1.0 - i * 0.1)
        s = fm.get_metric_summary("loss")
        assert s["count"] == 10
        assert s["min"] == pytest.approx(0.1, abs=0.01)

    def test_trend_increasing(self):
        fm = FederatedMetrics()
        for i in range(20):
            fm.record_round_metric(i, "acc", i * 0.05)
        assert fm.get_metric_summary("acc")["trend"] == "increasing"

    def test_trend_decreasing(self):
        fm = FederatedMetrics()
        for i in range(20):
            fm.record_round_metric(i, "loss", 1.0 - i * 0.04)
        assert fm.get_metric_summary("loss")["trend"] == "decreasing"

    def test_trend_stable(self):
        fm = FederatedMetrics()
        for i in range(20):
            fm.record_round_metric(i, "flat", 0.5)
        assert fm.get_metric_summary("flat")["trend"] == "stable"


class TestPerformanceTracker:
    def test_record_and_performance(self):
        pt = PerformanceTracker()
        for _ in range(5):
            pt.record_round_completion(0.1, 3)
        perf = pt.get_current_performance()
        assert perf["rounds_completed"] == 5
        assert "avg_round_time" in perf

    def test_detect_issues_empty(self):
        assert isinstance(PerformanceTracker().detect_performance_issues(), list)

    def test_detect_stagnant_accuracy(self):
        pt = PerformanceTracker()
        for _ in range(20):
            pt.record_model_performance(accuracy=0.85, loss=0.3)
        types = [i["type"] for i in pt.detect_performance_issues()]
        assert "stagnant_accuracy" in types


class TestConvergenceTracker:
    def test_not_converged_initially(self):
        assert ConvergenceTracker(patience=5).update(1.0, 0.5)["converged"] is False

    def test_converges_when_stable(self):
        ct = ConvergenceTracker(patience=3, threshold=0.001)
        ct.update(1.0, 0.5)
        ct.update(0.5, 0.7)
        ct.update(0.3, 0.8)
        for _ in range(4):
            r = ct.update(0.3, 0.8)
        assert r["converged"] is True

    def test_analysis(self):
        ct = ConvergenceTracker()
        ct.update(1.0, 0.5)
        ct.update(0.8, 0.6)
        a = ct.get_convergence_analysis()
        assert "loss_analysis" in a
        assert a["total_rounds"] == 2


# ############################################################################
# 6. ModelCompression — 6 tests
# ############################################################################


class TestQuantization:
    def test_roundtrip(self):
        qc = QuantizationCompressor({"quantization_bits": 8})
        orig = _rand_weights(shapes=((10, 5),), seed=0)
        compressed, meta = qc.compress(orig)
        restored = qc.decompress(compressed, meta)
        np.testing.assert_allclose(restored[0], orig[0], atol=0.05)

    def test_uniform_range(self):
        qc = QuantizationCompressor({"quantization_bits": 8, "method": "uniform"})
        w = [np.linspace(-1, 1, 100).astype(np.float32)]
        compressed, _ = qc.compress(w)
        qv = compressed["layer_0"]["quantized_values"]
        assert qv.min() >= 0
        assert qv.max() <= 255


class TestPruning:
    def test_sparsity_achieved(self):
        pc = PruningCompressor({"sparsity_ratio": 0.5, "method": "magnitude"})
        w = [np.random.randn(100).astype(np.float32)]
        _, meta = pc.compress(w)
        sp = meta["layer_info"]["layer_0"]["sparsity_achieved"]
        assert 0.4 <= sp <= 0.6

    def test_roundtrip(self):
        pc = PruningCompressor({"sparsity_ratio": 0.3, "method": "magnitude"})
        orig = [np.random.randn(8, 4).astype(np.float32)]
        compressed, meta = pc.compress(orig)
        restored = pc.decompress(compressed, meta)
        mask = compressed["layer_0"]["pruning_mask"]
        np.testing.assert_allclose(restored[0][mask], orig[0][mask], atol=1e-6)


class TestCompressorFactory:
    def test_factory(self):
        assert isinstance(
            create_compressor("quantization", {"quantization_bits": 4}), QuantizationCompressor
        )
        assert isinstance(create_compressor("pruning", {"sparsity_ratio": 0.2}), PruningCompressor)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown compression"):
            create_compressor("bogus", {})


class TestCompressionManager:
    def test_multi_stage(self):
        mgr = CompressionManager(
            [
                {"type": "pruning", "sparsity_ratio": 0.2, "method": "magnitude"},
                {"type": "quantization", "quantization_bits": 8},
            ]
        )
        compressed, meta = mgr.compress_weights(_rand_weights(shapes=((20, 10),), seed=5))
        assert len(meta["compression_stages"]) == 2


# ############################################################################
# 7. SecretSharing — 4 tests
# ############################################################################


class TestSecretSharing:
    def test_polynomial_length(self):
        ss = SecretSharing(threshold=3, num_parties=5)
        coeffs = ss.generate_polynomial_coefficients(42)
        assert len(coeffs) == 3
        assert coeffs[0] == 42

    def test_shares_count(self):
        shares = SecretSharing(threshold=3, num_parties=5).create_shares(12345)
        assert len(shares) == 5
        assert all(len(s) == 2 for s in shares)

    def test_reconstruction(self):
        ss = SecretSharing(threshold=3, num_parties=5)
        secret = 9999
        shares = ss.create_shares(secret)
        assert ss.lagrange_interpolation(shares[:3]) == secret

    def test_insufficient_shares(self):
        ss = SecretSharing(threshold=3, num_parties=5)
        shares = ss.create_shares(42)
        with pytest.raises(SecurityError):
            ss.lagrange_interpolation(shares[:2])


# ############################################################################
# 8. Differential Privacy — 7 tests
# ############################################################################


class TestLaplace:
    def test_shape_preserved(self):
        noisy = LaplaceMechanism(epsilon=1.0).add_noise(np.zeros((10, 5)), sensitivity=1.0)
        assert noisy.shape == (10, 5)

    def test_noise_added(self):
        noisy = LaplaceMechanism(epsilon=1.0).add_noise(np.zeros(100), sensitivity=1.0)
        assert not np.allclose(noisy, 0.0)


class TestGaussian:
    def test_invalid_delta(self):
        with pytest.raises(PrivacyError, match="Delta"):
            GaussianMechanism(epsilon=1.0, delta=0.0)

    def test_shape_preserved(self):
        noisy = GaussianMechanism(1.0, 1e-5).add_noise(np.ones((5, 5)), sensitivity=1.0)
        assert noisy.shape == (5, 5)


class TestDPManager:
    def test_clip_gradients(self):
        dpm = DifferentialPrivacyManager({"max_grad_norm": 1.0, "mechanism": "laplace"})
        grads = [np.ones(10, dtype=np.float32) * 10]
        clipped, _ = dpm.clip_gradients(grads)
        total = math.sqrt(sum(np.sum(g**2) for g in clipped))
        assert total <= 1.0 + 1e-6

    def test_clip_noop(self):
        dpm = DifferentialPrivacyManager({"max_grad_norm": 100.0, "mechanism": "laplace"})
        grads = [np.array([0.1, 0.2])]
        clipped, _ = dpm.clip_gradients(grads)
        np.testing.assert_allclose(clipped[0], grads[0])


class TestRenyiDP:
    def test_compute_rdp_positive(self):
        vals = RenyiDifferentialPrivacy().compute_rdp(noise_multiplier=1.0, num_steps=100)
        assert all(r >= 0 for r in vals)
