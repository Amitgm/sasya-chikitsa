"""
Core Planning Agent - Orchestrates the entire plant disease diagnosis workflow.

This is the main controller that coordinates between different components
and manages the dynamic flow based on user interactions and system state.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass

from ..session.session_manager import SessionManager
from ..flow.workflow_controller import WorkflowController
from ..components.intent_capture import IntentCaptureComponent
from ..components.llm_clarification import LLMClarificationComponent
from ..components.classification import ClassificationComponent
from ..components.prescription import PrescriptionComponent
from ..components.constraint_gathering import ConstraintGatheringComponent
from ..components.vendor_recommendation import VendorRecommendationComponent
from ..components.iterative_followup import IterativeFollowUpComponent

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Enum for tracking current workflow state"""
    INITIAL = "initial"
    INTENT_CAPTURE = "intent_capture"
    CLARIFICATION = "clarification"
    CLASSIFICATION = "classification"
    PRESCRIPTION = "prescription"
    CONSTRAINT_GATHERING = "constraint_gathering"
    VENDOR_RECOMMENDATION = "vendor_recommendation"
    FOLLOW_UP = "follow_up"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class PlanningResult:
    """Result from planning agent execution"""
    success: bool
    current_state: WorkflowState
    response: str
    next_actions: List[str]
    requires_user_input: bool
    session_data: Dict[str, Any]
    error_message: Optional[str] = None

class PlanningAgent:
    """
    Main Planning Agent that orchestrates the entire plant disease diagnosis workflow.
    
    This agent manages the dynamic flow through 8 core components:
    1. Leaf Upload & Intent Capture
    2. LLM-Guided Clarification
    3. Classification Step
    4. Prescription via RAG
    5. Display & Constraint Gathering
    6. Vendor Recommendation Branch
    7. Iterative Follow-Up
    8. Session Logging and State Tracking
    """
    
    def __init__(self):
        # Core system components
        self.session_manager = SessionManager()
        self.workflow_controller = WorkflowController()
        
        # Component handlers - each handles one core component
        self.components = {
            WorkflowState.INTENT_CAPTURE: IntentCaptureComponent(),
            WorkflowState.CLARIFICATION: LLMClarificationComponent(),
            WorkflowState.CLASSIFICATION: ClassificationComponent(),
            WorkflowState.PRESCRIPTION: PrescriptionComponent(),
            WorkflowState.CONSTRAINT_GATHERING: ConstraintGatheringComponent(),
            WorkflowState.VENDOR_RECOMMENDATION: VendorRecommendationComponent(),
            WorkflowState.FOLLOW_UP: IterativeFollowUpComponent()
        }
        
        logger.info("🎯 PlanningAgent initialized with all components")
    
    def _state_equals(self, state1, state2) -> bool:
        """
        Compare two workflow states handling both enum and string types.
        
        Args:
            state1: First state (could be enum, string, or other)
            state2: Second state (could be enum, string, or other)
            
        Returns:
            True if states are equal
        """
        # Handle None cases
        if state1 is None or state2 is None:
            return state1 == state2
        
        # Get comparable values
        def get_state_value(state):
            if isinstance(state, WorkflowState):
                return state.value
            elif hasattr(state, 'value'):
                return state.value
            elif hasattr(state, 'name'):
                return state.name.lower()
            else:
                return str(state).lower()
        
        return get_state_value(state1) == get_state_value(state2)
    
    def _state_in_components(self, state) -> bool:
        """
        Check if a state exists in the components dictionary, handling type mismatches.
        
        Args:
            state: State to check (could be enum, string, or other)
            
        Returns:
            True if state has a corresponding component
        """
        # Direct check first
        if state in self.components:
            return True
        
        # Check by comparing with all component keys
        for component_state in self.components.keys():
            if self._state_equals(state, component_state):
                return True
        
        return False

    async def process_user_request(
        self, 
        session_id: str,
        user_input: str = "",
        image_data: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[callable] = None
    ) -> PlanningResult:
        """
        Main entry point for processing user requests.
        
        Args:
            session_id: Unique session identifier
            user_input: User's text input
            image_data: Base64 encoded image data if provided
            context: Additional context information
            
        Returns:
            PlanningResult with response and next actions
        """
        try:
            logger.info(f"🚀 Processing request for session {session_id}")
            logger.debug(f"   User input: '{user_input[:100]}...'")
            logger.debug(f"   Has image: {bool(image_data)}")
            
            # Get or create session state
            session_state = await self.session_manager.get_session_state(session_id)
            
            # Determine current workflow state
            current_state = self._determine_current_state(session_state, user_input, image_data)
            logger.info(f"   Current state: {current_state}")
            
            # Execute appropriate component based on current state
            result = await self._execute_current_component(
                session_id, current_state, user_input, image_data, context
            )
            
            # Update session state with results
            await self.session_manager.update_session_state(
                session_id, current_state, result.session_data
            )
            
            # Determine next state and actions
            next_state, next_actions = await self.workflow_controller.determine_next_steps(
                current_state, result, session_state
            )
            
            # Log session activity
            await self.session_manager.log_activity(
                session_id, current_state, user_input, result.response
            )
            
            # STREAMING CONTINUOUS WORKFLOW: Stream each component's response as it completes
            # This enables real-time streaming while executing multiple components automatically
            all_responses = []
            final_result = result
            final_state = current_state
            final_actions = next_actions
            execution_chain = [current_state]
            is_streaming = stream_callback is not None
            
            logger.debug(f"🌊 Workflow streaming mode: {'ENABLED' if is_streaming else 'DISABLED'}")
            
            # Stream the initial result if streaming callback is provided
            if is_streaming and result.response.strip():
                try:
                    await stream_callback(result.response)
                    logger.info(f"📡 Streamed {current_state} response: {len(result.response)} chars")
                except Exception as e:
                    logger.warning(f"⚠️  Stream callback failed: {e}")
            
            all_responses.append(result.response)
            
            # Continue executing workflow automatically while components don't require user input
            while (not final_result.requires_user_input and 
                   not self._state_equals(next_state, final_state) and 
                   self._state_in_components(next_state)):
                
                logger.info(f"🔄 Auto-continuing workflow: {final_state} → {next_state}")
                execution_chain.append(next_state)
                
                # Update session with current results
                await self.session_manager.update_session_state(
                    session_id, next_state, final_result.session_data
                )
                
                try:
                    # Execute the next component automatically
                    next_result = await self._execute_current_component(
                        session_id, next_state, user_input, image_data, context
                    )
                    
                    # ✨ STREAM THE RESULT IMMEDIATELY after component execution
                    if is_streaming and next_result.response.strip():
                        try:
                            # Add a separator for readability between workflow steps
                            separator = f"\n\n🔄 **{next_state.upper()} STEP COMPLETED**\n"
                            await stream_callback(separator)
                            await stream_callback(next_result.response)
                            logger.info(f"📡 Streamed {next_state} response: {len(next_result.response)} chars")
                        except Exception as e:
                            logger.warning(f"⚠️  Stream callback failed for {next_state}: {e}")
                    else:
                        logger.debug(f"📝 Collected {next_state} response (no streaming): {len(next_result.response)} chars")
                    
                    all_responses.append(next_result.response)
                    
                    # Log the continued activity
                    await self.session_manager.log_activity(
                        session_id, next_state, user_input, next_result.response
                    )
                    
                    # Update session with the new result
                    await self.session_manager.update_session_state(
                        session_id, next_state, next_result.session_data
                    )
                    
                    # Determine next steps for the newly executed component
                    updated_session_state = await self.session_manager.get_session_data(session_id)
                    next_next_state, next_next_actions = await self.workflow_controller.determine_next_steps(
                        next_state, next_result, updated_session_state
                    )
                    
                    # Update tracking variables for next iteration
                    final_result = next_result
                    final_state = next_state
                    final_actions = next_next_actions
                    next_state = next_next_state
                    
                    # Safety check: prevent infinite loops
                    if len(execution_chain) > 8:  # Max 8 components in our workflow
                        logger.warning(f"⚠️  Workflow execution chain too long, stopping: {execution_chain}")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error during workflow continuation at {next_state}: {e}")
                    break
            
            # Log workflow completion
            if len(execution_chain) > 1:
                workflow_mode = "Streaming" if is_streaming else "Non-streaming"
                logger.info(f"✅ {workflow_mode} continuous workflow completed: {' → '.join(map(str, execution_chain))}")
                logger.info(f"   Final state: {final_state} (requires_user_input: {final_result.requires_user_input})")
                logger.info(f"   Total responses {'streamed' if is_streaming else 'collected'}: {len(all_responses)}")
            
            # Return the final result (response can be combined or just indicate completion)
            combined_response = final_result.response if len(all_responses) == 1 else "\n".join([r for r in all_responses if r.strip()])
            
            return PlanningResult(
                success=True,
                current_state=final_state,
                response=combined_response,
                next_actions=final_actions,
                requires_user_input=final_result.requires_user_input,
                session_data=final_result.session_data
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing request for session {session_id}: {e}")
            return PlanningResult(
                success=False,
                current_state=WorkflowState.ERROR,
                response=f"I encountered an error while processing your request. Please try again.",
                next_actions=["retry", "start_over"],
                requires_user_input=True,
                session_data={},
                error_message=str(e)
            )

    def _determine_current_state(
        self, 
        session_state: Dict[str, Any], 
        user_input: str, 
        image_data: Optional[str]
    ) -> WorkflowState:
        """
        Determine the current workflow state based on session data and user input.
        
        Args:
            session_state: Current session state data
            user_input: User's input text
            image_data: Image data if provided
            
        Returns:
            Current WorkflowState
        """
        # Check if this is a new session or continuation
        if not session_state.get('workflow_state'):
            if image_data:
                return WorkflowState.INTENT_CAPTURE
            else:
                return WorkflowState.CLARIFICATION
        
        # Handle workflow state conversion from session data
        stored_state = session_state.get('workflow_state')
        if isinstance(stored_state, WorkflowState):
            current_state = stored_state
        elif isinstance(stored_state, str):
            try:
                current_state = WorkflowState(stored_state)
            except ValueError:
                # If string doesn't match enum values, try by name
                current_state = getattr(WorkflowState, stored_state.upper(), WorkflowState.INITIAL)
        else:
            current_state = WorkflowState.INITIAL
        
        # Check if user wants to restart or change direction
        restart_keywords = ['start over', 'restart', 'new problem', 'different plant']
        if any(keyword in user_input.lower() for keyword in restart_keywords):
            return WorkflowState.INTENT_CAPTURE
        
        # Check if user uploaded new image during conversation
        if image_data and current_state != WorkflowState.INTENT_CAPTURE:
            return WorkflowState.INTENT_CAPTURE
        
        # Continue with current state or determine next logical state
        return current_state

    async def _execute_current_component(
        self,
        session_id: str,
        current_state: WorkflowState,
        user_input: str,
        image_data: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """
        Execute the component handler for the current workflow state.
        
        Args:
            session_id: Session identifier
            current_state: Current workflow state
            user_input: User input
            image_data: Image data if available
            context: Additional context
            
        Returns:
            Result from component execution
        """
        # Handle INITIAL state by transitioning to appropriate first state
        if self._state_equals(current_state, WorkflowState.INITIAL):
            logger.info("🔄 INITIAL state detected - transitioning to INTENT_CAPTURE")
            current_state = WorkflowState.INTENT_CAPTURE
        
        if not self._state_in_components(current_state):
            raise ValueError(f"No component handler for state: {current_state}")
        
        # Find the correct component using enum-safe lookup
        component = None
        for state_key, comp in self.components.items():
            if self._state_equals(current_state, state_key):
                component = comp
                break
        
        if component is None:
            raise ValueError(f"Component lookup failed for state: {current_state}")
        session_data = await self.session_manager.get_session_data(session_id)
        
        logger.debug(f"🔧 Executing component for state: {current_state} (component: {component.__class__.__name__})")
        
        result = await component.execute(
            session_id=session_id,
            user_input=user_input,
            image_data=image_data,
            session_data=session_data,
            context=context or {}
        )
        
        logger.debug(f"✅ Component execution completed for: {current_state}")
        return result

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the session state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary dictionary
        """
        return await self.session_manager.get_session_summary(session_id)

    async def restart_session(self, session_id: str) -> PlanningResult:
        """
        Restart a session from the beginning.
        
        Args:
            session_id: Session identifier
            
        Returns:
            PlanningResult for fresh session start
        """
        await self.session_manager.clear_session(session_id)
        logger.info(f"🔄 Session {session_id} restarted")
        
        return PlanningResult(
            success=True,
            current_state=WorkflowState.INITIAL,
            response="I've cleared our conversation history. Please upload a leaf image or tell me about your plant problem to get started!",
            next_actions=["upload_image", "describe_problem"],
            requires_user_input=True,
            session_data={}
        )

    async def get_available_actions(self, session_id: str) -> List[str]:
        """
        Get available actions for the current session state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of available actions
        """
        session_state = await self.session_manager.get_session_state(session_id)
        current_state = WorkflowState(session_state.get('workflow_state', 'initial'))
        
        return await self.workflow_controller.get_available_actions(current_state, session_state)
