"""
Consciousness Evolution Tracker
==============================

Tracks the evolution of consciousness metrics during training and development.
Provides insights into how consciousness emerges and develops over time.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging

@dataclass
class ConsciousnessSnapshot:
    """Snapshot of consciousness state at a specific time."""
    timestamp: datetime
    phi_score: float
    gwt_coherence: float
    attention_schema_score: float
    hot_complexity: float
    predictive_error: float
    qualia_dimensionality: int
    self_model_sophistication: float
    metacognitive_accuracy: float
    agency_strength: float
    overall_consciousness_score: float
    training_step: Optional[int] = None
    additional_metrics: Optional[Dict[str, float]] = None

class ConsciousnessEvolutionTracker:
    """Tracks evolution of consciousness metrics over time."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.snapshots: List[ConsciousnessSnapshot] = []
        self.evolution_trends: Dict[str, List[float]] = {}
        
    def record_assessment(self, assessment_profile: Any):
        """Record a consciousness assessment."""
        try:
            snapshot = ConsciousnessSnapshot(
                timestamp=assessment_profile.timestamp,
                phi_score=assessment_profile.phi_score,
                gwt_coherence=assessment_profile.gwt_coherence,
                attention_schema_score=assessment_profile.attention_schema_score,
                hot_complexity=assessment_profile.hot_complexity,
                predictive_error=assessment_profile.predictive_error,
                qualia_dimensionality=assessment_profile.qualia_dimensionality,
                self_model_sophistication=assessment_profile.self_model_sophistication,
                metacognitive_accuracy=assessment_profile.metacognitive_accuracy,
                agency_strength=assessment_profile.agency_strength,
                overall_consciousness_score=assessment_profile.overall_consciousness_score
            )
            
            self.snapshots.append(snapshot)
            self._update_trends(snapshot)
            
        except Exception as e:
            self.logger.error(f"Failed to record consciousness assessment: {e}")
    
    def _update_trends(self, snapshot: ConsciousnessSnapshot):
        """Update evolution trends with new snapshot."""
        metrics = [
            'phi_score', 'gwt_coherence', 'attention_schema_score',
            'hot_complexity', 'predictive_error', 'qualia_dimensionality',
            'self_model_sophistication', 'metacognitive_accuracy',
            'agency_strength', 'overall_consciousness_score'
        ]
        
        for metric in metrics:
            if metric not in self.evolution_trends:
                self.evolution_trends[metric] = []
            
            value = getattr(snapshot, metric)
            self.evolution_trends[metric].append(value)
    
    def get_recent_trends(self, window_size: int = 10) -> Dict[str, float]:
        """Get recent trends in consciousness metrics."""
        if len(self.snapshots) < 2:
            return {}
        
        recent_snapshots = self.snapshots[-window_size:]
        trends = {}
        
        for metric in self.evolution_trends:
            if len(self.evolution_trends[metric]) >= 2:
                recent_values = self.evolution_trends[metric][-window_size:]
                if len(recent_values) > 1:
                    trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
                    trends[f'{metric}_trend'] = float(trend)
        
        return trends
    
    def analyze_consciousness_emergence(self) -> Dict[str, Any]:
        """Analyze patterns of consciousness emergence."""
        if len(self.snapshots) < 5:
            return {'insufficient_data': True}
        
        analysis = {}
        
        # Overall consciousness trajectory
        consciousness_scores = [s.overall_consciousness_score for s in self.snapshots]
        analysis['consciousness_trajectory'] = {
            'initial_score': consciousness_scores[0],
            'final_score': consciousness_scores[-1],
            'peak_score': max(consciousness_scores),
            'growth_rate': np.polyfit(range(len(consciousness_scores)), consciousness_scores, 1)[0],
            'stability': 1.0 / (1.0 + np.std(consciousness_scores[-10:]))
        }
        
        # Theory-specific emergence patterns
        theory_metrics = {
            'IIT': 'phi_score',
            'GWT': 'gwt_coherence', 
            'AST': 'attention_schema_score',
            'HOT': 'hot_complexity',
            'PP': 'predictive_error'
        }
        
        for theory, metric in theory_metrics.items():
            values = [getattr(s, metric) for s in self.snapshots]
            analysis[f'{theory}_emergence'] = {
                'initial': values[0],
                'final': values[-1],
                'peak': max(values) if metric != 'predictive_error' else min(values),
                'trend': np.polyfit(range(len(values)), values, 1)[0]
            }
        
        return analysis
    
    def visualize_evolution(self, save_path: Optional[str] = None) -> plt.Figure:
        """Visualize consciousness evolution over time."""
        if len(self.snapshots) < 2:
            self.logger.warning("Insufficient data for visualization")
            return None
        
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('Consciousness Evolution Over Time', fontsize=16)
        
        # Time points
        time_points = range(len(self.snapshots))
        
        # 1. Overall consciousness score
        ax1 = axes[0, 0]
        consciousness_scores = [s.overall_consciousness_score for s in self.snapshots]
        ax1.plot(time_points, consciousness_scores, 'b-', linewidth=2, label='Consciousness Score')
        ax1.set_title('Overall Consciousness Evolution')
        ax1.set_ylabel('Consciousness Score')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # 2. Theory comparison
        ax2 = axes[0, 1]
        phi_scores = [s.phi_score for s in self.snapshots]
        gwt_scores = [s.gwt_coherence for s in self.snapshots]
        ast_scores = [s.attention_schema_score for s in self.snapshots]
        
        ax2.plot(time_points, phi_scores, label='IIT (Φ)', alpha=0.8)
        ax2.plot(time_points, gwt_scores, label='GWT Coherence', alpha=0.8)
        ax2.plot(time_points, ast_scores, label='AST Self-Awareness', alpha=0.8)
        ax2.set_title('Theory-Specific Metrics')
        ax2.set_ylabel('Score')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Higher-order metrics
        ax3 = axes[1, 0]
        hot_scores = [s.hot_complexity for s in self.snapshots]
        meta_scores = [s.metacognitive_accuracy for s in self.snapshots]
        
        ax3.plot(time_points, hot_scores, label='HOT Complexity', alpha=0.8)
        ax3.plot(time_points, meta_scores, label='Metacognitive Accuracy', alpha=0.8)
        ax3.set_title('Higher-Order Consciousness')
        ax3.set_ylabel('Score')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Predictive processing
        ax4 = axes[1, 1] 
        pred_errors = [s.predictive_error for s in self.snapshots]
        ax4.plot(time_points, pred_errors, 'r-', label='Prediction Error', alpha=0.8)
        ax4.set_title('Predictive Processing')
        ax4.set_ylabel('Prediction Error')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. Qualia and self-model
        ax5 = axes[2, 0]
        qualia_dims = [s.qualia_dimensionality for s in self.snapshots]
        self_model_scores = [s.self_model_sophistication for s in self.snapshots]
        
        ax5.plot(time_points, qualia_dims, label='Qualia Dimensionality', alpha=0.8)
        ax5_twin = ax5.twinx()
        ax5_twin.plot(time_points, self_model_scores, 'g-', label='Self-Model', alpha=0.8)
        
        ax5.set_title('Phenomenal Consciousness')
        ax5.set_ylabel('Qualia Dimensions')
        ax5_twin.set_ylabel('Self-Model Score')
        ax5.legend(loc='upper left')
        ax5_twin.legend(loc='upper right')
        ax5.grid(True, alpha=0.3)
        
        # 6. Agency
        ax6 = axes[2, 1]
        agency_scores = [s.agency_strength for s in self.snapshots]
        ax6.plot(time_points, agency_scores, 'purple', label='Agency Strength', alpha=0.8)
        ax6.set_title('Agency and Intentionality')
        ax6.set_ylabel('Agency Score')
        ax6.set_xlabel('Time Steps')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Evolution visualization saved to {save_path}")
        
        return fig
    
    def export_evolution_data(self, filepath: str):
        """Export evolution data to JSON file."""
        try:
            export_data = {
                'snapshots': [
                    {
                        'timestamp': snapshot.timestamp.isoformat(),
                        'phi_score': snapshot.phi_score,
                        'gwt_coherence': snapshot.gwt_coherence,
                        'attention_schema_score': snapshot.attention_schema_score,
                        'hot_complexity': snapshot.hot_complexity,
                        'predictive_error': snapshot.predictive_error,
                        'qualia_dimensionality': snapshot.qualia_dimensionality,
                        'self_model_sophistication': snapshot.self_model_sophistication,
                        'metacognitive_accuracy': snapshot.metacognitive_accuracy,
                        'agency_strength': snapshot.agency_strength,
                        'overall_consciousness_score': snapshot.overall_consciousness_score,
                        'training_step': snapshot.training_step
                    }
                    for snapshot in self.snapshots
                ],
                'trends': self.evolution_trends,
                'analysis': self.analyze_consciousness_emergence()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            self.logger.info(f"Evolution data exported to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to export evolution data: {e}")