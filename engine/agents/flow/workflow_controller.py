"""
Workflow Controller - Dynamic Flow Management

Manages state transitions, branching logic, and determines next steps
based on current state, user preferences, and system capabilities.
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Enum for tracking workflow states"""
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

class WorkflowController:
    """
    Controls the dynamic flow through the diagnosis workflow.
    
    Responsibilities:
    - Determine next logical steps based on current state
    - Handle branching logic (e.g., vendor recommendations vs. completion)
    - Manage iterative flows and recursive branching
    - Provide available actions for each state
    """
    
    def __init__(self):
        # Define state transition rules
        self.state_transitions = self._initialize_state_transitions()
        self.available_actions_map = self._initialize_available_actions()
        
        logger.info("🔀 WorkflowController initialized")
    
    def _state_equals(self, current_state, target_state: WorkflowState) -> bool:
        """
        Compare workflow states handling both enum and string types.
        
        Args:
            current_state: Current state (could be enum, string, or other)
            target_state: Target WorkflowState enum to compare against
            
        Returns:
            True if states are equal
        """
        if isinstance(current_state, WorkflowState):
            return current_state == target_state
        elif isinstance(current_state, str):
            return current_state == target_state.value
        elif hasattr(current_state, 'value'):
            return current_state.value == target_state.value
        elif hasattr(current_state, 'name'):
            return current_state.name == target_state.name
        else:
            return str(current_state) == target_state.value

    async def determine_next_steps(
        self,
        current_state: WorkflowState,
        component_result: Any,
        session_data: Dict[str, Any]
    ) -> Tuple[WorkflowState, List[str]]:
        """
        Determine the next workflow state and available actions.
        
        Args:
            current_state: Current workflow state
            component_result: Result from current component execution
            session_data: Current session data
            
        Returns:
            Tuple of (next_state, available_actions)
        """
        logger.debug(f"🔀 Determining next steps from state: {current_state}")
        
        # Get result data from component
        result_data = getattr(component_result, 'session_data', {})
        requires_input = getattr(component_result, 'requires_user_input', False)
        
        # If component requires user input, stay in current state
        if requires_input:
            actions = await self.get_available_actions(current_state, session_data)
            return current_state, actions
        
        # Determine next state based on current state and results
        next_state = await self._get_next_state(current_state, result_data, session_data)
        next_actions = await self.get_available_actions(next_state, session_data)
        
        logger.info(f"🔀 Workflow transition: {current_state} → {next_state}")
        return next_state, next_actions

    async def _get_next_state(
        self,
        current_state: WorkflowState,
        result_data: Dict[str, Any],
        session_data: Dict[str, Any]
    ) -> WorkflowState:
        """
        Get the next logical state based on current state and data.
        
        Args:
            current_state: Current workflow state
            result_data: Data from current component
            session_data: Session data
            
        Returns:
            Next WorkflowState
        """
        # Handle linear progression
        if self._state_equals(current_state, WorkflowState.INITIAL):
            # Check if we have image or need clarification
            if result_data.get('has_image') or session_data.get('diagnosis_results'):
                return WorkflowState.CLASSIFICATION
            else:
                return WorkflowState.CLARIFICATION

        elif self._state_equals(current_state, WorkflowState.INTENT_CAPTURE):
            # After capturing intent, check if we need more clarification
            if self._needs_clarification(result_data, session_data):
                return WorkflowState.CLARIFICATION
            else:
                return WorkflowState.CLASSIFICATION
        
        elif self._state_equals(current_state, WorkflowState.CLARIFICATION):
            # After clarification, proceed to classification if we have image
            if session_data.get('diagnosis_results') or result_data.get('has_image'):
                return WorkflowState.CLASSIFICATION
            else:
                return WorkflowState.CLARIFICATION  # Need more clarification
        
        elif self._state_equals(current_state, WorkflowState.CLASSIFICATION):
            # After classification, move to prescription
            return WorkflowState.PRESCRIPTION
        
        elif self._state_equals(current_state, WorkflowState.PRESCRIPTION):
            # After prescription, check for constraints or move to vendor recommendation
            if self._should_gather_constraints(result_data, session_data):
                return WorkflowState.CONSTRAINT_GATHERING
            elif self._should_recommend_vendors(result_data, session_data):
                return WorkflowState.VENDOR_RECOMMENDATION
            else:
                return WorkflowState.FOLLOW_UP
        
        elif self._state_equals(current_state, WorkflowState.CONSTRAINT_GATHERING):
            # After constraint gathering, check if vendor recommendation is needed
            if self._should_recommend_vendors(result_data, session_data):
                return WorkflowState.VENDOR_RECOMMENDATION
            else:
                return WorkflowState.FOLLOW_UP
        
        elif self._state_equals(current_state, WorkflowState.VENDOR_RECOMMENDATION):
            # After vendor recommendation, move to follow-up
            return WorkflowState.FOLLOW_UP
        
        elif self._state_equals(current_state, WorkflowState.FOLLOW_UP):
            # Follow-up can branch based on user choice
            follow_up_action = result_data.get('follow_up_action')
            
            if follow_up_action == 'reclassify':
                return WorkflowState.CLASSIFICATION
            elif follow_up_action == 'alternative_prescription':
                return WorkflowState.PRESCRIPTION
            elif follow_up_action == 'different_vendors':
                return WorkflowState.VENDOR_RECOMMENDATION
            elif follow_up_action == 'new_problem':
                return WorkflowState.INTENT_CAPTURE
            else:
                return WorkflowState.COMPLETED
        
        else:
            return WorkflowState.COMPLETED

    def _needs_clarification(self, result_data: Dict[str, Any], session_data: Dict[str, Any]) -> bool:
        """Check if more clarification is needed."""
        user_profile = result_data.get('user_profile', {})
        
        # Check for missing critical information
        missing_info = []
        if not user_profile.get('crop_type'):
            missing_info.append('crop_type')
        if not user_profile.get('location'):
            missing_info.append('location')
        if not user_profile.get('problem_description') and not result_data.get('has_image'):
            missing_info.append('problem_description')
        
        return len(missing_info) > 0

    def _should_gather_constraints(self, result_data: Dict[str, Any], session_data: Dict[str, Any]) -> bool:
        """Check if constraint gathering is needed."""
        user_profile = session_data.get('user_profile', {})
        prescription = result_data.get('prescription', {})
        
        # Check if user has specific preferences or constraints
        has_preferences = user_profile.get('organic_preference') or user_profile.get('budget_constraint')
        has_multiple_options = len(prescription.get('treatment_options', [])) > 1
        
        return not has_preferences and has_multiple_options

    def _should_recommend_vendors(self, result_data: Dict[str, Any], session_data: Dict[str, Any]) -> bool:
        """Check if vendor recommendation should be offered."""
        user_profile = session_data.get('user_profile', {})
        prescription = result_data.get('prescription', {})
        
        # Check if prescription has specific products that need vendors
        has_specific_products = prescription.get('recommended_products', [])
        user_wants_vendors = result_data.get('request_vendors', False)
        location_available = user_profile.get('location')
        
        return bool(has_specific_products and (user_wants_vendors or location_available))

    async def get_available_actions(
        self,
        current_state: WorkflowState,
        session_data: Dict[str, Any]
    ) -> List[str]:
        """
        Get available actions for the current state.
        
        Args:
            current_state: Current workflow state
            session_data: Current session data
            
        Returns:
            List of available actions
        """
        base_actions = self.available_actions_map.get(current_state, [])
        
        # Add contextual actions based on session data
        contextual_actions = []
        
        if self._state_equals(current_state, WorkflowState.PRESCRIPTION):
            if session_data.get('user_profile', {}).get('location'):
                contextual_actions.append('request_vendors')
            if len(session_data.get('prescriptions', [])) > 0:
                contextual_actions.append('compare_prescriptions')
        
        elif self._state_equals(current_state, WorkflowState.FOLLOW_UP):
            if session_data.get('diagnosis_results'):
                contextual_actions.extend(['reclassify', 'alternative_prescription'])
            if session_data.get('prescriptions'):
                contextual_actions.append('different_vendors')
        
        # Always available actions
        contextual_actions.extend(['restart', 'help', 'summary'])
        
        return base_actions + contextual_actions

    def _initialize_state_transitions(self) -> Dict[WorkflowState, List[WorkflowState]]:
        """Initialize valid state transitions."""
        return {
            WorkflowState.INITIAL: [WorkflowState.INTENT_CAPTURE, WorkflowState.CLARIFICATION],
            WorkflowState.INTENT_CAPTURE: [WorkflowState.CLARIFICATION, WorkflowState.CLASSIFICATION],
            WorkflowState.CLARIFICATION: [WorkflowState.CLASSIFICATION, WorkflowState.CLARIFICATION],
            WorkflowState.CLASSIFICATION: [WorkflowState.PRESCRIPTION, WorkflowState.CLARIFICATION],
            WorkflowState.PRESCRIPTION: [
                WorkflowState.CONSTRAINT_GATHERING,
                WorkflowState.VENDOR_RECOMMENDATION,
                WorkflowState.FOLLOW_UP
            ],
            WorkflowState.CONSTRAINT_GATHERING: [
                WorkflowState.VENDOR_RECOMMENDATION,
                WorkflowState.FOLLOW_UP,
                WorkflowState.PRESCRIPTION
            ],
            WorkflowState.VENDOR_RECOMMENDATION: [WorkflowState.FOLLOW_UP],
            WorkflowState.FOLLOW_UP: [
                WorkflowState.CLASSIFICATION,
                WorkflowState.PRESCRIPTION,
                WorkflowState.VENDOR_RECOMMENDATION,
                WorkflowState.INTENT_CAPTURE,
                WorkflowState.COMPLETED
            ],
            WorkflowState.COMPLETED: [WorkflowState.INTENT_CAPTURE],
            WorkflowState.ERROR: [WorkflowState.INITIAL, WorkflowState.INTENT_CAPTURE]
        }

    def _initialize_available_actions(self) -> Dict[WorkflowState, List[str]]:
        """Initialize available actions for each state."""
        return {
            WorkflowState.INITIAL: ['upload_image', 'describe_problem'],
            WorkflowState.INTENT_CAPTURE: ['provide_details', 'clarify_problem'],
            WorkflowState.CLARIFICATION: [
                'provide_crop_type', 'provide_location', 'describe_symptoms', 'upload_image'
            ],
            WorkflowState.CLASSIFICATION: ['confirm_diagnosis', 'request_reclassification'],
            WorkflowState.PRESCRIPTION: [
                'accept_prescription', 'request_alternatives', 'specify_preferences'
            ],
            WorkflowState.CONSTRAINT_GATHERING: [
                'specify_organic_preference', 'set_budget_constraint', 'no_constraints'
            ],
            WorkflowState.VENDOR_RECOMMENDATION: [
                'accept_vendor', 'request_more_vendors', 'skip_vendors'
            ],
            WorkflowState.FOLLOW_UP: [
                'continue', 'new_problem', 'reclassify', 'alternative_prescription'
            ],
            WorkflowState.COMPLETED: ['new_consultation', 'restart'],
            WorkflowState.ERROR: ['retry', 'restart']
        }
