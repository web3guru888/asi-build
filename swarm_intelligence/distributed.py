"""
Distributed Swarm Computing

This module implements distributed computing capabilities for
swarm intelligence algorithms, enabling parallel execution
across multiple processes and machines.
"""

import multiprocessing as mp
import time
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle
import logging
from .base import SwarmOptimizer


class DistributedSwarmManager:
    """Manager for distributed swarm computing"""
    
    def __init__(self, num_processes: int = None):
        self.num_processes = num_processes or mp.cpu_count()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parallel_optimize(self, swarms: List[SwarmOptimizer], 
                         objective_function: Callable,
                         iterations: int = 100) -> Dict[str, Any]:
        """Run multiple swarms in parallel"""
        
        with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
            # Submit swarm optimization tasks
            futures = {}
            for i, swarm in enumerate(swarms):
                future = executor.submit(
                    self._optimize_single_swarm, 
                    swarm, objective_function, iterations
                )
                futures[future] = f"swarm_{i}"
            
            # Collect results
            results = {}
            for future in as_completed(futures):
                swarm_id = futures[future]
                try:
                    result = future.result()
                    results[swarm_id] = result
                except Exception as e:
                    self.logger.error(f"Swarm {swarm_id} failed: {e}")
                    results[swarm_id] = None
        
        return results
    
    def _optimize_single_swarm(self, swarm: SwarmOptimizer, 
                              objective_function: Callable,
                              iterations: int) -> Dict[str, Any]:
        """Optimize a single swarm (used in subprocess)"""
        try:
            swarm.initialize_population()
            
            for _ in range(iterations):
                swarm.update_agents(objective_function)
            
            return {
                'best_fitness': swarm.global_best_fitness,
                'best_position': swarm.global_best_position.tolist() if swarm.global_best_position is not None else None,
                'convergence_history': swarm.convergence_history,
                'success': True
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class DistributedSwarmComputing:
    """Advanced distributed computing for swarm intelligence"""
    
    def __init__(self):
        self.manager = DistributedSwarmManager()
        self.results_cache = {}
    
    def distributed_benchmark(self, algorithms: List[str],
                            test_functions: List[Callable],
                            num_runs: int = 10) -> Dict[str, Any]:
        """Run distributed benchmark across algorithms and functions"""
        all_results = {}
        
        for algo_name in algorithms:
            for i, test_func in enumerate(test_functions):
                # Create multiple swarm instances for parallel runs
                swarms = []  # Would create actual swarm instances
                
                # Run parallel optimization
                results = self.manager.parallel_optimize(swarms, test_func, 100)
                
                all_results[f"{algo_name}_func_{i}"] = results
        
        return all_results


# Factory function
def create_distributed_swarm_computing(num_processes: int = None) -> DistributedSwarmComputing:
    """Create distributed swarm computing system"""
    return DistributedSwarmComputing()