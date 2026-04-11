"""
Homomorphic encryption schemes implementation.
"""

from .ckks import CKKSScheme
from .bfv import BFVScheme  
from .bgv import BGVScheme
from ..core.base import SchemeType

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