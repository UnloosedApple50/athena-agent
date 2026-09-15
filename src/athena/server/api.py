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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from athena.db.database import Database, db
from athena.db.migrations import init_schema, seed_knowledge
from athena.models.llm import llm_client
from athena.models.config import get_settings
from athena.server.websocket import ws_manager, WebSocketHandler
from athena.utils.logger import get_logger
from athena.utils.security import sanitize_input, validate_module, generate_session_id

# Import new modules
from athena.monitor.system import system_monitor
from athena.monitor.metrics import metrics_tracker
from athena.integrations.webhooks import webhook_manager
from athena.integrations.api_keys import api_key_manager
from athena.integrations.connectors import connector_manager
from athena.integrations.oauth import oauth_manager
from athena.training.feedback import feedback_manager
from athena.training.replay import replay_manager
from athena.training.adaptation import adaptation_manager

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
    version: str = "2.0.0"


class SettingsResponse(BaseModel):
    llm_base_url: str
    llm_model: str
    host: str
    port: int
    log_level: str


# === New Request Models ===

class WebhookRequest(BaseModel):
    url: str = Field(..., description="Webhook endpoint URL")
    events: list[str] = Field(..., description="Events to subscribe to")


class APIKeyRequest(BaseModel):
    name: str = Field(..., description="Key name")
    scopes: list[str] = Field(..., description="Permission scopes")
    rate_limit: int = Field(100, description="Requests per minute")


class TrainingFeedbackRequest(BaseModel):
    memory_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    correction: Optional[str] = None
    comment: Optional[str] = None
    category: str = "general"


class ConnectorRequest(BaseModel):
    webhook_url: Optional[str] = None
    bot_token: Optional[str] = None
    channel_id: Optional[str] = None
    api_key: Optional[str] = None


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


# === New Endpoints: System Metrics ===

@router.get("/system/metrics")
async def get_system_metrics():
    """Get real-time system metrics (CPU, RAM, disk, network)."""
    metrics = system_monitor.get_system_metrics()
    return metrics.to_dict()


@router.get("/system/info")
async def get_system_info():
    """Get system information."""
    metrics = system_monitor.get_system_metrics()
    return {
        "platform": metrics.platform_info,
        "uptime_seconds": metrics.uptime_seconds,
        "process_count": metrics.process_count,
    }


# === New Endpoints: Token Throughput ===

@router.get("/metrics/throughput")
async def get_throughput_metrics():
    """Get token throughput metrics."""
    return metrics_tracker.to_dict()


@router.get("/metrics/throughput/history")
async def get_throughput_history(hours: int = 24):
    """Get historical throughput metrics."""
    return await metrics_tracker.get_historical_stats(hours=hours)


# === New Endpoints: Integrations ===

@router.get("/integrations")
async def list_integrations():
    """List all configured integrations."""
    webhooks = await webhook_manager.list_webhooks()
    api_keys = await api_key_manager.list_keys()
    connectors = connector_manager.list_connectors()
    
    return {
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events,
                "active": w.active,
                "created_at": w.created_at,
            }
            for w in webhooks
        ],
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "prefix": k.key_prefix,
                "scopes": k.scopes,
                "active": k.active,
                "created_at": k.created_at,
            }
            for k in api_keys
        ],
        "connectors": connectors,
    }


@router.get("/integrations/webhooks")
async def list_webhooks():
    """List registered webhooks."""
    webhooks = await webhook_manager.list_webhooks()
    return [
        {
            "id": w.id,
            "url": w.url,
            "events": w.events,
            "active": w.active,
            "created_at": w.created_at,
        }
        for w in webhooks
    ]


@router.post("/integrations/webhooks")
async def register_webhook(body: WebhookRequest):
    """Register a new webhook."""
    try:
        webhook = await webhook_manager.register(url=body.url, events=body.events)
        return {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events,
            "secret": webhook.secret,
            "status": "registered",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/integrations/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Remove a webhook."""
    success = await webhook_manager.unregister(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted"}


@router.post("/integrations/api-keys")
async def generate_api_key(body: APIKeyRequest):
    """Generate a new API key."""
    try:
        full_key, api_key = await api_key_manager.create_key(
            name=body.name,
            scopes=body.scopes,
            rate_limit=body.rate_limit,
        )
        return {
            "key": full_key,
            "id": api_key.id,
            "name": api_key.name,
            "prefix": api_key.key_prefix,
            "scopes": api_key.scopes,
            "created_at": api_key.created_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/integrations/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    success = await api_key_manager.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}


@router.post("/integrations/{service}/connect")
async def connect_service(service: str, body: ConnectorRequest):
    """Connect an external service."""
    from athena.integrations.connectors import ConnectorConfig
    
    try:
        config = ConnectorConfig(
            service=service,
            webhook_url=body.webhook_url or "",
            bot_token=body.bot_token or "",
            channel_id=body.channel_id or "",
        )
        connector = connector_manager.create_connector(config)
        return {"service": service, "status": "connected"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/integrations/{service}")
async def disconnect_service(service: str):
    """Disconnect an external service."""
    success = connector_manager.remove_connector(service)
    if not success:
        raise HTTPException(status_code=404, detail="Service not connected")
    return {"status": "disconnected"}


# === New Endpoints: Training ===

@router.post("/training/feedback")
async def submit_training_feedback(body: TrainingFeedbackRequest):
    """Submit feedback on a response."""
    entry = await feedback_manager.submit_feedback(
        memory_id=body.memory_id,
        rating=body.rating,
        correction=body.correction,
        comment=body.comment,
        category=body.category,
    )
    return entry.to_dict()


@router.get("/training/history")
async def get_training_history(
    session_id: Optional[str] = None,
    module: Optional[str] = None,
    limit: int = 50,
):
    """Get feedback history."""
    return await feedback_manager.get_feedback_history(session_id, module, limit)


@router.get("/training/stats")
async def get_training_stats():
    """Get training statistics."""
    return await feedback_manager.get_feedback_stats()


@router.post("/training/adapt")
async def trigger_adaptation():
    """Trigger adaptation based on feedback."""
    # Get all feedback
    feedback = await feedback_manager.get_feedback_history(limit=1000)
    
    # Analyze and generate rules
    rules = await adaptation_manager.analyze_feedback(feedback)
    
    # Apply adaptations
    result = await adaptation_manager.apply_adaptations()
    
    return {
        "rules_generated": len(rules),
        "adaptations": result,
        "stats": adaptation_manager.get_stats(),
    }


@router.post("/training/replay/{session_id}")
async def replay_session(session_id: str):
    """Replay a session's interactions."""
    results = await replay_manager.replay_session(session_id)
    return {
        "session_id": session_id,
        "replayed": len(results),
        "improved": sum(1 for r in results if r.improved),
    }


# === Settings Endpoint ===

@router.get("/settings")
async def get_settings_endpoint():
    """Get current settings."""
    from athena.models.config import get_settings as get_config_settings
    settings = get_config_settings()
    return SettingsResponse(
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


# === Application Factory ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global start_time

    settings = get_settings()
    logger.info("Starting Athena Agent v2.0...")

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

    # Set database for managers
    metrics_tracker._db = db
    webhook_manager._db = db
    api_key_manager._db = db
    oauth_manager._db = db
    feedback_manager._db = db
    replay_manager._db = db
    adaptation_manager._db = db

    logger.info(f"Athena Agent ready on port {settings.port}")

    yield

    # Shutdown
    logger.info("Shutting down Athena Agent...")
    await llm_client.close()
    await db.close()
    await webhook_manager.close()
    await connector_manager.close_all()


# Mount static files and templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Athena Agent",
        description="Specialized Language Memory Agent for Sales & Trading",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
