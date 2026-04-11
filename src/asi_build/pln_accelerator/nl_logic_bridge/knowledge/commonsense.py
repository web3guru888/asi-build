"""
Commonsense reasoning integration with ConceptNet and Cyc.

This module provides commonsense reasoning capabilities by integrating with
external knowledge bases like ConceptNet and OpenCyc, enhancing the NL-Logic
bridge with world knowledge.
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
import networkx as nx
import numpy as np

from .conceptnet_integration import ConceptNetIntegration
from .cyc_integration import CycIntegration


class ReasoningType(Enum):
    """Types of commonsense reasoning."""

    CAUSAL = "causal"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    SOCIAL = "social"
    PHYSICAL = "physical"
    CONCEPTUAL = "conceptual"
    EMOTIONAL = "emotional"


@dataclass
class CommonsenseKnowledge:
    """Represents commonsense knowledge."""

    subject: str
    relation: str
    object: str
    confidence: float
    source: str  # "conceptnet", "cyc", "inference"
    reasoning_type: ReasoningType
    context: Dict[str, Any]
    supporting_evidence: List[str] = None


@dataclass
class ReasoningChain:
    """Represents a chain of commonsense reasoning."""

    premise: str
    conclusion: str
    steps: List[CommonsenseKnowledge]
    confidence: float
    reasoning_type: ReasoningType


class CommonsenseReasoner:
    """
    Commonsense reasoning system integrating ConceptNet and Cyc.

    This class provides advanced commonsense reasoning capabilities to enhance
    natural language understanding and logical inference.
    """

    def __init__(self):
        """Initialize the commonsense reasoner."""
        self.logger = logging.getLogger(__name__)

        # Initialize knowledge base integrations
        self.conceptnet = ConceptNetIntegration()
        self.cyc = CycIntegration()

        # Local knowledge cache
        self.knowledge_cache = {}
        self.reasoning_cache = {}

        # Reasoning statistics
        self.stats = {
            "queries_processed": 0,
            "cache_hits": 0,
            "reasoning_chains_generated": 0,
            "average_confidence": 0.0,
        }

        # Initialize reasoning patterns
        self._init_reasoning_patterns()

    def _init_reasoning_patterns(self):
        """Initialize common reasoning patterns."""
        self.reasoning_patterns = {
            ReasoningType.CAUSAL: [
                "if {A} then typically {B}",
                "{A} often leads to {B}",
                "{A} can cause {B}",
                "when {A} happens, {B} may occur",
            ],
            ReasoningType.TEMPORAL: [
                "{A} usually happens before {B}",
                "{A} follows {B} in sequence",
                "after {A}, {B} typically occurs",
            ],
            ReasoningType.SPATIAL: [
                "{A} is typically located in {B}",
                "{A} can be found near {B}",
                "{A} is part of {B}",
            ],
            ReasoningType.SOCIAL: [
                "people who {A} often {B}",
                "{A} is socially associated with {B}",
                "in society, {A} relates to {B}",
            ],
            ReasoningType.PHYSICAL: [
                "{A} has the property of being {B}",
                "{A} physically resembles {B}",
                "{A} shares physical characteristics with {B}",
            ],
            ReasoningType.CONCEPTUAL: [
                "{A} is a type of {B}",
                "{A} belongs to the category {B}",
                "{A} can be classified as {B}",
            ],
        }

    async def enhance_context(
        self, text: str, semantic_parse: Dict[str, Any], existing_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance context with commonsense knowledge.

        Args:
            text: Original text
            semantic_parse: Parsed semantic structure
            existing_context: Current context

        Returns:
            Enhanced context with commonsense knowledge
        """
        try:
            enhanced_context = existing_context.copy()

            # Extract key concepts from text
            concepts = await self._extract_concepts(text, semantic_parse)

            # Gather commonsense knowledge for each concept
            commonsense_knowledge = []
            for concept in concepts:
                knowledge = await self._get_concept_knowledge(concept)
                commonsense_knowledge.extend(knowledge)

            # Find relationships between concepts
            relationships = await self._find_concept_relationships(concepts)

            # Perform commonsense inference
            inferences = await self._perform_commonsense_inference(
                concepts, commonsense_knowledge, relationships
            )

            # Add to context
            enhanced_context.update(
                {
                    "commonsense_concepts": concepts,
                    "commonsense_knowledge": [k.__dict__ for k in commonsense_knowledge],
                    "concept_relationships": relationships,
                    "commonsense_inferences": [i.__dict__ for i in inferences],
                    "reasoning_confidence": self._calculate_reasoning_confidence(inferences),
                }
            )

            self.stats["queries_processed"] += 1

            self.logger.info(
                f"Enhanced context with {len(commonsense_knowledge)} pieces of commonsense knowledge"
            )
            return enhanced_context

        except Exception as e:
            self.logger.error(f"Error enhancing context: {str(e)}")
            return existing_context

    async def resolve_ambiguity(self, ambiguity: str, context: Dict[str, Any]) -> str:
        """
        Resolve ambiguity using commonsense reasoning.

        Args:
            ambiguity: Description of the ambiguity
            context: Context information

        Returns:
            Resolved interpretation
        """
        try:
            # Check cache first
            cache_key = f"ambiguity_{hash(ambiguity + str(context))}"
            if cache_key in self.reasoning_cache:
                self.stats["cache_hits"] += 1
                return self.reasoning_cache[cache_key]

            # Extract potential interpretations
            interpretations = await self._extract_interpretations(ambiguity, context)

            # Score each interpretation using commonsense knowledge
            scored_interpretations = []
            for interpretation in interpretations:
                score = await self._score_interpretation(interpretation, context)
                scored_interpretations.append((interpretation, score))

            # Select best interpretation
            if scored_interpretations:
                best_interpretation = max(scored_interpretations, key=lambda x: x[1])
                resolution = best_interpretation[0]
            else:
                resolution = f"Ambiguity unresolved: {ambiguity}"

            # Cache the result
            self.reasoning_cache[cache_key] = resolution

            return resolution

        except Exception as e:
            self.logger.error(f"Error resolving ambiguity: {str(e)}")
            return f"Unable to resolve: {ambiguity}"

    async def generate_commonsense_inferences(
        self, premise: str, context: Optional[Dict[str, Any]] = None
    ) -> List[ReasoningChain]:
        """
        Generate commonsense inferences from a premise.

        Args:
            premise: Starting premise
            context: Additional context

        Returns:
            List of reasoning chains
        """
        try:
            reasoning_chains = []

            # Extract concepts from premise
            concepts = await self._extract_concepts_from_text(premise)

            # For each concept, find related knowledge
            for concept in concepts:
                # Get direct knowledge
                knowledge = await self._get_concept_knowledge(concept)

                # Generate reasoning chains for different types
                for reasoning_type in ReasoningType:
                    chain = await self._build_reasoning_chain(
                        concept, knowledge, reasoning_type, context
                    )
                    if chain and chain.confidence > 0.3:
                        reasoning_chains.append(chain)

            # Cross-concept reasoning
            cross_chains = await self._generate_cross_concept_reasoning(concepts, context)
            reasoning_chains.extend(cross_chains)

            # Sort by confidence
            reasoning_chains.sort(key=lambda x: x.confidence, reverse=True)

            # Update statistics
            self.stats["reasoning_chains_generated"] += len(reasoning_chains)

            return reasoning_chains[:10]  # Return top 10

        except Exception as e:
            self.logger.error(f"Error generating inferences: {str(e)}")
            return []

    async def explain_reasoning(
        self, premise: str, conclusion: str, context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Explain how commonsense reasoning connects premise to conclusion.

        Args:
            premise: Starting premise
            conclusion: Target conclusion
            context: Additional context

        Returns:
            List of reasoning explanations
        """
        try:
            explanations = []

            # Find reasoning paths from premise to conclusion
            paths = await self._find_reasoning_paths(premise, conclusion, context)

            for path in paths:
                explanation = self._format_reasoning_path(path)
                explanations.append(explanation)

            # If no direct paths found, provide general explanations
            if not explanations:
                general_explanation = await self._generate_general_explanation(
                    premise, conclusion, context
                )
                explanations.append(general_explanation)

            return explanations

        except Exception as e:
            self.logger.error(f"Error explaining reasoning: {str(e)}")
            return [f"Unable to explain reasoning from '{premise}' to '{conclusion}'"]

    async def _extract_concepts(self, text: str, semantic_parse: Dict[str, Any]) -> List[str]:
        """Extract key concepts from text."""
        concepts = set()

        # From semantic parse
        if "entities" in semantic_parse:
            concepts.update(semantic_parse["entities"])

        if "keywords" in semantic_parse:
            concepts.update(semantic_parse["keywords"])

        # From text using simple extraction
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Filter out common words and keep nouns/verbs
        common_words = {"the", "and", "but", "for", "are", "with", "his", "her", "this", "that"}
        meaningful_words = [w for w in words if w not in common_words and len(w) > 3]

        concepts.update(meaningful_words[:10])  # Limit to top 10

        return list(concepts)

    async def _extract_concepts_from_text(self, text: str) -> List[str]:
        """Simple concept extraction from text."""
        # Remove punctuation and split
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Filter common words
        stop_words = {
            "the",
            "and",
            "but",
            "for",
            "are",
            "with",
            "his",
            "her",
            "this",
            "that",
            "was",
            "were",
            "been",
            "have",
            "has",
            "had",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "must",
            "shall",
            "not",
            "very",
            "more",
        }

        concepts = [w for w in words if w not in stop_words and len(w) > 3]
        return list(set(concepts))[:8]  # Return unique concepts, limit to 8

    async def _get_concept_knowledge(self, concept: str) -> List[CommonsenseKnowledge]:
        """Get commonsense knowledge about a concept."""
        knowledge = []

        # Check cache
        cache_key = f"concept_{concept}"
        if cache_key in self.knowledge_cache:
            return self.knowledge_cache[cache_key]

        try:
            # Get from ConceptNet
            conceptnet_knowledge = await self.conceptnet.get_concept_relations(concept)
            for rel in conceptnet_knowledge:
                knowledge.append(
                    CommonsenseKnowledge(
                        subject=rel.get("subject", concept),
                        relation=rel.get("relation", "related_to"),
                        object=rel.get("object", ""),
                        confidence=rel.get("weight", 0.5),
                        source="conceptnet",
                        reasoning_type=self._map_relation_to_reasoning_type(
                            rel.get("relation", "")
                        ),
                        context=rel,
                    )
                )

            # Get from Cyc (if available)
            try:
                cyc_knowledge = await self.cyc.get_concept_assertions(concept)
                for assertion in cyc_knowledge:
                    knowledge.append(
                        CommonsenseKnowledge(
                            subject=assertion.get("subject", concept),
                            relation=assertion.get("predicate", "related_to"),
                            object=assertion.get("object", ""),
                            confidence=assertion.get("confidence", 0.7),
                            source="cyc",
                            reasoning_type=ReasoningType.CONCEPTUAL,
                            context=assertion,
                        )
                    )
            except Exception:
                pass  # Cyc might not be available

            # Cache the result
            self.knowledge_cache[cache_key] = knowledge

        except Exception as e:
            self.logger.warning(f"Error getting knowledge for concept {concept}: {str(e)}")

        return knowledge

    def _map_relation_to_reasoning_type(self, relation: str) -> ReasoningType:
        """Map ConceptNet relation to reasoning type."""
        relation_mappings = {
            "Causes": ReasoningType.CAUSAL,
            "CausesDesire": ReasoningType.CAUSAL,
            "HasPrerequisite": ReasoningType.TEMPORAL,
            "HasFirstSubevent": ReasoningType.TEMPORAL,
            "HasLastSubevent": ReasoningType.TEMPORAL,
            "AtLocation": ReasoningType.SPATIAL,
            "LocatedNear": ReasoningType.SPATIAL,
            "IsA": ReasoningType.CONCEPTUAL,
            "PartOf": ReasoningType.CONCEPTUAL,
            "UsedFor": ReasoningType.PHYSICAL,
            "HasProperty": ReasoningType.PHYSICAL,
            "DesireOf": ReasoningType.EMOTIONAL,
            "MotivatedByGoal": ReasoningType.SOCIAL,
        }

        return relation_mappings.get(relation, ReasoningType.CONCEPTUAL)

    async def _find_concept_relationships(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Find relationships between concepts."""
        relationships = []

        # Check each pair of concepts
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i + 1 :]:
                # Find relationships via ConceptNet
                try:
                    relations = await self.conceptnet.get_concept_relations(
                        concept1, target_concept=concept2
                    )
                    for rel in relations:
                        relationships.append(
                            {
                                "source": concept1,
                                "target": concept2,
                                "relation": rel.get("relation", "related_to"),
                                "confidence": rel.get("weight", 0.5),
                                "source_kb": "conceptnet",
                            }
                        )
                except Exception:
                    pass

        return relationships

    async def _perform_commonsense_inference(
        self,
        concepts: List[str],
        knowledge: List[CommonsenseKnowledge],
        relationships: List[Dict[str, Any]],
    ) -> List[ReasoningChain]:
        """Perform commonsense inference."""
        inferences = []

        # Simple forward chaining
        for concept in concepts:
            concept_knowledge = [k for k in knowledge if k.subject == concept]

            for knowledge_item in concept_knowledge:
                # Generate simple inference
                if knowledge_item.reasoning_type == ReasoningType.CAUSAL:
                    inference = ReasoningChain(
                        premise=f"{knowledge_item.subject} occurs",
                        conclusion=f"{knowledge_item.object} likely occurs",
                        steps=[knowledge_item],
                        confidence=knowledge_item.confidence,
                        reasoning_type=ReasoningType.CAUSAL,
                    )
                    inferences.append(inference)

                elif knowledge_item.reasoning_type == ReasoningType.CONCEPTUAL:
                    inference = ReasoningChain(
                        premise=f"Something is a {knowledge_item.subject}",
                        conclusion=f"It is also a {knowledge_item.object}",
                        steps=[knowledge_item],
                        confidence=knowledge_item.confidence * 0.8,
                        reasoning_type=ReasoningType.CONCEPTUAL,
                    )
                    inferences.append(inference)

        return inferences

    def _calculate_reasoning_confidence(self, inferences: List[ReasoningChain]) -> float:
        """Calculate overall reasoning confidence."""
        if not inferences:
            return 0.0

        return sum(inf.confidence for inf in inferences) / len(inferences)

    async def _extract_interpretations(self, ambiguity: str, context: Dict[str, Any]) -> List[str]:
        """Extract possible interpretations of an ambiguity."""
        interpretations = []

        # Simple pattern-based extraction
        if "could mean" in ambiguity.lower():
            # Extract alternatives after "could mean"
            parts = ambiguity.lower().split("could mean")
            if len(parts) > 1:
                options = parts[1].split(" or ")
                interpretations.extend([opt.strip() for opt in options])

        # Check for word sense disambiguation
        if "ambiguous" in ambiguity.lower():
            # Look for concepts in context that might help
            if "commonsense_concepts" in context:
                concepts = context["commonsense_concepts"]
                # Generate interpretations based on concepts
                for concept in concepts[:3]:  # Limit to top 3
                    interpretations.append(f"Interpreted as related to {concept}")

        # Default interpretations
        if not interpretations:
            interpretations = [
                "Most common interpretation",
                "Alternative interpretation",
                "Context-dependent interpretation",
            ]

        return interpretations

    async def _score_interpretation(self, interpretation: str, context: Dict[str, Any]) -> float:
        """Score an interpretation using commonsense knowledge."""
        base_score = 0.5

        # Check against commonsense knowledge
        if "commonsense_knowledge" in context:
            knowledge_items = context["commonsense_knowledge"]

            # Count relevant knowledge items
            relevant_count = 0
            for item in knowledge_items:
                if any(
                    word in interpretation.lower()
                    for word in [item.get("subject", "").lower(), item.get("object", "").lower()]
                ):
                    relevant_count += 1
                    base_score += item.get("confidence", 0.1) * 0.1

            # Boost score if many relevant items
            if relevant_count > 2:
                base_score += 0.2

        return min(1.0, base_score)

    async def _build_reasoning_chain(
        self,
        concept: str,
        knowledge: List[CommonsenseKnowledge],
        reasoning_type: ReasoningType,
        context: Optional[Dict[str, Any]],
    ) -> Optional[ReasoningChain]:
        """Build a reasoning chain for a specific type."""
        relevant_knowledge = [
            k for k in knowledge if k.reasoning_type == reasoning_type and k.confidence > 0.3
        ]

        if not relevant_knowledge:
            return None

        # Take the most confident knowledge item
        best_knowledge = max(relevant_knowledge, key=lambda x: x.confidence)

        # Generate premise and conclusion
        patterns = self.reasoning_patterns.get(reasoning_type, ["related to"])
        pattern = patterns[0] if patterns else "related to"

        premise = concept
        conclusion = pattern.replace("{A}", concept).replace("{B}", best_knowledge.object)

        return ReasoningChain(
            premise=premise,
            conclusion=conclusion,
            steps=[best_knowledge],
            confidence=best_knowledge.confidence * 0.8,  # Slightly reduce confidence
            reasoning_type=reasoning_type,
        )

    async def _generate_cross_concept_reasoning(
        self, concepts: List[str], context: Optional[Dict[str, Any]]
    ) -> List[ReasoningChain]:
        """Generate reasoning chains between different concepts."""
        chains = []

        # Simple cross-concept inference
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i + 1 :]:
                # Look for potential connections
                knowledge1 = await self._get_concept_knowledge(concept1)
                knowledge2 = await self._get_concept_knowledge(concept2)

                # Find shared objects/subjects
                objects1 = {k.object for k in knowledge1}
                objects2 = {k.object for k in knowledge2}

                shared = objects1.intersection(objects2)

                if shared:
                    shared_obj = list(shared)[0]
                    chain = ReasoningChain(
                        premise=f"{concept1} and {concept2} are both involved",
                        conclusion=f"They share a connection through {shared_obj}",
                        steps=[],
                        confidence=0.6,
                        reasoning_type=ReasoningType.CONCEPTUAL,
                    )
                    chains.append(chain)

        return chains

    async def _find_reasoning_paths(
        self, premise: str, conclusion: str, context: Optional[Dict[str, Any]]
    ) -> List[List[CommonsenseKnowledge]]:
        """Find reasoning paths from premise to conclusion."""
        paths = []

        # Extract concepts from premise and conclusion
        premise_concepts = await self._extract_concepts_from_text(premise)
        conclusion_concepts = await self._extract_concepts_from_text(conclusion)

        # Try to find connections
        for p_concept in premise_concepts:
            for c_concept in conclusion_concepts:
                # Get knowledge for both concepts
                p_knowledge = await self._get_concept_knowledge(p_concept)
                c_knowledge = await self._get_concept_knowledge(c_concept)

                # Look for direct connections
                for p_k in p_knowledge:
                    if p_k.object in [c_k.subject for c_k in c_knowledge]:
                        # Found a connection
                        connecting_knowledge = [
                            c_k for c_k in c_knowledge if c_k.subject == p_k.object
                        ]
                        if connecting_knowledge:
                            path = [p_k, connecting_knowledge[0]]
                            paths.append(path)

        return paths

    def _format_reasoning_path(self, path: List[CommonsenseKnowledge]) -> str:
        """Format a reasoning path as a natural language explanation."""
        if not path:
            return "No clear reasoning path found."

        if len(path) == 1:
            k = path[0]
            return f"Based on commonsense knowledge: {k.subject} {k.relation} {k.object}"

        explanation = "Reasoning path: "
        for i, knowledge in enumerate(path):
            if i > 0:
                explanation += " → "
            explanation += f"{knowledge.subject} {knowledge.relation} {knowledge.object}"

        return explanation

    async def _generate_general_explanation(
        self, premise: str, conclusion: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a general explanation when no specific path is found."""
        # Extract key concepts
        premise_concepts = await self._extract_concepts_from_text(premise)
        conclusion_concepts = await self._extract_concepts_from_text(conclusion)

        if premise_concepts and conclusion_concepts:
            return f"The connection between '{premise}' and '{conclusion}' likely involves relationships between {', '.join(premise_concepts[:2])} and {', '.join(conclusion_concepts[:2])} based on commonsense knowledge."
        else:
            return f"While there may be a commonsense connection between '{premise}' and '{conclusion}', it requires domain-specific knowledge to explain clearly."

    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics."""
        return self.stats.copy()

    def clear_cache(self):
        """Clear knowledge and reasoning caches."""
        self.knowledge_cache.clear()
        self.reasoning_cache.clear()

    async def preload_common_concepts(self, concepts: List[str]):
        """Preload knowledge for common concepts."""
        tasks = [self._get_concept_knowledge(concept) for concept in concepts]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.logger.info(f"Preloaded knowledge for {len(concepts)} concepts")
