"""
Utilities package for the MySQL to Memgraph migration agent.

This package contains reusable utility modules for environment management,
database probing, configuration management, and other common functionality.
"""

try:
    from .environment import (
        DatabaseConnectionError,
        MigrationEnvironmentError,
        get_memgraph_config,
        get_mysql_config,
        get_optional_environment_variables,
        get_required_environment_variables,
        load_environment,
        print_environment_help,
        print_troubleshooting_help,
        probe_all_connections,
        probe_memgraph_connection,
        probe_mysql_connection,
        setup_and_validate_environment,
        validate_environment_variables,
        validate_openai_api_key,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    MigrationEnvironmentError = None
    DatabaseConnectionError = None
    load_environment = None
    get_required_environment_variables = None
    get_optional_environment_variables = None
    validate_environment_variables = None
    get_mysql_config = None
    get_memgraph_config = None
    probe_mysql_connection = None
    probe_memgraph_connection = None
    validate_openai_api_key = None
    setup_and_validate_environment = None
    probe_all_connections = None
    print_environment_help = None
    print_troubleshooting_help = None

try:
    from .config import (
        MigrationConfig,
        get_available_presets,
        get_preset_config,
        merge_config_with_preset,
        print_config_summary,
    )
except (ImportError, ModuleNotFoundError, SyntaxError):
    MigrationConfig = None
    get_preset_config = None
    merge_config_with_preset = None
    print_config_summary = None
    get_available_presets = None

__all__ = [
    # Environment utilities
    "MigrationEnvironmentError",
    "DatabaseConnectionError",
    "load_environment",
    "get_required_environment_variables",
    "get_optional_environment_variables",
    "validate_environment_variables",
    "get_mysql_config",
    "get_memgraph_config",
    "probe_mysql_connection",
    "probe_memgraph_connection",
    "validate_openai_api_key",
    "setup_and_validate_environment",
    "probe_all_connections",
    "print_environment_help",
    "print_troubleshooting_help",
    # Configuration utilities
    "MigrationConfig",
    "get_preset_config",
    "merge_config_with_preset",
    "print_config_summary",
    "get_available_presets",
]
