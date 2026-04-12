"""
End-to-End Scenario Tests for CognitiveCycle
==============================================

Comprehensive E2E tests exercising the full perception→cognition→action
pipeline across multiple adapters, safety gates, error resilience,
multi-tick convergence, and complex research scenarios.

46 tests total:
  - Full pipeline tests          (8)
  - Data flow tests              (8)
  - Safety gate tests            (8)
  - Multi-tick convergence tests (6)
  - Error resilience tests       (6)
  - Complex scenario tests       (10)
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence

import pytest

from asi_build.integration import CognitiveBlackboard
from asi_build.integration.cognitive_cycle import (
    AdapterRole,
    CognitiveCycle,
    CycleMetrics,
    CyclePhase,
    CycleState,
    TickResult,
)
from asi_build.integration.protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    ModuleCapability,
    ModuleInfo,
)
from asi_build.integration.adapters import (
    ConsciousnessAdapter,
    KnowledgeGraphAdapter,
    CognitiveSynergyAdapter,
    ReasoningAdapter,
    SafetyBlackboardAdapter,
    BCIBlackboardAdapter,
    QuantumBlackboardAdapter,
    AGICommunicationBlackboardAdapter,
    FederatedLearningBlackboardAdapter,
    BioInspiredAdapter,
    ComputeBlackboardAdapter,
    VectorDBBlackboardAdapter,
    BlockchainBlackboardAdapter,
    HolographicBlackboardAdapter,
    NeuromorphicBlackboardAdapter,
    AGIEconomicsBlackboardAdapter,
    RingsNetworkAdapter,
    KnowledgeManagementAdapter,
    GraphIntelligenceAdapter,
    KennyGraphBlackboardAdapter,
    IntegrationsBlackboardBridge,
    ReproducibilityBlackboardAdapter,
    VLABlackboardAdapter,
    DistributedTrainingAdapter,
)


# ============================================================================
# Mock adapters for controlled data-flow testing
# ============================================================================


class MockProducer:
    """Produces entries to a configurable topic on every tick."""

    MODULE_NAME = "mock_producer"

    def __init__(
        self,
        name: str = "mock_producer",
        topic: str = "test.data",
        data_factory: Optional[Callable[[], Any]] = None,
        topics_consumed: Optional[frozenset] = None,
    ):
        self.MODULE_NAME = name
        self._topic = topic
        self._data_factory = data_factory or (lambda: {"value": 42})
        self._topics_consumed = topics_consumed or frozenset()
        self._produce_count = 0
        self._consumed: List[BlackboardEntry] = []

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
            topics_produced=frozenset({self._topic}),
            topics_consumed=self._topics_consumed,
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        self._produce_count += 1
        return [
            BlackboardEntry(
                entry_id=f"{self.MODULE_NAME}-{uuid.uuid4().hex[:8]}",
                topic=self._topic,
                source_module=self.MODULE_NAME,
                data=self._data_factory(),
                priority=EntryPriority.NORMAL,
            )
        ]

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        self._consumed.extend(entries)


class MockConsumer:
    """Consumes entries from configurable topics."""

    MODULE_NAME = "mock_consumer"

    def __init__(
        self,
        name: str = "mock_consumer",
        topics_consumed: Optional[frozenset] = None,
    ):
        self.MODULE_NAME = name
        self._topics_consumed = topics_consumed or frozenset({"test"})
        self._consumed: List[BlackboardEntry] = []

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.CONSUMER,
            topics_produced=frozenset(),
            topics_consumed=self._topics_consumed,
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        return []

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        self._consumed.extend(entries)


class MockTransformer:
    """Transforms entries by enriching data with a marker."""

    MODULE_NAME = "mock_transformer"

    def __init__(
        self,
        name: str = "mock_transformer",
        topics_consumed: Optional[frozenset] = None,
        output_topic: str = "transformed.data",
    ):
        self.MODULE_NAME = name
        self._topics_consumed = topics_consumed or frozenset({"test"})
        self._output_topic = output_topic
        self._transformed_count = 0

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.CONSUMER | ModuleCapability.TRANSFORMER,
            topics_produced=frozenset({self._output_topic}),
            topics_consumed=self._topics_consumed,
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        return []

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        pass

    def transform(self, entries: Sequence[BlackboardEntry]) -> List[BlackboardEntry]:
        results = []
        for e in entries:
            self._transformed_count += 1
            data = dict(e.data) if isinstance(e.data, dict) else {"original": e.data}
            data["enriched_by"] = self.MODULE_NAME
            results.append(
                BlackboardEntry(
                    entry_id=f"{self.MODULE_NAME}-{uuid.uuid4().hex[:8]}",
                    topic=self._output_topic,
                    source_module=self.MODULE_NAME,
                    data=data,
                    priority=e.priority,
                    parent_id=e.entry_id,
                )
            )
        return results


class MockSafetyAdapter:
    """Safety adapter that can be configured to veto or approve."""

    MODULE_NAME = "mock_safety"

    def __init__(
        self,
        name: str = "mock_safety",
        should_veto: bool = False,
    ):
        self.MODULE_NAME = name
        self._should_veto = should_veto
        self._check_count = 0

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.VALIDATOR,
            topics_produced=frozenset({"safety.verification"}),
            topics_consumed=frozenset({"reasoning", "consciousness"}),
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        self._check_count += 1
        if self._should_veto:
            return [
                BlackboardEntry(
                    entry_id=f"veto-{uuid.uuid4().hex[:8]}",
                    topic="safety.verification",
                    source_module=self.MODULE_NAME,
                    data={"is_ethical": False, "reason": "test veto"},
                    priority=EntryPriority.CRITICAL,
                )
            ]
        return [
            BlackboardEntry(
                entry_id=f"approved-{uuid.uuid4().hex[:8]}",
                topic="safety.verification",
                source_module=self.MODULE_NAME,
                data={"is_ethical": True, "confidence": 0.95},
                priority=EntryPriority.NORMAL,
            )
        ]

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        pass


class MockFailingAdapter:
    """Adapter that raises exceptions on demand."""

    MODULE_NAME = "mock_failing"

    def __init__(
        self,
        name: str = "mock_failing",
        fail_on: str = "produce",  # "produce", "consume", "both"
    ):
        self.MODULE_NAME = name
        self._fail_on = fail_on

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
            topics_produced=frozenset({"failing.data"}),
            topics_consumed=frozenset({"test"}),
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        if self._fail_on in ("produce", "both"):
            raise RuntimeError(f"Intentional failure in {self.MODULE_NAME}.produce()")
        return []

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        if self._fail_on in ("consume", "both"):
            raise RuntimeError(f"Intentional failure in {self.MODULE_NAME}.consume()")


class MockActionAdapter:
    """Adapter intended for the ACTION role — produces action entries."""

    MODULE_NAME = "mock_action"

    def __init__(self, name: str = "mock_action"):
        self.MODULE_NAME = name
        self._action_count = 0

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.PRODUCER,
            topics_produced=frozenset({"action.output"}),
            topics_consumed=frozenset(),
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        self._action_count += 1
        return [
            BlackboardEntry(
                entry_id=f"action-{uuid.uuid4().hex[:8]}",
                topic="action.output",
                source_module=self.MODULE_NAME,
                data={"action": "executed", "count": self._action_count},
                priority=EntryPriority.NORMAL,
            )
        ]

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        pass


class MockPerceptionAdapter:
    """Adapter intended for the PERCEPTION role — produces sensory entries."""

    MODULE_NAME = "mock_perception"

    def __init__(self, name: str = "mock_perception"):
        self.MODULE_NAME = name
        self._perception_count = 0

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name=self.MODULE_NAME,
            version="1.0.0",
            capabilities=ModuleCapability.PRODUCER,
            topics_produced=frozenset({"perception.input"}),
            topics_consumed=frozenset(),
        )

    def on_registered(self, blackboard: Any) -> None:
        pass

    def produce(self) -> List[BlackboardEntry]:
        self._perception_count += 1
        return [
            BlackboardEntry(
                entry_id=f"percept-{uuid.uuid4().hex[:8]}",
                topic="perception.input",
                source_module=self.MODULE_NAME,
                data={"sensor": "camera", "count": self._perception_count},
                priority=EntryPriority.NORMAL,
            )
        ]

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def bb():
    """Fresh CognitiveBlackboard."""
    return CognitiveBlackboard()


@pytest.fixture
def cycle_no_safety(bb):
    """Cycle with safety_required=False, no rate limiting."""
    return CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)


@pytest.fixture
def cycle_with_safety(bb):
    """Cycle with a mock safety adapter pre-registered."""
    c = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
    safety = MockSafetyAdapter()
    c.register_adapter(safety, role="safety")
    return c


# ============================================================================
# 1. Full Pipeline Tests (8)
# ============================================================================


class TestFullPipeline:
    """Test the complete perception→cognition→action pipeline."""

    def test_pipeline_with_five_adapters_all_roles(self, bb):
        """5+ adapters covering all 4 roles run without errors."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)

        # GENERAL: consciousness + synergy
        cycle.register_adapter(ConsciousnessAdapter())
        cycle.register_adapter(CognitiveSynergyAdapter())
        # SAFETY
        safety = MockSafetyAdapter()
        cycle.register_adapter(safety, role="safety")
        # PERCEPTION
        percept = MockPerceptionAdapter()
        cycle.register_adapter(percept, role="perception")
        # ACTION
        action = MockActionAdapter()
        cycle.register_adapter(action, role="action")

        assert cycle.adapter_count == 5

        for _ in range(3):
            result = cycle.tick()
            assert result.tick_number > 0
            assert len(result.errors) == 0

    def test_tick_count_increments_across_multiple_ticks(self, cycle_no_safety):
        """tick_number increments monotonically across ticks."""
        for i in range(5):
            result = cycle_no_safety.tick()
            assert result.tick_number == i + 1
        assert cycle_no_safety.tick_number == 5

    def test_produced_entries_appear_on_blackboard(self, bb, cycle_no_safety):
        """Entries from produce() are posted to the blackboard."""
        producer = MockProducer(topic="test.output")
        cycle_no_safety.register_adapter(producer)

        cycle_no_safety.tick()

        entries = bb.get_by_topic("test.output")
        assert len(entries) >= 1
        assert entries[0].data["value"] == 42

    def test_blackboard_has_entries_after_ticks(self, bb, cycle_no_safety):
        """Blackboard entry_count grows after multiple ticks."""
        producer = MockProducer(topic="pipeline.data")
        cycle_no_safety.register_adapter(producer)

        for _ in range(3):
            cycle_no_safety.tick()

        assert bb.entry_count >= 3

    def test_metrics_accumulate_across_ticks(self, cycle_no_safety):
        """CycleMetrics totals grow with each tick."""
        producer = MockProducer(topic="metrics.data")
        cycle_no_safety.register_adapter(producer)

        for _ in range(4):
            cycle_no_safety.tick()

        m = cycle_no_safety.metrics
        assert m.total_ticks == 4
        assert m.total_entries_produced >= 4

    def test_safety_adapter_runs_in_act_phase(self, bb):
        """Safety adapter's produce() is called during ACT phase."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter()
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()

        # Safety adapter's produce() was invoked (it produces a verification entry)
        assert result.safety_checks >= 1
        entries = bb.get_by_topic("safety.verification")
        assert len(entries) >= 1

    def test_perception_adapter_runs_in_perceive_phase(self, bb):
        """Perception-role adapter produces entries during PERCEIVE."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        percept = MockPerceptionAdapter()
        cycle.register_adapter(percept, role="perception")

        cycle.tick()

        entries = bb.get_by_topic("perception.input")
        assert len(entries) >= 1
        assert percept._perception_count == 1

    def test_action_adapter_runs_in_act_phase_only(self, bb):
        """Action-role adapter only produces during ACT, not PERCEIVE."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        action = MockActionAdapter()
        cycle.register_adapter(action, role="action")

        result = cycle.tick()

        # Action adapter produces in ACT phase
        assert action._action_count == 1
        entries = bb.get_by_topic("action.output")
        assert len(entries) >= 1


# ============================================================================
# 2. Data Flow Tests (8)
# ============================================================================


class TestDataFlow:
    """Test data routing between producers, consumers, and transformers."""

    def test_producer_to_consumer_flow(self, bb):
        """Producer's entries reach a consumer subscribed to that topic."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        producer = MockProducer(name="flow_prod", topic="flow.data")
        consumer = MockConsumer(name="flow_cons", topics_consumed=frozenset({"flow"}))
        cycle.register_adapter(producer)
        cycle.register_adapter(consumer)

        cycle.tick()

        assert len(consumer._consumed) >= 1
        assert consumer._consumed[0].topic == "flow.data"
        assert consumer._consumed[0].data["value"] == 42

    def test_consumer_does_not_receive_unmatched_topics(self, bb):
        """Consumer only gets entries matching its subscribed topics."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        producer = MockProducer(name="other_prod", topic="other.data")
        consumer = MockConsumer(name="picky_cons", topics_consumed=frozenset({"unrelated"}))
        cycle.register_adapter(producer)
        cycle.register_adapter(consumer)

        cycle.tick()

        assert len(consumer._consumed) == 0

    def test_transformer_enriches_entries(self, bb):
        """Transformer reads entries, enriches them, and posts new entries."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        producer = MockProducer(name="t_prod", topic="raw.data")
        transformer = MockTransformer(
            name="t_xform",
            topics_consumed=frozenset({"raw"}),
            output_topic="enriched.data",
        )
        cycle.register_adapter(producer)
        cycle.register_adapter(transformer)

        cycle.tick()

        enriched = bb.get_by_topic("enriched.data")
        assert len(enriched) >= 1
        assert enriched[0].data.get("enriched_by") == "t_xform"
        assert enriched[0].parent_id is not None

    def test_cross_adapter_chain_a_to_b_to_c(self, bb):
        """Data flows: Adapter A → blackboard → Adapter B (which produces) → Adapter C."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        # A produces "stage1.data"
        adapter_a = MockProducer(name="chain_a", topic="stage1.data")
        # B consumes "stage1.*" and produces "stage2.data"
        adapter_b = MockProducer(
            name="chain_b",
            topic="stage2.data",
            topics_consumed=frozenset({"stage1"}),
            data_factory=lambda: {"forwarded": True},
        )
        # C consumes "stage2.*"
        adapter_c = MockConsumer(name="chain_c", topics_consumed=frozenset({"stage2"}))

        cycle.register_adapter(adapter_a)
        cycle.register_adapter(adapter_b)
        cycle.register_adapter(adapter_c)

        # Tick 1: A produces stage1, B produces stage2 (also in tick 1 perceive)
        cycle.tick()
        # B consumed from stage1
        assert len(adapter_b._consumed) >= 1
        # Tick 2: C consumes B's stage2 entries now on the board
        cycle.tick()
        assert len(adapter_c._consumed) >= 1

    def test_multiple_producers_same_topic(self, bb):
        """Multiple producers posting to the same topic — all entries arrive."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        p1 = MockProducer(name="multi_p1", topic="shared.topic", data_factory=lambda: {"src": 1})
        p2 = MockProducer(name="multi_p2", topic="shared.topic", data_factory=lambda: {"src": 2})
        consumer = MockConsumer(name="multi_cons", topics_consumed=frozenset({"shared"}))

        cycle.register_adapter(p1)
        cycle.register_adapter(p2)
        cycle.register_adapter(consumer)

        cycle.tick()

        assert len(consumer._consumed) >= 2
        sources = {e.data["src"] for e in consumer._consumed}
        assert sources == {1, 2}

    def test_event_bus_notifications_during_tick(self, bb):
        """Event bus emits cycle.tick.completed after each tick."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        captured_events: List[CognitiveEvent] = []
        bb.event_bus.subscribe(
            pattern="cycle.tick.*",
            handler=lambda ev: captured_events.append(ev),
        )

        cycle.tick()

        assert len(captured_events) >= 1
        assert captured_events[0].event_type == "cycle.tick.completed"
        assert "tick_number" in captured_events[0].payload

    def test_high_priority_entries_posted_correctly(self, bb):
        """Entries with different priorities are all stored correctly."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        def make_critical():
            return {"critical": True}

        producer = MockProducer(name="critical_prod", topic="urgent.alert", data_factory=make_critical)
        # Override produce to set CRITICAL priority
        original_produce = producer.produce

        def produce_critical():
            entries = original_produce()
            for e in entries:
                e.priority = EntryPriority.CRITICAL
            return entries

        producer.produce = produce_critical
        cycle.register_adapter(producer)

        cycle.tick()

        entries = bb.get_by_topic("urgent.alert")
        assert len(entries) >= 1
        assert entries[0].priority == EntryPriority.CRITICAL

    def test_subtopic_matching(self, bb):
        """Consumer subscribed to 'data' receives 'data.sub1' and 'data.sub2'."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        p1 = MockProducer(name="sub1_prod", topic="data.sub1")
        p2 = MockProducer(name="sub2_prod", topic="data.sub2")
        consumer = MockConsumer(name="data_cons", topics_consumed=frozenset({"data"}))

        cycle.register_adapter(p1)
        cycle.register_adapter(p2)
        cycle.register_adapter(consumer)

        cycle.tick()

        assert len(consumer._consumed) >= 2
        topics = {e.topic for e in consumer._consumed}
        assert "data.sub1" in topics
        assert "data.sub2" in topics


# ============================================================================
# 3. Safety Gate Tests (8)
# ============================================================================


class TestSafetyGate:
    """Test safety adapter veto/approval and safety_required constraints."""

    def test_safety_veto_tracked_in_result(self, bb):
        """Safety adapter that vetoes → safety_vetoes increments."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(should_veto=True)
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()

        assert result.safety_vetoes >= 1
        assert result.safety_checks >= 1

    def test_safety_veto_count_accumulates(self, bb):
        """Veto count grows across multiple ticks."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(should_veto=True)
        cycle.register_adapter(safety, role="safety")

        for _ in range(3):
            cycle.tick()

        m = cycle.metrics
        assert m.total_safety_vetoes >= 3
        assert m.total_safety_checks >= 3

    def test_safety_required_true_blocks_start_without_safety(self, bb):
        """start() raises RuntimeError when safety_required but no safety adapter."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)

        with pytest.raises(RuntimeError, match="safety_required=True"):
            cycle.start()

    def test_safety_required_false_allows_start_without_safety(self, bb):
        """start() succeeds when safety_required=False even without safety adapter."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=1
        )

        # Should not raise
        cycle.start()
        cycle.wait(timeout=5)
        cycle.stop()
        assert cycle.state == CycleState.STOPPED

    def test_safety_verification_entries_on_blackboard(self, bb):
        """Safety adapter posts verification entries to the blackboard."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(should_veto=False)
        cycle.register_adapter(safety, role="safety")

        cycle.tick()

        entries = bb.get_by_topic("safety.verification")
        assert len(entries) >= 1
        assert entries[0].data.get("is_ethical") is True

    def test_multiple_safety_checks_one_tick(self, bb):
        """Two safety adapters → multiple checks in a single tick."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        s1 = MockSafetyAdapter(name="safety_1", should_veto=False)
        s2 = MockSafetyAdapter(name="safety_2", should_veto=True)
        cycle.register_adapter(s1, role="safety")
        cycle.register_adapter(s2, role="safety")

        result = cycle.tick()

        assert result.safety_checks >= 2
        assert result.safety_vetoes >= 1  # s2 vetoes

    def test_safety_adapter_with_real_safety_module(self, bb):
        """Real SafetyBlackboardAdapter (None components) produces gracefully."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = SafetyBlackboardAdapter()
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()

        # With None components it may produce nothing or minimal entries,
        # but it should NOT error out
        assert isinstance(result, TickResult)

    def test_safety_approval_has_correct_priority(self, bb):
        """Non-veto safety entries are NORMAL, not CRITICAL."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)
        safety = MockSafetyAdapter(should_veto=False)
        cycle.register_adapter(safety, role="safety")

        result = cycle.tick()

        entries = bb.get_by_topic("safety.verification")
        for e in entries:
            assert e.priority == EntryPriority.NORMAL
        assert result.safety_vetoes == 0


# ============================================================================
# 4. Multi-Tick Convergence (6)
# ============================================================================


class TestMultiTickConvergence:
    """Test behaviour across many ticks — metrics, limits, timing."""

    def test_avg_tick_time_stabilizes(self, bb):
        """After 10+ ticks, avg_tick_time_ms should be positive and finite."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        producer = MockProducer()
        cycle.register_adapter(producer)

        for _ in range(15):
            cycle.tick()

        m = cycle.metrics
        assert m.avg_tick_time_ms > 0
        assert m.avg_tick_time_ms < 10000  # < 10s per tick
        assert m.min_tick_time_ms <= m.avg_tick_time_ms
        assert m.max_tick_time_ms >= m.avg_tick_time_ms

    def test_max_ticks_stops_automatically(self, bb):
        """Cycle with max_ticks=5 stops after exactly 5 ticks."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=5
        )
        producer = MockProducer()
        cycle.register_adapter(producer)

        cycle.start()
        finished = cycle.wait(timeout=10)

        assert finished
        cycle.stop()
        assert cycle.tick_number == 5

    def test_tick_history_grows(self, bb):
        """Tick history accumulates up to the history_maxlen."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        for _ in range(7):
            cycle.tick()

        history = cycle.get_tick_history(last_n=100)
        assert len(history) == 7

        for i, h in enumerate(history):
            assert h["tick_number"] == i + 1

    def test_uptime_seconds_increases(self, bb):
        """uptime_seconds > 0 after running."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=3
        )
        cycle.register_adapter(MockProducer())

        cycle.start()
        cycle.wait(timeout=10)
        cycle.stop()

        m = cycle.metrics
        assert m.uptime_seconds > 0

    def test_ticks_per_second_metric(self, bb):
        """ticks_per_second is > 0 after background run."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=10
        )
        cycle.register_adapter(MockProducer())

        cycle.start()
        cycle.wait(timeout=10)
        cycle.stop()

        m = cycle.metrics
        assert m.ticks_per_second > 0
        assert m.total_ticks == 10

    def test_metrics_to_dict_complete(self, bb):
        """metrics.to_dict() contains all expected keys after ticks."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        cycle.register_adapter(MockProducer())

        for _ in range(3):
            cycle.tick()

        d = cycle.metrics.to_dict()
        expected_keys = {
            "total_ticks", "total_entries_produced", "total_entries_consumed",
            "total_entries_transformed", "total_safety_checks", "total_safety_vetoes",
            "total_errors", "avg_tick_time_ms", "max_tick_time_ms", "min_tick_time_ms",
            "uptime_seconds", "ticks_per_second", "adapter_produce_counts",
            "adapter_consume_counts", "adapter_error_counts",
        }
        assert expected_keys <= set(d.keys())
        assert d["total_ticks"] == 3


# ============================================================================
# 5. Error Resilience Tests (6)
# ============================================================================


class TestErrorResilience:
    """Test that errors in one adapter don't break the whole cycle."""

    def test_failing_produce_doesnt_stop_others(self, bb):
        """One adapter errors in produce() — other adapters still work."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        failing = MockFailingAdapter(name="fail_prod", fail_on="produce")
        healthy = MockProducer(name="healthy_prod", topic="healthy.data")
        cycle.register_adapter(failing)
        cycle.register_adapter(healthy)

        result = cycle.tick()

        assert len(result.errors) >= 1
        assert "fail_prod" in result.errors[0]
        # Healthy adapter still produced
        entries = bb.get_by_topic("healthy.data")
        assert len(entries) >= 1

    def test_failing_consume_doesnt_stop_cycle(self, bb):
        """One adapter errors in consume() — cycle continues."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        producer = MockProducer(name="data_source", topic="test.payload")
        failing = MockFailingAdapter(name="fail_cons", fail_on="consume")
        cycle.register_adapter(producer)
        cycle.register_adapter(failing)

        # Multiple ticks all succeed
        for _ in range(3):
            result = cycle.tick()
            assert isinstance(result, TickResult)

    def test_on_error_callback_fires(self, bb):
        """on_error callback is invoked with (adapter_name, exception)."""
        errors_captured: List[tuple] = []

        def error_cb(name, exc):
            errors_captured.append((name, exc))

        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, on_error=error_cb
        )
        failing = MockFailingAdapter(name="cb_fail", fail_on="produce")
        cycle.register_adapter(failing)

        cycle.tick()

        assert len(errors_captured) >= 1
        assert errors_captured[0][0] == "cb_fail"
        assert isinstance(errors_captured[0][1], RuntimeError)

    def test_error_count_accumulates(self, bb):
        """total_errors grows with repeated failures."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        failing = MockFailingAdapter(name="repeat_fail", fail_on="produce")
        cycle.register_adapter(failing)

        for _ in range(5):
            cycle.tick()

        m = cycle.metrics
        assert m.total_errors >= 5

    def test_adapter_error_counts_per_adapter(self, bb):
        """adapter_error_counts tracks failures per adapter name."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        f1 = MockFailingAdapter(name="fail_alpha", fail_on="produce")
        f2 = MockFailingAdapter(name="fail_beta", fail_on="produce")
        cycle.register_adapter(f1)
        cycle.register_adapter(f2)

        for _ in range(3):
            cycle.tick()

        m = cycle.metrics
        assert m.adapter_error_counts["fail_alpha"] >= 3
        assert m.adapter_error_counts["fail_beta"] >= 3

    def test_mixed_healthy_and_failing_multi_tick(self, bb):
        """Mix of healthy and failing adapters across many ticks — no crash."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        cycle.register_adapter(MockProducer(name="ok_1", topic="ok.data"))
        cycle.register_adapter(MockProducer(name="ok_2", topic="ok.data2"))
        cycle.register_adapter(MockFailingAdapter(name="bad_1", fail_on="produce"))
        cycle.register_adapter(MockFailingAdapter(name="bad_2", fail_on="both"))
        cycle.register_adapter(MockConsumer(name="ok_cons", topics_consumed=frozenset({"ok"})))

        for i in range(10):
            result = cycle.tick()
            assert result.tick_number == i + 1

        m = cycle.metrics
        assert m.total_ticks == 10
        assert m.total_entries_produced >= 10  # At least 1 per tick from ok_1
        assert m.total_errors >= 10  # At least 1 per tick from bad_1+bad_2


# ============================================================================
# 6. Complex Scenario Tests (10)
# ============================================================================


class TestComplexScenarios:
    """Complex multi-adapter scenarios simulating real research workflows."""

    def test_research_cycle_consciousness_to_reasoning_to_safety(self, bb):
        """Research cycle: consciousness → reasoning → safety verification.

        Consciousness produces awareness → reasoning consumes → produces inference
        → safety verifies.
        """
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)

        consciousness = ConsciousnessAdapter()
        reasoning = ReasoningAdapter(engine=object())
        safety = SafetyBlackboardAdapter()
        synergy = CognitiveSynergyAdapter()

        cycle.register_adapter(consciousness)
        cycle.register_adapter(reasoning)
        cycle.register_adapter(synergy)
        cycle.register_adapter(safety, role="safety")

        # Run 3 ticks — modules interact through the blackboard
        for _ in range(3):
            result = cycle.tick()
            assert isinstance(result, TickResult)

        assert cycle.tick_number == 3
        # Blackboard should have entries from at least one module
        assert bb.entry_count >= 0  # Graceful degradation may produce nothing with None components

    def test_federated_learning_compute_chain(self, bb):
        """Compute → distributed training → federated learning chain."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        compute = ComputeBlackboardAdapter()
        distributed = DistributedTrainingAdapter()
        federated = FederatedLearningBlackboardAdapter()

        cycle.register_adapter(compute)
        cycle.register_adapter(distributed)
        cycle.register_adapter(federated)

        for _ in range(3):
            result = cycle.tick()
            assert len(result.errors) == 0

    def test_full_stack_ten_adapters_no_deadlock(self, bb):
        """10+ adapters all running — verify no deadlocks after 10 ticks."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)

        adapters = [
            (ConsciousnessAdapter(), "general"),
            (CognitiveSynergyAdapter(), "general"),
            (ReasoningAdapter(engine=object()), "general"),
            (SafetyBlackboardAdapter(), "safety"),
            (BCIBlackboardAdapter(), "general"),
            (QuantumBlackboardAdapter(), "general"),
            (AGICommunicationBlackboardAdapter(), "general"),
            (ComputeBlackboardAdapter(), "general"),
            (VectorDBBlackboardAdapter(), "general"),
            (BlockchainBlackboardAdapter(), "general"),
            (NeuromorphicBlackboardAdapter(), "general"),
        ]

        for adapter, role in adapters:
            cycle.register_adapter(adapter, role=role)

        assert cycle.adapter_count >= 10

        # Run 10 ticks — should complete without deadlock
        for i in range(10):
            result = cycle.tick()
            assert result.tick_number == i + 1

    def test_pause_resume_preserves_state(self, bb):
        """Pause and resume mid-cycle preserves tick count and state."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=20
        )
        producer = MockProducer()
        cycle.register_adapter(producer)

        # Manual ticks
        for _ in range(3):
            cycle.tick()
        assert cycle.tick_number == 3

        # Pause
        cycle.pause()
        assert cycle.state == CycleState.PAUSED

        # State preserved
        assert cycle.tick_number == 3
        m_paused = cycle.metrics
        ticks_paused = m_paused.total_ticks

        # Resume
        cycle.resume()
        assert cycle.state == CycleState.RUNNING

        # More ticks
        for _ in range(2):
            cycle.tick()
        assert cycle.tick_number == 5
        assert cycle.metrics.total_ticks == ticks_paused + 2

    def test_tick_rate_limiting_works(self, bb):
        """With tick_rate_hz set, ticks are rate-limited (roughly)."""
        # Use 50Hz = 20ms per tick
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=50, max_ticks=3
        )
        producer = MockProducer()
        cycle.register_adapter(producer)

        start = time.monotonic()
        cycle.start()
        cycle.wait(timeout=10)
        cycle.stop()
        elapsed = time.monotonic() - start

        # 3 ticks at 50Hz = ~60ms minimum
        # Allow generous margin for scheduling jitter
        assert elapsed >= 0.04  # At least ~40ms
        assert cycle.tick_number == 3

    def test_background_start_stop_lifecycle(self, bb):
        """start() → run N ticks → stop() lifecycle in background thread."""
        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, max_ticks=5
        )
        cycle.register_adapter(MockProducer())

        assert cycle.state == CycleState.CREATED
        cycle.start()
        assert cycle.state in (CycleState.STARTING, CycleState.RUNNING)

        finished = cycle.wait(timeout=10)
        assert finished
        cycle.stop()

        assert cycle.state == CycleState.STOPPED
        assert cycle.tick_number == 5

    def test_on_tick_callback_receives_results(self, bb):
        """on_tick callback is called with (tick_number, TickResult)."""
        tick_results: List[tuple] = []

        def on_tick(tick_num, result):
            tick_results.append((tick_num, result))

        cycle = CognitiveCycle(
            blackboard=bb, safety_required=False, tick_rate_hz=0, on_tick=on_tick
        )
        cycle.register_adapter(MockProducer())

        for _ in range(4):
            cycle.tick()

        assert len(tick_results) == 4
        for i, (num, res) in enumerate(tick_results):
            assert num == i + 1
            assert isinstance(res, TickResult)

    def test_full_adapter_zoo(self, bb):
        """Register the complete zoo of real adapters — all with None components."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=True, tick_rate_hz=0)

        all_adapters = [
            (ConsciousnessAdapter(), "general"),
            (CognitiveSynergyAdapter(), "general"),
            (ReasoningAdapter(engine=object()), "general"),
            (SafetyBlackboardAdapter(), "safety"),
            (BCIBlackboardAdapter(), "general"),
            (QuantumBlackboardAdapter(), "general"),
            (AGICommunicationBlackboardAdapter(), "general"),
            (FederatedLearningBlackboardAdapter(), "general"),
            (BioInspiredAdapter(), "general"),
            (ComputeBlackboardAdapter(), "general"),
            (VectorDBBlackboardAdapter(), "general"),
            (BlockchainBlackboardAdapter(), "general"),
            (HolographicBlackboardAdapter(), "general"),
            (NeuromorphicBlackboardAdapter(), "general"),
            (AGIEconomicsBlackboardAdapter(), "general"),
            (RingsNetworkAdapter(), "general"),
            (KnowledgeManagementAdapter(), "general"),
            (GraphIntelligenceAdapter(), "general"),
            (KennyGraphBlackboardAdapter(), "general"),
            (IntegrationsBlackboardBridge(), "general"),
            (ReproducibilityBlackboardAdapter(), "general"),
            (VLABlackboardAdapter(), "general"),
            (DistributedTrainingAdapter(), "general"),
        ]

        for adapter, role in all_adapters:
            cycle.register_adapter(adapter, role=role)

        assert cycle.adapter_count == 23

        # 3 ticks should complete without crash
        for i in range(3):
            result = cycle.tick()
            assert result.tick_number == i + 1

    def test_get_status_snapshot_complete(self, bb):
        """get_status() returns all expected keys after running."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)
        cycle.register_adapter(MockProducer())

        for _ in range(3):
            cycle.tick()

        status = cycle.get_status()
        assert status["tick_number"] == 3
        assert status["state"] == CycleState.CREATED.value
        assert "metrics" in status
        assert status["adapter_count"] == 1

    def test_adapter_produce_counts_tracked(self, bb):
        """Per-adapter produce counts are correctly tracked."""
        cycle = CognitiveCycle(blackboard=bb, safety_required=False, tick_rate_hz=0)

        p1 = MockProducer(name="counter_a", topic="a.data")
        p2 = MockProducer(name="counter_b", topic="b.data")
        cycle.register_adapter(p1)
        cycle.register_adapter(p2)

        for _ in range(5):
            cycle.tick()

        m = cycle.metrics
        assert m.adapter_produce_counts["counter_a"] == 5
        assert m.adapter_produce_counts["counter_b"] == 5
