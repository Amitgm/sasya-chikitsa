from fastapi import FastAPI, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import json

from ml.cnn_with_attention_classifier import CNNWithAttentionClassifier


class LeafClassifierAPI:
    def __init__(self):
        self.app = FastAPI()
        self.model = CNNWithAttentionClassifier()
        self.add_routes()

    def add_routes(self):

        class PredictRequest(BaseModel):
            image_b64: str
            text: Optional[str] = ""

        @self.app.post("/predict-leaf-classification")
        async def predict(body: PredictRequest, request: Request, format: Optional[str] = Query(None)):
            # Determine streaming format via explicit query param or Accept header
            accept_header = (format or request.headers.get("accept", "")).lower()

            if "text/event-stream" in accept_header or (format and format.lower() == "sse"):
                media_type = "text/event-stream"
                def transform(chunk: str) -> str:
                    return f"data: {chunk}\n\n"
                extra_headers = {
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            elif (
                "application/x-ndjson" in accept_header
                or "application/jsonl" in accept_header
                or (format and format.lower() in {"ndjson", "jsonl"})
                or "application/json" in accept_header  # fall back to json-lines for generic json
            ):
                media_type = "application/x-ndjson"
                def transform(chunk: str) -> str:
                    return json.dumps({"data": chunk}) + "\n"
                extra_headers = {}
            else:
                media_type = "text/plain"
                def transform(chunk: str) -> str:
                    return chunk if chunk.endswith("\n") else chunk + "\n"
                extra_headers = {}

            async def streamer():
                for out in self.model.predict_leaf_classification(body.image_b64, body.text):
                    yield transform(str(out)).encode("utf-8")
                    await asyncio.sleep(2)

            return StreamingResponse(streamer(), media_type=media_type, headers=extra_headers)


if __name__ == "__main__":
    import uvicorn
    # Main entrypoint
    classifier_api = LeafClassifierAPI()
    app = classifier_api.app  # Expose FastAPI app for uvicorn
    # TODO replace with real host name and port
    uvicorn.run(app, host="127.0.0.1", port=8080)
