"""
Completed Node for FSM Agent workflow
Final state with follow-up questions
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .base_node import BaseNode

try:
    from ..workflow_state import WorkflowState, add_message_to_state
except ImportError:
    from engine.fsm_agent.core.workflow_state import WorkflowState, add_message_to_state

logger = logging.getLogger(__name__)


class CompletedNode(BaseNode):
    """Completed node - final state with follow-up questions"""
    
    @property
    def node_name(self) -> str:
        return "completed"
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute completed node logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.update_node_state(state)
        
        # Check if user indicated they want to end the session
        user_wants_to_end = await self._detect_goodbye_intent(state)
        
        # Generate follow-up questions based on previous state and context
        follow_ups = self._generate_follow_ups(state)
        
        if user_wants_to_end:
            # User said goodbye - show full completion message
            completion_message = self._create_full_completion_message(follow_ups)
        else:
            # User didn't say goodbye - show ongoing support only
            completion_message = self._create_ongoing_support_message(follow_ups)
        
        # IMPORTANT: Store completion response in a field that gets streamed
        # (messages get filtered out, but we need this to stream to users)
        state["assistant_response"] = completion_message
        
        # Also add to messages for conversation history
        add_message_to_state(state, "assistant", completion_message)
        
        # Mark as complete only if user wants to end
        state["is_complete"] = user_wants_to_end
        
        return state
    
    def _create_full_completion_message(self, follow_ups: List[str]) -> str:
        """Create completion message for users saying goodbye"""
        completion_message = f"""✅ **YOUR PLANT CHECKUP IS DONE**

🌱 **WHAT WE DID**
We checked your plant and gave you treatment advice. Our smart system analyzed your plant photo and provided helpful recommendations.

🚀 **WHAT TO DO NEXT**"""
        
        if follow_ups:
            for i, follow_up in enumerate(follow_ups, 1):
                completion_message += f"""
{i}. {follow_up}"""
        else:
            completion_message += """
1. Check your plant daily to see if it's getting better
2. Keep following the care tips we gave you
3. Take new photos if you see more problems"""
        
        completion_message += f"""

💚 **WE'RE HERE TO HELP**
• Take new photos anytime if you see more problems
• Ask questions about how the treatment is working
• Find out where to buy medicines for your plants
• Get tips for different seasons and weather

⏰ **Checkup Completed**
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🌱 **Thank you for using Sasya Arogya! Keep your plants healthy!**"""
        
        return completion_message
    
    def _create_ongoing_support_message(self, follow_ups: List[str]) -> str:
        """Create completion message for ongoing support"""
        completion_message = f"""✅ **YOUR PLANT CHECKUP STATUS**

🌱 **WHAT WE DID**
We checked your plant and gave you treatment advice. Our smart system analyzed your plant photo and provided helpful recommendations.

🚀 **WHAT TO DO NEXT**"""
        
        if follow_ups:
            for i, follow_up in enumerate(follow_ups, 1):
                completion_message += f"""
{i}. {follow_up}"""
        else:
            completion_message += """
1. Check your plant daily to see if it's getting better
2. Keep following the care tips we gave you
3. Take new photos if you see more problems"""
        
        completion_message += f"""

💚 **WE'RE HERE TO HELP**
• Take new photos anytime if you see more problems
• Ask questions about how the treatment is working
• Find out where to buy medicines for your plants
• Get tips for different seasons and weather"""
        
        return completion_message
    
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
    
    def _generate_follow_ups(self, state: WorkflowState) -> List[str]:
        """
        Generate relevant follow-up questions based on previous state and user context
        
        Args:
            state: Current workflow state
            
        Returns:
            List of follow-up questions/suggestions (max 3)
        """
        follow_ups = []
        previous_node = state.get("previous_node", "")
        user_intent = state.get("user_intent", {})
        classification_results = state.get("classification_results", {})
        disease_name = state.get("disease_name", "")
        prescription_data = state.get("prescription_data", {})
        plant_type = state.get("plant_type", "")
        location = state.get("location", "")
        season = state.get("season", "")
        
        # Extract previous user messages to avoid duplicating questions
        messages = state.get("messages", [])
        user_messages = [msg.get("content", "").lower() for msg in messages if msg.get("role") == "user"]
        all_user_text = " ".join(user_messages)
        
        # Helper function to check if topic was already discussed
        def already_asked(keywords: List[str]) -> bool:
            return any(keyword.lower() in all_user_text for keyword in keywords)
        
        # Generate professional follow-ups based on previous state
        follow_ups.extend(self._generate_state_specific_followups(
            previous_node, disease_name, classification_results, prescription_data, already_asked))
        
        # Add context-aware professional suggestions (if not already covered)
        general_suggestions = self._generate_general_suggestions(
            plant_type, season, already_asked)
        
        # Combine specific and general suggestions, prioritizing specific ones
        all_suggestions = follow_ups + general_suggestions
        
        # Return max 3 follow-ups, prioritizing most relevant
        return all_suggestions[:3]
    
    def _generate_state_specific_followups(self, previous_node: str, disease_name: str, 
                                          classification_results: Dict[str, Any], 
                                          prescription_data: Dict[str, Any],
                                          already_asked) -> List[str]:
        """Generate followups specific to the previous workflow state"""
        follow_ups = []
        
        if previous_node == "classifying":
            if disease_name and disease_name.lower() != "healthy":
                # Diseased plant - suggest comprehensive treatment and management options
                confidence = classification_results.get("confidence", 0) * 100 if classification_results else 0
                severity = classification_results.get("severity", "Unknown")
                
                if not already_asked(["treatment", "medicine", "cure", "spray", "fungicide"]):
                    if severity.lower() in ["high", "severe"]:
                        follow_ups.append("🚨 **URGENT**: Request immediate therapeutic intervention plan for severe pathogen management")
                    else:
                        follow_ups.append("💊 **TREATMENT**: Get evidence-based therapeutic recommendations and application protocols")
                
                if not already_asked(["prevent", "prevention", "avoid", "future"]):
                    follow_ups.append("🛡️ **PREVENTION**: Develop integrated disease management strategy for long-term plant health")
                    
                if not already_asked(["vendor", "supplier", "buy", "purchase"]) and confidence >= 75:
                    follow_ups.append("🛒 **PROCUREMENT**: Connect with certified agricultural suppliers for recommended treatments")
            else:
                # Healthy plant - suggest proactive care and monitoring
                if not already_asked(["care", "maintenance", "fertilizer", "nutrients"]):
                    follow_ups.append("🌱 **OPTIMIZATION**: Enhance plant vigor with customized nutritional and care protocols")
                    
                if not already_asked(["monitor", "early detection", "signs", "symptoms"]):
                    follow_ups.append("🔍 **MONITORING**: Implement proactive surveillance system for early pathogen detection")
        
        elif previous_node == "prescribing":
            # After prescription - suggest comprehensive implementation support
            treatments = prescription_data.get("treatments", [])
            treatment_count = len(treatments)
            
            if not already_asked(["vendor", "supplier", "buy", "purchase", "order"]):
                follow_ups.append(f"🛒 **SUPPLY CHAIN**: Locate certified suppliers for {treatment_count} prescribed treatment{'s' if treatment_count != 1 else ''}")
            
            if not already_asked(["dosage", "application", "how to apply", "instructions"]):
                follow_ups.append("📋 **APPLICATION**: Get detailed administration protocols and safety guidelines")
                
            if not already_asked(["monitoring", "response", "effectiveness"]):
                follow_ups.append("📊 **MONITORING**: Establish treatment efficacy tracking and response assessment")
        
        elif previous_node in ["vendor_query", "show_vendors"]:
            # After vendor info - suggest comprehensive implementation strategy
            if not already_asked(["application", "timing", "when to apply"]):
                follow_ups.append("⏰ **TIMING**: Optimize treatment scheduling based on plant phenology and environmental conditions")
                
            if not already_asked(["follow-up", "monitoring", "track progress"]):
                follow_ups.append("📈 **TRACKING**: Develop systematic monitoring protocol for treatment response evaluation")
                
            if not already_asked(["resistance", "management", "rotation"]):
                follow_ups.append("🔄 **RESISTANCE MANAGEMENT**: Plan treatment rotation strategy to prevent pathogen resistance")
        
        return follow_ups
    
    def _generate_general_suggestions(self, plant_type: str, season: str, already_asked) -> List[str]:
        """Generate general agricultural suggestions"""
        general_suggestions = []
        
        if plant_type and not already_asked(["weather", "climate", "temperature"]):
            general_suggestions.append(f"🌤️ **ENVIRONMENTAL**: Get precision weather analytics and climate adaptation strategies for {plant_type} cultivation")
        
        if season and not already_asked(["seasonal", "season", "timing"]):
            general_suggestions.append(f"📅 **SEASONAL PLANNING**: Develop {season}-specific crop management and phenological optimization protocols")
        
        if not already_asked(["insurance", "crop insurance", "protection"]):
            general_suggestions.append("🛡️ **RISK MANAGEMENT**: Explore comprehensive crop insurance and agricultural risk mitigation solutions")
        
        if not already_asked(["soil", "soil health", "nutrients", "fertility"]):
            general_suggestions.append("🧪 **SOIL DIAGNOSTICS**: Conduct precision soil health assessment and nutrient optimization analysis")
        
        if not already_asked(["market", "price", "selling", "harvest"]):
            general_suggestions.append("📊 **MARKET INTELLIGENCE**: Access real-time commodity pricing and harvest timing optimization data")
        
        if not already_asked(["automation", "technology", "IoT", "sensors"]):
            general_suggestions.append("🤖 **PRECISION AGRICULTURE**: Implement IoT monitoring and automated crop management systems")
        
        return general_suggestions
