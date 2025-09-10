"""
Component 7: Iterative Follow-Up

Agent solicits feedback at each step and offers options for reclassification, alternative prescriptions, or continued support.
The flow adapts dynamically, allowing recursive branching before completion.
"""

import logging
from typing import Dict, Any, Optional
from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class IterativeFollowUpComponent(BaseComponent):
    """Handles follow-up conversations and iterative improvements."""
    
    async def execute(self, session_id: str, user_input: str, image_data: Optional[str], 
                     session_data: Dict[str, Any], context: Dict[str, Any]) -> ComponentResult:
        
        # Analyze user's follow-up intent
        follow_up_intent = self._analyze_follow_up_intent(user_input, session_data)
        
        if follow_up_intent == 'reclassify':
            response = "I'll reclassify the image with different parameters. Please wait..."
            return self.create_success_result(
                response=response,
                session_data={'follow_up_action': 'reclassify'},
                requires_user_input=False,
                next_suggestions=['wait_for_results']
            )
        
        elif follow_up_intent == 'alternative_prescription':
            response = "Let me provide alternative treatment options based on your preferences."
            return self.create_success_result(
                response=response,
                session_data={'follow_up_action': 'alternative_prescription'},
                requires_user_input=False,
                next_suggestions=['view_alternatives']
            )
        
        elif follow_up_intent == 'new_problem':
            response = "I understand you have a different plant problem. Please upload a new image or describe the issue."
            return self.create_success_result(
                response=response,
                session_data={'follow_up_action': 'new_problem'},
                requires_user_input=True,
                next_suggestions=['upload_image', 'describe_problem']
            )
        
        elif follow_up_intent == 'continue_support':
            response = "I'm here to continue helping. What would you like to know more about?"
            follow_up_options = self._generate_follow_up_options(session_data)
            response += f"\n\n💡 Options:\n" + "\n".join(f"• {option}" for option in follow_up_options)
            
            return self.create_success_result(
                response=response,
                session_data={},
                requires_user_input=True,
                next_suggestions=follow_up_options
            )
        
        else:
            # Default completion response
            response = "Thank you for using Sasya Chikitsa! I hope the diagnosis and treatment recommendations are helpful. "
            response += "Feel free to return anytime for more plant health support."
            
            return self.create_success_result(
                response=response,
                session_data={'follow_up_action': 'complete'},
                requires_user_input=False,
                next_suggestions=['new_consultation', 'rate_service']
            )
    
    def _analyze_follow_up_intent(self, user_input: str, session_data: Dict[str, Any]) -> str:
        """Analyze what the user wants to do next."""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['reclassify', 'try again', 'different result']):
            return 'reclassify'
        elif any(word in user_input_lower for word in ['alternative', 'different treatment', 'other option']):
            return 'alternative_prescription'
        elif any(word in user_input_lower for word in ['new problem', 'different plant', 'another issue']):
            return 'new_problem'
        elif any(word in user_input_lower for word in ['more info', 'tell me more', 'continue', 'help']):
            return 'continue_support'
        else:
            return 'complete'
    
    def _generate_follow_up_options(self, session_data: Dict[str, Any]) -> list:
        """Generate contextual follow-up options."""
        options = ['Ask questions about treatment', 'Get prevention tips']
        
        if session_data.get('classification_results'):
            options.append('Learn more about this disease')
        
        if session_data.get('prescription'):
            options.extend(['Alternative treatments', 'Application instructions'])
        
        if session_data.get('vendor_recommendations'):
            options.append('More vendor options')
        
        options.extend(['New plant problem', 'Start over'])
        return options
