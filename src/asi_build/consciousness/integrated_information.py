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
        """Compute Φ for a specific subset of elements.

        Uses IIT 3.0 (Oizumi, Albantakis & Tononi 2014): Φ is the minimum
        information partition (MIP) — the bipartition whose *unidirectional
        cut* loses the least integrated information.

        For each bipartition (A, B) we try two unidirectional cuts:
          1. Sever connections from A → B  (keep B → A)
          2. Sever connections from B → A  (keep A → B)

        The minimum KL divergence across both directions gives the φ for
        that partition.  The overall Φ is the minimum across all bipartitions.
        """
        if len(subset) > self.max_partition_size:
            return self._approximate_phi(subset)

        sorted_nodes = sorted(subset)
        n = len(sorted_nodes)

        # Build the whole-system TPM (state-by-node form: 2^n × n)
        tpm_whole = self._build_tpm(sorted_nodes)

        # Get the current binary state of the subset
        current_state = self._get_current_binary_state(sorted_nodes)

        # Whole-system effect distribution
        whole_dist = self._effect_distribution_from_sbn_tpm(tpm_whole, current_state, n)

        min_phi = float("inf")

        node_set_a: Set[str]
        node_set_b: Set[str]

        # Try all non-trivial bipartitions (each side non-empty).
        # Only iterate up to half the size to avoid mirrored duplicates.
        for partition_size in range(1, (n // 2) + 1):
            for indices_a in itertools.combinations(range(n), partition_size):
                indices_b = tuple(i for i in range(n) if i not in indices_a)

                # Skip mirrored duplicate when both halves are equal size
                if len(indices_a) == len(indices_b) and indices_a > indices_b:
                    continue

                node_set_a = {sorted_nodes[i] for i in indices_a}
                node_set_b = {sorted_nodes[i] for i in indices_b}

                # Try both unidirectional cut directions
                for cut_from, cut_to in [(node_set_a, node_set_b),
                                         (node_set_b, node_set_a)]:
                    # Build a TPM with the cut applied (sever cut_from → cut_to)
                    tpm_cut = self._build_tpm(sorted_nodes,
                                              cut_from=cut_from, cut_to=cut_to)
                    cut_dist = self._effect_distribution_from_sbn_tpm(
                        tpm_cut, current_state, n
                    )

                    kl = self._kl_divergence(whole_dist, cut_dist)
                    if kl < min_phi:
                        min_phi = kl

        return max(0.0, min_phi) if min_phi < float("inf") else 0.0

    # ------------------------------------------------------------------
    # TPM construction
    # ------------------------------------------------------------------

    def _build_tpm(
        self,
        sorted_nodes: List[str],
        cut_from: Optional[Set[str]] = None,
        cut_to: Optional[Set[str]] = None,
    ) -> np.ndarray:
        """Build a state-by-node Transition Probability Matrix.

        For *n* binary elements the TPM has shape ``(2**n, n)``.
        Row *i* corresponds to input state *i* (little-endian binary), and
        column *j* gives the probability that node *j* is ON at *t+1*.

        Parameters
        ----------
        sorted_nodes : list of str
            Node names in sorted order.
        cut_from, cut_to : set of str, optional
            If both are provided, connections from any node in *cut_from*
            to any node in *cut_to* are severed (unidirectional cut).
        """
        n = len(sorted_nodes)
        num_states = 1 << n  # 2^n
        epsilon = 1e-10

        # Pre-compute the connection weights *into* each node in sorted_nodes
        # from *all* nodes in sorted_nodes (intra-subset connections only),
        # honouring the optional unidirectional cut.
        node_set = set(sorted_nodes)
        weights_into: Dict[str, Dict[str, float]] = {node: {} for node in sorted_nodes}
        for conn in self.connections:
            if not conn.active:
                continue
            if conn.to_element not in node_set or conn.from_element not in node_set:
                continue
            # Apply the unidirectional cut: skip connections from cut_from→cut_to
            if (
                cut_from is not None
                and cut_to is not None
                and conn.from_element in cut_from
                and conn.to_element in cut_to
            ):
                continue
            weights_into[conn.to_element][conn.from_element] = conn.weight

        tpm = np.zeros((num_states, n), dtype=np.float64)

        for state_idx in range(num_states):
            # Decode state_idx to binary state (little-endian: node 0 = LSB)
            bits = tuple((state_idx >> j) & 1 for j in range(n))

            # Map node names to their binary values for this state
            state_map = {sorted_nodes[j]: float(bits[j]) for j in range(n)}

            for j, node in enumerate(sorted_nodes):
                elem = self.elements[node]

                # Compute total weighted input from within the subset
                total_input = 0.0
                for src, w in weights_into[node].items():
                    total_input += state_map[src] * w

                # Apply activation function to get next-state value
                if elem.activation_function == "sigmoid":
                    next_val = 1.0 / (1.0 + np.exp(-total_input))
                elif elem.activation_function == "threshold":
                    next_val = 1.0 if total_input > elem.threshold else 0.0
                elif elem.activation_function == "linear":
                    next_val = max(0.0, min(1.0, total_input))
                else:
                    next_val = 1.0 / (1.0 + np.exp(-total_input))

                # P(node ON at t+1) — clamp away from exact 0/1 for log safety
                p_on = np.clip(next_val, epsilon, 1.0 - epsilon)
                tpm[state_idx, j] = p_on

        return tpm

    # ------------------------------------------------------------------
    # Distribution helpers
    # ------------------------------------------------------------------

    def _get_current_binary_state(self, sorted_nodes: List[str]) -> Tuple[int, ...]:
        """Return the current binary state of the given nodes."""
        return tuple(1 if self.elements[n].state > 0.5 else 0 for n in sorted_nodes)

    def _effect_distribution_from_sbn_tpm(
        self, tpm: np.ndarray, state: Tuple[int, ...], n: int
    ) -> np.ndarray:
        """Convert a state-by-node TPM row into a full state distribution.

        Given the state-by-node TPM and a current state, compute
        ``P(next_state)`` for every possible next state (2^n entries).

        Each node is assumed to flip independently (conditional on the
        current state), so the joint distribution is the product of the
        marginals.
        """
        # Row index from little-endian binary state
        row_idx = sum(b << i for i, b in enumerate(state))
        p_on = tpm[row_idx]  # shape (n,)

        num_states = 1 << n
        dist = np.zeros(num_states, dtype=np.float64)

        for s in range(num_states):
            prob = 1.0
            for j in range(n):
                bit = (s >> j) & 1
                prob *= p_on[j] if bit else (1.0 - p_on[j])
            dist[s] = prob

        # Normalise (should already sum to ~1, but ensure)
        total = dist.sum()
        if total > 0:
            dist /= total
        else:
            dist[:] = 1.0 / num_states

        return dist

    @staticmethod
    def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
        """KL divergence D_KL(P || Q) with numerical safeguards.

        Adds a tiny epsilon so we never take log(0).
        """
        epsilon = 1e-12
        p_safe = np.clip(p, epsilon, None)
        q_safe = np.clip(q, epsilon, None)
        # Re-normalise after clipping
        p_safe = p_safe / p_safe.sum()
        q_safe = q_safe / q_safe.sum()
        return float(np.sum(p_safe * np.log2(p_safe / q_safe)))

    # ------------------------------------------------------------------
    # Approximation for large subsets
    # ------------------------------------------------------------------

    def _approximate_phi(self, subset: Set[str]) -> float:
        """Approximate Φ for large subsets using a spectral heuristic.

        For systems larger than ``max_partition_size`` we cannot enumerate
        all bipartitions.  Instead we use the algebraic connectivity
        (second-smallest eigenvalue of the Laplacian) of the subset's
        *connectivity* sub-graph as a proxy for integrated information.

        Algebraic connectivity (Fiedler value) measures how well-connected a
        graph is: it is 0 for disconnected graphs and increases with
        integration.  This correlates well with Φ in practice (Tononi &
        Sporns 2003).

        We also scale by the average absolute connection weight so that
        weak connections yield lower Φ.
        """
        sorted_nodes = sorted(subset)
        n = len(sorted_nodes)
        node_set = set(sorted_nodes)
        node_idx = {name: i for i, name in enumerate(sorted_nodes)}

        # Build adjacency matrix (undirected: max of both directions)
        adj = np.zeros((n, n), dtype=np.float64)
        for conn in self.connections:
            if (
                conn.active
                and conn.from_element in node_set
                and conn.to_element in node_set
            ):
                i = node_idx[conn.from_element]
                j = node_idx[conn.to_element]
                w = abs(conn.weight)
                adj[i, j] = max(adj[i, j], w)
                adj[j, i] = max(adj[j, i], w)

        # Graph Laplacian: L = D - A
        degree = adj.sum(axis=1)
        laplacian = np.diag(degree) - adj

        try:
            eigenvalues = np.sort(np.real(np.linalg.eigvalsh(laplacian)))
        except np.linalg.LinAlgError:
            return 0.0

        # Fiedler value (second-smallest eigenvalue)
        fiedler = eigenvalues[1] if n >= 2 else 0.0
        fiedler = max(0.0, fiedler)

        # Scale by mean absolute weight
        total_weight = adj.sum()
        num_edges = np.count_nonzero(adj)
        avg_weight = total_weight / max(num_edges, 1)

        return float(fiedler * avg_weight)

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
