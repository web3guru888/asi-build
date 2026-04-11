"""
Main NL-Logic Bridge system implementing Ben Goertzel's symbolic-neural AGI vision.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time

from ..parsers.semantic_parser import SemanticParser
from ..parsers.pln_extractor import PLNExtractor
from ..generators.explanation_generator import ExplanationGenerator
from ..generators.nl_generator import NLGenerator
from ..knowledge.commonsense import CommonsenseReasoner
from ..knowledge.graph_builder import KnowledgeGraphBuilder
from ..models.transformer_models import TransformerModels
from .context_manager import ContextManager
from .logic_systems import LogicSystems


class LogicFormalism(Enum):
    """Supported logic formalisms."""
    FOL = "first_order_logic"
    PLN = "probabilistic_logic_networks"
    TEMPORAL = "temporal_logic"
    MODAL = "modal_logic"
    DESCRIPTION = "description_logic"
    FUZZY = "fuzzy_logic"


@dataclass
class TranslationResult:
    """Result of NL-Logic translation."""
    source_text: str
    target_representation: str
    formalism: LogicFormalism
    confidence: float
    context: Dict[str, Any]
    ambiguities: List[str]
    explanations: List[str]
    metadata: Dict[str, Any]


@dataclass
class BridgeConfig:
    """Configuration for the NL-Logic Bridge."""
    default_formalism: LogicFormalism = LogicFormalism.PLN
    enable_commonsense: bool = True
    enable_multilingual: bool = True
    confidence_threshold: float = 0.7
    max_ambiguity_alternatives: int = 5
    context_window_size: int = 1000
    enable_real_time: bool = True
    debug_mode: bool = False


class NLLogicBridge:
    """
    Main Natural Language ↔ Logic Bridge system.
    
    This class orchestrates the entire translation pipeline between natural
    language and formal logical representations, implementing Ben Goertzel's
    vision for symbolic-neural AGI integration.
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        """Initialize the NL-Logic Bridge."""
        self.config = config or BridgeConfig()
        self.logger = self._setup_logger()
        
        # Core components
        self.semantic_parser = SemanticParser()
        self.pln_extractor = PLNExtractor()
        self.explanation_generator = ExplanationGenerator()
        self.nl_generator = NLGenerator()
        self.commonsense_reasoner = CommonsenseReasoner()
        self.graph_builder = KnowledgeGraphBuilder()
        self.transformer_models = TransformerModels()
        self.context_manager = ContextManager()
        self.logic_systems = LogicSystems()
        
        # State management
        self.session_context = {}
        self.translation_history = []
        self.active_sessions = {}
        
        self.logger.info("NL-Logic Bridge initialized successfully")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the bridge system."""
        logger = logging.getLogger("nl_logic_bridge")
        logger.setLevel(logging.DEBUG if self.config.debug_mode else logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def translate_nl_to_logic(
        self,
        text: str,
        target_formalism: Optional[LogicFormalism] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate natural language to logical representation.
        
        Args:
            text: Natural language input
            target_formalism: Target logic formalism
            context: Additional context information
            session_id: Session identifier for context continuity
            
        Returns:
            TranslationResult with logical representation and metadata
        """
        start_time = time.time()
        formalism = target_formalism or self.config.default_formalism
        
        try:
            # Update session context
            if session_id:
                self.context_manager.update_session_context(session_id, text, context)
                session_context = self.context_manager.get_session_context(session_id)
            else:
                session_context = context or {}
            
            # Parse semantic structure
            semantic_parse = await self.semantic_parser.parse(text, session_context)
            
            # Extract logical rules (PLN-specific)
            if formalism == LogicFormalism.PLN:
                pln_rules = await self.pln_extractor.extract_rules(text, semantic_parse)
            else:
                pln_rules = []
            
            # Apply commonsense reasoning if enabled
            if self.config.enable_commonsense:
                commonsense_context = await self.commonsense_reasoner.enhance_context(
                    text, semantic_parse, session_context
                )
                session_context.update(commonsense_context)
            
            # Convert to target logical formalism
            logical_representation = await self.logic_systems.convert_to_formalism(
                semantic_parse, formalism, pln_rules, session_context
            )
            
            # Detect and resolve ambiguities
            ambiguities = await self._detect_ambiguities(text, semantic_parse)
            resolved_ambiguities = await self._resolve_ambiguities(
                ambiguities, session_context
            )
            
            # Generate explanations
            explanations = await self.explanation_generator.generate_explanations(
                text, logical_representation, formalism, session_context
            )
            
            # Calculate confidence
            confidence = await self._calculate_confidence(
                text, semantic_parse, logical_representation, ambiguities
            )
            
            result = TranslationResult(
                source_text=text,
                target_representation=logical_representation,
                formalism=formalism,
                confidence=confidence,
                context=session_context,
                ambiguities=resolved_ambiguities,
                explanations=explanations,
                metadata={
                    "processing_time": time.time() - start_time,
                    "semantic_parse": semantic_parse,
                    "pln_rules": pln_rules,
                    "session_id": session_id
                }
            )
            
            # Update translation history
            self.translation_history.append(result)
            
            self.logger.info(f"Successfully translated NL to {formalism.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in NL to logic translation: {str(e)}")
            raise
    
    async def translate_logic_to_nl(
        self,
        logical_expression: str,
        source_formalism: LogicFormalism,
        target_language: str = "en",
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate logical representation to natural language.
        
        Args:
            logical_expression: Logical expression to translate
            source_formalism: Source logic formalism
            target_language: Target natural language (ISO code)
            context: Additional context information
            session_id: Session identifier for context continuity
            
        Returns:
            TranslationResult with natural language representation
        """
        start_time = time.time()
        
        try:
            # Update session context
            if session_id:
                self.context_manager.update_session_context(
                    session_id, logical_expression, context
                )
                session_context = self.context_manager.get_session_context(session_id)
            else:
                session_context = context or {}
            
            # Parse logical expression
            parsed_logic = await self.logic_systems.parse_expression(
                logical_expression, source_formalism
            )
            
            # Generate natural language
            nl_text = await self.nl_generator.generate(
                parsed_logic, source_formalism, target_language, session_context
            )
            
            # Generate explanations for the logical structure
            explanations = await self.explanation_generator.explain_logic(
                logical_expression, source_formalism, session_context
            )
            
            # Calculate confidence
            confidence = await self._calculate_logic_to_nl_confidence(
                logical_expression, nl_text, source_formalism
            )
            
            result = TranslationResult(
                source_text=logical_expression,
                target_representation=nl_text,
                formalism=source_formalism,
                confidence=confidence,
                context=session_context,
                ambiguities=[],  # Logic to NL typically has fewer ambiguities
                explanations=explanations,
                metadata={
                    "processing_time": time.time() - start_time,
                    "parsed_logic": parsed_logic,
                    "target_language": target_language,
                    "session_id": session_id
                }
            )
            
            # Update translation history
            self.translation_history.append(result)
            
            self.logger.info(f"Successfully translated {source_formalism.value} to NL")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in logic to NL translation: {str(e)}")
            raise
    
    async def bidirectional_translate(
        self,
        input_text: str,
        source_type: str,  # "natural_language" or "logical"
        source_formalism: Optional[LogicFormalism] = None,
        target_formalism: Optional[LogicFormalism] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Tuple[TranslationResult, TranslationResult]:
        """
        Perform bidirectional translation to verify consistency.
        
        Args:
            input_text: Input text or logical expression
            source_type: Type of input ("natural_language" or "logical")
            source_formalism: Source logic formalism (if logical input)
            target_formalism: Target logic formalism (if NL input)
            context: Additional context
            session_id: Session identifier
            
        Returns:
            Tuple of (forward_result, backward_result)
        """
        try:
            if source_type == "natural_language":
                # NL -> Logic -> NL
                forward_result = await self.translate_nl_to_logic(
                    input_text, target_formalism, context, session_id
                )
                backward_result = await self.translate_logic_to_nl(
                    forward_result.target_representation,
                    forward_result.formalism,
                    context=context,
                    session_id=session_id
                )
            else:
                # Logic -> NL -> Logic
                forward_result = await self.translate_logic_to_nl(
                    input_text, source_formalism, context=context, session_id=session_id
                )
                backward_result = await self.translate_nl_to_logic(
                    forward_result.target_representation,
                    source_formalism,
                    context,
                    session_id
                )
            
            # Calculate consistency score
            consistency_score = await self._calculate_consistency(
                input_text, forward_result, backward_result
            )
            
            # Add consistency metadata
            forward_result.metadata["consistency_score"] = consistency_score
            backward_result.metadata["consistency_score"] = consistency_score
            
            self.logger.info(f"Bidirectional translation completed with consistency: {consistency_score}")
            return forward_result, backward_result
            
        except Exception as e:
            self.logger.error(f"Error in bidirectional translation: {str(e)}")
            raise
    
    async def build_knowledge_graph(
        self,
        texts: List[str],
        formalism: Optional[LogicFormalism] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from natural language texts.
        
        Args:
            texts: List of natural language texts
            formalism: Target logic formalism
            session_id: Session identifier
            
        Returns:
            Knowledge graph structure
        """
        try:
            # Translate all texts to logical representations
            logical_representations = []
            for text in texts:
                result = await self.translate_nl_to_logic(
                    text, formalism, session_id=session_id
                )
                logical_representations.append(result)
            
            # Build knowledge graph
            knowledge_graph = await self.graph_builder.build_graph(
                logical_representations, formalism or self.config.default_formalism
            )
            
            self.logger.info(f"Built knowledge graph from {len(texts)} texts")
            return knowledge_graph
            
        except Exception as e:
            self.logger.error(f"Error building knowledge graph: {str(e)}")
            raise
    
    async def query_knowledge(
        self,
        query: str,
        query_type: str = "natural_language",
        formalism: Optional[LogicFormalism] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the knowledge base using natural language or logical expressions.
        
        Args:
            query: Query text or logical expression
            query_type: "natural_language" or "logical"
            formalism: Logic formalism for logical queries
            session_id: Session identifier
            
        Returns:
            Query results with explanations
        """
        try:
            if query_type == "natural_language":
                # Convert NL query to logical form
                query_result = await self.translate_nl_to_logic(
                    query, formalism, session_id=session_id
                )
                logical_query = query_result.target_representation
            else:
                logical_query = query
                formalism = formalism or self.config.default_formalism
            
            # Execute query against knowledge base
            results = await self.graph_builder.query_graph(logical_query, formalism)
            
            # Generate natural language explanations
            explanations = await self.explanation_generator.explain_query_results(
                query, results, formalism
            )
            
            return {
                "query": query,
                "logical_query": logical_query,
                "results": results,
                "explanations": explanations,
                "formalism": formalism.value if formalism else None
            }
            
        except Exception as e:
            self.logger.error(f"Error querying knowledge: {str(e)}")
            raise
    
    async def get_translation_alternatives(
        self,
        text: str,
        formalism: LogicFormalism,
        max_alternatives: Optional[int] = None
    ) -> List[TranslationResult]:
        """
        Get multiple alternative translations for ambiguous input.
        
        Args:
            text: Input text
            formalism: Target logic formalism
            max_alternatives: Maximum number of alternatives
            
        Returns:
            List of alternative translation results
        """
        max_alts = max_alternatives or self.config.max_ambiguity_alternatives
        
        try:
            # Generate multiple semantic parses
            alternative_parses = await self.semantic_parser.generate_alternatives(
                text, max_alts
            )
            
            alternatives = []
            for parse in alternative_parses:
                # Convert each parse to logical representation
                logical_rep = await self.logic_systems.convert_to_formalism(
                    parse, formalism, [], {}
                )
                
                # Calculate confidence for this alternative
                confidence = await self._calculate_confidence(text, parse, logical_rep, [])
                
                result = TranslationResult(
                    source_text=text,
                    target_representation=logical_rep,
                    formalism=formalism,
                    confidence=confidence,
                    context={},
                    ambiguities=[],
                    explanations=[],
                    metadata={"alternative_parse": parse}
                )
                alternatives.append(result)
            
            # Sort by confidence
            alternatives.sort(key=lambda x: x.confidence, reverse=True)
            
            self.logger.info(f"Generated {len(alternatives)} translation alternatives")
            return alternatives
            
        except Exception as e:
            self.logger.error(f"Error generating alternatives: {str(e)}")
            raise
    
    async def _detect_ambiguities(
        self,
        text: str,
        semantic_parse: Dict[str, Any]
    ) -> List[str]:
        """Detect potential ambiguities in the input."""
        ambiguities = []
        
        # Syntactic ambiguities
        if "ambiguous_attachments" in semantic_parse:
            ambiguities.extend(semantic_parse["ambiguous_attachments"])
        
        # Semantic ambiguities
        if "polysemous_words" in semantic_parse:
            ambiguities.extend(semantic_parse["polysemous_words"])
        
        # Scope ambiguities
        if "scope_ambiguities" in semantic_parse:
            ambiguities.extend(semantic_parse["scope_ambiguities"])
        
        return ambiguities
    
    async def _resolve_ambiguities(
        self,
        ambiguities: List[str],
        context: Dict[str, Any]
    ) -> List[str]:
        """Resolve ambiguities using context and commonsense reasoning."""
        resolved = []
        
        for ambiguity in ambiguities:
            if self.config.enable_commonsense:
                resolution = await self.commonsense_reasoner.resolve_ambiguity(
                    ambiguity, context
                )
                resolved.append(resolution)
            else:
                resolved.append(f"Unresolved: {ambiguity}")
        
        return resolved
    
    async def _calculate_confidence(
        self,
        text: str,
        semantic_parse: Dict[str, Any],
        logical_representation: str,
        ambiguities: List[str]
    ) -> float:
        """Calculate confidence score for the translation."""
        base_confidence = 0.8
        
        # Reduce confidence based on ambiguities
        ambiguity_penalty = len(ambiguities) * 0.1
        
        # Reduce confidence for complex semantic structures
        complexity_penalty = semantic_parse.get("complexity_score", 0) * 0.05
        
        # Reduce confidence for very long inputs
        length_penalty = max(0, (len(text) - 100) / 1000 * 0.1)
        
        confidence = base_confidence - ambiguity_penalty - complexity_penalty - length_penalty
        return max(0.1, min(1.0, confidence))
    
    async def _calculate_logic_to_nl_confidence(
        self,
        logical_expression: str,
        nl_text: str,
        formalism: LogicFormalism
    ) -> float:
        """Calculate confidence for logic to NL translation."""
        base_confidence = 0.85  # Generally higher than NL to logic
        
        # Reduce confidence for complex logical expressions
        complexity_penalty = len(logical_expression.split()) / 100 * 0.1
        
        confidence = base_confidence - complexity_penalty
        return max(0.1, min(1.0, confidence))
    
    async def _calculate_consistency(
        self,
        original: str,
        forward_result: TranslationResult,
        backward_result: TranslationResult
    ) -> float:
        """Calculate consistency score for bidirectional translation."""
        # Simple text similarity for now - could be enhanced with semantic similarity
        original_words = set(original.lower().split())
        final_words = set(backward_result.target_representation.lower().split())
        
        if not original_words:
            return 0.0
        
        intersection = original_words.intersection(final_words)
        union = original_words.union(final_words)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Adjust based on confidence scores
        avg_confidence = (forward_result.confidence + backward_result.confidence) / 2
        
        return (jaccard_similarity + avg_confidence) / 2
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific session."""
        session_history = [
            result for result in self.translation_history
            if result.metadata.get("session_id") == session_id
        ]
        
        if not session_history:
            return {"error": "Session not found"}
        
        total_translations = len(session_history)
        avg_confidence = sum(r.confidence for r in session_history) / total_translations
        avg_processing_time = sum(
            r.metadata.get("processing_time", 0) for r in session_history
        ) / total_translations
        
        formalisms_used = list(set(r.formalism.value for r in session_history))
        
        return {
            "session_id": session_id,
            "total_translations": total_translations,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "formalisms_used": formalisms_used,
            "context_size": len(self.context_manager.get_session_context(session_id))
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        if not self.translation_history:
            return {"total_translations": 0}
        
        total_translations = len(self.translation_history)
        avg_confidence = sum(r.confidence for r in self.translation_history) / total_translations
        avg_processing_time = sum(
            r.metadata.get("processing_time", 0) for r in self.translation_history
        ) / total_translations
        
        formalism_counts = {}
        for result in self.translation_history:
            formalism = result.formalism.value
            formalism_counts[formalism] = formalism_counts.get(formalism, 0) + 1
        
        return {
            "total_translations": total_translations,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_processing_time,
            "formalism_distribution": formalism_counts,
            "active_sessions": len(self.active_sessions),
            "high_confidence_rate": len([
                r for r in self.translation_history 
                if r.confidence >= self.config.confidence_threshold
            ]) / total_translations
        }