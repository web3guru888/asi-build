"""
Comprehensive tests for the Cognitive Integration Layer.

Tests cover:
- protocols.py: BlackboardEntry, BlackboardQuery, CognitiveEvent, ModuleInfo, enums
- events.py: EventBus pub/sub, wildcards, priorities, history, async, dead letters
- blackboard.py: CognitiveBlackboard CRUD, indexing, eviction, expiry, modules, thread safety
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import pytest

from src.asi_build.integration import (
    AsyncBlackboardConsumer,
    AsyncBlackboardProducer,
    BlackboardConsumer,
    BlackboardEntry,
    BlackboardParticipant,
    BlackboardProducer,
    BlackboardQuery,
    BlackboardTransformer,
    CognitiveBlackboard,
    CognitiveEvent,
    DeadLetter,
    EntryPriority,
    EntryStatus,
    EventBus,
    EventEmitter,
    EventListener,
    ModuleCapability,
    ModuleInfo,
    Subscription,
)


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

class MockParticipant:
    """A simple mock module implementing BlackboardParticipant."""

    def __init__(
        self,
        name: str = "mock",
        version: str = "1.0.0",
        capabilities: ModuleCapability = ModuleCapability.PRODUCER,
    ):
        self._info = ModuleInfo(
            name=name,
            version=version,
            capabilities=capabilities,
            description=f"Mock module '{name}'",
        )
        self.blackboard = None
        self.registered_count = 0

    @property
    def module_info(self) -> ModuleInfo:
        return self._info

    def on_registered(self, blackboard: Any) -> None:
        self.blackboard = blackboard
        self.registered_count += 1


class ProducerModule(MockParticipant):
    """Mock that also implements BlackboardProducer."""

    def __init__(self, name: str = "producer"):
        super().__init__(name, capabilities=ModuleCapability.PRODUCER)
        self.produce_entries: List[BlackboardEntry] = []

    def produce(self) -> Sequence[BlackboardEntry]:
        return self.produce_entries


class ConsumerModule(MockParticipant):
    """Mock that also implements BlackboardConsumer."""

    def __init__(self, name: str = "consumer"):
        super().__init__(name, capabilities=ModuleCapability.CONSUMER)
        self.consumed: List[BlackboardEntry] = []

    def consume(self, entries: Sequence[BlackboardEntry]) -> None:
        self.consumed.extend(entries)


class TransformerModule(MockParticipant):
    """Mock that also implements BlackboardTransformer."""

    def __init__(self, name: str = "transformer"):
        super().__init__(
            name,
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER | ModuleCapability.TRANSFORMER,
        )

    def transform(self, entries: Sequence[BlackboardEntry]) -> Sequence[BlackboardEntry]:
        return [
            BlackboardEntry(
                topic=e.topic + ".transformed",
                data={"original": e.data, "transformed": True},
                source_module=self.module_info.name,
                parent_id=e.entry_id,
            )
            for e in entries
        ]


class EventCapture:
    """Simple event handler that records all received events."""

    def __init__(self):
        self.events: List[CognitiveEvent] = []
        self.lock = threading.Lock()

    def __call__(self, event: CognitiveEvent) -> None:
        with self.lock:
            self.events.append(event)

    async def async_handler(self, event: CognitiveEvent) -> None:
        with self.lock:
            self.events.append(event)


def make_entry(
    topic: str = "test.data",
    data: Any = None,
    source: str = "test_module",
    confidence: float = 0.9,
    priority: EntryPriority = EntryPriority.NORMAL,
    ttl: Optional[float] = None,
    tags: frozenset = frozenset(),
) -> BlackboardEntry:
    return BlackboardEntry(
        topic=topic,
        data=data or {"value": 42},
        source_module=source,
        confidence=confidence,
        priority=priority,
        ttl_seconds=ttl,
        tags=tags,
    )


# ═══════════════════════════════════════════════════════════════════════
# PROTOCOL TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestModuleCapability:
    def test_single_capability(self):
        assert ModuleCapability.PRODUCER.name == "PRODUCER"

    def test_combined_capabilities(self):
        combo = ModuleCapability.PRODUCER | ModuleCapability.CONSUMER
        assert ModuleCapability.PRODUCER in combo
        assert ModuleCapability.CONSUMER in combo
        assert ModuleCapability.REASONER not in combo

    def test_all_flags(self):
        all_caps = (
            ModuleCapability.PRODUCER
            | ModuleCapability.CONSUMER
            | ModuleCapability.TRANSFORMER
            | ModuleCapability.REASONER
            | ModuleCapability.VALIDATOR
            | ModuleCapability.LEARNER
        )
        assert ModuleCapability.LEARNER in all_caps


class TestEntryPriority:
    def test_ordering(self):
        assert EntryPriority.LOW < EntryPriority.NORMAL
        assert EntryPriority.NORMAL < EntryPriority.HIGH
        assert EntryPriority.HIGH < EntryPriority.CRITICAL

    def test_int_comparison(self):
        assert EntryPriority.LOW == 0
        assert EntryPriority.CRITICAL == 3


class TestEntryStatus:
    def test_values(self):
        assert EntryStatus.ACTIVE.value == "active"
        assert EntryStatus.CONSUMED.value == "consumed"
        assert EntryStatus.SUPERSEDED.value == "superseded"
        assert EntryStatus.EXPIRED.value == "expired"
        assert EntryStatus.RETRACTED.value == "retracted"


class TestBlackboardEntry:
    def test_creation_defaults(self):
        entry = BlackboardEntry(
            topic="test", data={"x": 1}, source_module="mod"
        )
        assert entry.topic == "test"
        assert entry.data == {"x": 1}
        assert entry.source_module == "mod"
        assert entry.confidence == 1.0
        assert entry.priority == EntryPriority.NORMAL
        assert entry.status == EntryStatus.ACTIVE
        assert entry.ttl_seconds is None
        assert entry.tags == frozenset()
        assert entry.parent_id is None
        assert len(entry.entry_id) == 32  # UUID hex

    def test_unique_ids(self):
        e1 = make_entry()
        e2 = make_entry()
        assert e1.entry_id != e2.entry_id

    def test_ttl_not_expired(self):
        entry = make_entry(ttl=3600.0)
        assert not entry.is_expired

    def test_ttl_expired(self):
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        assert entry.is_expired

    def test_no_ttl_never_expires(self):
        entry = make_entry(ttl=None)
        entry.timestamp = 0.0  # ancient
        assert not entry.is_expired

    def test_tags_frozenset(self):
        entry = make_entry(tags=frozenset({"a", "b"}))
        assert "a" in entry.tags
        assert "c" not in entry.tags

    def test_metadata(self):
        entry = make_entry()
        entry.metadata["custom"] = "value"
        assert entry.metadata["custom"] == "value"


class TestCognitiveEvent:
    def test_creation(self):
        evt = CognitiveEvent(
            event_type="test.event",
            payload={"key": "val"},
            source="test",
        )
        assert evt.event_type == "test.event"
        assert evt.payload == {"key": "val"}
        assert evt.source == "test"
        assert len(evt.event_id) == 32

    def test_default_source(self):
        evt = CognitiveEvent(event_type="x")
        assert evt.source == "system"


class TestModuleInfo:
    def test_creation(self):
        info = ModuleInfo(
            name="consciousness",
            version="2.1.0",
            capabilities=ModuleCapability.PRODUCER | ModuleCapability.CONSUMER,
            description="Consciousness module",
            topics_produced=frozenset({"consciousness.phi", "consciousness.gwt"}),
            topics_consumed=frozenset({"reasoning.conclusion"}),
        )
        assert info.name == "consciousness"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert "consciousness.phi" in info.topics_produced

    def test_defaults(self):
        info = ModuleInfo(name="minimal")
        assert info.version == "0.0.0"
        assert info.capabilities == ModuleCapability.PRODUCER


class TestBlackboardQuery:
    def test_empty_query_matches_all(self):
        q = BlackboardQuery()
        entry = make_entry()
        assert q.matches(entry)

    def test_topic_filter(self):
        q = BlackboardQuery(topics=["consciousness"])
        assert q.matches(make_entry(topic="consciousness"))
        assert q.matches(make_entry(topic="consciousness.phi"))
        assert not q.matches(make_entry(topic="reasoning"))

    def test_source_filter(self):
        q = BlackboardQuery(source_modules=["mod_a"])
        assert q.matches(make_entry(source="mod_a"))
        assert not q.matches(make_entry(source="mod_b"))

    def test_min_confidence(self):
        q = BlackboardQuery(min_confidence=0.8)
        assert q.matches(make_entry(confidence=0.9))
        assert not q.matches(make_entry(confidence=0.7))

    def test_min_priority(self):
        q = BlackboardQuery(min_priority=EntryPriority.HIGH)
        assert q.matches(make_entry(priority=EntryPriority.HIGH))
        assert q.matches(make_entry(priority=EntryPriority.CRITICAL))
        assert not q.matches(make_entry(priority=EntryPriority.NORMAL))

    def test_tags_any(self):
        q = BlackboardQuery(tags_any={"important", "urgent"})
        assert q.matches(make_entry(tags=frozenset({"important"})))
        assert q.matches(make_entry(tags=frozenset({"urgent", "other"})))
        assert not q.matches(make_entry(tags=frozenset({"boring"})))

    def test_tags_all(self):
        q = BlackboardQuery(tags_all={"a", "b"})
        assert q.matches(make_entry(tags=frozenset({"a", "b", "c"})))
        assert not q.matches(make_entry(tags=frozenset({"a"})))

    def test_status_filter(self):
        q = BlackboardQuery(statuses={EntryStatus.ACTIVE})
        entry = make_entry()
        assert q.matches(entry)
        entry.status = EntryStatus.RETRACTED
        assert not q.matches(entry)

    def test_since_timestamp(self):
        q = BlackboardQuery(since_timestamp=time.time() - 10)
        assert q.matches(make_entry())  # just created
        old = make_entry()
        old.timestamp = time.time() - 100
        assert not q.matches(old)

    def test_expired_excluded_by_default(self):
        q = BlackboardQuery()
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        assert not q.matches(entry)

    def test_include_expired(self):
        q = BlackboardQuery(include_expired=True)
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        assert q.matches(entry)

    def test_combined_filters(self):
        q = BlackboardQuery(
            topics=["test"],
            source_modules=["mod_a"],
            min_confidence=0.5,
            min_priority=EntryPriority.NORMAL,
        )
        good = make_entry(topic="test.result", source="mod_a", confidence=0.8)
        assert q.matches(good)
        bad = make_entry(topic="test.result", source="mod_b", confidence=0.8)
        assert not q.matches(bad)


class TestProtocolCompliance:
    """Verify that mock classes satisfy protocol checks."""

    def test_participant_protocol(self):
        p = MockParticipant("test")
        assert isinstance(p, BlackboardParticipant)

    def test_producer_protocol(self):
        p = ProducerModule()
        assert isinstance(p, BlackboardProducer)

    def test_consumer_protocol(self):
        c = ConsumerModule()
        assert isinstance(c, BlackboardConsumer)

    def test_transformer_protocol(self):
        t = TransformerModule()
        assert isinstance(t, BlackboardTransformer)

    def test_non_participant(self):
        assert not isinstance("string", BlackboardParticipant)
        assert not isinstance(42, BlackboardProducer)


# ═══════════════════════════════════════════════════════════════════════
# EVENT BUS TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestEventBusSubscription:
    def test_subscribe_returns_id(self):
        bus = EventBus()
        sid = bus.subscribe("test.*", handler=lambda e: None)
        assert isinstance(sid, str)
        assert len(sid) == 32

    def test_subscribe_requires_handler(self):
        bus = EventBus()
        with pytest.raises(ValueError, match="handler"):
            bus.subscribe("test.*")

    def test_unsubscribe(self):
        bus = EventBus()
        sid = bus.subscribe("test.*", handler=lambda e: None)
        assert bus.subscription_count == 1
        assert bus.unsubscribe(sid) is True
        assert bus.subscription_count == 0

    def test_unsubscribe_nonexistent(self):
        bus = EventBus()
        assert bus.unsubscribe("nonexistent") is False

    def test_unsubscribe_all(self):
        bus = EventBus()
        bus.subscribe("a.*", handler=lambda e: None)
        bus.subscribe("b.*", handler=lambda e: None)
        bus.subscribe("a.*", handler=lambda e: None)
        removed = bus.unsubscribe_all("a.*")
        assert removed == 2
        assert bus.subscription_count == 1

    def test_unsubscribe_all_no_filter(self):
        bus = EventBus()
        bus.subscribe("a.*", handler=lambda e: None)
        bus.subscribe("b.*", handler=lambda e: None)
        removed = bus.unsubscribe_all()
        assert removed == 2
        assert bus.subscription_count == 0

    def test_get_subscriptions(self):
        bus = EventBus()
        bus.subscribe("test.*", handler=lambda e: None)
        bus.subscribe("other.*", handler=lambda e: None)
        subs = bus.get_subscriptions("test.*")
        assert len(subs) == 1
        assert subs[0].pattern == "test.*"


class TestEventBusEmit:
    def test_emit_delivers_to_matching(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test.*", handler=cap)
        bus.emit(CognitiveEvent(event_type="test.hello"))
        assert len(cap.events) == 1
        assert cap.events[0].event_type == "test.hello"

    def test_emit_does_not_deliver_non_matching(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test.*", handler=cap)
        bus.emit(CognitiveEvent(event_type="other.hello"))
        assert len(cap.events) == 0

    def test_exact_match(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test.exact", handler=cap)
        bus.emit(CognitiveEvent(event_type="test.exact"))
        bus.emit(CognitiveEvent(event_type="test.other"))
        assert len(cap.events) == 1

    def test_wildcard_all(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("*", handler=cap)
        bus.emit(CognitiveEvent(event_type="anything"))
        bus.emit(CognitiveEvent(event_type="whatever.sub"))
        assert len(cap.events) == 2

    def test_nested_wildcard(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("a.b.*", handler=cap)
        bus.emit(CognitiveEvent(event_type="a.b.c"))
        bus.emit(CognitiveEvent(event_type="a.b.c.d"))  # fnmatch * matches . too
        bus.emit(CognitiveEvent(event_type="a.c.d"))  # no match
        assert len(cap.events) == 2  # "a.b.c" and "a.b.c.d"

    def test_source_filter(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("*", handler=cap, source_filter="mod_a")
        bus.emit(CognitiveEvent(event_type="test", source="mod_a"))
        bus.emit(CognitiveEvent(event_type="test", source="mod_b"))
        assert len(cap.events) == 1

    def test_priority_ordering(self):
        bus = EventBus()
        order = []
        bus.subscribe("test", handler=lambda e: order.append("low"), priority=0)
        bus.subscribe("test", handler=lambda e: order.append("high"), priority=10)
        bus.subscribe("test", handler=lambda e: order.append("mid"), priority=5)
        bus.emit(CognitiveEvent(event_type="test"))
        assert order == ["high", "mid", "low"]

    def test_emit_returns_handler_count(self):
        bus = EventBus()
        bus.subscribe("test", handler=lambda e: None)
        bus.subscribe("test", handler=lambda e: None)
        bus.subscribe("other", handler=lambda e: None)
        count = bus.emit(CognitiveEvent(event_type="test"))
        assert count == 2

    def test_emit_count_stat(self):
        bus = EventBus()
        bus.subscribe("*", handler=lambda e: None)
        bus.emit(CognitiveEvent(event_type="a"))
        bus.emit(CognitiveEvent(event_type="b"))
        assert bus.emit_count == 2

    def test_dead_letter_on_handler_error(self):
        bus = EventBus()

        def bad_handler(e):
            raise RuntimeError("oops")

        bus.subscribe("test", handler=bad_handler)
        count = bus.emit(CognitiveEvent(event_type="test"))
        assert count == 0  # handler failed
        assert bus.error_count == 1
        dls = bus.get_dead_letters()
        assert len(dls) == 1
        assert "RuntimeError" in dls[0].error

    def test_multiple_dead_letters(self):
        bus = EventBus()
        bus.subscribe("test", handler=lambda e: 1 / 0)
        for _ in range(5):
            bus.emit(CognitiveEvent(event_type="test"))
        assert bus.error_count == 5

    def test_paused_drops_events(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("*", handler=cap)
        bus.pause()
        bus.emit(CognitiveEvent(event_type="test"))
        assert len(cap.events) == 0
        bus.resume()
        bus.emit(CognitiveEvent(event_type="test"))
        assert len(cap.events) == 1

    def test_is_paused(self):
        bus = EventBus()
        assert not bus.is_paused
        bus.pause()
        assert bus.is_paused
        bus.resume()
        assert not bus.is_paused


class TestEventBusHistory:
    def test_history_recorded(self):
        bus = EventBus(history_size=100)
        bus.emit(CognitiveEvent(event_type="a"))
        bus.emit(CognitiveEvent(event_type="b"))
        history = bus.get_history()
        assert len(history) == 2
        # Most recent first
        assert history[0].event_type == "b"
        assert history[1].event_type == "a"

    def test_history_limit(self):
        bus = EventBus(history_size=100)
        for i in range(10):
            bus.emit(CognitiveEvent(event_type=f"event.{i}"))
        history = bus.get_history(limit=3)
        assert len(history) == 3

    def test_history_pattern_filter(self):
        bus = EventBus()
        bus.emit(CognitiveEvent(event_type="a.x"))
        bus.emit(CognitiveEvent(event_type="b.y"))
        bus.emit(CognitiveEvent(event_type="a.z"))
        history = bus.get_history(pattern="a.*")
        assert len(history) == 2

    def test_history_since_filter(self):
        bus = EventBus()
        cutoff = time.time()
        bus.emit(CognitiveEvent(event_type="old", timestamp=cutoff - 100))
        bus.emit(CognitiveEvent(event_type="new", timestamp=cutoff + 1))
        history = bus.get_history(since=cutoff)
        assert len(history) == 1
        assert history[0].event_type == "new"

    def test_history_capacity(self):
        bus = EventBus(history_size=5)
        for i in range(10):
            bus.emit(CognitiveEvent(event_type=f"event.{i}"))
        history = bus.get_history()
        assert len(history) == 5
        # Most recent 5
        assert history[0].event_type == "event.9"

    def test_clear_history(self):
        bus = EventBus()
        bus.emit(CognitiveEvent(event_type="test"))
        bus.clear_history()
        assert len(bus.get_history()) == 0

    def test_replay(self):
        bus = EventBus()
        bus.emit(CognitiveEvent(event_type="a"))
        bus.emit(CognitiveEvent(event_type="b"))
        cap = EventCapture()
        replayed = bus.replay("*", handler=cap)
        assert replayed == 2
        # Replay is chronological (oldest first)
        assert cap.events[0].event_type == "a"
        assert cap.events[1].event_type == "b"

    def test_replay_with_pattern(self):
        bus = EventBus()
        bus.emit(CognitiveEvent(event_type="a.x"))
        bus.emit(CognitiveEvent(event_type="b.y"))
        cap = EventCapture()
        replayed = bus.replay("a.*", handler=cap)
        assert replayed == 1


class TestEventBusAsync:
    @pytest.mark.asyncio
    async def test_emit_async_sync_handler(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test", handler=cap)
        count = await bus.emit_async(CognitiveEvent(event_type="test"))
        assert count == 1
        assert len(cap.events) == 1

    @pytest.mark.asyncio
    async def test_emit_async_async_handler(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test", async_handler=cap.async_handler)
        count = await bus.emit_async(CognitiveEvent(event_type="test"))
        assert count == 1
        assert len(cap.events) == 1

    @pytest.mark.asyncio
    async def test_emit_async_both_handlers(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test", handler=cap, async_handler=cap.async_handler)
        count = await bus.emit_async(CognitiveEvent(event_type="test"))
        assert count == 2  # both invoked
        assert len(cap.events) == 2

    @pytest.mark.asyncio
    async def test_emit_async_dead_letter(self):
        bus = EventBus()

        async def bad_async(e):
            raise ValueError("async oops")

        bus.subscribe("test", async_handler=bad_async)
        count = await bus.emit_async(CognitiveEvent(event_type="test"))
        assert count == 0
        assert bus.error_count == 1

    @pytest.mark.asyncio
    async def test_emit_async_paused(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("test", async_handler=cap.async_handler)
        bus.pause()
        count = await bus.emit_async(CognitiveEvent(event_type="test"))
        assert count == 0


class TestEventBusStats:
    def test_get_stats(self):
        bus = EventBus(history_size=500)
        bus.subscribe("*", handler=lambda e: None)
        bus.emit(CognitiveEvent(event_type="test"))
        stats = bus.get_stats()
        assert stats["subscriptions"] == 1
        assert stats["history_size"] == 1
        assert stats["history_capacity"] == 500
        assert stats["total_emitted"] == 1
        assert stats["total_errors"] == 0
        assert stats["paused"] is False


# ═══════════════════════════════════════════════════════════════════════
# BLACKBOARD TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestBlackboardPost:
    def test_post_returns_id(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        assert isinstance(eid, str) and len(eid) == 32

    def test_post_increments_count(self):
        bb = CognitiveBlackboard()
        assert bb.entry_count == 0
        bb.post(make_entry())
        assert bb.entry_count == 1
        bb.post(make_entry())
        assert bb.entry_count == 2

    def test_post_emits_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.entry.added", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        bb.post(make_entry(topic="test.data", source="mod"))
        assert len(cap.events) == 1
        assert cap.events[0].payload["topic"] == "test.data"
        assert cap.events[0].payload["source_module"] == "mod"

    def test_post_many(self):
        bb = CognitiveBlackboard()
        entries = [make_entry(topic=f"test.{i}") for i in range(5)]
        ids = bb.post_many(entries)
        assert len(ids) == 5
        assert bb.entry_count == 5


class TestBlackboardGet:
    def test_get_by_id(self):
        bb = CognitiveBlackboard()
        entry = make_entry(data={"key": "value"})
        eid = bb.post(entry)
        got = bb.get(eid)
        assert got is not None
        assert got.data == {"key": "value"}

    def test_get_nonexistent(self):
        bb = CognitiveBlackboard()
        assert bb.get("nope") is None

    def test_get_expired_returns_none(self):
        bb = CognitiveBlackboard(auto_expire=True)
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        eid = bb.post(entry)
        assert bb.get(eid) is None

    def test_get_expired_with_auto_expire_off(self):
        bb = CognitiveBlackboard(auto_expire=False)
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        eid = bb.post(entry)
        got = bb.get(eid)
        assert got is not None  # not auto-expired


class TestBlackboardGetByTopic:
    def test_exact_topic(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="consciousness.phi"))
        bb.post(make_entry(topic="reasoning.result"))
        results = bb.get_by_topic("consciousness.phi")
        assert len(results) == 1

    def test_subtopic_included(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="consciousness.phi"))
        bb.post(make_entry(topic="consciousness.gwt"))
        bb.post(make_entry(topic="reasoning"))
        results = bb.get_by_topic("consciousness")
        assert len(results) == 2

    def test_subtopic_excluded(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="consciousness.phi"))
        bb.post(make_entry(topic="consciousness.gwt"))
        results = bb.get_by_topic("consciousness", include_subtopics=False)
        assert len(results) == 0

    def test_no_matches(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="test"))
        results = bb.get_by_topic("nonexistent")
        assert len(results) == 0


class TestBlackboardGetBySource:
    def test_get_by_source(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(source="mod_a"))
        bb.post(make_entry(source="mod_a"))
        bb.post(make_entry(source="mod_b"))
        results = bb.get_by_source("mod_a")
        assert len(results) == 2

    def test_no_matches(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(source="mod_a"))
        results = bb.get_by_source("mod_z")
        assert len(results) == 0


class TestBlackboardQuery:
    def test_query_by_topic(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="a.x"))
        bb.post(make_entry(topic="b.y"))
        results = bb.query(BlackboardQuery(topics=["a"]))
        assert len(results) == 1
        assert results[0].topic == "a.x"

    def test_query_with_limit(self):
        bb = CognitiveBlackboard()
        for i in range(10):
            bb.post(make_entry(topic="test", data={"i": i}))
        results = bb.query(BlackboardQuery(topics=["test"], limit=3))
        assert len(results) == 3

    def test_query_sorted_by_priority(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="test", priority=EntryPriority.LOW, data="low"))
        bb.post(make_entry(topic="test", priority=EntryPriority.CRITICAL, data="crit"))
        bb.post(make_entry(topic="test", priority=EntryPriority.NORMAL, data="norm"))
        results = bb.query(BlackboardQuery(topics=["test"]))
        assert results[0].data == "crit"
        assert results[1].data == "norm"
        assert results[2].data == "low"

    def test_query_all(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="a"))
        bb.post(make_entry(topic="b"))
        results = bb.query(BlackboardQuery())
        assert len(results) == 2

    def test_query_min_confidence(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(confidence=0.3))
        bb.post(make_entry(confidence=0.9))
        results = bb.query(BlackboardQuery(min_confidence=0.5))
        assert len(results) == 1
        assert results[0].confidence == 0.9

    def test_query_excludes_expired(self):
        bb = CognitiveBlackboard()
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        bb.post(entry)
        bb.post(make_entry())  # not expired
        results = bb.query(BlackboardQuery())
        assert len(results) == 1


class TestBlackboardUpdate:
    def test_update_data(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry(data={"old": True}))
        assert bb.update_entry(eid, data={"new": True})
        got = bb.get(eid)
        assert got.data == {"new": True}

    def test_update_confidence(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry(confidence=0.5))
        bb.update_entry(eid, confidence=0.95)
        assert bb.get(eid).confidence == 0.95

    def test_update_status(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        bb.update_entry(eid, status=EntryStatus.CONSUMED)
        assert bb.get(eid).status == EntryStatus.CONSUMED

    def test_update_priority(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry(priority=EntryPriority.LOW))
        bb.update_entry(eid, priority=EntryPriority.CRITICAL)
        assert bb.get(eid).priority == EntryPriority.CRITICAL

    def test_update_tags(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        bb.update_entry(eid, tags={"reviewed", "important"})
        assert "reviewed" in bb.get(eid).tags

    def test_update_metadata(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        bb.update_entry(eid, metadata={"version": 2})
        assert bb.get(eid).metadata == {"version": 2}

    def test_update_nonexistent(self):
        bb = CognitiveBlackboard()
        assert bb.update_entry("nonexistent", data=42) is False

    def test_update_emits_events(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.entry.updated", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        eid = bb.post(make_entry(data="old"))
        bb.update_entry(eid, data="new", confidence=0.99)
        assert len(cap.events) == 2  # one per field
        fields = {e.payload["field"] for e in cap.events}
        assert fields == {"data", "confidence"}

    def test_update_no_changes_returns_false(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        # No keyword args → no changes
        result = bb.update_entry(eid)
        assert result is False


class TestBlackboardRemove:
    def test_remove(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        assert bb.remove(eid) is True
        assert bb.get(eid) is None
        assert bb.entry_count == 0

    def test_remove_nonexistent(self):
        bb = CognitiveBlackboard()
        assert bb.remove("nope") is False

    def test_remove_emits_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.entry.removed", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        eid = bb.post(make_entry())
        bb.remove(eid, reason="test_cleanup")
        assert len(cap.events) == 1
        assert cap.events[0].payload["reason"] == "test_cleanup"

    def test_remove_cleans_indices(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry(topic="t", source="s"))
        bb.remove(eid)
        assert bb.get_by_topic("t") == []
        assert bb.get_by_source("s") == []


class TestBlackboardRetract:
    def test_retract(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry())
        assert bb.retract(eid) is True
        entry = bb.get(eid)
        assert entry.status == EntryStatus.RETRACTED

    def test_retract_nonexistent(self):
        bb = CognitiveBlackboard()
        assert bb.retract("nope") is False


class TestBlackboardSupersede:
    def test_supersede(self):
        bb = CognitiveBlackboard()
        old_id = bb.post(make_entry(data="v1"))
        new_entry = make_entry(data="v2")
        new_id = bb.supersede(old_id, new_entry)
        assert new_id != old_id
        # Old entry is superseded
        old = bb.get(old_id)
        assert old.status == EntryStatus.SUPERSEDED
        # New entry links to old
        new = bb.get(new_id)
        assert new.parent_id == old_id
        assert new.data == "v2"


class TestBlackboardExpiry:
    def test_sweep_expired(self):
        bb = CognitiveBlackboard()
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        bb.post(entry)
        bb.post(make_entry())  # no TTL
        count = bb.sweep_expired()
        assert count == 1
        # Expired entries are kept but marked
        assert bb.entry_count == 2
        assert bb.active_entry_count == 1

    def test_expired_emits_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.entry.expired", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        entry = make_entry(ttl=0.001)
        entry.timestamp = time.time() - 1.0
        bb.post(entry)
        bb.sweep_expired()
        expired_events = [e for e in cap.events if e.event_type == "blackboard.entry.expired"]
        assert len(expired_events) == 1

    def test_sweep_complete_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.sweep.complete", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        bb.post(make_entry())
        bb.sweep_expired()
        assert len(cap.events) == 1
        assert cap.events[0].payload["active_count"] == 1


class TestBlackboardEviction:
    def test_eviction_at_capacity(self):
        bb = CognitiveBlackboard(max_entries=3)
        bb.post(make_entry(priority=EntryPriority.LOW, data="oldest"))
        bb.post(make_entry(priority=EntryPriority.NORMAL, data="mid"))
        bb.post(make_entry(priority=EntryPriority.HIGH, data="high"))
        # This should evict the LOW entry
        bb.post(make_entry(priority=EntryPriority.NORMAL, data="new"))
        assert bb.entry_count == 3
        # The LOW one should be gone
        remaining = [e.data for e in bb.query(BlackboardQuery())]
        assert "oldest" not in remaining
        assert "mid" in remaining
        assert "high" in remaining
        assert "new" in remaining

    def test_eviction_order_by_priority_then_age(self):
        bb = CognitiveBlackboard(max_entries=2)
        e1 = make_entry(priority=EntryPriority.LOW, data="first_low")
        e2 = make_entry(priority=EntryPriority.LOW, data="second_low")
        e2.timestamp = time.time() + 100  # future = newer
        bb.post(e1)
        bb.post(e2)
        # Posting a third should evict e1 (oldest LOW)
        bb.post(make_entry(priority=EntryPriority.HIGH, data="high"))
        results = bb.query(BlackboardQuery())
        datas = [r.data for r in results]
        assert "first_low" not in datas
        assert "second_low" in datas

    def test_critical_entries_never_evicted(self):
        bb = CognitiveBlackboard(max_entries=2)
        bb.post(make_entry(priority=EntryPriority.CRITICAL, data="c1"))
        bb.post(make_entry(priority=EntryPriority.CRITICAL, data="c2"))
        # Posting a third — all existing are CRITICAL, so capacity is exceeded
        bb.post(make_entry(priority=EntryPriority.CRITICAL, data="c3"))
        assert bb.entry_count == 3  # over capacity, but no eviction possible


class TestBlackboardClear:
    def test_clear(self):
        bb = CognitiveBlackboard()
        for _ in range(5):
            bb.post(make_entry())
        cleared = bb.clear()
        assert cleared == 5
        assert bb.entry_count == 0
        assert bb.get_topics() == []


class TestBlackboardModuleRegistration:
    def test_register_module(self):
        bb = CognitiveBlackboard()
        mod = MockParticipant("test_mod")
        bb.register_module(mod)
        assert bb.module_count == 1
        assert bb.get_module("test_mod") is not None
        assert mod.registered_count == 1
        assert mod.blackboard is bb

    def test_register_duplicate_raises(self):
        bb = CognitiveBlackboard()
        bb.register_module(MockParticipant("dup"))
        with pytest.raises(ValueError, match="already registered"):
            bb.register_module(MockParticipant("dup"))

    def test_unregister_module(self):
        bb = CognitiveBlackboard()
        bb.register_module(MockParticipant("mod"))
        assert bb.unregister_module("mod") is True
        assert bb.module_count == 0
        assert bb.get_module("mod") is None

    def test_unregister_nonexistent(self):
        bb = CognitiveBlackboard()
        assert bb.unregister_module("nope") is False

    def test_get_module_instance(self):
        bb = CognitiveBlackboard()
        mod = MockParticipant("my_mod")
        bb.register_module(mod)
        instance = bb.get_module_instance("my_mod")
        assert instance is mod

    def test_list_modules(self):
        bb = CognitiveBlackboard()
        bb.register_module(MockParticipant("a"))
        bb.register_module(MockParticipant("b"))
        modules = bb.list_modules()
        names = {m.name for m in modules}
        assert names == {"a", "b"}

    def test_registration_emits_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.module.*", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        bb.register_module(MockParticipant("mod"))
        assert len(cap.events) == 1
        assert cap.events[0].event_type == "blackboard.module.registered"
        assert cap.events[0].payload["module_name"] == "mod"

    def test_unregistration_emits_event(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("blackboard.module.*", handler=cap)
        bb = CognitiveBlackboard(event_bus=bus)
        bb.register_module(MockParticipant("mod"))
        bb.unregister_module("mod")
        unreg_events = [
            e for e in cap.events
            if e.event_type == "blackboard.module.unregistered"
        ]
        assert len(unreg_events) == 1


class TestBlackboardIntrospection:
    def test_entry_count(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry())
        bb.post(make_entry())
        assert bb.entry_count == 2

    def test_active_entry_count(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry())
        eid = bb.post(make_entry())
        bb.retract(eid)
        assert bb.active_entry_count == 1

    def test_get_topics(self):
        bb = CognitiveBlackboard()
        bb.post(make_entry(topic="a"))
        bb.post(make_entry(topic="b"))
        bb.post(make_entry(topic="a"))
        topics = bb.get_topics()
        assert set(topics) == {"a", "b"}

    def test_get_stats(self):
        bb = CognitiveBlackboard()
        bb.register_module(MockParticipant("mod1"))
        bb.post(make_entry(topic="t1", source="mod1"))
        bb.post(make_entry(topic="t2", source="mod1"))
        stats = bb.get_stats()
        assert stats["total_entries"] == 2
        assert stats["total_posted"] == 2
        assert stats["registered_modules"] == 1
        assert stats["entries_by_topic"]["t1"] == 1
        assert stats["entries_by_topic"]["t2"] == 1
        assert stats["entries_by_source"]["mod1"] == 2
        assert "event_bus" in stats


# ═══════════════════════════════════════════════════════════════════════
# THREAD SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    def test_concurrent_posts(self):
        """Multiple threads posting simultaneously should not lose data."""
        bb = CognitiveBlackboard()
        n_threads = 8
        n_per_thread = 100

        def poster(thread_id):
            for i in range(n_per_thread):
                bb.post(make_entry(
                    topic=f"thread.{thread_id}",
                    data={"thread": thread_id, "i": i},
                    source=f"thread_{thread_id}",
                ))

        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(poster, t) for t in range(n_threads)]
            for f in futures:
                f.result()

        assert bb.entry_count == n_threads * n_per_thread

    def test_concurrent_posts_and_queries(self):
        """Posts and queries interleaved across threads."""
        bb = CognitiveBlackboard()
        errors = []

        def poster():
            for i in range(50):
                bb.post(make_entry(topic="mixed", data={"i": i}))

        def querier():
            for _ in range(50):
                try:
                    results = bb.get_by_topic("mixed")
                    # Should never crash
                    _ = len(results)
                except Exception as e:
                    errors.append(str(e))

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = []
            for _ in range(2):
                futures.append(pool.submit(poster))
                futures.append(pool.submit(querier))
            for f in futures:
                f.result()

        assert len(errors) == 0

    def test_concurrent_event_emission(self):
        """Multiple threads emitting events simultaneously."""
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("*", handler=cap)
        n_threads = 4
        n_per_thread = 100

        def emitter(tid):
            for i in range(n_per_thread):
                bus.emit(CognitiveEvent(event_type=f"thread.{tid}.{i}"))

        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(emitter, t) for t in range(n_threads)]
            for f in futures:
                f.result()

        assert len(cap.events) == n_threads * n_per_thread

    def test_concurrent_subscribe_unsubscribe(self):
        """Subscribing and unsubscribing across threads."""
        bus = EventBus()
        sub_ids = []
        lock = threading.Lock()

        def subscriber():
            for _ in range(50):
                sid = bus.subscribe("test", handler=lambda e: None)
                with lock:
                    sub_ids.append(sid)

        def unsubscriber():
            for _ in range(50):
                with lock:
                    if sub_ids:
                        sid = sub_ids.pop()
                    else:
                        sid = None
                if sid:
                    bus.unsubscribe(sid)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(subscriber),
                pool.submit(subscriber),
                pool.submit(unsubscriber),
                pool.submit(unsubscriber),
            ]
            for f in futures:
                f.result()

        # No crashes = success


class TestAsyncBlackboard:
    """Test that the blackboard works correctly from async contexts."""

    @pytest.mark.asyncio
    async def test_post_and_query_from_async(self):
        bb = CognitiveBlackboard()
        eid = bb.post(make_entry(data={"async": True}))
        entry = bb.get(eid)
        assert entry is not None
        assert entry.data == {"async": True}

    @pytest.mark.asyncio
    async def test_event_bus_async_emit(self):
        bb = CognitiveBlackboard()
        cap = EventCapture()
        bb.event_bus.subscribe("blackboard.*", async_handler=cap.async_handler)
        bb.post(make_entry())
        # The post() calls bus.emit() (sync), not emit_async(), so
        # async_handler won't be called.  This is by design —
        # to get async notification, use emit_async() directly.
        assert len(cap.events) == 0

    @pytest.mark.asyncio
    async def test_direct_async_emission(self):
        bus = EventBus()
        cap = EventCapture()
        bus.subscribe("custom.*", async_handler=cap.async_handler)
        await bus.emit_async(CognitiveEvent(event_type="custom.test"))
        assert len(cap.events) == 1


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════

class TestIntegrationScenario:
    """End-to-end scenarios simulating real module interactions."""

    def test_consciousness_posts_reasoning_consumes(self):
        """Consciousness module posts Φ values, reasoning module reads them."""
        bb = CognitiveBlackboard()

        # Register modules
        consciousness = MockParticipant(
            "consciousness",
            capabilities=ModuleCapability.PRODUCER,
        )
        reasoning = MockParticipant(
            "reasoning",
            capabilities=ModuleCapability.CONSUMER | ModuleCapability.REASONER,
        )
        bb.register_module(consciousness)
        bb.register_module(reasoning)

        # Consciousness posts Φ measurement
        bb.post(BlackboardEntry(
            topic="consciousness.phi",
            data={"phi": 3.14, "elements": ["a", "b", "c"], "timestamp": time.time()},
            source_module="consciousness",
            confidence=0.95,
            priority=EntryPriority.HIGH,
            tags=frozenset({"iit", "measurement"}),
        ))

        # Reasoning queries it
        results = bb.get_by_topic("consciousness")
        assert len(results) == 1
        assert results[0].data["phi"] == 3.14

        # Structured query with confidence filter
        high_conf = bb.query(BlackboardQuery(
            topics=["consciousness"],
            min_confidence=0.9,
        ))
        assert len(high_conf) == 1

    def test_transformer_chain(self):
        """Raw data → transformer → enriched data chain."""
        bb = CognitiveBlackboard()

        # Post raw observation
        raw_id = bb.post(BlackboardEntry(
            topic="observation.raw",
            data={"temperature": 22.5, "location": "lab_1"},
            source_module="sensor",
            confidence=0.99,
        ))

        # Transformer reads and enriches
        transformer = TransformerModule()
        raw_entries = bb.get_by_topic("observation.raw")
        enriched = transformer.transform(raw_entries)

        # Post enriched entries
        for entry in enriched:
            bb.post(entry)

        # Verify chain
        enriched_results = bb.get_by_topic("observation.raw.transformed")
        assert len(enriched_results) == 1
        assert enriched_results[0].data["transformed"] is True
        assert enriched_results[0].parent_id == raw_id

    def test_event_driven_pipeline(self):
        """Modules react to blackboard events in a pipeline."""
        bb = CognitiveBlackboard()
        processed = []

        def on_new_entry(event: CognitiveEvent):
            if event.payload.get("topic", "").startswith("stage1"):
                # React by posting a stage2 entry
                bb.post(BlackboardEntry(
                    topic="stage2.result",
                    data={"from": event.payload["entry_id"]},
                    source_module="pipeline",
                ))
                processed.append(event.payload["entry_id"])

        bb.event_bus.subscribe("blackboard.entry.added", handler=on_new_entry)

        # Post stage1 entry → triggers pipeline
        bb.post(BlackboardEntry(
            topic="stage1.input",
            data={"input": "hello"},
            source_module="source",
        ))

        # Both entries should exist
        assert bb.entry_count == 2
        stage2 = bb.get_by_topic("stage2")
        assert len(stage2) == 1
        assert len(processed) == 1

    def test_multi_domain_blackboard(self):
        """Multiple domains posting concurrently, each queryable."""
        bb = CognitiveBlackboard()
        domains = [
            ("astrophysics", "consciousness"),
            ("economics", "reasoning"),
            ("climate", "bio_inspired"),
            ("epidemiology", "knowledge_management"),
        ]

        for domain, module in domains:
            for i in range(5):
                bb.post(BlackboardEntry(
                    topic=f"discovery.{domain}",
                    data={"domain": domain, "finding": f"result_{i}"},
                    source_module=module,
                    confidence=0.5 + i * 0.1,
                ))

        assert bb.entry_count == 20

        # Query by domain
        astro = bb.get_by_topic("discovery.astrophysics")
        assert len(astro) == 5

        # Query by source module
        reasoning = bb.get_by_source("reasoning")
        assert len(reasoning) == 5

        # Cross-domain query
        high_conf = bb.query(BlackboardQuery(
            topics=["discovery"],
            min_confidence=0.8,
        ))
        # Each domain has entries at 0.5, 0.6, 0.7, 0.8, 0.9 → 2 per domain ≥ 0.8
        assert len(high_conf) == 8

    def test_supersession_chain(self):
        """Hypothesis refinement through supersession."""
        bb = CognitiveBlackboard()

        # Initial hypothesis
        v1_id = bb.post(BlackboardEntry(
            topic="hypothesis.dark_energy",
            data={"statement": "Dark energy is constant", "confidence": 0.6},
            source_module="reasoning",
        ))

        # Refined hypothesis supersedes v1
        v2 = BlackboardEntry(
            topic="hypothesis.dark_energy",
            data={"statement": "Dark energy varies with redshift", "confidence": 0.75},
            source_module="reasoning",
        )
        v2_id = bb.supersede(v1_id, v2)

        # v1 is superseded, v2 is active
        assert bb.get(v1_id).status == EntryStatus.SUPERSEDED
        assert bb.get(v2_id).status == EntryStatus.ACTIVE
        assert bb.get(v2_id).parent_id == v1_id

        # Active-only query returns only v2
        active = bb.query(BlackboardQuery(
            topics=["hypothesis"],
            statuses={EntryStatus.ACTIVE},
        ))
        assert len(active) == 1
        assert active[0].entry_id == v2_id

    def test_ttl_based_working_memory(self):
        """Short-TTL entries simulate working memory that expires."""
        bb = CognitiveBlackboard()

        # Post with 0.05s TTL
        entry = BlackboardEntry(
            topic="working_memory.scratch",
            data={"intermediate": "calculation"},
            source_module="reasoning",
            ttl_seconds=0.05,
        )
        eid = bb.post(entry)

        # Immediately available
        assert bb.get(eid) is not None

        # Wait for expiry
        time.sleep(0.1)
        assert bb.get(eid) is None  # auto-expired

    def test_full_stats_after_workflow(self):
        """Stats reflect correct state after a complex workflow."""
        bb = CognitiveBlackboard()
        bb.register_module(MockParticipant("mod_a"))
        bb.register_module(MockParticipant("mod_b"))

        # Post, update, retract, remove
        e1 = bb.post(make_entry(topic="a", source="mod_a"))
        e2 = bb.post(make_entry(topic="b", source="mod_b"))
        e3 = bb.post(make_entry(topic="a.sub", source="mod_a"))
        bb.retract(e2)
        bb.remove(e3)

        stats = bb.get_stats()
        assert stats["total_entries"] == 2  # e1 + e2 (e3 removed)
        assert stats["total_posted"] == 3
        assert stats["total_removed"] == 1
        assert stats["registered_modules"] == 2
        assert stats["status_distribution"]["active"] == 1
        assert stats["status_distribution"]["retracted"] == 1
