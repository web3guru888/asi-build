"""
Natural language generation and explanation systems.
"""

try:
    from .explanation_generator import ExplanationGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ExplanationGenerator = None
try:
    from .nl_generator import NLGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    NLGenerator = None
try:
    from .template_generator import TemplateGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    TemplateGenerator = None
try:
    from .multilingual_generator import MultilingualGenerator
except (ImportError, ModuleNotFoundError, SyntaxError):
    MultilingualGenerator = None

__all__ = ["ExplanationGenerator", "NLGenerator", "TemplateGenerator", "MultilingualGenerator"]