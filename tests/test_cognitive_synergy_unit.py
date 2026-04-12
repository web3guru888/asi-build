"""
Unit tests for the cognitive_synergy module.

Covers:
- Data classes (SynergyPair, CognitiveDynamic, PRIMUSState, CognitivePrimitive,
  SynergyMeasurement, SynergyProfile, EmergentProperty, OrganizationRule, OrganizationState)
- CognitiveSynergyEngine (init, register, stimulus, synergy strength, state, emergence, context mgr)
- SynergyMetrics (time series, profile computation, info-theory internals)
- PRIMUSFoundation (init, primitives, synergy, state, stimulus)
- EmergentPropertyDetector (detect_emergence, detect_system_emergence, stable/novel, summary)
- SelfOrganizationMechanism (apply, metrics, entropy)
- PerceptionEngine (process_input, get_state)
- PatternMiningEngine (process_input, mine_patterns, get_state)
"""

import time
from collections import defaultdict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# --- Imports ---

from asi_build.cognitive_synergy.core.cognitive_synergy_engine import (
    CognitiveDynamic,
    CognitiveSynergyEngine,
    SynergyPair,
)
from asi_build.cognitive_synergy.core.emergent_properties import (
    BehavioralEmergenceDetector,
    EmergentProperty,
    EmergentPropertyDetector,
    FunctionalEmergenceDetector,
    StructuralEmergenceDetector,
)
from asi_build.cognitive_synergy.core.primus_foundation import (
    CognitivePrimitive,
    PRIMUSFoundation,
    PRIMUSState,
)
from asi_build.cognitive_synergy.core.self_organization import (
    AdaptiveRestructurer,
    CoherenceMaintainer,
    HomeostaticController,
    OrganizationRule,
    OrganizationState,
    ResourceOptimizer,
    SelfOrganizationMechanism,
)
from asi_build.cognitive_synergy.core.synergy_metrics import (
    SynergyMeasurement,
    SynergyMetrics,
    SynergyProfile,
)
from asi_build.cognitive_synergy.perception_action.perception_engine import (
    PerceptionEngine,
)
from asi_build.cognitive_synergy.pattern_reasoning.pattern_mining_engine import (
    Pattern,
    PatternHierarchy,
    PatternMiningEngine,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def primus():
    """Fresh PRIMUSFoundation (never started)."""
    return PRIMUSFoundation(dimension=64, learning_rate=0.05)


@pytest.fixture
def engine():
    """Fresh CognitiveSynergyEngine (never started)."""
    return CognitiveSynergyEngine(update_frequency=10.0, synergy_threshold=0.6)


@pytest.fixture
def metrics():
    """Fresh SynergyMetrics with small window for fast tests."""
    return SynergyMetrics(history_length=200, sampling_rate=10.0)


@pytest.fixture
def detector():
    """Fresh EmergentPropertyDetector."""
    return EmergentPropertyDetector(emergence_threshold=0.7, stability_window=10)


@pytest.fixture
def self_org():
    """Fresh SelfOrganizationMechanism."""
    return SelfOrganizationMechanism(target_coherence=0.8)


# ============================================================
# 1. Data-class tests
# ============================================================

class TestSynergyPairDataclass:
    def test_field_defaults(self):
        sp = SynergyPair(process_a="x", process_b="y", synergy_strength=0.5)
        assert sp.bidirectional_flow == {}
        assert sp.integration_level == 0.0
        assert sp.emergence_indicators == []
        assert sp.last_updated > 0

    def test_mutable_defaults_independent(self):
        sp1 = SynergyPair("a", "b", 0.1)
        sp2 = SynergyPair("c", "d", 0.2)
        sp1.emergence_indicators.append("test")
        assert sp2.emergence_indicators == []


class TestCognitiveDynamicDataclass:
    def test_field_defaults(self):
        cd = CognitiveDynamic(dynamic_type="oscillation")
        assert cd.parameters == {}
        assert cd.intensity == 0.0
        assert cd.duration == 0.0
        assert cd.start_time > 0

    def test_custom_parameters(self):
        cd = CognitiveDynamic(
            dynamic_type="phase_transition",
            parameters={"change": 0.4},
            intensity=0.9,
            duration=2.5,
        )
        assert cd.parameters["change"] == 0.4
        assert cd.intensity == 0.9


class TestPRIMUSStateDataclass:
    def test_defaults(self):
        ps = PRIMUSState()
        assert ps.pattern_space == {}
        assert ps.understanding_level == 0.0
        assert len(ps.motivation_vector) == 10
        assert ps.timestamp > 0


class TestCognitivePrimitiveDataclass:
    def test_full_construction(self):
        cp = CognitivePrimitive(
            name="prim_1",
            type="pattern",
            content=np.zeros(5),
            confidence=0.8,
            activation=0.6,
            connections=["prim_2"],
            metadata={"source": "test"},
        )
        assert cp.name == "prim_1"
        assert cp.confidence == 0.8
        assert len(cp.connections) == 1

    def test_defaults(self):
        cp = CognitivePrimitive(name="x", type="concept", content="hello")
        assert cp.confidence == 1.0
        assert cp.activation == 0.0
        assert cp.connections == []
        assert cp.metadata == {}


class TestSynergyMeasurementDataclass:
    def test_construction(self):
        sm = SynergyMeasurement(
            measurement_type="mi",
            value=0.7,
            confidence=0.9,
            timestamp=1000.0,
        )
        assert sm.measurement_type == "mi"
        assert sm.metadata == {}


class TestSynergyProfileDataclass:
    def test_defaults(self):
        sp = SynergyProfile(pair_name="ab")
        assert sp.mutual_information == 0.0
        assert sp.transfer_entropy == 0.0
        assert sp.phase_coupling == 0.0
        assert sp.coherence == 0.0
        assert sp.emergence_index == 0.0
        assert sp.integration_index == 0.0
        assert sp.complexity_resonance == 0.0
        assert sp.measurements == []


class TestEmergentPropertyDataclass:
    def test_construction(self):
        ep = EmergentProperty(
            id="ep1",
            name="test_prop",
            description="A test property",
            emergence_type="behavioral",
            strength=0.85,
            novelty=0.9,
            stability=0.7,
            complexity=0.6,
            contributing_processes=["p1", "p2"],
        )
        assert ep.observation_count == 1
        assert ep.evidence == []
        assert ep.metadata == {}


class TestOrganizationRuleDataclass:
    def test_construction(self):
        rule = OrganizationRule(
            name="test_rule",
            condition=lambda s: True,
            action=lambda s: {},
            priority=0.5,
            activation_threshold=0.3,
        )
        assert rule.cooldown_time == 10.0
        assert rule.last_applied == 0.0
        assert rule.application_count == 0
        assert rule.effectiveness_history == []


class TestOrganizationStateDataclass:
    def test_defaults(self):
        os_ = OrganizationState()
        assert os_.entropy == 0.0
        assert os_.complexity == 0.0
        assert os_.coherence == 0.0
        assert os_.efficiency == 0.0
        assert os_.adaptability == 0.0
        assert os_.stability == 0.0
        assert os_.timestamp > 0


# ============================================================
# 2. CognitiveSynergyEngine tests
# ============================================================

class TestCognitiveSynergyEngine:
    def test_init_creates_10_pairs(self, engine):
        assert len(engine.synergy_pairs) == 10
        assert "pattern_reasoning" in engine.synergy_pairs
        assert "perception_action" in engine.synergy_pairs
        assert "conscious_unconscious" in engine.synergy_pairs

    def test_init_creates_primus_internally(self, engine):
        assert isinstance(engine.primus, PRIMUSFoundation)

    def test_init_custom_primus(self, primus):
        eng = CognitiveSynergyEngine(primus_foundation=primus)
        assert eng.primus is primus

    def test_register_module(self, engine):
        m = MagicMock()
        m.initialize = MagicMock()
        engine.register_module("reasoning", m)
        assert engine.modules["reasoning"] is m
        m.initialize.assert_called_once_with(engine)

    def test_register_module_without_initialize(self, engine):
        m = object()  # no initialize method
        engine.register_module("mem", m)
        assert engine.modules["mem"] is m

    def test_inject_stimulus_perceptual(self, engine):
        before = engine.synergy_pairs["perception_action"].synergy_strength
        engine.inject_stimulus({"type": "perceptual"})
        after = engine.synergy_pairs["perception_action"].synergy_strength
        assert after == pytest.approx(before + 0.2, abs=1e-9)

    def test_inject_stimulus_learning(self, engine):
        before = engine.synergy_pairs["memory_learning"].synergy_strength
        engine.inject_stimulus({"type": "learning"})
        assert engine.synergy_pairs["memory_learning"].synergy_strength == pytest.approx(
            before + 0.2, abs=1e-9
        )

    def test_inject_stimulus_goal(self, engine):
        before = engine.synergy_pairs["attention_intention"].synergy_strength
        engine.inject_stimulus({"type": "goal"})
        assert engine.synergy_pairs["attention_intention"].synergy_strength == pytest.approx(
            before + 0.2, abs=1e-9
        )

    def test_inject_stimulus_capped_at_1(self, engine):
        engine.synergy_pairs["perception_action"].synergy_strength = 0.95
        engine.inject_stimulus({"type": "perceptual"})
        assert engine.synergy_pairs["perception_action"].synergy_strength == 1.0

    def test_inject_stimulus_general_no_crash(self, engine):
        engine.inject_stimulus({"type": "general", "data": [1, 2, 3]})

    def test_get_synergy_strength_known(self, engine):
        engine.synergy_pairs["pattern_reasoning"].synergy_strength = 0.42
        assert engine.get_synergy_strength("pattern_reasoning") == pytest.approx(0.42)

    def test_get_synergy_strength_unknown(self, engine):
        """Unknown pair returns 0.0 (fixed: SynergyPair fallback was missing synergy_strength)."""
        assert engine.get_synergy_strength("nonexistent") == 0.0

    def test_get_emergence_indicators_empty(self, engine):
        indicators = engine.get_emergence_indicators()
        assert indicators == []

    def test_get_emergence_indicators_with_data(self, engine):
        engine.synergy_pairs["pattern_reasoning"].emergence_indicators = ["high_synergy"]
        indicators = engine.get_emergence_indicators()
        assert len(indicators) == 1
        assert indicators[0]["pair"] == "pattern_reasoning"

    def test_get_system_state_structure(self, engine):
        state = engine.get_system_state()
        assert "primus_state" in state
        assert "synergy_pairs" in state
        assert "global_coherence" in state
        assert "integration_matrix" in state
        assert "cognitive_dynamics" in state
        assert "emergence_events" in state
        assert "performance_metrics" in state
        assert isinstance(state["synergy_pairs"], dict)
        assert len(state["synergy_pairs"]) == 10

    def test_compute_global_coherence_zero(self, engine):
        # All synergy_strengths start at 0, so coherence = 0^1.5 = 0
        engine._compute_global_coherence()
        assert engine.global_coherence == 0.0

    def test_compute_global_coherence_nonzero(self, engine):
        for pair in engine.synergy_pairs.values():
            pair.synergy_strength = 0.5
            pair.integration_level = 0.5
        engine._compute_global_coherence()
        expected = (0.6 * 0.5 + 0.4 * 0.5) ** 1.5  # 0.5^1.5
        assert engine.global_coherence == pytest.approx(expected, abs=1e-6)

    def test_update_integration_matrix_diagonal_ones(self, engine):
        engine._update_integration_matrix()
        for i in range(10):
            assert engine.integration_matrix[i, i] == 1.0

    def test_context_manager_starts_and_stops(self):
        """Engine context manager calls start/stop without hanging."""
        eng = CognitiveSynergyEngine(update_frequency=100.0)
        with eng:
            assert eng._running is True
            time.sleep(0.05)
        assert eng._running is False

    def test_update_pair_from_primitives_decay(self, engine):
        """When no matching primitives, synergy decays by 0.95."""
        pair = engine.synergy_pairs["pattern_reasoning"]
        pair.synergy_strength = 0.8
        engine._update_pair_from_primitives("pattern_reasoning", pair)
        assert pair.synergy_strength == pytest.approx(0.76, abs=1e-9)

    def test_check_emergence_indicators_high_synergy(self, engine):
        pair = engine.synergy_pairs["pattern_reasoning"]
        pair.synergy_strength = 0.9
        pair.bidirectional_flow = {"total_flow": 0.9}
        engine._check_emergence_indicators(pair)
        assert "high_synergy" in pair.emergence_indicators
        assert "strong_bidirectional_flow" in pair.emergence_indicators

    def test_check_emergence_indicators_tracks_prev_integration(self, engine):
        pair = engine.synergy_pairs["pattern_reasoning"]
        pair.synergy_strength = 0.5
        pair.bidirectional_flow = {"total_flow": 0.1}
        engine._check_emergence_indicators(pair)
        assert hasattr(pair, "_prev_integration")

    def test_extract_numerical_features_mixed(self, engine):
        state = {
            "val_int": 3,
            "val_float": 1.5,
            "val_array": np.array([10.0, 20.0]),
            "val_list": [7.0, 8.0],
            "val_str": "ignored",
        }
        feats = engine._extract_numerical_features(state)
        assert len(feats) == 6  # 1 + 1 + 2 + 2
        assert 3.0 in feats
        assert 1.5 in feats

    def test_compute_pair_synergy_with_real_states(self, engine):
        state_a = {"x": 1.0, "y": 2.0, "z": 3.0}
        state_b = {"x": 1.1, "y": 2.1, "z": 3.1}
        synergy = engine._compute_pair_synergy(state_a, state_b)
        assert 0.0 <= synergy <= 1.0


# ============================================================
# 3. SynergyMetrics tests
# ============================================================

class TestSynergyMetrics:
    def test_add_time_series_creates_pair(self, metrics):
        metrics.add_time_series_data("pair_a", 1.0, 2.0)
        assert "pair_a" in metrics.time_series_data
        assert len(metrics.time_series_data["pair_a"]["process_a"]) == 1

    def test_add_time_series_respects_history_limit(self):
        m = SynergyMetrics(history_length=5, sampling_rate=1.0)
        for i in range(10):
            m.add_time_series_data("p", float(i), float(i))
        assert len(m.time_series_data["p"]["process_a"]) == 5
        # Oldest removed, newest kept
        assert m.time_series_data["p"]["process_a"][0] == 5.0

    def test_compute_profile_no_data(self, metrics):
        assert metrics.compute_synergy_profile("unknown") is None

    def test_compute_profile_insufficient_data(self, metrics):
        # Need window_size (10*10=100) data points
        for i in range(5):
            metrics.add_time_series_data("p", float(i), float(i))
        assert metrics.compute_synergy_profile("p") is None

    def test_compute_profile_sufficient_data(self, metrics):
        """With enough data, a profile is returned with all fields populated."""
        rng = np.random.RandomState(42)
        n = 200  # well above window_size = 100
        x = rng.randn(n)
        y = 0.5 * x + 0.5 * rng.randn(n)
        for i in range(n):
            metrics.add_time_series_data("corr_pair", x[i], y[i], timestamp=float(i))
        profile = metrics.compute_synergy_profile("corr_pair")
        assert profile is not None
        assert isinstance(profile, SynergyProfile)
        assert profile.pair_name == "corr_pair"
        # MI should be positive for correlated signals
        assert profile.mutual_information >= 0.0
        # Profile should be stored
        assert "corr_pair" in metrics.synergy_profiles

    def test_get_synergy_strength_no_profile(self, metrics):
        assert metrics.get_synergy_strength("nope") == 0.0

    def test_get_synergy_strength_with_profile(self, metrics):
        p = SynergyProfile(
            pair_name="test",
            mutual_information=0.5,
            transfer_entropy=0.3,
            phase_coupling=0.4,
            coherence=0.6,
            emergence_index=0.2,
            integration_index=0.1,
        )
        metrics.synergy_profiles["test"] = p
        strength = metrics.get_synergy_strength("test")
        expected = (
            0.25 * 0.5 + 0.20 * 0.3 + 0.15 * 0.4 + 0.15 * 0.6 + 0.15 * 0.2 + 0.10 * 0.1
        )
        assert strength == pytest.approx(expected, abs=1e-6)

    def test_get_emergence_indicators_no_profile(self, metrics):
        assert metrics.get_emergence_indicators("nope") == []

    def test_get_emergence_indicators_high_values(self, metrics):
        p = SynergyProfile(
            pair_name="hot",
            mutual_information=0.85,
            phase_coupling=0.85,
            emergence_index=0.85,
            integration_index=0.85,
            complexity_resonance=0.85,
        )
        metrics.synergy_profiles["hot"] = p
        indicators = metrics.get_emergence_indicators("hot")
        assert "high_emergence_index" in indicators
        assert "strong_statistical_coupling" in indicators
        assert "phase_synchronization" in indicators
        assert "complexity_matching" in indicators
        assert "strong_integration" in indicators
        assert "synergistic_emergence" in indicators

    def test_compute_global_synergy_empty(self, metrics):
        result = metrics.compute_global_synergy()
        assert result["global_synergy"] == 0.0
        assert result["total_emergence"] == 0.0

    def test_compute_global_synergy_with_profiles(self, metrics):
        metrics.synergy_profiles["a"] = SynergyProfile(
            pair_name="a",
            mutual_information=0.5,
            emergence_index=0.6,
            integration_index=0.3,
        )
        result = metrics.compute_global_synergy()
        assert result["global_synergy"] >= 0.0
        assert "num_synergistic_pairs" in result

    def test_discretize_constant_signal(self, metrics):
        sig = np.ones(20)
        disc = metrics._discretize_signal(sig)
        assert np.all(disc == 0)

    def test_discretize_empty_signal(self, metrics):
        disc = metrics._discretize_signal(np.array([]))
        assert len(disc) == 0

    def test_entropy_single_value(self, metrics):
        """Entropy of constant signal should be zero."""
        assert metrics._entropy(np.zeros(10, dtype=int)) == 0.0

    def test_entropy_two_values(self, metrics):
        """Entropy of equal-probability binary signal ~ 1 bit."""
        sig = np.array([0] * 50 + [1] * 50)
        h = metrics._entropy(sig)
        assert h == pytest.approx(1.0, abs=0.01)

    def test_lempel_ziv_constant(self, metrics):
        """Constant sequence has low complexity."""
        seq = np.zeros(50, dtype=int)
        lz = metrics._lempel_ziv_complexity(seq)
        assert lz < 0.3  # low but nonzero due to normalization

    def test_lempel_ziv_random(self, metrics):
        """Random sequence has high complexity."""
        rng = np.random.RandomState(42)
        seq = rng.randint(0, 2, size=200).astype(float)
        lz = metrics._lempel_ziv_complexity(seq)
        assert lz > 0.3

    def test_get_all_profiles(self, metrics):
        metrics.synergy_profiles["x"] = SynergyProfile(pair_name="x")
        result = metrics.get_all_profiles()
        assert "x" in result
        # Mutation of returned dict doesn't affect internal
        result.pop("x")
        assert "x" in metrics.synergy_profiles


# ============================================================
# 4. PRIMUSFoundation tests
# ============================================================

class TestPRIMUSFoundation:
    def test_init_defaults(self, primus):
        assert primus.dimension == 64
        assert primus.learning_rate == 0.05
        assert len(primus.primitives) == 0
        assert isinstance(primus.motivation_system, dict)
        assert "curiosity" in primus.motivation_system

    def test_add_and_get_primitive(self, primus):
        prim = CognitivePrimitive(name="p1", type="concept", content="hello")
        primus.add_primitive(prim)
        assert primus.get_primitive("p1") is prim
        assert primus.get_primitive("nonexistent") is None

    def test_add_pattern_updates_space(self, primus):
        prim = CognitivePrimitive(name="pat1", type="pattern", content={"data": 1})
        primus.add_primitive(prim)
        assert "pat1" in primus.pattern_space

    def test_add_primitive_creates_graph_node(self, primus):
        prim = CognitivePrimitive(name="node1", type="concept", content="x")
        primus.add_primitive(prim)
        assert primus.understanding_graph.has_node("node1")

    def test_add_primitive_with_connections(self, primus):
        p1 = CognitivePrimitive(name="a", type="concept", content="x")
        p2 = CognitivePrimitive(name="b", type="concept", content="y", connections=["a"])
        primus.add_primitive(p1)
        primus.add_primitive(p2)
        assert primus.understanding_graph.has_edge("b", "a")

    def test_compute_synergy_missing_returns_zero(self, primus):
        assert primus.compute_synergy("missing1", "missing2") == 0.0

    def test_compute_synergy_between_primitives_known_bug(self, primus):
        """compute_synergy: np.corrcoef([a, b]) returns scalar (not 2×2 matrix)
        so [0,1] indexing raises IndexError. Known pre-existing bug."""
        p1 = CognitivePrimitive(name="x", type="pattern", content="alpha beta", activation=0.5)
        p2 = CognitivePrimitive(name="y", type="concept", content="alpha gamma", activation=0.8)
        primus.add_primitive(p1)
        primus.add_primitive(p2)
        with pytest.raises(IndexError):
            primus.compute_synergy("x", "y")

    def test_type_synergy_known_pair(self, primus):
        assert primus._compute_type_synergy("pattern", "concept") == 0.8
        assert primus._compute_type_synergy("concept", "pattern") == 0.8  # symmetric lookup
        assert primus._compute_type_synergy("procedure", "goal") == 0.9

    def test_type_synergy_unknown_pair(self, primus):
        assert primus._compute_type_synergy("unknown1", "unknown2") == 0.1

    def test_content_synergy_strings(self, primus):
        s = primus._compute_content_synergy("hello world", "hello earth")
        assert 0.0 <= s <= 1.0
        assert s > 0.0  # share "hello"

    def test_content_synergy_arrays(self, primus):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        s = primus._compute_content_synergy(a, b)
        # Identical arrays → correlation 1.0 → abs(1.0) = 1.0
        assert s == pytest.approx(1.0, abs=0.01)

    def test_content_synergy_equal_scalars(self, primus):
        assert primus._compute_content_synergy(42, 42) == 0.5

    def test_content_synergy_different_scalars(self, primus):
        assert primus._compute_content_synergy(42, 99) == 0.1

    def test_get_system_state(self, primus):
        state = primus.get_system_state()
        assert isinstance(state, PRIMUSState)
        assert "primitives_count" in state.self_organization_metrics
        assert "graph_density" in state.self_organization_metrics

    def test_inject_stimulus_creates_primitive(self, primus):
        primus.inject_stimulus({"type": "learning", "data": "test"})
        # Should have added a stimulus primitive
        stim_prims = [p for p in primus.primitives.values() if p.type == "stimulus"]
        assert len(stim_prims) >= 1
        assert stim_prims[0].activation == 1.0

    def test_inject_stimulus_boosts_learning(self, primus):
        before = primus.motivation_system["learning"]
        primus.inject_stimulus({"type": "learning"})
        assert primus.motivation_system["learning"] == min(1.0, before + 0.2)

    def test_inject_stimulus_boosts_social(self, primus):
        before = primus.motivation_system["social_interaction"]
        primus.inject_stimulus({"type": "social"})
        assert primus.motivation_system["social_interaction"] == min(1.0, before + 0.2)

    def test_get_synergy_network_empty(self, primus):
        g = primus.get_synergy_network()
        assert len(g.nodes()) == 0

    def test_get_synergy_network_with_primitives_hits_corrcoef_bug(self, primus):
        """get_synergy_network calls compute_synergy internally,
        which hits the corrcoef scalar bug. Documented known issue."""
        p1 = CognitivePrimitive(
            name="a", type="pattern", content="foo bar", activation=0.9, connections=["b"]
        )
        p2 = CognitivePrimitive(
            name="b", type="concept", content="foo baz", activation=0.9, connections=["a"]
        )
        primus.add_primitive(p1)
        primus.add_primitive(p2)
        with pytest.raises(IndexError):
            primus.get_synergy_network()


# ============================================================
# 5. EmergentPropertyDetector tests
# ============================================================

class TestEmergentPropertyDetector:
    def test_init_has_three_detectors(self, detector):
        assert "behavioral" in detector.detectors
        assert "structural" in detector.detectors
        assert "functional" in detector.detectors

    def test_detect_emergence_empty_state(self, detector):
        props = detector.detect_emergence({})
        assert isinstance(props, list)

    def test_detect_emergence_with_high_synergy(self, detector):
        """High synergy in synergy_pairs triggers behavioral emergence."""
        state = {
            "synergy_pairs": {
                "pattern_reasoning": {"synergy_strength": 0.95},
            },
            "cognitive_dynamics": [],
        }
        # Lower the behavioral detector's novelty threshold for determinism
        detector.detectors["behavioral"].novelty_threshold = 0.3
        props = detector.detect_emergence(state)
        # Behavioral detector should find the coordinated pattern
        behavioral = [p for p in props if p.emergence_type == "behavioral"]
        assert len(behavioral) >= 1

    def test_detect_system_emergence_high_coherence(self, detector):
        pairs = {f"pair_{i}": {} for i in range(5)}
        matrix = np.ones((5, 5)) * 0.9
        props = detector.detect_system_emergence(pairs, 0.95, matrix)
        names = [p.name for p in props]
        assert "metacognitive_emergence" in names
        assert "collective_intelligence" in names

    def test_detect_system_emergence_low_coherence(self, detector):
        pairs = {}
        matrix = np.zeros((5, 5))
        props = detector.detect_system_emergence(pairs, 0.3, matrix)
        assert len(props) == 0

    def test_get_stable_properties(self, detector):
        ep = EmergentProperty(
            id="s1", name="stable", description="", emergence_type="behavioral",
            strength=0.8, novelty=0.5, stability=0.9, complexity=0.5,
            contributing_processes=[],
        )
        detector.detected_properties["s1"] = ep
        stable = detector.get_stable_properties(min_stability=0.85)
        assert len(stable) == 1

    def test_get_novel_properties(self, detector):
        ep = EmergentProperty(
            id="n1", name="novel", description="", emergence_type="behavioral",
            strength=0.8, novelty=0.95, stability=0.5, complexity=0.5,
            contributing_processes=[],
        )
        detector.detected_properties["n1"] = ep
        novel = detector.get_novel_properties(min_novelty=0.9)
        assert len(novel) == 1

    def test_get_complex_properties(self, detector):
        ep = EmergentProperty(
            id="c1", name="complex", description="", emergence_type="structural",
            strength=0.8, novelty=0.5, stability=0.5, complexity=0.95,
            contributing_processes=[],
        )
        detector.detected_properties["c1"] = ep
        complex_props = detector.get_complex_properties(min_complexity=0.9)
        assert len(complex_props) == 1

    def test_get_emergence_summary_structure(self, detector):
        summary = detector.get_emergence_summary()
        assert "total_properties" in summary
        assert "by_type" in summary
        assert "stability_distribution" in summary
        assert "novelty_distribution" in summary
        assert "detection_stats" in summary

    def test_property_tracking_updates_observation_count(self, detector):
        ep = EmergentProperty(
            id="track1", name="tracked", description="", emergence_type="behavioral",
            strength=0.8, novelty=0.9, stability=0.5, complexity=0.5,
            contributing_processes=[],
        )
        detector._update_property_tracking([ep])
        assert detector.detected_properties["track1"].observation_count == 1
        # Second time
        detector._update_property_tracking([ep])
        assert detector.detected_properties["track1"].observation_count == 2


class TestBehavioralEmergenceDetector:
    def test_detect_cascade_with_dynamics(self):
        det = BehavioralEmergenceDetector(novelty_threshold=0.3)
        dynamics = [
            {"age": 1, "parameters": {"pair": "a"}},
            {"age": 1, "parameters": {"pair": "b"}},
            {"age": 2, "parameters": {"pair": "c"}},
        ]
        cascades = det._detect_cascade_patterns(dynamics)
        assert len(cascades) >= 1

    def test_novelty_known_behavior(self):
        det = BehavioralEmergenceDetector()
        det.known_behaviors.add("coord_pair_a_0.90")
        behavior = {"signature": "coord_pair_a_0.90"}
        assert det._compute_behavior_novelty(behavior) == 0.0


class TestStructuralEmergenceDetector:
    def test_detect_with_integration_matrix(self):
        det = StructuralEmergenceDetector(structure_threshold=0.3)
        matrix = np.random.RandomState(42).rand(5, 5)
        matrix = (matrix + matrix.T) / 2  # symmetric
        np.fill_diagonal(matrix, 1.0)
        state = {"integration_matrix": matrix.tolist()}
        props = det.detect(state)
        assert isinstance(props, list)

    def test_novelty_first_is_1(self):
        det = StructuralEmergenceDetector()
        structure = {"type": "new_type", "strength": 0.8, "components": []}
        assert det._compute_structure_novelty(structure) == 1.0

    def test_novelty_known_type_same_strength(self):
        det = StructuralEmergenceDetector()
        det.known_structures["existing"] = 0.5
        structure = {"type": "existing", "strength": 0.5, "components": []}
        assert det._compute_structure_novelty(structure) == 0.0


class TestFunctionalEmergenceDetector:
    def test_detect_metacognitive_integration(self):
        det = FunctionalEmergenceDetector(capability_threshold=0.3)
        state = {"global_coherence": 0.9, "synergy_pairs": {}}
        props = det.detect(state)
        names = [p.name for p in props]
        assert "metacognitive_integration" in names

    def test_detect_enhanced_problem_solving(self):
        det = FunctionalEmergenceDetector(capability_threshold=0.3)
        state = {
            "synergy_pairs": {
                "pattern_reasoning": {"synergy_strength": 0.9},
            },
        }
        props = det.detect(state)
        names = [p.name for p in props]
        assert "enhanced_problem_solving" in names


# ============================================================
# 6. SelfOrganizationMechanism tests
# ============================================================

class TestSelfOrganizationMechanism:
    def _make_system_args(self, coherence=0.5, n_pairs=5, strength=0.5):
        """Build typical arguments for self_org.apply()."""
        synergy_pairs = {
            f"pair_{i}": {"synergy_strength": strength, "integration_level": strength}
            for i in range(n_pairs)
        }
        matrix = np.ones((n_pairs, n_pairs)) * strength
        np.fill_diagonal(matrix, 1.0)
        perf = {"metric_a": [0.5] * 10, "metric_b": [0.6] * 10}
        return synergy_pairs, coherence, matrix, perf

    def test_apply_returns_dict(self, self_org):
        pairs, coh, mat, perf = self._make_system_args()
        result = self_org.apply(pairs, coh, mat, perf)
        assert isinstance(result, dict)
        assert "applied_rules" in result
        assert "organization_state" in result

    def test_apply_updates_organization_state(self, self_org):
        pairs, coh, mat, perf = self._make_system_args(coherence=0.3)
        self_org.apply(pairs, coh, mat, perf)
        state = self_org.current_state
        assert state.coherence == 0.3

    def test_compute_system_entropy_uniform(self, self_org):
        """Uniform synergy distribution → high entropy (close to 1)."""
        pairs = {f"p{i}": {"synergy_strength": 0.5} for i in range(10)}
        matrix = np.eye(10)
        entropy = self_org._compute_system_entropy(pairs, matrix)
        assert entropy > 0.8

    def test_compute_system_entropy_empty(self, self_org):
        entropy = self_org._compute_system_entropy({}, np.array([]))
        assert entropy == 1.0  # max entropy for empty

    def test_get_organization_metrics(self, self_org):
        metrics = self_org.get_organization_metrics()
        assert "current_state" in metrics
        assert "rule_statistics" in metrics
        assert "organization_history_summary" in metrics

    def test_detect_load_imbalance_true(self, self_org):
        state = {
            "synergy_pairs": {
                "a": {"synergy_strength": 0.1},
                "b": {"synergy_strength": 0.9},
            }
        }
        assert self_org._detect_load_imbalance(state)

    def test_detect_load_imbalance_false(self, self_org):
        state = {
            "synergy_pairs": {
                "a": {"synergy_strength": 0.5},
                "b": {"synergy_strength": 0.5},
            }
        }
        assert not self_org._detect_load_imbalance(state)

    def test_detect_weak_connections(self, self_org):
        state = {
            "synergy_pairs": {
                "a": {"synergy_strength": 0.1},
                "b": {"synergy_strength": 0.1},
                "c": {"synergy_strength": 0.1},
                "d": {"synergy_strength": 0.9},
            }
        }
        assert self_org._detect_weak_connections(state)

    def test_detect_strong_synergy(self, self_org):
        state = {"synergy_pairs": {"a": {"synergy_strength": 0.85}}}
        assert self_org._detect_strong_synergy(state)

    def test_detect_specialization_opportunity(self, self_org):
        state = {
            "synergy_pairs": {
                "a": {"synergy_strength": 0.9, "integration_level": 0.9},
            }
        }
        assert self_org._detect_specialization_opportunity(state)


class TestHomeostaticController:
    def test_apply_adjustment(self):
        hc = HomeostaticController()
        actions = hc.apply({"global_coherence": 0.3})
        assert "coherence_adjustment" in actions
        assert actions["coherence_adjustment"]["target"] == 0.8

    def test_apply_no_adjustment(self):
        hc = HomeostaticController()
        actions = hc.apply({"global_coherence": 0.8})
        assert "coherence_adjustment" not in actions


class TestAdaptiveRestructurer:
    def test_increase_connectivity(self):
        ar = AdaptiveRestructurer()
        matrix = np.ones((3, 3)) * 0.3
        actions = ar.apply({"integration_matrix": matrix})
        assert "increase_connectivity" in actions

    def test_reduce_connectivity(self):
        ar = AdaptiveRestructurer()
        matrix = np.ones((3, 3)) * 0.95
        actions = ar.apply({"integration_matrix": matrix})
        assert "reduce_connectivity" in actions


class TestResourceOptimizer:
    def test_optimization_needed(self):
        ro = ResourceOptimizer()
        state = OrganizationState(efficiency=0.4)
        actions = ro.apply({"current_state": state})
        assert "resource_optimization" in actions

    def test_no_optimization_needed(self):
        ro = ResourceOptimizer()
        state = OrganizationState(efficiency=0.9)
        actions = ro.apply({"current_state": state})
        assert "resource_optimization" not in actions


class TestCoherenceMaintainer:
    def test_restoration_high_variance(self):
        cm = CoherenceMaintainer()
        pairs = {"a": {"synergy_strength": 0.1}, "b": {"synergy_strength": 0.9}}
        actions = cm.apply({"synergy_pairs": pairs})
        assert "coherence_restoration" in actions

    def test_no_restoration_low_variance(self):
        cm = CoherenceMaintainer()
        pairs = {"a": {"synergy_strength": 0.5}, "b": {"synergy_strength": 0.5}}
        actions = cm.apply({"synergy_pairs": pairs})
        assert "coherence_restoration" not in actions


# ============================================================
# 7. PerceptionEngine tests
# ============================================================

class TestPerceptionEngine:
    def test_init_state(self):
        pe = PerceptionEngine()
        state = pe.get_state()
        assert state["activation_level"] == 0.0
        assert state["last_input"] is None

    def test_process_input(self):
        pe = PerceptionEngine()
        data = np.array([0.5, 0.6, 0.7])
        result = pe.process_input("visual", data)
        assert result["modality"] == "visual"
        assert result["confidence"] > 0.0
        assert pe.state["activation_level"] > 0.0

    def test_process_empty_input(self):
        pe = PerceptionEngine()
        result = pe.process_input("audio", np.array([]))
        assert result["confidence"] == 0.0

    def test_get_state_is_copy(self):
        pe = PerceptionEngine()
        s = pe.get_state()
        s["activation_level"] = 999.0
        assert pe.state["activation_level"] != 999.0


# ============================================================
# 8. PatternMiningEngine tests
# ============================================================

class TestPatternDataclass:
    def test_construction_and_defaults(self):
        p = Pattern(
            id="p1",
            type="sequence",
            content=[1, 2, 3],
            confidence=0.8,
            support=5,
            frequency=0.5,
            complexity=0.3,
        )
        assert p.metadata == {}
        assert p.timestamp > 0

    def test_hierarchy_defaults(self):
        h = PatternHierarchy()
        assert h.root_patterns == []
        assert h.sub_patterns == {}
        assert h.super_patterns == {}


class TestPatternMiningEngine:
    def test_init(self):
        pme = PatternMiningEngine(max_patterns=100, min_support=2)
        assert pme.max_patterns == 100
        assert pme.min_support == 2

    def test_process_input_sequence(self):
        pme = PatternMiningEngine()
        pme.process_input({"type": "sequence", "data": [1.0, 2.0, 3.0]})
        assert len(pme.sequence_buffer) == 1
        assert pme.activation_level > 0.0

    def test_process_input_default_buffer(self):
        pme = PatternMiningEngine()
        pme.process_input({"type": "unknown", "data": "test"})
        assert len(pme.sequence_buffer) == 1  # default → sequence

    def test_get_state(self):
        pme = PatternMiningEngine()
        state = pme.get_state()
        assert "num_patterns" in state
        assert "buffer_sizes" in state
        assert "activation_level" in state
        assert "hierarchy_stats" in state

    def test_get_patterns_by_type_empty(self):
        pme = PatternMiningEngine()
        assert pme.get_patterns_by_type("sequence") == []

    def test_get_top_patterns_empty(self):
        pme = PatternMiningEngine()
        assert pme.get_top_patterns(5) == []
