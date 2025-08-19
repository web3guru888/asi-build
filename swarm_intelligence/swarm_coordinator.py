"""
Swarm Intelligence Coordinator

This module provides a unified coordinator for managing multiple
swarm intelligence algorithms, handling their interactions, and
optimizing their collective performance.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple, Union
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum

from .base import SwarmOptimizer, SwarmParameters
from .ant_colony import AntColonyOptimizer
from .particle_swarm import ParticleSwarmOptimizer
from .bee_colony import ArtificialBeeColony
from .firefly import FireflyAlgorithm
from .bacterial_foraging import BacterialForagingOptimizer
from .grey_wolf import GreyWolfOptimizer
from .whale_optimization import WhaleOptimizationAlgorithm
from .cuckoo_search import CuckooSearch
from .bat_algorithm import BatAlgorithm
from .multi_agent import MultiAgentCoordinator


class CoordinationStrategy(Enum):
    """Strategies for coordinating multiple swarms"""
    INDEPENDENT = "independent"           # Swarms run independently
    COOPERATIVE = "cooperative"           # Swarms share information
    COMPETITIVE = "competitive"           # Swarms compete for resources
    HIERARCHICAL = "hierarchical"         # Hierarchical coordination
    ADAPTIVE = "adaptive"                # Strategy adapts based on performance
    HYBRID = "hybrid"                    # Combination of strategies


class PerformanceMetric(Enum):
    """Performance metrics for swarm evaluation"""
    CONVERGENCE_SPEED = "convergence_speed"
    SOLUTION_QUALITY = "solution_quality"
    DIVERSITY = "diversity"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    SCALABILITY = "scalability"


@dataclass
class SwarmConfiguration:
    """Configuration for a swarm in the coordinator"""
    algorithm_type: str
    parameters: SwarmParameters
    weight: float = 1.0
    priority: int = 1
    active: bool = True
    resource_allocation: float = 1.0


class SwarmIntelligenceCoordinator:
    """
    Master coordinator for multiple swarm intelligence algorithms
    
    Manages multiple swarm optimizers, coordinates their execution,
    handles information exchange, and optimizes collective performance.
    """
    
    def __init__(self, swarm_configs: List[SwarmConfiguration]):
        """
        Initialize the swarm intelligence coordinator
        
        Args:
            swarm_configs: List of swarm configurations
        """
        self.swarm_configs = swarm_configs
        self.swarms: Dict[str, SwarmOptimizer] = {}
        self.coordination_strategy = CoordinationStrategy.ADAPTIVE
        
        # Coordination state
        self.global_best_position = None
        self.global_best_fitness = float('inf')
        self.global_best_swarm = None
        
        # Performance tracking
        self.performance_history = []
        self.convergence_tracking = []
        self.diversity_tracking = []
        self.efficiency_tracking = []
        
        # Resource management
        self.resource_pool = {
            'cpu_cores': 4,
            'memory_mb': 1024,
            'evaluations_budget': 100000
        }
        self.resource_allocation = {}
        
        # Communication and synchronization
        self.information_exchange_interval = 10
        self.migration_interval = 50
        self.migration_rate = 0.1
        
        # Adaptive parameters
        self.strategy_adaptation_enabled = True
        self.performance_window = 20
        self.adaptation_threshold = 0.05
        
        # Initialize logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize swarms
        self._initialize_swarms()
    
    def _initialize_swarms(self) -> None:
        """Initialize swarm optimizers from configurations"""
        algorithm_map = {
            'ant_colony': AntColonyOptimizer,
            'particle_swarm': ParticleSwarmOptimizer,
            'bee_colony': ArtificialBeeColony,
            'firefly': FireflyAlgorithm,
            'bacterial_foraging': BacterialForagingOptimizer,
            'grey_wolf': GreyWolfOptimizer,
            'whale_optimization': WhaleOptimizationAlgorithm,
            'cuckoo_search': CuckooSearch,
            'bat_algorithm': BatAlgorithm
        }
        
        for i, config in enumerate(self.swarm_configs):
            swarm_id = f"{config.algorithm_type}_{i}"
            
            if config.algorithm_type in algorithm_map:
                algorithm_class = algorithm_map[config.algorithm_type]
                swarm = algorithm_class(config.parameters)
                self.swarms[swarm_id] = swarm
                
                # Allocate resources
                self.resource_allocation[swarm_id] = config.resource_allocation
                
                self.logger.info(f"Initialized {config.algorithm_type} swarm: {swarm_id}")
            else:
                self.logger.warning(f"Unknown algorithm type: {config.algorithm_type}")
        
        self.logger.info(f"Coordinator initialized with {len(self.swarms)} swarms")
    
    def optimize(self, objective_function: Callable, 
                max_iterations: int = 1000,
                parallel_execution: bool = True) -> Dict[str, Any]:
        """
        Run coordinated optimization across all swarms
        
        Args:
            objective_function: Function to optimize
            max_iterations: Maximum number of iterations
            parallel_execution: Whether to run swarms in parallel
            
        Returns:
            Optimization results dictionary
        """
        self.logger.info("Starting coordinated swarm optimization")
        start_time = time.time()
        
        # Initialize all swarms
        for swarm in self.swarms.values():
            swarm.initialize_population()
        
        # Main optimization loop
        for iteration in range(max_iterations):
            iteration_start = time.time()
            
            # Execute swarm updates
            if parallel_execution:
                self._parallel_swarm_update(objective_function)
            else:
                self._sequential_swarm_update(objective_function)
            
            # Update global best
            self._update_global_best()
            
            # Coordinate swarms
            self._coordinate_swarms(iteration)
            
            # Record performance metrics
            self._record_performance_metrics(iteration)
            
            # Adaptive strategy adjustment
            if self.strategy_adaptation_enabled:
                self._adapt_coordination_strategy(iteration)
            
            # Progress logging
            if iteration % 100 == 0:
                self.logger.info(f"Iteration {iteration}: Global best = {self.global_best_fitness:.6f}")
            
            # Early termination check
            if self._check_termination_criteria():
                self.logger.info(f"Early termination at iteration {iteration}")
                break
        
        # Finalize optimization
        execution_time = time.time() - start_time
        results = self._compile_final_results(execution_time, iteration + 1)
        
        self.logger.info(f"Optimization completed in {execution_time:.2f} seconds")
        return results
    
    def _parallel_swarm_update(self, objective_function: Callable) -> None:
        """Update all swarms in parallel"""
        with ThreadPoolExecutor(max_workers=min(len(self.swarms), 4)) as executor:
            future_to_swarm = {
                executor.submit(swarm.update_agents, objective_function): swarm_id
                for swarm_id, swarm in self.swarms.items()
                if self.swarm_configs[0].active  # Simplified check
            }
            
            for future in as_completed(future_to_swarm):
                swarm_id = future_to_swarm[future]
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Error in swarm {swarm_id}: {e}")
    
    def _sequential_swarm_update(self, objective_function: Callable) -> None:
        """Update all swarms sequentially"""
        for swarm_id, swarm in self.swarms.items():
            try:
                swarm.update_agents(objective_function)
            except Exception as e:
                self.logger.error(f"Error in swarm {swarm_id}: {e}")
    
    def _update_global_best(self) -> None:
        """Update global best solution across all swarms"""
        for swarm_id, swarm in self.swarms.items():
            if swarm.global_best_fitness < self.global_best_fitness:
                self.global_best_fitness = swarm.global_best_fitness
                self.global_best_position = swarm.global_best_position.copy()
                self.global_best_swarm = swarm_id
    
    def _coordinate_swarms(self, iteration: int) -> None:
        """Coordinate interactions between swarms"""
        if self.coordination_strategy == CoordinationStrategy.INDEPENDENT:
            return  # No coordination needed
        
        elif self.coordination_strategy == CoordinationStrategy.COOPERATIVE:
            self._cooperative_coordination(iteration)
        
        elif self.coordination_strategy == CoordinationStrategy.COMPETITIVE:
            self._competitive_coordination(iteration)
        
        elif self.coordination_strategy == CoordinationStrategy.HIERARCHICAL:
            self._hierarchical_coordination(iteration)
        
        elif self.coordination_strategy == CoordinationStrategy.ADAPTIVE:
            self._adaptive_coordination(iteration)
        
        elif self.coordination_strategy == CoordinationStrategy.HYBRID:
            self._hybrid_coordination(iteration)
    
    def _cooperative_coordination(self, iteration: int) -> None:
        """Implement cooperative coordination strategy"""
        # Information exchange between swarms
        if iteration % self.information_exchange_interval == 0:
            self._exchange_global_best_information()
        
        # Migration of best solutions
        if iteration % self.migration_interval == 0:
            self._migrate_best_solutions()
    
    def _competitive_coordination(self, iteration: int) -> None:
        """Implement competitive coordination strategy"""
        # Allocate resources based on performance
        self._reallocate_resources_by_performance()
        
        # Only best performing swarms continue
        self._activate_top_performing_swarms()
    
    def _hierarchical_coordination(self, iteration: int) -> None:
        """Implement hierarchical coordination strategy"""
        # Master swarm directs others
        master_swarm_id = self.global_best_swarm
        if master_swarm_id:
            master_swarm = self.swarms[master_swarm_id]
            
            # Other swarms receive guidance from master
            for swarm_id, swarm in self.swarms.items():
                if swarm_id != master_swarm_id:
                    self._apply_master_guidance(swarm, master_swarm)
    
    def _adaptive_coordination(self, iteration: int) -> None:
        """Implement adaptive coordination strategy"""
        # Analyze performance and adapt strategy
        if iteration > self.performance_window:
            performance_trend = self._analyze_performance_trend()
            
            if performance_trend < -self.adaptation_threshold:
                # Poor performance - switch to cooperative
                self._cooperative_coordination(iteration)
            elif performance_trend > self.adaptation_threshold:
                # Good performance - continue current strategy
                pass
            else:
                # Stable performance - try competitive
                self._competitive_coordination(iteration)
    
    def _hybrid_coordination(self, iteration: int) -> None:
        """Implement hybrid coordination strategy"""
        # Combine multiple strategies
        if iteration % 2 == 0:
            self._cooperative_coordination(iteration)
        else:
            self._competitive_coordination(iteration)
    
    def _exchange_global_best_information(self) -> None:
        """Exchange global best information between swarms"""
        for swarm in self.swarms.values():
            if self.global_best_position is not None:
                # Update swarm's knowledge of global best
                if hasattr(swarm, 'global_best_position'):
                    if self.global_best_fitness < swarm.global_best_fitness:
                        swarm.global_best_position = self.global_best_position.copy()
                        swarm.global_best_fitness = self.global_best_fitness
    
    def _migrate_best_solutions(self) -> None:
        """Migrate best solutions between swarms"""
        swarm_list = list(self.swarms.values())
        
        for i, source_swarm in enumerate(swarm_list):
            target_swarm = swarm_list[(i + 1) % len(swarm_list)]
            
            # Migrate best agents
            num_migrants = max(1, int(len(source_swarm.agents) * self.migration_rate))
            
            # Sort agents by fitness
            source_agents = sorted(source_swarm.agents, key=lambda a: a.fitness)
            target_agents = sorted(target_swarm.agents, key=lambda a: a.fitness, reverse=True)
            
            # Replace worst target agents with best source agents
            for j in range(min(num_migrants, len(source_agents), len(target_agents))):
                target_agents[j].position = source_agents[j].position.copy()
                target_agents[j].fitness = source_agents[j].fitness
                target_agents[j].best_position = source_agents[j].best_position.copy()
                target_agents[j].best_fitness = source_agents[j].best_fitness
    
    def _reallocate_resources_by_performance(self) -> None:
        """Reallocate resources based on swarm performance"""
        # Calculate performance scores
        performance_scores = {}
        for swarm_id, swarm in self.swarms.items():
            score = 1.0 / (1.0 + swarm.global_best_fitness) if swarm.global_best_fitness != float('inf') else 0.0
            performance_scores[swarm_id] = score
        
        # Normalize scores
        total_score = sum(performance_scores.values())
        if total_score > 0:
            for swarm_id in performance_scores:
                normalized_score = performance_scores[swarm_id] / total_score
                self.resource_allocation[swarm_id] = normalized_score
    
    def _activate_top_performing_swarms(self, top_k: int = 3) -> None:
        """Activate only top performing swarms"""
        # Sort swarms by performance
        swarm_performance = [
            (swarm_id, swarm.global_best_fitness)
            for swarm_id, swarm in self.swarms.items()
        ]
        swarm_performance.sort(key=lambda x: x[1])
        
        # Activate top k swarms
        for i, (swarm_id, _) in enumerate(swarm_performance):
            config_idx = int(swarm_id.split('_')[-1])
            self.swarm_configs[config_idx].active = i < top_k
    
    def _apply_master_guidance(self, follower_swarm: SwarmOptimizer, 
                              master_swarm: SwarmOptimizer) -> None:
        """Apply guidance from master swarm to follower"""
        # Guide some agents towards master's best position
        guidance_rate = 0.1
        num_guided = max(1, int(len(follower_swarm.agents) * guidance_rate))
        
        # Select random agents to guide
        guided_agents = np.random.choice(follower_swarm.agents, size=num_guided, replace=False)
        
        for agent in guided_agents:
            # Move towards master's best position
            direction = master_swarm.global_best_position - agent.position
            step_size = 0.1
            agent.position += step_size * direction
            agent.clip_to_bounds()
    
    def _analyze_performance_trend(self) -> float:
        """Analyze recent performance trend"""
        if len(self.performance_history) < self.performance_window:
            return 0.0
        
        recent_performance = self.performance_history[-self.performance_window:]
        trend = np.polyfit(range(len(recent_performance)), recent_performance, 1)[0]
        return trend
    
    def _record_performance_metrics(self, iteration: int) -> None:
        """Record performance metrics for analysis"""
        # Overall performance
        self.performance_history.append(self.global_best_fitness)
        
        # Convergence tracking
        if len(self.performance_history) > 1:
            improvement = self.performance_history[-2] - self.performance_history[-1]
            self.convergence_tracking.append(improvement)
        
        # Diversity tracking
        diversity = self._calculate_swarm_diversity()
        self.diversity_tracking.append(diversity)
        
        # Efficiency tracking
        efficiency = self._calculate_coordination_efficiency()
        self.efficiency_tracking.append(efficiency)
    
    def _calculate_swarm_diversity(self) -> float:
        """Calculate diversity across all swarms"""
        all_positions = []
        for swarm in self.swarms.values():
            if hasattr(swarm, 'agents'):
                all_positions.extend([agent.position for agent in swarm.agents])
        
        if len(all_positions) < 2:
            return 0.0
        
        positions_array = np.array(all_positions)
        centroid = np.mean(positions_array, axis=0)
        distances = [np.linalg.norm(pos - centroid) for pos in positions_array]
        return np.mean(distances)
    
    def _calculate_coordination_efficiency(self) -> float:
        """Calculate coordination efficiency"""
        # Simple metric based on resource utilization
        active_swarms = sum(1 for config in self.swarm_configs if config.active)
        total_swarms = len(self.swarm_configs)
        return active_swarms / max(1, total_swarms)
    
    def _adapt_coordination_strategy(self, iteration: int) -> None:
        """Adapt coordination strategy based on performance"""
        if iteration < self.performance_window:
            return
        
        performance_trend = self._analyze_performance_trend()
        current_diversity = self.diversity_tracking[-1] if self.diversity_tracking else 0.0
        
        # Strategy adaptation logic
        if performance_trend < -0.01:  # Poor convergence
            if current_diversity < 0.5:  # Low diversity
                self.coordination_strategy = CoordinationStrategy.COOPERATIVE
            else:
                self.coordination_strategy = CoordinationStrategy.COMPETITIVE
        elif performance_trend > 0.01:  # Good convergence
            self.coordination_strategy = CoordinationStrategy.HIERARCHICAL
        else:  # Stable performance
            self.coordination_strategy = CoordinationStrategy.ADAPTIVE
    
    def _check_termination_criteria(self) -> bool:
        """Check if optimization should terminate early"""
        # Convergence criterion
        if len(self.convergence_tracking) > 50:
            recent_improvements = self.convergence_tracking[-50:]
            avg_improvement = np.mean(recent_improvements)
            if avg_improvement < 1e-8:
                return True
        
        # Diversity criterion
        if len(self.diversity_tracking) > 20:
            recent_diversity = self.diversity_tracking[-20:]
            if np.mean(recent_diversity) < 1e-6:
                return True
        
        return False
    
    def _compile_final_results(self, execution_time: float, iterations: int) -> Dict[str, Any]:
        """Compile final optimization results"""
        return {
            'global_best_position': self.global_best_position.tolist() if self.global_best_position is not None else None,
            'global_best_fitness': self.global_best_fitness,
            'global_best_swarm': self.global_best_swarm,
            'execution_time': execution_time,
            'iterations': iterations,
            'convergence_history': self.performance_history,
            'diversity_history': self.diversity_tracking,
            'efficiency_history': self.efficiency_tracking,
            'final_coordination_strategy': self.coordination_strategy.value,
            'swarm_results': {
                swarm_id: {
                    'best_fitness': swarm.global_best_fitness,
                    'best_position': swarm.global_best_position.tolist() if swarm.global_best_position is not None else None,
                    'convergence_history': swarm.convergence_history[-100:],  # Last 100 iterations
                    'final_diversity': swarm.diversity_history[-1] if swarm.diversity_history else 0.0
                }
                for swarm_id, swarm in self.swarms.items()
            },
            'resource_allocation': dict(self.resource_allocation),
            'performance_metrics': {
                'final_performance': self.performance_history[-1] if self.performance_history else float('inf'),
                'convergence_rate': np.mean(self.convergence_tracking[-50:]) if len(self.convergence_tracking) >= 50 else 0.0,
                'average_diversity': np.mean(self.diversity_tracking) if self.diversity_tracking else 0.0,
                'coordination_efficiency': np.mean(self.efficiency_tracking) if self.efficiency_tracking else 0.0
            }
        }
    
    def get_swarm_status(self) -> Dict[str, Any]:
        """Get current status of all swarms"""
        return {
            'coordinator_strategy': self.coordination_strategy.value,
            'global_best_fitness': self.global_best_fitness,
            'global_best_swarm': self.global_best_swarm,
            'active_swarms': sum(1 for config in self.swarm_configs if config.active),
            'total_swarms': len(self.swarms),
            'resource_allocation': dict(self.resource_allocation),
            'swarm_details': {
                swarm_id: {
                    'algorithm_type': swarm.__class__.__name__,
                    'population_size': len(swarm.agents) if hasattr(swarm, 'agents') else 0,
                    'current_best': swarm.global_best_fitness,
                    'iteration': swarm.iteration if hasattr(swarm, 'iteration') else 0,
                    'state': swarm.state.value if hasattr(swarm, 'state') else 'unknown'
                }
                for swarm_id, swarm in self.swarms.items()
            },
            'performance_trend': self._analyze_performance_trend() if len(self.performance_history) >= self.performance_window else 0.0,
            'current_diversity': self.diversity_tracking[-1] if self.diversity_tracking else 0.0
        }
    
    def add_swarm(self, config: SwarmConfiguration) -> str:
        """Add a new swarm to the coordinator"""
        swarm_id = f"{config.algorithm_type}_{len(self.swarms)}"
        
        # Create swarm instance (simplified)
        # In practice, you'd use the algorithm_map from _initialize_swarms
        self.swarm_configs.append(config)
        self.resource_allocation[swarm_id] = config.resource_allocation
        
        self.logger.info(f"Added new swarm: {swarm_id}")
        return swarm_id
    
    def remove_swarm(self, swarm_id: str) -> bool:
        """Remove a swarm from the coordinator"""
        if swarm_id in self.swarms:
            del self.swarms[swarm_id]
            del self.resource_allocation[swarm_id]
            self.logger.info(f"Removed swarm: {swarm_id}")
            return True
        return False
    
    def pause_swarm(self, swarm_id: str) -> bool:
        """Pause a specific swarm"""
        if swarm_id in self.swarms:
            # Find corresponding config
            for config in self.swarm_configs:
                if f"{config.algorithm_type}_" in swarm_id:
                    config.active = False
                    break
            return True
        return False
    
    def resume_swarm(self, swarm_id: str) -> bool:
        """Resume a paused swarm"""
        if swarm_id in self.swarms:
            # Find corresponding config
            for config in self.swarm_configs:
                if f"{config.algorithm_type}_" in swarm_id:
                    config.active = True
                    break
            return True
        return False


# Factory function for easy instantiation
def create_swarm_intelligence_coordinator(algorithms: List[str],
                                         population_size: int = 50,
                                         max_iterations: int = 1000,
                                         dimension: int = 2,
                                         bounds: Tuple[float, float] = (-10.0, 10.0)) -> SwarmIntelligenceCoordinator:
    """
    Create a swarm intelligence coordinator with specified algorithms
    
    Args:
        algorithms: List of algorithm names to include
        population_size: Population size for each swarm
        max_iterations: Maximum iterations for optimization
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured SwarmIntelligenceCoordinator instance
    """
    configs = []
    
    for algorithm in algorithms:
        params = SwarmParameters(
            population_size=population_size,
            max_iterations=max_iterations,
            dimension=dimension,
            bounds=bounds
        )
        
        config = SwarmConfiguration(
            algorithm_type=algorithm,
            parameters=params,
            weight=1.0,
            priority=1,
            active=True,
            resource_allocation=1.0 / len(algorithms)
        )
        configs.append(config)
    
    return SwarmIntelligenceCoordinator(configs)