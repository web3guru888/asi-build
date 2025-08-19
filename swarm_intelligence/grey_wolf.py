"""
Grey Wolf Optimizer (GWO) Algorithm

This module implements the Grey Wolf Optimizer algorithm, inspired by the
social hierarchy and hunting behavior of grey wolves. It includes alpha,
beta, delta, and omega wolves with coordinated hunting strategies.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class WolfRank(Enum):
    """Wolf hierarchy ranks"""
    ALPHA = "alpha"      # Best solution
    BETA = "beta"        # Second best
    DELTA = "delta"      # Third best
    OMEGA = "omega"      # Rest of the pack


@dataclass
class GWOParameters(SwarmParameters):
    """Grey Wolf Optimizer specific parameters"""
    # Hunting parameters
    a_max: float = 2.0              # Maximum value of 'a'
    a_min: float = 0.0              # Minimum value of 'a'
    
    # Advanced parameters
    pack_leadership_update: bool = True     # Update pack leadership
    adaptive_hunting: bool = True           # Adaptive hunting strategy
    territorial_behavior: bool = True       # Enable territorial behavior
    
    # Social parameters
    pack_cohesion_weight: float = 0.5       # Pack cohesion factor
    hunting_cooperation_weight: float = 0.8  # Cooperation during hunting
    
    # Evolution parameters
    mutation_probability: float = 0.1       # Mutation probability
    crossover_probability: float = 0.3      # Crossover probability


class GreyWolf(SwarmAgent):
    """
    Individual grey wolf agent
    
    Each wolf has a rank in the pack hierarchy and follows specific
    behavioral patterns based on its role.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Wolf hierarchy
        self.rank = WolfRank.OMEGA
        self.pack_position = len(GreyWolf._instances) if hasattr(GreyWolf, '_instances') else 0
        
        # Hunting behavior
        self.hunting_experience = 0.0
        self.leadership_score = 0.0
        self.cooperation_ability = np.random.random()
        
        # Social behavior
        self.pack_loyalty = np.random.uniform(0.7, 1.0)
        self.territorial_range = np.random.uniform(1.0, 3.0)
        self.communication_range = 5.0
        
        # Pack relationships
        self.pack_members = []
        self.alpha_wolf = None
        self.beta_wolf = None
        self.delta_wolf = None
        
        # Wolf-specific properties
        self.properties.update({
            'strength': np.random.uniform(0.5, 1.0),
            'agility': np.random.uniform(0.5, 1.0),
            'endurance': np.random.uniform(0.5, 1.0),
            'intelligence': np.random.uniform(0.5, 1.0),
            'pack_coordination': np.random.random()
        })
    
    def update_position(self, alpha_position: Optional[np.ndarray] = None,
                       beta_position: Optional[np.ndarray] = None,
                       delta_position: Optional[np.ndarray] = None,
                       a_value: float = 2.0, **kwargs) -> None:
        """
        Update wolf position based on pack leaders
        
        Args:
            alpha_position: Position of alpha wolf
            beta_position: Position of beta wolf
            delta_position: Position of delta wolf
            a_value: Current value of parameter 'a'
        """
        if self.rank == WolfRank.ALPHA:
            # Alpha wolf leads - small random movement
            self._alpha_movement(a_value)
        else:
            # Other wolves follow pack leaders
            self._pack_following_movement(alpha_position, beta_position, 
                                        delta_position, a_value)
        
        self.clip_to_bounds()
        self.age += 1
        self.hunting_experience += 0.1
    
    def update_velocity(self, **kwargs) -> None:
        """Update wolf velocity based on hunting behavior"""
        momentum = kwargs.get('momentum', 0.1)
        random_factor = kwargs.get('random_factor', 0.05)
        
        # Wolves don't have explicit velocity, but we maintain momentum
        self.velocity = momentum * self.velocity + random_factor * np.random.randn(self.dimension)
        
        # Limit velocity based on wolf capabilities
        max_velocity = self.properties['agility'] * 2.0
        velocity_magnitude = np.linalg.norm(self.velocity)
        if velocity_magnitude > max_velocity:
            self.velocity = (self.velocity / velocity_magnitude) * max_velocity
    
    def _alpha_movement(self, a_value: float) -> None:
        """Alpha wolf movement - exploration and leadership"""
        # Alpha wolf explores with some randomness
        exploration_factor = a_value / 2.0
        random_movement = exploration_factor * np.random.uniform(-1, 1, self.dimension)
        
        # Small leadership adjustment
        leadership_adjustment = 0.1 * self.leadership_score * np.random.randn(self.dimension)
        
        self.position += random_movement + leadership_adjustment
    
    def _pack_following_movement(self, alpha_pos: Optional[np.ndarray],
                               beta_pos: Optional[np.ndarray],
                               delta_pos: Optional[np.ndarray],
                               a_value: float) -> None:
        """Pack member movement following leaders"""
        if alpha_pos is None:
            # No leaders - random movement
            self.position += a_value * np.random.uniform(-1, 1, self.dimension)
            return
        
        # Calculate position updates from each leader
        position_updates = []
        
        # Follow alpha
        if alpha_pos is not None:
            alpha_update = self._calculate_leader_influence(alpha_pos, a_value, 1.0)
            position_updates.append(alpha_update)
        
        # Follow beta
        if beta_pos is not None:
            beta_update = self._calculate_leader_influence(beta_pos, a_value, 0.8)
            position_updates.append(beta_update)
        
        # Follow delta
        if delta_pos is not None:
            delta_update = self._calculate_leader_influence(delta_pos, a_value, 0.6)
            position_updates.append(delta_update)
        
        # Average the position updates
        if position_updates:
            average_update = np.mean(position_updates, axis=0)
            self.position += average_update
    
    def _calculate_leader_influence(self, leader_pos: np.ndarray, 
                                  a_value: float, influence_weight: float) -> np.ndarray:
        """Calculate influence from a pack leader"""
        # Calculate A and C vectors
        r1 = np.random.random(self.dimension)
        r2 = np.random.random(self.dimension)
        
        A = 2 * a_value * r1 - a_value
        C = 2 * r2
        
        # Calculate distance and position update
        D = np.abs(C * leader_pos - self.position)
        position_update = influence_weight * (leader_pos - A * D)
        
        return position_update - self.position
    
    def evaluate_leadership(self) -> float:
        """Evaluate wolf's leadership potential"""
        # Leadership based on fitness, experience, and traits
        fitness_score = 1.0 / (1.0 + self.fitness) if self.fitness != float('inf') else 0.0
        experience_score = min(self.hunting_experience / 100.0, 1.0)
        trait_score = (self.properties['strength'] + 
                      self.properties['intelligence'] + 
                      self.properties['pack_coordination']) / 3.0
        
        self.leadership_score = 0.5 * fitness_score + 0.3 * experience_score + 0.2 * trait_score
        return self.leadership_score
    
    def hunt_prey(self, prey_position: np.ndarray) -> np.ndarray:
        """Simulate hunting behavior towards prey"""
        # Calculate hunting direction
        direction = prey_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 0:
            direction /= distance
        
        # Hunting speed based on wolf capabilities
        hunting_speed = self.properties['agility'] * self.properties['endurance']
        
        # Add some randomness for realistic hunting
        random_factor = 0.1 * np.random.randn(self.dimension)
        
        hunting_vector = hunting_speed * direction + random_factor
        return hunting_vector
    
    def communicate_with_pack(self) -> Dict[str, Any]:
        """Communicate current status to pack"""
        return {
            'wolf_id': id(self),
            'rank': self.rank.value,
            'position': self.position.copy(),
            'fitness': self.fitness,
            'leadership_score': self.leadership_score,
            'hunting_experience': self.hunting_experience,
            'pack_loyalty': self.pack_loyalty
        }
    
    def respond_to_pack_call(self, pack_message: Dict[str, Any]) -> float:
        """Respond to communication from pack members"""
        if pack_message['rank'] in ['alpha', 'beta', 'delta']:
            # Higher response to leaders
            response_strength = self.pack_loyalty * 0.9
        else:
            # Moderate response to pack members
            response_strength = self.pack_loyalty * 0.5
        
        return response_strength


class GreyWolfOptimizer(SwarmOptimizer):
    """
    Grey Wolf Optimizer algorithm implementation
    
    Implements the complete GWO algorithm with pack hierarchy,
    hunting behavior, and social coordination.
    """
    
    def __init__(self, parameters: GWOParameters):
        super().__init__(parameters)
        self.gwo_params = parameters
        
        # Pack hierarchy
        self.alpha_wolf = None
        self.beta_wolf = None
        self.delta_wolf = None
        self.omega_wolves = []
        
        # Algorithm state
        self.current_a = parameters.a_max
        
        # Pack behavior tracking
        self.pack_communications = []
        self.hunting_success_history = []
        self.leadership_changes = []
        
        # Performance metrics
        self.pack_cohesion_history = []
        self.hunting_efficiency_history = []
    
    def initialize_population(self) -> None:
        """Initialize wolf pack"""
        self.agents = [
            GreyWolf(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Initialize pack relationships
        for wolf in self.agents:
            wolf.pack_members = [w for w in self.agents if w != wolf]
        
        self.logger.info(f"Initialized pack of {len(self.agents)} wolves")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all wolves in the pack"""
        # Evaluate all wolves
        for wolf in self.agents:
            wolf.evaluate_fitness(objective_function)
            wolf.evaluate_leadership()
        
        # Update pack hierarchy
        if self.gwo_params.pack_leadership_update:
            self._update_pack_hierarchy()
        
        # Update parameter 'a'
        self._update_a_parameter()
        
        # Pack communication
        self._handle_pack_communication()
        
        # Update wolf positions
        self._update_wolf_positions()
        
        # Adaptive hunting strategies
        if self.gwo_params.adaptive_hunting:
            self._adaptive_hunting_behavior()
        
        # Record pack metrics
        self._record_pack_metrics()
    
    def _update_pack_hierarchy(self) -> None:
        """Update pack hierarchy based on fitness and leadership"""
        # Sort wolves by fitness (best first)
        sorted_wolves = sorted(self.agents, key=lambda w: w.fitness)
        
        # Update hierarchy
        old_alpha = self.alpha_wolf
        old_beta = self.beta_wolf
        old_delta = self.delta_wolf
        
        # Assign new roles
        if len(sorted_wolves) >= 1:
            self.alpha_wolf = sorted_wolves[0]
            self.alpha_wolf.rank = WolfRank.ALPHA
        
        if len(sorted_wolves) >= 2:
            self.beta_wolf = sorted_wolves[1]
            self.beta_wolf.rank = WolfRank.BETA
        
        if len(sorted_wolves) >= 3:
            self.delta_wolf = sorted_wolves[2]
            self.delta_wolf.rank = WolfRank.DELTA
        
        # Rest are omega wolves
        self.omega_wolves = sorted_wolves[3:] if len(sorted_wolves) > 3 else []
        for wolf in self.omega_wolves:
            wolf.rank = WolfRank.OMEGA
        
        # Record leadership changes
        leadership_change = {
            'iteration': self.iteration,
            'alpha_changed': old_alpha != self.alpha_wolf,
            'beta_changed': old_beta != self.beta_wolf,
            'delta_changed': old_delta != self.delta_wolf
        }
        self.leadership_changes.append(leadership_change)
    
    def _update_a_parameter(self) -> None:
        """Update parameter 'a' linearly from a_max to a_min"""
        self.current_a = (self.gwo_params.a_max - 
                         (self.iteration / self.params.max_iterations) * 
                         (self.gwo_params.a_max - self.gwo_params.a_min))
    
    def _handle_pack_communication(self) -> None:
        """Handle communication between pack members"""
        communications = []
        
        # Leaders communicate their status
        for leader in [self.alpha_wolf, self.beta_wolf, self.delta_wolf]:
            if leader is not None:
                message = leader.communicate_with_pack()
                communications.append(message)
        
        # Pack members respond
        total_response = 0.0
        for wolf in self.omega_wolves:
            for message in communications:
                response = wolf.respond_to_pack_call(message)
                total_response += response
        
        # Record communication activity
        self.pack_communications.append({
            'iteration': self.iteration,
            'messages_sent': len(communications),
            'total_response': total_response,
            'average_response': total_response / max(len(self.omega_wolves), 1)
        })
    
    def _update_wolf_positions(self) -> None:
        """Update positions of all wolves"""
        alpha_pos = self.alpha_wolf.position if self.alpha_wolf else None
        beta_pos = self.beta_wolf.position if self.beta_wolf else None
        delta_pos = self.delta_wolf.position if self.delta_wolf else None
        
        for wolf in self.agents:
            wolf.update_position(
                alpha_position=alpha_pos,
                beta_position=beta_pos,
                delta_position=delta_pos,
                a_value=self.current_a
            )
            
            wolf.update_velocity()
    
    def _adaptive_hunting_behavior(self) -> None:
        """Implement adaptive hunting strategies"""
        # Analyze recent hunting success
        if len(self.convergence_history) > 5:
            recent_improvement = (self.convergence_history[-5] - 
                                self.convergence_history[-1])
            
            if recent_improvement < 1e-6:
                # Poor hunting success - increase exploration
                for wolf in self.agents:
                    if np.random.random() < self.gwo_params.mutation_probability:
                        self._mutate_wolf_position(wolf)
            else:
                # Good hunting success - maintain current strategy
                hunting_success = recent_improvement
                self.hunting_success_history.append(hunting_success)
    
    def _mutate_wolf_position(self, wolf: GreyWolf) -> None:
        """Apply mutation to wolf position"""
        mutation_strength = 0.1 * (self.params.bounds[1] - self.params.bounds[0])
        mutation = np.random.normal(0, mutation_strength, self.params.dimension)
        wolf.position += mutation
        wolf.clip_to_bounds()
    
    def _record_pack_metrics(self) -> None:
        """Record pack-specific performance metrics"""
        # Pack cohesion
        if len(self.agents) > 1:
            positions = np.array([wolf.position for wolf in self.agents])
            centroid = np.mean(positions, axis=0)
            distances = [np.linalg.norm(pos - centroid) for pos in positions]
            cohesion = 1.0 / (1.0 + np.mean(distances))  # Higher cohesion = lower dispersion
            self.pack_cohesion_history.append(cohesion)
        
        # Hunting efficiency
        if self.alpha_wolf:
            efficiency = 1.0 / (1.0 + self.alpha_wolf.fitness) if self.alpha_wolf.fitness != float('inf') else 0.0
            self.hunting_efficiency_history.append(efficiency)
    
    def get_pack_statistics(self) -> Dict[str, Any]:
        """Get pack-specific statistics"""
        return {
            'current_a': self.current_a,
            'alpha_fitness': self.alpha_wolf.fitness if self.alpha_wolf else float('inf'),
            'beta_fitness': self.beta_wolf.fitness if self.beta_wolf else float('inf'),
            'delta_fitness': self.delta_wolf.fitness if self.delta_wolf else float('inf'),
            'pack_size': len(self.agents),
            'omega_wolves': len(self.omega_wolves),
            'leadership_changes': self.leadership_changes[-10:],
            'pack_communications': self.pack_communications[-10:],
            'hunting_success_history': self.hunting_success_history[-10:],
            'pack_cohesion': self.pack_cohesion_history[-1] if self.pack_cohesion_history else 0.0,
            'hunting_efficiency': self.hunting_efficiency_history[-1] if self.hunting_efficiency_history else 0.0,
            'average_leadership_score': np.mean([w.leadership_score for w in self.agents]),
            'average_hunting_experience': np.mean([w.hunting_experience for w in self.agents])
        }
    
    def visualize_pack(self, save_path: Optional[str] = None) -> None:
        """Visualize wolf pack (2D only)"""
        if self.params.dimension != 2:
            self.logger.warning("Visualization only supported for 2D problems")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(15, 10))
            
            # Plot wolf positions by rank
            plt.subplot(2, 3, 1)
            
            # Omega wolves
            if self.omega_wolves:
                omega_positions = np.array([w.position for w in self.omega_wolves])
                plt.scatter(omega_positions[:, 0], omega_positions[:, 1], 
                          c='lightblue', label='Omega', alpha=0.6, s=30)
            
            # Delta wolf
            if self.delta_wolf:
                plt.scatter(self.delta_wolf.position[0], self.delta_wolf.position[1], 
                          c='green', label='Delta', s=80, marker='s')
            
            # Beta wolf
            if self.beta_wolf:
                plt.scatter(self.beta_wolf.position[0], self.beta_wolf.position[1], 
                          c='orange', label='Beta', s=120, marker='^')
            
            # Alpha wolf
            if self.alpha_wolf:
                plt.scatter(self.alpha_wolf.position[0], self.alpha_wolf.position[1], 
                          c='red', label='Alpha', s=200, marker='*')
            
            plt.title('Wolf Pack Hierarchy')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.legend()
            
            # Plot convergence
            plt.subplot(2, 3, 2)
            plt.plot(self.convergence_history)
            plt.title('Pack Hunting Success')
            plt.xlabel('Iteration')
            plt.ylabel('Best Fitness')
            plt.yscale('log')
            
            # Plot pack cohesion
            plt.subplot(2, 3, 3)
            if self.pack_cohesion_history:
                plt.plot(self.pack_cohesion_history)
            plt.title('Pack Cohesion')
            plt.xlabel('Iteration')
            plt.ylabel('Cohesion Level')
            
            # Plot parameter 'a'
            plt.subplot(2, 3, 4)
            a_history = [self.gwo_params.a_max - (i / self.params.max_iterations) * 
                        (self.gwo_params.a_max - self.gwo_params.a_min) 
                        for i in range(min(self.iteration + 1, self.params.max_iterations))]
            plt.plot(a_history)
            plt.title('Parameter a Decay')
            plt.xlabel('Iteration')
            plt.ylabel('Value of a')
            
            # Plot leadership changes
            plt.subplot(2, 3, 5)
            if self.leadership_changes:
                changes = [sum([c['alpha_changed'], c['beta_changed'], c['delta_changed']]) 
                          for c in self.leadership_changes]
                plt.plot(changes)
            plt.title('Leadership Changes')
            plt.xlabel('Iteration')
            plt.ylabel('Number of Changes')
            
            # Plot communication activity
            plt.subplot(2, 3, 6)
            if self.pack_communications:
                comm_activity = [c['total_response'] for c in self.pack_communications]
                plt.plot(comm_activity)
            plt.title('Pack Communication')
            plt.xlabel('Iteration')
            plt.ylabel('Communication Activity')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_grey_wolf_optimizer(population_size: int = 50,
                              max_iterations: int = 1000,
                              a_max: float = 2.0,
                              a_min: float = 0.0,
                              dimension: int = 2,
                              bounds: Tuple[float, float] = (-10.0, 10.0)) -> GreyWolfOptimizer:
    """
    Create a Grey Wolf Optimizer with specified parameters
    
    Args:
        population_size: Number of wolves in pack
        max_iterations: Maximum number of iterations
        a_max: Maximum value of parameter 'a'
        a_min: Minimum value of parameter 'a'
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured GreyWolfOptimizer instance
    """
    params = GWOParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        a_max=a_max,
        a_min=a_min
    )
    
    return GreyWolfOptimizer(params)