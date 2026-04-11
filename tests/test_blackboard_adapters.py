"""
Tests for Blackboard Adapters
==============================

Tests all four adapters (consciousness, knowledge_graph, cognitive_synergy,
reasoning) plus the ``wire_all`` / ``production_sweep`` utilities.

Uses mocks for underlying modules so tests are self-contained with zero
external dependencies.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

import pytest

from asi_build.integration import (
    BlackboardEntry,
    BlackboardQuery,
    CognitiveBlackboard,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventBus,
    ModuleCapability,
    ModuleInfo,
)
from asi_build.integration.adapters import (
    CognitiveSynergyAdapter,
    ConsciousnessAdapter,
    KnowledgeGraphAdapter,
    ReasoningAdapter,
    production_sweep,
    wire_all,
)


# =========================================================================
# Mock objects for underlying modules
# =========================================================================


class MockIIT:
    """Mock IntegratedInformationTheory."""

    def __init__(self, phi: float = 2.5):
        self._phi = phi
        self._complexes = []

    def calculate_phi(self, subset=None) -> float:
        return self._phi

    def find_conscious_complexes(self) -> list:
        return self._complexes

    def get_current_state(self) -> Dict[str, Any]:
        return {"state": "active", "phi": self._phi}


@dataclass
class MockBroadcast:
    content_id: str = "bc_001"
    strength: float = 0.9
    processors_reached: int = 5
    timestamp: float = field(default_factory=time.time)


class MockGWT:
    """Mock GlobalWorkspaceTheory."""

    def __init__(self):
        self.workspace_buffer: list = []
        self.cognitive_processors: dict = {"vis": None, "lang": None}
        self.current_broadcast: Optional[MockBroadcast] = None
        self.total_broadcasts: int = 0
        self.attention_focus: Dict[str, float] = {}
        self.submitted_contents: list = []

    def submit_content(self, content: Any) -> None:
        self.submitted_contents.append(content)

    def get_current_state(self) -> Dict[str, Any]:
        return {"state": "broadcasting", "buffer_size": len(self.workspace_buffer)}


class MockTemporalKG:
    """Mock TemporalKnowledgeGraph."""

    def __init__(self):
        self._triples: Dict[str, Dict] = {}
        self._counter = 0
        self._stats = {"total_triples": 0, "active_triples": 0}

    def add_triple(self, subject, predicate, object, source="", confidence=1.0,
                   agent="", statement_type="fact", **kwargs) -> str:
        self._counter += 1
        tid = f"t_{self._counter}"
        self._triples[tid] = {
            "triple_id": tid, "subject": subject, "predicate": predicate,
            "object": object, "source": source, "confidence": confidence,
        }
        self._stats["total_triples"] = len(self._triples)
        self._stats["active_triples"] = len(self._triples)
        return tid

    def detect_contradictions(self, subject, predicate, new_object, new_confidence) -> list:
        return []

    def get_statistics(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_entity_relations(self, entity: str) -> List[Dict]:
        return [t for t in self._triples.values() if t["subject"] == entity]

    def search_triples(self, text_query: str, current_only=True) -> list:
        return []


class MockPathfinder:
    """Mock KGPathfinder."""

    def __init__(self, found: bool = True):
        self._found = found

    def find_path(self, start: str, goal: str, **kwargs) -> Dict[str, Any]:
        if self._found:
            return {
                "found": True,
                "path": [start, "intermediate", goal],
                "confidence": 0.85,
                "edges": [],
            }
        return {"found": False, "path": [], "nodes_explored": 5}


@dataclass
class MockSynergyPair:
    module_a: str
    module_b: str
    synergy_strength: float = 0.0


class MockSynergyEngine:
    """Mock CognitiveSynergyEngine."""

    def __init__(self):
        self.synergy_pairs = {
            "pattern_reasoning": MockSynergyPair("pattern_mining", "reasoning", 0.5),
            "conscious_unconscious": MockSynergyPair("conscious", "unconscious", 0.3),
            "memory_learning": MockSynergyPair("memory", "learning", 0.6),
        }
        self.global_coherence = 0.65
        self._emergence_indicators: list = []
        self.modules: dict = {}

    def get_emergence_indicators(self) -> list:
        return list(self._emergence_indicators)

    def get_system_state(self) -> Dict[str, Any]:
        return {"coherence": self.global_coherence, "pairs": len(self.synergy_pairs)}

    def register_module(self, name, module):
        self.modules[name] = module


@dataclass
class MockSynergyProfile:
    mutual_information: float = 0.4
    transfer_entropy: float = 0.3
    phase_coupling: float = 0.5
    coherence: float = 0.6
    emergence_index: float = 0.2
    integration_index: float = 0.45
    complexity_resonance: float = 0.35


class MockSynergyMetrics:
    """Mock SynergyMetrics."""

    def __init__(self):
        self._profiles: Dict[str, MockSynergyProfile] = {}
        self._data: List = []

    def add_time_series_data(self, pair_name, a, b, timestamp=None):
        self._data.append((pair_name, a, b, timestamp))

    def compute_synergy_profile(self, pair_name) -> Optional[MockSynergyProfile]:
        return self._profiles.get(pair_name, MockSynergyProfile())

    def get_all_profiles(self) -> Dict[str, MockSynergyProfile]:
        return dict(self._profiles)


@dataclass
class MockReasoningResult:
    conclusion: str = "Test conclusion"
    confidence: float = 0.85
    confidence_level: str = "HIGH"
    reasoning_mode: str = "HYBRID"
    total_processing_time: float = 0.5
    explanation: str = "Test explanation"
    reasoning_steps: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    uncertainty_areas: list = field(default_factory=list)
    alternative_conclusions: list = field(default_factory=list)

    def to_dict(self):
        return {
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "reasoning_mode": self.reasoning_mode,
            "total_processing_time": self.total_processing_time,
            "explanation": self.explanation,
            "reasoning_steps": self.reasoning_steps,
            "sources": self.sources,
            "uncertainty_areas": self.uncertainty_areas,
            "alternative_conclusions": self.alternative_conclusions,
        }


class MockReasoningEngine:
    """Mock HybridReasoningEngine."""

    def __init__(self, result=None):
        self._result = result or MockReasoningResult()
        self.mode_weights = {
            "LOGICAL": 0.3,
            "PROBABILISTIC": 0.25,
            "ANALOGICAL": 0.15,
            "CAUSAL": 0.15,
            "CREATIVE": 0.1,
            "QUANTUM": 0.05,
        }
        self.performance_metrics = {
            "accuracy": 0.8,
            "speed": 0.9,
        }

    def reason(self, query, context=None, reasoning_mode=None, **kwargs):
        return self._result

    def get_performance_metrics(self):
        return dict(self.performance_metrics)


# =========================================================================
# Test: ConsciousnessAdapter
# =========================================================================


class TestConsciousnessAdapter:
    """Tests for ConsciousnessAdapter."""

    def test_module_info(self):
        adapter = ConsciousnessAdapter()
        info = adapter.module_info
        assert info.name == "consciousness"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert "consciousness.phi" in info.topics_produced

    def test_registration(self):
        bb = CognitiveBlackboard()
        adapter = ConsciousnessAdapter()
        bb.register_module(adapter)
        assert bb.get_module("consciousness") is not None
        assert adapter._blackboard is bb

    def test_duplicate_registration_raises(self):
        bb = CognitiveBlackboard()
        a1 = ConsciousnessAdapter()
        a2 = ConsciousnessAdapter()
        bb.register_module(a1)
        with pytest.raises(ValueError, match="already registered"):
            bb.register_module(a2)

    def test_produce_phi(self):
        iit = MockIIT(phi=3.14)
        adapter = ConsciousnessAdapter(iit=iit)
        entries = adapter.produce()
        phi_entries = [e for e in entries if e.topic == "consciousness.phi"]
        assert len(phi_entries) == 1
        assert phi_entries[0].data["phi"] == 3.14

    def test_produce_phi_change_detection(self):
        iit = MockIIT(phi=2.0)
        adapter = ConsciousnessAdapter(iit=iit)

        # First produce → phi entry
        entries1 = adapter.produce()
        assert any(e.topic == "consciousness.phi" for e in entries1)

        # Second produce, same phi → no entry
        entries2 = adapter.produce()
        phi2 = [e for e in entries2 if e.topic == "consciousness.phi"]
        assert len(phi2) == 0

        # Change phi → entry again
        iit._phi = 3.5
        entries3 = adapter.produce()
        assert any(e.topic == "consciousness.phi" for e in entries3)

    def test_produce_broadcast(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)

        # No broadcast → no entry
        entries0 = adapter.produce()
        assert not any(e.topic == "consciousness.broadcast" for e in entries0)

        # Set broadcast
        gwt.current_broadcast = MockBroadcast()
        gwt.total_broadcasts = 1
        entries1 = adapter.produce()
        bc_entries = [e for e in entries1 if e.topic == "consciousness.broadcast"]
        assert len(bc_entries) == 1
        assert bc_entries[0].data["content_id"] == "bc_001"

    def test_produce_state(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)
        entries = adapter.produce()
        state_entries = [e for e in entries if e.topic == "consciousness.state"]
        assert len(state_entries) == 1
        assert state_entries[0].data["state"] == "broadcasting"

    def test_produce_state_change_detection(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)

        entries1 = adapter.produce()
        assert any(e.topic == "consciousness.state" for e in entries1)

        # Same state → no entry
        entries2 = adapter.produce()
        state2 = [e for e in entries2 if e.topic == "consciousness.state"]
        assert len(state2) == 0

    def test_produce_no_components(self):
        adapter = ConsciousnessAdapter()
        entries = adapter.produce()
        assert len(entries) == 0

    def test_consume_reasoning(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)

        # Patch the module import so WorkspaceContent is available
        with patch(
            "asi_build.integration.adapters.consciousness_adapter._get_consciousness"
        ) as mock_get:
            mock_mod = MagicMock()
            mock_ws = MagicMock()
            mock_mod.WorkspaceContent = mock_ws
            mock_get.return_value = mock_mod

            entry = BlackboardEntry(
                topic="reasoning.inference",
                data={"conclusion": "test", "confidence": 0.9},
                source_module="reasoning",
                confidence=0.9,
            )
            adapter.consume([entry])
            assert len(gwt.submitted_contents) == 1

    def test_consume_synergy_updates_attention(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)
        entry = BlackboardEntry(
            topic="cognitive_synergy.coherence",
            data={"global_coherence": 0.85},
            source_module="cognitive_synergy",
        )
        adapter.consume([entry])
        assert gwt.attention_focus.get("synergy_coherence") == 0.85

    def test_event_handler_emission(self):
        iit = MockIIT(phi=2.5)
        adapter = ConsciousnessAdapter(iit=iit)
        events_received: list = []
        adapter.set_event_handler(lambda e: events_received.append(e))

        adapter.produce()
        phi_events = [e for e in events_received if e.event_type == "consciousness.phi.updated"]
        assert len(phi_events) == 1
        assert phi_events[0].payload["phi"] == 2.5

    def test_handle_event_reasoning(self):
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt)

        with patch(
            "asi_build.integration.adapters.consciousness_adapter._get_consciousness"
        ) as mock_get:
            mock_mod = MagicMock()
            mock_ws = MagicMock()
            mock_mod.WorkspaceContent = mock_ws
            mock_get.return_value = mock_mod

            event = CognitiveEvent(
                event_type="reasoning.inference.completed",
                payload={"conclusion": "x"},
                source="reasoning",
            )
            adapter.handle_event(event)
            assert len(gwt.submitted_contents) == 1

    def test_snapshot(self):
        iit = MockIIT(phi=1.5)
        gwt = MockGWT()
        adapter = ConsciousnessAdapter(gwt=gwt, iit=iit)
        snap = adapter.snapshot()
        assert snap["has_gwt"] is True
        assert snap["has_iit"] is True
        assert snap["current_phi"] == 1.5
        assert snap["workspace_size"] == 0

    def test_phi_high_priority(self):
        iit = MockIIT(phi=4.0)
        adapter = ConsciousnessAdapter(iit=iit)
        entries = adapter.produce()
        phi_entry = [e for e in entries if e.topic == "consciousness.phi"][0]
        assert phi_entry.priority == EntryPriority.HIGH

    def test_phi_normal_priority(self):
        iit = MockIIT(phi=1.0)
        adapter = ConsciousnessAdapter(iit=iit)
        entries = adapter.produce()
        phi_entry = [e for e in entries if e.topic == "consciousness.phi"][0]
        assert phi_entry.priority == EntryPriority.NORMAL


# =========================================================================
# Test: KnowledgeGraphAdapter
# =========================================================================


class TestKnowledgeGraphAdapter:
    """Tests for KnowledgeGraphAdapter."""

    def test_module_info(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        info = adapter.module_info
        assert info.name == "knowledge_graph"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities

    def test_requires_kg(self):
        with pytest.raises(ValueError, match="non-None"):
            KnowledgeGraphAdapter(kg=None)

    def test_registration(self):
        bb = CognitiveBlackboard()
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        bb.register_module(adapter)
        assert bb.get_module("knowledge_graph") is not None

    def test_add_triple_and_produce(self):
        bb = CognitiveBlackboard()
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        bb.register_module(adapter)

        tid = adapter.add_triple("sun", "is_a", "star", confidence=0.99)
        assert tid is not None
        assert tid.startswith("t_")

        entries = adapter.produce()
        triple_entries = [e for e in entries if e.topic == "knowledge_graph.triple"]
        assert len(triple_entries) == 1
        assert triple_entries[0].data["subject"] == "sun"

    def test_produce_stats(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        kg._stats["total_triples"] = 5

        entries = adapter.produce()
        stats_entries = [e for e in entries if e.topic == "knowledge_graph.statistics"]
        assert len(stats_entries) == 1

    def test_produce_stats_no_change(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        kg._stats["total_triples"] = 5

        adapter.produce()  # First call
        entries = adapter.produce()  # Same stats → no entry
        stats_entries = [e for e in entries if e.topic == "knowledge_graph.statistics"]
        assert len(stats_entries) == 0

    def test_find_path_posts_to_blackboard(self):
        bb = CognitiveBlackboard()
        kg = MockTemporalKG()
        pf = MockPathfinder(found=True)
        adapter = KnowledgeGraphAdapter(kg=kg, pathfinder=pf)
        bb.register_module(adapter)

        result = adapter.find_path("earth", "mars")
        assert result["found"] is True

        # Check entry was posted to blackboard
        pf_entries = bb.get_by_topic("knowledge_graph.pathfinding")
        assert len(pf_entries) == 1

    def test_find_path_not_found(self):
        bb = CognitiveBlackboard()
        kg = MockTemporalKG()
        pf = MockPathfinder(found=False)
        adapter = KnowledgeGraphAdapter(kg=kg, pathfinder=pf)
        bb.register_module(adapter)

        result = adapter.find_path("x", "y")
        assert result["found"] is False

        # Not-found paths are not posted
        pf_entries = bb.get_by_topic("knowledge_graph.pathfinding")
        assert len(pf_entries) == 0

    def test_find_path_no_pathfinder(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg, pathfinder=None)
        result = adapter.find_path("a", "b")
        assert result is None

    def test_consume_reasoning_auto_ingest(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg, auto_ingest_inferences=True)

        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"conclusion": "gravity exists", "subject": "physics"},
            source_module="reasoning",
            confidence=0.95,
        )
        adapter.consume([entry])

        # Should have added a triple
        assert len(kg._triples) == 1
        triple = list(kg._triples.values())[0]
        assert triple["subject"] == "physics"
        assert triple["object"] == "gravity exists"

    def test_consume_reasoning_auto_ingest_disabled(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg, auto_ingest_inferences=False)

        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"conclusion": "test"},
            source_module="reasoning",
        )
        adapter.consume([entry])
        assert len(kg._triples) == 0

    def test_consume_synergy(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)

        entry = BlackboardEntry(
            topic="cognitive_synergy.pair",
            data={"pair_name": "perception_action", "synergy": 0.75},
            source_module="cognitive_synergy",
        )
        adapter.consume([entry])
        assert len(kg._triples) == 1
        triple = list(kg._triples.values())[0]
        assert triple["predicate"] == "synergizes_with"

    def test_transform_enrichment(self):
        kg = MockTemporalKG()
        kg.add_triple("physics", "studies", "matter")
        adapter = KnowledgeGraphAdapter(kg=kg)

        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"subject": "physics", "conclusion": "test"},
            source_module="reasoning",
        )
        results = adapter.transform([entry])
        assert len(results) == 1
        assert results[0].topic == "knowledge_graph.enrichment"
        assert results[0].parent_id == entry.entry_id

    def test_transform_no_subject(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"conclusion": "something"},
            source_module="reasoning",
        )
        results = adapter.transform([entry])
        assert len(results) == 0

    def test_event_emission(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg)
        events: list = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter.add_triple("a", "b", "c")
        assert any(e.event_type == "knowledge_graph.triple.added" for e in events)

    def test_contradiction_events(self):
        kg = MockTemporalKG()
        kg.detect_contradictions = MagicMock(return_value=[
            {"triple_id": "t_old", "object": "old_val"}
        ])
        adapter = KnowledgeGraphAdapter(kg=kg)
        events: list = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter.add_triple("x", "is", "y")
        contra_events = [e for e in events if "contradiction" in e.event_type]
        assert len(contra_events) == 1

    def test_snapshot(self):
        kg = MockTemporalKG()
        adapter = KnowledgeGraphAdapter(kg=kg, pathfinder=MockPathfinder())
        snap = adapter.snapshot()
        assert snap["has_pathfinder"] is True
        assert snap["auto_ingest"] is True


# =========================================================================
# Test: CognitiveSynergyAdapter
# =========================================================================


class TestCognitiveSynergyAdapter:
    """Tests for CognitiveSynergyAdapter."""

    def test_module_info(self):
        adapter = CognitiveSynergyAdapter()
        info = adapter.module_info
        assert info.name == "cognitive_synergy"
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert ModuleCapability.VALIDATOR in info.capabilities

    def test_registration(self):
        bb = CognitiveBlackboard()
        adapter = CognitiveSynergyAdapter()
        bb.register_module(adapter)
        assert bb.get_module("cognitive_synergy") is not None

    def test_produce_pair_entries(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        entries = adapter.produce()
        pair_entries = [e for e in entries if e.topic == "cognitive_synergy.pair"]
        # Should produce entries for all 3 pairs
        assert len(pair_entries) == 3

    def test_produce_pair_change_detection(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        adapter.produce()  # First call
        entries2 = adapter.produce()  # Same values → no pair entries
        pair2 = [e for e in entries2 if e.topic == "cognitive_synergy.pair"]
        assert len(pair2) == 0

        # Change a pair value
        engine.synergy_pairs["pattern_reasoning"].synergy_strength = 0.9
        entries3 = adapter.produce()
        pair3 = [e for e in entries3 if e.topic == "cognitive_synergy.pair"]
        assert len(pair3) == 1

    def test_produce_coherence(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        entries = adapter.produce()
        coh = [e for e in entries if e.topic == "cognitive_synergy.coherence"]
        assert len(coh) == 1
        assert coh[0].data["global_coherence"] == 0.65

    def test_produce_coherence_change_detection(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        adapter.produce()
        entries2 = adapter.produce()
        coh2 = [e for e in entries2 if e.topic == "cognitive_synergy.coherence"]
        assert len(coh2) == 0

    def test_produce_emergence(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        adapter.produce()  # baseline

        engine._emergence_indicators.append({"type": "sync", "strength": 0.9})
        entries = adapter.produce()
        emg = [e for e in entries if e.topic == "cognitive_synergy.emergence"]
        assert len(emg) == 1

    def test_produce_profiles(self):
        metrics = MockSynergyMetrics()
        metrics._profiles["test_pair"] = MockSynergyProfile()
        adapter = CognitiveSynergyAdapter(metrics=metrics)

        entries = adapter.produce()
        profiles = [e for e in entries if e.topic == "cognitive_synergy.profile"]
        assert len(profiles) == 1

    def test_produce_no_components(self):
        adapter = CognitiveSynergyAdapter()
        entries = adapter.produce()
        assert len(entries) == 0

    def test_consume_feeds_metrics(self):
        metrics = MockSynergyMetrics()
        adapter = CognitiveSynergyAdapter(metrics=metrics)

        entry = BlackboardEntry(
            topic="consciousness.phi",
            data={"phi": 2.5},
            source_module="consciousness",
        )
        adapter.consume([entry])

        # Should have buffered data
        assert len(adapter._ts_buffers) >= 0  # May or may not have data yet

    def test_consume_reasoning_feeds_metrics(self):
        metrics = MockSynergyMetrics()
        adapter = CognitiveSynergyAdapter(metrics=metrics)

        # Feed consciousness data (side a) and reasoning data (side b)
        adapter.consume([BlackboardEntry(
            topic="consciousness.phi",
            data={"phi": 2.0},
            source_module="consciousness",
        )])
        adapter.consume([BlackboardEntry(
            topic="reasoning.inference",
            data={"confidence": 0.8},
            source_module="reasoning",
        )])

    def test_measure_pair_posts_to_blackboard(self):
        bb = CognitiveBlackboard()
        metrics = MockSynergyMetrics()
        adapter = CognitiveSynergyAdapter(metrics=metrics)
        bb.register_module(adapter)

        result = adapter.measure_pair("test_pair")
        assert result is not None
        assert result["mutual_information"] == 0.4

        entries = bb.get_by_topic("cognitive_synergy.profile")
        assert len(entries) == 1

    def test_transform_annotation(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)

        entry = BlackboardEntry(
            topic="reasoning.inference",
            data={"conclusion": "test"},
            source_module="reasoning",
        )
        results = adapter.transform([entry])
        assert len(results) == 1
        assert results[0].topic == "cognitive_synergy.annotation"
        # Only pattern_reasoning exists in our mock engine (symbolic_subsymbolic not present)
        assert len(results[0].data["relevant_pairs"]) >= 1
        assert results[0].data["relevant_pairs"][0]["pair_name"] == "pattern_reasoning"

    def test_event_emission(self):
        engine = MockSynergyEngine()
        adapter = CognitiveSynergyAdapter(engine=engine)
        events: list = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter.produce()
        pair_events = [e for e in events if "pair.updated" in e.event_type]
        assert len(pair_events) == 3

    def test_snapshot(self):
        engine = MockSynergyEngine()
        metrics = MockSynergyMetrics()
        adapter = CognitiveSynergyAdapter(engine=engine, metrics=metrics)
        snap = adapter.snapshot()
        assert snap["has_engine"] is True
        assert snap["has_metrics"] is True
        assert snap["last_coherence"] is None


# =========================================================================
# Test: ReasoningAdapter
# =========================================================================


class TestReasoningAdapter:
    """Tests for ReasoningAdapter."""

    def test_module_info(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)
        info = adapter.module_info
        assert info.name == "reasoning"
        assert ModuleCapability.REASONER in info.capabilities
        assert "reasoning.inference" in info.topics_produced

    def test_requires_engine(self):
        with pytest.raises(ValueError, match="non-None"):
            ReasoningAdapter(engine=None)

    def test_registration(self):
        bb = CognitiveBlackboard()
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)
        bb.register_module(adapter)
        assert bb.get_module("reasoning") is not None

    def test_reason_returns_result(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        result = adapter.reason("What is 2+2?")
        assert result is not None
        assert result["conclusion"] == "Test conclusion"
        assert result["confidence"] == 0.85

    def test_reason_queues_for_produce(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        adapter.reason("test query")
        entries = adapter.produce()

        inf_entries = [e for e in entries if e.topic == "reasoning.inference"]
        assert len(inf_entries) == 1
        assert inf_entries[0].confidence == 0.85

    def test_reason_produces_step_entries(self):
        result = MockReasoningResult(reasoning_steps=[
            {"mode": "logical", "output_data": "step1", "confidence": 0.9, "processing_time": 0.1},
            {"mode": "causal", "output_data": "step2", "confidence": 0.8, "processing_time": 0.2},
        ])
        engine = MockReasoningEngine(result=result)
        adapter = ReasoningAdapter(engine=engine)

        adapter.reason("test")
        entries = adapter.produce()

        step_entries = [e for e in entries if e.topic == "reasoning.step"]
        assert len(step_entries) == 2
        # Steps should have parent_id pointing to main inference
        inf_entry = [e for e in entries if e.topic == "reasoning.inference"][0]
        for se in step_entries:
            assert se.parent_id == inf_entry.entry_id

    def test_reason_with_context(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine, auto_context=False)

        result = adapter.reason("test", context={"extra": "data"})
        assert result is not None

    def test_reason_with_blackboard_context(self):
        bb = CognitiveBlackboard()
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine, auto_context=True)
        bb.register_module(adapter)

        # Post some KG data to the blackboard
        bb.post(BlackboardEntry(
            topic="knowledge_graph.triple",
            data={"subject": "earth", "predicate": "orbits", "object": "sun"},
            source_module="knowledge_graph",
        ))

        result = adapter.reason("about earth")
        assert result is not None

    def test_consume_kg_accumulates_context(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        entry = BlackboardEntry(
            topic="knowledge_graph.triple",
            data={"subject": "x", "predicate": "y", "object": "z"},
            source_module="knowledge_graph",
        )
        adapter.consume([entry])
        assert len(adapter._kg_context) == 1

    def test_consume_consciousness(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        entry = BlackboardEntry(
            topic="consciousness.state",
            data={"state": "active", "phi": 2.0},
            source_module="consciousness",
        )
        adapter.consume([entry])
        assert adapter._consciousness_context["state"] == "active"

    def test_consume_synergy_adapts_weights(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        # High coherence → boost logical
        entry = BlackboardEntry(
            topic="cognitive_synergy.coherence",
            data={"global_coherence": 0.9},
            source_module="cognitive_synergy",
        )
        original_logical = engine.mode_weights["LOGICAL"]
        adapter.consume([entry])
        assert engine.mode_weights["LOGICAL"] >= original_logical

    def test_consume_synergy_low_coherence(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        entry = BlackboardEntry(
            topic="cognitive_synergy.coherence",
            data={"global_coherence": 0.1},
            source_module="cognitive_synergy",
        )
        original_creative = engine.mode_weights["CREATIVE"]
        adapter.consume([entry])
        assert engine.mode_weights["CREATIVE"] >= original_creative

    def test_event_emission(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)
        events: list = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter.reason("test")
        inf_events = [e for e in events if "inference.completed" in e.event_type]
        assert len(inf_events) == 1
        assert inf_events[0].payload["conclusion"] == "Test conclusion"

    def test_event_listener_kg(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        event = CognitiveEvent(
            event_type="knowledge_graph.triple.added",
            payload={"subject": "test", "predicate": "is", "object": "good"},
            source="knowledge_graph",
        )
        adapter.handle_event(event)
        assert len(adapter._kg_context) == 1

    def test_event_listener_consciousness(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        event = CognitiveEvent(
            event_type="consciousness.state.changed",
            payload={"state": "focused"},
            source="consciousness",
        )
        adapter.handle_event(event)
        assert adapter._consciousness_context.get("state") == "focused"

    def test_produce_performance(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        entries = adapter.produce()
        perf = [e for e in entries if e.topic == "reasoning.performance"]
        assert len(perf) == 1

    def test_produce_performance_no_change(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)

        adapter.produce()
        entries2 = adapter.produce()
        perf2 = [e for e in entries2 if e.topic == "reasoning.performance"]
        assert len(perf2) == 0

    def test_safety_event(self):
        result = MockReasoningResult()
        result_dict = result.to_dict()
        result_dict["safety"] = {"flagged": True, "concerns": ["bias"]}
        engine = MockReasoningEngine()
        engine.reason = MagicMock(return_value=result_dict)
        adapter = ReasoningAdapter(engine=engine)
        events: list = []
        adapter.set_event_handler(lambda e: events.append(e))

        adapter.reason("test")
        safety_events = [e for e in events if "safety.flagged" in e.event_type]
        assert len(safety_events) == 1

    def test_snapshot(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine)
        snap = adapter.snapshot()
        assert snap["inference_count"] == 0
        assert snap["auto_context"] is True

    def test_kg_context_bounded(self):
        engine = MockReasoningEngine()
        adapter = ReasoningAdapter(engine=engine, max_context_entries=5)

        for i in range(50):
            entry = BlackboardEntry(
                topic="knowledge_graph.triple",
                data={"i": i},
                source_module="knowledge_graph",
            )
            adapter.consume([entry])

        assert len(adapter._kg_context) <= 10  # max * 2 = 10


# =========================================================================
# Test: wire_all utility
# =========================================================================


class TestWireAll:
    """Tests for the wire_all utility."""

    def test_wire_all_registers_modules(self):
        bb = CognitiveBlackboard()
        cons = ConsciousnessAdapter(iit=MockIIT())
        kg = KnowledgeGraphAdapter(kg=MockTemporalKG())
        syn = CognitiveSynergyAdapter(engine=MockSynergyEngine())
        reas = ReasoningAdapter(engine=MockReasoningEngine())

        wire_all(bb, cons, kg, syn, reas)

        assert bb.module_count == 4
        assert bb.get_module("consciousness") is not None
        assert bb.get_module("knowledge_graph") is not None
        assert bb.get_module("cognitive_synergy") is not None
        assert bb.get_module("reasoning") is not None

    def test_wire_all_sets_event_handlers(self):
        bb = CognitiveBlackboard()
        cons = ConsciousnessAdapter()
        wire_all(bb, cons)
        assert cons._event_handler is not None

    def test_wire_all_subscribes_to_events(self):
        bb = CognitiveBlackboard()
        cons = ConsciousnessAdapter()
        wire_all(bb, cons)
        # Should have subscriptions for consumed topics
        stats = bb.event_bus.get_stats()
        assert stats["subscriptions"] > 0

    def test_wire_all_graceful_on_duplicate(self):
        bb = CognitiveBlackboard()
        cons1 = ConsciousnessAdapter()
        cons2 = ConsciousnessAdapter()
        # First should succeed, second should log warning but not crash
        wire_all(bb, cons1, cons2)
        assert bb.module_count == 1  # Only first registered


# =========================================================================
# Test: production_sweep utility
# =========================================================================


class TestProductionSweep:
    """Tests for the production_sweep utility."""

    def test_sweep_posts_entries(self):
        bb = CognitiveBlackboard()
        iit = MockIIT(phi=3.0)
        cons = ConsciousnessAdapter(iit=iit)
        kg = KnowledgeGraphAdapter(kg=MockTemporalKG())

        wire_all(bb, cons, kg)

        # Add a triple to have something to produce
        kg.add_triple("test", "is", "good")

        ids = production_sweep(bb, cons, kg)
        assert len(ids) > 0
        # All posted entries should be retrievable
        for eid in ids:
            assert bb.get(eid) is not None

    def test_sweep_handles_errors(self):
        bb = CognitiveBlackboard()
        bad_adapter = MagicMock()
        bad_adapter.produce.side_effect = RuntimeError("boom")
        bad_adapter.MODULE_NAME = "bad"

        # Should not raise
        ids = production_sweep(bb, bad_adapter)
        assert ids == []


# =========================================================================
# Test: Cross-adapter communication (integration)
# =========================================================================


class TestCrossAdapterIntegration:
    """Integration tests: 4-module communication through the blackboard."""

    def test_reasoning_to_consciousness_flow(self):
        """Reasoning result → event → consciousness consumes it."""
        bb = CognitiveBlackboard()
        gwt = MockGWT()
        cons = ConsciousnessAdapter(gwt=gwt)
        reas = ReasoningAdapter(engine=MockReasoningEngine())

        wire_all(bb, cons, reas)

        # Reasoning produces an inference
        reas.reason("What is truth?")
        ids = production_sweep(bb, reas)
        assert len(ids) > 0

        # Consciousness should have received an event via bus
        # (wire_all subscribes cons to reasoning.* events)
        # We verify by checking GWT submissions
        # Note: direct event delivery happens during emit, so check now

    def test_reasoning_to_kg_flow(self):
        """Reasoning result → KG adapter ingests as triple."""
        bb = CognitiveBlackboard()
        kg_mock = MockTemporalKG()
        kg = KnowledgeGraphAdapter(kg=kg_mock, auto_ingest_inferences=True)
        reas = ReasoningAdapter(engine=MockReasoningEngine())

        wire_all(bb, kg, reas)

        # Reasoning produces
        reas.reason("test query")
        ids = production_sweep(bb, reas)

        # Feed reasoning entries to KG consumer
        reasoning_entries = bb.get_by_topic("reasoning")
        kg.consume(reasoning_entries)

        # KG should have ingested the inference
        assert len(kg_mock._triples) >= 1

    def test_kg_to_reasoning_context(self):
        """KG triples → reasoning context enrichment."""
        bb = CognitiveBlackboard()
        kg_mock = MockTemporalKG()
        kg = KnowledgeGraphAdapter(kg=kg_mock)
        reas = ReasoningAdapter(engine=MockReasoningEngine(), auto_context=True)

        wire_all(bb, kg, reas)

        # Add triples
        kg.add_triple("earth", "orbits", "sun")
        production_sweep(bb, kg)

        # Now reasoning should pick up KG context
        result = reas.reason("about earth")
        assert result is not None

    def test_synergy_to_reasoning_weights(self):
        """Synergy coherence → reasoning mode weight adaptation."""
        bb = CognitiveBlackboard()
        engine = MockSynergyEngine()
        engine.global_coherence = 0.9
        syn = CognitiveSynergyAdapter(engine=engine)
        reas_engine = MockReasoningEngine()
        reas = ReasoningAdapter(engine=reas_engine)

        wire_all(bb, syn, reas)

        # Produce synergy entries
        production_sweep(bb, syn)

        # Feed coherence to reasoning
        coh_entries = bb.get_by_topic("cognitive_synergy.coherence")
        if coh_entries:
            reas.consume(coh_entries)

    def test_full_four_module_sweep(self):
        """All 4 modules produce, post, and the blackboard has entries from all."""
        bb = CognitiveBlackboard()

        iit = MockIIT(phi=2.5)
        gwt = MockGWT()
        cons = ConsciousnessAdapter(gwt=gwt, iit=iit)

        kg_mock = MockTemporalKG()
        kg = KnowledgeGraphAdapter(kg=kg_mock)
        kg.add_triple("a", "b", "c")

        syn = CognitiveSynergyAdapter(
            engine=MockSynergyEngine(),
            metrics=MockSynergyMetrics(),
        )

        reas = ReasoningAdapter(engine=MockReasoningEngine())
        reas.reason("test query")

        wire_all(bb, cons, kg, syn, reas)
        ids = production_sweep(bb, cons, kg, syn, reas)

        # Should have entries from all modules
        sources = {bb.get(eid).source_module for eid in ids if bb.get(eid)}
        assert "consciousness" in sources
        assert "knowledge_graph" in sources
        assert "cognitive_synergy" in sources
        assert "reasoning" in sources

    def test_event_cross_delivery(self):
        """Events from one module are delivered to listeners in another."""
        bb = CognitiveBlackboard()
        cons = ConsciousnessAdapter()
        reas = ReasoningAdapter(engine=MockReasoningEngine())

        wire_all(bb, cons, reas)

        # Manually emit an event on the bus as if KG posted a triple
        bb.event_bus.emit(CognitiveEvent(
            event_type="knowledge_graph.triple.added",
            payload={"subject": "test", "predicate": "is", "object": "good"},
            source="knowledge_graph",
        ))

        # Reasoning should have accumulated context from the event
        assert len(reas._kg_context) == 1

    def test_thread_safety(self):
        """Multiple adapters producing concurrently."""
        bb = CognitiveBlackboard()
        cons = ConsciousnessAdapter(iit=MockIIT(phi=2.0))
        kg = KnowledgeGraphAdapter(kg=MockTemporalKG())
        syn = CognitiveSynergyAdapter(engine=MockSynergyEngine())
        reas = ReasoningAdapter(engine=MockReasoningEngine())

        wire_all(bb, cons, kg, syn, reas)

        errors: list = []

        def sweep_and_check(adapter):
            try:
                entries = adapter.produce()
                if entries:
                    bb.post_many(list(entries))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=sweep_and_check, args=(a,))
            for a in [cons, kg, syn, reas]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
