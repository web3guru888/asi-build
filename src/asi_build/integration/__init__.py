"""
ASI:BUILD Cognitive Integration Layer
======================================

Cross-module communication infrastructure based on the **Cognitive Blackboard**
pattern.  Provides:

- ``CognitiveBlackboard`` — Shared workspace for posting and querying findings
- ``EventBus`` — Pub/sub event delivery with topic routing and wildcards
- ``BlackboardEntry`` — Type-safe data container with provenance metadata
- Protocol definitions for type-safe module participation

Architecture
~~~~~~~~~~~~

Modules register with the blackboard, post findings (``BlackboardEntry``),
and query others' findings.  The embedded ``EventBus`` provides real-time
notifications (``CognitiveEvent``) for reactive inter-module workflows.

::

    ┌──────────┐     post()     ┌────────────────────┐    events     ┌──────────┐
    │  Module  │ ──────────────►│  CognitiveBlackboard│──────────────►│  Module  │
    │    A     │◄──────────────│                      │◄──────────────│    B     │
    └──────────┘     query()    │   ┌──────────┐      │   subscribe() └──────────┘
                                │   │ EventBus │      │
                                │   └──────────┘      │
                                └─────────────────────┘

Quick Start
~~~~~~~~~~~

::

    from asi_build.integration import (
        CognitiveBlackboard, BlackboardEntry, EntryPriority
    )

    bb = CognitiveBlackboard()
    bb.post(BlackboardEntry(
        topic="consciousness.phi",
        data={"phi": 3.14, "elements": ["a", "b", "c"]},
        source_module="consciousness",
        priority=EntryPriority.HIGH,
    ))

    results = bb.get_by_topic("consciousness")
"""

__version__ = "1.1.0"
__maturity__ = "beta"

# Blackboard
from .blackboard import CognitiveBlackboard

# Event bus
from .events import DeadLetter, EventBus, Subscription

# Protocols and data types
from .protocols import (
    AsyncBlackboardConsumer,
    AsyncBlackboardProducer,
    AsyncBlackboardTransformer,
    AsyncEventListener,
    BlackboardConsumer,
    BlackboardEntry,
    BlackboardParticipant,
    BlackboardProducer,
    BlackboardQuery,
    BlackboardTransformer,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    EventEmitter,
    EventHandler,
    EventListener,
    ModuleCapability,
    ModuleInfo,
)

__all__ = [
    # Core
    "CognitiveBlackboard",
    "EventBus",
    # Data types
    "BlackboardEntry",
    "BlackboardQuery",
    "CognitiveEvent",
    "ModuleInfo",
    "Subscription",
    "DeadLetter",
    # Enums
    "EntryPriority",
    "EntryStatus",
    "ModuleCapability",
    # Protocols
    "BlackboardParticipant",
    "BlackboardProducer",
    "BlackboardConsumer",
    "BlackboardTransformer",
    "EventEmitter",
    "EventListener",
    "AsyncBlackboardProducer",
    "AsyncBlackboardConsumer",
    "AsyncBlackboardTransformer",
    "AsyncEventListener",
    # Callback types
    "EventHandler",
]
