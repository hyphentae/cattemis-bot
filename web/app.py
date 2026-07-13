from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import os
import sys
import time

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

    @app.get("/api/stats")
    async def stats():
        try:
            from cattemis_bot.state import state
            uptime = time.time() - state.started_at
            return {
                "uptime_seconds": int(uptime),
                "messages_total": state.messages_total,
                "commands_used": state.commands_used,
                "llm_calls": state.llm_calls,
                "llm_errors": state.llm_errors,
                "media_total": state.media_total,
                "media_errors": state.media_errors,
                "tiktok_downloads": state.tiktok_downloads,
                "instagram_downloads": state.instagram_downloads,
                "twitter_downloads": state.twitter_downloads,
                "direct_image_downloads": state.direct_image_downloads,
                "ytdlp_downloads": state.ytdlp_downloads,
                "unique_chats": len(state.unique_chats),
                "bot_username": state.bot_username,
                "bot_id": state.bot_id,
            }
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/chats")
    async def chats():
        try:
            from cattemis_bot.state import state
            result = []
            for chat_id, history in state.chat_histories.items():
                result.append({
                    "chat_id": chat_id,
                    "message_count": len(history),
                    "last_role": history[-1]["role"] if history else None,
                    "last_preview": (history[-1]["content"][:80] + "...") if history and len(history[-1]["content"]) > 80 else (history[-1]["content"] if history else ""),
                })
            return {"chats": result, "total": len(result)}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/chats/{chat_id}")
    async def chat_history(chat_id: int):
        try:
            from cattemis_bot.state import state
            history = state.chat_histories.get(chat_id, [])
            return {"chat_id": chat_id, "history": history}
        except Exception as e:
            return {"error": str(e)}

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
