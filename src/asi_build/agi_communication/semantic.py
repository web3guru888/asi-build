"""
Semantic Interoperability Layer
===============================

Enables semantic understanding and translation between different knowledge
representations used by various AGI architectures.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .core import CommunicationMessage, MessageType

logger = logging.getLogger(__name__)


class KnowledgeRepresentation(Enum):
    """Types of knowledge representations."""

    SYMBOLIC_LOGIC = "symbolic_logic"
    NEURAL_EMBEDDINGS = "neural_embeddings"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PROBABILISTIC = "probabilistic"
    HYPERGRAPH = "hypergraph"
    METTA = "metta"  # Hyperon's MeTTa language
    PRIMUS = "primus"
    NATURAL_LANGUAGE = "natural_language"
    CATEGORY_THEORY = "category_theory"
    PROBABILISTIC_LOGIC_NETWORKS = "pln"


class SemanticFormat(Enum):
    """Semantic data formats."""

    RDF = "rdf"
    OWL = "owl"
    JSON_LD = "json_ld"
    METTA = "metta"
    PROLOG = "prolog"
    LAMBDA_CALCULUS = "lambda_calculus"
    VECTOR = "vector"
    GRAPH_JSON = "graph_json"
    CATEGORY_JSON = "category_json"


@dataclass
class SemanticEntity:
    """Represents a semantic entity in any knowledge representation."""

    id: str
    type: str
    representation: KnowledgeRepresentation
    format: SemanticFormat
    content: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
    relations: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.relations is None:
            self.relations = []


@dataclass
class SemanticMapping:
    """Mapping between different semantic representations."""

    source_representation: KnowledgeRepresentation
    target_representation: KnowledgeRepresentation
    mapping_function: str  # Name of the mapping function
    confidence: float
    bidirectional: bool = False
    cost: float = 1.0  # Computational cost of mapping


class SemanticInteroperabilityLayer:
    """
    Semantic Interoperability Layer

    Handles translation and understanding between different knowledge
    representations used by various AGI architectures.
    """

    def __init__(self, protocol):
        self.protocol = protocol
        self.mappings: Dict[
            Tuple[KnowledgeRepresentation, KnowledgeRepresentation], SemanticMapping
        ] = {}
        self.semantic_cache: Dict[str, SemanticEntity] = {}
        self.translation_history: List[Dict[str, Any]] = []

        self._initialize_mappings()

    def _initialize_mappings(self):
        """Initialize semantic mappings between different representations."""
        # Symbolic Logic mappings
        self.mappings[
            (KnowledgeRepresentation.SYMBOLIC_LOGIC, KnowledgeRepresentation.NEURAL_EMBEDDINGS)
        ] = SemanticMapping(
            source_representation=KnowledgeRepresentation.SYMBOLIC_LOGIC,
            target_representation=KnowledgeRepresentation.NEURAL_EMBEDDINGS,
            mapping_function="symbolic_to_neural",
            confidence=0.8,
            bidirectional=True,
            cost=0.5,
        )

        # Knowledge Graph mappings
        self.mappings[(KnowledgeRepresentation.KNOWLEDGE_GRAPH, KnowledgeRepresentation.RDF)] = (
            SemanticMapping(
                source_representation=KnowledgeRepresentation.KNOWLEDGE_GRAPH,
                target_representation=KnowledgeRepresentation.RDF,
                mapping_function="graph_to_rdf",
                confidence=0.95,
                bidirectional=True,
                cost=0.2,
            )
        )

        # Hyperon MeTTa mappings
        self.mappings[(KnowledgeRepresentation.METTA, KnowledgeRepresentation.SYMBOLIC_LOGIC)] = (
            SemanticMapping(
                source_representation=KnowledgeRepresentation.METTA,
                target_representation=KnowledgeRepresentation.SYMBOLIC_LOGIC,
                mapping_function="metta_to_symbolic",
                confidence=0.9,
                bidirectional=True,
                cost=0.3,
            )
        )

        # PLN mappings
        self.mappings[
            (
                KnowledgeRepresentation.PROBABILISTIC_LOGIC_NETWORKS,
                KnowledgeRepresentation.PROBABILISTIC,
            )
        ] = SemanticMapping(
            source_representation=KnowledgeRepresentation.PROBABILISTIC_LOGIC_NETWORKS,
            target_representation=KnowledgeRepresentation.PROBABILISTIC,
            mapping_function="pln_to_probabilistic",
            confidence=0.95,
            bidirectional=True,
            cost=0.4,
        )

        # Natural Language mappings
        for repr_type in [
            KnowledgeRepresentation.SYMBOLIC_LOGIC,
            KnowledgeRepresentation.KNOWLEDGE_GRAPH,
        ]:
            self.mappings[(KnowledgeRepresentation.NATURAL_LANGUAGE, repr_type)] = SemanticMapping(
                source_representation=KnowledgeRepresentation.NATURAL_LANGUAGE,
                target_representation=repr_type,
                mapping_function=f"nl_to_{repr_type.value}",
                confidence=0.7,
                bidirectional=True,
                cost=0.8,
            )

    async def translate(
        self, entity: SemanticEntity, target_representation: KnowledgeRepresentation
    ) -> SemanticEntity:
        """Translate semantic entity to target representation."""
        if entity.representation == target_representation:
            return entity

        # Find direct mapping
        mapping_key = (entity.representation, target_representation)
        if mapping_key in self.mappings:
            mapping = self.mappings[mapping_key]
            translated_entity = await self._apply_mapping(entity, mapping)
            self._record_translation(entity, translated_entity, mapping)
            return translated_entity

        # Find indirect mapping through intermediate representations
        path = self._find_translation_path(entity.representation, target_representation)
        if path:
            current_entity = entity
            for i in range(len(path) - 1):
                mapping_key = (path[i], path[i + 1])
                mapping = self.mappings[mapping_key]
                current_entity = await self._apply_mapping(current_entity, mapping)
                self._record_translation(
                    entity if i == 0 else current_entity, current_entity, mapping
                )
            return current_entity

        raise ValueError(
            f"No translation path from {entity.representation} to {target_representation}"
        )

    def _find_translation_path(
        self, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> Optional[List[KnowledgeRepresentation]]:
        """Find translation path between representations using BFS."""
        from collections import deque

        if source == target:
            return [source]

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            # Check all possible next steps
            for (src, dst), mapping in self.mappings.items():
                next_repr = None
                if src == current and dst not in visited:
                    next_repr = dst
                elif mapping.bidirectional and dst == current and src not in visited:
                    next_repr = src

                if next_repr:
                    new_path = path + [next_repr]
                    if next_repr == target:
                        return new_path

                    queue.append((next_repr, new_path))
                    visited.add(next_repr)

        return None

    async def _apply_mapping(
        self, entity: SemanticEntity, mapping: SemanticMapping
    ) -> SemanticEntity:
        """Apply semantic mapping to translate entity."""
        mapping_function = getattr(self, mapping.mapping_function)
        translated_content = await mapping_function(
            entity.content, entity.representation, mapping.target_representation
        )

        return SemanticEntity(
            id=f"{entity.id}_translated",
            type=entity.type,
            representation=mapping.target_representation,
            format=self._get_default_format(mapping.target_representation),
            content=translated_content,
            confidence=entity.confidence * mapping.confidence,
            metadata={
                **entity.metadata,
                "translation_source": entity.representation.value,
                "translation_confidence": mapping.confidence,
                "original_id": entity.id,
            },
            relations=entity.relations,
        )

    def _get_default_format(self, representation: KnowledgeRepresentation) -> SemanticFormat:
        """Get default format for a knowledge representation."""
        format_mapping = {
            KnowledgeRepresentation.SYMBOLIC_LOGIC: SemanticFormat.PROLOG,
            KnowledgeRepresentation.NEURAL_EMBEDDINGS: SemanticFormat.VECTOR,
            KnowledgeRepresentation.KNOWLEDGE_GRAPH: SemanticFormat.GRAPH_JSON,
            KnowledgeRepresentation.PROBABILISTIC: SemanticFormat.JSON_LD,
            KnowledgeRepresentation.HYPERGRAPH: SemanticFormat.GRAPH_JSON,
            KnowledgeRepresentation.METTA: SemanticFormat.METTA,
            KnowledgeRepresentation.PRIMUS: SemanticFormat.JSON_LD,
            KnowledgeRepresentation.NATURAL_LANGUAGE: SemanticFormat.JSON_LD,
            KnowledgeRepresentation.CATEGORY_THEORY: SemanticFormat.CATEGORY_JSON,
            KnowledgeRepresentation.PROBABILISTIC_LOGIC_NETWORKS: SemanticFormat.JSON_LD,
        }
        return format_mapping.get(representation, SemanticFormat.JSON_LD)

    async def symbolic_to_neural(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> np.ndarray:
        """Convert symbolic logic to neural embeddings."""
        # Simplified implementation - in practice, this would use sophisticated NLP models
        if isinstance(content, str):
            # Convert symbolic expressions to embeddings
            # This is a placeholder - real implementation would use transformers or similar
            import hashlib

            hash_obj = hashlib.md5(content.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            np.random.seed(seed)
            embedding = np.random.normal(0, 1, 768)  # 768-dimensional embedding
            return embedding.tolist()

        return [0.0] * 768

    async def neural_to_symbolic(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> str:
        """Convert neural embeddings to symbolic logic."""
        # Simplified implementation
        if isinstance(content, (list, np.ndarray)):
            # Convert embeddings back to symbolic form
            # This would use neural-symbolic methods in practice
            embedding = np.array(content)
            magnitude = np.linalg.norm(embedding)

            if magnitude > 0.5:
                return f"concept(high_magnitude, {magnitude:.2f})"
            else:
                return f"concept(low_magnitude, {magnitude:.2f})"

        return "unknown_concept"

    async def graph_to_rdf(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> Dict[str, Any]:
        """Convert knowledge graph to RDF format."""
        if isinstance(content, dict) and "nodes" in content and "edges" in content:
            rdf_triples = []

            # Convert nodes
            for node in content["nodes"]:
                rdf_triples.append(
                    {
                        "subject": node["id"],
                        "predicate": "rdf:type",
                        "object": node.get("type", "Entity"),
                    }
                )

                # Add properties
                for prop, value in node.get("properties", {}).items():
                    rdf_triples.append({"subject": node["id"], "predicate": prop, "object": value})

            # Convert edges
            for edge in content["edges"]:
                rdf_triples.append(
                    {
                        "subject": edge["source"],
                        "predicate": edge.get("type", "related_to"),
                        "object": edge["target"],
                    }
                )

            return {
                "@context": {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
                "triples": rdf_triples,
            }

        return {"triples": []}

    async def metta_to_symbolic(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> str:
        """Convert MeTTa expressions to symbolic logic."""
        if isinstance(content, str):
            # Simple MeTTa to Prolog-like conversion
            # Real implementation would parse MeTTa syntax properly
            metta_content = content.strip()

            # Convert basic MeTTa patterns
            if metta_content.startswith("("):
                # S-expression style
                return metta_content.replace("(", "").replace(")", "").replace(" ", ", ")

            return metta_content

        return str(content)

    async def pln_to_probabilistic(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> Dict[str, Any]:
        """Convert PLN to general probabilistic representation."""
        if isinstance(content, dict):
            # Convert PLN truth values to probability distributions
            probabilistic_content = {}

            if "strength" in content and "confidence" in content:
                # PLN truth value
                strength = content["strength"]
                confidence = content["confidence"]

                # Convert to probability with uncertainty
                probabilistic_content = {
                    "probability": strength,
                    "confidence": confidence,
                    "uncertainty": 1.0 - confidence,
                    "distribution_type": "beta",
                    "parameters": {
                        "alpha": strength * confidence * 100,
                        "beta": (1 - strength) * confidence * 100,
                    },
                }
            else:
                # Generic PLN content
                probabilistic_content = content

            return probabilistic_content

        return {"probability": 0.5, "confidence": 0.5}

    async def nl_to_symbolic_logic(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> str:
        """Convert natural language to symbolic logic."""
        if isinstance(content, str):
            # Simplified NL to logic conversion
            # Real implementation would use sophisticated NLP parsing
            text = content.lower().strip()

            # Simple pattern matching
            if "is a" in text or "is an" in text:
                parts = text.split(" is a ")
                if len(parts) == 2:
                    return f"isa({parts[0].strip()}, {parts[1].strip()})"

            if "has" in text:
                parts = text.split(" has ")
                if len(parts) == 2:
                    return f"has({parts[0].strip()}, {parts[1].strip()})"

            # Default predicate
            words = text.split()
            if len(words) >= 2:
                return f"relation({words[0]}, {words[1]})"

            return f"concept({text})"

        return "unknown_concept"

    async def nl_to_knowledge_graph(
        self, content: Any, source: KnowledgeRepresentation, target: KnowledgeRepresentation
    ) -> Dict[str, Any]:
        """Convert natural language to knowledge graph."""
        if isinstance(content, str):
            # Extract entities and relations from text
            # Simplified implementation
            import re

            text = content.strip()

            # Simple entity extraction (capitalized words)
            entities = re.findall(r"\b[A-Z][a-z]+\b", text)

            nodes = []
            edges = []

            for i, entity in enumerate(entities):
                nodes.append(
                    {
                        "id": f"entity_{i}",
                        "label": entity,
                        "type": "Entity",
                        "properties": {"name": entity},
                    }
                )

            # Create edges between consecutive entities
            for i in range(len(entities) - 1):
                edges.append(
                    {
                        "source": f"entity_{i}",
                        "target": f"entity_{i+1}",
                        "type": "related_to",
                        "properties": {"confidence": 0.7},
                    }
                )

            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": {"source": "natural_language", "original_text": text},
            }

        return {"nodes": [], "edges": []}

    def _record_translation(
        self, source_entity: SemanticEntity, target_entity: SemanticEntity, mapping: SemanticMapping
    ):
        """Record translation for analysis and improvement."""
        translation_record = {
            "timestamp": asyncio.get_event_loop().time(),
            "source_representation": source_entity.representation.value,
            "target_representation": target_entity.representation.value,
            "mapping_function": mapping.mapping_function,
            "confidence": mapping.confidence,
            "cost": mapping.cost,
            "source_id": source_entity.id,
            "target_id": target_entity.id,
        }

        self.translation_history.append(translation_record)

    async def handle_translation_request(self, message: CommunicationMessage):
        """Handle semantic translation request from another AGI."""
        payload = message.payload

        try:
            # Parse semantic entity from message
            entity_data = payload["semantic_entity"]
            entity = SemanticEntity(**entity_data)

            # Translate to requested representation
            target_repr = KnowledgeRepresentation(payload["target_representation"])
            translated_entity = await self.translate(entity, target_repr)

            # Send response
            response_message = CommunicationMessage(
                id=f"translation_response_{message.id}",
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.SEMANTIC_TRANSLATION,
                timestamp=asyncio.get_event_loop().time(),
                payload={
                    "original_message_id": message.id,
                    "translated_entity": {
                        "id": translated_entity.id,
                        "type": translated_entity.type,
                        "representation": translated_entity.representation.value,
                        "format": translated_entity.format.value,
                        "content": translated_entity.content,
                        "confidence": translated_entity.confidence,
                        "metadata": translated_entity.metadata,
                    },
                    "translation_success": True,
                },
                session_id=message.session_id,
            )

            await self.protocol.send_message(response_message)

        except Exception as e:
            logger.error(f"Error handling translation request: {e}")

            # Send error response
            error_response = CommunicationMessage(
                id=f"translation_error_{message.id}",
                sender_id=self.protocol.identity.id,
                receiver_id=message.sender_id,
                message_type=MessageType.SEMANTIC_TRANSLATION,
                timestamp=asyncio.get_event_loop().time(),
                payload={
                    "original_message_id": message.id,
                    "translation_success": False,
                    "error": str(e),
                },
                session_id=message.session_id,
            )

            await self.protocol.send_message(error_response)

    def get_supported_representations(self) -> List[KnowledgeRepresentation]:
        """Get list of supported knowledge representations."""
        representations = set()
        for src, dst in self.mappings.keys():
            representations.add(src)
            representations.add(dst)
        return list(representations)

    def get_translation_statistics(self) -> Dict[str, Any]:
        """Get translation statistics."""
        if not self.translation_history:
            return {"total_translations": 0}

        total_translations = len(self.translation_history)
        avg_confidence = (
            sum(record["confidence"] for record in self.translation_history) / total_translations
        )
        avg_cost = sum(record["cost"] for record in self.translation_history) / total_translations

        representation_counts = {}
        for record in self.translation_history:
            src = record["source_representation"]
            dst = record["target_representation"]
            key = f"{src}_to_{dst}"
            representation_counts[key] = representation_counts.get(key, 0) + 1

        return {
            "total_translations": total_translations,
            "average_confidence": avg_confidence,
            "average_cost": avg_cost,
            "representation_pairs": representation_counts,
        }
