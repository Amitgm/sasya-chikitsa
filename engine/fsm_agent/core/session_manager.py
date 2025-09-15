"""
Session Manager for FSM Agent Workflow
Handles state persistence between LangGraph invocations
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .workflow_state import WorkflowState, create_initial_state

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session state persistence for the FSM Agent workflow"""
    
    def __init__(self, storage_dir: str = "/tmp/fsm_sessions"):
        """
        Initialize session manager
        
        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        logger.info(f"SessionManager initialized with storage: {storage_dir}")
    
    def _get_session_file(self, session_id: str) -> str:
        """Get the file path for a session"""
        return os.path.join(self.storage_dir, f"{session_id}.json")
    
    def save_state(self, state: WorkflowState) -> None:
        """
        Save workflow state to disk
        
        Args:
            state: Current workflow state
        """
        try:
            session_file = self._get_session_file(state["session_id"])
            
            # Convert state to JSON-serializable format
            serializable_state = self._serialize_state(state)
            
            with open(session_file, 'w') as f:
                json.dump(serializable_state, f, indent=2, default=str)
            
            logger.info(f"💾 Saved state for session {state['session_id']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save state for session {state['session_id']}: {str(e)}")
    
    def load_state(self, session_id: str) -> Optional[WorkflowState]:
        """
        Load workflow state from disk
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Loaded state or None if not found/expired
        """
        try:
            session_file = self._get_session_file(session_id)
            
            if not os.path.exists(session_file):
                logger.info(f"📭 No saved state found for session {session_id}")
                return None
            
            # Check if session is expired (24 hours)
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(session_file))
            if file_age > timedelta(hours=24):
                logger.info(f"⏰ Session {session_id} expired, removing old state")
                os.remove(session_file)
                return None
            
            with open(session_file, 'r') as f:
                serialized_state = json.load(f)
            
            # Convert back to WorkflowState
            state = self._deserialize_state(serialized_state)
            
            logger.info(f"📂 Loaded state for session {session_id} with node: {state.get('current_node')}")
            return state
            
        except Exception as e:
            logger.error(f"❌ Failed to load state for session {session_id}: {str(e)}")
            return None
    
    def get_or_create_state(self, session_id: str, user_message: str, 
                           user_image: Optional[str] = None, 
                           context: Optional[Dict[str, Any]] = None) -> WorkflowState:
        """
        Get existing state or create new one
        
        Args:
            session_id: Session ID
            user_message: Current user message
            user_image: Optional image
            context: Optional context
            
        Returns:
            WorkflowState (existing or new)
        """
        # Try to load existing state
        existing_state = self.load_state(session_id)
        
        if existing_state:
            logger.info(f"🔄 Continuing conversation for session {session_id}")
            # Update with new user message
            existing_state["user_message"] = user_message
            existing_state["last_update_time"] = datetime.now()
            
            # Add new user image if provided (but don't overwrite existing)
            if user_image and not existing_state.get("user_image"):
                existing_state["user_image"] = user_image
                logger.info(f"📸 Added new image to existing session {session_id}")
            
            # Preserve existing image if no new one provided
            elif user_image:
                logger.info(f"📸 Updating image for session {session_id}")
                existing_state["user_image"] = user_image
            
            # Add user message to conversation history
            existing_state["messages"].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
                "node": existing_state.get("current_node", "unknown"),
                "image": user_image
            })
            
            return existing_state
        
        else:
            logger.info(f"🆕 Creating new session {session_id}")
            return create_initial_state(session_id, user_message, user_image, context)
    
    def _serialize_state(self, state: WorkflowState) -> Dict[str, Any]:
        """Convert WorkflowState to JSON-serializable format"""
        serialized = {}
        
        for key, value in state.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
                
        return serialized
    
    def _deserialize_state(self, data: Dict[str, Any]) -> WorkflowState:
        """Convert JSON data back to WorkflowState"""
        state = data.copy()
        
        # Convert datetime strings back to datetime objects
        for key in ["workflow_start_time", "last_update_time"]:
            if key in state and isinstance(state[key], str):
                try:
                    state[key] = datetime.fromisoformat(state[key])
                except ValueError:
                    state[key] = datetime.now()
        
        return state
    
    def cleanup_expired_sessions(self) -> None:
        """Remove expired session files"""
        try:
            current_time = datetime.now()
            removed_count = 0
            
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    file_age = current_time - datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_age > timedelta(hours=24):
                        os.remove(file_path)
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} expired sessions")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {str(e)}")
