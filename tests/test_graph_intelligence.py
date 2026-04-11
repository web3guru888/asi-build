"""
Tests for the graph_intelligence package.

Covers:
- NodeType / RelationshipType enums
- All node dataclass creation and to_dict serialization
- KnowledgeGraphSchema: create_node, create_relationship, validate_node
- Cypher generation for nodes and relationships
- Factory functions (create_ui_element, create_community, etc.)

Note: SchemaManager requires a live Neo4j/Memgraph instance, so those
tests are skipped unless a connection is available.
"""

import json
import time
import uuid

import pytest

from asi_build.graph_intelligence.schema import (  # Factory functions
    ApplicationNode,
    BaseNode,
    CommunityNode,
    ErrorNode,
    KnowledgeGraphSchema,
    MemoryItemNode,
    MemoryPatternNode,
    MemorySessionNode,
    NodeType,
    PatternNode,
    Relationship,
    RelationshipType,
    ScreenNode,
    UIElementNode,
    UserProfileNode,
    WorkflowNode,
    create_community,
    create_memory_item,
    create_memory_pattern,
    create_memory_session,
    create_ui_element,
    create_user_profile,
    create_workflow,
)

# =========================================================================
# Section 1 — Enum completeness
# =========================================================================


class TestEnums:
    """Verify enums have expected members."""

    def test_node_type_count(self):
        """NodeType has 13 members."""
        assert len(NodeType) == 13

    def test_relationship_type_count(self):
        """RelationshipType has 14 members."""
        assert len(RelationshipType) == 14

    def test_node_type_values_are_strings(self):
        """Every NodeType value is a non-empty string."""
        for nt in NodeType:
            assert isinstance(nt.value, str) and len(nt.value) > 0

    def test_relationship_type_values_uppercase(self):
        """RelationshipType values are UPPER_CASE by convention."""
        for rt in RelationshipType:
            assert rt.value == rt.value.upper()


# =========================================================================
# Section 2 — BaseNode
# =========================================================================


class TestBaseNode:
    """Tests for the BaseNode dataclass."""

    def test_default_id_is_uuid(self):
        """BaseNode generates a UUID id by default."""
        node = BaseNode()
        # Should be a valid UUID string
        uuid.UUID(node.id)  # raises ValueError if invalid

    def test_default_timestamp_is_recent(self):
        """BaseNode timestamp is close to current time."""
        before = time.time()
        node = BaseNode()
        after = time.time()
        assert before <= node.timestamp <= after

    def test_to_dict_has_required_keys(self):
        """BaseNode.to_dict includes id, timestamp, metadata."""
        node = BaseNode(metadata={"key": "val"})
        d = node.to_dict()
        assert "id" in d
        assert "timestamp" in d
        assert "metadata" in d
        # metadata is JSON-serialized
        assert json.loads(d["metadata"]) == {"key": "val"}


# =========================================================================
# Section 3 — Concrete node types
# =========================================================================


class TestUIElementNode:
    """Tests for UIElementNode."""

    def test_creation_with_fields(self):
        """UIElementNode stores all provided fields."""
        node = UIElementNode(
            type="button",
            text="Save",
            coordinates=[100, 200],
            confidence=0.95,
            application="notepad",
        )
        assert node.type == "button"
        assert node.text == "Save"
        assert node.confidence == 0.95

    def test_to_dict_includes_ui_fields(self):
        """to_dict includes UI-specific fields."""
        node = UIElementNode(type="menu", text="File")
        d = node.to_dict()
        assert d["type"] == "menu"
        assert d["text"] == "File"


class TestWorkflowNode:
    """Tests for WorkflowNode."""

    def test_default_status_is_pending(self):
        """WorkflowNode defaults to 'pending' status."""
        wf = WorkflowNode(name="test_wf")
        assert wf.status == "pending"

    def test_to_dict_serializes_steps(self):
        """Steps list is JSON-serialized in to_dict."""
        steps = [{"action": "click", "target": "save_button"}]
        wf = WorkflowNode(name="wf", steps=steps)
        d = wf.to_dict()
        assert json.loads(d["steps"]) == steps


class TestCommunityNode:
    """Tests for CommunityNode."""

    def test_members_stored(self):
        """CommunityNode stores member IDs."""
        cn = CommunityNode(purpose="file_ops", members=["n1", "n2"])
        assert "n1" in cn.members

    def test_to_dict_serializes_members(self):
        """Members list is JSON-serialized."""
        cn = CommunityNode(members=["a", "b"])
        d = cn.to_dict()
        assert json.loads(d["members"]) == ["a", "b"]


class TestMemoryNodes:
    """Tests for memory-specific node types."""

    def test_memory_item_node(self):
        """MemoryItemNode stores content and tags."""
        mi = MemoryItemNode(content="test memory", tags=["tag1", "tag2"])
        assert mi.content == "test memory"
        d = mi.to_dict()
        assert json.loads(d["tags"]) == ["tag1", "tag2"]

    def test_memory_session_node(self):
        """MemorySessionNode defaults to 'active' status."""
        ms = MemorySessionNode(session_name="s1", user_id="u1")
        assert ms.status == "active"

    def test_user_profile_node(self):
        """UserProfileNode stores preferences."""
        up = UserProfileNode(user_id="u1", preferences={"theme": "dark"})
        d = up.to_dict()
        assert json.loads(d["preferences"]) == {"theme": "dark"}

    def test_memory_pattern_node(self):
        """MemoryPatternNode defaults to 'behavioral' type."""
        mp = MemoryPatternNode(pattern_name="p1")
        assert mp.pattern_type == "behavioral"


# =========================================================================
# Section 4 — Relationship
# =========================================================================


class TestRelationship:
    """Tests for the Relationship dataclass."""

    def test_creation(self):
        """Relationship stores from/to/type correctly."""
        rel = Relationship(
            from_node="n1",
            to_node="n2",
            relationship_type=RelationshipType.CONTAINS,
        )
        assert rel.from_node == "n1"
        assert rel.weight == 1.0  # default

    def test_to_dict(self):
        """to_dict includes type as string value."""
        rel = Relationship("a", "b", RelationshipType.TRIGGERS, weight=0.5)
        d = rel.to_dict()
        assert d["type"] == "TRIGGERS"
        assert d["weight"] == 0.5


# =========================================================================
# Section 5 — KnowledgeGraphSchema
# =========================================================================


class TestKnowledgeGraphSchema:
    """Tests for the KnowledgeGraphSchema class methods."""

    def test_create_node_ui_element(self):
        """create_node returns UIElementNode for UI_ELEMENT type."""
        node = KnowledgeGraphSchema.create_node(NodeType.UI_ELEMENT, type="button", text="OK")
        assert isinstance(node, UIElementNode)
        assert node.text == "OK"

    def test_create_node_workflow(self):
        """create_node returns WorkflowNode for WORKFLOW type."""
        node = KnowledgeGraphSchema.create_node(NodeType.WORKFLOW, name="deploy")
        assert isinstance(node, WorkflowNode)

    def test_create_node_invalid_type_raises(self):
        """create_node raises ValueError for types not in NODE_CLASSES."""
        # MEMORY_ITEM is not in NODE_CLASSES (it was added to the schema
        # but not registered in the class map)
        with pytest.raises(ValueError, match="Unknown node type"):
            KnowledgeGraphSchema.create_node(NodeType.MEMORY_ITEM)

    def test_create_relationship(self):
        """create_relationship returns a Relationship with correct fields."""
        rel = KnowledgeGraphSchema.create_relationship(
            "n1", "n2", RelationshipType.SIMILAR_TO, weight=0.8
        )
        assert isinstance(rel, Relationship)
        assert rel.weight == 0.8

    def test_validate_node_valid(self):
        """validate_node returns True for a well-formed node."""
        node = BaseNode()
        assert KnowledgeGraphSchema.validate_node(node) is True

    def test_validate_node_missing_id(self):
        """validate_node returns False when id is empty."""
        node = BaseNode(id="")
        assert KnowledgeGraphSchema.validate_node(node) is False

    def test_cypher_create_node(self):
        """get_cypher_create_node generates valid-looking Cypher."""
        node = UIElementNode(type="button", text="Save", confidence=0.95)
        result = KnowledgeGraphSchema.get_cypher_create_node(node, NodeType.UI_ELEMENT)
        # After Cypher injection fix, returns (query, params) tuple
        if isinstance(result, tuple):
            cypher, params = result
            assert cypher.startswith("CREATE")
            assert "UIElement" in cypher
            assert "RETURN n.id as id" in cypher
        else:
            cypher = result
            assert cypher.startswith("CREATE")
            assert "UIElement" in cypher
            assert "RETURN n.id as id" in cypher
            assert "Save" in cypher

    def test_cypher_create_relationship(self):
        """get_cypher_create_relationship generates valid-looking Cypher."""
        rel = Relationship("n1", "n2", RelationshipType.TRIGGERS, weight=0.7)
        result = KnowledgeGraphSchema.get_cypher_create_relationship(rel)
        if isinstance(result, tuple):
            cypher, params = result
        else:
            cypher = result
        assert "MATCH" in cypher
        assert "TRIGGERS" in cypher
        # After parameterization, IDs are in params not in query string
        if isinstance(result, tuple):
            assert "$from_id" in cypher or "$to_id" in cypher
        else:
            assert "n1" in cypher
            assert "n2" in cypher

    def test_cypher_node_contains_id(self):
        """Generated Cypher includes the node's id property."""
        node = UIElementNode(id="test-id-123", type="input")
        result = KnowledgeGraphSchema.get_cypher_create_node(node, NodeType.UI_ELEMENT)
        # After parameterization, id is in params dict
        if isinstance(result, tuple):
            cypher, params = result
            assert params.get("prop_id") == "test-id-123"
        else:
            assert "test-id-123" in result


# =========================================================================
# Section 6 — Factory functions
# =========================================================================


class TestFactoryFunctions:
    """Tests for convenience factory functions."""

    def test_create_ui_element_factory(self):
        """create_ui_element returns UIElementNode."""
        node = create_ui_element("button", "OK", [10, 20], 0.9)
        assert isinstance(node, UIElementNode)
        assert node.type == "button"

    def test_create_community_factory(self):
        """create_community sets size from members list."""
        node = create_community("ops", ["a", "b", "c"], 0.8)
        assert isinstance(node, CommunityNode)
        assert node.size == 3

    def test_create_workflow_factory(self):
        """create_workflow returns WorkflowNode."""
        node = create_workflow("deploy", "deploy app", [{"step": 1}])
        assert isinstance(node, WorkflowNode)
        assert node.name == "deploy"

    def test_create_memory_item_factory(self):
        """create_memory_item returns MemoryItemNode."""
        node = create_memory_item("fact", "general", "user1")
        assert isinstance(node, MemoryItemNode)
        assert node.user_id == "user1"

    def test_create_memory_session_factory(self):
        """create_memory_session returns MemorySessionNode."""
        node = create_memory_session("sess1", "user1", "agent1")
        assert isinstance(node, MemorySessionNode)

    def test_create_user_profile_factory(self):
        """create_user_profile returns UserProfileNode."""
        node = create_user_profile("u1", "alice")
        assert isinstance(node, UserProfileNode)
        assert node.username == "alice"

    def test_create_memory_pattern_factory(self):
        """create_memory_pattern returns MemoryPatternNode."""
        node = create_memory_pattern("pat1", "temporal", "u1")
        assert isinstance(node, MemoryPatternNode)
        assert node.pattern_type == "temporal"


# =========================================================================
# Section 7 — SchemaManager (requires Neo4j — skip if unavailable)
# =========================================================================


@pytest.mark.skip(reason="Requires live Neo4j/Memgraph instance")
class TestSchemaManager:
    """
    Integration tests for SchemaManager.
    Un-skip these when a Neo4j/Memgraph service is available.
    """

    def test_create_and_get_node(self):
        from asi_build.graph_intelligence.schema_manager import SchemaManager

        with SchemaManager() as sm:
            node = create_ui_element("button", "Test", [0, 0], 0.9)
            node_id = sm.create_node(node, NodeType.UI_ELEMENT)
            retrieved = sm.get_node(node_id, NodeType.UI_ELEMENT)
            assert retrieved is not None
            sm.delete_node(node_id)
