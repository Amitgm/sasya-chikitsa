import os
import asyncio
from typing import Optional, Dict, Callable
from contextvars import ContextVar
from dotenv import load_dotenv


from pydantic import BaseModel

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from engine.ml.cnn_with_attention_classifier import CNNWithAttentionClassifier


try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:
    print("Exception for ChatOpenAI")  # pragma: no cover
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
    api_key = os.getenv("OPENAI_API_KEY")
    if ChatOpenAI is not None and api_key:
        # Choose a small, cost-effective model by default
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.2)
    if ChatOllama is not None and (ollama_host or os.path.exists("/usr/local/bin/ollama")):
        if ollama_host:
            return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"), temperature=0.2, base_url=ollama_host)
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"), temperature=0.2)
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

    def _get_session_history(self, session_id: str) -> ChatMessageHistory:
        if session_id not in self.session_store:
            self.session_store[session_id] = ChatMessageHistory()
        return self.session_store[session_id]

    def _build_agent(self) -> RunnableWithMessageHistory:
        @tool("classify_leaf", return_direct=True)
        def classify_leaf(image_handle: str, text: Optional[str] = None) -> str:
            """Classify a plant leaf image. Provide image_handle received from the system context, and optional text."""
            image_b64 = self.image_store.get(image_handle)
            if not image_b64:
                return "No image found for provided handle."

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

        tools = [classify_leaf]

        system = (
            "You are a helpful plant diagnostics assistant. "
            "Hold a helpful, concise conversation. "
            "When the user wants to analyze a leaf image, call the `classify_leaf` tool. "
            "Use the image_handle provided in the system context if present."
            "Summarize the results of the classification and send a simple response."
            "Ask relevant follow up question."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system + "\nSystem context: {system_context}"),
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
            return self._get_session_history(sid)

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
        return "\n".join(results)

    async def invoke_agent(self, inputs: Dict, session_id: str, callbacks: Optional[list] = None):
        return await asyncio.to_thread(self.agent_with_history.invoke,
                                       inputs,
                                       config={
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