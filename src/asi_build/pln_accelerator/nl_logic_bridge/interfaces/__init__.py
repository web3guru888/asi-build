"""
User interfaces for the NL-Logic Bridge system.
"""

try:
    from .query_interface import QueryInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    QueryInterface = None
try:
    from .web_interface import WebInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    WebInterface = None
try:
    from .cli_interface import CLIInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    CLIInterface = None
try:
    from .api_interface import APIInterface
except (ImportError, ModuleNotFoundError, SyntaxError):
    APIInterface = None

__all__ = ["QueryInterface", "WebInterface", "CLIInterface", "APIInterface"]
