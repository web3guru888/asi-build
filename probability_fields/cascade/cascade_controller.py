"""
Cascade Controller

Advanced system for creating and managing probability cascade effects
that propagate changes through interconnected probability networks.
"""

import numpy as np
import logging
import math
import time
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque
import networkx as nx


class CascadeType(Enum):
    """Types of probability cascades."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    OSCILLATING = "oscillating"
    DAMPED = "damped"
    AMPLIFIED = "amplified"
    RESONANT = "resonant"
    CHAOTIC = "chaotic"


@dataclass
class CascadeNode:
    """Node in a probability cascade network."""
    node_id: str
    entity_id: str
    initial_probability: float
    current_probability: float
    cascade_strength: float
    propagation_delay: float
    amplification_factor: float
    connected_nodes: Set[str] = field(default_factory=set)
    activation_time: float = 0.0
    last_update: float = field(default_factory=time.time)


@dataclass
class CascadeWave:
    """Represents a probability wave propagating through cascade."""
    wave_id: str
    source_node: str
    wave_strength: float
    propagation_speed: float
    frequency: float
    wavelength: float
    creation_time: float
    current_position: Tuple[float, float, float]
    affected_nodes: Set[str] = field(default_factory=set)


class CascadeController:
    """
    Advanced probability cascade control system.
    
    Creates and manages cascading probability effects that propagate
    through networks of interconnected events and entities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core system state
        self.cascade_networks: Dict[str, nx.DiGraph] = {}
        self.cascade_nodes: Dict[str, CascadeNode] = {}
        self.cascade_waves: Dict[str, CascadeWave] = {}
        self.active_cascades: Set[str] = set()
        
        # Threading
        self.cascade_lock = threading.RLock()
        
        # System parameters
        self.max_cascade_depth = 20
        self.wave_propagation_speed = 1.0  # units per second
        self.cascade_decay_rate = 0.01
        self.resonance_threshold = 0.8
        
        self.logger.info("CascadeController initialized")
    
    def create_cascade_network(
        self,
        network_id: str,
        nodes: List[Dict[str, Any]],
        connections: List[Tuple[str, str, float]]
    ) -> str:
        """Create a new probability cascade network."""
        with self.cascade_lock:
            # Create network graph
            network = nx.DiGraph()
            
            # Add nodes
            for node_data in nodes:
                node_id = node_data['node_id']
                cascade_node = CascadeNode(
                    node_id=node_id,
                    entity_id=node_data.get('entity_id', node_id),
                    initial_probability=node_data.get('probability', 0.5),
                    current_probability=node_data.get('probability', 0.5),
                    cascade_strength=node_data.get('cascade_strength', 1.0),
                    propagation_delay=node_data.get('propagation_delay', 0.0),
                    amplification_factor=node_data.get('amplification_factor', 1.0)
                )
                
                self.cascade_nodes[node_id] = cascade_node
                network.add_node(node_id, **cascade_node.__dict__)
            
            # Add connections
            for source, target, strength in connections:
                if source in self.cascade_nodes and target in self.cascade_nodes:
                    network.add_edge(source, target, cascade_strength=strength)
                    self.cascade_nodes[source].connected_nodes.add(target)
            
            self.cascade_networks[network_id] = network
            
            self.logger.info(f"Created cascade network {network_id} with {len(nodes)} nodes")
            return network_id
    
    def initiate_cascade(
        self,
        network_id: str,
        source_node_id: str,
        cascade_type: CascadeType,
        initial_strength: float = 1.0
    ) -> str:
        """Initiate a probability cascade from a source node."""
        if network_id not in self.cascade_networks:
            raise ValueError(f"Network {network_id} not found")
        
        cascade_id = f"cascade_{network_id}_{int(time.time() * 1000000)}"
        
        # Create initial wave
        wave_id = self._create_cascade_wave(
            source_node_id, initial_strength, cascade_type
        )
        
        # Start cascade propagation
        self._propagate_cascade(network_id, wave_id, cascade_type)
        
        self.active_cascades.add(cascade_id)
        
        self.logger.info(f"Initiated {cascade_type.value} cascade {cascade_id}")
        return cascade_id
    
    def _create_cascade_wave(
        self,
        source_node: str,
        strength: float,
        cascade_type: CascadeType
    ) -> str:
        """Create a cascade wave."""
        wave_id = f"wave_{source_node}_{int(time.time() * 1000000)}"
        
        # Calculate wave properties based on cascade type
        frequency, wavelength = self._calculate_wave_properties(cascade_type, strength)
        
        wave = CascadeWave(
            wave_id=wave_id,
            source_node=source_node,
            wave_strength=strength,
            propagation_speed=self.wave_propagation_speed,
            frequency=frequency,
            wavelength=wavelength,
            creation_time=time.time(),
            current_position=(0.0, 0.0, 0.0)
        )
        
        self.cascade_waves[wave_id] = wave
        return wave_id
    
    def _propagate_cascade(
        self,
        network_id: str,
        wave_id: str,
        cascade_type: CascadeType
    ) -> None:
        """Propagate cascade through the network."""
        network = self.cascade_networks[network_id]
        wave = self.cascade_waves[wave_id]
        
        visited = set()
        queue = deque([(wave.source_node, wave.wave_strength, 0)])
        
        while queue:
            current_node, current_strength, depth = queue.popleft()
            
            if (current_node in visited or 
                depth > self.max_cascade_depth or 
                current_strength < 0.01):
                continue
            
            visited.add(current_node)
            wave.affected_nodes.add(current_node)
            
            # Apply cascade effect to current node
            self._apply_cascade_effect(current_node, current_strength, cascade_type)
            
            # Propagate to connected nodes
            for neighbor in network.successors(current_node):
                edge_data = network[current_node][neighbor]
                edge_strength = edge_data.get('cascade_strength', 1.0)
                
                # Calculate propagated strength
                propagated_strength = self._calculate_propagated_strength(
                    current_strength, edge_strength, cascade_type, depth
                )
                
                queue.append((neighbor, propagated_strength, depth + 1))
    
    def _apply_cascade_effect(
        self,
        node_id: str,
        strength: float,
        cascade_type: CascadeType
    ) -> None:
        """Apply cascade effect to a specific node."""
        if node_id not in self.cascade_nodes:
            return
        
        node = self.cascade_nodes[node_id]
        
        # Calculate probability change based on cascade type
        if cascade_type == CascadeType.EXPONENTIAL:
            probability_change = strength * node.amplification_factor * math.exp(strength - 1)
        elif cascade_type == CascadeType.LINEAR:
            probability_change = strength * node.amplification_factor
        elif cascade_type == CascadeType.LOGARITHMIC:
            probability_change = strength * node.amplification_factor * math.log(1 + strength)
        elif cascade_type == CascadeType.OSCILLATING:
            time_factor = math.sin(time.time() * 2 * math.pi * 0.1)  # 0.1 Hz oscillation
            probability_change = strength * node.amplification_factor * time_factor
        elif cascade_type == CascadeType.DAMPED:
            damping_factor = math.exp(-time.time() * 0.1)
            probability_change = strength * node.amplification_factor * damping_factor
        elif cascade_type == CascadeType.AMPLIFIED:
            amplification = 1.0 + strength * 0.5
            probability_change = strength * node.amplification_factor * amplification
        elif cascade_type == CascadeType.RESONANT:
            resonance_factor = 1.0 if strength > self.resonance_threshold else 0.5
            probability_change = strength * node.amplification_factor * resonance_factor
        else:  # CHAOTIC
            chaos_factor = np.random.normal(1.0, 0.3)
            probability_change = strength * node.amplification_factor * chaos_factor
        
        # Apply change with bounds checking
        new_probability = node.current_probability + probability_change * 0.1
        node.current_probability = max(0.0, min(1.0, new_probability))
        node.last_update = time.time()
    
    def _calculate_propagated_strength(
        self,
        current_strength: float,
        edge_strength: float,
        cascade_type: CascadeType,
        depth: int
    ) -> float:
        """Calculate propagated strength to next node."""
        base_propagation = current_strength * edge_strength
        
        # Apply depth-based decay
        depth_decay = math.exp(-depth * self.cascade_decay_rate)
        
        # Apply cascade-type specific modifications
        if cascade_type == CascadeType.EXPONENTIAL:
            type_modifier = 1.1  # Slight amplification
        elif cascade_type == CascadeType.DAMPED:
            type_modifier = 0.9  # Slight reduction
        elif cascade_type == CascadeType.AMPLIFIED:
            type_modifier = 1.2  # Amplification
        else:
            type_modifier = 1.0
        
        propagated_strength = base_propagation * depth_decay * type_modifier
        return max(0.0, min(2.0, propagated_strength))
    
    def _calculate_wave_properties(
        self,
        cascade_type: CascadeType,
        strength: float
    ) -> Tuple[float, float]:
        """Calculate wave frequency and wavelength."""
        base_frequency = 1.0  # Hz
        
        if cascade_type == CascadeType.OSCILLATING:
            frequency = base_frequency * (1.0 + strength)
        elif cascade_type == CascadeType.RESONANT:
            frequency = base_frequency * 2.0  # Higher frequency for resonance
        else:
            frequency = base_frequency
        
        # Wavelength = speed / frequency
        wavelength = self.wave_propagation_speed / frequency
        
        return frequency, wavelength
    
    def get_cascade_status(self, network_id: str) -> Dict[str, Any]:
        """Get status of a cascade network."""
        if network_id not in self.cascade_networks:
            return {}
        
        network = self.cascade_networks[network_id]
        
        # Calculate network statistics
        total_nodes = network.number_of_nodes()
        total_edges = network.number_of_edges()
        
        # Calculate average probability
        probabilities = [
            self.cascade_nodes[node_id].current_probability
            for node_id in network.nodes()
            if node_id in self.cascade_nodes
        ]
        
        avg_probability = sum(probabilities) / len(probabilities) if probabilities else 0.0
        
        # Calculate cascade activity
        active_waves = len([
            wave for wave in self.cascade_waves.values()
            if any(node_id in network.nodes() for node_id in wave.affected_nodes)
        ])
        
        return {
            'network_id': network_id,
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'average_probability': avg_probability,
            'active_waves': active_waves,
            'network_density': nx.density(network),
            'strongly_connected_components': len(list(nx.strongly_connected_components(network)))
        }