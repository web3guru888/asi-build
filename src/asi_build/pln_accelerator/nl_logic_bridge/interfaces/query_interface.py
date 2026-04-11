"""
Interactive Query Interface for NL-Logic Bridge.

This module provides an interactive interface for researchers to query
the NL-Logic bridge system, perform translations, and explore the
relationship between natural language and logical representations.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.bridge import LogicFormalism, NLLogicBridge, TranslationResult
from ..core.context_manager import ContextManager


class QueryType(Enum):
    """Types of queries supported by the interface."""

    NL_TO_LOGIC = "nl_to_logic"
    LOGIC_TO_NL = "logic_to_nl"
    BIDIRECTIONAL = "bidirectional"
    KNOWLEDGE_QUERY = "knowledge_query"
    EXPLANATION = "explanation"
    ALTERNATIVES = "alternatives"
    VALIDATION = "validation"
    EXPLORATION = "exploration"


@dataclass
class QueryRequest:
    """Represents a query request."""

    query_id: str
    query_type: QueryType
    input_text: str
    parameters: Dict[str, Any]
    session_id: str
    timestamp: float
    user_id: Optional[str] = None


@dataclass
class QueryResponse:
    """Represents a query response."""

    query_id: str
    success: bool
    result: Any
    explanation: List[str]
    metadata: Dict[str, Any]
    processing_time: float
    confidence: float
    suggestions: List[str] = None
    error_message: Optional[str] = None


class QueryInterface:
    """
    Interactive Query Interface for researchers and users.

    This interface provides a comprehensive way to interact with the NL-Logic
    bridge system, offering various query types and exploration capabilities.
    """

    def __init__(self, bridge: Optional[NLLogicBridge] = None):
        """Initialize the query interface."""
        self.logger = logging.getLogger(__name__)
        self.bridge = bridge or NLLogicBridge()

        # Query history and statistics
        self.query_history: List[QueryRequest] = []
        self.response_history: List[QueryResponse] = []
        self.session_stats: Dict[str, Dict[str, Any]] = {}

        # Active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Query templates and examples
        self._init_query_templates()

        # Statistics
        self.stats = {
            "total_queries": 0,
            "queries_by_type": {},
            "average_processing_time": 0.0,
            "average_confidence": 0.0,
            "success_rate": 1.0,
        }

    def _init_query_templates(self):
        """Initialize query templates and examples."""
        self.query_templates = {
            QueryType.NL_TO_LOGIC: {
                "description": "Convert natural language to logical representation",
                "examples": [
                    "All birds can fly",
                    "If it rains, then the ground gets wet",
                    "Dogs are animals",
                    "Some students are hardworking",
                ],
                "parameters": [
                    {"name": "target_formalism", "type": "LogicFormalism", "optional": True},
                    {"name": "include_explanation", "type": "bool", "default": True},
                ],
            },
            QueryType.LOGIC_TO_NL: {
                "description": "Convert logical expression to natural language",
                "examples": [
                    "∀x (Bird(x) → CanFly(x))",
                    "InheritanceLink <0.9, 0.8>\\n  Dog\\n  Animal",
                    "Rain(x) → WetGround(x)",
                ],
                "parameters": [
                    {"name": "source_formalism", "type": "LogicFormalism", "required": True},
                    {"name": "target_language", "type": "str", "default": "en"},
                    {"name": "style", "type": "str", "default": "conversational"},
                ],
            },
            QueryType.BIDIRECTIONAL: {
                "description": "Perform bidirectional translation to check consistency",
                "examples": [
                    "All cats are animals",
                    "If you study hard, you will succeed",
                    "Water boils at 100 degrees Celsius",
                ],
                "parameters": [
                    {"name": "source_type", "type": "str", "default": "natural_language"},
                    {"name": "formalism", "type": "LogicFormalism", "optional": True},
                ],
            },
            QueryType.KNOWLEDGE_QUERY: {
                "description": "Query the knowledge base",
                "examples": [
                    "What do you know about dogs?",
                    "Tell me about the relationship between cats and animals",
                    "What causes rain?",
                ],
                "parameters": [
                    {"name": "query_type", "type": "str", "default": "natural_language"},
                    {"name": "max_results", "type": "int", "default": 10},
                ],
            },
        }

    async def process_query(
        self,
        query_text: str,
        query_type: QueryType,
        session_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> QueryResponse:
        """
        Process a query request.

        Args:
            query_text: Input query text
            query_type: Type of query to perform
            session_id: Session identifier
            parameters: Additional query parameters
            user_id: Optional user identifier

        Returns:
            Query response with results and metadata
        """
        start_time = time.time()
        query_id = str(uuid.uuid4())

        # Create query request
        request = QueryRequest(
            query_id=query_id,
            query_type=query_type,
            input_text=query_text,
            parameters=parameters or {},
            session_id=session_id,
            timestamp=start_time,
            user_id=user_id,
        )

        self.query_history.append(request)

        try:
            # Process based on query type
            if query_type == QueryType.NL_TO_LOGIC:
                result = await self._process_nl_to_logic(request)
            elif query_type == QueryType.LOGIC_TO_NL:
                result = await self._process_logic_to_nl(request)
            elif query_type == QueryType.BIDIRECTIONAL:
                result = await self._process_bidirectional(request)
            elif query_type == QueryType.KNOWLEDGE_QUERY:
                result = await self._process_knowledge_query(request)
            elif query_type == QueryType.EXPLANATION:
                result = await self._process_explanation_request(request)
            elif query_type == QueryType.ALTERNATIVES:
                result = await self._process_alternatives_request(request)
            elif query_type == QueryType.VALIDATION:
                result = await self._process_validation_request(request)
            elif query_type == QueryType.EXPLORATION:
                result = await self._process_exploration_request(request)
            else:
                raise ValueError(f"Unsupported query type: {query_type}")

            processing_time = time.time() - start_time

            # Create response
            response = QueryResponse(
                query_id=query_id,
                success=True,
                result=result,
                explanation=result.get("explanation", []),
                metadata=result.get("metadata", {}),
                processing_time=processing_time,
                confidence=result.get("confidence", 0.0),
                suggestions=result.get("suggestions", []),
            )

            # Update statistics
            self._update_stats(query_type, processing_time, response.confidence, True)

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error processing query {query_id}: {str(e)}")

            response = QueryResponse(
                query_id=query_id,
                success=False,
                result=None,
                explanation=[f"Error processing query: {str(e)}"],
                metadata={"error_type": type(e).__name__},
                processing_time=processing_time,
                confidence=0.0,
                error_message=str(e),
            )

            # Update statistics
            self._update_stats(query_type, processing_time, 0.0, False)

        self.response_history.append(response)

        # Update session stats
        self._update_session_stats(session_id, request, response)

        return response

    async def _process_nl_to_logic(self, request: QueryRequest) -> Dict[str, Any]:
        """Process natural language to logic translation request."""
        parameters = request.parameters
        target_formalism = parameters.get("target_formalism", LogicFormalism.PLN)
        include_explanation = parameters.get("include_explanation", True)

        # Convert string to LogicFormalism if needed
        if isinstance(target_formalism, str):
            target_formalism = LogicFormalism(target_formalism)

        # Perform translation
        result = await self.bridge.translate_nl_to_logic(
            request.input_text, target_formalism=target_formalism, session_id=request.session_id
        )

        response_data = {
            "input": request.input_text,
            "logical_representation": result.target_representation,
            "formalism": result.formalism.value,
            "confidence": result.confidence,
            "context": result.context,
            "metadata": result.metadata,
        }

        if include_explanation:
            response_data["explanation"] = result.explanations

        if result.ambiguities:
            response_data["ambiguities"] = result.ambiguities
            response_data["suggestions"] = [
                f"Consider clarifying: {amb}" for amb in result.ambiguities[:3]
            ]

        return response_data

    async def _process_logic_to_nl(self, request: QueryRequest) -> Dict[str, Any]:
        """Process logic to natural language translation request."""
        parameters = request.parameters
        source_formalism = parameters.get("source_formalism", LogicFormalism.FOL)
        target_language = parameters.get("target_language", "en")

        # Convert string to LogicFormalism if needed
        if isinstance(source_formalism, str):
            source_formalism = LogicFormalism(source_formalism)

        # Perform translation
        result = await self.bridge.translate_logic_to_nl(
            request.input_text,
            source_formalism=source_formalism,
            target_language=target_language,
            session_id=request.session_id,
        )

        response_data = {
            "input": request.input_text,
            "natural_language": result.target_representation,
            "source_formalism": result.formalism.value,
            "target_language": target_language,
            "confidence": result.confidence,
            "explanation": result.explanations,
            "metadata": result.metadata,
        }

        return response_data

    async def _process_bidirectional(self, request: QueryRequest) -> Dict[str, Any]:
        """Process bidirectional translation request."""
        parameters = request.parameters
        source_type = parameters.get("source_type", "natural_language")
        formalism = parameters.get("formalism", LogicFormalism.PLN)

        # Convert string to LogicFormalism if needed
        if isinstance(formalism, str):
            formalism = LogicFormalism(formalism)

        # Perform bidirectional translation
        forward_result, backward_result = await self.bridge.bidirectional_translate(
            request.input_text,
            source_type=source_type,
            target_formalism=formalism,
            session_id=request.session_id,
        )

        consistency_score = forward_result.metadata.get("consistency_score", 0.0)

        response_data = {
            "input": request.input_text,
            "forward_translation": forward_result.target_representation,
            "backward_translation": backward_result.target_representation,
            "consistency_score": consistency_score,
            "forward_confidence": forward_result.confidence,
            "backward_confidence": backward_result.confidence,
            "explanation": [
                f"Forward translation confidence: {forward_result.confidence:.2f}",
                f"Backward translation confidence: {backward_result.confidence:.2f}",
                f"Overall consistency: {consistency_score:.2f}",
            ],
            "metadata": {
                "forward_metadata": forward_result.metadata,
                "backward_metadata": backward_result.metadata,
            },
        }

        # Add interpretation of consistency
        if consistency_score > 0.8:
            response_data["suggestions"] = ["High consistency - translation appears reliable"]
        elif consistency_score > 0.6:
            response_data["suggestions"] = ["Moderate consistency - some information may be lost"]
        else:
            response_data["suggestions"] = [
                "Low consistency - consider rephrasing or using different formalism"
            ]

        return response_data

    async def _process_knowledge_query(self, request: QueryRequest) -> Dict[str, Any]:
        """Process knowledge base query request."""
        parameters = request.parameters
        query_type = parameters.get("query_type", "natural_language")
        max_results = parameters.get("max_results", 10)

        # Query the knowledge base
        result = await self.bridge.query_knowledge(
            request.input_text, query_type=query_type, session_id=request.session_id
        )

        response_data = {
            "query": request.input_text,
            "logical_query": result.get("logical_query", ""),
            "results": result.get("results", [])[:max_results],
            "explanations": result.get("explanations", []),
            "formalism": result.get("formalism", "unknown"),
            "confidence": 0.8,  # Default confidence for knowledge queries
            "metadata": {"total_results": len(result.get("results", []))},
        }

        if len(result.get("results", [])) == 0:
            response_data["suggestions"] = [
                "No matching results found. Try rephrasing your query.",
                "Consider using more specific terms.",
                "Check if the concept exists in the knowledge base.",
            ]

        return response_data

    async def _process_explanation_request(self, request: QueryRequest) -> Dict[str, Any]:
        """Process explanation request for a logical expression."""
        parameters = request.parameters
        formalism = parameters.get("formalism", LogicFormalism.FOL)

        if isinstance(formalism, str):
            formalism = LogicFormalism(formalism)

        # Generate explanations
        explanations = await self.bridge.explanation_generator.explain_logic(
            request.input_text, formalism, context={}
        )

        response_data = {
            "logical_expression": request.input_text,
            "formalism": formalism.value,
            "explanations": explanations,
            "confidence": 0.8,
            "metadata": {"explanation_count": len(explanations)},
        }

        return response_data

    async def _process_alternatives_request(self, request: QueryRequest) -> Dict[str, Any]:
        """Process request for alternative translations."""
        parameters = request.parameters
        formalism = parameters.get("formalism", LogicFormalism.PLN)
        max_alternatives = parameters.get("max_alternatives", 3)

        if isinstance(formalism, str):
            formalism = LogicFormalism(formalism)

        # Generate alternatives
        alternatives = await self.bridge.get_translation_alternatives(
            request.input_text, formalism, max_alternatives=max_alternatives
        )

        response_data = {
            "input": request.input_text,
            "alternatives": [
                {
                    "translation": alt.target_representation,
                    "confidence": alt.confidence,
                    "explanation": alt.explanations,
                }
                for alt in alternatives
            ],
            "confidence": alternatives[0].confidence if alternatives else 0.0,
            "metadata": {"alternatives_count": len(alternatives)},
        }

        return response_data

    async def _process_validation_request(self, request: QueryRequest) -> Dict[str, Any]:
        """Process logical expression validation request."""
        parameters = request.parameters
        formalism = parameters.get("formalism", LogicFormalism.FOL)

        if isinstance(formalism, str):
            formalism = LogicFormalism(formalism)

        # Validate expression
        is_valid = self.bridge.logic_systems.validate_expression(request.input_text, formalism)

        # Parse for additional information
        parsed = await self.bridge.logic_systems.parse_expression(request.input_text, formalism)

        response_data = {
            "expression": request.input_text,
            "formalism": formalism.value,
            "is_valid": is_valid,
            "parsed_components": parsed,
            "confidence": 1.0 if is_valid else 0.0,
            "explanation": [
                f"Expression is {'valid' if is_valid else 'invalid'} {formalism.value}"
            ],
        }

        if not is_valid:
            response_data["suggestions"] = [
                "Check syntax for the specified formalism",
                "Ensure all parentheses are balanced",
                "Verify that all symbols are valid for this logic type",
            ]

        return response_data

    async def _process_exploration_request(self, request: QueryRequest) -> Dict[str, Any]:
        """Process exploration request to discover relationships."""
        # This would implement more advanced exploration features
        # For now, provide a basic implementation

        response_data = {
            "query": request.input_text,
            "exploration_type": "basic",
            "findings": [
                "Exploration feature is under development",
                "This will provide advanced relationship discovery",
                "Check back for enhanced exploration capabilities",
            ],
            "confidence": 0.5,
            "metadata": {"feature_status": "development"},
        }

        return response_data

    def get_query_templates(self) -> Dict[QueryType, Dict[str, Any]]:
        """Get available query templates and examples."""
        return self.query_templates

    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get query history for a specific session."""
        session_queries = [q for q in self.query_history if q.session_id == session_id]

        session_responses = [
            r
            for r, q in zip(self.response_history, self.query_history)
            if q.session_id == session_id
        ]

        return {
            "session_id": session_id,
            "query_count": len(session_queries),
            "queries": [
                {
                    "query_id": q.query_id,
                    "query_type": q.query_type.value,
                    "input_text": q.input_text,
                    "timestamp": q.timestamp,
                    "success": r.success,
                    "confidence": r.confidence,
                    "processing_time": r.processing_time,
                }
                for q, r in zip(session_queries, session_responses)
            ],
        }

    def _update_stats(
        self, query_type: QueryType, processing_time: float, confidence: float, success: bool
    ):
        """Update interface statistics."""
        self.stats["total_queries"] += 1

        # Update query type counts
        type_key = query_type.value
        self.stats["queries_by_type"][type_key] = self.stats["queries_by_type"].get(type_key, 0) + 1

        # Update average processing time
        total_queries = self.stats["total_queries"]
        current_avg_time = self.stats["average_processing_time"]
        self.stats["average_processing_time"] = (
            current_avg_time * (total_queries - 1) + processing_time
        ) / total_queries

        # Update average confidence
        current_avg_conf = self.stats["average_confidence"]
        self.stats["average_confidence"] = (
            current_avg_conf * (total_queries - 1) + confidence
        ) / total_queries

        # Update success rate
        successful_queries = sum(1 for r in self.response_history if r.success)
        self.stats["success_rate"] = (
            successful_queries / total_queries if total_queries > 0 else 1.0
        )

    def _update_session_stats(
        self, session_id: str, request: QueryRequest, response: QueryResponse
    ):
        """Update statistics for a specific session."""
        if session_id not in self.session_stats:
            self.session_stats[session_id] = {
                "query_count": 0,
                "total_processing_time": 0.0,
                "average_confidence": 0.0,
                "success_count": 0,
                "query_types": {},
            }

        stats = self.session_stats[session_id]
        stats["query_count"] += 1
        stats["total_processing_time"] += response.processing_time

        if response.success:
            stats["success_count"] += 1

        # Update average confidence
        stats["average_confidence"] = (
            stats["average_confidence"] * (stats["query_count"] - 1) + response.confidence
        ) / stats["query_count"]

        # Update query type counts
        query_type_key = request.query_type.value
        stats["query_types"][query_type_key] = stats["query_types"].get(query_type_key, 0) + 1

    def get_interface_stats(self) -> Dict[str, Any]:
        """Get comprehensive interface statistics."""
        return {
            **self.stats,
            "active_sessions": len(self.session_stats),
            "total_sessions": len(set(q.session_id for q in self.query_history)),
            "recent_queries": len(
                [q for q in self.query_history if time.time() - q.timestamp < 3600]  # Last hour
            ),
        }

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific session."""
        return self.session_stats.get(session_id, {"error": "Session not found"})

    async def suggest_queries(self, partial_input: str, session_id: str) -> List[Dict[str, Any]]:
        """Suggest queries based on partial input and session history."""
        suggestions = []

        # Get session history for context
        session_queries = [q for q in self.query_history if q.session_id == session_id]

        # Basic suggestions based on partial input
        if "all" in partial_input.lower():
            suggestions.append(
                {
                    "query": "All birds can fly",
                    "type": QueryType.NL_TO_LOGIC.value,
                    "description": "Universal quantification example",
                }
            )

        if "if" in partial_input.lower():
            suggestions.append(
                {
                    "query": "If it rains, then the ground gets wet",
                    "type": QueryType.NL_TO_LOGIC.value,
                    "description": "Conditional statement example",
                }
            )

        if "∀" in partial_input or "∃" in partial_input:
            suggestions.append(
                {
                    "query": partial_input,
                    "type": QueryType.LOGIC_TO_NL.value,
                    "description": "Convert FOL to natural language",
                }
            )

        # Add template examples if no specific suggestions
        if not suggestions:
            for query_type, template in self.query_templates.items():
                if template["examples"]:
                    suggestions.append(
                        {
                            "query": template["examples"][0],
                            "type": query_type.value,
                            "description": template["description"],
                        }
                    )

        return suggestions[:5]  # Return top 5 suggestions
