"""
Integrated Information Theory (IIT) Implementation

Based on Giulio Tononi's Integrated Information Theory, this module implements
a consciousness model that measures consciousness as integrated information (Φ).

Key components:
- Information integration measurement
- System partitioning and analysis
- Phi (Φ) calculation
- Conscious complexes identification
- Causal structure analysis
"""

import itertools
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import networkx as nx
import numpy as np
from scipy.special import comb

from .base_consciousness import BaseConsciousness, ConsciousnessEvent, ConsciousnessState


@dataclass
class SystemElement:
    """Represents an element in the IIT system"""

    element_id: str
    state: float
    inputs: Set[str] = field(default_factory=set)
    outputs: Set[str] = field(default_factory=set)
    activation_function: str = "sigmoid"
    threshold: float = 0.5
    last_updated: float = field(default_factory=time.time)

    def update_state(self, input_values: Dict[str, float], weights: Dict[str, float]) -> None:
        """Update element state based on inputs"""
        total_input = sum(input_values.get(inp, 0) * weights.get(inp, 1.0) for inp in self.inputs)

        if self.activation_function == "sigmoid":
            self.state = 1.0 / (1.0 + np.exp(-total_input))
        elif self.activation_function == "threshold":
            self.state = 1.0 if total_input > self.threshold else 0.0
        elif self.activation_function == "linear":
            self.state = max(0.0, min(1.0, total_input))

        self.last_updated = time.time()


@dataclass
class Connection:
    """Represents a connection between system elements"""

    from_element: str
    to_element: str
    weight: float
    delay: float = 0.0
    active: bool = True


@dataclass
class SystemPartition:
    """Represents a partition of the system for phi calculation"""

    partition_id: str
    subset_a: Set[str]
    subset_b: Set[str]
    cut_connections: List[Connection]
    phi_value: float = 0.0

    def is_valid(self) -> bool:
        """Check if partition is valid (non-empty subsets)"""
        return len(self.subset_a) > 0 and len(self.subset_b) > 0


@dataclass
class IntegratedComplex:
    """Represents a complex with integrated information"""

    complex_id: str
    elements: Set[str]
    phi_value: float
    main_complex: bool = False
    partitions: List[SystemPartition] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class IntegratedInformationTheory(BaseConsciousness):
    """
    Implementation of Integrated Information Theory (IIT)

    Measures consciousness as integrated information (Φ) in a system
    by analyzing how much information is lost when the system is partitioned.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Pre-initialize instance attributes before super().__init__() which
        # calls _initialize() — attributes must exist before that hook runs.
        self.elements: Dict[str, SystemElement] = {}
        self.connections: List[Connection] = []
        self.system_graph = nx.DiGraph()
        self.current_phi = 0.0
        self.main_complex: Optional[IntegratedComplex] = None
        self.all_complexes: List[IntegratedComplex] = []
        self.system_state_history: List[Dict[str, float]] = []
        self.phi_calculation_lock = threading.Lock()
        self.last_phi_calculation = 0
        self.partition_cache: Dict[str, float] = {}
        self.connection_matrix: Optional[np.ndarray] = None
        self.total_phi_calculations = 0
        self.average_phi = 0.0
        self.phi_history: List[Tuple[float, float]] = []  # (timestamp, phi)

        super().__init__("IntegratedInformation", config)

        # IIT parameters (require self.config from super)
        self.phi_threshold = self.config.get("phi_threshold", 0.1)
        self.max_partition_size = self.config.get("max_partition_size", 8)
        self.integration_window = self.config.get("integration_window", 1.0)
        self.phi_calculation_interval = self.config.get("phi_interval", 2.0)

    def _initialize(self):
        """Initialize the IIT system"""
        # Create default neural network-like structure
        self._create_default_network()
        self.logger.info("Initialized Integrated Information Theory system")

    def _create_default_network(self):
        """Create a default network structure for IIT analysis"""
        # Create sensory input layer
        sensory_elements = []
        for i in range(4):
            element_id = f"sensory_{i}"
            element = SystemElement(element_id=element_id, state=0.0, activation_function="sigmoid")
            self.elements[element_id] = element
            sensory_elements.append(element_id)

        # Create processing layer
        processing_elements = []
        for i in range(6):
            element_id = f"process_{i}"
            element = SystemElement(element_id=element_id, state=0.0, activation_function="sigmoid")
            self.elements[element_id] = element
            processing_elements.append(element_id)

        # Create output layer
        output_elements = []
        for i in range(3):
            element_id = f"output_{i}"
            element = SystemElement(element_id=element_id, state=0.0, activation_function="sigmoid")
            self.elements[element_id] = element
            output_elements.append(element_id)

        # Connect layers
        self._connect_layers(sensory_elements, processing_elements, 0.7)
        self._connect_layers(processing_elements, processing_elements, 0.3)  # Recurrent
        self._connect_layers(processing_elements, output_elements, 0.8)

        # Update graph
        self._update_system_graph()

    def _connect_layers(
        self, from_layer: List[str], to_layer: List[str], connection_probability: float
    ):
        """Connect two layers with given probability"""
        for from_elem in from_layer:
            for to_elem in to_layer:
                if from_elem != to_elem and np.random.random() < connection_probability:
                    weight = np.random.normal(0.5, 0.2)
                    weight = max(-1.0, min(1.0, weight))

                    connection = Connection(
                        from_element=from_elem, to_element=to_elem, weight=weight
                    )
                    self.connections.append(connection)

                    # Update element connections
                    self.elements[from_elem].outputs.add(to_elem)
                    self.elements[to_elem].inputs.add(from_elem)

    def _update_system_graph(self):
        """Update the NetworkX graph representation"""
        self.system_graph.clear()

        # Add nodes
        for element_id in self.elements:
            self.system_graph.add_node(element_id)

        # Add edges
        for connection in self.connections:
            if connection.active:
                self.system_graph.add_edge(
                    connection.from_element, connection.to_element, weight=connection.weight
                )

    def add_element(self, element: SystemElement) -> None:
        """Add an element to the system"""
        self.elements[element.element_id] = element
        self._update_system_graph()
        self.logger.info(f"Added element: {element.element_id}")

    def add_connection(self, connection: Connection) -> None:
        """Add a connection between elements"""
        if connection.from_element in self.elements and connection.to_element in self.elements:

            self.connections.append(connection)
            self.elements[connection.from_element].outputs.add(connection.to_element)
            self.elements[connection.to_element].inputs.add(connection.from_element)
            self._update_system_graph()

            self.logger.info(
                f"Added connection: {connection.from_element} -> {connection.to_element}"
            )

    def update_system_state(self, external_inputs: Optional[Dict[str, float]] = None) -> None:
        """Update the state of all elements in the system"""
        external_inputs = external_inputs or {}

        # Get current state
        current_state = {eid: elem.state for eid, elem in self.elements.items()}

        # Apply external inputs
        for element_id, value in external_inputs.items():
            if element_id in self.elements:
                self.elements[element_id].state = value

        # Update each element based on its inputs
        connection_weights = defaultdict(dict)
        for conn in self.connections:
            if conn.active:
                connection_weights[conn.to_element][conn.from_element] = conn.weight

        for element_id, element in self.elements.items():
            if element_id not in external_inputs:  # Don't update externally driven elements
                input_values = {inp: self.elements[inp].state for inp in element.inputs}
                element.update_state(input_values, connection_weights[element_id])

        # Store state history
        new_state = {eid: elem.state for eid, elem in self.elements.items()}
        self.system_state_history.append(new_state)

        # Keep only recent history
        max_history = int(self.integration_window / self.update_interval) + 10
        if len(self.system_state_history) > max_history:
            self.system_state_history = self.system_state_history[-max_history:]

    def calculate_phi(self, subset: Optional[Set[str]] = None) -> float:
        """Calculate the integrated information (Φ) for a subset of elements"""
        if subset is None:
            subset = set(self.elements.keys())

        if len(subset) <= 1:
            return 0.0

        # Check cache
        subset_key = "_".join(sorted(subset))
        if subset_key in self.partition_cache:
            return self.partition_cache[subset_key]

        with self.phi_calculation_lock:
            phi = self._compute_phi_for_subset(subset)
            self.partition_cache[subset_key] = phi
            return phi

    def _compute_phi_for_subset(self, subset: Set[str]) -> float:
        """Compute Φ for a specific subset of elements"""
        if len(subset) > self.max_partition_size:
            # Use approximation for large subsets
            return self._approximate_phi(subset)

        min_phi = float("inf")
        best_partition = None

        # Try all possible bipartitions
        for partition_size in range(1, len(subset)):
            for subset_a in itertools.combinations(subset, partition_size):
                subset_a = set(subset_a)
                subset_b = subset - subset_a

                if len(subset_b) == 0:
                    continue

                # Calculate information loss for this partition
                phi_partition = self._calculate_partition_phi(subset_a, subset_b)

                if phi_partition < min_phi:
                    min_phi = phi_partition
                    best_partition = (subset_a, subset_b)

        return max(0.0, min_phi)

    def _calculate_partition_phi(self, subset_a: Set[str], subset_b: Set[str]) -> float:
        """Calculate Φ for a specific partition"""
        # Find connections that cross the partition
        cross_connections = []
        for conn in self.connections:
            if not conn.active:
                continue

            if (conn.from_element in subset_a and conn.to_element in subset_b) or (
                conn.from_element in subset_b and conn.to_element in subset_a
            ):
                cross_connections.append(conn)

        if not cross_connections:
            return 0.0

        # Calculate information before and after cutting connections
        original_entropy = self._calculate_system_entropy(subset_a | subset_b)

        # Temporarily cut cross connections
        for conn in cross_connections:
            conn.active = False

        # Calculate entropy with cut connections
        cut_entropy = self._calculate_system_entropy(subset_a | subset_b)

        # Restore connections
        for conn in cross_connections:
            conn.active = True

        # Φ is the difference in integrated information
        phi = original_entropy - cut_entropy
        return max(0.0, phi)

    def _calculate_system_entropy(self, subset: Set[str]) -> float:
        """Calculate the entropy of a system subset"""
        if not self.system_state_history:
            return 0.0

        # Get recent states for subset
        recent_states = []
        for state_dict in self.system_state_history[-10:]:  # Last 10 states
            subset_state = tuple(state_dict.get(elem_id, 0.0) for elem_id in sorted(subset))
            recent_states.append(subset_state)

        if not recent_states:
            return 0.0

        # Calculate entropy based on state transitions
        state_counts = defaultdict(int)
        for state in recent_states:
            # Discretize continuous states
            discrete_state = tuple(1 if s > 0.5 else 0 for s in state)
            state_counts[discrete_state] += 1

        total_states = len(recent_states)
        entropy = 0.0

        for count in state_counts.values():
            probability = count / total_states
            if probability > 0:
                entropy -= probability * np.log2(probability)

        return entropy

    def _approximate_phi(self, subset: Set[str]) -> float:
        """Approximate Φ for large subsets using sampling"""
        if len(subset) <= 4:
            return self._compute_phi_for_subset(subset)

        # Sample random partitions
        num_samples = min(50, 2 ** (len(subset) - 1))
        phi_samples = []

        for _ in range(num_samples):
            partition_size = np.random.randint(1, len(subset))
            subset_a = set(np.random.choice(list(subset), partition_size, replace=False))
            subset_b = subset - subset_a

            if len(subset_b) > 0:
                phi = self._calculate_partition_phi(subset_a, subset_b)
                phi_samples.append(phi)

        return min(phi_samples) if phi_samples else 0.0

    def find_conscious_complexes(self) -> List[IntegratedComplex]:
        """Find all complexes with Φ > threshold"""
        complexes = []

        # Check all possible subsets (up to max size)
        all_elements = set(self.elements.keys())

        for size in range(2, min(len(all_elements) + 1, self.max_partition_size + 1)):
            for subset in itertools.combinations(all_elements, size):
                subset = set(subset)
                phi = self.calculate_phi(subset)

                if phi > self.phi_threshold:
                    complex = IntegratedComplex(
                        complex_id=f"complex_{len(complexes)}", elements=subset, phi_value=phi
                    )
                    complexes.append(complex)

        # Sort by Φ value (highest first)
        complexes.sort(key=lambda c: c.phi_value, reverse=True)

        # Mark main complex (highest Φ)
        if complexes:
            complexes[0].main_complex = True

        return complexes

    def process_event(self, event: ConsciousnessEvent) -> Optional[ConsciousnessEvent]:
        """Process consciousness events"""
        if event.event_type == "external_input":
            # Apply external inputs to system
            inputs = event.data.get("inputs", {})
            self.update_system_state(inputs)

        elif event.event_type == "calculate_phi":
            # Force Φ calculation
            subset = event.data.get("subset")
            if subset:
                subset = set(subset)
            phi = self.calculate_phi(subset)

            return ConsciousnessEvent(
                event_id=f"phi_result_{event.event_id}",
                timestamp=time.time(),
                event_type="phi_calculated",
                data={"phi_value": phi, "subset": list(subset) if subset else None},
                source_module="integrated_information",
            )

        elif event.event_type == "add_element":
            # Add new element to system
            element_data = event.data.get("element")
            if element_data:
                element = SystemElement(**element_data)
                self.add_element(element)

        return None

    def update(self) -> None:
        """Update the IIT system"""
        current_time = time.time()

        # Update system state with random inputs (simulation)
        if np.random.random() < 0.1:  # 10% chance of external input
            external_inputs = {}
            for element_id in list(self.elements.keys())[:4]:  # First 4 are sensory
                if np.random.random() < 0.3:
                    external_inputs[element_id] = np.random.random()

            if external_inputs:
                self.update_system_state(external_inputs)
        else:
            self.update_system_state()

        # Calculate Φ periodically
        if current_time - self.last_phi_calculation > self.phi_calculation_interval:
            self.last_phi_calculation = current_time

            # Calculate Φ for whole system
            self.current_phi = self.calculate_phi()

            # Find conscious complexes
            self.all_complexes = self.find_conscious_complexes()
            if self.all_complexes:
                self.main_complex = self.all_complexes[0]

            # Update statistics
            self.total_phi_calculations += 1
            self.phi_history.append((current_time, self.current_phi))

            # Calculate average Φ
            recent_phis = [phi for _, phi in self.phi_history[-20:]]
            self.average_phi = sum(recent_phis) / len(recent_phis) if recent_phis else 0.0

            # Update metrics
            self.metrics.awareness_level = min(1.0, self.current_phi / 2.0)
            self.metrics.integration_level = self.current_phi

            # Keep history manageable
            if len(self.phi_history) > 100:
                self.phi_history = self.phi_history[-100:]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the IIT system"""
        return {
            "num_elements": len(self.elements),
            "num_connections": len([c for c in self.connections if c.active]),
            "current_phi": self.current_phi,
            "main_complex_phi": self.main_complex.phi_value if self.main_complex else 0.0,
            "num_complexes": len(self.all_complexes),
            "total_phi_calculations": self.total_phi_calculations,
            "average_phi": self.average_phi,
            "element_states": {eid: elem.state for eid, elem in self.elements.items()},
            "cache_size": len(self.partition_cache),
        }

    def get_system_visualization_data(self) -> Dict[str, Any]:
        """Get data for visualizing the system"""
        nodes = []
        edges = []

        for element_id, element in self.elements.items():
            nodes.append(
                {
                    "id": element_id,
                    "state": element.state,
                    "activation_function": element.activation_function,
                    "threshold": element.threshold,
                }
            )

        for connection in self.connections:
            if connection.active:
                edges.append(
                    {
                        "from": connection.from_element,
                        "to": connection.to_element,
                        "weight": connection.weight,
                    }
                )

        return {
            "nodes": nodes,
            "edges": edges,
            "phi": self.current_phi,
            "complexes": [
                {
                    "id": c.complex_id,
                    "elements": list(c.elements),
                    "phi": c.phi_value,
                    "main": c.main_complex,
                }
                for c in self.all_complexes
            ],
        }

    def get_phi_history(self) -> List[Dict[str, Any]]:
        """Get Φ calculation history"""
        return [{"timestamp": timestamp, "phi": phi} for timestamp, phi in self.phi_history]

    def reset_system(self) -> None:
        """Reset the system to initial state"""
        for element in self.elements.values():
            element.state = 0.0

        self.system_state_history.clear()
        self.partition_cache.clear()
        self.current_phi = 0.0
        self.main_complex = None
        self.all_complexes = []

        self.logger.info("Reset IIT system to initial state")
