"""
Cognitive Synergy Engine - Main Orchestrator
============================================

The central orchestrator that coordinates all synergistic cognitive processes
based on Ben Goertzel's PRIMUS theory. This engine manages the interaction
between all synergy modules and maintains global cognitive coherence.
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import asyncio
import logging
import threading
import time
from collections import defaultdict, deque

from .primus_foundation import PRIMUSFoundation, CognitivePrimitive, PRIMUSState
from .synergy_metrics import SynergyMetrics
from .emergent_properties import EmergentPropertyDetector
from .self_organization import SelfOrganizationMechanism


@dataclass
class SynergyPair:
    """Represents a synergistic pair of cognitive processes"""
    process_a: str
    process_b: str
    synergy_strength: float
    bidirectional_flow: Dict[str, Any] = field(default_factory=dict)
    integration_level: float = 0.0
    emergence_indicators: List[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


@dataclass
class CognitiveDynamic:
    """Represents dynamic cognitive state changes"""
    dynamic_type: str  # 'oscillation', 'phase_transition', 'emergence', etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    intensity: float = 0.0
    duration: float = 0.0
    start_time: float = field(default_factory=time.time)


class CognitiveSynergyEngine:
    """
    Main engine orchestrating cognitive synergy according to PRIMUS theory.
    
    Manages 10 core synergy pairs:
    1. Pattern Mining ↔ Reasoning
    2. Perception ↔ Action  
    3. Memory ↔ Learning
    4. Attention ↔ Intention
    5. Symbolic ↔ Subsymbolic
    6. Local ↔ Global
    7. Reactive ↔ Deliberative
    8. Exploitation ↔ Exploration
    9. Self ↔ Other
    10. Conscious ↔ Unconscious
    """
    
    def __init__(self, 
                 primus_foundation: Optional[PRIMUSFoundation] = None,
                 update_frequency: float = 10.0,
                 synergy_threshold: float = 0.6,
                 emergence_threshold: float = 0.8):
        """
        Initialize the Cognitive Synergy Engine.
        
        Args:
            primus_foundation: PRIMUS foundation instance
            update_frequency: Hz for main processing loop
            synergy_threshold: Threshold for detecting synergy
            emergence_threshold: Threshold for detecting emergence
        """
        self.primus = primus_foundation or PRIMUSFoundation()
        self.update_frequency = update_frequency
        self.synergy_threshold = synergy_threshold
        self.emergence_threshold = emergence_threshold
        
        # Core synergy pairs
        self.synergy_pairs: Dict[str, SynergyPair] = {
            'pattern_reasoning': SynergyPair('pattern_mining', 'reasoning', 0.0),
            'perception_action': SynergyPair('perception', 'action', 0.0),
            'memory_learning': SynergyPair('memory', 'learning', 0.0),
            'attention_intention': SynergyPair('attention', 'intention', 0.0),
            'symbolic_subsymbolic': SynergyPair('symbolic', 'subsymbolic', 0.0),
            'local_global': SynergyPair('local', 'global', 0.0),
            'reactive_deliberative': SynergyPair('reactive', 'deliberative', 0.0),
            'exploit_explore': SynergyPair('exploitation', 'exploration', 0.0),
            'self_other': SynergyPair('self_model', 'other_model', 0.0),
            'conscious_unconscious': SynergyPair('conscious', 'unconscious', 0.0)
        }
        
        # Processing modules (to be populated by module registration)
        self.modules: Dict[str, Any] = {}
        
        # Synergy analysis components
        self.synergy_metrics = SynergyMetrics()
        self.emergence_detector = EmergentPropertyDetector()
        self.self_organization = SelfOrganizationMechanism()
        
        # Dynamic state tracking
        self.cognitive_dynamics: deque = deque(maxlen=1000)
        self.global_coherence = 0.0
        self.integration_matrix = np.zeros((10, 10))  # 10x10 for synergy pairs
        
        # Control and monitoring
        self._running = False
        self._main_thread = None
        self._lock = threading.RLock()
        
        # Performance tracking
        self.performance_history = defaultdict(list)
        self.emergence_events = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize synergy pair indices for matrix operations
        self.pair_indices = {name: i for i, name in enumerate(self.synergy_pairs.keys())}
    
    def register_module(self, name: str, module: Any):
        """Register a synergy module with the engine"""
        self.modules[name] = module
        self.logger.info(f"Registered module: {name}")
        
        # If module has initialization method, call it
        if hasattr(module, 'initialize'):
            module.initialize(self)
    
    def start(self):
        """Start the cognitive synergy engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start PRIMUS foundation
        self.primus.start()
        
        # Start main processing thread
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()
        
        self.logger.info("Cognitive Synergy Engine started")
    
    def stop(self):
        """Stop the cognitive synergy engine"""
        self._running = False
        
        # Stop PRIMUS foundation
        self.primus.stop()
        
        # Wait for main thread to finish
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=2.0)
        
        self.logger.info("Cognitive Synergy Engine stopped")
    
    def _main_loop(self):
        """Main processing loop"""
        sleep_time = 1.0 / self.update_frequency
        
        while self._running:
            try:
                loop_start = time.time()
                
                # Core synergy processing
                self._update_synergy_pairs()
                self._compute_global_coherence()
                self._detect_emergent_properties()
                self._update_integration_matrix()
                self._manage_cognitive_dynamics()
                
                # Self-organization
                self._apply_self_organization()
                
                # Performance tracking
                loop_time = time.time() - loop_start
                self.performance_history['loop_time'].append(loop_time)
                
                # Sleep for remaining time
                remaining_time = max(0, sleep_time - loop_time)
                time.sleep(remaining_time)
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                time.sleep(sleep_time)
    
    def _update_synergy_pairs(self):
        """Update all synergy pairs"""
        with self._lock:
            for pair_name, synergy_pair in self.synergy_pairs.items():
                self._update_single_synergy_pair(pair_name, synergy_pair)
    
    def _update_single_synergy_pair(self, pair_name: str, synergy_pair: SynergyPair):
        """Update a single synergy pair"""
        process_a = synergy_pair.process_a
        process_b = synergy_pair.process_b
        
        # Get modules for this pair
        module_a = self.modules.get(process_a)
        module_b = self.modules.get(process_b)
        
        if not (module_a and module_b):
            # Use PRIMUS primitives if modules not available
            self._update_pair_from_primitives(pair_name, synergy_pair)
            return
        
        # Get current states from modules
        state_a = self._get_module_state(module_a)
        state_b = self._get_module_state(module_b)
        
        # Compute synergy strength
        synergy_strength = self._compute_pair_synergy(state_a, state_b)
        synergy_pair.synergy_strength = synergy_strength
        
        # Update bidirectional information flow
        flow_a_to_b = self._compute_information_flow(state_a, state_b)
        flow_b_to_a = self._compute_information_flow(state_b, state_a)
        
        synergy_pair.bidirectional_flow = {
            f'{process_a}_to_{process_b}': flow_a_to_b,
            f'{process_b}_to_{process_a}': flow_b_to_a,
            'total_flow': flow_a_to_b + flow_b_to_a
        }
        
        # Update integration level
        synergy_pair.integration_level = self._compute_integration_level(
            synergy_strength, flow_a_to_b + flow_b_to_a
        )
        
        # Check for emergence indicators
        self._check_emergence_indicators(synergy_pair)
        
        synergy_pair.last_updated = time.time()
    
    def _update_pair_from_primitives(self, pair_name: str, synergy_pair: SynergyPair):
        """Update synergy pair using PRIMUS primitives when modules unavailable"""
        process_a = synergy_pair.process_a
        process_b = synergy_pair.process_b
        
        # Find relevant primitives
        primitives_a = [p for name, p in self.primus.primitives.items()
                       if process_a in name.lower()]
        primitives_b = [p for name, p in self.primus.primitives.items()
                       if process_b in name.lower()]
        
        if not (primitives_a and primitives_b):
            synergy_pair.synergy_strength *= 0.95  # Gradual decay
            return
        
        # Compute average synergy between primitive groups
        synergies = []
        for prim_a in primitives_a:
            for prim_b in primitives_b:
                synergy = self.primus.compute_synergy(prim_a.name, prim_b.name)
                synergies.append(synergy)
        
        synergy_pair.synergy_strength = np.mean(synergies) if synergies else 0.0
    
    def _get_module_state(self, module: Any) -> Dict[str, Any]:
        """Get state from a module"""
        if hasattr(module, 'get_state'):
            return module.get_state()
        elif hasattr(module, 'state'):
            return module.state
        else:
            return {'activation': getattr(module, 'activation', 0.0)}
    
    def _compute_pair_synergy(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> float:
        """Compute synergy between two process states"""
        # Extract numerical features from states
        features_a = self._extract_numerical_features(state_a)
        features_b = self._extract_numerical_features(state_b)
        
        if len(features_a) == 0 or len(features_b) == 0:
            return 0.0
        
        # Mutual information approximation
        mutual_info = self._estimate_mutual_information(features_a, features_b)
        
        # Correlation-based synergy
        correlation = np.corrcoef(features_a[:len(features_b)], features_b[:len(features_a)])[0, 1]
        correlation = 0.0 if np.isnan(correlation) else abs(correlation)
        
        # Combined synergy measure
        synergy = 0.6 * mutual_info + 0.4 * correlation
        return max(0.0, min(1.0, synergy))
    
    def _extract_numerical_features(self, state: Dict[str, Any]) -> np.ndarray:
        """Extract numerical features from state dictionary"""
        features = []
        
        for key, value in state.items():
            if isinstance(value, (int, float)):
                features.append(float(value))
            elif isinstance(value, np.ndarray):
                features.extend(value.flatten()[:10])  # Limit to prevent explosion
            elif isinstance(value, list) and all(isinstance(x, (int, float)) for x in value):
                features.extend(value[:10])
        
        return np.array(features) if features else np.array([0.0])
    
    def _estimate_mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        """Estimate mutual information between two feature vectors"""
        try:
            # Simple histogram-based MI estimation
            min_len = min(len(x), len(y))
            x_norm = (x[:min_len] - np.mean(x[:min_len])) / (np.std(x[:min_len]) + 1e-6)
            y_norm = (y[:min_len] - np.mean(y[:min_len])) / (np.std(y[:min_len]) + 1e-6)
            
            # Discretize for histogram
            x_disc = np.digitize(x_norm, bins=np.linspace(-3, 3, 10))
            y_disc = np.digitize(y_norm, bins=np.linspace(-3, 3, 10))
            
            # Joint histogram
            joint_hist = np.histogram2d(x_disc, y_disc, bins=10)[0]
            joint_hist = joint_hist / np.sum(joint_hist) + 1e-10
            
            # Marginal histograms
            x_hist = np.sum(joint_hist, axis=1)
            y_hist = np.sum(joint_hist, axis=0)
            
            # MI calculation
            mi = 0.0
            for i in range(len(x_hist)):
                for j in range(len(y_hist)):
                    if joint_hist[i, j] > 1e-10:
                        mi += joint_hist[i, j] * np.log2(joint_hist[i, j] / (x_hist[i] * y_hist[j]))
            
            return max(0.0, min(1.0, mi))
            
        except Exception:
            return 0.0
    
    def _compute_information_flow(self, source_state: Dict[str, Any], 
                                 target_state: Dict[str, Any]) -> float:
        """Compute information flow from source to target"""
        source_features = self._extract_numerical_features(source_state)
        target_features = self._extract_numerical_features(target_state)
        
        # Information flow approximated by feature activation correlation
        if len(source_features) > 0 and len(target_features) > 0:
            min_len = min(len(source_features), len(target_features))
            correlation = np.corrcoef(source_features[:min_len], target_features[:min_len])[0, 1]
            return max(0.0, correlation) if not np.isnan(correlation) else 0.0
        
        return 0.0
    
    def _compute_integration_level(self, synergy: float, total_flow: float) -> float:
        """Compute integration level from synergy and information flow"""
        return 0.7 * synergy + 0.3 * min(1.0, total_flow)
    
    def _check_emergence_indicators(self, synergy_pair: SynergyPair):
        """Check for emergence indicators in a synergy pair"""
        indicators = []
        
        # High synergy indicator
        if synergy_pair.synergy_strength > self.emergence_threshold:
            indicators.append('high_synergy')
        
        # Strong bidirectional flow
        total_flow = synergy_pair.bidirectional_flow.get('total_flow', 0)
        if total_flow > 0.8:
            indicators.append('strong_bidirectional_flow')
        
        # Rapid integration increase
        if hasattr(synergy_pair, '_prev_integration'):
            integration_change = synergy_pair.integration_level - synergy_pair._prev_integration
            if integration_change > 0.2:
                indicators.append('rapid_integration_increase')
        
        synergy_pair._prev_integration = synergy_pair.integration_level
        synergy_pair.emergence_indicators = indicators
        
        # Log significant emergence
        if len(indicators) >= 2:
            self.emergence_events.append({
                'pair': f"{synergy_pair.process_a}_{synergy_pair.process_b}",
                'indicators': indicators,
                'synergy': synergy_pair.synergy_strength,
                'timestamp': time.time()
            })
    
    def _compute_global_coherence(self):
        """Compute global cognitive coherence across all synergy pairs"""
        synergy_values = [pair.synergy_strength for pair in self.synergy_pairs.values()]
        integration_values = [pair.integration_level for pair in self.synergy_pairs.values()]
        
        # Coherence as weighted combination of synergy and integration
        coherence = 0.6 * np.mean(synergy_values) + 0.4 * np.mean(integration_values)
        
        # Apply nonlinear scaling to emphasize high coherence
        self.global_coherence = coherence ** 1.5
        
        # Track coherence history
        self.performance_history['global_coherence'].append(self.global_coherence)
    
    def _detect_emergent_properties(self):
        """Detect emergent properties across the cognitive system"""
        # Collect all emergence indicators
        all_indicators = []
        for pair in self.synergy_pairs.values():
            all_indicators.extend(pair.emergence_indicators)
        
        # Check for system-wide emergence patterns
        if len(all_indicators) >= 5:  # Multiple pairs showing emergence
            self.emergence_detector.detect_system_emergence(
                self.synergy_pairs, 
                self.global_coherence,
                self.integration_matrix
            )
    
    def _update_integration_matrix(self):
        """Update the integration matrix between synergy pairs"""
        pairs = list(self.synergy_pairs.items())
        n = len(pairs)
        
        for i, (name_i, pair_i) in enumerate(pairs):
            for j, (name_j, pair_j) in enumerate(pairs):
                if i != j:
                    # Integration based on shared processes or complementary functions
                    integration = self._compute_pair_integration(pair_i, pair_j)
                    self.integration_matrix[i, j] = integration
                else:
                    self.integration_matrix[i, j] = 1.0
    
    def _compute_pair_integration(self, pair1: SynergyPair, pair2: SynergyPair) -> float:
        """Compute integration level between two synergy pairs"""
        # Check for shared processes
        processes1 = {pair1.process_a, pair1.process_b}
        processes2 = {pair2.process_a, pair2.process_b}
        shared = len(processes1 & processes2)
        
        # Base integration from shared processes
        base_integration = shared / 2.0
        
        # Synergy-based integration
        synergy_integration = (pair1.synergy_strength * pair2.synergy_strength) ** 0.5
        
        # Combined integration
        return 0.4 * base_integration + 0.6 * synergy_integration
    
    def _manage_cognitive_dynamics(self):
        """Manage dynamic cognitive processes"""
        current_time = time.time()
        
        # Detect oscillations in synergy pairs
        self._detect_oscillations()
        
        # Detect phase transitions
        self._detect_phase_transitions()
        
        # Manage dynamic lifetimes
        self._cleanup_expired_dynamics()
    
    def _detect_oscillations(self):
        """Detect oscillatory patterns in synergy pairs"""
        for pair_name, pair in self.synergy_pairs.items():
            # Check synergy history for oscillations
            synergy_history = self.performance_history.get(f'{pair_name}_synergy', [])
            
            if len(synergy_history) > 10:
                # Simple oscillation detection using autocorrelation
                recent_history = np.array(synergy_history[-20:])
                if len(recent_history) > 5:
                    autocorr = np.correlate(recent_history, recent_history, mode='full')
                    autocorr = autocorr[len(autocorr)//2:]
                    
                    # Look for peaks indicating periodicity
                    if len(autocorr) > 3 and autocorr[2] > 0.7 * autocorr[0]:
                        dynamic = CognitiveDynamic(
                            dynamic_type='oscillation',
                            parameters={'pair': pair_name, 'period': 2},
                            intensity=autocorr[2] / autocorr[0]
                        )
                        self.cognitive_dynamics.append(dynamic)
            
            # Track synergy history
            if f'{pair_name}_synergy' not in self.performance_history:
                self.performance_history[f'{pair_name}_synergy'] = []
            self.performance_history[f'{pair_name}_synergy'].append(pair.synergy_strength)
    
    def _detect_phase_transitions(self):
        """Detect phase transitions in cognitive state"""
        # Check for sudden changes in global coherence
        coherence_history = self.performance_history['global_coherence']
        
        if len(coherence_history) > 5:
            recent_change = coherence_history[-1] - coherence_history[-5]
            if abs(recent_change) > 0.3:  # Significant change
                dynamic = CognitiveDynamic(
                    dynamic_type='phase_transition',
                    parameters={'coherence_change': recent_change},
                    intensity=abs(recent_change)
                )
                self.cognitive_dynamics.append(dynamic)
    
    def _cleanup_expired_dynamics(self):
        """Remove expired cognitive dynamics"""
        current_time = time.time()
        max_age = 60.0  # 1 minute
        
        self.cognitive_dynamics = deque([
            d for d in self.cognitive_dynamics
            if current_time - d.start_time < max_age
        ], maxlen=1000)
    
    def _apply_self_organization(self):
        """Apply self-organization mechanisms"""
        self.self_organization.apply(
            synergy_pairs=self.synergy_pairs,
            global_coherence=self.global_coherence,
            integration_matrix=self.integration_matrix,
            performance_history=self.performance_history
        )
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get comprehensive system state"""
        return {
            'primus_state': self.primus.get_system_state(),
            'synergy_pairs': {name: {
                'synergy_strength': pair.synergy_strength,
                'integration_level': pair.integration_level,
                'bidirectional_flow': pair.bidirectional_flow,
                'emergence_indicators': pair.emergence_indicators
            } for name, pair in self.synergy_pairs.items()},
            'global_coherence': self.global_coherence,
            'integration_matrix': self.integration_matrix.tolist(),
            'cognitive_dynamics': [
                {
                    'type': d.dynamic_type,
                    'parameters': d.parameters,
                    'intensity': d.intensity,
                    'age': time.time() - d.start_time
                }
                for d in self.cognitive_dynamics
            ],
            'emergence_events': self.emergence_events[-10:],  # Last 10 events
            'performance_metrics': {
                'average_synergy': np.mean([p.synergy_strength for p in self.synergy_pairs.values()]),
                'average_integration': np.mean([p.integration_level for p in self.synergy_pairs.values()]),
                'system_uptime': time.time() - getattr(self, '_start_time', time.time())
            }
        }
    
    def inject_stimulus(self, stimulus: Dict[str, Any]):
        """Inject stimulus into the cognitive system"""
        # Pass to PRIMUS foundation
        self.primus.inject_stimulus(stimulus)
        
        # Activate relevant synergy pairs based on stimulus type
        stimulus_type = stimulus.get('type', 'general')
        
        if stimulus_type == 'perceptual':
            self.synergy_pairs['perception_action'].synergy_strength = min(1.0,
                self.synergy_pairs['perception_action'].synergy_strength + 0.2)
        elif stimulus_type == 'learning':
            self.synergy_pairs['memory_learning'].synergy_strength = min(1.0,
                self.synergy_pairs['memory_learning'].synergy_strength + 0.2)
        elif stimulus_type == 'goal':
            self.synergy_pairs['attention_intention'].synergy_strength = min(1.0,
                self.synergy_pairs['attention_intention'].synergy_strength + 0.2)
    
    def get_synergy_strength(self, pair_name: str) -> float:
        """Get synergy strength for a specific pair"""
        return self.synergy_pairs.get(pair_name, SynergyPair('', '')).synergy_strength
    
    def get_emergence_indicators(self) -> List[Dict[str, Any]]:
        """Get current emergence indicators across all pairs"""
        indicators = []
        for name, pair in self.synergy_pairs.items():
            if pair.emergence_indicators:
                indicators.append({
                    'pair': name,
                    'indicators': pair.emergence_indicators,
                    'synergy': pair.synergy_strength,
                    'integration': pair.integration_level
                })
        return indicators
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()