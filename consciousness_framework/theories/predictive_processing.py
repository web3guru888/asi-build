"""
Predictive Processing Consciousness Metrics
==========================================

Implementation of Predictive Processing theory for measuring consciousness
through predictive accuracy, hierarchical prediction, and active inference.

Key concepts:
- Predictive Hierarchies: Multi-level prediction systems
- Prediction Error: Difference between prediction and actual input
- Active Inference: Actions taken to minimize prediction error
- Precision-Weighted Prediction Errors: Attention as precision weighting
- Hierarchical Message Passing: Bottom-up prediction errors, top-down predictions

Based on Friston's Free Energy Principle and predictive processing frameworks.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from dataclasses import dataclass
from collections import deque
import math

@dataclass
class PredictionLevel:
    """Representation of a single level in the predictive hierarchy."""
    level: int
    prediction: torch.Tensor
    prediction_error: torch.Tensor
    precision: torch.Tensor
    confidence: float
    temporal_depth: int
    
@dataclass
class PredictiveHierarchy:
    """Complete predictive processing hierarchy."""
    levels: List[PredictionLevel]
    total_prediction_error: float
    hierarchical_consistency: float
    active_inference_score: float
    precision_weighted_error: float
    temporal_coherence: float
    
@dataclass
class ConsciousPredictionMetrics:
    """Consciousness metrics based on predictive processing."""
    predictive_accuracy: float
    hierarchical_integration: float
    active_inference_strength: float
    precision_modulation_efficacy: float
    temporal_prediction_depth: float
    surprise_minimization: float

class PredictiveProcessingMetrics:
    """
    Predictive Processing metrics for consciousness assessment.
    
    Measures consciousness through predictive accuracy, hierarchical prediction,
    precision-weighted prediction errors, and active inference capabilities.
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize Predictive Processing metrics.
        
        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Predictive processing parameters
        self.num_levels = 5  # Number of hierarchical levels
        self.temporal_depth = 8  # Depth of temporal predictions
        self.precision_learning_rate = 0.01
        self.prediction_horizon = 3  # Steps ahead to predict
        
        # Initialize predictive networks
        self._initialize_predictive_networks()
        
        # Prediction history for temporal analysis
        self.prediction_history: deque = deque(maxlen=50)
        
    def _initialize_predictive_networks(self):
        """Initialize predictive processing neural networks."""
        # Hierarchical predictive models (one for each level)
        self.predictive_models = nn.ModuleList()
        self.error_precision_estimators = nn.ModuleList()
        
        input_dims = [512, 256, 128, 64, 32]  # Decreasing dimensions up the hierarchy
        
        for level in range(self.num_levels):
            # Predictive model for this level
            predictor = nn.Sequential(
                nn.Linear(input_dims[level], input_dims[level] // 2),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(input_dims[level] // 2, input_dims[level] // 4),
                nn.ReLU(),
                nn.Linear(input_dims[level] // 4, input_dims[level]),
                nn.Tanh()
            )
            self.predictive_models.append(predictor)
            
            # Precision estimator for prediction errors
            precision_estimator = nn.Sequential(
                nn.Linear(input_dims[level], 64),
                nn.ReLU(),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid()  # Precision weights between 0 and 1
            )
            self.error_precision_estimators.append(precision_estimator)
        
        # Temporal prediction network
        self.temporal_predictor = nn.LSTM(
            input_size=512,
            hidden_size=256,
            num_layers=2,
            batch_first=True,
            dropout=0.2
        ).to(self.device)
        
        # Temporal prediction head
        self.temporal_prediction_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 512)
        ).to(self.device)
        
        # Active inference controller
        self.active_inference_controller = nn.Sequential(
            nn.Linear(512 + self.num_levels, 256),  # Input + precision weights
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 512),  # Action/attention control signals
            nn.Tanh()
        ).to(self.device)
        
        # Surprise computation network
        self.surprise_estimator = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Softplus()  # Always positive surprise
        ).to(self.device)
        
        self.logger.info("Predictive Processing networks initialized")
    
    def compute_prediction_metrics(self, 
                                 neural_activations: torch.Tensor,
                                 behavioral_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Compute predictive processing consciousness metrics.
        
        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            behavioral_data: Optional behavioral and response data
            
        Returns:
            Predictive processing error (lower = more conscious)
        """
        self.logger.info("Computing Predictive Processing consciousness metrics")
        
        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
                
            activations = neural_activations.to(self.device)
            
            # Adapt network input size if needed
            input_size = activations.shape[-1]
            self._adapt_network_sizes(input_size)
            
            # Process temporal sequence
            prediction_metrics_sequence = []
            
            for t in range(1, activations.shape[1]):  # Start from 1 to have previous state
                current_state = activations[:, t, :]  # [batch, neurons]
                previous_states = activations[:, max(0, t-self.temporal_depth):t, :]
                
                # Build predictive hierarchy
                predictive_hierarchy = self._build_predictive_hierarchy(
                    current_state, previous_states
                )
                
                # Compute consciousness metrics
                metrics = self._compute_consciousness_metrics(
                    predictive_hierarchy, current_state, behavioral_data
                )
                prediction_metrics_sequence.append(metrics)
                
                # Store prediction history
                self.prediction_history.append(predictive_hierarchy)
            
            # Aggregate prediction metrics
            if prediction_metrics_sequence:
                # Primary metric is prediction error (lower = better consciousness)
                prediction_errors = [1.0 - m.predictive_accuracy for m in prediction_metrics_sequence]
                average_prediction_error = np.mean(prediction_errors)
                
                # Additional temporal consistency
                temporal_consistency = self._compute_temporal_consistency(prediction_metrics_sequence)
                
                # Final prediction error (lower is better for consciousness)
                final_error = average_prediction_error * (2.0 - temporal_consistency)
                
                self.logger.info(f"Prediction error: {final_error:.3f}")
                return float(final_error)
            else:
                return 1.0  # Maximum error if no predictions
                
        except Exception as e:
            self.logger.error(f"Predictive processing metrics computation failed: {e}")
            return 1.0  # Return maximum error on failure
    
    def _adapt_network_sizes(self, input_size: int):
        """Adapt network input sizes to match neural activations."""
        # Adapt first predictive model
        if hasattr(self.predictive_models[0][0], 'in_features'):
            if self.predictive_models[0][0].in_features != input_size:
                # Rebuild first level with correct input size
                self.predictive_models[0][0] = nn.Linear(input_size, input_size // 2).to(self.device)
                self.predictive_models[0][2] = nn.Linear(input_size // 2, input_size // 4).to(self.device)
                self.predictive_models[0][4] = nn.Linear(input_size // 4, input_size).to(self.device)
                
                # Adapt precision estimator
                self.error_precision_estimators[0][0] = nn.Linear(input_size, 64).to(self.device)
                
                # Adapt temporal predictor
                self.temporal_predictor = nn.LSTM(
                    input_size=input_size,
                    hidden_size=256,
                    num_layers=2,
                    batch_first=True,
                    dropout=0.2
                ).to(self.device)
                
                # Adapt temporal prediction head
                self.temporal_prediction_head[2] = nn.Linear(128, input_size).to(self.device)
                
                # Adapt active inference controller
                self.active_inference_controller[0] = nn.Linear(
                    input_size + self.num_levels, 256
                ).to(self.device)
                self.active_inference_controller[4] = nn.Linear(128, input_size).to(self.device)
                
                # Adapt surprise estimator
                self.surprise_estimator[0] = nn.Linear(input_size, 128).to(self.device)
    
    def _build_predictive_hierarchy(self, 
                                   current_state: torch.Tensor,
                                   previous_states: torch.Tensor) -> PredictiveHierarchy:
        """
        Build hierarchical predictive processing structure.
        
        Args:
            current_state: Current neural state [batch, neurons]
            previous_states: Previous states [batch, time, neurons]
            
        Returns:
            Complete predictive hierarchy
        """
        batch_size = current_state.shape[0]
        levels = []
        
        # Start with the input level
        current_representation = current_state
        
        for level in range(self.num_levels):
            # Make prediction at this level
            prediction = self.predictive_models[level](current_representation)
            
            # Compute prediction error
            prediction_error = current_representation - prediction
            
            # Estimate precision (attention/confidence) for this error
            precision = self.error_precision_estimators[level](
                torch.abs(prediction_error)
            ).squeeze(-1)  # [batch]
            
            # Compute confidence for this level
            error_magnitude = torch.mean(torch.abs(prediction_error), dim=1)  # [batch]
            confidence = torch.exp(-error_magnitude).mean().item()
            
            # Create prediction level
            prediction_level = PredictionLevel(
                level=level,
                prediction=torch.mean(prediction, dim=0),  # Average across batch
                prediction_error=torch.mean(prediction_error, dim=0),
                precision=torch.mean(precision, dim=0),
                confidence=confidence,
                temporal_depth=min(previous_states.shape[1], self.temporal_depth)
            )
            levels.append(prediction_level)
            
            # Prepare input for next level (dimensionality reduction)
            if level < self.num_levels - 1:
                next_dim = current_representation.shape[1] // 2
                if next_dim > 0:
                    # Simple dimensionality reduction via pooling
                    current_representation = F.adaptive_avg_pool1d(
                        current_representation.unsqueeze(1), next_dim
                    ).squeeze(1)
                else:
                    break
        
        # Compute hierarchy-level metrics
        total_error = sum(torch.mean(torch.abs(level.prediction_error)).item() for level in levels)
        hierarchical_consistency = self._compute_hierarchical_consistency(levels)
        
        # Compute active inference score
        active_inference_score = self._compute_active_inference_score(
            current_state, levels, previous_states
        )
        
        # Compute precision-weighted error
        precision_weighted_error = self._compute_precision_weighted_error(levels)
        
        # Compute temporal coherence
        temporal_coherence = self._compute_temporal_coherence(previous_states, current_state)
        
        return PredictiveHierarchy(
            levels=levels,
            total_prediction_error=total_error,
            hierarchical_consistency=hierarchical_consistency,
            active_inference_score=active_inference_score,
            precision_weighted_error=precision_weighted_error,
            temporal_coherence=temporal_coherence
        )
    
    def _compute_hierarchical_consistency(self, levels: List[PredictionLevel]) -> float:
        """Compute consistency across hierarchical levels."""
        if len(levels) < 2:
            return 1.0
        
        consistency_scores = []
        
        for i in range(len(levels) - 1):
            current_level = levels[i]
            next_level = levels[i + 1]
            
            # Compare prediction patterns between adjacent levels
            if (current_level.prediction.shape[0] >= next_level.prediction.shape[0] and
                next_level.prediction.shape[0] > 0):
                
                # Downsample current level to match next level
                current_downsampled = F.adaptive_avg_pool1d(
                    current_level.prediction.unsqueeze(0),
                    next_level.prediction.shape[0]
                ).squeeze(0)
                
                # Compute similarity
                similarity = F.cosine_similarity(
                    current_downsampled.unsqueeze(0),
                    next_level.prediction.unsqueeze(0),
                    dim=1
                ).item()
                
                consistency_scores.append(max(0.0, (similarity + 1.0) / 2.0))
        
        return np.mean(consistency_scores) if consistency_scores else 0.0
    
    def _compute_active_inference_score(self, 
                                      current_state: torch.Tensor,
                                      levels: List[PredictionLevel],
                                      previous_states: torch.Tensor) -> float:
        """
        Compute active inference score - how well the system acts to minimize prediction error.
        """
        try:
            # Collect all precision weights
            precision_weights = torch.stack([level.precision for level in levels])
            
            # Create input for active inference controller
            controller_input = torch.cat([
                current_state.mean(dim=0),  # Average across batch
                precision_weights
            ], dim=0)
            
            # Generate control signal
            control_signal = self.active_inference_controller(
                controller_input.unsqueeze(0)
            ).squeeze(0)
            
            # Measure effectiveness of control signal
            # (How much it would reduce future prediction error)
            if previous_states.shape[1] > 1:
                # Simulate applying control signal to previous state
                prev_state = previous_states[:, -1, :].mean(dim=0)
                controlled_state = prev_state + 0.1 * control_signal  # Small control influence
                
                # Measure how this affects prediction accuracy
                prediction_improvement = torch.mean(torch.abs(
                    controlled_state - current_state.mean(dim=0)
                )).item()
                
                # Active inference score (lower prediction error after control = higher score)
                active_inference_score = 1.0 / (1.0 + prediction_improvement)
            else:
                active_inference_score = 0.5  # Default when insufficient temporal data
            
            return active_inference_score
            
        except Exception as e:
            self.logger.warning(f"Active inference computation failed: {e}")
            return 0.0
    
    def _compute_precision_weighted_error(self, levels: List[PredictionLevel]) -> float:
        """Compute precision-weighted prediction error across levels."""
        weighted_errors = []
        
        for level in levels:
            # Weight prediction error by precision (attention)
            error_magnitude = torch.mean(torch.abs(level.prediction_error))
            precision_weight = level.precision.item() if level.precision.numel() == 1 else torch.mean(level.precision).item()
            
            weighted_error = error_magnitude * precision_weight
            weighted_errors.append(weighted_error.item())
        
        return np.mean(weighted_errors) if weighted_errors else 0.0
    
    def _compute_temporal_coherence(self, 
                                  previous_states: torch.Tensor,
                                  current_state: torch.Tensor) -> float:
        """Compute temporal coherence of predictions."""
        if previous_states.shape[1] < 2:
            return 0.0
        
        try:
            # Use LSTM to predict current state from previous states
            prev_sequence = previous_states  # [batch, time, neurons]
            
            # LSTM prediction
            lstm_output, _ = self.temporal_predictor(prev_sequence)
            temporal_prediction = self.temporal_prediction_head(lstm_output[:, -1, :])  # Last timestep
            
            # Compare with actual current state
            prediction_error = torch.mean(torch.abs(
                temporal_prediction - current_state
            ), dim=1)  # [batch]
            
            # Temporal coherence (lower error = higher coherence)
            temporal_coherence = torch.exp(-prediction_error.mean()).item()
            
            return temporal_coherence
            
        except Exception as e:
            self.logger.warning(f"Temporal coherence computation failed: {e}")
            return 0.0
    
    def _compute_consciousness_metrics(self, 
                                     hierarchy: PredictiveHierarchy,
                                     current_state: torch.Tensor,
                                     behavioral_data: Optional[Dict[str, Any]] = None) -> ConsciousPredictionMetrics:
        """
        Compute consciousness metrics from predictive hierarchy.
        
        Args:
            hierarchy: Predictive processing hierarchy
            current_state: Current neural state
            behavioral_data: Optional behavioral context
            
        Returns:
            Comprehensive consciousness metrics
        """
        # 1. Predictive Accuracy (inverse of prediction error)
        predictive_accuracy = 1.0 / (1.0 + hierarchy.total_prediction_error)
        
        # 2. Hierarchical Integration
        hierarchical_integration = hierarchy.hierarchical_consistency
        
        # 3. Active Inference Strength
        active_inference_strength = hierarchy.active_inference_score
        
        # 4. Precision Modulation Efficacy
        precision_modulation = self._compute_precision_modulation_efficacy(hierarchy)
        
        # 5. Temporal Prediction Depth
        temporal_depth = hierarchy.temporal_coherence
        
        # 6. Surprise Minimization
        surprise_minimization = self._compute_surprise_minimization(
            hierarchy, current_state
        )
        
        return ConsciousPredictionMetrics(
            predictive_accuracy=predictive_accuracy,
            hierarchical_integration=hierarchical_integration,
            active_inference_strength=active_inference_strength,
            precision_modulation_efficacy=precision_modulation,
            temporal_prediction_depth=temporal_depth,
            surprise_minimization=surprise_minimization
        )
    
    def _compute_precision_modulation_efficacy(self, hierarchy: PredictiveHierarchy) -> float:
        """Compute how effectively precision weights modulate attention."""
        precision_values = [level.precision.item() if level.precision.numel() == 1 
                           else torch.mean(level.precision).item() for level in hierarchy.levels]
        
        if len(precision_values) < 2:
            return 0.0
        
        # Efficacy based on precision variance and error correlation
        precision_variance = np.var(precision_values)
        
        # Higher precision should correlate with lower prediction errors
        errors = [torch.mean(torch.abs(level.prediction_error)).item() for level in hierarchy.levels]
        
        try:
            correlation = np.corrcoef(precision_values, errors)[0, 1]
            # Negative correlation is good (high precision -> low error)
            correlation_score = max(0.0, -correlation)
        except:
            correlation_score = 0.0
        
        # Combined efficacy
        efficacy = 0.6 * min(precision_variance * 2.0, 1.0) + 0.4 * correlation_score
        
        return efficacy
    
    def _compute_surprise_minimization(self, 
                                     hierarchy: PredictiveHierarchy,
                                     current_state: torch.Tensor) -> float:
        """Compute surprise minimization capability."""
        try:
            # Estimate surprise for current state
            surprise = self.surprise_estimator(current_state.mean(dim=0, keepdim=True))
            surprise_value = surprise.item()
            
            # Lower surprise indicates better predictive processing
            surprise_minimization = 1.0 / (1.0 + surprise_value)
            
            return surprise_minimization
            
        except Exception as e:
            self.logger.warning(f"Surprise minimization computation failed: {e}")
            return 0.0
    
    def _compute_temporal_consistency(self, 
                                    metrics_sequence: List[ConsciousPredictionMetrics]) -> float:
        """Compute temporal consistency of predictive processing."""
        if len(metrics_sequence) < 2:
            return 1.0
        
        # Extract time series of key metrics
        accuracy_series = [m.predictive_accuracy for m in metrics_sequence]
        integration_series = [m.hierarchical_integration for m in metrics_sequence]
        
        # Compute consistency as inverse of variance
        accuracy_consistency = 1.0 / (1.0 + np.var(accuracy_series))
        integration_consistency = 1.0 / (1.0 + np.var(integration_series))
        
        # Overall temporal consistency
        temporal_consistency = 0.6 * accuracy_consistency + 0.4 * integration_consistency
        
        return temporal_consistency
    
    def analyze_prediction_dynamics(self, 
                                  activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze predictive processing dynamics over time.
        
        Args:
            activations_sequence: Sequence of neural activations
            
        Returns:
            Dictionary with prediction dynamics analysis
        """
        prediction_errors = []
        hierarchical_consistencies = []
        active_inference_scores = []
        
        for activations in activations_sequence:
            error = self.compute_prediction_metrics(activations)
            prediction_errors.append(error)
            
            # Extract additional metrics from prediction history
            if self.prediction_history:
                latest_hierarchy = self.prediction_history[-1]
                hierarchical_consistencies.append(latest_hierarchy.hierarchical_consistency)
                active_inference_scores.append(latest_hierarchy.active_inference_score)
        
        error_array = np.array(prediction_errors)
        
        dynamics = {
            'mean_prediction_error': float(np.mean(error_array)),
            'prediction_stability': float(1.0 / (1.0 + np.std(error_array))),
            'error_trend': float(np.polyfit(range(len(prediction_errors)), prediction_errors, 1)[0]) if len(prediction_errors) > 1 else 0.0,
            'predictive_consciousness_score': float(1.0 - np.mean(error_array))  # Higher = more conscious
        }
        
        if hierarchical_consistencies:
            dynamics['mean_hierarchical_consistency'] = float(np.mean(hierarchical_consistencies))
            dynamics['consistency_stability'] = float(1.0 - np.std(hierarchical_consistencies))
        
        if active_inference_scores:
            dynamics['mean_active_inference'] = float(np.mean(active_inference_scores))
            dynamics['active_inference_progression'] = float(np.mean(np.diff(active_inference_scores))) if len(active_inference_scores) > 1 else 0.0
        
        return dynamics
    
    def measure_predictive_depth(self, 
                               neural_activations: torch.Tensor,
                               prediction_horizons: List[int] = [1, 2, 3, 5]) -> Dict[str, float]:
        """
        Measure predictive depth across different time horizons.
        
        Args:
            neural_activations: Neural activations
            prediction_horizons: List of timesteps to predict ahead
            
        Returns:
            Predictive depth measurements
        """
        depth_metrics = {}
        
        try:
            activations = neural_activations.to(self.device)
            if activations.dim() == 2:
                activations = activations.unsqueeze(0)
            
            seq_len = activations.shape[1]
            
            for horizon in prediction_horizons:
                if seq_len > horizon + self.temporal_depth:
                    horizon_errors = []
                    
                    for t in range(self.temporal_depth, seq_len - horizon):
                        # Use past states to predict future state
                        past_states = activations[:, t-self.temporal_depth:t, :]
                        target_state = activations[:, t+horizon, :]
                        
                        # LSTM prediction
                        lstm_output, _ = self.temporal_predictor(past_states)
                        prediction = self.temporal_prediction_head(lstm_output[:, -1, :])
                        
                        # Prediction error
                        error = torch.mean(torch.abs(prediction - target_state)).item()
                        horizon_errors.append(error)
                    
                    if horizon_errors:
                        depth_metrics[f'prediction_error_{horizon}_steps'] = np.mean(horizon_errors)
                        depth_metrics[f'prediction_accuracy_{horizon}_steps'] = 1.0 / (1.0 + np.mean(horizon_errors))
                    else:
                        depth_metrics[f'prediction_error_{horizon}_steps'] = 1.0
                        depth_metrics[f'prediction_accuracy_{horizon}_steps'] = 0.0
                else:
                    depth_metrics[f'prediction_error_{horizon}_steps'] = 1.0
                    depth_metrics[f'prediction_accuracy_{horizon}_steps'] = 0.0
            
            # Compute overall predictive depth
            accuracy_scores = [v for k, v in depth_metrics.items() if 'accuracy' in k]
            if accuracy_scores:
                depth_metrics['overall_predictive_depth'] = np.mean(accuracy_scores)
                depth_metrics['depth_consistency'] = 1.0 - np.std(accuracy_scores)
            else:
                depth_metrics['overall_predictive_depth'] = 0.0
                depth_metrics['depth_consistency'] = 0.0
            
        except Exception as e:
            self.logger.error(f"Predictive depth measurement failed: {e}")
            for horizon in prediction_horizons:
                depth_metrics[f'prediction_error_{horizon}_steps'] = 1.0
                depth_metrics[f'prediction_accuracy_{horizon}_steps'] = 0.0
            depth_metrics['overall_predictive_depth'] = 0.0
            depth_metrics['depth_consistency'] = 0.0
        
        return depth_metrics
    
    def assess_free_energy_minimization(self, 
                                      neural_activations: torch.Tensor) -> Dict[str, float]:
        """
        Assess free energy minimization according to Friston's framework.
        
        Args:
            neural_activations: Neural activations
            
        Returns:
            Free energy minimization assessment
        """
        free_energy_metrics = {}
        
        try:
            activations = neural_activations.to(self.device)
            if activations.dim() == 2:
                activations = activations.unsqueeze(0)
            
            seq_len = activations.shape[1]
            free_energies = []
            
            for t in range(1, seq_len):
                current_state = activations[:, t, :]
                previous_state = activations[:, t-1, :]
                
                # Compute surprise (negative log likelihood)
                surprise = self.surprise_estimator(current_state.mean(dim=0, keepdim=True))
                
                # Compute complexity (KL divergence approximation)
                state_change = torch.abs(current_state - previous_state)
                complexity = torch.mean(state_change, dim=1).mean().item()
                
                # Free energy approximation: Surprise + Complexity
                free_energy = surprise.item() + complexity
                free_energies.append(free_energy)
            
            if free_energies:
                free_energy_metrics['mean_free_energy'] = float(np.mean(free_energies))
                free_energy_metrics['free_energy_trend'] = float(np.polyfit(range(len(free_energies)), free_energies, 1)[0]) if len(free_energies) > 1 else 0.0
                free_energy_metrics['free_energy_minimization'] = float(1.0 / (1.0 + np.mean(free_energies)))
                free_energy_metrics['free_energy_stability'] = float(1.0 / (1.0 + np.std(free_energies)))
            else:
                free_energy_metrics = {
                    'mean_free_energy': 1.0,
                    'free_energy_trend': 0.0,
                    'free_energy_minimization': 0.0,
                    'free_energy_stability': 0.0
                }
            
        except Exception as e:
            self.logger.error(f"Free energy minimization assessment failed: {e}")
            free_energy_metrics = {
                'mean_free_energy': 1.0,
                'free_energy_trend': 0.0,
                'free_energy_minimization': 0.0,
                'free_energy_stability': 0.0
            }
        
        return free_energy_metrics