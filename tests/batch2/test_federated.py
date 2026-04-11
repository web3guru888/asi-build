import pytest
tf = pytest.importorskip("tensorflow", reason="tensorflow not installed")
tensorflow = pytest.importorskip("tensorflow")
"""Tests for federated learning module (Candidate 7)."""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch


class TestFedAvgAggregator:
    """Test FedAvg weighted averaging."""

    def _make_aggregator(self, **kwargs):
        from src.asi_build.federated.aggregation.fedavg import FedAvgAggregator
        return FedAvgAggregator(config=kwargs)

    def test_init_defaults(self):
        agg = self._make_aggregator()
        assert agg.momentum == 0.0
        assert agg.server_learning_rate == 1.0
        assert agg.adaptive_weighting is False

    def test_weighted_averaging_uniform(self):
        agg = self._make_aggregator()
        weights_a = [np.array([1.0, 2.0]), np.array([3.0])]
        weights_b = [np.array([3.0, 4.0]), np.array([5.0])]
        result = agg._weighted_averaging([weights_a, weights_b], [0.5, 0.5])
        np.testing.assert_allclose(result[0], [2.0, 3.0])
        np.testing.assert_allclose(result[1], [4.0])

    def test_weighted_averaging_biased(self):
        agg = self._make_aggregator()
        w1 = [np.array([0.0, 0.0])]
        w2 = [np.array([10.0, 10.0])]
        result = agg._weighted_averaging([w1, w2], [0.2, 0.8])
        np.testing.assert_allclose(result[0], [8.0, 8.0])

    def test_server_optimization_momentum(self):
        agg = self._make_aggregator(momentum=0.9, server_learning_rate=1.0)
        initial = [np.array([1.0, 1.0])]
        agg.previous_global_weights = [np.array([0.0, 0.0])]
        result = agg._apply_server_optimization(initial)
        # With momentum and previous weights at 0, update = 1.0
        # momentum_buffer = 0.1 * 1.0 = 0.1 (momentum=0.9, so (1-0.9)*update)
        assert result[0].shape == (2,)

    def test_adaptive_weights_normalize(self):
        agg = self._make_aggregator(adaptive_weighting=True)
        updates = [
            {"data_size": 100, "metrics": {"loss": 0.5, "accuracy": 0.8}},
            {"data_size": 200, "metrics": {"loss": 1.0, "accuracy": 0.6}},
        ]
        weights = agg._compute_adaptive_weights(updates)
        assert abs(sum(weights) - 1.0) < 1e-6

    def test_adaptive_weights_lower_loss_higher_weight(self):
        agg = self._make_aggregator(adaptive_weighting=True)
        updates = [
            {"data_size": 100, "metrics": {"loss": 0.1, "accuracy": 0.9}},
            {"data_size": 100, "metrics": {"loss": 5.0, "accuracy": 0.1}},
        ]
        weights = agg._compute_adaptive_weights(updates)
        assert weights[0] > weights[1]

    def test_reset_server_state(self):
        agg = self._make_aggregator()
        agg.server_momentum_buffer = [np.zeros(3)]
        agg.previous_global_weights = [np.ones(3)]
        agg.reset_server_state()
        assert agg.server_momentum_buffer is None
        assert agg.previous_global_weights is None


class TestByzantineRobust:
    """Test Byzantine-robust aggregation."""

    def _make_aggregator(self, **kwargs):
        from src.asi_build.federated.aggregation.byzantine_robust import ByzantineRobustAggregator
        cfg = {"defense_method": "krum", "num_byzantine": 1}
        cfg.update(kwargs)
        return ByzantineRobustAggregator(config=cfg)

    def test_krum_selects_closest(self):
        agg = self._make_aggregator(defense_method="krum", num_byzantine=1)
        # 3 clients, one is an outlier
        w_honest1 = [np.array([1.0, 1.0])]
        w_honest2 = [np.array([1.1, 0.9])]
        w_outlier = [np.array([100.0, 100.0])]
        result, info = agg._krum_aggregation(
            [w_honest1, w_honest2, w_outlier],
            [100, 100, 100],
            ["c1", "c2", "c_bad"]
        )
        # Krum should select one of the honest clients
        assert info["selected_client"] in ["c1", "c2"]

    def test_trimmed_mean_removes_extremes(self):
        agg = self._make_aggregator(defense_method="trimmed_mean", trimmed_mean_ratio=0.2)
        # 5 clients, two extremes
        weights = [
            [np.array([0.0])],    # extreme low
            [np.array([1.0])],
            [np.array([1.1])],
            [np.array([0.9])],
            [np.array([100.0])],  # extreme high
        ]
        result, info = agg._trimmed_mean_aggregation(weights, [100]*5)
        # After trimming 1 from each end, should be ~1.0
        assert 0.5 < result[0][0] < 1.5

    def test_coordinate_wise_median(self):
        agg = self._make_aggregator(defense_method="median")
        weights = [[np.array([v])] for v in [1.0, 2.0, 3.0, 100.0, -50.0]]
        result, info = agg._coordinate_wise_median(weights, [100]*5)
        assert abs(result[0][0] - 2.0) < 0.01

    def test_detect_byzantine_scores_normalized(self):
        agg = self._make_aggregator(enable_anomaly_detection=True)
        w_normal = [np.array([1.0, 1.0])]
        w_bad = [np.array([999.0, 999.0])]
        scores = agg._detect_byzantine_clients(
            [w_normal, w_normal, w_bad],
            ["c1", "c2", "c3"]
        )
        assert len(scores) == 3
        assert max(scores) <= 1.0
        assert scores[2] >= scores[0]  # outlier has highest score


class TestSecureAggregation:
    """Test secure aggregation primitives."""

    def test_shamir_secret_sharing_roundtrip(self):
        from src.asi_build.federated.aggregation.secure_aggregation import SecretSharing
        ss = SecretSharing(threshold=3, num_parties=5)
        secret = 42
        shares = ss.create_shares(secret)
        assert len(shares) == 5
        # Reconstruct from first 3 shares
        recovered = ss.lagrange_interpolation(shares[:3])
        assert recovered == secret

    def test_shamir_insufficient_shares_raises(self):
        from src.asi_build.federated.aggregation.secure_aggregation import SecretSharing
        ss = SecretSharing(threshold=3, num_parties=5)
        shares = ss.create_shares(100)
        with pytest.raises(Exception):
            ss.lagrange_interpolation(shares[:2])

    def test_paillier_encrypt_decrypt(self):
        from src.asi_build.federated.aggregation.secure_aggregation import PaillierCryptosystem
        paillier = PaillierCryptosystem(key_size=64)  # small for speed
        plaintext = 42
        ciphertext = paillier.encrypt(plaintext)
        decrypted = paillier.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_paillier_homomorphic_addition(self):
        from src.asi_build.federated.aggregation.secure_aggregation import PaillierCryptosystem
        paillier = PaillierCryptosystem(key_size=64)
        c1 = paillier.encrypt(10)
        c2 = paillier.encrypt(32)
        c_sum = paillier.add_encrypted(c1, c2)
        decrypted_sum = paillier.decrypt(c_sum)
        assert decrypted_sum == 42


class TestDifferentialPrivacy:
    """Test differential privacy mechanisms."""

    def test_laplace_adds_noise(self):
        from src.asi_build.federated.privacy.differential_privacy import LaplaceMechanism
        mech = LaplaceMechanism(epsilon=1.0)
        data = np.zeros(1000)
        noisy = mech.add_noise(data, sensitivity=1.0)
        assert not np.allclose(data, noisy)
        assert abs(np.mean(noisy)) < 0.2  # mean should be close to 0

    def test_gaussian_noise_scale(self):
        from src.asi_build.federated.privacy.differential_privacy import GaussianMechanism
        mech = GaussianMechanism(epsilon=1.0, delta=0.01)
        sigma = mech.compute_noise_scale(sensitivity=1.0)
        assert sigma > 0

    def test_dp_manager_budget_tracking(self):
        from src.asi_build.federated.privacy.differential_privacy import DifferentialPrivacyManager
        mgr = DifferentialPrivacyManager({"epsilon": 10.0, "delta": 1e-5, "max_grad_norm": 1.0})
        grads = [np.random.randn(5)]
        mgr.add_noise_to_gradients(grads)
        status = mgr.get_privacy_status()
        assert status["epsilon_spent"] > 0
        assert status["query_count"] == 1

    def test_gradient_clipping(self):
        from src.asi_build.federated.privacy.differential_privacy import DifferentialPrivacyManager
        mgr = DifferentialPrivacyManager({"epsilon": 1.0, "delta": 1e-5, "max_grad_norm": 1.0})
        big_grad = [np.ones(100) * 100]
        clipped, norm = mgr.clip_gradients(big_grad)
        total_norm = np.sqrt(sum(np.sum(g**2) for g in clipped))
        assert total_norm <= 1.0 + 1e-6

    def test_renyi_dp_computation(self):
        from src.asi_build.federated.privacy.differential_privacy import RenyiDifferentialPrivacy
        rdp = RenyiDifferentialPrivacy()
        eps = rdp.compute_dp_from_gaussian(noise_multiplier=1.0, num_steps=100, delta=1e-5)
        assert eps > 0 and eps < float('inf')
