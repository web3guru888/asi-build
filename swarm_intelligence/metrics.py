"""
Swarm Intelligence Metrics and Evaluation System

This module provides comprehensive metrics and evaluation tools for
swarm intelligence algorithms, including performance measurement,
statistical analysis, and benchmarking capabilities.
"""

import numpy as np
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from .base import SwarmOptimizer


class MetricType(Enum):
    """Types of metrics for swarm evaluation"""
    PERFORMANCE = "performance"
    CONVERGENCE = "convergence"
    DIVERSITY = "diversity"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    SCALABILITY = "scalability"
    QUALITY = "quality"


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    algorithm_name: str
    problem_name: str
    best_fitness: float
    mean_fitness: float
    std_fitness: float
    convergence_iteration: Optional[int]
    execution_time: float
    success_rate: float
    diversity_score: float
    efficiency_score: float


class SwarmMetrics:
    """
    Comprehensive metrics calculator for swarm intelligence algorithms
    
    Provides tools for measuring performance, convergence, diversity,
    efficiency, and other important characteristics of swarm algorithms.
    """
    
    def __init__(self):
        self.metrics_history = []
        self.benchmark_results = []
        
    def calculate_convergence_metrics(self, fitness_history: List[float]) -> Dict[str, float]:
        """Calculate convergence-related metrics"""
        if not fitness_history:
            return {}
        
        fitness_array = np.array(fitness_history)
        
        # Basic convergence metrics
        initial_fitness = fitness_array[0]
        final_fitness = fitness_array[-1]
        improvement = initial_fitness - final_fitness
        improvement_ratio = improvement / max(abs(initial_fitness), 1e-10)
        
        # Convergence speed
        convergence_iteration = self._find_convergence_iteration(fitness_array)
        convergence_speed = convergence_iteration / len(fitness_array) if convergence_iteration else 1.0
        
        # Stability metrics
        final_window = min(50, len(fitness_array) // 4)
        if final_window > 1:
            final_values = fitness_array[-final_window:]
            stability = 1.0 / (1.0 + np.std(final_values))
        else:
            stability = 1.0
        
        # Convergence curve characteristics
        if len(fitness_array) > 10:
            gradient = np.gradient(fitness_array)
            convergence_smoothness = 1.0 / (1.0 + np.std(gradient))
        else:
            convergence_smoothness = 1.0
        
        return {
            'initial_fitness': float(initial_fitness),
            'final_fitness': float(final_fitness),
            'improvement': float(improvement),
            'improvement_ratio': float(improvement_ratio),
            'convergence_iteration': convergence_iteration,
            'convergence_speed': float(convergence_speed),
            'stability': float(stability),
            'convergence_smoothness': float(convergence_smoothness)
        }
    
    def calculate_diversity_metrics(self, population_positions: List[np.ndarray]) -> Dict[str, float]:
        """Calculate diversity-related metrics"""
        if len(population_positions) < 2:
            return {'diversity': 0.0}
        
        positions = np.array(population_positions)
        
        # Centroid-based diversity
        centroid = np.mean(positions, axis=0)
        distances_from_centroid = [np.linalg.norm(pos - centroid) for pos in positions]
        mean_distance = np.mean(distances_from_centroid)
        
        # Pairwise diversity
        pairwise_distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                distance = np.linalg.norm(positions[i] - positions[j])
                pairwise_distances.append(distance)
        
        mean_pairwise_distance = np.mean(pairwise_distances) if pairwise_distances else 0.0
        
        # Normalized diversity (0-1 scale)
        dimension = positions.shape[1]
        max_possible_distance = np.sqrt(dimension)  # Normalized space
        normalized_diversity = mean_distance / max_possible_distance
        
        # Diversity distribution
        diversity_std = np.std(distances_from_centroid)
        diversity_uniformity = 1.0 / (1.0 + diversity_std)
        
        return {
            'mean_distance_from_centroid': float(mean_distance),
            'mean_pairwise_distance': float(mean_pairwise_distance),
            'normalized_diversity': float(normalized_diversity),
            'diversity_uniformity': float(diversity_uniformity),
            'diversity_std': float(diversity_std)
        }
    
    def calculate_efficiency_metrics(self, execution_time: float, 
                                   evaluations: int,
                                   final_fitness: float) -> Dict[str, float]:
        """Calculate efficiency-related metrics"""
        # Time efficiency
        evaluations_per_second = evaluations / max(execution_time, 1e-6)
        
        # Quality efficiency (quality per evaluation)
        quality_per_evaluation = 1.0 / (1.0 + final_fitness) / max(evaluations, 1)
        
        # Quality per time
        quality_per_time = 1.0 / (1.0 + final_fitness) / max(execution_time, 1e-6)
        
        return {
            'execution_time': float(execution_time),
            'total_evaluations': int(evaluations),
            'evaluations_per_second': float(evaluations_per_second),
            'quality_per_evaluation': float(quality_per_evaluation),
            'quality_per_time': float(quality_per_time)
        }
    
    def calculate_robustness_metrics(self, multiple_run_results: List[float]) -> Dict[str, float]:
        """Calculate robustness metrics across multiple runs"""
        if not multiple_run_results:
            return {}
        
        results = np.array(multiple_run_results)
        
        # Statistical measures
        mean_result = np.mean(results)
        std_result = np.std(results)
        min_result = np.min(results)
        max_result = np.max(results)
        
        # Robustness indicators
        coefficient_of_variation = std_result / max(abs(mean_result), 1e-10)
        robustness_score = 1.0 / (1.0 + coefficient_of_variation)
        
        # Success rate (assuming lower is better)
        threshold = mean_result + std_result
        success_rate = np.sum(results <= threshold) / len(results)
        
        return {
            'mean_result': float(mean_result),
            'std_result': float(std_result),
            'min_result': float(min_result),
            'max_result': float(max_result),
            'coefficient_of_variation': float(coefficient_of_variation),
            'robustness_score': float(robustness_score),
            'success_rate': float(success_rate)
        }
    
    def calculate_scalability_metrics(self, dimension_results: Dict[int, float]) -> Dict[str, float]:
        """Calculate scalability metrics across different dimensions"""
        if len(dimension_results) < 2:
            return {}
        
        dimensions = sorted(dimension_results.keys())
        results = [dimension_results[d] for d in dimensions]
        
        # Fit scaling curve
        log_dims = np.log(dimensions)
        log_results = np.log(np.array(results) + 1e-10)  # Avoid log(0)
        
        # Linear fit in log space
        coeffs = np.polyfit(log_dims, log_results, 1)
        scaling_exponent = coeffs[0]
        
        # Scalability score (lower scaling exponent is better)
        scalability_score = 1.0 / (1.0 + abs(scaling_exponent))
        
        return {
            'scaling_exponent': float(scaling_exponent),
            'scalability_score': float(scalability_score),
            'dimension_results': dimension_results
        }
    
    def _find_convergence_iteration(self, fitness_history: np.ndarray, 
                                  tolerance: float = 1e-6) -> Optional[int]:
        """Find the iteration where convergence occurred"""
        if len(fitness_history) < 10:
            return None
        
        # Look for stabilization in fitness
        window_size = min(10, len(fitness_history) // 4)
        
        for i in range(window_size, len(fitness_history)):
            window = fitness_history[i-window_size:i]
            if np.std(window) < tolerance:
                return i - window_size
        
        return None
    
    def evaluate_swarm_algorithm(self, swarm: SwarmOptimizer, 
                               objective_function: Callable,
                               num_runs: int = 10) -> Dict[str, Any]:
        """Comprehensive evaluation of a swarm algorithm"""
        run_results = []
        run_histories = []
        run_times = []
        
        for run in range(num_runs):
            start_time = time.time()
            
            # Reset swarm
            swarm.iteration = 0
            swarm.convergence_history = []
            swarm.diversity_history = []
            
            # Run optimization
            result = swarm.optimize(objective_function)
            
            execution_time = time.time() - start_time
            
            run_results.append(result['best_fitness'])
            run_histories.append(result['convergence_history'])
            run_times.append(execution_time)
        
        # Calculate comprehensive metrics
        convergence_metrics = self.calculate_convergence_metrics(
            np.mean(run_histories, axis=0).tolist()
        )
        
        robustness_metrics = self.calculate_robustness_metrics(run_results)
        
        efficiency_metrics = self.calculate_efficiency_metrics(
            np.mean(run_times),
            swarm.statistics.get('evaluations', 0),
            np.mean(run_results)
        )
        
        # Get final population for diversity analysis
        if hasattr(swarm, 'agents'):
            final_positions = [agent.position for agent in swarm.agents]
            diversity_metrics = self.calculate_diversity_metrics(final_positions)
        else:
            diversity_metrics = {}
        
        return {
            'algorithm_name': swarm.__class__.__name__,
            'num_runs': num_runs,
            'convergence_metrics': convergence_metrics,
            'robustness_metrics': robustness_metrics,
            'efficiency_metrics': efficiency_metrics,
            'diversity_metrics': diversity_metrics,
            'run_results': run_results,
            'run_histories': run_histories,
            'run_times': run_times
        }
    
    def benchmark_algorithms(self, algorithms: List[SwarmOptimizer],
                           benchmark_functions: List[Tuple[str, Callable]],
                           num_runs: int = 10) -> List[BenchmarkResult]:
        """Benchmark multiple algorithms on multiple test functions"""
        results = []
        
        for algorithm in algorithms:
            for func_name, func in benchmark_functions:
                print(f"Benchmarking {algorithm.__class__.__name__} on {func_name}...")
                
                evaluation = self.evaluate_swarm_algorithm(algorithm, func, num_runs)
                
                # Create benchmark result
                result = BenchmarkResult(
                    algorithm_name=algorithm.__class__.__name__,
                    problem_name=func_name,
                    best_fitness=min(evaluation['run_results']),
                    mean_fitness=evaluation['robustness_metrics']['mean_result'],
                    std_fitness=evaluation['robustness_metrics']['std_result'],
                    convergence_iteration=evaluation['convergence_metrics'].get('convergence_iteration'),
                    execution_time=evaluation['efficiency_metrics']['execution_time'],
                    success_rate=evaluation['robustness_metrics']['success_rate'],
                    diversity_score=evaluation['diversity_metrics'].get('normalized_diversity', 0.0),
                    efficiency_score=evaluation['efficiency_metrics']['quality_per_time']
                )
                
                results.append(result)
                self.benchmark_results.append(result)
        
        return results
    
    def generate_performance_report(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        if not results:
            return {}
        
        # Group results by algorithm
        algorithm_results = {}
        for result in results:
            if result.algorithm_name not in algorithm_results:
                algorithm_results[result.algorithm_name] = []
            algorithm_results[result.algorithm_name].append(result)
        
        # Calculate summary statistics
        summary = {}
        for algo_name, algo_results in algorithm_results.items():
            fitness_values = [r.best_fitness for r in algo_results]
            times = [r.execution_time for r in algo_results]
            success_rates = [r.success_rate for r in algo_results]
            
            summary[algo_name] = {
                'mean_best_fitness': float(np.mean(fitness_values)),
                'std_best_fitness': float(np.std(fitness_values)),
                'mean_execution_time': float(np.mean(times)),
                'mean_success_rate': float(np.mean(success_rates)),
                'num_problems': len(algo_results),
                'rank_by_fitness': 0,  # Will be calculated below
                'rank_by_time': 0,     # Will be calculated below
                'overall_score': 0.0   # Will be calculated below
            }
        
        # Calculate rankings
        algo_names = list(summary.keys())
        
        # Rank by fitness (lower is better)
        fitness_ranking = sorted(algo_names, key=lambda x: summary[x]['mean_best_fitness'])
        for rank, algo in enumerate(fitness_ranking):
            summary[algo]['rank_by_fitness'] = rank + 1
        
        # Rank by time (lower is better)
        time_ranking = sorted(algo_names, key=lambda x: summary[x]['mean_execution_time'])
        for rank, algo in enumerate(time_ranking):
            summary[algo]['rank_by_time'] = rank + 1
        
        # Calculate overall score (lower is better)
        for algo in algo_names:
            fitness_rank = summary[algo]['rank_by_fitness']
            time_rank = summary[algo]['rank_by_time']
            success_rate = summary[algo]['mean_success_rate']
            
            # Weighted combination (fitness 50%, time 30%, success rate 20%)
            overall_score = (0.5 * fitness_rank + 
                           0.3 * time_rank + 
                           0.2 * (len(algo_names) + 1 - success_rate * len(algo_names)))
            summary[algo]['overall_score'] = float(overall_score)
        
        return {
            'summary': summary,
            'detailed_results': [
                {
                    'algorithm': r.algorithm_name,
                    'problem': r.problem_name,
                    'best_fitness': r.best_fitness,
                    'mean_fitness': r.mean_fitness,
                    'execution_time': r.execution_time,
                    'success_rate': r.success_rate
                }
                for r in results
            ],
            'best_algorithm_by_fitness': min(algo_names, key=lambda x: summary[x]['mean_best_fitness']),
            'best_algorithm_by_time': min(algo_names, key=lambda x: summary[x]['mean_execution_time']),
            'best_algorithm_overall': min(algo_names, key=lambda x: summary[x]['overall_score'])
        }
    
    def export_results(self, results: List[BenchmarkResult], filename: str) -> None:
        """Export benchmark results to JSON file"""
        export_data = {
            'timestamp': time.time(),
            'results': [
                {
                    'algorithm_name': r.algorithm_name,
                    'problem_name': r.problem_name,
                    'best_fitness': r.best_fitness,
                    'mean_fitness': r.mean_fitness,
                    'std_fitness': r.std_fitness,
                    'convergence_iteration': r.convergence_iteration,
                    'execution_time': r.execution_time,
                    'success_rate': r.success_rate,
                    'diversity_score': r.diversity_score,
                    'efficiency_score': r.efficiency_score
                }
                for r in results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def load_results(self, filename: str) -> List[BenchmarkResult]:
        """Load benchmark results from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        results = []
        for result_data in data['results']:
            result = BenchmarkResult(**result_data)
            results.append(result)
        
        return results


# Common benchmark functions
def sphere_function(x: np.ndarray) -> float:
    """Sphere function: f(x) = sum(x^2)"""
    return np.sum(x**2)


def rastrigin_function(x: np.ndarray) -> float:
    """Rastrigin function: f(x) = An + sum(x^2 - A*cos(2*pi*x))"""
    A = 10
    n = len(x)
    return A * n + np.sum(x**2 - A * np.cos(2 * np.pi * x))


def rosenbrock_function(x: np.ndarray) -> float:
    """Rosenbrock function: f(x) = sum(100*(x[i+1] - x[i]^2)^2 + (1 - x[i])^2)"""
    return np.sum(100 * (x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2)


def ackley_function(x: np.ndarray) -> float:
    """Ackley function"""
    a, b, c = 20, 0.2, 2 * np.pi
    n = len(x)
    
    sum1 = np.sum(x**2)
    sum2 = np.sum(np.cos(c * x))
    
    return -a * np.exp(-b * np.sqrt(sum1 / n)) - np.exp(sum2 / n) + a + np.exp(1)


def griewank_function(x: np.ndarray) -> float:
    """Griewank function"""
    sum_term = np.sum(x**2) / 4000
    prod_term = np.prod(np.cos(x / np.sqrt(np.arange(1, len(x) + 1))))
    return sum_term - prod_term + 1


# Benchmark function registry
BENCHMARK_FUNCTIONS = [
    ('sphere', sphere_function),
    ('rastrigin', rastrigin_function),
    ('rosenbrock', rosenbrock_function),
    ('ackley', ackley_function),
    ('griewank', griewank_function)
]