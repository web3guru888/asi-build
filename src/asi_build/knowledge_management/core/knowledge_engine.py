"""
Kenny Knowledge Engine - Core Omniscience System
===============================================

Main orchestrator for the omniscience network that coordinates all knowledge
subsystems and provides unified access to comprehensive information processing.
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..learning.contextual_learner import ContextualLearner
from ..search.intelligent_search import IntelligentSearch
from ..synthesis.predictive_synthesizer import PredictiveSynthesizer
from ..validation.quality_controller import QualityController
from .information_aggregator import InformationAggregator
from .knowledge_graph_manager import KnowledgeGraphManager


@dataclass
class KnowledgeQuery:
    """Represents a knowledge query with context and metadata."""

    query: str
    context: Dict[str, Any]
    priority: int = 1
    timestamp: float = None
    session_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class KnowledgeResult:
    """Represents the result of a knowledge query."""

    query: KnowledgeQuery
    result: Dict[str, Any]
    confidence: float
    sources: List[str]
    processing_time: float
    metadata: Dict[str, Any]


class KnowledgeEngine:
    """
    Main Knowledge Engine for Kenny's Omniscience Network

    Orchestrates comprehensive knowledge processing across multiple
    subsystems to provide intelligent, contextual information synthesis.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = self._setup_logging()

        # Initialize subsystems
        self.aggregator = InformationAggregator(self.config.get("aggregator", {}))
        self.graph_manager = KnowledgeGraphManager(self.config.get("graph", {}))
        self.search_engine = IntelligentSearch(self.config.get("search", {}))
        self.synthesizer = PredictiveSynthesizer(self.config.get("synthesis", {}))
        self.quality_controller = QualityController(self.config.get("validation", {}))
        self.learner = ContextualLearner(self.config.get("learning", {}))

        # Performance tracking
        self.query_count = 0
        self.total_processing_time = 0.0
        self.average_confidence = 0.0

        self.logger.info("Kenny Knowledge Engine initialized successfully")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the knowledge engine."""
        return {
            "max_concurrent_queries": 10,
            "default_timeout": 30.0,
            "quality_threshold": 0.7,
            "learning_enabled": True,
            "caching_enabled": True,
            "parallel_processing": True,
            "aggregator": {"max_sources": 50, "timeout_per_source": 5.0},
            "graph": {"max_depth": 5, "relationship_threshold": 0.6},
            "search": {"semantic_search": True, "fuzzy_matching": True, "context_expansion": True},
            "synthesis": {"prediction_horizon": "24h", "confidence_threshold": 0.8},
            "validation": {"fact_checking": True, "source_verification": True},
            "learning": {"adaptive_learning": True, "pattern_recognition": True},
        }

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the knowledge engine."""
        logger = logging.getLogger("kenny.omniscience.engine")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def process_query(self, query: Union[str, KnowledgeQuery]) -> KnowledgeResult:
        """
        Process a knowledge query through the complete omniscience pipeline.

        Args:
            query: The knowledge query to process

        Returns:
            KnowledgeResult containing comprehensive analysis
        """
        start_time = time.time()

        # Convert string to KnowledgeQuery if needed
        if isinstance(query, str):
            query = KnowledgeQuery(query=query, context={})

        self.logger.info(f"Processing knowledge query: {query.query[:100]}...")

        try:
            # Phase 1: Information Aggregation
            aggregated_info = await self.aggregator.aggregate_information(query)

            # Phase 2: Knowledge Graph Analysis
            graph_insights = await self.graph_manager.analyze_relationships(query, aggregated_info)

            # Phase 3: Intelligent Search
            search_results = await self.search_engine.search_comprehensive(query, aggregated_info)

            # Phase 4: Predictive Synthesis
            synthesis_result = await self.synthesizer.synthesize_knowledge(
                query, aggregated_info, graph_insights, search_results
            )

            # Phase 5: Quality Validation
            validated_result = await self.quality_controller.validate_knowledge(synthesis_result)

            # Phase 6: Contextual Learning (if enabled)
            if self.config.get("learning_enabled", True):
                await self.learner.learn_from_interaction(query, validated_result)

            processing_time = time.time() - start_time

            # Create comprehensive result
            result = KnowledgeResult(
                query=query,
                result={
                    "aggregated_info": aggregated_info,
                    "graph_insights": graph_insights,
                    "search_results": search_results,
                    "synthesis": synthesis_result,
                    "validation": validated_result,
                    "summary": self._create_summary(validated_result),
                    "recommendations": self._generate_recommendations(validated_result),
                },
                confidence=validated_result.get("confidence", 0.0),
                sources=self._extract_sources(aggregated_info, search_results),
                processing_time=processing_time,
                metadata={
                    "engine_version": "1.0.0",
                    "processing_phases": 6,
                    "subsystems_used": [
                        "aggregator",
                        "graph_manager",
                        "search_engine",
                        "synthesizer",
                        "quality_controller",
                        "learner",
                    ],
                },
            )

            # Update performance metrics
            self._update_metrics(result)

            self.logger.info(
                f"Query processed successfully in {processing_time:.2f}s "
                f"with confidence {result.confidence:.2f}"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error processing query: {str(e)}")

            # Return error result
            return KnowledgeResult(
                query=query,
                result={"error": str(e)},
                confidence=0.0,
                sources=[],
                processing_time=processing_time,
                metadata={"error": True},
            )

    async def batch_process_queries(
        self, queries: List[Union[str, KnowledgeQuery]]
    ) -> List[KnowledgeResult]:
        """
        Process multiple knowledge queries concurrently.

        Args:
            queries: List of queries to process

        Returns:
            List of KnowledgeResults
        """
        self.logger.info(f"Processing batch of {len(queries)} queries")

        max_concurrent = self.config.get("max_concurrent_queries", 10)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(query):
            async with semaphore:
                return await self.process_query(query)

        tasks = [process_with_semaphore(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch query {i} failed: {str(result)}")
                # Create error result
                query = (
                    queries[i]
                    if isinstance(queries[i], KnowledgeQuery)
                    else KnowledgeQuery(query=queries[i], context={})
                )
                processed_results.append(
                    KnowledgeResult(
                        query=query,
                        result={"error": str(result)},
                        confidence=0.0,
                        sources=[],
                        processing_time=0.0,
                        metadata={"error": True},
                    )
                )
            else:
                processed_results.append(result)

        self.logger.info(f"Batch processing completed: {len(processed_results)} results")
        return processed_results

    def _create_summary(self, validated_result: Dict[str, Any]) -> str:
        """Create a concise summary of the knowledge result."""
        if "summary" in validated_result:
            return validated_result["summary"]

        # Generate default summary
        return "Comprehensive knowledge analysis completed with multi-system validation."

    def _generate_recommendations(self, validated_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on the knowledge result."""
        recommendations = []

        confidence = validated_result.get("confidence", 0.0)

        if confidence < 0.5:
            recommendations.append("Consider gathering additional information sources")
            recommendations.append("Verify key facts through multiple channels")
        elif confidence < 0.8:
            recommendations.append("Cross-reference findings with authoritative sources")
        else:
            recommendations.append("High confidence result - suitable for decision making")

        return recommendations

    def _extract_sources(
        self, aggregated_info: Dict[str, Any], search_results: Dict[str, Any]
    ) -> List[str]:
        """Extract unique sources from aggregated information and search results."""
        sources = set()

        # Extract from aggregated info
        if "sources" in aggregated_info:
            sources.update(aggregated_info["sources"])

        # Extract from search results
        if "sources" in search_results:
            sources.update(search_results["sources"])

        return list(sources)

    def _update_metrics(self, result: KnowledgeResult):
        """Update performance metrics."""
        self.query_count += 1
        self.total_processing_time += result.processing_time

        # Update rolling average confidence
        alpha = 0.1  # Smoothing factor
        self.average_confidence = alpha * result.confidence + (1 - alpha) * self.average_confidence

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        avg_processing_time = (
            self.total_processing_time / self.query_count if self.query_count > 0 else 0.0
        )

        return {
            "total_queries": self.query_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "average_confidence": self.average_confidence,
            "subsystem_status": {
                "aggregator": "active",
                "graph_manager": "active",
                "search_engine": "active",
                "synthesizer": "active",
                "quality_controller": "active",
                "learner": "active",
            },
        }

    async def shutdown(self):
        """Gracefully shutdown the knowledge engine."""
        self.logger.info("Shutting down Kenny Knowledge Engine...")

        # Shutdown subsystems
        await self.aggregator.shutdown()
        await self.graph_manager.shutdown()
        await self.search_engine.shutdown()
        await self.synthesizer.shutdown()
        await self.quality_controller.shutdown()
        await self.learner.shutdown()

        self.logger.info("Knowledge Engine shutdown complete")


# Module-level convenience functions
async def query_knowledge(query: str, context: Optional[Dict[str, Any]] = None) -> KnowledgeResult:
    """Convenience function to query the knowledge engine."""
    engine = KnowledgeEngine()
    knowledge_query = KnowledgeQuery(query=query, context=context or {})
    return await engine.process_query(knowledge_query)


async def batch_query_knowledge(queries: List[str]) -> List[KnowledgeResult]:
    """Convenience function to batch query the knowledge engine."""
    engine = KnowledgeEngine()
    return await engine.batch_process_queries(queries)
