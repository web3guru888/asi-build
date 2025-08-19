"""
Cosmic Event Logger - Logs all cosmic engineering events
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CosmicEventLogger:
    """Comprehensive logging system for cosmic events"""
    
    def __init__(self):
        self.events = []
        self.log_file = "cosmic_events.log"
        
    def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log cosmic event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": event_data
        }
        
        self.events.append(event)
        
        # Log to file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
            
        logger.info(f"Cosmic event logged: {event_type}")
        
    def log_galaxy_creation(self, galaxy_id: str, properties: Dict[str, Any]):
        """Log galaxy creation event"""
        self.log_event("galaxy_creation", {
            "galaxy_id": galaxy_id,
            "properties": properties
        })
        
    def log_black_hole_creation(self, bh_id: str, properties: Dict[str, Any]):
        """Log black hole creation event"""
        self.log_event("black_hole_creation", {
            "black_hole_id": bh_id,
            "properties": properties
        })
        
    def log_universe_creation(self, universe_id: str, initial_conditions: Dict[str, Any]):
        """Log universe creation event"""
        self.log_event("universe_creation", {
            "universe_id": universe_id,
            "initial_conditions": initial_conditions
        })
        
    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.events if e["event_type"] == event_type]
        
    def clear_events(self):
        """Clear event log"""
        self.events.clear()