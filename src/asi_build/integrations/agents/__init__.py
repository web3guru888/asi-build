"""
SQL Database to Memgraph Migration Agent

This package provides intelligent database migration capabilities from SQL databases
to Memgraph with LLM-powered graph modeling and analysis.

## Package Structure

- `core/` - Main migration orchestration and graph modeling (HyGM)
- `database/` - Database analysis and data interface layer
- `query_generation/` - Cypher query generation and schema utilities
- `utils/` - Configuration and environment utilities
- `examples/` - Usage examples and demonstrations
- `tests/` - Tests and troubleshooting tools

## Quick Start

```python
from agents.core import SQLToMemgraphAgent, HyGM
from agents.database import DatabaseDataInterface
from agents.utils import setup_and_validate_environment

# Setup environment
mysql_config, memgraph_config = setup_and_validate_environment()

# Create migration agent
agent = SQLToMemgraphAgent(interactive_graph_modeling=False)

# Run migration
result = agent.migrate(mysql_config, memgraph_config)
```
"""

# Main exports
try:
    from .core import HyGM, SQLToMemgraphAgent
except (ImportError, ModuleNotFoundError, SyntaxError):
    SQLToMemgraphAgent = None
    HyGM = None
try:
    from .database import DatabaseAnalyzerFactory, DatabaseDataInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    DatabaseAnalyzerFactory = None
    DatabaseDataInterface = None
try:
    from .query_generation import CypherGenerator, SchemaUtilities
except (ImportError, ModuleNotFoundError, SyntaxError):
    CypherGenerator = None
    SchemaUtilities = None

__version__ = "0.1.0"

__all__ = [
    "SQLToMemgraphAgent",
    "HyGM",
    "DatabaseAnalyzerFactory",
    "DatabaseDataInterface",
    "CypherGenerator",
    "SchemaUtilities",
]
