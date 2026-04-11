"""
ConceptNet integration for commonsense knowledge.

This module provides integration with ConceptNet 5.7, a large-scale semantic
network that captures commonsense knowledge about concepts and their relationships.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp


class ConceptNetIntegration:
    """
    Integration with ConceptNet API for commonsense knowledge.

    ConceptNet is a freely-available semantic network designed to help computers
    understand the meanings of words that people use.
    """

    def __init__(self):
        """Initialize ConceptNet integration."""
        self.logger = logging.getLogger(__name__)
        self.base_url = "http://api.conceptnet.io"
        self.cache = {}
        self.rate_limit_delay = 0.1  # Seconds between requests
        self.last_request_time = 0

        # Session for connection pooling
        self.session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _rate_limited_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make rate-limited request to ConceptNet API."""
        # Implement simple rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                self.last_request_time = time.time()

                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.warning(
                        f"ConceptNet API returned status {response.status} for {url}"
                    )
                    return None

        except Exception as e:
            self.logger.error(f"Error requesting {url}: {str(e)}")
            return None

    async def get_concept_relations(
        self,
        concept: str,
        target_concept: Optional[str] = None,
        relation_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get relations for a concept from ConceptNet.

        Args:
            concept: Source concept
            target_concept: Optional target concept to filter relations
            relation_types: Optional list of relation types to include
            limit: Maximum number of relations to return

        Returns:
            List of relation dictionaries
        """
        # Check cache first
        cache_key = f"relations_{concept}_{target_concept}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Construct URL
        concept_encoded = concept.replace(" ", "_").lower()
        url = f"{self.base_url}/c/en/{concept_encoded}?offset=0&limit={limit}"

        response = await self._rate_limited_request(url)

        if not response:
            return []

        relations = []

        try:
            edges = response.get("edges", [])

            for edge in edges:
                # Extract relation information
                rel = edge.get("rel", {})
                start = edge.get("start", {})
                end = edge.get("end", {})

                relation_type = rel.get("label", "")
                weight = edge.get("weight", 1.0)

                # Filter by relation type if specified
                if relation_types and relation_type not in relation_types:
                    continue

                # Extract subject and object
                start_label = start.get("label", "").lower()
                end_label = end.get("label", "").lower()

                # Determine subject and object based on direction
                if start_label == concept.lower():
                    subject = start_label
                    obj = end_label
                else:
                    subject = end_label
                    obj = start_label

                # Filter by target concept if specified
                if target_concept and target_concept.lower() not in [subject, obj]:
                    continue

                relation_data = {
                    "subject": subject,
                    "relation": relation_type,
                    "object": obj,
                    "weight": weight,
                    "uri": edge.get("@id", ""),
                    "start_uri": start.get("@id", ""),
                    "end_uri": end.get("@id", ""),
                    "dataset": edge.get("dataset", ""),
                    "sources": edge.get("sources", []),
                }

                relations.append(relation_data)

            # Cache the result
            self.cache[cache_key] = relations

        except Exception as e:
            self.logger.error(f"Error parsing ConceptNet response: {str(e)}")

        return relations

    async def get_related_concepts(
        self, concept: str, relation_type: Optional[str] = None, limit: int = 10
    ) -> List[str]:
        """
        Get concepts related to the given concept.

        Args:
            concept: Source concept
            relation_type: Optional specific relation type
            limit: Maximum number of related concepts

        Returns:
            List of related concept names
        """
        relations = await self.get_concept_relations(
            concept, relation_types=[relation_type] if relation_type else None, limit=limit
        )

        related_concepts = []
        for rel in relations:
            if rel["subject"].lower() == concept.lower():
                related_concepts.append(rel["object"])
            else:
                related_concepts.append(rel["subject"])

        # Remove duplicates and return
        return list(set(related_concepts))[:limit]

    async def find_path(
        self, start_concept: str, end_concept: str, max_depth: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two concepts.

        Args:
            start_concept: Starting concept
            end_concept: Target concept
            max_depth: Maximum path length

        Returns:
            List of relations forming the path, or None if no path found
        """
        # Use breadth-first search to find shortest path
        visited = set()
        queue = [(start_concept, [])]

        while queue and len(queue[0][1]) < max_depth:
            current_concept, path = queue.pop(0)

            if current_concept.lower() == end_concept.lower():
                return path

            if current_concept in visited:
                continue

            visited.add(current_concept)

            # Get relations for current concept
            relations = await self.get_concept_relations(current_concept, limit=10)

            for relation in relations:
                next_concept = None
                if relation["subject"].lower() == current_concept.lower():
                    next_concept = relation["object"]
                elif relation["object"].lower() == current_concept.lower():
                    next_concept = relation["subject"]

                if next_concept and next_concept not in visited:
                    new_path = path + [relation]
                    queue.append((next_concept, new_path))

        return None  # No path found

    async def get_concept_properties(self, concept: str) -> Dict[str, List[str]]:
        """
        Get properties of a concept organized by relation type.

        Args:
            concept: Concept to analyze

        Returns:
            Dictionary with relation types as keys and lists of related concepts as values
        """
        relations = await self.get_concept_relations(concept, limit=50)

        properties = {}

        for relation in relations:
            rel_type = relation["relation"]

            if rel_type not in properties:
                properties[rel_type] = []

            # Add the related concept
            if relation["subject"].lower() == concept.lower():
                properties[rel_type].append(relation["object"])
            else:
                properties[rel_type].append(relation["subject"])

        # Remove duplicates
        for rel_type in properties:
            properties[rel_type] = list(set(properties[rel_type]))

        return properties

    async def get_common_sense_facts(self, concept: str) -> List[str]:
        """
        Get common sense facts about a concept in natural language.

        Args:
            concept: Concept to get facts about

        Returns:
            List of natural language facts
        """
        relations = await self.get_concept_relations(concept, limit=30)

        facts = []

        # Relation templates for natural language generation
        templates = {
            "IsA": "{subject} is a type of {object}",
            "PartOf": "{subject} is part of {object}",
            "UsedFor": "{subject} is used for {object}",
            "CapableOf": "{subject} is capable of {object}",
            "AtLocation": "{subject} is located at {object}",
            "HasProperty": "{subject} has the property of being {object}",
            "Causes": "{subject} causes {object}",
            "HasPrerequisite": "{subject} requires {object}",
            "MotivatedByGoal": "{subject} is motivated by the goal of {object}",
            "CreatedBy": "{subject} is created by {object}",
            "DefinedAs": "{subject} is defined as {object}",
        }

        for relation in relations:
            rel_type = relation["relation"]
            subject = relation["subject"]
            obj = relation["object"]

            if rel_type in templates:
                fact = templates[rel_type].format(subject=subject, object=obj)
                facts.append(fact)
            else:
                # Generic template
                fact = f"{subject} is related to {obj} by {rel_type}"
                facts.append(fact)

        return facts[:15]  # Return top 15 facts

    async def search_concepts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for concepts matching a query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching concepts with metadata
        """
        # Use ConceptNet search endpoint
        url = f"{self.base_url}/search?q={query}&limit={limit}"

        response = await self._rate_limited_request(url)

        if not response:
            return []

        concepts = []

        try:
            for item in response.get("edges", []):
                start = item.get("start", {})
                end = item.get("end", {})

                # Extract concept information
                concept_data = {
                    "label": start.get("label", ""),
                    "uri": start.get("@id", ""),
                    "language": start.get("language", "en"),
                    "weight": item.get("weight", 1.0),
                    "related_to": end.get("label", ""),
                    "relation": item.get("rel", {}).get("label", ""),
                }

                concepts.append(concept_data)

        except Exception as e:
            self.logger.error(f"Error parsing search results: {str(e)}")

        return concepts

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def clear_cache(self):
        """Clear the concept relations cache."""
        self.cache.clear()
        self.logger.info("ConceptNet cache cleared")

    async def batch_get_relations(
        self, concepts: List[str], batch_size: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relations for multiple concepts in batches.

        Args:
            concepts: List of concepts
            batch_size: Number of concepts to process concurrently

        Returns:
            Dictionary mapping concepts to their relations
        """
        results = {}

        for i in range(0, len(concepts), batch_size):
            batch = concepts[i : i + batch_size]

            # Process batch concurrently
            tasks = [self.get_concept_relations(concept) for concept in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for concept, relations in zip(batch, batch_results):
                if isinstance(relations, list):
                    results[concept] = relations
                else:
                    results[concept] = []
                    self.logger.error(f"Error getting relations for {concept}: {relations}")

        return results
