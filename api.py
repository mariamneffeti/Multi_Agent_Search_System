"""
FastAPI server exposing the multi-agent research system as a chatbot API.

Endpoints:
  GET  /                  → serves static/index.html
  GET  /history           → serves static/history.html
  GET  /about             → serves static/about.html
  POST /research          → runs the research graph, streams progress + final report
  GET  /api/health        → health check

Run:
    uvicorn api:app --reload --port 8000
"""
import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
load_dotenv()

app = FastAPI(title="Multi-Agent Research System", version = "1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static",StaticFiles(directory= STATIC_DIR),name = "static")

# request/ response models

class ResearchRequest(BaseModel):
    query: str
    parallel: bool = False

#page routes
@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")
@app.get("/history")
async def history_page():
    return FileResponse(STATIC_DIR / "history.html")
@app.get("/about")
async def about_page():
    return FileResponse(STATIC_DIR / "about.html")

#Health check

@app.get("/api/health")
async def health():
    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    return {
        "status": "ok",
        "groq_key": groq_ok,
        "tavily_key": tavily_ok,
    }

# Research endpoint ( SSE stream)

def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"



async def run_research_stream(query: str, parallel: bool) -> AsyncGenerator[str, None]:
    """
    Runs the research graph in a thread and streams progress events back
    as Server-Sent Events so the UI can show live status updates.
    """
    from state import ResearchState

    yield _sse("status", {"message": "🔍 Decomposing your query into subtasks…", "step": 1})
    await asyncio.sleep(0.1)

    loop = asyncio.get_event_loop()

    # Import graph lazily (avoids slow startup)
    def _load_graph():
        if parallel:
            from parallel_graph import parallel_research_graph as g
        else:
            from graph import research_graph as g
        return g

    graph = await loop.run_in_executor(None, _load_graph)

    # Step 1: run orchestrator to get subtasks
    initial_state = ResearchState(query=query)

    # We run the full graph in a thread so we don't block the event loop
    result_holder = {}
    error_holder = {}

    # Stream intermediate status while graph runs
    async def _run():
        def _invoke():
            try:
                result_holder["result"] = graph.invoke(initial_state)
            except Exception as exc:
                error_holder["error"] = str(exc)

        await loop.run_in_executor(None, _invoke)

    task = asyncio.create_task(_run())

    steps = [
        (3,  "🕵️ Research agents gathering sources…",   2),
        (8,  "🧠 Analysis agent synthesising findings…", 3),
        (13, "🔎 Critique agent reviewing analysis…",    4),
        (18, "✍️  Synthesiser writing final report…",    5),
    ]

    for delay, message, step in steps:
        await asyncio.sleep(delay)
        if task.done():
            break
        yield _sse("status", {"message": message, "step": step})

    await task  # wait for completion

    if "error" in error_holder:
        yield _sse("error", {"message": error_holder["error"]})
        return

    result = result_holder.get("result", {})
    report = result.get("final_report", "[no report generated]")
    flags  = result.get("critique_flags", [])
    citations = result.get("citations", [])
    subtasks  = result.get("subtasks", [])

    yield _sse("done", {
        "report": report,
        "flags": flags,
        "citations": citations,
        "subtasks": subtasks,
    })


@app.post("/research")
async def research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    return StreamingResponse(
        run_research_stream(req.query.strip(), req.parallel),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

