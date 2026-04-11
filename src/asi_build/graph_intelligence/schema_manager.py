"""
Schema Manager for Kenny Graph Intelligence System

Handles schema validation, migrations, and database operations.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from neo4j import GraphDatabase

from .schema import (
    ApplicationNode,
    BaseNode,
    CommunityNode,
    ErrorNode,
    KnowledgeGraphSchema,
    NodeType,
    PatternNode,
    Relationship,
    RelationshipType,
    ScreenNode,
    UIElementNode,
    WorkflowNode,
    _sanitize_label,
)

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages schema operations for the knowledge graph."""

    def __init__(self, uri: str = "bolt://localhost:7687"):
        self.driver = GraphDatabase.driver(uri)
        self.schema = KnowledgeGraphSchema()

    def close(self):
        """Close database connection."""
        self.driver.close()

    def create_node(self, node: BaseNode, node_type: NodeType) -> str:
        """Create a node in the database."""
        with self.driver.session() as session:
            cypher, params = self.schema.get_cypher_create_node(node, node_type)
            try:
                result = session.run(cypher, **params)
                record = result.single()
                node_id = record["id"] if record else node.id
                logger.info(f"✅ Created {node_type.value} node: {node_id}")
                return node_id
            except Exception as e:
                logger.error(f"❌ Failed to create {node_type.value} node: {e}")
                raise

    def create_relationship(self, rel: Relationship) -> bool:
        """Create a relationship in the database."""
        with self.driver.session() as session:
            cypher, params = self.schema.get_cypher_create_relationship(rel)
            try:
                result = session.run(cypher, **params)
                record = result.single()
                rel_type = record["relationship_type"] if record else rel.relationship_type.value
                logger.info(f"✅ Created {rel_type} relationship: {rel.from_node} -> {rel.to_node}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create relationship: {e}")
                return False

    def get_node(
        self, node_id: str, node_type: Optional[NodeType] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a node by ID."""
        with self.driver.session() as session:
            if node_type:
                safe_label = _sanitize_label(node_type.value)
                cypher = f"MATCH (n:{safe_label} {{id: $node_id}}) RETURN n"
            else:
                cypher = "MATCH (n {id: $node_id}) RETURN n"

            try:
                result = session.run(cypher, node_id=node_id)
                record = result.single()
                return dict(record["n"]) if record else None
            except Exception as e:
                logger.error(f"❌ Failed to get node {node_id}: {e}")
                return None

    def update_node(
        self, node_id: str, properties: Dict[str, Any], node_type: Optional[NodeType] = None
    ) -> bool:
        """Update node properties."""
        with self.driver.session() as session:
            # Build parameterized SET clause
            params: Dict[str, Any] = {"node_id": node_id}
            set_clauses = []
            for key, value in properties.items():
                safe_key = _sanitize_label(key)
                param_name = f"upd_{safe_key}"
                if isinstance(value, (str, int, float, bool)):
                    params[param_name] = value
                elif isinstance(value, list):
                    params[param_name] = value
                else:
                    params[param_name] = str(value)
                set_clauses.append(f"n.{safe_key} = ${param_name}")

            set_clause = ", ".join(set_clauses)

            if node_type:
                safe_label = _sanitize_label(node_type.value)
                cypher = (
                    f"MATCH (n:{safe_label} {{id: $node_id}}) SET {set_clause} RETURN n.id as id"
                )
            else:
                cypher = f"MATCH (n {{id: $node_id}}) SET {set_clause} RETURN n.id as id"

            try:
                result = session.run(cypher, **params)
                record = result.single()
                success = record is not None
                if success:
                    logger.info(f"✅ Updated node {node_id}")
                return success
            except Exception as e:
                logger.error(f"❌ Failed to update node {node_id}: {e}")
                return False

    def delete_node(self, node_id: str, node_type: Optional[NodeType] = None) -> bool:
        """Delete a node and its relationships."""
        with self.driver.session() as session:
            if node_type:
                safe_label = _sanitize_label(node_type.value)
                cypher = f"MATCH (n:{safe_label} {{id: $node_id}}) DETACH DELETE n"
            else:
                cypher = "MATCH (n {id: $node_id}) DETACH DELETE n"

            try:
                session.run(cypher, node_id=node_id)
                logger.info(f"✅ Deleted node {node_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to delete node {node_id}: {e}")
                return False

    def find_nodes(
        self, node_type: NodeType, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find nodes by type and optional filters."""
        with self.driver.session() as session:
            safe_label = _sanitize_label(node_type.value)
            cypher = f"MATCH (n:{safe_label})"
            params: Dict[str, Any] = {"query_limit": int(limit)}

            if filters:
                where_clauses = []
                for idx, (key, value) in enumerate(filters.items()):
                    safe_key = _sanitize_label(key)
                    param_name = f"filter_{idx}"
                    params[param_name] = value
                    where_clauses.append(f"n.{safe_key} = ${param_name}")

                if where_clauses:
                    cypher += " WHERE " + " AND ".join(where_clauses)

            cypher += " RETURN n LIMIT $query_limit"

            try:
                result = session.run(cypher, **params)
                return [dict(record["n"]) for record in result]
            except Exception as e:
                logger.error(f"❌ Failed to find {node_type.value} nodes: {e}")
                return []

    def find_relationships(
        self,
        from_node: Optional[str] = None,
        to_node: Optional[str] = None,
        rel_type: Optional[RelationshipType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Find relationships with optional filters."""
        with self.driver.session() as session:
            params: Dict[str, Any] = {"query_limit": int(limit)}

            if rel_type:
                safe_rel = _sanitize_label(rel_type.value)
                cypher = f"MATCH (a)-[r:{safe_rel}]->(b)"
            else:
                cypher = "MATCH (a)-[r]->(b)"

            where_clauses = []
            if from_node:
                params["from_node_id"] = from_node
                where_clauses.append("a.id = $from_node_id")
            if to_node:
                params["to_node_id"] = to_node
                where_clauses.append("b.id = $to_node_id")

            if where_clauses:
                cypher += " WHERE " + " AND ".join(where_clauses)

            cypher += (
                " RETURN a.id as from_id, type(r) as rel_type, b.id as to_id, r LIMIT $query_limit"
            )

            try:
                result = session.run(cypher, **params)
                relationships = []
                for record in result:
                    relationships.append(
                        {
                            "from_id": record["from_id"],
                            "to_id": record["to_id"],
                            "type": record["rel_type"],
                            "properties": dict(record["r"]),
                        }
                    )
                return relationships
            except Exception as e:
                logger.error(f"❌ Failed to find relationships: {e}")
                return []

    def get_node_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        rel_type: Optional[RelationshipType] = None,
        max_hops: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get neighboring nodes."""
        with self.driver.session() as session:
            if direction == "outgoing":
                arrow = "->"
            elif direction == "incoming":
                arrow = "<-"
            else:
                arrow = "-"

            rel_pattern = f":{_sanitize_label(rel_type.value)}" if rel_type else ""
            # max_hops must be a positive integer — sanitize to prevent injection
            safe_hops = max(1, int(max_hops))

            cypher = f"""
            MATCH (start {{id: $node_id}}){arrow}[r{rel_pattern}*1..{safe_hops}]{arrow}(neighbor)
            RETURN neighbor, r
            """

            try:
                result = session.run(cypher, node_id=node_id)
                neighbors = []
                for record in result:
                    neighbor = dict(record["neighbor"])
                    relationships = [dict(r) for r in record["r"]]
                    neighbors.append({"node": neighbor, "relationships": relationships})
                return neighbors
            except Exception as e:
                logger.error(f"❌ Failed to get neighbors for {node_id}: {e}")
                return []

    def get_communities_containing_node(self, node_id: str) -> List[Dict[str, Any]]:
        """Find all communities that contain a specific node."""
        with self.driver.session() as session:
            cypher = """
            MATCH (c:Community)-[:CONTAINS]->(n {id: $node_id})
            RETURN c
            """

            try:
                result = session.run(cypher, node_id=node_id)
                return [dict(record["c"]) for record in result]
            except Exception as e:
                logger.error(f"❌ Failed to find communities for node {node_id}: {e}")
                return []

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get all steps for a workflow in order."""
        with self.driver.session() as session:
            cypher = """
            MATCH (w:Workflow {id: $workflow_id})-[:CONTAINS]->(step)
            RETURN step
            ORDER BY step.sequence_number
            """

            try:
                result = session.run(cypher, workflow_id=workflow_id)
                return [dict(record["step"]) for record in result]
            except Exception as e:
                logger.error(f"❌ Failed to get workflow steps for {workflow_id}: {e}")
                return []

    def validate_schema_consistency(self) -> Dict[str, Any]:
        """Validate schema consistency and integrity."""
        validation_results = {"consistent": True, "issues": [], "statistics": {}}

        with self.driver.session() as session:
            try:
                # Check for orphaned nodes (nodes without required relationships)
                orphaned_ui_elements = session.run("""
                    MATCH (ui:UIElement)
                    WHERE NOT (ui)-[:BELONGS_TO]->(:Community)
                    RETURN count(ui) as count
                """).single()["count"]

                if orphaned_ui_elements > 0:
                    validation_results["issues"].append(
                        f"{orphaned_ui_elements} UI elements not assigned to communities"
                    )

                # Check for invalid relationships
                invalid_rels = session.run("""
                    MATCH (a)-[r]->(b)
                    WHERE NOT exists(a.id) OR NOT exists(b.id)
                    RETURN count(r) as count
                """).single()["count"]

                if invalid_rels > 0:
                    validation_results["issues"].append(
                        f"{invalid_rels} relationships with invalid node references"
                    )
                    validation_results["consistent"] = False

                # Get statistics
                node_stats = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(n) as count
                    ORDER BY count DESC
                """)

                validation_results["statistics"]["nodes"] = {
                    record["type"]: record["count"] for record in node_stats
                }

                rel_stats = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """)

                validation_results["statistics"]["relationships"] = {
                    record["type"]: record["count"] for record in rel_stats
                }

            except Exception as e:
                validation_results["consistent"] = False
                validation_results["issues"].append(f"Validation error: {e}")

        return validation_results

    def export_schema_sample(self, sample_size: int = 10) -> Dict[str, Any]:
        """Export a sample of the schema for inspection."""
        sample_data = {"nodes": {}, "relationships": []}

        # Sample nodes from each type
        for node_type in NodeType:
            nodes = self.find_nodes(node_type, limit=sample_size)
            if nodes:
                sample_data["nodes"][node_type.value] = nodes

        # Sample relationships
        relationships = self.find_relationships(limit=sample_size * 2)
        sample_data["relationships"] = relationships

        return sample_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Test the schema manager
if __name__ == "__main__":
    print("🧪 Testing Schema Manager...")

    with SchemaManager() as sm:
        # Create test UI element
        from .schema import create_ui_element

        button = create_ui_element(
            element_type="button",
            text="Test Save Button",
            coordinates=[200, 300],
            confidence=0.98,
            application="test_app",
        )

        # Create the node in database
        node_id = sm.create_node(button, NodeType.UI_ELEMENT)
        print(f"✅ Created test node: {node_id}")

        # Retrieve the node
        retrieved = sm.get_node(node_id, NodeType.UI_ELEMENT)
        print(f"✅ Retrieved node: {retrieved['text'] if retrieved else 'None'}")

        # Update the node
        updated = sm.update_node(node_id, {"confidence": 0.99}, NodeType.UI_ELEMENT)
        print(f"✅ Updated node: {updated}")

        # Find nodes
        ui_elements = sm.find_nodes(NodeType.UI_ELEMENT, {"type": "button"})
        print(f"✅ Found {len(ui_elements)} button elements")

        # Validate schema
        validation = sm.validate_schema_consistency()
        print(f"✅ Schema consistent: {validation['consistent']}")
        print(f"   Issues: {len(validation['issues'])}")

        # Clean up test data
        deleted = sm.delete_node(node_id, NodeType.UI_ELEMENT)
        print(f"✅ Cleaned up test data: {deleted}")

    print("✅ Schema Manager testing completed!")
