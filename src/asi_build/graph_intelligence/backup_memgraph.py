#!/usr/bin/env python3
"""
Backup current Memgraph data before schema migration.
"""

from neo4j import GraphDatabase
import json
import time
from datetime import datetime

def backup_memgraph_data():
    """Backup all nodes and relationships from Memgraph."""
    
    driver = GraphDatabase.driver("bolt://localhost:7687")
    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "nodes": [],
        "relationships": []
    }
    
    try:
        with driver.session() as session:
            # Backup all nodes
            print("📦 Backing up nodes...")
            result = session.run("MATCH (n) RETURN n, labels(n) as labels")
            for record in result:
                node_data = dict(record['n'])
                node_data['_labels'] = record['labels']
                backup_data['nodes'].append(node_data)
            print(f"  ✅ Backed up {len(backup_data['nodes'])} nodes")
            
            # Backup all relationships
            print("📦 Backing up relationships...")
            result = session.run("""
                MATCH (a)-[r]->(b) 
                RETURN id(a) as from_id, id(b) as to_id, 
                       type(r) as type, properties(r) as props,
                       labels(a) as from_labels, labels(b) as to_labels,
                       a as from_node, b as to_node
            """)
            for record in result:
                rel_data = {
                    "from_node": dict(record['from_node']),
                    "to_node": dict(record['to_node']),
                    "from_labels": record['from_labels'],
                    "to_labels": record['to_labels'],
                    "type": record['type'],
                    "properties": dict(record['props']) if record['props'] else {}
                }
                backup_data['relationships'].append(rel_data)
            print(f"  ✅ Backed up {len(backup_data['relationships'])} relationships")
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None
    finally:
        driver.close()
    
    # Save to file
    backup_file = f"memgraph_backup_{int(time.time())}.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    print(f"✅ Backup saved to {backup_file}")
    return backup_file

if __name__ == "__main__":
    print("🔄 Starting Memgraph backup...")
    backup_file = backup_memgraph_data()
    if backup_file:
        print(f"✅ Backup completed successfully: {backup_file}")
    else:
        print("❌ Backup failed")