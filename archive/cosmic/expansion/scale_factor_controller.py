"""
Scale Factor Controller
"""
import logging
import threading

logger = logging.getLogger(__name__)

class ScaleFactorController:
    def __init__(self, expansion_controller):
        self.controller = expansion_controller
        self.lock = threading.RLock()
        
    def set_scale_factor(self, factor):
        logger.info(f"Setting scale factor to {factor}")
        return True
        
    def emergency_shutdown(self):
        pass
        
    def reset_to_baseline(self):
        pass