#!/usr/bin/env python3
"""
Memgraph Setup Script for Kenny Graph Intelligence System

Sets up the database with proper schema, indexes, and constraints.
"""

import logging
import time

import mgclient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_memgraph():
    """Set up Memgraph database for Kenny Graph Intelligence System."""

    # Connect to Memgraph (using simple connection for DDL operations)
    try:
        conn = mgclient.connect(host="127.0.0.1", port=7687)
        logger.info("✅ Connected to Memgraph")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Memgraph: {e}")
        return False

    # Create indexes (each must be a separate auto-commit transaction)
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
        "CREATE INDEX ON :Screen(timestamp)",
        "CREATE INDEX ON :Error(category)",
    ]

    index_success = 0
    for index_query in indexes:
        try:
            cursor = conn.cursor()
            cursor.execute(index_query)
            cursor.close()
            logger.info(f"✅ Created index: {index_query}")
            index_success += 1
        except mgclient.DatabaseError as e:
            if "already exists" in str(e).lower():
                logger.info(f"✓ Index already exists: {index_query}")
                index_success += 1
            else:
                logger.warning(f"❌ Failed to create index: {index_query} - {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error creating index: {index_query} - {e}")

    # Create constraints (each must be a separate auto-commit transaction)
    constraints = [
        "CREATE CONSTRAINT ON (n:UIElement) ASSERT n.id IS UNIQUE",
        "CREATE CONSTRAINT ON (n:Workflow) ASSERT n.id IS UNIQUE",
        "CREATE CONSTRAINT ON (n:Community) ASSERT n.id IS UNIQUE",
        "CREATE CONSTRAINT ON (n:Application) ASSERT n.name IS UNIQUE",
        "CREATE CONSTRAINT ON (n:Screen) ASSERT n.id IS UNIQUE",
        "CREATE CONSTRAINT ON (n:Pattern) ASSERT n.id IS UNIQUE",
    ]

    constraint_success = 0
    for constraint_query in constraints:
        try:
            cursor = conn.cursor()
            cursor.execute(constraint_query)
            cursor.close()
            logger.info(f"✅ Created constraint: {constraint_query}")
            constraint_success += 1
        except mgclient.DatabaseError as e:
            if "already exists" in str(e).lower():
                logger.info(f"✓ Constraint already exists: {constraint_query}")
                constraint_success += 1
            else:
                logger.warning(f"❌ Failed to create constraint: {constraint_query} - {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error creating constraint: {constraint_query} - {e}")

    # Clear existing test data for Kenny's clean schema
    try:
        cursor = conn.cursor()
        cursor.execute("MATCH (n) WHERE labels(n)[0] IN ['User', 'Post'] DETACH DELETE n")
        cursor.close()
        logger.info("✅ Cleared test data (User/Post nodes)")
    except Exception as e:
        logger.warning(f"Failed to clear test data: {e}")

    # Verify setup
    try:
        cursor = conn.cursor()
        cursor.execute("MATCH (n) RETURN count(n) as total_nodes")
        node_count = cursor.fetchone()[0]
        cursor.close()
        logger.info(f"✅ Database ready. Current nodes: {node_count}")
    except Exception as e:
        logger.error(f"Failed to verify setup: {e}")

    conn.close()

    logger.info(f"✅ Memgraph setup complete!")
    logger.info(f"   - Indexes: {index_success}/{len(indexes)} created")
    logger.info(f"   - Constraints: {constraint_success}/{len(constraints)} created")
    logger.info(f"   - Ready for Kenny Graph Intelligence System")

    return index_success > 0 and constraint_success > 0


def test_setup():
    """Test the Memgraph setup by creating and querying sample data."""

    try:
        conn = mgclient.connect(host="127.0.0.1", port=7687)
        cursor = conn.cursor()

        # Test creating a UI element
        test_query = """
        CREATE (btn:UIElement {
            id: 'test_button_001',
            type: 'button',
            text: 'Save',
            coordinates: [100, 200],
            timestamp: timestamp()
        })
        RETURN btn.id as button_id
        """

        cursor.execute(test_query)
        result = cursor.fetchone()
        button_id = result[0]
        logger.info(f"✅ Created test UI element: {button_id}")

        # Test querying with index
        cursor.execute("MATCH (btn:UIElement {id: 'test_button_001'}) RETURN btn.type as type")
        result = cursor.fetchone()
        element_type = result[0]
        logger.info(f"✅ Retrieved test element type: {element_type}")

        # Clean up test data
        cursor.execute("MATCH (btn:UIElement {id: 'test_button_001'}) DELETE btn")
        logger.info("✅ Cleaned up test data")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"❌ Setup test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Setting up Memgraph for Kenny Graph Intelligence System...")

    # Run setup
    setup_success = setup_memgraph()

    if setup_success:
        # Test the setup
        test_success = test_setup()

        if test_success:
            print("✅ Memgraph setup and testing completed successfully!")
            print("🎯 Ready to implement Kenny's Graph Intelligence System")
        else:
            print("⚠️ Setup completed but testing failed")
    else:
        print("❌ Memgraph setup failed")
        exit(1)
