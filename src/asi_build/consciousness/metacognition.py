"""
Metacognition System

This module implements metacognitive processes - the ability to think about
thinking, monitor cognitive processes, and regulate mental activity.

Key components:
- Metacognitive monitoring
- Cognitive control and regulation
- Metamemory and meta-learning
- Confidence and uncertainty assessment
- Strategy selection and adaptation
- Self-reflection and introspection
"""

import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


class CognitiveState(Enum):
    """Different cognitive states that can be monitored"""

    FOCUSED = "focused"
    DISTRACTED = "distracted"
    LEARNING = "learning"
    PROBLEM_SOLVING = "problem_solving"
    REMEMBERING = "remembering"
    REFLECTING = "reflecting"
    UNCERTAIN = "uncertain"
    CONFIDENT = "confident"


class MetacognitiveStrategy(Enum):
    """Different metacognitive strategies"""

    REHEARSAL = "rehearsal"
    ELABORATION = "elaboration"
    ORGANIZATION = "organization"
    MONITORING = "monitoring"
    PLANNING = "planning"
    EVALUATION = "evaluation"
    REGULATION = "regulation"


@dataclass
class CognitiveProcess:
    """Represents a cognitive process being monitored"""

    process_id: str
    process_type: str
    start_time: float
    estimated_duration: float
    difficulty_level: float
    confidence_level: float
    progress: float = 0.0
    resources_used: float = 0.0
    interruptions: int = 0
    success_probability: float = 0.5
    strategy_used: Optional[MetacognitiveStrategy] = None

    def get_efficiency(self) -> float:
        """Calculate process efficiency"""
        if self.resources_used > 0:
            return self.progress / self.resources_used
        return 0.0

    def is_overdue(self) -> bool:
        """Check if process is taking longer than estimated"""
        elapsed = time.time() - self.start_time
        return elapsed > self.estimated_duration * 1.2


@dataclass
class MetacognitiveJudgment:
    """Represents a metacognitive judgment or assessment"""

    judgment_id: str
    judgment_type: str  # 'confidence', 'difficulty', 'time', 'strategy'
    target_process: str
    value: float
    accuracy: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    reasoning: str = ""

    def calculate_calibration(self, actual_value: float) -> float:
        """Calculate how well calibrated this judgment was"""
        if actual_value is not None:
            error = abs(self.value - actual_value)
            calibration = 1.0 - min(1.0, error)
            self.accuracy = calibration
            return calibration
        return 0.0


@dataclass
class MetacognitiveStrategyInstance:
    """Represents a concrete metacognitive strategy instance"""

    strategy_id: str
    strategy_type: MetacognitiveStrategy
    description: str
    effectiveness: float = 0.5
    usage_count: int = 0
    success_rate: float = 0.0
    applicable_contexts: Set[str] = field(default_factory=set)

    def update_effectiveness(self, outcome: float) -> None:
        """Update strategy effectiveness based on outcome"""
        self.usage_count += 1
        # Exponential moving average
        alpha = 0.1
        self.effectiveness = alpha * outcome + (1 - alpha) * self.effectiveness

        # Update success rate
        if outcome > 0.7:
            successes = self.success_rate * (self.usage_count - 1) + 1
        else:
            successes = self.success_rate * (self.usage_count - 1)
        self.success_rate = successes / self.usage_count


class MetacognitionSystem(BaseConsciousness):
    """
    Implementation of Metacognitive Processes

    Monitors and regulates cognitive processes, makes judgments about
    mental states, and adapts strategies based on performance.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Pre-initialize instance attributes before super().__init__() which
        # calls _initialize() — attributes must exist before that hook runs.
        self.active_processes: Dict[str, CognitiveProcess] = {}
        self.completed_processes: deque = deque(maxlen=100)
        self.metacognitive_judgments: Dict[str, MetacognitiveJudgment] = {}
        self.available_strategies: Dict[str, MetacognitiveStrategyInstance] = {}
        self.current_cognitive_state = CognitiveState.FOCUSED
        self.state_history: deque = deque(maxlen=50)
        self.attention_monitor = AttentionMonitor()
        self.memory_monitor = MemoryMonitor()
        self.learning_monitor = LearningMonitor()
        self.cognitive_load = 0.0
        self.regulation_active = False
        self.overall_confidence = 0.5
        self.judgment_accuracy = 0.5
        self.strategy_effectiveness = defaultdict(float)
        self.metacognition_lock = threading.Lock()
        self.last_monitoring_time = 0
        self.total_judgments_made = 0
        self.total_strategies_applied = 0
        self.regulation_events = 0

        super().__init__("Metacognition", config)

        # Parameters (require self.config from super)
        self.max_cognitive_load = self.config.get("max_load", 1.0)
        self.load_threshold = self.config.get("load_threshold", 0.8)
        self.monitoring_interval = self.config.get("monitoring_interval", 0.5)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.uncertainty_threshold = self.config.get("uncertainty_threshold", 0.3)

    def _initialize(self):
        """Initialize the Metacognition system"""
        # Create default metacognitive strategies
        default_strategies = [
            (
                "rehearsal",
                MetacognitiveStrategy.REHEARSAL,
                "Repeat information to maintain in memory",
                {"memory", "learning"},
            ),
            (
                "elaboration",
                MetacognitiveStrategy.ELABORATION,
                "Connect new information to existing knowledge",
                {"learning", "understanding"},
            ),
            (
                "organization",
                MetacognitiveStrategy.ORGANIZATION,
                "Structure information for better comprehension",
                {"learning", "problem_solving"},
            ),
            (
                "self_monitoring",
                MetacognitiveStrategy.MONITORING,
                "Track progress and comprehension",
                {"all"},
            ),
            (
                "planning",
                MetacognitiveStrategy.PLANNING,
                "Set goals and allocate resources",
                {"problem_solving", "learning"},
            ),
            (
                "evaluation",
                MetacognitiveStrategy.EVALUATION,
                "Assess outcomes and performance",
                {"all"},
            ),
            (
                "cognitive_regulation",
                MetacognitiveStrategy.REGULATION,
                "Adjust cognitive processes based on monitoring",
                {"all"},
            ),
        ]

        for strategy_id, strategy_type, description, contexts in default_strategies:
            strategy = MetacognitiveStrategyInstance(
                strategy_id=strategy_id,
                strategy_type=strategy_type,
                description=description,
                applicable_contexts=set(contexts),
            )
            self.available_strategies[strategy_id] = strategy

        self.logger.info(
            f"Initialized Metacognition with {len(self.available_strategies)} strategies"
        )

    def start_cognitive_process(
        self, process_type: str, estimated_duration: float = 5.0, difficulty: float = 0.5
    ) -> str:
        """Start monitoring a new cognitive process"""
        process_id = f"{process_type}_{int(time.time() * 1000)}"

        process = CognitiveProcess(
            process_id=process_id,
            process_type=process_type,
            start_time=time.time(),
            estimated_duration=estimated_duration,
            difficulty_level=difficulty,
            confidence_level=self._estimate_initial_confidence(process_type, difficulty),
        )

        with self.metacognition_lock:
            self.active_processes[process_id] = process

        # Select appropriate strategy
        strategy = self._select_strategy(process_type, difficulty)
        if strategy:
            process.strategy_used = strategy.strategy_type
            self._apply_strategy(strategy, process)

        self.logger.info(f"Started monitoring process: {process_id}")
        return process_id

    def update_process_progress(
        self, process_id: str, progress: float, confidence: Optional[float] = None
    ) -> None:
        """Update progress and confidence for a cognitive process"""
        if process_id in self.active_processes:
            process = self.active_processes[process_id]
            process.progress = min(1.0, max(0.0, progress))

            if confidence is not None:
                process.confidence_level = confidence

            # Update resource usage
            elapsed = time.time() - process.start_time
            expected_elapsed = process.estimated_duration * process.progress
            if expected_elapsed > 0:
                process.resources_used = elapsed / expected_elapsed

            # Make metacognitive judgments
            self._make_progress_judgments(process)

    def complete_process(
        self, process_id: str, success: bool, actual_difficulty: Optional[float] = None
    ) -> None:
        """Mark a cognitive process as completed"""
        if process_id in self.active_processes:
            process = self.active_processes[process_id]
            process.progress = 1.0

            # Calculate final metrics
            total_time = time.time() - process.start_time
            efficiency = process.get_efficiency()

            # Update strategy effectiveness if strategy was used
            if process.strategy_used:
                strategy_id = self._get_strategy_id(process.strategy_used)
                if strategy_id in self.available_strategies:
                    outcome = 1.0 if success else 0.0
                    self.available_strategies[strategy_id].update_effectiveness(outcome)

            # Update judgment accuracy if we have actual difficulty
            if actual_difficulty is not None:
                self._update_judgment_accuracy(process_id, "difficulty", actual_difficulty)

            # Move to completed processes
            with self.metacognition_lock:
                self.completed_processes.append(process)
                del self.active_processes[process_id]

            self.logger.info(f"Completed process: {process_id}, success: {success}")

    def _estimate_initial_confidence(self, process_type: str, difficulty: float) -> float:
        """Estimate initial confidence for a process"""
        # Base confidence inversely related to difficulty
        base_confidence = 1.0 - difficulty

        # Adjust based on past experience with this process type
        similar_processes = [p for p in self.completed_processes if p.process_type == process_type]

        if similar_processes:
            avg_success = sum(p.progress for p in similar_processes[-10:]) / min(
                10, len(similar_processes)
            )
            base_confidence = (base_confidence + avg_success) / 2

        return max(0.1, min(0.9, base_confidence))

    def _select_strategy(
        self, process_type: str, difficulty: float
    ) -> Optional[MetacognitiveStrategy]:
        """Select the most appropriate strategy for a process"""
        applicable_strategies = []

        for strategy in self.available_strategies.values():
            if (
                process_type in strategy.applicable_contexts
                or "all" in strategy.applicable_contexts
            ):
                applicable_strategies.append(strategy)

        if not applicable_strategies:
            return None

        # Select based on effectiveness and appropriateness
        best_strategy = max(
            applicable_strategies, key=lambda s: s.effectiveness * (2.0 - difficulty)
        )

        return best_strategy

    def _apply_strategy(self, strategy: MetacognitiveStrategy, process: CognitiveProcess) -> None:
        """Apply a metacognitive strategy to a process"""
        self.total_strategies_applied += 1

        # Strategy-specific adjustments
        if strategy.strategy_type == MetacognitiveStrategy.PLANNING:
            # Adjust estimated duration based on difficulty
            process.estimated_duration *= 1.0 + process.difficulty_level * 0.5

        elif strategy.strategy_type == MetacognitiveStrategy.MONITORING:
            # Increase monitoring frequency for this process
            process.confidence_level *= 1.1  # Slight confidence boost from monitoring

        elif strategy.strategy_type == MetacognitiveStrategy.ELABORATION:
            # Increase resource requirement but improve success probability
            process.estimated_duration *= 1.2
            process.success_probability *= 1.3

        self.logger.debug(f"Applied strategy {strategy.strategy_id} to {process.process_id}")

    def _get_strategy_id(self, strategy_type: MetacognitiveStrategy) -> str:
        """Get strategy ID from strategy type"""
        for strategy_id, strategy in self.available_strategies.items():
            if strategy.strategy_type == strategy_type:
                return strategy_id
        return ""

    def make_metacognitive_judgment(
        self, judgment_type: str, target_process: str, reasoning: str = ""
    ) -> MetacognitiveJudgment:
        """Make a metacognitive judgment about a process"""
        judgment_id = f"judgment_{self.total_judgments_made:06d}"
        self.total_judgments_made += 1

        if target_process in self.active_processes:
            process = self.active_processes[target_process]

            # Calculate judgment value based on type
            if judgment_type == "confidence":
                value = process.confidence_level
            elif judgment_type == "difficulty":
                value = process.difficulty_level
            elif judgment_type == "time_remaining":
                elapsed = time.time() - process.start_time
                remaining = max(0, process.estimated_duration - elapsed)
                value = (
                    remaining / process.estimated_duration if process.estimated_duration > 0 else 0
                )
            elif judgment_type == "success_probability":
                value = process.success_probability
            else:
                value = 0.5  # Default

            judgment = MetacognitiveJudgment(
                judgment_id=judgment_id,
                judgment_type=judgment_type,
                target_process=target_process,
                value=value,
                reasoning=reasoning,
            )

            self.metacognitive_judgments[judgment_id] = judgment
            return judgment

        return None

    def _make_progress_judgments(self, process: CognitiveProcess) -> None:
        """Make automatic judgments about process progress"""
        # Confidence judgment
        confidence_judgment = self.make_metacognitive_judgment(
            "confidence",
            process.process_id,
            f"Based on progress {process.progress:.2f} and difficulty {process.difficulty_level:.2f}",
        )

        # Time estimation judgment
        if process.progress > 0.1:
            time_judgment = self.make_metacognitive_judgment(
                "time_remaining", process.process_id, f"Based on current progress rate"
            )

    def _update_judgment_accuracy(
        self, process_id: str, judgment_type: str, actual_value: float
    ) -> None:
        """Update accuracy of judgments based on actual outcomes"""
        # Find relevant judgments
        relevant_judgments = [
            j
            for j in self.metacognitive_judgments.values()
            if j.target_process == process_id and j.judgment_type == judgment_type
        ]

        for judgment in relevant_judgments:
            calibration = judgment.calculate_calibration(actual_value)

            # Update overall judgment accuracy
            alpha = 0.1
            self.judgment_accuracy = alpha * calibration + (1 - alpha) * self.judgment_accuracy

    def monitor_cognitive_state(self) -> CognitiveState:
        """Monitor and determine current cognitive state"""
        # Analyze current processes and metrics
        load = self.calculate_cognitive_load()
        confidence = self.calculate_overall_confidence()

        # Determine state based on metrics
        if load > self.load_threshold:
            state = CognitiveState.DISTRACTED
        elif confidence < self.uncertainty_threshold:
            state = CognitiveState.UNCERTAIN
        elif confidence > self.confidence_threshold:
            state = CognitiveState.CONFIDENT
        elif any(p.process_type == "learning" for p in self.active_processes.values()):
            state = CognitiveState.LEARNING
        elif any(p.process_type == "problem_solving" for p in self.active_processes.values()):
            state = CognitiveState.PROBLEM_SOLVING
        else:
            state = CognitiveState.FOCUSED

        # Update state history
        if state != self.current_cognitive_state:
            self.state_history.append((time.time(), self.current_cognitive_state, state))
            self.current_cognitive_state = state

        return state

    def calculate_cognitive_load(self) -> float:
        """Calculate current cognitive load"""
        if not self.active_processes:
            return 0.0

        total_load = 0.0
        for process in self.active_processes.values():
            # Load based on difficulty, resource usage, and time pressure
            difficulty_load = process.difficulty_level
            resource_load = process.resources_used

            # Time pressure (if overdue)
            time_pressure = 0.0
            if process.is_overdue():
                elapsed = time.time() - process.start_time
                overdue_factor = elapsed / process.estimated_duration - 1.0
                time_pressure = min(0.5, overdue_factor)

            process_load = difficulty_load + resource_load * 0.5 + time_pressure
            total_load += process_load

        # Normalize by max capacity
        self.cognitive_load = min(1.0, total_load / self.max_cognitive_load)
        return self.cognitive_load

    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence across all processes"""
        if not self.active_processes:
            return self.overall_confidence

        confidences = [p.confidence_level for p in self.active_processes.values()]
        current_confidence = sum(confidences) / len(confidences)

        # Exponential moving average
        alpha = 0.2
        self.overall_confidence = alpha * current_confidence + (1 - alpha) * self.overall_confidence

        return self.overall_confidence

    def regulate_cognition(self) -> List[str]:
        """Perform cognitive regulation based on monitoring"""
        regulations = []

        # Check if regulation is needed
        if self.cognitive_load > self.load_threshold:
            self.regulation_active = True
            self.regulation_events += 1

            # Identify problematic processes
            overloaded_processes = [
                p
                for p in self.active_processes.values()
                if p.resources_used > 1.5 or p.is_overdue()
            ]

            for process in overloaded_processes:
                # Apply regulation strategies
                if process.difficulty_level > 0.7:
                    # Break down difficult processes
                    regulations.append(f"Break down {process.process_id} into smaller steps")
                    process.difficulty_level *= 0.8

                if process.is_overdue():
                    # Adjust time estimates
                    regulations.append(f"Extend time estimate for {process.process_id}")
                    process.estimated_duration *= 1.5

                # Reduce confidence if struggling
                if (
                    process.progress < 0.3
                    and time.time() - process.start_time > process.estimated_duration * 0.5
                ):
                    process.confidence_level *= 0.9
                    regulations.append(f"Reduced confidence for struggling {process.process_id}")

        else:
            self.regulation_active = False

        return regulations

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "start_cognitive_process":
            process_type = event.data.get("process_type", "unknown")
            duration = event.data.get("duration", 5.0)
            difficulty = event.data.get("difficulty", 0.5)

            process_id = self.start_cognitive_process(process_type, duration, difficulty)

            return ConsciousnessEvent(
                event_id=f"process_started_{process_id}",
                timestamp=time.time(),
                event_type="process_started",
                data={"process_id": process_id},
                source_module="metacognition",
            )

        elif event.event_type == "update_process":
            process_id = event.data.get("process_id")
            progress = event.data.get("progress")
            confidence = event.data.get("confidence")

            if process_id and progress is not None:
                self.update_process_progress(process_id, progress, confidence)

        elif event.event_type == "make_judgment":
            judgment_type = event.data.get("judgment_type")
            target_process = event.data.get("target_process")
            reasoning = event.data.get("reasoning", "")

            if judgment_type and target_process:
                judgment = self.make_metacognitive_judgment(
                    judgment_type, target_process, reasoning
                )
                if judgment:
                    return ConsciousnessEvent(
                        event_id=f"judgment_made_{judgment.judgment_id}",
                        timestamp=time.time(),
                        event_type="metacognitive_judgment",
                        data={
                            "judgment_id": judgment.judgment_id,
                            "judgment_type": judgment.judgment_type,
                            "value": judgment.value,
                            "reasoning": judgment.reasoning,
                        },
                        source_module="metacognition",
                    )

        return None

    def update(self) -> None:
        """Update the Metacognition system"""
        current_time = time.time()

        # Periodic monitoring
        if current_time - self.last_monitoring_time > self.monitoring_interval:
            self.last_monitoring_time = current_time

            # Monitor cognitive state
            self.monitor_cognitive_state()

            # Calculate metrics
            self.calculate_cognitive_load()
            self.calculate_overall_confidence()

            # Perform regulation if needed
            regulations = self.regulate_cognition()

            # Update metrics
            self.metrics.metacognitive_accuracy = self.judgment_accuracy
            self.metrics.awareness_level = self.overall_confidence

            # Emit regulation events if any
            if regulations:
                regulation_event = ConsciousnessEvent(
                    event_id=f"regulation_{int(current_time)}",
                    timestamp=current_time,
                    event_type="cognitive_regulation",
                    data={"regulations": regulations, "cognitive_load": self.cognitive_load},
                    priority=7,
                    source_module="metacognition",
                )
                self.emit_event(regulation_event)

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Metacognition system"""
        return {
            "active_processes": len(self.active_processes),
            "completed_processes": len(self.completed_processes),
            "current_cognitive_state": self.current_cognitive_state.value,
            "cognitive_load": self.cognitive_load,
            "overall_confidence": self.overall_confidence,
            "judgment_accuracy": self.judgment_accuracy,
            "regulation_active": self.regulation_active,
            "total_judgments": self.total_judgments_made,
            "total_strategies_applied": self.total_strategies_applied,
            "regulation_events": self.regulation_events,
            "available_strategies": len(self.available_strategies),
            "strategy_effectiveness": {
                sid: s.effectiveness for sid, s in self.available_strategies.items()
            },
        }


# Supporting monitor classes
class AttentionMonitor:
    """Monitors attention-related metrics"""

    def __init__(self):
        self.focus_level = 0.5
        self.distractions = 0
        self.attention_switches = 0

    def update(self, focus_change: float):
        self.focus_level = max(0.0, min(1.0, self.focus_level + focus_change))
        if abs(focus_change) > 0.3:
            self.attention_switches += 1


class MemoryMonitor:
    """Monitors memory-related processes"""

    def __init__(self):
        self.retrieval_success_rate = 0.5
        self.encoding_efficiency = 0.5
        self.working_memory_load = 0.0

    def update_retrieval(self, success: bool):
        alpha = 0.1
        new_value = 1.0 if success else 0.0
        self.retrieval_success_rate = alpha * new_value + (1 - alpha) * self.retrieval_success_rate


class LearningMonitor:
    """Monitors learning processes"""

    def __init__(self):
        self.comprehension_level = 0.5
        self.learning_rate = 0.1
        self.retention_estimate = 0.5

    def update_comprehension(self, level: float):
        self.comprehension_level = max(0.0, min(1.0, level))
