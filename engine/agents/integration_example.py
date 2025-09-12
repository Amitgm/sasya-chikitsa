"""
Integration Example - How to use the Planning Agent System

This file demonstrates how to integrate the new planning agent system
with the existing agent architecture and API endpoints.
"""

import asyncio
import logging
from fastapi import FastAPI
from api.agent_api import AgentAPI
from api.agent_core import AgentCore
from agents.server.planning_api import add_planning_agent_to_app

logger = logging.getLogger(__name__)

class HybridAgentSystem:
    """
    Example of hybrid system that uses both planning agent and legacy agent.
    
    This demonstrates how to:
    - Route requests to appropriate system based on preferences
    - Migrate sessions between systems
    - Maintain backward compatibility
    - Leverage strengths of both approaches
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        
        # Initialize existing system
        self.legacy_agent_core = AgentCore()
        self.legacy_agent_api = AgentAPI(self.legacy_agent_core)
        
        # Add planning agent system
        self.planning_agent_api = add_planning_agent_to_app(app)
        
        # Add hybrid routing endpoints
        self._add_hybrid_routes()
        
        logger.info("🎯 Hybrid agent system initialized with both legacy and planning agents")

    def _add_hybrid_routes(self):
        """Add hybrid routing endpoints."""
        
        @self.app.post("/chat-intelligent")
        async def intelligent_chat_router(req):
            """
            Intelligent router that chooses the best system based on request.
            
            Planning Agent for:
            - New sessions with images
            - Multi-step workflows
            - Users requesting guided experience
            
            Legacy Agent for:
            - Simple text questions
            - Quick responses
            - Backward compatibility
            """
            # Route to planning agent for complex workflows
            if req.image_b64 or 'guided' in req.message.lower() or 'step by step' in req.message.lower():
                logger.info("🎯 Routing to Planning Agent")
                return await self.planning_agent_api.planning_chat(req)
            else:
                logger.info("⚡ Routing to Legacy Agent")
                return await self.legacy_agent_api.chat(req)

# Example usage in existing main.py or app initialization:
def initialize_hybrid_system():
    """
    Example initialization function.
    
    This shows how to modify existing FastAPI app initialization
    to include the planning agent system.
    """
    
    # Create FastAPI app (existing)
    app = FastAPI(title="Sasya Chikitsa - Plant Disease Diagnosis API")
    
    # Initialize existing agent system (existing)
    agent_core = AgentCore()
    agent_api = AgentAPI(agent_core)
    
    # NEW: Add planning agent system
    planning_api = add_planning_agent_to_app(app)
    
    # NEW: Optional - Create hybrid system for intelligent routing
    hybrid_system = HybridAgentSystem(app)
    
    logger.info("✅ Hybrid agent system fully initialized")
    return app, agent_core, planning_api

# Example of using the planning agent programmatically:
async def example_usage():
    """
    Example of how to use the planning agent programmatically.
    """
    from agents.server.planning_agent import PlanningAgent
    
    # Initialize planning agent
    planning_agent = PlanningAgent()
    
    # Example 1: User uploads image and asks for diagnosis
    result = await planning_agent.process_user_request(
        session_id="user123",
        user_input="What's wrong with my tomato plant?",
        image_data="base64_encoded_image_data_here",
        context={"crop_type": "tomato"}
    )
    
    print(f"Response: {result.response}")
    print(f"Current State: {result.current_state}")
    print(f"Next Actions: {result.next_actions}")
    
    # Example 2: Follow-up question
    result2 = await planning_agent.process_user_request(
        session_id="user123",
        user_input="I'm in Punjab, India and it's Kharif season",
        image_data=None,
        context={}
    )
    
    print(f"Follow-up Response: {result2.response}")
    
    # Example 3: Get session summary
    summary = await planning_agent.get_session_summary("user123")
    print(f"Session Summary: {summary}")

# Migration helper for existing sessions:
async def migrate_legacy_session_to_planning(session_id: str, legacy_agent: AgentCore, planning_agent: PlanningAgent):
    """
    Helper function to migrate existing session data to planning agent.
    
    Args:
        session_id: Session to migrate
        legacy_agent: Existing agent core instance
        planning_agent: Planning agent instance
    """
    try:
        # Get existing session data
        legacy_history = legacy_agent.get_session_history(session_id)
        legacy_metadata = legacy_agent.get_session_metadata(session_id)
        
        # Convert to planning agent format
        migration_context = {
            "migrated_from_legacy": True,
            "legacy_history_length": len(getattr(legacy_history, 'messages', [])),
            "legacy_metadata": legacy_metadata
        }
        
        # Initialize planning session with migration context
        result = await planning_agent.process_user_request(
            session_id=session_id,
            user_input="Continue with my plant problem",
            image_data=None,
            context=migration_context
        )
        
        logger.info(f"✅ Successfully migrated session {session_id} to planning agent")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate session {session_id}: {e}")
        raise

if __name__ == "__main__":
    # Example of running the system
    app, agent_core, planning_api = initialize_hybrid_system()
    
    # Run example usage
    asyncio.run(example_usage())
