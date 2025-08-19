from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio


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
        async def predict(request: PredictRequest):
            async def streamer():
                for out in self.model.predict_leaf_classification(request.image_b64, request.text):
                    yield out.encode("utf-8")
                    await asyncio.sleep(0)
            return StreamingResponse(streamer(), media_type="text/plain")

        @self.app.get("/hello")
        async def hello():
            async def hello_generator():
                while True:
                    yield b"Hello World\n"
                    await asyncio.sleep(2)
            return StreamingResponse(hello_generator(), media_type="text/plain")

# Main entrypoint
classifier_api = LeafClassifierAPI()
app = classifier_api.app  # Expose FastAPI app for uvicorn

if __name__ == "__main__":
    import uvicorn
    # TODO replace with real host name and port
    uvicorn.run(app, host="127.0.0.1", port=8080)
