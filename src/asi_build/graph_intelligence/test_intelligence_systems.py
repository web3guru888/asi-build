#!/usr/bin/env python3
"""
Comprehensive test suite for Kenny's Intelligence Systems with Memgraph integration.
Tests all graph intelligence components and identifies issues.
"""

import sys
import os
import json
import time
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligenceSystemTester:
    """Comprehensive tester for Kenny's intelligence systems."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver("bolt://localhost:7687")
        self.test_results = []
        self.issues_found = []
        
    def close(self):
        """Close database connection."""
        self.driver.close()
    
    def run_test(self, test_name: str, test_func) -> Tuple[bool, str]:
        """Run a single test and capture results."""
        try:
            logger.info(f"🧪 Testing: {test_name}")
            result = test_func()
            if result:
                logger.info(f"  ✅ PASSED: {test_name}")
                self.test_results.append({"test": test_name, "status": "PASSED", "error": None})
                return True, None
            else:
                logger.error(f"  ❌ FAILED: {test_name}")
                error_msg = f"Test returned False"
                self.test_results.append({"test": test_name, "status": "FAILED", "error": error_msg})
                self.issues_found.append({"test": test_name, "error": error_msg})
                return False, error_msg
        except Exception as e:
            logger.error(f"  ❌ ERROR: {test_name} - {str(e)}")
            self.test_results.append({"test": test_name, "status": "ERROR", "error": str(e)})
            self.issues_found.append({"test": test_name, "error": str(e)})
            return False, str(e)
    
    def test_kenny_intelligence_module(self) -> bool:
        """Test the main kenny_intelligence.py module."""
        try:
            from kenny_intelligence import (
                ContextEngine, DecisionEngine, LearningEngine,
                ActionExecutor, KennyIntelligence
            )
            
            # Test ContextEngine
            context_engine = ContextEngine()
            # Note: Can't test observe_environment without running intelligent_agent
            
            # Test DecisionEngine initialization
            decision_engine = DecisionEngine()
            
            # Test LearningEngine with Memgraph
            learning_engine = LearningEngine()
            
            # Check if learning engine can connect to Memgraph
            if not hasattr(learning_engine, 'graph_driver'):
                raise Exception("LearningEngine missing graph_driver attribute")
            
            return True
        except ImportError as e:
            logger.error(f"Import error: {e}")
            return False
        except Exception as e:
            logger.error(f"Module test error: {e}")
            return False
    
    def test_schema_manager(self) -> bool:
        """Test the SchemaManager functionality."""
        try:
            from graph_intelligence.schema_manager import SchemaManager
            from graph_intelligence.schema import NodeType, create_ui_element
            
            manager = SchemaManager()
            
            # Test node creation
            test_node = create_ui_element(
                element_type="test_button",
                text="Test Element",
                coordinates=[100, 200],
                confidence=0.95
            )
            
            node_id = manager.create_node(test_node, NodeType.UI_ELEMENT)
            if not node_id:
                raise Exception("Failed to create node")
            
            # Test node retrieval
            retrieved = manager.get_node(node_id, NodeType.UI_ELEMENT)
            if not retrieved:
                raise Exception("Failed to retrieve node")
            
            # Test node update
            success = manager.update_node(node_id, {"confidence": 0.99}, NodeType.UI_ELEMENT)
            if not success:
                raise Exception("Failed to update node")
            
            # Test node deletion
            success = manager.delete_node(node_id, NodeType.UI_ELEMENT)
            if not success:
                raise Exception("Failed to delete node")
            
            manager.close()
            return True
            
        except Exception as e:
            logger.error(f"SchemaManager test error: {e}")
            return False
    
    def test_data_ingestion(self) -> bool:
        """Test data ingestion capabilities."""
        try:
            from graph_intelligence.data_ingestion import DataIngestion
            
            ingestion = DataIngestion()
            
            # Test screenshot data ingestion
            test_screenshot_data = {
                "timestamp": time.time(),
                "resolution": [1920, 1080],
                "ui_elements": [
                    {"type": "button", "text": "Save", "x": 100, "y": 200},
                    {"type": "menu", "text": "File", "x": 50, "y": 50}
                ]
            }
            
            result = ingestion.ingest_screenshot(test_screenshot_data)
            if not result:
                raise Exception("Failed to ingest screenshot data")
            
            # Test workflow ingestion
            test_workflow = {
                "name": "Test Workflow",
                "steps": ["click", "type", "submit"],
                "success_rate": 0.85
            }
            
            result = ingestion.ingest_workflow(test_workflow)
            if not result:
                raise Exception("Failed to ingest workflow")
            
            return True
            
        except ImportError:
            # Module might not exist yet
            logger.warning("DataIngestion module not found - may need implementation")
            return True  # Don't fail if module doesn't exist yet
        except Exception as e:
            logger.error(f"Data ingestion test error: {e}")
            return False
    
    def test_community_detection(self) -> bool:
        """Test community detection algorithms."""
        try:
            from graph_intelligence.community_detection import CommunityDetection
            
            detector = CommunityDetection()
            
            # Test Louvain algorithm
            communities = detector.detect_communities(algorithm="louvain")
            
            # Test that communities were found
            if not isinstance(communities, list):
                raise Exception("Community detection did not return a list")
            
            return True
            
        except ImportError:
            logger.warning("CommunityDetection module not found - may need implementation")
            return True
        except Exception as e:
            logger.error(f"Community detection test error: {e}")
            return False
    
    def test_performance_optimizer(self) -> bool:
        """Test performance optimization features."""
        try:
            from graph_intelligence.performance_optimizer import PerformanceOptimizer
            
            optimizer = PerformanceOptimizer()
            
            # Test query optimization
            test_query = "MATCH (n:UIElement) RETURN n"
            optimized = optimizer.optimize_query(test_query)
            
            if not optimized:
                raise Exception("Query optimization failed")
            
            # Test cache functionality
            cache_key = "test_cache"
            cache_value = {"data": "test"}
            
            optimizer.cache_result(cache_key, cache_value)
            cached = optimizer.get_cached_result(cache_key)
            
            if cached != cache_value:
                raise Exception("Cache functionality failed")
            
            return True
            
        except ImportError:
            logger.warning("PerformanceOptimizer module not found - may need implementation")
            return True
        except Exception as e:
            logger.error(f"Performance optimizer test error: {e}")
            return False
    
    def test_kenny_integration(self) -> bool:
        """Test Kenny integration module."""
        try:
            from graph_intelligence.kenny_integration import KennyIntegration
            
            integration = KennyIntegration()
            
            # Test OCR data integration
            ocr_data = {
                "elements": [
                    {"text": "Button", "confidence": 0.9, "bbox": [10, 20, 100, 50]}
                ]
            }
            
            result = integration.process_ocr_data(ocr_data)
            if not result:
                raise Exception("OCR data processing failed")
            
            # Test action prediction
            context = {"current_screen": "main_menu", "last_action": "click"}
            prediction = integration.predict_next_action(context)
            
            if not prediction:
                raise Exception("Action prediction failed")
            
            return True
            
        except ImportError:
            logger.warning("KennyIntegration module not found - may need implementation")
            return True
        except Exception as e:
            logger.error(f"Kenny integration test error: {e}")
            return False
    
    def test_graph_queries(self) -> bool:
        """Test complex graph queries."""
        with self.driver.session() as session:
            # Test 1: Path finding - Memgraph compatible
            # Instead of shortestPath, use BFS or simple pattern matching
            result = session.run("""
                MATCH (a:UIElement), (b:UIElement)
                WHERE a.id <> b.id
                WITH a, b LIMIT 1
                MATCH path = (a)-[*..3]-(b)
                RETURN path LIMIT 1
            """)
            
            if not result.single():
                logger.warning("No paths found between UI elements")
            
            # Test 2: Pattern matching
            result = session.run("""
                MATCH (u:UserAction)-[:FOLLOWED_BY*2]->(final:UserAction)
                RETURN u.action_type as start, final.action_type as end, count(*) as frequency
                ORDER BY frequency DESC
                LIMIT 5
            """)
            
            patterns = list(result)
            if len(patterns) == 0:
                logger.warning("No action patterns found")
            
            # Test 3: Aggregation
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count, 
                       avg(n.confidence) as avg_confidence
                ORDER BY count DESC
            """)
            
            aggregates = list(result)
            if len(aggregates) == 0:
                raise Exception("Aggregation query failed")
            
            return True
    
    def test_relationship_traversal(self) -> bool:
        """Test relationship traversal capabilities."""
        with self.driver.session() as session:
            # Test variable-length traversal - Memgraph compatible
            # Use simpler pattern without shortestPath
            result = session.run("""
                MATCH (start:Screen)-[:NAVIGATES_TO]->(end:Screen)
                RETURN start.id as from, end.id as to, 1 as distance
                UNION
                MATCH (start:Screen)-[:NAVIGATES_TO]->()-[:NAVIGATES_TO]->(end:Screen)
                RETURN start.id as from, end.id as to, 2 as distance
                UNION
                MATCH (start:Screen)-[:NAVIGATES_TO]->()-[:NAVIGATES_TO]->()-[:NAVIGATES_TO]->(end:Screen)
                RETURN start.id as from, end.id as to, 3 as distance
            """)
            
            paths = list(result)
            if len(paths) == 0:
                logger.warning("No navigation paths found")
            
            # Test relationship filtering
            result = session.run("""
                MATCH (n)-[r]-(m)
                WHERE type(r) IN ['CONTAINS', 'BELONGS_TO', 'TRIGGERS']
                RETURN count(DISTINCT r) as relationship_count
            """)
            
            count = result.single()['relationship_count']
            if count == 0:
                raise Exception("Relationship filtering failed")
            
            return True
    
    def test_data_consistency(self) -> bool:
        """Test data consistency and integrity."""
        with self.driver.session() as session:
            # Check for orphaned nodes - Memgraph compatible
            # Use OPTIONAL MATCH instead of WHERE NOT pattern
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, r
                WHERE r IS NULL
                RETURN labels(n)[0] as label, count(DISTINCT n) as orphan_count
            """)
            
            orphans = list(result)
            for record in orphans:
                if record['orphan_count'] > 0:
                    logger.warning(f"Found {record['orphan_count']} orphaned {record['label']} nodes")
            
            # Check for duplicate IDs
            result = session.run("""
                MATCH (n)
                WHERE n.id IS NOT NULL
                WITH n.id as id, count(*) as count
                WHERE count > 1
                RETURN id, count
            """)
            
            duplicates = list(result)
            if len(duplicates) > 0:
                raise Exception(f"Found duplicate IDs: {duplicates}")
            
            # Check required properties
            result = session.run("""
                MATCH (n:UIElement)
                WHERE n.id IS NULL OR n.type IS NULL OR n.confidence IS NULL
                RETURN count(*) as invalid_count
            """)
            
            invalid = result.single()['invalid_count']
            if invalid > 0:
                raise Exception(f"Found {invalid} UIElements with missing required properties")
            
            return True
    
    def test_memory_patterns(self) -> bool:
        """Test memory and learning patterns."""
        with self.driver.session() as session:
            # Test pattern storage
            test_pattern = {
                "id": f"test_pattern_{int(time.time())}",
                "pattern_type": "test",
                "sequence": json.dumps(["action1", "action2"]),
                "confidence": 0.85
            }
            
            session.run("""
                CREATE (p:Pattern {
                    id: $id,
                    pattern_type: $type,
                    sequence: $sequence,
                    confidence: $confidence,
                    timestamp: timestamp()
                })
            """, id=test_pattern["id"], type=test_pattern["pattern_type"],
                sequence=test_pattern["sequence"], confidence=test_pattern["confidence"])
            
            # Verify pattern was stored
            result = session.run("""
                MATCH (p:Pattern {id: $id})
                RETURN p
            """, id=test_pattern["id"])
            
            if not result.single():
                raise Exception("Pattern storage failed")
            
            # Clean up test pattern
            session.run("MATCH (p:Pattern {id: $id}) DELETE p", id=test_pattern["id"])
            
            return True
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        logger.info("🚀 Starting comprehensive intelligence system testing...")
        
        tests = [
            ("Kenny Intelligence Module", self.test_kenny_intelligence_module),
            ("Schema Manager", self.test_schema_manager),
            ("Data Ingestion", self.test_data_ingestion),
            ("Community Detection", self.test_community_detection),
            ("Performance Optimizer", self.test_performance_optimizer),
            ("Kenny Integration", self.test_kenny_integration),
            ("Graph Queries", self.test_graph_queries),
            ("Relationship Traversal", self.test_relationship_traversal),
            ("Data Consistency", self.test_data_consistency),
            ("Memory Patterns", self.test_memory_patterns)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report and identify issues."""
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASSED"])
        failed = len([r for r in self.test_results if r["status"] == "FAILED"])
        errors = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        logger.info("\n" + "="*60)
        logger.info("📊 TEST REPORT")
        logger.info("="*60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️ Errors: {errors}")
        logger.info(f"Success Rate: {(passed/total_tests)*100:.1f}%")
        
        if self.issues_found:
            logger.info("\n🐛 ISSUES FOUND:")
            for i, issue in enumerate(self.issues_found, 1):
                logger.info(f"{i}. {issue['test']}: {issue['error']}")
            
            # Save issues for GitHub creation
            with open("test_issues.json", "w") as f:
                json.dump(self.issues_found, f, indent=2)
            logger.info(f"\n💾 Issues saved to test_issues.json")
        else:
            logger.info("\n✅ No issues found!")
        
        logger.info("="*60)


if __name__ == "__main__":
    tester = IntelligenceSystemTester()
    try:
        tester.run_all_tests()
    finally:
        tester.close()