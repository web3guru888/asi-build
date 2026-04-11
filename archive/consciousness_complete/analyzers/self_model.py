"""
Self-Model Sophistication Analyzer
=================================

Implementation of self-model analysis for measuring consciousness through
self-representation sophistication and self-awareness capabilities.

Key concepts:
- Self-Model: Internal representation of the system's own state and capabilities
- Self-Awareness: Knowledge and monitoring of one's own mental processes
- Self-Reflection: Ability to think about one's own thoughts and experiences
- Identity Coherence: Consistency of self-representation across time
- Agency Attribution: Recognition of one's own causal agency

Based on theories of self-consciousness and metacognitive self-models.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from dataclasses import dataclass
from collections import deque
import networkx as nx

@dataclass
class SelfModelComponent:
    """Component of the self-model representation."""
    content: torch.Tensor
    confidence: float
    temporal_stability: float
    self_reference_strength: float
    component_type: str  # 'cognitive', 'emotional', 'physical', 'social', 'temporal'

@dataclass
class SelfModelProfile:
    """Complete self-model representation profile."""
    components: List[SelfModelComponent]
    overall_sophistication: float
    identity_coherence: float
    self_awareness_depth: float
    agency_attribution: float
    temporal_consistency: float

class SelfModelAnalyzer:
    """
    Self-Model Sophistication Analyzer for consciousness assessment.
    
    Analyzes the sophistication and coherence of self-representational
    capabilities as indicators of consciousness.
    """
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize Self-Model Analyzer.
        
        Args:
            device: Computing device for tensor operations
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Self-model parameters
        self.model_dimensions = 128
        self.component_types = ['cognitive', 'emotional', 'physical', 'social', 'temporal']
        self.history_length = 20
        
        # Initialize self-model networks
        self._initialize_self_model_networks()
        
        # Self-model history
        self.self_model_history: deque = deque(maxlen=self.history_length)
        
    def _initialize_self_model_networks(self):
        """Initialize self-model analysis networks."""
        # Self-model encoder
        self.self_model_encoder = nn.Sequential(
            nn.Linear(512, 256),  # Adapted dynamically
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, self.model_dimensions),
            nn.Tanh()
        ).to(self.device)
        
        # Component analyzers for different aspects of self
        self.component_analyzers = nn.ModuleDict()
        for comp_type in self.component_types:
            self.component_analyzers[comp_type] = nn.Sequential(
                nn.Linear(self.model_dimensions, 64),
                nn.ReLU(),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, self.model_dimensions),
                nn.Tanh()
            )
        
        # Self-reference detector
        self.self_reference_detector = nn.Sequential(
            nn.Linear(self.model_dimensions, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        ).to(self.device)
        
        # Identity coherence analyzer
        self.identity_coherence_analyzer = nn.Sequential(
            nn.Linear(self.model_dimensions * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        ).to(self.device)
        
        # Agency attribution network
        self.agency_attributor = nn.Sequential(
            nn.Linear(self.model_dimensions, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        ).to(self.device)
        
        self.logger.info("Self-Model Analyzer networks initialized")
    
    def analyze_self_representation(self, 
                                  neural_activations: torch.Tensor,
                                  behavioral_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Analyze self-model sophistication from neural activations.
        
        Args:
            neural_activations: Neural network activations [batch, time, neurons]
            behavioral_data: Optional behavioral context data
            
        Returns:
            Self-model sophistication score (0-1)
        """
        self.logger.info("Analyzing self-model sophistication")
        
        try:
            # Ensure proper tensor format
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
                
            activations = neural_activations.to(self.device)
            
            # Adapt network input size if needed
            input_size = activations.shape[-1]
            self._adapt_network_sizes(input_size)
            
            # Build self-model profile
            self_model_profile = self._build_self_model_profile(activations, behavioral_data)
            
            # Store in history
            self.self_model_history.append(self_model_profile)
            
            # Return overall sophistication
            sophistication = self_model_profile.overall_sophistication
            
            self.logger.info(f"Self-model sophistication: {sophistication:.3f}")
            return sophistication
            
        except Exception as e:
            self.logger.error(f"Self-model analysis failed: {e}")
            return 0.0
    
    def _adapt_network_sizes(self, input_size: int):
        """Adapt network input sizes to match neural activations."""
        if hasattr(self.self_model_encoder[0], 'in_features'):
            if self.self_model_encoder[0].in_features != input_size:
                self.self_model_encoder[0] = nn.Linear(input_size, 256).to(self.device)
                nn.init.xavier_uniform_(self.self_model_encoder[0].weight)
    
    def _build_self_model_profile(self, 
                                activations: torch.Tensor,
                                behavioral_data: Optional[Dict[str, Any]] = None) -> SelfModelProfile:
        """Build comprehensive self-model profile."""
        batch_size, seq_len, num_neurons = activations.shape
        
        # Extract self-model components over time
        all_components = []
        
        for t in range(seq_len):
            timestep_activations = activations[:, t, :].mean(dim=0, keepdim=True)  # [1, neurons]
            
            # Encode to self-model space
            self_model_representation = self.self_model_encoder(timestep_activations).squeeze(0)
            
            # Analyze different components of self-model
            components = self._extract_self_model_components(self_model_representation)
            all_components.extend(components)
        
        # Compute overall metrics
        overall_sophistication = self._compute_overall_sophistication(all_components)
        identity_coherence = self._compute_identity_coherence(all_components)
        self_awareness_depth = self._compute_self_awareness_depth(all_components)
        agency_attribution = self._compute_agency_attribution(all_components)
        temporal_consistency = self._compute_temporal_consistency(all_components)
        
        return SelfModelProfile(
            components=all_components,
            overall_sophistication=overall_sophistication,
            identity_coherence=identity_coherence,
            self_awareness_depth=self_awareness_depth,
            agency_attribution=agency_attribution,
            temporal_consistency=temporal_consistency
        )
    
    def _extract_self_model_components(self, 
                                     self_model_repr: torch.Tensor) -> List[SelfModelComponent]:
        """Extract different components of self-model."""
        components = []
        
        for comp_type in self.component_types:
            # Extract component-specific representation
            component_content = self.component_analyzers[comp_type](
                self_model_repr.unsqueeze(0)
            ).squeeze(0)
            
            # Compute component metrics
            confidence = torch.sigmoid(torch.mean(torch.abs(component_content))).item()
            temporal_stability = self._estimate_temporal_stability(component_content, comp_type)
            self_reference_strength = self.self_reference_detector(
                component_content.unsqueeze(0)
            ).item()
            
            component = SelfModelComponent(
                content=component_content,
                confidence=confidence,
                temporal_stability=temporal_stability,
                self_reference_strength=self_reference_strength,
                component_type=comp_type
            )
            components.append(component)
        
        return components
    
    def _estimate_temporal_stability(self, component_content: torch.Tensor, comp_type: str) -> float:
        """Estimate temporal stability of component across history."""
        if len(self.self_model_history) < 2:
            return 0.5  # Default stability
        
        # Compare with recent history
        recent_components = []
        for profile in self.self_model_history[-5:]:  # Last 5 profiles
            matching_components = [c for c in profile.components if c.component_type == comp_type]
            if matching_components:
                recent_components.append(matching_components[0].content)
        
        if len(recent_components) < 2:
            return 0.5
        
        # Compute stability as consistency across time
        similarities = []
        for recent_content in recent_components:
            similarity = F.cosine_similarity(
                component_content.unsqueeze(0),
                recent_content.unsqueeze(0),
                dim=1
            ).item()
            similarities.append(max(0.0, (similarity + 1.0) / 2.0))
        
        return np.mean(similarities)
    
    def _compute_overall_sophistication(self, components: List[SelfModelComponent]) -> float:
        """Compute overall self-model sophistication."""
        if not components:
            return 0.0
        
        sophistication_factors = []
        
        # 1. Component diversity and strength
        component_strengths = {}
        for component in components:
            comp_type = component.component_type
            if comp_type not in component_strengths:
                component_strengths[comp_type] = []
            component_strengths[comp_type].append(component.confidence)
        
        diversity_score = len(component_strengths) / len(self.component_types)
        strength_score = np.mean([np.mean(strengths) for strengths in component_strengths.values()])
        sophistication_factors.extend([diversity_score, strength_score])
        
        # 2. Self-reference sophistication
        self_ref_scores = [c.self_reference_strength for c in components]
        self_ref_sophistication = np.mean(self_ref_scores)
        sophistication_factors.append(self_ref_sophistication)
        
        # 3. Temporal stability sophistication
        stability_scores = [c.temporal_stability for c in components]
        stability_sophistication = np.mean(stability_scores)
        sophistication_factors.append(stability_sophistication)
        
        # Weighted combination
        weights = [0.3, 0.25, 0.25, 0.2]
        overall_sophistication = sum(w * f for w, f in zip(weights, sophistication_factors))
        
        return overall_sophistication
    
    def _compute_identity_coherence(self, components: List[SelfModelComponent]) -> float:
        """Compute coherence of identity across components."""
        if len(components) < 2:
            return 0.0
        
        # Compute pairwise coherence between components
        coherence_scores = []
        
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                comp_i = components[i]
                comp_j = components[j]
                
                # Use identity coherence analyzer
                combined_input = torch.cat([comp_i.content, comp_j.content], dim=0)
                coherence = self.identity_coherence_analyzer(
                    combined_input.unsqueeze(0)
                ).item()
                
                coherence_scores.append(coherence)
        
        return np.mean(coherence_scores) if coherence_scores else 0.0
    
    def _compute_self_awareness_depth(self, components: List[SelfModelComponent]) -> float:
        """Compute depth of self-awareness."""
        if not components:
            return 0.0
        
        # Self-awareness depth based on:
        # 1. Self-reference strength across components
        self_ref_depth = np.mean([c.self_reference_strength for c in components])
        
        # 2. Component sophistication variance (depth of differentiation)
        confidences = [c.confidence for c in components]
        differentiation_depth = np.std(confidences)  # Higher variance = more differentiated
        
        # 3. Temporal stability (stable self-awareness over time)
        temporal_depth = np.mean([c.temporal_stability for c in components])
        
        # Combined depth measure
        depth_score = (
            0.5 * self_ref_depth + 
            0.3 * min(differentiation_depth, 1.0) + 
            0.2 * temporal_depth
        )
        
        return depth_score
    
    def _compute_agency_attribution(self, components: List[SelfModelComponent]) -> float:
        """Compute strength of agency attribution."""
        if not components:
            return 0.0
        
        # Use agency attributor on each component
        agency_scores = []
        
        for component in components:
            agency_score = self.agency_attributor(
                component.content.unsqueeze(0)
            ).item()
            
            # Weight by component confidence
            weighted_agency = agency_score * component.confidence
            agency_scores.append(weighted_agency)
        
        return np.mean(agency_scores)
    
    def _compute_temporal_consistency(self, components: List[SelfModelComponent]) -> float:
        """Compute temporal consistency of self-model."""
        if not components:
            return 0.0
        
        # Average temporal stability across all components
        stability_scores = [c.temporal_stability for c in components]
        return np.mean(stability_scores)
    
    def analyze_self_model_evolution(self, 
                                   activations_sequence: List[torch.Tensor]) -> Dict[str, float]:
        """
        Analyze evolution of self-model over time.
        
        Args:
            activations_sequence: Sequence of neural activations
            
        Returns:
            Dictionary with self-model evolution analysis
        """
        sophistication_scores = []
        identity_coherence_scores = []
        agency_scores = []
        
        for activations in activations_sequence:
            sophistication = self.analyze_self_representation(activations)
            sophistication_scores.append(sophistication)
            
            # Extract additional metrics from history
            if self.self_model_history:
                latest_profile = self.self_model_history[-1]
                identity_coherence_scores.append(latest_profile.identity_coherence)
                agency_scores.append(latest_profile.agency_attribution)
        
        sophistication_array = np.array(sophistication_scores)
        
        evolution = {
            'mean_self_model_sophistication': float(np.mean(sophistication_array)),
            'sophistication_trend': float(np.polyfit(range(len(sophistication_scores)), sophistication_scores, 1)[0]) if len(sophistication_scores) > 1 else 0.0,
            'sophistication_stability': float(1.0 / (1.0 + np.std(sophistication_array)))
        }
        
        if identity_coherence_scores:
            evolution['mean_identity_coherence'] = float(np.mean(identity_coherence_scores))
            evolution['identity_consistency'] = float(1.0 - np.std(identity_coherence_scores))
        
        if agency_scores:
            evolution['mean_agency_attribution'] = float(np.mean(agency_scores))
            evolution['agency_development'] = float(np.polyfit(range(len(agency_scores)), agency_scores, 1)[0]) if len(agency_scores) > 1 else 0.0
        
        return evolution