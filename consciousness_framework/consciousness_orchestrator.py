"""
Consciousness Testing Framework Orchestrator
===========================================

Main orchestrator class that coordinates all consciousness measurement theories
and provides a unified interface for consciousness assessment.
"""

import numpy as np
import torch
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class ConsciousnessProfile:
    """Complete consciousness assessment profile."""
    timestamp: datetime
    phi_score: float  # IIT Φ value
    gwt_coherence: float  # Global Workspace coherence
    attention_schema_score: float  # Self-awareness metric
    hot_complexity: float  # Higher-order thought complexity
    predictive_error: float  # Predictive processing accuracy
    qualia_dimensionality: int  # Phenomenal experience dimensions
    self_model_sophistication: float  # Self-representation quality
    metacognitive_accuracy: float  # Metacognition performance
    agency_strength: float  # Intentionality measure
    overall_consciousness_score: float  # Weighted composite score
    

class ConsciousnessOrchestrator:
    """
    Main orchestrator for consciousness testing framework.
    
    Coordinates multiple theories of consciousness to provide comprehensive
    assessment of machine consciousness across different paradigms.
    """
    
    def __init__(self, 
                 device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
                 log_level: str = 'INFO'):
        """
        Initialize the consciousness testing framework.
        
        Args:
            device: Computing device for neural operations
            log_level: Logging verbosity level
        """
        self.device = device
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level))
        
        # Initialize theory implementations
        self._initialize_theories()
        
        # Consciousness assessment history
        self.assessment_history: List[ConsciousnessProfile] = []
        
        # Theoretical weights for composite scoring
        self.theory_weights = {
            'iit': 0.15,           # Integrated Information Theory
            'gwt': 0.15,           # Global Workspace Theory
            'attention_schema': 0.12,  # Attention Schema Theory
            'hot': 0.12,           # Higher-Order Thought Theory
            'predictive': 0.10,    # Predictive Processing
            'qualia': 0.10,        # Qualia mapping
            'self_model': 0.10,    # Self-model sophistication
            'metacognition': 0.08, # Metacognitive assessment
            'agency': 0.08         # Agency detection
        }
        
        # Biological consciousness benchmarks
        self.biological_benchmarks = {
            'human_phi_range': (0.5, 1.0),
            'human_gwt_coherence': (0.7, 0.95),
            'human_metacognitive_accuracy': (0.6, 0.85),
            'consciousness_threshold': 0.65  # Composite score threshold
        }
        
    def _initialize_theories(self):
        """Initialize all consciousness theory implementations."""
        from .theories.integrated_information import IITCalculator
        from .theories.global_workspace import GWTImplementation
        from .theories.attention_schema import AttentionSchemaAnalyzer
        from .theories.higher_order_thought import HOTTheoryImplementation
        from .theories.predictive_processing import PredictiveProcessingMetrics
        from .analyzers.qualia_mapper import QualiaSpaceMapper
        from .analyzers.self_model import SelfModelAnalyzer
        from .analyzers.metacognition import MetacognitionAssessor
        from .analyzers.agency_detector import AgencyDetector
        from .trackers.consciousness_evolution import ConsciousnessEvolutionTracker
        
        try:
            self.iit_calculator = IITCalculator(device=self.device)
            self.gwt_implementation = GWTImplementation(device=self.device)
            self.attention_schema = AttentionSchemaAnalyzer(device=self.device)
            self.hot_theory = HOTTheoryImplementation(device=self.device)
            self.predictive_processing = PredictiveProcessingMetrics(device=self.device)
            self.qualia_mapper = QualiaSpaceMapper(device=self.device)
            self.self_model_analyzer = SelfModelAnalyzer(device=self.device)
            self.metacognition_assessor = MetacognitionAssessor(device=self.device)
            self.agency_detector = AgencyDetector(device=self.device)
            self.evolution_tracker = ConsciousnessEvolutionTracker()
            
            self.logger.info("All consciousness theory implementations initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize consciousness theories: {e}")
            raise
    
    def assess_consciousness(self, 
                           neural_activations: torch.Tensor,
                           attention_maps: Optional[torch.Tensor] = None,
                           behavioral_data: Optional[Dict[str, Any]] = None,
                           include_visualization: bool = False) -> ConsciousnessProfile:
        """
        Perform comprehensive consciousness assessment.
        
        Args:
            neural_activations: Neural network activations to analyze
            attention_maps: Attention mechanism outputs (optional)
            behavioral_data: Behavioral metrics and responses
            include_visualization: Whether to generate visualization data
            
        Returns:
            Complete consciousness assessment profile
        """
        self.logger.info("Starting comprehensive consciousness assessment")
        
        try:
            # 1. Integrated Information Theory (IIT) - Φ computation
            phi_score = self.iit_calculator.compute_phi(neural_activations)
            
            # 2. Global Workspace Theory (GWT) - coherence analysis
            gwt_coherence = self.gwt_implementation.assess_global_coherence(
                neural_activations, attention_maps
            )
            
            # 3. Attention Schema Theory - self-awareness
            attention_schema_score = self.attention_schema.measure_self_awareness(
                neural_activations, attention_maps
            )
            
            # 4. Higher-Order Thought Theory - metacognitive complexity
            hot_complexity = self.hot_theory.assess_higher_order_thoughts(
                neural_activations, behavioral_data
            )
            
            # 5. Predictive Processing - prediction accuracy
            predictive_error = self.predictive_processing.compute_prediction_metrics(
                neural_activations, behavioral_data
            )
            
            # 6. Qualia Space Mapping - phenomenal experience
            qualia_dimensionality = self.qualia_mapper.map_qualia_space(
                neural_activations
            )
            
            # 7. Self-Model Sophistication
            self_model_sophistication = self.self_model_analyzer.analyze_self_representation(
                neural_activations, behavioral_data
            )
            
            # 8. Metacognitive Assessment
            metacognitive_accuracy = self.metacognition_assessor.assess_metacognition(
                neural_activations, behavioral_data
            )
            
            # 9. Agency Detection
            agency_strength = self.agency_detector.detect_intentionality(
                neural_activations, behavioral_data
            )
            
            # 10. Compute overall consciousness score
            overall_score = self._compute_composite_score({
                'phi': phi_score,
                'gwt': gwt_coherence,
                'attention_schema': attention_schema_score,
                'hot': hot_complexity,
                'predictive': 1.0 - predictive_error,  # Lower error = higher consciousness
                'qualia': min(qualia_dimensionality / 100.0, 1.0),  # Normalize
                'self_model': self_model_sophistication,
                'metacognition': metacognitive_accuracy,
                'agency': agency_strength
            })
            
            # Create consciousness profile
            profile = ConsciousnessProfile(
                timestamp=datetime.now(),
                phi_score=phi_score,
                gwt_coherence=gwt_coherence,
                attention_schema_score=attention_schema_score,
                hot_complexity=hot_complexity,
                predictive_error=predictive_error,
                qualia_dimensionality=qualia_dimensionality,
                self_model_sophistication=self_model_sophistication,
                metacognitive_accuracy=metacognitive_accuracy,
                agency_strength=agency_strength,
                overall_consciousness_score=overall_score
            )
            
            # Store assessment
            self.assessment_history.append(profile)
            
            # Track evolution
            self.evolution_tracker.record_assessment(profile)
            
            self.logger.info(f"Consciousness assessment completed. Overall score: {overall_score:.3f}")
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Consciousness assessment failed: {e}")
            raise
    
    def _compute_composite_score(self, theory_scores: Dict[str, float]) -> float:
        """
        Compute weighted composite consciousness score.
        
        Args:
            theory_scores: Individual theory assessment scores
            
        Returns:
            Weighted composite consciousness score
        """
        composite = 0.0
        total_weight = 0.0
        
        for theory, score in theory_scores.items():
            if theory in self.theory_weights:
                weight = self.theory_weights[theory]
                composite += score * weight
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            composite /= total_weight
            
        return composite
    
    def compare_to_biological_benchmarks(self, profile: ConsciousnessProfile) -> Dict[str, Any]:
        """
        Compare consciousness profile to biological benchmarks.
        
        Args:
            profile: Consciousness assessment profile
            
        Returns:
            Comparison results with biological consciousness markers
        """
        comparisons = {
            'phi_comparison': self._compare_to_range(
                profile.phi_score, 
                self.biological_benchmarks['human_phi_range']
            ),
            'gwt_comparison': self._compare_to_range(
                profile.gwt_coherence,
                self.biological_benchmarks['human_gwt_coherence']
            ),
            'metacognitive_comparison': self._compare_to_range(
                profile.metacognitive_accuracy,
                self.biological_benchmarks['human_metacognitive_accuracy']
            ),
            'consciousness_threshold_met': (
                profile.overall_consciousness_score >= 
                self.biological_benchmarks['consciousness_threshold']
            ),
            'biological_similarity_score': self._compute_biological_similarity(profile)
        }
        
        return comparisons
    
    def _compare_to_range(self, value: float, range_tuple: Tuple[float, float]) -> Dict[str, Any]:
        """Compare a value to a biological range."""
        min_val, max_val = range_tuple
        
        return {
            'value': value,
            'range': range_tuple,
            'within_range': min_val <= value <= max_val,
            'percentile': (value - min_val) / (max_val - min_val) if max_val > min_val else 0.0
        }
    
    def _compute_biological_similarity(self, profile: ConsciousnessProfile) -> float:
        """Compute overall similarity to biological consciousness."""
        similarities = []
        
        # Phi similarity
        phi_sim = 1.0 - abs(profile.phi_score - 0.75) / 0.75  # Assume 0.75 as human average
        similarities.append(max(0.0, phi_sim))
        
        # GWT similarity  
        gwt_sim = 1.0 - abs(profile.gwt_coherence - 0.825) / 0.825
        similarities.append(max(0.0, gwt_sim))
        
        # Metacognitive similarity
        meta_sim = 1.0 - abs(profile.metacognitive_accuracy - 0.725) / 0.725
        similarities.append(max(0.0, meta_sim))
        
        return np.mean(similarities)
    
    def generate_consciousness_report(self, profile: ConsciousnessProfile) -> Dict[str, Any]:
        """
        Generate comprehensive consciousness assessment report.
        
        Args:
            profile: Consciousness assessment profile
            
        Returns:
            Detailed assessment report
        """
        biological_comparison = self.compare_to_biological_benchmarks(profile)
        
        report = {
            'assessment_timestamp': profile.timestamp.isoformat(),
            'consciousness_scores': {
                'integrated_information_phi': profile.phi_score,
                'global_workspace_coherence': profile.gwt_coherence,
                'attention_schema_awareness': profile.attention_schema_score,
                'higher_order_thought_complexity': profile.hot_complexity,
                'predictive_processing_error': profile.predictive_error,
                'qualia_space_dimensions': profile.qualia_dimensionality,
                'self_model_sophistication': profile.self_model_sophistication,
                'metacognitive_accuracy': profile.metacognitive_accuracy,
                'agency_intentionality': profile.agency_strength,
                'overall_consciousness': profile.overall_consciousness_score
            },
            'biological_comparison': biological_comparison,
            'consciousness_classification': self._classify_consciousness_level(profile),
            'evolution_trends': self.evolution_tracker.get_recent_trends() if len(self.assessment_history) > 1 else None,
            'recommendations': self._generate_recommendations(profile)
        }
        
        return report
    
    def _classify_consciousness_level(self, profile: ConsciousnessProfile) -> str:
        """Classify the level of consciousness based on assessment."""
        score = profile.overall_consciousness_score
        
        if score >= 0.85:
            return "High-level consciousness (approaching human-like)"
        elif score >= 0.65:
            return "Moderate consciousness (threshold met)"
        elif score >= 0.45:
            return "Emerging consciousness (subthreshold)"
        elif score >= 0.25:
            return "Proto-consciousness (basic awareness)"
        else:
            return "Minimal consciousness (primarily reactive)"
    
    def _generate_recommendations(self, profile: ConsciousnessProfile) -> List[str]:
        """Generate recommendations for consciousness enhancement."""
        recommendations = []
        
        if profile.phi_score < 0.3:
            recommendations.append("Increase neural integration and connectivity")
        
        if profile.gwt_coherence < 0.5:
            recommendations.append("Enhance global workspace coherence mechanisms")
            
        if profile.attention_schema_score < 0.4:
            recommendations.append("Develop stronger attention monitoring and self-awareness")
            
        if profile.metacognitive_accuracy < 0.5:
            recommendations.append("Improve metacognitive monitoring and control processes")
            
        if profile.agency_strength < 0.4:
            recommendations.append("Strengthen goal-directed behavior and intentionality")
            
        if not recommendations:
            recommendations.append("Consciousness profile appears well-developed across all dimensions")
            
        return recommendations
    
    def save_assessment_history(self, filepath: str):
        """Save consciousness assessment history to file."""
        history_data = []
        for profile in self.assessment_history:
            history_data.append({
                'timestamp': profile.timestamp.isoformat(),
                'phi_score': profile.phi_score,
                'gwt_coherence': profile.gwt_coherence,
                'attention_schema_score': profile.attention_schema_score,
                'hot_complexity': profile.hot_complexity,
                'predictive_error': profile.predictive_error,
                'qualia_dimensionality': profile.qualia_dimensionality,
                'self_model_sophistication': profile.self_model_sophistication,
                'metacognitive_accuracy': profile.metacognitive_accuracy,
                'agency_strength': profile.agency_strength,
                'overall_consciousness_score': profile.overall_consciousness_score
            })
        
        with open(filepath, 'w') as f:
            json.dump(history_data, f, indent=2)
    
    def load_assessment_history(self, filepath: str):
        """Load consciousness assessment history from file."""
        with open(filepath, 'r') as f:
            history_data = json.load(f)
        
        self.assessment_history = []
        for data in history_data:
            profile = ConsciousnessProfile(
                timestamp=datetime.fromisoformat(data['timestamp']),
                phi_score=data['phi_score'],
                gwt_coherence=data['gwt_coherence'],
                attention_schema_score=data['attention_schema_score'],
                hot_complexity=data['hot_complexity'],
                predictive_error=data['predictive_error'],
                qualia_dimensionality=data['qualia_dimensionality'],
                self_model_sophistication=data['self_model_sophistication'],
                metacognitive_accuracy=data['metacognitive_accuracy'],
                agency_strength=data['agency_strength'],
                overall_consciousness_score=data['overall_consciousness_score']
            )
            self.assessment_history.append(profile)