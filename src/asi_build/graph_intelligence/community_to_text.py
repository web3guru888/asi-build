"""
Community-to-Text Conversion for Kenny Graph Intelligence System

Implements Triple2Text and Graph2Text methods to convert graph communities
into natural language descriptions for LLM reasoning. Based on FastToG research paper.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import time
from collections import defaultdict, Counter

from .schema import NodeType, RelationshipType
from .schema_manager import SchemaManager

logger = logging.getLogger(__name__)


@dataclass
class TextConversionResult:
    """Result of community-to-text conversion."""
    community_id: str
    triple_descriptions: List[str]
    graph_description: str
    natural_language_summary: str
    conversion_method: str
    processing_time: float
    node_count: int
    relationship_count: int
    complexity_score: float
    summary_text: str = ""  # Alias for natural_language_summary
    community_type: str = "general"  # Type of community
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.summary_text and self.natural_language_summary:
            self.summary_text = self.natural_language_summary


@dataclass
class Triple:
    """Represents a single graph triple (subject, predicate, object)."""
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    confidence: float = 1.0
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class Triple2TextConverter:
    """Converts graph triples to natural language descriptions."""
    
    def __init__(self):
        # Predicate templates for natural language conversion
        self.predicate_templates = {
            RelationshipType.CONTAINS.value: "{subject} contains {object}",
            RelationshipType.TRIGGERS.value: "{subject} triggers {object}",
            RelationshipType.NAVIGATES_TO.value: "{subject} navigates to {object}",
            RelationshipType.REQUIRES.value: "{subject} requires {object}",
            RelationshipType.PRECEDES.value: "{subject} comes before {object}",
            RelationshipType.BELONGS_TO.value: "{subject} belongs to {object}",
            RelationshipType.SIMILAR_TO.value: "{subject} is similar to {object}",
            RelationshipType.CAUSED_BY.value: "{subject} was caused by {object}",
            RelationshipType.RESOLVES.value: "{subject} resolves {object}",
            RelationshipType.FOLLOWED_BY.value: "{subject} is followed by {object}"
        }
        
        # Node type descriptions for better readability
        self.node_type_descriptions = {
            NodeType.UI_ELEMENT.value: "UI element",
            NodeType.WORKFLOW.value: "workflow",
            NodeType.COMMUNITY.value: "community",
            NodeType.APPLICATION.value: "application",
            NodeType.SCREEN.value: "screen",
            NodeType.PATTERN.value: "pattern",
            NodeType.ERROR.value: "error",
            NodeType.USER_ACTION.value: "user action"
        }
    
    def convert_triple_to_text(self, triple: Triple) -> str:
        """Convert a single triple to natural language."""
        template = self.predicate_templates.get(
            triple.predicate, 
            "{subject} is connected to {object}"
        )
        
        # Get readable names for subject and object
        subject_name = self._get_readable_name(triple.subject, triple.subject_type)
        object_name = self._get_readable_name(triple.object, triple.object_type)
        
        # Apply template
        description = template.format(
            subject=subject_name,
            object=object_name
        )
        
        # Add confidence if low
        if triple.confidence < 0.8:
            description += f" (confidence: {triple.confidence:.1%})"
            
        return description
    
    def convert_triples_to_text(self, triples: List[Triple]) -> List[str]:
        """Convert multiple triples to natural language descriptions."""
        descriptions = []
        
        # Group triples by subject for better organization
        subject_groups = defaultdict(list)
        for triple in triples:
            subject_groups[triple.subject].append(triple)
        
        # Convert each group
        for subject, subject_triples in subject_groups.items():
            if len(subject_triples) == 1:
                # Single triple
                descriptions.append(self.convert_triple_to_text(subject_triples[0]))
            else:
                # Multiple triples with same subject - combine them
                combined = self._combine_subject_triples(subject, subject_triples)
                descriptions.append(combined)
        
        return descriptions
    
    def _get_readable_name(self, node_id: str, node_type: str) -> str:
        """Get a human-readable name for a node."""
        # This would query the database for actual node details
        # For now, use simplified names
        type_desc = self.node_type_descriptions.get(node_type, "item")
        
        if node_type == NodeType.UI_ELEMENT.value:
            # Would extract actual text from UI element
            return f"{type_desc} '{node_id[:8]}'"
        elif node_type == NodeType.WORKFLOW.value:
            return f"'{node_id[:8]}' workflow"
        elif node_type == NodeType.COMMUNITY.value:
            return f"community '{node_id[:8]}'"
        else:
            return f"{type_desc} '{node_id[:8]}'"
    
    def _combine_subject_triples(self, subject: str, triples: List[Triple]) -> str:
        """Combine multiple triples with the same subject."""
        subject_name = self._get_readable_name(triples[0].subject, triples[0].subject_type)
        
        # Group by predicate type
        predicate_groups = defaultdict(list)
        for triple in triples:
            predicate_groups[triple.predicate].append(triple)
        
        parts = [f"{subject_name}"]
        
        for predicate, pred_triples in predicate_groups.items():
            if predicate == RelationshipType.CONTAINS.value:
                objects = [self._get_readable_name(t.object, t.object_type) for t in pred_triples]
                if len(objects) == 1:
                    parts.append(f"contains {objects[0]}")
                else:
                    parts.append(f"contains {', '.join(objects[:-1])} and {objects[-1]}")
            
            elif predicate == RelationshipType.TRIGGERS.value:
                objects = [self._get_readable_name(t.object, t.object_type) for t in pred_triples]
                parts.append(f"triggers {', '.join(objects)}")
            
            # Add more predicate-specific combinations as needed
            else:
                for triple in pred_triples:
                    template = self.predicate_templates.get(predicate, "is connected to {object}")
                    object_name = self._get_readable_name(triple.object, triple.object_type)
                    parts.append(template.format(subject="", object=object_name).strip())
        
        return " ".join(parts)


class Graph2TextConverter:
    """Converts entire graph communities to coherent text descriptions."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.triple_converter = Triple2TextConverter()
    
    def generate_community_summary(self, community_id: str, 
                                  include_statistics: bool = True) -> 'TextConversionResult':
        """
        Generate a summary for a community (alias for convert_community_to_text).
        
        Args:
            community_id: ID of the community
            include_statistics: Whether to include stats
            
        Returns:
            TextConversionResult with summary
        """
        try:
            return self.convert_community_to_text(community_id, include_context=include_statistics)
        except Exception as e:
            # Return a default result if conversion fails
            return TextConversionResult(
                community_id=community_id,
                triple_descriptions=[],
                graph_description="",
                natural_language_summary="Community summary not available",
                conversion_method="graph2text",
                processing_time=0.0,
                node_count=0,
                relationship_count=0,
                complexity_score=0.0,
                summary_text="Community summary not available",
                community_type="unknown"
            )
        
    def convert_community_to_text(self, community_id: str, 
                                 include_context: bool = True) -> TextConversionResult:
        """
        Convert a community and its relationships to natural language.
        
        Args:
            community_id: ID of the community to convert
            include_context: Whether to include surrounding context
            
        Returns:
            TextConversionResult with various text representations
        """
        start_time = time.time()
        
        # Get community details
        community = self.sm.get_node(community_id, NodeType.COMMUNITY)
        if not community:
            raise ValueError(f"Community {community_id} not found")
        
        # Extract community triples
        triples = self._extract_community_triples(community_id)
        
        # Convert triples to text descriptions
        triple_descriptions = self.triple_converter.convert_triples_to_text(triples)
        
        # Generate comprehensive graph description
        graph_description = self._generate_graph_description(community, triples)
        
        # Create natural language summary
        natural_summary = self._generate_natural_summary(community, triples, triple_descriptions)
        
        # Calculate complexity score
        complexity = self._calculate_complexity(triples)
        
        processing_time = time.time() - start_time
        
        result = TextConversionResult(
            community_id=community_id,
            triple_descriptions=triple_descriptions,
            graph_description=graph_description,
            natural_language_summary=natural_summary,
            conversion_method="graph2text",
            processing_time=processing_time,
            node_count=len(set([t.subject for t in triples] + [t.object for t in triples])),
            relationship_count=len(triples),
            complexity_score=complexity
        )
        
        logger.info(f"✅ Converted community {community_id[:8]} to text: "
                   f"{len(triple_descriptions)} descriptions, {complexity:.2f} complexity")
        
        return result
    
    def convert_multiple_communities(self, community_ids: List[str]) -> List[TextConversionResult]:
        """Convert multiple communities to text efficiently."""
        results = []
        
        for community_id in community_ids:
            try:
                result = self.convert_community_to_text(community_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to convert community {community_id}: {e}")
                # Create empty result for failed conversion
                results.append(TextConversionResult(
                    community_id=community_id,
                    triple_descriptions=[],
                    graph_description=f"Error converting community: {e}",
                    natural_language_summary="Conversion failed",
                    conversion_method="error",
                    processing_time=0.0,
                    node_count=0,
                    relationship_count=0,
                    complexity_score=0.0
                ))
        
        return results
    
    def _extract_community_triples(self, community_id: str) -> List[Triple]:
        """Extract all triples (relationships) within and connected to a community."""
        triples = []
        
        # Get community members
        community = self.sm.get_node(community_id)
        if not community or 'members' not in community:
            return triples
        
        try:
            members = json.loads(community['members']) if isinstance(community['members'], str) else community['members']
        except:
            members = []
        
        if not members:
            return triples
        
        # Get all relationships involving community members
        for member_id in members:
            # Outgoing relationships
            outgoing = self.sm.find_relationships(from_node=member_id, limit=50)
            for rel in outgoing:
                triple = Triple(
                    subject=rel['from_id'],
                    subject_type=self._get_node_type(rel['from_id']),
                    predicate=rel['type'],
                    object=rel['to_id'],
                    object_type=self._get_node_type(rel['to_id']),
                    confidence=rel['properties'].get('confidence', 1.0) if rel['properties'] else 1.0,
                    properties=rel['properties']
                )
                triples.append(triple)
            
            # Incoming relationships
            incoming = self.sm.find_relationships(to_node=member_id, limit=50)
            for rel in incoming:
                # Avoid duplicates
                if not any(t.subject == rel['from_id'] and t.object == rel['to_id'] 
                          and t.predicate == rel['type'] for t in triples):
                    triple = Triple(
                        subject=rel['from_id'],
                        subject_type=self._get_node_type(rel['from_id']),
                        predicate=rel['type'],
                        object=rel['to_id'],
                        object_type=self._get_node_type(rel['to_id']),
                        confidence=rel['properties'].get('confidence', 1.0) if rel['properties'] else 1.0,
                        properties=rel['properties']
                    )
                    triples.append(triple)
        
        return triples
    
    def _get_node_type(self, node_id: str) -> str:
        """Get the type of a node by querying the database."""
        # Try each node type
        for node_type in NodeType:
            node = self.sm.get_node(node_id, node_type)
            if node:
                return node_type.value
        
        return "Unknown"
    
    def _generate_graph_description(self, community: Dict[str, Any], 
                                  triples: List[Triple]) -> str:
        """Generate a structured description of the community graph."""
        purpose = community.get('purpose', 'unknown purpose')
        size = community.get('size', 0)
        
        description_parts = [
            f"This is a community focused on {purpose.replace('_', ' ')} with {size} members."
        ]
        
        if triples:
            # Analyze relationship patterns
            predicate_counts = Counter(t.predicate for t in triples)
            most_common = predicate_counts.most_common(3)
            
            relationship_desc = []
            for predicate, count in most_common:
                readable_pred = predicate.lower().replace('_', ' ')
                relationship_desc.append(f"{count} {readable_pred} relationships")
            
            if relationship_desc:
                description_parts.append(f"It contains {', '.join(relationship_desc)}.")
            
            # Identify key nodes (most connected)
            node_connections = Counter()
            for triple in triples:
                node_connections[triple.subject] += 1
                node_connections[triple.object] += 1
            
            if node_connections:
                most_connected = node_connections.most_common(1)[0]
                node_id, connection_count = most_connected
                node_name = self._get_node_readable_name(node_id)
                description_parts.append(f"The most connected element is {node_name} with {connection_count} connections.")
        
        return " ".join(description_parts)
    
    def _generate_natural_summary(self, community: Dict[str, Any], 
                                 triples: List[Triple],
                                 triple_descriptions: List[str]) -> str:
        """Generate a natural language summary of the community."""
        purpose = community.get('purpose', 'general operations').replace('_', ' ')
        
        summary_parts = [f"This community handles {purpose}."]
        
        if triple_descriptions:
            # Group descriptions by type for better flow
            ui_descriptions = [d for d in triple_descriptions if 'UI element' in d or 'button' in d or 'menu' in d]
            workflow_descriptions = [d for d in triple_descriptions if 'workflow' in d]
            other_descriptions = [d for d in triple_descriptions if d not in ui_descriptions and d not in workflow_descriptions]
            
            if ui_descriptions:
                summary_parts.append("The UI components involved include:")
                summary_parts.extend([f"- {desc}" for desc in ui_descriptions[:3]])  # Limit to avoid verbosity
            
            if workflow_descriptions:
                summary_parts.append("The workflows include:")
                summary_parts.extend([f"- {desc}" for desc in workflow_descriptions[:2]])
            
            if other_descriptions and len(summary_parts) < 5:  # Add if we have space
                summary_parts.extend([f"- {desc}" for desc in other_descriptions[:2]])
        
        # Add frequency information if available
        frequency = community.get('frequency', 0)
        if frequency > 0:
            usage_desc = "frequently" if frequency > 50 else "occasionally" if frequency > 10 else "rarely"
            summary_parts.append(f"This community is {usage_desc} used in automation tasks.")
        
        return " ".join(summary_parts)
    
    def _get_node_readable_name(self, node_id: str) -> str:
        """Get a readable name for a node by examining its properties."""
        # Try to get the actual node and extract meaningful name
        for node_type in NodeType:
            node = self.sm.get_node(node_id, node_type)
            if node:
                if node_type == NodeType.UI_ELEMENT:
                    text = node.get('text', '')
                    element_type = node.get('type', 'element')
                    if text:
                        return f"{element_type} '{text}'"
                    else:
                        return f"{element_type}"
                
                elif node_type == NodeType.WORKFLOW:
                    name = node.get('name', f'workflow {node_id[:8]}')
                    return f"'{name}'"
                
                elif node_type == NodeType.APPLICATION:
                    name = node.get('name', f'app {node_id[:8]}')
                    return f"application '{name}'"
                
                elif node_type == NodeType.COMMUNITY:
                    purpose = node.get('purpose', 'community')
                    return f"{purpose.replace('_', ' ')} community"
                
                else:
                    return f"{node_type.value.lower()} '{node_id[:8]}'"
        
        return f"item '{node_id[:8]}'"
    
    def _calculate_complexity(self, triples: List[Triple]) -> float:
        """Calculate complexity score based on graph structure."""
        if not triples:
            return 0.0
        
        # Factor in number of nodes and relationships
        unique_nodes = set()
        for triple in triples:
            unique_nodes.add(triple.subject)
            unique_nodes.add(triple.object)
        
        node_count = len(unique_nodes)
        edge_count = len(triples)
        
        # Basic complexity: edge to node ratio
        basic_complexity = edge_count / node_count if node_count > 0 else 0
        
        # Relationship type diversity
        unique_predicates = len(set(t.predicate for t in triples))
        diversity_factor = unique_predicates / 5.0  # Normalize to ~1.0
        
        # Combined complexity score
        complexity = (basic_complexity * 0.7) + (diversity_factor * 0.3)
        return min(complexity, 5.0)  # Cap at 5.0


class CommunityTextGenerator:
    """High-level interface for community text generation."""
    
    def __init__(self, schema_manager: SchemaManager):
        self.sm = schema_manager
        self.graph2text = Graph2TextConverter(schema_manager)
        
    def generate_task_context_description(self, community_ids: List[str],
                                        task_description: str = "") -> str:
        """
        Generate a comprehensive text description for a list of communities
        in the context of a specific task.
        """
        if not community_ids:
            return "No relevant communities found for this task."
        
        logger.info(f"🔄 Generating task context for {len(community_ids)} communities...")
        
        # Convert communities to text
        conversion_results = self.graph2text.convert_multiple_communities(community_ids)
        
        # Build comprehensive description
        description_parts = []
        
        if task_description:
            description_parts.append(f"For the task: {task_description}")
            description_parts.append("")
        
        description_parts.append("The following communities are relevant:")
        description_parts.append("")
        
        for i, result in enumerate(conversion_results, 1):
            if result.conversion_method != "error":
                description_parts.append(f"{i}. {result.natural_language_summary}")
                
                # Add key relationships if not too verbose
                if len(result.triple_descriptions) <= 3:
                    description_parts.append("   Key relationships:")
                    for desc in result.triple_descriptions:
                        description_parts.append(f"   - {desc}")
                
                description_parts.append("")
        
        # Add summary statistics
        successful_conversions = [r for r in conversion_results if r.conversion_method != "error"]
        if successful_conversions:
            total_nodes = sum(r.node_count for r in successful_conversions)
            total_relationships = sum(r.relationship_count for r in successful_conversions)
            avg_complexity = sum(r.complexity_score for r in successful_conversions) / len(successful_conversions)
            
            description_parts.append(f"Summary: {len(successful_conversions)} communities, "
                                   f"{total_nodes} nodes, {total_relationships} relationships, "
                                   f"complexity score: {avg_complexity:.1f}")
        
        return "\n".join(description_parts)
    
    def generate_reasoning_prompt(self, community_ids: List[str], 
                                task_context: Dict[str, Any]) -> str:
        """Generate a prompt for LLM reasoning with community context."""
        user_intent = task_context.get('user_intent', 'perform automation task')
        
        # Generate community descriptions
        context_description = self.generate_task_context_description(
            community_ids, 
            f"User wants to: {user_intent}"
        )
        
        prompt = f"""# UI Automation Task Analysis

## Task Context
{context_description}

## Your Task
Based on the communities and relationships described above, analyze how to accomplish: "{user_intent}"

Consider:
1. Which UI elements from these communities are most relevant
2. What sequence of actions would be most effective
3. How the relationships between elements can guide the automation
4. Any potential challenges or alternative approaches

Please provide a step-by-step reasoning process and recommend the best automation approach.
"""
        return prompt


# Test the community-to-text conversion system
if __name__ == "__main__":
    print("🧪 Testing Community-to-Text Conversion...")
    
    with SchemaManager() as sm:
        text_generator = CommunityTextGenerator(sm)
        
        # Get some communities to test with
        communities = sm.find_nodes(NodeType.COMMUNITY, limit=3)
        community_ids = [c['id'] for c in communities]
        
        if community_ids:
            print(f"✅ Testing with {len(community_ids)} communities...")
            
            # Test individual community conversion
            first_community = community_ids[0]
            result = text_generator.graph2text.convert_community_to_text(first_community)
            
            print(f"✅ Community Conversion Results:")
            print(f"   - Community ID: {result.community_id[:8]}")
            print(f"   - Nodes: {result.node_count}, Relationships: {result.relationship_count}")
            print(f"   - Complexity: {result.complexity_score:.2f}")
            print(f"   - Processing time: {result.processing_time:.3f}s")
            print(f"   - Natural summary: {result.natural_language_summary[:100]}...")
            
            # Test task context generation
            task_context = {
                'user_intent': 'save a document to file',
                'application': 'notepad'
            }
            
            context_description = text_generator.generate_task_context_description(
                community_ids, task_context['user_intent']
            )
            
            print(f"✅ Task Context Description ({len(context_description)} chars):")
            print(f"   First 200 chars: {context_description[:200]}...")
            
            # Test reasoning prompt generation
            reasoning_prompt = text_generator.generate_reasoning_prompt(community_ids[:2], task_context)
            print(f"✅ Generated reasoning prompt ({len(reasoning_prompt)} chars)")
            
        else:
            print("⚠️ No communities found in database for testing")
    
    print("✅ Community-to-Text Conversion testing completed!")