"""
API Integration Layer for Planning Agent System

Integrates the new planning agent with the existing FastAPI system,
providing endpoints for the multi-step plant diagnosis workflow.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import os
import sys

# Add the necessary directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
agents_dir = os.path.dirname(current_dir)
engine_dir = os.path.dirname(agents_dir)

for path in [agents_dir, engine_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from agents.server.planning_agent import PlanningAgent
# from api.agent_api import ChatRequest  # Import from existing system - disabled for now

logger = logging.getLogger(__name__)

class PlanningChatRequest(BaseModel):
    """Extended chat request for planning agent."""
    session_id: Optional[str] = "default"
    message: str = ""
    image_b64: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    workflow_action: Optional[str] = None  # Specific action like 'reclassify', 'get_vendors'

class PlanningAgentAPI:
    """
    API layer for the Planning Agent system.
    
    Provides endpoints that integrate with existing FastAPI application
    while leveraging the new multi-step planning architecture.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.planning_agent = PlanningAgent()
        self._add_planning_routes()
        
        logger.info("🚀 PlanningAgentAPI initialized and routes added")

    def _add_planning_routes(self):
        """Add planning agent routes to FastAPI app."""
        
        @self.app.post("/planning/chat")
        async def planning_chat(req: PlanningChatRequest):
            """
            Main planning agent chat endpoint.
            Processes user requests through the multi-step workflow.
            """
            try:
                logger.info(f"🎯 Planning chat request: session={req.session_id}, has_image={bool(req.image_b64)}")
                
                result = await self.planning_agent.process_user_request(
                    session_id=req.session_id or "default",
                    user_input=req.message,
                    image_data=req.image_b64,
                    context=req.context or {}
                )
                
                return {
                    "success": result.success,
                    "response": result.response,
                    "current_state": result.current_state.value,
                    "next_actions": result.next_actions,
                    "requires_user_input": result.requires_user_input,
                    "error_message": result.error_message
                }
                
            except Exception as e:
                logger.error(f"❌ Planning chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/planning/chat-stream")
        async def planning_chat_stream(req: PlanningChatRequest):
            """
            Streaming version of planning agent chat.
            Streams progress updates and results in real-time.
            """
            try:
                logger.info(f"🌊 Planning stream request: session={req.session_id}")
                
                async def stream_generator():
                    # Emit initial status
                    yield f"data: Starting analysis...\n\n"
                    await asyncio.sleep(0.3)
                    
                    # Define streaming callback to emit intermediate results
                    async def stream_callback(response_chunk: str):
                        """Stream intermediate component responses in real-time"""
                        if response_chunk.strip():
                            yield f"data: {response_chunk}\n\n"
                            await asyncio.sleep(0.1)  # Small delay for readability
                    
                    # Create a queue to collect streamed chunks from the planning agent
                    stream_queue = asyncio.Queue()
                    streaming_complete = False
                    
                    async def queue_callback(chunk: str):
                        """Callback that puts chunks into the queue"""
                        await stream_queue.put(chunk)
                    
                    # Start processing the request with streaming
                    async def process_request():
                        nonlocal streaming_complete
                        try:
                            result = await self.planning_agent.process_user_request(
                                session_id=req.session_id or "default",
                                user_input=req.message,
                                image_data=req.image_b64,
                                context=req.context or {},
                                stream_callback=queue_callback
                            )
                            # Signal completion
                            await stream_queue.put(None)  # End marker
                            streaming_complete = True
                            return result
                        except Exception as e:
                            await stream_queue.put(f"Error: {str(e)}")
                            await stream_queue.put(None)  # End marker
                            streaming_complete = True
                            raise
                    
                    # Start the request processing in the background
                    request_task = asyncio.create_task(process_request())
                    
                    # Stream chunks as they arrive
                    while not streaming_complete:
                        try:
                            # Wait for next chunk with timeout
                            chunk = await asyncio.wait_for(stream_queue.get(), timeout=30.0)
                            
                            if chunk is None:  # End marker
                                break
                                
                            # Emit the chunk
                            yield f"data: {chunk}\n\n"
                            
                        except asyncio.TimeoutError:
                            logger.warning("Stream timeout - no new chunks received")
                            break
                        except Exception as e:
                            logger.error(f"Stream error: {e}")
                            break
                    
                    # Wait for the request to complete and get the final result
                    try:
                        result = await request_task
                        
                        # Only emit final result if it wasn't already streamed
                        if not streaming_complete or result.requires_user_input:
                            if result.success:
                                logger.info("✅ Streaming workflow completed successfully")
                            else:
                                yield f"data: {result.response}\n\n"
                                
                    except Exception as e:
                        logger.error(f"Request processing failed: {e}")
                        yield f"data: I encountered an error processing your request. Please try again.\n\n"
                    
                    # Emit completion marker
                    yield f"data: [DONE]\n\n"
                
                return StreamingResponse(
                    stream_generator(),
                    media_type="text/plain",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
                
            except Exception as e:
                logger.error(f"❌ Planning stream error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/planning/session/{session_id}")
        async def get_planning_session(session_id: str):
            """Get current planning session state and history."""
            try:
                session_summary = await self.planning_agent.get_session_summary(session_id)
                return {
                    "session_id": session_id,
                    "summary": session_summary,
                    "success": True
                }
            except Exception as e:
                logger.error(f"❌ Error getting session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/planning/session/{session_id}/restart")
        async def restart_planning_session(session_id: str):
            """Restart a planning session from the beginning."""
            try:
                result = await self.planning_agent.restart_session(session_id)
                return {
                    "success": result.success,
                    "message": "Session restarted successfully",
                    "response": result.response
                }
            except Exception as e:
                logger.error(f"❌ Error restarting session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/planning/session/{session_id}/actions")
        async def get_available_actions(session_id: str):
            """Get available actions for current session state."""
            try:
                actions = await self.planning_agent.get_available_actions(session_id)
                return {
                    "session_id": session_id,
                    "available_actions": actions,
                    "success": True
                }
            except Exception as e:
                logger.error(f"❌ Error getting actions for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/planning/migrate-session")
        async def migrate_existing_session(req: ChatRequest):
            """
            Migrate existing agent session to planning system.
            Useful for transitioning from old to new system.
            """
            try:
                # Convert existing chat request to planning request
                planning_req = PlanningChatRequest(
                    session_id=req.session_id,
                    message=req.message,
                    image_b64=req.image_b64,
                    context={"migrated": True}
                )
                
                # Process through planning system
                result = await self.planning_agent.process_user_request(
                    session_id=planning_req.session_id or "default",
                    user_input=planning_req.message,
                    image_data=planning_req.image_b64,
                    context=planning_req.context or {}
                )
                
                return {
                    "success": True,
                    "message": "Session migrated to planning system",
                    "response": result.response,
                    "current_state": result.current_state.value
                }
                
            except Exception as e:
                logger.error(f"❌ Session migration error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def integrate_with_existing_agent(self, agent_core):
        """
        Integration method to work alongside existing agent system.
        
        Args:
            agent_core: Existing AgentCore instance
        """
        # Store reference to existing system for hybrid operations
        self.legacy_agent = agent_core
        
        # Could implement fallback mechanisms or hybrid routing here
        logger.info("🔄 Integration with existing agent system established")

# Utility function to add planning agent to existing FastAPI app
def add_planning_agent_to_app(app: FastAPI) -> PlanningAgentAPI:
    """
    Utility function to add planning agent endpoints to existing FastAPI app.
    
    Args:
        app: Existing FastAPI application
        
    Returns:
        PlanningAgentAPI instance
    """
    planning_api = PlanningAgentAPI(app)
    logger.info("✅ Planning agent API added to existing FastAPI application")
    return planning_api
