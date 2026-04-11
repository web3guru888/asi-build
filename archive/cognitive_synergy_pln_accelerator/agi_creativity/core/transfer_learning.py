"""
Cross-Domain Creative Transfer Learning

This module implements advanced transfer learning for creativity across different domains,
enabling AGI to apply creative patterns and techniques from one domain to another.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pickle
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import networkx as nx


@dataclass
class Domain:
    """Represents a creative domain with its characteristics."""
    name: str
    description: str
    modalities: List[str]  # visual, audio, text, interactive, etc.
    techniques: List[str]
    constraints: Dict[str, Any]
    cultural_context: Dict[str, Any]
    examples: List[Any]


@dataclass
class CreativePattern:
    """Represents a transferable creative pattern."""
    pattern_id: str
    source_domain: str
    pattern_type: str  # technique, structure, style, etc.
    abstract_representation: np.ndarray
    concrete_features: Dict[str, Any]
    transferability_score: float
    success_rate: float


@dataclass
class TransferMapping:
    """Represents a mapping between domains for knowledge transfer."""
    source_domain: str
    target_domain: str
    pattern_mappings: Dict[str, str]
    transformation_matrix: np.ndarray
    confidence_score: float
    adaptation_strategy: str


class AbstractPatternExtractor(nn.Module):
    """Neural network for extracting abstract creative patterns."""
    
    def __init__(self, input_dim: int, latent_dim: int = 256):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, latent_dim)
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, input_dim)
        )
        
        # Pattern classifier
        self.pattern_classifier = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 10)  # 10 pattern types
        )
        
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)
        
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.decoder(z)
        
    def classify_pattern(self, z: torch.Tensor) -> torch.Tensor:
        return self.pattern_classifier(z)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.encode(x)
        x_recon = self.decode(z)
        pattern_type = self.classify_pattern(z)
        return z, x_recon, pattern_type


class DomainAdapter(nn.Module):
    """Neural network for adapting patterns between domains."""
    
    def __init__(self, source_dim: int, target_dim: int, latent_dim: int = 256):
        super().__init__()
        self.source_dim = source_dim
        self.target_dim = target_dim
        self.latent_dim = latent_dim
        
        # Source encoder
        self.source_encoder = nn.Sequential(
            nn.Linear(source_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, latent_dim)
        )
        
        # Target decoder
        self.target_decoder = nn.Sequential(
            nn.Linear(latent_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, target_dim)
        )
        
        # Domain discriminator (for adversarial training)
        self.domain_discriminator = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        
    def forward(self, source_input: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        latent = self.source_encoder(source_input)
        target_output = self.target_decoder(latent)
        domain_pred = self.domain_discriminator(latent)
        return latent, target_output, domain_pred


class CreativePatternLibrary:
    """Library of extractable and transferable creative patterns."""
    
    def __init__(self):
        self.patterns = {}
        self.domain_patterns = {}
        self.pattern_relationships = nx.Graph()
        
    def add_pattern(self, pattern: CreativePattern) -> None:
        """Add a creative pattern to the library."""
        self.patterns[pattern.pattern_id] = pattern
        
        if pattern.source_domain not in self.domain_patterns:
            self.domain_patterns[pattern.source_domain] = []
        self.domain_patterns[pattern.source_domain].append(pattern.pattern_id)
        
        # Add to pattern relationship graph
        self.pattern_relationships.add_node(pattern.pattern_id, 
                                          domain=pattern.source_domain,
                                          type=pattern.pattern_type)
        
    def find_similar_patterns(self, pattern: CreativePattern, 
                            similarity_threshold: float = 0.8) -> List[CreativePattern]:
        """Find patterns similar to the given pattern."""
        similar = []
        
        for pid, stored_pattern in self.patterns.items():
            if pid != pattern.pattern_id:
                similarity = np.dot(pattern.abstract_representation, 
                                  stored_pattern.abstract_representation) / (
                    np.linalg.norm(pattern.abstract_representation) * 
                    np.linalg.norm(stored_pattern.abstract_representation)
                )
                
                if similarity >= similarity_threshold:
                    similar.append(stored_pattern)
                    
        return similar
        
    def get_transferable_patterns(self, source_domain: str, 
                                target_domain: str) -> List[CreativePattern]:
        """Get patterns that can be transferred between domains."""
        transferable = []
        
        if source_domain in self.domain_patterns:
            for pattern_id in self.domain_patterns[source_domain]:
                pattern = self.patterns[pattern_id]
                if pattern.transferability_score > 0.5:
                    transferable.append(pattern)
                    
        return transferable
        
    def build_pattern_graph(self) -> None:
        """Build relationships between patterns."""
        pattern_list = list(self.patterns.values())
        
        for i, pattern1 in enumerate(pattern_list):
            for j, pattern2 in enumerate(pattern_list[i+1:], i+1):
                similarity = np.dot(pattern1.abstract_representation,
                                  pattern2.abstract_representation) / (
                    np.linalg.norm(pattern1.abstract_representation) *
                    np.linalg.norm(pattern2.abstract_representation)
                )
                
                if similarity > 0.6:
                    self.pattern_relationships.add_edge(
                        pattern1.pattern_id, pattern2.pattern_id,
                        similarity=similarity
                    )


class TransferLearner:
    """Main class for cross-domain creative transfer learning."""
    
    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim
        self.domains = {}
        self.pattern_library = CreativePatternLibrary()
        self.transfer_mappings = {}
        self.pattern_extractor = AbstractPatternExtractor(embedding_dim)
        self.domain_adapters = {}
        self.transfer_history = []
        
    def register_domain(self, domain: Domain) -> None:
        """Register a new creative domain."""
        self.domains[domain.name] = domain
        
    def extract_patterns_from_domain(self, domain_name: str, 
                                   examples: List[np.ndarray]) -> List[CreativePattern]:
        """Extract transferable patterns from domain examples."""
        if domain_name not in self.domains:
            raise ValueError(f"Domain {domain_name} not registered")
            
        domain = self.domains[domain_name]
        extracted_patterns = []
        
        # Convert examples to tensors
        example_tensors = [torch.tensor(ex, dtype=torch.float32) for ex in examples]
        
        for i, example_tensor in enumerate(example_tensors):
            # Extract abstract representation
            with torch.no_grad():
                latent, reconstructed, pattern_type = self.pattern_extractor(example_tensor)
                
            # Create pattern
            pattern = CreativePattern(
                pattern_id=f"{domain_name}_pattern_{i}",
                source_domain=domain_name,
                pattern_type=self._decode_pattern_type(pattern_type),
                abstract_representation=latent.numpy(),
                concrete_features=self._extract_concrete_features(example_tensor),
                transferability_score=self._compute_transferability_score(latent, domain),
                success_rate=0.0  # Will be updated based on transfer results
            )
            
            extracted_patterns.append(pattern)
            self.pattern_library.add_pattern(pattern)
            
        return extracted_patterns
        
    def learn_domain_mapping(self, source_domain: str, target_domain: str,
                           paired_examples: List[Tuple[np.ndarray, np.ndarray]]) -> TransferMapping:
        """Learn mapping between two domains using paired examples."""
        if source_domain not in self.domains or target_domain not in self.domains:
            raise ValueError("Both domains must be registered")
            
        # Create domain adapter if not exists
        adapter_key = f"{source_domain}_to_{target_domain}"
        if adapter_key not in self.domain_adapters:
            source_dim = len(paired_examples[0][0])
            target_dim = len(paired_examples[0][1])
            self.domain_adapters[adapter_key] = DomainAdapter(source_dim, target_dim)
            
        adapter = self.domain_adapters[adapter_key]
        
        # Train adapter
        self._train_domain_adapter(adapter, paired_examples)
        
        # Extract transformation matrix
        transformation_matrix = self._extract_transformation_matrix(adapter)
        
        # Create transfer mapping
        mapping = TransferMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            pattern_mappings=self._compute_pattern_mappings(source_domain, target_domain),
            transformation_matrix=transformation_matrix,
            confidence_score=self._compute_mapping_confidence(paired_examples, adapter),
            adaptation_strategy="neural_adaptation"
        )
        
        mapping_key = f"{source_domain}_to_{target_domain}"
        self.transfer_mappings[mapping_key] = mapping
        
        return mapping
        
    def transfer_pattern(self, pattern: CreativePattern, target_domain: str,
                        adaptation_strength: float = 1.0) -> Dict[str, Any]:
        """Transfer a pattern to a target domain."""
        if target_domain not in self.domains:
            raise ValueError(f"Target domain {target_domain} not registered")
            
        mapping_key = f"{pattern.source_domain}_to_{target_domain}"
        
        if mapping_key not in self.transfer_mappings:
            # Create basic mapping if none exists
            self._create_basic_mapping(pattern.source_domain, target_domain)
            
        mapping = self.transfer_mappings[mapping_key]
        adapter = self.domain_adapters.get(mapping_key)
        
        # Apply transformation
        if adapter is not None:
            source_tensor = torch.tensor(pattern.abstract_representation, dtype=torch.float32)
            with torch.no_grad():
                latent, target_output, _ = adapter(source_tensor.unsqueeze(0))
                transferred_representation = target_output.squeeze(0).numpy()
        else:
            # Fallback to matrix transformation
            transferred_representation = mapping.transformation_matrix @ pattern.abstract_representation
            
        # Adapt to target domain constraints
        adapted_features = self._adapt_to_domain_constraints(
            pattern.concrete_features,
            self.domains[target_domain],
            adaptation_strength
        )
        
        # Create transferred pattern
        transferred_pattern = CreativePattern(
            pattern_id=f"transferred_{pattern.pattern_id}_to_{target_domain}",
            source_domain=target_domain,
            pattern_type=pattern.pattern_type,
            abstract_representation=transferred_representation,
            concrete_features=adapted_features,
            transferability_score=pattern.transferability_score * mapping.confidence_score,
            success_rate=0.0
        )
        
        # Evaluate transfer quality
        transfer_quality = self._evaluate_transfer_quality(pattern, transferred_pattern, mapping)
        
        # Record transfer
        transfer_record = {
            "original_pattern": pattern,
            "transferred_pattern": transferred_pattern,
            "mapping_used": mapping,
            "transfer_quality": transfer_quality,
            "adaptation_strength": adaptation_strength
        }
        
        self.transfer_history.append(transfer_record)
        
        return transfer_record
        
    def find_cross_domain_analogies(self, source_domain: str, 
                                   target_domain: str) -> List[Dict[str, Any]]:
        """Find analogical relationships between domains."""
        source_patterns = self.pattern_library.get_transferable_patterns(source_domain, target_domain)
        target_patterns = self.pattern_library.domain_patterns.get(target_domain, [])
        target_pattern_objs = [self.pattern_library.patterns[pid] for pid in target_patterns]
        
        analogies = []
        
        for source_pattern in source_patterns:
            for target_pattern in target_pattern_objs:
                analogy_strength = self._compute_analogy_strength(source_pattern, target_pattern)
                
                if analogy_strength > 0.6:
                    analogy = {
                        "source_pattern": source_pattern,
                        "target_pattern": target_pattern,
                        "analogy_strength": analogy_strength,
                        "mapping": self._compute_analogical_mapping(source_pattern, target_pattern),
                        "transferable_elements": self._identify_transferable_elements(
                            source_pattern, target_pattern
                        )
                    }
                    analogies.append(analogy)
                    
        # Sort by analogy strength
        analogies.sort(key=lambda x: x["analogy_strength"], reverse=True)
        return analogies
        
    def generate_creative_variations(self, base_pattern: CreativePattern,
                                   variation_strategies: List[str],
                                   num_variations: int = 5) -> List[CreativePattern]:
        """Generate creative variations of a pattern."""
        variations = []
        
        for strategy in variation_strategies:
            if len(variations) >= num_variations:
                break
                
            strategy_variations = self._apply_variation_strategy(base_pattern, strategy)
            variations.extend(strategy_variations[:num_variations - len(variations)])
            
        return variations
        
    def _train_domain_adapter(self, adapter: DomainAdapter, 
                            paired_examples: List[Tuple[np.ndarray, np.ndarray]]) -> None:
        """Train domain adapter on paired examples."""
        optimizer = torch.optim.Adam(adapter.parameters(), lr=0.001)
        
        for epoch in range(100):  # Quick training
            total_loss = 0
            
            for source_ex, target_ex in paired_examples:
                source_tensor = torch.tensor(source_ex, dtype=torch.float32).unsqueeze(0)
                target_tensor = torch.tensor(target_ex, dtype=torch.float32).unsqueeze(0)
                
                latent, predicted_target, domain_pred = adapter(source_tensor)
                
                # Reconstruction loss
                recon_loss = F.mse_loss(predicted_target, target_tensor)
                
                # Domain confusion loss (for domain invariance)
                domain_loss = F.binary_cross_entropy(domain_pred, torch.ones_like(domain_pred) * 0.5)
                
                loss = recon_loss + 0.1 * domain_loss
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                
            if epoch % 20 == 0:
                print(f"Epoch {epoch}, Loss: {total_loss/len(paired_examples):.4f}")
                
    def _extract_transformation_matrix(self, adapter: DomainAdapter) -> np.ndarray:
        """Extract transformation matrix from trained adapter."""
        # Use the encoder-decoder weights as transformation matrix
        encoder_weight = adapter.source_encoder[0].weight.detach().numpy()
        decoder_weight = adapter.target_decoder[-1].weight.detach().numpy()
        return decoder_weight @ encoder_weight
        
    def _compute_pattern_mappings(self, source_domain: str, target_domain: str) -> Dict[str, str]:
        """Compute pattern mappings between domains."""
        source_domain_obj = self.domains[source_domain]
        target_domain_obj = self.domains[target_domain]
        
        mappings = {}
        
        # Map techniques
        for source_technique in source_domain_obj.techniques:
            best_match = self._find_best_technique_match(source_technique, target_domain_obj.techniques)
            if best_match:
                mappings[f"technique_{source_technique}"] = f"technique_{best_match}"
                
        # Map modalities
        for source_modality in source_domain_obj.modalities:
            if source_modality in target_domain_obj.modalities:
                mappings[f"modality_{source_modality}"] = f"modality_{source_modality}"
                
        return mappings
        
    def _compute_mapping_confidence(self, paired_examples: List[Tuple[np.ndarray, np.ndarray]],
                                  adapter: DomainAdapter) -> float:
        """Compute confidence score for domain mapping."""
        total_error = 0
        
        with torch.no_grad():
            for source_ex, target_ex in paired_examples:
                source_tensor = torch.tensor(source_ex, dtype=torch.float32).unsqueeze(0)
                target_tensor = torch.tensor(target_ex, dtype=torch.float32).unsqueeze(0)
                
                _, predicted_target, _ = adapter(source_tensor)
                error = F.mse_loss(predicted_target, target_tensor).item()
                total_error += error
                
        avg_error = total_error / len(paired_examples)
        confidence = 1.0 / (1.0 + avg_error)  # Convert error to confidence
        return confidence
        
    def _create_basic_mapping(self, source_domain: str, target_domain: str) -> None:
        """Create basic mapping when no trained mapping exists."""
        # Create identity transformation matrix
        transformation_matrix = np.eye(self.embedding_dim)
        
        mapping = TransferMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            pattern_mappings={},
            transformation_matrix=transformation_matrix,
            confidence_score=0.5,
            adaptation_strategy="identity"
        )
        
        mapping_key = f"{source_domain}_to_{target_domain}"
        self.transfer_mappings[mapping_key] = mapping
        
    def _adapt_to_domain_constraints(self, features: Dict[str, Any], 
                                   target_domain: Domain,
                                   adaptation_strength: float) -> Dict[str, Any]:
        """Adapt features to target domain constraints."""
        adapted_features = features.copy()
        
        # Apply domain-specific constraints
        for constraint_name, constraint_value in target_domain.constraints.items():
            if constraint_name in adapted_features:
                original_value = adapted_features[constraint_name]
                
                if isinstance(constraint_value, (int, float)) and isinstance(original_value, (int, float)):
                    # Interpolate towards constraint
                    adapted_value = original_value + adaptation_strength * (constraint_value - original_value)
                    adapted_features[constraint_name] = adapted_value
                    
        return adapted_features
        
    def _evaluate_transfer_quality(self, original: CreativePattern, 
                                 transferred: CreativePattern,
                                 mapping: TransferMapping) -> Dict[str, float]:
        """Evaluate the quality of pattern transfer."""
        # Preservation of abstract structure
        structure_preservation = np.dot(original.abstract_representation,
                                      transferred.abstract_representation) / (
            np.linalg.norm(original.abstract_representation) *
            np.linalg.norm(transferred.abstract_representation)
        )
        
        # Adaptation to target domain
        adaptation_quality = mapping.confidence_score
        
        # Novelty in target domain
        novelty_score = self._compute_novelty_in_domain(transferred)
        
        return {
            "structure_preservation": structure_preservation,
            "adaptation_quality": adaptation_quality,
            "novelty": novelty_score,
            "overall_quality": (structure_preservation + adaptation_quality + novelty_score) / 3
        }
        
    def _compute_analogy_strength(self, pattern1: CreativePattern, 
                                pattern2: CreativePattern) -> float:
        """Compute strength of analogical relationship between patterns."""
        # Structural similarity
        structural_sim = np.dot(pattern1.abstract_representation,
                              pattern2.abstract_representation) / (
            np.linalg.norm(pattern1.abstract_representation) *
            np.linalg.norm(pattern2.abstract_representation)
        )
        
        # Functional similarity (based on pattern type)
        functional_sim = 1.0 if pattern1.pattern_type == pattern2.pattern_type else 0.5
        
        # Cross-domain bonus
        cross_domain_bonus = 0.2 if pattern1.source_domain != pattern2.source_domain else 0.0
        
        return (0.6 * structural_sim + 0.3 * functional_sim + cross_domain_bonus)
        
    def _compute_analogical_mapping(self, pattern1: CreativePattern,
                                  pattern2: CreativePattern) -> Dict[str, str]:
        """Compute analogical mapping between patterns."""
        mapping = {}
        
        # Map similar features
        for key1, val1 in pattern1.concrete_features.items():
            for key2, val2 in pattern2.concrete_features.items():
                if self._are_analogous_features(val1, val2):
                    mapping[f"{pattern1.source_domain}:{key1}"] = f"{pattern2.source_domain}:{key2}"
                    
        return mapping
        
    def _identify_transferable_elements(self, source: CreativePattern,
                                      target: CreativePattern) -> List[str]:
        """Identify elements that can be transferred between patterns."""
        transferable = []
        
        for key, value in source.concrete_features.items():
            if key not in target.concrete_features:
                transferable.append(f"{key}: {value}")
            elif self._is_transferable_feature(value, target.concrete_features[key]):
                transferable.append(f"{key}: {value} -> {target.concrete_features[key]}")
                
        return transferable
        
    def _apply_variation_strategy(self, pattern: CreativePattern, 
                                strategy: str) -> List[CreativePattern]:
        """Apply variation strategy to generate new patterns."""
        variations = []
        
        if strategy == "interpolation":
            # Find similar patterns and interpolate
            similar_patterns = self.pattern_library.find_similar_patterns(pattern, 0.7)
            for similar in similar_patterns[:3]:
                interpolated_repr = 0.7 * pattern.abstract_representation + 0.3 * similar.abstract_representation
                variation = CreativePattern(
                    pattern_id=f"{pattern.pattern_id}_interp_{similar.pattern_id}",
                    source_domain=pattern.source_domain,
                    pattern_type=pattern.pattern_type,
                    abstract_representation=interpolated_repr,
                    concrete_features=pattern.concrete_features.copy(),
                    transferability_score=pattern.transferability_score,
                    success_rate=0.0
                )
                variations.append(variation)
                
        elif strategy == "perturbation":
            # Add noise to create variations
            for i in range(3):
                noise = np.random.normal(0, 0.1, pattern.abstract_representation.shape)
                perturbed_repr = pattern.abstract_representation + noise
                variation = CreativePattern(
                    pattern_id=f"{pattern.pattern_id}_pert_{i}",
                    source_domain=pattern.source_domain,
                    pattern_type=pattern.pattern_type,
                    abstract_representation=perturbed_repr,
                    concrete_features=pattern.concrete_features.copy(),
                    transferability_score=pattern.transferability_score,
                    success_rate=0.0
                )
                variations.append(variation)
                
        return variations
        
    def _decode_pattern_type(self, pattern_type_tensor: torch.Tensor) -> str:
        """Decode pattern type from model output."""
        pattern_types = [
            "rhythm", "structure", "color", "texture", "movement",
            "harmony", "contrast", "balance", "emphasis", "unity"
        ]
        predicted_idx = torch.argmax(pattern_type_tensor).item()
        return pattern_types[predicted_idx]
        
    def _extract_concrete_features(self, example_tensor: torch.Tensor) -> Dict[str, Any]:
        """Extract concrete features from example."""
        features = {}
        
        # Basic statistics
        features["mean"] = torch.mean(example_tensor).item()
        features["std"] = torch.std(example_tensor).item()
        features["max"] = torch.max(example_tensor).item()
        features["min"] = torch.min(example_tensor).item()
        
        # Pattern characteristics
        if len(example_tensor.shape) > 1:
            features["dimensionality"] = len(example_tensor.shape)
            features["size"] = example_tensor.numel()
            
        return features
        
    def _compute_transferability_score(self, latent: torch.Tensor, domain: Domain) -> float:
        """Compute how transferable a pattern is."""
        # Base transferability on pattern abstraction and domain characteristics
        abstraction_level = torch.std(latent).item()  # Higher std = more abstract
        
        # Domain flexibility
        domain_flexibility = len(domain.modalities) / 5.0  # Normalize by max expected modalities
        
        return min(1.0, abstraction_level * domain_flexibility)
        
    def _compute_novelty_in_domain(self, pattern: CreativePattern) -> float:
        """Compute novelty of pattern within its domain."""
        domain_patterns = self.pattern_library.domain_patterns.get(pattern.source_domain, [])
        
        if not domain_patterns:
            return 1.0
            
        similarities = []
        for pattern_id in domain_patterns:
            other_pattern = self.pattern_library.patterns[pattern_id]
            if other_pattern.pattern_id != pattern.pattern_id:
                similarity = np.dot(pattern.abstract_representation,
                                  other_pattern.abstract_representation) / (
                    np.linalg.norm(pattern.abstract_representation) *
                    np.linalg.norm(other_pattern.abstract_representation)
                )
                similarities.append(similarity)
                
        return 1.0 - np.mean(similarities) if similarities else 1.0
        
    def _find_best_technique_match(self, technique: str, target_techniques: List[str]) -> Optional[str]:
        """Find best matching technique in target domain."""
        # Simple string similarity for now
        best_match = None
        best_score = 0
        
        for target_technique in target_techniques:
            # Basic string similarity
            common_chars = len(set(technique.lower()) & set(target_technique.lower()))
            total_chars = len(set(technique.lower()) | set(target_technique.lower()))
            score = common_chars / total_chars if total_chars > 0 else 0
            
            if score > best_score and score > 0.3:
                best_score = score
                best_match = target_technique
                
        return best_match
        
    def _are_analogous_features(self, val1: Any, val2: Any) -> bool:
        """Check if two feature values are analogous."""
        if type(val1) == type(val2):
            if isinstance(val1, str):
                return len(val1) == len(val2)
            elif isinstance(val1, (int, float)):
                return abs(val1 - val2) < 0.1 * max(abs(val1), abs(val2))
        return False
        
    def _is_transferable_feature(self, source_val: Any, target_val: Any) -> bool:
        """Check if a feature can be meaningfully transferred."""
        return self._are_analogous_features(source_val, target_val)
        
    def get_transfer_statistics(self) -> Dict[str, Any]:
        """Get statistics about transfer learning performance."""
        if not self.transfer_history:
            return {"total_transfers": 0}
            
        quality_scores = [record["transfer_quality"]["overall_quality"] 
                         for record in self.transfer_history]
        
        domain_pairs = {}
        for record in self.transfer_history:
            pair = f"{record['original_pattern'].source_domain} -> {record['transferred_pattern'].source_domain}"
            domain_pairs[pair] = domain_pairs.get(pair, 0) + 1
            
        return {
            "total_transfers": len(self.transfer_history),
            "average_quality": np.mean(quality_scores),
            "domain_transfer_counts": domain_pairs,
            "total_patterns": len(self.pattern_library.patterns),
            "total_domains": len(self.domains)
        }