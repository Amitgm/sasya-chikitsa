import os
import uuid
import asyncio
from typing import Optional, Dict, Callable
from contextvars import ContextVar
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse
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


class AgentServer:
    def __init__(self):
        load_dotenv()
        self.app = FastAPI()
        self.model = CNNWithAttentionClassifier()
        self.image_store: Dict[str, str] = {}
        self.session_store: Dict[str, ChatMessageHistory] = {}
        self.agent_with_history = self._build_agent()
        self._add_routes()
        # Context variable to carry a per-request streaming emitter into tool calls safely
        self._emit_ctx: ContextVar[Optional[Callable[[str], None]]] = ContextVar("emit_ctx", default=None)
        # Fallback map to find per-request emitter via image handle (works across threads)
        self._image_emitters: Dict[str, Callable[[str], None]] = {}

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

            # Stream intermediate chunks through per-request emitter if present
            # Prefer emitter mapped to this image handle (thread-safe),
            # fall back to ContextVar for cases without handle
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
            sid = cfg.get("configurable", {}).get("session_id", "default") if isinstance(cfg, dict) else "default"
            return self._get_session_history(sid)

        self.get_history = get_history  # Save as instance method!
        return RunnableWithMessageHistory(
            executor,
            get_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def _add_routes(self):
        @self.app.post("/chat")
        async def chat(req: ChatRequest):
            system_context = ""
            if req.image_b64:
                handle = str(uuid.uuid4())
                self.image_store[handle] = req.image_b64
                # Provide only the handle to the model to avoid large prompts
                system_context = f"image_handle={handle}"

            inputs = {"input": req.message, "system_context": system_context}

            # AgentExecutor is sync; run in thread to avoid blocking
            def _invoke():
                return self.agent_with_history.invoke(
                    inputs,
                    config={"configurable": {"session_id": req.session_id or "default"}},
                )

            result = await asyncio.to_thread(_invoke)
            # Summarize final output for the user
            final_text = result.get("output") if isinstance(result, dict) else str(result)

            def _summ():
                prompt = (
                    "Summarize the following leaf classification results concisely for the end user. "
                    "Respond with plain text only.\n\n" + str(final_text)
                )
                out = self.llm.invoke(prompt)
                try:
                    return out.content  # ChatModel
                except Exception:
                    return str(out)
            summary = await asyncio.to_thread(_summ)
            return {"reply": summary}

        @self.app.post("/chat-stream")
        async def chat_stream(req: ChatRequest, request: Request, format: Optional[str] = Query(None)):
            # Determine streaming format
            accept_header = (format or request.headers.get("accept", "")).lower()
            if "text/event-stream" in accept_header or (format and format.lower() == "sse"):
                media_type = "text/event-stream"
                def wrap(chunk: str) -> bytes:
                    return (f"data: {chunk}\n\n").encode("utf-8")
                extra_headers = {
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            else:
                media_type = "text/plain"
                def wrap(chunk: str) -> bytes:
                    if not chunk.endswith("\n"):
                        chunk_out = chunk + "\n"
                    else:
                        chunk_out = chunk
                    return chunk_out.encode("utf-8")
                extra_headers = {}

            queue: asyncio.Queue[bytes] = asyncio.Queue()
            loop = asyncio.get_event_loop()

            def emit(text: str) -> None:
                # Thread-safe enqueue for both sync and threaded callbacks
                loop.call_soon_threadsafe(queue.put_nowait, wrap(text))

            # Callback handler for LLM token streaming
            try:
                from langchain_core.callbacks.base import BaseCallbackHandler  # type: ignore
            except Exception:
                BaseCallbackHandler = object  # type: ignore

            class QueueCallbackHandler(BaseCallbackHandler):  # type: ignore
                def on_llm_new_token(self, token: str, **kwargs) -> None:  # type: ignore
                    emit(token)

            # Prepare system context and set per-request emitter
            system_context = ""
            handle: Optional[str] = None
            if req.image_b64:
                handle = str(uuid.uuid4())
                self.image_store[handle] = req.image_b64
                system_context = f"image_handle={handle}"

            inputs = {"input": req.message, "system_context": system_context}

            async def run_agent():
                token = self._emit_ctx.set(emit)
                # Register emitter for this image handle so the tool can find it across threads
                if handle:
                    self._image_emitters[handle] = emit
                try:
                    # Invoke with callbacks so LLM tokens stream
                    def _invoke():
                        return self.agent_with_history.invoke(
                            inputs,
                            config={
                                "callbacks": [QueueCallbackHandler()],
                                "configurable": {"session_id": req.session_id or "default"},
                            },
                        )
                    result = await asyncio.to_thread(_invoke)
                    # Summarize final output
                    final_text = result.get("output") if isinstance(result, dict) else str(result)

                    def _get_classification_history(self, session_id: str) -> str:
                        history = self.get_history({"configurable": {"session_id": session_id}})
                        results = []
                        for msg in getattr(history, 'messages', []):
                            if getattr(msg, "type", None) == "ai":
                                text = getattr(msg, "content", "") if hasattr(msg, "content") else str(msg)
                                results.append(text)
                        return "\n".join(results)

                    def _summ():
                        session_id = req.session_id or "default"
                        classification_history = _get_classification_history(self, session_id)
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
                        out = self.llm.invoke(prompt)
                        try:
                            return out.content
                        except Exception:
                            return str(out)
                    summary = await asyncio.to_thread(_summ)
                    emit(summary)
                finally:
                    self._emit_ctx.reset(token)
                    if handle and handle in self._image_emitters:
                        try:
                            del self._image_emitters[handle]
                        except Exception:
                            pass
                # Signal end for SSE consumers
                if media_type == "text/event-stream":
                    emit("[DONE]")

            async def streamer():
                # Run the agent concurrently
                task = asyncio.create_task(run_agent())
                try:
                    while True:
                        chunk = await queue.get()
                        yield chunk
                        queue.task_done()
                        if task.done() and queue.empty():
                            break
                finally:
                    if not task.done():
                        task.cancel()

            return StreamingResponse(streamer(), media_type=media_type, headers=extra_headers)


if __name__ == "__main__":
    server = AgentServer()
    uvicorn.run(server.app, host="127.0.0.1", port=8080)


