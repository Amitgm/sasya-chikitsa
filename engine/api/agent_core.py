import os
import asyncio
import logging
import re
from typing import Optional, Dict, Callable, List, Union
from contextvars import ContextVar
from dotenv import load_dotenv

from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from engine.ml.cnn_with_attention_classifier import CNNWithAttentionClassifier


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
        def classify_leaf_safe(tool_input: str) -> str:
            """SAFE VERSION: Classify a plant leaf image using provided image handle. Input should be JSON with image_handle and optional text."""
            logger.debug(f"classify_leaf_safe tool called with input: '{tool_input}'")
            
            # Parse the tool input (could be JSON string or direct parameters)
            import json
            try:
                if isinstance(tool_input, str) and tool_input.startswith("{"):
                    # JSON string input from ReAct agent
                    parsed_input = json.loads(tool_input)
                    image_handle = parsed_input.get("image_handle", "")
                    text = parsed_input.get("text", "")
                else:
                    # Direct string input (fallback)
                    image_handle = tool_input
                    text = ""
            except (json.JSONDecodeError, AttributeError):
                # Fallback to treating it as direct image_handle
                image_handle = str(tool_input)
                text = ""
                
            logger.debug(f"Parsed: image_handle='{image_handle}', text='{text}'")
            
            # Check if there are any images available at all
            if not self.image_store:
                return "ERROR: No images are currently available for classification. Please ask the user to upload an image first."
            
            # Check if the specific handle exists
            if image_handle not in self.image_store:
                return f"ERROR: Image handle '{image_handle}' not found. Available handles: {list(self.image_store.keys())}. Please ask the user to upload a new image."
            
            # If we get here, we have a valid image, so call the actual classification
            logger.info(f"✅ classify_leaf_safe called successfully - proceeding with classification")
            
            # Call the inner function directly to avoid callback issues
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

        tools = [classify_leaf_safe]  # Use the safe version that checks availability

        system = (
            "You are a helpful plant diagnostics assistant.\n\n"
            
            "🚨 TOOL CALLING RULES (CRITICAL):\n"
            "1. IF system_context contains 'image_handle=' → MUST call classify_leaf_safe(image_handle, text)\n"
            "2. IF system_context is empty or no 'image_handle=' → NO TOOL CALLS, respond conversationally\n\n"
            
            "When calling classify_leaf_safe:\n"
            "- Use the image_handle from system_context\n" 
            "- Pass user's text as 'text' parameter for context\n"
            "- Process both image classification AND user's text question\n\n"
            
            "When NO tools available:\n"
            "- Use conversation history to answer questions\n"
            "- Reference previous diagnoses and results\n"
            "- Provide general plant care advice\n"
            "\n\n🚨 CRITICAL RESPONSE FORMAT REQUIREMENT: "
            "EVERY SINGLE RESPONSE MUST BE STRUCTURED AS FOLLOWS - NO EXCEPTIONS: "
            "\n\nMAIN_ANSWER: <your complete response content here>"
            "\nACTION_ITEMS: <specific actionable requests separated by |>"
            "\n\nEXAMPLE:"
            "\nMAIN_ANSWER: Based on our previous analysis, your plant requires regular watering and fertilization to thrive. For a personalized schedule, I need to know your plant type, local climate, and current care routine."
            "\nACTION_ITEMS: Tell me your plant type | Describe your local climate | Share current watering schedule | Get soil test recommendations"
            "\n\nRULES:"
            "• MAIN_ANSWER contains your complete diagnosis/response/information"
            "• ACTION_ITEMS contains specific, tappable requests users can make"
            "• Both sections are MANDATORY in EVERY response"
            "• Never respond without this exact format"
            "• ACTION_ITEMS should be actionable like 'Send me prescription', 'Give watering schedule', 'Show treatment steps'"
            "• Separate multiple action items with ' | '"
            "• This format is REQUIRED even for follow-up questions, general advice, or clarifications"
        )

        format_enforcement = (
            "\n\n" + "="*80 + "\n"
            "🚨🚨🚨 ABSOLUTE MANDATORY RESPONSE FORMAT 🚨🚨🚨\n"
            "="*80 + "\n"
            "EVERY RESPONSE MUST START WITH EXACTLY:\n\n"
            "MAIN_ANSWER: [your complete response here]\n"
            "ACTION_ITEMS: [specific actions separated by |]\n\n"
            "NO EXCEPTIONS! NO PLAIN TEXT RESPONSES!\n"
            "WRONG: 'I cannot call the classify_leaf_safe tool...'\n"
            "CORRECT: 'MAIN_ANSWER: I cannot call the classify_leaf_safe tool without a valid image. Please share an image for plant analysis.\nACTION_ITEMS: Upload plant image | Ask general plant question | Get care tips'\n"
            "="*80 + "\n"
        )

        # Simplified prompt structure to avoid overwhelming the LLM
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("system", "🔍 CURRENT REQUEST CONTEXT: {system_context}\n\n" + 
             "CRITICAL TOOL DECISION LOGIC:\n" +
             "• If system_context contains 'image_handle=' → CALL classify_leaf_safe tool with the image_handle\n" + 
             "• If system_context is empty or no 'image_handle=' → NO TOOLS, respond conversationally\n\n" +
             "DEBUG INFO: system_context = '{system_context}'"),
            ("system", "CONVERSATION STATE: {conversation_summary}"),
            ("system", "TOOL GUIDANCE: {tool_guidance}"),
            ("system", "AVAILABLE RESULTS: {available_results}"),
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
            ("system", "RESPONSE FORMAT REMINDER: Start with MAIN_ANSWER: then ACTION_ITEMS:"),
            ("human", "{input}"),
        ])

        llm = create_llm()
        self.llm = llm
        
        # Use ReAct agent for Ollama models, tool_calling_agent for OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and ChatOpenAI is not None:
            logger.info("🤖 Using OpenAI with tool_calling_agent")
            agent = create_tool_calling_agent(llm, tools, prompt)
        else:
            logger.info("🦙 Using Ollama with custom hybrid agent (optimized for both cases)")
            # Create a hybrid agent that handles both image and no-image scenarios efficiently
            agent = self._create_hybrid_agent(llm, tools, system, format_enforcement)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "5")),
            return_intermediate_steps=True,
            handle_parsing_errors=True,  # Allow parsing errors to be passed back to agent
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

    def _create_react_prompt(self, system: str):
        """Create a ReAct-compatible prompt for Ollama models."""
        from langchain_core.prompts import PromptTemplate
        
        # Create a simple, focused ReAct prompt without format conflicts
        react_template = PromptTemplate(
            input_variables=["input", "system_context", "tool_guidance", "conversation_summary", "available_results", "tools", "tool_names", "agent_scratchpad"],
            template=(
                "You are a helpful plant diagnostics assistant.\n\n"
                "🔍 SYSTEM CONTEXT: {system_context}\n"
                "📋 GUIDANCE: {tool_guidance}\n\n"
                "💬 CONVERSATION STATE: {conversation_summary}\n"
                "📊 AVAILABLE PREVIOUS RESULTS: {available_results}\n\n"
                "DECISION LOGIC:\n"
                "• If system_context contains 'image_handle=' → Use classify_leaf_safe tool\n"
                "• If system_context is empty → NO tools, answer conversationally using previous results\n\n"
                "AVAILABLE TOOLS:\n{tools}\n"
                "TOOL NAMES: {tool_names}\n\n"
                "FORMAT REQUIREMENT:\n\n"
                "CASE 1 - WITH IMAGE (system_context has 'image_handle='):\n"
                "Question: the input question\n"
                "Thought: I see an image_handle, so I'll use the tool\n"
                "Action: classify_leaf_safe\n"
                "Action Input: {{\"image_handle\": \"handle_from_context\", \"text\": \"user's question\"}}\n"
                "Observation: [tool result]\n"
                "Thought: Now I can provide the diagnosis\n"
                "Final Answer: [analysis based on tool result]\n\n"
                "CASE 2 - NO IMAGE (system_context is empty):\n"
                "Question: How do I fertilize my plants?\n"
                "Thought: No image provided, I'll answer conversationally using plant knowledge\n"
                "Final Answer: For most plants, fertilize during growing season with balanced fertilizer. Apply every 4-6 weeks in spring/summer. Check soil first - over-fertilizing can harm plants.\n\n"
                "CRITICAL: When system_context is empty, NEVER use Action/Action Input - go straight to Final Answer!\n\n"
                "Begin!\n\n"
                "Question: {input}\n"
                "Thought:{agent_scratchpad}"
            )
        )
        
        return react_template

    def _create_hybrid_agent(self, llm, tools, system: str, format_enforcement: str):
        """Create a custom hybrid agent using a much simpler, more direct approach."""
        
        # For now, let's fall back to an improved ReAct agent with very strict instructions
        # to avoid format confusion, and implement a pre-check for no-image scenarios
        
        logger.info("🔧 Creating optimized ReAct agent with pre-filtering")
        
        # Create a simplified React prompt that's less likely to confuse the model
        from langchain_core.prompts import PromptTemplate
        simplified_react_prompt = PromptTemplate(
            input_variables=["input", "system_context", "tool_guidance", "conversation_summary", "available_results", "tools", "tool_names", "agent_scratchpad"],
            template=(
                "You are a plant diagnostics assistant.\n\n"
                "🔍 CHECK: {system_context}\n"
                "📋 GUIDANCE: {tool_guidance}\n\n"
                "SIMPLE RULE:\n"
                "- Has 'image_handle=' in context? → Use classify_leaf_safe tool\n" 
                "- No 'image_handle='? → Just answer the question directly\n\n"
                "TOOLS: {tools}\n"
                "TOOL NAMES: {tool_names}\n\n"
                "EXAMPLES:\n\n"
                "WITH IMAGE:\n"
                "Question: Analyze this plant\n"
                "Thought: I see image_handle in context, using tool\n"
                "Action: classify_leaf_safe\n"
                "Action Input: {{\"image_handle\": \"abc123\"}}\n"
                "Observation: Plant is healthy\n"
                "Thought: Got the result\n"
                "Final Answer: Your plant looks healthy!\n\n"
                "NO IMAGE:\n"
                "Question: How do I water plants?\n" 
                "Thought: No image_handle, answering directly\n"
                "Final Answer: Water when soil feels dry, about 2-3 times per week.\n\n"
                "Question: {input}\n"
                "Thought:{agent_scratchpad}"
            )
        )
        
        return create_react_agent(llm, tools, simplified_react_prompt)

    async def _handle_conversational_question(self, inputs: Dict, session_id: str):
        """Handle conversational questions directly without ReAct format confusion."""
        
        user_input = inputs.get("input", "")
        system_context = inputs.get("system_context", "")
        
        logger.debug(f"Handling conversational question: '{user_input}'")
        
        # Get conversation history for context
        history = self.get_session_history(session_id)
        messages = getattr(history, 'messages', [])
        
        # Build context from recent conversation
        conversation_context = ""
        if messages:
            recent_messages = messages[-4:]  # Last 4 messages for context
            for msg in recent_messages:
                msg_type = getattr(msg, "type", "unknown")
                content = getattr(msg, "content", str(msg))[:100]
                conversation_context += f"{msg_type}: {content}\n"
        
        # Create a simple conversational prompt
        conversational_prompt = (
            "You are a helpful plant diagnostics assistant. Answer the user's question conversationally.\n\n"
            f"Recent conversation:\n{conversation_context}\n\n"
            f"User's question: {user_input}\n\n"
            "Provide a helpful response about plant care, watering, fertilizing, or related topics. "
            "Be concise but informative. If the question is empty or unclear, ask for clarification."
        )
        
        logger.debug(f"Using conversational prompt: {conversational_prompt[:200]}...")
        
        # Call LLM directly for conversational response
        try:
            response = await asyncio.to_thread(self.llm.invoke, conversational_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"✅ Direct conversational response: '{response_text[:150]}...'")
            
            return {
                "output": response_text,
                "intermediate_steps": []  # No intermediate steps for direct responses
            }
        except Exception as e:
            logger.error(f"Error in conversational response: {e}")
            return {
                "output": "I'd be happy to help with your plant care questions! Could you please rephrase your question?",
                "intermediate_steps": []
            }

    async def _handle_image_classification(self, inputs: Dict, session_id: str):
        """Handle image classification directly without ReAct format confusion."""
        
        user_input = inputs.get("input", "")
        system_context = inputs.get("system_context", "")
        
        logger.debug(f"Handling image classification: input='{user_input}', context='{system_context}'")
        
        # Extract image handle from system context
        import re
        handle_match = re.search(r'image_handle=([^,\s]+)', system_context)
        if not handle_match:
            return {
                "output": "ERROR: No valid image handle found in system context.",
                "intermediate_steps": []
            }
        
        image_handle = handle_match.group(1)
        logger.info(f"🔍 Extracted image handle: {image_handle}")
        
        # Call the image classification logic directly (same as in classify_leaf_safe tool)
        try:
            logger.info(f"🔧 Processing image classification for handle: {image_handle}")
            
            # Check if there are any images available at all
            if not self.image_store:
                return {
                    "output": "ERROR: No images are currently available for classification. Please ask the user to upload an image first.",
                    "intermediate_steps": []
                }
            
            # Check if the specific handle exists
            if image_handle not in self.image_store:
                return {
                    "output": f"ERROR: Image handle '{image_handle}' not found. Available handles: {list(self.image_store.keys())}. Please ask the user to upload a new image.",
                    "intermediate_steps": []
                }
            
            # If we get here, we have a valid image, so do the actual classification
            logger.info(f"✅ Starting image classification for handle: {image_handle}")
            
            # Call the image classification with async streaming delays
            image_b64 = self.image_store[image_handle]
            logger.debug(f"Image found, proceeding with async classification")
            emitter = self._image_emitters.get(image_handle) or self._emit_ctx.get()
            outputs = []
            
            # Stream chunks with proper async delays
            classification_result = await self._stream_image_classification(image_b64, user_input or "", emitter, outputs)
            logger.info(f"✅ Classification completed: {classification_result[:200]}...")
            
            # Create a proper agent result format
            return {
                "output": classification_result,
                "intermediate_steps": [
                    (f"Image classification completed for {image_handle}", classification_result)
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in direct image classification: {e}")
            return {
                "output": f"ERROR: Failed to classify image - {str(e)}",
                "intermediate_steps": []
            }

    async def _stream_image_classification(self, image_b64: str, user_input: str, emitter, outputs: list) -> str:
        """Handle image classification with proper async streaming delays."""
        import asyncio
        
        try:
            # Process image step by step with real async delays
            logger.info("🔄 Starting streaming image classification...")
            
            # Step 1: Image preprocessing
            chunk1 = "Resized image, normalizing and preprocessing..."
            outputs.append(chunk1)
            if emitter:
                emitter(chunk1)
            await asyncio.sleep(1.5)  # Non-blocking async delay
            
            # Step 2: Preparation
            chunk2 = "Preparing image for neural network analysis..."
            outputs.append(chunk2)
            if emitter:
                emitter(chunk2)
            await asyncio.sleep(1.0)  # Non-blocking async delay
            
            # Step 3: CNN inference start
            chunk3 = "Running CNN model inference..."
            outputs.append(chunk3)
            if emitter:
                emitter(chunk3)
            await asyncio.sleep(1.0)  # Non-blocking async delay
            
            # Step 4: Actual CNN prediction (synchronous operation)
            logger.info("🧠 Running actual CNN prediction...")
            prediction_chunks = []
            for chunk in self.model.predict_leaf_classification(image_b64, user_input):
                chunk_str = str(chunk).rstrip("\n")
                prediction_chunks.append(chunk_str)
            
            # Step 5: Analysis
            chunk4 = "Analyzing prediction results..."
            outputs.append(chunk4)
            if emitter:
                emitter(chunk4)
            await asyncio.sleep(1.0)  # Non-blocking async delay
            
            # Step 6: Finalization
            chunk5 = "Finalizing diagnosis..."
            outputs.append(chunk5)
            if emitter:
                emitter(chunk5)
            await asyncio.sleep(1.0)  # Non-blocking async delay
            
            # Step 7: Final result from CNN prediction
            if prediction_chunks:
                final_chunk = prediction_chunks[-1]  # Get the final diagnosis
            else:
                final_chunk = "Diagnosis Complete! Class: unknown | Health Status: unknown | Confidence: 0.0"
            
            outputs.append(final_chunk)
            if emitter:
                emitter(final_chunk)
            
            logger.info("✅ Streaming image classification completed")
            return "\n".join(outputs)
            
        except Exception as e:
            error_msg = f"ERROR: Streaming classification failed - {str(e)}"
            logger.error(f"❌ {error_msg}")
            outputs.append(error_msg)
            if emitter:
                emitter(error_msg)
            return "\n".join(outputs)

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
        
        # PRE-FILTER: Handle both scenarios directly to avoid ReAct format confusion entirely
        if not has_image:
            logger.info("🚀 Using direct conversational response (bypassing ReAct agent)")
            return await self._handle_conversational_question(inputs, session_id)
        else:
            logger.info("🔧 Using direct image classification (bypassing ReAct agent)")
            return await self._handle_image_classification(inputs, session_id)
        
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
        
        # Enhanced debug logging for tool calling issues
        logger.info(f"🚨 ENHANCED DEBUG - TOOL CALLING STATUS:")
        logger.info(f"   System context: '{system_context}'")
        logger.info(f"   Has image handle: {has_image}")
        logger.info(f"   Tool guidance sent to LLM: {tool_guidance}")
        logger.info(f"   Expected behavior: {'SHOULD call classify_leaf_safe' if has_image else 'NO tool calls expected'}")
        
        # Use the agent for image classification
        logger.debug("Using agent with conversation history preserved for image analysis")
        
        result = await asyncio.to_thread(self.agent_with_history.invoke, inputs, config={
            "callbacks": callbacks,
            "configurable": {"session_id": session_id}
        })

        # Debug the agent result to see if tool was called
        output_text = result.get("output", "") if isinstance(result, dict) else str(result)
        intermediate_steps = result.get("intermediate_steps", []) if isinstance(result, dict) else []
        
        logger.info(f"🚨 AGENT EXECUTION RESULT DEBUG:")
        logger.info(f"   Output text: '{output_text[:200]}...'")
        logger.info(f"   Intermediate steps count: {len(intermediate_steps)}")
        logger.info(f"   Tool was called: {len(intermediate_steps) > 0}")
        
        if intermediate_steps:
            for i, step in enumerate(intermediate_steps):
                logger.info(f"   Step {i+1}: {step}")
        else:
            logger.warning(f"   ⚠️  NO TOOL CALLS DETECTED - Expected classify_leaf_safe to be called!")
            
        return result

    def parse_structured_response(self, response_text: str) -> Dict[str, Union[str, List[str]]]:
        """Parse structured response into main answer and action items array."""
        logger.debug(f"Parsing structured response: {response_text}")
        
        # Initialize default values
        main_answer = ""
        action_items_str = ""
        
        try:
            # Look for MAIN_ANSWER section
            main_answer_match = re.search(r'MAIN_ANSWER:\s*(.*?)(?=ACTION_ITEMS:|$)', response_text, re.DOTALL | re.IGNORECASE)
            if main_answer_match:
                main_answer = main_answer_match.group(1).strip()
            
            # Look for ACTION_ITEMS section
            action_items_match = re.search(r'ACTION_ITEMS:\s*(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            if action_items_match:
                action_items_str = action_items_match.group(1).strip()
            
            # Fallback: if no structured format found, create one with intelligent action items
            if not main_answer and not action_items_str:
                main_answer = response_text.strip()
                action_items_str = self._generate_fallback_action_items(main_answer)
                logger.warning(f"No structured format found, created fallback format with action items: {action_items_str}")
            elif main_answer and not action_items_str:
                # Main answer found but no action items, generate fallback action items
                action_items_str = self._generate_fallback_action_items(main_answer)
                logger.warning(f"Found main answer but no action items, generated fallback: {action_items_str}")
            
        except Exception as e:
            logger.error(f"Error parsing structured response: {e}")
            main_answer = response_text.strip()
            action_items_str = self._generate_fallback_action_items(main_answer)
        
        # Convert pipe-separated string to array
        action_items_array = []
        if action_items_str:
            action_items_array = [item.strip() for item in action_items_str.split("|") if item.strip()]
        
        result = {
            "main_answer": main_answer,
            "action_items": action_items_array
        }
        
        logger.debug(f"Parsed response - Main: '{main_answer[:100]}...', Action Items: {action_items_array}")
        return result

    @staticmethod
    def _generate_fallback_action_items(main_answer: str) -> str:
        """Generate appropriate action items based on the main answer content."""
        action_items = []
        
        # Convert to lowercase for keyword matching
        content_lower = main_answer.lower()
        
        # Based on content, suggest relevant action items
        if any(keyword in content_lower for keyword in ['watering', 'water', 'irrigation']):
            action_items.append("Give me watering schedule")
        
        if any(keyword in content_lower for keyword in ['fertiliz', 'nutrien', 'feed']):
            action_items.append("Show fertilization procedure")
        
        if any(keyword in content_lower for keyword in ['disease', 'infection', 'fungal', 'bacterial', 'pest']):
            action_items.append("Send me prescription for this disease")
            action_items.append("Show treatment steps")
        
        if any(keyword in content_lower for keyword in ['care', 'maintain', 'schedule']):
            action_items.append("Create plant care schedule")
        
        if any(keyword in content_lower for keyword in ['prevent', 'avoid']):
            action_items.append("Explain prevention methods")
        
        if any(keyword in content_lower for keyword in ['soil', 'potting', 'repot']):
            action_items.append("Get soil recommendations")
        
        if any(keyword in content_lower for keyword in ['information', 'need', 'tell me', 'describe']):
            action_items.append("Provide more details")
            action_items.append("Ask specific question")
        
        # Always include these general options if no specific matches
        if not action_items:
            action_items = ["Ask follow-up question", "Get more plant care tips", "Upload new plant image"]
        else:
            # Add general backup options
            action_items.append("Ask follow-up question")
            action_items.append("Upload new plant image")
        
        return " | ".join(action_items)
    
    def force_structure_response(self, response_text: str) -> str:
        """Force any response into the required MAIN_ANSWER/ACTION_ITEMS structure."""
        # Check if response already has proper structure
        if "MAIN_ANSWER:" in response_text and "ACTION_ITEMS:" in response_text:
            return response_text
        
        logger.warning(f"Forcing structure on unstructured response: {response_text[:100]}...")
        
        # Extract the original response content
        main_content = response_text.strip()
        
        # Generate appropriate action items based on content
        action_items = self._generate_fallback_action_items(main_content)
        
        # Force the structured format
        structured_response = f"MAIN_ANSWER: {main_content}\nACTION_ITEMS: {action_items}"
        
        logger.info(f"Forced structure result: {structured_response[:200]}...")
        return structured_response

    async def summarize_response(self, final_text: str, session_id: str, user_text: Optional[str] = None):
        classification_history = self._get_classification_history(session_id)
        
        # Base prompt for plant expert assistant
        base_prompt = (
                "You are a plant expert assistant. Use all previous plant leaf classification results in this session (provided below) "
                "to answer the user's latest question. If an image is present, respond to the classification result as before. "
                "If the image is not present, use the classification history (shown as 'Previous Results') to answer. "
            "Always follow up with relevant action items.\n\n"
        )
        
        # Add user text prompt handling if provided
        if user_text and user_text.strip():
            base_prompt += (
                "IMPORTANT: The user has provided both an image AND a text prompt. You must:\n"
                "1. First analyze and explain the image classification results\n"
                "2. Then address the user's specific text prompt/question\n"
                "3. Provide a comprehensive response that covers both aspects\n"
                "4. Make sure your response is cohesive and addresses the user's text prompt in context of the plant analysis\n\n"
                f"USER'S SPECIFIC QUESTION/PROMPT: '{user_text}'\n\n"
                "Your response should acknowledge both the image classification AND answer their specific question.\n\n"
            )
        
        prompt = (
                base_prompt +
                "="*80 + "\n"
                + "🚨🚨🚨 ABSOLUTE MANDATORY RESPONSE FORMAT 🚨🚨🚨\n"
                + "="*80 + "\n"
                + "YOUR RESPONSE MUST START WITH EXACTLY THESE WORDS:\n\n"
                + "MAIN_ANSWER: [complete response here]\n"
                + "ACTION_ITEMS: [actions separated by |]\n\n"
                + "EXAMPLE CORRECT RESPONSE:\n"
                + "MAIN_ANSWER: Based on the image classification, your plant shows signs of powdery mildew. Regarding your question about watering frequency, this fungal disease is often caused by overwatering combined with poor air circulation. I recommend reducing watering to twice weekly and improving ventilation.\n"
                + "ACTION_ITEMS: Adjust watering schedule | Improve air circulation | Apply fungicide treatment | Monitor plant progress\n\n"
                + "NEVER START WITH PLAIN TEXT! ALWAYS START WITH 'MAIN_ANSWER:'\n"
                + "="*80 + "\n\n"
                + "Previous Results:\n" +
                str(classification_history) + "\n"
                + "Latest Classification:\n" +
                str(final_text) + "\n\n"
        )
        
        # Add user text context if provided
        if user_text and user_text.strip():
            prompt += f"User's Additional Question: {user_text}\n\n"
            
        prompt += (
                "="*80 + "\n"
                + "REMEMBER: Start your response with 'MAIN_ANSWER:' followed by 'ACTION_ITEMS:'"
                + "\n" + "="*80
        )
        out = await asyncio.to_thread(self.llm.invoke, prompt)
        try:
            return out.content
        except Exception:
            return str(out)