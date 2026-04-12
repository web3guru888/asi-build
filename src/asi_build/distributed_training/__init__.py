"""
decentralized_training - ASI:BUILD Integrated System
Consolidated on: Tue Aug 19 06:40:01 +08 2025
"""

import importlib

# Auto-import all modules
import os
from pathlib import Path

current_dir = Path(__file__).parent
python_files = [f.stem for f in current_dir.glob("*.py") if f.stem != "__init__"]

__all__ = []
for module_name in python_files:
    try:
        module = importlib.import_module(f".{module_name}", package=__name__)
        for attr_name in dir(module):
            if not attr_name.startswith("_"):
                attr = getattr(module, attr_name)
                if callable(attr) or isinstance(attr, type):
                    globals()[attr_name] = attr
                    __all__.append(attr_name)
    except ImportError:
        pass

__version__ = "1.0.0-consolidated"
__maturity__ = "alpha"
__consolidation_date__ = "Tue Aug 19 06:40:01 +08 2025"
