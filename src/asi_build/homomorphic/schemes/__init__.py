"""
Homomorphic encryption schemes implementation.
"""

try:
    from .ckks import CKKSScheme
except (ImportError, ModuleNotFoundError, SyntaxError):
    CKKSScheme = None
try:
    from .bfv import BFVScheme  
except (ImportError, ModuleNotFoundError, SyntaxError):
    BFVScheme = None
try:
    from .bgv import BGVScheme
except (ImportError, ModuleNotFoundError, SyntaxError):
    BGVScheme = None
try:
    from ..core.base import SchemeType
except (ImportError, ModuleNotFoundError, SyntaxError):
    SchemeType = None

__all__ = [
    "CKKSScheme",
    "BFVScheme", 
    "BGVScheme",
    "get_scheme_class"
]


def get_scheme_class(scheme_type: SchemeType):
    """
    Get the appropriate scheme class for the given scheme type.
    
    Args:
        scheme_type: The type of FHE scheme
    
    Returns:
        Appropriate scheme class
    """
    if scheme_type == SchemeType.CKKS:
        return CKKSScheme
    elif scheme_type == SchemeType.BFV:
        return BFVScheme
    elif scheme_type == SchemeType.BGV:
        return BGVScheme
    else:
        raise ValueError(f"Unknown scheme type: {scheme_type}")