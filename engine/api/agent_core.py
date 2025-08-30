import os
import asyncio
import logging
from typing import Optional, Dict, Callable
from contextvars import ContextVar
from dotenv import load_dotenv

from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from ml.cnn_with_attention_classifier import CNNWithAttentionClassifier


try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:
    logger.warning("Exception for ChatOpenAI")  # pragma: no cover
    ChatOpenAI = None  # type: ignore

# Prefer modern package, fall back to legacy community import
try:
    from langchain_ollama import ChatOllama  # type: ignore
except Exception:  # pragma: no cover
    try:
        from langchain_community.chat_models import ChatOllama  # type: ignore
    except Exception:  # pragma: no cover
        ChatOllama = None  # type: ignore


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    # Optional: attach an image per turn. We avoid placing raw base64 in the prompt by using a handle.
    image_b64: Optional[str] = None
    text: Optional[str] = None


def create_llm():
    """Create a chat model. Prefers OpenAI if OPENAI_API_KEY is set, otherwise tries Ollama.
    Raises if none configured.
    """
    ollama_host = os.getenv("OLLAMA_HOST")
    print(f"DEBUG: OLLAMA_HOST={ollama_host}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if ChatOpenAI is not None and api_key:
        # Choose a small, cost-effective model by default
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2)
    if ChatOllama is not None and (ollama_host or os.path.exists("/usr/local/bin/ollama")):
        if ollama_host:
            return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"), temperature=0.1, base_url=ollama_host)
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"), temperature=0.1)
    raise RuntimeError(
        "No chat model configured. Set OPENAI_API_KEY (and optionally OPENAI_MODEL) or run Ollama and set OLLAMA_MODEL."
    )


class AgentCore:
    def __init__(self):
        load_dotenv()
        self.model = CNNWithAttentionClassifier()
        self.image_store: Dict[str, str] = {}
        self.session_store: Dict[str, ChatMessageHistory] = {}
        self.agent_with_history = self._build_agent()
        self._emit_ctx: ContextVar[Optional[Callable[[str], None]]] = ContextVar("emit_ctx", default=None)
        self._image_emitters: Dict[str, Callable[[str], None]] = {}
        self.llm = create_llm() # Initialize LLM here
        logger.debug(f"AgentCore initialized with agent_with_history: {self.agent_with_history}")

    def get_image_store_status(self):
        """Get current status of image store for debugging."""
        return {
            "num_images": len(self.image_store),
            "keys": list(self.image_store.keys()),
            "has_images": bool(self.image_store)
        }

    def get_agent_status(self):
        """Get current status of the agent for debugging."""
        return {
            "agent_type": type(self.agent_with_history).__name__,
            "has_tools": hasattr(self.agent_with_history, 'tools'),
            "image_store_status": self.get_image_store_status(),
            "session_count": len(self.session_store)
        }

    def get_conversation_debug_info(self, session_id: str) -> Dict:
        """Get detailed debug information about a conversation session."""
        history = self.get_session_history(session_id)
        messages = getattr(history, 'messages', [])
        
        debug_info = {
            "session_id": session_id,
            "total_messages": len(messages),
            "message_types": {},
            "recent_messages": []
        }
        
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            debug_info["message_types"][msg_type] = debug_info["message_types"].get(msg_type, 0) + 1
            
            # Show last 5 messages for debugging
            if len(debug_info["recent_messages"]) < 5:
                content = getattr(msg, "content", str(msg))
                debug_info["recent_messages"].append({
                    "type": msg_type,
                    "content": content[:100] + "..." if len(str(content)) > 100 else content
                })
        
        return debug_info

    def get_conversation_summary(self, session_id: str) -> str:
        """Get a human-readable summary of the conversation for the agent."""
        history = self.get_session_history(session_id)
        messages = getattr(history, 'messages', [])
        
        if not messages:
            return "This is a new conversation with no previous history."
        
        # Count different types of messages
        ai_messages = [msg for msg in messages if getattr(msg, "type", None) == "ai"]
        human_messages = [msg for msg in messages if getattr(msg, "type", None) == "human"]
        
        summary = f"Conversation Summary:\n"
        summary += f"- Total messages: {len(messages)}\n"
        summary += f"- AI responses: {len(ai_messages)}\n"
        summary += f"- Human messages: {len(human_messages)}\n"
        
        if ai_messages:
            summary += f"\nRecent AI responses:\n"
            for i, msg in enumerate(ai_messages[-3:], 1):  # Last 3 AI messages
                content = getattr(msg, "content", str(msg))
                summary += f"  {i}. {content[:80]}...\n"
        
        return summary

    def get_tool_availability_guidance(self, system_context: str) -> str:
        """Get clear guidance about tool availability for the agent."""
        if not system_context or "image_handle=" not in system_context:
            guidance = "TOOL AVAILABILITY: NO TOOLS AVAILABLE\n"
            guidance += "Reason: No new image provided (system_context is empty or missing 'image_handle=')\n"
            guidance += "Action Required: Use conversation history to answer questions. Do NOT call any tools.\n"
            guidance += "You can reference previous classification results and provide follow-up advice.\n"
        else:
            guidance = "TOOL AVAILABILITY: classify_leaf_safe tool is AVAILABLE\n"
            guidance += f"Reason: New image provided with handle in system_context\n"
            guidance += "Action Required: Use the classify_leaf_safe tool with the provided image_handle.\n"
        
        return guidance

    def get_available_results_summary(self, session_id: str) -> str:
        """Get a summary of what classification results are available in the conversation history."""
        history = self.get_session_history(session_id)
        messages = getattr(history, 'messages', [])
        
        if not messages:
            return "No previous results available."
        
        # Look for AI messages that contain classification results
        ai_messages = [msg for msg in messages if getattr(msg, "type", None) == "ai"]
        
        if not ai_messages:
            return "No previous AI responses found."
        
        summary = "AVAILABLE PREVIOUS RESULTS:\n"
        for i, msg in enumerate(ai_messages, 1):
            content = getattr(msg, "content", str(msg))
            if "healthy" in content.lower():
                summary += f"{i}. HEALTHY LEAF - Plant appears to be healthy\n"
            elif "disease" in content.lower() or "infection" in content.lower():
                summary += f"{i}. DISEASE DETECTED - Plant shows signs of disease\n"
            elif "error" in content.lower() or "no image" in content.lower():
                summary += f"{i}. ERROR - No valid image was provided\n"
            else:
                summary += f"{i}. ANALYSIS RESULT - {content[:50]}...\n"
        
        summary += "\nUse these previous results to answer questions when no new image is provided."
        return summary

    def get_conversation_state_summary(self, session_id: str, system_context: str) -> str:
        """Get a comprehensive summary of the current conversation state for the agent."""
        has_image = "image_handle=" in system_context
        history = self.get_session_history(session_id)
        messages = getattr(history, 'messages', [])
        
        summary = "=== CONVERSATION STATE SUMMARY ===\n"
        summary += f"Current Request: {'WITH NEW IMAGE' if has_image else 'NO NEW IMAGE'}\n"
        summary += f"System Context: {system_context if system_context else 'EMPTY'}\n"
        summary += f"Total Messages: {len(messages)}\n"
        
        if has_image:
            summary += "\nACTION REQUIRED: Use the classify_leaf_safe tool with the provided image_handle.\n"
        else:
            summary += "\nACTION REQUIRED: Use conversation history to answer questions. DO NOT call any tools.\n"
            summary += "You have access to previous classification results and can provide follow-up advice.\n"
        
        if messages:
            ai_messages = [msg for msg in messages if getattr(msg, "type", None) == "ai"]
            if ai_messages:
                summary += f"\nPrevious Results Available: {len(ai_messages)} AI responses\n"
                summary += "Use these to provide context-aware answers.\n"
        
        summary += "=== END SUMMARY ===\n"
        return summary

    def get_session_history(self, session_id: str) -> ChatMessageHistory:
        if session_id not in self.session_store:
            self.session_store[session_id] = ChatMessageHistory()
        return self.session_store[session_id]

    def _build_agent(self) -> RunnableWithMessageHistory:
        @tool("classify_leaf", return_direct=True)
        def classify_leaf(image_handle: str, text: Optional[str] = None) -> str:
            """CRITICAL: ONLY use this tool when system_context contains 'image_handle='. If system_context is empty or missing 'image_handle=', DO NOT call this tool. Classify a plant leaf image using the provided image_handle from system context."""
            logger.debug(f"classify_leaf tool called with image_handle: '{image_handle}', text: '{text}'")
            logger.debug(f"Current image_store keys: {list(self.image_store.keys())}")
            
            # CRITICAL SAFETY CHECK: This tool should NEVER be called without a valid image
            # If we reach this point, it means the LLM ignored our instructions
            # We need to check if there's actually an image available
            if not self.image_store:
                logger.error("CRITICAL ERROR - Tool called but image_store is empty!")
                return "ERROR: This tool should not have been called. No images are available in the system. Please ask the user to upload an image first."
            
            # Additional safety check - ensure image_handle is not empty or None
            if not image_handle or image_handle.strip() == "":
                logger.error("Empty or None image_handle provided")
                return "ERROR: No image handle provided. This tool should not have been called without a valid image handle."
            
            # Check if the provided handle actually exists in our store
            if image_handle not in self.image_store:
                logger.error(f"CRITICAL ERROR - Tool called with invalid handle '{image_handle}' that doesn't exist in image_store")
                logger.error(f"Available handles: {list(self.image_store.keys())}")
                return f"ERROR: Invalid image handle '{image_handle}'. This tool should not have been called. Available handles: {list(self.image_store.keys())}"
            
            image_b64 = self.image_store[image_handle]
            logger.debug(f"Image found, proceeding with classification")
            emitter = self._image_emitters.get(image_handle) or self._emit_ctx.get()
            outputs = []
            for chunk in self.model.predict_leaf_classification(image_b64, text or ""):
                chunk_str = str(chunk).rstrip("\n")
                outputs.append(chunk_str)
                if emitter:
                    try:
                        emitter(chunk_str)
                    except Exception:
                        pass
            return "\n".join(outputs)

        # Create a wrapper tool that checks availability at runtime
        @tool("classify_leaf_safe", return_direct=True)
        def classify_leaf_safe(image_handle: str, text: Optional[str] = None) -> str:
            """SAFE VERSION: This tool will only work when there are actual images available. If no images are available, it will return an error message."""
            logger.debug(f"classify_leaf_safe tool called with image_handle: '{image_handle}', text: '{text}'")
            
            # Check if there are any images available at all
            if not self.image_store:
                return "ERROR: No images are currently available for classification. Please ask the user to upload an image first."
            
            # Check if the specific handle exists
            if image_handle not in self.image_store:
                return f"ERROR: Image handle '{image_handle}' not found. Available handles: {list(self.image_store.keys())}. Please ask the user to upload a new image."
            
            # If we get here, we have a valid image, so call the actual classification
            return classify_leaf(image_handle, text)

        tools = [classify_leaf_safe]  # Use the safe version that checks availability

        system = (
            "You are a helpful plant diagnostics assistant. "
            "Hold a helpful, concise conversation. "
            "CRITICAL RULE: You MUST check the system_context before calling any tools. "
            "ONLY call the `classify_leaf_safe` tool when the system_context contains 'image_handle='. "
            "If the system_context does NOT contain 'image_handle=', then you CANNOT and MUST NOT call the classify_leaf_safe tool. "
            "Instead, respond conversationally and ask the user to provide an image if they want leaf analysis. "
            "When an image_handle is present in system_context, use it to call the tool, then summarize results and ask follow-up questions. "
            "NEVER call the classify_leaf_safe tool without a valid image_handle in system_context. "
            "If system_context is empty or does not contain 'image_handle=', you have NO tools available. "
            "IMPORTANT: You have access to the full conversation history. Use previous classification results and context to provide helpful responses even when no new image is provided. "
            "You can reference previous diagnoses, answer follow-up questions about past results, and provide general plant care advice based on the conversation history. "
            "CRITICAL: When no new image is provided (system_context is empty), you MUST use the conversation history to answer questions. Do NOT try to call any tools. "
            "EXAMPLE: If someone asks 'What did we find about my plant?' and there's no new image, look at the conversation history for previous results and say something like 'Based on our previous analysis, we found...'"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system + "\n\nSystem context: {system_context}\n\nIMPORTANT: Check the system_context above before deciding to use any tools. If system_context is empty or does not contain 'image_handle=', you have NO tools available and must respond conversationally. Use the conversation history to provide context-aware responses. The conversation history below contains all previous interactions and results - use it to answer questions when no new image is provided."),
            ("system", "CONVERSATION STATE: {conversation_summary}"),
            ("system", "TOOL GUIDANCE: {tool_guidance}"),
            ("system", "AVAILABLE RESULTS: {available_results}"),
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
            ("human", "{input}"),
        ])

        llm = create_llm()
        self.llm = llm
        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "2")),
            return_intermediate_steps=True,
        )

        def get_history(cfg):
            sid = cfg.get("configurable", {}).get("session_id", "default") \
                if isinstance(cfg, dict) else cfg if isinstance(cfg, str) else "default"
            return self.get_session_history(sid)

        self.get_history = get_history
        return RunnableWithMessageHistory(
            executor,
            get_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def _get_classification_history(self, session_id: str) -> str:
        history = self.get_history({"configurable": {"session_id": session_id}})
        results = []
        for msg in getattr(history, 'messages', []):
            if getattr(msg, "type", None) == "ai":
                text = getattr(msg, "content", "") if hasattr(msg, "content") else str(msg)
                results.append(text)
        
        if not results:
            return "No previous classification results available."
        
        # Format the history to be more readable and informative
        formatted_results = ["=== PREVIOUS CLASSIFICATION RESULTS ==="]
        for i, result in enumerate(results, 1):
            # Extract key information from the result
            if "healthy" in result.lower():
                formatted_results.append(f"Result {i}: HEALTHY LEAF - {result[:100]}...")
            elif "error" in result.lower() or "no image" in result.lower():
                formatted_results.append(f"Result {i}: ERROR - {result[:100]}...")
            else:
                formatted_results.append(f"Result {i}: {result[:100]}...")
        formatted_results.append("=== END PREVIOUS RESULTS ===")
        
        return "\n".join(formatted_results)

    async def invoke_agent(self, inputs: Dict, session_id: str, callbacks: Optional[list] = None):
        # Check if there's an image_handle in the system context
        system_context = inputs.get("system_context", "")
        has_image = "image_handle=" in system_context
        
        logger.debug(f"invoke_agent called with system_context: '{system_context}'")
        logger.debug(f"has_image: {has_image}")
        logger.debug(f"inputs: {inputs}")
        
        # Add tool guidance to help the agent understand what's available
        tool_guidance = self.get_tool_availability_guidance(system_context)
        inputs["tool_guidance"] = tool_guidance
        logger.debug(f"Tool guidance: {tool_guidance}")
        
        # Add conversation state summary to help the agent understand the current situation
        conversation_summary = self.get_conversation_state_summary(session_id, system_context)
        inputs["conversation_summary"] = conversation_summary
        logger.debug(f"Conversation state summary: {conversation_summary}")
        
        # Add available results summary to help the agent understand what's in conversation history
        results_summary = self.get_available_results_summary(session_id)
        inputs["available_results"] = results_summary
        logger.debug(f"Available results summary: {results_summary}")
        
        # Always use the same agent to preserve conversation history
        # The system prompt and tool availability will handle preventing inappropriate tool calls
        logger.debug("Using agent with conversation history preserved")
        return await asyncio.to_thread(self.agent_with_history.invoke, inputs, config={
            "callbacks": callbacks,
            "configurable": {"session_id": session_id}
        })

    async def summarize_response(self, final_text: str, session_id: str):
        classification_history = self._get_classification_history(session_id)
        prompt = (
                "You are a plant expert assistant. Use all previous plant leaf classification results in this session (provided below) "
                "to answer the user's latest question. If an image is present, respond to the classification result as before. "
                "If the image is not present, use the classification history (shown as 'Previous Results') to answer. "
                "Always follow up with a relevant question.\n\n"
                "Previous Results:\n" +
                str(classification_history) + "\n"
                                             "Latest:\n" +
                str(final_text)
        )
        out = await asyncio.to_thread(self.llm.invoke, prompt)
        try:
            return out.content
        except Exception:
            return str(out)