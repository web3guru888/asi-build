"""
Tests for asi_build.integrations module.

These tests are designed to work WITHOUT external dependencies
(langchain, memgraph, pymysql, etc.) by using:
- ast.parse() for structural verification
- importlib.util.spec_from_file_location for isolated module loading
- unittest.mock for import mocking
"""

import ast
import os
import sys
import importlib
import importlib.util
from pathlib import Path
from dataclasses import fields
from unittest.mock import patch, MagicMock

import pytest

# ------------------------------------------------------------------
# Setup: ensure src/ is on the path
# ------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
_INTEGRATIONS_DIR = _SRC_DIR / "asi_build" / "integrations"


def _parse_py(path: Path) -> ast.Module:
    """Parse a Python file into an AST, raising FileNotFoundError if missing."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _load_module_from_file(name: str, filepath: Path):
    """Load a single Python module directly from a file path,
    bypassing __init__.py import chains that may pull in missing deps."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Pre-load the interface module once (no external deps needed)
_INTERFACE_PATH = (
    _INTEGRATIONS_DIR / "agents" / "database" / "interface.py"
)
_interface_mod = _load_module_from_file(
    "asi_build.integrations.agents.database.interface", _INTERFACE_PATH
)


# ==================================================================
# Section 1: Module Structure (3 tests)
# ==================================================================

class TestModuleStructure:
    """Verify the integrations package layout and lazy-import mechanism."""

    def test_integrations_package_importable(self):
        """Importing asi_build.integrations should succeed without crashing."""
        mod = importlib.import_module("asi_build.integrations")
        assert mod is not None
        assert hasattr(mod, "__all__")

    def test_integrations_all_exports(self):
        """__all__ should advertise the three sub-packages."""
        mod = importlib.import_module("asi_build.integrations")
        expected = {"agents", "langchain_memgraph", "mcp_memgraph"}
        assert set(mod.__all__) == expected

    def test_integrations_agents_importable(self):
        """The 'agents' sub-module should be importable even without optional deps.
        Import guards (try/except) should allow graceful degradation."""
        mod = importlib.import_module("asi_build.integrations")
        # 'agents' should now import without error due to try/except guards
        agents = mod.agents
        assert agents is not None

    def test_integrations_nonexistent_attr_raises_attribute_error(self):
        """Accessing a completely unknown attribute should raise AttributeError."""
        mod = importlib.import_module("asi_build.integrations")
        with pytest.raises(AttributeError, match=r"has no attribute"):
            _ = mod.this_does_not_exist


# ==================================================================
# Section 2: Agent Data Structures (5 tests)
# ==================================================================

class TestAgentDataStructures:
    """Test pure-Python data classes from the agents sub-package.

    We load interface.py directly via importlib.util to avoid the agents/__init__.py
    chain that pulls in langgraph and other missing deps.
    """

    # Aliases for convenience — all come from the pre-loaded _interface_mod
    DatabaseAnalyzer = _interface_mod.DatabaseAnalyzer
    ColumnInfo = _interface_mod.ColumnInfo
    ForeignKeyInfo = _interface_mod.ForeignKeyInfo
    TableInfo = _interface_mod.TableInfo
    TableType = _interface_mod.TableType
    RelationshipInfo = _interface_mod.RelationshipInfo
    DatabaseStructure = _interface_mod.DatabaseStructure

    @staticmethod
    def _make_fake_analyzer(config=None):
        """Build a minimal concrete DatabaseAnalyzer subclass."""
        DBA = _interface_mod.DatabaseAnalyzer

        class FakeAnalyzer(DBA):
            def _get_database_type(self): return "fake"
            def connect(self): return True
            def disconnect(self): pass
            def get_tables(self): return []
            def get_table_schema(self, t): return []
            def get_foreign_keys(self, t): return []
            def get_table_data(self, t, limit=None): return []
            def get_table_row_count(self, t): return 0
            def is_view(self, t): return False

        return FakeAnalyzer(connection_config=config or {})

    def test_database_interface_abc(self):
        """DatabaseAnalyzer is abstract and cannot be directly instantiated."""
        with pytest.raises(TypeError):
            self.DatabaseAnalyzer(connection_config={"host": "localhost"})

    def test_column_info_dataclass(self):
        """ColumnInfo can be constructed with required + optional fields."""
        col = self.ColumnInfo(
            name="user_id",
            data_type="INT",
            is_nullable=False,
            is_primary_key=True,
            is_foreign_key=False,
        )
        assert col.name == "user_id"
        assert col.is_primary_key is True
        assert col.default_value is None
        assert col.auto_increment is False
        assert col.max_length is None

    def test_foreign_key_info_dataclass(self):
        """ForeignKeyInfo captures FK relationships with optional constraint name."""
        fk = self.ForeignKeyInfo(
            column_name="order_id",
            referenced_table="orders",
            referenced_column="id",
            constraint_name="fk_order",
        )
        assert fk.referenced_table == "orders"
        assert fk.constraint_name == "fk_order"

    def test_table_type_enum(self):
        """TableType enum has the four expected members."""
        TT = self.TableType
        assert set(TT.__members__.keys()) == {"ENTITY", "JOIN", "VIEW", "LOOKUP"}
        assert TT.ENTITY.value == "entity"
        assert TT.JOIN.value == "join"

    def test_is_join_table_logic(self):
        """The non-abstract is_join_table() should detect join tables correctly."""
        CI = self.ColumnInfo
        FK = self.ForeignKeyInfo
        TI = self.TableInfo
        TT = self.TableType

        analyzer = self._make_fake_analyzer()

        # A classic join table: two FK columns, nothing else
        join_table = TI(
            name="user_roles",
            table_type=TT.ENTITY,
            columns=[
                CI("user_id", "INT", False, False, True),
                CI("role_id", "INT", False, False, True),
            ],
            foreign_keys=[
                FK("user_id", "users", "id"),
                FK("role_id", "roles", "id"),
            ],
            row_count=10,
            primary_keys=[],
            indexes=[],
        )
        assert analyzer.is_join_table(join_table) is True

        # An entity table: one FK + several data columns
        entity_table = TI(
            name="orders",
            table_type=TT.ENTITY,
            columns=[
                CI("id", "INT", False, True, False),
                CI("user_id", "INT", False, False, True),
                CI("total", "DECIMAL", False, False, False),
                CI("status", "VARCHAR", False, False, False),
            ],
            foreign_keys=[
                FK("user_id", "users", "id"),
            ],
            row_count=100,
            primary_keys=["id"],
            indexes=[],
        )
        assert analyzer.is_join_table(entity_table) is False

    def test_relationship_info_dataclass(self):
        """RelationshipInfo defaults + optional join fields."""
        rel = self.RelationshipInfo(
            relationship_type="one_to_many",
            from_table="orders",
            from_column="user_id",
            to_table="users",
            to_column="id",
        )
        assert rel.join_table is None
        assert rel.additional_properties is None

    def test_database_structure_dataclass(self):
        """DatabaseStructure can be instantiated with all required fields."""
        ds = self.DatabaseStructure(
            tables={},
            entity_tables={},
            join_tables={},
            view_tables={},
            relationships=[],
            sample_data={},
            table_counts={},
            database_name="test_db",
            database_type="mysql",
        )
        assert ds.database_name == "test_db"
        assert ds.database_type == "mysql"
        assert len(ds.tables) == 0

    def test_connection_info_hides_password(self):
        """get_connection_info() should mask the password."""
        analyzer = self._make_fake_analyzer({"host": "localhost", "password": "secret123"})
        info = analyzer.get_connection_info()
        assert info["config"]["password"] == "***"
        assert info["database_type"] == "fake"
        assert info["connected"] is False

    def test_query_generation_module_exists(self):
        """The query_generation sub-package should have the expected files."""
        qg_dir = _INTEGRATIONS_DIR / "agents" / "query_generation"
        assert (qg_dir / "__init__.py").exists()
        assert (qg_dir / "cypher_generator.py").exists()
        assert (qg_dir / "schema_utilities.py").exists()


# ==================================================================
# Section 3: Graph Modeling (AST-based, avoids langchain import)
# ==================================================================

class TestGraphModeling:
    """Verify graph_modeling.py structure via AST since it imports langchain_core."""

    _GM_PATH = (
        _INTEGRATIONS_DIR / "agents" / "core" / "graph_modeling.py"
    )

    def test_graph_modeling_file_exists(self):
        """graph_modeling.py should exist."""
        assert self._GM_PATH.exists()

    def test_graph_modeling_has_expected_classes(self):
        """AST should contain HyGM, GraphNode, GraphRelationship, GraphModel,
        and the Pydantic models for LLM output."""
        tree = _parse_py(self._GM_PATH)
        class_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        }
        expected = {
            "HyGM",
            "GraphNode",
            "GraphRelationship",
            "GraphModel",
            "LLMGraphNode",
            "LLMGraphRelationship",
            "LLMGraphModel",
            "GraphModelingStrategy",
            "ModelingMode",
            "ModelOperation",
            "ModelModifications",
        }
        missing = expected - class_names
        assert not missing, f"Missing classes in graph_modeling.py: {missing}"

    def test_graph_modeling_hygm_methods(self):
        """HyGM class should have key methods (create_graph_model, validate_graph_model, etc.)."""
        tree = _parse_py(self._GM_PATH)
        hygm_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "HyGM":
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        hygm_methods.add(item.name)
        expected_methods = {
            "__init__",
            "create_graph_model",
            "model_graph",
            "validate_graph_model",
            "_automatic_modeling",
            "_generate_initial_model",
        }
        missing = expected_methods - hygm_methods
        assert not missing, f"Missing HyGM methods: {missing}"


# ==================================================================
# Section 4: LangChain Structures (3 tests, AST-based)
# ==================================================================

class TestLangChainStructures:
    """Test the langchain-memgraph sub-package (can't import due to langchain dep)."""

    _LC_DIR = _INTEGRATIONS_DIR / "langchain-memgraph" / "langchain_memgraph"

    def test_langchain_module_structure(self):
        """The expected sub-directories and key files should exist."""
        assert (self._LC_DIR / "__init__.py").exists() or (self._LC_DIR).is_dir()
        assert (self._LC_DIR / "graphs").is_dir()
        assert (self._LC_DIR / "graphs" / "graph_document.py").exists()
        assert (self._LC_DIR / "graphs" / "graph_store.py").exists()

    def test_graph_document_classes(self):
        """graph_document.py should define Node, Relationship, GraphDocument."""
        path = self._LC_DIR / "graphs" / "graph_document.py"
        tree = _parse_py(path)
        class_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        }
        assert {"Node", "Relationship", "GraphDocument"} <= class_names

    def test_graph_store_protocol(self):
        """graph_store.py should define a GraphStore Protocol with expected methods."""
        path = self._LC_DIR / "graphs" / "graph_store.py"
        tree = _parse_py(path)

        # Find GraphStore class
        gs_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "GraphStore":
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        gs_methods.add(item.name)
        expected = {"get_schema", "get_structured_schema", "query", "refresh_schema", "add_graph_documents"}
        missing = expected - gs_methods
        assert not missing, f"Missing GraphStore methods: {missing}"


# ==================================================================
# Section 5: MCP Server Structure (3 tests)
# ==================================================================

class TestMCPServerStructure:
    """Test the mcp-memgraph sub-package structure via AST."""

    _MCP_DIR = _INTEGRATIONS_DIR / "mcp-memgraph" / "src" / "mcp_memgraph"

    def test_mcp_server_module_exists(self):
        """MCP server should have __init__.py, server.py, main.py."""
        assert (self._MCP_DIR / "__init__.py").exists()
        assert (self._MCP_DIR / "server.py").exists()
        assert (self._MCP_DIR / "main.py").exists()

    def test_mcp_tool_definitions(self):
        """server.py should define the 9 expected MCP tool functions."""
        path = self._MCP_DIR / "server.py"
        tree = _parse_py(path)
        # Collect top-level function names
        func_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        expected_tools = {
            "run_query",
            "get_configuration",
            "get_index",
            "get_constraint",
            "get_schema",
            "get_storage",
            "get_triggers",
            "get_betweenness_centrality",
            "get_page_rank",
        }
        missing = expected_tools - func_names
        assert not missing, f"Missing MCP tool functions: {missing}"
        assert len(expected_tools) == 9

    def test_mcp_tools_have_docstrings(self):
        """Each MCP tool function should have a docstring (used as tool description)."""
        path = self._MCP_DIR / "server.py"
        tree = _parse_py(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                docstring = ast.get_docstring(node)
                assert docstring is not None, (
                    f"MCP tool function '{node.name}' is missing a docstring"
                )


# ==================================================================
# Section 6: Cross-cutting (2 tests)
# ==================================================================

class TestCrossCutting:
    """Cross-cutting structural tests."""

    def test_agents_subpackage_has_init(self):
        """Each sub-directory under agents/ should have an __init__.py."""
        agents_dir = _INTEGRATIONS_DIR / "agents"
        for subdir in agents_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith((".", "__")):
                init = subdir / "__init__.py"
                assert init.exists(), f"Missing __init__.py in {subdir}"

    def test_all_python_files_parse(self):
        """Every .py file under integrations/ should be valid Python syntax."""
        errors = []
        for py_file in _INTEGRATIONS_DIR.rglob("*.py"):
            try:
                _parse_py(py_file)
            except SyntaxError as e:
                errors.append(f"{py_file.relative_to(_INTEGRATIONS_DIR)}: {e}")
        assert not errors, f"Syntax errors found:\n" + "\n".join(errors)
