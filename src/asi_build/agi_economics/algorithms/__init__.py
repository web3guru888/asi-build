"""
Resource Allocation Algorithms
=============================

Advanced algorithms for optimal resource allocation in AGI systems.
"""

try:
    from .resource_allocator import ResourceAllocator
except (ImportError, ModuleNotFoundError, SyntaxError):
    ResourceAllocator = None
try:
    from .auction_mechanisms import AuctionMechanism, VickreyAuction, DutchAuction
except (ImportError, ModuleNotFoundError, SyntaxError):
    AuctionMechanism = None
    VickreyAuction = None
    DutchAuction = None
try:
    from .optimization import OptimizationEngine
except (ImportError, ModuleNotFoundError, SyntaxError):
    OptimizationEngine = None

__all__ = [
    'ResourceAllocator',
    'AuctionMechanism',
    'VickreyAuction', 
    'DutchAuction',
    'OptimizationEngine'
]