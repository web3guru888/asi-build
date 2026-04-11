"""
Attention Schema Theory (AST) Implementation

Based on Michael Graziano's Attention Schema Theory, this module implements
a consciousness model where consciousness is the brain's model of its own
attention processes.

Key components:
- Attention processes and mechanisms
- Attention schema (model of attention)
- Awareness as attention modeling
- Spatial and temporal attention
- Attention competition and selection
"""

import time
import threading
import math
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import numpy as np

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState

@dataclass
class AttentionTarget:
    """Represents a target of attention"""
    target_id: str
    location: Tuple[float, float, float]  # 3D spatial location
    salience: float
    target_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    persistence: float = 1.0  # How long attention persists
    
    def calculate_distance(self, other: 'AttentionTarget') -> float:
        """Calculate spatial distance to another target"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.location, other.location)))

@dataclass
class AttentionProcess:
    """Represents an attention process"""
    process_id: str
    attention_type: str  # 'spatial', 'temporal', 'feature', 'object'
    current_target: Optional[str] = None
    attention_strength: float = 0.0
    focus_window: Tuple[float, float] = (1.0, 1.0)  # Width, duration
    inhibition_of_return: Set[str] = field(default_factory=set)
    last_shift_time: float = field(default_factory=time.time)
    
    def can_attend_to(self, target: AttentionTarget) -> bool:
        """Check if this process can attend to the target"""
        return target.target_id not in self.inhibition_of_return

@dataclass
class AttentionSchema:
    """The brain's model of its own attention state"""
    schema_id: str
    modeled_process: str
    confidence: float
    predicted_target: Optional[str] = None
    predicted_strength: float = 0.0
    predicted_duration: float = 0.0
    accuracy_history: List[float] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)
    
    def update_accuracy(self, actual_target: Optional[str], actual_strength: float) -> None:
        """Update schema accuracy based on actual attention state"""
        if self.predicted_target == actual_target:
            strength_error = abs(self.predicted_strength - actual_strength)
            accuracy = 1.0 - min(1.0, strength_error)
        else:
            accuracy = 0.0
        
        self.accuracy_history.append(accuracy)
        if len(self.accuracy_history) > 20:
            self.accuracy_history = self.accuracy_history[-20:]
        
        # Update confidence based on recent accuracy
        recent_accuracy = sum(self.accuracy_history) / len(self.accuracy_history)
        self.confidence = recent_accuracy

@dataclass
class AwarenessState:
    """Represents the current state of awareness"""
    aware_of: Set[str] = field(default_factory=set)
    awareness_strength: Dict[str, float] = field(default_factory=dict)
    awareness_location: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    global_awareness_level: float = 0.0
    attention_focus_point: Optional[Tuple[float, float, float]] = None
    timestamp: float = field(default_factory=time.time)

class AttentionSchemaTheory(BaseConsciousness):
    """
    Implementation of Attention Schema Theory
    
    Models consciousness as the brain's model of its own attention processes.
    Awareness emerges from the attention schema's monitoring of attention.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Pre-initialize instance attributes before super().__init__() which
        # calls _initialize() — attributes must exist before that hook runs.
        self.attention_targets: Dict[str, AttentionTarget] = {}
        self.attention_processes: Dict[str, AttentionProcess] = {}
        self.attention_schemas: Dict[str, AttentionSchema] = {}
        self.awareness_state = AwarenessState()
        self.spatial_attention_map = np.zeros((20, 20, 10))
        self.attention_history: deque = deque(maxlen=100)
        self.total_attention_shifts = 0
        self.schema_prediction_accuracy = 0.0
        self.awareness_episodes = []
        self.attention_lock = threading.Lock()

        super().__init__("AttentionSchema", config)

        # Parameters (require self.config from super)
        self.max_simultaneous_targets = self.config.get('max_targets', 5)
        self.attention_decay_rate = self.config.get('decay_rate', 0.95)
        self.salience_threshold = self.config.get('salience_threshold', 0.3)
        self.schema_update_rate = self.config.get('schema_update_rate', 0.1)
        self.attention_focus_sigma = self.config.get('focus_sigma', 2.0)
        self.temporal_window = self.config.get('temporal_window', 2.0)
        self.competition_strength = self.config.get('competition_strength', 0.8)
        self.winner_take_all_threshold = self.config.get('wta_threshold', 0.7)
    
    def _initialize(self):
        """Initialize the Attention Schema Theory system"""
        # Create default attention processes
        default_processes = [
            AttentionProcess("spatial_attention", "spatial"),
            AttentionProcess("temporal_attention", "temporal"),
            AttentionProcess("feature_attention", "feature"),
            AttentionProcess("object_attention", "object"),
            AttentionProcess("executive_attention", "executive")
        ]
        
        for process in default_processes:
            self.attention_processes[process.process_id] = process
        
        # Create attention schemas for each process
        for process_id in self.attention_processes:
            schema = AttentionSchema(
                schema_id=f"schema_{process_id}",
                modeled_process=process_id,
                confidence=0.5
            )
            self.attention_schemas[schema.schema_id] = schema
        
        self.logger.info(f"Initialized AST with {len(self.attention_processes)} processes")
    
    def add_attention_target(self, target: AttentionTarget) -> None:
        """Add a new target for attention"""
        with self.attention_lock:
            self.attention_targets[target.target_id] = target
            
            # Remove old targets if too many
            if len(self.attention_targets) > self.max_simultaneous_targets * 2:
                # Remove oldest low-salience targets
                sorted_targets = sorted(
                    self.attention_targets.items(),
                    key=lambda x: (x[1].salience, x[1].timestamp)
                )
                for target_id, _ in sorted_targets[:len(sorted_targets)//4]:
                    del self.attention_targets[target_id]
        
        self.logger.debug(f"Added attention target: {target.target_id}")
    
    def update_spatial_attention_map(self) -> None:
        """Update the spatial attention map based on current targets"""
        # Clear previous map
        self.spatial_attention_map.fill(0.0)
        
        # Add attention for each target
        for target in self.attention_targets.values():
            if target.salience > self.salience_threshold:
                x, y, z = target.location
                
                # Convert to map coordinates
                map_x = int(np.clip(x * 10, 0, 19))
                map_y = int(np.clip(y * 10, 0, 19))
                map_z = int(np.clip(z * 5, 0, 9))
                
                # Add Gaussian attention blob
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        for dz in range(-1, 2):
                            nx, ny, nz = map_x + dx, map_y + dy, map_z + dz
                            if 0 <= nx < 20 and 0 <= ny < 20 and 0 <= nz < 10:
                                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                                attention_value = target.salience * math.exp(
                                    -distance**2 / (2 * self.attention_focus_sigma**2)
                                )
                                self.spatial_attention_map[nx, ny, nz] += attention_value
    
    def compete_for_attention(self) -> Dict[str, str]:
        """Run attention competition to select winners"""
        winners = {}
        
        for process_id, process in self.attention_processes.items():
            if not self.attention_targets:
                continue
            
            # Calculate competition scores for each target
            competition_scores = {}
            
            for target_id, target in self.attention_targets.items():
                if not process.can_attend_to(target):
                    continue
                
                # Base score from salience
                score = target.salience
                
                # Add process-specific factors
                if process.attention_type == "spatial":
                    # Prefer targets closer to current focus
                    if process.current_target and process.current_target in self.attention_targets:
                        current_target = self.attention_targets[process.current_target]
                        distance = target.calculate_distance(current_target)
                        score *= math.exp(-distance * 0.5)
                
                elif process.attention_type == "temporal":
                    # Prefer newer targets
                    age = time.time() - target.timestamp
                    score *= math.exp(-age / self.temporal_window)
                
                elif process.attention_type == "feature":
                    # Prefer targets with distinctive features
                    uniqueness = target.properties.get('uniqueness', 0.5)
                    score *= (1.0 + uniqueness)
                
                competition_scores[target_id] = score
            
            # Select winner
            if competition_scores:
                winner_id = max(competition_scores.items(), key=lambda x: x[1])[0]
                winner_score = competition_scores[winner_id]
                
                # Apply winner-take-all threshold
                if winner_score > self.winner_take_all_threshold:
                    winners[process_id] = winner_id
                    
                    # Update process state
                    if process.current_target != winner_id:
                        process.last_shift_time = time.time()
                        self.total_attention_shifts += 1
                        
                        # Add previous target to inhibition of return
                        if process.current_target:
                            process.inhibition_of_return.add(process.current_target)
                            # Clean old inhibited targets
                            if len(process.inhibition_of_return) > 3:
                                process.inhibition_of_return.pop()
                    
                    process.current_target = winner_id
                    process.attention_strength = winner_score
        
        return winners
    
    def update_attention_schemas(self, current_attention_state: Dict[str, str]) -> None:
        """Update attention schemas based on current attention state"""
        for schema_id, schema in self.attention_schemas.items():
            process_id = schema.modeled_process
            
            if process_id in self.attention_processes:
                process = self.attention_processes[process_id]
                
                # Update schema accuracy
                schema.update_accuracy(process.current_target, process.attention_strength)
                
                # Make predictions for next step
                if process.current_target:
                    target = self.attention_targets.get(process.current_target)
                    if target:
                        # Predict continuation or shift based on target properties
                        shift_probability = self._calculate_shift_probability(process, target)
                        
                        if shift_probability < 0.5:
                            # Predict continuation
                            schema.predicted_target = process.current_target
                            schema.predicted_strength = process.attention_strength * 0.95
                            schema.predicted_duration = target.persistence
                        else:
                            # Predict shift to most salient alternative
                            alternatives = [
                                (tid, t) for tid, t in self.attention_targets.items()
                                if tid != process.current_target and t.salience > self.salience_threshold
                            ]
                            if alternatives:
                                best_alternative = max(alternatives, key=lambda x: x[1].salience)
                                schema.predicted_target = best_alternative[0]
                                schema.predicted_strength = best_alternative[1].salience
                            else:
                                schema.predicted_target = None
                                schema.predicted_strength = 0.0
                
                schema.last_updated = time.time()
    
    def _calculate_shift_probability(self, process: AttentionProcess, target: AttentionTarget) -> float:
        """Calculate probability of attention shifting away from current target"""
        # Base probability from target properties
        shift_prob = 1.0 - target.persistence
        
        # Increase probability based on time since last shift
        time_since_shift = time.time() - process.last_shift_time
        time_factor = min(1.0, time_since_shift / self.temporal_window)
        shift_prob += time_factor * 0.3
        
        # Increase probability if there are more salient competing targets
        max_competing_salience = 0.0
        for other_target in self.attention_targets.values():
            if other_target.target_id != target.target_id:
                max_competing_salience = max(max_competing_salience, other_target.salience)
        
        if max_competing_salience > target.salience:
            shift_prob += (max_competing_salience - target.salience) * 0.5
        
        return min(1.0, shift_prob)
    
    def generate_awareness(self) -> AwarenessState:
        """Generate awareness state based on attention schemas"""
        awareness = AwarenessState()
        
        # Collect what we're aware of based on attention schemas
        total_confidence = 0.0
        
        for schema in self.attention_schemas.values():
            if schema.predicted_target and schema.confidence > 0.5:
                target_id = schema.predicted_target
                
                # Add to awareness
                awareness.aware_of.add(target_id)
                awareness.awareness_strength[target_id] = schema.confidence * schema.predicted_strength
                
                # Add location if target exists
                if target_id in self.attention_targets:
                    target = self.attention_targets[target_id]
                    awareness.awareness_location[target_id] = target.location
                
                total_confidence += schema.confidence
        
        # Calculate global awareness level
        awareness.global_awareness_level = min(1.0, total_confidence / len(self.attention_schemas))
        
        # Find attention focus point (center of mass of attended locations)
        if awareness.awareness_location:
            x_coords = [loc[0] for loc in awareness.awareness_location.values()]
            y_coords = [loc[1] for loc in awareness.awareness_location.values()]
            z_coords = [loc[2] for loc in awareness.awareness_location.values()]
            
            awareness.attention_focus_point = (
                sum(x_coords) / len(x_coords),
                sum(y_coords) / len(y_coords),
                sum(z_coords) / len(z_coords)
            )
        
        return awareness
    
    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "add_attention_target":
            # Add new attention target
            target_data = event.data.get('target')
            if target_data:
                target = AttentionTarget(**target_data)
                self.add_attention_target(target)
        
        elif event.event_type == "shift_attention":
            # Force attention shift
            process_id = event.data.get('process_id')
            target_id = event.data.get('target_id')
            
            if process_id in self.attention_processes and target_id in self.attention_targets:
                process = self.attention_processes[process_id]
                process.current_target = target_id
                process.attention_strength = 1.0
                process.last_shift_time = time.time()
                self.total_attention_shifts += 1
        
        elif event.event_type == "query_awareness":
            # Return current awareness state
            return ConsciousnessEvent(
                event_id=f"awareness_report_{event.event_id}",
                timestamp=time.time(),
                event_type="awareness_state",
                data={
                    'aware_of': list(self.awareness_state.aware_of),
                    'awareness_strength': dict(self.awareness_state.awareness_strength),
                    'global_level': self.awareness_state.global_awareness_level,
                    'focus_point': self.awareness_state.attention_focus_point
                },
                source_module="attention_schema"
            )
        
        return None
    
    def update(self) -> None:
        """Update the Attention Schema Theory system"""
        # Decay existing targets
        current_time = time.time()
        targets_to_remove = []
        
        for target_id, target in self.attention_targets.items():
            target.salience *= self.attention_decay_rate
            if target.salience < 0.01 or (current_time - target.timestamp) > 10.0:
                targets_to_remove.append(target_id)
        
        for target_id in targets_to_remove:
            del self.attention_targets[target_id]
        
        # Update spatial attention map
        self.update_spatial_attention_map()
        
        # Run attention competition
        current_attention = self.compete_for_attention()
        
        # Update attention schemas
        self.update_attention_schemas(current_attention)
        
        # Generate awareness
        self.awareness_state = self.generate_awareness()
        
        # Store attention history
        self.attention_history.append({
            'timestamp': current_time,
            'attention_state': {pid: p.current_target for pid, p in self.attention_processes.items()},
            'awareness_level': self.awareness_state.global_awareness_level
        })
        
        # Update metrics
        self.metrics.awareness_level = self.awareness_state.global_awareness_level
        
        # Calculate average schema accuracy
        accuracies = []
        for schema in self.attention_schemas.values():
            if schema.accuracy_history:
                accuracies.append(sum(schema.accuracy_history) / len(schema.accuracy_history))
        
        self.schema_prediction_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
        self.metrics.prediction_accuracy = self.schema_prediction_accuracy
        
        # Focus attention metric
        if self.awareness_state.attention_focus_point:
            self.metrics.attention_focus = 1.0
        else:
            self.metrics.attention_focus = 0.0
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the Attention Schema system"""
        return {
            'num_targets': len(self.attention_targets),
            'num_processes': len(self.attention_processes),
            'num_schemas': len(self.attention_schemas),
            'total_attention_shifts': self.total_attention_shifts,
            'schema_accuracy': self.schema_prediction_accuracy,
            'awareness_level': self.awareness_state.global_awareness_level,
            'current_attention': {
                pid: p.current_target for pid, p in self.attention_processes.items()
            },
            'aware_of': list(self.awareness_state.aware_of),
            'attention_focus_point': self.awareness_state.attention_focus_point,
            'spatial_attention_peak': float(np.max(self.spatial_attention_map))
        }
    
    def get_attention_visualization_data(self) -> Dict[str, Any]:
        """Get data for visualizing attention state"""
        targets = []
        for target_id, target in self.attention_targets.items():
            targets.append({
                'id': target_id,
                'location': target.location,
                'salience': target.salience,
                'type': target.target_type,
                'being_attended': any(
                    p.current_target == target_id for p in self.attention_processes.values()
                )
            })
        
        processes = []
        for process_id, process in self.attention_processes.items():
            processes.append({
                'id': process_id,
                'type': process.attention_type,
                'current_target': process.current_target,
                'strength': process.attention_strength,
                'inhibited': list(process.inhibition_of_return)
            })
        
        schemas = []
        for schema_id, schema in self.attention_schemas.items():
            schemas.append({
                'id': schema_id,
                'modeled_process': schema.modeled_process,
                'confidence': schema.confidence,
                'predicted_target': schema.predicted_target,
                'predicted_strength': schema.predicted_strength
            })
        
        return {
            'targets': targets,
            'processes': processes,
            'schemas': schemas,
            'awareness_state': {
                'aware_of': list(self.awareness_state.aware_of),
                'global_level': self.awareness_state.global_awareness_level,
                'focus_point': self.awareness_state.attention_focus_point
            },
            'spatial_attention_map': self.spatial_attention_map.tolist()
        }
    
    def simulate_visual_scene(self, objects: List[Dict[str, Any]]) -> None:
        """Simulate a visual scene with objects to attend to"""
        # Clear existing targets
        self.attention_targets.clear()
        
        # Add scene objects as attention targets
        for i, obj in enumerate(objects):
            target = AttentionTarget(
                target_id=f"object_{i}",
                location=obj.get('location', (0.5, 0.5, 0.5)),
                salience=obj.get('salience', 0.5),
                target_type=obj.get('type', 'visual_object'),
                properties=obj.get('properties', {})
            )
            self.add_attention_target(target)
        
        self.logger.info(f"Simulated visual scene with {len(objects)} objects")