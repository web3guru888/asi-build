"""
Particle Swarm Optimization (PSO) Algorithm

This module implements the Particle Swarm Optimization algorithm, inspired by
the social behavior of bird flocking and fish schooling. It includes various
PSO variants and advanced features.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class PSOVariant(Enum):
    """PSO algorithm variants"""
    STANDARD = "standard"
    INERTIA_WEIGHT = "inertia_weight"
    CONSTRICTION = "constriction"
    FULLY_INFORMED = "fully_informed"
    COMPREHENSIVE_LEARNING = "comprehensive_learning"


@dataclass
class PSOParameters(SwarmParameters):
    """Particle Swarm Optimization specific parameters"""
    c1: float = 2.0          # Cognitive acceleration coefficient
    c2: float = 2.0          # Social acceleration coefficient
    w_min: float = 0.4       # Minimum inertia weight
    w_max: float = 0.9       # Maximum inertia weight
    variant: PSOVariant = PSOVariant.INERTIA_WEIGHT
    
    # Advanced parameters
    neighborhood_size: int = 3    # For local best PSO
    learning_probability: float = 0.05  # For comprehensive learning PSO
    velocity_clamping: bool = True      # Enable velocity clamping
    max_velocity_ratio: float = 0.2     # Max velocity as ratio of search space
    
    # Adaptive parameters
    adaptive_inertia: bool = True       # Dynamic inertia weight adjustment
    adaptive_coefficients: bool = False # Dynamic c1/c2 adjustment
    success_threshold: float = 0.1      # Success rate threshold for adaptation


class Particle(SwarmAgent):
    """
    Individual particle in the swarm
    
    Each particle has position, velocity, personal best, and social connections.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Initialize velocity randomly
        velocity_range = (bounds[1] - bounds[0]) * 0.1
        self.velocity = np.random.uniform(-velocity_range, velocity_range, dimension)
        
        # PSO-specific properties
        self.personal_best_position = self.position.copy()
        self.personal_best_fitness = float('inf')
        
        # Social connections
        self.neighbors = []
        self.local_best_position = None
        self.local_best_fitness = float('inf')
        
        # Learning and adaptation
        self.success_rate = 0.0
        self.stagnation_counter = 0
        self.learning_probability = 0.05
        
        # Particle-specific properties
        self.properties.update({
            'social_tendency': np.random.random(),
            'cognitive_tendency': np.random.random(),
            'exploration_tendency': np.random.random(),
            'communication_range': 1.0
        })
    
    def update_position(self, **kwargs) -> None:
        """Update particle position using velocity"""
        # Update position: x(t+1) = x(t) + v(t+1)
        self.position += self.velocity
        self.clip_to_bounds()
        
        # Update age and activity
        self.age += 1
        
        # Handle boundary violations
        self._handle_boundary_violations()
    
    def update_velocity(self, global_best_position: np.ndarray = None,
                       inertia_weight: float = 0.729,
                       c1: float = 2.0, c2: float = 2.0,
                       variant: PSOVariant = PSOVariant.INERTIA_WEIGHT,
                       **kwargs) -> None:
        """
        Update particle velocity using PSO equations
        
        Args:
            global_best_position: Global best position
            inertia_weight: Inertia weight parameter
            c1: Cognitive acceleration coefficient
            c2: Social acceleration coefficient
            variant: PSO variant to use
        """
        if global_best_position is None:
            global_best_position = self.position
        
        # Random components
        r1 = np.random.random(self.dimension)
        r2 = np.random.random(self.dimension)
        
        # Cognitive component (personal experience)
        cognitive_component = c1 * r1 * (self.personal_best_position - self.position)
        
        # Social component (swarm experience)
        if variant == PSOVariant.FULLY_INFORMED:
            social_component = self._calculate_informed_component(c2, r2)
        else:
            social_component = c2 * r2 * (global_best_position - self.position)
        
        # Update velocity based on variant
        if variant == PSOVariant.STANDARD:
            self.velocity = (self.velocity + 
                           cognitive_component + 
                           social_component)
        
        elif variant == PSOVariant.INERTIA_WEIGHT:
            self.velocity = (inertia_weight * self.velocity + 
                           cognitive_component + 
                           social_component)
        
        elif variant == PSOVariant.CONSTRICTION:
            chi = kwargs.get('constriction_factor', 0.729)
            self.velocity = chi * (self.velocity + 
                                 cognitive_component + 
                                 social_component)
        
        elif variant == PSOVariant.COMPREHENSIVE_LEARNING:
            self._comprehensive_learning_velocity_update(c1, c2, r1, r2, global_best_position)
        
        # Apply velocity clamping if enabled
        max_velocity = kwargs.get('max_velocity')
        if max_velocity is not None:
            self._clamp_velocity(max_velocity)
    
    def _calculate_informed_component(self, c2: float, r2: np.ndarray) -> np.ndarray:
        """Calculate fully informed social component"""
        if not self.neighbors:
            return np.zeros(self.dimension)
        
        # Average influence from all neighbors
        neighbor_influence = np.zeros(self.dimension)
        for neighbor in self.neighbors:
            neighbor_influence += (neighbor.personal_best_position - self.position)
        
        if len(self.neighbors) > 0:
            neighbor_influence /= len(self.neighbors)
        
        return c2 * r2 * neighbor_influence
    
    def _comprehensive_learning_velocity_update(self, c1: float, c2: float, 
                                              r1: np.ndarray, r2: np.ndarray,
                                              global_best_position: np.ndarray) -> None:
        """Comprehensive Learning PSO velocity update"""
        # Learning probability determines which dimensions to update
        learning_mask = np.random.random(self.dimension) < self.learning_probability
        
        # Update velocity for learning dimensions
        for i in range(self.dimension):
            if learning_mask[i]:
                # Learn from exemplar (best neighbor or global best)
                exemplar = self._select_exemplar(global_best_position)
                self.velocity[i] = (0.729 * self.velocity[i] + 
                                  c1 * r1[i] * (exemplar[i] - self.position[i]))
            else:
                # Standard velocity update
                self.velocity[i] = (0.729 * self.velocity[i] + 
                                  c1 * r1[i] * (self.personal_best_position[i] - self.position[i]) +
                                  c2 * r2[i] * (global_best_position[i] - self.position[i]))
    
    def _select_exemplar(self, global_best_position: np.ndarray) -> np.ndarray:
        """Select exemplar for comprehensive learning"""
        if self.neighbors and np.random.random() < 0.5:
            # Select random neighbor's best position
            neighbor = np.random.choice(self.neighbors)
            return neighbor.personal_best_position
        else:
            # Use global best
            return global_best_position
    
    def _clamp_velocity(self, max_velocity: float) -> None:
        """Clamp velocity to maximum allowed values"""
        velocity_magnitude = np.linalg.norm(self.velocity)
        if velocity_magnitude > max_velocity:
            self.velocity = (self.velocity / velocity_magnitude) * max_velocity
    
    def _handle_boundary_violations(self) -> None:
        """Handle boundary violations with velocity adjustment"""
        # Check for boundary violations
        lower_violations = self.position < self.bounds[0]
        upper_violations = self.position > self.bounds[1]
        
        # Reflect velocity for violated dimensions
        self.velocity[lower_violations] = abs(self.velocity[lower_violations])
        self.velocity[upper_violations] = -abs(self.velocity[upper_violations])
    
    def update_personal_best(self) -> bool:
        """Update personal best if current position is better"""
        if self.fitness < self.personal_best_fitness:
            self.personal_best_fitness = self.fitness
            self.personal_best_position = self.position.copy()
            self.stagnation_counter = 0
            return True
        else:
            self.stagnation_counter += 1
            return False
    
    def add_neighbor(self, neighbor: 'Particle') -> None:
        """Add a neighbor particle"""
        if neighbor not in self.neighbors:
            self.neighbors.append(neighbor)
    
    def update_local_best(self) -> None:
        """Update local best from neighborhood"""
        if not self.neighbors:
            self.local_best_position = self.personal_best_position.copy()
            self.local_best_fitness = self.personal_best_fitness
            return
        
        best_neighbor = min(self.neighbors, key=lambda p: p.personal_best_fitness)
        
        if best_neighbor.personal_best_fitness < self.local_best_fitness:
            self.local_best_fitness = best_neighbor.personal_best_fitness
            self.local_best_position = best_neighbor.personal_best_position.copy()


class ParticleSwarmOptimizer(SwarmOptimizer):
    """
    Particle Swarm Optimization algorithm implementation
    
    Implements various PSO variants with adaptive parameters and
    neighborhood topologies.
    """
    
    def __init__(self, parameters: PSOParameters):
        super().__init__(parameters)
        self.pso_params = parameters
        
        # PSO-specific state
        self.current_inertia_weight = parameters.w_max
        self.current_c1 = parameters.c1
        self.current_c2 = parameters.c2
        
        # Neighborhood topology
        self.topology = "global"  # global, ring, von_neumann, random
        
        # Adaptive control
        self.success_counter = 0
        self.failure_counter = 0
        self.adaptation_interval = 10
        
        # Performance tracking
        self.velocity_statistics = []
        self.swarm_diversity_history = []
        
        # Calculate max velocity
        search_range = parameters.bounds[1] - parameters.bounds[0]
        self.max_velocity = search_range * parameters.max_velocity_ratio
    
    def initialize_population(self) -> None:
        """Initialize particle swarm"""
        self.agents = [
            Particle(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Setup neighborhood topology
        self._setup_neighborhood_topology()
        
        self.logger.info(f"Initialized {len(self.agents)} particles with {self.topology} topology")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all particles in the swarm"""
        # Evaluate fitness for all particles
        improvements = 0
        for particle in self.agents:
            old_fitness = particle.fitness
            particle.evaluate_fitness(objective_function)
            
            # Update personal best
            if particle.update_personal_best():
                improvements += 1
        
        # Update local bests
        for particle in self.agents:
            particle.update_local_best()
        
        # Adaptive parameter control
        if self.pso_params.adaptive_inertia or self.pso_params.adaptive_coefficients:
            self._adaptive_parameter_control(improvements)
        
        # Update velocities and positions
        for particle in self.agents:
            particle.update_velocity(
                global_best_position=self.global_best_position,
                inertia_weight=self.current_inertia_weight,
                c1=self.current_c1,
                c2=self.current_c2,
                variant=self.pso_params.variant,
                max_velocity=self.max_velocity if self.pso_params.velocity_clamping else None,
                constriction_factor=0.729
            )
            
            particle.update_position()
        
        # Record statistics
        self._record_velocity_statistics()
        self._record_diversity_statistics()
    
    def _setup_neighborhood_topology(self) -> None:
        """Setup particle neighborhood topology"""
        if self.topology == "global":
            # All particles connected to all others
            for particle in self.agents:
                particle.neighbors = [p for p in self.agents if p != particle]
        
        elif self.topology == "ring":
            # Ring topology
            for i, particle in enumerate(self.agents):
                left_neighbor = self.agents[(i - 1) % len(self.agents)]
                right_neighbor = self.agents[(i + 1) % len(self.agents)]
                particle.neighbors = [left_neighbor, right_neighbor]
        
        elif self.topology == "von_neumann":
            # Von Neumann (grid) topology
            self._setup_von_neumann_topology()
        
        elif self.topology == "random":
            # Random topology
            for particle in self.agents:
                num_neighbors = min(self.pso_params.neighborhood_size, len(self.agents) - 1)
                neighbors = np.random.choice(
                    [p for p in self.agents if p != particle],
                    size=num_neighbors,
                    replace=False
                )
                particle.neighbors = list(neighbors)
    
    def _setup_von_neumann_topology(self) -> None:
        """Setup Von Neumann grid topology"""
        n = len(self.agents)
        grid_size = int(np.ceil(np.sqrt(n)))
        
        for i, particle in enumerate(self.agents):
            row, col = divmod(i, grid_size)
            neighbors = []
            
            # Add cardinal neighbors
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < grid_size and 0 <= nc < grid_size:
                    neighbor_idx = nr * grid_size + nc
                    if neighbor_idx < n:
                        neighbors.append(self.agents[neighbor_idx])
            
            particle.neighbors = neighbors
    
    def _adaptive_parameter_control(self, improvements: int) -> None:
        """Adaptive control of PSO parameters"""
        success_rate = improvements / len(self.agents)
        
        if self.pso_params.adaptive_inertia:
            self._adapt_inertia_weight(success_rate)
        
        if self.pso_params.adaptive_coefficients:
            self._adapt_acceleration_coefficients(success_rate)
    
    def _adapt_inertia_weight(self, success_rate: float) -> None:
        """Adapt inertia weight based on success rate"""
        if success_rate > self.pso_params.success_threshold:
            # Good performance, increase exploration
            self.current_inertia_weight = min(
                self.pso_params.w_max,
                self.current_inertia_weight + 0.01
            )
        else:
            # Poor performance, increase exploitation
            self.current_inertia_weight = max(
                self.pso_params.w_min,
                self.current_inertia_weight - 0.01
            )
    
    def _adapt_acceleration_coefficients(self, success_rate: float) -> None:
        """Adapt acceleration coefficients based on performance"""
        if success_rate > self.pso_params.success_threshold:
            # Emphasize cognitive component
            self.current_c1 = min(3.0, self.current_c1 + 0.05)
            self.current_c2 = max(1.0, self.current_c2 - 0.05)
        else:
            # Emphasize social component
            self.current_c1 = max(1.0, self.current_c1 - 0.05)
            self.current_c2 = min(3.0, self.current_c2 + 0.05)
    
    def _record_velocity_statistics(self) -> None:
        """Record velocity statistics for analysis"""
        velocities = np.array([particle.velocity for particle in self.agents])
        
        stats = {
            'mean_magnitude': np.mean([np.linalg.norm(v) for v in velocities]),
            'max_magnitude': np.max([np.linalg.norm(v) for v in velocities]),
            'std_magnitude': np.std([np.linalg.norm(v) for v in velocities]),
            'mean_velocity': np.mean(velocities, axis=0).tolist(),
            'std_velocity': np.std(velocities, axis=0).tolist()
        }
        
        self.velocity_statistics.append(stats)
    
    def _record_diversity_statistics(self) -> None:
        """Record swarm diversity statistics"""
        positions = np.array([particle.position for particle in self.agents])
        
        # Calculate average distance from centroid
        centroid = np.mean(positions, axis=0)
        distances = [np.linalg.norm(pos - centroid) for pos in positions]
        
        diversity = {
            'mean_distance_from_centroid': np.mean(distances),
            'std_distance_from_centroid': np.std(distances),
            'max_distance_from_centroid': np.max(distances),
            'centroid': centroid.tolist()
        }
        
        self.swarm_diversity_history.append(diversity)
    
    def get_pso_statistics(self) -> Dict[str, Any]:
        """Get PSO-specific statistics"""
        return {
            'current_inertia_weight': self.current_inertia_weight,
            'current_c1': self.current_c1,
            'current_c2': self.current_c2,
            'topology': self.topology,
            'max_velocity': self.max_velocity,
            'variant': self.pso_params.variant.value,
            'velocity_statistics': self.velocity_statistics[-10:],  # Last 10 iterations
            'diversity_history': self.swarm_diversity_history[-10:],
            'average_neighbors': np.mean([len(p.neighbors) for p in self.agents]),
            'stagnation_particles': sum(1 for p in self.agents if p.stagnation_counter > 10)
        }
    
    def set_topology(self, topology: str) -> None:
        """Change neighborhood topology"""
        valid_topologies = ["global", "ring", "von_neumann", "random"]
        if topology not in valid_topologies:
            raise ValueError(f"Invalid topology. Choose from: {valid_topologies}")
        
        self.topology = topology
        self._setup_neighborhood_topology()
        self.logger.info(f"Changed topology to {topology}")
    
    def visualize_swarm(self, save_path: Optional[str] = None) -> None:
        """Visualize particle positions and velocities (2D only)"""
        if self.params.dimension != 2:
            self.logger.warning("Visualization only supported for 2D problems")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            positions = np.array([p.position for p in self.agents])
            velocities = np.array([p.velocity for p in self.agents])
            
            plt.figure(figsize=(12, 8))
            
            # Plot particles
            plt.subplot(2, 2, 1)
            plt.scatter(positions[:, 0], positions[:, 1], alpha=0.6)
            if self.global_best_position is not None:
                plt.scatter(self.global_best_position[0], self.global_best_position[1], 
                          color='red', s=100, marker='*', label='Global Best')
            plt.title('Particle Positions')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.legend()
            
            # Plot velocity vectors
            plt.subplot(2, 2, 2)
            plt.quiver(positions[:, 0], positions[:, 1], 
                      velocities[:, 0], velocities[:, 1], alpha=0.6)
            plt.title('Velocity Vectors')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            
            # Plot convergence
            plt.subplot(2, 2, 3)
            plt.plot(self.convergence_history)
            plt.title('Convergence History')
            plt.xlabel('Iteration')
            plt.ylabel('Best Fitness')
            plt.yscale('log')
            
            # Plot diversity
            plt.subplot(2, 2, 4)
            if self.swarm_diversity_history:
                diversity_values = [d['mean_distance_from_centroid'] 
                                  for d in self.swarm_diversity_history]
                plt.plot(diversity_values)
            plt.title('Swarm Diversity')
            plt.xlabel('Iteration')
            plt.ylabel('Mean Distance from Centroid')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_particle_swarm_optimizer(population_size: int = 50,
                                   max_iterations: int = 1000,
                                   c1: float = 2.0,
                                   c2: float = 2.0,
                                   w_min: float = 0.4,
                                   w_max: float = 0.9,
                                   variant: PSOVariant = PSOVariant.INERTIA_WEIGHT,
                                   dimension: int = 2,
                                   bounds: Tuple[float, float] = (-10.0, 10.0)) -> ParticleSwarmOptimizer:
    """
    Create a Particle Swarm Optimizer with specified parameters
    
    Args:
        population_size: Number of particles in swarm
        max_iterations: Maximum number of iterations
        c1: Cognitive acceleration coefficient
        c2: Social acceleration coefficient
        w_min: Minimum inertia weight
        w_max: Maximum inertia weight
        variant: PSO variant to use
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured ParticleSwarmOptimizer instance
    """
    params = PSOParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        c1=c1,
        c2=c2,
        w_min=w_min,
        w_max=w_max,
        variant=variant
    )
    
    return ParticleSwarmOptimizer(params)