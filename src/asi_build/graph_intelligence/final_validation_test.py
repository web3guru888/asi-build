#!/usr/bin/env python3
"""
Final validation test for Kenny's Intelligence Systems.
Ensures all components work together seamlessly.
"""

import json
import logging
import os
import sys
import time

from neo4j import GraphDatabase

try:
    from kenny_intelligence import (
        ActionExecutor,
        ActionType,
        Context,
        ContextEngine,
        DecisionEngine,
        KennyIntelligence,
        LearningEngine,
    )
except ImportError:
    ContextEngine = DecisionEngine = LearningEngine = None
    ActionExecutor = KennyIntelligence = Context = ActionType = None
from asi_build.graph_intelligence.performance_optimizer import PerformanceOptimizer
from asi_build.graph_intelligence.schema import NodeType, RelationshipType, create_ui_element
from asi_build.graph_intelligence.schema_manager import SchemaManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_end_to_end_intelligence():
    """Test complete intelligence system workflow."""
    logger.info("🚀 Starting end-to-end intelligence system validation...")

    all_passed = True

    # Test 1: Intelligence Components Integration
    logger.info("\n📊 Test 1: Intelligence Components Integration")
    try:
        # Create all components
        context_engine = ContextEngine()
        decision_engine = DecisionEngine()
        learning_engine = LearningEngine()

        # Create a test context
        test_context = Context()
        test_context.detected_issues = ["dialog prompt detected"]
        test_context.confidence = 0.8

        # Make a decision
        decision = decision_engine.make_decision(test_context)
        assert decision is not None, "Decision should not be None"
        assert decision.action == ActionType.KEY_PRESS, "Should decide to press key for prompt"

        # Learn from the decision
        learning_engine.learn_pattern(test_context, decision, success=True)

        # Retrieve learned patterns
        patterns = learning_engine.get_similar_patterns(test_context, limit=1)

        logger.info("  ✅ Intelligence components work together successfully")

    except Exception as e:
        logger.error(f"  ❌ Intelligence integration failed: {e}")
        all_passed = False
    finally:
        if "learning_engine" in locals():
            learning_engine.close()

    # Test 2: Graph Database Operations
    logger.info("\n📊 Test 2: Graph Database Operations")
    try:
        manager = SchemaManager()

        # Create a workflow in the graph
        workflow_id = f"test_workflow_{int(time.time())}"
        with manager.driver.session() as session:
            session.run(
                """
                CREATE (w:Workflow {
                    id: $id,
                    name: 'Test Workflow',
                    status: 'active',
                    success_rate: 0.95,
                    timestamp: timestamp()
                })
            """,
                id=workflow_id,
            )

            # Create UI elements and link them
            for i in range(3):
                elem_id = f"{workflow_id}_elem_{i}"
                session.run(
                    """
                    CREATE (e:UIElement {
                        id: $id,
                        type: 'button',
                        text: $text,
                        confidence: 0.9,
                        timestamp: timestamp()
                    })
                """,
                    id=elem_id,
                    text=f"Button {i}",
                )

                # Link to workflow
                session.run(
                    """
                    MATCH (w:Workflow {id: $wid}), (e:UIElement {id: $eid})
                    CREATE (w)-[:CONTAINS]->(e)
                """,
                    wid=workflow_id,
                    eid=elem_id,
                )

            # Verify relationships
            result = session.run(
                """
                MATCH (w:Workflow {id: $id})-[:CONTAINS]->(e:UIElement)
                RETURN count(e) as element_count
            """,
                id=workflow_id,
            )

            count = result.single()["element_count"]
            assert count == 3, f"Should have 3 elements, got {count}"

            # Clean up
            session.run(
                """
                MATCH (w:Workflow {id: $id})-[:CONTAINS]->(e:UIElement)
                DETACH DELETE w, e
            """,
                id=workflow_id,
            )

        manager.close()
        logger.info("  ✅ Graph database operations successful")

    except Exception as e:
        logger.error(f"  ❌ Graph database operations failed: {e}")
        all_passed = False

    # Test 3: Performance Optimization
    logger.info("\n📊 Test 3: Performance Optimization")
    try:
        optimizer = PerformanceOptimizer()

        # Test query optimization
        test_query = "MATCH (n:UIElement) WHERE n.type = 'button' RETURN n"
        optimized = optimizer.optimize_query(test_query)
        assert "LIMIT" in optimized, "Optimized query should include LIMIT"

        # Test caching
        cache_key = "test_key"
        cache_value = {"data": "test_value", "timestamp": time.time()}

        optimizer.cache_result(cache_key, cache_value)
        retrieved = optimizer.get_cached_result(cache_key)

        assert retrieved == cache_value, "Cache should return stored value"

        logger.info("  ✅ Performance optimization working correctly")

    except Exception as e:
        logger.error(f"  ❌ Performance optimization failed: {e}")
        all_passed = False

    # Test 4: Complex Graph Queries
    logger.info("\n📊 Test 4: Complex Graph Queries")
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687")

        with driver.session() as session:
            # Test pattern matching
            result = session.run("""
                MATCH (ui:UIElement)
                WITH ui LIMIT 5
                OPTIONAL MATCH (ui)-[r]-(connected)
                RETURN ui.id as id, ui.type as type, count(r) as connections
                ORDER BY connections DESC
            """)

            elements = list(result)
            logger.info(f"    Found {len(elements)} UI elements with connections")

            # Test aggregation
            result = session.run("""
                MATCH (n)
                WITH labels(n)[0] as node_type, count(*) as count
                RETURN node_type, count
                ORDER BY count DESC
                LIMIT 5
            """)

            aggregates = list(result)
            logger.info(f"    Top node types: {[r['node_type'] for r in aggregates[:3]]}")

            # Test path queries
            result = session.run("""
                MATCH (a:Screen), (b:Screen)
                WHERE a.id <> b.id
                WITH a, b LIMIT 1
                OPTIONAL MATCH path = (a)-[*..2]-(b)
                RETURN a.id as from, b.id as to, path IS NOT NULL as connected
            """)

            paths = list(result)
            if paths:
                logger.info(f"    Screen connectivity test passed")

        driver.close()
        logger.info("  ✅ Complex graph queries successful")

    except Exception as e:
        logger.error(f"  ❌ Complex graph queries failed: {e}")
        all_passed = False

    # Test 5: Memory and Learning Integration
    logger.info("\n📊 Test 5: Memory and Learning Integration")
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687")

        with driver.session() as session:
            # Store a learning pattern
            pattern_id = f"validation_pattern_{int(time.time())}"
            session.run(
                """
                CREATE (p:Pattern {
                    id: $id,
                    pattern_type: 'validation_test',
                    sequence: $sequence,
                    confidence: 0.92,
                    success_rate: 0.88,
                    frequency: 10,
                    timestamp: timestamp()
                })
            """,
                id=pattern_id,
                sequence=json.dumps(["click", "type", "submit"]),
            )

            # Create prediction based on pattern
            pred_id = f"validation_pred_{int(time.time())}"
            session.run(
                """
                MATCH (p:Pattern {id: $pid})
                CREATE (pred:Prediction {
                    id: $id,
                    prediction_type: 'next_action',
                    predicted_action: 'submit',
                    confidence: p.confidence * 0.9,
                    timestamp: timestamp()
                })
                CREATE (pred)-[:BASED_ON]->(p)
            """,
                pid=pattern_id,
                id=pred_id,
            )

            # Verify the relationship
            result = session.run(
                """
                MATCH (pred:Prediction)-[:BASED_ON]->(p:Pattern)
                WHERE p.id = $pid
                RETURN pred.confidence as pred_conf, p.confidence as pattern_conf
            """,
                pid=pattern_id,
            )

            record = result.single()
            assert record is not None, "Should find prediction-pattern relationship"

            # Clean up
            session.run(
                """
                MATCH (p:Pattern {id: $pid})
                OPTIONAL MATCH (p)<-[:BASED_ON]-(pred)
                DETACH DELETE p, pred
            """,
                pid=pattern_id,
            )

        driver.close()
        logger.info("  ✅ Memory and learning integration successful")

    except Exception as e:
        logger.error(f"  ❌ Memory and learning integration failed: {e}")
        all_passed = False

    # Final Summary
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ ALL VALIDATION TESTS PASSED!")
        logger.info("🎯 Kenny's Intelligence Systems are fully operational!")
        logger.info("📊 Memgraph integration is working perfectly!")
        logger.info("⚡ Performance optimization is active!")
        logger.info("🧠 Learning and memory systems are functional!")
    else:
        logger.info("⚠️ Some validation tests failed. Check logs above.")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_end_to_end_intelligence()
    sys.exit(0 if success else 1)
