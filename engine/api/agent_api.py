import asyncio
import uuid

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from engine.api.agent_core import AgentCore, ChatRequest

class AgentAPI:
    def __init__(self, agent_core: AgentCore):
        self.app = FastAPI()
        self.agent_core = agent_core
        self._add_routes()

    def _add_routes(self):
        @self.app.post("/chat")
        async def chat(req: ChatRequest):
            system_context = ""
            if req.image_b64:
                handle = str(uuid.uuid4())
                self.agent_core.image_store[handle] = req.image_b64
                system_context = f"image_handle={handle}"

            inputs = {"input": req.message, "system_context": system_context}

            result = await self.agent_core.invoke_agent(inputs, req.session_id or "default")
            final_text = result.get("output") if isinstance(result, dict) else str(result)
            summary = await self.agent_core.summarize_response(final_text, req.session_id or "default")
            return {"reply": summary}

        @self.app.post("/chat-stream")
        async def chat_stream(req: ChatRequest, request: Request, format: Optional[str] = Query(None)):
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
                loop.call_soon_threadsafe(queue.put_nowait, wrap(text))

            try:
                from langchain_core.callbacks.base import BaseCallbackHandler
            except Exception:
                BaseCallbackHandler = object

            class QueueCallbackHandler(BaseCallbackHandler):
                def on_llm_new_token(self, token: str, **kwargs) -> None:
                    emit(token)

            system_context = ""
            handle: Optional[str] = None
            if req.image_b64:
                handle = str(uuid.uuid4())
                self.agent_core.image_store[handle] = req.image_b64
                system_context = f"image_handle={handle}"

            inputs = {"input": req.message, "system_context": system_context}

            async def run_agent():
                token = self.agent_core._emit_ctx.set(emit)
                if handle:
                    self.agent_core._image_emitters[handle] = emit
                try:
                    result = await self.agent_core.invoke_agent(
                        inputs,
                        req.session_id or "default",
                        callbacks=[QueueCallbackHandler()]
                    )
                    final_text = result.get("output") if isinstance(result, dict) else str(result)
                    summary = await self.agent_core.summarize_response(final_text, req.session_id or "default")
                    emit(summary)
                finally:
                    self.agent_core._emit_ctx.reset(token)
                    if handle and handle in self.agent_core._image_emitters:
                        try:
                            del self.agent_core._image_emitters[handle]
                        except Exception:
                            pass
                if media_type == "text/event-stream":
                    emit("[DONE]")

            async def streamer():
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
    agent_core_instance = AgentCore()
    api_server = AgentAPI(agent_core_instance)
    uvicorn.run(api_server.app, host="127.0.0.1", port=8080)