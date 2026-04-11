"""
OpenCyc integration for formal commonsense knowledge.

This module provides integration with OpenCyc, a formal ontology and knowledge base
that contains hundreds of thousands of terms and millions of assertions.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp


class CycIntegration:
    """
    Integration with OpenCyc knowledge base.

    OpenCyc provides a formal representation of commonsense knowledge
    using first-order logic and specialized inference engines.
    """

    def __init__(self, cyc_server_url: Optional[str] = None):
        """
        Initialize Cyc integration.

        Args:
            cyc_server_url: URL of Cyc server (if available)
        """
        self.logger = logging.getLogger(__name__)
        self.cyc_server_url = cyc_server_url or "http://localhost:3602"  # Default ResearchCyc port
        self.available = False
        self.cache = {}
        self.session = None

        # Built-in knowledge for when Cyc server is not available
        self._init_builtin_knowledge()

    def _init_builtin_knowledge(self):
        """Initialize built-in Cyc-style knowledge for fallback."""
        self.builtin_knowledge = {
            # Basic taxonomic relationships
            "dog": [
                {"predicate": "isa", "object": "DomesticatedAnimal", "confidence": 0.95},
                {"predicate": "isa", "object": "Mammal", "confidence": 0.95},
                {"predicate": "isa", "object": "Pet", "confidence": 0.9},
            ],
            "cat": [
                {"predicate": "isa", "object": "DomesticatedAnimal", "confidence": 0.95},
                {"predicate": "isa", "object": "Mammal", "confidence": 0.95},
                {"predicate": "isa", "object": "Pet", "confidence": 0.9},
            ],
            "bird": [
                {"predicate": "isa", "object": "Animal", "confidence": 0.95},
                {"predicate": "isa", "object": "FlyingAnimal", "confidence": 0.8},
            ],
            "car": [
                {"predicate": "isa", "object": "Vehicle", "confidence": 0.95},
                {"predicate": "isa", "object": "TransportationDevice", "confidence": 0.9},
            ],
            "book": [
                {"predicate": "isa", "object": "InformationBearingObject", "confidence": 0.9},
                {"predicate": "isa", "object": "PhysicalObject", "confidence": 0.9},
            ],
            "water": [
                {"predicate": "isa", "object": "Liquid", "confidence": 0.95},
                {"predicate": "isa", "object": "ChemicalCompound", "confidence": 0.95},
            ],
            "tree": [
                {"predicate": "isa", "object": "Plant", "confidence": 0.95},
                {"predicate": "isa", "object": "LivingThing", "confidence": 0.95},
            ],
            "house": [
                {"predicate": "isa", "object": "Building", "confidence": 0.95},
                {"predicate": "isa", "object": "Shelter", "confidence": 0.9},
            ],
            "person": [
                {"predicate": "isa", "object": "Human", "confidence": 0.95},
                {"predicate": "isa", "object": "IntelligentAgent", "confidence": 0.9},
                {"predicate": "isa", "object": "SocialBeing", "confidence": 0.9},
            ],
            "computer": [
                {"predicate": "isa", "object": "ComputingDevice", "confidence": 0.95},
                {"predicate": "isa", "object": "ElectronicDevice", "confidence": 0.9},
            ],
        }

        # Common predicates and their meanings
        self.predicate_meanings = {
            "isa": "is a type of",
            "genls": "is a generalization of",
            "partOf": "is part of",
            "spatiallyContains": "spatially contains",
            "causes": "causes",
            "prerequisiteFor": "is a prerequisite for",
            "purposeOf": "serves the purpose of",
            "behaviorCapable": "is capable of the behavior",
            "physicalParts": "has physical parts",
            "typicallyContains": "typically contains",
        }

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def check_availability(self) -> bool:
        """Check if Cyc server is available."""
        try:
            session = await self._get_session()
            test_url = f"{self.cyc_server_url}/cyc/api/status"

            async with session.get(test_url, timeout=5) as response:
                if response.status == 200:
                    self.available = True
                    self.logger.info("Cyc server is available")
                    return True
        except Exception as e:
            self.logger.info(f"Cyc server not available, using builtin knowledge: {str(e)}")

        self.available = False
        return False

    async def get_concept_assertions(self, concept: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get assertions about a concept from Cyc.

        Args:
            concept: Concept to query
            limit: Maximum number of assertions

        Returns:
            List of assertion dictionaries
        """
        # Check cache first
        cache_key = f"assertions_{concept}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        assertions = []

        if self.available:
            # Try to get from actual Cyc server
            assertions = await self._query_cyc_server(concept, limit)

        # If server not available or no results, use builtin knowledge
        if not assertions:
            assertions = self._get_builtin_assertions(concept)

        # Cache the result
        self.cache[cache_key] = assertions

        return assertions

    async def _query_cyc_server(self, concept: str, limit: int) -> List[Dict[str, Any]]:
        """Query actual Cyc server for assertions."""
        try:
            session = await self._get_session()

            # Construct CycL query
            # This is a simplified query - actual Cyc queries are more complex
            query = f"(#$isa ?X #${concept})"

            query_url = f"{self.cyc_server_url}/cyc/api/query"
            data = {
                "query": query,
                "microtheory": "#$EverythingPSC",  # Default microtheory
                "limit": limit,
            }

            async with session.post(query_url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_cyc_response(result)
                else:
                    self.logger.warning(f"Cyc server returned status {response.status}")

        except Exception as e:
            self.logger.error(f"Error querying Cyc server: {str(e)}")

        return []

    def _parse_cyc_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse response from Cyc server."""
        assertions = []

        try:
            # This would need to be adapted based on actual Cyc API format
            bindings = response.get("bindings", [])

            for binding in bindings:
                # Extract subject, predicate, object from binding
                # This is simplified - actual parsing would be more complex
                assertion = {
                    "subject": binding.get("subject", ""),
                    "predicate": binding.get("predicate", ""),
                    "object": binding.get("object", ""),
                    "confidence": binding.get("confidence", 0.8),
                    "microtheory": binding.get("microtheory", "#$EverythingPSC"),
                }
                assertions.append(assertion)

        except Exception as e:
            self.logger.error(f"Error parsing Cyc response: {str(e)}")

        return assertions

    def _get_builtin_assertions(self, concept: str) -> List[Dict[str, Any]]:
        """Get assertions from builtin knowledge base."""
        concept_lower = concept.lower()

        assertions = []

        # Direct lookup
        if concept_lower in self.builtin_knowledge:
            base_assertions = self.builtin_knowledge[concept_lower]
            for assertion in base_assertions:
                assertions.append(
                    {
                        "subject": concept,
                        "predicate": assertion["predicate"],
                        "object": assertion["object"],
                        "confidence": assertion["confidence"],
                        "source": "builtin",
                    }
                )

        # Pattern-based inference
        assertions.extend(self._infer_assertions(concept))

        return assertions

    def _infer_assertions(self, concept: str) -> List[Dict[str, Any]]:
        """Infer assertions based on patterns and common knowledge."""
        assertions = []
        concept_lower = concept.lower()

        # Pattern-based inference rules
        if concept_lower.endswith("ing"):
            # Likely an activity or process
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "Activity",
                    "confidence": 0.7,
                    "source": "inference",
                }
            )

        elif concept_lower.endswith("er") or concept_lower.endswith("or"):
            # Likely a person who does something
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "Person",
                    "confidence": 0.6,
                    "source": "inference",
                }
            )

        elif concept_lower.endswith("tion") or concept_lower.endswith("sion"):
            # Likely an abstract concept or process
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "AbstractEntity",
                    "confidence": 0.7,
                    "source": "inference",
                }
            )

        # Common word patterns
        if any(word in concept_lower for word in ["food", "meal", "eat"]):
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "Food",
                    "confidence": 0.8,
                    "source": "inference",
                }
            )

        if any(word in concept_lower for word in ["color", "colour"]):
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "Color",
                    "confidence": 0.9,
                    "source": "inference",
                }
            )

        if any(word in concept_lower for word in ["tool", "equipment", "device"]):
            assertions.append(
                {
                    "subject": concept,
                    "predicate": "isa",
                    "object": "Artifact",
                    "confidence": 0.8,
                    "source": "inference",
                }
            )

        return assertions

    async def query_relationship(
        self, subject: str, predicate: str, object_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for specific relationships.

        Args:
            subject: Subject of the relationship
            predicate: Relationship predicate
            object_type: Optional type constraint on object

        Returns:
            List of matching relationships
        """
        # This would query Cyc for specific relationships
        # For now, we'll use pattern matching on builtin knowledge

        results = []

        # Get all assertions for the subject
        assertions = await self.get_concept_assertions(subject)

        for assertion in assertions:
            if assertion["predicate"] == predicate:
                if object_type is None or assertion["object"] == object_type:
                    results.append(assertion)

        return results

    async def get_superclasses(self, concept: str) -> List[str]:
        """
        Get superclasses (generalizations) of a concept.

        Args:
            concept: Concept to find superclasses for

        Returns:
            List of superclass names
        """
        assertions = await self.get_concept_assertions(concept)

        superclasses = []
        for assertion in assertions:
            if assertion["predicate"] in ["isa", "genls"]:
                superclasses.append(assertion["object"])

        return superclasses

    async def get_subclasses(self, concept: str) -> List[str]:
        """
        Get subclasses (specializations) of a concept.

        Args:
            concept: Concept to find subclasses for

        Returns:
            List of subclass names
        """
        # This would require reverse lookup in a full Cyc implementation
        # For now, return empty list as this requires comprehensive data
        return []

    async def check_isa_relationship(self, specific: str, general: str) -> float:
        """
        Check if one concept is a type of another.

        Args:
            specific: More specific concept
            general: More general concept

        Returns:
            Confidence score (0.0 to 1.0)
        """
        assertions = await self.get_concept_assertions(specific)

        for assertion in assertions:
            if assertion["predicate"] == "isa" and assertion["object"].lower() == general.lower():
                return assertion["confidence"]

        # Check through inheritance chain
        superclasses = await self.get_superclasses(specific)
        for superclass in superclasses:
            if superclass.lower() == general.lower():
                return 0.8  # High confidence for direct superclass

            # Recursive check (limited depth)
            indirect_confidence = await self.check_isa_relationship(superclass, general)
            if indirect_confidence > 0.5:
                return indirect_confidence * 0.8  # Reduce confidence for indirect

        return 0.0

    def generate_cyc_formula(self, subject: str, predicate: str, obj: str) -> str:
        """
        Generate a CycL formula from components.

        Args:
            subject: Subject term
            predicate: Predicate term
            obj: Object term

        Returns:
            CycL formula string
        """
        # Simple CycL formula generation
        # Real CycL is much more complex with proper term formatting

        return f"(#{predicate} #{subject} #{obj})"

    def explain_assertion(self, assertion: Dict[str, Any]) -> str:
        """
        Generate natural language explanation of an assertion.

        Args:
            assertion: Assertion dictionary

        Returns:
            Natural language explanation
        """
        subject = assertion.get("subject", "something")
        predicate = assertion.get("predicate", "relates to")
        obj = assertion.get("object", "something else")

        # Get human-readable predicate meaning
        predicate_meaning = self.predicate_meanings.get(predicate, predicate)

        explanation = f"{subject} {predicate_meaning} {obj}"

        # Add confidence information
        confidence = assertion.get("confidence", 0.0)
        if confidence > 0.9:
            explanation += " (very confident)"
        elif confidence > 0.7:
            explanation += " (confident)"
        elif confidence > 0.5:
            explanation += " (somewhat confident)"
        else:
            explanation += " (uncertain)"

        return explanation

    async def batch_query_concepts(self, concepts: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query multiple concepts in batch.

        Args:
            concepts: List of concepts to query

        Returns:
            Dictionary mapping concepts to their assertions
        """
        results = {}

        # Process in parallel
        tasks = [self.get_concept_assertions(concept) for concept in concepts]
        all_assertions = await asyncio.gather(*tasks, return_exceptions=True)

        for concept, assertions in zip(concepts, all_assertions):
            if isinstance(assertions, list):
                results[concept] = assertions
            else:
                results[concept] = []
                self.logger.error(f"Error querying {concept}: {assertions}")

        return results

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def clear_cache(self):
        """Clear the assertion cache."""
        self.cache.clear()
        self.logger.info("Cyc cache cleared")

    def get_predicate_info(self, predicate: str) -> Dict[str, Any]:
        """
        Get information about a predicate.

        Args:
            predicate: Predicate name

        Returns:
            Dictionary with predicate information
        """
        meaning = self.predicate_meanings.get(predicate, "relates to")

        return {
            "predicate": predicate,
            "meaning": meaning,
            "arity": 2,  # Most predicates are binary
            "type": "relation",
        }
