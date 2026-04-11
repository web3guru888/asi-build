"""
Wave Systems - Complete 6-Wave Architecture
Consolidated on: $(date)
"""

# Import all wave systems
for wave_num in range(1, 7):
    try:
        exec(f"from .wave{wave_num} import *")
    except ImportError:
        pass

__version__ = "1.0.0-consolidated"
__waves__ = 6
