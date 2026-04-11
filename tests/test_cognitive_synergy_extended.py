"""
Extended tests for the cognitive_synergy module — ASI:BUILD.

Covers ALL submodules not tested in test_cognitive_synergy.py:
- core/cognitive_synergy_engine.py (CognitiveSynergyEngine, SynergyPair, CognitiveDynamic)
- core/emergent_properties.py (EmergentPropertyDetector, BehavioralEmergenceDetector, ...)
- core/primus_foundation.py (PRIMUSFoundation, CognitivePrimitive, PRIMUSState)
- core/self_organization.py (SelfOrganizationMechanism, HomeostaticController, ...)
- pattern_reasoning/reasoning_engine.py (ReasoningEngine, DeductiveRule, ...)
- pattern_reasoning/pattern_mining_engine.py (PatternMiningEngine, Pattern, ...)
- pattern_reasoning/pattern_reasoning_synergy.py (PatternReasoningSynergy, ...)
- perception_action/ (PerceptionEngine, ActionEngine, SensorimotorSynergy, ...)

All tests run standalone without optional deps (torch) — only numpy, scipy, networkx, sklearn.
"""

import time
import threading
from collections import defaultdict, deque
from unittest.mock import MagicMock, patch

import numpy as np
import networkx as nx
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Module imports
# ═══════════════════════════════════════════════════════════════════════════

from asi_build.cognitive_synergy.core.primus_foundation import (
    PRIMUSFoundation,
    PRIMUSState,
    CognitivePrimitive,
)
from asi_build.cognitive_synergy.core.cognitive_synergy_engine import (
    CognitiveSynergyEngine,
    SynergyPair,
    CognitiveDynamic,
)
from asi_build.cognitive_synergy.core.emergent_properties import (
    EmergentPropertyDetector,
    EmergentProperty,
    EmergenceSignature,
    BehavioralEmergenceDetector,
    StructuralEmergenceDetector,
    FunctionalEmergenceDetector,
)
from asi_build.cognitive_synergy.core.self_organization import (
    SelfOrganizationMechanism,
    HomeostaticController,
    AdaptiveRestructurer,
    ResourceOptimizer,
    CoherenceMaintainer,
    OrganizationRule,
    OrganizationState,
)
from asi_build.cognitive_synergy.pattern_reasoning.reasoning_engine import (
    ReasoningEngine,
    ReasoningType,
    Hypothesis,
    Inference,
    KnowledgeItem,
    DeductiveRule,
    InductiveRule,
    AbductiveRule,
)
from asi_build.cognitive_synergy.pattern_reasoning.pattern_mining_engine import (
    PatternMiningEngine,
    Pattern,
    PatternHierarchy,
)
from asi_build.cognitive_synergy.pattern_reasoning.pattern_reasoning_synergy import (
    PatternReasoningSynergy,
    AbstractionEngine,
    AttentionCoordinator,
    CrossValidationEngine,
    SynergyEvent,
)
from asi_build.cognitive_synergy.perception_action.perception_engine import (
    PerceptionEngine,
)
from asi_build.cognitive_synergy.perception_action.action_engine import (
    ActionEngine,
)
from asi_build.cognitive_synergy.perception_action.sensorimotor_synergy import (
    SensorimotorSynergy,
    SensorimotorLoop,
    PerceptionState,
    ActionState,
    ForwardModel,
    InverseModel,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. PRIMUS Foundation
# ═══════════════════════════════════════════════════════════════════════════

class TestPRIMUSDataclasses:
    """PRIMUSState and CognitivePrimitive dataclasses."""

    def test_primus_state_defaults(self):
        state = PRIMUSState()
        assert state.pattern_space == {}
        assert state.understanding_level == 0.0
        assert len(state.motivation_vector) == 10
        assert state.timestamp > 0

    def test_cognitive_primitive_defaults(self):
        cp = CognitivePrimitive(name="test", type="pattern", content="abc")
        assert cp.name == "test"
        assert cp.confidence == 1.0
        assert cp.activation == 0.0
        assert cp.connections == []


class TestPRIMUSFoundation:
    """PRIMUSFoundation (no background threads)."""

    def _make_primus(self, **kwargs):
        return PRIMUSFoundation(**kwargs)

    def test_constructor_defaults(self):
        p = self._make_primus()
        assert p.dimension == 512
        assert p.learning_rate == 0.01
        assert p.decay_rate == 0.99
        assert p.synergy_threshold == 0.5
        assert len(p.primitives) == 0

    def test_add_and_get_primitive(self):
        p = self._make_primus()
        cp = CognitivePrimitive(name="alpha", type="concept", content="x")
        p.add_primitive(cp)
        assert p.get_primitive("alpha") is cp
        assert p.get_primitive("nonexistent") is None
        assert p.understanding_graph.has_node("alpha")

    def test_add_primitive_pattern_updates_space(self):
        p = self._make_primus()
        cp = CognitivePrimitive(name="pat1", type="pattern", content=[1, 2])
        p.add_primitive(cp)
        assert "pat1" in p.pattern_space

    def test_add_primitive_connections(self):
        p = self._make_primus()
        p.add_primitive(CognitivePrimitive(name="a", type="concept", content="a"))
        p.add_primitive(CognitivePrimitive(name="b", type="concept", content="b", connections=["a"]))
        assert p.understanding_graph.has_edge("b", "a")

    def test_compute_synergy_missing_primitive(self):
        p = self._make_primus()
        assert p.compute_synergy("missing1", "missing2") == 0.0

    def test_compute_synergy_between_primitives(self):
        """compute_synergy hits a pre-existing bug: np.corrcoef on a 2-element
        1-D list returns a scalar, not a 2×2 matrix, so [0,1] indexing raises
        IndexError.  We document the bug and verify the other components work."""
        p = self._make_primus()
        p.add_primitive(CognitivePrimitive(
            name="p1", type="pattern", content="hello world", activation=0.8, connections=["p2"],
        ))
        p.add_primitive(CognitivePrimitive(
            name="p2", type="concept", content="hello there", activation=0.7, connections=["p1"],
        ))
        # BUG: np.corrcoef([scalar, scalar]) → scalar, not 2x2 matrix
        with pytest.raises(IndexError):
            p.compute_synergy("p1", "p2")

    def test_type_synergy_matrix(self):
        p = self._make_primus()
        # Known pair
        assert p._compute_type_synergy("pattern", "concept") == 0.8
        # Symmetric lookup
        assert p._compute_type_synergy("concept", "pattern") == 0.8
        # Unknown pair
        assert p._compute_type_synergy("unknown_a", "unknown_b") == 0.1

    def test_content_synergy_strings(self):
        p = self._make_primus()
        sim = p._compute_content_synergy("hello world", "hello there")
        assert 0.0 < sim < 1.0

    def test_content_synergy_arrays(self):
        p = self._make_primus()
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.5])
        sim = p._compute_content_synergy(a, b)
        assert sim > 0.9  # very similar

    def test_content_synergy_equal(self):
        p = self._make_primus()
        assert p._compute_content_synergy(42, 42) == 0.5

    def test_content_synergy_different(self):
        p = self._make_primus()
        assert p._compute_content_synergy(42, 99) == 0.1

    def test_get_system_state_returns_primus_state(self):
        p = self._make_primus()
        state = p.get_system_state()
        assert isinstance(state, PRIMUSState)

    def test_inject_stimulus(self):
        p = self._make_primus()
        before_count = len(p.primitives)
        p.inject_stimulus({"type": "learning", "data": [1, 2]})
        assert len(p.primitives) == before_count + 1
        # Learning motivation should have been boosted
        assert p.motivation_system["learning"] >= 0.8

    def test_inject_stimulus_social(self):
        p = self._make_primus()
        original = p.motivation_system["social_interaction"]
        p.inject_stimulus({"type": "social", "data": "hi"})
        assert p.motivation_system["social_interaction"] >= original

    def test_get_synergy_network(self):
        """get_synergy_network delegates to compute_synergy which has the
        np.corrcoef scalar bug.  Verify it raises IndexError."""
        p = self._make_primus()
        p.add_primitive(CognitivePrimitive(name="x", type="pattern", content="a", activation=0.9))
        p.add_primitive(CognitivePrimitive(name="y", type="concept", content="a", activation=0.9))
        p.synergy_threshold = 0.0
        with pytest.raises(IndexError):
            p.get_synergy_network()

    def test_get_synergy_network_empty(self):
        """With no primitives, get_synergy_network returns empty graph."""
        p = self._make_primus()
        g = p.get_synergy_network()
        assert isinstance(g, nx.Graph)
        assert g.number_of_nodes() == 0

    def test_motivation_system_init(self):
        p = self._make_primus()
        ms = p.motivation_system
        assert "curiosity" in ms
        assert "self_preservation" in ms
        assert ms["self_preservation"] == 0.9

    def test_context_manager_does_not_crash(self):
        """start/stop via context manager"""
        p = self._make_primus()
        p.start()
        time.sleep(0.05)
        p.stop()
        assert not p._running

    def test_synthesize_understanding_empty(self):
        p = self._make_primus()
        p._synthesize_understanding()
        assert p.current_state.understanding_level == 0.0

    def test_synthesize_understanding_with_patterns(self):
        p = self._make_primus()
        p.pattern_space["sp1"] = {"synergy": 0.8, "timestamp": time.time(), "components": ["a", "b"]}
        p._synthesize_understanding()
        assert p.current_state.understanding_level == pytest.approx(0.8, abs=0.01)

    def test_update_pattern_space_removes_old(self):
        p = self._make_primus()
        p.pattern_space["old"] = {"timestamp": time.time() - 400, "synergy": 0.5}
        p._update_pattern_space()
        assert "old" not in p.pattern_space

    def test_reorganize_structures_prunes(self):
        p = self._make_primus()
        cp = CognitivePrimitive(name="weak", type="concept", content="x", activation=0.001)
        p.add_primitive(cp)
        p._reorganize_structures()
        assert "weak" not in p.primitives

    def test_generate_goals(self):
        p = self._make_primus()
        before = len(p.primitives)
        p._generate_goals()
        # Should have added a goal primitive (motivation defaults > 0.7)
        assert len(p.primitives) > before

    def test_adapt_system_no_crash(self):
        p = self._make_primus()
        p._adapt_system()  # No patterns → threshold should decrease
        assert p.synergy_threshold < 0.5

    def test_mine_patterns_no_crash(self):
        p = self._make_primus()
        p._mine_patterns()  # nothing active → no new patterns


# ═══════════════════════════════════════════════════════════════════════════
# 2. Cognitive Synergy Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestSynergyPairDataclass:
    def test_defaults(self):
        sp = SynergyPair("a", "b", 0.5)
        assert sp.process_a == "a"
        assert sp.synergy_strength == 0.5
        assert sp.integration_level == 0.0


class TestCognitiveDynamicDataclass:
    def test_defaults(self):
        cd = CognitiveDynamic(dynamic_type="oscillation")
        assert cd.dynamic_type == "oscillation"
        assert cd.intensity == 0.0


class TestCognitiveSynergyEngine:
    """CognitiveSynergyEngine without starting background threads."""

    def _make_engine(self, **kwargs):
        return CognitiveSynergyEngine(**kwargs)

    def test_constructor_defaults(self):
        e = self._make_engine()
        assert len(e.synergy_pairs) == 10
        assert e.global_coherence == 0.0
        assert e.integration_matrix.shape == (10, 10)

    def test_register_module(self):
        e = self._make_engine()
        mock_mod = MagicMock()
        mock_mod.initialize = MagicMock()
        e.register_module("perception", mock_mod)
        assert "perception" in e.modules
        mock_mod.initialize.assert_called_once_with(e)

    def test_register_module_without_initialize(self):
        e = self._make_engine()
        class SimpleModule:
            pass
        e.register_module("simple", SimpleModule())
        assert "simple" in e.modules

    def test_get_module_state_with_get_state(self):
        e = self._make_engine()
        mod = MagicMock()
        mod.get_state.return_value = {"activation": 0.7}
        state = e._get_module_state(mod)
        assert state == {"activation": 0.7}

    def test_get_module_state_with_state_attr(self):
        e = self._make_engine()
        class Mod:
            state = {"x": 1}
        state = e._get_module_state(Mod())
        assert state == {"x": 1}

    def test_get_module_state_fallback(self):
        e = self._make_engine()
        state = e._get_module_state(object())
        assert "activation" in state

    def test_extract_numerical_features_numeric(self):
        e = self._make_engine()
        features = e._extract_numerical_features({"a": 1.0, "b": 2, "c": "text"})
        assert 1.0 in features
        assert 2.0 in features

    def test_extract_numerical_features_array(self):
        e = self._make_engine()
        features = e._extract_numerical_features({"arr": np.array([1, 2, 3])})
        assert len(features) == 3

    def test_extract_numerical_features_list(self):
        e = self._make_engine()
        features = e._extract_numerical_features({"lst": [4, 5, 6]})
        assert 4.0 in features

    def test_extract_numerical_features_empty(self):
        e = self._make_engine()
        features = e._extract_numerical_features({})
        np.testing.assert_array_equal(features, np.array([0.0]))

    def test_compute_pair_synergy_both_empty(self):
        e = self._make_engine()
        assert e._compute_pair_synergy({}, {}) == 0.0

    def test_compute_pair_synergy_basic(self):
        e = self._make_engine()
        s = e._compute_pair_synergy({"val": 0.5}, {"val": 0.5})
        assert 0.0 <= s <= 1.0

    def test_estimate_mutual_information_identical(self):
        e = self._make_engine()
        x = np.random.randn(100)
        mi = e._estimate_mutual_information(x, x)
        assert mi >= 0.0

    def test_estimate_mutual_information_different_lengths(self):
        e = self._make_engine()
        mi = e._estimate_mutual_information(np.array([1, 2]), np.array([1, 2, 3]))
        assert 0.0 <= mi <= 1.0

    def test_compute_information_flow_empty(self):
        e = self._make_engine()
        flow = e._compute_information_flow({}, {})
        assert flow == 0.0

    def test_compute_integration_level(self):
        e = self._make_engine()
        il = e._compute_integration_level(0.8, 0.6)
        assert il == pytest.approx(0.7 * 0.8 + 0.3 * 0.6, abs=0.01)

    def test_check_emergence_indicators_high_synergy(self):
        e = self._make_engine()
        sp = SynergyPair("a", "b", 0.9)
        sp.bidirectional_flow = {"total_flow": 0.9}
        e._check_emergence_indicators(sp)
        assert "high_synergy" in sp.emergence_indicators
        assert "strong_bidirectional_flow" in sp.emergence_indicators

    def test_check_emergence_indicators_rapid_integration(self):
        e = self._make_engine()
        sp = SynergyPair("a", "b", 0.5)
        sp.bidirectional_flow = {"total_flow": 0.1}
        sp._prev_integration = 0.1
        sp.integration_level = 0.5  # +0.4 change
        e._check_emergence_indicators(sp)
        assert "rapid_integration_increase" in sp.emergence_indicators

    def test_compute_global_coherence(self):
        e = self._make_engine()
        # All pairs at 0 → coherence = 0
        e._compute_global_coherence()
        assert e.global_coherence == pytest.approx(0.0, abs=0.01)

    def test_compute_global_coherence_high(self):
        e = self._make_engine()
        for pair in e.synergy_pairs.values():
            pair.synergy_strength = 0.8
            pair.integration_level = 0.8
        e._compute_global_coherence()
        assert e.global_coherence > 0.0

    def test_update_integration_matrix(self):
        e = self._make_engine()
        e._update_integration_matrix()
        # Diagonal should be 1.0
        for i in range(10):
            assert e.integration_matrix[i, i] == 1.0

    def test_compute_pair_integration_shared(self):
        e = self._make_engine()
        p1 = SynergyPair("x", "y", 0.5)
        p2 = SynergyPair("x", "z", 0.5)
        integration = e._compute_pair_integration(p1, p2)
        assert integration > 0.0  # shared process "x"

    def test_compute_pair_integration_no_shared(self):
        e = self._make_engine()
        p1 = SynergyPair("a", "b", 0.5)
        p2 = SynergyPair("c", "d", 0.5)
        integration = e._compute_pair_integration(p1, p2)
        # No shared processes → base is 0, synergy part remains
        assert integration >= 0.0

    def test_inject_stimulus_perceptual(self):
        e = self._make_engine()
        original = e.synergy_pairs["perception_action"].synergy_strength
        e.inject_stimulus({"type": "perceptual"})
        assert e.synergy_pairs["perception_action"].synergy_strength >= original + 0.2 - 0.01

    def test_inject_stimulus_learning(self):
        e = self._make_engine()
        e.inject_stimulus({"type": "learning"})
        assert e.synergy_pairs["memory_learning"].synergy_strength > 0.0

    def test_inject_stimulus_goal(self):
        e = self._make_engine()
        e.inject_stimulus({"type": "goal"})
        assert e.synergy_pairs["attention_intention"].synergy_strength > 0.0

    def test_get_synergy_strength_known(self):
        """get_synergy_strength has a pre-existing bug: the default fallback
        `SynergyPair('', '')` is missing the required `synergy_strength` arg,
        so it always raises TypeError.  We test via direct dict access."""
        e = self._make_engine()
        e.synergy_pairs["perception_action"].synergy_strength = 0.77
        # Access known pair directly (avoid buggy .get default)
        assert e.synergy_pairs["perception_action"].synergy_strength == 0.77

    def test_get_synergy_strength_unknown_raises(self):
        """Pre-existing bug: SynergyPair('', '') missing positional arg."""
        e = self._make_engine()
        with pytest.raises(TypeError):
            e.get_synergy_strength("nonexistent")

    def test_get_emergence_indicators(self):
        e = self._make_engine()
        e.synergy_pairs["perception_action"].emergence_indicators = ["high_synergy"]
        indicators = e.get_emergence_indicators()
        assert len(indicators) == 1
        assert indicators[0]["pair"] == "perception_action"

    def test_get_system_state_keys(self):
        e = self._make_engine()
        state = e.get_system_state()
        assert "primus_state" in state
        assert "synergy_pairs" in state
        assert "global_coherence" in state
        assert "integration_matrix" in state
        assert "performance_metrics" in state

    def test_detect_oscillations_no_crash(self):
        e = self._make_engine()
        e._detect_oscillations()

    def test_detect_phase_transitions_no_crash(self):
        e = self._make_engine()
        e._detect_phase_transitions()

    def test_cleanup_expired_dynamics(self):
        e = self._make_engine()
        old = CognitiveDynamic(dynamic_type="test")
        old.start_time = time.time() - 120  # 2 min old
        e.cognitive_dynamics.append(old)
        e._cleanup_expired_dynamics()
        assert len(e.cognitive_dynamics) == 0

    def test_update_single_synergy_pair_no_modules(self):
        """Without modules registered, falls back to primitives."""
        e = self._make_engine()
        pair = e.synergy_pairs["perception_action"]
        e._update_single_synergy_pair("perception_action", pair)
        # Should not crash — falls through to _update_pair_from_primitives

    def test_update_pair_from_primitives_decay(self):
        """No matching primitives → strength decays."""
        e = self._make_engine()
        pair = SynergyPair("x", "y", 0.5)
        e._update_pair_from_primitives("test", pair)
        assert pair.synergy_strength < 0.5  # decayed

    def test_context_manager(self):
        e = self._make_engine()
        e.start()
        time.sleep(0.05)
        e.stop()
        assert not e._running


# ═══════════════════════════════════════════════════════════════════════════
# 3. Emergent Properties
# ═══════════════════════════════════════════════════════════════════════════

class TestEmergentPropertyDataclass:
    def test_basic_creation(self):
        ep = EmergentProperty(
            id="ep1", name="test", description="desc",
            emergence_type="behavioral", strength=0.8, novelty=0.9,
            stability=0.7, complexity=0.6, contributing_processes=["a"]
        )
        assert ep.observation_count == 1
        assert ep.evidence == []


class TestBehavioralEmergenceDetector:
    def test_empty_state(self):
        d = BehavioralEmergenceDetector()
        result = d.detect({})
        assert result == []

    def test_detect_high_synergy_behavior(self):
        d = BehavioralEmergenceDetector(novelty_threshold=0.5)
        state = {
            "synergy_pairs": {
                "pattern_reasoning": {"synergy_strength": 0.9}
            }
        }
        results = d.detect(state)
        assert len(results) >= 1
        assert results[0].emergence_type == "behavioral"

    def test_known_behavior_not_novel(self):
        d = BehavioralEmergenceDetector(novelty_threshold=0.5)
        state = {
            "synergy_pairs": {
                "p_r": {"synergy_strength": 0.9}
            }
        }
        # First detection → novel
        r1 = d.detect(state)
        assert len(r1) >= 1
        # Second detection — same signature → not novel
        r2 = d.detect(state)
        # Signature is already known, so novelty=0, won't pass threshold
        assert len(r2) == 0

    def test_cascade_detection(self):
        d = BehavioralEmergenceDetector(novelty_threshold=0.3)
        dynamics = [
            {"age": 1, "parameters": {"pair": "a"}},
            {"age": 1, "parameters": {"pair": "b"}},
            {"age": 1, "parameters": {"pair": "c"}},
        ]
        state = {"cognitive_dynamics": dynamics}
        results = d.detect(state)
        # Should detect cascade (3+ dynamics in same time bin)
        cascade_found = any("cascade" in r.name for r in results)
        assert cascade_found

    def test_behavior_complexity(self):
        d = BehavioralEmergenceDetector()
        behavior = {"processes": ["a", "b", "c"], "type": "cascade"}
        complexity = d._compute_behavior_complexity(behavior)
        assert 0.0 <= complexity <= 1.0

    def test_signature_similarity(self):
        d = BehavioralEmergenceDetector()
        sim = d._compute_signature_similarity("coord_pattern_reasoning_0.90",
                                               "coord_pattern_reasoning_0.85")
        assert sim > 0.5  # High overlap in words

    def test_get_detector_type(self):
        d = BehavioralEmergenceDetector()
        assert d.get_detector_type() == "behavioral"


class TestStructuralEmergenceDetector:
    def test_empty_state(self):
        d = StructuralEmergenceDetector()
        assert d.detect({}) == []

    def test_integration_matrix_analysis(self):
        d = StructuralEmergenceDetector(structure_threshold=0.3)
        # Create a matrix with some structure
        matrix = np.eye(5) * 0.8
        matrix[0, 1] = matrix[1, 0] = 0.9
        matrix[2, 3] = matrix[3, 2] = 0.9
        state = {"integration_matrix": matrix.tolist()}
        results = d.detect(state)
        # Should detect at least hub or community structure
        assert isinstance(results, list)

    def test_hierarchical_detection(self):
        d = StructuralEmergenceDetector(structure_threshold=0.3)
        state = {
            "synergy_pairs": {
                "high1": {"synergy_strength": 0.9},
                "high2": {"synergy_strength": 0.85},
                "mid1": {"synergy_strength": 0.7},
                "low1": {"synergy_strength": 0.2},
            }
        }
        results = d.detect(state)
        hierarchy_found = any(r.name == "hierarchical_synergy" for r in results)
        assert hierarchy_found

    def test_structure_novelty_new_type(self):
        d = StructuralEmergenceDetector()
        assert d._compute_structure_novelty({"type": "brand_new", "strength": 0.5}) == 1.0

    def test_get_detector_type(self):
        assert StructuralEmergenceDetector().get_detector_type() == "structural"


class TestFunctionalEmergenceDetector:
    def test_empty_state(self):
        d = FunctionalEmergenceDetector()
        assert d.detect({}) == []

    def test_metacognitive_function_detected(self):
        d = FunctionalEmergenceDetector(capability_threshold=0.5)
        state = {"global_coherence": 0.9}
        results = d.detect(state)
        assert any(r.name == "metacognitive_integration" for r in results)

    def test_problem_solving_function(self):
        d = FunctionalEmergenceDetector(capability_threshold=0.5)
        state = {
            "synergy_pairs": {
                "pattern_reasoning": {"synergy_strength": 0.9}
            }
        }
        results = d.detect(state)
        assert any(r.name == "enhanced_problem_solving" for r in results)

    def test_learning_function(self):
        d = FunctionalEmergenceDetector(capability_threshold=0.5)
        state = {
            "synergy_pairs": {
                "memory_learning": {"synergy_strength": 0.9}
            }
        }
        results = d.detect(state)
        assert any(r.name == "accelerated_learning" for r in results)

    def test_known_function_not_novel(self):
        d = FunctionalEmergenceDetector(capability_threshold=0.5)
        state = {"global_coherence": 0.9}
        d.detect(state)  # first time → novel
        results = d.detect(state)  # second → not novel
        assert len(results) == 0

    def test_function_stability_tracks_history(self):
        d = FunctionalEmergenceDetector()
        func = {"name": "test_func", "strength": 0.8}
        for _ in range(6):
            d._compute_function_stability(func)
        assert len(d.performance_history["test_func"]) >= 6

    def test_get_detector_type(self):
        assert FunctionalEmergenceDetector().get_detector_type() == "functional"


class TestEmergentPropertyDetector:
    def test_constructor(self):
        epd = EmergentPropertyDetector()
        assert epd.emergence_threshold == 0.7
        assert len(epd.detectors) == 3

    def test_detect_emergence_empty(self):
        epd = EmergentPropertyDetector()
        results = epd.detect_emergence({})
        assert isinstance(results, list)

    def test_detect_emergence_with_data(self):
        epd = EmergentPropertyDetector(emergence_threshold=0.5)
        state = {
            "global_coherence": 0.95,
            "synergy_pairs": {
                "pattern_reasoning": {"synergy_strength": 0.95},
                "memory_learning": {"synergy_strength": 0.95},
            },
        }
        results = epd.detect_emergence(state)
        assert len(results) > 0

    def test_detect_system_emergence_high_coherence(self):
        epd = EmergentPropertyDetector()
        props = epd.detect_system_emergence(
            synergy_pairs={"a": {}, "b": {}},
            global_coherence=0.95,
            integration_matrix=np.ones((2, 2)),
        )
        assert any("metacognitive" in p.name for p in props)

    def test_detect_system_emergence_high_integration(self):
        epd = EmergentPropertyDetector()
        props = epd.detect_system_emergence(
            synergy_pairs={"a": {}},
            global_coherence=0.5,
            integration_matrix=np.full((3, 3), 0.9),
        )
        assert any("collective" in p.name for p in props)

    def test_get_stable_properties(self):
        epd = EmergentPropertyDetector()
        ep = EmergentProperty(
            id="test1", name="t", description="d", emergence_type="cognitive",
            strength=0.9, novelty=0.9, stability=0.9, complexity=0.9,
            contributing_processes=["x"]
        )
        epd.detected_properties["test1"] = ep
        stable = epd.get_stable_properties(0.8)
        assert len(stable) == 1

    def test_get_novel_properties(self):
        epd = EmergentPropertyDetector()
        ep = EmergentProperty(
            id="n1", name="n", description="d", emergence_type="behavioral",
            strength=0.9, novelty=0.95, stability=0.5, complexity=0.5,
            contributing_processes=[]
        )
        epd.detected_properties["n1"] = ep
        assert len(epd.get_novel_properties(0.9)) == 1

    def test_get_complex_properties(self):
        epd = EmergentPropertyDetector()
        ep = EmergentProperty(
            id="c1", name="c", description="d", emergence_type="structural",
            strength=0.5, novelty=0.5, stability=0.5, complexity=0.95,
            contributing_processes=[]
        )
        epd.detected_properties["c1"] = ep
        assert len(epd.get_complex_properties(0.9)) == 1

    def test_get_emergence_summary(self):
        epd = EmergentPropertyDetector()
        summary = epd.get_emergence_summary()
        assert "total_properties" in summary
        assert "by_type" in summary
        assert "detection_stats" in summary

    def test_property_tracking_update_existing(self):
        epd = EmergentPropertyDetector()
        ep = EmergentProperty(
            id="x1", name="x", description="d", emergence_type="behavioral",
            strength=0.8, novelty=0.8, stability=0.8, complexity=0.8,
            contributing_processes=[]
        )
        epd.detected_properties["x1"] = ep
        epd._update_property_tracking([ep])
        assert ep.observation_count == 2


# ═══════════════════════════════════════════════════════════════════════════
# 4. Self-Organization
# ═══════════════════════════════════════════════════════════════════════════

class TestOrganizationState:
    def test_defaults(self):
        s = OrganizationState()
        assert s.entropy == 0.0
        assert s.coherence == 0.0


class TestSelfOrganizationMechanism:
    def _make_som(self, **kwargs):
        return SelfOrganizationMechanism(**kwargs)

    def test_constructor(self):
        som = self._make_som()
        assert som.target_coherence == 0.8
        assert len(som.organization_rules) == 6

    def test_apply_basic(self):
        som = self._make_som()
        synergy_pairs = {
            "pair1": {"synergy_strength": 0.5, "integration_level": 0.5}
        }
        result = som.apply(
            synergy_pairs=synergy_pairs,
            global_coherence=0.5,
            integration_matrix=np.eye(3),
            performance_history={"metric": [0.5, 0.6]}
        )
        assert "organization_rules" in result
        assert "homeostatic" in result
        assert "restructuring" in result

    def test_system_entropy_no_pairs(self):
        som = self._make_som()
        entropy = som._compute_system_entropy({}, np.eye(3))
        assert entropy == 1.0  # Max entropy

    def test_system_entropy_uniform(self):
        som = self._make_som()
        pairs = {"a": {"synergy_strength": 0.5}, "b": {"synergy_strength": 0.5}}
        entropy = som._compute_system_entropy(pairs, np.eye(2))
        assert 0.0 <= entropy <= 1.0

    def test_system_complexity(self):
        som = self._make_som()
        c = som._compute_system_complexity({}, np.eye(5))
        assert 0.0 <= c <= 1.0

    def test_system_efficiency_empty(self):
        som = self._make_som()
        assert som._compute_system_efficiency({}) == 0.5

    def test_system_efficiency_with_data(self):
        som = self._make_som()
        perf = {"m1": [0.8] * 10, "m2": [0.7] * 10}
        eff = som._compute_system_efficiency(perf)
        assert 0.0 <= eff <= 1.0

    def test_system_adaptability_insufficient_history(self):
        som = self._make_som()
        assert som._compute_system_adaptability() == 0.5

    def test_system_stability_empty(self):
        som = self._make_som()
        assert som._compute_system_stability({}) == 0.5

    def test_system_stability_with_data(self):
        som = self._make_som()
        perf = {"m": [0.5] * 20}
        stab = som._compute_system_stability(perf)
        assert stab > 0.9  # constant → high stability

    def test_detect_load_imbalance(self):
        som = self._make_som()
        state = {"synergy_pairs": {
            "a": {"synergy_strength": 0.1},
            "b": {"synergy_strength": 0.9},
        }}
        assert som._detect_load_imbalance(state) == True  # np.bool_ compatible

    def test_detect_load_imbalance_balanced(self):
        som = self._make_som()
        state = {"synergy_pairs": {
            "a": {"synergy_strength": 0.5},
            "b": {"synergy_strength": 0.5},
        }}
        assert som._detect_load_imbalance(state) == False  # np.bool_ compatible

    def test_detect_weak_connections(self):
        som = self._make_som()
        state = {"synergy_pairs": {
            "a": {"synergy_strength": 0.1},
            "b": {"synergy_strength": 0.1},
            "c": {"synergy_strength": 0.9},
        }}
        assert som._detect_weak_connections(state) is True

    def test_detect_strong_synergy(self):
        som = self._make_som()
        state = {"synergy_pairs": {"a": {"synergy_strength": 0.9}}}
        assert som._detect_strong_synergy(state) is True

    def test_detect_resource_inefficiency(self):
        som = self._make_som()
        os = OrganizationState(efficiency=0.3)
        state = {"current_state": os}
        assert som._detect_resource_inefficiency(state) is True

    def test_detect_specialization_opportunity(self):
        som = self._make_som()
        state = {"synergy_pairs": {
            "a": {"synergy_strength": 0.8, "integration_level": 0.8}
        }}
        assert som._detect_specialization_opportunity(state) is True

    def test_regulate_coherence_low(self):
        som = self._make_som()
        result = som._regulate_coherence({"global_coherence": 0.3})
        assert result["action"] == "increase_integration"

    def test_regulate_coherence_high(self):
        som = self._make_som()
        result = som._regulate_coherence({"global_coherence": 0.95})
        assert result["action"] == "add_noise"

    def test_balance_load_empty(self):
        som = self._make_som()
        result = som._balance_load({"synergy_pairs": {}})
        assert result == {}

    def test_prune_weak_connections(self):
        som = self._make_som()
        state = {"synergy_pairs": {
            "a": {"synergy_strength": 0.1},
            "b": {"synergy_strength": 0.9},
        }}
        result = som._prune_weak_connections(state)
        assert "a" in result["pairs_to_prune"]

    def test_get_organization_metrics(self):
        som = self._make_som()
        metrics = som.get_organization_metrics()
        assert "current_state" in metrics
        assert "rule_statistics" in metrics
        assert "organization_history_summary" in metrics

    def test_should_apply_rule_cooldown(self):
        som = self._make_som()
        rule = som.organization_rules[0]
        rule.last_applied = time.time()  # just applied
        assert som._should_apply_rule(rule, {}) is False

    def test_evaluate_rule_effectiveness(self):
        som = self._make_som()
        rule = som.organization_rules[0]
        eff = som._evaluate_rule_effectiveness(rule, {"improvement": 0.9})
        assert eff == 0.9
        eff2 = som._evaluate_rule_effectiveness(rule, {})
        assert eff2 == 0.6


class TestHomeostaticController:
    def test_apply_divergent(self):
        hc = HomeostaticController()
        result = hc.apply({"global_coherence": 0.3})
        assert "coherence_adjustment" in result

    def test_apply_stable(self):
        hc = HomeostaticController()
        result = hc.apply({"global_coherence": 0.8})
        assert result == {}


class TestAdaptiveRestructurer:
    def test_low_integration(self):
        ar = AdaptiveRestructurer()
        result = ar.apply({"integration_matrix": np.full((3, 3), 0.3)})
        assert "increase_connectivity" in result

    def test_high_integration(self):
        ar = AdaptiveRestructurer()
        result = ar.apply({"integration_matrix": np.full((3, 3), 0.95)})
        assert "reduce_connectivity" in result

    def test_empty_matrix(self):
        ar = AdaptiveRestructurer()
        result = ar.apply({"integration_matrix": np.array([])})
        assert result == {}


class TestResourceOptimizer:
    def test_low_efficiency(self):
        ro = ResourceOptimizer()
        state = OrganizationState(efficiency=0.3)
        result = ro.apply({"current_state": state})
        assert "resource_optimization" in result

    def test_high_efficiency(self):
        ro = ResourceOptimizer()
        state = OrganizationState(efficiency=0.9)
        result = ro.apply({"current_state": state})
        assert result == {}


class TestCoherenceMaintainer:
    def test_high_variance(self):
        cm = CoherenceMaintainer()
        result = cm.apply({"synergy_pairs": {
            "a": {"synergy_strength": 0.1},
            "b": {"synergy_strength": 0.9},
        }})
        assert "coherence_restoration" in result

    def test_low_variance(self):
        cm = CoherenceMaintainer()
        result = cm.apply({"synergy_pairs": {
            "a": {"synergy_strength": 0.5},
            "b": {"synergy_strength": 0.5},
        }})
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════
# 5. Reasoning Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestReasoningType:
    def test_enum_values(self):
        assert ReasoningType.DEDUCTIVE.value == "deductive"
        assert ReasoningType.INDUCTIVE.value == "inductive"
        assert ReasoningType.ABDUCTIVE.value == "abductive"
        assert ReasoningType.ANALOGICAL.value == "analogical"


class TestKnowledgeItem:
    def test_creation(self):
        ki = KnowledgeItem(id="k1", content="test", knowledge_type="fact",
                          confidence=0.9, source="input")
        assert ki.id == "k1"
        assert ki.connections == set()


class TestDeductiveRule:
    def test_can_apply_true(self):
        rule = DeductiveRule("mp", "A->B, A |- B")
        premises = [
            KnowledgeItem(id="i1", content="rain implies wet", knowledge_type="rule",
                         confidence=0.9, source="input"),
            KnowledgeItem(id="f1", content="rain", knowledge_type="fact",
                         confidence=0.9, source="input"),
        ]
        assert rule.can_apply(premises) is True

    def test_can_apply_false_no_implication(self):
        rule = DeductiveRule("mp", "A->B, A |- B")
        premises = [
            KnowledgeItem(id="f1", content="sun", knowledge_type="fact",
                         confidence=0.9, source="input"),
        ]
        assert rule.can_apply(premises) is False

    def test_apply_modus_ponens(self):
        rule = DeductiveRule("mp", "A->B, A |- B")
        premises = [
            KnowledgeItem(id="i1", content="rain implies wet ground",
                         knowledge_type="rule", confidence=0.9, source="input"),
            KnowledgeItem(id="f1", content="rain is falling",
                         knowledge_type="fact", confidence=0.8, source="input"),
        ]
        inferences = rule.apply(premises)
        assert len(inferences) >= 1
        assert inferences[0].inference_type == ReasoningType.DEDUCTIVE
        assert "wet ground" in inferences[0].conclusion

    def test_extract_consequent(self):
        rule = DeductiveRule("mp", "test")
        ki = KnowledgeItem(id="i", content="A implies B", knowledge_type="rule",
                          confidence=0.9, source="input")
        result = rule._extract_consequent(ki)
        assert result == "B"


class TestInductiveRule:
    def test_can_apply_enough_facts(self):
        rule = InductiveRule()
        facts = [
            KnowledgeItem(id=f"f{i}", content="birds can fly",
                         knowledge_type="fact", confidence=0.9, source="input")
            for i in range(3)
        ]
        assert rule.can_apply(facts) is True

    def test_can_apply_not_enough(self):
        rule = InductiveRule()
        facts = [
            KnowledgeItem(id="f1", content="bird", knowledge_type="fact",
                         confidence=0.9, source="input"),
        ]
        assert rule.can_apply(facts) is False

    def test_apply_generalization(self):
        rule = InductiveRule()
        facts = [
            KnowledgeItem(id=f"f{i}", content=f"birds can fly in area {i}",
                         knowledge_type="fact", confidence=0.9, source="input")
            for i in range(5)
        ]
        inferences = rule.apply(facts)
        # Should find groups and generalize
        assert isinstance(inferences, list)

    def test_facts_similar(self):
        rule = InductiveRule()
        f1 = KnowledgeItem(id="a", content="birds can fly high", knowledge_type="fact",
                          confidence=1.0, source="input")
        f2 = KnowledgeItem(id="b", content="birds can fly far", knowledge_type="fact",
                          confidence=1.0, source="input")
        assert rule._facts_similar(f1, f2) is True

    def test_facts_not_similar(self):
        rule = InductiveRule()
        f1 = KnowledgeItem(id="a", content="birds fly", knowledge_type="fact",
                          confidence=1.0, source="input")
        f2 = KnowledgeItem(id="b", content="fish swim underwater deep",
                          knowledge_type="fact", confidence=1.0, source="input")
        assert rule._facts_similar(f1, f2) is False


class TestAbductiveRule:
    def test_can_apply(self):
        rule = AbductiveRule()
        premises = [
            KnowledgeItem(id="o1", content="observed wet ground",
                         knowledge_type="fact", confidence=0.9, source="input"),
        ]
        assert rule.can_apply(premises) is True

    def test_can_apply_no_observations(self):
        rule = AbductiveRule()
        premises = [
            KnowledgeItem(id="f1", content="clear sky",
                         knowledge_type="fact", confidence=0.9, source="input"),
        ]
        assert rule.can_apply(premises) is False

    def test_apply(self):
        rule = AbductiveRule()
        premises = [
            KnowledgeItem(id="o1", content="observed wet ground",
                         knowledge_type="fact", confidence=0.9, source="input"),
            KnowledgeItem(id="r1", content="rain causes wet ground",
                         knowledge_type="rule", confidence=0.8, source="input"),
        ]
        inferences = rule.apply(premises)
        assert len(inferences) >= 1
        assert inferences[0].inference_type == ReasoningType.ABDUCTIVE


class TestReasoningEngine:
    def _make_engine(self, **kwargs):
        return ReasoningEngine(**kwargs)

    def test_constructor(self):
        re = self._make_engine()
        assert re.confidence_threshold == 0.5
        assert len(re.knowledge_base) == 0

    def test_add_knowledge(self):
        re = self._make_engine()
        re.add_knowledge("the sky is blue", knowledge_type="fact", confidence=0.9)
        assert len(re.knowledge_base) == 1
        assert len(re.reasoning_agenda) == 1

    def test_add_knowledge_low_confidence(self):
        re = self._make_engine()
        re.add_knowledge("maybe something", confidence=0.3)
        # Low confidence → not in working memory
        assert len(re.working_memory) == 0

    def test_reason_empty(self):
        re = self._make_engine()
        inferences = re.reason()
        assert inferences == []

    def test_reason_with_facts(self):
        re = self._make_engine()
        re.add_knowledge("rain implies wet", knowledge_type="rule", confidence=0.9)
        re.add_knowledge("rain today", knowledge_type="fact", confidence=0.9)
        inferences = re.reason()
        # May or may not produce inferences depending on term matching
        assert isinstance(inferences, list)

    def test_generate_hypothesis(self):
        re = self._make_engine()
        hyp = re.generate_hypothesis(["observed X", "observed Y"])
        assert isinstance(hyp, Hypothesis)
        assert hyp.confidence == 0.6
        assert re.reasoning_stats["hypotheses_generated"] == 1

    def test_generate_hypothesis_inductive(self):
        re = self._make_engine()
        hyp = re.generate_hypothesis(["obs1"], reasoning_type=ReasoningType.INDUCTIVE)
        assert "Generalization" in hyp.content

    def test_find_related_knowledge(self):
        re = self._make_engine()
        # Use time.sleep to avoid ID collision (add_knowledge uses ms timestamp as ID)
        # Need >0.2 Jaccard overlap, so use content with high word overlap
        re.add_knowledge("birds can fly fast in the sky", knowledge_type="fact", confidence=0.9)
        time.sleep(0.002)
        re.add_knowledge("birds can fly high in the sky", knowledge_type="fact", confidence=0.8)
        time.sleep(0.002)
        re.add_knowledge("fish swim deep underwater alone", knowledge_type="fact", confidence=0.9)

        re.reasoning_agenda.clear()

        target = list(re.knowledge_base.values())[0]
        related = re._find_related_knowledge(target)
        # "birds can fly ... in the sky" shares 6/8 words → Jaccard=6/8=0.75 > 0.2
        assert len(related) >= 1

    def test_compute_analogy_strength(self):
        re = self._make_engine()
        k1 = KnowledgeItem(id="a", content="birds can fly", knowledge_type="fact",
                          confidence=0.9, source="input")
        k2 = KnowledgeItem(id="b", content="birds can swim", knowledge_type="fact",
                          confidence=0.9, source="input")
        strength = re._compute_analogy_strength(k1, k2)
        assert 0.0 < strength < 1.0

    def test_validate_inferences_filters_low_confidence(self):
        re = self._make_engine()
        inf = Inference(
            id="test", premises=["p1"], conclusion="low conf result",
            inference_type=ReasoningType.DEDUCTIVE, confidence=0.1
        )
        valid = re._validate_inferences([inf])
        assert len(valid) == 0

    def test_validate_inferences_filters_duplicates(self):
        re = self._make_engine()
        inf1 = Inference(
            id="dup1", premises=["p1"], conclusion="same conclusion here",
            inference_type=ReasoningType.DEDUCTIVE, confidence=0.9
        )
        re.inferences["existing"] = Inference(
            id="existing", premises=["p2"], conclusion="same conclusion here exactly",
            inference_type=ReasoningType.DEDUCTIVE, confidence=0.9
        )
        valid = re._validate_inferences([inf1])
        # "same conclusion here" vs "same conclusion here exactly" — high Jaccard overlap
        # Whether filtered depends on > 0.8 threshold
        assert isinstance(valid, list)

    def test_get_state(self):
        re = self._make_engine()
        state = re.get_state()
        assert "activation_level" in state
        assert "knowledge_base_size" in state
        assert "reasoning_stats" in state
        assert "confidence_distribution" in state

    def test_query_knowledge(self):
        re = self._make_engine()
        re.add_knowledge("the cat sat on the mat", knowledge_type="fact", confidence=0.9)
        time.sleep(0.002)
        re.add_knowledge("the dog ran in the park", knowledge_type="fact", confidence=0.9)
        results = re.query_knowledge("cat mat")
        assert len(results) >= 1
        assert "cat" in str(results[0].content).lower()

    def test_receive_pattern_feedback(self):
        re = self._make_engine()
        initial_activation = re.activation_level
        re.receive_pattern_feedback(["pattern_1"])
        time.sleep(0.002)
        re.receive_pattern_feedback(["pattern_2"])
        assert re.activation_level > initial_activation
        # Should have added patterns as knowledge (2 separate calls to avoid ms collision)
        assert len(re.knowledge_base) == 2

    def test_send_reasoning_to_patterns(self):
        re = self._make_engine()
        mock_pattern_engine = MagicMock()
        result = re.send_reasoning_to_patterns(mock_pattern_engine)
        assert "inferences" in result
        assert "hypotheses" in result
        assert "timestamp" in result

    def test_confidence_distribution(self):
        re = self._make_engine()
        re.add_knowledge("high confidence item", confidence=0.9)
        time.sleep(0.002)
        re.add_knowledge("mid confidence item", confidence=0.6)
        time.sleep(0.002)
        re.add_knowledge("low confidence item", confidence=0.2)
        assert len(re.knowledge_base) == 3
        dist = re._get_confidence_distribution()
        assert dist["high"] == 1
        assert dist["medium"] == 1
        assert dist["low"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# 6. Pattern Mining Engine
# ═══════════════════════════════════════════════════════════════════════════

class TestPatternDataclass:
    def test_creation(self):
        p = Pattern(id="p1", type="sequence", content=[1, 2], confidence=0.9,
                   support=5, frequency=0.3, complexity=0.1)
        assert p.metadata == {}


class TestPatternMiningEngine:
    def _make_engine(self, **kwargs):
        return PatternMiningEngine(**kwargs)

    def test_constructor(self):
        pe = self._make_engine()
        assert pe.max_patterns == 10000
        assert pe.min_support == 3

    def test_process_input_sequence(self):
        pe = self._make_engine()
        pe.process_input({"type": "sequence", "data": [1, 2, 3]})
        assert len(pe.sequence_buffer) == 1
        assert pe.activation_level > 0.0

    def test_process_input_temporal(self):
        pe = self._make_engine()
        pe.process_input({"type": "temporal", "data": 0.5})
        assert len(pe.temporal_buffer) == 1

    def test_process_input_causal(self):
        pe = self._make_engine()
        pe.process_input({"type": "causal", "data": {"state": "A"}})
        assert len(pe.causal_buffer) == 1

    def test_process_input_unknown_type(self):
        pe = self._make_engine()
        pe.process_input({"type": "unknown", "data": "x"})
        # Default goes to sequence buffer
        assert len(pe.sequence_buffer) == 1

    def test_mine_patterns_empty(self):
        pe = self._make_engine()
        patterns = pe.mine_patterns()
        assert patterns == []

    def test_mine_sequence_patterns(self):
        pe = self._make_engine(min_support=2, min_confidence=0.3)
        # Add identical sequences
        for _ in range(5):
            pe.process_input({"type": "sequence", "data": [1.0, 2.0, 3.0]})
        patterns = pe._mine_sequence_patterns()
        assert isinstance(patterns, list)

    def test_mine_temporal_patterns(self):
        pe = self._make_engine()
        for i in range(20):
            pe.process_input({"type": "temporal", "data": float(i), "timestamp": float(i)})
        patterns = pe._mine_temporal_patterns()
        assert isinstance(patterns, list)

    def test_detect_trends_increasing(self):
        pe = self._make_engine()
        ts = np.arange(20, dtype=float)  # monotonically increasing
        trends = pe._detect_trends(ts)
        assert any(t["type"] == "increasing" for t in trends)

    def test_detect_trends_decreasing(self):
        pe = self._make_engine()
        ts = np.arange(20, 0, -1, dtype=float)
        trends = pe._detect_trends(ts)
        assert any(t["type"] == "decreasing" for t in trends)

    def test_detect_trends_short(self):
        pe = self._make_engine()
        trends = pe._detect_trends(np.array([1.0, 2.0]))
        assert trends == []

    def test_detect_cycles(self):
        pe = self._make_engine()
        # Create sinusoidal signal with period ~4
        t = np.arange(40)
        ts = np.sin(2 * np.pi * t / 4)
        cycles = pe._detect_cycles(ts)
        assert isinstance(cycles, list)

    def test_detect_cycles_short(self):
        pe = self._make_engine()
        assert pe._detect_cycles(np.array([1, 2])) == []

    def test_mine_spatial_patterns(self):
        pe = self._make_engine(min_support=2, min_confidence=0.3)
        # Add similar spatial data
        for _ in range(5):
            pe.process_input({"type": "spatial", "data": np.random.randn(10)})
        patterns = pe._mine_spatial_patterns()
        assert isinstance(patterns, list)

    def test_mine_causal_patterns(self):
        pe = self._make_engine()
        for i in range(5):
            pe.process_input({"type": "causal", "data": {"state": f"state_{i % 2}"}})
        patterns = pe._mine_causal_patterns()
        assert isinstance(patterns, list)

    def test_find_common_subsequences(self):
        pe = self._make_engine(min_support=2, min_confidence=0.3)
        seqs = [[1, 2, 3], [1, 2, 3], [1, 2, 4]]
        result = pe._find_common_subsequences(seqs)
        assert isinstance(result, list)

    def test_validate_patterns(self):
        pe = self._make_engine()
        p = Pattern(id="v1", type="sequence", content=[1], confidence=0.9,
                   support=5, frequency=0.5, complexity=0.1)
        valid = pe._validate_patterns([p])
        assert len(valid) == 1

    def test_validate_patterns_low_support(self):
        pe = self._make_engine(min_support=10)
        p = Pattern(id="v1", type="sequence", content=[1], confidence=0.9,
                   support=2, frequency=0.5, complexity=0.1)
        valid = pe._validate_patterns([p])
        assert len(valid) == 0

    def test_patterns_similar_different_types(self):
        pe = self._make_engine()
        p1 = Pattern(id="a", type="sequence", content=[1], confidence=0.9,
                    support=5, frequency=0.5, complexity=0.1)
        p2 = Pattern(id="b", type="temporal", content=[1], confidence=0.9,
                    support=5, frequency=0.5, complexity=0.1)
        assert pe._patterns_similar(p1, p2) is False

    def test_sequence_similarity(self):
        pe = self._make_engine()
        assert pe._sequence_similarity([1, 2, 3], [1, 2, 3]) == 1.0
        assert pe._sequence_similarity([], []) == 0.0

    def test_numerical_similarity(self):
        pe = self._make_engine()
        assert pe._numerical_similarity(np.array([1, 2, 3]), np.array([1, 2, 3])) > 0.99
        assert pe._numerical_similarity(np.array([1, 2]), np.array([1, 2, 3])) == 0.0

    def test_structural_similarity(self):
        pe = self._make_engine()
        s1 = {"a": 1, "b": 2}
        s2 = {"a": 1, "c": 3}
        sim = pe._structural_similarity(s1, s2)
        assert 0.0 < sim < 1.0

    def test_prune_patterns(self):
        pe = self._make_engine(max_patterns=2)
        for i in range(5):
            pe.patterns[f"p{i}"] = Pattern(
                id=f"p{i}", type="sequence", content=[i], confidence=0.5,
                support=1, frequency=0.1, complexity=0.1
            )
        pe._prune_patterns()
        assert len(pe.patterns) == 2

    def test_get_state(self):
        pe = self._make_engine()
        state = pe.get_state()
        assert "num_patterns" in state
        assert "buffer_sizes" in state
        assert "mining_stats" in state

    def test_get_patterns_by_type(self):
        pe = self._make_engine()
        pe.patterns["s1"] = Pattern(id="s1", type="sequence", content=[1],
                                   confidence=0.9, support=3, frequency=0.5, complexity=0.1)
        pe.patterns["t1"] = Pattern(id="t1", type="temporal", content=[2],
                                   confidence=0.9, support=3, frequency=0.5, complexity=0.1)
        assert len(pe.get_patterns_by_type("sequence")) == 1
        assert len(pe.get_patterns_by_type("temporal")) == 1

    def test_get_top_patterns(self):
        pe = self._make_engine()
        pe.patterns["a"] = Pattern(id="a", type="sequence", content=[], confidence=0.9,
                                  support=10, frequency=0.5, complexity=0.1)
        pe.patterns["b"] = Pattern(id="b", type="sequence", content=[], confidence=0.5,
                                  support=1, frequency=0.1, complexity=0.5)
        top = pe.get_top_patterns(1)
        assert len(top) == 1
        assert top[0].id == "a"

    def test_receive_reasoning_feedback(self):
        pe = self._make_engine()
        pe.patterns["x"] = Pattern(id="x", type="causal", content={}, confidence=0.7,
                                  support=3, frequency=0.5, complexity=0.1)
        pe.receive_reasoning_feedback({"boost_types": ["causal"]})
        assert pe.patterns["x"].confidence > 0.7

    def test_send_patterns_to_reasoning(self):
        pe = self._make_engine()
        mock_re = MagicMock()
        result = pe.send_patterns_to_reasoning(mock_re)
        assert "patterns" in result
        assert "timestamp" in result

    def test_build_pattern_hierarchy(self):
        pe = self._make_engine()
        pe.patterns["p1"] = Pattern(id="p1", type="sequence", content=[1],
                                   confidence=0.9, support=5, frequency=0.5, complexity=0.1)
        pe.patterns["p2"] = Pattern(id="p2", type="sequence", content=[1, 2],
                                   confidence=0.9, support=10, frequency=0.5, complexity=0.2)
        pe._build_pattern_hierarchy()
        # At least nodes should be added
        assert pe.pattern_hierarchy.relationships.number_of_nodes() >= 2


# ═══════════════════════════════════════════════════════════════════════════
# 7. Pattern-Reasoning Synergy
# ═══════════════════════════════════════════════════════════════════════════

class TestSynergyEvent:
    def test_creation(self):
        se = SynergyEvent(event_type="test")
        assert se.synergy_strength == 0.0
        assert se.timestamp > 0


class TestAbstractionEngine:
    def test_detect_abstractions_empty(self):
        ae = AbstractionEngine()
        result = ae.detect_abstractions({}, {}, [])
        assert result == []

    def test_detect_convergent_pattern_knowledge(self):
        """Convergence = jaccard(words) × pattern.confidence × knowledge.confidence.
        Need overlap large enough to exceed 0.7 threshold."""
        ae = AbstractionEngine()
        # Use identical content for maximum convergence: Jaccard=1.0, conf=1.0×1.0=1.0
        p = Pattern(id="p1", type="causal", content="rain wet ground",
                   confidence=1.0, support=5, frequency=0.5, complexity=0.1)
        k = KnowledgeItem(id="k1", content="rain wet ground",
                         knowledge_type="fact", confidence=1.0, source="input")
        result = ae.detect_abstractions({"p1": p}, {"k1": k}, [])
        assert len(result) >= 1
        assert result[0]["emergence_level"] > 0.7

    def test_compute_convergence_disjoint(self):
        ae = AbstractionEngine()
        p = Pattern(id="p1", type="seq", content="apple banana cherry",
                   confidence=0.9, support=5, frequency=0.5, complexity=0.1)
        k = KnowledgeItem(id="k1", content="xyz uvw rst",
                         knowledge_type="fact", confidence=0.9, source="input")
        assert ae._compute_convergence(p, k) == 0.0


class TestAttentionCoordinator:
    def test_balanced(self):
        ac = AttentionCoordinator()
        from asi_build.cognitive_synergy.pattern_reasoning.pattern_reasoning_synergy import SynergyMetrics as PRSynergyMetrics
        result = ac.coordinate(
            {"activation_level": 0.5},
            {"activation_level": 0.5},
            PRSynergyMetrics()
        )
        assert not result["focus_on_patterns"]
        assert not result["focus_on_reasoning"]

    def test_pattern_dominant(self):
        ac = AttentionCoordinator()
        from asi_build.cognitive_synergy.pattern_reasoning.pattern_reasoning_synergy import SynergyMetrics as PRSynergyMetrics
        result = ac.coordinate(
            {"activation_level": 0.9},
            {"activation_level": 0.3},
            PRSynergyMetrics()
        )
        assert result["focus_on_reasoning"] is True

    def test_high_synergy_both_focus(self):
        ac = AttentionCoordinator()
        from asi_build.cognitive_synergy.pattern_reasoning.pattern_reasoning_synergy import SynergyMetrics as PRSynergyMetrics
        metrics = PRSynergyMetrics(synergy_strength=0.9)
        result = ac.coordinate(
            {"activation_level": 0.5},
            {"activation_level": 0.5},
            metrics
        )
        assert result["focus_on_patterns"] is True
        assert result["focus_on_reasoning"] is True


class TestCrossValidationEngine:
    def test_empty(self):
        cve = CrossValidationEngine()
        assert cve.validate({}, {}, {}) == []

    def test_validate_pattern_inference(self):
        cve = CrossValidationEngine()
        p = Pattern(id="p1", type="causal", content="rain causes wet ground",
                   confidence=0.9, support=5, frequency=0.5, complexity=0.1)
        inf = Inference(id="i1", premises=["p1"], conclusion="wet ground after rain",
                       inference_type=ReasoningType.ABDUCTIVE, confidence=0.9)
        strength = cve._validate_pattern_inference(p, inf)
        assert strength > 0.0

    def test_validate_pattern_hypothesis(self):
        cve = CrossValidationEngine()
        p = Pattern(id="p1", type="causal", content="rain causes wet ground",
                   confidence=0.9, support=5, frequency=0.5, complexity=0.1)
        h = Hypothesis(id="h1", content="rain causes wet ground",
                      reasoning_type=ReasoningType.ABDUCTIVE, confidence=0.9)
        strength = cve._validate_pattern_hypothesis(p, h)
        assert strength > 0.5


class TestPatternReasoningSynergy:
    def _make_synergy(self, **kwargs):
        return PatternReasoningSynergy(**kwargs)

    def test_constructor(self):
        prs = self._make_synergy()
        assert prs.pattern_engine is not None
        assert prs.reasoning_engine is not None
        assert prs.integration_threshold == 0.7

    def test_process_external_input(self):
        prs = self._make_synergy()
        prs.process_external_input({
            "type": "sequence",
            "data": "test data",
            "confidence": 0.8
        })
        # Should create synergy event
        assert len(prs.synergy_events) == 1

    def test_get_synergy_state(self):
        prs = self._make_synergy()
        state = prs.get_synergy_state()
        assert "metrics" in state
        assert "pattern_engine_state" in state
        assert "reasoning_engine_state" in state
        assert "performance_summary" in state

    def test_pattern_to_knowledge_content(self):
        prs = self._make_synergy()
        p = Pattern(id="p1", type="causal", content={"cause": "rain", "effect": "wet"},
                   confidence=0.9, support=5, frequency=0.5, complexity=0.1)
        content = prs._pattern_to_knowledge_content(p)
        assert "Causal" in content

    def test_pattern_to_knowledge_content_types(self):
        prs = self._make_synergy()
        for ptype, expected in [("sequence", "Sequential"), ("temporal", "Temporal"),
                                ("spatial", "Spatial"), ("structural", "Structural"),
                                ("other", "other")]:
            p = Pattern(id="p", type=ptype, content="x", confidence=0.9,
                       support=5, frequency=0.5, complexity=0.1)
            content = prs._pattern_to_knowledge_content(p)
            assert expected in content

    def test_update_flow_metrics(self):
        prs = self._make_synergy()
        prs.pattern_to_reasoning_buffer.append({"timestamp": time.time(), "transferred": True})
        prs._update_flow_metrics()
        assert prs.metrics.pattern_to_reasoning_transfer > 0.0

    def test_start_stop(self):
        prs = self._make_synergy()
        prs.start()
        assert prs._running
        time.sleep(0.05)
        prs.stop()
        assert not prs._running


# ═══════════════════════════════════════════════════════════════════════════
# 8. Perception & Action Engines
# ═══════════════════════════════════════════════════════════════════════════

class TestPerceptionEngine:
    def test_constructor(self):
        pe = PerceptionEngine()
        assert pe.state["activation_level"] == 0.0

    def test_process_input(self):
        pe = PerceptionEngine()
        result = pe.process_input("visual", np.array([0.5, 0.3, 0.8]))
        assert result["modality"] == "visual"
        assert result["confidence"] > 0.0
        assert pe.state["activation_level"] > 0.0

    def test_process_input_empty(self):
        pe = PerceptionEngine()
        result = pe.process_input("audio", np.array([]))
        assert result["confidence"] == 0.0

    def test_get_state(self):
        pe = PerceptionEngine()
        state = pe.get_state()
        assert "activation_level" in state


class TestActionEngine:
    def test_constructor(self):
        ae = ActionEngine()
        assert ae.state["activation_level"] == 0.0

    def test_execute_action(self):
        ae = ActionEngine()
        result = ae.execute_action("motor", np.array([1.0, 0.5]))
        assert result["modality"] == "motor"
        assert result["success_probability"] > 0.0

    def test_execute_action_empty(self):
        ae = ActionEngine()
        result = ae.execute_action("motor", np.array([]))
        assert result["success_probability"] == 0.0

    def test_get_state(self):
        ae = ActionEngine()
        state = ae.get_state()
        assert "activation_level" in state


# ═══════════════════════════════════════════════════════════════════════════
# 9. Sensorimotor Synergy
# ═══════════════════════════════════════════════════════════════════════════

class TestForwardModel:
    def test_predict(self):
        fm = ForwardModel("visual", "motor")
        action = np.array([1.0, 0.5, 0.3])
        prediction = fm.predict(action)
        assert prediction.shape == (10,)

    def test_predict_long_input(self):
        fm = ForwardModel("visual", "motor")
        action = np.ones(20)
        prediction = fm.predict(action)
        assert prediction.shape == (10,)

    def test_predict_change(self):
        fm = ForwardModel("visual", "motor")
        current = np.array([0.5, 0.3])
        action = np.array([1.0])
        change = fm.predict_change(current, action)
        assert len(change) == 2

    def test_adapt(self):
        fm = ForwardModel("visual", "motor")
        original_weights = fm.weights.copy()
        fm.adapt(0.5, 0.01)
        # Weights should have changed
        assert not np.allclose(fm.weights, original_weights)


class TestInverseModel:
    def test_predict(self):
        im = InverseModel("motor", "visual")
        perception = np.array([0.5, 0.3])
        action = im.predict(perception)
        assert action.shape == (10,)

    def test_generate_exploratory_actions(self):
        im = InverseModel("motor", "visual")
        np.random.seed(42)
        actions = im.generate_exploratory_actions(np.array([0.5, 0.3]), uncertainty=0.5)
        assert len(actions) == 3
        for a in actions:
            assert a.shape == (10,)

    def test_adapt(self):
        im = InverseModel("motor", "visual")
        original = im.weights.copy()
        im.adapt(0.5, 0.01)
        assert not np.allclose(im.weights, original)


class TestSensorimotorSynergy:
    def _make_synergy(self, **kwargs):
        return SensorimotorSynergy(**kwargs)

    def test_constructor(self):
        ss = self._make_synergy()
        assert ss.coupling_threshold == 0.6
        assert len(ss.sensorimotor_loops) == 0

    def test_add_loop(self):
        ss = self._make_synergy()
        loop = ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        assert isinstance(loop, SensorimotorLoop)
        assert "vis_motor" in ss.sensorimotor_loops
        assert "vis_motor" in ss.forward_models
        assert "vis_motor" in ss.inverse_models

    def test_process_perception(self):
        ss = self._make_synergy()
        ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        result = ss.process_perception("visual", np.array([0.5, 0.3]))
        assert "processed_perception" in result
        assert "predictions" in result
        assert len(ss.perception_history) == 1

    def test_process_action(self):
        ss = self._make_synergy()
        ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        result = ss.process_action("motor", np.array([1.0, 0.5]))
        assert "processed_action" in result
        assert "sensory_predictions" in result
        assert len(ss.action_history) == 1

    def test_process_perception_irrelevant_modality(self):
        ss = self._make_synergy()
        ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        result = ss.process_perception("audio", np.array([0.5]))
        # No loop for audio → no loop_responses
        assert result["loop_responses"] == {}

    def test_get_synergy_state(self):
        ss = self._make_synergy()
        ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        state = ss.get_synergy_state()
        assert "sensorimotor_loops" in state
        assert "vis_motor" in state["sensorimotor_loops"]
        assert "average_coupling_strength" in state

    def test_perception_then_action_coupling(self):
        """Process perception then action to test loop updates."""
        ss = self._make_synergy()
        ss.add_sensorimotor_loop("vis_motor", "visual", "motor")

        # Process perception
        ss.process_perception("visual", np.array([0.5, 0.3, 0.1]))

        # Process action (creates prediction)
        ss.process_action("motor", np.array([1.0, 0.5, 0.3]))

        # Predictions should have been generated
        assert len(ss.predictions) >= 1

    def test_generate_active_perception_actions_low_confidence(self):
        ss = self._make_synergy()
        loop = ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        perception = PerceptionState(
            modality="visual", features=np.array([0.5]), confidence=0.3, timestamp=time.time()
        )
        actions = ss._generate_active_perception_actions(loop, perception)
        assert len(actions) > 0
        assert actions[0]["type"] == "exploratory"

    def test_generate_active_perception_actions_high_confidence(self):
        ss = self._make_synergy()
        loop = ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        perception = PerceptionState(
            modality="visual", features=np.array([0.5]), confidence=0.9, timestamp=time.time()
        )
        actions = ss._generate_active_perception_actions(loop, perception)
        # High confidence → no exploratory actions
        assert len(actions) == 0

    def test_adapt_sensorimotor_loop_no_errors(self):
        ss = self._make_synergy()
        loop = ss.add_sensorimotor_loop("vis_motor", "visual", "motor")
        # No errors → should not crash
        ss._adapt_sensorimotor_loop(loop)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Module-level __init__ imports
# ═══════════════════════════════════════════════════════════════════════════

class TestModuleExports:
    """Verify __all__ exports are importable."""

    def test_all_exports(self):
        from asi_build import cognitive_synergy
        for name in cognitive_synergy.__all__:
            assert hasattr(cognitive_synergy, name), f"Missing export: {name}"

    def test_version(self):
        from asi_build.cognitive_synergy import __version__
        assert __version__ == "2.0.0"


# ═══════════════════════════════════════════════════════════════════════════
# 11. Integration / Smoke Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegrationSmoke:
    """End-to-end sanity without background threads."""

    def test_primus_add_get_state(self):
        """Full flow: add primitives → get state. compute_synergy skipped
        due to pre-existing np.corrcoef scalar bug."""
        p = PRIMUSFoundation()
        p.add_primitive(CognitivePrimitive(name="a", type="pattern", content="hello world", activation=0.9))
        p.add_primitive(CognitivePrimitive(name="b", type="concept", content="hello there", activation=0.8))
        state = p.get_system_state()
        assert isinstance(state, PRIMUSState)
        assert state.self_organization_metrics["primitives_count"] == 2

    def test_reasoning_add_reason_query(self):
        re = ReasoningEngine()
        re.add_knowledge("birds can fly", knowledge_type="fact", confidence=0.9)
        re.add_knowledge("birds have wings implies birds can fly",
                        knowledge_type="rule", confidence=0.9)
        re.reason()
        results = re.query_knowledge("birds fly")
        assert len(results) >= 1

    def test_pattern_mine_flow(self):
        pe = PatternMiningEngine(min_support=2, min_confidence=0.3)
        for _ in range(5):
            pe.process_input({"type": "temporal", "data": 1.0, "timestamp": time.time()})
        patterns = pe.mine_patterns()
        state = pe.get_state()
        assert "mining_stats" in state

    def test_sensorimotor_loop_cycle(self):
        ss = SensorimotorSynergy()
        loop = ss.add_sensorimotor_loop("test", "visual", "motor")
        ss.process_perception("visual", np.array([0.5, 0.3]))
        ss.process_action("motor", np.array([1.0]))
        state = ss.get_synergy_state()
        assert "sensorimotor_loops" in state

    def test_emergence_detection_pipeline(self):
        epd = EmergentPropertyDetector(emergence_threshold=0.5)
        state = {
            "global_coherence": 0.95,
            "synergy_pairs": {"pattern_reasoning": {"synergy_strength": 0.95}},
            "integration_matrix": np.eye(3).tolist(),
        }
        props = epd.detect_emergence(state)
        summary = epd.get_emergence_summary()
        assert "total_properties" in summary
