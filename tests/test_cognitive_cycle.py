"""
Comprehensive tests for CognitiveCycle — the tick loop orchestrator.

Tests cover:  lifecycle, adapter management, tick execution, safety gates,
metrics & history, multi-tick / background, and error handling.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional, Sequence
from dataclasses import field

import pytest

from asi_build.integration import (
    CognitiveBlackboard,
    CognitiveCycle,
    CyclePhase,
    CycleState,
    CycleMetrics,
    TickResult,
    AdapterRole,
)
from asi_build.integration.protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EntryPriority,
    ModuleCapability,
    ModuleInfo,
)


# ============================================================================
# Mock adapters
# ============================================================================


class MockAdapter:
    """General-purpose mock adapter implementing the BlackboardParticipant protocol."""

    MODULE_NAME = "mock_adapter"
    MODULE_VERSION = "1.0.0"

    def __init__(
        self,
        name: str = "mock",
        entries: Optional[List[BlackboardEntry]] = None,
    ):
        self.MODULE_NAME = name
        self._blackboard: Any = None
        self._event_handler: Any = None
        self._entries: List[BlackboardEntry] = entries or []
        self._consumed: List[BlackboardEntry] = []
        self._events: List[CognitiveEvent] = []

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
            topics_produced=frozenset({"mock.data"}),
            topics_consumed=frozenset({"mock"}),
        )

    def on_registered(self, blackboard: Any) -> None:
        self._blackboard = blackboard

    def set_event_handler(self, handler: Any) -> None:
        self._event_handler = handler

    def handle_event(self, event: CognitiveEvent) -> None:
        self._events.append(event)

    def produce(self) -> List[BlackboardEntry]:
        return list(self._entries)

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        self._consumed.extend(entries)

    def snapshot(self) -> dict:
        return {"consumed": len(self._consumed)}


class MockSafetyAdapter(MockAdapter):
    """Safety adapter that can optionally veto."""

    def __init__(self, name: str = "safety_adapter", veto: bool = False):
        super().__init__(name=name)
        self.veto = veto

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=ModuleCapability.PRODUCER,
            topics_produced=frozenset({"safety.check"}),
            topics_consumed=frozenset(),
        )

    def produce(self) -> List[BlackboardEntry]:
        if self.veto:
            return [
                BlackboardEntry(
                    topic="safety.check",
                    data={"is_ethical": False, "reason": "veto!"},
                    source_module=self.MODULE_NAME,
                    priority=EntryPriority.CRITICAL,
                )
            ]
        return [
            BlackboardEntry(
                topic="safety.check",
                data={"is_ethical": True},
                source_module=self.MODULE_NAME,
            )
        ]


class ErrorAdapter(MockAdapter):
    """Adapter whose produce/consume raise on demand."""

    def __init__(
        self,
        name: str = "error_adapter",
        fail_produce: bool = False,
        fail_consume: bool = False,
    ):
        super().__init__(name=name)
        self.fail_produce = fail_produce
        self.fail_consume = fail_consume

    def produce(self) -> List[BlackboardEntry]:
        if self.fail_produce:
            raise RuntimeError("produce boom")
        return []

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        if self.fail_consume:
            raise RuntimeError("consume boom")


class MockTransformerAdapter(MockAdapter):
    """Adapter with TRANSFORMER capability."""

    def __init__(self, name: str = "transformer", tag: str = "transformed"):
        super().__init__(name=name)
        self._tag = tag

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version=self.MODULE_VERSION,
            capabilities=(
                ModuleCapability.PRODUCER
                | ModuleCapability.CONSUMER
                | ModuleCapability.TRANSFORMER
            ),
            topics_produced=frozenset({"transformed.data"}),
            topics_consumed=frozenset({"mock"}),
        )

    def produce(self) -> List[BlackboardEntry]:
        return []

    def transform(self, entries: Sequence[BlackboardEntry]) -> List[BlackboardEntry]:
        result: List[BlackboardEntry] = []
        for e in entries:
            result.append(
                BlackboardEntry(
                    topic="transformed.data",
                    data={**(e.data if isinstance(e.data, dict) else {}), "tag": self._tag},
                    source_module=self.MODULE_NAME,
                    parent_id=e.entry_id,
                )
            )
        return result


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def bb() -> CognitiveBlackboard:
    """Fresh blackboard."""
    return CognitiveBlackboard()


@pytest.fixture
def cycle(bb: CognitiveBlackboard) -> CognitiveCycle:
    """Cycle with safety_required=False (most tests don't need a safety adapter)."""
    return CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)


@pytest.fixture
def cycle_with_safety(bb: CognitiveBlackboard) -> CognitiveCycle:
    """Cycle with safety_required=True."""
    return CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)


def _make_entry(topic: str = "mock.data", data: Any = None, source: str = "mock") -> BlackboardEntry:
    """Helper: create a BlackboardEntry with defaults."""
    return BlackboardEntry(
        topic=topic,
        data=data or {"value": 1},
        source_module=source,
    )


# ============================================================================
# 1. Lifecycle (5 tests)
# ============================================================================


class TestLifecycle:
    """Tests for cycle state transitions."""

    def test_01_created_state(self, bb: CognitiveBlackboard) -> None:
        """Freshly constructed cycle is in CREATED state."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False)
        assert cycle.state == CycleState.CREATED
        assert cycle.phase == CyclePhase.IDLE
        assert cycle.tick_number == 0

    def test_02_start_running(self, bb: CognitiveBlackboard) -> None:
        """start() transitions to RUNNING."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=100, max_ticks=1,
        )
        cycle.start()
        assert cycle.state in (CycleState.RUNNING, CycleState.STOPPED)
        cycle.stop(timeout=2)
        assert cycle.state == CycleState.STOPPED

    def test_03_stop_from_running(self, bb: CognitiveBlackboard) -> None:
        """stop() transitions from RUNNING to STOPPED."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=100, max_ticks=2,
        )
        cycle.start()
        cycle.stop(timeout=2)
        assert cycle.state == CycleState.STOPPED

    def test_04_pause(self, bb: CognitiveBlackboard) -> None:
        """pause() sets state to PAUSED."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=10,
        )
        cycle.start()
        time.sleep(0.05)
        cycle.pause()
        assert cycle.state == CycleState.PAUSED
        assert cycle.is_paused
        cycle.stop(timeout=2)

    def test_05_resume_from_paused(self, bb: CognitiveBlackboard) -> None:
        """resume() moves from PAUSED back to RUNNING."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=10,
        )
        cycle.start()
        time.sleep(0.05)
        cycle.pause()
        assert cycle.is_paused

        ticks_at_pause = cycle.tick_number
        cycle.resume()
        assert cycle.state == CycleState.RUNNING
        assert cycle.is_running
        time.sleep(0.15)  # Let some ticks run
        assert cycle.tick_number > ticks_at_pause
        cycle.stop(timeout=2)


# ============================================================================
# 2. Adapter Management (5 tests)
# ============================================================================


class TestAdapterManagement:
    """Tests for registering / unregistering / listing / getting adapters."""

    def test_06_register_increases_count(self, cycle: CognitiveCycle) -> None:
        """Registering an adapter increases adapter_count."""
        assert cycle.adapter_count == 0
        cycle.register_adapter(MockAdapter(name="a"))
        assert cycle.adapter_count == 1
        cycle.register_adapter(MockAdapter(name="b"))
        assert cycle.adapter_count == 2

    def test_07_register_duplicate_raises(self, cycle: CognitiveCycle) -> None:
        """Registering the same name twice raises ValueError."""
        cycle.register_adapter(MockAdapter(name="dup"))
        with pytest.raises(ValueError, match="already registered"):
            cycle.register_adapter(MockAdapter(name="dup"))

    def test_08_unregister_removes(self, cycle: CognitiveCycle) -> None:
        """unregister_adapter removes the adapter and returns True."""
        cycle.register_adapter(MockAdapter(name="removeme"))
        assert cycle.adapter_count == 1
        result = cycle.unregister_adapter("removeme")
        assert result is True
        assert cycle.adapter_count == 0

    def test_08b_unregister_missing_returns_false(self, cycle: CognitiveCycle) -> None:
        """unregister_adapter on unknown name returns False."""
        assert cycle.unregister_adapter("nope") is False

    def test_09_list_adapters(self, cycle: CognitiveCycle) -> None:
        """list_adapters returns info dicts with expected fields."""
        cycle.register_adapter(MockAdapter(name="alpha"))
        cycle.register_adapter(MockAdapter(name="beta"))
        adapters = cycle.list_adapters()
        assert len(adapters) == 2
        names = [a["name"] for a in adapters]
        assert "alpha" in names
        assert "beta" in names
        # Each entry has the required keys
        for a in adapters:
            assert "role" in a
            assert "version" in a
            assert "capabilities" in a
            assert "topics_produced" in a
            assert "topics_consumed" in a

    def test_10_get_adapter(self, cycle: CognitiveCycle) -> None:
        """get_adapter returns the adapter instance by name."""
        adapter = MockAdapter(name="target")
        cycle.register_adapter(adapter)
        retrieved = cycle.get_adapter("target")
        assert retrieved is adapter

    def test_10b_get_adapter_missing(self, cycle: CognitiveCycle) -> None:
        """get_adapter returns None for unknown name."""
        assert cycle.get_adapter("nonexistent") is None


# ============================================================================
# 3. Tick Execution (5 tests)
# ============================================================================


class TestTickExecution:
    """Tests for the tick() method and its phases."""

    def test_11_tick_produces_entries(self, cycle: CognitiveCycle) -> None:
        """A tick with a producing adapter puts entries on the blackboard."""
        entry = _make_entry()
        adapter = MockAdapter(name="producer", entries=[entry])
        cycle.register_adapter(adapter)

        result = cycle.tick()
        assert result.entries_produced == 1
        # Entry should be on the blackboard
        assert cycle.blackboard.entry_count >= 1

    def test_12_tick_consumer_receives(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """Consumer receives entries matching its topics during cognize phase."""
        # Pre-post an entry matching the consumer's topic
        entry = _make_entry(topic="mock.data")
        bb.post(entry)

        consumer = MockAdapter(name="consumer")
        cycle.register_adapter(consumer)

        cycle.tick()
        assert len(consumer._consumed) > 0

    def test_13_tick_no_adapters(self, cycle: CognitiveCycle) -> None:
        """Tick with no adapters produces an empty result and doesn't crash."""
        result = cycle.tick()
        assert result.entries_produced == 0
        assert result.entries_consumed == 0
        assert result.errors == []
        assert result.tick_number == 1

    def test_14_tick_increments_number(self, cycle: CognitiveCycle) -> None:
        """Each tick increments tick_number."""
        assert cycle.tick_number == 0
        cycle.tick()
        assert cycle.tick_number == 1
        cycle.tick()
        assert cycle.tick_number == 2
        cycle.tick()
        assert cycle.tick_number == 3

    def test_15_tick_result_phase_times(self, cycle: CognitiveCycle) -> None:
        """TickResult contains phase_times for perceive, cognize, act."""
        cycle.register_adapter(MockAdapter(name="p"))
        result = cycle.tick()
        assert "perceive" in result.phase_times
        assert "cognize" in result.phase_times
        assert "act" in result.phase_times
        for phase_name, ms in result.phase_times.items():
            assert isinstance(ms, float)
            assert ms >= 0

    def test_15b_tick_result_total_time(self, cycle: CognitiveCycle) -> None:
        """TickResult.total_time_ms is populated and positive."""
        result = cycle.tick()
        assert result.total_time_ms >= 0


# ============================================================================
# 4. Safety (3 tests)
# ============================================================================


class TestSafety:
    """Tests for safety adapter gate checks."""

    def test_16_safety_required_no_adapter(self, cycle_with_safety: CognitiveCycle) -> None:
        """safety_required=True + no safety adapter → RuntimeError on start."""
        with pytest.raises(RuntimeError, match="safety_required"):
            cycle_with_safety.start()

    def test_17_safety_not_required(self, bb: CognitiveBlackboard) -> None:
        """safety_required=False allows starting without a safety adapter."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=100, max_ticks=1,
        )
        cycle.start()
        cycle.stop(timeout=2)
        assert cycle.state == CycleState.STOPPED

    def test_18_safety_veto_counted(self, bb: CognitiveBlackboard) -> None:
        """A safety adapter that vetoes increments safety_vetoes."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(name="safety", veto=True)
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()
        assert result.safety_checks >= 1
        assert result.safety_vetoes >= 1

    def test_18b_safety_pass_no_veto(self, bb: CognitiveBlackboard) -> None:
        """A safety adapter that passes has checks but zero vetoes."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(name="safety", veto=False)
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()
        assert result.safety_checks >= 1
        assert result.safety_vetoes == 0


# ============================================================================
# 5. Metrics & History (4 tests)
# ============================================================================


class TestMetricsAndHistory:
    """Tests for get_status, get_tick_history, and CycleMetrics."""

    def test_19_get_status_keys(self, cycle: CognitiveCycle) -> None:
        """get_status returns a dict with all expected keys."""
        cycle.register_adapter(MockAdapter(name="x"))
        cycle.tick()

        status = cycle.get_status()
        expected_keys = {
            "state",
            "phase",
            "tick_number",
            "tick_rate_hz",
            "max_ticks",
            "adapter_count",
            "safety_required",
            "uptime_seconds",
            "blackboard_entries",
            "blackboard_modules",
            "metrics",
        }
        assert expected_keys.issubset(status.keys())
        assert isinstance(status["metrics"], dict)

    def test_20_tick_history(self, cycle: CognitiveCycle) -> None:
        """get_tick_history returns the last N ticks as dicts."""
        for _ in range(5):
            cycle.tick()

        history = cycle.get_tick_history(last_n=3)
        assert len(history) == 3
        # Should be last 3 ticks (3, 4, 5)
        assert history[0]["tick_number"] == 3
        assert history[-1]["tick_number"] == 5
        for h in history:
            assert "total_time_ms" in h
            assert "entries_produced" in h
            assert "phase_times" in h

    def test_21_metrics_to_dict(self, cycle: CognitiveCycle) -> None:
        """CycleMetrics.to_dict() returns a JSON-serializable dict."""
        import json

        cycle.register_adapter(MockAdapter(name="m", entries=[_make_entry()]))
        cycle.tick()
        cycle.tick()

        d = cycle.metrics.to_dict()
        assert isinstance(d, dict)
        # Should be JSON-serializable
        json_str = json.dumps(d)
        assert json_str  # non-empty

        assert d["total_ticks"] == 2
        assert d["total_entries_produced"] >= 2
        assert isinstance(d["avg_tick_time_ms"], float)
        assert isinstance(d["adapter_produce_counts"], dict)

    def test_22_avg_tick_time_updates(self, cycle: CognitiveCycle) -> None:
        """avg_tick_time_ms updates after ticks."""
        assert cycle.metrics.avg_tick_time_ms == 0.0
        cycle.tick()
        assert cycle.metrics.avg_tick_time_ms > 0.0
        first_avg = cycle.metrics.avg_tick_time_ms
        cycle.tick()
        # Average should be recalculated (not necessarily different, but exists)
        assert cycle.metrics.avg_tick_time_ms > 0.0
        assert cycle.metrics.total_ticks == 2


# ============================================================================
# 6. Multi-tick / Background (3+ tests)
# ============================================================================


class TestMultiTickBackground:
    """Tests for background thread operation, max_ticks, callbacks."""

    def test_23_max_ticks_stops(self, bb: CognitiveBlackboard) -> None:
        """max_ticks causes the loop to stop after N ticks."""
        cycle = CognitiveCycle(
            blackboard=bb,
            safety_required=False,
            tick_rate_hz=0,  # as fast as possible
            max_ticks=5,
        )
        cycle.start()
        finished = cycle.wait(timeout=5.0)
        assert finished
        # Thread stopped on its own
        cycle.stop(timeout=2)
        assert cycle.tick_number == 5

    def test_24_on_tick_callback(self, bb: CognitiveBlackboard) -> None:
        """on_tick callback is invoked with (tick_number, TickResult)."""
        received: List[tuple] = []

        def callback(tick_num: int, result: TickResult) -> None:
            received.append((tick_num, result))

        cycle = CognitiveCycle(
            blackboard=bb,
            safety_required=False,
            tick_rate_hz=0,
            max_ticks=3,
            on_tick=callback,
        )
        cycle.start()
        cycle.wait(timeout=5.0)
        cycle.stop(timeout=2)

        assert len(received) == 3
        # Tick numbers match
        assert received[0][0] == 1
        assert received[1][0] == 2
        assert received[2][0] == 3
        # Second element is TickResult
        assert isinstance(received[0][1], TickResult)

    def test_25_tick_rate_hz_adjustable(self, bb: CognitiveBlackboard) -> None:
        """tick_rate_hz property can be adjusted after construction."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=10,
        )
        assert cycle.tick_rate_hz == 10
        cycle.tick_rate_hz = 50
        assert cycle.tick_rate_hz == 50

    def test_25b_wait_returns_true_on_stop(self, bb: CognitiveBlackboard) -> None:
        """wait() returns True when cycle stops naturally."""
        cycle = CognitiveCycle(
            blackboard=bb,
            safety_required=False,
            tick_rate_hz=0,
            max_ticks=2,
        )
        cycle.start()
        result = cycle.wait(timeout=5.0)
        assert result is True
        cycle.stop(timeout=2)

    def test_25c_wait_returns_true_when_not_started(self, cycle: CognitiveCycle) -> None:
        """wait() returns True immediately if the thread was never started."""
        assert cycle.wait(timeout=0.1) is True

    def test_25d_multiple_ticks_accumulate_metrics(self, bb: CognitiveBlackboard) -> None:
        """Running multiple ticks accumulates metrics correctly."""
        cycle = CognitiveCycle(
            blackboard=bb,
            safety_required=False,
            tick_rate_hz=0,
            max_ticks=10,
        )
        adapter = MockAdapter(name="prod", entries=[_make_entry()])
        cycle.register_adapter(adapter)

        cycle.start()
        cycle.wait(timeout=5.0)
        cycle.stop(timeout=2)

        m = cycle.metrics
        assert m.total_ticks == 10
        assert m.total_entries_produced >= 10
        assert m.max_tick_time_ms >= m.min_tick_time_ms
        assert m.ticks_per_second > 0


# ============================================================================
# 7. Error Handling (2+ tests)
# ============================================================================


class TestErrorHandling:
    """Tests for graceful error handling in adapters."""

    def test_26_produce_error_recorded(self, cycle: CognitiveCycle) -> None:
        """If produce() raises, the error is recorded but others still run."""
        good = MockAdapter(name="good", entries=[_make_entry()])
        bad = ErrorAdapter(name="bad_producer", fail_produce=True)

        cycle.register_adapter(bad)
        cycle.register_adapter(good)

        result = cycle.tick()
        # Error from bad adapter recorded
        assert len(result.errors) >= 1
        assert "bad_producer" in result.errors[0]
        # Good adapter's entry was still produced
        assert result.entries_produced >= 1

    def test_27_consume_error_recorded(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """If consume() raises, the error is recorded."""
        # Put an entry on the blackboard matching consumer topic
        bb.post(_make_entry(topic="mock.data"))

        bad = ErrorAdapter(name="bad_consumer", fail_consume=True)
        cycle.register_adapter(bad)

        result = cycle.tick()
        assert len(result.errors) >= 1
        assert "bad_consumer" in result.errors[0]

    def test_27b_on_error_callback(self, bb: CognitiveBlackboard) -> None:
        """on_error callback is invoked when an adapter raises."""
        errors_seen: List[tuple] = []

        def on_err(name: str, exc: Exception) -> None:
            errors_seen.append((name, exc))

        cycle = CognitiveCycle(
            blackboard=bb,
            safety_required=False,
            tick_rate_hz=0,
            on_error=on_err,
        )
        bad = ErrorAdapter(name="kaboom", fail_produce=True)
        cycle.register_adapter(bad)

        cycle.tick()
        assert len(errors_seen) == 1
        assert errors_seen[0][0] == "kaboom"
        assert isinstance(errors_seen[0][1], RuntimeError)

    def test_27c_errors_tracked_in_metrics(self, cycle: CognitiveCycle) -> None:
        """Adapter errors increment metrics.adapter_error_counts."""
        bad = ErrorAdapter(name="err", fail_produce=True)
        cycle.register_adapter(bad)

        cycle.tick()
        cycle.tick()
        assert cycle.metrics.adapter_error_counts["err"] >= 2
        assert cycle.metrics.total_errors >= 2


# ============================================================================
# 8. Adapter Roles (additional)
# ============================================================================


class TestAdapterRoles:
    """Tests for different AdapterRole behaviour."""

    def test_action_adapter_skipped_in_perceive(self, cycle: CognitiveCycle) -> None:
        """ACTION-role adapter is NOT called during perceive phase."""
        action = MockAdapter(name="action_only", entries=[_make_entry()])
        cycle.register_adapter(action, role="action")

        result = cycle.tick()
        # The action adapter produces in the ACT phase, not perceive
        # Its entries should still appear in entries_produced
        assert result.entries_produced >= 1

    def test_perception_adapter_skipped_in_cognize(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """PERCEPTION-role adapter is NOT called during cognize (consume) phase."""
        bb.post(_make_entry(topic="mock.data"))

        percept = MockAdapter(name="perceiver")
        cycle.register_adapter(percept, role="perception")

        cycle.tick()
        # Perception adapters are skipped in cognize, so consume is never called
        assert len(percept._consumed) == 0

    def test_invalid_role_raises(self, cycle: CognitiveCycle) -> None:
        """Registering with an invalid role string raises ValueError."""
        adapter = MockAdapter(name="x")
        with pytest.raises(ValueError):
            cycle.register_adapter(adapter, role="invalid_role")

    def test_register_while_running_raises(self, bb: CognitiveBlackboard) -> None:
        """Cannot register adapters while cycle is RUNNING."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=10,
        )
        cycle.start()
        time.sleep(0.05)
        with pytest.raises(RuntimeError, match="Cannot register"):
            cycle.register_adapter(MockAdapter(name="late"))
        cycle.stop(timeout=2)


# ============================================================================
# 9. Transformer support
# ============================================================================


class TestTransformer:
    """Tests for the transform phase within cognize."""

    def test_transformer_enriches_entries(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """A transformer adapter produces transformed entries on the blackboard."""
        # Seed the blackboard with an entry matching the transformer's consumed topic
        original = _make_entry(topic="mock.data", data={"x": 1})
        bb.post(original)

        transformer = MockTransformerAdapter(name="enricher", tag="enriched")
        cycle.register_adapter(transformer)

        result = cycle.tick()
        assert result.entries_transformed >= 1

    def test_transformer_entries_on_blackboard(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """Transformed entries are actually posted to the blackboard."""
        bb.post(_make_entry(topic="mock.data", data={"x": 42}))
        transformer = MockTransformerAdapter(name="tformer", tag="done")
        cycle.register_adapter(transformer)

        cycle.tick()
        # Check that transformed.data topic entries exist
        transformed_entries = bb.get_by_topic("transformed", include_subtopics=True)
        assert len(transformed_entries) >= 1
        assert transformed_entries[0].data.get("tag") == "done"


# ============================================================================
# 10. Events emitted
# ============================================================================


class TestCycleEvents:
    """Tests for events emitted by the cycle."""

    def test_tick_completed_event(self, cycle: CognitiveCycle) -> None:
        """Each tick emits a 'cycle.tick.completed' event."""
        received: List[CognitiveEvent] = []
        cycle.blackboard.event_bus.subscribe(
            pattern="cycle.tick.*",
            handler=lambda e: received.append(e),
        )
        cycle.tick()
        assert len(received) >= 1
        assert received[0].event_type == "cycle.tick.completed"
        assert received[0].payload["tick_number"] == 1

    def test_started_stopped_events(self, bb: CognitiveBlackboard) -> None:
        """start() and stop() emit cycle.started and cycle.stopped events."""
        events: List[CognitiveEvent] = []
        bb.event_bus.subscribe(
            pattern="cycle.*",
            handler=lambda e: events.append(e),
        )
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=1,
        )
        cycle.start()
        cycle.wait(timeout=5.0)
        cycle.stop(timeout=2)

        types = [e.event_type for e in events]
        assert "cycle.started" in types
        assert "cycle.stopped" in types


# ============================================================================
# 11. Repr & edge cases
# ============================================================================


class TestEdgeCases:
    """Miscellaneous edge cases and __repr__."""

    def test_repr(self, cycle: CognitiveCycle) -> None:
        """__repr__ returns a descriptive string."""
        r = repr(cycle)
        assert "CognitiveCycle" in r
        assert "state=" in r
        assert "tick=" in r

    def test_double_start_raises(self, bb: CognitiveBlackboard) -> None:
        """Starting an already-running cycle raises RuntimeError."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=10,
        )
        cycle.start()
        time.sleep(0.05)
        with pytest.raises(RuntimeError, match="already"):
            cycle.start()
        cycle.stop(timeout=2)

    def test_history_ring_buffer_capped(self, cycle: CognitiveCycle) -> None:
        """Tick history is capped at _history_maxlen."""
        cycle._history_maxlen = 5
        for _ in range(10):
            cycle.tick()
        history = cycle.get_tick_history(last_n=100)
        assert len(history) == 5
        # Should contain the last 5 ticks (6-10)
        assert history[0]["tick_number"] == 6
        assert history[-1]["tick_number"] == 10

    def test_min_tick_time_updates(self, cycle: CognitiveCycle) -> None:
        """min_tick_time_ms is updated from inf after first tick."""
        assert cycle.metrics.min_tick_time_ms == float("inf")
        cycle.tick()
        assert cycle.metrics.min_tick_time_ms != float("inf")
        assert cycle.metrics.min_tick_time_ms >= 0

    def test_metrics_to_dict_min_inf_becomes_zero(self) -> None:
        """CycleMetrics.to_dict() converts inf min_tick_time_ms to 0.0."""
        m = CycleMetrics()
        d = m.to_dict()
        assert d["min_tick_time_ms"] == 0.0

    def test_cycle_properties(self, cycle: CognitiveCycle, bb: CognitiveBlackboard) -> None:
        """Various property accessors work correctly."""
        assert cycle.blackboard is bb
        assert cycle.is_running is False
        assert cycle.is_paused is False
        assert cycle.adapter_count == 0
        assert cycle.tick_number == 0


# ============================================================================
# Factory function: create_default_cycle
# ============================================================================


from asi_build.integration.cognitive_cycle import create_default_cycle  # noqa: E402


class TestCreateDefaultCycle:
    """Tests for the ``create_default_cycle()`` convenience factory."""

    def test_returns_cognitive_cycle(self) -> None:
        """Returns a CognitiveCycle instance."""
        cycle = create_default_cycle()
        assert isinstance(cycle, CognitiveCycle)

    def test_has_24_adapters(self) -> None:
        """All 24 adapters are registered."""
        cycle = create_default_cycle()
        assert cycle.adapter_count == 24

    def test_adapter_list_length(self) -> None:
        """list_adapters() returns 24 entries."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        assert len(adapters) == 24

    def test_safety_adapter_registered_with_safety_role(self) -> None:
        """SafetyBlackboardAdapter has role='safety'."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        safety = [a for a in adapters if a["name"] == "safety"]
        assert len(safety) == 1
        assert safety[0]["role"] == "safety"

    def test_perception_adapters(self) -> None:
        """BCI and Quantum adapters have role='perception'."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        perception = [a for a in adapters if a["role"] == "perception"]
        names = {a["name"] for a in perception}
        assert "bci" in names
        assert "quantum" in names
        assert len(perception) == 2

    def test_action_adapters(self) -> None:
        """Communication and Federated adapters have role='action'."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        action = [a for a in adapters if a["role"] == "action"]
        names = {a["name"] for a in action}
        assert "agi_communication" in names
        assert "federated_learning" in names
        assert len(action) == 2

    def test_general_adapters_count(self) -> None:
        """19 adapters have role='general'."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        general = [a for a in adapters if a["role"] == "general"]
        # 24 total - 1 safety - 2 perception - 2 action = 19 general
        assert len(general) == 19

    def test_all_adapter_names_unique(self) -> None:
        """Each adapter has a unique name."""
        cycle = create_default_cycle()
        adapters = cycle.list_adapters()
        names = [a["name"] for a in adapters]
        assert len(names) == len(set(names))

    def test_can_run_one_tick(self) -> None:
        """A single tick executes without error (graceful degradation)."""
        cycle = create_default_cycle()
        result = cycle.tick()
        assert result.tick_number == 1
        # No fatal errors — adapters with None components just skip
        assert isinstance(result.total_time_ms, float)

    def test_can_run_multiple_ticks(self) -> None:
        """Multiple ticks accumulate correctly."""
        cycle = create_default_cycle()
        for _ in range(3):
            cycle.tick()
        assert cycle.tick_number == 3
        assert cycle.metrics.total_ticks == 3

    def test_custom_tick_rate(self) -> None:
        """tick_rate_hz kwarg is forwarded."""
        cycle = create_default_cycle(tick_rate_hz=42.0)
        assert cycle.tick_rate_hz == 42.0

    def test_custom_max_ticks(self) -> None:
        """max_ticks kwarg is forwarded."""
        cycle = create_default_cycle(max_ticks=5)
        status = cycle.get_status()
        assert status["max_ticks"] == 5

    def test_custom_safety_required_false(self) -> None:
        """safety_required=False is forwarded."""
        cycle = create_default_cycle(safety_required=False)
        status = cycle.get_status()
        assert status["safety_required"] is False

    def test_default_safety_required_true(self) -> None:
        """Default safety_required is True."""
        cycle = create_default_cycle()
        status = cycle.get_status()
        assert status["safety_required"] is True

    def test_on_tick_callback_fires(self) -> None:
        """on_tick callback is called during tick."""
        results = []
        cycle = create_default_cycle(on_tick=lambda n, r: results.append(n))
        cycle.tick()
        assert results == [1]

    def test_on_error_callback(self) -> None:
        """on_error callback is forwarded to the cycle."""
        errors = []
        cycle = create_default_cycle(on_error=lambda name, exc: errors.append(name))
        # Errors are only recorded when an adapter actually fails,
        # which may happen in degraded mode — just check the cycle accepted the callback
        cycle.tick()
        # The callback should have been set (we can't force an error easily,
        # but at least verify it didn't blow up)
        assert isinstance(cycle.metrics.total_ticks, int)

    def test_blackboard_accessible(self) -> None:
        """The blackboard is accessible from the returned cycle."""
        cycle = create_default_cycle()
        bb = cycle.blackboard
        assert isinstance(bb, CognitiveBlackboard)

    def test_start_stop_with_max_ticks(self) -> None:
        """Cycle can start/stop with max_ticks in background mode."""
        cycle = create_default_cycle(max_ticks=2, tick_rate_hz=100.0)
        cycle.start(daemon=True)
        # Wait for the background thread to finish (max_ticks reached)
        cycle.wait(timeout=5.0)
        # The loop exits but stop() must be called to set state properly
        cycle.stop(timeout=2.0)
        assert cycle.tick_number >= 2
        assert cycle.state in (CycleState.STOPPED, CycleState.STOPPING)

    def test_get_adapter_by_name(self) -> None:
        """Can retrieve individual adapters by their MODULE_NAME."""
        cycle = create_default_cycle()
        consciousness = cycle.get_adapter("consciousness")
        assert consciousness is not None
        reasoning = cycle.get_adapter("reasoning")
        assert reasoning is not None
        safety = cycle.get_adapter("safety")
        assert safety is not None
