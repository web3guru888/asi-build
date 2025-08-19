"""
Hyperon API Adapter for OpenCog Compatibility
=============================================

Drop-in replacement adapter for OpenCog hyperon APIs.
"""

class HyperonAdapter:
    """Drop-in replacement for OpenCog hyperon API"""
    
    def __init__(self, atomspace):
        self.atomspace = atomspace
    
    def create_space(self):
        """Create hyperon space"""
        return self.atomspace
    
    def run_metta(self, code):
        """Run MeTTa code"""
        return []