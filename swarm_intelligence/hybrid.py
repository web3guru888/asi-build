"""
Hybrid Swarm Intelligence Algorithms

This module implements hybrid algorithms that combine multiple
swarm intelligence approaches for enhanced performance.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .base import SwarmOptimizer, SwarmParameters, SwarmAgent


class HybridStrategy(Enum):
    """Hybrid combination strategies"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    HIERARCHICAL = "hierarchical"


@dataclass
class HybridParameters(SwarmParameters):
    """Hybrid algorithm parameters"""
    algorithms: List[str] = None
    strategy: HybridStrategy = HybridStrategy.ADAPTIVE
    switching_criterion: str = "performance"
    adaptation_interval: int = 10


class HybridSwarmAgent(SwarmAgent):
    """Agent that can use multiple behavioral strategies"""
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        self.current_strategy = 0
        self.strategy_performance = {}
    
    def update_position(self, **kwargs) -> None:
        """Update position using current strategy"""
        strategy = kwargs.get('strategy', 'pso')
        
        if strategy == 'pso':
            self._pso_update(**kwargs)
        elif strategy == 'aco':
            self._aco_update(**kwargs)
        elif strategy == 'firefly':
            self._firefly_update(**kwargs)
        else:
            self._default_update(**kwargs)
        
        self.clip_to_bounds()
        self.age += 1
    
    def _pso_update(self, **kwargs):
        """PSO-style position update"""
        global_best = kwargs.get('global_best_position')
        c1, c2 = kwargs.get('c1', 2.0), kwargs.get('c2', 2.0)
        w = kwargs.get('inertia', 0.7)
        
        if global_best is not None:
            r1, r2 = np.random.random(self.dimension), np.random.random(self.dimension)
            cognitive = c1 * r1 * (self.best_position - self.position)
            social = c2 * r2 * (global_best - self.position)
            self.velocity = w * self.velocity + cognitive + social
            self.position += self.velocity
    
    def _aco_update(self, **kwargs):
        """ACO-style position update"""
        best_position = kwargs.get('global_best_position')
        if best_position is not None:
            direction = best_position - self.position
            step_size = kwargs.get('step_size', 0.1)
            self.position += step_size * direction + 0.1 * np.random.randn(self.dimension)
    
    def _firefly_update(self, **kwargs):
        """Firefly-style position update"""
        attractors = kwargs.get('attractors', [])
        alpha = kwargs.get('alpha', 0.2)
        
        if attractors:
            for attractor in attractors:
                distance = np.linalg.norm(attractor - self.position)
                attractiveness = np.exp(-distance)
                direction = attractor - self.position
                self.position += attractiveness * direction
        
        self.position += alpha * np.random.randn(self.dimension)
    
    def _default_update(self, **kwargs):
        """Default random update"""
        self.position += 0.1 * np.random.randn(self.dimension)


class HybridSwarmOptimizer(SwarmOptimizer):
    """Hybrid swarm optimizer combining multiple algorithms"""
    
    def __init__(self, parameters: HybridParameters):
        super().__init__(parameters)
        self.hybrid_params = parameters
        self.current_algorithms = parameters.algorithms or ['pso', 'aco', 'firefly']
        self.algorithm_performance = {algo: [] for algo in self.current_algorithms}
        self.current_strategy = self.current_algorithms[0]
        
    def initialize_population(self):
        """Initialize hybrid population"""
        self.agents = [
            HybridSwarmAgent(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
    
    def update_agents(self, objective_function: Callable):
        """Update agents using hybrid strategy"""
        if self.hybrid_params.strategy == HybridStrategy.ADAPTIVE:
            self._adaptive_update(objective_function)
        elif self.hybrid_params.strategy == HybridStrategy.SEQUENTIAL:
            self._sequential_update(objective_function)
        elif self.hybrid_params.strategy == HybridStrategy.PARALLEL:
            self._parallel_update(objective_function)
        else:
            self._hierarchical_update(objective_function)
    
    def _adaptive_update(self, objective_function: Callable):
        """Adaptive strategy selection"""
        # Evaluate current strategy performance
        old_fitness = self.global_best_fitness
        
        # Update with current strategy
        for agent in self.agents:
            agent.update_position(
                strategy=self.current_strategy,
                global_best_position=self.global_best_position,
                alpha=0.2, step_size=0.1, c1=2.0, c2=2.0, inertia=0.7
            )
            agent.evaluate_fitness(objective_function)
        
        # Record performance
        improvement = old_fitness - self.global_best_fitness
        self.algorithm_performance[self.current_strategy].append(improvement)
        
        # Switch strategy if needed
        if self.iteration % self.hybrid_params.adaptation_interval == 0:
            self._select_best_strategy()
    
    def _select_best_strategy(self):
        """Select best performing strategy"""
        strategy_scores = {}
        for algo, performance in self.algorithm_performance.items():
            if performance:
                strategy_scores[algo] = np.mean(performance[-10:])  # Last 10 performances
            else:
                strategy_scores[algo] = 0
        
        self.current_strategy = max(strategy_scores, key=strategy_scores.get)


# Factory function
def create_hybrid_swarm_optimizer(algorithms: List[str] = None,
                                population_size: int = 50,
                                max_iterations: int = 1000,
                                dimension: int = 2,
                                bounds: Tuple[float, float] = (-10.0, 10.0)) -> HybridSwarmOptimizer:
    """Create hybrid swarm optimizer"""
    if algorithms is None:
        algorithms = ['pso', 'aco', 'firefly']
    
    params = HybridParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        algorithms=algorithms
    )
    
    return HybridSwarmOptimizer(params)