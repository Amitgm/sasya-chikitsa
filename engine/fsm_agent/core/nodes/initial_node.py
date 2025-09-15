"""
Initial Node for FSM Agent workflow
Handles user input and determines first action based on user intent
"""

import logging
from typing import Dict, Any, Optional

from .base_node import BaseNode

try:
    from ..workflow_state import WorkflowState, add_message_to_state, set_error
    from ...tools.context_extractor import ContextExtractorTool
except ImportError:
    from engine.fsm_agent.core.workflow_state import WorkflowState, add_message_to_state, set_error
    from engine.fsm_agent.tools.context_extractor import ContextExtractorTool

logger = logging.getLogger(__name__)


class InitialNode(BaseNode):
    """Initial node - handles user input and determines first action based on user intent"""
    
    @property
    def node_name(self) -> str:
        return "initial"
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute initial node logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.update_node_state(state)
        
        try:
            # Check if this is a continuing conversation (loaded from session)
            is_continuing_conversation = self._is_continuing_conversation(state)
            
            if is_continuing_conversation:
                # This is a followup in an existing conversation - route to followup handling
                logger.info(f"🔄 Detected continuing conversation for session {state['session_id']} - routing to followup")
                state["next_action"] = "followup"
                return state
            
            # Analyze user intent for NEW conversations
            user_intent = await self._analyze_user_intent(state["user_message"])
            state["user_intent"] = user_intent
            
            # Extract context from user message if possible
            context_tool = self.tools["context_extractor"]
            context_input = {"user_message": state["user_message"]}
            context_result = await context_tool.arun(context_input)
            
            if context_result and not context_result.get("error"):
                self._process_context_extraction(state, context_result)
            
            # Store general answer for later use (for hybrid requests)
            general_answer = user_intent.get("general_answer", "")
            if general_answer:
                state["general_answer"] = general_answer
                logger.info(f"🌾 Stored general answer for hybrid request: {general_answer[:100]}...")
            
            # Determine next action based on user intent and input
            self._determine_next_action(state, user_intent, general_answer)
            
        except Exception as e:
            logger.error(f"Error in initial node: {str(e)}", exc_info=True)
            set_error(state, f"Error processing initial request: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
    def _process_context_extraction(self, state: WorkflowState, context_result: Dict[str, Any]) -> None:
        """Process context extraction results and update state"""
        # Debug: Log current state before context processing
        logger.info(f"🔍 BEFORE context processing - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
        logger.info(f"🔍 Context extractor result: {context_result}")
        
        # Preserve existing context from API request, only supplement missing values
        existing_context = state.get("user_context", {})
        extracted_context = context_result or {}
        
        # Merge contexts - API context takes precedence, extractor supplements
        merged_context = {**extracted_context, **existing_context}
        state["user_context"] = merged_context
        
        # Only update individual fields if not already set from API request
        context_fields = [
            ("location", "🔄 Updating location from extractor", "✅ Keeping API location"),
            ("season", "🔄 Updating season from extractor", "✅ Keeping API season"),
            ("plant_type", "🔄 Updating plant_type from extractor", "✅ Keeping API plant_type"),
            ("growth_stage", None, None)
        ]
        
        for field, update_msg, keep_msg in context_fields:
            if not state.get(field):
                if update_msg:
                    logger.info(f"{update_msg}: {context_result.get(field)}")
                state[field] = context_result.get(field)
            else:
                if keep_msg:
                    logger.info(f"{keep_msg}: {state.get(field)}")
        
        # Debug: Log final state after context processing
        logger.info(f"✅ AFTER context processing - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
    
    def _determine_next_action(self, state: WorkflowState, user_intent: Dict[str, Any], general_answer: str) -> None:
        """Determine the next action based on user intent"""
        # Check for tool requests first, then handle pure general questions
        if state.get("user_image") and user_intent["wants_classification"]:
            # Has image and user wants classification
            state["next_action"] = "classify"
            classification_msg = "🌱 I can see you've uploaded an image of a plant leaf. Let me analyze it for disease detection."
            
            # Add general answer if this is a hybrid request
            if general_answer:
                classification_msg += f"\n\n🌾 **General Agricultural Advice:** {general_answer}"
            
            add_message_to_state(state, "assistant", classification_msg)
            
        elif user_intent["wants_classification"] and not state.get("user_image"):
            # Wants classification but no image
            state["next_action"] = "request_image"
            image_request_msg = "🌱 I'd be happy to help analyze your plant! Please upload a clear photo of the affected leaf showing any symptoms."
            
            # Add general answer if this is a hybrid request
            if general_answer:
                image_request_msg += f"\n\n🌾 **General Agricultural Advice:** {general_answer}"
            
            add_message_to_state(state, "assistant", image_request_msg)
            state["requires_user_input"] = True
            
        elif user_intent.get("is_general_question", False) and not any([
            user_intent["wants_classification"], 
            user_intent["wants_prescription"], 
            user_intent["wants_vendors"]
        ]):
            # Pure general question (no tool requests)
            state["next_action"] = "completed"
            if general_answer:
                add_message_to_state(
                    state,
                    "assistant", 
                    f"🌾 {general_answer}\n\nIs there anything else I can help you with regarding plant disease diagnosis or treatment?"
                )
            else:
                add_message_to_state(
                    state,
                    "assistant", 
                    "🌾 I understand you have a general farming question. I can provide basic guidance on agricultural topics, but I specialize in plant disease diagnosis and treatment. Feel free to ask about specific plant issues or upload a photo for disease analysis!"
                )
            state["requires_user_input"] = False
        else:
            # General greeting or unclear intent
            state["next_action"] = "general_help"
            help_msg = "🌱 Hello! I'm your plant disease diagnosis assistant. I can help you:\n\n" + \
                      "• **Identify diseases** - Upload a photo for analysis\n" + \
                      "• **Get treatment recommendations** - Get prescription after diagnosis\n" + \
                      "• **Find vendors** - Locate suppliers for treatments\n\n" + \
                      "What would you like me to help you with today?"
            
            # Add general answer if available
            if general_answer:
                help_msg = f"🌾 {general_answer}\n\n" + help_msg
            
            add_message_to_state(state, "assistant", help_msg)
            state["requires_user_input"] = True
    
    async def _analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Analyze user intent using LLM to determine what they want from the agent.
        This provides much more robust intent recognition than keyword matching.
        Handles both specialized tool requests and general agricultural questions.
        """
        try:
            intent_prompt = self._build_intent_analysis_prompt(user_message)
            
            # Get LLM response
            response = await self.llm.ainvoke(intent_prompt)
            response_text = response.content.strip()
            
            logger.debug(f"🧠 LLM intent analysis raw response: {response_text}")
            
            # Parse JSON response
            intent = self._parse_intent_response(response_text)
            if intent:
                logger.info(f"🎯 LLM-driven user intent analysis: {intent}")
                return intent
                    
        except Exception as e:
            logger.error(f"❌ Error in LLM intent analysis: {e}, using fallback analysis")
        
        # Fallback to simple keyword-based analysis if LLM fails
        logger.info("🔄 Using fallback keyword-based intent analysis")
        return await self._fallback_intent_analysis(user_message)
    
    def _build_intent_analysis_prompt(self, user_message: str) -> str:
        """Build the intent analysis prompt"""
        return f"""You are an expert at understanding user intent for a plant disease diagnosis and treatment system.

Analyze the following user message and determine their intent by responding with ONLY a JSON object containing these fields:
- wants_classification: (boolean) Does the user want disease diagnosis/identification?
- wants_prescription: (boolean) Does the user want treatment recommendations?  
- wants_vendors: (boolean) Does the user want to find/buy products?
- wants_full_workflow: (boolean) Does the user want the complete process (diagnosis + treatment + vendors)?
- is_general_question: (boolean) Does the message contain general agricultural/farming questions (soil tips, weather advice, growing tips, etc.)?
- general_answer: (string) If is_general_question=true, provide helpful answers to the general agriculture questions. Otherwise, leave as empty string.

Rules:
1. If they want prescription OR vendors OR full workflow, they automatically need classification first
2. If they want vendors OR full workflow, they automatically need prescription first
3. Use natural language understanding, not just keyword matching
4. Consider context and implied meaning
5. IMPORTANT: Tool requests (wants_*) and general questions (is_general_question) are NOT mutually exclusive
6. A message can contain BOTH tool requests AND general questions - analyze each part independently
7. If any part asks for general advice (soil health, weather, growing tips, timing, etc.), set is_general_question=true
8. Answer the general questions even if there are also tool requests in the same message

Examples:
- "What's wrong with my plant?" → {{"wants_classification": true, "wants_prescription": false, "wants_vendors": false, "wants_full_workflow": false, "is_general_question": false, "general_answer": ""}}
- "Help my tomato plant get better" → {{"wants_classification": true, "wants_prescription": true, "wants_vendors": false, "wants_full_workflow": false, "is_general_question": false, "general_answer": ""}}
- "What's the best time to plant tomatoes?" → {{"wants_classification": false, "wants_prescription": false, "wants_vendors": false, "wants_full_workflow": false, "is_general_question": true, "general_answer": "The best time to plant tomatoes depends on your location. Generally, plant tomatoes after the last frost date in your area. In most regions, this is 2-3 weeks after the last frost when soil temperature reaches 60-65°F (15-18°C). For warm climates, plant in early spring or fall. For cooler climates, start seeds indoors 6-8 weeks before the last frost date."}}
- "Analyze my plant disease and also give me watering tips" → {{"wants_classification": true, "wants_prescription": false, "wants_vendors": false, "wants_full_workflow": false, "is_general_question": true, "general_answer": "For proper watering: Water deeply but less frequently to encourage deep root growth. Check soil moisture 2-3 inches deep - if dry, it's time to water. Most crops need 1-2 inches of water per week including rainfall. Water early morning to reduce evaporation and disease risk."}}
- "Diagnose this leaf, get treatment, and tell me about soil health" → {{"wants_classification": true, "wants_prescription": true, "wants_vendors": false, "wants_full_workflow": false, "is_general_question": true, "general_answer": "For healthy soil: Test pH regularly (most crops prefer 6.0-7.0). Add organic matter like compost to improve structure and nutrients. Ensure good drainage while retaining moisture. Rotate crops to prevent nutrient depletion. Consider cover crops during off-season to maintain soil health."}}

User message: "{user_message}"

Response (JSON only):"""
    
    def _parse_intent_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM intent response"""
        try:
            import json
            # Extract JSON from response (in case there's extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                intent = json.loads(json_str)
                
                # Ensure all required keys exist with defaults
                default_intent = {
                    "wants_classification": False,
                    "wants_prescription": False,
                    "wants_vendors": False,
                    "wants_full_workflow": False,
                    "is_general_question": False,
                    "general_answer": ""
                }
                default_intent.update(intent)
                intent = default_intent
                
                # Apply dependency rules (ensure logical consistency)
                # Only apply tool dependency rules if it's not a general question
                if not intent.get("is_general_question", False):
                    if intent.get("wants_prescription") or intent.get("wants_vendors") or intent.get("wants_full_workflow"):
                        intent["wants_classification"] = True
                    
                    if intent.get("wants_vendors") or intent.get("wants_full_workflow"):
                        intent["wants_prescription"] = True
                        intent["wants_classification"] = True
                    
                    if intent.get("wants_full_workflow"):
                        intent["wants_vendors"] = True
                        intent["wants_prescription"] = True
                        intent["wants_classification"] = True
                
                return intent
                
            else:
                logger.warning("🚨 Could not find valid JSON in LLM response, using fallback analysis")
                
        except json.JSONDecodeError as e:
            logger.warning(f"🚨 Failed to parse JSON from LLM response: {e}, using fallback analysis")
            
        return None
    
    async def _fallback_intent_analysis(self, user_message: str) -> Dict[str, Any]:
        """
        Fallback intent analysis using simple keyword matching.
        Used when LLM-based analysis fails.
        """
        user_message_lower = user_message.lower()
        
        intent = {
            "wants_classification": False,
            "wants_prescription": False,
            "wants_vendors": False,
            "wants_full_workflow": False,
            "is_general_question": False,
            "general_answer": ""
        }
        
        # Classification keywords
        classification_keywords = ["analyze", "detect", "identify", "classify", "disease", "what", "wrong", "issue", "problem"]
        if any(word in user_message_lower for word in classification_keywords):
            intent["wants_classification"] = True
        
        # Prescription keywords
        prescription_keywords = ["treatment", "cure", "fix", "help", "recommend", "prescription", "medicine", "spray"]
        if any(word in user_message_lower for word in prescription_keywords):
            intent["wants_prescription"] = True
            intent["wants_classification"] = True  # Need classification first
        
        # Vendor keywords
        vendor_keywords = ["buy", "purchase", "order", "vendor", "shop", "price", "cost"]
        if any(word in user_message_lower for word in vendor_keywords):
            intent["wants_vendors"] = True
            intent["wants_prescription"] = True  # Need prescription first
            intent["wants_classification"] = True  # Need classification first
        
        # Full workflow keywords
        full_keywords = ["complete", "full", "everything", "all", "comprehensive"]
        if any(word in user_message_lower for word in full_keywords):
            intent["wants_full_workflow"] = True
            intent["wants_vendors"] = True
            intent["wants_prescription"] = True
            intent["wants_classification"] = True
        
        # Check for general questions (fallback has limited capability)
        general_keywords = ["how", "when", "why", "what", "where", "best time", "tips", "advice", "weather", "climate"]
        farming_keywords = ["plant", "grow", "crop", "farm", "soil", "water", "fertilizer", "seed"]
        
        # If it contains general question words + farming context but no specific tool requests
        if (any(word in user_message_lower for word in general_keywords) and 
            any(word in user_message_lower for word in farming_keywords) and 
            not any([intent["wants_classification"], intent["wants_prescription"], intent["wants_vendors"]])):
            
            intent["is_general_question"] = True
            intent["general_answer"] = "I understand you have a general farming question. For the best answer, please try again when the LLM system is available, or feel free to ask about specific plant diseases or issues that I can help diagnose and treat."
        
        logger.info(f"📝 Fallback intent analysis: {intent}")
        return intent
    
    def _is_continuing_conversation(self, state: WorkflowState) -> bool:
        """
        Detect if this is a continuing conversation (loaded from session) rather than a new one
        
        Args:
            state: Current workflow state
            
        Returns:
            True if this is a continuing conversation, False if it's a new conversation
        """
        # Check for indicators that this is a loaded session with previous conversation history
        has_previous_results = bool(
            state.get("classification_results") or 
            state.get("prescription_data") or
            state.get("vendor_options") or
            state.get("disease_name")
        )
        
        # Check if there are previous messages (more than just the current user message)
        messages = state.get("messages", [])
        has_conversation_history = len(messages) > 1
        
        # Check if current node indicates this came from a previous workflow state
        current_node = state.get("current_node", "initial")
        was_in_middle_of_workflow = current_node != "initial"
        
        is_continuing = has_previous_results or has_conversation_history or was_in_middle_of_workflow
        
        if is_continuing:
            logger.info(f"🔍 Continuing conversation detected:")
            logger.info(f"   - Has previous results: {has_previous_results}")
            logger.info(f"   - Has conversation history: {has_conversation_history} ({len(messages)} messages)")
            logger.info(f"   - Was in middle of workflow: {was_in_middle_of_workflow} (node: {current_node})")
        
        return is_continuing
