"""
Knowledge Graph Schema for Kenny Graph Intelligence System

Defines node types, relationships, and data structures for the graph database.
Based on comprehensive analysis in GitHub Issue #165.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


def _sanitize_label(label: str) -> str:
    """Allow only alphanumeric and underscore in Cypher labels/types.

    Prevents Cypher injection via node labels or relationship types which
    cannot be parameterized in Neo4j/Memgraph.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "", label)


class NodeType(Enum):
    """Supported node types in Kenny's knowledge graph."""

    UI_ELEMENT = "UIElement"
    WORKFLOW = "Workflow"
    COMMUNITY = "Community"
    APPLICATION = "Application"
    SCREEN = "Screen"
    PATTERN = "Pattern"
    ERROR = "Error"
    USER_ACTION = "UserAction"
    PREDICTION = "Prediction"
    # Memory-specific node types
    MEMORY_ITEM = "MemoryItem"
    MEMORY_SESSION = "MemorySession"
    USER_PROFILE = "UserProfile"
    MEMORY_PATTERN = "MemoryPattern"


class RelationshipType(Enum):
    """Supported relationship types."""

    CONTAINS = "CONTAINS"  # parent-child UI hierarchy
    TRIGGERS = "TRIGGERS"  # action-result relationship
    NAVIGATES_TO = "NAVIGATES_TO"  # navigation flow
    REQUIRES = "REQUIRES"  # dependency relationship
    PRECEDES = "PRECEDES"  # sequential relationship
    BELONGS_TO = "BELONGS_TO"  # community membership
    SIMILAR_TO = "SIMILAR_TO"  # pattern similarity
    CAUSED_BY = "CAUSED_BY"  # error causation
    RESOLVES = "RESOLVES"  # error resolution
    FOLLOWED_BY = "FOLLOWED_BY"  # action sequence
    # Memory-specific relationships
    REMEMBERS = "REMEMBERS"  # entity to memory relationships
    CONTAINS_MEMORY = "CONTAINS_MEMORY"  # session to memory relationships
    LEARNED_FROM = "LEARNED_FROM"  # pattern derivation relationships
    CACHED_FROM = "CACHED_FROM"  # cache relationships


@dataclass
class BaseNode:
    """Base class for all graph nodes."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for database storage."""
        return {"id": self.id, "timestamp": self.timestamp, "metadata": json.dumps(self.metadata)}


@dataclass
class UIElementNode(BaseNode):
    """UI Element node representing screen elements detected by OCR."""

    type: str = ""  # button, menu, dialog, text_field, etc.
    text: str = ""  # displayed text
    coordinates: List[int] = field(default_factory=list)  # [x, y] or [x, y, width, height]
    confidence: float = 0.0  # OCR confidence score
    application: str = ""  # parent application
    screen_id: str = ""  # associated screen
    properties: Dict[str, Any] = field(default_factory=dict)  # additional properties

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "type": self.type,
                "text": self.text,
                "coordinates": self.coordinates,
                "confidence": self.confidence,
                "application": self.application,
                "screen_id": self.screen_id,
                "properties": json.dumps(self.properties),
            }
        )
        return data


@dataclass
class WorkflowNode(BaseNode):
    """Workflow node representing automation sequences."""

    name: str = ""
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    success_rate: float = 0.0
    avg_duration: float = 0.0
    execution_count: int = 0
    user_id: str = ""
    complexity: str = "simple"  # simple, medium, complex, enterprise

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "description": self.description,
                "steps": json.dumps(self.steps),
                "status": self.status,
                "success_rate": self.success_rate,
                "avg_duration": self.avg_duration,
                "execution_count": self.execution_count,
                "user_id": self.user_id,
                "complexity": self.complexity,
            }
        )
        return data


@dataclass
class CommunityNode(BaseNode):
    """Community node representing groups of related elements."""

    purpose: str = ""  # file_operations, email_composition, etc.
    members: List[str] = field(default_factory=list)  # member node IDs
    modularity: float = 0.0  # community quality score
    size: int = 0
    cohesion: float = 0.0  # internal connectivity
    frequency: int = 0  # usage frequency
    success_rate: float = 0.0
    avg_completion_time: float = 0.0
    detection_algorithm: str = ""  # louvain, girvan_newman, etc.

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "purpose": self.purpose,
                "members": json.dumps(self.members),
                "modularity": self.modularity,
                "size": self.size,
                "cohesion": self.cohesion,
                "frequency": self.frequency,
                "success_rate": self.success_rate,
                "avg_completion_time": self.avg_completion_time,
                "detection_algorithm": self.detection_algorithm,
            }
        )
        return data


@dataclass
class ApplicationNode(BaseNode):
    """Application node representing software applications."""

    name: str = ""
    version: str = ""
    process_id: int = 0
    window_title: str = ""
    executable_path: str = ""
    ui_framework: str = ""  # qt, gtk, electron, etc.
    automation_confidence: float = 0.0
    last_active: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "version": self.version,
                "process_id": self.process_id,
                "window_title": self.window_title,
                "executable_path": self.executable_path,
                "ui_framework": self.ui_framework,
                "automation_confidence": self.automation_confidence,
                "last_active": self.last_active,
            }
        )
        return data


@dataclass
class ScreenNode(BaseNode):
    """Screen node representing screen captures and states."""

    resolution: List[int] = field(default_factory=list)  # [width, height]
    screenshot_path: str = ""
    screenshot_hash: str = ""
    active_window: str = ""
    ui_elements_count: int = 0
    processing_time: float = 0.0
    ocr_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "resolution": self.resolution,
                "screenshot_path": self.screenshot_path,
                "screenshot_hash": self.screenshot_hash,
                "active_window": self.active_window,
                "ui_elements_count": self.ui_elements_count,
                "processing_time": self.processing_time,
                "ocr_confidence": self.ocr_confidence,
            }
        )
        return data


@dataclass
class PatternNode(BaseNode):
    """Pattern node representing learned behavioral patterns."""

    pattern_type: str = ""  # sequence, prediction, optimization
    sequence: List[str] = field(default_factory=list)  # action sequence
    frequency: int = 0
    confidence: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    last_used: float = 0.0
    generalization_score: float = 0.0  # how well it transfers to new contexts

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "pattern_type": self.pattern_type,
                "sequence": json.dumps(self.sequence),
                "frequency": self.frequency,
                "confidence": self.confidence,
                "context": json.dumps(self.context),
                "success_rate": self.success_rate,
                "last_used": self.last_used,
                "generalization_score": self.generalization_score,
            }
        )
        return data


@dataclass
class ErrorNode(BaseNode):
    """Error node representing failures and recovery strategies."""

    category: str = ""  # ui_not_found, timeout, permission, etc.
    message: str = ""
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical
    frequency: int = 0
    resolved: bool = False
    resolution_strategy: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "category": self.category,
                "message": self.message,
                "stack_trace": self.stack_trace,
                "context": json.dumps(self.context),
                "severity": self.severity,
                "frequency": self.frequency,
                "resolved": self.resolved,
                "resolution_strategy": self.resolution_strategy,
            }
        )
        return data


@dataclass
class MemoryItemNode(BaseNode):
    """Memory item node representing individual memory entries from Mem0."""

    content: str = ""  # memory content
    memory_type: str = "general"  # general, screen, workflow, error, etc.
    user_id: str = ""  # user who owns this memory
    session_id: str = ""  # session when memory was created
    confidence: float = 1.0  # memory confidence score
    embedding: List[float] = field(default_factory=list)  # vector embedding
    tags: List[str] = field(default_factory=list)  # memory tags
    mem0_id: str = ""  # original Mem0 memory ID
    access_count: int = 0  # how often this memory is accessed

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "content": self.content,
                "memory_type": self.memory_type,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "confidence": self.confidence,
                "embedding": json.dumps(self.embedding),
                "tags": json.dumps(self.tags),
                "mem0_id": self.mem0_id,
                "access_count": self.access_count,
            }
        )
        return data


@dataclass
class MemorySessionNode(BaseNode):
    """Memory session node representing a memory session container."""

    session_name: str = ""  # human-readable session name
    user_id: str = ""  # session owner
    agent_id: str = ""  # agent associated with session
    run_id: str = ""  # specific run ID
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    memory_count: int = 0  # number of memories in session
    status: str = "active"  # active, completed, archived
    context: Dict[str, Any] = field(default_factory=dict)  # session context

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "session_name": self.session_name,
                "user_id": self.user_id,
                "agent_id": self.agent_id,
                "run_id": self.run_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "memory_count": self.memory_count,
                "status": self.status,
                "context": json.dumps(self.context),
            }
        )
        return data


@dataclass
class UserProfileNode(BaseNode):
    """User profile node representing user-specific memory aggregations."""

    user_id: str = ""  # unique user identifier
    username: str = ""  # human-readable username
    preferences: Dict[str, Any] = field(default_factory=dict)  # user preferences
    behavioral_patterns: List[Dict[str, Any]] = field(default_factory=list)
    memory_statistics: Dict[str, Any] = field(default_factory=dict)
    last_active: float = field(default_factory=time.time)
    total_memories: int = 0  # total memories for this user
    automation_preferences: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "user_id": self.user_id,
                "username": self.username,
                "preferences": json.dumps(self.preferences),
                "behavioral_patterns": json.dumps(self.behavioral_patterns),
                "memory_statistics": json.dumps(self.memory_statistics),
                "last_active": self.last_active,
                "total_memories": self.total_memories,
                "automation_preferences": json.dumps(self.automation_preferences),
            }
        )
        return data


@dataclass
class MemoryPatternNode(BaseNode):
    """Memory pattern node representing learned behavioral patterns."""

    pattern_name: str = ""  # descriptive pattern name
    pattern_type: str = "behavioral"  # behavioral, workflow, error, temporal
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 0  # how often this pattern occurs
    confidence: float = 0.0  # pattern confidence score
    user_id: str = ""  # user associated with pattern
    context_requirements: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0  # pattern prediction success rate
    last_reinforced: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "pattern_name": self.pattern_name,
                "pattern_type": self.pattern_type,
                "pattern_data": json.dumps(self.pattern_data),
                "frequency": self.frequency,
                "confidence": self.confidence,
                "user_id": self.user_id,
                "context_requirements": json.dumps(self.context_requirements),
                "success_rate": self.success_rate,
                "last_reinforced": self.last_reinforced,
            }
        )
        return data


@dataclass
class Relationship:
    """Relationship between nodes in the graph."""

    from_node: str  # source node ID
    to_node: str  # target node ID
    relationship_type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # relationship strength
    confidence: float = 1.0  # relationship confidence
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "type": self.relationship_type.value,
            "properties": json.dumps(self.properties),
            "weight": self.weight,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


class KnowledgeGraphSchema:
    """Schema manager for Kenny's knowledge graph."""

    NODE_CLASSES = {
        NodeType.UI_ELEMENT: UIElementNode,
        NodeType.WORKFLOW: WorkflowNode,
        NodeType.COMMUNITY: CommunityNode,
        NodeType.APPLICATION: ApplicationNode,
        NodeType.SCREEN: ScreenNode,
        NodeType.PATTERN: PatternNode,
        NodeType.ERROR: ErrorNode,
    }

    @classmethod
    def create_node(cls, node_type: NodeType, **kwargs) -> BaseNode:
        """Create a node of the specified type."""
        node_class = cls.NODE_CLASSES.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")

        return node_class(**kwargs)

    @classmethod
    def create_relationship(
        cls, from_node: str, to_node: str, rel_type: RelationshipType, **kwargs
    ) -> Relationship:
        """Create a relationship between nodes."""
        return Relationship(
            from_node=from_node, to_node=to_node, relationship_type=rel_type, **kwargs
        )

    @classmethod
    def validate_node(cls, node: BaseNode) -> bool:
        """Validate node data."""
        if not node.id:
            return False
        if not isinstance(node.timestamp, (int, float)):
            return False
        return True

    @classmethod
    def get_cypher_create_node(
        cls, node: BaseNode, node_type: NodeType
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate parameterized Cypher query to create a node.

        Returns:
            (cypher_query, params) tuple.  The query uses ``$prop_<key>``
            placeholders so that user-supplied values never appear in the
            query string itself, preventing Cypher injection.
        """
        props = node.to_dict()
        params: Dict[str, Any] = {}
        prop_placeholders = []

        for key, value in props.items():
            safe_key = _sanitize_label(key)
            param_name = f"prop_{safe_key}"
            # Lists of mixed types need JSON serialisation for graph DBs
            if isinstance(value, list):
                params[param_name] = value
            elif isinstance(value, (str, int, float, bool)):
                params[param_name] = value
            else:
                params[param_name] = str(value)
            prop_placeholders.append(f"{safe_key}: ${param_name}")

        props_str = ", ".join(prop_placeholders)
        safe_label = _sanitize_label(node_type.value)
        query = f"CREATE (n:{safe_label} {{{props_str}}}) RETURN n.id as id"
        return query, params

    @classmethod
    def get_cypher_create_relationship(cls, rel: Relationship) -> Tuple[str, Dict[str, Any]]:
        """Generate parameterized Cypher query to create a relationship.

        Returns:
            (cypher_query, params) tuple.  Node IDs and relationship
            properties use ``$param`` placeholders; the relationship type
            label is sanitised (labels cannot be parameterized in Cypher).
        """
        props = rel.to_dict()
        params: Dict[str, Any] = {
            "from_id": rel.from_node,
            "to_id": rel.to_node,
        }
        prop_placeholders = []

        for key, value in props.items():
            if key in ["from_node", "to_node", "type"]:
                continue
            safe_key = _sanitize_label(key)
            param_name = f"rel_{safe_key}"
            if isinstance(value, (str, int, float, bool)):
                params[param_name] = value
            else:
                params[param_name] = str(value)
            prop_placeholders.append(f"{safe_key}: ${param_name}")

        props_str = ", ".join(prop_placeholders)
        if props_str:
            props_str = f" {{{props_str}}}"

        safe_rel_type = _sanitize_label(rel.relationship_type.value)
        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        CREATE (a)-[r:{safe_rel_type}{props_str}]->(b)
        RETURN type(r) as relationship_type
        """
        return query, params


# Factory functions for common node creation
def create_ui_element(
    element_type: str, text: str, coordinates: List[int], confidence: float, **kwargs
) -> UIElementNode:
    """Factory function to create UI element nodes."""
    return UIElementNode(
        type=element_type, text=text, coordinates=coordinates, confidence=confidence, **kwargs
    )


def create_community(
    purpose: str, members: List[str], modularity: float, **kwargs
) -> CommunityNode:
    """Factory function to create community nodes."""
    return CommunityNode(
        purpose=purpose, members=members, modularity=modularity, size=len(members), **kwargs
    )


def create_workflow(
    name: str, description: str, steps: List[Dict[str, Any]], **kwargs
) -> WorkflowNode:
    """Factory function to create workflow nodes."""
    return WorkflowNode(name=name, description=description, steps=steps, **kwargs)


def create_memory_item(
    content: str, memory_type: str, user_id: str, session_id: str = "", **kwargs
) -> MemoryItemNode:
    """Factory function to create memory item nodes."""
    return MemoryItemNode(
        content=content, memory_type=memory_type, user_id=user_id, session_id=session_id, **kwargs
    )


def create_memory_session(
    session_name: str, user_id: str, agent_id: str = "", **kwargs
) -> MemorySessionNode:
    """Factory function to create memory session nodes."""
    return MemorySessionNode(
        session_name=session_name, user_id=user_id, agent_id=agent_id, **kwargs
    )


def create_user_profile(user_id: str, username: str = "", **kwargs) -> UserProfileNode:
    """Factory function to create user profile nodes."""
    return UserProfileNode(user_id=user_id, username=username or user_id, **kwargs)


def create_memory_pattern(
    pattern_name: str, pattern_type: str, user_id: str, **kwargs
) -> MemoryPatternNode:
    """Factory function to create memory pattern nodes."""
    return MemoryPatternNode(
        pattern_name=pattern_name, pattern_type=pattern_type, user_id=user_id, **kwargs
    )


# Test the schema
if __name__ == "__main__":
    print("🧪 Testing Knowledge Graph Schema...")

    # Test UI element creation
    button = create_ui_element(
        element_type="button",
        text="Save",
        coordinates=[150, 200],
        confidence=0.95,
        application="notepad",
    )
    print(f"✅ Created UI element: {button.id}")

    # Test community creation
    community = create_community(
        purpose="save_workflow", members=[button.id], modularity=0.82, frequency=156
    )
    print(f"✅ Created community: {community.id}")

    # Test relationship creation
    schema = KnowledgeGraphSchema()
    rel = schema.create_relationship(
        from_node=community.id, to_node=button.id, rel_type=RelationshipType.CONTAINS, weight=1.0
    )
    print(f"✅ Created relationship: {rel.relationship_type.value}")

    # Test Cypher generation
    cypher_node = schema.get_cypher_create_node(button, NodeType.UI_ELEMENT)
    print(f"✅ Generated Cypher for node: {cypher_node[:50]}...")

    cypher_rel = schema.get_cypher_create_relationship(rel)
    print(f"✅ Generated Cypher for relationship: {cypher_rel[:50]}...")

    print("✅ Knowledge Graph Schema testing completed!")
