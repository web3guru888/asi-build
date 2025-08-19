"""
Whale Optimization Algorithm (WOA)

This module implements the Whale Optimization Algorithm, inspired by the
social behavior of humpback whales. It includes encircling prey, bubble-net
attacking method (exploitation), and search for prey (exploration).
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class WhaleHuntingPhase(Enum):
    """Whale hunting behavior phases"""
    ENCIRCLING = "encircling"          # Encircling prey
    BUBBLE_NET = "bubble_net"          # Bubble-net feeding
    SEARCH = "search"                  # Searching for prey
    SPIRAL_UPDATE = "spiral_update"    # Spiral bubble-net feeding


@dataclass
class WOAParameters(SwarmParameters):
    """Whale Optimization Algorithm specific parameters"""
    # Algorithm parameters
    a_max: float = 2.0              # Maximum value of 'a'
    a_min: float = 0.0              # Minimum value of 'a'
    b: float = 1.0                  # Constant for spiral equation
    l_min: float = -1.0             # Minimum value for spiral parameter
    l_max: float = 1.0              # Maximum value for spiral parameter
    
    # Behavioral parameters
    bubble_net_probability: float = 0.5     # Probability of bubble-net feeding
    spiral_constant: float = 1.0            # Spiral shape constant
    
    # Advanced parameters
    adaptive_parameters: bool = True         # Enable adaptive parameter tuning
    levy_flight_search: bool = True          # Enable Levy flight in search phase
    social_learning: bool = True             # Enable social learning
    memory_capacity: int = 10                # Memory capacity for whales


class Whale(SwarmAgent):
    """
    Individual whale agent
    
    Each whale can perform encircling, bubble-net feeding, and
    searching behaviors based on the hunting strategy.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Whale behavior state
        self.hunting_phase = WhaleHuntingPhase.SEARCH
        self.bubble_net_skill = np.random.random()
        self.diving_depth = 0.0
        self.song_frequency = np.random.uniform(20, 20000)  # Hz
        
        # Memory and learning
        self.memory = []
        self.social_connections = []
        self.learning_rate = np.random.uniform(0.1, 0.5)
        
        # Physical characteristics
        self.body_length = np.random.uniform(12, 16)  # meters
        self.swimming_speed = np.random.uniform(5, 15)  # km/h
        self.energy_level = 100.0
        
        # Whale-specific properties
        self.properties.update({
            'echolocation_ability': np.random.uniform(0.7, 1.0),
            'social_cooperation': np.random.uniform(0.5, 1.0),
            'hunting_experience': np.random.uniform(0.3, 0.8),
            'navigation_skill': np.random.uniform(0.6, 1.0),
            'communication_range': np.random.uniform(1000, 5000)  # meters
        })
    
    def update_position(self, best_whale_position: Optional[np.ndarray] = None,
                       random_whale_position: Optional[np.ndarray] = None,
                       a_value: float = 2.0, l_value: float = 0.0,
                       p_value: float = 0.5, **kwargs) -> None:
        """
        Update whale position based on hunting behavior
        
        Args:
            best_whale_position: Position of the best whale (prey)
            random_whale_position: Position of a random whale
            a_value: Current value of parameter 'a'
            l_value: Spiral parameter value
            p_value: Random value for phase selection
        """
        if best_whale_position is None:
            # No best position - random search
            self._random_search_movement(a_value)
            return
        
        # Select hunting behavior based on probability
        if p_value < 0.5:
            # Encircling prey or search for prey
            if abs(a_value) < 1:
                # Encircling prey (exploitation)
                self._encircling_prey(best_whale_position, a_value)
                self.hunting_phase = WhaleHuntingPhase.ENCIRCLING
            else:
                # Search for prey (exploration)
                self._search_for_prey(random_whale_position, a_value)
                self.hunting_phase = WhaleHuntingPhase.SEARCH
        else:
            # Spiral bubble-net feeding method
            self._spiral_bubble_net_feeding(best_whale_position, l_value)
            self.hunting_phase = WhaleHuntingPhase.SPIRAL_UPDATE
        
        self.clip_to_bounds()
        self.age += 1
        self._update_energy()
    
    def update_velocity(self, **kwargs) -> None:
        """Update whale velocity based on swimming behavior"""
        current_speed = kwargs.get('current_speed', self.swimming_speed)
        water_resistance = kwargs.get('water_resistance', 0.1)
        
        # Update velocity based on swimming dynamics
        self.velocity = (1 - water_resistance) * self.velocity
        
        # Add propulsion based on hunting phase
        if self.hunting_phase == WhaleHuntingPhase.ENCIRCLING:
            # Slower, more controlled movement
            propulsion = 0.5 * current_speed
        elif self.hunting_phase == WhaleHuntingPhase.SEARCH:
            # Faster exploration movement
            propulsion = 1.2 * current_speed
        else:  # SPIRAL_UPDATE
            # Variable speed for spiral movement
            propulsion = 0.8 * current_speed
        
        # Add random component for realistic swimming
        random_component = 0.1 * np.random.randn(self.dimension)
        self.velocity += propulsion * random_component / self.dimension
    
    def _encircling_prey(self, prey_position: np.ndarray, a_value: float) -> None:
        """Encircling prey behavior (exploitation)"""
        # Calculate distance to prey
        r1 = np.random.random(self.dimension)
        r2 = np.random.random(self.dimension)
        
        A = 2 * a_value * r1 - a_value
        C = 2 * r2
        
        D = np.abs(C * prey_position - self.position)
        self.position = prey_position - A * D
    
    def _search_for_prey(self, random_position: Optional[np.ndarray], a_value: float) -> None:
        """Search for prey behavior (exploration)"""
        if random_position is None:
            # Random search if no reference position
            self._random_search_movement(a_value)
            return
        
        r1 = np.random.random(self.dimension)
        r2 = np.random.random(self.dimension)
        
        A = 2 * a_value * r1 - a_value
        C = 2 * r2
        
        D = np.abs(C * random_position - self.position)
        self.position = random_position - A * D
    
    def _spiral_bubble_net_feeding(self, prey_position: np.ndarray, l_value: float) -> None:
        """Spiral bubble-net feeding behavior"""
        # Calculate distance to prey
        distance = np.abs(prey_position - self.position)
        
        # Spiral equation: X(t+1) = D' * e^(bl) * cos(2πl) + X*(t)
        b = 1.0  # Shape constant for spiral
        
        # Create spiral movement
        spiral_term = distance * np.exp(b * l_value) * np.cos(2 * np.pi * l_value)
        self.position = spiral_term + prey_position
    
    def _random_search_movement(self, a_value: float) -> None:
        """Random search movement when no reference available"""
        # Random movement with decreasing amplitude
        random_step = a_value * np.random.uniform(-1, 1, self.dimension)
        self.position += random_step
    
    def _update_energy(self) -> None:
        """Update whale energy based on activity"""
        # Energy consumption based on hunting phase
        if self.hunting_phase == WhaleHuntingPhase.SEARCH:
            energy_cost = 2.0  # High energy for exploration
        elif self.hunting_phase == WhaleHuntingPhase.ENCIRCLING:
            energy_cost = 1.0  # Moderate energy for encircling
        else:  # SPIRAL_UPDATE
            energy_cost = 1.5  # High energy for complex maneuvers
        
        self.energy_level = max(0, self.energy_level - energy_cost * 0.1)
        
        # Gradual energy recovery
        if self.energy_level < 50:
            self.energy_level += 0.5
    
    def communicate_with_pod(self) -> Dict[str, Any]:
        """Communicate with other whales in pod"""
        return {
            'whale_id': id(self),
            'position': self.position.copy(),
            'fitness': self.fitness,
            'hunting_phase': self.hunting_phase.value,
            'energy_level': self.energy_level,
            'song_frequency': self.song_frequency,
            'bubble_net_skill': self.bubble_net_skill
        }
    
    def learn_from_pod(self, pod_information: List[Dict[str, Any]]) -> None:
        """Learn from other whales in the pod"""
        if not pod_information:
            return
        
        # Learn from successful whales
        successful_whales = [info for info in pod_information 
                           if info['fitness'] < self.fitness]
        
        if successful_whales:
            # Select best whale to learn from
            best_whale = min(successful_whales, key=lambda x: x['fitness'])
            
            # Social learning - adjust behavior based on successful whale
            learning_factor = self.learning_rate * self.properties['social_cooperation']
            
            # Adjust bubble net skill
            skill_diff = best_whale['bubble_net_skill'] - self.bubble_net_skill
            self.bubble_net_skill += learning_factor * skill_diff
            self.bubble_net_skill = np.clip(self.bubble_net_skill, 0, 1)
    
    def perform_echolocation(self, target_position: np.ndarray) -> Dict[str, float]:
        """Perform echolocation to assess environment"""
        distance = np.linalg.norm(target_position - self.position)
        
        # Echolocation accuracy based on whale's ability
        accuracy = self.properties['echolocation_ability']
        detected_distance = distance * (1 + 0.1 * (1 - accuracy) * np.random.randn())
        
        return {
            'detected_distance': max(0, detected_distance),
            'confidence': accuracy,
            'signal_strength': accuracy / (1 + distance * 0.1)
        }
    
    def add_to_memory(self, experience: Dict[str, Any]) -> None:
        """Add experience to whale's memory"""
        self.memory.append(experience)
        
        # Limit memory size
        if len(self.memory) > 10:  # Memory capacity
            self.memory.pop(0)
    
    def recall_best_experience(self) -> Optional[np.ndarray]:
        """Recall best position from memory"""
        if not self.memory:
            return None
        
        best_experience = min(self.memory, key=lambda x: x.get('fitness', float('inf')))
        return best_experience.get('position')


class WhaleOptimizationAlgorithm(SwarmOptimizer):
    """
    Whale Optimization Algorithm implementation
    
    Implements the complete WOA algorithm with encircling prey,
    bubble-net feeding, and search behaviors.
    """
    
    def __init__(self, parameters: WOAParameters):
        super().__init__(parameters)
        self.woa_params = parameters
        
        # Algorithm state
        self.current_a = parameters.a_max
        
        # Pod behavior tracking
        self.pod_communications = []
        self.hunting_phase_distribution = []
        self.echolocation_data = []
        
        # Performance metrics
        self.convergence_rate_history = []
        self.exploration_exploitation_balance = []
        
        # Best whale tracking
        self.best_whale = None
    
    def initialize_population(self) -> None:
        """Initialize whale pod"""
        self.agents = [
            Whale(self.params.dimension, self.params.bounds)
            for _ in range(self.params.population_size)
        ]
        
        # Establish social connections
        for whale in self.agents:
            # Each whale connects to a few others
            num_connections = min(5, len(self.agents) - 1)
            connections = np.random.choice(
                [w for w in self.agents if w != whale],
                size=num_connections,
                replace=False
            )
            whale.social_connections = list(connections)
        
        self.logger.info(f"Initialized pod of {len(self.agents)} whales")
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all whales in the pod"""
        # Evaluate all whales
        for whale in self.agents:
            whale.evaluate_fitness(objective_function)
        
        # Find best whale
        self.best_whale = min(self.agents, key=lambda w: w.fitness)
        
        # Update parameter 'a'
        self._update_a_parameter()
        
        # Pod communication and learning
        if self.woa_params.social_learning:
            self._handle_pod_communication()
        
        # Update whale positions
        self._update_whale_positions()
        
        # Adaptive parameter tuning
        if self.woa_params.adaptive_parameters:
            self._adaptive_parameter_tuning()
        
        # Record performance metrics
        self._record_woa_metrics()
    
    def _update_a_parameter(self) -> None:
        """Update parameter 'a' linearly from a_max to a_min"""
        self.current_a = (self.woa_params.a_max - 
                         (self.iteration / self.params.max_iterations) * 
                         (self.woa_params.a_max - self.woa_params.a_min))
    
    def _handle_pod_communication(self) -> None:
        """Handle communication between whales in the pod"""
        # Collect communication data
        pod_info = [whale.communicate_with_pod() for whale in self.agents]
        
        # Share information among connected whales
        for whale in self.agents:
            # Get information from social connections
            connection_info = []
            for connection in whale.social_connections:
                for info in pod_info:
                    if info['whale_id'] == id(connection):
                        connection_info.append(info)
            
            # Learn from connections
            whale.learn_from_pod(connection_info)
        
        # Record communication activity
        self.pod_communications.append({
            'iteration': self.iteration,
            'total_communications': len(pod_info),
            'average_energy': np.mean([info['energy_level'] for info in pod_info]),
            'phase_distribution': self._calculate_phase_distribution(pod_info)
        })
    
    def _update_whale_positions(self) -> None:
        """Update positions of all whales"""
        for whale in self.agents:
            # Select random whale for search phase
            random_whale = np.random.choice([w for w in self.agents if w != whale])
            
            # Generate random parameters
            l_value = np.random.uniform(self.woa_params.l_min, self.woa_params.l_max)
            p_value = np.random.random()
            
            # Update position
            whale.update_position(
                best_whale_position=self.best_whale.position,
                random_whale_position=random_whale.position,
                a_value=self.current_a,
                l_value=l_value,
                p_value=p_value
            )
            
            # Update velocity
            whale.update_velocity()
            
            # Add experience to memory
            if self.woa_params.memory_capacity > 0:
                experience = {
                    'position': whale.position.copy(),
                    'fitness': whale.fitness,
                    'iteration': self.iteration
                }
                whale.add_to_memory(experience)
    
    def _adaptive_parameter_tuning(self) -> None:
        """Adaptively tune algorithm parameters"""
        # Analyze convergence rate
        if len(self.convergence_history) > 10:
            recent_improvement = (self.convergence_history[-10] - 
                                self.convergence_history[-1])
            
            # Adjust bubble-net probability based on convergence
            if recent_improvement < 1e-6:
                # Poor convergence - increase exploration
                self.woa_params.bubble_net_probability = max(
                    0.3, self.woa_params.bubble_net_probability - 0.05
                )
            else:
                # Good convergence - maintain current strategy
                self.woa_params.bubble_net_probability = min(
                    0.7, self.woa_params.bubble_net_probability + 0.02
                )
    
    def _calculate_phase_distribution(self, pod_info: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of hunting phases"""
        phase_counts = {phase.value: 0 for phase in WhaleHuntingPhase}
        
        for info in pod_info:
            phase = info['hunting_phase']
            if phase in phase_counts:
                phase_counts[phase] += 1
        
        return phase_counts
    
    def _record_woa_metrics(self) -> None:
        """Record WOA-specific performance metrics"""
        # Hunting phase distribution
        phase_distribution = self._calculate_phase_distribution(
            [whale.communicate_with_pod() for whale in self.agents]
        )
        self.hunting_phase_distribution.append(phase_distribution)
        
        # Convergence rate
        if len(self.convergence_history) > 1:
            convergence_rate = abs(self.convergence_history[-1] - self.convergence_history[-2])
            self.convergence_rate_history.append(convergence_rate)
        
        # Exploration vs exploitation balance
        exploration_count = (phase_distribution.get('search', 0) + 
                           phase_distribution.get('spiral_update', 0))
        exploitation_count = phase_distribution.get('encircling', 0)
        total_count = sum(phase_distribution.values())
        
        if total_count > 0:
            exploration_ratio = exploration_count / total_count
            self.exploration_exploitation_balance.append(exploration_ratio)
    
    def get_woa_statistics(self) -> Dict[str, Any]:
        """Get WOA-specific statistics"""
        return {
            'current_a': self.current_a,
            'best_whale_fitness': self.best_whale.fitness if self.best_whale else float('inf'),
            'bubble_net_probability': self.woa_params.bubble_net_probability,
            'pod_size': len(self.agents),
            'hunting_phase_distribution': self.hunting_phase_distribution[-1] if self.hunting_phase_distribution else {},
            'pod_communications': self.pod_communications[-10:],
            'convergence_rate_history': self.convergence_rate_history[-10:],
            'exploration_exploitation_balance': self.exploration_exploitation_balance[-10:],
            'average_energy': np.mean([w.energy_level for w in self.agents]),
            'average_bubble_net_skill': np.mean([w.bubble_net_skill for w in self.agents]),
            'total_social_connections': sum(len(w.social_connections) for w in self.agents),
            'memory_utilization': np.mean([len(w.memory) for w in self.agents])
        }
    
    def visualize_pod(self, save_path: Optional[str] = None) -> None:
        """Visualize whale pod (2D only)"""
        if self.params.dimension != 2:
            self.logger.warning("Visualization only supported for 2D problems")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(15, 10))
            
            # Plot whale positions by hunting phase
            plt.subplot(2, 3, 1)
            
            colors = {
                'encircling': 'blue',
                'bubble_net': 'green',
                'search': 'red',
                'spiral_update': 'orange'
            }
            
            for whale in self.agents:
                color = colors.get(whale.hunting_phase.value, 'gray')
                plt.scatter(whale.position[0], whale.position[1], 
                          c=color, alpha=0.7, s=50)
            
            # Mark best whale
            if self.best_whale:
                plt.scatter(self.best_whale.position[0], self.best_whale.position[1], 
                          c='gold', s=200, marker='*', label='Best Whale')
            
            plt.title('Whale Pod Hunting Behavior')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            
            # Create legend
            for phase, color in colors.items():
                plt.scatter([], [], c=color, label=phase.replace('_', ' ').title())
            plt.legend()
            
            # Plot convergence
            plt.subplot(2, 3, 2)
            plt.plot(self.convergence_history)
            plt.title('Pod Hunting Success')
            plt.xlabel('Iteration')
            plt.ylabel('Best Fitness')
            plt.yscale('log')
            
            # Plot parameter 'a'
            plt.subplot(2, 3, 3)
            a_history = [self.woa_params.a_max - (i / self.params.max_iterations) * 
                        (self.woa_params.a_max - self.woa_params.a_min) 
                        for i in range(min(self.iteration + 1, self.params.max_iterations))]
            plt.plot(a_history)
            plt.title('Parameter a Decay')
            plt.xlabel('Iteration')
            plt.ylabel('Value of a')
            
            # Plot hunting phase distribution
            plt.subplot(2, 3, 4)
            if self.hunting_phase_distribution:
                phases = list(self.hunting_phase_distribution[-1].keys())
                counts = list(self.hunting_phase_distribution[-1].values())
                plt.pie(counts, labels=phases, autopct='%1.1f%%')
            plt.title('Current Hunting Phase Distribution')
            
            # Plot exploration vs exploitation
            plt.subplot(2, 3, 5)
            if self.exploration_exploitation_balance:
                plt.plot(self.exploration_exploitation_balance)
                plt.axhline(y=0.5, color='r', linestyle='--', label='Balance Line')
            plt.title('Exploration vs Exploitation Balance')
            plt.xlabel('Iteration')
            plt.ylabel('Exploration Ratio')
            plt.ylim(0, 1)
            plt.legend()
            
            # Plot energy levels
            plt.subplot(2, 3, 6)
            energy_levels = [whale.energy_level for whale in self.agents]
            plt.hist(energy_levels, bins=20, alpha=0.7)
            plt.title('Pod Energy Distribution')
            plt.xlabel('Energy Level')
            plt.ylabel('Number of Whales')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_whale_optimization_algorithm(population_size: int = 50,
                                       max_iterations: int = 1000,
                                       a_max: float = 2.0,
                                       a_min: float = 0.0,
                                       dimension: int = 2,
                                       bounds: Tuple[float, float] = (-10.0, 10.0)) -> WhaleOptimizationAlgorithm:
    """
    Create a Whale Optimization Algorithm with specified parameters
    
    Args:
        population_size: Number of whales in pod
        max_iterations: Maximum number of iterations
        a_max: Maximum value of parameter 'a'
        a_min: Minimum value of parameter 'a'
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured WhaleOptimizationAlgorithm instance
    """
    params = WOAParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        a_max=a_max,
        a_min=a_min
    )
    
    return WhaleOptimizationAlgorithm(params)