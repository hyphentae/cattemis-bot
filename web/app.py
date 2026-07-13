from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def create_app() -> FastAPI:
    app = FastAPI(title="Cattemis Web UI")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "bot": "cattemis :3"}

    class ChatRequest(BaseModel):
        message: str
        history: list = []

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        try:
            from cattemis_bot.llm import ask_llm
            from cattemis_bot.config import Config
            cfg = Config()

            messages = req.history + [{"role": "user", "content": req.message}]

            async def stream():
                full = ""
                async for chunk in ask_llm(cfg, messages):
                    full += chunk
                    yield json.dumps({"chunk": chunk}) + "\n"
                yield json.dumps({"done": True, "full": full}) + "\n"

            return StreamingResponse(stream(), media_type="application/x-ndjson")
        except Exception as e:
            return {"error": str(e)}

    return app
