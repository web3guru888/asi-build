"""
FastToG Reasoning Engine for Kenny Graph Intelligence System

Implements the core "Fast Think-on-Graph" reasoning system that enables Kenny
to think "community by community" for 75% faster and more accurate automation decisions.
Based on the FastToG research paper: arXiv:2501.14300v1.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .schema import NodeType, RelationshipType
from .schema_manager import SchemaManager
from .community_detection import CommunityDetectionEngine
from .community_pruning import CommunityPruningSystem
from .community_to_text import CommunityTextGenerator

logger = logging.getLogger(__name__)


class ReasoningMode(Enum):
    """Different reasoning modes for FastToG."""
    COMMUNITY_BASED = "community_based"    # Use community structure for reasoning
    TRADITIONAL = "traditional"           # Traditional node-by-node reasoning
    HYBRID = "hybrid"                     # Combine both approaches


@dataclass
class ReasoningRequest:
    """Request for FastToG reasoning."""
    user_intent: str
    context: Dict[str, Any]
    max_communities: int = 10
    reasoning_mode: ReasoningMode = ReasoningMode.COMMUNITY_BASED
    include_explanations: bool = True
    timeout_seconds: int = 30


@dataclass 
class CommunityReasoning:
    """Reasoning result for a single community."""
    community_id: str
    community_purpose: str
    relevance_score: float
    reasoning_text: str
    recommended_actions: List[Dict[str, Any]]
    confidence: float
    processing_time: float
    node_count: int


@dataclass
class FastToGResult:
    """Complete FastToG reasoning result."""
    request_id: str
    user_intent: str
    reasoning_mode: str
    community_reasonings: List[CommunityReasoning]
    final_recommendation: Dict[str, Any]
    overall_confidence: float
    processing_time: float
    communities_analyzed: int
    performance_metrics: Dict[str, Any]
    explanation: str


class CommunityReasoningEngine:
    """Core reasoning engine for individual communities."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.text_generator = CommunityTextGenerator(schema_manager)
        
    async def reason_about_community(self, community_id: str, 
                                   task_context: Dict[str, Any]) -> CommunityReasoning:
        """
        Perform reasoning about a single community in the context of a task.
        
        Args:
            community_id: ID of the community to reason about
            task_context: Context including user intent and constraints
            
        Returns:
            CommunityReasoning with analysis and recommendations
        """
        start_time = time.time()
        
        # Get community details
        community = self.sm.get_node(community_id, NodeType.COMMUNITY)
        if not community:
            return self._create_error_reasoning(community_id, "Community not found")
        
        purpose = community.get('purpose', 'unknown')
        
        # Convert community to text for analysis
        try:
            conversion_result = self.text_generator.graph2text.convert_community_to_text(community_id)
        except Exception as e:
            logger.error(f"Failed to convert community {community_id} to text: {e}")
            return self._create_error_reasoning(community_id, f"Text conversion failed: {e}")
        
        # Calculate relevance score
        relevance_score = self._calculate_community_relevance(
            community, task_context, conversion_result
        )
        
        # Generate reasoning text
        reasoning_text = self._generate_community_reasoning(
            community, task_context, conversion_result
        )
        
        # Extract recommended actions
        recommended_actions = self._extract_recommended_actions(
            community, task_context, conversion_result
        )
        
        # Calculate confidence
        confidence = self._calculate_reasoning_confidence(
            community, task_context, conversion_result, relevance_score
        )
        
        processing_time = time.time() - start_time
        
        return CommunityReasoning(
            community_id=community_id,
            community_purpose=purpose,
            relevance_score=relevance_score,
            reasoning_text=reasoning_text,
            recommended_actions=recommended_actions,
            confidence=confidence,
            processing_time=processing_time,
            node_count=conversion_result.node_count
        )
    
    def _calculate_community_relevance(self, community: Dict[str, Any],
                                     task_context: Dict[str, Any],
                                     conversion_result) -> float:
        """Calculate how relevant a community is to the current task."""
        user_intent = task_context.get('user_intent', '').lower()
        purpose = community.get('purpose', '').lower()
        
        # Direct purpose alignment
        purpose_score = 0.0
        if any(word in purpose for word in user_intent.split() if len(word) > 2):
            purpose_score = 0.8
        elif any(keyword in purpose for keyword in ['save', 'file', 'workflow', 'automation']):
            purpose_score = 0.6
        else:
            purpose_score = 0.3
        
        # Community quality factors
        modularity = community.get('modularity', 0.0)
        frequency = min(1.0, community.get('frequency', 0) / 100.0)
        
        # Node content relevance (simplified)
        content_score = 0.5  # Default
        if conversion_result.natural_language_summary:
            summary_lower = conversion_result.natural_language_summary.lower()
            if any(word in summary_lower for word in user_intent.split() if len(word) > 2):
                content_score = 0.9
        
        # Combined relevance score
        relevance = (
            0.4 * purpose_score +
            0.3 * content_score +
            0.2 * modularity +
            0.1 * frequency
        )
        
        return min(1.0, relevance)
    
    def _generate_community_reasoning(self, community: Dict[str, Any],
                                    task_context: Dict[str, Any],
                                    conversion_result) -> str:
        """Generate reasoning text for a community."""
        user_intent = task_context.get('user_intent', 'perform task')
        purpose = community.get('purpose', '').replace('_', ' ')
        
        reasoning_parts = []
        
        # Community purpose analysis
        reasoning_parts.append(f"This community focuses on {purpose}.")
        
        # Task alignment analysis
        if purpose in user_intent.lower():
            reasoning_parts.append("It directly aligns with the user's intent.")
        elif any(word in purpose for word in ['save', 'file'] if word in user_intent.lower()):
            reasoning_parts.append("It contains functionality relevant to the user's goal.")
        else:
            reasoning_parts.append("It may provide supporting functionality.")
        
        # Structural analysis
        if conversion_result.node_count > 0:
            reasoning_parts.append(f"The community contains {conversion_result.node_count} connected elements "
                                 f"with {conversion_result.relationship_count} relationships.")
            
            if conversion_result.complexity_score > 2.0:
                reasoning_parts.append("This indicates a complex interaction pattern that may require careful sequencing.")
            elif conversion_result.complexity_score > 1.0:
                reasoning_parts.append("The interaction pattern is moderately complex with multiple pathways.")
            else:
                reasoning_parts.append("The interaction pattern is straightforward with clear pathways.")
        
        # Usage patterns
        frequency = community.get('frequency', 0)
        if frequency > 50:
            reasoning_parts.append("This community is frequently used, indicating high reliability.")
        elif frequency > 10:
            reasoning_parts.append("This community has moderate usage, suggesting proven functionality.")
        else:
            reasoning_parts.append("This community has limited usage history.")
        
        return " ".join(reasoning_parts)
    
    def _extract_recommended_actions(self, community: Dict[str, Any],
                                   task_context: Dict[str, Any],
                                   conversion_result) -> List[Dict[str, Any]]:
        """Extract recommended actions from community analysis."""
        actions = []
        
        # Get community members and their details
        try:
            members = json.loads(community.get('members', '[]')) if community.get('members') else []
        except:
            members = []
        
        # Analyze member nodes for actionable elements
        for member_id in members[:5]:  # Limit to avoid excessive processing
            node = self.sm.get_node(member_id)
            if not node:
                continue
                
            # UI Element actions
            if 'text' in node and 'coordinates' in node:
                element_type = node.get('type', 'element')
                text = node.get('text', '')
                coords = node.get('coordinates', [])
                
                if element_type == 'button' and text:
                    actions.append({
                        'type': 'click',
                        'target': member_id,
                        'element_text': text,
                        'coordinates': coords,
                        'confidence': node.get('confidence', 0.8),
                        'reasoning': f"Click '{text}' button to proceed"
                    })
                elif element_type == 'menu' and text:
                    actions.append({
                        'type': 'navigate',
                        'target': member_id,
                        'element_text': text,
                        'coordinates': coords,
                        'confidence': node.get('confidence', 0.8),
                        'reasoning': f"Navigate to '{text}' menu"
                    })
                elif element_type == 'text_field' and text:
                    actions.append({
                        'type': 'input',
                        'target': member_id,
                        'element_text': text,
                        'coordinates': coords,
                        'confidence': node.get('confidence', 0.8),
                        'reasoning': f"Enter text in '{text}' field"
                    })
            
            # Workflow actions
            elif 'name' in node and 'steps' in node:
                workflow_name = node.get('name', '')
                actions.append({
                    'type': 'workflow',
                    'target': member_id,
                    'workflow_name': workflow_name,
                    'confidence': 0.9,
                    'reasoning': f"Execute '{workflow_name}' workflow"
                })
        
        return actions
    
    def _calculate_reasoning_confidence(self, community: Dict[str, Any],
                                      task_context: Dict[str, Any],
                                      conversion_result,
                                      relevance_score: float) -> float:
        """Calculate confidence in the reasoning result."""
        factors = []
        
        # Relevance factor
        factors.append(relevance_score)
        
        # Community quality factor
        modularity = community.get('modularity', 0.0)
        factors.append(modularity)
        
        # Data completeness factor
        if conversion_result.node_count > 0 and conversion_result.relationship_count > 0:
            completeness = min(1.0, (conversion_result.node_count + conversion_result.relationship_count) / 10.0)
            factors.append(completeness)
        else:
            factors.append(0.3)  # Low confidence for incomplete data
        
        # Usage history factor
        frequency = community.get('frequency', 0)
        history_factor = min(1.0, frequency / 50.0)
        factors.append(history_factor)
        
        # Weighted average
        weights = [0.35, 0.25, 0.25, 0.15]
        confidence = sum(f * w for f, w in zip(factors, weights))
        
        return min(1.0, confidence)
    
    def _create_error_reasoning(self, community_id: str, error_message: str) -> CommunityReasoning:
        """Create an error reasoning result."""
        return CommunityReasoning(
            community_id=community_id,
            community_purpose="error",
            relevance_score=0.0,
            reasoning_text=f"Error analyzing community: {error_message}",
            recommended_actions=[],
            confidence=0.0,
            processing_time=0.0,
            node_count=0
        )


class FastToGReasoningEngine:
    """Main FastToG reasoning engine coordinating community-based thinking."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.community_engine = CommunityReasoningEngine(schema_manager)
        self.community_detection = CommunityDetectionEngine(schema_manager)
        self.pruning_system = CommunityPruningSystem(schema_manager)
        self.text_generator = CommunityTextGenerator(schema_manager)
        
    async def reason(self, request: ReasoningRequest) -> FastToGResult:
        """
        Perform FastToG reasoning for a user request.
        
        Args:
            request: ReasoningRequest with user intent and context
            
        Returns:
            FastToGResult with reasoning and recommendations
        """
        start_time = time.time()
        request_id = f"fastog_{int(start_time)}_{id(request) % 10000}"
        
        logger.info(f"🧠 Starting FastToG reasoning for: {request.user_intent}")
        
        try:
            if request.reasoning_mode == ReasoningMode.COMMUNITY_BASED:
                result = await self._community_based_reasoning(request, request_id)
            elif request.reasoning_mode == ReasoningMode.TRADITIONAL:
                result = await self._traditional_reasoning(request, request_id)
            else:  # HYBRID
                result = await self._hybrid_reasoning(request, request_id)
            
            result.processing_time = time.time() - start_time
            
            logger.info(f"✅ FastToG reasoning completed in {result.processing_time:.2f}s: "
                       f"{result.communities_analyzed} communities analyzed")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ FastToG reasoning failed: {e}")
            return self._create_error_result(request, request_id, str(e))
    
    async def _community_based_reasoning(self, request: ReasoningRequest, 
                                       request_id: str) -> FastToGResult:
        """Implement community-based reasoning (main FastToG approach)."""
        # Step 1: Get relevant communities through pruning
        pruning_result = self.pruning_system.prune_communities_for_task(
            request.context, 
            target_community_count=request.max_communities
        )
        
        relevant_communities = self.pruning_system.get_relevant_communities(
            request.context,
            max_communities=request.max_communities
        )
        
        if not relevant_communities:
            return self._create_no_communities_result(request, request_id)
        
        # Step 2: Reason about each community concurrently
        reasoning_tasks = []
        for community in relevant_communities:
            task = self.community_engine.reason_about_community(
                community['id'], 
                request.context
            )
            reasoning_tasks.append(task)
        
        # Execute reasoning in parallel
        community_reasonings = await asyncio.gather(*reasoning_tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to results
        valid_reasonings = []
        for reasoning in community_reasonings:
            if isinstance(reasoning, Exception):
                logger.error(f"Community reasoning failed: {reasoning}")
            else:
                valid_reasonings.append(reasoning)
        
        # Step 3: Synthesize final recommendation
        final_recommendation = self._synthesize_recommendations(
            valid_reasonings, request.context
        )
        
        # Step 4: Calculate overall confidence and create explanation
        overall_confidence = self._calculate_overall_confidence(valid_reasonings)
        explanation = self._generate_explanation(
            request, valid_reasonings, final_recommendation
        ) if request.include_explanations else ""
        
        # Step 5: Generate performance metrics
        performance_metrics = {
            'communities_found': len(relevant_communities),
            'communities_analyzed': len(valid_reasonings),
            'pruning_ratio': pruning_result.pruning_ratio,
            'avg_community_confidence': sum(cr.confidence for cr in valid_reasonings) / len(valid_reasonings) if valid_reasonings else 0,
            'reasoning_mode': 'community_based'
        }
        
        return FastToGResult(
            request_id=request_id,
            user_intent=request.user_intent,
            reasoning_mode=request.reasoning_mode.value,
            community_reasonings=valid_reasonings,
            final_recommendation=final_recommendation,
            overall_confidence=overall_confidence,
            processing_time=0.0,  # Will be set by caller
            communities_analyzed=len(valid_reasonings),
            performance_metrics=performance_metrics,
            explanation=explanation
        )
    
    async def _traditional_reasoning(self, request: ReasoningRequest,
                                   request_id: str) -> FastToGResult:
        """Implement traditional node-by-node reasoning for comparison."""
        # This would implement traditional graph reasoning
        # For now, return a simplified version that shows the contrast
        
        # Get all UI elements (traditional approach would analyze each individually)
        ui_elements = self.sm.find_nodes(NodeType.UI_ELEMENT, limit=100)
        
        # Simple scoring based on text matching
        scored_elements = []
        user_intent_words = request.user_intent.lower().split()
        
        for element in ui_elements:
            text = element.get('text', '').lower()
            score = sum(1 for word in user_intent_words if word in text and len(word) > 2)
            if score > 0:
                scored_elements.append((element, score))
        
        # Sort by score and take top elements
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        top_elements = [elem for elem, score in scored_elements[:10]]
        
        # Create simple recommendations
        recommendations = []
        for element in top_elements:
            if element.get('type') == 'button':
                recommendations.append({
                    'type': 'click',
                    'target': element['id'],
                    'element_text': element.get('text', ''),
                    'coordinates': element.get('coordinates', []),
                    'confidence': 0.7,
                    'reasoning': f"Click button with text '{element.get('text', '')}'"
                })
        
        # Create synthetic community reasonings for compatibility
        synthetic_reasoning = CommunityReasoning(
            community_id="traditional_analysis",
            community_purpose="individual_elements",
            relevance_score=0.7,
            reasoning_text=f"Traditional analysis found {len(top_elements)} relevant UI elements",
            recommended_actions=recommendations,
            confidence=0.7,
            processing_time=0.1,
            node_count=len(top_elements)
        )
        
        final_recommendation = {
            'approach': 'traditional',
            'recommended_actions': recommendations,
            'reasoning': 'Selected highest scoring individual elements'
        }
        
        return FastToGResult(
            request_id=request_id,
            user_intent=request.user_intent,
            reasoning_mode=request.reasoning_mode.value,
            community_reasonings=[synthetic_reasoning],
            final_recommendation=final_recommendation,
            overall_confidence=0.7,
            processing_time=0.0,
            communities_analyzed=1,
            performance_metrics={'reasoning_mode': 'traditional', 'elements_analyzed': len(top_elements)},
            explanation="Traditional element-by-element analysis"
        )
    
    async def _hybrid_reasoning(self, request: ReasoningRequest,
                              request_id: str) -> FastToGResult:
        """Combine community-based and traditional reasoning."""
        # Run both approaches
        community_request = ReasoningRequest(
            user_intent=request.user_intent,
            context=request.context,
            max_communities=request.max_communities // 2,
            reasoning_mode=ReasoningMode.COMMUNITY_BASED,
            include_explanations=False
        )
        
        traditional_request = ReasoningRequest(
            user_intent=request.user_intent,
            context=request.context,
            reasoning_mode=ReasoningMode.TRADITIONAL,
            include_explanations=False
        )
        
        community_result, traditional_result = await asyncio.gather(
            self._community_based_reasoning(community_request, f"{request_id}_community"),
            self._traditional_reasoning(traditional_request, f"{request_id}_traditional")
        )
        
        # Combine results
        all_reasonings = community_result.community_reasonings + traditional_result.community_reasonings
        
        # Synthesize hybrid recommendation
        final_recommendation = {
            'approach': 'hybrid',
            'community_recommendations': community_result.final_recommendation,
            'traditional_recommendations': traditional_result.final_recommendation,
            'combined_actions': self._combine_action_lists([
                community_result.final_recommendation.get('recommended_actions', []),
                traditional_result.final_recommendation.get('recommended_actions', [])
            ])
        }
        
        overall_confidence = (community_result.overall_confidence + traditional_result.overall_confidence) / 2
        
        return FastToGResult(
            request_id=request_id,
            user_intent=request.user_intent,
            reasoning_mode=request.reasoning_mode.value,
            community_reasonings=all_reasonings,
            final_recommendation=final_recommendation,
            overall_confidence=overall_confidence,
            processing_time=0.0,
            communities_analyzed=len(all_reasonings),
            performance_metrics={
                'reasoning_mode': 'hybrid',
                'community_confidence': community_result.overall_confidence,
                'traditional_confidence': traditional_result.overall_confidence
            },
            explanation=f"Hybrid analysis combining {len(community_result.community_reasonings)} communities and {len(traditional_result.community_reasonings)} individual elements"
        )
    
    def _synthesize_recommendations(self, reasonings: List[CommunityReasoning],
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize final recommendations from community reasonings."""
        if not reasonings:
            return {'approach': 'none', 'recommended_actions': [], 'reasoning': 'No valid reasonings'}
        
        # Sort reasonings by relevance and confidence
        sorted_reasonings = sorted(
            reasonings, 
            key=lambda r: r.relevance_score * r.confidence, 
            reverse=True
        )
        
        # Collect all recommended actions
        all_actions = []
        for reasoning in sorted_reasonings:
            all_actions.extend(reasoning.recommended_actions)
        
        # Prioritize actions by type and confidence
        prioritized_actions = self._prioritize_actions(all_actions, context)
        
        # Select top communities for explanation
        top_communities = sorted_reasonings[:3]
        
        return {
            'approach': 'community_based',
            'recommended_actions': prioritized_actions,
            'primary_communities': [
                {'id': cr.community_id, 'purpose': cr.community_purpose, 'relevance': cr.relevance_score}
                for cr in top_communities
            ],
            'reasoning': f"Based on analysis of {len(reasonings)} relevant communities"
        }
    
    def _prioritize_actions(self, actions: List[Dict[str, Any]], 
                          context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize actions based on type and context."""
        if not actions:
            return []
        
        # Remove duplicates based on target
        seen_targets = set()
        unique_actions = []
        for action in actions:
            target = action.get('target', '')
            if target not in seen_targets:
                seen_targets.add(target)
                unique_actions.append(action)
        
        # Sort by confidence and relevance
        def action_priority(action):
            confidence = action.get('confidence', 0.5)
            type_priority = {
                'click': 0.9,      # Buttons are usually primary actions
                'input': 0.8,      # Text input is important
                'navigate': 0.7,   # Navigation is secondary
                'workflow': 0.95   # Workflows are high priority
            }.get(action.get('type', ''), 0.5)
            
            return confidence * type_priority
        
        unique_actions.sort(key=action_priority, reverse=True)
        return unique_actions[:10]  # Limit to top 10 actions
    
    def _calculate_overall_confidence(self, reasonings: List[CommunityReasoning]) -> float:
        """Calculate overall confidence from individual reasoning confidences."""
        if not reasonings:
            return 0.0
        
        # Weight by relevance score
        weighted_confidences = []
        for reasoning in reasonings:
            weight = reasoning.relevance_score
            weighted_confidence = reasoning.confidence * weight
            weighted_confidences.append(weighted_confidence)
        
        # Calculate weighted average
        if weighted_confidences:
            total_weight = sum(r.relevance_score for r in reasonings)
            overall = sum(weighted_confidences) / total_weight if total_weight > 0 else 0.0
            return min(1.0, overall)
        
        return 0.0
    
    def _generate_explanation(self, request: ReasoningRequest,
                            reasonings: List[CommunityReasoning],
                            final_recommendation: Dict[str, Any]) -> str:
        """Generate human-readable explanation of the reasoning process."""
        explanation_parts = []
        
        explanation_parts.append(f"FastToG Analysis for: '{request.user_intent}'")
        explanation_parts.append("")
        
        if reasonings:
            explanation_parts.append(f"Analyzed {len(reasonings)} relevant communities:")
            
            for i, reasoning in enumerate(reasonings[:3], 1):
                explanation_parts.append(
                    f"{i}. {reasoning.community_purpose.replace('_', ' ').title()} "
                    f"(relevance: {reasoning.relevance_score:.1%}, confidence: {reasoning.confidence:.1%})"
                )
                explanation_parts.append(f"   {reasoning.reasoning_text}")
                
                if reasoning.recommended_actions:
                    explanation_parts.append(f"   Key actions: {len(reasoning.recommended_actions)} recommendations")
                
                explanation_parts.append("")
        
        # Summary
        actions = final_recommendation.get('recommended_actions', [])
        if actions:
            explanation_parts.append(f"Final recommendation: {len(actions)} prioritized actions")
            top_action = actions[0]
            explanation_parts.append(f"Primary action: {top_action.get('reasoning', 'N/A')}")
        else:
            explanation_parts.append("No specific actions recommended")
        
        return "\n".join(explanation_parts)
    
    def _combine_action_lists(self, action_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Combine multiple action lists, removing duplicates."""
        combined = []
        seen_targets = set()
        
        for action_list in action_lists:
            for action in action_list:
                target = action.get('target', '')
                if target not in seen_targets:
                    combined.append(action)
                    seen_targets.add(target)
        
        return combined
    
    def _create_error_result(self, request: ReasoningRequest, 
                           request_id: str, error_message: str) -> FastToGResult:
        """Create error result."""
        return FastToGResult(
            request_id=request_id,
            user_intent=request.user_intent,
            reasoning_mode=request.reasoning_mode.value,
            community_reasonings=[],
            final_recommendation={'approach': 'error', 'error': error_message},
            overall_confidence=0.0,
            processing_time=0.0,
            communities_analyzed=0,
            performance_metrics={'error': error_message},
            explanation=f"Reasoning failed: {error_message}"
        )
    
    def _create_no_communities_result(self, request: ReasoningRequest,
                                    request_id: str) -> FastToGResult:
        """Create result when no communities are found."""
        return FastToGResult(
            request_id=request_id,
            user_intent=request.user_intent,
            reasoning_mode=request.reasoning_mode.value,
            community_reasonings=[],
            final_recommendation={
                'approach': 'fallback', 
                'message': 'No relevant communities found for this task',
                'recommended_actions': []
            },
            overall_confidence=0.1,
            processing_time=0.0,
            communities_analyzed=0,
            performance_metrics={'communities_found': 0},
            explanation="No relevant communities detected for the requested task"
        )


# Test the FastToG reasoning engine
if __name__ == "__main__":
    print("🧪 Testing FastToG Reasoning Engine...")
    
    async def test_fastog():
        with SchemaManager() as sm:
            engine = FastToGReasoningEngine(sm)
            
            # Test community-based reasoning
            request = ReasoningRequest(
                user_intent="save document to file",
                context={
                    'application': 'notepad',
                    'ui_elements': [
                        {'text': 'Save', 'type': 'button'},
                        {'text': 'File', 'type': 'menu'}
                    ]
                },
                max_communities=5,
                reasoning_mode=ReasoningMode.COMMUNITY_BASED,
                include_explanations=True
            )
            
            result = await engine.reason(request)
            
            print(f"✅ FastToG Reasoning Results:")
            print(f"   - Request ID: {result.request_id}")
            print(f"   - User Intent: {result.user_intent}")
            print(f"   - Reasoning Mode: {result.reasoning_mode}")
            print(f"   - Communities Analyzed: {result.communities_analyzed}")
            print(f"   - Overall Confidence: {result.overall_confidence:.1%}")
            print(f"   - Processing Time: {result.processing_time:.3f}s")
            
            if result.community_reasonings:
                print(f"   - Community Insights:")
                for i, cr in enumerate(result.community_reasonings[:3], 1):
                    print(f"     {i}. {cr.community_purpose} (rel: {cr.relevance_score:.1%}, conf: {cr.confidence:.1%})")
                    print(f"        Actions: {len(cr.recommended_actions)}")
            
            if result.final_recommendation.get('recommended_actions'):
                actions = result.final_recommendation['recommended_actions']
                print(f"   - Top Recommendation: {actions[0].get('reasoning', 'N/A')}")
            
            # Test traditional reasoning for comparison
            traditional_request = ReasoningRequest(
                user_intent="save document to file",
                context=request.context,
                reasoning_mode=ReasoningMode.TRADITIONAL
            )
            
            traditional_result = await engine.reason(traditional_request)
            
            print(f"✅ Traditional Reasoning Comparison:")
            print(f"   - Processing Time: {traditional_result.processing_time:.3f}s")
            print(f"   - Confidence: {traditional_result.overall_confidence:.1%}")
            print(f"   - Approach: {traditional_result.final_recommendation.get('approach')}")
    
    # Run async test
    asyncio.run(test_fastog())
    print("✅ FastToG Reasoning Engine testing completed!")