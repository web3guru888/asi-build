"""
Cuckoo Search (CS) Algorithm

This module implements the Cuckoo Search algorithm, inspired by the
obligation brood parasitism of some cuckoo species and the Levy flight
behavior of some birds and fruit flies.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


@dataclass
class CSParameters(SwarmParameters):
    """Cuckoo Search specific parameters"""
    discovery_rate: float = 0.25        # Probability of discovery
    levy_alpha: float = 1.5             # Levy flight parameter
    step_size_scaling: float = 0.01     # Step size scaling factor
    
    # Advanced parameters
    adaptive_discovery: bool = True      # Adaptive discovery rate
    elite_selection: bool = True         # Elite nest selection
    local_search: bool = True           # Local search enhancement


class Cuckoo(SwarmAgent):
    """Individual cuckoo agent representing a nest/solution"""
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        self.nest_quality = 0.0
        self.discovery_probability = 0.0
        
        # Cuckoo-specific properties
        self.properties.update({
            'mimicry_skill': np.random.random(),
            'flight_efficiency': np.random.uniform(0.5, 1.0),
            'nest_building_ability': np.random.random()
        })
    
    def update_position(self, best_nest: Optional[np.ndarray] = None,
                       levy_alpha: float = 1.5, 
                       step_size: float = 0.01, **kwargs) -> None:
        """Update cuckoo position using Levy flight"""
        if best_nest is not None:
            # Levy flight towards best nest
            levy_step = self._levy_flight(levy_alpha)
            direction = best_nest - self.position
            
            self.position += step_size * levy_step * direction
        else:
            # Random Levy flight
            levy_step = self._levy_flight(levy_alpha)
            self.position += step_size * levy_step
        
        self.clip_to_bounds()
        self.age += 1
    
    def update_velocity(self, **kwargs) -> None:
        """Update cuckoo velocity (flight dynamics)"""
        efficiency = self.properties['flight_efficiency']
        self.velocity *= efficiency
        
        # Add flight variation
        variation = 0.1 * np.random.randn(self.dimension)
        self.velocity += variation
    
    def _levy_flight(self, alpha: float = 1.5) -> np.ndarray:
        """Generate Levy flight step"""
        # Calculate sigma for Levy distribution
        num = np.math.gamma(1 + alpha) * np.sin(np.pi * alpha / 2)
        den = np.math.gamma((1 + alpha) / 2) * alpha * (2 ** ((alpha - 1) / 2))
        sigma_u = (num / den) ** (1 / alpha)
        
        # Generate Levy flight
        u = np.random.normal(0, sigma_u, self.dimension)
        v = np.random.normal(0, 1, self.dimension)
        
        step = u / (np.abs(v) ** (1 / alpha))
        return step


class CuckooSearch(SwarmOptimizer):
    """Cuckoo Search optimization algorithm implementation"""
    
    def __init__(self, parameters: CSParameters):
        super().__init__(parameters)
        self.cs_params = parameters
        self.current_discovery_rate = parameters.discovery_rate
        
        # Performance tracking
        self.discovery_events = []
        self.levy_flight_statistics = []
    
    def initialize_population(self) -> None:
        """Initialize cuckoo population"""
        self.agents = [
            Cuckoo(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        self.logger.info(f"Initialized {len(self.agents)} cuckoos")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all cuckoos"""
        # Evaluate fitness
        for cuckoo in self.agents:
            cuckoo.evaluate_fitness(objective_function)
        
        # Get best nest
        best_cuckoo = min(self.agents, key=lambda c: c.fitness)
        
        # Generate new solutions via Levy flights
        for cuckoo in self.agents:
            if cuckoo != best_cuckoo:
                cuckoo.update_position(
                    best_nest=best_cuckoo.position,
                    levy_alpha=self.cs_params.levy_alpha,
                    step_size=self.cs_params.step_size_scaling
                )
                cuckoo.evaluate_fitness(objective_function)
        
        # Abandon some nests (discovery)
        self._abandon_nests(objective_function)
        
        # Adaptive parameter adjustment
        if self.cs_params.adaptive_discovery:
            self._adapt_discovery_rate()
    
    def _abandon_nests(self, objective_function: Callable) -> None:
        """Abandon a fraction of worst nests"""
        num_abandon = int(self.current_discovery_rate * len(self.agents))
        
        if num_abandon > 0:
            # Sort by fitness (worst first)
            sorted_cuckoos = sorted(self.agents, key=lambda c: c.fitness, reverse=True)
            
            # Abandon worst nests
            for i in range(num_abandon):
                if i < len(sorted_cuckoos):
                    cuckoo = sorted_cuckoos[i]
                    # Random new position
                    cuckoo.position = np.random.uniform(
                        self.params.bounds[0], 
                        self.params.bounds[1], 
                        self.params.dimension
                    )
                    cuckoo.evaluate_fitness(objective_function)
            
            self.discovery_events.append(num_abandon)
    
    def _adapt_discovery_rate(self) -> None:
        """Adaptively adjust discovery rate"""
        if len(self.convergence_history) > 10:
            recent_improvement = (
                self.convergence_history[-10] - self.convergence_history[-1]
            )
            
            if recent_improvement < 1e-6:
                # Poor convergence - increase discovery
                self.current_discovery_rate = min(0.5, self.current_discovery_rate * 1.1)
            else:
                # Good convergence - maintain or decrease discovery
                self.current_discovery_rate = max(0.1, self.current_discovery_rate * 0.95)


# Factory function
def create_cuckoo_search(population_size: int = 50,
                        max_iterations: int = 1000,
                        discovery_rate: float = 0.25,
                        dimension: int = 2,
                        bounds: Tuple[float, float] = (-10.0, 10.0)) -> CuckooSearch:
    """Create a Cuckoo Search optimizer"""
    params = CSParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        discovery_rate=discovery_rate
    )
    return CuckooSearch(params)