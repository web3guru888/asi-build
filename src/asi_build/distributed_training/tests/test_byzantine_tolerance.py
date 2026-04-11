"""
Comprehensive tests for Byzantine Fault Tolerance system
"""

import time
from unittest.mock import Mock, patch

import numpy as np
import pytest
import torch

from ..core.byzantine_tolerance import (
    AdaptiveByzantineDefense,
    AggregationResult,
    AttackType,
    ByzantineDetector,
    ByzantineTolerantAggregator,
    NodeBehavior,
)


@pytest.fixture
def sample_gradients():
    """Sample gradients for testing"""
    return {
        "node_1": {
            "layer1.weight": torch.randn(10, 5),
            "layer1.bias": torch.randn(10),
            "layer2.weight": torch.randn(1, 10),
        },
        "node_2": {
            "layer1.weight": torch.randn(10, 5),
            "layer1.bias": torch.randn(10),
            "layer2.weight": torch.randn(1, 10),
        },
        "node_3": {
            "layer1.weight": torch.randn(10, 5),
            "layer1.bias": torch.randn(10),
            "layer2.weight": torch.randn(1, 10),
        },
    }


@pytest.fixture
def malicious_gradients():
    """Gradients with malicious modifications"""
    gradients = {
        "honest_1": {
            "layer1.weight": torch.randn(10, 5) * 0.1,
            "layer1.bias": torch.randn(10) * 0.1,
        },
        "honest_2": {
            "layer1.weight": torch.randn(10, 5) * 0.1,
            "layer1.bias": torch.randn(10) * 0.1,
        },
        "malicious_1": {
            "layer1.weight": torch.randn(10, 5) * 10,  # Abnormally large gradients
            "layer1.bias": torch.randn(10) * 10,
        },
        "malicious_2": {
            "layer1.weight": -torch.randn(10, 5) * 5,  # Sign-flipped gradients
            "layer1.bias": -torch.randn(10) * 5,
        },
    }
    return gradients


@pytest.fixture
def detector_config():
    """Configuration for Byzantine detector"""
    return {
        "norm_deviation_threshold": 2.0,
        "similarity_threshold": 0.1,
        "timing_correlation_threshold": 0.8,
        "reputation_decay_rate": 0.05,
    }


@pytest.fixture
def aggregator_config():
    """Configuration for Byzantine tolerant aggregator"""
    return {
        "aggregation_method": "krum",
        "byzantine_ratio": 0.3,
        "detection": {"norm_deviation_threshold": 2.0, "similarity_threshold": 0.1},
    }


class TestByzantineDetector:
    """Test cases for Byzantine detection"""

    def test_detector_initialization(self, detector_config):
        """Test detector initialization"""
        detector = ByzantineDetector(detector_config)

        assert detector.norm_deviation_threshold == 2.0
        assert detector.similarity_threshold == 0.1
        assert detector.timing_correlation_threshold == 0.8
        assert len(detector.node_behaviors) == 0

    def test_gradient_analysis_honest_nodes(self, detector_config, sample_gradients):
        """Test gradient analysis with honest nodes"""
        detector = ByzantineDetector(detector_config)

        suspicion_scores = detector.analyze_gradients(sample_gradients)

        # All nodes should have low suspicion scores
        assert len(suspicion_scores) == 3
        for node_id, score in suspicion_scores.items():
            assert 0.0 <= score <= 1.0
            assert score < 0.5  # Should be low for honest nodes

    def test_gradient_analysis_with_malicious(self, detector_config, malicious_gradients):
        """Test gradient analysis with malicious nodes"""
        detector = ByzantineDetector(detector_config)

        suspicion_scores = detector.analyze_gradients(malicious_gradients)

        # Malicious nodes should have higher suspicion scores
        assert suspicion_scores["malicious_1"] > suspicion_scores["honest_1"]
        assert suspicion_scores["malicious_2"] > suspicion_scores["honest_2"]

    def test_cosine_similarity_calculation(self, detector_config):
        """Test cosine similarity calculation"""
        detector = ByzantineDetector(detector_config)

        # Create identical gradients
        grad1 = {"param": torch.ones(5)}
        grad2 = {"param": torch.ones(5)}

        similarity = detector._calculate_cosine_similarity(grad1, grad2)
        assert abs(similarity - 1.0) < 1e-6  # Should be 1.0 for identical

        # Create orthogonal gradients
        grad3 = {"param": torch.tensor([1.0, 0.0, 0.0, 0.0, 0.0])}
        grad4 = {"param": torch.tensor([0.0, 1.0, 0.0, 0.0, 0.0])}

        similarity = detector._calculate_cosine_similarity(grad3, grad4)
        assert abs(similarity - 0.0) < 1e-6  # Should be 0.0 for orthogonal

    def test_node_behavior_tracking(self, detector_config, sample_gradients):
        """Test node behavior tracking"""
        detector = ByzantineDetector(detector_config)

        # Analyze gradients to create behavior tracking
        detector.analyze_gradients(sample_gradients)

        # Check that node behaviors were created
        assert len(detector.node_behaviors) == 3

        for node_id in sample_gradients.keys():
            assert node_id in detector.node_behaviors
            behavior = detector.node_behaviors[node_id]
            assert isinstance(behavior, NodeBehavior)
            assert len(behavior.gradient_norms) == 1

    def test_trusted_nodes_selection(self, detector_config):
        """Test trusted nodes selection"""
        detector = ByzantineDetector(detector_config)

        # Create mock node behaviors
        detector.node_behaviors = {
            "trusted_1": NodeBehavior("trusted_1", [], [], [], [], 0.8, 0.8, [], time.time()),
            "trusted_2": NodeBehavior("trusted_2", [], [], [], [], 0.7, 0.7, [], time.time()),
            "untrusted": NodeBehavior("untrusted", [], [], [], [], 0.2, 0.2, [], time.time()),
        }

        trusted = detector.get_trusted_nodes(
            ["trusted_1", "trusted_2", "untrusted"], min_trust_score=0.5
        )

        assert "trusted_1" in trusted
        assert "trusted_2" in trusted
        assert "untrusted" not in trusted

    def test_coordinated_attack_detection(self, detector_config):
        """Test detection of coordinated attacks"""
        detector = ByzantineDetector(detector_config)

        # Create gradients with coordinated similar patterns
        coordinated_gradients = {
            "sybil_1": {"param": torch.ones(5) * 0.5},
            "sybil_2": {"param": torch.ones(5) * 0.51},  # Very similar to sybil_1
            "sybil_3": {"param": torch.ones(5) * 0.49},  # Very similar to sybil_1
            "honest": {"param": torch.randn(5)},
        }

        suspicious_groups = detector.detect_coordinated_attacks(coordinated_gradients)

        # Should detect the coordinated group
        assert len(suspicious_groups) > 0

        # The detected group should contain the similar nodes
        detected_group = suspicious_groups[0]
        assert len(detected_group) >= 3


class TestByzantineTolerantAggregator:
    """Test cases for Byzantine tolerant aggregation"""

    def test_aggregator_initialization(self, aggregator_config):
        """Test aggregator initialization"""
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        assert aggregator.aggregation_method == "krum"
        assert aggregator.byzantine_ratio == 0.3
        assert isinstance(aggregator.detector, ByzantineDetector)

    @pytest.mark.asyncio
    async def test_krum_aggregation(self, aggregator_config, sample_gradients):
        """Test Multi-Krum aggregation"""
        aggregator_config["aggregation_method"] = "krum"
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        result = await aggregator.aggregate(sample_gradients)

        assert isinstance(result, AggregationResult)
        assert result.aggregation_method == "multi_krum"
        assert len(result.aggregated_gradients) > 0
        assert len(result.honest_participants) > 0
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_trimmed_mean_aggregation(self, aggregator_config, sample_gradients):
        """Test trimmed mean aggregation"""
        aggregator_config["aggregation_method"] = "trimmed_mean"
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        result = await aggregator.aggregate(sample_gradients)

        assert result.aggregation_method == "trimmed_mean"
        assert len(result.aggregated_gradients) > 0

        # Check that aggregated gradients have correct shapes
        for param_name, aggregated_param in result.aggregated_gradients.items():
            original_shape = sample_gradients["node_1"][param_name].shape
            assert aggregated_param.shape == original_shape

    @pytest.mark.asyncio
    async def test_median_aggregation(self, aggregator_config, sample_gradients):
        """Test coordinate-wise median aggregation"""
        aggregator_config["aggregation_method"] = "median"
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        result = await aggregator.aggregate(sample_gradients)

        assert result.aggregation_method == "coordinate_median"
        assert len(result.aggregated_gradients) > 0

    @pytest.mark.asyncio
    async def test_aggregation_with_malicious_nodes(self, aggregator_config, malicious_gradients):
        """Test aggregation in presence of malicious nodes"""
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        result = await aggregator.aggregate(malicious_gradients)

        # Should identify malicious nodes
        assert len(result.suspected_byzantine) > 0
        assert (
            "malicious_1" in result.suspected_byzantine
            or "malicious_2" in result.suspected_byzantine
        )

        # Honest nodes should be in honest participants
        assert "honest_1" in result.honest_participants
        assert "honest_2" in result.honest_participants

    def test_euclidean_distance_calculation(self, aggregator_config):
        """Test Euclidean distance calculation"""
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        grad1 = {"param": torch.zeros(3)}
        grad2 = {"param": torch.ones(3)}

        distance = aggregator._calculate_euclidean_distance(grad1, grad2)
        expected_distance = np.sqrt(3)  # sqrt(1^2 + 1^2 + 1^2)

        assert abs(distance - expected_distance) < 1e-6

    def test_gradient_averaging(self, aggregator_config):
        """Test gradient averaging functionality"""
        aggregator = ByzantineTolerantAggregator(aggregator_config)

        gradients = [
            {"param": torch.ones(3)},
            {"param": torch.zeros(3)},
            {"param": torch.ones(3) * 2},
        ]

        averaged = aggregator._average_gradients(gradients)
        expected = torch.ones(3)  # (1 + 0 + 2) / 3 = 1

        assert torch.allclose(averaged["param"], expected)


class TestAdaptiveByzantineDefense:
    """Test cases for adaptive Byzantine defense"""

    @pytest.fixture
    def defense_config(self):
        """Configuration for adaptive defense"""
        return {
            "aggregation_method": "krum",
            "byzantine_ratio": 0.3,
            "adaptation_rate": 0.1,
            "min_samples": 5,
        }

    def test_defense_initialization(self, defense_config):
        """Test adaptive defense initialization"""
        defense = AdaptiveByzantineDefense(defense_config)

        assert isinstance(defense.aggregator, ByzantineTolerantAggregator)
        assert len(defense.defense_effectiveness) > 0
        assert "krum" in defense.defense_effectiveness
        assert "trimmed_mean" in defense.defense_effectiveness

    def test_threat_level_assessment(self, defense_config, sample_gradients):
        """Test threat level assessment"""
        defense = AdaptiveByzantineDefense(defense_config)

        threat_level = defense._assess_threat_level(sample_gradients)

        assert 0.0 <= threat_level <= 1.0

    def test_threat_level_with_malicious(self, defense_config, malicious_gradients):
        """Test threat level with malicious gradients"""
        defense = AdaptiveByzantineDefense(defense_config)

        threat_level = defense._assess_threat_level(malicious_gradients)

        # Should detect higher threat with malicious nodes
        assert threat_level > 0.0

    def test_optimal_method_selection(self, defense_config):
        """Test optimal aggregation method selection"""
        defense = AdaptiveByzantineDefense(defense_config)

        # Test low threat scenario
        low_threat_method = defense._select_optimal_method(0.1)
        assert low_threat_method in defense.defense_effectiveness

        # Test high threat scenario
        high_threat_method = defense._select_optimal_method(0.9)
        assert high_threat_method in defense.defense_effectiveness

    @pytest.mark.asyncio
    async def test_adaptive_aggregation(self, defense_config, sample_gradients):
        """Test adaptive aggregation"""
        defense = AdaptiveByzantineDefense(defense_config)

        result = await defense.adaptive_aggregate(sample_gradients)

        assert isinstance(result, AggregationResult)
        assert result.aggregation_method.startswith("adaptive_")
        assert len(result.aggregated_gradients) > 0

    def test_effectiveness_update(self, defense_config):
        """Test defense effectiveness update"""
        defense = AdaptiveByzantineDefense(defense_config)

        initial_effectiveness = defense.defense_effectiveness["krum"]

        # Mock a good result
        mock_result = AggregationResult(
            aggregated_gradients={},
            honest_participants=["node_1"],
            suspected_byzantine=[],
            confidence_score=0.9,
            aggregation_method="krum",
            detection_stats={},
        )

        defense._update_effectiveness("krum", mock_result)

        # Effectiveness should increase slightly
        new_effectiveness = defense.defense_effectiveness["krum"]
        assert new_effectiveness >= initial_effectiveness

    def test_attack_classification(self, defense_config, malicious_gradients):
        """Test attack type classification"""
        defense = AdaptiveByzantineDefense(defense_config)

        suspected_nodes = ["malicious_1", "malicious_2"]
        attack_type = defense._classify_attack_type(malicious_gradients, suspected_nodes)

        assert isinstance(attack_type, AttackType)


@pytest.mark.integration
class TestByzantineToleranceIntegration:
    """Integration tests for Byzantine tolerance system"""

    @pytest.mark.asyncio
    async def test_end_to_end_byzantine_tolerance(self, aggregator_config):
        """Test complete Byzantine tolerance workflow"""

        # Create mixed gradients (honest + malicious)
        mixed_gradients = {
            "honest_1": {"param": torch.randn(5) * 0.1},
            "honest_2": {"param": torch.randn(5) * 0.1},
            "honest_3": {"param": torch.randn(5) * 0.1},
            "malicious_1": {"param": torch.randn(5) * 5},  # Large magnitude
            "malicious_2": {"param": torch.randn(5) * -3},  # Sign flipped
        }

        # Test with different aggregation methods
        methods = ["krum", "trimmed_mean", "median"]

        for method in methods:
            aggregator_config["aggregation_method"] = method
            aggregator = ByzantineTolerantAggregator(aggregator_config)

            result = await aggregator.aggregate(mixed_gradients)

            # Should produce valid result
            assert isinstance(result, AggregationResult)
            assert len(result.aggregated_gradients) > 0

            # Should identify some nodes as honest
            assert len(result.honest_participants) > 0

            # Confidence should be reasonable
            assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_scalability_with_many_nodes(self, aggregator_config):
        """Test Byzantine tolerance with many nodes"""

        # Create gradients from 20 nodes (16 honest, 4 malicious)
        gradients = {}

        # Honest nodes
        for i in range(16):
            gradients[f"honest_{i}"] = {
                "param1": torch.randn(10) * 0.1,
                "param2": torch.randn(5) * 0.1,
            }

        # Malicious nodes
        for i in range(4):
            gradients[f"malicious_{i}"] = {
                "param1": torch.randn(10) * 2,  # Larger magnitude
                "param2": torch.randn(5) * 2,
            }

        aggregator = ByzantineTolerantAggregator(aggregator_config)

        start_time = time.time()
        result = await aggregator.aggregate(gradients)
        processing_time = time.time() - start_time

        # Should complete in reasonable time
        assert processing_time < 5.0  # 5 seconds max

        # Should identify malicious nodes
        assert len(result.suspected_byzantine) > 0
        assert len(result.honest_participants) >= 10  # Most honest nodes should be identified

        print(f"Processed 20 nodes in {processing_time:.2f} seconds")


@pytest.mark.performance
class TestByzantineTolerancePerformance:
    """Performance tests for Byzantine tolerance"""

    @pytest.mark.asyncio
    async def test_detection_performance(self, detector_config):
        """Test detection performance with large gradients"""
        detector = ByzantineDetector(detector_config)

        # Create large gradients
        large_gradients = {}
        for i in range(50):
            large_gradients[f"node_{i}"] = {
                "layer1": torch.randn(1000, 500),
                "layer2": torch.randn(100, 1000),
                "layer3": torch.randn(10, 100),
            }

        start_time = time.time()
        suspicion_scores = detector.analyze_gradients(large_gradients)
        detection_time = time.time() - start_time

        assert len(suspicion_scores) == 50
        assert detection_time < 10.0  # Should complete within 10 seconds

        print(
            f"Byzantine detection for 50 nodes with large gradients: {detection_time:.2f} seconds"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
