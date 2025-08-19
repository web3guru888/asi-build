"""
Global Workspace Theory (GWT) Implementation
===========================================

Implementation of Bernard Baars' Global Workspace Theory for measuring
consciousness through global information integration and coherence.

Key concepts:
- Global Workspace: A limited-capacity system that broadcasts information globally
- Attention: Selection mechanism for entering the global workspace
- Competition: Multiple processes compete for global access
- Broadcasting: Selected information is made available system-wide
- Coherence: Integration of distributed information into unified conscious experience

Mathematical foundation based on GWT computational models.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import logging
from dataclasses import dataclass
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist
import networkx as nx

@dataclass
class WorkspaceState:
    """State of the global workspace at a given time."""
    active_coalitions: List[torch.Tensor]
    winning_coalition: torch.Tensor
    broadcast_signal: torch.Tensor
    coherence_score: float
    competition_intensity: float
    global_availability: float
    
@dataclass
class AttentionCoalition:
    """A coalition of neural elements competing for global access."""
    elements: torch.Tensor
    strength: float
    coherence: float
    context_relevance: float
    novelty_score: float

class GWTImplementation:
    """
    Global Workspace Theory implementation for consciousness assessment.
    
    Measures consciousness through global information integration,
    attention competition, and broadcasting mechanisms.
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize GWT implementation.
        
        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # GWT parameters
        self.workspace_capacity = 128  # Global workspace capacity
        self.coalition_threshold = 0.3  # Minimum strength for coalition formation
        self.broadcast_threshold = 0.5  # Threshold for global broadcasting
        self.decay_rate = 0.1  # Information decay rate
        self.competition_strength = 2.0  # Competition intensity factor
        
        # Initialize workspace components
        self._initialize_workspace()
        
    def _initialize_workspace(self):
        """Initialize global workspace neural components."""
        # Global workspace buffer
        self.workspace_buffer = torch.zeros(self.workspace_capacity, device=self.device)
        
        # Attention network for coalition selection
        self.attention_network = nn.Sequential(
            nn.Linear(512, 256),  # Input size will be adapted dynamically
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.Sigmoid()
        ).to(self.device)
        
        # Broadcasting network
        self.broadcast_network = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, 512),
            nn.Tanh()
        ).to(self.device)
        
        self.logger.info("Global Workspace Theory components initialized")
    
    def assess_global_coherence(self, 
                               neural_activations: torch.Tensor,
                               attention_maps: Optional[torch.Tensor] = None) -> float:
        """
        Assess global workspace coherence from neural activations.
        
        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            attention_maps: Optional attention mechanism outputs
            
        Returns:
            Global coherence score (0-1)
        """
        self.logger.info("Assessing global workspace coherence")
        
        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
                
            activations = neural_activations.to(self.device)
            
            # Adapt network input size if needed
            input_size = activations.shape[-1]
            if hasattr(self.attention_network[0], 'in_features'):
                if self.attention_network[0].in_features != input_size:
                    self._adapt_network_size(input_size)
            
            # Process through global workspace
            workspace_states = []
            coherence_scores = []
            
            for t in range(activations.shape[1]):
                timestep_activations = activations[:, t, :]  # [batch, neurons]
                
                # Form competing coalitions
                coalitions = self._form_coalitions(timestep_activations, attention_maps)
                
                # Competition for global access
                workspace_state = self._global_competition(coalitions, timestep_activations)
                workspace_states.append(workspace_state)
                
                # Measure coherence
                coherence = self._measure_coherence(workspace_state, timestep_activations)
                coherence_scores.append(coherence)
            
            # Overall coherence assessment
            overall_coherence = np.mean(coherence_scores) if coherence_scores else 0.0
            
            # Additional coherence metrics
            temporal_coherence = self._compute_temporal_coherence(workspace_states)
            spatial_coherence = self._compute_spatial_coherence(activations)
            
            # Weighted combination
            final_coherence = (
                0.5 * overall_coherence +
                0.3 * temporal_coherence +
                0.2 * spatial_coherence
            )
            
            self.logger.info(f"Global coherence score: {final_coherence:.3f}")
            return float(final_coherence)
            
        except Exception as e:
            self.logger.error(f"Global coherence assessment failed: {e}")
            return 0.0
    
    def _adapt_network_size(self, input_size: int):
        """Adapt attention network to match input size."""
        self.attention_network[0] = nn.Linear(input_size, 256).to(self.device)
        
        # Reinitialize weights
        nn.init.xavier_uniform_(self.attention_network[0].weight)
        nn.init.zeros_(self.attention_network[0].bias)
    
    def _form_coalitions(self, 
                        activations: torch.Tensor,
                        attention_maps: Optional[torch.Tensor] = None) -> List[AttentionCoalition]:
        """
        Form competing coalitions from neural activations.
        
        Args:
            activations: Neural activations [batch, neurons]
            attention_maps: Optional attention maps
            
        Returns:
            List of competing coalitions
        """
        batch_size, num_neurons = activations.shape
        coalitions = []
        
        # Use clustering to identify natural coalitions
        for b in range(batch_size):
            batch_activations = activations[b]  # [neurons]
            
            # Find highly active regions
            activity_threshold = torch.quantile(torch.abs(batch_activations), 0.7)
            active_neurons = batch_activations > activity_threshold
            
            if torch.sum(active_neurons) < 2:
                continue
                
            # Cluster active neurons
            active_indices = torch.where(active_neurons)[0]
            active_values = batch_activations[active_indices]
            
            # Simple clustering based on activation similarity
            if len(active_indices) > 2:
                try:
                    # Convert to numpy for clustering
                    values_np = active_values.detach().cpu().numpy().reshape(-1, 1)
                    distances = pdist(values_np)
                    
                    if len(distances) > 0:
                        linkage_matrix = linkage(distances, method='ward')
                        cluster_labels = fcluster(linkage_matrix, t=0.7, criterion='distance')
                        
                        # Form coalitions from clusters
                        unique_labels = np.unique(cluster_labels)
                        for label in unique_labels:
                            cluster_mask = cluster_labels == label
                            coalition_indices = active_indices[cluster_mask]
                            
                            if len(coalition_indices) >= 2:
                                coalition_elements = batch_activations[coalition_indices]
                                strength = torch.mean(torch.abs(coalition_elements)).item()
                                
                                if strength > self.coalition_threshold:
                                    coherence = self._compute_coalition_coherence(coalition_elements)
                                    context_relevance = self._compute_context_relevance(
                                        coalition_elements, batch_activations
                                    )
                                    novelty = self._compute_novelty_score(coalition_elements)
                                    
                                    coalition = AttentionCoalition(
                                        elements=coalition_elements,
                                        strength=strength,
                                        coherence=coherence,
                                        context_relevance=context_relevance,
                                        novelty_score=novelty
                                    )
                                    coalitions.append(coalition)
                                    
                except Exception as e:
                    self.logger.warning(f"Coalition formation clustering failed: {e}")
                    # Fallback: single coalition from all active neurons
                    coalition_elements = batch_activations[active_indices]
                    strength = torch.mean(torch.abs(coalition_elements)).item()
                    
                    if strength > self.coalition_threshold:
                        coalition = AttentionCoalition(
                            elements=coalition_elements,
                            strength=strength,
                            coherence=0.5,  # Default coherence
                            context_relevance=0.5,
                            novelty_score=0.5
                        )
                        coalitions.append(coalition)
        
        return coalitions
    
    def _compute_coalition_coherence(self, elements: torch.Tensor) -> float:
        """Compute internal coherence of a coalition."""
        if len(elements) < 2:
            return 1.0
        
        # Compute pairwise correlations
        correlations = []
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                corr = torch.corrcoef(torch.stack([elements[i:i+1], elements[j:j+1]]))[0, 1]
                if not torch.isnan(corr):
                    correlations.append(corr.abs())
        
        if correlations:
            return torch.mean(torch.stack(correlations)).item()
        else:
            return 0.5  # Default coherence
    
    def _compute_context_relevance(self, coalition: torch.Tensor, 
                                 global_context: torch.Tensor) -> float:
        """Compute how relevant coalition is to global context."""
        coalition_mean = torch.mean(coalition)
        context_mean = torch.mean(global_context)
        
        # Relevance based on deviation from global average
        relevance = 1.0 - torch.abs(coalition_mean - context_mean) / (torch.abs(context_mean) + 1e-6)
        return torch.clamp(relevance, 0.0, 1.0).item()
    
    def _compute_novelty_score(self, elements: torch.Tensor) -> float:
        """Compute novelty score of coalition elements."""
        # Novelty based on variance and uniqueness
        variance = torch.var(elements)
        uniqueness = len(torch.unique(elements)) / len(elements)
        
        novelty = 0.7 * torch.sqrt(variance) + 0.3 * uniqueness
        return torch.clamp(novelty, 0.0, 1.0).item()
    
    def _global_competition(self, 
                          coalitions: List[AttentionCoalition],
                          activations: torch.Tensor) -> WorkspaceState:
        """
        Simulate competition for global workspace access.
        
        Args:
            coalitions: Competing coalitions
            activations: Current neural activations
            
        Returns:
            Resulting workspace state
        """
        if not coalitions:
            # No coalitions - create default state
            return WorkspaceState(
                active_coalitions=[],
                winning_coalition=torch.zeros(1, device=self.device),
                broadcast_signal=torch.zeros(self.workspace_capacity, device=self.device),
                coherence_score=0.0,
                competition_intensity=0.0,
                global_availability=0.0
            )
        
        # Compute competition scores
        competition_scores = []
        for coalition in coalitions:
            # Weighted competition score
            score = (
                0.4 * coalition.strength +
                0.2 * coalition.coherence +
                0.2 * coalition.context_relevance +
                0.2 * coalition.novelty_score
            )
            competition_scores.append(score)
        
        competition_scores = torch.tensor(competition_scores, device=self.device)
        
        # Apply competition dynamics (softmax with temperature)
        temperature = 1.0 / self.competition_strength
        competition_probs = F.softmax(competition_scores / temperature, dim=0)
        
        # Select winning coalition
        winner_idx = torch.argmax(competition_probs)
        winning_coalition = coalitions[winner_idx]
        
        # Competition intensity
        competition_intensity = torch.std(competition_scores).item()
        
        # Generate broadcast signal if winner exceeds threshold
        if winning_coalition.strength > self.broadcast_threshold:
            broadcast_signal = self._generate_broadcast(winning_coalition, activations)
            global_availability = winning_coalition.strength
        else:
            broadcast_signal = torch.zeros(self.workspace_capacity, device=self.device)
            global_availability = 0.0
        
        # Update workspace buffer
        self.workspace_buffer = (
            (1 - self.decay_rate) * self.workspace_buffer +
            self.decay_rate * broadcast_signal[:self.workspace_capacity]
        )
        
        return WorkspaceState(
            active_coalitions=coalitions,
            winning_coalition=winning_coalition.elements,
            broadcast_signal=broadcast_signal,
            coherence_score=winning_coalition.coherence,
            competition_intensity=competition_intensity,
            global_availability=global_availability
        )
    
    def _generate_broadcast(self, 
                          winning_coalition: AttentionCoalition,
                          activations: torch.Tensor) -> torch.Tensor:
        """
        Generate global broadcast signal from winning coalition.
        
        Args:
            winning_coalition: Coalition that won the competition
            activations: Current activations
            
        Returns:
            Broadcast signal tensor
        """
        try:
            # Create coalition representation
            coalition_repr = torch.mean(winning_coalition.elements)
            coalition_input = coalition_repr.repeat(128).unsqueeze(0)
            
            # Generate broadcast through broadcasting network
            broadcast_signal = self.broadcast_network(coalition_input).squeeze(0)
            
            # Amplify based on coalition strength
            amplification = winning_coalition.strength * 2.0
            broadcast_signal = broadcast_signal * amplification
            
            return broadcast_signal
            
        except Exception as e:
            self.logger.warning(f"Broadcast generation failed: {e}")
            return torch.zeros(512, device=self.device)
    
    def _measure_coherence(self, 
                          workspace_state: WorkspaceState,
                          activations: torch.Tensor) -> float:
        """
        Measure coherence of workspace state.
        
        Args:
            workspace_state: Current workspace state
            activations: Neural activations
            
        Returns:
            Coherence measure (0-1)
        """
        coherence_components = []
        
        # 1. Coalition coherence
        coalition_coherence = workspace_state.coherence_score
        coherence_components.append(coalition_coherence)
        
        # 2. Broadcast coherence
        if torch.sum(torch.abs(workspace_state.broadcast_signal)) > 0:
            broadcast_coherence = self._compute_broadcast_coherence(workspace_state.broadcast_signal)
        else:
            broadcast_coherence = 0.0
        coherence_components.append(broadcast_coherence)
        
        # 3. Global integration
        global_integration = workspace_state.global_availability
        coherence_components.append(global_integration)
        
        # 4. Competition clarity
        competition_clarity = min(workspace_state.competition_intensity / 2.0, 1.0)
        coherence_components.append(competition_clarity)
        
        # Weighted average
        weights = [0.3, 0.25, 0.25, 0.2]
        total_coherence = sum(w * c for w, c in zip(weights, coherence_components))
        
        return total_coherence
    
    def _compute_broadcast_coherence(self, broadcast_signal: torch.Tensor) -> float:
        """Compute coherence of broadcast signal."""
        # Coherence based on signal structure and consistency
        signal_variance = torch.var(broadcast_signal)
        signal_mean = torch.abs(torch.mean(broadcast_signal))
        
        # Higher coherence for structured signals (not too random, not too uniform)
        coherence = 1.0 / (1.0 + signal_variance) * signal_mean
        return torch.clamp(coherence, 0.0, 1.0).item()
    
    def _compute_temporal_coherence(self, workspace_states: List[WorkspaceState]) -> float:
        """Compute coherence across time."""
        if len(workspace_states) < 2:
            return 0.0
        
        # Measure consistency of global availability over time
        availabilities = [state.global_availability for state in workspace_states]
        temporal_consistency = 1.0 - np.std(availabilities) if availabilities else 0.0
        
        # Measure broadcast signal correlations across time
        broadcast_correlations = []
        for i in range(len(workspace_states) - 1):
            signal1 = workspace_states[i].broadcast_signal
            signal2 = workspace_states[i + 1].broadcast_signal
            
            if torch.sum(torch.abs(signal1)) > 0 and torch.sum(torch.abs(signal2)) > 0:
                corr = F.cosine_similarity(signal1.unsqueeze(0), signal2.unsqueeze(0), dim=1)
                broadcast_correlations.append(corr.item())
        
        broadcast_consistency = np.mean(broadcast_correlations) if broadcast_correlations else 0.0
        
        # Combine temporal measures
        temporal_coherence = 0.6 * temporal_consistency + 0.4 * broadcast_consistency
        return max(0.0, min(1.0, temporal_coherence))
    
    def _compute_spatial_coherence(self, activations: torch.Tensor) -> float:
        """Compute spatial coherence across neural activations."""
        # Measure global integration across spatial dimensions
        batch_size, seq_len, num_neurons = activations.shape
        
        spatial_correlations = []
        
        for t in range(seq_len):
            timestep_activations = activations[:, t, :].mean(dim=0)  # Average across batch
            
            # Compute spatial correlation structure
            if num_neurons > 1:
                expanded = timestep_activations.unsqueeze(0).expand(num_neurons, -1)
                spatial_corr_matrix = torch.corrcoef(expanded)
                
                # Global coherence as mean absolute correlation
                off_diagonal = spatial_corr_matrix[torch.triu(torch.ones_like(spatial_corr_matrix), diagonal=1) == 1]
                mean_correlation = torch.mean(torch.abs(off_diagonal))
                
                if not torch.isnan(mean_correlation):
                    spatial_correlations.append(mean_correlation.item())
        
        if spatial_correlations:
            return np.mean(spatial_correlations)
        else:
            return 0.0
    
    def analyze_workspace_dynamics(self, 
                                 activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze global workspace dynamics over time.
        
        Args:
            activations_sequence: Sequence of neural activations
            
        Returns:
            Dictionary with workspace dynamics analysis
        """
        coherence_values = []
        availability_values = []
        competition_values = []
        
        for activations in activations_sequence:
            coherence = self.assess_global_coherence(activations)
            coherence_values.append(coherence)
            
            # Extract additional metrics from workspace states
            try:
                if activations.dim() == 2:
                    activations = activations.unsqueeze(0)
                    
                activations = activations.to(self.device)
                coalitions = self._form_coalitions(activations.mean(dim=1), None)
                workspace_state = self._global_competition(coalitions, activations.mean(dim=1))
                
                availability_values.append(workspace_state.global_availability)
                competition_values.append(workspace_state.competition_intensity)
                
            except Exception as e:
                self.logger.warning(f"Workspace dynamics extraction failed: {e}")
                availability_values.append(0.0)
                competition_values.append(0.0)
        
        coherence_array = np.array(coherence_values)
        availability_array = np.array(availability_values)
        competition_array = np.array(competition_values)
        
        return {
            'mean_coherence': float(np.mean(coherence_array)),
            'coherence_stability': float(1.0 / (1.0 + np.std(coherence_array))),
            'mean_availability': float(np.mean(availability_array)),
            'availability_consistency': float(1.0 - np.std(availability_array)),
            'mean_competition': float(np.mean(competition_array)),
            'competition_dynamics': float(np.std(competition_array)),
            'workspace_efficiency': float(np.mean(availability_array) * np.mean(coherence_array))
        }
    
    def measure_conscious_access(self, 
                               neural_activations: torch.Tensor,
                               target_information: Optional[torch.Tensor] = None) -> Dict[str, float]:
        """
        Measure conscious access to specific information.
        
        Args:
            neural_activations: Neural activations
            target_information: Optional target information to track
            
        Returns:
            Conscious access measurements
        """
        access_metrics = {}
        
        try:
            activations = neural_activations.to(self.device)
            if activations.dim() == 2:
                activations = activations.unsqueeze(0)
            
            # Global accessibility
            global_coherence = self.assess_global_coherence(activations)
            access_metrics['global_accessibility'] = global_coherence
            
            # Broadcast strength
            coalitions = self._form_coalitions(activations.mean(dim=1), None)
            workspace_state = self._global_competition(coalitions, activations.mean(dim=1))
            broadcast_strength = torch.mean(torch.abs(workspace_state.broadcast_signal)).item()
            access_metrics['broadcast_strength'] = broadcast_strength
            
            # Information persistence in workspace
            workspace_persistence = torch.mean(torch.abs(self.workspace_buffer)).item()
            access_metrics['workspace_persistence'] = workspace_persistence
            
            # Competition success rate
            competition_success = float(workspace_state.global_availability > self.broadcast_threshold)
            access_metrics['competition_success'] = competition_success
            
            if target_information is not None:
                # Target-specific access
                target_broadcast_similarity = F.cosine_similarity(
                    workspace_state.broadcast_signal.unsqueeze(0),
                    target_information.flatten().unsqueeze(0),
                    dim=1
                ).item()
                access_metrics['target_access'] = max(0.0, target_broadcast_similarity)
            
        except Exception as e:
            self.logger.error(f"Conscious access measurement failed: {e}")
            access_metrics = {
                'global_accessibility': 0.0,
                'broadcast_strength': 0.0,
                'workspace_persistence': 0.0,
                'competition_success': 0.0
            }
        
        return access_metrics