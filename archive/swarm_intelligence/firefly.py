"""
Firefly Algorithm (FA)

This module implements the Firefly Algorithm, inspired by the flashing behavior
and attraction characteristics of fireflies. It includes brightness-based
attraction, distance-dependent movement, and various firefly variants.
"""

import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from .base import SwarmAgent, SwarmOptimizer, SwarmParameters


class FireflyVariant(Enum):
    """Firefly algorithm variants"""
    STANDARD = "standard"
    IMPROVED = "improved"
    MULTI_SWARM = "multi_swarm"
    DISCRETE = "discrete"
    LEVY_FLIGHT = "levy_flight"


@dataclass
class FireflyParameters(SwarmParameters):
    """Firefly Algorithm specific parameters"""
    alpha: float = 0.2          # Randomization parameter
    beta_min: float = 0.2       # Minimum attractiveness
    beta_max: float = 1.0       # Maximum attractiveness
    gamma: float = 1.0          # Light absorption coefficient
    variant: FireflyVariant = FireflyVariant.STANDARD
    
    # Advanced parameters
    light_intensity_exp: float = 2.0    # Light intensity exponent
    distance_metric: str = "euclidean"   # Distance calculation method
    adaptive_alpha: bool = True          # Adaptive randomization
    levy_flight_enabled: bool = False    # Enable Levy flights
    
    # Multi-swarm parameters
    num_subswarms: int = 3              # Number of subswarms
    migration_interval: int = 50        # Migration frequency
    migration_rate: float = 0.1         # Migration rate
    
    # Social parameters
    communication_range: float = 5.0    # Communication range
    social_attraction: bool = True       # Enable social attraction


class Firefly(SwarmAgent):
    """
    Individual firefly agent
    
    Each firefly has brightness, attraction patterns, and movement behaviors
    based on the brightness of other fireflies.
    """
    
    def __init__(self, dimension: int, bounds: Tuple[float, float]):
        super().__init__(dimension, bounds)
        
        # Firefly-specific properties
        self.brightness = 0.0
        self.light_intensity = 0.0
        self.attractiveness = 1.0
        self.flash_frequency = 1.0
        self.communication_partners = []
        
        # Movement history
        self.movement_history = []
        self.attraction_history = []
        
        # Biological properties
        self.energy_level = 100.0
        self.visibility_range = 10.0
        self.flash_pattern = np.random.randint(1, 5)
        
        # Firefly behavior properties
        self.properties.update({
            'bioluminescence_efficiency': np.random.uniform(0.5, 1.0),
            'photophobia_threshold': np.random.uniform(0.1, 0.5),
            'social_tendency': np.random.random(),
            'exploration_tendency': np.random.random(),
            'flash_synchronization': np.random.random()
        })
    
    def update_position(self, other_fireflies: List['Firefly'] = None,
                       alpha: float = 0.2, gamma: float = 1.0,
                       beta_min: float = 0.2, beta_max: float = 1.0,
                       variant: FireflyVariant = FireflyVariant.STANDARD,
                       **kwargs) -> None:
        """
        Update firefly position based on attraction to brighter fireflies
        
        Args:
            other_fireflies: List of other fireflies in the swarm
            alpha: Randomization parameter
            gamma: Light absorption coefficient
            beta_min: Minimum attractiveness
            beta_max: Maximum attractiveness
            variant: Firefly algorithm variant
        """
        if other_fireflies is None:
            other_fireflies = []
        
        # Find brighter fireflies
        brighter_fireflies = [f for f in other_fireflies 
                             if f.brightness > self.brightness and f != self]
        
        if not brighter_fireflies:
            # No brighter fireflies - random movement
            self._random_movement(alpha, variant)
        else:
            # Move towards brighter fireflies
            self._attraction_movement(brighter_fireflies, alpha, gamma, 
                                    beta_min, beta_max, variant)
        
        self.clip_to_bounds()
        self.age += 1
        
        # Record movement
        self.movement_history.append(self.position.copy())
        if len(self.movement_history) > 100:  # Keep last 100 positions
            self.movement_history.pop(0)
    
    def update_velocity(self, **kwargs) -> None:
        """Update firefly velocity for smoother movement"""
        # Fireflies use position-based movement, but we maintain velocity for momentum
        decay_factor = kwargs.get('velocity_decay', 0.95)
        self.velocity *= decay_factor
        
        # Add small random component
        random_component = np.random.normal(0, 0.01, self.dimension)
        self.velocity += random_component
    
    def _random_movement(self, alpha: float, variant: FireflyVariant) -> None:
        """Perform random movement when no brighter fireflies are found"""
        if variant == FireflyVariant.LEVY_FLIGHT:
            # Levy flight movement
            levy_step = self._levy_flight_step()
            self.position += alpha * levy_step
        else:
            # Standard random movement
            random_step = np.random.uniform(-1, 1, self.dimension)
            self.position += alpha * random_step
    
    def _attraction_movement(self, brighter_fireflies: List['Firefly'],
                           alpha: float, gamma: float,
                           beta_min: float, beta_max: float,
                           variant: FireflyVariant) -> None:
        """Move towards brighter fireflies based on attraction"""
        total_attraction = np.zeros(self.dimension)
        total_weight = 0.0
        
        for firefly in brighter_fireflies:
            # Calculate distance
            distance = self._calculate_distance(firefly)
            
            # Calculate attractiveness
            attractiveness = self._calculate_attractiveness(
                distance, gamma, beta_min, beta_max
            )
            
            # Calculate attraction vector
            direction = firefly.position - self.position
            attraction = attractiveness * direction
            
            # Weight by brightness difference
            brightness_diff = firefly.brightness - self.brightness
            weight = brightness_diff / max(brightness_diff, 1e-10)
            
            total_attraction += weight * attraction
            total_weight += weight
            
            # Record attraction
            self.attraction_history.append({
                'target_firefly': id(firefly),
                'distance': distance,
                'attractiveness': attractiveness,
                'brightness_diff': brightness_diff
            })
        
        # Normalize attraction
        if total_weight > 0:
            total_attraction /= total_weight
        
        # Add randomization
        random_component = alpha * np.random.uniform(-1, 1, self.dimension)
        
        # Update position
        if variant == FireflyVariant.IMPROVED:
            # Improved variant with momentum
            momentum = 0.1 * self.velocity if hasattr(self, 'velocity') else 0
            self.position += total_attraction + random_component + momentum
        else:
            # Standard variant
            self.position += total_attraction + random_component
    
    def _calculate_distance(self, other_firefly: 'Firefly') -> float:
        """Calculate distance to another firefly"""
        return np.linalg.norm(self.position - other_firefly.position)
    
    def _calculate_attractiveness(self, distance: float, gamma: float,
                                beta_min: float, beta_max: float) -> float:
        """Calculate attractiveness based on distance"""
        # Standard attractiveness formula: β = β₀ * e^(-γr²)
        beta_0 = beta_max
        attractiveness = beta_0 * np.exp(-gamma * distance**2)
        
        # Ensure minimum attractiveness
        return max(attractiveness, beta_min)
    
    def _levy_flight_step(self) -> np.ndarray:
        """Generate Levy flight step"""
        # Levy flight with β = 1.5
        beta = 1.5
        sigma_u = (np.math.gamma(1 + beta) * np.sin(np.pi * beta / 2) / 
                  (np.math.gamma((1 + beta) / 2) * beta * (2 ** ((beta - 1) / 2)))) ** (1 / beta)
        
        u = np.random.normal(0, sigma_u, self.dimension)
        v = np.random.normal(0, 1, self.dimension)
        
        step = u / (np.abs(v) ** (1 / beta))
        return step
    
    def update_brightness(self, objective_function: Callable) -> None:
        """Update firefly brightness based on objective function"""
        # Evaluate fitness
        self.evaluate_fitness(objective_function)
        
        # Convert fitness to brightness (lower fitness = higher brightness)
        if self.fitness == float('inf'):
            self.brightness = 0.0
        else:
            # Normalize brightness to [0, 1] range
            max_fitness = 1000.0  # Assumed maximum for normalization
            normalized_fitness = min(self.fitness / max_fitness, 1.0)
            self.brightness = 1.0 - normalized_fitness
        
        # Update light intensity based on efficiency
        efficiency = self.properties['bioluminescence_efficiency']
        self.light_intensity = self.brightness * efficiency
    
    def is_visible_to(self, other_firefly: 'Firefly') -> bool:
        """Check if this firefly is visible to another firefly"""
        distance = self._calculate_distance(other_firefly)
        return distance <= self.visibility_range
    
    def flash(self) -> Dict[str, Any]:
        """Generate flash signal"""
        return {
            'firefly_id': id(self),
            'position': self.position.copy(),
            'brightness': self.brightness,
            'light_intensity': self.light_intensity,
            'flash_pattern': self.flash_pattern,
            'timestamp': self.age
        }
    
    def respond_to_flash(self, flash_signal: Dict[str, Any]) -> float:
        """Respond to flash from another firefly"""
        # Calculate response probability based on flash characteristics
        brightness_factor = flash_signal['brightness']
        distance_factor = 1.0 / (1.0 + self._calculate_distance_from_position(flash_signal['position']))
        social_factor = self.properties['social_tendency']
        
        response_probability = brightness_factor * distance_factor * social_factor
        return min(response_probability, 1.0)
    
    def _calculate_distance_from_position(self, position: np.ndarray) -> float:
        """Calculate distance from a position"""
        return np.linalg.norm(self.position - position)


class FireflyAlgorithm(SwarmOptimizer):
    """
    Firefly Algorithm optimization implementation
    
    Implements the complete firefly algorithm with various variants and
    advanced features like adaptive parameters and multi-swarm capabilities.
    """
    
    def __init__(self, parameters: FireflyParameters):
        super().__init__(parameters)
        self.firefly_params = parameters
        
        # Algorithm state
        self.current_alpha = parameters.alpha
        self.current_gamma = parameters.gamma
        
        # Multi-swarm support
        self.subswarms = []
        self.migration_counter = 0
        
        # Performance tracking
        self.attraction_statistics = []
        self.brightness_statistics = []
        self.flash_communication_history = []
        
        # Adaptive control
        self.alpha_adaptation_rate = 0.95
        self.gamma_adaptation_rate = 1.02
    
    def initialize_population(self) -> None:
        """Initialize firefly population"""
        if self.firefly_params.variant == FireflyVariant.MULTI_SWARM:
            self._initialize_multi_swarm()
        else:
            self.agents = [
                Firefly(self.params.dimension, self.params.bounds)
                for _ in range(self.params.population_size)
            ]
        
        self.logger.info(f"Initialized {len(self.agents)} fireflies "
                        f"with variant: {self.firefly_params.variant.value}")
    
    def _initialize_multi_swarm(self) -> None:
        """Initialize multiple subswarms"""
        swarm_size = self.params.population_size // self.firefly_params.num_subswarms
        
        for i in range(self.firefly_params.num_subswarms):
            subswarm = [
                Firefly(self.params.dimension, self.params.bounds)
                for _ in range(swarm_size)
            ]
            self.subswarms.append(subswarm)
        
        # Combine all fireflies
        self.agents = [firefly for subswarm in self.subswarms for firefly in subswarm]
    
    def update_agents(self, objective_function: Callable) -> None:
        """Update all fireflies in the swarm"""
        # Update brightness for all fireflies
        for firefly in self.agents:
            firefly.update_brightness(objective_function)
        
        # Sort fireflies by brightness (brightest first)
        sorted_fireflies = sorted(self.agents, key=lambda f: f.brightness, reverse=True)
        
        # Update positions
        if self.firefly_params.variant == FireflyVariant.MULTI_SWARM:
            self._update_multi_swarm(objective_function)
        else:
            self._update_standard_swarm(sorted_fireflies)
        
        # Adaptive parameter control
        if self.firefly_params.adaptive_alpha:
            self._adapt_parameters()
        
        # Handle flash communication
        if self.firefly_params.social_attraction:
            self._handle_flash_communication()
        
        # Record statistics
        self._record_firefly_statistics()
    
    def _update_standard_swarm(self, sorted_fireflies: List[Firefly]) -> None:
        """Update fireflies in standard swarm mode"""
        for i, firefly in enumerate(sorted_fireflies):
            # Get other fireflies for comparison
            other_fireflies = sorted_fireflies[:i] + sorted_fireflies[i+1:]
            
            # Update position
            firefly.update_position(
                other_fireflies=other_fireflies,
                alpha=self.current_alpha,
                gamma=self.current_gamma,
                beta_min=self.firefly_params.beta_min,
                beta_max=self.firefly_params.beta_max,
                variant=self.firefly_params.variant
            )
            
            # Update velocity for momentum
            firefly.update_velocity()
    
    def _update_multi_swarm(self, objective_function: Callable) -> None:
        """Update fireflies in multi-swarm mode"""
        for subswarm in self.subswarms:
            # Sort subswarm by brightness
            sorted_subswarm = sorted(subswarm, key=lambda f: f.brightness, reverse=True)
            
            # Update each firefly within its subswarm
            for i, firefly in enumerate(sorted_subswarm):
                other_fireflies = sorted_subswarm[:i] + sorted_subswarm[i+1:]
                
                firefly.update_position(
                    other_fireflies=other_fireflies,
                    alpha=self.current_alpha,
                    gamma=self.current_gamma,
                    beta_min=self.firefly_params.beta_min,
                    beta_max=self.firefly_params.beta_max,
                    variant=self.firefly_params.variant
                )
                
                firefly.update_velocity()
        
        # Handle migration between subswarms
        self.migration_counter += 1
        if self.migration_counter >= self.firefly_params.migration_interval:
            self._migrate_fireflies()
            self.migration_counter = 0
    
    def _migrate_fireflies(self) -> None:
        """Migrate fireflies between subswarms"""
        migration_count = max(1, int(len(self.agents) * self.firefly_params.migration_rate))
        
        for _ in range(migration_count):
            # Select random source and target subswarms
            source_idx = np.random.randint(0, len(self.subswarms))
            target_idx = np.random.randint(0, len(self.subswarms))
            
            if source_idx != target_idx and len(self.subswarms[source_idx]) > 1:
                # Select worst firefly from source
                worst_firefly = min(self.subswarms[source_idx], key=lambda f: f.brightness)
                
                # Move to target subswarm
                self.subswarms[source_idx].remove(worst_firefly)
                self.subswarms[target_idx].append(worst_firefly)
    
    def _adapt_parameters(self) -> None:
        """Adaptively adjust algorithm parameters"""
        # Adapt alpha based on convergence
        if len(self.convergence_history) > 5:
            recent_improvement = (self.convergence_history[-5] - 
                                self.convergence_history[-1])
            
            if recent_improvement < 1e-6:
                # Poor convergence - increase randomization
                self.current_alpha = min(1.0, self.current_alpha * 1.05)
            else:
                # Good convergence - decrease randomization
                self.current_alpha = max(0.01, self.current_alpha * self.alpha_adaptation_rate)
        
        # Adapt gamma based on diversity
        if self.diversity_history:
            current_diversity = self.diversity_history[-1]
            target_diversity = 1.0
            
            if current_diversity < target_diversity:
                # Low diversity - decrease absorption (increase long-range attraction)
                self.current_gamma = max(0.1, self.current_gamma / self.gamma_adaptation_rate)
            else:
                # High diversity - increase absorption (increase local search)
                self.current_gamma = min(10.0, self.current_gamma * self.gamma_adaptation_rate)
    
    def _handle_flash_communication(self) -> None:
        """Handle flash communication between fireflies"""
        flash_signals = []
        
        # Generate flash signals from bright fireflies
        bright_threshold = np.percentile([f.brightness for f in self.agents], 75)
        
        for firefly in self.agents:
            if firefly.brightness >= bright_threshold:
                flash = firefly.flash()
                flash_signals.append(flash)
        
        # Process flash responses
        communication_events = []
        for firefly in self.agents:
            for flash in flash_signals:
                if flash['firefly_id'] != id(firefly):
                    response_prob = firefly.respond_to_flash(flash)
                    
                    if np.random.random() < response_prob:
                        communication_events.append({
                            'sender': flash['firefly_id'],
                            'receiver': id(firefly),
                            'response_probability': response_prob,
                            'brightness_difference': flash['brightness'] - firefly.brightness
                        })
        
        self.flash_communication_history.append({
            'iteration': self.iteration,
            'flash_count': len(flash_signals),
            'communication_events': len(communication_events),
            'average_response_prob': np.mean([e['response_probability'] 
                                            for e in communication_events]) if communication_events else 0.0
        })
    
    def _record_firefly_statistics(self) -> None:
        """Record firefly-specific statistics"""
        # Brightness statistics
        brightnesses = [f.brightness for f in self.agents]
        brightness_stats = {
            'mean': np.mean(brightnesses),
            'std': np.std(brightnesses),
            'max': np.max(brightnesses),
            'min': np.min(brightnesses),
            'median': np.median(brightnesses)
        }
        self.brightness_statistics.append(brightness_stats)
        
        # Attraction statistics
        total_attractions = 0
        total_distances = []
        
        for firefly in self.agents:
            if firefly.attraction_history:
                recent_attractions = firefly.attraction_history[-10:]  # Last 10 attractions
                total_attractions += len(recent_attractions)
                total_distances.extend([a['distance'] for a in recent_attractions])
        
        attraction_stats = {
            'total_attractions': total_attractions,
            'average_attraction_distance': np.mean(total_distances) if total_distances else 0.0,
            'attraction_range': np.max(total_distances) - np.min(total_distances) if total_distances else 0.0
        }
        self.attraction_statistics.append(attraction_stats)
    
    def get_firefly_statistics(self) -> Dict[str, Any]:
        """Get firefly-specific statistics"""
        return {
            'current_alpha': self.current_alpha,
            'current_gamma': self.current_gamma,
            'variant': self.firefly_params.variant.value,
            'brightness_statistics': self.brightness_statistics[-10:],  # Last 10 iterations
            'attraction_statistics': self.attraction_statistics[-10:],
            'flash_communication': self.flash_communication_history[-10:],
            'average_brightness': np.mean([f.brightness for f in self.agents]),
            'brightest_firefly_fitness': min(f.fitness for f in self.agents),
            'total_flash_communications': sum(event['communication_events'] 
                                            for event in self.flash_communication_history[-10:]),
            'num_subswarms': len(self.subswarms) if self.subswarms else 1,
            'migration_counter': self.migration_counter
        }
    
    def visualize_fireflies(self, save_path: Optional[str] = None) -> None:
        """Visualize firefly swarm (2D only)"""
        if self.params.dimension != 2:
            self.logger.warning("Visualization only supported for 2D problems")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(15, 10))
            
            # Plot firefly positions with brightness
            plt.subplot(2, 3, 1)
            positions = np.array([f.position for f in self.agents])
            brightnesses = [f.brightness for f in self.agents]
            
            scatter = plt.scatter(positions[:, 0], positions[:, 1], 
                                c=brightnesses, cmap='hot', s=50, alpha=0.7)
            plt.colorbar(scatter, label='Brightness')
            
            if self.global_best_position is not None:
                plt.scatter(self.global_best_position[0], self.global_best_position[1], 
                          c='cyan', s=200, marker='*', label='Global Best')
            
            plt.title('Firefly Positions and Brightness')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.legend()
            
            # Plot movement trails for selected fireflies
            plt.subplot(2, 3, 2)
            for i, firefly in enumerate(self.agents[:5]):  # Show trails for first 5 fireflies
                if firefly.movement_history:
                    trail = np.array(firefly.movement_history)
                    plt.plot(trail[:, 0], trail[:, 1], alpha=0.6, label=f'Firefly {i+1}')
            
            plt.title('Movement Trails')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.legend()
            
            # Plot convergence
            plt.subplot(2, 3, 3)
            plt.plot(self.convergence_history)
            plt.title('Convergence History')
            plt.xlabel('Iteration')
            plt.ylabel('Best Fitness')
            plt.yscale('log')
            
            # Plot brightness distribution
            plt.subplot(2, 3, 4)
            plt.hist(brightnesses, bins=20, alpha=0.7)
            plt.title('Brightness Distribution')
            plt.xlabel('Brightness')
            plt.ylabel('Count')
            
            # Plot parameter adaptation
            plt.subplot(2, 3, 5)
            if len(self.brightness_statistics) > 1:
                alpha_history = [self.current_alpha] * len(self.brightness_statistics)  # Simplified
                plt.plot(alpha_history, label='Alpha')
                plt.plot([self.current_gamma] * len(self.brightness_statistics), label='Gamma')
            plt.title('Parameter Adaptation')
            plt.xlabel('Iteration')
            plt.ylabel('Parameter Value')
            plt.legend()
            
            # Plot communication statistics
            plt.subplot(2, 3, 6)
            if self.flash_communication_history:
                flash_counts = [event['flash_count'] for event in self.flash_communication_history]
                comm_events = [event['communication_events'] for event in self.flash_communication_history]
                
                plt.plot(flash_counts, label='Flash Signals')
                plt.plot(comm_events, label='Communication Events')
            
            plt.title('Flash Communication')
            plt.xlabel('Iteration')
            plt.ylabel('Count')
            plt.legend()
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path)
            else:
                plt.show()
                
        except ImportError:
            self.logger.warning("Matplotlib not available for visualization")


# Factory function for easy instantiation
def create_firefly_algorithm(population_size: int = 50,
                           max_iterations: int = 1000,
                           alpha: float = 0.2,
                           beta_min: float = 0.2,
                           beta_max: float = 1.0,
                           gamma: float = 1.0,
                           variant: FireflyVariant = FireflyVariant.STANDARD,
                           dimension: int = 2,
                           bounds: Tuple[float, float] = (-10.0, 10.0)) -> FireflyAlgorithm:
    """
    Create a Firefly Algorithm optimizer with specified parameters
    
    Args:
        population_size: Number of fireflies in swarm
        max_iterations: Maximum number of iterations
        alpha: Randomization parameter
        beta_min: Minimum attractiveness
        beta_max: Maximum attractiveness
        gamma: Light absorption coefficient
        variant: Firefly algorithm variant
        dimension: Problem dimension
        bounds: Search space bounds
        
    Returns:
        Configured FireflyAlgorithm instance
    """
    params = FireflyParameters(
        population_size=population_size,
        max_iterations=max_iterations,
        dimension=dimension,
        bounds=bounds,
        alpha=alpha,
        beta_min=beta_min,
        beta_max=beta_max,
        gamma=gamma,
        variant=variant
    )
    
    return FireflyAlgorithm(params)