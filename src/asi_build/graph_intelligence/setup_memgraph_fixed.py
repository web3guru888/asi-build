#!/usr/bin/env python3
"""
Memgraph Setup Script using Neo4j driver for better auto-commit handling
"""

import logging

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_memgraph_with_neo4j_driver():
    """Set up Memgraph using Neo4j driver for proper auto-commit."""

    # Connect using Neo4j driver (compatible with Memgraph)
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri)

    try:
        with driver.session() as session:
            # Clear existing test data
            session.run("MATCH (n) WHERE labels(n)[0] IN ['User', 'Post'] DETACH DELETE n")
            logger.info("✅ Cleared test data")

            # Create indexes (auto-commit)
            indexes = [
                "CREATE INDEX ON :UIElement(id)",
                "CREATE INDEX ON :UIElement(type)",
                "CREATE INDEX ON :UIElement(coordinates)",
                "CREATE INDEX ON :Workflow(id)",
                "CREATE INDEX ON :Workflow(status)",
                "CREATE INDEX ON :Community(id)",
                "CREATE INDEX ON :Community(modularity)",
                "CREATE INDEX ON :Application(name)",
                "CREATE INDEX ON :Pattern(frequency)",
            ]

            index_success = 0
            for index_query in indexes:
                try:
                    session.run(index_query)
                    logger.info(f"✅ Created index: {index_query}")
                    index_success += 1
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"✓ Index already exists: {index_query}")
                        index_success += 1
                    else:
                        logger.warning(f"Failed to create index: {index_query} - {e}")

            # Create constraints (auto-commit)
            constraints = [
                "CREATE CONSTRAINT ON (n:UIElement) ASSERT n.id IS UNIQUE",
                "CREATE CONSTRAINT ON (n:Workflow) ASSERT n.id IS UNIQUE",
                "CREATE CONSTRAINT ON (n:Community) ASSERT n.id IS UNIQUE",
                "CREATE CONSTRAINT ON (n:Application) ASSERT n.name IS UNIQUE",
            ]

            constraint_success = 0
            for constraint_query in constraints:
                try:
                    session.run(constraint_query)
                    logger.info(f"✅ Created constraint: {constraint_query}")
                    constraint_success += 1
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"✓ Constraint already exists: {constraint_query}")
                        constraint_success += 1
                    else:
                        logger.warning(f"Failed to create constraint: {constraint_query} - {e}")

            # Test the setup
            result = session.run("MATCH (n) RETURN count(n) as total")
            node_count = result.single()["total"]
            logger.info(f"✅ Database ready. Current nodes: {node_count}")

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False
    finally:
        driver.close()

    logger.info(f"✅ Memgraph setup complete!")
    logger.info(f"   - Ready for Kenny Graph Intelligence System")
    return True


def test_database_operations():
    """Test database operations with sample data."""

    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri)

    try:
        with driver.session() as session:
            # Create sample UI elements
            session.run("""
                CREATE (btn:UIElement {
                    id: 'save_button',
                    type: 'button',
                    text: 'Save',
                    coordinates: [150, 200],
                    confidence: 0.95,
                    timestamp: timestamp()
                })
            """)

            session.run("""
                CREATE (menu:UIElement {
                    id: 'file_menu',
                    type: 'menu',
                    text: 'File',
                    coordinates: [50, 180],
                    confidence: 0.98,
                    timestamp: timestamp()
                })
            """)

            # Create relationship
            session.run("""
                MATCH (menu:UIElement {id: 'file_menu'}), (btn:UIElement {id: 'save_button'})
                CREATE (menu)-[:CONTAINS]->(btn)
            """)

            # Test query performance
            result = session.run("""
                MATCH (ui:UIElement)
                RETURN ui.type as type, count(ui) as count
                ORDER BY count DESC
            """)

            logger.info("✅ Test data created successfully:")
            for record in result:
                logger.info(f"   - {record['type']}: {record['count']} elements")

            # Clean up test data
            session.run("MATCH (ui:UIElement {id: 'save_button'}) DETACH DELETE ui")
            session.run("MATCH (ui:UIElement {id: 'file_menu'}) DETACH DELETE ui")
            logger.info("✅ Test data cleaned up")

    except Exception as e:
        logger.error(f"❌ Test operations failed: {e}")
        return False
    finally:
        driver.close()

    return True


if __name__ == "__main__":
    print("🚀 Setting up Memgraph for Kenny Graph Intelligence System...")

    # Run setup
    setup_success = setup_memgraph_with_neo4j_driver()

    if setup_success:
        # Test operations
        test_success = test_database_operations()

        if test_success:
            print("✅ Memgraph setup and testing completed successfully!")
            print("🎯 Kenny Graph Intelligence System database ready!")
        else:
            print("⚠️ Setup completed but testing failed")
    else:
        print("❌ Memgraph setup failed")
