"""
Followup Node for FSM Agent workflow
Handles additional questions and navigation using LLM-based intent analysis
"""

import logging
from typing import Dict, Any

from .base_node import BaseNode

try:
    from ..workflow_state import WorkflowState, add_message_to_state, set_error, mark_complete
    from ...tools.attention_overlay_tool import AttentionOverlayTool
except ImportError:
    from engine.fsm_agent.core.workflow_state import WorkflowState, add_message_to_state, set_error, mark_complete
    from engine.fsm_agent.tools.attention_overlay_tool import AttentionOverlayTool

logger = logging.getLogger(__name__)


class FollowupNode(BaseNode):
    """Followup node - handles additional questions and navigation using LLM-based intent analysis"""
    
    @property
    def node_name(self) -> str:
        return "followup"
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute followup node logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.update_node_state(state)
        
        try:
            # Use LLM to analyze user intent and determine action
            followup_intent = await self._analyze_followup_intent(state)
            
            # Route based on LLM-determined intent
            if followup_intent["action"] == "classify":
                self._handle_classify_action(state)
                    
            elif followup_intent["action"] == "prescribe":
                self._handle_prescribe_action(state)
                    
            elif followup_intent["action"] == "show_vendors":
                self._handle_show_vendors_action(state)
                    
            elif followup_intent["action"] == "attention_overlay":
                await self._handle_attention_overlay_action(state, followup_intent)
                    
            elif followup_intent["action"] == "restart":
                self._handle_restart_action(state)
                
            elif followup_intent["action"] == "complete":
                await self._handle_complete_action(state)
                
            elif followup_intent["action"] == "direct_response":
                self._handle_direct_response_action(state, followup_intent)
                
            else:
                self._handle_general_help_action(state)
            
        except Exception as e:
            logger.error(f"Error in followup node: {str(e)}", exc_info=True)
            set_error(state, f"Followup error: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
    def _handle_classify_action(self, state: WorkflowState) -> None:
        """Handle classification action"""
        if state.get("user_image"):
            state["next_action"] = "classify"
        else:
            state["next_action"] = "request_image"
            add_message_to_state(state, "assistant", "📸 Please upload an image of the plant leaf you'd like me to analyze.")
            state["requires_user_input"] = True
    
    def _handle_prescribe_action(self, state: WorkflowState) -> None:
        """Handle prescription action"""
        if state.get("classification_results"):
            state["next_action"] = "prescribe"
        else:
            state["next_action"] = "classify_first"
            add_message_to_state(state, "assistant", "🔬 I need to classify the disease first. Please upload an image of the affected leaf.")
            state["requires_user_input"] = True
    
    def _handle_show_vendors_action(self, state: WorkflowState) -> None:
        """Handle show vendors action"""
        if state.get("prescription_data"):
            state["next_action"] = "show_vendors"
        else:
            state["next_action"] = "prescribe_first"
            add_message_to_state(state, "assistant", "💊 I need to generate treatment recommendations first. Let me analyze your plant image.")
            state["requires_user_input"] = True
    
    async def _handle_attention_overlay_action(self, state: WorkflowState, followup_intent: Dict[str, Any]) -> None:
        """Handle attention overlay action"""
        attention_tool = self.tools["attention_overlay"]
        attention_tool.set_state(state)
        
        try:
            overlay_response = await attention_tool.arun({
                "request_type": followup_intent.get("overlay_type", "show_overlay"),
                "format_preference": "base64"
            })
            add_message_to_state(state, "assistant", overlay_response)
            state["next_action"] = "general_help"
            state["requires_user_input"] = True
        except Exception as e:
            logger.error(f"Error retrieving attention overlay: {str(e)}")
            add_message_to_state(state, "assistant", "❌ Sorry, I encountered an error while trying to retrieve the attention overlay. Please try again or start a new classification.")
            state["next_action"] = "general_help"
    
    def _handle_restart_action(self, state: WorkflowState) -> None:
        """Handle restart action"""
        state["next_action"] = "restart"
        add_message_to_state(state, "assistant", "🔄 Starting a new diagnosis. Please share your plant image and any additional context.")
        state["requires_user_input"] = True
    
    async def _handle_complete_action(self, state: WorkflowState) -> None:
        """Handle completion action"""
        # Check if user wants to actually end the session
        user_wants_to_end = await self._detect_goodbye_intent(state)
        if user_wants_to_end:
            state["next_action"] = "complete"
            mark_complete(state, "🌱 Thank you for using the plant disease diagnosis service! Take care of your plants!")
        else:
            # User reached completion but didn't say goodbye, show ongoing support
            self._show_ongoing_support(state)
    
    def _handle_direct_response_action(self, state: WorkflowState, followup_intent: Dict[str, Any]) -> None:
        """Handle direct response action"""
        # LLM can handle this directly - use the generated response
        llm_response = followup_intent.get("response", "I'm here to help! What would you like to know?")
        add_message_to_state(state, "assistant", llm_response)
        
        # Store the response for streaming (important for immediate streaming)
        state["assistant_response"] = llm_response
        
        # Don't set next_action to "complete" as it would overwrite our response
        # Instead, stay in followup to await further user input
        state["next_action"] = "await_user_input"
        state["requires_user_input"] = True
    
    def _handle_general_help_action(self, state: WorkflowState) -> None:
        """Handle general help action"""
        state["next_action"] = "general_help"
        help_message = """🤔 I can help you with:

• **New diagnosis** - Upload a new plant image
• **Review results** - Look at previous diagnosis or prescription
• **Show attention overlay** - See where the AI focused during diagnosis
• **Find vendors** - Get vendor options for treatments
• **Ask questions** - Any plant care related questions

What would you like to do next?"""
        
        add_message_to_state(state, "assistant", help_message)
        state["requires_user_input"] = True
    
    def _show_ongoing_support(self, state: WorkflowState) -> None:
        """Show ongoing support message"""
        state["next_action"] = "general_help"
        help_message = """🤔 I'm here to help with more questions! You can:

• **Upload new plant images** for diagnosis
• **Ask about treatment progress** and monitoring
• **Request vendor information** for treatments
• **Get seasonal care advice** and tips

What would you like to know more about?"""
        
        add_message_to_state(state, "assistant", help_message)
        state["requires_user_input"] = True
    
    async def _analyze_followup_intent(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Analyze user's followup message to determine intent and action using LLM
        """
        try:
            user_message = state["user_message"]
            
            # Build context about current workflow state
            context_info = []
            if state.get("classification_results"):
                disease_name = state.get("disease_name", "Unknown")
                context_info.append(f"- Already diagnosed disease: {disease_name}")
            
            if state.get("prescription_data"):
                context_info.append(f"- Already have treatment recommendations")
            
            if state.get("vendor_options"):
                context_info.append(f"- Already have vendor information")
                
            context_str = "\n".join(context_info) if context_info else "- No previous workflow steps completed"
            
            intent_prompt = self._build_followup_intent_prompt(user_message, context_str, state)
            
            # Get LLM response
            response = await self.llm.ainvoke(intent_prompt)
            response_text = response.content.strip()
            
            logger.debug(f"🧠 LLM followup intent analysis: {response_text}")
            
            # Parse JSON response  
            intent = self._parse_followup_intent_response(response_text, state)
            if intent:
                logger.info(f"🎯 LLM followup intent analysis: {intent}")
                return intent
                    
        except Exception as e:
            logger.error(f"❌ Error in LLM followup intent analysis: {e}")
        
        # Fallback to direct response
        return {
            "action": "direct_response",
            "response": "I'm here to help! What would you like to know about plant disease diagnosis or treatment?",
            "overlay_type": "",
            "confidence": 0.1
        }
    
    def _build_followup_intent_prompt(self, user_message: str, context_str: str, state: WorkflowState) -> str:
        """Build the followup intent analysis prompt"""
        return f"""You are analyzing a user's followup message in a plant disease diagnosis system.

Current workflow context:
{context_str}

User's message: "{user_message}"

Analyze the user's intent and respond with ONLY a JSON object containing:
- action: One of ["classify", "prescribe", "show_vendors", "attention_overlay", "restart", "complete", "direct_response"]
- response: (string) If action is "direct_response", provide a helpful answer to their question. Otherwise, leave empty.
- overlay_type: (string) If action is "attention_overlay", specify "show_overlay" or "overlay_info". Otherwise, leave empty.
- confidence: (number 0-1) How confident you are in this classification.

Action meanings:
- "classify": User wants disease diagnosis/classification
- "prescribe": User wants treatment recommendations, dosage info, application instructions  
- "show_vendors": User wants to find/buy products or vendors
- "attention_overlay": User wants to see diagnostic attention overlay/heatmap
- "restart": User wants to start over with new diagnosis
- "complete": User is done/saying goodbye
- "direct_response": Answer their question directly (for general agriculture questions, clarifications, etc.)

Guidelines:
1. If they ask about dosage, application, treatment instructions - use "prescribe" if no prescription exists, otherwise "direct_response" with detailed answer using available prescription data
2. If they ask general agriculture questions (soil, weather, growing tips) - use "direct_response"  
3. If they're asking for clarification about previous results - use "direct_response"
4. Be flexible with natural language - "yes give me dosage" means they want prescription/dosage info
5. Consider context - if they have prescription data and ask about dosage, provide direct_response with that info

Current prescription data available: {bool(state.get("prescription_data"))}

Response (JSON only):"""
    
    def _parse_followup_intent_response(self, response_text: str, state: WorkflowState) -> Dict[str, Any]:
        """Parse the followup intent response"""
        try:
            import json
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                intent = json.loads(json_str)
                
                # Ensure required keys exist
                default_intent = {
                    "action": "direct_response",
                    "response": "I'm here to help! What would you like to know?",
                    "overlay_type": "",
                    "confidence": 0.5
                }
                default_intent.update(intent)
                
                # Special handling for prescription-related requests when we have prescription data
                user_message = state["user_message"]
                if (intent.get("action") == "prescribe" and 
                    state.get("prescription_data") and 
                    any(word in user_message.lower() for word in ["dosage", "dose", "application", "instructions", "how much", "how to"])):
                    
                    # Generate direct response with prescription data
                    dosage_info = self._generate_prescription_dosage_info(state)
                    default_intent["action"] = "direct_response"
                    default_intent["response"] = dosage_info
                
                return default_intent
                        
        except json.JSONDecodeError as e:
            logger.warning(f"🚨 Failed to parse JSON from LLM followup response: {e}")
            
        return None
    
    def _generate_prescription_dosage_info(self, state: WorkflowState) -> str:
        """Generate dosage information from prescription data"""
        prescription_data = state.get("prescription_data", {})
        treatments = prescription_data.get("treatments", [])
        
        if treatments:
            dosage_info = f"""📋 **HOW TO USE YOUR MEDICINES**

💊 **STEP-BY-STEP INSTRUCTIONS**"""
            
            for i, treatment in enumerate(treatments, 1):
                treatment_name = treatment.get('name', 'Treatment')
                dosage_info += f"""

🔹 **MEDICINE #{i}: {treatment_name}**
• **How much to use:** {treatment.get('dosage', 'Follow bottle label')}
• **How to apply:** {treatment.get('application', 'Mix with water and spray')}
• **How often:** {treatment.get('frequency', 'Check medicine bottle')}
• **For how long:** {treatment.get('duration', 'Until plant gets better')}"""
            
            notes = prescription_data.get("notes")
            if notes:
                dosage_info += f"""

⚠️ **IMPORTANT SAFETY TIPS**
{notes}"""
            
            dosage_info += f"""

✅ **SAFETY FIRST**
• Always read the medicine bottle label
• Wear gloves when spraying
• Watch your plant daily for changes
• Ask local experts if you need help

💚 **Take care of yourself and your plants!**"""
            
            return dosage_info
        
        return "I don't have detailed dosage information available. Please refer to the medicine bottle labels or consult with local agricultural experts."
    
    async def _detect_goodbye_intent(self, state: WorkflowState) -> bool:
        """
        Detect if user wants to end the session using LLM analysis
        """
        try:
            user_message = state.get("user_message", "")
            if not user_message:
                return False
            
            goodbye_prompt = f"""Analyze this user message to determine if they want to END or CLOSE their consultation session.

User message: "{user_message}"

Look for goodbye indicators like:
- Thank you, thanks, thank u
- Bye, goodbye, see you, farewell
- That's all, that's it, I'm done
- End session, close, finish, complete
- No more questions, nothing else
- Perfect, great, awesome (when indicating satisfaction and closure)

Respond with ONLY "YES" if they want to end the session, or "NO" if they want to continue.

Response:"""

            # Get LLM response
            response = await self.llm.ainvoke(goodbye_prompt)
            response_text = response.content.strip().upper()
            
            logger.debug(f"🤖 Goodbye intent analysis: '{user_message}' -> {response_text}")
            
            # Simple check for YES/NO
            wants_to_end = "YES" in response_text and "NO" not in response_text
            
            logger.info(f"👋 User goodbye intent detected: {wants_to_end}")
            return wants_to_end
            
        except Exception as e:
            logger.error(f"❌ Error in goodbye intent detection: {e}")
            # Fallback to simple keyword detection
            user_message_lower = user_message.lower() if user_message else ""
            goodbye_keywords = ["thank you", "thanks", "bye", "goodbye", "that's all", "that's it", "done", "finish", "complete"]
            fallback_result = any(keyword in user_message_lower for keyword in goodbye_keywords)
            logger.info(f"👋 Fallback goodbye intent: {fallback_result}")
            return fallback_result
