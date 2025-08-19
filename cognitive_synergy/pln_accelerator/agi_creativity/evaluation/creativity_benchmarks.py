"""
Creativity Benchmarks and Evaluation Framework

This module implements comprehensive benchmarks for evaluating creativity in AI-generated art,
providing standardized metrics for measuring creative capabilities across different domains.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time


@dataclass
class CreativityMetrics:
    """Standard creativity evaluation metrics."""
    novelty: float
    value: float
    intentionality: float
    originality: float
    fluency: float
    flexibility: float
    elaboration: float
    overall_creativity: float


class CreativityBenchmarks:
    """Comprehensive creativity benchmarking system."""
    
    def __init__(self):
        """Initialize creativity benchmark system."""
        self.benchmarks = {
            'torrance_inspired': TorranceInspiredBenchmark(),
            'consensual_assessment': ConsensualAssessmentBenchmark(),
            'computational_creativity': ComputationalCreativityBenchmark(),
            'aesthetic_measures': AestheticMeasuresBenchmark(),
            'novelty_assessment': NoveltyAssessmentBenchmark()
        }
        
        self.benchmark_history = []
        
        print("📊 Creativity benchmarks system initialized")
        print(f"🧪 Available benchmarks: {list(self.benchmarks.keys())}")
        
    def evaluate_artwork(self, artwork: Any, specification: Any = None,
                        benchmarks_to_run: List[str] = None) -> Dict[str, Any]:
        """Evaluate artwork using multiple creativity benchmarks."""
        if benchmarks_to_run is None:
            benchmarks_to_run = list(self.benchmarks.keys())
            
        results = {}
        
        for benchmark_name in benchmarks_to_run:
            if benchmark_name in self.benchmarks:
                print(f"🔬 Running {benchmark_name} benchmark...")
                try:
                    benchmark_result = self.benchmarks[benchmark_name].evaluate(artwork, specification)
                    results[benchmark_name] = benchmark_result
                except Exception as e:
                    print(f"⚠️ Benchmark {benchmark_name} failed: {e}")
                    results[benchmark_name] = None
                    
        # Calculate overall creativity score
        overall_score = self._calculate_overall_creativity(results)
        results['overall_creativity_score'] = overall_score
        
        # Store in history
        evaluation_record = {
            'timestamp': time.time(),
            'artwork_id': getattr(artwork, 'artwork_id', 'unknown'),
            'benchmark_results': results,
            'overall_score': overall_score
        }
        self.benchmark_history.append(evaluation_record)
        
        return results
        
    def _calculate_overall_creativity(self, benchmark_results: Dict[str, Any]) -> float:
        """Calculate overall creativity score from benchmark results."""
        valid_scores = []
        
        for benchmark_name, result in benchmark_results.items():
            if result is not None and isinstance(result, dict):
                if 'creativity_score' in result:
                    valid_scores.append(result['creativity_score'])
                elif 'overall_score' in result:
                    valid_scores.append(result['overall_score'])
                    
        if valid_scores:
            return np.mean(valid_scores)
        else:
            return 0.0
            
    def get_benchmark_statistics(self) -> Dict[str, Any]:
        """Get statistics about benchmark performance."""
        if not self.benchmark_history:
            return {"total_evaluations": 0}
            
        scores = [record['overall_score'] for record in self.benchmark_history]
        
        return {
            "total_evaluations": len(self.benchmark_history),
            "average_creativity": np.mean(scores),
            "creativity_std": np.std(scores),
            "max_creativity": np.max(scores),
            "min_creativity": np.min(scores),
            "recent_trend": self._calculate_trend(scores[-10:]) if len(scores) >= 10 else 0.0
        }
        
    def _calculate_trend(self, recent_scores: List[float]) -> float:
        """Calculate trend in recent creativity scores."""
        if len(recent_scores) < 2:
            return 0.0
            
        x = np.arange(len(recent_scores))
        coefficients = np.polyfit(x, recent_scores, 1)
        return coefficients[0]  # Slope indicates trend


class CreativityBenchmark(ABC):
    """Abstract base class for creativity benchmarks."""
    
    @abstractmethod
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate artwork and return creativity metrics."""
        pass


class TorranceInspiredBenchmark(CreativityBenchmark):
    """Benchmark inspired by Torrance Tests of Creative Thinking."""
    
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate using Torrance-inspired metrics."""
        
        # Fluency: Number of ideas/elements
        fluency = self._measure_fluency(artwork)
        
        # Flexibility: Variety of categories/approaches
        flexibility = self._measure_flexibility(artwork)
        
        # Originality: Statistical rarity/uniqueness
        originality = self._measure_originality(artwork)
        
        # Elaboration: Level of detail and development
        elaboration = self._measure_elaboration(artwork)
        
        # Overall creativity score
        creativity_score = (fluency + flexibility + originality + elaboration) / 4
        
        return {
            'fluency': fluency,
            'flexibility': flexibility,
            'originality': originality,
            'elaboration': elaboration,
            'creativity_score': creativity_score,
            'benchmark_type': 'torrance_inspired'
        }
        
    def _measure_fluency(self, artwork: Any) -> float:
        """Measure fluency - quantity of creative output."""
        if hasattr(artwork, 'modalities'):
            # Multi-modal artwork
            num_modalities = len(artwork.modalities)
            return min(1.0, num_modalities / 3.0)  # Normalize to 3 modalities max
        elif isinstance(artwork, dict):
            # Dictionary-based artwork
            return min(1.0, len(artwork) / 10.0)  # Normalize to 10 elements max
        elif isinstance(artwork, np.ndarray):
            # Array-based artwork - use complexity as proxy
            if len(artwork.shape) > 1:
                complexity = np.std(artwork)
                return min(1.0, complexity)
            else:
                return 0.5  # Default for 1D arrays
        else:
            return 0.5  # Default score
            
    def _measure_flexibility(self, artwork: Any) -> float:
        """Measure flexibility - variety of approaches."""
        if hasattr(artwork, 'modalities'):
            # Count different types of modalities
            modality_types = set()
            for modality in artwork.modalities.keys():
                modality_types.add(str(modality))
            return min(1.0, len(modality_types) / 4.0)  # Max 4 types
        elif isinstance(artwork, np.ndarray):
            # For arrays, measure variety in values
            if len(artwork.shape) == 3:  # Image
                # Color variety
                unique_colors = len(np.unique(artwork.reshape(-1, artwork.shape[-1]), axis=0))
                return min(1.0, unique_colors / 100.0)  # Normalize to 100 unique colors
            else:
                # General array variety
                unique_values = len(np.unique(artwork))
                total_values = artwork.size
                return unique_values / total_values if total_values > 0 else 0.0
        else:
            return 0.5
            
    def _measure_originality(self, artwork: Any) -> float:
        """Measure originality - statistical rarity."""
        # This is a simplified measure
        # In practice, would compare against large database of artworks
        
        if isinstance(artwork, np.ndarray):
            # Use entropy as proxy for originality
            if artwork.size > 1:
                # Calculate entropy
                hist, _ = np.histogram(artwork.flatten(), bins=50)
                hist = hist / np.sum(hist)  # Normalize
                entropy = -np.sum(hist * np.log(hist + 1e-10))
                return min(1.0, entropy / 4.0)  # Normalize entropy
            else:
                return 0.5
        else:
            # Default originality score
            return 0.6
            
    def _measure_elaboration(self, artwork: Any) -> float:
        """Measure elaboration - level of detail and development."""
        if isinstance(artwork, np.ndarray):
            if len(artwork.shape) == 3:  # Image
                # Use edge density as proxy for detail
                gray = np.mean(artwork, axis=2) if artwork.shape[2] > 1 else artwork[:,:,0]
                # Simple edge detection
                grad_x = np.abs(np.diff(gray, axis=1))
                grad_y = np.abs(np.diff(gray, axis=0))
                edge_density = (np.mean(grad_x) + np.mean(grad_y)) / 2
                return min(1.0, edge_density * 10)  # Scale appropriately
            elif len(artwork.shape) == 1:  # Audio
                # Use variation as proxy for elaboration
                variation = np.std(artwork)
                return min(1.0, variation * 5)
            else:
                return 0.5
        else:
            return 0.5


class ConsensualAssessmentBenchmark(CreativityBenchmark):
    """Benchmark based on Consensual Assessment Technique principles."""
    
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate using consensual assessment principles."""
        
        # Creativity assessment
        creativity = self._assess_creativity(artwork)
        
        # Technical quality
        technical_quality = self._assess_technical_quality(artwork)
        
        # Aesthetic appeal
        aesthetic_appeal = self._assess_aesthetic_appeal(artwork)
        
        # Novelty
        novelty = self._assess_novelty(artwork)
        
        # Overall assessment
        overall_score = (creativity + technical_quality + aesthetic_appeal + novelty) / 4
        
        return {
            'creativity': creativity,
            'technical_quality': technical_quality,
            'aesthetic_appeal': aesthetic_appeal,
            'novelty': novelty,
            'overall_score': overall_score,
            'benchmark_type': 'consensual_assessment'
        }
        
    def _assess_creativity(self, artwork: Any) -> float:
        """Assess overall creativity."""
        # Composite measure
        if isinstance(artwork, np.ndarray):
            # Complexity and variation
            complexity = np.std(artwork)
            uniqueness = len(np.unique(artwork)) / artwork.size if artwork.size > 0 else 0
            return min(1.0, (complexity + uniqueness) / 2)
        else:
            return 0.6  # Default
            
    def _assess_technical_quality(self, artwork: Any) -> float:
        """Assess technical execution quality."""
        if isinstance(artwork, np.ndarray):
            # Use signal-to-noise ratio as proxy
            if artwork.size > 1:
                signal_power = np.mean(artwork ** 2)
                noise_estimate = np.var(np.diff(artwork.flatten()))
                snr = signal_power / (noise_estimate + 1e-10)
                return min(1.0, snr / 10.0)  # Normalize
            else:
                return 0.5
        else:
            return 0.6
            
    def _assess_aesthetic_appeal(self, artwork: Any) -> float:
        """Assess aesthetic appeal."""
        if isinstance(artwork, np.ndarray):
            if len(artwork.shape) == 3:  # Image
                # Simple aesthetic measures
                # Color harmony (simplified)
                color_std = np.std(artwork, axis=(0,1))
                color_harmony = 1.0 - np.std(color_std) / (np.mean(color_std) + 1e-10)
                
                # Composition balance
                center_mass_x = np.sum(np.arange(artwork.shape[1]) * np.sum(artwork, axis=(0,2)))
                center_mass_x = center_mass_x / (np.sum(artwork) + 1e-10)
                balance = 1.0 - abs(center_mass_x - artwork.shape[1]/2) / (artwork.shape[1]/2)
                
                return (color_harmony + balance) / 2
            else:
                # For non-image data, use smoothness as aesthetic proxy
                if artwork.size > 1:
                    smoothness = 1.0 - np.mean(np.abs(np.diff(artwork.flatten())))
                    return max(0.0, min(1.0, smoothness))
                else:
                    return 0.5
        else:
            return 0.5
            
    def _assess_novelty(self, artwork: Any) -> float:
        """Assess novelty/uniqueness."""
        if isinstance(artwork, np.ndarray):
            # Use distribution entropy
            hist, _ = np.histogram(artwork.flatten(), bins=20)
            hist = hist / (np.sum(hist) + 1e-10)
            entropy = -np.sum(hist * np.log(hist + 1e-10))
            return min(1.0, entropy / 3.0)  # Normalize
        else:
            return 0.6


class ComputationalCreativityBenchmark(CreativityBenchmark):
    """Benchmark specifically for computational creativity evaluation."""
    
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate computational creativity aspects."""
        
        # Algorithmic creativity
        algorithmic_creativity = self._measure_algorithmic_creativity(artwork, specification)
        
        # Autonomy level
        autonomy = self._measure_autonomy(artwork, specification)
        
        # Intentionality
        intentionality = self._measure_intentionality(artwork, specification)
        
        # Value generation
        value = self._measure_value_generation(artwork)
        
        # Overall computational creativity
        overall_score = (algorithmic_creativity + autonomy + intentionality + value) / 4
        
        return {
            'algorithmic_creativity': algorithmic_creativity,
            'autonomy': autonomy,
            'intentionality': intentionality,
            'value': value,
            'overall_score': overall_score,
            'benchmark_type': 'computational_creativity'
        }
        
    def _measure_algorithmic_creativity(self, artwork: Any, specification: Any) -> float:
        """Measure creativity specific to algorithmic generation."""
        # Assess complexity of generative process
        if hasattr(artwork, 'quality_metrics'):
            complexity = artwork.quality_metrics.get('overall_quality', 0.5)
            return min(1.0, complexity)
        else:
            return 0.6
            
    def _measure_autonomy(self, artwork: Any, specification: Any) -> float:
        """Measure level of autonomous creative decision-making."""
        # In practice, this would analyze the generation process
        # For now, return a reasonable default based on available info
        return 0.7  # Assume moderate autonomy
        
    def _measure_intentionality(self, artwork: Any, specification: Any) -> float:
        """Measure goal-directed creative behavior."""
        if specification is not None:
            # Check alignment between specification and outcome
            if hasattr(specification, 'theme') and hasattr(artwork, 'metadata'):
                # Simple alignment check
                return 0.8  # Assume good alignment
            else:
                return 0.6
        else:
            return 0.5  # No specification to compare against
            
    def _measure_value_generation(self, artwork: Any) -> float:
        """Measure the value/worth of generated content."""
        # This is inherently subjective; use proxy measures
        if isinstance(artwork, np.ndarray):
            # Use information content as proxy for value
            if artwork.size > 1:
                # Entropy-based value measure
                hist, _ = np.histogram(artwork.flatten(), bins=30)
                hist = hist / (np.sum(hist) + 1e-10)
                entropy = -np.sum(hist * np.log(hist + 1e-10))
                return min(1.0, entropy / 4.0)
            else:
                return 0.5
        else:
            return 0.6


class AestheticMeasuresBenchmark(CreativityBenchmark):
    """Benchmark focusing on aesthetic quality measures."""
    
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate aesthetic measures."""
        
        # Balance and proportion
        balance = self._measure_balance(artwork)
        
        # Harmony
        harmony = self._measure_harmony(artwork)
        
        # Rhythm and movement
        rhythm = self._measure_rhythm(artwork)
        
        # Unity and coherence
        unity = self._measure_unity(artwork)
        
        # Overall aesthetic score
        overall_score = (balance + harmony + rhythm + unity) / 4
        
        return {
            'balance': balance,
            'harmony': harmony,
            'rhythm': rhythm,
            'unity': unity,
            'overall_score': overall_score,
            'benchmark_type': 'aesthetic_measures'
        }
        
    def _measure_balance(self, artwork: Any) -> float:
        """Measure visual/compositional balance."""
        if isinstance(artwork, np.ndarray):
            if len(artwork.shape) >= 2:
                # Calculate center of mass
                total_mass = np.sum(artwork)
                if total_mass > 0:
                    if len(artwork.shape) == 2:
                        center_x = np.sum(np.arange(artwork.shape[1]) * np.sum(artwork, axis=0)) / total_mass
                        center_y = np.sum(np.arange(artwork.shape[0]) * np.sum(artwork, axis=1)) / total_mass
                    else:  # 3D (e.g., color image)
                        gray = np.mean(artwork, axis=2) if artwork.shape[2] > 1 else artwork[:,:,0]
                        total_mass = np.sum(gray)
                        center_x = np.sum(np.arange(gray.shape[1]) * np.sum(gray, axis=0)) / total_mass
                        center_y = np.sum(np.arange(gray.shape[0]) * np.sum(gray, axis=1)) / total_mass
                    
                    # Distance from geometric center
                    geom_center_x, geom_center_y = artwork.shape[1] / 2, artwork.shape[0] / 2
                    distance = np.sqrt((center_x - geom_center_x)**2 + (center_y - geom_center_y)**2)
                    max_distance = np.sqrt(geom_center_x**2 + geom_center_y**2)
                    
                    balance_score = 1.0 - (distance / max_distance)
                    return max(0.0, balance_score)
                else:
                    return 0.0
            else:
                return 0.5
        else:
            return 0.5
            
    def _measure_harmony(self, artwork: Any) -> float:
        """Measure harmony in artwork."""
        if isinstance(artwork, np.ndarray):
            # Use correlation between different parts as harmony measure
            if artwork.size > 4:
                flat = artwork.flatten()
                mid = len(flat) // 2
                part1, part2 = flat[:mid], flat[mid:2*mid]
                if len(part1) == len(part2) and np.std(part1) > 0 and np.std(part2) > 0:
                    correlation = np.corrcoef(part1, part2)[0, 1]
                    return max(0.0, correlation) if not np.isnan(correlation) else 0.5
                else:
                    return 0.5
            else:
                return 0.5
        else:
            return 0.5
            
    def _measure_rhythm(self, artwork: Any) -> float:
        """Measure rhythm and movement."""
        if isinstance(artwork, np.ndarray):
            # Use periodicity in the data as rhythm measure
            if len(artwork.shape) == 1 and len(artwork) > 8:
                # 1D case - look for periodic patterns
                autocorr = np.correlate(artwork, artwork, mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                
                # Find peaks (excluding the zero-lag peak)
                peaks = []
                for i in range(1, min(len(autocorr), len(artwork)//2)):
                    if (i == 1 or autocorr[i] > autocorr[i-1]) and \
                       (i == len(autocorr)-1 or autocorr[i] > autocorr[i+1]):
                        peaks.append(autocorr[i])
                        
                if peaks:
                    rhythm_strength = max(peaks) / (autocorr[0] + 1e-10)
                    return min(1.0, rhythm_strength)
                else:
                    return 0.0
            else:
                # Multi-dimensional case - use gradient regularity
                gradients = np.gradient(artwork.flatten())
                gradient_regularity = 1.0 - (np.std(gradients) / (np.mean(np.abs(gradients)) + 1e-10))
                return max(0.0, min(1.0, gradient_regularity))
        else:
            return 0.5
            
    def _measure_unity(self, artwork: Any) -> float:
        """Measure unity and coherence."""
        if isinstance(artwork, np.ndarray):
            # Use consistency of values across the artwork
            if artwork.size > 1:
                # Coefficient of variation as unity measure
                mean_val = np.mean(artwork)
                std_val = np.std(artwork)
                if mean_val != 0:
                    cv = std_val / abs(mean_val)
                    unity_score = 1.0 / (1.0 + cv)  # Higher unity for lower variation
                    return unity_score
                else:
                    return 1.0 if std_val == 0 else 0.0
            else:
                return 1.0
        else:
            return 0.5


class NoveltyAssessmentBenchmark(CreativityBenchmark):
    """Benchmark specifically for assessing novelty and originality."""
    
    def __init__(self):
        self.reference_database = []  # Would store reference artworks in practice
        
    def evaluate(self, artwork: Any, specification: Any = None) -> Dict[str, Any]:
        """Evaluate novelty aspects."""
        
        # Statistical novelty
        statistical_novelty = self._measure_statistical_novelty(artwork)
        
        # Conceptual novelty
        conceptual_novelty = self._measure_conceptual_novelty(artwork, specification)
        
        # Historical novelty
        historical_novelty = self._measure_historical_novelty(artwork)
        
        # Contextual novelty
        contextual_novelty = self._measure_contextual_novelty(artwork, specification)
        
        # Overall novelty score
        overall_score = (statistical_novelty + conceptual_novelty + historical_novelty + contextual_novelty) / 4
        
        return {
            'statistical_novelty': statistical_novelty,
            'conceptual_novelty': conceptual_novelty,
            'historical_novelty': historical_novelty,
            'contextual_novelty': contextual_novelty,
            'overall_score': overall_score,
            'benchmark_type': 'novelty_assessment'
        }
        
    def _measure_statistical_novelty(self, artwork: Any) -> float:
        """Measure statistical rarity/unusualness."""
        if isinstance(artwork, np.ndarray):
            # Use entropy and distribution shape
            hist, _ = np.histogram(artwork.flatten(), bins=50)
            hist = hist / (np.sum(hist) + 1e-10)
            
            # Entropy
            entropy = -np.sum(hist * np.log(hist + 1e-10))
            
            # Distribution uniformity (higher = more novel)
            expected_uniform = 1.0 / len(hist)
            uniformity = 1.0 - np.sum(np.abs(hist - expected_uniform)) / 2
            
            return (entropy / 4.0 + uniformity) / 2  # Normalize and combine
        else:
            return 0.6
            
    def _measure_conceptual_novelty(self, artwork: Any, specification: Any) -> float:
        """Measure novelty of underlying concepts."""
        # This would require sophisticated concept analysis
        # For now, use proxy measures
        if hasattr(artwork, 'metadata'):
            if 'synthesis_method' in artwork.metadata:
                return 0.8  # Synthesized concepts are novel
            else:
                return 0.6
        else:
            return 0.6
            
    def _measure_historical_novelty(self, artwork: Any) -> float:
        """Measure novelty compared to historical artworks."""
        # This would require comparison with historical database
        # For now, return a reasonable estimate
        return 0.7  # Assume moderate historical novelty
        
    def _measure_contextual_novelty(self, artwork: Any, specification: Any) -> float:
        """Measure novelty within specific context."""
        # Context-dependent novelty assessment
        if specification is not None:
            # Higher novelty if artwork differs from typical for its context
            return 0.75  # Assume good contextual novelty
        else:
            return 0.6