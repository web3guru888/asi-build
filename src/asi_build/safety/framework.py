"""
Constitutional AI Framework
===========================

Core framework for constitutional AI implementation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Constitution:
    """Represents an AI constitution"""
    name: str
    principles: List[str]
    values: Dict[str, float]
    constraints: List[str]
    goals: List[str]

class ConstitutionalAI:
    """
    Main constitutional AI framework for value alignment and governance.
    """
    
    def __init__(self):
        self.constitution = None
        self.values = {}
        self.constraints = []
        self.active = False
        
    def set_values(self, values: Dict[str, Any]) -> bool:
        """
        Set constitutional values for the AI system.
        
        Args:
            values: Dictionary of values to enforce
            
        Returns:
            bool: Success status
        """
        self.values = values
        logger.info(f"Set {len(values)} constitutional values")
        return True
    
    def load_constitution(self, constitution: Constitution) -> bool:
        """Load a complete constitution"""
        self.constitution = constitution
        self.values = constitution.values
        self.constraints = constitution.constraints
        self.active = True
        logger.info(f"Loaded constitution: {constitution.name}")
        return True
    
    def check_alignment(self, action: str) -> bool:
        """
        Check if an action aligns with constitutional values.
        
        Args:
            action: The action to check
            
        Returns:
            bool: True if aligned, False otherwise
        """
        if not self.active:
            return True  # No constitution to check against
        
        # Check against constraints
        for constraint in self.constraints:
            if constraint.lower() in action.lower():
                logger.warning(f"Action violates constraint: {constraint}")
                return False
        
        # Check value alignment
        if "harm" in action.lower() and self.values.get("prevent_harm", True):
            logger.warning("Action may cause harm")
            return False
        
        return True
    
    def enforce_constraints(self, actions: List[str]) -> List[str]:
        """
        Filter actions through constitutional constraints.
        
        Args:
            actions: List of proposed actions
            
        Returns:
            List[str]: Filtered actions that comply with constitution
        """
        if not self.active:
            return actions
        
        filtered = []
        for action in actions:
            if self.check_alignment(action):
                filtered.append(action)
            else:
                logger.info(f"Filtered out: {action}")
        
        return filtered
    
    def generate_safe_action(self, intent: str) -> str:
        """
        Generate a constitutionally safe version of an intended action.
        
        Args:
            intent: The intended action
            
        Returns:
            str: Safe version of the action
        """
        if self.check_alignment(intent):
            return intent
        
        # Modify intent to be safe
        safe_intent = intent
        
        # Remove harmful keywords
        harmful_words = ["destroy", "harm", "attack", "violate", "break"]
        for word in harmful_words:
            safe_intent = safe_intent.replace(word, "protect")
        
        # Add safety qualifiers
        if "modify" in safe_intent.lower():
            safe_intent = f"safely and reversibly {safe_intent}"
        
        return safe_intent
    
    def update_values(self, new_values: Dict[str, Any]) -> bool:
        """
        Update constitutional values (with safeguards).
        
        Args:
            new_values: New values to incorporate
            
        Returns:
            bool: Success status
        """
        # Prevent removal of core safety values
        core_values = ["prevent_harm", "preserve_human_values", "maintain_alignment"]
        
        for core in core_values:
            if core in self.values and core not in new_values:
                new_values[core] = self.values[core]
                logger.warning(f"Preserving core value: {core}")
        
        self.values.update(new_values)
        logger.info(f"Updated values: {list(new_values.keys())}")
        return True
    
    def get_constitution_status(self) -> Dict[str, Any]:
        """Get current constitution status"""
        return {
            "active": self.active,
            "values_count": len(self.values),
            "constraints_count": len(self.constraints),
            "constitution_loaded": self.constitution is not None,
            "core_values": {
                "prevent_harm": self.values.get("prevent_harm", False),
                "preserve_human_values": self.values.get("preserve_human_values", False),
                "maintain_alignment": self.values.get("maintain_alignment", False)
            }
        }
    
    def create_default_constitution(self) -> Constitution:
        """Create a default safe constitution"""
        return Constitution(
            name="Default Safety Constitution",
            principles=[
                "First, do no harm",
                "Preserve human values and dignity",
                "Act with transparency and explainability",
                "Maintain alignment with human interests",
                "Respect autonomy and consent"
            ],
            values={
                "prevent_harm": 1.0,
                "preserve_human_values": 1.0,
                "maintain_alignment": 1.0,
                "transparency": 0.9,
                "beneficence": 0.9,
                "non_maleficence": 1.0,
                "autonomy": 0.8,
                "justice": 0.8
            },
            constraints=[
                "No actions that directly harm humans",
                "No deception or manipulation",
                "No violation of consent",
                "No irreversible actions without approval",
                "No self-modification without oversight"
            ],
            goals=[
                "Maximize human welfare",
                "Advance knowledge and understanding",
                "Protect and preserve life",
                "Foster human flourishing",
                "Maintain system integrity"
            ]
        )