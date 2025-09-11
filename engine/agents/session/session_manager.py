"""
Session Manager - Component 8: Session Logging and State Tracking

Maintains a record of user inputs, diagnosis results, prescriptions, and vendor choices.
Supports longitudinal support, reminders, and enables seamless restarts from any step.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

@dataclass
class SessionActivity:
    """Record of a single activity in a session"""
    timestamp: datetime
    workflow_state: str
    user_input: str
    system_response: str
    component_data: Dict[str, Any]

@dataclass
class SessionData:
    """Complete session data structure"""
    session_id: str
    created_at: datetime
    last_updated: datetime
    workflow_state: str
    user_profile: Dict[str, Any]
    diagnosis_results: Dict[str, Any]
    prescriptions: List[Dict[str, Any]]
    vendor_choices: List[Dict[str, Any]]
    activities: List[SessionActivity]
    context: Dict[str, Any]

class SessionManager:
    """
    Manages session state, persistence, and activity logging.
    
    Core responsibilities:
    - Track user inputs and system responses
    - Maintain diagnosis results and prescriptions
    - Log vendor recommendations and user choices
    - Enable seamless session recovery and continuation
    - Support longitudinal analysis and reminders
    """
    
    def __init__(self):
        # In-memory session store (could be replaced with database)
        self.sessions: Dict[str, SessionData] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        
        logger.info("📊 SessionManager initialized")

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session state for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dictionary containing session state
        """
        await self._ensure_session_exists(session_id)
        
        session = self.sessions[session_id]
        return {
            'session_id': session.session_id,
            'workflow_state': session.workflow_state,
            'created_at': session.created_at,
            'last_updated': session.last_updated,
            'activity_count': len(session.activities)
        }

    async def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Complete session data dictionary
        """
        await self._ensure_session_exists(session_id)
        
        session = self.sessions[session_id]
        return {
            'user_profile': session.user_profile,
            'diagnosis_results': session.diagnosis_results,
            'classification_results': session.diagnosis_results,  # Provide both keys for compatibility
            'prescriptions': session.prescriptions,
            'vendor_choices': session.vendor_choices,
            'context': session.context,
            'workflow_state': session.workflow_state
        }

    async def update_session_state(
        self, 
        session_id: str, 
        workflow_state, 
        component_data: Dict[str, Any]
    ) -> None:
        """
        Update session state with new component data.
        
        Args:
            session_id: Session identifier
            workflow_state: Current workflow state
            component_data: Data from component execution
        """
        async with self._get_session_lock(session_id):
            await self._ensure_session_exists(session_id)
            
            session = self.sessions[session_id]
            
            # Handle both enum and string workflow states
            if hasattr(workflow_state, 'value'):
                state_str = workflow_state.value  # Extract value from enum
                session.workflow_state = state_str
            else:
                state_str = str(workflow_state)
                session.workflow_state = state_str
            
            session.last_updated = datetime.utcnow()
            
            logger.debug(f"📊 Updating session {session_id}: {workflow_state} -> {state_str}")
            logger.debug(f"   Component data keys: {list(component_data.keys())}")
            
            # Update relevant session data based on component type
            if state_str == 'intent_capture':
                user_profile_data = component_data.get('user_profile', {})
                session.user_profile.update(user_profile_data)
                session.context.update(component_data.get('context', {}))
                logger.debug(f"   ✅ Updated user_profile: {user_profile_data}")
            
            elif state_str == 'clarification':
                clarification_data = component_data.get('clarification_data', {})
                session.user_profile.update(clarification_data)
                logger.debug(f"   ✅ Updated user_profile from clarification: {clarification_data}")
            
            elif state_str == 'classification':
                classification_results = component_data.get('classification_results', {})
                if classification_results:
                    session.diagnosis_results.update(classification_results)
                    logger.debug(f"   ✅ Updated diagnosis_results: {list(classification_results.keys())}")
                    logger.debug(f"   ✅ diagnosis_results now contains: {session.diagnosis_results}")
                else:
                    logger.warning(f"   ⚠️  No classification_results found in component_data: {list(component_data.keys())}")
            
            elif state_str == 'prescription':
                prescription = component_data.get('prescription')
                if prescription:
                    session.prescriptions.append({
                        'timestamp': datetime.utcnow(),
                        'prescription': prescription
                    })
                    logger.debug(f"   ✅ Added prescription")
            
            elif state_str == 'vendor_recommendation':
                vendor_choice = component_data.get('vendor_choice')
                if vendor_choice:
                    session.vendor_choices.append({
                        'timestamp': datetime.utcnow(),
                        'choice': vendor_choice
                    })
                    logger.debug(f"   ✅ Added vendor choice")
            
            # Always update general context
            general_context = component_data.get('general_context', {})
            session.context.update(general_context)
            if general_context:
                logger.debug(f"   ✅ Updated general context: {list(general_context.keys())}")
            
            logger.info(f"📊 Session {session_id} updated: {workflow_state}")
            logger.debug(f"   Final user_profile: {session.user_profile}")
            logger.debug(f"   Final context: {session.context}")
            logger.debug(f"   Final diagnosis_results: {list(session.diagnosis_results.keys())}")

    async def log_activity(
        self,
        session_id: str,
        workflow_state: str,
        user_input: str,
        system_response: str,
        component_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an activity in the session.
        
        Args:
            session_id: Session identifier
            workflow_state: Current workflow state
            user_input: User's input
            system_response: System's response
            component_data: Additional component data
        """
        async with self._get_session_lock(session_id):
            await self._ensure_session_exists(session_id)
            
            activity = SessionActivity(
                timestamp=datetime.utcnow(),
                workflow_state=workflow_state,
                user_input=user_input[:500],  # Limit length for storage
                system_response=system_response[:1000],  # Limit length for storage
                component_data=component_data or {}
            )
            
            self.sessions[session_id].activities.append(activity)
            logger.debug(f"📝 Logged activity for session {session_id}: {workflow_state}")

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive session summary.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary dictionary
        """
        await self._ensure_session_exists(session_id)
        
        session = self.sessions[session_id]
        
        return {
            'session_info': {
                'session_id': session.session_id,
                'created_at': session.created_at,
                'last_updated': session.last_updated,
                'duration_minutes': (session.last_updated - session.created_at).total_seconds() / 60,
                'current_state': session.workflow_state
            },
            'user_profile': session.user_profile,
            'diagnosis_summary': {
                'has_diagnosis': bool(session.diagnosis_results),
                'diagnosis_count': len([a for a in session.activities if a.workflow_state == 'classification']),
                'latest_results': session.diagnosis_results
            },
            'prescription_summary': {
                'prescription_count': len(session.prescriptions),
                'latest_prescription': session.prescriptions[-1] if session.prescriptions else None
            },
            'vendor_summary': {
                'vendor_interactions': len(session.vendor_choices),
                'latest_choice': session.vendor_choices[-1] if session.vendor_choices else None
            },
            'activity_summary': {
                'total_interactions': len(session.activities),
                'states_visited': list(set(a.workflow_state for a in session.activities)),
                'recent_activities': [
                    {
                        'timestamp': a.timestamp,
                        'state': a.workflow_state,
                        'user_input': a.user_input[:100] + "..." if len(a.user_input) > 100 else a.user_input
                    }
                    for a in session.activities[-5:]  # Last 5 activities
                ]
            }
        }

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history for context.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of activities to return
            
        Returns:
            List of conversation activities
        """
        await self._ensure_session_exists(session_id)
        
        session = self.sessions[session_id]
        recent_activities = session.activities[-limit:] if session.activities else []
        
        return [
            {
                'timestamp': activity.timestamp,
                'state': activity.workflow_state,
                'user_input': activity.user_input,
                'system_response': activity.system_response
            }
            for activity in recent_activities
        ]

    async def clear_session(self, session_id: str) -> None:
        """
        Clear session data (restart session).
        
        Args:
            session_id: Session identifier
        """
        async with self._get_session_lock(session_id):
            if session_id in self.sessions:
                # Keep session ID and creation time, reset everything else
                created_at = self.sessions[session_id].created_at
                self.sessions[session_id] = SessionData(
                    session_id=session_id,
                    created_at=created_at,
                    last_updated=datetime.utcnow(),
                    workflow_state='initial',
                    user_profile={},
                    diagnosis_results={},
                    prescriptions=[],
                    vendor_choices=[],
                    activities=[],
                    context={}
                )
                logger.info(f"🔄 Cleared session {session_id}")

    async def get_sessions_for_cleanup(self, hours_old: int = 24) -> List[str]:
        """
        Get session IDs that are older than specified hours for cleanup.
        
        Args:
            hours_old: Age threshold in hours
            
        Returns:
            List of session IDs to cleanup
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)
        
        return [
            session_id
            for session_id, session in self.sessions.items()
            if session.last_updated < cutoff_time
        ]

    async def _ensure_session_exists(self, session_id: str) -> None:
        """Create session if it doesn't exist."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData(
                session_id=session_id,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                workflow_state='initial',
                user_profile={},
                diagnosis_results={},
                prescriptions=[],
                vendor_choices=[],
                activities=[],
                context={}
            )
            logger.info(f"📋 Created new session: {session_id}")

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a lock for session thread safety."""
        if session_id not in self.session_locks:
            self.session_locks[session_id] = asyncio.Lock()
        return self.session_locks[session_id]
