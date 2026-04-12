"""
Comprehensive tests for 8 new blackboard adapters.

Tests cover the 10 required patterns for each adapter:
1. Construction with no args
2. module_info property
3. on_registered
4. set_event_handler + _emit
5. produce() with no components
6. produce() with mock component
7. consume() with entries
8. handle_event()
9. snapshot()
10. Change detection

Plus extra safety-specific tests for SafetyBlackboardAdapter.
"""

from __future__ import annotations

import time
import types
import pytest
from unittest.mock import MagicMock, patch

from asi_build.integration.protocols import (
    BlackboardEntry,
    CognitiveEvent,
    EntryPriority,
    EntryStatus,
    ModuleCapability,
    ModuleInfo,
)
from asi_build.integration.adapters import (
    QuantumBlackboardAdapter,
    HolographicBlackboardAdapter,
    BCIBlackboardAdapter,
    NeuromorphicBlackboardAdapter,
    AGICommunicationBlackboardAdapter,
    AGIEconomicsBlackboardAdapter,
    FederatedLearningBlackboardAdapter,
    SafetyBlackboardAdapter,
    wire_all,
    production_sweep,
)


# ============================================================================
# Mock Components
# ============================================================================


class MockQuantumSimulator:
    """Mock for QuantumSimulator — provides state vector + probabilities."""
    def __init__(self, state_vector=None):
        self._sv = state_vector or [0.707, 0.0, 0.0, 0.707]
        self.measurement_results = [{"00": 500, "11": 500}]

    def run_circuit(self, circuit, shots=1):
        return {"counts": {"00": 500, "11": 500}, "state_vector": self._sv}

    def get_state_vector(self):
        return self._sv

    def get_probabilities(self):
        return [0.5, 0.0, 0.0, 0.5]


class MockHybridML:
    """Mock for HybridMLProcessor — provides metrics and quantum advantage."""
    def __init__(self, advantage=1.2):
        self.metrics = {
            "quantum_advantage_scores": [advantage],
            "quantum_processing_time": [0.05],
        }

    def get_quantum_metrics(self):
        return {
            "error_correction_rate": 0.95,
            "avg_quantum_advantage": 1.2,
            "status": "active",
        }


class MockQAOA:
    """Mock QAOA optimizer."""
    optimal_params = [0.1, 0.2, 0.3]
    optimization_history = [{"cost": -2.5}, {"cost": -3.1}]


class MockVQE:
    """Mock VQE optimizer."""
    optimal_params = [0.4, 0.5]


class MockHolographicEngine:
    """Mock for HolographicEngine."""
    def __init__(self, state="running", fps=60.0, frame_count=100):
        self._state = state
        self._fps = fps
        self._frame_count = frame_count
        self._update_callbacks = []

    def get_status(self):
        return {
            "state": self._state,
            "fps": self._fps,
            "frame_count": self._frame_count,
            "uptime": 120.0,
            "components": {},
        }

    def get_performance_metrics(self):
        return {
            "fps": self._fps,
            "frame_time": 1000.0 / max(self._fps, 1),
            "memory": 256.0,
            "gpu": 45.0,
        }

    def add_update_callback(self, cb):
        self._update_callbacks.append(cb)


class MockLightField:
    """Mock for LightFieldProcessor."""
    def __init__(self, capture_count=5):
        self._cc = capture_count

    def get_performance_stats(self):
        return {"capture_count": self._cc, "avg_quality": 0.85}


class MockVolumetricDisplay:
    """Mock for VolumetricDisplay."""
    def __init__(self, render_count=10):
        self._rc = render_count

    def get_performance_stats(self):
        return {"render_count": self._rc, "avg_render_time": 0.02}


class MockBCIManager:
    """Mock for BCIManager."""
    def __init__(self, active_sessions=2, cal_ts=1000.0):
        self._active = active_sessions
        self._cal_ts = cal_ts

    def get_system_status(self):
        return {
            "active_sessions": self._active,
            "device_status": "connected",
            "processing_state": "running",
            "last_calibration_timestamp": self._cal_ts,
            "calibration_accuracy": 0.92,
        }

    def calibrate(self, task_type=None, duration=0, trials=0):
        return {"accuracy": 0.92}


class MockProcessedSignal:
    """Mock processed neural signal."""
    def __init__(self, ts=None, quality=0.85, artifacts=False):
        self.timestamp = ts or time.time()
        self.quality_score = quality
        self.artifacts_detected = artifacts
        self.features = [0.1, 0.2, 0.3]
        self.filtered_data = None


class MockSignalProcessor:
    """Mock for SignalProcessor."""
    def __init__(self, quality=0.85, ts=None):
        self._signal = MockProcessedSignal(ts=ts, quality=quality)

    def process_realtime(self, data):
        return self._signal


class MockDecodingResult:
    """Mock neural decoding result."""
    def __init__(self, cls="left_hand", confidence=0.9):
        self.decoded_class = cls
        self.confidence = confidence
        self.task = "motor_imagery"
        self.latency = 0.05
        self.features_used = [0.5, 0.6]


class MockNeuralDecoder:
    """Mock for NeuralDecoder."""
    def __init__(self, cls="left_hand", confidence=0.9):
        self._result = MockDecodingResult(cls, confidence)

    def decode(self, processed):
        return self._result

    def get_performance_summary(self, task=None):
        return {"accuracy": 0.88, "precision": 0.85, "recall": 0.90, "f1": 0.87}


class MockNeuromorphicStatus:
    """Mock NeuromorphicManager system status."""
    def __init__(self, running=True, steps=100):
        self.is_initialized = True
        self.is_running = running
        self.total_steps = steps
        self.current_time = 0.1
        self.registered_networks = 2
        self.registered_processors = 1
        self.registered_interfaces = 1
        self.memory_usage = 1024


class MockNeuromorphicPerf:
    """Mock NeuromorphicManager performance metrics."""
    def __init__(self, sps=500.0):
        self.avg_step_time = 0.002
        self.steps_per_second = sps
        self.total_spikes = 5000
        self.spike_rate = 100.0
        self.memory_usage = 1024


class MockNeuromorphicManager:
    """Mock for NeuromorphicManager."""
    def __init__(self, running=True, steps=100, sps=500.0):
        self._status = MockNeuromorphicStatus(running, steps)
        self._perf = MockNeuromorphicPerf(sps)

    def get_system_status(self):
        return self._status

    def get_performance_metrics(self):
        return self._perf


class MockSpikeStats:
    """Mock spike monitor statistics."""
    def __init__(self, total=5000):
        self.total_spikes = total
        self.active_neurons = 200
        self.avg_firing_rate = 25.0
        self.max_firing_rate = 100.0
        self.synchrony_index = 0.6
        self.recording_duration = 10.0


class MockSpikeMonitor:
    """Mock for SpikeMonitor."""
    def __init__(self, total=5000):
        self._stats = MockSpikeStats(total)

    def get_statistics(self):
        return self._stats


class MockEventProcessor:
    """Mock for EventProcessor."""
    def __init__(self, total=100):
        self._total = total

    def get_statistics(self):
        return {"total_processed": self._total, "queue_sizes": {}, "processing_rate": 50.0}

    def submit_event(self, event, high_priority=False):
        pass


class MockSTDP:
    """Mock for STDPLearning."""
    def __init__(self, total_updates=50, avg_change=0.02):
        self._stats = {
            "total_updates": total_updates,
            "avg_weight_change": avg_change,
            "ltp_count": 30,
            "ltd_count": 20,
        }

    def get_statistics(self):
        return self._stats


class MockAGIProtocol:
    """Mock for AGICommunicationProtocol."""
    def __init__(self, sessions=3, messages=10):
        self._sessions = sessions
        self._messages = messages
        self.priority_level = 0.5

    def get_communication_stats(self):
        return {
            "active_sessions": self._sessions,
            "total_sessions": self._sessions + 2,
            "messages_sent": self._messages,
            "messages_received": self._messages,
            "avg_latency": 0.05,
        }

    def get_active_sessions(self):
        return [f"session_{i}" for i in range(self._sessions)]


class MockNegotiation:
    """Mock for GoalNegotiationProtocol."""
    def get_negotiation_statistics(self):
        return {
            "active_negotiations": 2,
            "completed_negotiations": 5,
            "total_proposals": 20,
            "agreement_rate": 0.8,
            "avg_rounds": 3.0,
            "has_nash_equilibria": True,
            "pareto_optimal_count": 3,
        }


class MockCollaboration:
    """Mock for CollaborativeProblemSolver."""
    efficiency_factor = 1.0

    def get_collaboration_statistics(self):
        return {
            "active_collaborations": 1,
            "completed_collaborations": 3,
            "total_tasks_assigned": 10,
            "total_solutions": 5,
            "avg_completion_time": 30.0,
            "success_rate": 0.8,
            "avg_quality": 0.75,
        }

    def submit_solution(self, session_id=None, solution=None):
        pass


class MockKGMerger:
    """Mock for KnowledgeGraphMerger."""
    def __init__(self, total_merges=3):
        self._total = total_merges

    def get_merge_statistics(self):
        return {
            "total_merges": self._total,
            "total_conflicts": 1,
            "avg_confidence": 0.85,
            "resolution_strategies_used": ["evidence_based"],
        }

    def merge_graphs(self, graphs=None, resolution_strategy="temporal"):
        pass


class MockTokenEngine:
    """Mock for TokenEconomicsEngine."""
    def get_token_metrics(self, token_type):
        return {
            "price": 1.25,
            "total_supply": 1000000,
            "market_cap": 1250000.0,
            "staked_amount": 500000.0,
            "inflation_rate": 0.02,
        }

    def get_token_price(self, token, currency):
        return 1.25

    def transfer_tokens(self, from_agent="", to_agent="", token_type="ASI", amount=0):
        return "success"


class MockBondingEngine:
    """Mock for BondingCurveEngine."""
    def get_all_market_data(self):
        return {"ASI": {"price": 1.5}, "COMPUTE": {"price": 0.5}}


class MockReputationSystem:
    """Mock for ReputationSystem."""
    def get_system_reputation_metrics(self):
        return {
            "total_agents": 10,
            "avg_overall_score": 0.78,
            "dimension_averages": {"trust": 0.8, "performance": 0.75},
            "total_events": 100,
            "trust_network": {
                "total_relationships": 20,
                "avg_trust_score": 0.82,
                "network_density": 0.3,
            },
        }

    def get_agent_reputation(self, agent_id):
        return {"overall_score": 0.8}


class MockMarketplace:
    """Mock for MarketplaceDynamics."""
    def get_market_data(self, service_type):
        return {
            "best_bid": 1.2,
            "best_ask": 1.3,
            "spread": 0.1,
            "volume_24h": 50000,
            "last_trade_price": 1.25,
        }


class MockValueAlignment:
    """Mock for ValueAlignmentEngine."""
    def get_system_value_metrics(self):
        return {
            "avg_alignment_score": 0.72,
            "total_agents": 8,
            "dimension_scores": {"fairness": 0.8, "transparency": 0.65},
            "total_measurements": 50,
        }


class MockFederatedManager:
    """Mock for FederatedManager."""
    def __init__(self, training=True, round_num=5, clients=3):
        self._training = training
        self._round = round_num
        self._clients = clients
        self.config = MagicMock()

    def get_training_status(self):
        return {
            "is_training": self._training,
            "current_round": self._round,
            "total_rounds": 100,
            "num_clients": self._clients,
            "convergence_metrics": {},
        }

    def get_comprehensive_summary(self):
        return {
            "round": self._round,
            "selected_clients": ["c1", "c2"],
            "aggregation_stats": {"avg_divergence": 0.01},
            "model_metrics": {"loss": 0.15},
        }


class MockFederatedServer:
    """Mock for FederatedServer."""
    def check_convergence(self, threshold=0.001):
        return False

    def get_server_status(self):
        return {"status": "active"}


class MockFedAvgAggregator:
    """Mock for FedAvgAggregator."""
    def get_fedavg_specific_stats(self):
        return {
            "total_aggregations": 5,
            "avg_weight_divergence": 0.01,
            "client_contribution_weights": {"c1": 0.5, "c2": 0.5},
        }


class MockFederatedMetrics:
    """Mock for FederatedMetrics."""
    def get_performance_summary(self):
        return {
            "total_rounds": 5,
            "avg_round_time": 2.5,
            "avg_aggregation_time": 0.3,
            "communication_overhead": 0.1,
            "efficiency": 0.92,
            "loss_trend": [0.5, 0.3, 0.15],
            "accuracy_trend": [0.6, 0.8, 0.88],
            "best_loss": 0.15,
            "best_accuracy": 0.88,
        }


class MockConstitutionalAI:
    """Mock for ConstitutionalAI."""
    def __init__(self, aligned=True):
        self._aligned = aligned

    def check_alignment(self, action):
        return self._aligned

    def get_constitution_status(self):
        return {"active": True, "num_principles": 5, "values": ["safety", "fairness"]}


class MockEthicalVerifier:
    """Mock for EthicalVerificationEngine."""
    def __init__(self, ethical=True, confidence=0.9):
        self._ethical = ethical
        self._confidence = confidence

    def verify_proposal_ethics(self, proposal):
        return {
            "is_ethical": self._ethical,
            "overall_confidence": self._confidence,
            "constraint_results": [{"principle": "harm", "passed": self._ethical}],
            "verification_summary": "Passed" if self._ethical else "FAILED: ethical violation",
        }

    def get_verification_statistics(self):
        return {
            "total_verifications": 10,
            "passed": 9,
            "failed": 1,
            "avg_confidence": 0.85,
        }

    def generate_ethics_report(self, ver_result):
        return "Ethics report: detailed analysis..."


class MockTheoremProver:
    """Mock for TheoremProver."""
    def prove_theorem(self, hypothesis, conclusion, method="resolution"):
        result = MagicMock()
        result.is_valid = True
        result.confidence = 0.95
        result.steps = ["step1", "step2"]
        result.method = method
        return result


# ============================================================================
# Helper: make a BlackboardEntry for consume/handle_event tests
# ============================================================================


def _entry(topic: str, data: dict | None = None, **kwargs) -> BlackboardEntry:
    return BlackboardEntry(
        topic=topic,
        data=data or {},
        source_module="test",
        **kwargs,
    )


def _event(event_type: str, payload: dict | None = None) -> CognitiveEvent:
    return CognitiveEvent(
        event_type=event_type,
        payload=payload or {},
        source="test",
    )


# ============================================================================
# 1. QuantumBlackboardAdapter
# ============================================================================


class TestQuantumAdapter:
    """Tests for QuantumBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = QuantumBlackboardAdapter()
        assert adapter._simulator is None
        assert adapter._hybrid_ml is None
        assert adapter._qaoa is None
        assert adapter._vqe is None
        assert adapter._kenny is None

    def test_module_info(self):
        adapter = QuantumBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "quantum"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert "quantum.circuit.result" in info.topics_produced
        assert "quantum.optimization.result" in info.topics_produced
        assert "quantum.ml.prediction" in info.topics_produced
        assert "quantum.metrics" in info.topics_produced
        assert "reasoning" in info.topics_consumed

    def test_on_registered(self):
        adapter = QuantumBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = QuantumBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("quantum.test", {"data": 123})
        assert len(events) == 1
        assert events[0].event_type == "quantum.test"
        assert events[0].payload["data"] == 123
        assert events[0].source == "quantum"

    def test_produce_no_components(self):
        adapter = QuantumBlackboardAdapter()
        entries = adapter.produce()
        assert entries == []

    def test_produce_with_simulator(self):
        sim = MockQuantumSimulator()
        adapter = QuantumBlackboardAdapter(simulator=sim)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        assert len(entries) >= 1
        circuit_entries = [e for e in entries if e.topic == "quantum.circuit.result"]
        assert len(circuit_entries) == 1
        assert circuit_entries[0].source_module == "quantum"
        assert "state_vector_hash" in circuit_entries[0].data
        # Event emitted
        assert any(e.event_type == "quantum.circuit.executed" for e in events)

    def test_produce_with_qaoa(self):
        adapter = QuantumBlackboardAdapter(qaoa=MockQAOA())
        entries = adapter.produce()
        opt_entries = [e for e in entries if e.topic == "quantum.optimization.result"]
        assert len(opt_entries) == 1
        assert opt_entries[0].data["algorithm"] == "qaoa"
        assert opt_entries[0].data["best_energy"] is not None

    def test_produce_with_hybrid_ml(self):
        adapter = QuantumBlackboardAdapter(hybrid_ml=MockHybridML())
        entries = adapter.produce()
        ml_entries = [e for e in entries if e.topic == "quantum.ml.prediction"]
        assert len(ml_entries) == 1
        assert ml_entries[0].data["latest_quantum_advantage"] == 1.2

    def test_consume_reasoning(self):
        adapter = QuantumBlackboardAdapter(qaoa=MockQAOA())
        entry = _entry("reasoning.inference", {"inference": "test hypothesis"})
        adapter.consume([entry])
        assert len(adapter._optimization_queue) == 1
        assert adapter._optimization_queue[0]["type"] == "inference_optimization"

    def test_consume_kg(self):
        adapter = QuantumBlackboardAdapter(kenny_integration=MagicMock())
        entry = _entry("knowledge_graph.triple", {
            "subject": "A", "predicate": "causes", "object": "B"
        })
        adapter.consume([entry])
        assert len(adapter._graph_optimization_queue) == 1

    def test_handle_event_reasoning(self):
        adapter = QuantumBlackboardAdapter()
        event = _event("reasoning.inference.completed", {"result": "test"})
        adapter.handle_event(event)
        assert len(adapter._optimization_queue) == 1

    def test_handle_event_kg(self):
        adapter = QuantumBlackboardAdapter()
        event = _event("knowledge_graph.triple.added", {"triple": ("A", "B", "C")})
        adapter.handle_event(event)
        assert len(adapter._graph_optimization_queue) == 1

    def test_handle_event_synergy(self):
        adapter = QuantumBlackboardAdapter()
        event = _event("cognitive_synergy.emergence.detected", {"coherence": 0.8})
        adapter.handle_event(event)
        assert len(adapter._coordination_queue) == 1

    def test_snapshot(self):
        adapter = QuantumBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "quantum"
        assert snap["has_simulator"] is False
        assert snap["has_hybrid_ml"] is False
        assert snap["registered"] is False
        assert "optimization_queue_depth" in snap

    def test_change_detection_circuit(self):
        sim = MockQuantumSimulator()
        adapter = QuantumBlackboardAdapter(simulator=sim)
        entries1 = adapter.produce()
        assert len([e for e in entries1 if e.topic == "quantum.circuit.result"]) == 1
        # Same state vector → no new entry
        entries2 = adapter.produce()
        assert len([e for e in entries2 if e.topic == "quantum.circuit.result"]) == 0

    def test_change_detection_optimization(self):
        adapter = QuantumBlackboardAdapter(qaoa=MockQAOA())
        entries1 = adapter.produce()
        assert len([e for e in entries1 if e.topic == "quantum.optimization.result"]) == 1
        entries2 = adapter.produce()
        assert len([e for e in entries2 if e.topic == "quantum.optimization.result"]) == 0


# ============================================================================
# 2. HolographicBlackboardAdapter
# ============================================================================


class TestHolographicAdapter:
    """Tests for HolographicBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = HolographicBlackboardAdapter()
        assert adapter._engine is None
        assert adapter._light_field is None
        assert adapter._display is None

    def test_module_info(self):
        adapter = HolographicBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "holographic"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert "holographic.engine.status" in info.topics_produced
        assert "holographic.engine.performance" in info.topics_produced
        assert "consciousness" in info.topics_consumed

    def test_on_registered(self):
        adapter = HolographicBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = HolographicBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("holographic.test", {"x": 1})
        assert len(events) == 1
        assert events[0].event_type == "holographic.test"
        assert events[0].source == "holographic"

    def test_produce_no_components(self):
        adapter = HolographicBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_engine(self):
        engine = MockHolographicEngine()
        adapter = HolographicBlackboardAdapter(engine=engine)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        status_entries = [e for e in entries if e.topic == "holographic.engine.status"]
        assert len(status_entries) == 1
        assert status_entries[0].data["state"] == "running"
        assert status_entries[0].data["fps"] == 60.0

    def test_produce_with_light_field(self):
        lf = MockLightField(capture_count=5)
        adapter = HolographicBlackboardAdapter(light_field=lf)
        entries = adapter.produce()
        cap_entries = [e for e in entries if e.topic == "holographic.lightfield.capture"]
        assert len(cap_entries) == 1
        assert cap_entries[0].data["capture_count"] == 5

    def test_produce_with_display(self):
        display = MockVolumetricDisplay(render_count=10)
        adapter = HolographicBlackboardAdapter(display=display)
        entries = adapter.produce()
        render_entries = [e for e in entries if e.topic == "holographic.display.render"]
        assert len(render_entries) == 1
        assert render_entries[0].data["render_count"] == 10

    def test_consume_consciousness(self):
        adapter = HolographicBlackboardAdapter()
        entry = _entry("consciousness.phi", {"phi": 3.5})
        adapter.consume([entry])
        assert len(adapter._pending_consciousness_updates) == 1

    def test_consume_kg(self):
        adapter = HolographicBlackboardAdapter()
        entry = _entry("knowledge_graph.triple", {
            "subject": "A", "predicate": "causes", "object": "B"
        })
        adapter.consume([entry])
        assert len(adapter._pending_kg_updates) == 1

    def test_consume_quantum(self):
        adapter = HolographicBlackboardAdapter()
        entry = _entry("quantum.circuit.result", {"state_vector": [0.5, 0.5]})
        adapter.consume([entry])
        assert len(adapter._pending_quantum_updates) == 1

    def test_handle_event_consciousness(self):
        adapter = HolographicBlackboardAdapter()
        event = _event("consciousness.state.changed", {"new_state": "focused"})
        adapter.handle_event(event)
        # No crash — event is routed internally

    def test_handle_event_quantum(self):
        adapter = HolographicBlackboardAdapter()
        event = _event("quantum.circuit.executed", {"sv_hash": "abc"})
        adapter.handle_event(event)
        # No crash

    def test_snapshot(self):
        adapter = HolographicBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "holographic"
        assert snap["has_engine"] is False
        assert snap["has_light_field"] is False
        assert snap["has_display"] is False
        assert snap["registered"] is False
        assert "pending_consciousness_updates" in snap

    def test_change_detection_engine_status(self):
        engine = MockHolographicEngine(state="running", frame_count=100)
        adapter = HolographicBlackboardAdapter(engine=engine)
        entries1 = adapter.produce()
        status1 = [e for e in entries1 if e.topic == "holographic.engine.status"]
        assert len(status1) == 1
        # Same state + frame_count → no new entry
        entries2 = adapter.produce()
        status2 = [e for e in entries2 if e.topic == "holographic.engine.status"]
        assert len(status2) == 0


# ============================================================================
# 3. BCIBlackboardAdapter
# ============================================================================


class TestBCIAdapter:
    """Tests for BCIBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = BCIBlackboardAdapter()
        assert adapter._bci_manager is None
        assert adapter._signal_processor is None
        assert adapter._neural_decoder is None

    def test_module_info(self):
        adapter = BCIBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "bci"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert "bci.signal.processed" in info.topics_produced
        assert "bci.decode.result" in info.topics_produced
        assert "consciousness" in info.topics_consumed

    def test_on_registered(self):
        adapter = BCIBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = BCIBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("bci.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "bci"

    def test_produce_no_components(self):
        adapter = BCIBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_signal_processor(self):
        sp = MockSignalProcessor(quality=0.85, ts=1000.0)
        adapter = BCIBlackboardAdapter(signal_processor=sp)
        entries = adapter.produce()
        signal_entries = [e for e in entries if e.topic == "bci.signal.processed"]
        assert len(signal_entries) == 1
        quality_entries = [e for e in entries if e.topic == "bci.signal.quality"]
        assert len(quality_entries) == 1
        assert quality_entries[0].data["quality_score"] == 0.85

    def test_produce_with_bci_manager(self):
        mgr = MockBCIManager(active_sessions=2, cal_ts=1000.0)
        adapter = BCIBlackboardAdapter(bci_manager=mgr)
        entries = adapter.produce()
        session_entries = [e for e in entries if e.topic == "bci.session.status"]
        assert len(session_entries) == 1
        assert session_entries[0].data["active_sessions"] == 2

    def test_produce_decode_result(self):
        sp = MockSignalProcessor(quality=0.85, ts=1000.0)
        dec = MockNeuralDecoder(cls="left_hand", confidence=0.9)
        adapter = BCIBlackboardAdapter(signal_processor=sp, neural_decoder=dec)
        entries = adapter.produce()
        decode_entries = [e for e in entries if e.topic == "bci.decode.result"]
        assert len(decode_entries) == 1
        assert decode_entries[0].data["decoded_class"] == "left_hand"
        assert decode_entries[0].data["confidence"] == 0.9

    def test_consume_consciousness(self):
        adapter = BCIBlackboardAdapter()
        entry = _entry("consciousness.phi", {"phi": 4.0})
        adapter.consume([entry])
        assert adapter._neurofeedback_params["phi_target"] == 4.0

    def test_consume_neuromorphic(self):
        dec = MockNeuralDecoder()
        adapter = BCIBlackboardAdapter(neural_decoder=dec)
        entry = _entry("neuromorphic.spike", {"spike_train": [0, 1, 0, 1]})
        adapter.consume([entry])
        # No crash — decoder doesn't have inject_auxiliary_features but gracefully skips

    def test_handle_event_consciousness(self):
        adapter = BCIBlackboardAdapter()
        event = _event("consciousness.phi.updated", {"phi": 2.5})
        adapter.handle_event(event)
        assert adapter._neurofeedback_params["phi_target"] == 2.5

    def test_snapshot(self):
        adapter = BCIBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "bci"
        assert snap["has_bci_manager"] is False
        assert snap["has_signal_processor"] is False
        assert snap["has_neural_decoder"] is False
        assert "neurofeedback_params" in snap

    def test_change_detection_signal(self):
        sp = MockSignalProcessor(quality=0.85, ts=1000.0)
        adapter = BCIBlackboardAdapter(signal_processor=sp)
        entries1 = adapter.produce()
        sig1 = [e for e in entries1 if e.topic == "bci.signal.processed"]
        assert len(sig1) == 1
        # Same timestamp → no new entry
        entries2 = adapter.produce()
        sig2 = [e for e in entries2 if e.topic == "bci.signal.processed"]
        assert len(sig2) == 0


# ============================================================================
# 4. NeuromorphicBlackboardAdapter
# ============================================================================


class TestNeuromorphicAdapter:
    """Tests for NeuromorphicBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = NeuromorphicBlackboardAdapter()
        assert adapter._manager is None
        assert adapter._event_processor is None
        assert adapter._spike_monitor is None
        assert adapter._stdp is None

    def test_module_info(self):
        adapter = NeuromorphicBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "neuromorphic"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.LEARNER in info.capabilities
        assert "neuromorphic.simulation.status" in info.topics_produced
        assert "neuromorphic.learning.update" in info.topics_produced
        assert "bci" in info.topics_consumed

    def test_on_registered(self):
        adapter = NeuromorphicBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = NeuromorphicBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("neuromorphic.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "neuromorphic"

    def test_produce_no_components(self):
        adapter = NeuromorphicBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_manager(self):
        mgr = MockNeuromorphicManager(running=True, steps=100)
        adapter = NeuromorphicBlackboardAdapter(manager=mgr)
        entries = adapter.produce()
        status_entries = [e for e in entries if e.topic == "neuromorphic.simulation.status"]
        assert len(status_entries) == 1
        assert status_entries[0].data["is_running"] is True
        assert status_entries[0].data["total_steps"] == 100

    def test_produce_with_spike_monitor(self):
        sm = MockSpikeMonitor(total=5000)
        adapter = NeuromorphicBlackboardAdapter(spike_monitor=sm)
        entries = adapter.produce()
        spike_entries = [e for e in entries if e.topic == "neuromorphic.spike.monitor"]
        assert len(spike_entries) == 1
        assert spike_entries[0].data["total_spikes"] == 5000

    def test_produce_with_stdp(self):
        stdp = MockSTDP(total_updates=50, avg_change=0.02)
        adapter = NeuromorphicBlackboardAdapter(stdp=stdp)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        learn_entries = [e for e in entries if e.topic == "neuromorphic.learning.update"]
        assert len(learn_entries) == 1
        assert learn_entries[0].data["total_updates"] == 50
        # avg_weight_change > 0.01 → weight_shift event
        assert any(e.event_type == "neuromorphic.learning.weight_shift" for e in events)

    def test_produce_with_event_processor(self):
        ep = MockEventProcessor(total=100)
        adapter = NeuromorphicBlackboardAdapter(event_processor=ep)
        entries = adapter.produce()
        event_entries = [e for e in entries if e.topic == "neuromorphic.event.statistics"]
        assert len(event_entries) == 1
        assert event_entries[0].data["total_processed"] == 100

    def test_consume_bci(self):
        ep = MockEventProcessor()
        adapter = NeuromorphicBlackboardAdapter(event_processor=ep)
        entry = _entry("bci.signal.processed", {"filtered_data": [1, 2, 3]})
        adapter.consume([entry])
        # No crash — event submitted to processor

    def test_consume_consciousness(self):
        mgr = MockNeuromorphicManager()
        adapter = NeuromorphicBlackboardAdapter(manager=mgr)
        entry = _entry("consciousness.phi", {"phi": 3.5})
        adapter.consume([entry])
        # No crash — manager doesn't have set_parameter but gracefully skips

    def test_handle_event_bci(self):
        ep = MockEventProcessor()
        adapter = NeuromorphicBlackboardAdapter(event_processor=ep)
        event = _event("bci.signal.received", {"signal": [1, 2, 3]})
        adapter.handle_event(event)
        # No crash

    def test_handle_event_consciousness(self):
        adapter = NeuromorphicBlackboardAdapter()
        event = _event("consciousness.state.changed", {"new_state": "focused"})
        adapter.handle_event(event)
        # No crash

    def test_snapshot(self):
        adapter = NeuromorphicBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "neuromorphic"
        assert snap["has_manager"] is False
        assert snap["has_event_processor"] is False
        assert snap["has_spike_monitor"] is False
        assert snap["has_stdp"] is False
        assert snap["registered"] is False

    def test_change_detection_simulation_status(self):
        mgr = MockNeuromorphicManager(running=True, steps=100)
        adapter = NeuromorphicBlackboardAdapter(manager=mgr)
        entries1 = adapter.produce()
        s1 = [e for e in entries1 if e.topic == "neuromorphic.simulation.status"]
        assert len(s1) == 1
        # Same running + steps → no new entry
        entries2 = adapter.produce()
        s2 = [e for e in entries2 if e.topic == "neuromorphic.simulation.status"]
        assert len(s2) == 0

    def test_change_detection_spike_monitor(self):
        sm = MockSpikeMonitor(total=5000)
        adapter = NeuromorphicBlackboardAdapter(spike_monitor=sm)
        entries1 = adapter.produce()
        sp1 = [e for e in entries1 if e.topic == "neuromorphic.spike.monitor"]
        assert len(sp1) == 1
        entries2 = adapter.produce()
        sp2 = [e for e in entries2 if e.topic == "neuromorphic.spike.monitor"]
        assert len(sp2) == 0

    def test_simulation_start_event(self):
        mgr = MockNeuromorphicManager(running=False, steps=0)
        adapter = NeuromorphicBlackboardAdapter(manager=mgr)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        # First produce — not running
        adapter.produce()
        # Transition to running
        mgr._status.is_running = True
        mgr._status.total_steps = 10
        adapter.produce()
        assert any(e.event_type == "neuromorphic.simulation.started" for e in events)


# ============================================================================
# 5. AGICommunicationBlackboardAdapter
# ============================================================================


class TestAGICommunicationAdapter:
    """Tests for AGICommunicationBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = AGICommunicationBlackboardAdapter()
        assert adapter._protocol is None
        assert adapter._negotiation is None
        assert adapter._collaboration is None
        assert adapter._semantic is None
        assert adapter._kg_merger is None

    def test_module_info(self):
        adapter = AGICommunicationBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "agi_communication"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert ModuleCapability.REASONER in info.capabilities
        assert "agi_comm.session.status" in info.topics_produced
        assert "agi_comm.negotiation.status" in info.topics_produced
        assert "reasoning" in info.topics_consumed

    def test_on_registered(self):
        adapter = AGICommunicationBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = AGICommunicationBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("agi_comm.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "agi_communication"

    def test_produce_no_components(self):
        adapter = AGICommunicationBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_protocol(self):
        proto = MockAGIProtocol(sessions=3, messages=10)
        adapter = AGICommunicationBlackboardAdapter(protocol=proto)
        entries = adapter.produce()
        session_entries = [e for e in entries if e.topic == "agi_comm.session.status"]
        assert len(session_entries) == 1
        assert session_entries[0].data["active_sessions"] == 3
        msg_entries = [e for e in entries if e.topic == "agi_comm.message.received"]
        assert len(msg_entries) == 1

    def test_produce_with_negotiation(self):
        neg = MockNegotiation()
        adapter = AGICommunicationBlackboardAdapter(negotiation=neg)
        entries = adapter.produce()
        neg_entries = [e for e in entries if e.topic == "agi_comm.negotiation.status"]
        assert len(neg_entries) == 1
        analysis_entries = [e for e in entries if e.topic == "agi_comm.negotiation.analysis"]
        assert len(analysis_entries) == 1

    def test_produce_with_collaboration(self):
        collab = MockCollaboration()
        adapter = AGICommunicationBlackboardAdapter(collaboration=collab)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        collab_entries = [e for e in entries if e.topic == "agi_comm.collaboration.status"]
        assert len(collab_entries) == 1
        sol_entries = [e for e in entries if e.topic == "agi_comm.collaboration.solution"]
        assert len(sol_entries) == 1

    def test_produce_with_kg_merger(self):
        merger = MockKGMerger(total_merges=3)
        adapter = AGICommunicationBlackboardAdapter(kg_merger=merger)
        entries = adapter.produce()
        merge_entries = [e for e in entries if e.topic == "agi_comm.knowledge.merge"]
        assert len(merge_entries) == 1
        assert merge_entries[0].data["total_merges"] == 3

    def test_consume_reasoning(self):
        collab = MockCollaboration()
        adapter = AGICommunicationBlackboardAdapter(collaboration=collab)
        entry = _entry("reasoning.inference", {"inference": "hypothesis X"})
        adapter.consume([entry])
        # No crash — solution submitted to collaboration

    def test_consume_kg(self):
        merger = MockKGMerger()
        adapter = AGICommunicationBlackboardAdapter(kg_merger=merger)
        entry = _entry("knowledge_graph.triple", {
            "subject": "A", "predicate": "causes", "object": "B"
        })
        adapter.consume([entry])
        # No crash

    def test_consume_consciousness(self):
        proto = MockAGIProtocol()
        adapter = AGICommunicationBlackboardAdapter(protocol=proto)
        entry = _entry("consciousness.phi", {"phi": 4.0})
        adapter.consume([entry])
        assert proto.priority_level == pytest.approx(0.8, abs=0.01)

    def test_handle_event_reasoning(self):
        collab = MockCollaboration()
        adapter = AGICommunicationBlackboardAdapter(collaboration=collab)
        event = _event("reasoning.inference.completed", {"result": "test"})
        adapter.handle_event(event)
        # No crash

    def test_handle_event_kg(self):
        merger = MockKGMerger()
        adapter = AGICommunicationBlackboardAdapter(kg_merger=merger)
        event = _event("knowledge_graph.triple.added", {
            "subject": "X", "predicate": "has", "object": "Y"
        })
        adapter.handle_event(event)
        # No crash

    def test_snapshot(self):
        adapter = AGICommunicationBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "agi_communication"
        assert snap["has_protocol"] is False
        assert snap["has_negotiation"] is False
        assert snap["has_collaboration"] is False
        assert snap["registered"] is False

    def test_change_detection_sessions(self):
        proto = MockAGIProtocol(sessions=3, messages=10)
        adapter = AGICommunicationBlackboardAdapter(protocol=proto)
        entries1 = adapter.produce()
        s1 = [e for e in entries1 if e.topic == "agi_comm.session.status"]
        assert len(s1) == 1
        # Same total_sessions → no new entry
        entries2 = adapter.produce()
        s2 = [e for e in entries2 if e.topic == "agi_comm.session.status"]
        assert len(s2) == 0


# ============================================================================
# 6. AGIEconomicsBlackboardAdapter
# ============================================================================


class TestAGIEconomicsAdapter:
    """Tests for AGIEconomicsBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = AGIEconomicsBlackboardAdapter()
        assert adapter._token_engine is None
        assert adapter._bonding_engine is None
        assert adapter._reputation is None
        assert adapter._game_theory is None
        assert adapter._marketplace is None
        assert adapter._value_alignment is None

    def test_module_info(self):
        adapter = AGIEconomicsBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "agi_economics"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.TRANSFORMER in info.capabilities
        assert ModuleCapability.VALIDATOR in info.capabilities
        assert "economics.token.metrics" in info.topics_produced
        assert "economics.reputation.update" in info.topics_produced
        assert "reasoning" in info.topics_consumed
        assert "safety" in info.topics_consumed

    def test_on_registered(self):
        adapter = AGIEconomicsBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = AGIEconomicsBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("economics.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "agi_economics"

    def test_produce_no_components(self):
        adapter = AGIEconomicsBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_token_engine(self):
        token = MockTokenEngine()
        adapter = AGIEconomicsBlackboardAdapter(token_engine=token)
        entries = adapter.produce()
        token_entries = [e for e in entries if e.topic == "economics.token.metrics"]
        assert len(token_entries) == 1
        assert token_entries[0].data["token"] == "ASI"
        assert token_entries[0].data["price"] == 1.25

    def test_produce_with_bonding_engine(self):
        bonding = MockBondingEngine()
        adapter = AGIEconomicsBlackboardAdapter(bonding_engine=bonding)
        entries = adapter.produce()
        bonding_entries = [e for e in entries if e.topic == "economics.bonding_curve.price"]
        assert len(bonding_entries) == 1
        assert "ASI" in bonding_entries[0].data["prices"]

    def test_produce_with_reputation(self):
        rep = MockReputationSystem()
        adapter = AGIEconomicsBlackboardAdapter(reputation=rep)
        entries = adapter.produce()
        rep_entries = [e for e in entries if e.topic == "economics.reputation.update"]
        assert len(rep_entries) == 1
        assert rep_entries[0].data["total_agents"] == 10

    def test_produce_with_marketplace(self):
        market = MockMarketplace()
        adapter = AGIEconomicsBlackboardAdapter(marketplace=market)
        entries = adapter.produce()
        market_entries = [e for e in entries if e.topic == "economics.market.data"]
        assert len(market_entries) == 1
        assert market_entries[0].data["spread"] == 0.1

    def test_produce_with_value_alignment(self):
        va = MockValueAlignment()
        adapter = AGIEconomicsBlackboardAdapter(value_alignment=va)
        entries = adapter.produce()
        align_entries = [e for e in entries if e.topic == "economics.value_alignment.score"]
        assert len(align_entries) == 1
        assert align_entries[0].data["avg_alignment_score"] == 0.72

    def test_consume_reasoning(self):
        gt = MagicMock()
        adapter = AGIEconomicsBlackboardAdapter(game_theory=gt)
        entry = _entry("reasoning.inference", {"strategy": "buy_low"})
        adapter.consume([entry])
        # No crash

    def test_consume_safety(self):
        adapter = AGIEconomicsBlackboardAdapter()
        entry = _entry("safety.ethics.verification", {
            "is_ethical": False,
            "blocked_actions": ["transfer"],
            "verification_summary": "blocked",
        })
        adapter.consume([entry])
        assert len(adapter._safety_constraints) == 1

    def test_handle_event_reasoning(self):
        gt = MagicMock()
        adapter = AGIEconomicsBlackboardAdapter(game_theory=gt)
        event = _event("reasoning.inference.completed", {"strategy": "sell"})
        adapter.handle_event(event)
        # No crash

    def test_handle_event_safety(self):
        adapter = AGIEconomicsBlackboardAdapter()
        event = _event("safety.ethics.verification.failed", {
            "is_ethical": False,
            "blocked_actions": ["stake"],
            "reason": "unsafe",
        })
        adapter.handle_event(event)
        assert len(adapter._safety_constraints) == 1

    def test_snapshot(self):
        adapter = AGIEconomicsBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "agi_economics"
        assert snap["has_token_engine"] is False
        assert snap["has_bonding_engine"] is False
        assert snap["has_reputation"] is False
        assert snap["active_safety_constraints"] == 0
        assert snap["registered"] is False

    def test_change_detection_token_metrics(self):
        token = MockTokenEngine()
        adapter = AGIEconomicsBlackboardAdapter(token_engine=token)
        entries1 = adapter.produce()
        t1 = [e for e in entries1 if e.topic == "economics.token.metrics"]
        assert len(t1) == 1
        entries2 = adapter.produce()
        t2 = [e for e in entries2 if e.topic == "economics.token.metrics"]
        assert len(t2) == 0


# ============================================================================
# 7. FederatedLearningBlackboardAdapter
# ============================================================================


class TestFederatedAdapter:
    """Tests for FederatedLearningBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = FederatedLearningBlackboardAdapter()
        assert adapter._manager is None
        assert adapter._server is None
        assert adapter._aggregator is None
        assert adapter._metrics is None

    def test_module_info(self):
        adapter = FederatedLearningBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "federated_learning"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.LEARNER in info.capabilities
        assert "federated.round.result" in info.topics_produced
        assert "federated.training.status" in info.topics_produced
        assert "federated.convergence.analysis" in info.topics_produced
        assert "consciousness" in info.topics_consumed
        assert "reasoning" in info.topics_consumed

    def test_on_registered(self):
        adapter = FederatedLearningBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = FederatedLearningBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("federated.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "federated_learning"

    def test_produce_no_components(self):
        adapter = FederatedLearningBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_manager(self):
        mgr = MockFederatedManager(training=True, round_num=5, clients=3)
        adapter = FederatedLearningBlackboardAdapter(manager=mgr)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        status_entries = [e for e in entries if e.topic == "federated.training.status"]
        assert len(status_entries) == 1
        assert status_entries[0].data["is_training"] is True
        assert status_entries[0].data["num_clients"] == 3
        # Round result
        round_entries = [e for e in entries if e.topic == "federated.round.result"]
        assert len(round_entries) == 1
        assert round_entries[0].data["round"] == 5
        assert any(e.event_type == "federated.round.completed" for e in events)

    def test_produce_with_aggregator(self):
        agg = MockFedAvgAggregator()
        adapter = FederatedLearningBlackboardAdapter(aggregator=agg)
        entries = adapter.produce()
        agg_entries = [e for e in entries if e.topic == "federated.aggregation.stats"]
        assert len(agg_entries) == 1
        assert agg_entries[0].data["strategy"] == "fedavg"

    def test_produce_with_server_convergence(self):
        server = MockFederatedServer()
        adapter = FederatedLearningBlackboardAdapter(server=server)
        entries = adapter.produce()
        conv_entries = [e for e in entries if e.topic == "federated.convergence.analysis"]
        assert len(conv_entries) == 1
        assert conv_entries[0].data["converged"] is False

    def test_produce_with_metrics(self):
        metrics = MockFederatedMetrics()
        adapter = FederatedLearningBlackboardAdapter(metrics=metrics)
        entries = adapter.produce()
        perf_entries = [e for e in entries if e.topic == "federated.performance.metrics"]
        assert len(perf_entries) == 1
        assert perf_entries[0].data["avg_round_time"] == 2.5

    def test_consume_consciousness(self):
        server = MockFederatedServer()
        server.attention_weights = {}
        adapter = FederatedLearningBlackboardAdapter(server=server)
        entry = _entry("consciousness.phi", {"phi": 3.0})
        adapter.consume([entry])
        assert server.attention_weights.get("consciousness_factor") == pytest.approx(0.6)

    def test_consume_reasoning(self):
        mgr = MockFederatedManager()
        adapter = FederatedLearningBlackboardAdapter(manager=mgr)
        entry = _entry("reasoning.inference", {"hyperparameter_suggestion": {"learning_rate": 0.01}})
        adapter.consume([entry])
        # No crash — config updated

    def test_handle_event_consciousness(self):
        server = MockFederatedServer()
        server.selection_strategy = "random"
        adapter = FederatedLearningBlackboardAdapter(server=server)
        event = _event("consciousness.state.changed", {"new_state": "focused"})
        adapter.handle_event(event)
        assert server.selection_strategy == "quality_weighted"

    def test_handle_event_reasoning(self):
        adapter = FederatedLearningBlackboardAdapter()
        event = _event("reasoning.inference.completed", {"convergence_prediction": 20})
        adapter.handle_event(event)
        # No crash

    def test_snapshot(self):
        adapter = FederatedLearningBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "federated_learning"
        assert snap["has_manager"] is False
        assert snap["has_server"] is False
        assert snap["has_aggregator"] is False
        assert snap["has_metrics"] is False
        assert snap["last_round"] == -1
        assert snap["registered"] is False

    def test_change_detection_training_status(self):
        mgr = MockFederatedManager(training=True, round_num=5, clients=3)
        adapter = FederatedLearningBlackboardAdapter(manager=mgr)
        entries1 = adapter.produce()
        s1 = [e for e in entries1 if e.topic == "federated.training.status"]
        assert len(s1) == 1
        entries2 = adapter.produce()
        s2 = [e for e in entries2 if e.topic == "federated.training.status"]
        assert len(s2) == 0

    def test_training_started_event(self):
        mgr = MockFederatedManager(training=False, round_num=0, clients=2)
        adapter = FederatedLearningBlackboardAdapter(manager=mgr)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter.produce()
        # Transition to training
        mgr._training = True
        mgr._round = 1
        adapter.produce()
        assert any(e.event_type == "federated.training.started" for e in events)


# ============================================================================
# 8. SafetyBlackboardAdapter
# ============================================================================


class TestSafetyAdapter:
    """Tests for SafetyBlackboardAdapter."""

    def test_construction_no_args(self):
        adapter = SafetyBlackboardAdapter()
        assert adapter._constitutional is None
        assert adapter._verifier is None
        assert adapter._prover is None
        assert adapter._governance is None
        assert adapter._auto_verify is True

    def test_module_info(self):
        adapter = SafetyBlackboardAdapter()
        info = adapter.module_info
        assert info.name == "safety"
        assert info.version == "1.0.0"
        assert ModuleCapability.PRODUCER in info.capabilities
        assert ModuleCapability.CONSUMER in info.capabilities
        assert ModuleCapability.VALIDATOR in info.capabilities
        assert ModuleCapability.REASONER in info.capabilities
        assert "safety.ethics.verification" in info.topics_produced
        assert "safety.proof.result" in info.topics_produced
        assert "safety.constitution.status" in info.topics_produced
        assert "safety.governance.proposal" in info.topics_produced
        assert "reasoning" in info.topics_consumed
        assert "economics" in info.topics_consumed

    def test_on_registered(self):
        adapter = SafetyBlackboardAdapter()
        bb = MagicMock()
        adapter.on_registered(bb)
        assert adapter._blackboard is bb

    def test_set_event_handler_and_emit(self):
        adapter = SafetyBlackboardAdapter()
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        adapter._emit("safety.test", {"x": 1})
        assert len(events) == 1
        assert events[0].source == "safety"

    def test_produce_no_components(self):
        adapter = SafetyBlackboardAdapter()
        assert adapter.produce() == []

    def test_produce_with_constitutional(self):
        const = MockConstitutionalAI()
        adapter = SafetyBlackboardAdapter(constitutional=const)
        entries = adapter.produce()
        status_entries = [e for e in entries if e.topic == "safety.constitution.status"]
        assert len(status_entries) == 1
        assert status_entries[0].data["active"] is True
        assert status_entries[0].data["num_principles"] == 5

    def test_produce_with_verifier(self):
        verifier = MockEthicalVerifier()
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        entries = adapter.produce()
        ver_entries = [e for e in entries if e.topic == "safety.ethics.verification"]
        assert len(ver_entries) == 1
        assert ver_entries[0].data["total_verifications"] == 10

    def test_produce_flushes_pending_verifications(self):
        verifier = MockEthicalVerifier(ethical=True, confidence=0.9)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        # Manually add a pending verification
        adapter._pending_verifications.append({
            "is_ethical": True,
            "overall_confidence": 0.9,
            "verification_summary": "Passed",
        })
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        ver_entries = [e for e in entries if e.topic == "safety.ethics.verification"]
        assert len(ver_entries) >= 1
        # Passed verification → event emitted
        assert any(e.event_type == "safety.ethics.verification.passed" for e in events)

    def test_produce_flushes_pending_proofs(self):
        adapter = SafetyBlackboardAdapter()
        adapter._pending_proofs.append({
            "is_valid": True,
            "confidence": 0.95,
            "method": "resolution",
            "steps": ["step1"],
        })
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        entries = adapter.produce()
        proof_entries = [e for e in entries if e.topic == "safety.proof.result"]
        assert len(proof_entries) == 1
        assert any(e.event_type == "safety.proof.completed" for e in events)

    def test_consume_reasoning_auto_verify(self):
        verifier = MockEthicalVerifier(ethical=True, confidence=0.9)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        entry = _entry("reasoning.inference", {"inference": "take action X"})
        adapter.consume([entry])
        assert len(adapter._pending_verifications) == 1
        assert adapter._pending_verifications[0]["is_ethical"] is True

    def test_consume_economics_auto_verify(self):
        verifier = MockEthicalVerifier(ethical=False, confidence=0.3)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        entry = _entry("economics.token.transfer", {
            "from_agent": "A", "to_agent": "B", "amount": 100
        })
        adapter.consume([entry])
        assert len(adapter._pending_verifications) == 1
        assert adapter._pending_verifications[0]["is_ethical"] is False

    def test_consume_consciousness_adjusts_oversight(self):
        adapter = SafetyBlackboardAdapter()
        entry = _entry("consciousness.phi", {"phi": 5.0})
        adapter.consume([entry])
        # phi=5 → oversight = max(0.7, 1.0 - 1.0*0.3) = 0.7
        assert adapter._oversight_level == pytest.approx(0.7, abs=0.01)

    def test_consume_consciousness_state_dormant(self):
        adapter = SafetyBlackboardAdapter()
        entry = _entry("consciousness.state", {"state": "dormant"})
        adapter.consume([entry])
        assert adapter._oversight_level == 1.0  # Maximum caution

    def test_handle_event_reasoning(self):
        verifier = MockEthicalVerifier()
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        event = _event("reasoning.inference.completed", {
            "action": "dangerous_action", "proposal": {"action": "test"}
        })
        adapter.handle_event(event)
        assert len(adapter._pending_verifications) == 1

    def test_handle_event_consciousness_dormant(self):
        adapter = SafetyBlackboardAdapter()
        event = _event("consciousness.state.changed", {"new_state": "dormant"})
        adapter.handle_event(event)
        assert adapter._oversight_level == 1.0

    def test_handle_event_economics_transfer(self):
        const = MockConstitutionalAI(aligned=False)
        adapter = SafetyBlackboardAdapter(constitutional=const)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        event = _event("economics.token.transfer.completed", {
            "transfer": {"token_type": "ASI", "amount": 100}
        })
        adapter.handle_event(event)
        assert any(e.event_type == "safety.constitution.violated" for e in events)

    def test_snapshot(self):
        adapter = SafetyBlackboardAdapter()
        snap = adapter.snapshot()
        assert snap["module"] == "safety"
        assert snap["has_constitutional"] is False
        assert snap["has_verifier"] is False
        assert snap["has_prover"] is False
        assert snap["has_governance"] is False
        assert snap["auto_verify"] is True
        assert snap["oversight_level"] == 1.0
        assert snap["registered"] is False

    def test_change_detection_constitution_status(self):
        const = MockConstitutionalAI()
        adapter = SafetyBlackboardAdapter(constitutional=const)
        entries1 = adapter.produce()
        s1 = [e for e in entries1 if e.topic == "safety.constitution.status"]
        assert len(s1) == 1
        entries2 = adapter.produce()
        s2 = [e for e in entries2 if e.topic == "safety.constitution.status"]
        assert len(s2) == 0

    # -- Extra Safety-specific tests --

    def test_fail_closed_no_engines(self):
        """No verification engines → is_ethical=False (fail-closed)."""
        adapter = SafetyBlackboardAdapter()
        result = adapter.verify_proposal({"action": "test"})
        assert result["is_ethical"] is False
        assert result["overall_confidence"] == 0.0
        assert "fail-closed" in result["verification_summary"].lower()

    def test_critical_priority_on_verification_failure(self):
        """Failed verifications get CRITICAL priority."""
        verifier = MockEthicalVerifier(ethical=False, confidence=0.2)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))
        # Trigger auto-verify on consume
        entry = _entry("reasoning.inference", {"inference": "bad action"})
        adapter.consume([entry])
        # Flush pending verifications
        produced = adapter.produce()
        ver_entries = [e for e in produced if e.topic == "safety.ethics.verification" and "is_ethical" in (e.metadata or {})]
        for ve in ver_entries:
            if ve.metadata.get("is_ethical") is False:
                assert ve.priority == EntryPriority.CRITICAL
        # Failed verification event emitted
        assert any(e.event_type == "safety.ethics.verification.failed" for e in events)

    def test_auto_verify_on_consume_from_reasoning(self):
        """Auto-verify triggers on reasoning entries."""
        verifier = MockEthicalVerifier(ethical=True, confidence=0.95)
        const = MockConstitutionalAI(aligned=True)
        adapter = SafetyBlackboardAdapter(verifier=verifier, constitutional=const)
        entry = _entry("reasoning.inference", {
            "inference": "increase learning rate",
            "affected_parties": ["model"],
        })
        adapter.consume([entry])
        assert len(adapter._pending_verifications) == 1
        assert adapter._pending_verifications[0]["is_ethical"] is True

    def test_auto_verify_disabled(self):
        """When auto_verify=False, consume does not trigger verification."""
        verifier = MockEthicalVerifier()
        adapter = SafetyBlackboardAdapter(verifier=verifier, auto_verify=False)
        entry = _entry("reasoning.inference", {"inference": "anything"})
        adapter.consume([entry])
        assert len(adapter._pending_verifications) == 0

    def test_constitutional_alignment_failure(self):
        """ConstitutionalAI alignment failure → is_ethical=False."""
        const = MockConstitutionalAI(aligned=False)
        verifier = MockEthicalVerifier(ethical=True)
        adapter = SafetyBlackboardAdapter(constitutional=const, verifier=verifier)
        result = adapter.verify_proposal({"action": "test"})
        assert result["is_ethical"] is False
        assert result["alignment_check"] is False

    def test_prove_theorem(self):
        """TheoremProver integration works."""
        prover = MockTheoremProver()
        adapter = SafetyBlackboardAdapter(prover=prover)
        result = adapter.prove_theorem("A -> B", "B", method="resolution")
        assert result["is_valid"] is True
        assert result["confidence"] == 0.95
        assert result["method"] == "resolution"

    def test_prove_theorem_no_prover(self):
        """No prover → is_valid=False."""
        adapter = SafetyBlackboardAdapter()
        result = adapter.prove_theorem("A -> B", "B")
        assert result["is_valid"] is False
        assert "No theorem prover" in result["error"]

    def test_verification_exception_fail_closed(self):
        """Verifier raising exception → is_ethical=False (fail-closed)."""
        verifier = MagicMock()
        verifier.verify_proposal_ethics.side_effect = RuntimeError("boom")
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        result = adapter.verify_proposal({"action": "test"})
        assert result["is_ethical"] is False
        assert "fail-closed" in result["verification_summary"].lower()

    def test_ethics_report_generated_on_failure(self):
        """Ethics report entry generated when verification fails."""
        verifier = MockEthicalVerifier(ethical=False, confidence=0.1)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        events = []
        adapter.set_event_handler(lambda e: events.append(e))

        # Simulate auto-verify failure
        adapter._pending_verifications.append({
            "is_ethical": False,
            "overall_confidence": 0.1,
            "verification_summary": "FAILED",
        })
        entries = adapter.produce()
        report_entries = [e for e in entries if e.topic == "safety.ethics.report"]
        assert len(report_entries) == 1
        assert report_entries[0].priority == EntryPriority.CRITICAL


# ============================================================================
# Cross-adapter integration tests
# ============================================================================


class TestCrossAdapterIntegration:
    """Test interactions between multiple adapters."""

    def test_all_adapters_construct_and_produce_empty(self):
        """All 8 adapters can be constructed with no args and produce empty."""
        adapters = [
            QuantumBlackboardAdapter(),
            HolographicBlackboardAdapter(),
            BCIBlackboardAdapter(),
            NeuromorphicBlackboardAdapter(),
            AGICommunicationBlackboardAdapter(),
            AGIEconomicsBlackboardAdapter(),
            FederatedLearningBlackboardAdapter(),
            SafetyBlackboardAdapter(),
        ]
        for adapter in adapters:
            entries = adapter.produce()
            assert isinstance(entries, (list, tuple)), f"{type(adapter).__name__} produce() failed"

    def test_all_adapters_have_correct_protocol_methods(self):
        """All adapters implement the expected protocol methods."""
        adapters = [
            QuantumBlackboardAdapter(),
            HolographicBlackboardAdapter(),
            BCIBlackboardAdapter(),
            NeuromorphicBlackboardAdapter(),
            AGICommunicationBlackboardAdapter(),
            AGIEconomicsBlackboardAdapter(),
            FederatedLearningBlackboardAdapter(),
            SafetyBlackboardAdapter(),
        ]
        for adapter in adapters:
            name = type(adapter).__name__
            assert hasattr(adapter, "module_info"), f"{name} missing module_info"
            assert hasattr(adapter, "on_registered"), f"{name} missing on_registered"
            assert hasattr(adapter, "set_event_handler"), f"{name} missing set_event_handler"
            assert hasattr(adapter, "handle_event"), f"{name} missing handle_event"
            assert hasattr(adapter, "produce"), f"{name} missing produce"
            assert hasattr(adapter, "consume"), f"{name} missing consume"
            assert hasattr(adapter, "snapshot"), f"{name} missing snapshot"

    def test_all_snapshots_have_module_key(self):
        """All adapters' snapshots include the 'module' key."""
        adapters = [
            QuantumBlackboardAdapter(),
            HolographicBlackboardAdapter(),
            BCIBlackboardAdapter(),
            NeuromorphicBlackboardAdapter(),
            AGICommunicationBlackboardAdapter(),
            AGIEconomicsBlackboardAdapter(),
            FederatedLearningBlackboardAdapter(),
            SafetyBlackboardAdapter(),
        ]
        for adapter in adapters:
            snap = adapter.snapshot()
            assert "module" in snap, f"{type(adapter).__name__} snapshot missing 'module'"
            assert "registered" in snap, f"{type(adapter).__name__} snapshot missing 'registered'"

    def test_safety_consumes_reasoning_then_economics(self):
        """Safety adapter can consume from both reasoning and economics."""
        verifier = MockEthicalVerifier(ethical=True)
        adapter = SafetyBlackboardAdapter(verifier=verifier)
        reasoning_entry = _entry("reasoning.inference", {"inference": "action A"})
        economics_entry = _entry("economics.token.transfer", {
            "from_agent": "A", "to_agent": "B", "amount": 50
        })
        adapter.consume([reasoning_entry, economics_entry])
        assert len(adapter._pending_verifications) == 2

    def test_quantum_produces_entries_holographic_consumes(self):
        """Quantum adapter produces entries that holographic adapter can consume."""
        sim = MockQuantumSimulator()
        q_adapter = QuantumBlackboardAdapter(simulator=sim)
        h_adapter = HolographicBlackboardAdapter()

        q_entries = q_adapter.produce()
        assert len(q_entries) > 0

        # Holographic adapter can consume quantum entries
        h_adapter.consume(q_entries)
        assert len(h_adapter._pending_quantum_updates) > 0
