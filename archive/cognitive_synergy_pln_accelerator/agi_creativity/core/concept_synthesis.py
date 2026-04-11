"""
Novel Concept Synthesis with Combinatorial Creativity

This module implements advanced concept synthesis using combinatorial creativity,
allowing AGI to generate novel ideas by combining existing concepts in innovative ways.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import networkx as nx
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import itertools
import random
from abc import ABC, abstractmethod


@dataclass
class Concept:
    """Represents a creative concept with semantic and structural properties."""
    name: str
    embedding: np.ndarray
    domain: str
    properties: Dict[str, Any]
    creativity_score: float
    novelty_score: float
    feasibility_score: float


@dataclass
class ConceptCombination:
    """Represents a combination of concepts with synthesis metadata."""
    concepts: List[Concept]
    combination_type: str
    synthesis_embedding: np.ndarray
    creativity_potential: float
    coherence_score: float
    novelty_factor: float


class CreativitySpace:
    """Multi-dimensional creativity space for concept exploration."""
    
    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions
        self.concept_graph = nx.Graph()
        self.domain_clusters = {}
        self.creativity_vectors = {}
        
    def add_concept(self, concept: Concept) -> None:
        """Add a concept to the creativity space."""
        self.concept_graph.add_node(concept.name, 
                                   embedding=concept.embedding,
                                   domain=concept.domain,
                                   properties=concept.properties)
        
    def compute_concept_distances(self, concept1: Concept, concept2: Concept) -> Dict[str, float]:
        """Compute various distance metrics between concepts."""
        semantic_distance = np.linalg.norm(concept1.embedding - concept2.embedding)
        
        # Domain distance
        domain_distance = 0.0 if concept1.domain == concept2.domain else 1.0
        
        # Property distance
        property_overlap = len(set(concept1.properties.keys()) & 
                             set(concept2.properties.keys()))
        property_distance = 1.0 - (property_overlap / 
                                 max(len(concept1.properties), len(concept2.properties)))
        
        return {
            'semantic': semantic_distance,
            'domain': domain_distance,
            'property': property_distance,
            'combined': (semantic_distance + domain_distance + property_distance) / 3
        }
        
    def find_creative_neighborhoods(self, concept: Concept, 
                                  radius: float = 0.3) -> List[Concept]:
        """Find concepts within creative neighborhood for potential synthesis."""
        neighbors = []
        
        for node in self.concept_graph.nodes():
            if node != concept.name:
                node_data = self.concept_graph.nodes[node]
                other_concept = Concept(
                    name=node,
                    embedding=node_data['embedding'],
                    domain=node_data['domain'],
                    properties=node_data['properties'],
                    creativity_score=0.0,
                    novelty_score=0.0,
                    feasibility_score=0.0
                )
                
                distances = self.compute_concept_distances(concept, other_concept)
                if distances['combined'] <= radius:
                    neighbors.append(other_concept)
                    
        return neighbors


class CombinatorialCreativity:
    """Engine for generating novel concepts through combinatorial methods."""
    
    def __init__(self):
        self.combination_strategies = {
            'blend': self._blend_concepts,
            'merge': self._merge_concepts,
            'juxtapose': self._juxtapose_concepts,
            'transform': self._transform_concepts,
            'analogize': self._analogize_concepts,
            'metaphorize': self._metaphorize_concepts
        }
        
    def _blend_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Blend concepts by interpolating their properties."""
        if len(concepts) < 2:
            raise ValueError("Blending requires at least 2 concepts")
            
        # Average embeddings
        avg_embedding = np.mean([c.embedding for c in concepts], axis=0)
        
        # Blend properties
        blended_properties = {}
        for concept in concepts:
            for key, value in concept.properties.items():
                if key in blended_properties:
                    if isinstance(value, (int, float)):
                        blended_properties[key] = (blended_properties[key] + value) / 2
                    else:
                        blended_properties[key] = f"{blended_properties[key]}+{value}"
                else:
                    blended_properties[key] = value
        
        creativity_potential = np.mean([c.creativity_score for c in concepts]) * 1.2
        coherence_score = self._compute_coherence(concepts)
        novelty_factor = self._compute_novelty_factor(concepts, 'blend')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='blend',
            synthesis_embedding=avg_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _merge_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Merge concepts by combining their distinct properties."""
        merged_embedding = np.concatenate([c.embedding for c in concepts])
        if len(merged_embedding) > concepts[0].embedding.shape[0]:
            # Use PCA to reduce dimensions
            pca = PCA(n_components=concepts[0].embedding.shape[0])
            merged_embedding = pca.fit_transform(merged_embedding.reshape(1, -1))[0]
            
        merged_properties = {}
        for concept in concepts:
            merged_properties.update(concept.properties)
            
        creativity_potential = sum(c.creativity_score for c in concepts) * 0.8
        coherence_score = self._compute_coherence(concepts)
        novelty_factor = self._compute_novelty_factor(concepts, 'merge')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='merge',
            synthesis_embedding=merged_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _juxtapose_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Create novel combinations through conceptual juxtaposition."""
        # Create tension between disparate concepts
        juxtaposed_embedding = concepts[0].embedding - concepts[1].embedding if len(concepts) >= 2 else concepts[0].embedding
        
        # Create contrasting properties
        juxtaposed_properties = {
            'primary_concept': concepts[0].name,
            'secondary_concept': concepts[1].name if len(concepts) > 1 else None,
            'tension_points': self._find_tension_points(concepts)
        }
        
        creativity_potential = max(c.creativity_score for c in concepts) * 1.5
        coherence_score = self._compute_coherence(concepts) * 0.7  # Lower coherence for juxtaposition
        novelty_factor = self._compute_novelty_factor(concepts, 'juxtapose')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='juxtapose',
            synthesis_embedding=juxtaposed_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _transform_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Transform concepts through systematic modification."""
        base_concept = concepts[0]
        transformed_embedding = self._apply_transformation_matrix(base_concept.embedding)
        
        transformed_properties = base_concept.properties.copy()
        for key, value in transformed_properties.items():
            if isinstance(value, str):
                transformed_properties[key] = f"transformed_{value}"
            elif isinstance(value, (int, float)):
                transformed_properties[key] = value * random.uniform(0.5, 2.0)
                
        creativity_potential = base_concept.creativity_score * 1.3
        coherence_score = 0.8  # Transformations maintain some coherence
        novelty_factor = self._compute_novelty_factor(concepts, 'transform')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='transform',
            synthesis_embedding=transformed_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _analogize_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Create analogical relationships between concepts."""
        if len(concepts) < 2:
            raise ValueError("Analogizing requires at least 2 concepts")
            
        # Find structural similarities
        analogy_embedding = self._compute_analogy_embedding(concepts[0], concepts[1])
        
        analogy_properties = {
            'source_domain': concepts[0].domain,
            'target_domain': concepts[1].domain,
            'analogical_mapping': self._compute_analogical_mapping(concepts[0], concepts[1]),
            'structural_similarity': self._compute_structural_similarity(concepts[0], concepts[1])
        }
        
        creativity_potential = (concepts[0].creativity_score + concepts[1].creativity_score) * 1.1
        coherence_score = self._compute_coherence(concepts)
        novelty_factor = self._compute_novelty_factor(concepts, 'analogize')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='analogize',
            synthesis_embedding=analogy_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _metaphorize_concepts(self, concepts: List[Concept]) -> ConceptCombination:
        """Create metaphorical relationships between concepts."""
        if len(concepts) < 2:
            raise ValueError("Metaphorizing requires at least 2 concepts")
            
        # Create metaphorical space
        metaphor_embedding = self._create_metaphor_space(concepts[0], concepts[1])
        
        metaphor_properties = {
            'tenor': concepts[0].name,  # What we're talking about
            'vehicle': concepts[1].name,  # What we're comparing it to
            'metaphorical_features': self._extract_metaphorical_features(concepts[0], concepts[1]),
            'conceptual_distance': np.linalg.norm(concepts[0].embedding - concepts[1].embedding)
        }
        
        creativity_potential = max(c.creativity_score for c in concepts) * 1.4
        coherence_score = self._compute_coherence(concepts) * 0.9
        novelty_factor = self._compute_novelty_factor(concepts, 'metaphorize')
        
        return ConceptCombination(
            concepts=concepts,
            combination_type='metaphorize',
            synthesis_embedding=metaphor_embedding,
            creativity_potential=creativity_potential,
            coherence_score=coherence_score,
            novelty_factor=novelty_factor
        )
        
    def _compute_coherence(self, concepts: List[Concept]) -> float:
        """Compute coherence score for concept combination."""
        if len(concepts) < 2:
            return 1.0
            
        coherence_scores = []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                similarity = np.dot(concepts[i].embedding, concepts[j].embedding) / (
                    np.linalg.norm(concepts[i].embedding) * np.linalg.norm(concepts[j].embedding)
                )
                coherence_scores.append(abs(similarity))
                
        return np.mean(coherence_scores) if coherence_scores else 0.0
        
    def _compute_novelty_factor(self, concepts: List[Concept], combination_type: str) -> float:
        """Compute novelty factor for concept combination."""
        base_novelty = np.mean([c.novelty_score for c in concepts])
        
        type_multipliers = {
            'blend': 1.1,
            'merge': 1.0,
            'juxtapose': 1.5,
            'transform': 1.3,
            'analogize': 1.2,
            'metaphorize': 1.4
        }
        
        return base_novelty * type_multipliers.get(combination_type, 1.0)
        
    def _find_tension_points(self, concepts: List[Concept]) -> List[str]:
        """Find points of tension between concepts for juxtaposition."""
        if len(concepts) < 2:
            return []
            
        tension_points = []
        for key in concepts[0].properties:
            if key in concepts[1].properties:
                val1, val2 = concepts[0].properties[key], concepts[1].properties[key]
                if val1 != val2:
                    tension_points.append(f"{key}: {val1} vs {val2}")
                    
        return tension_points
        
    def _apply_transformation_matrix(self, embedding: np.ndarray) -> np.ndarray:
        """Apply creative transformation to concept embedding."""
        # Random rotation and scaling
        rotation_angle = random.uniform(0, 2 * np.pi)
        scale_factor = random.uniform(0.8, 1.2)
        
        if len(embedding) >= 2:
            rotation_matrix = np.array([
                [np.cos(rotation_angle), -np.sin(rotation_angle)],
                [np.sin(rotation_angle), np.cos(rotation_angle)]
            ])
            transformed = embedding.copy()
            transformed[:2] = rotation_matrix @ transformed[:2] * scale_factor
            return transformed
        else:
            return embedding * scale_factor
            
    def _compute_analogy_embedding(self, concept1: Concept, concept2: Concept) -> np.ndarray:
        """Compute embedding for analogical relationship."""
        # A:B :: C:? pattern
        return concept2.embedding - concept1.embedding + concept1.embedding
        
    def _compute_analogical_mapping(self, concept1: Concept, concept2: Concept) -> Dict[str, str]:
        """Compute analogical mapping between concepts."""
        mapping = {}
        for key1, val1 in concept1.properties.items():
            for key2, val2 in concept2.properties.items():
                if key1 != key2 and self._are_analogous(val1, val2):
                    mapping[f"{key1}:{val1}"] = f"{key2}:{val2}"
        return mapping
        
    def _compute_structural_similarity(self, concept1: Concept, concept2: Concept) -> float:
        """Compute structural similarity between concepts."""
        common_structure = len(set(concept1.properties.keys()) & 
                             set(concept2.properties.keys()))
        total_structure = len(set(concept1.properties.keys()) | 
                            set(concept2.properties.keys()))
        return common_structure / total_structure if total_structure > 0 else 0.0
        
    def _create_metaphor_space(self, concept1: Concept, concept2: Concept) -> np.ndarray:
        """Create metaphorical space combining concepts."""
        # Weighted combination favoring the vehicle (concept2)
        return 0.3 * concept1.embedding + 0.7 * concept2.embedding
        
    def _extract_metaphorical_features(self, tenor: Concept, vehicle: Concept) -> List[str]:
        """Extract metaphorical features from tenor-vehicle relationship."""
        features = []
        for key, value in vehicle.properties.items():
            if key not in tenor.properties:
                features.append(f"{tenor.name} has {key} like {value}")
        return features
        
    def _are_analogous(self, val1: Any, val2: Any) -> bool:
        """Check if two values are analogous."""
        if type(val1) == type(val2):
            if isinstance(val1, str):
                return len(val1) == len(val2)  # Similar string structure
            elif isinstance(val1, (int, float)):
                return abs(val1 - val2) < 0.1 * max(abs(val1), abs(val2))
        return False


class ConceptSynthesizer:
    """Main class for novel concept synthesis with combinatorial creativity."""
    
    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim
        self.creativity_space = CreativitySpace(embedding_dim)
        self.combinatorial_engine = CombinatorialCreativity()
        self.concept_repository = {}
        self.synthesis_history = []
        
    def add_concept(self, concept: Concept) -> None:
        """Add a concept to the synthesis system."""
        self.concept_repository[concept.name] = concept
        self.creativity_space.add_concept(concept)
        
    def synthesize_novel_concepts(self, 
                                base_concepts: List[str],
                                num_combinations: int = 5,
                                strategies: Optional[List[str]] = None) -> List[ConceptCombination]:
        """Synthesize novel concepts from base concepts."""
        if strategies is None:
            strategies = list(self.combinatorial_engine.combination_strategies.keys())
            
        base_concept_objects = [self.concept_repository[name] for name in base_concepts 
                              if name in self.concept_repository]
        
        if len(base_concept_objects) < 2:
            raise ValueError("Need at least 2 concepts for synthesis")
            
        novel_combinations = []
        
        # Generate combinations using different strategies
        for strategy in strategies:
            if len(novel_combinations) >= num_combinations:
                break
                
            # Try different concept groupings
            for r in range(2, min(len(base_concept_objects) + 1, 4)):
                for concept_group in itertools.combinations(base_concept_objects, r):
                    if len(novel_combinations) >= num_combinations:
                        break
                        
                    try:
                        combination_func = self.combinatorial_engine.combination_strategies[strategy]
                        combination = combination_func(list(concept_group))
                        
                        # Filter by creativity potential
                        if combination.creativity_potential > 0.5:
                            novel_combinations.append(combination)
                            self.synthesis_history.append(combination)
                            
                    except Exception as e:
                        continue  # Skip invalid combinations
                        
        # Sort by creativity potential and return top combinations
        novel_combinations.sort(key=lambda x: x.creativity_potential, reverse=True)
        return novel_combinations[:num_combinations]
        
    def explore_creative_space(self, 
                             starting_concept: str,
                             exploration_depth: int = 3,
                             breadth: int = 5) -> List[ConceptCombination]:
        """Explore the creative space starting from a concept."""
        if starting_concept not in self.concept_repository:
            raise ValueError(f"Concept '{starting_concept}' not found")
            
        explored_combinations = []
        current_concepts = [self.concept_repository[starting_concept]]
        
        for depth in range(exploration_depth):
            next_level_concepts = []
            
            for concept in current_concepts[:breadth]:
                # Find creative neighbors
                neighbors = self.creativity_space.find_creative_neighborhoods(concept)
                
                # Generate combinations with neighbors
                for neighbor in neighbors[:3]:  # Limit to top 3 neighbors
                    combinations = self.synthesize_novel_concepts(
                        [concept.name, neighbor.name], 
                        num_combinations=2,
                        strategies=['blend', 'analogize']
                    )
                    explored_combinations.extend(combinations)
                    
                    # Add synthesized concepts for next exploration level
                    for combo in combinations:
                        # Create new concept from combination
                        new_concept = Concept(
                            name=f"synth_{len(self.concept_repository)}",
                            embedding=combo.synthesis_embedding,
                            domain=f"synthetic_{depth}",
                            properties={'source': [c.name for c in combo.concepts],
                                      'type': combo.combination_type},
                            creativity_score=combo.creativity_potential,
                            novelty_score=combo.novelty_factor,
                            feasibility_score=combo.coherence_score
                        )
                        next_level_concepts.append(new_concept)
                        self.add_concept(new_concept)
                        
            current_concepts = next_level_concepts
            
        return explored_combinations
        
    def evaluate_concept_creativity(self, concept: Concept) -> Dict[str, float]:
        """Evaluate the creativity of a concept across multiple dimensions."""
        evaluation = {}
        
        # Novelty: How different is it from existing concepts?
        if len(self.concept_repository) > 1:
            similarities = []
            for other_concept in self.concept_repository.values():
                if other_concept.name != concept.name:
                    similarity = np.dot(concept.embedding, other_concept.embedding) / (
                        np.linalg.norm(concept.embedding) * np.linalg.norm(other_concept.embedding)
                    )
                    similarities.append(similarity)
            evaluation['novelty'] = 1.0 - np.mean(similarities) if similarities else 1.0
        else:
            evaluation['novelty'] = 1.0
            
        # Value: How valuable/useful is the concept?
        evaluation['value'] = concept.feasibility_score * concept.creativity_score
        
        # Surprise: How unexpected is the concept?
        evaluation['surprise'] = concept.novelty_score * (1.0 - concept.coherence_score)
        
        # Overall creativity
        evaluation['creativity'] = (
            0.4 * evaluation['novelty'] +
            0.3 * evaluation['value'] +
            0.3 * evaluation['surprise']
        )
        
        return evaluation
        
    def get_synthesis_statistics(self) -> Dict[str, Any]:
        """Get statistics about the synthesis process."""
        if not self.synthesis_history:
            return {"total_syntheses": 0}
            
        strategies_used = [combo.combination_type for combo in self.synthesis_history]
        strategy_counts = {}
        for strategy in strategies_used:
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
        creativity_scores = [combo.creativity_potential for combo in self.synthesis_history]
        
        return {
            "total_syntheses": len(self.synthesis_history),
            "strategy_usage": strategy_counts,
            "average_creativity": np.mean(creativity_scores),
            "max_creativity": np.max(creativity_scores),
            "total_concepts": len(self.concept_repository)
        }