"""
Ant Colony Optimization (ACO) Algorithm

This module implements the Ant Colony Optimization algorithm, inspired by the
foraging behavior of ants. It includes pheromone trails, probabilistic movement,
and various ACO variants.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


@dataclass
class ACOParameters(SwarmParameters):
    """Ant Colony Optimization specific parameters"""
    alpha: float = 1.0  # Pheromone importance
    beta: float = 2.0   # Heuristic importance
    rho: float = 0.1    # Evaporation rate
    q0: float = 0.9     # Exploitation vs exploration parameter
    pheromone_init: float = 0.1  # Initial pheromone level
    local_search: bool = True    # Enable local search
    elitist_ants: int = 5        # Number of elitist ants


class Ant(SwarmAgent):
    """
    Individual ant agent in the colony
    
    Each ant constructs solutions probabilistically based on pheromone
    trails and heuristic information.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        self.path = []
        self.visited = set()
        self.tour_length = 0.0
        self.pheromone_delta = 0.0
        
        # Ant-specific properties
        self.properties.update({
            'energy': 100.0,
            'carrying_capacity': 1.0,
            'exploration_tendency': np.random.random(),
            'speed': 1.0
        })
    
    def update_position(self, pheromone_matrix: np.ndarray = None, 
                       heuristic_matrix: np.ndarray = None,
                       alpha: float = 1.0, beta: float = 2.0,
                       q0: float = 0.9) -> None:
        """
        Update ant position using ACO probabilistic rules
        
        Args:
            pheromone_matrix: Pheromone trail matrix
            heuristic_matrix: Heuristic information matrix
            alpha: Pheromone importance factor
            beta: Heuristic importance factor
            q0: Exploitation vs exploration parameter
        """
        if pheromone_matrix is None or heuristic_matrix is None:
            # Random walk fallback
            self.position += np.random.normal(0, 0.1, self.dimension)
            self.clip_to_bounds()
            return
        
        # Probabilistic state transition rule
        current_node = self._position_to_node()
        unvisited = self._get_unvisited_nodes()
        
        if not unvisited:
            self._reset_tour()
            return
        
        # Calculate transition probabilities
        probabilities = self._calculate_transition_probabilities(
            current_node, unvisited, pheromone_matrix, heuristic_matrix, alpha, beta
        )
        
        # Choose next node
        if np.random.random() < q0:
            # Exploitation: choose best option
            next_node = unvisited[np.argmax(probabilities)]
        else:
            # Exploration: probabilistic selection
            next_node = np.random.choice(unvisited, p=probabilities)
        
        # Update position and path
        self._move_to_node(next_node)
        self.path.append(next_node)
        self.visited.add(next_node)
    
    def update_velocity(self, **kwargs) -> None:
        """Update ant velocity (momentum-based movement)"""
        momentum = kwargs.get('momentum', 0.1)
        random_factor = kwargs.get('random_factor', 0.1)
        
        # Add momentum to velocity
        self.velocity = momentum * self.velocity + random_factor * np.random.randn(self.dimension)
        
        # Limit velocity magnitude
        max_velocity = kwargs.get('max_velocity', 2.0)
        velocity_magnitude = np.linalg.norm(self.velocity)
        if velocity_magnitude > max_velocity:
            self.velocity = (self.velocity / velocity_magnitude) * max_velocity
    
    def _position_to_node(self) -> int:
        """Convert continuous position to discrete node"""
        # Simple mapping for demonstration
        return int(np.sum(self.position) * 10) % 100
    
    def _get_unvisited_nodes(self) -> List[int]:
        """Get list of unvisited nodes"""
        all_nodes = list(range(100))  # Example node set
        return [node for node in all_nodes if node not in self.visited]
    
    def _calculate_transition_probabilities(self, current_node: int, 
                                          unvisited: List[int],
                                          pheromone_matrix: np.ndarray,
                                          heuristic_matrix: np.ndarray,
                                          alpha: float, beta: float) -> np.ndarray:
        """Calculate transition probabilities to unvisited nodes"""
        probabilities = []
        
        for node in unvisited:
            pheromone = pheromone_matrix[current_node, node]
            heuristic = heuristic_matrix[current_node, node]
            
            # ACO probability formula
            prob = (pheromone ** alpha) * (heuristic ** beta)
            probabilities.append(prob)
        
        # Normalize probabilities
        probabilities = np.array(probabilities)
        total = np.sum(probabilities)
        if total > 0:
            probabilities /= total
        else:
            probabilities = np.ones(len(unvisited)) / len(unvisited)
        
        return probabilities
    
    def _move_to_node(self, node: int) -> None:
        """Move ant to specified node"""
        # Convert node back to position
        new_position = np.random.uniform(self.bounds[0], self.bounds[1], self.dimension)
        self.position = new_position
        self.clip_to_bounds()
    
    def _reset_tour(self) -> None:
        """Reset ant's tour"""
        self.path.clear()
        self.visited.clear()
        self.tour_length = 0.0


class AntColonyOptimizer(SwarmOptimizer):
    """
    Ant Colony Optimization algorithm implementation
    
    Implements the complete ACO algorithm with pheromone management,
    probabilistic construction, and local search capabilities.
    """
    
    def __init__(self, parameters: ACOParameters):
        super().__init__(parameters)
        self.aco_params = parameters
        
        # Pheromone and heuristic matrices
        self.pheromone_matrix = None
        self.heuristic_matrix = None
        
        # ACO-specific tracking
        self.elite_ants = []
        self.pheromone_history = []
        
        # Performance metrics
        self.construction_time = 0.0
        self.local_search_time = 0.0
        self.pheromone_update_time = 0.0
    
    def initialize_population(self) -> None:
        """Initialize ant colony"""
        self.agents = [
            Ant(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Initialize pheromone matrix
        matrix_size = max(100, self.params.dimension * 10)  # Adaptive size
        self.pheromone_matrix = np.full(
            (matrix_size, matrix_size), 
            self.aco_params.pheromone_init
        )
        
        # Initialize heuristic matrix (distance-based)
        self.heuristic_matrix = self._initialize_heuristic_matrix(matrix_size)
        
        self.logger.info(f"Initialized {len(self.agents)} ants with {matrix_size}x{matrix_size} matrices")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all ants in the colony"""
        import time
        
        start_time = time.time()
        
        # Construction phase: ants build solutions
        self._construction_phase()
        self.construction_time += time.time() - start_time
        
        # Evaluation phase
        start_time = time.time()
        for ant in self.agents:
            ant.evaluate_fitness(objective_function)
        
        # Local search phase (optional)
        if self.aco_params.local_search:
            self._local_search_phase(objective_function)
        self.local_search_time += time.time() - start_time
        
        # Pheromone update phase
        start_time = time.time()
        self._pheromone_update_phase()
        self.pheromone_update_time += time.time() - start_time
        
        # Update elite ants
        self._update_elite_ants()
    
    def _construction_phase(self) -> None:
        """Construction phase where ants build solutions"""
        for ant in self.agents:
            # Reset ant for new tour
            ant._reset_tour()
            
            # Construct solution step by step
            max_steps = min(50, self.params.dimension * 2)
            for _ in range(max_steps):
                ant.update_position(
                    pheromone_matrix=self.pheromone_matrix,
                    heuristic_matrix=self.heuristic_matrix,
                    alpha=self.aco_params.alpha,
                    beta=self.aco_params.beta,
                    q0=self.aco_params.q0
                )
                
                # Early termination if tour is complete
                if len(ant.visited) >= 20:  # Sufficient exploration
                    break
    
    def _local_search_phase(self, objective_function: Callable) -> None:
        """Local search improvement phase"""
        for ant in self.agents:
            if np.random.random() < 0.3:  # Apply local search probabilistically
                self._local_search_2opt(ant, objective_function)
    
    def _local_search_2opt(self, ant: Ant, objective_function: Callable) -> None:
        """2-opt local search for solution improvement"""
        current_fitness = ant.fitness
        best_position = ant.position.copy()
        
        # Try small perturbations
        for _ in range(5):
            # Random perturbation
            perturbation = np.random.normal(0, 0.1, self.params.dimension)
            new_position = ant.position + perturbation
            new_position = np.clip(new_position, self.params.bounds[0], self.params.bounds[1])
            
            # Evaluate new position
            old_position = ant.position.copy()
            ant.position = new_position
            new_fitness = ant.evaluate_fitness(objective_function)
            
            # Keep improvement
            if new_fitness < current_fitness:
                current_fitness = new_fitness
                best_position = new_position.copy()
            else:
                ant.position = old_position  # Revert
        
        # Apply best improvement
        ant.position = best_position
        ant.fitness = current_fitness
    
    def _pheromone_update_phase(self) -> None:
        """Update pheromone trails"""
        # Evaporation
        self.pheromone_matrix *= (1.0 - self.aco_params.rho)
        
        # Pheromone deposit by all ants
        for ant in self.agents:
            self._deposit_pheromone(ant)
        
        # Additional deposit by elite ants
        for ant in self.elite_ants:
            self._deposit_pheromone(ant, elite_factor=2.0)
        
        # Record pheromone statistics
        self.pheromone_history.append({
            'mean': np.mean(self.pheromone_matrix),
            'std': np.std(self.pheromone_matrix),
            'max': np.max(self.pheromone_matrix),
            'min': np.min(self.pheromone_matrix)
        })
    
    def _deposit_pheromone(self, ant: Ant, elite_factor: float = 1.0) -> None:
        """Deposit pheromone for an ant's path"""
        if len(ant.path) < 2 or ant.fitness == float('inf'):
            return
        
        # Calculate pheromone amount
        pheromone_amount = elite_factor / (1.0 + ant.fitness)
        
        # Deposit on edges in path
        for i in range(len(ant.path) - 1):
            node1, node2 = ant.path[i], ant.path[i + 1]
            if (0 <= node1 < self.pheromone_matrix.shape[0] and 
                0 <= node2 < self.pheromone_matrix.shape[1]):
                self.pheromone_matrix[node1, node2] += pheromone_amount
                self.pheromone_matrix[node2, node1] += pheromone_amount  # Symmetric
    
    def _update_elite_ants(self) -> None:
        """Update elite ants list"""
        # Sort ants by fitness
        sorted_ants = sorted(self.agents, key=lambda x: x.fitness)
        
        # Select elite ants
        self.elite_ants = sorted_ants[:self.aco_params.elitist_ants]
    
    def _initialize_heuristic_matrix(self, size: int) -> np.ndarray:
        """Initialize heuristic information matrix"""
        # Distance-based heuristic
        heuristic = np.zeros((size, size))
        
        for i in range(size):
            for j in range(size):
                if i != j:
                    # Simple distance heuristic
                    distance = abs(i - j) + 1
                    heuristic[i, j] = 1.0 / distance
        
        return heuristic
    
    def get_pheromone_statistics(self) -> Dict[str, Any]:
        """Get pheromone matrix statistics"""
        if self.pheromone_matrix is None:
            return {}
        
        return {
            'matrix_shape': self.pheromone_matrix.shape,
            'mean_pheromone': np.mean(self.pheromone_matrix),
            'std_pheromone': np.std(self.pheromone_matrix),
            'max_pheromone': np.max(self.pheromone_matrix),
            'min_pheromone': np.min(self.pheromone_matrix),
            'pheromone_history': self.pheromone_history[-10:],  # Last 10 iterations
            'elite_ants_count': len(self.elite_ants),
            'elite_fitness': [ant.fitness for ant in self.elite_ants]
        }
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get algorithm performance metrics"""
        total_time = self.construction_time + self.local_search_time + self.pheromone_update_time
        
        return {
            'construction_time': self.construction_time,
            'local_search_time': self.local_search_time,
            'pheromone_update_time': self.pheromone_update_time,
            'total_algorithm_time': total_time,
            'construction_ratio': self.construction_time / max(total_time, 1e-6),
            'local_search_ratio': self.local_search_time / max(total_time, 1e-6),
            'pheromone_ratio': self.pheromone_update_time / max(total_time, 1e-6)
        }
    
    def visualize_pheromone_trails(self, save_path: Optional[str] = None) -> None:
        """Visualize pheromone trails (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 8))
            plt.imshow(self.pheromone_matrix[:50, :50], cmap='hot', interpolation='nearest')
            plt.colorbar(label='Pheromone Intensity')
            plt.title('Pheromone Trail Matrix')
            plt.xlabel('Node Index')
            plt.ylabel('Node Index')
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_ant_colony_optimizer(population_size: int = 50,
                               max_iterations: int = 1000,
                               alpha: float = 1.0,
                               beta: float = 2.0,
                               rho: float = 0.1,
                               dimension: int = 2,
                               bounds: Tuple[float, float] = (-10.0, 10.0)) -> AntColonyOptimizer:
    """
    Create an Ant Colony Optimizer with specified parameters
    
    Args:
        population_size: Number of ants in colony
        max_iterations: Maximum number of iterations
        alpha: Pheromone importance factor
        beta: Heuristic importance factor
        rho: Pheromone evaporation rate
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured AntColonyOptimizer instance
    """
    params = ACOParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        alpha=alpha,
        beta=beta,
        rho=rho
    )
    
    return AntColonyOptimizer(params)