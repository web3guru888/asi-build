"""
Swarm Intelligence Module for Kenny AI System

This module implements various swarm intelligence algorithms including:
- Ant Colony Optimization (ACO)
- Particle Swarm Optimization (PSO)
- Artificial Bee Colony (ABC)
- Firefly Algorithm (FA)
- Bacterial Foraging Optimization (BFO)
- Grey Wolf Optimizer (GWO)
- Whale Optimization Algorithm (WOA)
- Cuckoo Search (CS)
- Bat Algorithm (BA)
- Multi-Agent Coordination Systems

Author: Agent SW1 - Swarm Intelligence Specialist
Version: 1.0.0
"""

from .base import SwarmAgent, SwarmOptimizer, SwarmCoordinator
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
from .swarm_coordinator import SwarmIntelligenceCoordinator
from .metrics import SwarmMetrics
from .visualization import SwarmVisualizer
from .hybrid import HybridSwarmOptimizer
from .distributed import DistributedSwarmComputing
from .memory import SwarmMemorySystem
from .adaptive import AdaptiveSwarmParameters
from .communication import SwarmCommunicationProtocol

__all__ = [
    'SwarmAgent',
    'SwarmOptimizer', 
    'SwarmCoordinator',
    'AntColonyOptimizer',
    'ParticleSwarmOptimizer',
    'ArtificialBeeColony',
    'FireflyAlgorithm',
    'BacterialForagingOptimizer',
    'GreyWolfOptimizer',
    'WhaleOptimizationAlgorithm',
    'CuckooSearch',
    'BatAlgorithm',
    'MultiAgentCoordinator',
    'SwarmIntelligenceCoordinator',
    'SwarmMetrics',
    'SwarmVisualizer',
    'HybridSwarmOptimizer',
    'DistributedSwarmComputing',
    'SwarmMemorySystem',
    'AdaptiveSwarmParameters',
    'SwarmCommunicationProtocol'
]

__version__ = "1.0.0"
__author__ = "Agent SW1 - Swarm Intelligence Specialist"