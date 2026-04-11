"""
Community Pruning System for Kenny Graph Intelligence System

Implements two-stage pruning for FastToG reasoning:
1. Modularity-based coarse pruning
2. LLM-based fine pruning

Based on FastToG research paper for efficient community-based reasoning.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
import time
import json
import numpy as np
from collections import defaultdict

from .schema import NodeType, RelationshipType
from .schema_manager import SchemaManager
from .community_detection import CommunityDetectionEngine

logger = logging.getLogger(__name__)


@dataclass
class PruningResult:
    """Result of community pruning operation."""
    original_communities: int
    pruned_communities: int
    pruning_ratio: float
    processing_time: float
    pruning_method: str
    quality_threshold: float
    retained_coverage: float  # Percentage of important relationships retained
    
    @property
    def original_count(self) -> int:
        """Alias for original_communities for backward compatibility."""
        return self.original_communities
    
    @property
    def pruned_count(self) -> int:
        """Alias for pruned_communities for backward compatibility."""
        return self.pruned_communities


@dataclass 
class CommunityScore:
    """Scoring metrics for community evaluation."""
    community_id: str
    relevance_score: float
    modularity_score: float
    frequency_score: float
    recency_score: float
    size_score: float
    combined_score: float
    reasoning: str


class ModularityPruner:
    """Coarse pruning based on modularity and graph metrics."""
    
    def __init__(self, modularity_threshold: float = 0.3, 
                 min_community_size: int = 2,
                 max_communities: int = 50):
        self.modularity_threshold = modularity_threshold
        self.min_community_size = min_community_size
        self.max_communities = max_communities
        
    def prune_communities(self, communities: List[Dict[str, Any]], 
                         context: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform modularity-based coarse pruning.
        
        Args:
            communities: List of community dictionaries
            context: Optional context for relevance scoring
            
        Returns:
            (pruned_communities, pruning_stats)
        """
        if not communities:
            return [], {"pruned_count": 0, "method": "modularity"}
        
        logger.info(f"🔍 Starting modularity-based pruning of {len(communities)} communities...")
        
        scored_communities = []
        
        for community in communities:
            score = self._calculate_community_score(community, context)
            scored_communities.append((community, score))
        
        # Sort by combined score (descending)
        scored_communities.sort(key=lambda x: x[1].combined_score, reverse=True)
        
        # Apply pruning criteria
        pruned_communities = []
        
        for community, score in scored_communities:
            # Size filter
            if len(community.get('members', [])) < self.min_community_size:
                continue
                
            # Modularity filter
            if score.modularity_score < self.modularity_threshold:
                continue
                
            # Max communities limit
            if len(pruned_communities) >= self.max_communities:
                break
                
            pruned_communities.append(community)
        
        pruning_stats = {
            "original_count": len(communities),
            "pruned_count": len(pruned_communities),
            "removed_count": len(communities) - len(pruned_communities),
            "pruning_ratio": 1 - (len(pruned_communities) / len(communities)) if communities else 0,
            "method": "modularity",
            "threshold": self.modularity_threshold
        }
        
        logger.info(f"✅ Modularity pruning: {len(communities)} → {len(pruned_communities)} communities "
                   f"({pruning_stats['pruning_ratio']:.2%} pruned)")
        
        return pruned_communities, pruning_stats
    
    def _calculate_community_score(self, community: Dict[str, Any], 
                                  context: Dict[str, Any] = None) -> CommunityScore:
        """Calculate comprehensive score for a community."""
        community_id = community.get('id', '')
        
        # Modularity score (from community detection)
        modularity = community.get('modularity', 0.0)
        
        # Size score (balanced - not too small, not too large)
        size = len(community.get('members', []))
        if size <= 1:
            size_score = 0.0
        elif size <= 5:
            size_score = size / 5.0  # Linear growth up to 5
        elif size <= 20:
            size_score = 1.0  # Optimal size range
        else:
            size_score = max(0.5, 1.0 - (size - 20) / 100.0)  # Penalty for very large
        
        # Frequency score (how often community is used)
        frequency = community.get('frequency', 0)
        frequency_score = min(1.0, frequency / 100.0)  # Normalize to 0-1
        
        # Recency score (based on community timestamp or member activity)
        current_time = time.time()
        community_time = community.get('timestamp', current_time)
        time_diff_hours = (current_time - community_time) / 3600.0
        
        if time_diff_hours < 24:
            recency_score = 1.0
        elif time_diff_hours < 168:  # 1 week
            recency_score = 0.8
        elif time_diff_hours < 720:  # 1 month
            recency_score = 0.5
        else:
            recency_score = 0.2
        
        # Relevance score (based on context if provided)
        relevance_score = 1.0  # Default
        if context:
            purpose = community.get('purpose', '')
            context_purpose = context.get('purpose', '')
            context_application = context.get('application', '')
            
            # Check purpose alignment
            if context_purpose and context_purpose in purpose:
                relevance_score = 1.0
            elif any(keyword in purpose for keyword in ['save', 'file', 'workflow']):
                relevance_score = 0.9  # Generally useful purposes
            else:
                relevance_score = 0.7
        
        # Combine scores with weights
        combined_score = (
            0.3 * modularity +           # Community quality
            0.2 * size_score +           # Optimal size
            0.2 * frequency_score +      # Usage frequency  
            0.15 * recency_score +       # Recent activity
            0.15 * relevance_score       # Context relevance
        )
        
        reasoning = f"mod:{modularity:.2f} size:{size_score:.2f} freq:{frequency_score:.2f} rec:{recency_score:.2f} rel:{relevance_score:.2f}"
        
        return CommunityScore(
            community_id=community_id,
            relevance_score=relevance_score,
            modularity_score=modularity,
            frequency_score=frequency_score,
            recency_score=recency_score,
            size_score=size_score,
            combined_score=combined_score,
            reasoning=reasoning
        )


class LLMFinePruner:
    """Fine pruning using LLM-based semantic analysis."""
    
    def __init__(self, max_communities_for_llm: int = 20,
                 semantic_threshold: float = 0.7):
        self.max_communities_for_llm = max_communities_for_llm
        self.semantic_threshold = semantic_threshold
        
    def prune_communities(self, communities: List[Dict[str, Any]], 
                         context: Dict[str, Any], 
                         schema_manager: SchemaManager) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Perform LLM-based fine pruning with semantic understanding.
        
        Args:
            communities: Pre-pruned communities from modularity stage
            context: Context for the current reasoning task
            schema_manager: For accessing node details
            
        Returns:
            (final_pruned_communities, pruning_stats)
        """
        if not communities or len(communities) <= self.max_communities_for_llm:
            logger.info(f"🔍 Skipping LLM pruning: {len(communities)} communities (under threshold)")
            return communities, {"method": "llm", "pruned_count": len(communities)}
        
        logger.info(f"🔍 Starting LLM-based fine pruning of {len(communities)} communities...")
        
        # Prepare community descriptions for LLM analysis
        community_descriptions = []
        for community in communities:
            description = self._create_community_description(community, schema_manager)
            community_descriptions.append(description)
        
        # Create prompt for LLM evaluation
        task_description = self._extract_task_description(context)
        evaluation_prompt = self._create_evaluation_prompt(
            community_descriptions, task_description, self.max_communities_for_llm
        )
        
        # Simulate LLM evaluation (in real implementation, would call Claude API)
        selected_indices = self._simulate_llm_selection(
            community_descriptions, task_description
        )
        
        # Select communities based on LLM recommendations
        selected_communities = [communities[i] for i in selected_indices if i < len(communities)]
        
        pruning_stats = {
            "original_count": len(communities),
            "pruned_count": len(selected_communities),
            "removed_count": len(communities) - len(selected_communities),
            "pruning_ratio": 1 - (len(selected_communities) / len(communities)) if communities else 0,
            "method": "llm_semantic",
            "threshold": self.semantic_threshold
        }
        
        logger.info(f"✅ LLM fine pruning: {len(communities)} → {len(selected_communities)} communities "
                   f"({pruning_stats['pruning_ratio']:.2%} pruned)")
        
        return selected_communities, pruning_stats
    
    def _create_community_description(self, community: Dict[str, Any], 
                                    schema_manager: SchemaManager) -> Dict[str, Any]:
        """Create a rich description of a community for LLM evaluation."""
        community_id = community.get('id', '')
        purpose = community.get('purpose', '')
        members = community.get('members', [])
        size = community.get('size', len(members))
        
        # Sample member details
        member_details = []
        for member_id in members[:5]:  # Sample first 5 members
            node = schema_manager.get_node(member_id)
            if node:
                node_type = self._infer_node_type(node)
                if node_type == 'UIElement':
                    detail = f"{node.get('type', 'element')}: '{node.get('text', 'N/A')}'"
                elif node_type == 'Workflow':
                    detail = f"workflow: '{node.get('name', 'N/A')}'"
                else:
                    detail = f"{node_type.lower()}: {node.get('name', member_id[:8])}"
                member_details.append(detail)
        
        return {
            'id': community_id,
            'purpose': purpose,
            'size': size,
            'members_sample': member_details,
            'modularity': community.get('modularity', 0.0),
            'frequency': community.get('frequency', 0)
        }
    
    def _extract_task_description(self, context: Dict[str, Any]) -> str:
        """Extract meaningful task description from context."""
        task_elements = []
        
        if context.get('user_intent'):
            task_elements.append(f"User wants to: {context['user_intent']}")
            
        if context.get('application'):
            task_elements.append(f"Target application: {context['application']}")
            
        if context.get('ui_elements'):
            elements = context['ui_elements'][:3]  # First 3 elements
            element_texts = [elem.get('text', '') for elem in elements if elem.get('text')]
            if element_texts:
                task_elements.append(f"UI elements involved: {', '.join(element_texts)}")
        
        if context.get('workflow_name'):
            task_elements.append(f"Workflow: {context['workflow_name']}")
            
        return "; ".join(task_elements) if task_elements else "General automation task"
    
    def _create_evaluation_prompt(self, community_descriptions: List[Dict[str, Any]], 
                                task_description: str, max_communities: int) -> str:
        """Create prompt for LLM-based community evaluation."""
        prompt = f"""
You are evaluating UI automation communities for the following task:
{task_description}

Here are the available communities:

"""
        for i, desc in enumerate(community_descriptions):
            prompt += f"{i+1}. Purpose: {desc['purpose']} (Size: {desc['size']}, Modularity: {desc['modularity']:.2f})\n"
            prompt += f"   Members: {', '.join(desc['members_sample'])}\n\n"
        
        prompt += f"""
Please select the {max_communities} most relevant communities for this task. Consider:
1. Semantic relevance to the task
2. Likelihood of containing needed UI elements
3. Community quality (modularity score)
4. Appropriate scope (not too broad, not too narrow)

Return the indices (1-based) of selected communities as a comma-separated list.
"""
        return prompt
    
    def _simulate_llm_selection(self, community_descriptions: List[Dict[str, Any]], 
                              task_description: str) -> List[int]:
        """
        Simulate LLM selection logic.
        In real implementation, this would call Claude API.
        """
        scored_communities = []
        
        for i, desc in enumerate(community_descriptions):
            score = self._calculate_semantic_score(desc, task_description)
            scored_communities.append((i, score))
        
        # Sort by semantic score and select top communities
        scored_communities.sort(key=lambda x: x[1], reverse=True)
        
        selected_count = min(self.max_communities_for_llm, len(scored_communities))
        selected_indices = [idx for idx, score in scored_communities[:selected_count]]
        
        return selected_indices
    
    def _calculate_semantic_score(self, community_desc: Dict[str, Any], 
                                task_description: str) -> float:
        """Calculate semantic relevance score (simplified heuristic)."""
        purpose = community_desc['purpose'].lower()
        task = task_description.lower()
        
        # Simple keyword matching (in real implementation, would use embeddings)
        score = 0.0
        
        # Purpose alignment
        if any(word in task for word in purpose.split('_')):
            score += 0.4
            
        # Member relevance
        members_text = ' '.join(community_desc['members_sample']).lower()
        if any(word in members_text for word in ['save', 'file', 'button'] if word in task):
            score += 0.3
            
        # Quality factors
        score += community_desc['modularity'] * 0.2
        score += min(1.0, community_desc['frequency'] / 100.0) * 0.1
        
        return score
    
    def _infer_node_type(self, node: Dict[str, Any]) -> str:
        """Infer node type from node properties."""
        if 'text' in node and 'coordinates' in node:
            return 'UIElement'
        elif 'name' in node and 'steps' in node:
            return 'Workflow'
        elif 'purpose' in node and 'members' in node:
            return 'Community'
        elif 'resolution' in node and 'screenshot_path' in node:
            return 'Screen'
        elif 'pattern_type' in node:
            return 'Pattern'
        else:
            return 'Unknown'


class CommunityPruningSystem:
    """Main pruning system coordinating coarse and fine pruning stages."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.modularity_pruner = ModularityPruner()
        self.llm_fine_pruner = LLMFinePruner()
        
    def prune_communities_for_task(self, task_context: Dict[str, Any], 
                                  target_community_count: int = 10) -> PruningResult:
        """
        Perform two-stage pruning for a specific task.
        
        Args:
            task_context: Context describing the current task
            target_community_count: Desired number of communities after pruning
            
        Returns:
            PruningResult with pruning statistics
        """
        start_time = time.time()
        logger.info(f"🎯 Starting two-stage community pruning for task...")
        
        # Get all communities from database
        all_communities = self.sm.find_nodes(NodeType.COMMUNITY, limit=1000)
        original_count = len(all_communities)
        
        if original_count == 0:
            logger.warning("No communities found in database")
            return PruningResult(
                original_communities=0,
                pruned_communities=0,
                pruning_ratio=0.0,
                processing_time=0.0,
                pruning_method="none",
                quality_threshold=0.0,
                retained_coverage=0.0
            )
        
        # Convert to dictionary format expected by pruners
        community_dicts = []
        for community in all_communities:
            members = json.loads(community.get('members', '[]')) if community.get('members') else []
            community_dict = {
                'id': community.get('id', ''),
                'purpose': community.get('purpose', ''),
                'members': members,
                'size': community.get('size', len(members)),
                'modularity': community.get('modularity', 0.0),
                'frequency': community.get('frequency', 0),
                'timestamp': community.get('timestamp', time.time())
            }
            community_dicts.append(community_dict)
        
        # Stage 1: Modularity-based coarse pruning
        coarse_pruned, coarse_stats = self.modularity_pruner.prune_communities(
            community_dicts, task_context
        )
        
        # Stage 2: LLM-based fine pruning (if still too many communities)
        if len(coarse_pruned) > target_community_count:
            self.llm_fine_pruner.max_communities_for_llm = target_community_count
            final_pruned, fine_stats = self.llm_fine_pruner.prune_communities(
                coarse_pruned, task_context, self.sm
            )
        else:
            final_pruned = coarse_pruned
            fine_stats = {"method": "skipped", "pruned_count": len(coarse_pruned)}
        
        processing_time = time.time() - start_time
        final_count = len(final_pruned)
        
        # Calculate coverage retention (simplified)
        coverage_retained = self._calculate_coverage_retention(
            community_dicts, final_pruned
        )
        
        result = PruningResult(
            original_communities=original_count,
            pruned_communities=final_count,
            pruning_ratio=1 - (final_count / original_count) if original_count > 0 else 0,
            processing_time=processing_time,
            pruning_method="two_stage",
            quality_threshold=self.modularity_pruner.modularity_threshold,
            retained_coverage=coverage_retained
        )
        
        logger.info(f"✅ Two-stage pruning completed: {original_count} → {final_count} communities "
                   f"({result.pruning_ratio:.2%} pruned, {processing_time:.2f}s)")
        
        # Store pruning results for analysis
        self._store_pruning_results(final_pruned, task_context, result)
        
        return result
    
    def get_relevant_communities(self, task_context: Dict[str, Any], 
                               max_communities: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most relevant communities for a task after pruning.
        
        Args:
            task_context: Context describing the current task
            max_communities: Maximum number of communities to return
            
        Returns:
            List of relevant community dictionaries
        """
        pruning_result = self.prune_communities_for_task(task_context, max_communities)
        
        # Retrieve final communities from database
        relevant_communities = []
        all_communities = self.sm.find_nodes(NodeType.COMMUNITY, limit=1000)
        
        for community in all_communities:
            # Check if this community would be selected by pruning
            members = json.loads(community.get('members', '[]')) if community.get('members') else []
            community_dict = {
                'id': community.get('id', ''),
                'purpose': community.get('purpose', ''),
                'members': members,
                'size': community.get('size', len(members)),
                'modularity': community.get('modularity', 0.0),
                'frequency': community.get('frequency', 0)
            }
            
            # Apply same scoring logic as pruning
            score = self.modularity_pruner._calculate_community_score(community_dict, task_context)
            if score.combined_score > 0.5:  # Threshold for relevance
                relevant_communities.append(community_dict)
        
        # Sort by relevance and limit
        relevant_communities.sort(
            key=lambda c: self.modularity_pruner._calculate_community_score(c, task_context).combined_score,
            reverse=True
        )
        
        return relevant_communities[:max_communities]
    
    def _calculate_coverage_retention(self, original_communities: List[Dict[str, Any]], 
                                    pruned_communities: List[Dict[str, Any]]) -> float:
        """Calculate what percentage of important relationships are retained."""
        if not original_communities:
            return 0.0
        
        original_members = set()
        for community in original_communities:
            original_members.update(community.get('members', []))
        
        retained_members = set()
        for community in pruned_communities:
            retained_members.update(community.get('members', []))
        
        coverage = len(retained_members) / len(original_members) if original_members else 0.0
        return coverage
    
    def _store_pruning_results(self, final_communities: List[Dict[str, Any]], 
                              task_context: Dict[str, Any], 
                              result: PruningResult):
        """Store pruning results for future analysis and optimization."""
        # In a full implementation, would store to analytics database
        logger.debug(f"Pruning results: {result.original_communities} → {result.pruned_communities} "
                    f"({result.pruning_ratio:.2%} reduction)")


# Test the community pruning system
if __name__ == "__main__":
    print("🧪 Testing Community Pruning System...")
    
    with SchemaManager() as sm:
        pruning_system = CommunityPruningSystem(sm)
        
        # Test with sample task context
        task_context = {
            'user_intent': 'save document to file',
            'application': 'notepad',
            'ui_elements': [
                {'text': 'Save', 'type': 'button'},
                {'text': 'File', 'type': 'menu'}
            ],
            'workflow_name': 'Document Save Workflow'
        }
        
        # Test two-stage pruning
        result = pruning_system.prune_communities_for_task(task_context, target_community_count=5)
        
        print(f"✅ Pruning Results:")
        print(f"   - Original communities: {result.original_communities}")
        print(f"   - Pruned communities: {result.pruned_communities}")
        print(f"   - Pruning ratio: {result.pruning_ratio:.2%}")
        print(f"   - Processing time: {result.processing_time:.3f}s")
        print(f"   - Coverage retained: {result.retained_coverage:.2%}")
        
        # Test relevant community retrieval
        relevant = pruning_system.get_relevant_communities(task_context, max_communities=3)
        print(f"✅ Found {len(relevant)} relevant communities:")
        for i, community in enumerate(relevant):
            print(f"   {i+1}. {community['purpose']} (size: {community['size']})")
    
    print("✅ Community Pruning System testing completed!")