"""
Bacterial Foraging Optimization (BFO) Algorithm

This module implements the Bacterial Foraging Optimization algorithm,
inspired by the foraging behavior of E. coli bacteria. It includes
chemotaxis, swarming, reproduction, and elimination-dispersal operations.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class BacterialState(Enum):
    """States of bacterial behavior"""
    FORAGING = "foraging"
    SWARMING = "swarming"
    REPRODUCING = "reproducing"
    DISPERSED = "dispersed"


@dataclass
class BFOParameters(SwarmParameters):
    """Bacterial Foraging Optimization specific parameters"""
    # Chemotaxis parameters
    step_size: float = 0.1          # Chemotactic step size
    num_chemotactic_steps: int = 4   # Number of chemotactic steps
    swim_length: int = 4             # Maximum swim length
    
    # Swarming parameters
    d_attract: float = 0.1           # Depth of attractant
    w_attract: float = 0.2           # Width of attractant
    h_repellant: float = 0.1         # Height of repellant
    w_repellant: float = 10.0        # Width of repellant
    
    # Reproduction parameters
    num_reproduction_steps: int = 4   # Number of reproduction steps
    
    # Elimination-dispersal parameters
    num_elimination_dispersal_events: int = 2  # Number of elimination events
    elimination_probability: float = 0.25      # Probability of elimination
    
    # Advanced parameters
    adaptive_step_size: bool = True    # Adaptive step size
    nutrient_concentration: bool = True # Consider nutrient concentration
    cell_to_cell_signaling: bool = True # Enable cell communication


class Bacterium(SwarmAgent):
    """
    Individual bacterium agent
    
    Each bacterium can perform chemotaxis, swarming, reproduction,
    and elimination-dispersal behaviors.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Bacterial state
        self.state = BacterialState.FORAGING
        self.health = 100.0
        self.nutrient_accumulated = 0.0
        self.swim_length = 0
        
        # Chemotaxis properties
        self.tumble_direction = np.random.randn(dimension)
        self.tumble_direction /= np.linalg.norm(self.tumble_direction)
        self.last_fitness = float('inf')
        
        # Communication properties
        self.signal_molecules = 0.0
        self.communication_range = 2.0
        self.neighbors = []
        
        # Biological properties
        self.generation = 0
        self.reproduction_success = 0
        self.elimination_resistance = np.random.random()
        
        # Bacterial behavior properties
        self.properties.update({
            'motility': np.random.uniform(0.5, 1.0),
            'chemotaxis_sensitivity': np.random.uniform(0.5, 1.0),
            'reproduction_rate': np.random.uniform(0.3, 0.8),
            'stress_resistance': np.random.uniform(0.2, 0.9),
            'communication_ability': np.random.random()
        })
    
    def update_position(self, step_size: float = 0.1, 
                       nutrient_field: Optional[np.ndarray] = None,
                       signal_field: Optional[np.ndarray] = None,
                       **kwargs) -> None:
        """
        Update bacterium position through chemotaxis
        
        Args:
            step_size: Chemotactic step size
            nutrient_field: Nutrient concentration field
            signal_field: Chemical signal field
        """
        # Perform chemotaxis based on current state
        if self.state == BacterialState.FORAGING:
            self._chemotaxis_movement(step_size, nutrient_field)
        elif self.state == BacterialState.SWARMING:
            self._swarming_movement(step_size, signal_field)
        elif self.state == BacterialState.REPRODUCING:
            self._reproduction_movement(step_size)
        else:  # DISPERSED
            self._dispersal_movement()
        
        self.clip_to_bounds()
        self.age += 1
    
    def update_velocity(self, **kwargs) -> None:
        """Update bacterium velocity (tumbling direction)"""
        tumble_probability = kwargs.get('tumble_probability', 0.1)
        
        # Random tumbling
        if np.random.random() < tumble_probability:
            self.tumble_direction = np.random.randn(self.dimension)
            self.tumble_direction /= np.linalg.norm(self.tumble_direction)
            self.swim_length = 0
    
    def _chemotaxis_movement(self, step_size: float, 
                           nutrient_field: Optional[np.ndarray]) -> None:
        """Perform chemotaxis (movement toward nutrients)"""
        # Calculate gradient if nutrient field is provided
        if nutrient_field is not None:
            gradient = self._calculate_nutrient_gradient(nutrient_field)
            if np.linalg.norm(gradient) > 0:
                self.tumble_direction = gradient / np.linalg.norm(gradient)
        
        # Move in tumble direction
        new_position = self.position + step_size * self.tumble_direction
        
        # Evaluate improvement
        old_position = self.position.copy()
        self.position = new_position
        
        # Check if movement is beneficial (simplified)
        current_nutrient = self._evaluate_nutrient_concentration()
        if current_nutrient > self.nutrient_accumulated:
            # Good movement - continue swimming
            self.swim_length += 1
            self.nutrient_accumulated = current_nutrient
        else:
            # Bad movement - tumble
            self.position = old_position
            self._tumble()
    
    def _swarming_movement(self, step_size: float, 
                         signal_field: Optional[np.ndarray]) -> None:
        """Perform swarming movement based on cell signaling"""
        if not self.neighbors:
            # No neighbors - random movement
            self.position += step_size * np.random.randn(self.dimension)
            return
        
        # Calculate swarm center
        neighbor_positions = np.array([n.position for n in self.neighbors])
        swarm_center = np.mean(neighbor_positions, axis=0)
        
        # Move toward swarm center with some randomness
        direction = swarm_center - self.position
        if np.linalg.norm(direction) > 0:
            direction /= np.linalg.norm(direction)
        
        random_component = 0.3 * np.random.randn(self.dimension)
        self.position += step_size * (0.7 * direction + random_component)
    
    def _reproduction_movement(self, step_size: float) -> None:
        """Movement during reproduction phase"""
        # Limited movement during reproduction
        small_step = step_size * 0.1
        self.position += small_step * np.random.randn(self.dimension)
    
    def _dispersal_movement(self) -> None:
        """Random dispersal movement"""
        # Random repositioning within bounds
        self.position = np.random.uniform(self.bounds[0], self.bounds[1], self.dimension)
        self.state = BacterialState.FORAGING
        self.health = 100.0
        self.nutrient_accumulated = 0.0
    
    def _tumble(self) -> None:
        """Perform tumbling (random reorientation)"""
        self.tumble_direction = np.random.randn(self.dimension)
        self.tumble_direction /= np.linalg.norm(self.tumble_direction)
        self.swim_length = 0
    
    def _calculate_nutrient_gradient(self, nutrient_field: np.ndarray) -> np.ndarray:
        """Calculate nutrient gradient at current position"""
        # Simplified gradient calculation
        gradient = np.zeros(self.dimension)
        epsilon = 0.01
        
        for i in range(self.dimension):
            pos_forward = self.position.copy()
            pos_backward = self.position.copy()
            
            pos_forward[i] += epsilon
            pos_backward[i] -= epsilon
            
            # Evaluate nutrient at forward and backward positions
            nutrient_forward = self._evaluate_position_nutrient(pos_forward)
            nutrient_backward = self._evaluate_position_nutrient(pos_backward)
            
            gradient[i] = (nutrient_forward - nutrient_backward) / (2 * epsilon)
        
        return gradient
    
    def _evaluate_nutrient_concentration(self) -> float:
        """Evaluate nutrient concentration at current position"""
        return self._evaluate_position_nutrient(self.position)
    
    def _evaluate_position_nutrient(self, position: np.ndarray) -> float:
        """Evaluate nutrient concentration at given position"""
        # Simplified nutrient model - higher concentration near origin
        distance_from_origin = np.linalg.norm(position)
        return 1.0 / (1.0 + distance_from_origin)
    
    def reproduce(self) -> 'Bacterium':
        """Create offspring bacterium"""
        offspring = Bacterium(self.dimension, self.bounds)
        
        # Inherit some properties with mutation
        mutation_rate = 0.1
        for key, value in self.properties.items():
            if isinstance(value, (int, float)):
                mutation = np.random.normal(0, mutation_rate * value)
                offspring.properties[key] = np.clip(value + mutation, 0, 1)
        
        # Position near parent with some variation
        variation = np.random.normal(0, 0.1, self.dimension)
        offspring.position = self.position + variation
        offspring.clip_to_bounds()
        
        offspring.generation = self.generation + 1
        return offspring
    
    def should_be_eliminated(self, elimination_probability: float) -> bool:
        """Check if bacterium should be eliminated"""
        # Elimination probability modified by stress resistance
        actual_probability = elimination_probability * (1 - self.elimination_resistance)
        return np.random.random() < actual_probability
    
    def release_signal_molecule(self) -> float:
        """Release chemical signal for communication"""
        signal_strength = self.health * self.properties['communication_ability']
        self.signal_molecules += signal_strength
        return signal_strength
    
    def detect_signal_molecules(self, total_signal: float) -> None:
        """Detect and respond to signal molecules"""
        if total_signal > 0.5:  # Threshold for swarming
            self.state = BacterialState.SWARMING
        else:
            self.state = BacterialState.FORAGING


class BacterialForagingOptimizer(SwarmOptimizer):
    """
    Bacterial Foraging Optimization algorithm implementation
    
    Implements the complete BFO algorithm with chemotaxis, swarming,
    reproduction, and elimination-dispersal operations.
    """
    
    def __init__(self, parameters: BFOParameters):
        super().__init__(parameters)
        self.bfo_params = parameters
        
        # Algorithm state counters
        self.chemotaxis_step = 0
        self.reproduction_step = 0
        self.elimination_step = 0
        
        # Population management
        self.eliminated_bacteria = []
        self.offspring_bacteria = []
        
        # Environmental factors
        self.nutrient_field = None
        self.signal_field = None
        
        # Performance tracking
        self.chemotaxis_success_rate = []
        self.reproduction_events = []
        self.elimination_events = []
        self.swarming_activity = []
        
        # Adaptive parameters
        self.current_step_size = parameters.step_size
    
    def initialize_population(self) -> None:
        """Initialize bacterial population"""
        self.agents = [
            Bacterium(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Initialize environmental fields
        if self.bfo_params.nutrient_concentration:
            self._initialize_nutrient_field()
        
        self.logger.info(f"Initialized {len(self.agents)} bacteria")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all bacteria through BFO operations"""
        # Chemotaxis loop
        self._chemotaxis_phase(objective_function)
        
        # Swarming
        if self.bfo_params.cell_to_cell_signaling:
            self._swarming_phase()
        
        # Reproduction
        if (self.chemotaxis_step % 
            (self.bfo_params.num_chemotactic_steps * self.bfo_params.num_reproduction_steps) == 0):
            self._reproduction_phase(objective_function)
        
        # Elimination-dispersal
        if (self.reproduction_step % self.bfo_params.num_elimination_dispersal_events == 0):
            self._elimination_dispersal_phase()
        
        # Adaptive parameter adjustment
        if self.bfo_params.adaptive_step_size:
            self._adapt_step_size()
        
        # Record performance metrics
        self._record_bfo_metrics()
        
        self.chemotaxis_step += 1
    
    def _chemotaxis_phase(self, objective_function: Callable) -> None:
        """Chemotaxis phase - bacteria search for nutrients"""
        successful_moves = 0
        
        for bacterium in self.agents:
            if bacterium.state == BacterialState.REPRODUCING:
                continue
            
            # Perform chemotactic steps
            for _ in range(self.bfo_params.num_chemotactic_steps):
                old_fitness = bacterium.fitness
                
                # Update position
                bacterium.update_position(
                    step_size=self.current_step_size,
                    nutrient_field=self.nutrient_field
                )
                
                # Evaluate new position
                bacterium.evaluate_fitness(objective_function)
                
                # Check improvement
                if bacterium.fitness < old_fitness:
                    successful_moves += 1
                    # Continue swimming
                    if bacterium.swim_length < self.bfo_params.swim_length:
                        continue
                else:
                    # Tumble
                    bacterium._tumble()
                    break
        
        # Record chemotaxis success rate
        total_moves = len(self.agents) * self.bfo_params.num_chemotactic_steps
        success_rate = successful_moves / max(total_moves, 1)
        self.chemotaxis_success_rate.append(success_rate)
    
    def _swarming_phase(self) -> None:
        """Swarming phase - bacteria communicate and form groups"""
        # Calculate signal field
        self._update_signal_field()
        
        # Update neighborhoods
        self._update_bacterial_neighborhoods()
        
        # Process swarming behavior
        swarming_bacteria = 0
        for bacterium in self.agents:
            # Release signal molecules
            signal = bacterium.release_signal_molecule()
            
            # Detect surrounding signals
            total_signal = self._calculate_local_signal(bacterium)
            bacterium.detect_signal_molecules(total_signal)
            
            if bacterium.state == BacterialState.SWARMING:
                swarming_bacteria += 1
        
        self.swarming_activity.append(swarming_bacteria / len(self.agents))
    
    def _reproduction_phase(self, objective_function: Callable) -> None:
        """Reproduction phase - healthiest bacteria reproduce"""
        # Sort bacteria by health (fitness)
        sorted_bacteria = sorted(self.agents, key=lambda b: b.fitness)
        
        # Select top 50% for reproduction
        reproduction_count = len(self.agents) // 2
        parents = sorted_bacteria[:reproduction_count]
        
        # Create offspring
        offspring = []
        for parent in parents:
            parent.state = BacterialState.REPRODUCING
            child = parent.reproduce()
            offspring.append(child)
        
        # Replace worst bacteria with offspring
        worst_bacteria = sorted_bacteria[reproduction_count:]
        for i, child in enumerate(offspring):
            if i < len(worst_bacteria):
                # Replace worst bacterium
                worst_bacteria[i].position = child.position.copy()
                worst_bacteria[i].properties = child.properties.copy()
                worst_bacteria[i].generation = child.generation
                worst_bacteria[i].state = BacterialState.FORAGING
        
        # Record reproduction event
        self.reproduction_events.append({
            'iteration': self.iteration,
            'parents': len(parents),
            'offspring': len(offspring),
            'average_parent_fitness': np.mean([p.fitness for p in parents])
        })
        
        self.reproduction_step += 1
    
    def _elimination_dispersal_phase(self) -> None:
        """Elimination-dispersal phase - random elimination and dispersal"""
        eliminated_count = 0
        
        for bacterium in self.agents:
            if bacterium.should_be_eliminated(self.bfo_params.elimination_probability):
                bacterium._dispersal_movement()
                eliminated_count += 1
        
        # Record elimination event
        self.elimination_events.append({
            'iteration': self.iteration,
            'eliminated_count': eliminated_count,
            'elimination_rate': eliminated_count / len(self.agents)
        })
        
        self.elimination_step += 1
    
    def _initialize_nutrient_field(self) -> None:
        """Initialize nutrient concentration field"""
        # Simple nutrient field - higher concentration near global optimum
        field_size = 100
        self.nutrient_field = np.random.random((field_size, field_size))
    
    def _update_signal_field(self) -> None:
        """Update chemical signal field"""
        # Simple signal field based on bacterial positions
        total_signal = sum(b.signal_molecules for b in self.agents)
        self.signal_field = total_signal
    
    def _update_bacterial_neighborhoods(self) -> None:
        """Update neighborhoods for each bacterium"""
        for bacterium in self.agents:
            bacterium.neighbors = []
            
            for other in self.agents:
                if other != bacterium:
                    distance = np.linalg.norm(bacterium.position - other.position)
                    if distance <= bacterium.communication_range:
                        bacterium.neighbors.append(other)
    
    def _calculate_local_signal(self, bacterium: Bacterium) -> float:
        """Calculate local signal concentration around a bacterium"""
        local_signal = bacterium.signal_molecules
        
        for neighbor in bacterium.neighbors:
            distance = np.linalg.norm(bacterium.position - neighbor.position)
            signal_contribution = neighbor.signal_molecules / (1 + distance)
            local_signal += signal_contribution
        
        return local_signal
    
    def _adapt_step_size(self) -> None:
        """Adaptively adjust chemotactic step size"""
        if len(self.chemotaxis_success_rate) > 5:
            recent_success = np.mean(self.chemotaxis_success_rate[-5:])
            
            if recent_success > 0.7:
                # High success rate - increase step size for faster exploration
                self.current_step_size = min(1.0, self.current_step_size * 1.05)
            elif recent_success < 0.3:
                # Low success rate - decrease step size for better exploitation
                self.current_step_size = max(0.01, self.current_step_size * 0.95)
    
    def _record_bfo_metrics(self) -> None:
        """Record BFO-specific performance metrics"""
        # Count bacteria in different states
        state_counts = {state: 0 for state in BacterialState}
        generation_sum = 0
        health_sum = 0
        
        for bacterium in self.agents:
            state_counts[bacterium.state] += 1
            generation_sum += bacterium.generation
            health_sum += bacterium.health
        
        # Calculate averages
        avg_generation = generation_sum / len(self.agents)
        avg_health = health_sum / len(self.agents)
        
        # Store metrics (simplified)
        self.statistics.update({
            'avg_generation': avg_generation,
            'avg_health': avg_health,
            'current_step_size': self.current_step_size,
            'chemotaxis_step': self.chemotaxis_step,
            'reproduction_step': self.reproduction_step,
            'elimination_step': self.elimination_step
        })
    
    def get_bfo_statistics(self) -> Dict[str, Any]:
        """Get BFO-specific statistics"""
        return {
            'current_step_size': self.current_step_size,
            'chemotaxis_success_rate': self.chemotaxis_success_rate[-10:],
            'reproduction_events': self.reproduction_events[-5:],
            'elimination_events': self.elimination_events[-5:],
            'swarming_activity': self.swarming_activity[-10:],
            'average_generation': np.mean([b.generation for b in self.agents]),
            'average_health': np.mean([b.health for b in self.agents]),
            'state_distribution': {
                state.value: sum(1 for b in self.agents if b.state == state)
                for state in BacterialState
            },
            'total_chemotaxis_steps': self.chemotaxis_step,
            'total_reproduction_events': self.reproduction_step,
            'total_elimination_events': self.elimination_step
        }


# Factory function for easy instantiation
def create_bacterial_foraging_optimizer(population_size: int = 50,
                                       max_iterations: int = 1000,
                                       step_size: float = 0.1,
                                       num_chemotactic_steps: int = 4,
                                       dimension: int = 2,
                                       bounds: Tuple[float, float] = (-10.0, 10.0)) -> BacterialForagingOptimizer:
    """
    Create a Bacterial Foraging Optimizer with specified parameters
    
    Args:
        population_size: Number of bacteria in colony
        max_iterations: Maximum number of iterations
        step_size: Chemotactic step size
        num_chemotactic_steps: Number of chemotactic steps per iteration
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured BacterialForagingOptimizer instance
    """
    params = BFOParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        step_size=step_size,
        num_chemotactic_steps=num_chemotactic_steps
    )
    
    return BacterialForagingOptimizer(params)