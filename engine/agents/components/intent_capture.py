"""
Component 1: Leaf Upload & Intent Capture

User uploads a leaf image and specifies if a disease classification is desired.
The agent records user input and begins dialog to clarify the objective.
"""

import logging
import re
from typing import Dict, Any, Optional

from .base_component import BaseComponent, ComponentResult

logger = logging.getLogger(__name__)

class IntentCaptureComponent(BaseComponent):
    """
    Handles initial user intent capture and image upload processing.
    
    This component:
    - Processes uploaded leaf images
    - Captures user's stated intent and objectives
    - Extracts initial context from user input
    - Determines if disease classification is desired
    - Sets up initial session profile
    """
    
    def __init__(self):
        super().__init__()
        self.intent_keywords = {
            'disease_classification': [
                'disease', 'sick', 'problem', 'wrong', 'diagnosis', 'identify', 
                'classify', 'what is', 'spots', 'yellowing', 'wilting', 'dying'
            ],
            'general_care': [
                'care', 'watering', 'fertilizer', 'nutrients', 'growing', 
                'maintenance', 'healthy', 'improve'
            ],
            'pest_identification': [
                'pest', 'bug', 'insect', 'eating', 'holes', 'damage', 'attack'
            ],
            'treatment_advice': [
                'treatment', 'cure', 'fix', 'help', 'remedy', 'solution', 'medicine'
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
        Execute intent capture and initial processing.
        
        Args:
            session_id: Session identifier
            user_input: User's message with their intent
            image_data: Base64 encoded leaf image
            session_data: Current session data
            context: Additional context
            
        Returns:
            ComponentResult with captured intent and next steps
        """
        # Extract user intent from input
        captured_intent = self._analyze_user_intent(user_input)
        
        # Process image if provided
        image_context = {}
        if image_data:
            image_context = await self._process_uploaded_image(image_data)
        
        # Extract additional context from user input
        extracted_context = self._extract_context_from_input(user_input)
        
        # Build user profile from available information
        user_profile = self._build_initial_user_profile(
            captured_intent, extracted_context, image_context, context or {}
        )
        
        # Determine if we need more information
        missing_info = self._identify_missing_information(user_profile, captured_intent)
        
        # Generate response based on captured information
        response = self._generate_intent_response(
            captured_intent, user_profile, missing_info, bool(image_data)
        )
        
        # Prepare session data update
        session_update = {
            'user_profile': user_profile,
            'captured_intent': captured_intent,
            'context': extracted_context,
            'has_image': bool(image_data),
            'missing_info': missing_info
        }
        
        # Determine if we need user input (usually yes for clarification)
        # If image + context provided, we can proceed automatically to classification
        has_sufficient_info = (bool(image_data) and 
                              user_profile.get('crop_type') and 
                              user_profile.get('location'))
        
        requires_input = len(missing_info) > 0 and not has_sufficient_info
        
        # Generate next step suggestions
        next_suggestions = self._generate_next_suggestions(captured_intent, missing_info, bool(image_data))
        
        logger.info(f"📋 Intent captured: {captured_intent.get('primary_intent', 'unclear')}")
        logger.debug(f"   Missing info: {missing_info}")
        logger.debug(f"   Requires input: {requires_input}")
        
        return self.create_success_result(
            response=response,
            session_data=session_update,
            requires_user_input=requires_input,
            next_suggestions=next_suggestions
        )

    def _analyze_user_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user input to determine their primary intent.
        
        Args:
            user_input: User's text input
            
        Returns:
            Dictionary with intent analysis results
        """
        user_input_lower = user_input.lower()
        
        # Score different intent categories
        intent_scores = {}
        for category, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in user_input_lower)
            if score > 0:
                intent_scores[category] = score
        
        # Determine primary intent
        primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k]) if intent_scores else 'general_inquiry'
        
        # Check for explicit disease classification request
        wants_classification = any(word in user_input_lower for word in [
            'classify', 'identify', 'diagnose', 'what is', 'what\'s wrong', 'disease'
        ])
        
        # Check for urgency indicators
        is_urgent = any(word in user_input_lower for word in [
            'urgent', 'dying', 'emergency', 'quickly', 'fast', 'immediate'
        ])
        
        return {
            'primary_intent': primary_intent,
            'intent_scores': intent_scores,
            'wants_classification': wants_classification,
            'is_urgent': is_urgent,
            'clear_intent': len(intent_scores) > 0,
            'original_input': user_input
        }

    async def _process_uploaded_image(self, image_data: str) -> Dict[str, Any]:
        """
        Process the uploaded leaf image and extract metadata.
        
        Args:
            image_data: Base64 encoded image
            
        Returns:
            Dictionary with image processing results
        """
        # Basic image validation and metadata extraction
        try:
            # Validate base64 format
            import base64
            decoded_data = base64.b64decode(image_data)
            image_size = len(decoded_data)
            
            # Estimate image quality (basic check)
            quality_estimate = "good" if image_size > 50000 else "low"
            
            return {
                'image_received': True,
                'image_size_bytes': image_size,
                'estimated_quality': quality_estimate,
                'processing_ready': True
            }
        except Exception as e:
            logger.warning(f"Image processing error: {e}")
            return {
                'image_received': True,
                'image_size_bytes': 0,
                'estimated_quality': "unknown",
                'processing_ready': False,
                'error': str(e)
            }

    def _extract_context_from_input(self, user_input: str) -> Dict[str, Any]:
        """
        Extract contextual information from user input.
        
        Args:
            user_input: User's text input
            
        Returns:
            Dictionary with extracted context
        """
        context = {}
        
        # Extract crop/plant type
        plant_patterns = [
            r'(?:my |the )?([a-zA-Z]+) (?:plant|crop|tree|leaf|leaves)',
            r'(?:tomato|potato|wheat|rice|corn|maize|cotton|sugarcane|onion|garlic)',
            r'(?:apple|mango|banana|citrus|orange|lemon)'
        ]
        
        for pattern in plant_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                if len(pattern.split('|')) > 1:  # Specific crop pattern
                    context['crop_type'] = match.group(0)
                else:
                    context['crop_type'] = match.group(1)
                break
        
        # Extract location information
        location_patterns = [
            r'(?:from |in |at )([A-Z][a-zA-Z\s]+(?:state|State|district|District))',
            r'(?:Punjab|Maharashtra|Gujarat|Karnataka|Tamil Nadu|Uttar Pradesh)',
            r'(?:India|Pakistan|Bangladesh|Sri Lanka)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, user_input)
            if match:
                context['location'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # Extract season/time information
        season_patterns = [
            r'(?:during |in |this )?(summer|winter|monsoon|spring|autumn|rainy|dry)',
            r'(?:kharif|rabi|zaid) season'
        ]
        
        for pattern in season_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                context['season'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # Extract problem description
        problem_indicators = ['problem', 'issue', 'wrong', 'sick', 'diseased', 'spots', 'yellowing']
        if any(indicator in user_input.lower() for indicator in problem_indicators):
            context['problem_description'] = user_input
        
        return context

    def _build_initial_user_profile(
        self,
        captured_intent: Dict[str, Any],
        extracted_context: Dict[str, Any],
        image_context: Dict[str, Any],
        request_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build initial user profile from captured information.
        
        Args:
            captured_intent: Captured user intent
            extracted_context: Extracted context information
            image_context: Image processing results
            request_context: Additional context from request parameter
            
        Returns:
            Initial user profile dictionary
        """
        profile = {
            'primary_intent': captured_intent.get('primary_intent'),
            'wants_classification': captured_intent.get('wants_classification', False),
            'is_urgent': captured_intent.get('is_urgent', False),
        }
        
        # Add context information from extracted text
        if 'crop_type' in extracted_context:
            profile['crop_type'] = extracted_context['crop_type']
        
        if 'location' in extracted_context:
            profile['location'] = extracted_context['location']
        
        if 'season' in extracted_context:
            profile['season'] = extracted_context['season']
        
        if 'problem_description' in extracted_context:
            profile['problem_description'] = extracted_context['problem_description']
            
        # PRIORITY: Use explicit context from request parameter (overrides extracted context)
        if request_context:
            if 'crop_type' in request_context:
                profile['crop_type'] = request_context['crop_type']
                logger.debug(f"   Using crop_type from request context: {request_context['crop_type']}")
                
            if 'location' in request_context:
                profile['location'] = request_context['location']
                logger.debug(f"   Using location from request context: {request_context['location']}")
                
            if 'season' in request_context:
                profile['season'] = request_context['season']
                logger.debug(f"   Using season from request context: {request_context['season']}")
        
        # Add image information
        profile['has_image'] = image_context.get('image_received', False)
        profile['image_quality'] = image_context.get('estimated_quality', 'unknown')
        
        return profile

    def _identify_missing_information(
        self,
        user_profile: Dict[str, Any],
        captured_intent: Dict[str, Any]
    ) -> list:
        """
        Identify what information is still needed.
        
        Args:
            user_profile: Current user profile
            captured_intent: Captured intent information
            
        Returns:
            List of missing information types
        """
        missing = []
        
        # For disease classification, we need certain information
        if user_profile.get('wants_classification', True):
            if not user_profile.get('has_image') and not user_profile.get('problem_description'):
                missing.append('image_or_description')
            
            if not user_profile.get('crop_type'):
                missing.append('crop_type')
        
        # For any treatment advice, location is helpful
        if not user_profile.get('location') and captured_intent.get('primary_intent') in ['treatment_advice', 'disease_classification']:
            missing.append('location')
        
        # Check if intent is unclear
        if not captured_intent.get('clear_intent', False):
            missing.append('clear_intent')
        
        return missing

    def _generate_intent_response(
        self,
        captured_intent: Dict[str, Any],
        user_profile: Dict[str, Any],
        missing_info: list,
        has_image: bool
    ) -> str:
        """
        Generate appropriate response based on captured intent.
        
        Args:
            captured_intent: Captured user intent
            user_profile: User profile data
            missing_info: List of missing information
            has_image: Whether image was uploaded
            
        Returns:
            Response message for user
        """
        # Build response based on primary intent
        primary_intent = captured_intent.get('primary_intent', 'general_inquiry')
        
        if primary_intent == 'disease_classification':
            if has_image:
                response = "I can see you've uploaded a leaf image for disease identification. "
            else:
                response = "I understand you want help identifying a plant disease. "
        
        elif primary_intent == 'treatment_advice':
            response = "I see you're looking for treatment advice for your plant. "
        
        elif primary_intent == 'pest_identification':
            response = "I can help you identify and deal with pest problems on your plants. "
        
        elif primary_intent == 'general_care':
            response = "I'd be happy to help with general plant care advice. "
        
        else:
            response = "I'm here to help with your plant health questions. "
        
        # Add what we've understood
        understood = []
        if user_profile.get('crop_type'):
            understood.append(f"crop type: {user_profile['crop_type']}")
        if user_profile.get('location'):
            understood.append(f"location: {user_profile['location']}")
        if user_profile.get('season'):
            understood.append(f"season: {user_profile['season']}")
        
        if understood:
            response += f"I've noted your {', '.join(understood)}. "
        
        # Add what we still need
        if missing_info:
            if 'crop_type' in missing_info:
                response += "What type of crop or plant is this? "
            
            if 'location' in missing_info:
                response += "What's your location (district/state) so I can provide region-specific advice? "
            
            if 'image_or_description' in missing_info:
                response += "Could you upload a clear image of the affected leaves or describe the symptoms you're seeing? "
            
            if 'clear_intent' in missing_info:
                response += "Could you tell me more about what specific help you need? "
        
        else:
            response += "I have enough information to proceed with helping you!"
        
        return response

    def _generate_next_suggestions(
        self,
        captured_intent: Dict[str, Any],
        missing_info: list,
        has_image: bool
    ) -> list:
        """
        Generate suggestions for next user actions.
        
        Args:
            captured_intent: Captured intent
            missing_info: Missing information list
            has_image: Whether image exists
            
        Returns:
            List of suggested actions
        """
        suggestions = []
        
        if 'crop_type' in missing_info:
            suggestions.append("Tell me your crop type (e.g., 'tomato', 'wheat', 'cotton')")
        
        if 'location' in missing_info:
            suggestions.append("Share your location for region-specific advice")
        
        if 'image_or_description' in missing_info:
            if not has_image:
                suggestions.append("Upload a clear image of affected leaves")
            suggestions.append("Describe the symptoms you're seeing")
        
        if not missing_info:
            if captured_intent.get('wants_classification'):
                suggestions.append("Proceed with disease classification")
            suggestions.append("Ask follow-up questions")
        
        return suggestions
