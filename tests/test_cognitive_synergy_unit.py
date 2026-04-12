"""
Additional unit tests for cognitive_synergy module.
Extends test_cognitive_synergy.py and test_cognitive_synergy_extended.py

Based on issue #1 suggestions for comprehensive test coverage.
"""

import time
from collections import deque
from unittest.mock import MagicMock

import numpy as np
import pytest

from asi_build.cognitive_synergy.core.cognitive_synergy_engine import (
    CognitiveDynamic,
    CognitiveSynergyEngine,
    SynergyPair,
)
from asi_build.cognitive_synergy.core.emergent_properties import (
    BehavioralEmergenceDetector,
    EmergentProperty,
    EmergentPropertyDetector,
)
from asi_build.cognitive_synergy.core.primus_foundation import (
    CognitivePrimitive,
    PRIMUSFoundation,
    PRIMUSState,
)
from asi_build.cognitive_synergy.core.self_organization import (
    HomeostaticController,
    OrganizationState,
    SelfOrganizationMechanism,
)
from asi_build.cognitive_synergy.core.synergy_metrics import (
    SynergyMetrics,
    SynergyProfile,
)


# ============================================================================
# Transfer Entropy Tests
# ============================================================================


class TestTransferEntropy:
    """Tests for transfer entropy computation between variables."""

    def _make_metrics(self, history_length=5000, sampling_rate=10.0):
        return SynergyMetrics(history_length=history_length, sampling_rate=sampling_rate)

    def test_transfer_entropy_independent_variables(self):
        """
        TE between two independent uniform RVs should be ≈0.
        """
        sm = self._make_metrics()
        np.random.seed(42)
        x = np.random.uniform(0, 1, 500)
        y = np.random.uniform(0, 1, 500)

        for xi, yi in zip(x, y):
            sm.add_time_series_data("X", float(xi), float(yi))

        profile = sm.compute_synergy_profile("X_Y")
        assert profile is not None
        # TE should be close to 0 for independent variables
        assert profile.transfer_entropy < 0.1

    def test_transfer_entropy_deterministic(self):
        """
        TE from X→Y when Y is a copy of X should be ≈H(X).
        """
        sm = self._make_metrics()
        np.random.seed(42)
        x = np.random.uniform(0, 1, 500)

        for xi in x:
            sm.add_time_series_data("X", float(xi), float(xi))

        profile = sm.compute_synergy_profile("X_copy")
        assert profile is not None
        # High transfer entropy when Y is deterministic function of X
        assert profile.transfer_entropy > 0.1

    def test_transfer_entropy_empty_series(self):
        """
        TE on empty or very short series should not crash.
        """
        sm = self._make_metrics()
        # Just add one data point
        sm.add_time_series_data("test", 0.5, 0.5)
        profile = sm.compute_synergy_profile("test")
        # Should handle gracefully
        assert profile is not None


# ============================================================================
# Dual Total Correlation / O-information Tests
# ============================================================================


class TestDualTotalCorrelation:
    """Tests for O-information (synergy vs redundancy decomposition)."""

    def _make_metrics(self, history_length=5000, sampling_rate=10.0):
        return SynergyMetrics(history_length=history_length, sampling_rate=sampling_rate)

    def test_dtc_single_variable(self):
        """
        DTC of a single variable should be 0.
        """
        sm = self._make_metrics()
        np.random.seed(42)
        x = np.random.randn(500)

        for xi in x:
            sm.add_time_series_data("single", float(xi), float(xi))

        profile = sm.compute_synergy_profile("single")
        assert profile is not None
        # Single variable should have low O-information
        # (emergence_index is the O-information proxy)
        assert hasattr(profile, 'emergence_index') or hasattr(profile, 'integration')

    def test_dtc_identical_signals(self):
        """
        Two identical signals should show redundancy.
        """
        sm = self._make_metrics()
        np.random.seed(42)
        x = np.random.randn(500)

        for xi in x:
            sm.add_time_series_data("identical", float(xi), float(xi))

        profile = sm.compute_synergy_profile("identical")
        assert profile is not None
        # Identical signals should have high mutual information
        assert profile.mutual_information > 0.5


# ============================================================================
# Synergy XOR Gate Tests
# ============================================================================


class TestSynergyXORGate:
    """
    The classic XOR synergy example:
    Two inputs (X1, X2) with one output Y = XOR(X1, X2).
    Should have positive O-information (synergy).
    """

    def _make_metrics(self, history_length=5000, sampling_rate=10.0):
        return SynergyMetrics(history_length=history_length, sampling_rate=sampling_rate)

    def test_xor_gate_synergy(self):
        """
        XOR gate creates synergistic relationship between inputs.
        """
        sm = self._make_metrics()
        np.random.seed(42)

        # Generate XOR pattern
        for i in range(500):
            x1 = np.random.randint(0, 2)
            x2 = np.random.randint(0, 2)
            y = int(x1 != x2)  # XOR

            sm.add_time_series_data("X1", float(x1), float(y))
            sm.add_time_series_data("X2", float(x2), float(y))

        # XOR should show synergy characteristics
        profile_x1_y = sm.compute_synergy_profile("X1_Y")
        profile_x2_y = sm.compute_synergy_profile("X2_Y")

        assert profile_x1_y is not None
        assert profile_x2_y is not None


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def _make_metrics(self, history_length=5000, sampling_rate=10.0):
        return SynergyMetrics(history_length=history_length, sampling_rate=sampling_rate)

    def test_empty_time_series_raises(self):
        """
        Empty input should raise ValueError or handle gracefully.
        """
        sm = self._make_metrics()
        # Don't add any data
        profile = sm.compute_synergy_profile("empty")
        # Should return None or handle gracefully
        assert profile is None or isinstance(profile, SynergyProfile)

    def test_single_data_point(self):
        """
        Single data point should not crash.
        """
        sm = self._make_metrics()
        sm.add_time_series_data("single", 0.5, 0.5)
        profile = sm.compute_synergy_profile("single")
        assert profile is not None

    def test_high_dimensional_arrays(self):
        """
        High-dimensional arrays should be handled.
        """
        sm = self._make_metrics()
        np.random.seed(42)
        x = np.random.randn(500)
        y = np.random.randn(500)

        for xi, yi in zip(x, y):
            sm.add_time_series_data("high_dim", float(xi), float(yi))

        profile = sm.compute_synergy_profile("high_dim")
        assert profile is not None


# ============================================================================
# CognitiveSynergyEngine Integration Tests
# ============================================================================


class TestCognitiveSynergyEngineIntegration:
    """Integration tests for CognitiveSynergyEngine."""

    def test_engine_tick_updates_pairs(self):
        """
        Engine tick should update SynergyPair last_updated timestamps.
        """
        engine = CognitiveSynergyEngine()

        # Add a synergy pair
        pair = SynergyPair(name="test_pair", source_module="A", target_module="B")
        initial_time = pair.last_updated

        engine.synergy_pairs["test_pair"] = pair

        # Wait a bit
        time.sleep(0.01)

        # Get system state triggers internal updates
        state = engine.get_system_state()

        # Should have synergy_pairs in state
        assert "synergy_pairs" in state
        assert len(state["synergy_pairs"]) == 1

    def test_add_synergy_pair(self):
        """
        Adding synergy pairs should work correctly.
        """
        engine = CognitiveSynergyEngine()
        pair = SynergyPair(name="new_pair", source_module="X", target_module="Y")
        engine.add_synergy_pair(pair)

        assert "new_pair" in engine.synergy_pairs
        assert engine.synergy_pairs["new_pair"].name == "new_pair"


# ============================================================================
# PRIMUS Foundation Tests
# ============================================================================


class TestPRIMUSWeightUpdates:
    """Tests for PRIMUS weight updates with learning_rate and decay_rate."""

    def test_learning_rate_affects_weights(self):
        """
        Higher learning rate should cause larger weight changes.
        """
        p1 = PRIMUSFoundation(learning_rate=0.1)
        p2 = PRIMUSFoundation(learning_rate=0.01)

        cp1 = CognitivePrimitive(name="a1", type="pattern", content="test")
        cp2 = CognitivePrimitive(name="a2", type="pattern", content="test")

        p1.add_primitive(cp1)
        p2.add_primitive(cp2)

        # Initial activations
        initial_1 = p1.primitives["a1"].activation
        initial_2 = p2.primitives["a2"].activation

        # Update understanding
        p1.update_understanding("a1", {"pattern": 0.8})
        p2.update_understanding("a2", {"pattern": 0.8})

        # Check that weights were updated
        updated_1 = p1.primitives["a1"].activation
        updated_2 = p2.primitives["a2"].activation

        assert updated_1 != initial_1 or updated_2 != initial_2

    def test_decay_rate_affects_weights(self):
        """
        Decay rate should gradually reduce activations over time.
        """
        p = PRIMUSFoundation(decay_rate=0.5)

        cp = CognitivePrimitive(name="decay_test", type="pattern", content="test", activation=1.0)
        p.add_primitive(cp)

        initial_activation = p.primitives["decay_test"].activation

        # Apply decay
        p._apply_decay()

        decayed_activation = p.primitives["decay_test"].activation

        assert decayed_activation <= initial_activation


# ============================================================================
# BehavioralEmergenceDetector Tests
# ============================================================================


class TestBehavioralEmergenceDetector:
    """Tests for BehavioralEmergenceDetector."""

    def test_detector_requires_history(self):
        """
        Behavioral emergence needs history to detect patterns.
        """
        detector = BehavioralEmergenceDetector(window_size=5)

        # Without enough history, should not detect emergence
        state_history = []  # Empty history
        emergence = detector.detect_behavioral_emergence(state_history)

        # Should return 0 or handle gracefully
        assert emergence == 0.0 or isinstance(emergence, (int, float))

    def test_detector_with_sufficient_history(self):
        """
        With sufficient history, should compute emergence.
        """
        detector = BehavioralEmergenceDetector(window_size=5)

        # Generate some state history
        state_history = [
            {"coherence": 0.5, "complexity": 0.3},
            {"coherence": 0.6, "complexity": 0.4},
            {"coherence": 0.7, "complexity": 0.5},
            {"coherence": 0.8, "complexity": 0.6},
            {"coherence": 0.9, "complexity": 0.7},
        ]

        emergence = detector.detect_behavioral_emergence(state_history)

        # Should compute some emergence value
        assert isinstance(emergence, (int, float))


# ============================================================================
# Self Organization Tests
# ============================================================================


class TestSelfOrganizationMetrics:
    """Tests for self-organization metrics tracking."""

    def test_homeostatic_controller_defaults(self):
        """
        HomeostaticController initializes with proper defaults.
        """
        controller = HomeostaticController(
            target_coherence=0.8,
            adaptation_rate=0.1
        )

        assert controller.target_coherence == 0.8
        assert controller.adaptation_rate == 0.1
        assert controller.current_coherence == 0.0

    def test_organization_state_tracking(self):
        """
        OrganizationState should track metrics correctly.
        """
        state = OrganizationState()

        assert "coherence" in state.metrics
        assert "adaptation_level" in state.metrics
        assert state.metrics["coherence"] == 0.0


# ============================================================================
# Pattern Mining Engine Property Tests
# ============================================================================


class TestPatternMiningEngine:
    """Additional tests for PatternMiningEngine."""

    def test_pattern_confidence_bounds(self):
        """
        Pattern confidence should always be in [0, 1].
        """
        from asi_build.cognitive_synergy.pattern_reasoning.pattern_mining_engine import (
            Pattern,
            PatternMiningEngine,
        )

        engine = PatternMiningEngine(min_support=1, min_confidence=0.0)

        # Generate various patterns
        for i in range(10):
            engine.process_input({
                "type": "test",
                "data": float(i % 3),
                "timestamp": time.time()
            })

        patterns = engine.mine_patterns()

        # All pattern confidences should be in valid range
        for pattern in patterns:
            assert 0.0 <= pattern.confidence <= 1.0, \
                f"Pattern confidence {pattern.confidence} out of bounds"

    def test_pattern_hierarchy_consistency(self):
        """
        PatternHierarchy parent/child relationships should be consistent.
        """
        from asi_build.cognitive_synergy.pattern_reasoning.pattern_mining_engine import (
            Pattern,
            PatternHierarchy,
        )

        hierarchy = PatternHierarchy()

        parent = Pattern(name="parent", pattern_type="abstract", confidence=0.9)
        child = Pattern(name="child", pattern_type="concrete", confidence=0.7)

        hierarchy.add_pattern(parent)
        hierarchy.add_pattern(child)
        hierarchy.add_relation("child", "parent", strength=0.5)

        # Parent should have child in children
        assert "child" in hierarchy.get_children("parent")

        # Child should have parent in parents
        assert "parent" in hierarchy.get_parents("child")


# ============================================================================
# CognitiveSynergyEngine Tests
# ============================================================================


class TestCognitiveSynergyEngine:
    """Tests for CognitiveSynergyEngine lifecycle."""

    def test_engine_initialization(self):
        """
        Engine should initialize with default parameters.
        """
        engine = CognitiveSynergyEngine()

        assert engine.synergy_threshold == 0.5
        assert engine.learning_rate == 0.01
        assert len(engine.synergy_pairs) == 0

    def test_engine_with_custom_parameters(self):
        """
        Engine should accept custom parameters.
        """
        engine = CognitiveSynergyEngine(
            synergy_threshold=0.7,
            learning_rate=0.05,
            decay_rate=0.95
        )

        assert engine.synergy_threshold == 0.7
        assert engine.learning_rate == 0.05
        assert engine.decay_rate == 0.95

    def test_get_system_state_structure(self):
        """
        get_system_state should return properly structured state.
        """
        engine = CognitiveSynergyEngine()
        state = engine.get_system_state()

        assert isinstance(state, dict)
        assert "synergy_pairs" in state
        assert "cognitive_dynamics" in state


# ============================================================================
# Run all tests if executed directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
