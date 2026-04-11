"""
Agency and Intentionality Detector
=================================

Implementation of agency detection for consciousness measurement.
Evaluates the system's sense of agency and intentional action capabilities.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Optional
import logging

class AgencyDetector:
    """Agency and intentionality detection for consciousness assessment."""
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Initialize agency detection networks
        self.intention_detector = nn.Sequential(
            nn.Linear(512, 256), nn.ReLU(),
            nn.Linear(256, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1), nn.Sigmoid()
        ).to(self.device)
        
        self.causality_estimator = nn.Sequential(
            nn.Linear(512, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1), nn.Sigmoid()
        ).to(self.device)
        
    def detect_intentionality(self, 
                            neural_activations: torch.Tensor,
                            behavioral_data: Optional[Dict[str, Any]] = None) -> float:
        """Detect intentionality and agency strength."""
        try:
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
            
            activations = neural_activations.to(self.device)
            
            # Adapt network size
            input_size = activations.shape[-1]
            if hasattr(self.intention_detector[0], 'in_features'):
                if self.intention_detector[0].in_features != input_size:
                    self.intention_detector[0] = nn.Linear(input_size, 256).to(self.device)
                    self.causality_estimator[0] = nn.Linear(input_size, 128).to(self.device)
            
            # Compute agency metrics
            intention_scores = []
            causality_scores = []
            
            for t in range(activations.shape[1]):
                timestep_act = activations[:, t, :].mean(dim=0, keepdim=True)
                
                intention = self.intention_detector(timestep_act).item()
                causality = self.causality_estimator(timestep_act).item()
                
                intention_scores.append(intention)
                causality_scores.append(causality)
            
            # Overall agency strength
            agency_strength = 0.7 * np.mean(intention_scores) + 0.3 * np.mean(causality_scores)
            
            return float(agency_strength)
            
        except Exception as e:
            self.logger.error(f"Agency detection failed: {e}")
            return 0.0