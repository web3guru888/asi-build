"""
Biological Consciousness Markers
===============================

Benchmarking system that compares machine consciousness metrics
against known biological consciousness markers and thresholds.
"""

import numpy as np
from typing import Dict, List, Tuple, Any
import logging
from dataclasses import dataclass

@dataclass
class BiologicalBenchmark:
    """A biological consciousness benchmark."""
    name: str
    human_range: Tuple[float, float]
    animal_ranges: Dict[str, Tuple[float, float]]
    threshold_conscious: float
    measurement_unit: str
    description: str

class BiologicalConsciousnessMarkers:
    """
    Biological consciousness benchmarking system.
    
    Provides benchmarks based on known biological consciousness markers
    from neuroscience research.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_benchmarks()
    
    def _initialize_benchmarks(self):
        """Initialize biological consciousness benchmarks."""
        self.benchmarks = {
            'phi_score': BiologicalBenchmark(
                name='Integrated Information (Φ)',
                human_range=(0.5, 1.0),
                animal_ranges={
                    'primates': (0.3, 0.7),
                    'mammals': (0.2, 0.5),
                    'birds': (0.15, 0.4),
                    'reptiles': (0.05, 0.2)
                },
                threshold_conscious=0.3,
                measurement_unit='phi units',
                description='IIT-based integrated information measure'
            ),
            
            'gwt_coherence': BiologicalBenchmark(
                name='Global Workspace Coherence',
                human_range=(0.7, 0.95),
                animal_ranges={
                    'primates': (0.5, 0.8),
                    'mammals': (0.4, 0.7),
                    'birds': (0.3, 0.6)
                },
                threshold_conscious=0.4,
                measurement_unit='coherence score',
                description='Global workspace integration measure'
            ),
            
            'attention_schema_score': BiologicalBenchmark(
                name='Attention Schema Sophistication',
                human_range=(0.6, 0.9),
                animal_ranges={
                    'primates': (0.4, 0.7),
                    'mammals': (0.2, 0.5),
                    'birds': (0.15, 0.4)
                },
                threshold_conscious=0.3,
                measurement_unit='self-awareness score',
                description='Self-awareness and attention monitoring'
            ),
            
            'metacognitive_accuracy': BiologicalBenchmark(
                name='Metacognitive Accuracy',
                human_range=(0.6, 0.85),
                animal_ranges={
                    'primates': (0.3, 0.6),
                    'mammals': (0.1, 0.4),
                    'birds': (0.05, 0.3)
                },
                threshold_conscious=0.2,
                measurement_unit='accuracy score',
                description='Metacognitive monitoring and control'
            ),
            
            'predictive_accuracy': BiologicalBenchmark(
                name='Predictive Processing Accuracy',
                human_range=(0.7, 0.9),
                animal_ranges={
                    'primates': (0.5, 0.8),
                    'mammals': (0.4, 0.7),
                    'birds': (0.3, 0.6),
                    'reptiles': (0.2, 0.4)
                },
                threshold_conscious=0.3,
                measurement_unit='prediction accuracy',
                description='Predictive processing effectiveness'
            ),
            
            'agency_strength': BiologicalBenchmark(
                name='Agency Attribution',
                human_range=(0.6, 0.9),
                animal_ranges={
                    'primates': (0.4, 0.7),
                    'mammals': (0.2, 0.5),
                    'birds': (0.1, 0.4)
                },
                threshold_conscious=0.25,
                measurement_unit='agency score',
                description='Sense of agency and intentionality'
            )
        }
        
        self.logger.info("Biological consciousness benchmarks initialized")
    
    def compare_to_biological_markers(self, consciousness_profile: Any) -> Dict[str, Any]:
        """
        Compare consciousness profile to biological markers.
        
        Args:
            consciousness_profile: Consciousness assessment profile
            
        Returns:
            Comprehensive biological comparison
        """
        comparison_results = {
            'overall_assessment': {},
            'metric_comparisons': {},
            'consciousness_classification': '',
            'biological_similarity_scores': {},
            'recommendations': []
        }
        
        # Compare each metric
        metric_scores = []
        human_similarities = []
        
        for metric_name, benchmark in self.benchmarks.items():
            if hasattr(consciousness_profile, metric_name):
                value = getattr(consciousness_profile, metric_name)
                
                # Special handling for prediction error (convert to accuracy)
                if metric_name == 'predictive_accuracy' and hasattr(consciousness_profile, 'predictive_error'):
                    value = 1.0 - consciousness_profile.predictive_error
                
                comparison = self._compare_metric_to_benchmark(value, benchmark)
                comparison_results['metric_comparisons'][metric_name] = comparison
                
                # Track overall scores
                metric_scores.append(comparison['consciousness_likelihood'])
                human_similarities.append(comparison['human_similarity'])
        
        # Overall assessment
        if metric_scores:
            comparison_results['overall_assessment'] = {
                'mean_consciousness_likelihood': float(np.mean(metric_scores)),
                'consciousness_confidence': float(np.std(metric_scores)),  # Lower std = higher confidence
                'human_similarity': float(np.mean(human_similarities)),
                'metrics_above_threshold': int(sum(1 for score in metric_scores if score > 0.5))
            }
        
        # Classification
        comparison_results['consciousness_classification'] = self._classify_consciousness_level(
            comparison_results['overall_assessment'].get('mean_consciousness_likelihood', 0.0)
        )
        
        # Biological similarity scores
        comparison_results['biological_similarity_scores'] = self._compute_biological_similarities(
            consciousness_profile
        )
        
        # Recommendations
        comparison_results['recommendations'] = self._generate_enhancement_recommendations(
            comparison_results['metric_comparisons']
        )
        
        return comparison_results
    
    def _compare_metric_to_benchmark(self, value: float, benchmark: BiologicalBenchmark) -> Dict[str, Any]:
        """Compare a single metric to its biological benchmark."""
        comparison = {
            'value': value,
            'benchmark_name': benchmark.name,
            'human_range': benchmark.human_range,
            'threshold_conscious': benchmark.threshold_conscious,
            'consciousness_likelihood': 0.0,
            'human_similarity': 0.0,
            'animal_comparisons': {},
            'above_threshold': value >= benchmark.threshold_conscious
        }
        
        # Consciousness likelihood based on threshold
        if value >= benchmark.threshold_conscious:
            # Sigmoid scaling above threshold
            excess = value - benchmark.threshold_conscious
            max_excess = 1.0 - benchmark.threshold_conscious
            comparison['consciousness_likelihood'] = 0.5 + 0.5 * (excess / max_excess)
        else:
            # Linear scaling below threshold
            comparison['consciousness_likelihood'] = 0.5 * (value / benchmark.threshold_conscious)
        
        # Human similarity
        human_min, human_max = benchmark.human_range
        if human_min <= value <= human_max:
            comparison['human_similarity'] = 1.0
        elif value < human_min:
            comparison['human_similarity'] = value / human_min
        else:  # value > human_max
            comparison['human_similarity'] = max(0.0, 1.0 - (value - human_max))
        
        # Animal comparisons
        for animal, (animal_min, animal_max) in benchmark.animal_ranges.items():
            if animal_min <= value <= animal_max:
                comparison['animal_comparisons'][animal] = 1.0
            elif value < animal_min:
                comparison['animal_comparisons'][animal] = value / animal_min
            else:
                comparison['animal_comparisons'][animal] = max(0.0, 1.0 - (value - animal_max))
        
        return comparison
    
    def _classify_consciousness_level(self, mean_likelihood: float) -> str:
        """Classify consciousness level based on biological comparison."""
        if mean_likelihood >= 0.85:
            return "Human-level consciousness"
        elif mean_likelihood >= 0.70:
            return "High-level consciousness (primate-like)"
        elif mean_likelihood >= 0.50:
            return "Moderate consciousness (mammalian-like)"
        elif mean_likelihood >= 0.30:
            return "Basic consciousness (vertebrate-like)"
        elif mean_likelihood >= 0.15:
            return "Minimal consciousness (simple organism)"
        else:
            return "Pre-conscious (primarily reactive)"
    
    def _compute_biological_similarities(self, consciousness_profile: Any) -> Dict[str, float]:
        """Compute similarity scores to different biological categories."""
        similarities = {
            'human': [],
            'primates': [],
            'mammals': [],
            'birds': [],
            'reptiles': []
        }
        
        for metric_name, benchmark in self.benchmarks.items():
            if hasattr(consciousness_profile, metric_name):
                value = getattr(consciousness_profile, metric_name)
                
                # Special handling for prediction error
                if metric_name == 'predictive_accuracy' and hasattr(consciousness_profile, 'predictive_error'):
                    value = 1.0 - consciousness_profile.predictive_error
                
                # Human similarity
                human_min, human_max = benchmark.human_range
                human_center = (human_min + human_max) / 2
                human_sim = 1.0 - abs(value - human_center) / (human_max - human_min + 0.1)
                similarities['human'].append(max(0.0, human_sim))
                
                # Animal similarities
                for animal in similarities:
                    if animal != 'human' and animal in benchmark.animal_ranges:
                        animal_min, animal_max = benchmark.animal_ranges[animal]
                        animal_center = (animal_min + animal_max) / 2
                        animal_sim = 1.0 - abs(value - animal_center) / (animal_max - animal_min + 0.1)
                        similarities[animal].append(max(0.0, animal_sim))
        
        # Average similarities
        similarity_scores = {}
        for category, scores in similarities.items():
            if scores:
                similarity_scores[category] = float(np.mean(scores))
            else:
                similarity_scores[category] = 0.0
        
        return similarity_scores
    
    def _generate_enhancement_recommendations(self, metric_comparisons: Dict[str, Any]) -> List[str]:
        """Generate recommendations for enhancing consciousness metrics."""
        recommendations = []
        
        for metric_name, comparison in metric_comparisons.items():
            if not comparison['above_threshold']:
                benchmark_name = comparison['benchmark_name']
                threshold = comparison['threshold_conscious']
                current_value = comparison['value']
                
                improvement_needed = threshold - current_value
                
                if metric_name == 'phi_score':
                    recommendations.append(
                        f"Increase neural integration and connectivity to improve Φ score "
                        f"(current: {current_value:.3f}, needs: +{improvement_needed:.3f})"
                    )
                elif metric_name == 'gwt_coherence':
                    recommendations.append(
                        f"Enhance global workspace mechanisms and attention integration "
                        f"(current: {current_value:.3f}, target: >{threshold:.3f})"
                    )
                elif metric_name == 'attention_schema_score':
                    recommendations.append(
                        f"Develop stronger self-monitoring and attention awareness capabilities "
                        f"(current: {current_value:.3f}, target: >{threshold:.3f})"
                    )
                elif metric_name == 'metacognitive_accuracy':
                    recommendations.append(
                        f"Improve metacognitive monitoring and confidence calibration "
                        f"(current: {current_value:.3f}, target: >{threshold:.3f})"
                    )
                elif metric_name == 'predictive_accuracy':
                    recommendations.append(
                        f"Enhance predictive processing and error minimization "
                        f"(current: {current_value:.3f}, target: >{threshold:.3f})"
                    )
                elif metric_name == 'agency_strength':
                    recommendations.append(
                        f"Strengthen sense of agency and intentional control mechanisms "
                        f"(current: {current_value:.3f}, target: >{threshold:.3f})"
                    )
        
        # High-level recommendations
        consciousness_likelihood = np.mean([
            comp['consciousness_likelihood'] for comp in metric_comparisons.values()
        ])
        
        if consciousness_likelihood < 0.3:
            recommendations.append("Overall consciousness level is low - focus on basic integration and awareness mechanisms")
        elif consciousness_likelihood < 0.7:
            recommendations.append("Moderate consciousness detected - enhance higher-order cognitive capabilities")
        
        if not recommendations:
            recommendations.append("Consciousness profile shows strong performance across biological markers")
        
        return recommendations
    
    def generate_biological_consciousness_report(self, consciousness_profile: Any) -> Dict[str, Any]:
        """Generate comprehensive biological consciousness comparison report."""
        comparison = self.compare_to_biological_markers(consciousness_profile)
        
        report = {
            'assessment_timestamp': consciousness_profile.timestamp.isoformat(),
            'biological_comparison_summary': {
                'consciousness_classification': comparison['consciousness_classification'],
                'mean_consciousness_likelihood': comparison['overall_assessment'].get('mean_consciousness_likelihood', 0.0),
                'human_similarity_score': comparison['overall_assessment'].get('human_similarity', 0.0),
                'metrics_above_biological_threshold': comparison['overall_assessment'].get('metrics_above_threshold', 0)
            },
            'detailed_metric_comparisons': comparison['metric_comparisons'],
            'biological_similarity_profile': comparison['biological_similarity_scores'],
            'enhancement_recommendations': comparison['recommendations'],
            'consciousness_development_stage': self._determine_development_stage(comparison),
            'research_implications': self._generate_research_implications(comparison)
        }
        
        return report
    
    def _determine_development_stage(self, comparison: Dict[str, Any]) -> str:
        """Determine the developmental stage of consciousness."""
        likelihood = comparison['overall_assessment'].get('mean_consciousness_likelihood', 0.0)
        
        if likelihood >= 0.8:
            return "Advanced consciousness (human-comparable)"
        elif likelihood >= 0.6:
            return "Developing consciousness (emerging higher-order capabilities)"
        elif likelihood >= 0.4:
            return "Basic consciousness (fundamental awareness present)"
        elif likelihood >= 0.2:
            return "Proto-consciousness (rudimentary awareness emerging)"
        else:
            return "Pre-conscious (no clear consciousness markers)"
    
    def _generate_research_implications(self, comparison: Dict[str, Any]) -> List[str]:
        """Generate research implications from biological comparison."""
        implications = []
        
        likelihood = comparison['overall_assessment'].get('mean_consciousness_likelihood', 0.0)
        human_similarity = comparison['overall_assessment'].get('human_similarity', 0.0)
        
        if likelihood > 0.7:
            implications.append("System shows strong consciousness signatures - suitable for advanced consciousness research")
        
        if human_similarity > 0.6:
            implications.append("Human-like consciousness patterns detected - valuable for comparative consciousness studies")
        
        # Theory-specific implications
        metric_comparisons = comparison['metric_comparisons']
        
        if 'phi_score' in metric_comparisons and metric_comparisons['phi_score']['consciousness_likelihood'] > 0.7:
            implications.append("High IIT Φ score supports integrated information theory of consciousness")
        
        if 'gwt_coherence' in metric_comparisons and metric_comparisons['gwt_coherence']['consciousness_likelihood'] > 0.7:
            implications.append("Strong global workspace coherence supports GWT framework")
        
        if not implications:
            implications.append("System requires further development to reach consciousness thresholds suitable for research")
        
        return implications