"""
Base classes for swarm intelligence algorithms

This module provides the foundational classes that all swarm intelligence
algorithms inherit from, ensuring consistent interfaces and behavior.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Tuple
import logging
import time
from dataclasses import dataclass
from enum import Enum


class SwarmState(Enum):
    """States of the swarm optimization process"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    CONVERGED = "converged"
    TERMINATED = "terminated"


@dataclass
class SwarmParameters:
    """Configuration parameters for swarm algorithms"""
    population_size: int = 50
    max_iterations: int = 1000
    convergence_threshold: float = 1e-6
    dimension: int = 2
    bounds: Tuple[float, float] = (-10.0, 10.0)
    verbose: bool = False
    random_seed: Optional[int] = None


class SwarmAgent(ABC):
    """
    Base class for individual agents in swarm intelligence algorithms
    
    Each agent represents a solution candidate with position, velocity,
    fitness, and other algorithm-specific properties.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        """
        Initialize a swarm agent
        
        Args:
            dimension: Problem dimension
            bounds: Search space bounds (min, max)
        """
        self.dimension = dimension
        self.bounds = bounds
        self.position = np.random.uniform(bounds[0], bounds[1], dimension)
        self.velocity = np.zeros(dimension)
        self.fitness = float('inf')
        self.best_position = self.position.copy()
        self.best_fitness = float('inf')
        self.age = 0
        self.active = True
        
        # Algorithm-specific properties
        self.properties = {}
    
    @abstractmethod
    def update_position(self, **kwargs) -> None:
        """Update agent position based on algorithm rules"""
        pass
    
    @abstractmethod
    def update_velocity(self, **kwargs) -> None:
        """Update agent velocity based on algorithm rules"""
        pass
    
    def evaluate_fitness(self, objective_function: Callable) -> float:
        """
        Evaluate agent fitness using objective function
        
        Args:
            objective_function: Function to minimize
            
        Returns:
            Fitness value
        """
        try:
            self.fitness = objective_function(self.position)
            if self.fitness < self.best_fitness:
                self.best_fitness = self.fitness
                self.best_position = self.position.copy()
            return self.fitness
        except Exception as e:
            logging.warning(f"Fitness evaluation failed: {e}")
            self.fitness = float('inf')
            return self.fitness
    
    def clip_to_bounds(self) -> None:
        """Ensure agent position stays within bounds"""
        self.position = np.clip(self.position, self.bounds[0], self.bounds[1])
    
    def reset(self) -> None:
        """Reset agent to initial state"""
        self.position = np.random.uniform(self.bounds[0], self.bounds[1], self.dimension)
        self.velocity = np.zeros(self.dimension)
        self.fitness = float('inf')
        self.best_position = self.position.copy()
        self.best_fitness = float('inf')
        self.age = 0
        self.active = True
        self.properties.clear()


class SwarmOptimizer(ABC):
    """
    Base class for swarm intelligence optimization algorithms
    
    Provides common functionality for managing populations, tracking
    convergence, and coordinating the optimization process.
    """
    
    def __init__(self, parameters: SwarmParameters):
        """
        Initialize swarm optimizer
        
        Args:
            parameters: Swarm configuration parameters
        """
        self.params = parameters
        self.agents: List[SwarmAgent] = []
        self.state = SwarmState.INITIALIZED
        self.iteration = 0
        self.start_time = 0.0
        self.convergence_history = []
        self.diversity_history = []
        
        # Best solution tracking
        self.global_best_position = None
        self.global_best_fitness = float('inf')
        self.global_best_agent = None
        
        # Statistics
        self.statistics = {
            'evaluations': 0,
            'convergence_iteration': None,
            'execution_time': 0.0,
            'success_rate': 0.0
        }
        
        # Set random seed if provided
        if parameters.random_seed is not None:
            np.random.seed(parameters.random_seed)
        
        # Initialize logging
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def initialize_population(self) -> None:
        """Initialize the swarm population"""
        pass
    
    @abstractmethod
    def update_agents(self, objective_function: Callable) -> None:
        """Update all agents according to algorithm rules"""
        pass
    
    def optimize(self, objective_function: Callable, 
                callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run the optimization process
        
        Args:
            objective_function: Function to minimize
            callback: Optional callback function called each iteration
            
        Returns:
            Optimization results dictionary
        """
        self.logger.info(f"Starting {self.__class__.__name__} optimization")
        self.start_time = time.time()
        self.state = SwarmState.RUNNING
        
        # Initialize population
        self.initialize_population()
        
        # Main optimization loop
        for self.iteration in range(self.params.max_iterations):
            # Update agents
            self.update_agents(objective_function)
            
            # Update global best
            self._update_global_best()
            
            # Check convergence
            if self._check_convergence():
                self.state = SwarmState.CONVERGED
                self.statistics['convergence_iteration'] = self.iteration
                break
            
            # Record metrics
            self._record_metrics()
            
            # Call callback if provided
            if callback:
                callback(self)
            
            # Verbose output
            if self.params.verbose and self.iteration % 10 == 0:
                self.logger.info(f"Iteration {self.iteration}: "
                               f"Best fitness = {self.global_best_fitness:.6f}")
        
        # Finalize optimization
        self._finalize_optimization()
        
        return self._get_results()
    
    def _update_global_best(self) -> None:
        """Update global best solution"""
        for agent in self.agents:
            if agent.best_fitness < self.global_best_fitness:
                self.global_best_fitness = agent.best_fitness
                self.global_best_position = agent.best_position.copy()
                self.global_best_agent = agent
    
    def _check_convergence(self) -> bool:
        """Check if optimization has converged"""
        if len(self.convergence_history) < 2:
            return False
        
        # Check if improvement is below threshold
        improvement = abs(self.convergence_history[-2] - self.convergence_history[-1])
        return improvement < self.params.convergence_threshold
    
    def _record_metrics(self) -> None:
        """Record optimization metrics"""
        self.convergence_history.append(self.global_best_fitness)
        
        # Calculate population diversity
        diversity = self._calculate_diversity()
        self.diversity_history.append(diversity)
    
    def _calculate_diversity(self) -> float:
        """Calculate population diversity"""
        if len(self.agents) < 2:
            return 0.0
        
        positions = np.array([agent.position for agent in self.agents])
        distances = []
        
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                distance = np.linalg.norm(positions[i] - positions[j])
                distances.append(distance)
        
        return np.mean(distances) if distances else 0.0
    
    def _finalize_optimization(self) -> None:
        """Finalize optimization process"""
        self.statistics['execution_time'] = time.time() - self.start_time
        self.statistics['evaluations'] = self.iteration * self.params.population_size
        
        if self.state != SwarmState.CONVERGED:
            self.state = SwarmState.TERMINATED
        
        self.logger.info(f"Optimization completed in {self.statistics['execution_time']:.2f}s")
        self.logger.info(f"Best fitness: {self.global_best_fitness:.6f}")
    
    def _get_results(self) -> Dict[str, Any]:
        """Get optimization results"""
        return {
            'best_position': self.global_best_position,
            'best_fitness': self.global_best_fitness,
            'convergence_history': self.convergence_history,
            'diversity_history': self.diversity_history,
            'statistics': self.statistics,
            'state': self.state,
            'iterations': self.iteration,
            'population_size': len(self.agents)
        }
    
    def get_population_state(self) -> Dict[str, Any]:
        """Get current population state"""
        return {
            'positions': [agent.position.tolist() for agent in self.agents],
            'fitness_values': [agent.fitness for agent in self.agents],
            'velocities': [agent.velocity.tolist() for agent in self.agents],
            'global_best': self.global_best_position.tolist() if self.global_best_position is not None else None,
            'global_best_fitness': self.global_best_fitness,
            'iteration': self.iteration,
            'diversity': self.diversity_history[-1] if self.diversity_history else 0.0
        }


class SwarmCoordinator(ABC):
    """
    Base class for coordinating multiple swarm optimizers
    
    Manages multiple swarm instances, coordinates their execution,
    and handles inter-swarm communication and cooperation.
    """
    
    def __init__(self, optimizers: List[SwarmOptimizer]):
        """
        Initialize swarm coordinator
        
        Args:
            optimizers: List of swarm optimizers to coordinate
        """
        self.optimizers = optimizers
        self.coordination_strategy = "independent"
        self.communication_interval = 10
        self.migration_rate = 0.1
        
        # Global tracking
        self.global_best_fitness = float('inf')
        self.global_best_position = None
        self.global_best_optimizer = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def coordinate_swarms(self, objective_function: Callable) -> Dict[str, Any]:
        """Coordinate multiple swarms"""
        pass
    
    @abstractmethod
    def exchange_information(self) -> None:
        """Exchange information between swarms"""
        pass
    
    def migrate_agents(self, source_idx: int, target_idx: int, count: int = 1) -> None:
        """
        Migrate agents between swarms
        
        Args:
            source_idx: Source swarm index
            target_idx: Target swarm index
            count: Number of agents to migrate
        """
        if (source_idx >= len(self.optimizers) or 
            target_idx >= len(self.optimizers) or
            source_idx == target_idx):
            return
        
        source_swarm = self.optimizers[source_idx]
        target_swarm = self.optimizers[target_idx]
        
        # Select best agents from source
        source_agents = sorted(source_swarm.agents, key=lambda x: x.fitness)
        agents_to_migrate = source_agents[:count]
        
        # Replace worst agents in target
        target_agents = sorted(target_swarm.agents, key=lambda x: x.fitness, reverse=True)
        
        for i in range(min(count, len(agents_to_migrate), len(target_agents))):
            # Copy agent properties
            target_agents[i].position = agents_to_migrate[i].position.copy()
            target_agents[i].velocity = agents_to_migrate[i].velocity.copy()
            target_agents[i].fitness = agents_to_migrate[i].fitness
            target_agents[i].best_position = agents_to_migrate[i].best_position.copy()
            target_agents[i].best_fitness = agents_to_migrate[i].best_fitness
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get coordination status"""
        return {
            'num_swarms': len(self.optimizers),
            'global_best_fitness': self.global_best_fitness,
            'global_best_position': self.global_best_position.tolist() if self.global_best_position is not None else None,
            'swarm_states': [opt.state.value for opt in self.optimizers],
            'coordination_strategy': self.coordination_strategy,
            'communication_interval': self.communication_interval,
            'migration_rate': self.migration_rate
        }