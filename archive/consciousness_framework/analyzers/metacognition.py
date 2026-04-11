"""
Metacognition Assessment Tools
=============================

Implementation of metacognitive assessment for consciousness measurement.
Evaluates the system's ability to monitor and control its own cognitive processes.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Optional
import logging

class MetacognitionAssessor:
    """Metacognitive assessment tools for consciousness evaluation."""
    
    def __init__(self, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.logger = logging.getLogger(__name__)
        
        # Initialize metacognitive assessment networks
        self.confidence_estimator = nn.Sequential(
            nn.Linear(512, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(), 
            nn.Linear(64, 1), nn.Sigmoid()
        ).to(self.device)
        
        self.monitoring_network = nn.Sequential(
            nn.Linear(512, 256), nn.ReLU(),
            nn.Linear(256, 128), nn.ReLU(),
            nn.Linear(128, 1), nn.Sigmoid()
        ).to(self.device)
        
    def assess_metacognition(self, 
                           neural_activations: torch.Tensor,
                           behavioral_data: Optional[Dict[str, Any]] = None) -> float:
        """Assess metacognitive capabilities."""
        try:
            if neural_activations.dim() == 2:
                neural_activations = neural_activations.unsqueeze(0)
            
            activations = neural_activations.to(self.device)
            
            # Adapt network size
            input_size = activations.shape[-1]
            if hasattr(self.confidence_estimator[0], 'in_features'):
                if self.confidence_estimator[0].in_features != input_size:
                    self.confidence_estimator[0] = nn.Linear(input_size, 128).to(self.device)
                    self.monitoring_network[0] = nn.Linear(input_size, 256).to(self.device)
            
            # Compute metacognitive metrics
            confidence_scores = []
            monitoring_scores = []
            
            for t in range(activations.shape[1]):
                timestep_act = activations[:, t, :].mean(dim=0, keepdim=True)
                
                confidence = self.confidence_estimator(timestep_act).item()
                monitoring = self.monitoring_network(timestep_act).item()
                
                confidence_scores.append(confidence)
                monitoring_scores.append(monitoring)
            
            # Overall metacognitive accuracy
            metacognitive_accuracy = 0.6 * np.mean(confidence_scores) + 0.4 * np.mean(monitoring_scores)
            
            return float(metacognitive_accuracy)
            
        except Exception as e:
            self.logger.error(f"Metacognition assessment failed: {e}")
            return 0.0