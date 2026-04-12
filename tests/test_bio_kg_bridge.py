"""
Tests for the Bio-Inspired → Knowledge Graph bridge.

Covers:
- CognitiveStateKGBridge creation and wiring
- record_state_change triple correctness
- enable_kg_logging wrapper behaviour
- State change detection (no-op when state unchanged)
- Old current_state invalidation via resolve_contradictions
- Multi-transition sequences
- Metric recording as triples
- TransitionRecord data integrity
- Query helpers (get_current_state_triple, get_transition_history)
"""

import pytest

from asi_build.bio_inspired.core import BioCognitiveArchitecture, CognitiveState
from asi_build.bio_inspired.kg_bridge import (
    AGENT,
    SUBJECT,
    SOURCE,
    CognitiveStateKGBridge,
    TransitionRecord,
    enable_kg_logging,
)
from asi_build.knowledge_graph.temporal_kg import TemporalKnowledgeGraph


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def arch():
    """Fresh BioCognitiveArchitecture (starts AWAKE_ACTIVE)."""
    return BioCognitiveArchitecture()


@pytest.fixture
def kg():
    """In-memory TemporalKnowledgeGraph."""
    _kg = TemporalKnowledgeGraph(db_path=":memory:")
    yield _kg
    _kg.close()


@pytest.fixture
def bridge(arch, kg):
    """CognitiveStateKGBridge with metrics enabled."""
    return CognitiveStateKGBridge(arch, kg, record_metrics=True)


@pytest.fixture
def bridge_no_metrics(arch, kg):
    """CognitiveStateKGBridge with metrics disabled."""
    return CognitiveStateKGBridge(arch, kg, record_metrics=False)


# ── 1. Bridge construction ─────────────────────────────────────────────


class TestBridgeConstruction:
    def test_bridge_created_with_correct_refs(self, arch, kg, bridge):
        assert bridge.arch is arch
        assert bridge.kg is kg
        assert bridge.record_metrics is True
        assert bridge.history == []
        assert bridge._current_state_triple_id is None

    def test_bridge_no_metrics_flag(self, bridge_no_metrics):
        assert bridge_no_metrics.record_metrics is False


# ── 2. record_state_change correctness ─────────────────────────────────


class TestRecordStateChange:
    def test_writes_three_core_triples(self, bridge, kg):
        rec = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        assert len(rec.triple_ids) == 3

        # Verify each triple exists in KG
        matches = kg.get_triples(current_only=False)
        ids = [t["triple_id"] for t in matches]
        for tid in rec.triple_ids:
            assert tid in ids

    def test_transitioned_from_triple(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.NREM_SLEEP
        )
        triples = kg.get_triples(subject=SUBJECT, predicate="transitioned_from")
        assert len(triples) >= 1
        assert triples[0]["object"] == "awake_active"

    def test_transitioned_to_triple(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.NREM_SLEEP
        )
        triples = kg.get_triples(subject=SUBJECT, predicate="transitioned_to")
        assert len(triples) >= 1
        assert triples[0]["object"] == "nrem_sleep"

    def test_current_state_triple(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        triples = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=True
        )
        assert len(triples) == 1
        assert triples[0]["object"] == "learning"

    def test_subject_is_correct(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.CONSOLIDATING
        )
        triples = kg.get_triples(subject=SUBJECT)
        for t in triples:
            # TemporalKG normalises to lowercase+underscores
            assert t["subject"] == SUBJECT.lower().replace(" ", "_")

    def test_source_is_bio_inspired(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.ADAPTING
        )
        triples = kg.get_triples(subject=SUBJECT, predicate="transitioned_to")
        assert triples[0]["source"] == SOURCE

    def test_temporal_type_is_dynamic(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.DEVELOPING
        )
        triples = kg.get_triples(subject=SUBJECT, predicate="transitioned_from")
        assert triples[0]["temporal_type"] == "dynamic"

    def test_returns_transition_record(self, bridge):
        rec = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.REM_SLEEP
        )
        assert isinstance(rec, TransitionRecord)
        assert rec.old_state == CognitiveState.AWAKE_ACTIVE
        assert rec.new_state == CognitiveState.REM_SLEEP
        assert rec.timestamp > 0

    def test_history_grows(self, bridge):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        bridge.record_state_change(
            CognitiveState.LEARNING, CognitiveState.CONSOLIDATING
        )
        assert len(bridge.history) == 2


# ── 3. current_state invalidation ──────────────────────────────────────


class TestCurrentStateInvalidation:
    def test_old_current_state_is_invalidated(self, bridge, kg):
        """After two transitions, only the latest current_state is active."""
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        bridge.record_state_change(
            CognitiveState.LEARNING, CognitiveState.CONSOLIDATING
        )
        active = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=True
        )
        assert len(active) == 1
        assert active[0]["object"] == "consolidating"

    def test_invalidated_triple_still_in_history(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        bridge.record_state_change(
            CognitiveState.LEARNING, CognitiveState.NREM_SLEEP
        )
        all_triples = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=False
        )
        assert len(all_triples) == 2  # one invalidated, one active

    def test_three_transitions_single_active(self, bridge, kg):
        for new_state in [
            CognitiveState.LEARNING,
            CognitiveState.CONSOLIDATING,
            CognitiveState.AWAKE_RESTING,
        ]:
            old = CognitiveState.AWAKE_ACTIVE  # simplified
            bridge.record_state_change(old, new_state)

        active = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=True
        )
        assert len(active) == 1
        assert active[0]["object"] == "awake_resting"


# ── 4. enable_kg_logging wrapper ───────────────────────────────────────


class TestEnableKGLogging:
    def test_returns_bridge(self, arch, kg):
        bridge = enable_kg_logging(arch, kg)
        assert isinstance(bridge, CognitiveStateKGBridge)

    def test_bridge_stored_on_arch(self, arch, kg):
        bridge = enable_kg_logging(arch, kg)
        assert arch._kg_bridge is bridge

    def test_wrapper_detects_change(self, arch, kg):
        bridge = enable_kg_logging(arch, kg)

        # Force a state change by manipulating sleep pressure
        arch.state = CognitiveState.AWAKE_ACTIVE
        arch.sleep_pressure = 10.0  # extreme → will trigger sleep
        arch.circadian_clock = 0.25  # sin(π/2)=1 → sleep_drive ≫ threshold

        arch._update_cognitive_state()

        # State should have changed and bridge should have recorded it
        if arch.state != CognitiveState.AWAKE_ACTIVE:
            assert len(bridge.history) == 1
            assert bridge.history[0].old_state == CognitiveState.AWAKE_ACTIVE
        # If by chance state didn't change (unlikely), bridge should be empty
        else:
            assert len(bridge.history) == 0

    def test_wrapper_no_write_when_state_unchanged(self, arch, kg):
        bridge = enable_kg_logging(arch, kg)

        # Set conditions so state stays AWAKE_ACTIVE
        arch.state = CognitiveState.AWAKE_ACTIVE
        arch.sleep_pressure = 0.0
        arch.circadian_clock = 0.0  # sin(0)=0 → sleep_drive=0 < wake_threshold

        arch._update_cognitive_state()

        assert len(bridge.history) == 0

    def test_original_method_still_called(self, arch, kg):
        """The original _update_cognitive_state logic still runs."""
        bridge = enable_kg_logging(arch, kg)
        arch.sleep_pressure = 10.0
        arch.circadian_clock = 0.25

        arch._update_cognitive_state()

        # State should be a sleep state (NREM or REM)
        assert arch.state in (
            CognitiveState.NREM_SLEEP,
            CognitiveState.REM_SLEEP,
        )


# ── 5. Metrics recording ──────────────────────────────────────────────


class TestMetricsRecording:
    def test_metrics_triples_created(self, bridge, kg):
        rec = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        # global_metrics defaults are all 0.0 — should still be recorded
        assert len(rec.metric_triple_ids) > 0

    def test_no_metrics_when_disabled(self, bridge_no_metrics):
        rec = bridge_no_metrics.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        assert len(rec.metric_triple_ids) == 0

    def test_metric_predicate_values(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        # energy_efficiency is a known metric predicate
        triples = kg.get_triples(subject=SUBJECT, predicate="energy_efficiency")
        assert len(triples) >= 1
        # Value should be parseable as float
        float(triples[0]["object"])

    def test_metric_confidence_is_0_9(self, bridge, kg):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        triples = kg.get_triples(subject=SUBJECT, predicate="energy_efficiency")
        assert triples[0]["confidence"] == pytest.approx(0.9)


# ── 6. Multi-transition sequences ─────────────────────────────────────


class TestMultiTransition:
    def test_full_lifecycle(self, bridge, kg):
        """Walk through a realistic lifecycle."""
        transitions = [
            (CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING),
            (CognitiveState.LEARNING, CognitiveState.CONSOLIDATING),
            (CognitiveState.CONSOLIDATING, CognitiveState.NREM_SLEEP),
            (CognitiveState.NREM_SLEEP, CognitiveState.REM_SLEEP),
            (CognitiveState.REM_SLEEP, CognitiveState.AWAKE_RESTING),
            (CognitiveState.AWAKE_RESTING, CognitiveState.AWAKE_ACTIVE),
        ]

        for old, new in transitions:
            bridge.record_state_change(old, new)

        assert len(bridge.history) == 6

        # Only one active current_state
        active = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=True
        )
        assert len(active) == 1
        assert active[0]["object"] == "awake_active"

        # 6 transitioned_from triples (all still active — they're not contradicting)
        from_triples = kg.get_triples(
            subject=SUBJECT, predicate="transitioned_from"
        )
        assert len(from_triples) == 6

    def test_all_states_representable(self, bridge, kg):
        """Every CognitiveState value can be recorded."""
        states = list(CognitiveState)
        for i in range(len(states) - 1):
            bridge.record_state_change(states[i], states[i + 1])

        active = kg.get_triples(
            subject=SUBJECT, predicate="current_state", current_only=True
        )
        assert active[0]["object"] == states[-1].value


# ── 7. Query helpers ───────────────────────────────────────────────────


class TestQueryHelpers:
    def test_get_current_state_triple_none_initially(self, bridge):
        assert bridge.get_current_state_triple() is None

    def test_get_current_state_triple_after_transition(self, bridge):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        triple = bridge.get_current_state_triple()
        assert triple is not None
        assert triple["object"] == "learning"

    def test_get_transition_history(self, bridge):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        bridge.record_state_change(
            CognitiveState.LEARNING, CognitiveState.CONSOLIDATING
        )
        history = bridge.get_transition_history()
        # Should contain at least 2 entries (all current_state triples, active + invalidated)
        assert len(history) >= 2

    def test_current_state_triple_id_tracked(self, bridge):
        bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.DEVELOPING
        )
        assert bridge._current_state_triple_id is not None
        assert isinstance(bridge._current_state_triple_id, str)
        assert len(bridge._current_state_triple_id) > 0


# ── 8. TransitionRecord integrity ─────────────────────────────────────


class TestTransitionRecord:
    def test_record_fields(self, bridge):
        rec = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.ADAPTING
        )
        assert rec.old_state == CognitiveState.AWAKE_ACTIVE
        assert rec.new_state == CognitiveState.ADAPTING
        assert isinstance(rec.triple_ids, list)
        assert isinstance(rec.metric_triple_ids, list)
        assert rec.timestamp > 0

    def test_record_timestamps_increase(self, bridge):
        rec1 = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        rec2 = bridge.record_state_change(
            CognitiveState.LEARNING, CognitiveState.CONSOLIDATING
        )
        assert rec2.timestamp >= rec1.timestamp

    def test_record_triple_ids_are_unique(self, bridge):
        rec = bridge.record_state_change(
            CognitiveState.AWAKE_ACTIVE, CognitiveState.LEARNING
        )
        all_ids = rec.triple_ids + rec.metric_triple_ids
        assert len(all_ids) == len(set(all_ids))
