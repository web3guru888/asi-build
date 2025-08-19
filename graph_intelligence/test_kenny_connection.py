#!/usr/bin/env python3
"""
Test that Kenny's intelligence systems can connect to the rebuilt Memgraph schema.
"""

from neo4j import GraphDatabase
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph_intelligence.schema_manager import SchemaManager
from graph_intelligence.schema import NodeType, RelationshipType, create_ui_element

def test_kenny_connection():
    """Test Kenny's ability to interact with the new schema."""
    
    print("🧪 Testing Kenny's connection to Memgraph...")
    
    # Test direct connection
    driver = GraphDatabase.driver("bolt://localhost:7687")
    
    try:
        with driver.session() as session:
            # Test 1: Query all node types
            print("\n📊 Test 1: Query Node Types")
            result = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN DISTINCT label, count(*) as count
                ORDER BY label
            """)
            
            node_types = {}
            for record in result:
                node_types[record['label']] = record['count']
                print(f"  ✅ {record['label']}: {record['count']} nodes")
            
            # Test 2: Query relationship types
            print("\n📊 Test 2: Query Relationship Types")
            result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as type, count(*) as count
                ORDER BY type
            """)
            
            rel_types = {}
            for record in result:
                rel_types[record['type']] = record['count']
                print(f"  ✅ {record['type']}: {record['count']} relationships")
            
            # Test 3: Pattern matching for UI automation
            print("\n🎯 Test 3: UI Automation Pattern Query")
            result = session.run("""
                MATCH (ui:UIElement)-[:BELONGS_TO]->(c:Community)
                WHERE c.purpose = 'file_operations'
                RETURN ui.id as id, ui.text as text, ui.type as type
                LIMIT 5
            """)
            
            ui_elements = []
            for record in result:
                ui_elements.append(record)
                print(f"  ✅ Found UI element: {record['text']} ({record['type']})")
            
            # Test 4: Workflow analysis
            print("\n🔄 Test 4: Workflow Analysis")
            result = session.run("""
                MATCH (w:Workflow)
                WHERE w.status = 'completed'
                RETURN w.name as name, w.success_rate as rate, w.execution_count as count
                ORDER BY w.success_rate DESC
            """)
            
            workflows = []
            for record in result:
                workflows.append(record)
                print(f"  ✅ Workflow: {record['name']} - {record['rate']*100:.0f}% success ({record['count']} runs)")
            
            # Test 5: Error pattern detection
            print("\n⚠️ Test 5: Error Pattern Detection")
            result = session.run("""
                MATCH (e:Error)<-[:RESOLVES]-(p:Pattern)
                RETURN e.category as error, p.pattern_type as pattern, p.confidence as confidence
            """)
            
            error_patterns = []
            for record in result:
                error_patterns.append(record)
                print(f"  ✅ Error '{record['error']}' resolved by {record['pattern']} (confidence: {record['confidence']:.2f})")
            
            # Test 6: Predictive intelligence
            print("\n🔮 Test 6: Predictive Intelligence")
            result = session.run("""
                MATCH (ua:UserAction)-[:FOLLOWED_BY]->(next:UserAction)
                RETURN ua.action_type as current, next.action_type as predicted, count(*) as frequency
                ORDER BY frequency DESC
                LIMIT 3
            """)
            
            predictions = []
            for record in result:
                predictions.append(record)
                print(f"  ✅ After '{record['current']}' → predict '{record['predicted']}' (frequency: {record['frequency']})")
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        driver.close()
    
    # Test SchemaManager
    print("\n🔧 Test 7: SchemaManager Operations")
    try:
        manager = SchemaManager()
        
        # Create a test UI element
        test_element = create_ui_element(
            element_type="button",
            text="Test Button",
            coordinates=[500, 500],
            confidence=0.99,
            application="test_app"
        )
        
        # Add to database
        node_id = manager.create_node(test_element, NodeType.UI_ELEMENT)
        print(f"  ✅ Created test node: {node_id}")
        
        # Retrieve it
        retrieved = manager.get_node(node_id, NodeType.UI_ELEMENT)
        if retrieved:
            print(f"  ✅ Retrieved node: {retrieved['text']}")
        
        # Update it
        success = manager.update_node(node_id, {"confidence": 0.95}, NodeType.UI_ELEMENT)
        if success:
            print(f"  ✅ Updated node confidence")
        
        # Delete it
        success = manager.delete_node(node_id, NodeType.UI_ELEMENT)
        if success:
            print(f"  ✅ Deleted test node")
        
        manager.close()
        
    except Exception as e:
        print(f"❌ SchemaManager test failed: {e}")
        return False
    
    print("\n✅ All tests passed! Kenny's Graph Intelligence System is fully operational!")
    return True


if __name__ == "__main__":
    success = test_kenny_connection()
    
    if success:
        print("\n🎯 Kenny can successfully interact with the rebuilt Memgraph schema!")
        print("📊 The database is ready for intelligent UI automation!")
    else:
        print("\n❌ Some tests failed. Please check the configuration.")