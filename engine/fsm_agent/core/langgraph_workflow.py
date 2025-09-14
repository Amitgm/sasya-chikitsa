"""
LangGraph Workflow for Dynamic Planning Agent

This module implements the main LangGraph workflow for plant disease 
diagnosis and prescription using StateGraph.
"""

import json
import asyncio
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama

# Add the parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from .workflow_state import (
        WorkflowState, 
        add_message_to_state, 
        update_state_node, 
        set_error, 
        can_retry, 
        mark_complete
    )
    from ..tools.classification_tool import ClassificationTool
    from ..tools.prescription_tool import PrescriptionTool
    from ..tools.vendor_tool import VendorTool
    from ..tools.context_extractor import ContextExtractorTool
    from ..tools.attention_overlay_tool import AttentionOverlayTool
except ImportError:
    # Fallback to absolute imports if relative imports fail
    from engine.fsm_agent.core.workflow_state import (
        WorkflowState, 
        add_message_to_state, 
        update_state_node, 
        set_error, 
        can_retry, 
        mark_complete
    )
    from engine.fsm_agent.tools.classification_tool import ClassificationTool
    from engine.fsm_agent.tools.prescription_tool import PrescriptionTool
    from engine.fsm_agent.tools.vendor_tool import VendorTool
    from engine.fsm_agent.tools.context_extractor import ContextExtractorTool
    from engine.fsm_agent.tools.attention_overlay_tool import AttentionOverlayTool

logger = logging.getLogger(__name__)


class DynamicPlanningWorkflow:
    """
    Main LangGraph workflow for dynamic plant disease diagnosis and prescription
    """
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Initialize the workflow
        
        Args:
            llm_config: Configuration for the LLM (model, base_url, etc.)
        """
        # Initialize LLM
        self.llm = ChatOllama(**llm_config)
        
        # Initialize tools
        self.tools = {
            "classification": ClassificationTool(),
            "prescription": PrescriptionTool(),
            "vendor": VendorTool(),
            "context_extractor": ContextExtractorTool(),
            "attention_overlay": AttentionOverlayTool(),
        }
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
        logger.info("Dynamic Planning Workflow initialized")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph StateGraph workflow
        
        Returns:
            Configured StateGraph
        """
        # Create workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("initial", self._initial_node)
        workflow.add_node("classifying", self._classifying_node)
        workflow.add_node("prescribing", self._prescribing_node)
        workflow.add_node("vendor_query", self._vendor_query_node)
        workflow.add_node("show_vendors", self._show_vendors_node)
        workflow.add_node("order_booking", self._order_booking_node)
        workflow.add_node("followup", self._followup_node)
        workflow.add_node("completed", self._completed_node)
        workflow.add_node("error", self._error_node)
        
        # Set entry point
        workflow.set_entry_point("initial")
        
        # Add conditional edges (dynamic routing based on LLM decisions)
        workflow.add_conditional_edges(
            "initial",
            self._route_from_initial,
            {
                "classifying": "classifying",
                "followup": "followup",
                "error": "error",
                "completed": "completed"
            }
        )
        
        workflow.add_conditional_edges(
            "classifying",
            self._route_from_classifying,
            {
                "prescribing": "prescribing",
                "completed": "completed",
                "followup": "followup",
                "error": "error",
                "retry": "classifying"
            }
        )
        
        workflow.add_conditional_edges(
            "prescribing",
            self._route_from_prescribing,
            {
                "vendor_query": "vendor_query",
                "followup": "followup",
                "completed": "completed",
                "error": "error",
                "retry": "prescribing"
            }
        )
        
        workflow.add_conditional_edges(
            "vendor_query",
            self._route_from_vendor_query,
            {
                "show_vendors": "show_vendors",
                "completed": "completed",
                "followup": "followup",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "show_vendors",
            self._route_from_show_vendors,
            {
                "order_booking": "order_booking",
                "followup": "followup",
                "completed": "completed",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "order_booking",
            self._route_from_order_booking,
            {
                "completed": "completed",
                "followup": "followup",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "followup",
            self._route_from_followup,
            {
                "initial": "initial",
                "classifying": "classifying",
                "prescribing": "prescribing",
                "vendor_query": "vendor_query",
                "show_vendors": "show_vendors",
                "completed": "completed",
                "error": "error"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("completed", END)
        workflow.add_edge("error", END)
        
        return workflow
    
    # ==================== NODE IMPLEMENTATIONS ====================
    
    async def _analyze_user_intent(self, user_message: str) -> dict:
        """
        Analyze user intent using LLM to determine what they want from the agent.
        This provides much more robust intent recognition than keyword matching.
        Handles both specialized tool requests and general agricultural questions.
        """
        try:
            intent_prompt = f"""You are an expert at understanding user intent for a plant disease diagnosis and treatment system.

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

            # Get LLM response
            response = await self.llm.ainvoke(intent_prompt)
            response_text = response.content.strip()
            
            logger.debug(f"🧠 LLM intent analysis raw response: {response_text}")
            
            # Parse JSON response
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
                    
                    logger.info(f"🎯 LLM-driven user intent analysis: {intent}")
                    return intent
                    
                else:
                    logger.warning("🚨 Could not find valid JSON in LLM response, using fallback analysis")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"🚨 Failed to parse JSON from LLM response: {e}, using fallback analysis")
            
        except Exception as e:
            logger.error(f"❌ Error in LLM intent analysis: {e}, using fallback analysis")
        
        # Fallback to simple keyword-based analysis if LLM fails
        logger.info("🔄 Using fallback keyword-based intent analysis")
        return await self._fallback_intent_analysis(user_message)
    
    async def _fallback_intent_analysis(self, user_message: str) -> dict:
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

    async def _initial_node(self, state: WorkflowState) -> WorkflowState:
        """
        Initial node - handles user input and determines first action based on user intent
        """
        logger.info(f"Executing initial node for session {state['session_id']}")
        update_state_node(state, "initial")
        
        try:
            # Analyze user intent
            user_intent = await self._analyze_user_intent(state["user_message"])
            state["user_intent"] = user_intent
            
            # Extract context from user message if possible
            context_tool = self.tools["context_extractor"]
            # Ensure proper dictionary format for LangChain BaseTool
            context_input = {"user_message": state["user_message"]}
            context_result = await context_tool.arun(context_input)
            
            if context_result and not context_result.get("error"):
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
                if not state.get("location"):
                    logger.info(f"🔄 Updating location from extractor: {context_result.get('location')}")
                    state["location"] = context_result.get("location")
                else:
                    logger.info(f"✅ Keeping API location: {state.get('location')}")
                    
                if not state.get("season"):
                    logger.info(f"🔄 Updating season from extractor: {context_result.get('season')}")
                    state["season"] = context_result.get("season") 
                else:
                    logger.info(f"✅ Keeping API season: {state.get('season')}")
                    
                if not state.get("plant_type"):
                    logger.info(f"🔄 Updating plant_type from extractor: {context_result.get('plant_type')}")
                    state["plant_type"] = context_result.get("plant_type")
                else:
                    logger.info(f"✅ Keeping API plant_type: {state.get('plant_type')}")
                    
                if not state.get("growth_stage"):
                    state["growth_stage"] = context_result.get("growth_stage")
                
                # Debug: Log final state after context processing
                logger.info(f"✅ AFTER context processing - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
            
            # Store general answer for later use (for hybrid requests)
            general_answer = user_intent.get("general_answer", "")
            if general_answer:
                state["general_answer"] = general_answer
                logger.info(f"🌾 Stored general answer for hybrid request: {general_answer[:100]}...")
            
            # Determine next action based on user intent and input
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
            
        except Exception as e:
            logger.error(f"Error in initial node: {str(e)}", exc_info=True)
            set_error(state, f"Error processing initial request: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
    async def _classifying_node(self, state: WorkflowState) -> WorkflowState:
        """
        Classification node - runs disease classification on uploaded image
        """
        logger.info(f"Executing classifying node for session {state['session_id']}")
        logger.info(f"User intent in classifying node: {state.get('user_intent', 'NOT_FOUND')}")
        update_state_node(state, "classifying")
        
        try:
            if not state.get("user_image"):
                set_error(state, "No image provided for classification")
                state["next_action"] = "error"
                return state
            
            # Run classification tool
            classification_tool = self.tools["classification"]
            
            # Debug logging to verify context flow
            logger.info(f"Classification context - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
            logger.info(f"Full user_context: {state.get('user_context', {})}")
            
            classification_input = {
                "image_b64": state["user_image"],
                "plant_type": state.get("plant_type"),
                "location": state.get("location"),
                "season": state.get("season")
            }
            
            add_message_to_state(
                state,
                "assistant",
                "🔬 Analyzing the plant leaf image for disease detection..."
            )
            
            result = await classification_tool.arun(classification_input)
            
            # Determine next action based on user intent FIRST (regardless of classification result)
            user_intent = state.get("user_intent", {})
            logger.info(f"Classification attempted. User intent: {user_intent}")
            
            if result and not result.get("error"):
                # Classification successful
                state["classification_results"] = result
                state["disease_name"] = result.get("disease_name")
                state["confidence"] = result.get("confidence")
                state["attention_overlay"] = result.get("attention_overlay")
                
                # Format classification response
                confidence_pct = (result.get("confidence", 0) * 100)
                response = f"""🔬 **Disease Classification Complete**

**Diagnosis:** {result.get("disease_name", "Unknown")}
**Confidence:** {confidence_pct:.1f}%
**Severity:** {result.get("severity", "Unknown")}

{result.get("description", "")}"""
                
                # Store response for streaming and add to messages
                state["assistant_response"] = response
                add_message_to_state(state, "assistant", response)
                
                # Set next action based on user intent
                if user_intent.get("wants_prescription", False):
                    state["next_action"] = "prescribe"
                    logger.info("Setting next_action to 'prescribe' based on user intent")
                elif user_intent.get("wants_vendors", False):
                    state["next_action"] = "prescribe"  # Need prescription first
                    logger.info("Setting next_action to 'prescribe' (vendors requested, prescription needed first)")
                else:
                    # User only wanted classification
                    state["next_action"] = "completed"
                    state["is_complete"] = True
                    logger.info("Setting next_action to 'completed' (user only wanted classification)")
                    
                    completion_msg = "✅ **Analysis Complete!** If you need treatment recommendations or want to find vendors, just let me know!"
                    
                    # Add general answer if this was a hybrid request
                    if state.get("general_answer"):
                        completion_msg += f"\n\n🌾 **General Agricultural Advice:** {state['general_answer']}"
                    
                    add_message_to_state(state, "assistant", completion_msg)
                    
            else:
                # Classification failed
                error_msg = result.get("error", "Classification failed") if result else "Classification tool returned no result"
                logger.info(f"Classification failed: {error_msg}")
                
                if can_retry(state):
                    state["next_action"] = "retry"
                    add_message_to_state(
                        state,
                        "assistant", 
                        f"⚠️ Classification attempt failed: {error_msg}. Retrying..."
                    )
                else:
                    set_error(state, error_msg)
                    state["next_action"] = "error"
            
            logger.info(f"Final next_action set to: {state.get('next_action')}")
        
        except Exception as e:
            logger.error(f"Error in classifying node: {str(e)}", exc_info=True)
            if can_retry(state):
                state["next_action"] = "retry"
                add_message_to_state(
                    state,
                    "assistant",
                    f"⚠️ Error during classification: {str(e)}. Retrying..."
                )
            else:
                set_error(state, f"Classification error: {str(e)}")
                state["next_action"] = "error"
        
        return state
    
    async def _prescribing_node(self, state: WorkflowState) -> WorkflowState:
        """
        Prescription node - generates treatment recommendations
        """
        logger.info(f"Executing prescribing node for session {state['session_id']}")
        update_state_node(state, "prescribing")
        
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
                
            else:
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
        
        except Exception as e:
            logger.error(f"Error in prescribing node: {str(e)}", exc_info=True)
            if can_retry(state):
                state["next_action"] = "retry"
                add_message_to_state(
                    state,
                    "assistant",
                    f"⚠️ Error during prescription generation: {str(e)}. Retrying..."
                )
            else:
                set_error(state, f"Prescription error: {str(e)}")
                state["next_action"] = "error"
        
        return state
    
    async def _vendor_query_node(self, state: WorkflowState) -> WorkflowState:
        """
        Vendor query node - asks user if they want vendor information
        """
        logger.info(f"Executing vendor query node for session {state['session_id']}")
        update_state_node(state, "vendor_query")
        
        try:
            vendor_query_msg = """🛒 **Would you like to see local vendor options?**

I can help you find:
• Local suppliers with current pricing
• Online vendors with delivery options
• Organic/chemical treatment alternatives

Would you like me to show you vendor options for the recommended treatments? (Yes/No)"""
            
            add_message_to_state(state, "assistant", vendor_query_msg)
            state["requires_user_input"] = True
            state["next_action"] = "await_vendor_response"
            
        except Exception as e:
            logger.error(f"Error in vendor query node: {str(e)}", exc_info=True)
            set_error(state, f"Vendor query error: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
    async def _show_vendors_node(self, state: WorkflowState) -> WorkflowState:
        """
        Show vendors node - displays vendor options and pricing
        """
        logger.info(f"Executing show vendors node for session {state['session_id']}")
        update_state_node(state, "show_vendors")
        
        try:
            if not state.get("treatment_recommendations"):
                set_error(state, "No treatment recommendations available for vendor search")
                state["next_action"] = "error"
                return state
            
            add_message_to_state(
                state,
                "assistant",
                "🔍 Searching for local vendors and current pricing..."
            )
            
            # Run vendor tool
            vendor_tool = self.tools["vendor"]
            
            # Debug logging to verify context flow
            logger.info(f"Vendor context - location: {state.get('location', '')}")
            logger.info(f"User preferences for vendor: {state.get('user_context', {})}")
            
            vendor_input = {
                "treatments": state["treatment_recommendations"],
                "location": state.get("location", ""),
                "user_preferences": state.get("user_context", {})
            }
            
            result = await vendor_tool.arun(vendor_input)
            
            if result and not result.get("error"):
                state["vendor_options"] = result.get("vendors", [])
                
                # Format vendor response
                response = self._format_vendor_response(result.get("vendors", []))
                
                if state["vendor_options"]:
                    response += "\n\n💡 Would you like to proceed with ordering from any of these vendors? Please let me know which option interests you, or say 'no' if you'd prefer not to order right now."
                
                # Store response for streaming and add to messages
                state["assistant_response"] = response
                add_message_to_state(state, "assistant", response)
                
                if state["vendor_options"]:
                    state["requires_user_input"] = True
                    state["next_action"] = "await_vendor_selection"
                else:
                    state["next_action"] = "complete"
                
            else:
                error_msg = result.get("error", "Vendor search failed") if result else "Vendor tool returned no result"
                add_message_to_state(
                    state,
                    "assistant",
                    f"⚠️ Unable to fetch vendor information: {error_msg}. You can still proceed with the treatment recommendations using local suppliers."
                )
                state["next_action"] = "complete"
        
        except Exception as e:
            logger.error(f"Error in show vendors node: {str(e)}", exc_info=True)
            add_message_to_state(
                state,
                "assistant",
                f"⚠️ Error searching for vendors: {str(e)}. You can still proceed with the treatment recommendations using local suppliers."
            )
            state["next_action"] = "complete"
        
        return state
    
    async def _order_booking_node(self, state: WorkflowState) -> WorkflowState:
        """
        Order booking node - simulates order booking with selected vendor
        """
        logger.info(f"Executing order booking node for session {state['session_id']}")
        update_state_node(state, "order_booking")
        
        try:
            selected_vendor = state.get("selected_vendor")
            if not selected_vendor:
                set_error(state, "No vendor selected for order booking")
                state["next_action"] = "error"
                return state
            
            # Simulate order booking (this would integrate with actual vendor APIs)
            order_id = f"ORD-{state['session_id'][:8]}-{datetime.now().strftime('%Y%m%d%H%M')}"
            
            order_details = {
                "order_id": order_id,
                "vendor": selected_vendor,
                "items": state.get("treatment_recommendations", []),
                "total_amount": selected_vendor.get("total_price", 0),
                "status": "confirmed",
                "estimated_delivery": "3-5 business days"
            }
            
            state["order_details"] = order_details
            state["order_status"] = "confirmed"
            
            order_confirmation = f"""✅ **Order Confirmed!**

**Order ID:** {order_id}
**Vendor:** {selected_vendor.get('name', 'N/A')}
**Total Amount:** ₹{selected_vendor.get('total_price', 0)}
**Estimated Delivery:** 3-5 business days

Your order has been successfully placed! You should receive a confirmation email shortly with tracking details.

Is there anything else I can help you with regarding your plant care?"""
            
            add_message_to_state(state, "assistant", order_confirmation)
            state["requires_user_input"] = True
            state["next_action"] = "await_final_input"
            
        except Exception as e:
            logger.error(f"Error in order booking node: {str(e)}", exc_info=True)
            set_error(state, f"Order booking error: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
    async def _followup_node(self, state: WorkflowState) -> WorkflowState:
        """
        Followup node - handles additional questions and navigation
        """
        logger.info(f"Executing followup node for session {state['session_id']}")
        update_state_node(state, "followup")
        
        try:
            # Analyze user message to determine what they want to do
            user_message = state["user_message"].lower()
            
            # Determine next action based on user input
            if any(word in user_message for word in ["new", "another", "different", "start over"]):
                state["next_action"] = "restart"
                add_message_to_state(
                    state,
                    "assistant",
                    "🔄 Starting a new diagnosis. Please share your plant image and any additional context."
                )
            elif any(word in user_message for word in ["classify", "diagnose", "analyze"]):
                if state.get("user_image"):
                    state["next_action"] = "classify"
                else:
                    state["next_action"] = "request_image"
                    add_message_to_state(
                        state,
                        "assistant",
                        "📸 Please upload an image of the plant leaf you'd like me to analyze."
                    )
            elif any(word in user_message for word in ["prescription", "treatment", "recommend"]):
                if state.get("classification_results"):
                    state["next_action"] = "prescribe"
                else:
                    state["next_action"] = "classify_first"
                    add_message_to_state(
                        state,
                        "assistant",
                        "🔬 I need to classify the disease first. Please upload an image of the affected leaf."
                    )
            elif any(word in user_message for word in ["vendor", "buy", "purchase", "order"]):
                if state.get("prescription_data"):
                    state["next_action"] = "show_vendors"
                else:
                    state["next_action"] = "prescribe_first"
                    add_message_to_state(
                        state,
                        "assistant",
                        "💊 I need to generate treatment recommendations first. Let me analyze your plant image."
                    )
            elif any(word in user_message for word in ["attention", "overlay", "heatmap", "focus", "looking", "important", "highlight"]):
                # Handle attention overlay requests
                attention_tool = self.tools["attention_overlay"]
                attention_tool.set_state(state)
                
                # Determine request type based on user message
                if any(word in user_message for word in ["info", "about", "what", "explain"]):
                    request_type = "overlay_info"
                else:
                    request_type = "show_overlay"
                
                # Get the attention overlay
                try:
                    overlay_response = await attention_tool.arun({
                        "request_type": request_type,
                        "format_preference": "base64"
                    })
                    add_message_to_state(state, "assistant", overlay_response)
                    state["next_action"] = "general_help"
                    state["requires_user_input"] = True
                except Exception as e:
                    logger.error(f"Error retrieving attention overlay: {str(e)}")
                    add_message_to_state(
                        state,
                        "assistant", 
                        "❌ Sorry, I encountered an error while trying to retrieve the attention overlay. Please try again or start a new classification."
                    )
                    state["next_action"] = "general_help"
            elif any(word in user_message for word in ["done", "finish", "complete", "bye", "thanks"]):
                state["next_action"] = "complete"
                mark_complete(state, "🌱 Thank you for using the plant disease diagnosis service! Take care of your plants!")
            else:
                # General followup response
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
            
        except Exception as e:
            logger.error(f"Error in followup node: {str(e)}", exc_info=True)
            set_error(state, f"Followup error: {str(e)}")
            state["next_action"] = "error"
        
        return state
    
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
        
        # Generate follow-ups based on previous state
        if previous_node == "classifying":
            if disease_name and disease_name.lower() != "healthy":
                # Diseased plant - suggest treatment options
                if not already_asked(["treatment", "medicine", "cure", "spray", "fungicide"]):
                    follow_ups.append("Would you like specific treatment recommendations or medicine suggestions for this disease?")
                
                if not already_asked(["prevent", "prevention", "avoid", "future"]):
                    follow_ups.append("Would you like to know how to prevent this disease in the future?")
            else:
                # Healthy plant - suggest general care
                if not already_asked(["care", "maintenance", "fertilizer", "nutrients"]):
                    follow_ups.append("Would you like tips on optimal care and nutrition for your healthy plants?")
                    
                if not already_asked(["monitor", "early detection", "signs", "symptoms"]):
                    follow_ups.append("Would you like to know early warning signs to watch for potential diseases?")
        
        elif previous_node == "prescribing":
            # After prescription - suggest vendor options
            if not already_asked(["vendor", "supplier", "buy", "purchase", "order"]):
                follow_ups.append("Would you like to know about vendors or suppliers who can provide these treatments?")
            
            if not already_asked(["dosage", "application", "how to apply", "instructions"]):
                follow_ups.append("Do you need detailed application instructions or dosage information?")
        
        elif previous_node == "vendor_query" or previous_node == "show_vendors":
            # After vendor info - suggest practical next steps
            if not already_asked(["application", "timing", "when to apply"]):
                follow_ups.append("Would you like guidance on the best timing and method for applying the treatments?")
                
            if not already_asked(["follow-up", "monitoring", "track progress"]):
                follow_ups.append("Would you like to know how to monitor treatment progress and follow-up care?")
        
        # Add context-aware general suggestions (if not already covered)
        general_suggestions = []
        
        if plant_type and not already_asked(["weather", "climate", "temperature"]):
            general_suggestions.append(f"Would you like current weather recommendations for your {plant_type} in {location or 'your area'}?")
        
        if season and not already_asked(["seasonal", "season", "timing"]):
            general_suggestions.append(f"Are you interested in seasonal care tips for {season}?")
        
        if not already_asked(["insurance", "crop insurance", "protection"]):
            general_suggestions.append("Would you like information about crop insurance options to protect your investment?")
        
        if user_intent.get("wants_technical_details") and not already_asked(["analysis", "leaf analysis", "detailed scan"]):
            general_suggestions.append("Would you like a detailed leaf analysis with technical insights?")
        
        if not already_asked(["soil", "soil health", "nutrients", "fertility"]):
            general_suggestions.append("Are you interested in soil health assessment or nutrient management tips?")
        
        if not already_asked(["market", "price", "selling", "harvest"]):
            general_suggestions.append("Would you like market insights or harvest timing recommendations?")
        
        # Combine specific and general suggestions, prioritizing specific ones
        all_suggestions = follow_ups + general_suggestions
        
        # Return max 3 follow-ups, prioritizing most relevant
        return all_suggestions[:3]
    
    async def _completed_node(self, state: WorkflowState) -> WorkflowState:
        """
        Completed node - final state with follow-up questions
        """
        logger.info(f"Executing completed node for session {state['session_id']}")
        update_state_node(state, "completed")
        
        # Generate follow-up questions based on previous state and context
        follow_ups = self._generate_follow_ups(state)
        
        # Add completion message with follow-ups
        completion_message = "🌱 Workflow completed successfully!"
        
        if follow_ups:
            completion_message += "\n\n📝 Here are some additional things that might interest you:"
            for i, follow_up in enumerate(follow_ups, 1):
                completion_message += f"\n{i}. {follow_up}"
        
        # IMPORTANT: Store completion response in a field that gets streamed
        # (messages get filtered out, but we need this to stream to users)
        state["assistant_response"] = completion_message
        
        # Also add to messages for conversation history
        add_message_to_state(state, "assistant", completion_message)
        
        # Mark as complete
        state["is_complete"] = True
        
        return state
    
    async def _error_node(self, state: WorkflowState) -> WorkflowState:
        """
        Error node - handles errors
        """
        logger.info(f"Executing error node for session {state['session_id']}")
        update_state_node(state, "error")
        
        error_msg = state.get("error_message", "An unknown error occurred")
        add_message_to_state(
            state,
            "assistant",
            f"❌ **Error:** {error_msg}\n\nPlease try again or contact support if the issue persists."
        )
        
        mark_complete(state)
        return state
    
    # ==================== ROUTING FUNCTIONS ====================
    
    async def _route_from_initial(self, state: WorkflowState) -> str:
        """Route from initial node"""
        next_action = state.get("next_action", "error")
        
        if next_action == "classify":
            return "classifying"
        elif next_action == "request_image":
            return "followup"  # Stay in followup to wait for image
        elif next_action == "error":
            return "error"
        else:
            return "completed"
    
    async def _route_from_classifying(self, state: WorkflowState) -> str:
        """Route from classifying node"""
        next_action = state.get("next_action", "error")
        logger.info(f"Routing from classifying node. next_action = '{next_action}'")
        
        if next_action == "prescribe":
            logger.info("Routing to prescribing node")
            return "prescribing"
        elif next_action == "completed":
            logger.info("Routing to completed node")
            return "completed"
        elif next_action == "retry":
            logger.info("Routing to retry (classifying again)")
            return "retry"
        elif next_action == "error":
            logger.info("Routing to error node")
            return "error"
        else:
            logger.info(f"Routing to followup node (unknown next_action: {next_action})")
            return "followup"
    
    async def _route_from_prescribing(self, state: WorkflowState) -> str:
        """Route from prescribing node"""
        next_action = state.get("next_action", "error")
        
        if next_action == "vendor_query":
            return "vendor_query"
        elif next_action == "complete":
            return "completed"
        elif next_action == "retry":
            return "retry"
        elif next_action == "error":
            return "error"
        else:
            return "followup"
    
    async def _route_from_vendor_query(self, state: WorkflowState) -> str:
        """Route from vendor query node"""
        # This will be determined by user response
        user_response = state.get("user_message", "").lower()
        
        if any(word in user_response for word in ["yes", "sure", "okay", "show", "vendors"]):
            return "show_vendors"
        elif any(word in user_response for word in ["no", "skip", "later", "not now"]):
            return "completed"
        elif state.get("next_action") == "error":
            return "error"
        else:
            return "followup"
    
    async def _route_from_show_vendors(self, state: WorkflowState) -> str:
        """Route from show vendors node"""
        next_action = state.get("next_action", "complete")
        
        if next_action == "await_vendor_selection":
            return "followup"  # Wait for user to select vendor
        elif next_action == "order" and state.get("selected_vendor"):
            return "order_booking"
        elif next_action == "error":
            return "error"
        else:
            return "completed"
    
    async def _route_from_order_booking(self, state: WorkflowState) -> str:
        """Route from order booking node"""
        next_action = state.get("next_action", "complete")
        
        if next_action == "await_final_input":
            return "followup"
        elif next_action == "error":
            return "error"
        else:
            return "completed"
    
    async def _route_from_followup(self, state: WorkflowState) -> str:
        """Route from followup node"""
        next_action = state.get("next_action", "complete")
        
        routing_map = {
            "restart": "initial",
            "classify": "classifying",
            "prescribe": "prescribing",
            "show_vendors": "show_vendors",
            "complete": "completed",
            "error": "error",
            "request_image": "followup",
            "classify_first": "followup",
            "prescribe_first": "followup",
            "general_help": "followup"
        }
        
        return routing_map.get(next_action, "completed")
    
    # ==================== HELPER METHODS ====================
    
    def _format_prescription_response(self, prescription_data: Dict[str, Any]) -> str:
        """Format prescription data into a readable response"""
        response = "💊 **Treatment Recommendations**\n\n"
        
        treatments = prescription_data.get("treatments", [])
        for i, treatment in enumerate(treatments, 1):
            response += f"**{i}. {treatment.get('name', 'Unknown Treatment')}**\n"
            response += f"   • Type: {treatment.get('type', 'N/A')}\n"
            response += f"   • Application: {treatment.get('application', 'N/A')}\n"
            response += f"   • Dosage: {treatment.get('dosage', 'N/A')}\n"
            response += f"   • Frequency: {treatment.get('frequency', 'N/A')}\n\n"
        
        preventive_measures = prescription_data.get("preventive_measures", [])
        if preventive_measures:
            response += "🛡️ **Preventive Measures**\n"
            for measure in preventive_measures:
                response += f"• {measure}\n"
            response += "\n"
        
        additional_notes = prescription_data.get("notes")
        if additional_notes:
            response += f"📝 **Additional Notes:** {additional_notes}\n\n"
        
        return response
    
    def _format_vendor_response(self, vendors: List[Dict[str, Any]]) -> str:
        """Format vendor data into a readable response"""
        if not vendors:
            return "🔍 **No vendors found** in your area for the recommended treatments. Please check with local agricultural suppliers."
        
        response = "🛒 **Vendor Options**\n\n"
        
        for i, vendor in enumerate(vendors, 1):
            response += f"**{i}. {vendor.get('name', 'Unknown Vendor')}**\n"
            response += f"   • Location: {vendor.get('location', 'N/A')}\n"
            response += f"   • Contact: {vendor.get('contact', 'N/A')}\n"
            response += f"   • Delivery: {vendor.get('delivery_options', 'N/A')}\n"
            response += f"   • Total Price: ₹{vendor.get('total_price', 'N/A')}\n"
            
            items = vendor.get('items', [])
            if items:
                response += "   • Available Items:\n"
                for item in items:
                    response += f"     - {item.get('name', 'N/A')}: ₹{item.get('price', 'N/A')}\n"
            
            response += "\n"
        
        return response
    
    # ==================== PUBLIC METHODS ====================
    
    async def process_message(self, session_id: str, user_message: str, user_image: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message through the workflow
        
        Args:
            session_id: Unique session identifier
            user_message: User's input message
            user_image: Optional base64 encoded image
        
        Returns:
            Dictionary containing response and state information
        """
        try:
            # Import state creation function
            from .workflow_state import create_initial_state
            
            # Create proper workflow state
            state = create_initial_state(session_id, user_message, user_image, context)
            
            # Run workflow
            result = await self.app.ainvoke(state)
            
            return {
                "success": True,
                "session_id": session_id,
                "messages": result.get("messages", []),
                "state": result.get("current_node"),
                "is_complete": result.get("is_complete", False),
                "requires_user_input": result.get("requires_user_input", False),
                "classification_results": result.get("classification_results"),
                "prescription_data": result.get("prescription_data"),
                "vendor_options": result.get("vendor_options"),
                "order_details": result.get("order_details")
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def stream_process_message(self, session_id: str, user_message: str, user_image: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """
        Stream process a user message through the workflow
        
        Args:
            session_id: Unique session identifier
            user_message: User's input message
            user_image: Optional base64 encoded image
            context: Optional context dict with plant_type, location, season, etc.
        
        Yields:
            Stream of INCREMENTAL state updates and responses (no duplication)
        """
        try:
            # Import state functions
            from .workflow_state import create_initial_state, update_state_node, add_message_to_state
            
            # Create initial state for LangGraph entry point
            # The initial node will set user_intent and other derived state
            state = create_initial_state(session_id, user_message, user_image, context)
            
            logger.info(f"Starting workflow stream for session {session_id} with message: {user_message[:50]}...")
            if user_image:
                logger.info(f"Session {session_id} includes image data: {len(user_image)} characters")
            if context:
                logger.info(f"Session {session_id} includes context: {context}")
            
            # Debug: Check initial state context
            logger.info(f"Initial state context - plant_type: {state.get('plant_type')}, location: {state.get('location')}, season: {state.get('season')}")
            
            # Track previous state to implement delta-based streaming
            previous_state = {}
            streamed_messages = set()
            last_node = None
            
            # Stream workflow execution - LangGraph will manage state flow between nodes
            async for chunk in self.app.astream(state, stream_mode='updates'):
                # Log the chunk for debugging (without sensitive data)
                # Extract current node from LangGraph updates format for logging
                current_node_for_log = "unknown"
                has_messages_for_log = False
                for node_name, state_data in chunk.items():
                    if isinstance(state_data, dict):
                        current_node_for_log = state_data.get("current_node", node_name)
                        has_messages_for_log = bool(state_data.get("messages"))
                        break
                logger.debug(f"Workflow chunk for {session_id}: current_node={current_node_for_log}, has_messages={has_messages_for_log}")
                
                # Calculate DELTA - only what's NEW/CHANGED from previous state
                delta_chunk = self._calculate_state_delta(chunk, previous_state)
                
                # Only stream if there are meaningful changes
                if delta_chunk:
                    # Remove problematic data from delta (images, attention_overlay)  
                    filtered_delta = self._filter_chunk_for_streaming(delta_chunk)
                    
                    if filtered_delta:  # Only stream non-empty deltas
                        yield {
                            "type": "state_update",
                            "session_id": session_id,
                            "data": filtered_delta
                        }
                
                # Extract actual state data from LangGraph updates format
                actual_state_data = {}
                for node_name, state_data in chunk.items():
                    if isinstance(state_data, dict):
                        actual_state_data.update(state_data)
                
                # DON'T stream separate message/classification/prescription events
                # All information is included in the state_update to prevent duplication
                
                # Only track state transitions for logging purposes
                current_node = actual_state_data.get("current_node")
                if current_node and current_node != last_node:
                    last_node = current_node
                    logger.info(f"State transition: {previous_state.get('current_node', 'None')} → {current_node}")
                
                # Update previous state for next iteration (CLEAN COPY - no images/overlays)
                previous_state = self._create_clean_state_copy_from_actual_data(actual_state_data)
            
            logger.info(f"Workflow stream completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "session_id": session_id,
                "error": str(e)
            }
    
    def _filter_chunk_for_streaming(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter chunk data to remove images, verbose data, but keep essential state results
        
        Args:
            chunk: Original state chunk
            
        Returns:
            Clean chunk suitable for streaming (essential results only)
        """
        if not isinstance(chunk, dict):
            return chunk
            
        # Create filtered copy - start with everything and remove problematic data
        filtered = chunk.copy()
        
        # 1. Remove large base64 image data
        for img_key in ["user_image", "image"]:
            if img_key in filtered:
                del filtered[img_key]
            
        # 2. Remove attention_overlay (auto-streaming issue)
        if "attention_overlay" in filtered:
            del filtered["attention_overlay"]
        
        # 3. Remove messages (handled separately to prevent duplication)    
        if "messages" in filtered:
            del filtered["messages"]
            
        # 4. Clean up verbose data in classification_results
        if "classification_results" in filtered and isinstance(filtered["classification_results"], dict):
            classification = filtered["classification_results"]
            
            # Remove verbose fields but keep essential results
            verbose_fields = ["raw_predictions", "plant_context", "attention_overlay"]
            for verbose_field in verbose_fields:
                if verbose_field in classification:
                    del classification[verbose_field]
            
            filtered["classification_results"] = classification
        
        # 5. Remove verbose timestamps that change constantly
        if "last_update_time" in filtered:
            del filtered["last_update_time"]
            
        # KEEP essential results:
        # - classification_results (cleaned)
        # - prescription_data  
        # - disease_name, confidence, severity
        # - current_node, next_action, is_complete
        # - plant_type, location, season
        # - error_message, requires_user_input
        # - assistant_response (completion messages with follow-ups)
        
        return filtered
    
    def _calculate_state_delta(self, current_state: Dict[str, Any], previous_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the delta (new/changed data) between current and previous state
        
        Args:
            current_state: Current state chunk from LangGraph (format: {node_name: {state_data}})
            previous_state: Previous state chunk (flattened state data)
            
        Returns:
            Dictionary containing only NEW/CHANGED data
        """
        if not isinstance(current_state, dict):
            return current_state
        
        # Extract actual state data from LangGraph updates format: {node_name: {state_data}}
        actual_state_data = {}
        for node_name, state_data in current_state.items():
            if isinstance(state_data, dict):
                actual_state_data.update(state_data)
            
        if not previous_state:
            # First state - everything is new, but exclude problematic data
            return {k: v for k, v in actual_state_data.items() 
                   if k not in ["user_image", "image", "attention_overlay", "messages", "last_update_time"]}
        
        delta = {}
        
        # Check each key for changes in the actual state data
        for key, value in actual_state_data.items():
            # Skip problematic data that we never want to stream
            if key in ["user_image", "image", "attention_overlay", "messages", "last_update_time"]:
                continue
                
            # Include if key is new or value has changed
            if key not in previous_state or previous_state[key] != value:
                delta[key] = value
        
        return delta
    
    def _extract_new_messages(self, current_messages: list, previous_messages: list) -> list:
        """
        Extract only NEW messages (delta-based message extraction)
        
        Args:
            current_messages: Current messages list
            previous_messages: Previous messages list
            
        Returns:
            List of new messages only
        """
        if not current_messages:
            return []
            
        if not previous_messages:
            return current_messages
        
        # If current has more messages than previous, return the new ones
        if len(current_messages) > len(previous_messages):
            return current_messages[len(previous_messages):]
        
        return []
    
    def _create_clean_state_copy(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a clean copy of state for tracking (no images/overlays)
        
        Args:
            chunk: State chunk to copy
            
        Returns:
            Clean copy without problematic data
        """
        if not isinstance(chunk, dict):
            return {}
            
        clean_copy = {}
        
        for key, value in chunk.items():
            # Exclude problematic data from state tracking
            if key in ["user_image", "image", "attention_overlay", "messages", "last_update_time"]:
                continue
            
            clean_copy[key] = value
                
        return clean_copy
    
    def _create_clean_state_copy_from_actual_data(self, actual_state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a clean copy of actual state data for tracking (no images/overlays)
        
        Args:
            actual_state_data: Already extracted/flattened state data
            
        Returns:
            Clean copy without problematic data
        """
        if not isinstance(actual_state_data, dict):
            return {}
            
        clean_copy = {}
        
        for key, value in actual_state_data.items():
            # Exclude problematic data from state tracking
            if key in ["user_image", "image", "attention_overlay", "messages", "last_update_time"]:
                continue
            
            clean_copy[key] = value
                
        return clean_copy
