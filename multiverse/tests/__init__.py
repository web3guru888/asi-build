"""
Multiverse Framework Test Suite
==============================

Comprehensive test suite for the multiverse framework covering all
components, integration points, and operational scenarios.
"""

import sys
import os

# Add multiverse path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test categories
from .unit import *
from .integration import *
from .performance import *
from .stress import *

__all__ = [
    'run_all_tests',
    'run_unit_tests', 
    'run_integration_tests',
    'run_performance_tests',
    'run_stress_tests'
]

def run_all_tests():
    """Run all multiverse framework tests."""
    import unittest
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_unit_tests():
    """Run unit tests only."""
    import unittest
    from .unit import *
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__ + '.unit'])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests only."""
    import unittest
    from .integration import *
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__ + '.integration'])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_performance_tests():
    """Run performance tests only."""
    import unittest
    from .performance import *
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__ + '.performance'])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_stress_tests():
    """Run stress tests only."""
    import unittest
    from .stress import *
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__ + '.stress'])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)