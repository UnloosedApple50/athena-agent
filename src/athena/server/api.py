"""FastAPI server with REST API and WebSocket endpoints."""

from __future__ import annotations

import asyncio
import time
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from athena.db.database import Database, db
from athena.db.migrations import init_schema, seed_knowledge
from athena.models.llm import llm_client
from athena.models.config import get_settings
from athena.server.websocket import ws_manager, WebSocketHandler
from athena.utils.logger import get_logger
from athena.utils.security import sanitize_input, validate_module, generate_session_id

logger = get_logger("server")

# Global state (initialized in lifespan)
start_time: float = 0


# === Request/Response Models ===

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    module: str = Field("general", description="Module context")
    session_id: Optional[str] = Field(None, description="Session ID for context")


class ChatResponseModel(BaseModel):
    response: str
    confidence: float
    module: str
    session_id: str
    memories_used: int
    fallback: bool
    timestamp: str


class DecisionRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=10000)
    options: list[str] = Field(..., min_length=2, max_length=10)
    module: str = Field("general")
    session_id: Optional[str] = None


class KnowledgeRequest(BaseModel):
    module: str
    category: str
    key: str
    value: str
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    tags: list[str] = []


class FeedbackRequest(BaseModel):
    outcome: str
    score: float = Field(..., ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    status: str
    llm_connected: bool
    db_connected: bool
    uptime_seconds: float
    memory_count: int
    version: str = "1.0.0"


# === Router for API v1 ===

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check endpoint."""
    agent = request.app.state.agent
    db_conn = request.app.state.db

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    return HealthResponse(
        status="healthy",
        llm_connected=llm_client.is_available,
        db_connected=db_conn.is_connected,
        uptime_seconds=agent.uptime_seconds,
        memory_count=await agent._memory.count_episodic(),
    )


@router.post("/chat", response_model=ChatResponseModel)
async def chat(request: Request, body: ChatRequest):
    """Send a message to the agent."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    try:
        response = await agent.chat(
            message=body.message,
            module=body.module,
            session_id=body.session_id,
        )
        return ChatResponseModel(**response.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.post("/decisions")
async def make_decision(request: Request, body: DecisionRequest):
    """Get a decision between options."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    try:
        decision = await agent.decide(
            context=body.context,
            options=body.options,
            module=body.module,
            session_id=body.session_id,
        )
        return decision.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Decision error: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.get("/memory/episodic")
async def get_episodic_memory(
    request: Request,
    session_id: Optional[str] = None,
    module: Optional[str] = None,
    limit: int = 50,
):
    """Retrieve episodic memories."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    memories = await agent._memory.get_episodic(session_id, module, limit)
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "module": m.module,
            "query": m.query,
            "response": m.response[:500],
            "confidence": m.confidence,
            "outcome": m.outcome,
            "created_at": m.created_at,
        }
        for m in memories
    ]


@router.get("/memory/semantic")
async def get_semantic_memory(
    request: Request,
    module: Optional[str] = None,
    category: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = 50,
):
    """Retrieve semantic memories."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    memories = await agent._memory.get_semantic(module, category, key, limit)
    return [
        {
            "id": m.id,
            "module": m.module,
            "category": m.category,
            "key": m.key,
            "value": m.value,
            "confidence": m.confidence,
            "tags": m.tags,
            "use_count": m.use_count,
        }
        for m in memories
    ]


@router.post("/memory/semantic")
async def add_knowledge(request: Request, body: KnowledgeRequest):
    """Add knowledge to semantic memory."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    try:
        memory_id = await agent.add_knowledge(
            module=body.module,
            category=body.category,
            key=body.key,
            value=body.value,
            confidence=body.confidence,
            tags=body.tags,
        )
        return {"id": memory_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/memory/{memory_id}")
async def delete_memory(request: Request, memory_id: int, memory_type: str = "episodic"):
    """Delete a memory by ID."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    if memory_type == "episodic":
        success = await agent._memory.delete_episodic(memory_id)
    elif memory_type == "semantic":
        success = await agent._memory.delete_semantic(memory_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid memory type")

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"status": "deleted"}


@router.get("/sessions/{session_id}")
async def get_session(request: Request, session_id: str):
    """Get session history."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    history = await agent.get_session_history(session_id)
    return [
        {
            "query": h.query,
            "response": h.response[:300],
            "confidence": h.confidence,
            "created_at": h.created_at,
        }
        for h in history
    ]


@router.post("/feedback/{memory_id}")
async def provide_feedback(request: Request, memory_id: int, body: FeedbackRequest):
    """Provide feedback on a past interaction."""
    agent = request.app.state.agent
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")

    await agent.provide_feedback(memory_id, body.outcome, body.score)
    return {"status": "received"}


# === Application Factory ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global start_time

    settings = get_settings()
    logger.info("Starting Athena Agent...")

    # Initialize database
    await db.initialize()
    await init_schema(db)
    await seed_knowledge(db)

    # Initialize LLM
    await llm_client.initialize()
    if llm_client.is_available:
        logger.info(f"LLM connected: {settings.llm_model} at {settings.llm_base_url}")
    else:
        logger.warning("LLM not available — using rule-based fallback")

    # Initialize components
    from athena.core.memory import MemoryManager
    from athena.core.retrieval import RetrievalEngine
    from athena.core.decision import DecisionEngine
    from athena.core.agent import AthenaAgent

    memory = MemoryManager(db)
    retrieval = RetrievalEngine(memory, llm_client)
    decision = DecisionEngine(memory, retrieval, llm_client)
    app.state.agent = AthenaAgent(memory, retrieval, decision, llm_client)
    app.state.db = db
    start_time = time.time()

    logger.info(f"Athena Agent ready on port {settings.port}")

    yield

    # Shutdown
    logger.info("Shutting down Athena Agent...")
    await llm_client.close()
    await db.close()


# Mount static files and templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Athena Agent",
        description="Specialized Language Memory Agent for Sales & Trading",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Include API router
    app.include_router(router)

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Serve the main dashboard."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time communication."""
        connection_id = generate_session_id()
        handler = WebSocketHandler(websocket.app.state.agent, ws_manager)
        await handler.handle(websocket, connection_id)

    return app


# Default app instance (for running with uvicorn)
app = create_app()
