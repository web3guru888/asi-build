"""
Emergent Properties Detection
============================

Advanced detection system for emergent properties arising from cognitive synergy.
Identifies novel behaviors, capabilities, and structures that emerge from the
interaction of cognitive processes.
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import time
from abc import ABC, abstractmethod
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import logging


@dataclass
class EmergentProperty:
    """Represents an emergent property"""
    id: str
    name: str
    description: str
    emergence_type: str  # 'behavioral', 'structural', 'functional', 'cognitive'
    strength: float  # Emergence strength (0-1)
    novelty: float  # How novel this property is (0-1)
    stability: float  # How stable/persistent the property is (0-1)
    complexity: float  # Complexity level of the property (0-1)
    contributing_processes: List[str]
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    first_detected: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    observation_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergenceSignature:
    """Signature pattern indicating emergence"""
    signature_type: str
    pattern: Dict[str, Any]
    threshold: float
    confidence: float
    detection_function: Optional[Callable] = None


class EmergenceDetector(ABC):
    """Abstract base class for emergence detectors"""
    
    @abstractmethod
    def detect(self, system_state: Dict[str, Any]) -> List[EmergentProperty]:
        """Detect emergent properties in system state"""
        pass
    
    @abstractmethod
    def get_detector_type(self) -> str:
        """Get detector type identifier"""
        pass


class BehavioralEmergenceDetector(EmergenceDetector):
    """Detects emergent behaviors in cognitive processes"""
    
    def __init__(self, novelty_threshold: float = 0.7):
        self.novelty_threshold = novelty_threshold
        self.behavior_history = defaultdict(list)
        self.known_behaviors = set()
    
    def detect(self, system_state: Dict[str, Any]) -> List[EmergentProperty]:
        """Detect emergent behaviors"""
        emergent_properties = []
        
        # Extract behavioral patterns from system state
        behaviors = self._extract_behaviors(system_state)
        
        for behavior in behaviors:
            novelty = self._compute_behavior_novelty(behavior)
            
            if novelty > self.novelty_threshold:
                # Detected novel behavior
                prop = EmergentProperty(
                    id=f"behavior_{int(time.time() * 1000)}",
                    name=behavior['name'],
                    description=f"Emergent behavior: {behavior['description']}",
                    emergence_type='behavioral',
                    strength=behavior['strength'],
                    novelty=novelty,
                    stability=self._compute_behavior_stability(behavior),
                    complexity=self._compute_behavior_complexity(behavior),
                    contributing_processes=behavior.get('processes', [])
                )
                emergent_properties.append(prop)
                
                # Add to known behaviors
                self.known_behaviors.add(behavior['signature'])
        
        return emergent_properties
    
    def _extract_behaviors(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract behavioral patterns from system state"""
        behaviors = []
        
        # Look for coordinated process activations
        if 'synergy_pairs' in system_state:
            for pair_name, pair_data in system_state['synergy_pairs'].items():
                synergy_strength = pair_data.get('synergy_strength', 0)
                
                if synergy_strength > 0.8:  # High synergy
                    behaviors.append({
                        'name': f'coordinated_{pair_name}',
                        'description': f'High coordination between {pair_name} processes',
                        'signature': f'coord_{pair_name}_{synergy_strength:.2f}',
                        'strength': synergy_strength,
                        'processes': [pair_name],
                        'type': 'coordination'
                    })
        
        # Look for cascade patterns
        if 'cognitive_dynamics' in system_state:
            cascade_behaviors = self._detect_cascade_patterns(
                system_state['cognitive_dynamics']
            )
            behaviors.extend(cascade_behaviors)
        
        return behaviors
    
    def _detect_cascade_patterns(self, dynamics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect cascade behavioral patterns"""
        cascades = []
        
        # Group dynamics by time
        time_groups = defaultdict(list)
        for dynamic in dynamics:
            time_key = int(dynamic.get('age', 0) / 5)  # 5-second bins
            time_groups[time_key].append(dynamic)
        
        # Look for rapid succession of related dynamics
        for time_key, group in time_groups.items():
            if len(group) >= 3:  # Multiple dynamics in short time
                cascades.append({
                    'name': f'cascade_{time_key}',
                    'description': f'Cascade of {len(group)} dynamics',
                    'signature': f'cascade_{len(group)}_{time_key}',
                    'strength': min(1.0, len(group) / 5.0),
                    'processes': [d.get('parameters', {}).get('pair', 'unknown') for d in group],
                    'type': 'cascade'
                })
        
        return cascades
    
    def _compute_behavior_novelty(self, behavior: Dict[str, Any]) -> float:
        """Compute novelty of a behavior"""
        signature = behavior['signature']
        
        if signature in self.known_behaviors:
            return 0.0  # Already known
        
        # Compute similarity to known behaviors
        max_similarity = 0.0
        for known_signature in self.known_behaviors:
            similarity = self._compute_signature_similarity(signature, known_signature)
            max_similarity = max(max_similarity, similarity)
        
        novelty = 1.0 - max_similarity
        return novelty
    
    def _compute_signature_similarity(self, sig1: str, sig2: str) -> float:
        """Compute similarity between behavior signatures"""
        # Simple string similarity
        words1 = set(sig1.split('_'))
        words2 = set(sig2.split('_'))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_behavior_stability(self, behavior: Dict[str, Any]) -> float:
        """Compute stability of behavior"""
        # For now, use strength as proxy for stability
        return behavior['strength']
    
    def _compute_behavior_complexity(self, behavior: Dict[str, Any]) -> float:
        """Compute complexity of behavior"""
        # Based on number of contributing processes and type
        num_processes = len(behavior.get('processes', []))
        type_complexity = {'coordination': 0.5, 'cascade': 0.8, 'oscillation': 0.6}
        
        base_complexity = min(1.0, num_processes / 5.0)
        type_mult = type_complexity.get(behavior.get('type'), 0.5)
        
        return base_complexity * type_mult
    
    def get_detector_type(self) -> str:
        return "behavioral"


class StructuralEmergenceDetector(EmergenceDetector):
    """Detects emergent structures in cognitive architecture"""
    
    def __init__(self, structure_threshold: float = 0.6):
        self.structure_threshold = structure_threshold
        self.known_structures = {}
    
    def detect(self, system_state: Dict[str, Any]) -> List[EmergentProperty]:
        """Detect emergent structures"""
        emergent_properties = []
        
        # Extract structural information
        structures = self._extract_structures(system_state)
        
        for structure in structures:
            novelty = self._compute_structure_novelty(structure)
            
            if novelty > self.structure_threshold:
                prop = EmergentProperty(
                    id=f"structure_{int(time.time() * 1000)}",
                    name=structure['name'],
                    description=f"Emergent structure: {structure['description']}",
                    emergence_type='structural',
                    strength=structure['strength'],
                    novelty=novelty,
                    stability=self._compute_structure_stability(structure),
                    complexity=self._compute_structure_complexity(structure),
                    contributing_processes=structure.get('components', [])
                )
                emergent_properties.append(prop)
        
        return emergent_properties
    
    def _extract_structures(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structural patterns"""
        structures = []
        
        # Network structures from integration matrix
        if 'integration_matrix' in system_state:
            matrix = np.array(system_state['integration_matrix'])
            network_structures = self._analyze_network_structure(matrix)
            structures.extend(network_structures)
        
        # Hierarchical structures from synergy relationships
        if 'synergy_pairs' in system_state:
            hierarchical_structures = self._analyze_hierarchical_structures(
                system_state['synergy_pairs']
            )
            structures.extend(hierarchical_structures)
        
        return structures
    
    def _analyze_network_structure(self, matrix: np.ndarray) -> List[Dict[str, Any]]:
        """Analyze network structures in integration matrix"""
        structures = []
        
        # Create graph from matrix
        G = nx.from_numpy_array(matrix)
        
        # Detect communities
        try:
            import networkx.algorithms.community as nx_comm
            communities = list(nx_comm.greedy_modularity_communities(G))
            
            if len(communities) > 1:
                structures.append({
                    'name': 'modular_community',
                    'description': f'Modular community structure with {len(communities)} communities',
                    'strength': nx_comm.modularity(G, communities),
                    'components': [f'community_{i}' for i in range(len(communities))],
                    'type': 'community'
                })
        except Exception:
            pass
        
        # Detect hubs
        degrees = dict(G.degree())
        if degrees:
            max_degree = max(degrees.values())
            avg_degree = np.mean(list(degrees.values()))
            
            if max_degree > avg_degree * 2:  # Hub detected
                hubs = [node for node, degree in degrees.items() 
                       if degree > avg_degree * 1.5]
                
                structures.append({
                    'name': 'hub_structure',
                    'description': f'Hub structure with {len(hubs)} hubs',
                    'strength': max_degree / (len(G.nodes()) - 1) if len(G.nodes()) > 1 else 0,
                    'components': [f'hub_{hub}' for hub in hubs],
                    'type': 'hub'
                })
        
        return structures
    
    def _analyze_hierarchical_structures(self, synergy_pairs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze hierarchical structures in synergy relationships"""
        structures = []
        
        # Build hierarchy based on synergy strengths
        hierarchy_levels = defaultdict(list)
        
        for pair_name, pair_data in synergy_pairs.items():
            strength = pair_data.get('synergy_strength', 0)
            
            if strength > 0.8:
                hierarchy_levels['high'].append(pair_name)
            elif strength > 0.6:
                hierarchy_levels['medium'].append(pair_name)
            elif strength > 0.3:
                hierarchy_levels['low'].append(pair_name)
        
        # Check for hierarchical organization
        if len(hierarchy_levels['high']) > 0 and len(hierarchy_levels['medium']) > 0:
            structures.append({
                'name': 'hierarchical_synergy',
                'description': f'Hierarchical synergy organization',
                'strength': len(hierarchy_levels['high']) / len(synergy_pairs),
                'components': list(synergy_pairs.keys()),
                'type': 'hierarchy'
            })
        
        return structures
    
    def _compute_structure_novelty(self, structure: Dict[str, Any]) -> float:
        """Compute novelty of structure"""
        structure_type = structure.get('type', 'unknown')
        
        if structure_type in self.known_structures:
            # Compare with known structures of same type
            known_strength = self.known_structures[structure_type]
            strength_diff = abs(structure['strength'] - known_strength)
            novelty = min(1.0, strength_diff * 2)  # Scale difference
        else:
            novelty = 1.0  # Completely new structure type
            self.known_structures[structure_type] = structure['strength']
        
        return novelty
    
    def _compute_structure_stability(self, structure: Dict[str, Any]) -> float:
        """Compute stability of structure"""
        return structure['strength']  # Use strength as proxy
    
    def _compute_structure_complexity(self, structure: Dict[str, Any]) -> float:
        """Compute complexity of structure"""
        num_components = len(structure.get('components', []))
        type_complexity = {'community': 0.8, 'hub': 0.6, 'hierarchy': 0.9}
        
        base_complexity = min(1.0, num_components / 10.0)
        type_mult = type_complexity.get(structure.get('type'), 0.5)
        
        return base_complexity * type_mult
    
    def get_detector_type(self) -> str:
        return "structural"


class FunctionalEmergenceDetector(EmergenceDetector):
    """Detects emergent functions and capabilities"""
    
    def __init__(self, capability_threshold: float = 0.7):
        self.capability_threshold = capability_threshold
        self.known_capabilities = set()
        self.performance_history = defaultdict(list)
    
    def detect(self, system_state: Dict[str, Any]) -> List[EmergentProperty]:
        """Detect emergent functional capabilities"""
        emergent_properties = []
        
        # Extract functional patterns
        functions = self._extract_functions(system_state)
        
        for function in functions:
            novelty = self._compute_function_novelty(function)
            
            if novelty > self.capability_threshold:
                prop = EmergentProperty(
                    id=f"function_{int(time.time() * 1000)}",
                    name=function['name'],
                    description=f"Emergent capability: {function['description']}",
                    emergence_type='functional',
                    strength=function['strength'],
                    novelty=novelty,
                    stability=self._compute_function_stability(function),
                    complexity=self._compute_function_complexity(function),
                    contributing_processes=function.get('processes', [])
                )
                emergent_properties.append(prop)
        
        return emergent_properties
    
    def _extract_functions(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract functional capabilities"""
        functions = []
        
        # Meta-cognitive functions from high integration
        if 'global_coherence' in system_state:
            coherence = system_state['global_coherence']
            
            if coherence > 0.8:
                functions.append({
                    'name': 'metacognitive_integration',
                    'description': 'High-level cognitive integration capability',
                    'strength': coherence,
                    'processes': ['all_systems'],
                    'type': 'integration'
                })
        
        # Problem-solving functions from reasoning-pattern synergy
        if 'synergy_pairs' in system_state:
            pr_synergy = system_state['synergy_pairs'].get('pattern_reasoning', {})
            pr_strength = pr_synergy.get('synergy_strength', 0)
            
            if pr_strength > 0.8:
                functions.append({
                    'name': 'enhanced_problem_solving',
                    'description': 'Enhanced problem-solving from pattern-reasoning synergy',
                    'strength': pr_strength,
                    'processes': ['pattern_mining', 'reasoning'],
                    'type': 'problem_solving'
                })
        
        # Learning functions from memory-learning synergy
        if 'synergy_pairs' in system_state:
            ml_synergy = system_state['synergy_pairs'].get('memory_learning', {})
            ml_strength = ml_synergy.get('synergy_strength', 0)
            
            if ml_strength > 0.8:
                functions.append({
                    'name': 'accelerated_learning',
                    'description': 'Accelerated learning from memory-learning synergy',
                    'strength': ml_strength,
                    'processes': ['memory', 'learning'],
                    'type': 'learning'
                })
        
        return functions
    
    def _compute_function_novelty(self, function: Dict[str, Any]) -> float:
        """Compute novelty of functional capability"""
        func_name = function['name']
        
        if func_name in self.known_capabilities:
            return 0.0  # Already known
        
        # Check for similar capabilities
        similarity_threshold = 0.8
        for known_func in self.known_capabilities:
            similarity = self._compute_function_similarity(func_name, known_func)
            if similarity > similarity_threshold:
                return 1.0 - similarity
        
        # Completely novel
        self.known_capabilities.add(func_name)
        return 1.0
    
    def _compute_function_similarity(self, func1: str, func2: str) -> float:
        """Compute similarity between functions"""
        words1 = set(func1.lower().split('_'))
        words2 = set(func2.lower().split('_'))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_function_stability(self, function: Dict[str, Any]) -> float:
        """Compute stability of function"""
        func_name = function['name']
        strength = function['strength']
        
        # Track performance history
        self.performance_history[func_name].append(strength)
        
        if len(self.performance_history[func_name]) >= 5:
            # Compute stability as inverse of variance
            history = self.performance_history[func_name][-10:]  # Last 10 observations
            variance = np.var(history)
            stability = 1.0 / (1.0 + variance)
            return stability
        
        return strength  # Use strength as initial stability estimate
    
    def _compute_function_complexity(self, function: Dict[str, Any]) -> float:
        """Compute complexity of function"""
        num_processes = len(function.get('processes', []))
        type_complexity = {
            'integration': 0.9,
            'problem_solving': 0.8,
            'learning': 0.7,
            'memory': 0.6
        }
        
        base_complexity = min(1.0, num_processes / 3.0)
        type_mult = type_complexity.get(function.get('type'), 0.5)
        
        return base_complexity * type_mult
    
    def get_detector_type(self) -> str:
        return "functional"


class EmergentPropertyDetector:
    """
    Main detector orchestrating multiple emergence detection mechanisms.
    
    Coordinates detection of:
    - Behavioral emergence (novel behaviors)
    - Structural emergence (new architectures)
    - Functional emergence (new capabilities)
    - Cognitive emergence (higher-order cognition)
    """
    
    def __init__(self, 
                 emergence_threshold: float = 0.7,
                 stability_window: int = 10):
        """
        Initialize emergent property detector.
        
        Args:
            emergence_threshold: Minimum emergence strength to report
            stability_window: Window size for stability analysis
        """
        self.emergence_threshold = emergence_threshold
        self.stability_window = stability_window
        
        # Specialized detectors
        self.detectors = {
            'behavioral': BehavioralEmergenceDetector(),
            'structural': StructuralEmergenceDetector(),
            'functional': FunctionalEmergenceDetector()
        }
        
        # Property tracking
        self.detected_properties: Dict[str, EmergentProperty] = {}
        self.emergence_history = deque(maxlen=1000)
        
        # Statistics
        self.detection_stats = {
            'total_detected': 0,
            'by_type': defaultdict(int),
            'novel_properties': 0,
            'stable_properties': 0
        }
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def detect_emergence(self, system_state: Dict[str, Any]) -> List[EmergentProperty]:
        """Detect emergent properties across all categories"""
        all_emergent_properties = []
        
        # Run all detectors
        for detector_type, detector in self.detectors.items():
            try:
                properties = detector.detect(system_state)
                
                # Filter by threshold
                filtered_properties = [
                    prop for prop in properties
                    if prop.strength > self.emergence_threshold
                ]
                
                all_emergent_properties.extend(filtered_properties)
                
            except Exception as e:
                self.logger.error(f"Error in {detector_type} detector: {e}")
        
        # Update tracking
        self._update_property_tracking(all_emergent_properties)
        
        # Update statistics
        self._update_statistics(all_emergent_properties)
        
        return all_emergent_properties
    
    def _update_property_tracking(self, properties: List[EmergentProperty]):
        """Update tracking of detected properties"""
        current_time = time.time()
        
        for prop in properties:
            if prop.id in self.detected_properties:
                # Update existing property
                existing = self.detected_properties[prop.id]
                existing.last_observed = current_time
                existing.observation_count += 1
                
                # Update stability based on consistency
                existing.stability = self._compute_stability(existing)
                
            else:
                # New property
                prop.first_detected = current_time
                prop.last_observed = current_time
                self.detected_properties[prop.id] = prop
            
            # Add to history
            self.emergence_history.append({
                'property_id': prop.id,
                'timestamp': current_time,
                'strength': prop.strength,
                'novelty': prop.novelty
            })
    
    def _compute_stability(self, prop: EmergentProperty) -> float:
        """Compute stability of a property based on observation history"""
        # Get recent observations
        recent_observations = [
            obs for obs in self.emergence_history
            if (obs['property_id'] == prop.id and
                time.time() - obs['timestamp'] < 300)  # Last 5 minutes
        ]
        
        if len(recent_observations) < 3:
            return prop.stability  # Not enough data
        
        # Compute stability as consistency of strength
        strengths = [obs['strength'] for obs in recent_observations]
        variance = np.var(strengths)
        stability = 1.0 / (1.0 + variance)
        
        return stability
    
    def _update_statistics(self, properties: List[EmergentProperty]):
        """Update detection statistics"""
        self.detection_stats['total_detected'] += len(properties)
        
        for prop in properties:
            self.detection_stats['by_type'][prop.emergence_type] += 1
            
            if prop.novelty > 0.8:
                self.detection_stats['novel_properties'] += 1
            
            if prop.stability > 0.8:
                self.detection_stats['stable_properties'] += 1
    
    def get_stable_properties(self, min_stability: float = 0.7) -> List[EmergentProperty]:
        """Get properties with high stability"""
        return [
            prop for prop in self.detected_properties.values()
            if prop.stability > min_stability
        ]
    
    def get_novel_properties(self, min_novelty: float = 0.8) -> List[EmergentProperty]:
        """Get highly novel properties"""
        return [
            prop for prop in self.detected_properties.values()
            if prop.novelty > min_novelty
        ]
    
    def get_complex_properties(self, min_complexity: float = 0.7) -> List[EmergentProperty]:
        """Get highly complex properties"""
        return [
            prop for prop in self.detected_properties.values()
            if prop.complexity > min_complexity
        ]
    
    def detect_system_emergence(self, synergy_pairs: Dict[str, Any],
                              global_coherence: float,
                              integration_matrix: np.ndarray) -> List[EmergentProperty]:
        """Detect system-level emergence patterns"""
        system_properties = []
        
        # Meta-cognitive emergence from high global coherence
        if global_coherence > 0.9:
            prop = EmergentProperty(
                id=f"metacognitive_{int(time.time() * 1000)}",
                name="metacognitive_emergence",
                description="System-level metacognitive emergence",
                emergence_type="cognitive",
                strength=global_coherence,
                novelty=0.9,
                stability=global_coherence,
                complexity=0.95,
                contributing_processes=list(synergy_pairs.keys())
            )
            system_properties.append(prop)
        
        # Collective intelligence from high integration
        integration_mean = np.mean(integration_matrix)
        if integration_mean > 0.8:
            prop = EmergentProperty(
                id=f"collective_{int(time.time() * 1000)}",
                name="collective_intelligence",
                description="Collective intelligence emergence",
                emergence_type="cognitive",
                strength=integration_mean,
                novelty=0.8,
                stability=integration_mean,
                complexity=0.9,
                contributing_processes=list(synergy_pairs.keys())
            )
            system_properties.append(prop)
        
        return system_properties
    
    def get_emergence_summary(self) -> Dict[str, Any]:
        """Get comprehensive emergence summary"""
        current_time = time.time()
        
        # Recent emergence activity
        recent_properties = [
            prop for prop in self.detected_properties.values()
            if current_time - prop.last_observed < 300  # Last 5 minutes
        ]
        
        return {
            'total_properties': len(self.detected_properties),
            'recent_properties': len(recent_properties),
            'by_type': {
                emergence_type: len([p for p in self.detected_properties.values()
                                   if p.emergence_type == emergence_type])
                for emergence_type in ['behavioral', 'structural', 'functional', 'cognitive']
            },
            'stability_distribution': {
                'high': len([p for p in self.detected_properties.values() if p.stability > 0.8]),
                'medium': len([p for p in self.detected_properties.values() 
                             if 0.5 < p.stability <= 0.8]),
                'low': len([p for p in self.detected_properties.values() if p.stability <= 0.5])
            },
            'novelty_distribution': {
                'high': len([p for p in self.detected_properties.values() if p.novelty > 0.8]),
                'medium': len([p for p in self.detected_properties.values() 
                             if 0.5 < p.novelty <= 0.8]),
                'low': len([p for p in self.detected_properties.values() if p.novelty <= 0.5])
            },
            'detection_stats': self.detection_stats.copy(),
            'most_stable': sorted(self.detected_properties.values(), 
                                key=lambda x: x.stability, reverse=True)[:5],
            'most_novel': sorted(self.detected_properties.values(),
                               key=lambda x: x.novelty, reverse=True)[:5],
            'most_complex': sorted(self.detected_properties.values(),
                                 key=lambda x: x.complexity, reverse=True)[:5]
        }