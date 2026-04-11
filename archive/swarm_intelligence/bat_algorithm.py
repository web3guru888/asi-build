"""
Bat Algorithm (BA)

This module implements the Bat Algorithm, inspired by the echolocation
behavior of microbats. It includes frequency tuning, loudness, and
pulse emission rate adjustments.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


@dataclass
class BAParameters(SwarmParameters):
    """Bat Algorithm specific parameters"""
    # Echolocation parameters
    freq_min: float = 0.0           # Minimum frequency
    freq_max: float = 2.0           # Maximum frequency
    loudness: float = 0.5           # Initial loudness
    pulse_rate: float = 0.5         # Initial pulse emission rate
    
    # Control parameters
    alpha: float = 0.9              # Loudness decay factor
    gamma: float = 0.9              # Pulse rate increase factor
    
    # Advanced parameters
    local_search_prob: float = 0.5  # Local search probability
    adaptive_frequency: bool = True  # Adaptive frequency tuning


class Bat(SwarmAgent):
    """Individual bat agent with echolocation capabilities"""
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Echolocation properties
        self.frequency = 0.0
        self.loudness = 0.5
        self.pulse_rate = 0.5
        self.pulse_rate_initial = 0.5
        
        # Bat-specific properties
        self.properties.update({
            'hearing_sensitivity': np.random.uniform(0.7, 1.0),
            'flight_agility': np.random.uniform(0.5, 1.0),
            'echolocation_accuracy': np.random.uniform(0.6, 1.0)
        })
    
    def update_position(self, best_position: Optional[np.ndarray] = None,
                       freq_min: float = 0.0, freq_max: float = 2.0,
                       **kwargs) -> None:
        """Update bat position using echolocation"""
        if best_position is None:
            # Random flight
            self.position += 0.1 * np.random.randn(self.dimension)
        else:
            # Update frequency and velocity
            beta = np.random.random()
            self.frequency = freq_min + (freq_max - freq_min) * beta
            
            # Update velocity
            self.velocity += (self.position - best_position) * self.frequency
            
            # Update position
            self.position += self.velocity
        
        self.clip_to_bounds()
        self.age += 1
    
    def update_velocity(self, **kwargs) -> None:
        """Update bat velocity based on echolocation"""
        # Velocity affected by flight agility
        agility = self.properties['flight_agility']
        self.velocity *= agility
    
    def local_search(self, best_position: np.ndarray, loudness: float) -> None:
        """Perform local search around best solution"""
        if np.random.random() > self.pulse_rate:
            # Generate local solution
            epsilon = np.random.uniform(-1, 1, self.dimension)
            self.position = best_position + epsilon * loudness
            self.clip_to_bounds()
    
    def update_loudness_and_pulse_rate(self, alpha: float, gamma: float, iteration: int) -> None:
        """Update loudness and pulse emission rate"""
        # Update loudness (decreases over time)
        self.loudness *= alpha
        
        # Update pulse rate (increases over time)
        self.pulse_rate = self.pulse_rate_initial * (1 - np.exp(-gamma * iteration))


class BatAlgorithm(SwarmOptimizer):
    """Bat Algorithm optimization implementation"""
    
    def __init__(self, parameters: BAParameters):
        super().__init__(parameters)
        self.ba_params = parameters
        
        # Algorithm state
        self.current_loudness = parameters.loudness
        
        # Performance tracking
        self.echolocation_success = []
        self.local_search_applications = []
    
    def initialize_population(self) -> None:
        """Initialize bat colony"""
        self.agents = [
            Bat(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Initialize bat parameters
        for bat in self.agents:
            bat.loudness = self.ba_params.loudness
            bat.pulse_rate = self.ba_params.pulse_rate
            bat.pulse_rate_initial = self.ba_params.pulse_rate
        
        self.logger.info(f"Initialized {len(self.agents)} bats")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all bats in the colony"""
        # Evaluate fitness
        for bat in self.agents:
            bat.evaluate_fitness(objective_function)
        
        # Find best bat
        best_bat = min(self.agents, key=lambda b: b.fitness)
        
        local_searches = 0
        successful_echolocations = 0
        
        # Update bat positions
        for bat in self.agents:
            old_fitness = bat.fitness
            
            # Generate new solution by flying
            bat.update_position(
                best_position=best_bat.position,
                freq_min=self.ba_params.freq_min,
                freq_max=self.ba_params.freq_max
            )
            
            # Evaluate new position
            bat.evaluate_fitness(objective_function)
            
            # Local search
            if (np.random.random() < self.ba_params.local_search_prob and
                np.random.random() > bat.pulse_rate):
                bat.local_search(best_bat.position, bat.loudness)
                bat.evaluate_fitness(objective_function)
                local_searches += 1
            
            # Accept new solution if better and random condition
            if (bat.fitness < old_fitness and 
                np.random.random() < bat.loudness):
                successful_echolocations += 1
                
                # Update loudness and pulse rate
                bat.update_loudness_and_pulse_rate(
                    self.ba_params.alpha, 
                    self.ba_params.gamma, 
                    self.iteration
                )
        
        # Record performance metrics
        self.echolocation_success.append(successful_echolocations)
        self.local_search_applications.append(local_searches)


# Factory function
def create_bat_algorithm(population_size: int = 50,
                        max_iterations: int = 1000,
                        loudness: float = 0.5,
                        pulse_rate: float = 0.5,
                        dimension: int = 2,
                        bounds: Tuple[float, float] = (-10.0, 10.0)) -> BatAlgorithm:
    """Create a Bat Algorithm optimizer"""
    params = BAParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        loudness=loudness,
        pulse_rate=pulse_rate
    )
    return BatAlgorithm(params)