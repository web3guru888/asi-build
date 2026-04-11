"""
Artificial Bee Colony (ABC) Algorithm

This module implements the Artificial Bee Colony optimization algorithm,
inspired by the intelligent foraging behavior of honey bee swarms. It includes
employed bees, onlooker bees, and scout bees.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class BeeType(Enum):
    """Types of bees in the colony"""
    EMPLOYED = "employed"
    ONLOOKER = "onlooker"
    SCOUT = "scout"


@dataclass
class ABCParameters(SwarmParameters):
    """Artificial Bee Colony specific parameters"""
    limit: int = 100              # Abandonment limit for food sources
    scout_probability: float = 0.1 # Probability of becoming a scout
    onlooker_ratio: float = 0.5   # Ratio of onlooker bees
    employed_ratio: float = 0.5   # Ratio of employed bees
    
    # Advanced parameters
    modification_rate: float = 1.0    # Rate of position modification
    elite_sites: int = 5              # Number of elite sites for recruitment
    search_radius: float = 1.0        # Search radius around food sources
    waggle_dance_threshold: float = 0.8  # Threshold for waggle dance
    
    # Adaptive parameters
    adaptive_limit: bool = True       # Dynamic abandonment limit
    adaptive_search: bool = True      # Adaptive search radius
    communication_enabled: bool = True # Inter-bee communication


class Bee(SwarmAgent):
    """
    Individual bee agent in the colony
    
    Can be employed, onlooker, or scout bee with different behaviors.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float], bee_type: BeeType = BeeType.EMPLOYED):
        super().__init__(dimension, bounds)
        
        self.bee_type = bee_type
        self.food_source = self.position.copy()
        self.food_quality = float('inf')  # Lower is better
        self.trial_count = 0
        self.abandonment_limit = 100
        
        # Bee-specific properties
        self.energy = 100.0
        self.dance_intensity = 0.0
        self.recruitment_success = 0
        self.exploration_history = []
        
        # Communication and memory
        self.known_food_sources = []
        self.communication_partners = []
        
        # Bee behavior properties
        self.properties.update({
            'foraging_efficiency': np.random.random(),
            'dance_skill': np.random.random(),
            'memory_capacity': np.random.randint(5, 20),
            'social_tendency': np.random.random(),
            'risk_tolerance': np.random.random()
        })
    
    def update_position(self, partner_bee: Optional['Bee'] = None,
                       modification_rate: float = 1.0,
                       search_radius: float = 1.0, **kwargs) -> None:
        """
        Update bee position based on its type and role
        
        Args:
            partner_bee: Partner bee for position modification
            modification_rate: Rate of position modification
            search_radius: Search radius for new positions
        """
        if self.bee_type == BeeType.EMPLOYED:
            self._employed_bee_search(partner_bee, modification_rate)
        elif self.bee_type == BeeType.ONLOOKER:
            self._onlooker_bee_search(partner_bee, modification_rate)
        elif self.bee_type == BeeType.SCOUT:
            self._scout_bee_search(search_radius)
        
        self.clip_to_bounds()
        self.trial_count += 1
        self.age += 1
    
    def update_velocity(self, **kwargs) -> None:
        """Update bee velocity (movement momentum)"""
        # Bees don't have explicit velocity like particles
        # Instead, we use momentum for smoother movements
        momentum = kwargs.get('momentum', 0.1)
        self.velocity *= momentum
        
        # Add random component for exploration
        random_component = np.random.normal(0, 0.05, self.dimension)
        self.velocity += random_component
    
    def _employed_bee_search(self, partner_bee: Optional['Bee'], modification_rate: float) -> None:
        """Employed bee searches around its assigned food source"""
        if partner_bee is None:
            # Random perturbation if no partner
            perturbation = np.random.normal(0, 0.1, self.dimension)
            self.position = self.food_source + perturbation
        else:
            # ABC position update equation
            phi = np.random.uniform(-modification_rate, modification_rate, self.dimension)
            dimension_idx = np.random.randint(0, self.dimension)
            
            new_position = self.position.copy()
            new_position[dimension_idx] = (self.position[dimension_idx] + 
                                         phi[dimension_idx] * 
                                         (self.position[dimension_idx] - partner_bee.position[dimension_idx]))
            
            self.position = new_position
    
    def _onlooker_bee_search(self, partner_bee: Optional['Bee'], modification_rate: float) -> None:
        """Onlooker bee selects food source based on probability and searches"""
        if partner_bee is not None:
            # Move towards high-quality food source
            direction = partner_bee.food_source - self.position
            step_size = np.random.uniform(0.1, 0.5)
            self.position += step_size * direction
        else:
            # Random exploration
            self.position += np.random.normal(0, 0.2, self.dimension)
    
    def _scout_bee_search(self, search_radius: float) -> None:
        """Scout bee performs random exploration"""
        # Random position within search radius
        random_direction = np.random.normal(0, 1, self.dimension)
        random_direction /= np.linalg.norm(random_direction)
        
        random_distance = np.random.uniform(0, search_radius)
        self.position += random_distance * random_direction
        
        # Reset trial count for new food source
        self.trial_count = 0
    
    def evaluate_food_source(self, objective_function: Callable) -> float:
        """Evaluate quality of current food source"""
        old_food_quality = self.food_quality
        self.food_quality = objective_function(self.position)
        
        # Update food source if better
        if self.food_quality < self.fitness:
            self.fitness = self.food_quality
            self.food_source = self.position.copy()
            self.trial_count = 0
            return True
        else:
            self.trial_count += 1
            return False
    
    def calculate_selection_probability(self, max_fitness: float, 
                                      total_fitness: float) -> float:
        """Calculate selection probability for onlooker bees"""
        if total_fitness == 0:
            return 1.0 / 100  # Default probability
        
        # Convert minimization to maximization problem
        relative_fitness = max_fitness - self.food_quality + 1e-10
        return relative_fitness / total_fitness
    
    def should_abandon_food_source(self) -> bool:
        """Check if bee should abandon current food source"""
        return self.trial_count >= self.abandonment_limit
    
    def perform_waggle_dance(self) -> Dict[str, Any]:
        """Perform waggle dance to communicate food source quality"""
        if self.food_quality == float('inf'):
            return {}
        
        # Dance intensity based on food quality (lower quality = higher intensity)
        max_quality = 1000.0  # Assumed max quality for normalization
        normalized_quality = min(self.food_quality / max_quality, 1.0)
        self.dance_intensity = 1.0 - normalized_quality
        
        return {
            'food_source': self.food_source.copy(),
            'quality': self.food_quality,
            'dance_intensity': self.dance_intensity,
            'bee_id': id(self),
            'trial_count': self.trial_count
        }
    
    def observe_waggle_dance(self, dance_info: Dict[str, Any]) -> float:
        """Observe waggle dance and return attraction probability"""
        if not dance_info:
            return 0.0
        
        # Attraction based on dance intensity and bee's social tendency
        base_attraction = dance_info['dance_intensity']
        social_factor = self.properties['social_tendency']
        
        return base_attraction * social_factor
    
    def become_scout(self) -> None:
        """Convert bee to scout bee"""
        self.bee_type = BeeType.SCOUT
        self.trial_count = 0
        self.food_quality = float('inf')
        # Random repositioning will occur in next update


class ArtificialBeeColony(SwarmOptimizer):
    """
    Artificial Bee Colony optimization algorithm implementation
    
    Simulates the foraging behavior of honey bees with employed bees,
    onlooker bees, and scout bees.
    """
    
    def __init__(self, parameters: ABCParameters):
        super().__init__(parameters)
        self.abc_params = parameters
        
        # Bee population management
        self.employed_bees: List[Bee] = []
        self.onlooker_bees: List[Bee] = []
        self.scout_bees: List[Bee] = []
        
        # Colony state
        self.food_sources = []
        self.waggle_dances = []
        self.colony_energy = 0.0
        
        # Performance tracking
        self.recruitment_success_history = []
        self.food_source_abandonment_history = []
        self.dance_participation_history = []
        
        # Adaptive parameters
        self.current_limit = parameters.limit
        self.current_search_radius = parameters.search_radius
    
    def initialize_population(self) -> None:
        """Initialize bee colony with different bee types"""
        total_bees = self.params.population_size
        
        # Calculate bee numbers
        num_employed = int(total_bees * self.abc_params.employed_ratio)
        num_onlooker = int(total_bees * self.abc_params.onlooker_ratio)
        num_scout = total_bees - num_employed - num_onlooker
        
        # Create employed bees
        self.employed_bees = [
            Bee(self.params.dimension, self.params.bounds, BeeType.EMPLOYED)
            for _ in range(num_employed)
        ]
        
        # Create onlooker bees
        self.onlooker_bees = [
            Bee(self.params.dimension, self.params.bounds, BeeType.ONLOOKER)
            for _ in range(num_onlooker)
        ]
        
        # Create scout bees
        self.scout_bees = [
            Bee(self.params.dimension, self.params.bounds, BeeType.SCOUT)
            for _ in range(num_scout)
        ]
        
        # Combine all bees
        self.agents = self.employed_bees + self.onlooker_bees + self.scout_bees
        
        # Set abandonment limits
        for bee in self.agents:
            bee.abandonment_limit = self.current_limit
        
        self.logger.info(f"Initialized colony: {num_employed} employed, "
                        f"{num_onlooker} onlooker, {num_scout} scout bees")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all bees in the colony"""
        # Phase 1: Employed bees phase
        self._employed_bees_phase(objective_function)
        
        # Phase 2: Onlooker bees phase
        self._onlooker_bees_phase(objective_function)
        
        # Phase 3: Scout bees phase
        self._scout_bees_phase(objective_function)
        
        # Update colony state
        self._update_colony_state()
        
        # Adaptive parameter adjustment
        if self.abc_params.adaptive_limit or self.abc_params.adaptive_search:
            self._adaptive_parameter_adjustment()
        
        # Record performance metrics
        self._record_colony_metrics()
    
    def _employed_bees_phase(self, objective_function: Callable) -> None:
        """Employed bees explore around their food sources"""
        improvements = 0
        
        for bee in self.employed_bees:
            # Select random partner bee
            partner_candidates = [b for b in self.employed_bees if b != bee]
            partner_bee = np.random.choice(partner_candidates) if partner_candidates else None
            
            # Search around food source
            old_position = bee.position.copy()
            bee.update_position(
                partner_bee=partner_bee,
                modification_rate=self.abc_params.modification_rate,
                search_radius=self.current_search_radius
            )
            
            # Evaluate new position
            improved = bee.evaluate_food_source(objective_function)
            if improved:
                improvements += 1
            else:
                # Revert if no improvement
                bee.position = old_position
            
            # Check abandonment
            if bee.should_abandon_food_source():
                bee.become_scout()
                self.scout_bees.append(bee)
                self.employed_bees.remove(bee)
        
        self.logger.debug(f"Employed bees phase: {improvements} improvements")
    
    def _onlooker_bees_phase(self, objective_function: Callable) -> None:
        """Onlooker bees select food sources based on waggle dances"""
        if not self.employed_bees:
            return
        
        # Calculate selection probabilities
        max_fitness = max(bee.food_quality for bee in self.employed_bees)
        total_fitness = sum(max_fitness - bee.food_quality + 1e-10 
                          for bee in self.employed_bees)
        
        probabilities = [
            bee.calculate_selection_probability(max_fitness, total_fitness)
            for bee in self.employed_bees
        ]
        
        # Normalize probabilities
        total_prob = sum(probabilities)
        if total_prob > 0:
            probabilities = [p / total_prob for p in probabilities]
        else:
            probabilities = [1.0 / len(self.employed_bees)] * len(self.employed_bees)
        
        # Onlooker bees select food sources
        for bee in self.onlooker_bees:
            # Select food source based on probability
            selected_idx = np.random.choice(len(self.employed_bees), p=probabilities)
            selected_employed_bee = self.employed_bees[selected_idx]
            
            # Search around selected food source
            old_position = bee.position.copy()
            bee.update_position(
                partner_bee=selected_employed_bee,
                modification_rate=self.abc_params.modification_rate,
                search_radius=self.current_search_radius
            )
            
            # Evaluate new position
            improved = bee.evaluate_food_source(objective_function)
            if not improved:
                bee.position = old_position
    
    def _scout_bees_phase(self, objective_function: Callable) -> None:
        """Scout bees perform random exploration"""
        for bee in self.scout_bees:
            # Random exploration
            bee.update_position(search_radius=self.current_search_radius)
            bee.evaluate_food_source(objective_function)
            
            # Chance to become employed bee if good food source found
            if bee.food_quality < np.mean([b.food_quality for b in self.employed_bees]):
                bee.bee_type = BeeType.EMPLOYED
                self.employed_bees.append(bee)
                self.scout_bees.remove(bee)
    
    def _update_colony_state(self) -> None:
        """Update overall colony state"""
        # Update food sources
        self.food_sources = [bee.food_source.copy() for bee in self.employed_bees]
        
        # Calculate colony energy
        self.colony_energy = sum(bee.energy for bee in self.agents)
        
        # Generate waggle dances
        self.waggle_dances = []
        for bee in self.employed_bees:
            if bee.food_quality < self.abc_params.waggle_dance_threshold * self.global_best_fitness:
                dance = bee.perform_waggle_dance()
                if dance:
                    self.waggle_dances.append(dance)
    
    def _adaptive_parameter_adjustment(self) -> None:
        """Adaptively adjust algorithm parameters"""
        if self.abc_params.adaptive_limit:
            # Adjust abandonment limit based on convergence
            if len(self.convergence_history) > 10:
                recent_improvement = (self.convergence_history[-10] - 
                                    self.convergence_history[-1])
                if recent_improvement < 1e-6:
                    self.current_limit = max(10, int(self.current_limit * 0.95))
                else:
                    self.current_limit = min(200, int(self.current_limit * 1.05))
        
        if self.abc_params.adaptive_search:
            # Adjust search radius based on diversity
            if self.diversity_history:
                current_diversity = self.diversity_history[-1]
                target_diversity = 1.0  # Target diversity level
                
                if current_diversity < target_diversity:
                    self.current_search_radius *= 1.1  # Increase exploration
                else:
                    self.current_search_radius *= 0.95  # Increase exploitation
                
                # Keep search radius within bounds
                self.current_search_radius = np.clip(self.current_search_radius, 0.1, 5.0)
    
    def _record_colony_metrics(self) -> None:
        """Record colony-specific performance metrics"""
        # Recruitment success
        total_dances = len(self.waggle_dances)
        successful_recruitments = sum(
            1 for bee in self.onlooker_bees 
            if hasattr(bee, 'recruitment_success') and bee.recruitment_success > 0
        )
        recruitment_rate = successful_recruitments / max(total_dances, 1)
        self.recruitment_success_history.append(recruitment_rate)
        
        # Food source abandonment
        abandoned_sources = sum(1 for bee in self.employed_bees if bee.should_abandon_food_source())
        abandonment_rate = abandoned_sources / max(len(self.employed_bees), 1)
        self.food_source_abandonment_history.append(abandonment_rate)
        
        # Dance participation
        dancing_bees = len(self.waggle_dances)
        participation_rate = dancing_bees / max(len(self.employed_bees), 1)
        self.dance_participation_history.append(participation_rate)
    
    def get_colony_statistics(self) -> Dict[str, Any]:
        """Get colony-specific statistics"""
        return {
            'employed_bees': len(self.employed_bees),
            'onlooker_bees': len(self.onlooker_bees),
            'scout_bees': len(self.scout_bees),
            'food_sources': len(self.food_sources),
            'active_dances': len(self.waggle_dances),
            'colony_energy': self.colony_energy,
            'current_limit': self.current_limit,
            'current_search_radius': self.current_search_radius,
            'recruitment_success_rate': (self.recruitment_success_history[-1] 
                                       if self.recruitment_success_history else 0.0),
            'abandonment_rate': (self.food_source_abandonment_history[-1] 
                               if self.food_source_abandonment_history else 0.0),
            'dance_participation_rate': (self.dance_participation_history[-1] 
                                       if self.dance_participation_history else 0.0),
            'average_trial_count': np.mean([bee.trial_count for bee in self.employed_bees])
        }
    
    def visualize_colony(self, save_path: Optional[str] = None) -> None:
        """Visualize bee colony state (2D only)"""
        if self.params.dimension != 2:
            self.logger.warning("Visualization only supported for 2D problems")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(15, 10))
            
            # Plot bee positions by type
            plt.subplot(2, 3, 1)
            
            # Employed bees
            if self.employed_bees:
                emp_positions = np.array([bee.position for bee in self.employed_bees])
                plt.scatter(emp_positions[:, 0], emp_positions[:, 1], 
                          c='blue', label='Employed', alpha=0.7, s=50)
            
            # Onlooker bees
            if self.onlooker_bees:
                onl_positions = np.array([bee.position for bee in self.onlooker_bees])
                plt.scatter(onl_positions[:, 0], onl_positions[:, 1], 
                          c='green', label='Onlooker', alpha=0.7, s=30)
            
            # Scout bees
            if self.scout_bees:
                scout_positions = np.array([bee.position for bee in self.scout_bees])
                plt.scatter(scout_positions[:, 0], scout_positions[:, 1], 
                          c='red', label='Scout', alpha=0.7, s=40, marker='^')
            
            # Global best
            if self.global_best_position is not None:
                plt.scatter(self.global_best_position[0], self.global_best_position[1], 
                          c='gold', s=200, marker='*', label='Global Best')
            
            plt.title('Bee Colony Positions')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.legend()
            
            # Plot food sources
            plt.subplot(2, 3, 2)
            if self.food_sources:
                food_positions = np.array(self.food_sources)
                qualities = [bee.food_quality for bee in self.employed_bees]
                plt.scatter(food_positions[:, 0], food_positions[:, 1], 
                          c=qualities, cmap='viridis', s=100, alpha=0.7)
                plt.colorbar(label='Food Quality')
            plt.title('Food Sources')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            
            # Plot convergence
            plt.subplot(2, 3, 3)
            plt.plot(self.convergence_history)
            plt.title('Convergence History')
            plt.xlabel('Iteration')
            plt.ylabel('Best Fitness')
            plt.yscale('log')
            
            # Plot colony composition
            plt.subplot(2, 3, 4)
            bee_types = ['Employed', 'Onlooker', 'Scout']
            bee_counts = [len(self.employed_bees), len(self.onlooker_bees), len(self.scout_bees)]
            plt.pie(bee_counts, labels=bee_types, autopct='%1.1f%%')
            plt.title('Colony Composition')
            
            # Plot performance metrics
            plt.subplot(2, 3, 5)
            if self.recruitment_success_history:
                plt.plot(self.recruitment_success_history, label='Recruitment')
            if self.food_source_abandonment_history:
                plt.plot(self.food_source_abandonment_history, label='Abandonment')
            if self.dance_participation_history:
                plt.plot(self.dance_participation_history, label='Dance Participation')
            plt.title('Colony Performance Metrics')
            plt.xlabel('Iteration')
            plt.ylabel('Rate')
            plt.legend()
            
            # Plot diversity
            plt.subplot(2, 3, 6)
            if self.diversity_history:
                plt.plot(self.diversity_history)
            plt.title('Population Diversity')
            plt.xlabel('Iteration')
            plt.ylabel('Diversity')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_artificial_bee_colony(population_size: int = 50,
                                max_iterations: int = 1000,
                                limit: int = 100,
                                employed_ratio: float = 0.5,
                                onlooker_ratio: float = 0.5,
                                dimension: int = 2,
                                bounds: Tuple[float, float] = (-10.0, 10.0)) -> ArtificialBeeColony:
    """
    Create an Artificial Bee Colony optimizer with specified parameters
    
    Args:
        population_size: Number of bees in colony
        max_iterations: Maximum number of iterations
        limit: Abandonment limit for food sources
        employed_ratio: Ratio of employed bees
        onlooker_ratio: Ratio of onlooker bees
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured ArtificialBeeColony instance
    """
    params = ABCParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        limit=limit,
        employed_ratio=employed_ratio,
        onlooker_ratio=onlooker_ratio
    )
    
    return ArtificialBeeColony(params)