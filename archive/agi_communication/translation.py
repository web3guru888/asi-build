"""
Translation Between Different Cognitive Architectures
===================================================

Advanced translation system that enables communication between
AGIs built on different cognitive architectures (neural, symbolic,
hybrid, neuromorphic, etc.).
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)

class CognitiveArchitecture(Enum):
    """Types of cognitive architectures."""
    NEURAL_NETWORK = "neural_network"
    SYMBOLIC_AI = "symbolic_ai"
    HYBRID_NEURO_SYMBOLIC = "hybrid_neuro_symbolic"
    NEUROMORPHIC = "neuromorphic"
    QUANTUM_COGNITIVE = "quantum_cognitive"
    EVOLUTIONARY = "evolutionary"
    BAYESIAN_COGNITIVE = "bayesian_cognitive"
    CONNECTIONIST = "connectionist"
    HYPERON = "hyperon"
    PRIMUS = "primus"
    OPENCOG = "opencog"
    SOAR = "soar"
    ACT_R = "act_r"
    CLARION = "clarion"

class RepresentationType(Enum):
    """Types of knowledge representations in different architectures."""
    NEURAL_ACTIVATION = "neural_activation"
    SYMBOLIC_LOGIC = "symbolic_logic"
    PRODUCTION_RULES = "production_rules"
    SEMANTIC_NETWORKS = "semantic_networks"
    FRAMES = "frames"
    SCRIPTS = "scripts"
    EMBEDDINGS = "embeddings"
    TENSORS = "tensors"
    PROBABILISTIC_GRAPHICAL_MODELS = "probabilistic_graphical_models"
    METTA_EXPRESSIONS = "metta_expressions"
    PRIMUS_ATOMS = "primus_atoms"
    OPENCOG_ATOMS = "opencog_atoms"

class ProcessingParadigm(Enum):
    """Processing paradigms of different architectures."""
    FEEDFORWARD = "feedforward"
    RECURRENT = "recurrent"
    ATTENTION_BASED = "attention_based"
    RULE_BASED = "rule_based"
    CASE_BASED = "case_based"
    MODEL_BASED = "model_based"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    BACKPROPAGATION = "backpropagation"
    HEBBIAN = "hebbian"
    SPIKE_TIMING = "spike_timing"
    QUANTUM_SUPERPOSITION = "quantum_superposition"

@dataclass
class ArchitectureProfile:
    """Profile describing a cognitive architecture."""
    architecture: CognitiveArchitecture
    representation_types: List[RepresentationType]
    processing_paradigms: List[ProcessingParadigm]
    knowledge_formats: List[str]
    reasoning_capabilities: List[str]
    learning_mechanisms: List[str]
    memory_systems: List[str]
    communication_interfaces: List[str]
    computational_characteristics: Dict[str, Any] = field(default_factory=dict)
    
    def supports_representation(self, rep_type: RepresentationType) -> bool:
        """Check if architecture supports a representation type."""
        return rep_type in self.representation_types
    
    def supports_paradigm(self, paradigm: ProcessingParadigm) -> bool:
        """Check if architecture supports a processing paradigm."""
        return paradigm in self.processing_paradigms

@dataclass
class TranslationContext:
    """Context for translation between architectures."""
    source_architecture: CognitiveArchitecture
    target_architecture: CognitiveArchitecture
    source_representation: RepresentationType
    target_representation: RepresentationType
    translation_quality: float = 0.0
    computational_cost: float = 0.0
    semantic_preservation: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CognitiveData:
    """Data structure representing cognitive information."""
    id: str
    architecture: CognitiveArchitecture
    representation: RepresentationType
    content: Any
    semantic_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_hints: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

class ArchitectureRegistry:
    """Registry of cognitive architecture profiles."""
    
    def __init__(self):
        self.profiles: Dict[CognitiveArchitecture, ArchitectureProfile] = {}
        self._initialize_standard_profiles()
    
    def _initialize_standard_profiles(self):
        """Initialize profiles for standard cognitive architectures."""
        
        # Neural Network Architecture
        self.profiles[CognitiveArchitecture.NEURAL_NETWORK] = ArchitectureProfile(
            architecture=CognitiveArchitecture.NEURAL_NETWORK,
            representation_types=[
                RepresentationType.NEURAL_ACTIVATION,
                RepresentationType.EMBEDDINGS,
                RepresentationType.TENSORS
            ],
            processing_paradigms=[
                ProcessingParadigm.FEEDFORWARD,
                ProcessingParadigm.RECURRENT,
                ProcessingParadigm.ATTENTION_BASED,
                ProcessingParadigm.BACKPROPAGATION
            ],
            knowledge_formats=["tensor", "embedding", "weights"],
            reasoning_capabilities=["pattern_recognition", "classification", "regression"],
            learning_mechanisms=["supervised", "unsupervised", "reinforcement"],
            memory_systems=["weight_matrices", "lstm_cells", "attention_memory"],
            communication_interfaces=["vector_space", "neural_codes"]
        )
        
        # Symbolic AI Architecture
        self.profiles[CognitiveArchitecture.SYMBOLIC_AI] = ArchitectureProfile(
            architecture=CognitiveArchitecture.SYMBOLIC_AI,
            representation_types=[
                RepresentationType.SYMBOLIC_LOGIC,
                RepresentationType.PRODUCTION_RULES,
                RepresentationType.SEMANTIC_NETWORKS,
                RepresentationType.FRAMES
            ],
            processing_paradigms=[
                ProcessingParadigm.RULE_BASED,
                ProcessingParadigm.CASE_BASED,
                ProcessingParadigm.MODEL_BASED
            ],
            knowledge_formats=["logic", "rules", "semantic_networks", "ontologies"],
            reasoning_capabilities=["logical_inference", "planning", "theorem_proving"],
            learning_mechanisms=["rule_induction", "concept_learning"],
            memory_systems=["knowledge_base", "working_memory", "long_term_memory"],
            communication_interfaces=["logic_expressions", "semantic_queries"]
        )
        
        # Hyperon Architecture
        self.profiles[CognitiveArchitecture.HYPERON] = ArchitectureProfile(
            architecture=CognitiveArchitecture.HYPERON,
            representation_types=[
                RepresentationType.METTA_EXPRESSIONS,
                RepresentationType.SYMBOLIC_LOGIC,
                RepresentationType.PROBABILISTIC_GRAPHICAL_MODELS
            ],
            processing_paradigms=[
                ProcessingParadigm.RULE_BASED,
                ProcessingParadigm.MODEL_BASED
            ],
            knowledge_formats=["metta", "atomspace", "hypergraphs"],
            reasoning_capabilities=["probabilistic_reasoning", "pattern_matching", "inference"],
            learning_mechanisms=["probabilistic_learning", "pattern_learning"],
            memory_systems=["atomspace", "attention_allocation"],
            communication_interfaces=["metta_expressions", "atom_protocols"]
        )
        
        # PRIMUS Architecture
        self.profiles[CognitiveArchitecture.PRIMUS] = ArchitectureProfile(
            architecture=CognitiveArchitecture.PRIMUS,
            representation_types=[
                RepresentationType.PRIMUS_ATOMS,
                RepresentationType.SYMBOLIC_LOGIC
            ],
            processing_paradigms=[
                ProcessingParadigm.RULE_BASED,
                ProcessingParadigm.MODEL_BASED
            ],
            knowledge_formats=["primus_atoms", "logical_forms"],
            reasoning_capabilities=["formal_reasoning", "proof_construction"],
            learning_mechanisms=["formal_learning", "theorem_proving"],
            memory_systems=["atom_memory", "proof_cache"],
            communication_interfaces=["atomic_messages", "formal_protocols"]
        )
        
        # Hybrid Neuro-Symbolic Architecture
        self.profiles[CognitiveArchitecture.HYBRID_NEURO_SYMBOLIC] = ArchitectureProfile(
            architecture=CognitiveArchitecture.HYBRID_NEURO_SYMBOLIC,
            representation_types=[
                RepresentationType.NEURAL_ACTIVATION,
                RepresentationType.SYMBOLIC_LOGIC,
                RepresentationType.EMBEDDINGS,
                RepresentationType.SEMANTIC_NETWORKS
            ],
            processing_paradigms=[
                ProcessingParadigm.FEEDFORWARD,
                ProcessingParadigm.RULE_BASED,
                ProcessingParadigm.ATTENTION_BASED,
                ProcessingParadigm.BACKPROPAGATION
            ],
            knowledge_formats=["hybrid_representations", "neural_symbolic_binding"],
            reasoning_capabilities=["hybrid_reasoning", "neural_symbolic_integration"],
            learning_mechanisms=["end_to_end_learning", "symbolic_grounding"],
            memory_systems=["hybrid_memory", "neural_symbolic_memory"],
            communication_interfaces=["hybrid_protocols", "multi_modal_interfaces"]
        )
    
    def get_profile(self, architecture: CognitiveArchitecture) -> Optional[ArchitectureProfile]:
        """Get architecture profile."""
        return self.profiles.get(architecture)
    
    def register_profile(self, profile: ArchitectureProfile):
        """Register a new architecture profile."""
        self.profiles[profile.architecture] = profile

class TranslationEngine:
    """Engine for translating between cognitive architectures."""
    
    def __init__(self):
        self.translators: Dict[Tuple[RepresentationType, RepresentationType], Callable] = {}
        self.architecture_adapters: Dict[Tuple[CognitiveArchitecture, CognitiveArchitecture], Callable] = {}
        self._initialize_translators()
    
    def _initialize_translators(self):
        """Initialize translation functions between representation types."""
        
        # Neural to Symbolic translations
        self.translators[(RepresentationType.NEURAL_ACTIVATION, RepresentationType.SYMBOLIC_LOGIC)] = \
            self._neural_to_symbolic
        self.translators[(RepresentationType.EMBEDDINGS, RepresentationType.SYMBOLIC_LOGIC)] = \
            self._embedding_to_symbolic
        
        # Symbolic to Neural translations
        self.translators[(RepresentationType.SYMBOLIC_LOGIC, RepresentationType.NEURAL_ACTIVATION)] = \
            self._symbolic_to_neural
        self.translators[(RepresentationType.SYMBOLIC_LOGIC, RepresentationType.EMBEDDINGS)] = \
            self._symbolic_to_embedding
        
        # Hyperon specific translations
        self.translators[(RepresentationType.METTA_EXPRESSIONS, RepresentationType.SYMBOLIC_LOGIC)] = \
            self._metta_to_symbolic
        self.translators[(RepresentationType.SYMBOLIC_LOGIC, RepresentationType.METTA_EXPRESSIONS)] = \
            self._symbolic_to_metta
        
        # PRIMUS specific translations
        self.translators[(RepresentationType.PRIMUS_ATOMS, RepresentationType.SYMBOLIC_LOGIC)] = \
            self._primus_to_symbolic
        self.translators[(RepresentationType.SYMBOLIC_LOGIC, RepresentationType.PRIMUS_ATOMS)] = \
            self._symbolic_to_primus
        
        # Cross-architecture translations
        self.translators[(RepresentationType.METTA_EXPRESSIONS, RepresentationType.EMBEDDINGS)] = \
            self._metta_to_embedding
        self.translators[(RepresentationType.EMBEDDINGS, RepresentationType.METTA_EXPRESSIONS)] = \
            self._embedding_to_metta
    
    def can_translate(self, source_rep: RepresentationType, target_rep: RepresentationType) -> bool:
        """Check if translation is possible between representation types."""
        return (source_rep, target_rep) in self.translators
    
    def translate_representation(self, data: Any, source_rep: RepresentationType,
                               target_rep: RepresentationType) -> Tuple[Any, TranslationContext]:
        """Translate data between representation types."""
        if not self.can_translate(source_rep, target_rep):
            raise ValueError(f"Cannot translate from {source_rep.value} to {target_rep.value}")
        
        translator = self.translators[(source_rep, target_rep)]
        translated_data, quality, cost, semantic_preservation = translator(data)
        
        context = TranslationContext(
            source_architecture=CognitiveArchitecture.NEURAL_NETWORK,  # Default, should be specified
            target_architecture=CognitiveArchitecture.SYMBOLIC_AI,      # Default, should be specified
            source_representation=source_rep,
            target_representation=target_rep,
            translation_quality=quality,
            computational_cost=cost,
            semantic_preservation=semantic_preservation
        )
        
        return translated_data, context
    
    # Translation functions
    def _neural_to_symbolic(self, neural_data: Any) -> Tuple[Any, float, float, float]:
        """Convert neural activations to symbolic logic."""
        if isinstance(neural_data, (list, np.ndarray)):
            activations = np.array(neural_data)
            
            # Find high-activation nodes
            threshold = np.mean(activations) + np.std(activations)
            active_nodes = np.where(activations > threshold)[0]
            
            # Generate symbolic predicates
            predicates = []
            for node_idx in active_nodes:
                activation_level = activations[node_idx]
                if activation_level > 0.8:
                    predicates.append(f"high_activation(node_{node_idx})")
                elif activation_level > 0.5:
                    predicates.append(f"medium_activation(node_{node_idx})")
                else:
                    predicates.append(f"low_activation(node_{node_idx})")
            
            symbolic_expression = " & ".join(predicates) if predicates else "inactive_network"
            return symbolic_expression, 0.7, 0.3, 0.6
        
        return str(neural_data), 0.5, 0.2, 0.5
    
    def _embedding_to_symbolic(self, embedding_data: Any) -> Tuple[Any, float, float, float]:
        """Convert embeddings to symbolic representation."""
        if isinstance(embedding_data, (list, np.ndarray)):
            embedding = np.array(embedding_data)
            
            # Analyze embedding characteristics
            magnitude = np.linalg.norm(embedding)
            positive_dims = np.sum(embedding > 0)
            negative_dims = np.sum(embedding < 0)
            max_dim = np.argmax(np.abs(embedding))
            
            # Generate symbolic description
            predicates = []
            predicates.append(f"magnitude({magnitude:.2f})")
            predicates.append(f"positive_dimensions({positive_dims})")
            predicates.append(f"negative_dimensions({negative_dims})")
            predicates.append(f"dominant_dimension({max_dim})")
            
            if magnitude > 1.0:
                predicates.append("high_magnitude_concept")
            elif magnitude > 0.5:
                predicates.append("medium_magnitude_concept")
            else:
                predicates.append("low_magnitude_concept")
            
            symbolic_expression = " & ".join(predicates)
            return symbolic_expression, 0.6, 0.4, 0.5
        
        return str(embedding_data), 0.4, 0.2, 0.4
    
    def _symbolic_to_neural(self, symbolic_data: str) -> Tuple[Any, float, float, float]:
        """Convert symbolic logic to neural activations."""
        # Simple symbolic to neural conversion
        # In practice, this would use sophisticated neural-symbolic methods
        
        # Parse predicates
        predicates = symbolic_data.split(" & ")
        
        # Create activation pattern based on predicates
        activations = np.zeros(128)  # 128-dimensional activation
        
        for i, predicate in enumerate(predicates[:128]):
            # Hash predicate to activation value
            hash_val = hash(predicate) % 1000000
            activation = (hash_val / 1000000.0) * 2 - 1  # Scale to [-1, 1]
            activations[i] = activation
        
        return activations.tolist(), 0.6, 0.5, 0.5
    
    def _symbolic_to_embedding(self, symbolic_data: str) -> Tuple[Any, float, float, float]:
        """Convert symbolic logic to embedding representation."""
        # Simple symbolic to embedding conversion
        words = symbolic_data.replace("(", " ").replace(")", " ").replace(",", " ").split()
        
        # Create embedding by averaging word hashes
        embedding_dim = 384
        embedding = np.zeros(embedding_dim)
        
        for word in words:
            if word:
                word_hash = hash(word)
                for i in range(embedding_dim):
                    hash_component = hash(f"{word}_{i}") % 2000 - 1000
                    embedding[i] += hash_component / 1000.0
        
        if len(words) > 0:
            embedding /= len(words)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        
        return embedding.tolist(), 0.65, 0.4, 0.6
    
    def _metta_to_symbolic(self, metta_data: str) -> Tuple[Any, float, float, float]:
        """Convert MeTTa expressions to symbolic logic."""
        # Convert MeTTa S-expressions to standard logic
        metta_expr = metta_data.strip()
        
        # Simple conversion rules
        if metta_expr.startswith("("):
            # S-expression format
            content = metta_expr[1:-1] if metta_expr.endswith(")") else metta_expr[1:]
            parts = content.split()
            
            if len(parts) >= 2:
                operator = parts[0]
                args = parts[1:]
                
                if operator == "and":
                    symbolic_expr = " & ".join(args)
                elif operator == "or":
                    symbolic_expr = " | ".join(args)
                elif operator == "not":
                    symbolic_expr = f"~{args[0]}" if args else "~unknown"
                elif operator == "implies":
                    symbolic_expr = f"{args[0]} -> {args[1]}" if len(args) >= 2 else content
                else:
                    symbolic_expr = f"{operator}({', '.join(args)})"
            else:
                symbolic_expr = content
        else:
            symbolic_expr = metta_expr
        
        return symbolic_expr, 0.85, 0.2, 0.9
    
    def _symbolic_to_metta(self, symbolic_data: str) -> Tuple[Any, float, float, float]:
        """Convert symbolic logic to MeTTa expressions."""
        # Convert standard logic to MeTTa S-expressions
        logic_expr = symbolic_data.strip()
        
        # Simple conversion rules
        logic_expr = logic_expr.replace(" & ", " and ")
        logic_expr = logic_expr.replace(" | ", " or ")
        logic_expr = logic_expr.replace("~", "not ")
        logic_expr = logic_expr.replace(" -> ", " implies ")
        
        # Wrap in S-expression if needed
        if not logic_expr.startswith("("):
            logic_expr = f"({logic_expr})"
        
        return logic_expr, 0.8, 0.25, 0.85
    
    def _primus_to_symbolic(self, primus_data: Any) -> Tuple[Any, float, float, float]:
        """Convert PRIMUS atoms to symbolic logic."""
        if isinstance(primus_data, dict):
            # Assume PRIMUS atom structure
            atom_type = primus_data.get("type", "unknown")
            atom_content = primus_data.get("content", "")
            
            if atom_type == "predicate":
                symbolic_expr = atom_content
            elif atom_type == "relation":
                args = primus_data.get("args", [])
                relation_name = primus_data.get("name", "relation")
                symbolic_expr = f"{relation_name}({', '.join(map(str, args))})"
            else:
                symbolic_expr = str(atom_content)
            
            return symbolic_expr, 0.9, 0.15, 0.95
        
        return str(primus_data), 0.7, 0.2, 0.8
    
    def _symbolic_to_primus(self, symbolic_data: str) -> Tuple[Any, float, float, float]:
        """Convert symbolic logic to PRIMUS atoms."""
        # Parse symbolic expression into PRIMUS atom structure
        import re
        
        # Look for predicate patterns
        predicate_match = re.match(r'(\w+)\((.*)\)', symbolic_data)
        if predicate_match:
            predicate_name = predicate_match.group(1)
            args_str = predicate_match.group(2)
            args = [arg.strip() for arg in args_str.split(',') if arg.strip()]
            
            primus_atom = {
                "type": "predicate",
                "name": predicate_name,
                "args": args,
                "content": symbolic_data
            }
        else:
            # Simple atom
            primus_atom = {
                "type": "simple",
                "content": symbolic_data,
                "value": symbolic_data
            }
        
        return primus_atom, 0.85, 0.2, 0.9
    
    def _metta_to_embedding(self, metta_data: str) -> Tuple[Any, float, float, float]:
        """Convert MeTTa expressions to embeddings."""
        # First convert to symbolic, then to embedding
        symbolic_data, _, _, _ = self._metta_to_symbolic(metta_data)
        embedding, _, _, _ = self._symbolic_to_embedding(symbolic_data)
        
        return embedding, 0.7, 0.6, 0.6
    
    def _embedding_to_metta(self, embedding_data: Any) -> Tuple[Any, float, float, float]:
        """Convert embeddings to MeTTa expressions."""
        # First convert to symbolic, then to MeTTa
        symbolic_data, _, _, _ = self._embedding_to_symbolic(embedding_data)
        metta_data, _, _, _ = self._symbolic_to_metta(symbolic_data)
        
        return metta_data, 0.6, 0.7, 0.55

class CognitiveArchitectureTranslator:
    """
    Translation Between Different Cognitive Architectures
    
    Enables communication between AGIs built on different cognitive
    architectures by translating between their knowledge representations
    and processing paradigms.
    """
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.registry = ArchitectureRegistry()
        self.translation_engine = TranslationEngine()
        self.translation_cache: Dict[str, Tuple[Any, TranslationContext]] = {}
        self.translation_history: List[Dict[str, Any]] = []
        
        # Register own architecture
        self._register_own_architecture()
    
    def _register_own_architecture(self):
        """Register this AGI's cognitive architecture."""
        # Default to hybrid neuro-symbolic for Kenny AGI
        own_architecture = CognitiveArchitecture.HYBRID_NEURO_SYMBOLIC
        
        # Update protocol identity with architecture info
        self.protocol.identity.architecture = own_architecture.value
    
    async def translate_cognitive_data(self, data: CognitiveData, 
                                     target_architecture: CognitiveArchitecture) -> CognitiveData:
        """Translate cognitive data to target architecture format."""
        # Get architecture profiles
        source_profile = self.registry.get_profile(data.architecture)
        target_profile = self.registry.get_profile(target_architecture)
        
        if not source_profile or not target_profile:
            raise ValueError("Unknown architecture in translation request")
        
        # Find compatible representation types
        compatible_target_reps = self._find_compatible_representations(
            data.representation, target_profile.representation_types
        )
        
        if not compatible_target_reps:
            raise ValueError("No compatible representations found for translation")
        
        # Use the first compatible representation
        target_representation = compatible_target_reps[0]
        
        # Check cache first
        cache_key = f"{data.id}_{data.representation.value}_{target_representation.value}"
        if cache_key in self.translation_cache:
            cached_data, cached_context = self.translation_cache[cache_key]
            return CognitiveData(
                id=f"{data.id}_translated",
                architecture=target_architecture,
                representation=target_representation,
                content=cached_data,
                semantic_metadata=data.semantic_metadata,
                processing_hints=data.processing_hints,
                confidence=data.confidence * cached_context.semantic_preservation
            )
        
        # Perform translation
        translated_content, translation_context = self.translation_engine.translate_representation(
            data.content, data.representation, target_representation
        )
        
        # Update translation context
        translation_context.source_architecture = data.architecture
        translation_context.target_architecture = target_architecture
        
        # Cache result
        self.translation_cache[cache_key] = (translated_content, translation_context)
        
        # Create translated cognitive data
        translated_data = CognitiveData(
            id=f"{data.id}_translated",
            architecture=target_architecture,
            representation=target_representation,
            content=translated_content,
            semantic_metadata=data.semantic_metadata.copy(),
            processing_hints=data.processing_hints.copy(),
            confidence=data.confidence * translation_context.semantic_preservation
        )
        
        # Add translation metadata
        translated_data.processing_hints.update({
            'translation_quality': translation_context.translation_quality,
            'computational_cost': translation_context.computational_cost,
            'semantic_preservation': translation_context.semantic_preservation,
            'original_architecture': data.architecture.value,
            'original_representation': data.representation.value
        })
        
        # Record translation
        self._record_translation(data, translated_data, translation_context)
        
        return translated_data
    
    def _find_compatible_representations(self, source_rep: RepresentationType, 
                                       target_reps: List[RepresentationType]) -> List[RepresentationType]:
        """Find compatible representation types for translation."""
        compatible = []
        
        for target_rep in target_reps:
            if self.translation_engine.can_translate(source_rep, target_rep):
                compatible.append(target_rep)
        
        # Sort by preference (exact matches first, then close matches)
        def representation_distance(rep: RepresentationType) -> int:
            if rep == source_rep:
                return 0
            elif "symbolic" in rep.value and "symbolic" in source_rep.value:
                return 1
            elif "neural" in rep.value and "neural" in source_rep.value:
                return 1
            else:
                return 2
        
        compatible.sort(key=representation_distance)
        return compatible
    
    async def negotiate_communication_format(self, target_agi_id: str) -> Dict[str, Any]:
        """Negotiate optimal communication format with target AGI."""
        # Get target AGI info
        target_agi = self.protocol.known_agis.get(target_agi_id)
        if not target_agi:
            raise ValueError(f"Unknown AGI: {target_agi_id}")
        
        target_architecture = CognitiveArchitecture(target_agi.architecture)
        own_architecture = CognitiveArchitecture(self.protocol.identity.architecture)
        
        # Get architecture profiles
        own_profile = self.registry.get_profile(own_architecture)
        target_profile = self.registry.get_profile(target_architecture)
        
        if not own_profile or not target_profile:
            return {"format": "json", "confidence": 0.5}  # Fallback
        
        # Find best mutual format
        own_interfaces = set(own_profile.communication_interfaces)
        target_interfaces = set(target_profile.communication_interfaces)
        common_interfaces = own_interfaces.intersection(target_interfaces)
        
        if common_interfaces:
            best_interface = list(common_interfaces)[0]  # Use first common interface
            confidence = 0.9
        else:
            # Find translatable formats
            own_reps = set(own_profile.representation_types)
            target_reps = set(target_profile.representation_types)
            
            translatable_pairs = []
            for own_rep in own_reps:
                for target_rep in target_reps:
                    if self.translation_engine.can_translate(own_rep, target_rep):
                        translatable_pairs.append((own_rep, target_rep))
            
            if translatable_pairs:
                best_pair = translatable_pairs[0]
                best_interface = f"translate_{best_pair[0].value}_to_{best_pair[1].value}"
                confidence = 0.7
            else:
                best_interface = "universal_json"
                confidence = 0.5
        
        return {
            "format": best_interface,
            "confidence": confidence,
            "source_architecture": own_architecture.value,
            "target_architecture": target_architecture.value
        }
    
    def _record_translation(self, source_data: CognitiveData, translated_data: CognitiveData,
                          translation_context: TranslationContext):
        """Record translation operation for analysis."""
        translation_record = {
            'timestamp': datetime.now().isoformat(),
            'source_id': source_data.id,
            'translated_id': translated_data.id,
            'source_architecture': translation_context.source_architecture.value,
            'target_architecture': translation_context.target_architecture.value,
            'source_representation': translation_context.source_representation.value,
            'target_representation': translation_context.target_representation.value,
            'quality': translation_context.translation_quality,
            'cost': translation_context.computational_cost,
            'semantic_preservation': translation_context.semantic_preservation,
            'confidence_change': translated_data.confidence - source_data.confidence
        }
        
        self.translation_history.append(translation_record)
        
        # Keep history limited
        if len(self.translation_history) > 1000:
            self.translation_history = self.translation_history[-800:]
    
    async def handle_translation_request(self, message: CommunicationMessage):
        """Handle translation request from another AGI."""
        payload = message.payload
        
        try:
            # Parse cognitive data
            data_info = payload['cognitive_data']
            cognitive_data = CognitiveData(
                id=data_info['id'],
                architecture=CognitiveArchitecture(data_info['architecture']),
                representation=RepresentationType(data_info['representation']),
                content=data_info['content'],
                semantic_metadata=data_info.get('semantic_metadata', {}),
                processing_hints=data_info.get('processing_hints', {}),
                confidence=data_info.get('confidence', 1.0)
            )
            
            target_architecture = CognitiveArchitecture(payload['target_architecture'])
            
            # Perform translation
            translated_data = await self.translate_cognitive_data(cognitive_data, target_architecture)
            
            # Send response
            response_message = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.SEMANTIC_TRANSLATION,
                timestamp=datetime.now(),
                payload={
                    'action': 'translation_response',
                    'original_message_id': message.id,
                    'translated_data': {
                        'id': translated_data.id,
                        'architecture': translated_data.architecture.value,
                        'representation': translated_data.representation.value,
                        'content': translated_data.content,
                        'semantic_metadata': translated_data.semantic_metadata,
                        'processing_hints': translated_data.processing_hints,
                        'confidence': translated_data.confidence
                    },
                    'translation_success': True
                }
            )
            
            await self.protocol.send_message(response_message)
            
        except Exception as e:
            logger.error(f"Error handling translation request: {e}")
            
            # Send error response
            error_response = CommunicationMessage(
                id=str(uuid.uuid4()),
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.SEMANTIC_TRANSLATION,
                timestamp=datetime.now(),
                payload={
                    'action': 'translation_error',
                    'original_message_id': message.id,
                    'error': str(e),
                    'translation_success': False
                }
            )
            
            await self.protocol.send_message(error_response)
    
    def get_supported_architectures(self) -> List[str]:
        """Get list of supported cognitive architectures."""
        return [arch.value for arch in self.registry.profiles.keys()]
    
    def get_supported_representations(self) -> List[str]:
        """Get list of supported representation types."""
        all_reps = set()
        for profile in self.registry.profiles.values():
            all_reps.update(rep.value for rep in profile.representation_types)
        return list(all_reps)
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """Get translation statistics."""
        if not self.translation_history:
            return {'total_translations': 0}
        
        total_translations = len(self.translation_history)
        avg_quality = sum(record['quality'] for record in self.translation_history) / total_translations
        avg_cost = sum(record['cost'] for record in self.translation_history) / total_translations
        avg_semantic_preservation = sum(record['semantic_preservation'] for record in self.translation_history) / total_translations
        
        architecture_pairs = {}
        for record in self.translation_history:
            pair = f"{record['source_architecture']}_to_{record['target_architecture']}"
            architecture_pairs[pair] = architecture_pairs.get(pair, 0) + 1
        
        return {
            'total_translations': total_translations,
            'average_quality': avg_quality,
            'average_cost': avg_cost,
            'average_semantic_preservation': avg_semantic_preservation,
            'architecture_pairs': architecture_pairs,
            'cache_size': len(self.translation_cache),
            'supported_architectures': len(self.registry.profiles)
        }