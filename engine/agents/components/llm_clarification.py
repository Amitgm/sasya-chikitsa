"""
Component 2: LLM-Guided Clarification

Ollama LLM prompts user for additional context: crop type, location, previous treatments, etc.
This ensures detailed understanding and personalizes the subsequent steps.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class LLMClarificationComponent(BaseComponent):
    """
    Uses Ollama LLM to intelligently guide clarification conversations.
    
    This component:
    - Uses LLM to ask intelligent follow-up questions
    - Personalizes questions based on user's context and intent
    - Ensures all necessary information is gathered efficiently
    - Adapts questioning strategy based on user responses
    - Validates completeness of gathered information
    """
    
    def __init__(self):
        super().__init__()
        # Import LLM here to avoid circular imports
        from api.agent_core import create_llm
        self.llm = create_llm()
        
        # Essential information categories for different intents
        self.required_info = {
            'disease_classification': ['crop_type', 'location', 'problem_description'],
            'treatment_advice': ['crop_type', 'location', 'current_problem'],
            'pest_identification': ['crop_type', 'symptom_description'],
            'general_care': ['crop_type'],
            'prescription_request': ['crop_type', 'location', 'season', 'disease_name']
        }
        
        # Question templates for different information types
        self.question_templates = {
            'crop_type': [
                "What type of crop or plant are you growing?",
                "Which plant is affected?",
                "What crop species is this?"
            ],
            'location': [
                "What's your location (district and state)?",
                "Where is your farm or garden located?",
                "Which region are you farming in?"
            ],
            'season': [
                "What's the current season?",
                "Are you in Kharif, Rabi, or Zaid season?",
                "What time of year is it?"
            ],
            'problem_description': [
                "Can you describe the symptoms you're seeing?",
                "What problems are you noticing with your plants?",
                "How do the affected plants look?"
            ],
            'previous_treatments': [
                "Have you tried any treatments so far?",
                "What have you done to address this issue?",
                "Any pesticides or fertilizers used recently?"
            ],
            'farm_size': [
                "How large is your farm or garden?",
                "What's the scale of your operation?",
                "Are you growing commercially or for personal use?"
            ]
        }

    async def execute(
        self,
        session_id: str,
        user_input: str,
        image_data: Optional[str],
        session_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ComponentResult:
        """
        Execute LLM-guided clarification to gather missing information.
        
        Args:
            session_id: Session identifier
            user_input: User's response to previous questions
            image_data: Image data if provided
            session_data: Current session data
            context: Additional context
            
        Returns:
            ComponentResult with clarification questions or completion
        """
        # Get current user profile and intent
        user_profile = session_data.get('user_profile', {})
        primary_intent = user_profile.get('primary_intent', 'general_inquiry')
        
        # Process user's response to extract new information
        extracted_info = await self._extract_information_from_response(user_input, user_profile)
        
        # Update user profile with extracted information
        updated_profile = {**user_profile, **extracted_info}
        
        # Determine what information is still missing
        missing_info = self._identify_missing_info(updated_profile, primary_intent)
        
        # Generate appropriate response
        if missing_info:
            # Use LLM to generate intelligent follow-up questions
            response = await self._generate_clarification_questions(
                updated_profile, missing_info, user_input
            )
            requires_input = True
            next_suggestions = self._generate_clarification_suggestions(missing_info)
        else:
            # All necessary information gathered
            response = self._generate_completion_response(updated_profile, primary_intent)
            requires_input = False
            next_suggestions = ['proceed_to_classification', 'modify_information']
        
        # Prepare session data update
        session_update = {
            'user_profile': updated_profile,
            'clarification_data': extracted_info,
            'missing_info': missing_info,
            'clarification_complete': len(missing_info) == 0
        }
        
        logger.info(f"💬 Clarification step: {len(missing_info)} items missing")
        logger.debug(f"   Missing: {missing_info}")
        logger.debug(f"   Profile updated: {bool(extracted_info)}")
        
        return self.create_success_result(
            response=response,
            session_data=session_update,
            requires_user_input=requires_input,
            next_suggestions=next_suggestions
        )

    async def _extract_information_from_response(
        self,
        user_response: str,
        current_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured information from user's response using LLM.
        
        Args:
            user_response: User's text response
            current_profile: Current user profile
            
        Returns:
            Dictionary with extracted information
        """
        if not user_response.strip():
            return {}
        
        # Create prompt for LLM to extract structured information
        extraction_prompt = f"""
Extract specific information from this user response about their plant/crop problem:

User Response: "{user_response}"

Current Information: {current_profile}

Extract and return ONLY the new information in this format:
- Crop Type: [if mentioned]
- Location: [if mentioned, include district/state]
- Season: [if mentioned]
- Problem Description: [symptoms/issues mentioned]
- Previous Treatments: [if mentioned]
- Urgency: [urgent/normal if indicated]

If information is not mentioned, don't make assumptions. Only extract what is clearly stated.
"""
        
        try:
            # Get LLM response
            llm_response = await asyncio.to_thread(self.llm.invoke, extraction_prompt)
            response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # Parse LLM response into structured data
            extracted = self._parse_llm_extraction(response_text)
            
            logger.debug(f"📝 Extracted from user response: {extracted}")
            return extracted
            
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")
            return self._fallback_extraction(user_response)

    def _parse_llm_extraction(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse structured information from LLM response.
        
        Args:
            llm_response: LLM's extraction response
            
        Returns:
            Parsed information dictionary
        """
        extracted = {}
        
        # Parse each line for information
        lines = llm_response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip('- ').lower().replace(' ', '_')
                value = value.strip()
                
                # Only add if value is not empty or placeholder
                if value and value != '[if mentioned]' and value != '[not mentioned]':
                    if key == 'crop_type':
                        extracted['crop_type'] = value
                    elif key == 'location':
                        extracted['location'] = value
                    elif key == 'season':
                        extracted['season'] = value
                    elif key == 'problem_description':
                        extracted['problem_description'] = value
                    elif key == 'previous_treatments':
                        extracted['previous_treatments'] = value
                    elif key == 'urgency' and value.lower() == 'urgent':
                        extracted['is_urgent'] = True
        
        return extracted

    def _fallback_extraction(self, user_response: str) -> Dict[str, Any]:
        """
        Fallback extraction method using simple pattern matching.
        
        Args:
            user_response: User's response
            
        Returns:
            Extracted information
        """
        import re
        extracted = {}
        response_lower = user_response.lower()
        
        # Simple crop type extraction
        crop_patterns = ['tomato', 'potato', 'wheat', 'rice', 'corn', 'cotton', 'onion']
        for crop in crop_patterns:
            if crop in response_lower:
                extracted['crop_type'] = crop
                break
        
        # Simple location extraction
        location_match = re.search(r'\b([A-Z][a-zA-Z]+)\s*,?\s*([A-Z][a-zA-Z]+)\b', user_response)
        if location_match:
            extracted['location'] = f"{location_match.group(1)}, {location_match.group(2)}"
        
        # Season extraction
        seasons = ['kharif', 'rabi', 'zaid', 'summer', 'winter', 'monsoon', 'rainy']
        for season in seasons:
            if season in response_lower:
                extracted['season'] = season
                break
        
        return extracted

    def _identify_missing_info(self, user_profile: Dict[str, Any], intent: str) -> list:
        """
        Identify what information is still missing based on intent.
        
        Args:
            user_profile: Current user profile
            intent: User's primary intent
            
        Returns:
            List of missing information categories
        """
        required_for_intent = self.required_info.get(intent, ['crop_type'])
        missing = []
        
        for info_type in required_for_intent:
            if not user_profile.get(info_type):
                missing.append(info_type)
        
        # Special cases based on context
        if intent in ['treatment_advice', 'prescription_request']:
            if not user_profile.get('season') and user_profile.get('location'):
                missing.append('season')
            
            if not user_profile.get('previous_treatments'):
                missing.append('previous_treatments')
        
        return missing

    async def _generate_clarification_questions(
        self,
        user_profile: Dict[str, Any],
        missing_info: list,
        user_response: str
    ) -> str:
        """
        Generate intelligent clarification questions using LLM.
        
        Args:
            user_profile: Current user profile
            missing_info: List of missing information types
            user_response: User's previous response
            
        Returns:
            Generated clarification question(s)
        """
        # Create context-aware prompt for question generation
        context_prompt = f"""
You are an expert plant disease consultant. You need to ask follow-up questions to help a farmer.

Current Information About User:
{self._format_profile_for_prompt(user_profile)}

Missing Information: {', '.join(missing_info)}
User's Last Response: "{user_response}"

Generate 1-2 intelligent, contextual questions to gather the missing information. 
Be conversational, empathetic, and specific to their farming situation.
Ask about the most critical missing information first.

Focus on: {missing_info[0] if missing_info else 'general clarification'}
"""
        
        try:
            llm_response = await asyncio.to_thread(self.llm.invoke, context_prompt)
            response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # Clean up the response
            cleaned_response = response_text.strip()
            
            # Add helpful context if appropriate
            if 'location' in missing_info:
                cleaned_response += "\n\n💡 I ask about location to provide region-specific treatment recommendations and local vendor suggestions."
            
            logger.debug(f"💬 Generated LLM clarification: {cleaned_response[:100]}...")
            return cleaned_response
            
        except Exception as e:
            logger.warning(f"LLM question generation failed, using template: {e}")
            return self._generate_template_question(missing_info[0] if missing_info else 'general')

    def _generate_template_question(self, info_type: str) -> str:
        """
        Generate question using predefined templates as fallback.
        
        Args:
            info_type: Type of information needed
            
        Returns:
            Template-based question
        """
        templates = self.question_templates.get(info_type, ["Could you provide more details?"])
        
        # Use first template for simplicity
        question = templates[0]
        
        # Add helpful context
        if info_type == 'location':
            question += " This helps me provide region-specific advice and local vendor suggestions."
        elif info_type == 'crop_type':
            question += " Different crops have different disease patterns and treatments."
        elif info_type == 'season':
            question += " Treatment timing depends on the growing season."
        
        return question

    def _generate_completion_response(
        self,
        user_profile: Dict[str, Any],
        intent: str
    ) -> str:
        """
        Generate response when clarification is complete.
        
        Args:
            user_profile: Complete user profile
            intent: User's primary intent
            
        Returns:
            Completion response message
        """
        response = "Perfect! I now have all the information I need. "
        
        # Summarize what we know
        summary_parts = []
        if user_profile.get('crop_type'):
            summary_parts.append(f"Crop: {user_profile['crop_type']}")
        if user_profile.get('location'):
            summary_parts.append(f"Location: {user_profile['location']}")
        if user_profile.get('season'):
            summary_parts.append(f"Season: {user_profile['season']}")
        
        if summary_parts:
            response += f"Here's what I understand: {', '.join(summary_parts)}. "
        
        # Add next step based on intent
        if intent == 'disease_classification':
            if user_profile.get('has_image'):
                response += "I'll now analyze your leaf image to identify any diseases."
            else:
                response += "Based on your description, I'll help identify the potential disease."
        elif intent == 'treatment_advice':
            response += "I'll provide specific treatment recommendations for your situation."
        elif intent == 'prescription_request':
            response += "I'll generate a detailed prescription based on your location and crop."
        else:
            response += "Let me provide the best possible advice for your situation."
        
        return response

    def _generate_clarification_suggestions(self, missing_info: list) -> list:
        """
        Generate suggestions for missing information.
        
        Args:
            missing_info: List of missing information types
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        for info_type in missing_info[:3]:  # Limit to top 3 suggestions
            if info_type == 'crop_type':
                suggestions.append("Specify your crop (e.g., 'tomato', 'wheat', 'rice')")
            elif info_type == 'location':
                suggestions.append("Share your district and state")
            elif info_type == 'season':
                suggestions.append("Tell me the current season")
            elif info_type == 'problem_description':
                suggestions.append("Describe the symptoms you see")
            elif info_type == 'previous_treatments':
                suggestions.append("Mention any treatments you've tried")
        
        return suggestions

    def _format_profile_for_prompt(self, profile: Dict[str, Any]) -> str:
        """Format user profile for LLM prompt."""
        formatted = []
        for key, value in profile.items():
            if value and key != 'primary_intent':
                formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        return '\n'.join(formatted) if formatted else "No information provided yet"
