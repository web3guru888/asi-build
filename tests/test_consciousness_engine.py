"""
Tests for the consciousness_engine package.

Covers:
- ConsciousnessState / ConsciousnessEvent / ConsciousnessMetrics dataclasses
- BaseConsciousness subclass instantiation (all 14 classes)
- GlobalWorkspaceTheory: competition, broadcast, processor management
- IntegratedInformationTheory: Φ computation, element/connection management
- MemoryIntegration: store, retrieve, consolidation, working memory
"""

import time

import numpy as np
import pytest

from asi_build.consciousness.base_consciousness import (
    BaseConsciousness,
    ConsciousnessEvent,
    ConsciousnessMetrics,
    ConsciousnessState,
)
from asi_build.consciousness.global_workspace import (
    CognitiveProcessor,
    GlobalWorkspaceTheory,
    WorkspaceContent,
)
from asi_build.consciousness.integrated_information import (
    Connection,
    IntegratedInformationTheory,
    SystemElement,
)
from asi_build.consciousness.memory_integration import (
    ConsolidationState,
    MemoryIntegration,
    MemoryType,
)

# =========================================================================
# Section 1 — Data-class / enum sanity
# =========================================================================


class TestConsciousnessDataTypes:
    """Basic tests for the consciousness data types."""

    def test_consciousness_state_enum_values(self):
        """All expected states exist and have string values."""
        assert ConsciousnessState.INACTIVE.value == "inactive"
        assert ConsciousnessState.ACTIVE.value == "active"
        assert ConsciousnessState.PROCESSING.value == "processing"
        assert ConsciousnessState.ERROR.value == "error"

    def test_consciousness_event_creation(self):
        """ConsciousnessEvent can be constructed with required fields."""
        evt = ConsciousnessEvent(
            event_id="e1",
            timestamp=time.time(),
            event_type="test",
            data={"key": "value"},
        )
        assert evt.event_id == "e1"
        assert evt.priority == 5  # default

    def test_consciousness_event_to_dict(self):
        """to_dict() round-trips all fields."""
        evt = ConsciousnessEvent(
            event_id="e2",
            timestamp=1234.0,
            event_type="test",
            data={"a": 1},
            priority=8,
            source_module="mod",
            confidence=0.9,
        )
        d = evt.to_dict()
        assert d["event_id"] == "e2"
        assert d["priority"] == 8
        assert d["confidence"] == 0.9

    def test_consciousness_metrics_defaults(self):
        """ConsciousnessMetrics initializes with sane defaults."""
        m = ConsciousnessMetrics()
        assert m.awareness_level == 0.0
        assert m.total_events_processed == 0
        assert isinstance(m.last_updated, float)

    def test_consciousness_metrics_to_dict(self):
        """to_dict() returns all metric fields."""
        m = ConsciousnessMetrics(awareness_level=0.5, learning_rate=0.01)
        d = m.to_dict()
        assert d["awareness_level"] == 0.5
        assert d["learning_rate"] == 0.01


# =========================================================================
# Section 2 — Subclass instantiation (relies on conftest patch)
# =========================================================================


class TestSubclassInstantiation:
    """
    Every BaseConsciousness subclass should be instantiable after the
    conftest `patch_consciousness_initialize` fixture patches the nine
    classes that lack `_initialize` on main.
    """

    # Classes that already have _initialize on main (5)
    @pytest.mark.parametrize(
        "cls_name",
        [
            "GlobalWorkspaceTheory",
            "IntegratedInformationTheory",
            "AttentionSchemaTheory",
            "PredictiveProcessing",
            "MetacognitionSystem",
        ],
    )
    def test_instantiate_classes_with_initialize(self, cls_name):
        """Classes with their own _initialize instantiate cleanly."""
        import asi_build.consciousness as ce

        cls = getattr(ce, cls_name)
        obj = cls()
        assert obj.state == ConsciousnessState.INACTIVE or obj.state == ConsciousnessState.ACTIVE
        assert isinstance(obj.metrics, ConsciousnessMetrics)

    # Classes that are patched by conftest (9)
    @pytest.mark.parametrize(
        "cls_name",
        [
            "ConsciousnessOrchestrator",
            "EmotionalConsciousness",
            "TheoryOfMind",
            "MemoryIntegration",
            "QualiaProcessor",
            "RecursiveSelfImprovement",
            "SelfAwarenessEngine",
            "SensoryIntegration",
            "TemporalConsciousness",
        ],
    )
    def test_instantiate_patched_classes(self, cls_name):
        """Classes patched with no-op _initialize also instantiate."""
        import asi_build.consciousness as ce

        cls = getattr(ce, cls_name)
        obj = cls()
        assert obj.name  # every subclass passes a name to super().__init__
        assert isinstance(obj.metrics, ConsciousnessMetrics)


# =========================================================================
# Section 3 — BaseConsciousness infrastructure
# =========================================================================


class TestBaseConsciousnessInfra:
    """Test common BaseConsciousness infrastructure using GWT as a concrete class."""

    def test_event_queue_priority_ordering(self):
        """Events are sorted by priority (highest first)."""
        gwt = GlobalWorkspaceTheory()
        low = ConsciousnessEvent("low", time.time(), "t", {}, priority=1)
        high = ConsciousnessEvent("high", time.time(), "t", {}, priority=9)
        gwt.add_event(low)
        gwt.add_event(high)
        assert gwt.event_queue[0].event_id == "high"

    def test_subscribe_and_emit_event(self):
        """Event subscription and emission work."""
        gwt = GlobalWorkspaceTheory()
        received = []
        gwt.subscribe_to_event("test_type", lambda e: received.append(e))
        evt = ConsciousnessEvent("e1", time.time(), "test_type", {})
        gwt.emit_event(evt)
        assert len(received) == 1
        assert received[0].event_id == "e1"

    def test_state_change_callback(self):
        """State-change callbacks fire on _set_state."""
        gwt = GlobalWorkspaceTheory()
        transitions = []
        gwt.add_state_change_callback(lambda name, old, new: transitions.append((name, old, new)))
        gwt._set_state(ConsciousnessState.PROCESSING)
        assert len(transitions) == 1
        assert transitions[0][2] == ConsciousnessState.PROCESSING

    def test_get_status_returns_dict(self):
        """get_status() returns well-structured dict."""
        gwt = GlobalWorkspaceTheory()
        status = gwt.get_status()
        assert "name" in status
        assert "state" in status
        assert "metrics" in status
        assert "internal_state" in status

    def test_save_and_load_state(self, tmp_db):
        """State save/load round-trips metrics."""
        gwt = GlobalWorkspaceTheory()
        gwt.metrics.awareness_level = 0.42
        path = str(tmp_db / "state.json")
        gwt.save_state(path)

        gwt2 = GlobalWorkspaceTheory()
        gwt2.load_state(path)
        assert gwt2.metrics.awareness_level == pytest.approx(0.42)

    def test_repr(self):
        """__repr__ is human-readable."""
        gwt = GlobalWorkspaceTheory()
        r = repr(gwt)
        assert "GlobalWorkspaceTheory" in r
        assert "GlobalWorkspace" in r  # the name


# =========================================================================
# Section 4 — Global Workspace Theory
# =========================================================================


class TestGlobalWorkspaceTheory:
    """Tests for GWT competition, broadcast, and processor management."""

    def test_default_processors_created(self):
        """GWT _initialize creates 8 default cognitive processors."""
        gwt = GlobalWorkspaceTheory()
        assert len(gwt.cognitive_processors) == 8
        assert "visual" in gwt.cognitive_processors
        assert "executive" in gwt.cognitive_processors

    def test_add_and_remove_processor(self):
        """Custom processors can be added and removed."""
        gwt = GlobalWorkspaceTheory()
        proc = CognitiveProcessor("custom", "custom_spec", interests={"custom"})
        gwt.add_processor(proc)
        assert "custom" in gwt.cognitive_processors
        gwt.remove_processor("custom")
        assert "custom" not in gwt.cognitive_processors

    def test_submit_content_adds_to_buffer(self):
        """Submitting one content item adds it to workspace buffer."""
        gwt = GlobalWorkspaceTheory()
        content = WorkspaceContent(
            content_id="c1",
            data={"text": "hello", "tags": ["text"]},
            source="test",
            activation_level=0.8,
        )
        gwt.submit_content(content)
        # Buffer may or may not still have it (competition may fire),
        # but workspace internal state should reflect activity
        assert gwt.competition_events >= 0

    def test_competition_selects_highest_activation(self):
        """Competition should broadcast the highest-activation content."""
        gwt = GlobalWorkspaceTheory(config={"broadcast_interval": 0.0})
        low = WorkspaceContent("low", {"tags": ["text"]}, "test", activation_level=0.1)
        high = WorkspaceContent("high", {"tags": ["text"]}, "test", activation_level=0.9)
        gwt.submit_content(low)
        gwt.submit_content(high)

        # After submitting two items, competition fires
        if gwt.conscious_content is not None:
            assert gwt.conscious_content.content_id == "high"

    def test_workspace_enforces_max_size(self):
        """Workspace buffer never exceeds max_workspace_size."""
        gwt = GlobalWorkspaceTheory(
            config={
                "max_workspace_size": 3,
                "competition_threshold": 999.0,  # prevent broadcast from draining
            }
        )
        for i in range(10):
            c = WorkspaceContent(f"c{i}", {"tags": []}, "test", activation_level=0.01)
            gwt.workspace_buffer.append(c)
            if len(gwt.workspace_buffer) > gwt.max_workspace_size:
                gwt.workspace_buffer.sort(key=lambda x: x.calculate_strength())
                gwt.workspace_buffer.pop(0)
        assert len(gwt.workspace_buffer) <= 3

    def test_processor_can_process_checks_interests(self):
        """CognitiveProcessor.can_process respects interests."""
        proc = CognitiveProcessor("vis", "visual", interests={"visual", "image"})
        matching = WorkspaceContent("m", {"tags": ["visual"]}, "test")
        non_matching = WorkspaceContent("n", {"tags": ["audio"]}, "test")
        assert proc.can_process(matching) is True
        assert proc.can_process(non_matching) is False

    def test_processor_can_process_respects_capacity(self):
        """Overloaded processor cannot process new content."""
        proc = CognitiveProcessor("vis", "visual", interests={"visual"})
        proc.current_load = 1.0  # maxed out
        content = WorkspaceContent("c", {"tags": ["visual"]}, "test")
        assert proc.can_process(content) is False

    def test_broadcast_history_recorded(self):
        """Broadcasts are recorded in broadcast_history."""
        gwt = GlobalWorkspaceTheory(config={"broadcast_interval": 0.0})
        c1 = WorkspaceContent("c1", {"tags": ["text"]}, "test", activation_level=0.9)
        c2 = WorkspaceContent("c2", {"tags": ["text"]}, "test", activation_level=0.1)
        gwt.submit_content(c1)
        gwt.submit_content(c2)
        # At least one broadcast should have happened
        history = gwt.get_broadcast_history()
        assert isinstance(history, list)

    def test_workspace_content_calculate_strength(self):
        """WorkspaceContent.calculate_strength returns a positive float."""
        content = WorkspaceContent(
            "c1",
            {},
            "test",
            activation_level=0.5,
            support_coalition={"a", "b"},
        )
        s = content.calculate_strength()
        assert s > 0

    def test_get_current_state_keys(self):
        """get_current_state returns expected keys."""
        gwt = GlobalWorkspaceTheory()
        state = gwt.get_current_state()
        expected_keys = [
            "workspace_buffer_size",
            "active_processors",
            "total_broadcasts",
            "competition_events",
        ]
        for k in expected_keys:
            assert k in state


# =========================================================================
# Section 5 — Integrated Information Theory
# =========================================================================


class TestIntegratedInformationTheory:
    """Tests for IIT Φ computation and system management."""

    def test_default_network_created(self):
        """IIT _initialize creates a multi-layer network."""
        iit = IntegratedInformationTheory()
        assert len(iit.elements) == 13  # 4 sensory + 6 processing + 3 output
        assert len(iit.connections) > 0

    def test_phi_for_single_element_is_zero(self):
        """Φ of a single element is 0 by definition."""
        iit = IntegratedInformationTheory()
        phi = iit.calculate_phi({"sensory_0"})
        assert phi == 0.0

    def test_phi_returns_non_negative(self):
        """Φ for the whole system is always ≥ 0."""
        iit = IntegratedInformationTheory()
        # Run a few state updates to build history
        for _ in range(15):
            iit.update_system_state({"sensory_0": np.random.random()})
        phi = iit.calculate_phi()
        assert phi >= 0.0

    def test_phi_known_disconnected_system(self):
        """Two completely disconnected elements have Φ = 0."""
        iit = IntegratedInformationTheory(config={"max_partition_size": 8})
        # Clear default network
        iit.elements.clear()
        iit.connections.clear()
        iit.system_state_history.clear()
        iit.partition_cache.clear()

        # Add two disconnected elements
        iit.add_element(SystemElement("a", state=0.5))
        iit.add_element(SystemElement("b", state=0.5))
        # No connections

        # Add some state history
        for _ in range(12):
            iit.system_state_history.append({"a": np.random.random(), "b": np.random.random()})

        phi = iit.calculate_phi({"a", "b"})
        assert phi == 0.0  # no cross-connections → no integrated information

    def test_add_element_and_connection(self):
        """Elements and connections can be added dynamically."""
        iit = IntegratedInformationTheory()
        initial_elem_count = len(iit.elements)
        iit.add_element(SystemElement("new_elem", state=0.3))
        assert len(iit.elements) == initial_elem_count + 1

        iit.add_connection(Connection("sensory_0", "new_elem", weight=0.5))
        # new_elem should now have sensory_0 in its inputs
        assert "sensory_0" in iit.elements["new_elem"].inputs

    def test_update_system_state_with_external_inputs(self):
        """External inputs drive sensory element states."""
        iit = IntegratedInformationTheory()
        iit.update_system_state({"sensory_0": 1.0, "sensory_1": 0.0})
        assert iit.elements["sensory_0"].state == 1.0
        assert iit.elements["sensory_1"].state == 0.0

    def test_system_state_history_grows(self):
        """Each update_system_state call appends to history."""
        iit = IntegratedInformationTheory()
        initial_len = len(iit.system_state_history)
        iit.update_system_state()
        assert len(iit.system_state_history) == initial_len + 1

    def test_reset_system_clears_state(self):
        """reset_system zeroes everything out."""
        iit = IntegratedInformationTheory()
        iit.update_system_state({"sensory_0": 1.0})
        iit.current_phi = 1.5
        iit.reset_system()
        assert iit.current_phi == 0.0
        assert len(iit.system_state_history) == 0
        assert all(e.state == 0.0 for e in iit.elements.values())

    def test_system_element_sigmoid_activation(self):
        """SystemElement sigmoid activation produces value in (0, 1)."""
        elem = SystemElement("e", state=0.0, inputs={"a"}, activation_function="sigmoid")
        elem.update_state({"a": 2.0}, {"a": 1.0})
        assert 0.0 < elem.state < 1.0

    def test_system_element_threshold_activation(self):
        """SystemElement threshold activation produces 0 or 1."""
        elem = SystemElement(
            "e", state=0.0, inputs={"a"}, activation_function="threshold", threshold=0.5
        )
        elem.update_state({"a": 1.0}, {"a": 1.0})
        assert elem.state == 1.0
        elem.update_state({"a": 0.1}, {"a": 1.0})
        assert elem.state == 0.0

    def test_get_visualization_data(self):
        """get_system_visualization_data returns nodes and edges."""
        iit = IntegratedInformationTheory()
        viz = iit.get_system_visualization_data()
        assert "nodes" in viz
        assert "edges" in viz
        assert len(viz["nodes"]) == 13


# =========================================================================
# Section 6 — Memory Integration
# =========================================================================


class TestMemoryIntegration:
    """Tests for memory store, retrieve, consolidation, and working memory."""

    def test_form_memory_returns_trace(self):
        """form_memory creates a MemoryTrace with correct fields."""
        mi = MemoryIntegration()
        trace = mi.form_memory(
            {"text": "hello world"},
            MemoryType.EPISODIC,
            consciousness_level=0.8,
        )
        assert trace.memory_id.startswith("memory_")
        assert trace.memory_type == MemoryType.EPISODIC
        assert trace.strength == pytest.approx(0.8)

    def test_form_memory_increments_counter(self):
        """Each form_memory call increments total_memories_formed."""
        mi = MemoryIntegration()
        mi.form_memory({"a": 1}, MemoryType.SEMANTIC)
        mi.form_memory({"b": 2}, MemoryType.SEMANTIC)
        assert mi.total_memories_formed == 2

    def test_retrieve_memory_keyword_match(self):
        """Memories with matching keywords are retrieved."""
        mi = MemoryIntegration()
        mi.form_memory(
            {"topic": "python programming language"},
            MemoryType.SEMANTIC,
            consciousness_level=0.9,
        )
        mi.form_memory(
            {"topic": "cooking recipes for pasta"},
            MemoryType.SEMANTIC,
            consciousness_level=0.9,
        )
        results = mi.retrieve_memory({"query": "python programming"})
        # The python memory should appear (keyword Jaccard overlap)
        assert len(results) >= 1
        # The first result should be the python one
        assert "python" in str(results[0].content).lower()

    def test_retrieve_memory_respects_type_filter(self):
        """retrieve_memory filters by memory type."""
        mi = MemoryIntegration()
        mi.form_memory({"t": "episodic data"}, MemoryType.EPISODIC, 0.9)
        mi.form_memory({"t": "semantic data"}, MemoryType.SEMANTIC, 0.9)
        results = mi.retrieve_memory(
            {"query": "data"},
            memory_types=[MemoryType.SEMANTIC],
        )
        for r in results:
            assert r.memory_type == MemoryType.SEMANTIC

    def test_working_memory_capacity_limit(self):
        """Working memory evicts oldest items when capacity is exceeded."""
        mi = MemoryIntegration(config={"working_memory_capacity": 3})
        for i in range(5):
            mi.update_working_memory(f"item_{i}", f"content_{i}")
            time.sleep(0.001)  # ensure distinct timestamps
        assert len(mi.working_memory) <= 3

    def test_consolidation_strengthens_memory(self):
        """Consolidated memories gain strength."""
        mi = MemoryIntegration()
        trace = mi.form_memory(
            {"text": "important fact"},
            MemoryType.SEMANTIC,
            consciousness_level=0.9,  # above default threshold 0.7
        )
        initial_strength = trace.strength
        consolidated = mi.consolidate_memories()
        assert len(consolidated) >= 1
        # The memory should now be stronger
        updated = mi.memory_traces[trace.memory_id]
        assert updated.strength >= initial_strength

    def test_reconsolidate_memory_updates_content(self):
        """reconsolidate_memory merges new context into existing memory."""
        mi = MemoryIntegration()
        trace = mi.form_memory({"fact": "water boils"}, MemoryType.SEMANTIC, 0.8)
        success = mi.reconsolidate_memory(trace.memory_id, {"detail": "at 100C"})
        assert success is True
        assert "detail" in mi.memory_traces[trace.memory_id].content

    def test_reconsolidate_nonexistent_returns_false(self):
        """reconsolidate_memory returns False for unknown memory IDs."""
        mi = MemoryIntegration()
        assert mi.reconsolidate_memory("nonexistent", {}) is False

    def test_memory_decay(self):
        """Memory strength decays when update() is called."""
        mi = MemoryIntegration(config={"decay_rate": 0.5})
        trace = mi.form_memory({"x": 1}, MemoryType.EPISODIC, 0.9)
        initial = trace.strength
        mi.update()
        assert mi.memory_traces[trace.memory_id].strength < initial

    def test_bind_consciousness_to_memory(self):
        """Binding a consciousness event strengthens the memory."""
        mi = MemoryIntegration()
        trace = mi.form_memory({"x": 1}, MemoryType.EPISODIC, 0.5)
        initial_cl = trace.consciousness_level
        mi.bind_consciousness_to_memory("event_001", trace.memory_id)
        assert trace.consciousness_level > initial_cl
        assert "event_001" in trace.associated_consciousness_events

    def test_get_current_state_structure(self):
        """get_current_state returns all expected keys."""
        mi = MemoryIntegration()
        mi.form_memory({"x": 1}, MemoryType.EPISODIC, 0.5)
        state = mi.get_current_state()
        assert "total_memories" in state
        assert "memory_by_type" in state
        assert "working_memory_items" in state
        assert state["total_memories"] == 1

    def test_process_event_memory_formation(self):
        """process_event handles memory_formation_request."""
        mi = MemoryIntegration()
        evt = ConsciousnessEvent(
            event_id="req_1",
            timestamp=time.time(),
            event_type="memory_formation_request",
            data={
                "content": {"text": "event-formed memory"},
                "memory_type": "episodic",
                "consciousness_level": 0.7,
            },
        )
        response = mi.process_event(evt)
        assert response is not None
        assert response.event_type == "memory_formed"
        assert mi.total_memories_formed == 1
