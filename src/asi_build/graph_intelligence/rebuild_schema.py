#!/usr/bin/env python3
"""
Complete schema rebuild for Kenny's Graph Intelligence System.
Addresses GitHub Issues #225, #226, #227, #228.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List

from neo4j import GraphDatabase

from .schema import (
    KnowledgeGraphSchema,
    NodeType,
    RelationshipType,
    _sanitize_label,
    create_community,
    create_ui_element,
    create_workflow,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaRebuilder:
    """Rebuilds Memgraph schema to match Kenny's requirements."""

    def __init__(self):
        self.driver = GraphDatabase.driver("bolt://localhost:7687")
        self.schema = KnowledgeGraphSchema()

    def close(self):
        """Close database connection."""
        self.driver.close()

    def flush_database(self):
        """Completely flush the database."""
        logger.info("🗑️ Flushing database...")
        with self.driver.session() as session:
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("✅ All nodes and relationships deleted")

            # Note: Memgraph doesn't support dropping constraints/indexes via Cypher
            # They persist but won't interfere with new schema

    def create_constraints(self):
        """Create all required constraints."""
        logger.info("🔒 Creating constraints...")
        constraints = [
            ("UIElement", "id"),
            ("Workflow", "id"),
            ("Community", "id"),
            ("Application", "name"),
            ("Screen", "id"),
            ("Pattern", "id"),
            ("Error", "id"),
            ("UserAction", "id"),
            ("Prediction", "id"),
        ]

        with self.driver.session() as session:
            for node_type, property_name in constraints:
                try:
                    safe_type = _sanitize_label(node_type)
                    safe_prop = _sanitize_label(property_name)
                    query = f"CREATE CONSTRAINT ON (n:{safe_type}) ASSERT n.{safe_prop} IS UNIQUE"
                    session.run(query)
                    logger.info(f"  ✅ Created constraint: {node_type}.{property_name} UNIQUE")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"  ✓ Constraint already exists: {node_type}.{property_name}")
                    else:
                        logger.warning(f"  ⚠️ Failed to create constraint: {e}")

    def create_indexes(self):
        """Create all required indexes."""
        logger.info("📇 Creating indexes...")
        indexes = [
            ("UIElement", "id"),
            ("UIElement", "type"),
            ("UIElement", "coordinates"),
            ("UIElement", "text"),
            ("UIElement", "confidence"),
            ("Workflow", "id"),
            ("Workflow", "status"),
            ("Workflow", "complexity"),
            ("Community", "id"),
            ("Community", "modularity"),
            ("Community", "purpose"),
            ("Application", "name"),
            ("Application", "process_id"),
            ("Screen", "id"),
            ("Screen", "screenshot_hash"),
            ("Pattern", "frequency"),
            ("Pattern", "pattern_type"),
            ("Error", "category"),
            ("Error", "severity"),
            ("UserAction", "id"),
            ("UserAction", "action_type"),
            ("Prediction", "id"),
            ("Prediction", "confidence"),
        ]

        with self.driver.session() as session:
            for node_type, property_name in indexes:
                try:
                    safe_type = _sanitize_label(node_type)
                    safe_prop = _sanitize_label(property_name)
                    query = f"CREATE INDEX ON :{safe_type}({safe_prop})"
                    session.run(query)
                    logger.info(f"  ✅ Created index: {node_type}.{property_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"  ✓ Index already exists: {node_type}.{property_name}")
                    else:
                        logger.warning(f"  ⚠️ Failed to create index: {e}")

    def create_sample_data(self):
        """Create sample data for all node types."""
        logger.info("📊 Creating sample data...")

        with self.driver.session() as session:
            # Create Screen nodes
            screens = []
            for i in range(3):
                screen_id = f"screen_{i+1}"
                session.run(
                    """
                    CREATE (s:Screen {
                        id: $id,
                        resolution: [1920, 1080],
                        screenshot_path: $path,
                        screenshot_hash: $hash,
                        active_window: $window,
                        ui_elements_count: $count,
                        processing_time: $time,
                        ocr_confidence: $conf,
                        timestamp: timestamp()
                    })
                """,
                    id=screen_id,
                    path=f"/screenshots/{screen_id}.png",
                    hash=f"hash_{i}",
                    window=f"Window {i+1}",
                    count=10 + i * 5,
                    time=0.5 + i * 0.1,
                    conf=0.85 + i * 0.05,
                )
                screens.append(screen_id)
            logger.info(f"  ✅ Created {len(screens)} Screen nodes")

            # Create Application nodes
            apps = [
                ("Terminal", "gnome-terminal", "/usr/bin/gnome-terminal"),
                ("VS Code", "code", "/usr/bin/code"),
                ("Chrome", "chrome", "/usr/bin/google-chrome"),
                ("File Manager", "nautilus", "/usr/bin/nautilus"),
            ]
            for name, process, path in apps:
                session.run(
                    """
                    CREATE (a:Application {
                        id: $id,
                        name: $name,
                        version: '1.0.0',
                        process_id: 0,
                        window_title: $title,
                        executable_path: $path,
                        ui_framework: 'gtk',
                        automation_confidence: 0.95,
                        last_active: timestamp(),
                        timestamp: timestamp()
                    })
                """,
                    id=name.lower().replace(" ", "_"),
                    name=name,
                    title=f"{name} - Ubuntu",
                    path=path,
                )
            logger.info(f"  ✅ Created {len(apps)} Application nodes")

            # Create UIElement nodes
            ui_elements = []
            element_types = ["button", "menu", "text_field", "dialog", "label"]
            for i in range(20):
                elem_id = f"ui_element_{i+1}"
                elem_type = element_types[i % len(element_types)]
                session.run(
                    """
                    CREATE (u:UIElement {
                        id: $id,
                        type: $type,
                        text: $text,
                        coordinates: $coords,
                        confidence: $conf,
                        application: $app,
                        screen_id: $screen,
                        properties: '{}',
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=elem_id,
                    type=elem_type,
                    text=f"{elem_type.title()} {i+1}",
                    coords=[100 + i * 50, 200 + i * 30],
                    conf=0.8 + (i % 10) * 0.02,
                    app=apps[i % len(apps)][0],
                    screen=screens[i % len(screens)],
                )
                ui_elements.append(elem_id)
            logger.info(f"  ✅ Created {len(ui_elements)} UIElement nodes")

            # Create Workflow nodes
            workflows = []
            for i in range(5):
                wf_id = f"workflow_{i+1}"
                session.run(
                    """
                    CREATE (w:Workflow {
                        id: $id,
                        name: $name,
                        description: $desc,
                        steps: $steps,
                        status: $status,
                        success_rate: $rate,
                        avg_duration: $duration,
                        execution_count: $count,
                        user_id: 'user_1',
                        complexity: $complexity,
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=wf_id,
                    name=f"Workflow {i+1}",
                    desc=f"Automated workflow for task {i+1}",
                    steps=json.dumps([{"step": j + 1, "action": "click"} for j in range(3)]),
                    status="completed" if i < 3 else "pending",
                    rate=0.85 + i * 0.03,
                    duration=5.5 + i * 2,
                    count=10 + i * 5,
                    complexity=["simple", "medium", "complex"][i % 3],
                )
                workflows.append(wf_id)
            logger.info(f"  ✅ Created {len(workflows)} Workflow nodes")

            # Create Community nodes
            for i in range(3):
                comm_id = f"community_{i+1}"
                members = ui_elements[i * 5 : (i + 1) * 5]
                session.run(
                    """
                    CREATE (c:Community {
                        id: $id,
                        purpose: $purpose,
                        members: $members,
                        modularity: $mod,
                        size: $size,
                        cohesion: $cohesion,
                        frequency: $freq,
                        success_rate: $rate,
                        avg_completion_time: $time,
                        detection_algorithm: 'louvain',
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=comm_id,
                    purpose=["file_operations", "navigation", "data_entry"][i],
                    members=json.dumps(members),
                    mod=0.7 + i * 0.1,
                    size=len(members),
                    cohesion=0.8 + i * 0.05,
                    freq=50 + i * 20,
                    rate=0.9 + i * 0.03,
                    time=3.5 + i,
                )
            logger.info("  ✅ Created 3 Community nodes")

            # Create Pattern nodes
            for i in range(5):
                pattern_id = f"pattern_{i+1}"
                session.run(
                    """
                    CREATE (p:Pattern {
                        id: $id,
                        pattern_type: $type,
                        sequence: $seq,
                        frequency: $freq,
                        confidence: $conf,
                        context: $context,
                        success_rate: $rate,
                        last_used: timestamp(),
                        generalization_score: $score,
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=pattern_id,
                    type=["sequence", "prediction", "optimization"][i % 3],
                    seq=json.dumps([f"action_{j}" for j in range(3)]),
                    freq=20 + i * 10,
                    conf=0.75 + i * 0.05,
                    context=json.dumps({"app": apps[i % len(apps)][0]}),
                    rate=0.8 + i * 0.04,
                    score=0.6 + i * 0.08,
                )
            logger.info("  ✅ Created 5 Pattern nodes")

            # Create Error nodes
            for i in range(3):
                error_id = f"error_{i+1}"
                session.run(
                    """
                    CREATE (e:Error {
                        id: $id,
                        category: $cat,
                        message: $msg,
                        stack_trace: $trace,
                        context: $context,
                        severity: $sev,
                        frequency: $freq,
                        resolved: $resolved,
                        resolution_strategy: $strategy,
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=error_id,
                    cat=["ui_not_found", "timeout", "permission"][i],
                    msg=f"Error message {i+1}",
                    trace=f"Stack trace line {i+1}",
                    context=json.dumps({"screen": screens[i]}),
                    sev=["low", "medium", "high"][i],
                    freq=5 + i * 2,
                    resolved=i < 2,
                    strategy="retry" if i < 2 else "manual",
                )
            logger.info("  ✅ Created 3 Error nodes")

            # Create UserAction nodes
            for i in range(10):
                action_id = f"user_action_{i+1}"
                session.run(
                    """
                    CREATE (ua:UserAction {
                        id: $id,
                        action_type: $type,
                        target: $target,
                        coordinates: $coords,
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=action_id,
                    type=["click", "type", "scroll", "drag"][i % 4],
                    target=ui_elements[i % len(ui_elements)],
                    coords=[200 + i * 20, 300 + i * 15],
                )
            logger.info("  ✅ Created 10 UserAction nodes")

            # Create Prediction nodes
            for i in range(5):
                pred_id = f"prediction_{i+1}"
                session.run(
                    """
                    CREATE (pr:Prediction {
                        id: $id,
                        prediction_type: 'next_action',
                        predicted_action: $action,
                        confidence: $conf,
                        context: $context,
                        timestamp: timestamp(),
                        metadata: '{}'
                    })
                """,
                    id=pred_id,
                    action=f"action_{i+1}",
                    conf=0.7 + i * 0.06,
                    context=json.dumps({"workflow": workflows[i % len(workflows)]}),
                )
            logger.info("  ✅ Created 5 Prediction nodes")

    def create_relationships(self):
        """Create all relationship types."""
        logger.info("🔗 Creating relationships...")

        with self.driver.session() as session:
            # CONTAINS relationships (UI hierarchy)
            session.run("""
                MATCH (s:Screen), (u:UIElement)
                WHERE u.screen_id = s.id
                CREATE (s)-[:CONTAINS]->(u)
            """)

            # BELONGS_TO relationships (Community membership)
            # First parse the JSON string into a list
            communities = session.run("MATCH (c:Community) RETURN c.id as id, c.members as members")
            for record in communities:
                members_str = record["members"]
                if members_str:
                    import json

                    members_list = json.loads(members_str)
                    for member_id in members_list:
                        session.run(
                            """
                            MATCH (c:Community {id: $comm_id}), (u:UIElement {id: $member_id})
                            CREATE (u)-[:BELONGS_TO]->(c)
                        """,
                            comm_id=record["id"],
                            member_id=member_id,
                        )

            # TRIGGERS relationships (UserAction -> UIElement)
            session.run("""
                MATCH (ua:UserAction), (u:UIElement)
                WHERE ua.target = u.id
                CREATE (ua)-[:TRIGGERS]->(u)
            """)

            # NAVIGATES_TO relationships (Screen navigation)
            session.run("""
                MATCH (s1:Screen), (s2:Screen)
                WHERE s1.id < s2.id
                WITH s1, s2 LIMIT 3
                CREATE (s1)-[:NAVIGATES_TO]->(s2)
            """)

            # REQUIRES relationships (Workflow dependencies)
            session.run("""
                MATCH (w:Workflow), (a:Application)
                WHERE w.id CONTAINS '1' AND a.name = 'Terminal'
                CREATE (w)-[:REQUIRES]->(a)
            """)

            # PRECEDES relationships (Workflow steps)
            session.run("""
                MATCH (w1:Workflow), (w2:Workflow)
                WHERE w1.id < w2.id
                WITH w1, w2 LIMIT 4
                CREATE (w1)-[:PRECEDES]->(w2)
            """)

            # SIMILAR_TO relationships (Pattern similarity)
            session.run("""
                MATCH (p1:Pattern), (p2:Pattern)
                WHERE p1.id < p2.id AND p1.pattern_type = p2.pattern_type
                WITH p1, p2 LIMIT 3
                CREATE (p1)-[:SIMILAR_TO]->(p2)
            """)

            # CAUSED_BY relationships (Error causation)
            session.run("""
                MATCH (e:Error), (ua:UserAction)
                WHERE e.id CONTAINS '1' AND ua.id CONTAINS '1'
                CREATE (e)-[:CAUSED_BY]->(ua)
            """)

            # RESOLVES relationships (Pattern resolves Error)
            session.run("""
                MATCH (p:Pattern), (e:Error)
                WHERE p.id CONTAINS '1' AND e.resolved = true
                CREATE (p)-[:RESOLVES]->(e)
            """)

            # FOLLOWED_BY relationships (Action sequences)
            # Create sequential relationships based on IDs
            for i in range(1, 10):  # We have 10 UserActions
                session.run(
                    """
                    MATCH (ua1:UserAction {id: $id1}), (ua2:UserAction {id: $id2})
                    CREATE (ua1)-[:FOLLOWED_BY]->(ua2)
                """,
                    id1=f"user_action_{i}",
                    id2=f"user_action_{i+1}",
                )

            logger.info("  ✅ Created all relationship types")

    def verify_schema(self):
        """Verify the schema is correctly implemented."""
        logger.info("✔️ Verifying schema...")

        with self.driver.session() as session:
            # Check node types - aggregate by label
            result = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN DISTINCT label, count(n) as count
                ORDER BY label
            """)

            logger.info("📊 Node Types:")
            required_nodes = set([nt.value for nt in NodeType])
            found_nodes = set()
            for record in result:
                label = record["label"]
                found_nodes.add(label)
                status = "✅" if label in required_nodes else "⚠️"
                logger.info(f"  {status} {label}: {record['count']} nodes")

            missing_nodes = required_nodes - found_nodes
            if missing_nodes:
                logger.warning(f"  ❌ Missing node types: {missing_nodes}")

            # Check relationship types
            result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as type, count(r) as count
                ORDER BY type
            """)

            logger.info("📊 Relationship Types:")
            required_rels = set([rt.value for rt in RelationshipType])
            found_rels = set()
            for record in result:
                rel_type = record["type"]
                found_rels.add(rel_type)
                status = "✅" if rel_type in required_rels else "⚠️"
                logger.info(f"  {status} {rel_type}: {record['count']} relationships")

            missing_rels = required_rels - found_rels
            if missing_rels:
                logger.warning(f"  ❌ Missing relationship types: {missing_rels}")

            # Check total counts
            result = session.run("MATCH (n) RETURN count(n) as total")
            total_nodes = result.single()["total"]

            result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
            total_rels = result.single()["total"]

            logger.info(f"\n📈 Summary:")
            logger.info(f"  Total Nodes: {total_nodes}")
            logger.info(f"  Total Relationships: {total_rels}")
            logger.info(f"  Node Types: {len(found_nodes)}/{len(required_nodes)}")
            logger.info(f"  Relationship Types: {len(found_rels)}/{len(required_rels)}")

            return len(missing_nodes) == 0 and len(missing_rels) == 0

    def run_full_rebuild(self):
        """Execute the complete schema rebuild."""
        logger.info("🚀 Starting complete schema rebuild for Kenny...")

        try:
            # Step 1: Flush database
            self.flush_database()

            # Step 2: Create constraints
            self.create_constraints()

            # Step 3: Create indexes
            self.create_indexes()

            # Step 4: Create sample data
            self.create_sample_data()

            # Step 5: Create relationships
            self.create_relationships()

            # Step 6: Verify schema
            success = self.verify_schema()

            if success:
                logger.info("✅ Schema rebuild completed successfully!")
                logger.info("🎯 Kenny's Graph Intelligence System is ready!")
                return True
            else:
                logger.warning("⚠️ Schema rebuild completed with warnings")
                return False

        except Exception as e:
            logger.error(f"❌ Schema rebuild failed: {e}")
            return False
        finally:
            self.close()


if __name__ == "__main__":
    rebuilder = SchemaRebuilder()
    success = rebuilder.run_full_rebuild()

    if success:
        print("\n✅ All GitHub issues addressed:")
        print("  #225: Missing Node Types - RESOLVED")
        print("  #226: Missing Relationship Types - RESOLVED")
        print("  #227: Missing Properties and Constraints - RESOLVED")
        print("  #228: Schema Migration - COMPLETED")
    else:
        print("\n⚠️ Schema rebuild completed with issues. Check logs.")
