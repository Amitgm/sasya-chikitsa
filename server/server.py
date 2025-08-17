from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import uvicorn

app = FastAPI()

# Example streaming function - replace with your ML code as needed
async def predict_leaf_classification(image_bytes, text=None):
    for step in range(1, 4):
        await asyncio.sleep(1)  # Simulate processing time
        yield f"Step {step}: Intermediate output\n"
    yield "Prediction: Banana leaf detected\n"

# Streaming generator for FastAPI
async def stream_prediction(image: UploadFile, text: Optional[str]):
    image_bytes = await image.read()  # Read image file
    async for intermediate in predict_leaf_classification(image_bytes, text):
        yield intermediate.encode("utf-8")

@app.post("/predict-leaf-classification")
async def predict(
    image: UploadFile = File(..., description="Image file (binary)"),
    text: Optional[str] = Form(None, description="Optional text info")
):
    return StreamingResponse(
        stream_prediction(image, text),
        media_type="text/plain"
    )

async def hello_generator():
    while True:
        yield b"Hello World\n"
        await asyncio.sleep(2)

@app.get("/hello")
async def hello():
    return StreamingResponse(hello_generator(), media_type="text/plain")

if __name__ == "__main__":
    # Start the FastAPI server at localhost:8080
    uvicorn.run(app, host="127.0.0.1", port=8080)
