"""FastAPI backend for EBM 5A Web UI.

Endpoints:
  POST /api/sessions          Register a question, get session_id
  GET  /api/run?session_id=X  SSE stream of workflow progress events
  GET  /api/health            Health check
"""

import asyncio
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.main import create_workflow
from web.backend.instrumented_coordinator import InstrumentedCoordinator
from web.backend.event_types import SSEEvent, EventType
from web.backend import log_capture as _lc

import os

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

app = FastAPI(title="TrueTruth Clinical Decision Support", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool — keep max_workers=1 to avoid LLM API rate-limit contention
_executor = ThreadPoolExecutor(max_workers=1)

# In-memory session store  { session_id: question }
_sessions: dict = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SessionRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/sessions")
async def create_session(req: SessionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    sid = str(uuid.uuid4())
    _sessions[sid] = req.question.strip()
    return {"session_id": sid}


@app.get("/api/run")
async def run_workflow_sse(request: Request, session_id: str):
    question = _sessions.pop(session_id, None)
    if question is None:
        raise HTTPException(
            status_code=404, detail="session_id not found or already consumed"
        )

    loop = asyncio.get_event_loop()
    event_queue: asyncio.Queue = asyncio.Queue()
    cancel_flag = threading.Event()
    SENTINEL = object()

    async def event_generator() -> AsyncGenerator[str, None]:
        async def _heartbeat():
            while True:
                await asyncio.sleep(25)
                hb = SSEEvent(
                    event=EventType.HEARTBEAT,
                    data={"ts": datetime.now(timezone.utc).isoformat()},
                )
                await event_queue.put(hb)

        async def _watch_disconnect():
            while True:
                await asyncio.sleep(2)
                if await request.is_disconnected():
                    cancel_flag.set()
                    await event_queue.put(SENTINEL)
                    return

        hb_task = asyncio.create_task(_heartbeat())
        dc_task = asyncio.create_task(_watch_disconnect())
        try:
            while True:
                item = await event_queue.get()
                if item is SENTINEL:
                    break
                if isinstance(item, SSEEvent):
                    yield item.to_sse_string()
        finally:
            hb_task.cancel()
            dc_task.cancel()

    def run_in_thread():
        # Register log callback for this thread
        def log_callback(line: str, agent: str):
            evt = SSEEvent(
                event=EventType.AGENT_LOG,
                data={
                    "agent": agent,
                    "line": line,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            asyncio.run_coroutine_threadsafe(event_queue.put(evt), loop)

        _lc.register_thread_callback(log_callback)
        try:
            base = create_workflow()
            coordinator = InstrumentedCoordinator(
                agents=base.agents,
                judge_llm=base.judge_llm,
                scheduling_llm=base.scheduling_llm,
                event_queue=event_queue,
                loop=loop,
                cancel_flag=cancel_flag,
            )
            coordinator.execute_workflow(question)
        except Exception as e:
            err_evt = SSEEvent(
                event=EventType.WORKFLOW_ERROR,
                data={
                    "error": str(e),
                    "traceback": traceback.format_exc()[:3000],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            asyncio.run_coroutine_threadsafe(event_queue.put(err_evt), loop)
        finally:
            _lc.unregister_thread_callback()
            asyncio.run_coroutine_threadsafe(event_queue.put(SENTINEL), loop)

    loop.run_in_executor(_executor, run_in_thread)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Serve built frontend (production mode)
# ---------------------------------------------------------------------------
_frontend_dist = os.path.join(_PROJECT_ROOT, "web", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
