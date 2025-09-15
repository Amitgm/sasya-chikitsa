"""
Prescribing Node for FSM Agent workflow
Generates treatment recommendations
"""

import logging
from typing import Dict, Any

from .base_node import BaseNode

try:
    from ..workflow_state import WorkflowState, add_message_to_state, set_error, can_retry
    from ...tools.prescription_tool import PrescriptionTool
except ImportError:
    from engine.fsm_agent.core.workflow_state import WorkflowState, add_message_to_state, set_error, can_retry
    from engine.fsm_agent.tools.prescription_tool import PrescriptionTool

logger = logging.getLogger(__name__)


class PrescribingNode(BaseNode):
    """Prescription node - generates treatment recommendations"""
    
    @property
    def node_name(self) -> str:
        return "prescribing"
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute prescription node logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.update_node_state(state)
        
        try:
            if not state.get("classification_results"):
                set_error(state, "No classification results available for prescription")
                state["next_action"] = "error"
                return state
            
            add_message_to_state(
                state,
                "assistant",
                "💊 Generating personalized treatment recommendations based on the diagnosis..."
            )
            
            # Run prescription tool
            prescription_tool = self.tools["prescription"]
            
            # Debug logging to verify context flow
            logger.info(f"Prescription context - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
            logger.info(f"Full user_context for prescription: {state.get('user_context', {})}")
            
            prescription_input = {
                "disease_name": state.get("disease_name"),
                "plant_type": state.get("plant_type"),
                "location": state.get("location"),
                "season": state.get("season"),
                "severity": state.get("classification_results", {}).get("severity"),
                "user_context": state.get("user_context", {})
            }
            
            result = await prescription_tool.arun(prescription_input)
            
            if result and not result.get("error"):
                self._process_successful_prescription(state, result)
            else:
                self._process_failed_prescription(state, result)
        
        except Exception as e:
            logger.error(f"Error in prescribing node: {str(e)}", exc_info=True)
            self._handle_prescription_exception(state, e)
        
        return state
    
    def _process_successful_prescription(self, state: WorkflowState, result: Dict[str, Any]) -> None:
        """Process successful prescription generation"""
        state["prescription_data"] = result
        state["treatment_recommendations"] = result.get("treatments", [])
        state["preventive_measures"] = result.get("preventive_measures", [])
        
        # Format prescription response
        response = self._format_prescription_response(result)
        
        # Store response for streaming and add to messages
        state["assistant_response"] = response
        add_message_to_state(state, "assistant", response)
        
        # Determine next action based on user intent
        user_intent = state.get("user_intent", {})
        if user_intent.get("wants_vendors", False):
            state["next_action"] = "vendor_query"
        else:
            # User only wanted classification and prescription
            state["next_action"] = "complete"
            state["is_complete"] = True
            
            completion_msg = "✅ **Treatment Plan Complete!** If you'd like to find vendors to purchase these treatments, just let me know!"
            
            # Add general answer if this was a hybrid request
            if state.get("general_answer"):
                completion_msg += f"\n\n🌾 **General Agricultural Advice:** {state['general_answer']}"
            
            add_message_to_state(state, "assistant", completion_msg)
    
    def _process_failed_prescription(self, state: WorkflowState, result: Dict[str, Any]) -> None:
        """Process failed prescription generation"""
        error_msg = result.get("error", "Prescription generation failed") if result else "Prescription tool returned no result"
        if can_retry(state):
            state["next_action"] = "retry"
            add_message_to_state(
                state,
                "assistant",
                f"⚠️ Prescription generation failed: {error_msg}. Retrying..."
            )
        else:
            set_error(state, error_msg)
            state["next_action"] = "error"
    
    def _handle_prescription_exception(self, state: WorkflowState, exception: Exception) -> None:
        """Handle exceptions during prescription generation"""
        if can_retry(state):
            state["next_action"] = "retry"
            add_message_to_state(
                state,
                "assistant",
                f"⚠️ Error during prescription generation: {str(exception)}. Retrying..."
            )
        else:
            set_error(state, f"Prescription error: {str(exception)}")
            state["next_action"] = "error"
    
    def _format_prescription_response(self, prescription_data: Dict[str, Any]) -> str:
        """Format prescription data into a professional treatment plan"""
        
        treatments = prescription_data.get("treatments", [])
        preventive_measures = prescription_data.get("preventive_measures", [])
        additional_notes = prescription_data.get("notes")
        
        response = f"""💊 **TREATMENT PLAN FOR YOUR PLANT**

🌿 **MEDICINES TO USE**"""
        
        for i, treatment in enumerate(treatments, 1):
            treatment_name = treatment.get('name', 'Unknown Treatment')
            treatment_type = treatment.get('type', 'N/A')
            
            response += f"""

🔹 **MEDICINE #{i}: {treatment_name}**
• **What it is:** {treatment_type}
• **How to apply:** {treatment.get('application', 'Follow bottle instructions')}
• **How much:** {treatment.get('dosage', 'As directed on package')}
• **How often:** {treatment.get('frequency', 'Check instructions')}
• **For how long:** {treatment.get('duration', 'Until plant looks better')}"""
        
        if preventive_measures:
            response += f"""

🛡️ **HOW TO PREVENT THIS DISEASE**"""
            for i, measure in enumerate(preventive_measures, 1):
                response += f"""
{i}. {measure}"""
        
        if additional_notes:
            response += f"""

⚠️ **IMPORTANT TIPS**
{additional_notes}"""
        
        response += f"""

✅ **REMEMBER**
• Always read the medicine bottle instructions
• Check your plant daily for improvement  
• Ask local experts if you need help
• Keep notes about what works

💚 **Your plant will get better with proper care!**"""
        
        return response
