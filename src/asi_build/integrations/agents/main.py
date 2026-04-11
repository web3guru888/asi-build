#!/usr/bin/env python3
"""
SQL Database to Memgraph Migration Agent - Main Entry Point

This is the main entry point for the SQL database to Memgraph migration agent.
Run with: uv run main.py
"""

import logging
from typing import Any, Dict

from .core import SQLToMemgraphAgent
from .core.graph_modeling import GraphModelingStrategy
from .utils import (
    DatabaseConnectionError,
    MigrationEnvironmentError,
    print_environment_help,
    print_troubleshooting_help,
    probe_all_connections,
    setup_and_validate_environment,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def print_banner() -> None:
    """Print application banner."""
    print("=" * 60)
    print("🚀 SQL Database to Memgraph Migration Agent")
    print("=" * 60)
    print("Intelligent database migration with LLM-powered analysis")
    print()


def get_graph_modeling_mode() -> bool:
    """
    Get user choice for graph modeling mode.

    Returns:
        bool: True for interactive graph modeling, False for automatic
    """
    print("Graph modeling mode:")
    print("  1. Interactive - Refine the graph model with natural language")
    print("                   feedback")
    print("  2. Automatic - Generate graph model automatically")
    print()

    while True:
        try:
            choice = input("Select mode (1-2) or press Enter for automatic: ").strip()
            if not choice:
                return False  # Default to automatic

            if choice == "1":
                return True  # Interactive
            elif choice == "2":
                return False  # Automatic
            else:
                print("Invalid choice. Please select 1-2.")
        except ValueError:
            print("Invalid input. Please enter 1-2.")


def get_graph_modeling_strategy() -> GraphModelingStrategy:
    """
    Get user choice for graph modeling strategy.

    Returns:
        GraphModelingStrategy: Selected strategy
    """
    print("Graph modeling strategy:")
    print("  1. Deterministic - Rule-based graph creation (fast, predictable)")
    print("  2. LLM-Powered - AI generates optimal graph model")
    print("                   (flexible, smart)")
    print()

    while True:
        try:
            choice = input("Select strategy (1-2) or press Enter for deterministic: ").strip()
            if not choice:
                return GraphModelingStrategy.DETERMINISTIC  # Default

            if choice == "1":
                return GraphModelingStrategy.DETERMINISTIC
            elif choice == "2":
                return GraphModelingStrategy.LLM_POWERED
            else:
                print("Invalid choice. Please select 1-2.")
        except ValueError:
            print("Invalid input. Please enter 1-2.")


def run_migration(
    source_db_config: Dict[str, Any],
    memgraph_config: Dict[str, Any],
    interactive_graph_modeling: bool,
    graph_modeling_strategy: GraphModelingStrategy,
) -> Dict[str, Any]:
    """
    Run the migration with the specified configuration.

    Args:
        source_db_config: Source database connection configuration
        memgraph_config: Memgraph connection configuration
        interactive_graph_modeling: Whether to use interactive graph modeling
        graph_modeling_strategy: Strategy for graph model creation

    Returns:
        Migration result dictionary
    """
    print("🔧 Creating migration agent...")

    graph_mode = "interactive" if interactive_graph_modeling else "automatic"
    strategy_name = graph_modeling_strategy.value
    print(f"🎯 Graph modeling: {graph_mode} with {strategy_name} strategy")
    print()

    # Create agent with graph modeling settings
    agent = SQLToMemgraphAgent(
        interactive_graph_modeling=interactive_graph_modeling,
        graph_modeling_strategy=graph_modeling_strategy,
    )

    print("🚀 Starting migration workflow...")
    print("This will:")
    print("  1. 🔍 Analyze source database schema")
    print("  2. 🎯 Generate graph model with HyGM")
    print("  3. 📝 Create indexes and constraints")
    print("  4. ⚙️  Generate migration queries")
    print("  5. 🔄 Execute migration to Memgraph")
    print("  6. ✅ Verify the migration results")
    print()

    # Handle interactive vs automatic mode
    if interactive_graph_modeling:
        print("🔄 Interactive mode: You'll be prompted to review and refine")
        print("   the graph model")
        print()

    # Run the migration with the user's chosen settings
    return agent.migrate(source_db_config, memgraph_config)


def print_migration_results(result: Dict[str, Any]) -> None:
    """
    Print formatted migration results.

    Args:
        result: Migration result dictionary
    """
    print("\n" + "=" * 60)
    print("📊 MIGRATION RESULTS")
    print("=" * 60)

    if result.get("success", False):
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration encountered errors")

    # Print error details
    if result.get("errors"):
        print(f"\n🚨 Errors ({len(result['errors'])}):")
        for i, error in enumerate(result["errors"], 1):
            print(f"  {i}. {error}")

    # Print completion stats
    completed = len(result.get("completed_tables", []))
    total = result.get("total_tables", 0)
    print(f"\n📋 Tables processed: {completed}/{total}")

    # Print schema analysis details
    if result.get("database_structure"):
        structure = result["database_structure"]
        print("\n🔍 Schema Analysis:")
        print(f"  📁 Entity tables: {len(structure.get('entity_tables', {}))}")
        print(f"  🔗 Join tables: {len(structure.get('join_tables', {}))}")
        print(f"  👁️  Views (excluded): {len(structure.get('views', {}))}")
        print(f"  🔄 Relationships: {len(structure.get('relationships', []))}")

        # Show index/constraint creation results
        if result.get("created_indexes") is not None:
            index_count = len(result.get("created_indexes", []))
            constraint_count = len(result.get("created_constraints", []))
            print(f"  📇 Created indexes: {index_count}")
            print(f"  🔒 Created constraints: {constraint_count}")

        # Show excluded views
        if structure.get("views"):
            print("\n👁️  Excluded view tables:")
            for table_name, table_info in structure["views"].items():
                row_count = table_info.get("row_count", 0)
                print(f"    - {table_name}: {row_count} rows")

        # Show detected join tables
        if structure.get("join_tables"):
            print("\n🔗 Detected join tables:")
            for table_name, table_info in structure["join_tables"].items():
                fk_count = len(table_info.get("foreign_keys", []))
                row_count = table_info.get("row_count", 0)
                print(f"    - {table_name}: {fk_count} FKs, {row_count} rows")

        # Show relationship breakdown
        relationships_by_type = {}
        for rel in structure.get("relationships", []):
            rel_type = rel["type"]
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(rel)

        if relationships_by_type:
            print("\n🔄 Relationship breakdown:")
            for rel_type, rels in relationships_by_type.items():
                print(f"    - {rel_type}: {len(rels)} relationships")

    print(f"\n🏁 Final status: {result.get('final_step', 'Unknown')}")
    print("=" * 60)


def main() -> None:
    """Main entry point for the migration agent."""
    print_banner()

    try:
        # Setup and validate environment
        print("🔧 Setting up environment...")
        source_db_config, memgraph_config = setup_and_validate_environment()
        print("✅ Environment validation completed")
        print()

        # Probe database connections
        print("🔌 Testing database connections...")
        probe_all_connections(source_db_config, memgraph_config)
        print("✅ All connections verified")
        print()

        # Get user preferences
        graph_interactive = get_graph_modeling_mode()
        graph_strategy = get_graph_modeling_strategy()

        # Run migration
        result = run_migration(source_db_config, memgraph_config, graph_interactive, graph_strategy)

        # Display results
        print_migration_results(result)

    except MigrationEnvironmentError as e:
        print("\n❌ Environment Setup Error:")
        print(str(e))
        print_environment_help()
        sys.exit(1)

    except DatabaseConnectionError as e:
        print("\n❌ Database Connection Error:")
        print(str(e))
        print_troubleshooting_help()
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(0)

    except Exception as e:  # pylint: disable=broad-except
        print(f"\n❌ Unexpected Error: {e}")
        logger.error("Unexpected error in main: %s", e, exc_info=True)
        print_troubleshooting_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
