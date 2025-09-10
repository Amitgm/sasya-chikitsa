"""
Component 5: Display & Constraint Gathering

Agent presents prescription/advice, asking for further preferences (e.g., organic treatments, regional restrictions).
User can request alternatives or clarify constraints.
"""

import logging
from typing import Dict, Any, Optional
from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class ConstraintGatheringComponent(BaseComponent):
    """Handles gathering user constraints and preferences for treatment."""
    
    async def execute(self, session_id: str, user_input: str, image_data: Optional[str], 
                     session_data: Dict[str, Any], context: Dict[str, Any]) -> ComponentResult:
        
        # Parse user preferences from input
        preferences = self._extract_preferences(user_input)
        
        response = "I understand your preferences. "
        if preferences.get('organic_only'):
            response += "I'll focus on organic treatment options. "
        if preferences.get('budget_constraint'):
            response += f"I'll consider your budget constraint of {preferences['budget_constraint']}. "
        
        response += "Let me update the prescription accordingly."
        
        return self.create_success_result(
            response=response,
            session_data={'user_constraints': preferences},
            requires_user_input=False,
            next_suggestions=['proceed_to_prescription', 'specify_more_constraints']
        )
    
    def _extract_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract user preferences from input."""
        prefs = {}
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['organic', 'natural', 'chemical-free']):
            prefs['organic_only'] = True
        
        if any(word in user_input_lower for word in ['budget', 'cheap', 'affordable', 'low cost']):
            prefs['budget_constraint'] = 'low'
        
        return prefs
