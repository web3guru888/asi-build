"""
Attention Schema Theory (AST) Implementation
===========================================

Implementation of Michael Graziano's Attention Schema Theory for measuring
consciousness through attention monitoring and self-awareness mechanisms.

Key concepts:
- Attention Schema: Internal model of attention processes
- Self-Awareness: Monitoring of one's own attention states
- Social Awareness: Modeling others' attention states
- Attribution: Assigning attention and awareness to agents
- Metacognitive Control: Top-down control of attention

Based on Graziano's computational framework for consciousness.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import logging
from dataclasses import dataclass
from sklearn.cluster import KMeans
from scipy.signal import find_peaks

@dataclass
class AttentionState:
    """Snapshot of attention state and schema."""
    focus_locations: torch.Tensor
    attention_intensity: torch.Tensor
    schema_representation: torch.Tensor
    self_awareness_score: float
    metacognitive_confidence: float
    attention_control_strength: float
    
@dataclass
class SelfAwarenessProfile:
    """Profile of self-awareness capabilities."""
    attention_monitoring_accuracy: float
    schema_sophistication: float
    metacognitive_precision: float
    self_attribution_strength: float
    attention_control_efficacy: float
    social_awareness_capability: float

class AttentionSchemaAnalyzer:
    """
    Attention Schema Theory analyzer for consciousness assessment.
    
    Measures consciousness through attention schema modeling,
    self-awareness monitoring, and metacognitive control.
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize Attention Schema analyzer.
        
        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # AST parameters
        self.schema_dimensions = 64
        self.attention_window_size = 16
        self.awareness_threshold = 0.4
        self.metacognitive_depth = 3  # Levels of metacognition
        
        # Initialize attention schema networks
        self._initialize_schema_networks()
        
        # Attention history for temporal analysis
        self.attention_history: List[AttentionState] = []
        
    def _initialize_schema_networks(self):
        """Initialize attention schema neural networks."""
        # Attention location network
        self.attention_locator = nn.Sequential(
            nn.Linear(512, 256),  # Input will be adapted dynamically
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, self.attention_window_size),
            nn.Softmax(dim=-1)
        ).to(self.device)
        
        # Attention intensity estimator
        self.intensity_estimator = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        ).to(self.device)
        
        # Schema representation network
        self.schema_encoder = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, self.schema_dimensions),
            nn.Tanh()
        ).to(self.device)
        
        # Metacognitive monitoring network
        self.metacognitive_monitor = nn.Sequential(
            nn.Linear(self.schema_dimensions + self.attention_window_size + 1, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        ).to(self.device)
        
        # Attention control network
        self.attention_controller = nn.Sequential(
            nn.Linear(self.schema_dimensions, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 512),  # Control signals
            nn.Tanh()
        ).to(self.device)
        
        self.logger.info("Attention Schema Theory networks initialized")
    
    def measure_self_awareness(self, 
                             neural_activations: torch.Tensor,
                             attention_maps: Optional[torch.Tensor] = None) -> float:
        """
        Measure self-awareness through attention schema analysis.
        
        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            attention_maps: Optional attention mechanism outputs
            
        Returns:
            Self-awareness score (0-1)
        """
        self.logger.info("Measuring self-awareness through attention schema")
        
        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
                
            activations = neural_activations.to(self.device)
            
            # Adapt network input size if needed
            input_size = activations.shape[-1]
            self._adapt_network_sizes(input_size)
            
            # Analyze attention states over time
            awareness_profiles = []
            
            for t in range(activations.shape[1]):
                timestep_activations = activations[:, t, :]  # [batch, neurons]
                
                # Extract attention state
                attention_state = self._extract_attention_state(
                    timestep_activations, attention_maps
                )
                
                # Assess self-awareness for this timestep
                awareness_profile = self._assess_self_awareness(
                    attention_state, timestep_activations
                )
                awareness_profiles.append(awareness_profile)
                
                # Store attention state
                self.attention_history.append(attention_state)
                
                # Limit history size
                if len(self.attention_history) > 100:
                    self.attention_history.pop(0)
            
            # Aggregate self-awareness measures
            overall_awareness = self._aggregate_awareness_profiles(awareness_profiles)
            
            self.logger.info(f"Self-awareness score: {overall_awareness:.3f}")
            return overall_awareness
            
        except Exception as e:
            self.logger.error(f"Self-awareness measurement failed: {e}")
            return 0.0
    
    def _adapt_network_sizes(self, input_size: int):
        """Adapt network input sizes to match neural activations."""
        # Attention locator
        if hasattr(self.attention_locator[0], 'in_features'):
            if self.attention_locator[0].in_features != input_size:
                self.attention_locator[0] = nn.Linear(input_size, 256).to(self.device)
                nn.init.xavier_uniform_(self.attention_locator[0].weight)
                
        # Intensity estimator
        if hasattr(self.intensity_estimator[0], 'in_features'):
            if self.intensity_estimator[0].in_features != input_size:
                self.intensity_estimator[0] = nn.Linear(input_size, 128).to(self.device)
                nn.init.xavier_uniform_(self.intensity_estimator[0].weight)
                
        # Schema encoder
        if hasattr(self.schema_encoder[0], 'in_features'):
            if self.schema_encoder[0].in_features != input_size:
                self.schema_encoder[0] = nn.Linear(input_size, 256).to(self.device)
                nn.init.xavier_uniform_(self.schema_encoder[0].weight)
    
    def _extract_attention_state(self, 
                               activations: torch.Tensor,
                               attention_maps: Optional[torch.Tensor] = None) -> AttentionState:
        """
        Extract current attention state from neural activations.
        
        Args:
            activations: Neural activations [batch, neurons]
            attention_maps: Optional attention maps
            
        Returns:
            Current attention state
        """
        batch_size = activations.shape[0]
        
        # Compute attention focus locations
        focus_locations = self.attention_locator(activations)  # [batch, attention_window]
        
        # Compute attention intensity
        attention_intensity = self.intensity_estimator(activations)  # [batch, 1]
        
        # Generate attention schema representation
        schema_representation = self.schema_encoder(activations)  # [batch, schema_dims]
        
        # Compute metacognitive confidence
        metacognitive_input = torch.cat([
            schema_representation, 
            focus_locations, 
            attention_intensity
        ], dim=1)
        metacognitive_confidence = self.metacognitive_monitor(metacognitive_input)  # [batch, 1]
        
        # Compute attention control strength
        control_signals = self.attention_controller(schema_representation)  # [batch, neurons]
        control_strength = torch.mean(torch.abs(control_signals), dim=1, keepdim=True)  # [batch, 1]
        
        # Aggregate across batch for single state
        attention_state = AttentionState(
            focus_locations=torch.mean(focus_locations, dim=0),
            attention_intensity=torch.mean(attention_intensity, dim=0),
            schema_representation=torch.mean(schema_representation, dim=0),
            self_awareness_score=0.0,  # Will be computed separately
            metacognitive_confidence=torch.mean(metacognitive_confidence, dim=0).item(),
            attention_control_strength=torch.mean(control_strength, dim=0).item()
        )
        
        return attention_state
    
    def _assess_self_awareness(self, 
                             attention_state: AttentionState,
                             activations: torch.Tensor) -> SelfAwarenessProfile:
        """
        Assess self-awareness capabilities from attention state.
        
        Args:
            attention_state: Current attention state
            activations: Neural activations
            
        Returns:
            Self-awareness assessment profile
        """
        # 1. Attention monitoring accuracy
        monitoring_accuracy = self._compute_monitoring_accuracy(attention_state, activations)
        
        # 2. Schema sophistication
        schema_sophistication = self._compute_schema_sophistication(attention_state.schema_representation)
        
        # 3. Metacognitive precision
        metacognitive_precision = self._compute_metacognitive_precision(attention_state)
        
        # 4. Self-attribution strength
        self_attribution = self._compute_self_attribution(attention_state)
        
        # 5. Attention control efficacy
        control_efficacy = attention_state.attention_control_strength
        
        # 6. Social awareness capability (simplified)
        social_awareness = self._compute_social_awareness_capability(attention_state)
        
        return SelfAwarenessProfile(
            attention_monitoring_accuracy=monitoring_accuracy,
            schema_sophistication=schema_sophistication,
            metacognitive_precision=metacognitive_precision,
            self_attribution_strength=self_attribution,
            attention_control_efficacy=control_efficacy,
            social_awareness_capability=social_awareness
        )
    
    def _compute_monitoring_accuracy(self, 
                                   attention_state: AttentionState,
                                   activations: torch.Tensor) -> float:
        """Compute how accurately the system monitors its own attention."""
        # Compare predicted attention focus with actual neural activity patterns
        actual_focus = F.softmax(torch.mean(torch.abs(activations), dim=0)[:self.attention_window_size], dim=0)
        predicted_focus = attention_state.focus_locations
        
        # Compute alignment between predicted and actual focus
        alignment = F.cosine_similarity(
            actual_focus.unsqueeze(0), 
            predicted_focus.unsqueeze(0), 
            dim=1
        ).item()
        
        # Convert to accuracy score
        accuracy = max(0.0, (alignment + 1.0) / 2.0)  # Convert from [-1,1] to [0,1]
        
        return accuracy
    
    def _compute_schema_sophistication(self, schema_representation: torch.Tensor) -> float:
        """Compute sophistication of attention schema representation."""
        # Sophistication based on representational complexity and structure
        
        # 1. Representational richness (variance)
        richness = torch.var(schema_representation).item()
        
        # 2. Structural organization (entropy)
        schema_probs = F.softmax(torch.abs(schema_representation), dim=0)
        entropy = -torch.sum(schema_probs * torch.log(schema_probs + 1e-8)).item()
        entropy_normalized = entropy / np.log(len(schema_representation))
        
        # 3. Information density
        non_zero_ratio = torch.sum(torch.abs(schema_representation) > 0.1).item() / len(schema_representation)
        
        # Combine measures
        sophistication = (
            0.4 * min(richness, 1.0) +
            0.4 * entropy_normalized +
            0.2 * non_zero_ratio
        )
        
        return sophistication
    
    def _compute_metacognitive_precision(self, attention_state: AttentionState) -> float:
        """Compute precision of metacognitive monitoring."""
        # Precision based on confidence calibration and consistency
        
        confidence = attention_state.metacognitive_confidence
        
        # Historical consistency
        if len(self.attention_history) > 1:
            recent_confidences = [state.metacognitive_confidence for state in self.attention_history[-5:]]
            confidence_consistency = 1.0 - np.std(recent_confidences)
        else:
            confidence_consistency = 0.5
        
        # Attention-confidence correlation
        attention_strength = attention_state.attention_intensity.item()
        confidence_calibration = 1.0 - abs(confidence - attention_strength)
        
        # Combined precision
        precision = (
            0.4 * confidence +
            0.3 * confidence_consistency +
            0.3 * confidence_calibration
        )
        
        return max(0.0, min(1.0, precision))
    
    def _compute_self_attribution(self, attention_state: AttentionState) -> float:
        """Compute strength of self-attribution of attention."""
        # Self-attribution based on schema self-reference and control strength
        
        # Schema self-reference (how much the schema represents self-directed attention)
        schema_self_reference = torch.mean(torch.abs(attention_state.schema_representation)).item()
        
        # Control attribution (sense of control over attention)
        control_attribution = attention_state.attention_control_strength
        
        # Metacognitive self-model
        metacognitive_self_model = attention_state.metacognitive_confidence
        
        # Combined self-attribution
        self_attribution = (
            0.4 * schema_self_reference +
            0.4 * control_attribution +
            0.2 * metacognitive_self_model
        )
        
        return self_attribution
    
    def _compute_social_awareness_capability(self, attention_state: AttentionState) -> float:
        """Compute capability for modeling others' attention states."""
        # Simplified social awareness based on schema generalization capability
        
        # Schema flexibility (ability to model different attention states)
        schema_flexibility = torch.std(attention_state.schema_representation).item()
        
        # Attention modeling complexity
        focus_complexity = -torch.sum(
            attention_state.focus_locations * torch.log(attention_state.focus_locations + 1e-8)
        ).item()
        focus_complexity_normalized = focus_complexity / np.log(len(attention_state.focus_locations))
        
        # Theory of mind capability (simplified)
        tom_capability = min(schema_flexibility * focus_complexity_normalized, 1.0)
        
        return tom_capability
    
    def _aggregate_awareness_profiles(self, profiles: List[SelfAwarenessProfile]) -> float:
        """Aggregate self-awareness profiles into overall score."""
        if not profiles:
            return 0.0
        
        # Extract all measurements
        monitoring_scores = [p.attention_monitoring_accuracy for p in profiles]
        sophistication_scores = [p.schema_sophistication for p in profiles]
        precision_scores = [p.metacognitive_precision for p in profiles]
        attribution_scores = [p.self_attribution_strength for p in profiles]
        control_scores = [p.attention_control_efficacy for p in profiles]
        social_scores = [p.social_awareness_capability for p in profiles]
        
        # Aggregate with weights
        weights = {
            'monitoring': 0.25,
            'sophistication': 0.20,
            'precision': 0.20,
            'attribution': 0.15,
            'control': 0.10,
            'social': 0.10
        }
        
        overall_score = (
            weights['monitoring'] * np.mean(monitoring_scores) +
            weights['sophistication'] * np.mean(sophistication_scores) +
            weights['precision'] * np.mean(precision_scores) +
            weights['attribution'] * np.mean(attribution_scores) +
            weights['control'] * np.mean(control_scores) +
            weights['social'] * np.mean(social_scores)
        )
        
        return overall_score
    
    def analyze_attention_dynamics(self, 
                                 activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze attention schema dynamics over time.
        
        Args:
            activations_sequence: Sequence of neural activations
            
        Returns:
            Dictionary with attention dynamics analysis
        """
        awareness_scores = []
        control_strengths = []
        schema_stabilities = []
        
        for activations in activations_sequence:
            # Measure self-awareness
            awareness = self.measure_self_awareness(activations)
            awareness_scores.append(awareness)
            
            # Extract additional dynamics
            if self.attention_history:
                latest_state = self.attention_history[-1]
                control_strengths.append(latest_state.attention_control_strength)
                
                # Schema stability (compare with previous state)
                if len(self.attention_history) > 1:
                    prev_schema = self.attention_history[-2].schema_representation
                    curr_schema = latest_state.schema_representation
                    stability = F.cosine_similarity(
                        prev_schema.unsqueeze(0), 
                        curr_schema.unsqueeze(0), 
                        dim=1
                    ).item()
                    schema_stabilities.append(max(0.0, (stability + 1.0) / 2.0))
        
        # Compute dynamics metrics
        awareness_array = np.array(awareness_scores)
        
        dynamics = {
            'mean_self_awareness': float(np.mean(awareness_array)),
            'awareness_stability': float(1.0 / (1.0 + np.std(awareness_array))),
            'awareness_trend': float(np.polyfit(range(len(awareness_scores)), awareness_scores, 1)[0]) if len(awareness_scores) > 1 else 0.0
        }
        
        if control_strengths:
            dynamics['mean_control_strength'] = float(np.mean(control_strengths))
            dynamics['control_consistency'] = float(1.0 - np.std(control_strengths))
        
        if schema_stabilities:
            dynamics['schema_stability'] = float(np.mean(schema_stabilities))
        
        return dynamics
    
    def measure_attention_control_efficacy(self, 
                                         neural_activations: torch.Tensor,
                                         control_targets: Optional[torch.Tensor] = None) -> Dict[str, float]:
        """
        Measure efficacy of attention control mechanisms.
        
        Args:
            neural_activations: Neural activations
            control_targets: Optional target attention states
            
        Returns:
            Attention control efficacy measurements
        """
        control_metrics = {}
        
        try:
            activations = neural_activations.to(self.device)
            if activations.dim() == 2:
                activations = activations.unsqueeze(0)
            
            # Extract attention states
            attention_states = []
            control_signals_sequence = []
            
            for t in range(activations.shape[1]):
                timestep_activations = activations[:, t, :]
                attention_state = self._extract_attention_state(timestep_activations)
                attention_states.append(attention_state)
                
                # Generate control signals
                control_signals = self.attention_controller(attention_state.schema_representation.unsqueeze(0))
                control_signals_sequence.append(control_signals.squeeze(0))
            
            # Control strength
            control_strengths = [state.attention_control_strength for state in attention_states]
            control_metrics['mean_control_strength'] = float(np.mean(control_strengths))
            
            # Control consistency
            control_metrics['control_consistency'] = float(1.0 - np.std(control_strengths))
            
            # Control effectiveness (how well control signals influence subsequent states)
            if len(attention_states) > 1:
                effectiveness_scores = []
                
                for i in range(len(attention_states) - 1):
                    control_signal = control_signals_sequence[i]
                    next_state = attention_states[i + 1]
                    
                    # Measure influence of control on next attention state
                    predicted_influence = torch.mean(torch.abs(control_signal)).item()
                    actual_change = torch.mean(torch.abs(next_state.schema_representation)).item()
                    
                    # Effectiveness as correlation between control and change
                    effectiveness = min(predicted_influence / (actual_change + 1e-6), 1.0)
                    effectiveness_scores.append(effectiveness)
                
                control_metrics['control_effectiveness'] = float(np.mean(effectiveness_scores))
            else:
                control_metrics['control_effectiveness'] = 0.0
            
            # Control precision (granularity of control signals)
            all_control_signals = torch.stack(control_signals_sequence, dim=0)
            control_variance = torch.var(all_control_signals, dim=0)
            control_precision = torch.mean(control_variance).item()
            control_metrics['control_precision'] = control_precision
            
            if control_targets is not None:
                # Target-directed control efficacy
                target_similarities = []
                
                for control_signal in control_signals_sequence:
                    similarity = F.cosine_similarity(
                        control_signal.unsqueeze(0),
                        control_targets.flatten().unsqueeze(0),
                        dim=1
                    ).item()
                    target_similarities.append(max(0.0, (similarity + 1.0) / 2.0))
                
                control_metrics['target_control_efficacy'] = float(np.mean(target_similarities))
            
        except Exception as e:
            self.logger.error(f"Attention control efficacy measurement failed: {e}")
            control_metrics = {
                'mean_control_strength': 0.0,
                'control_consistency': 0.0,
                'control_effectiveness': 0.0,
                'control_precision': 0.0
            }
        
        return control_metrics
    
    def assess_metacognitive_sophistication(self, 
                                          neural_activations: torch.Tensor) -> Dict[str, float]:
        """
        Assess sophistication of metacognitive processes.
        
        Args:
            neural_activations: Neural activations
            
        Returns:
            Metacognitive sophistication assessment
        """
        metacognitive_metrics = {}
        
        try:
            activations = neural_activations.to(self.device)
            if activations.dim() == 2:
                activations = activations.unsqueeze(0)
            
            # Multi-level metacognition analysis
            metacognitive_levels = []
            
            for level in range(self.metacognitive_depth):
                level_metrics = self._analyze_metacognitive_level(activations, level)
                metacognitive_levels.append(level_metrics)
            
            # Aggregate metacognitive sophistication
            sophistication_scores = [metrics['sophistication'] for metrics in metacognitive_levels]
            metacognitive_metrics['overall_sophistication'] = float(np.mean(sophistication_scores))
            
            # Hierarchical depth
            depth_utilization = len([score for score in sophistication_scores if score > 0.3])
            metacognitive_metrics['metacognitive_depth'] = float(depth_utilization / self.metacognitive_depth)
            
            # Metacognitive integration
            integration_scores = [metrics['integration'] for metrics in metacognitive_levels]
            metacognitive_metrics['metacognitive_integration'] = float(np.mean(integration_scores))
            
        except Exception as e:
            self.logger.error(f"Metacognitive sophistication assessment failed: {e}")
            metacognitive_metrics = {
                'overall_sophistication': 0.0,
                'metacognitive_depth': 0.0,
                'metacognitive_integration': 0.0
            }
        
        return metacognitive_metrics
    
    def _analyze_metacognitive_level(self, 
                                   activations: torch.Tensor, 
                                   level: int) -> Dict[str, float]:
        """Analyze a specific level of metacognitive processing."""
        # Simplified multi-level metacognition analysis
        
        # Apply hierarchical attention at different levels
        level_factor = 2 ** level
        downsampled = F.avg_pool1d(
            activations.transpose(1, 2), 
            kernel_size=min(level_factor, activations.shape[1]),
            stride=max(1, level_factor // 2)
        ).transpose(1, 2)
        
        if downsampled.shape[1] == 0:
            return {'sophistication': 0.0, 'integration': 0.0}
        
        # Extract attention state at this level
        avg_activations = torch.mean(downsampled, dim=1)
        attention_state = self._extract_attention_state(avg_activations)
        
        # Level-specific sophistication
        sophistication = self._compute_schema_sophistication(attention_state.schema_representation)
        
        # Integration with other levels
        integration = attention_state.metacognitive_confidence
        
        return {
            'sophistication': sophistication,
            'integration': integration
        }