"""WebSocket handler for real-time updates."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from athena.core.agent import AthenaAgent, ChatResponse
from athena.utils.logger import get_logger
from athena.monitor.system import system_monitor
from athena.monitor.metrics import metrics_tracker

log = get_logger("websocket")


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        self._active_connections: dict[str, WebSocket] = {}
        self._session_map: dict[str, str] = {}  # session_id -> connection_id

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self._active_connections[connection_id] = websocket
        log.info(f"WebSocket connected: {connection_id} (total: {len(self._active_connections)})")

    def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        if connection_id in self._active_connections:
            del self._active_connections[connection_id]
        # Clean up session mapping
        for sid, cid in list(self._session_map.items()):
            if cid == connection_id:
                del self._session_map[sid]
        log.info(f"WebSocket disconnected: {connection_id}")

    async def send_message(self, connection_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific connection."""
        if connection_id not in self._active_connections:
            return False

        websocket = self._active_connections[connection_id]
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            log.warning(f"Failed to send to {connection_id}: {e}")
            self.disconnect(connection_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        disconnected: list[str] = []
        for conn_id, websocket in self._active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception:
                disconnected.append(conn_id)

        for conn_id in disconnected:
            self.disconnect(conn_id)

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._active_connections)


class WebSocketHandler:
    """Handles WebSocket message routing."""

    def __init__(self, agent: AthenaAgent, manager: ConnectionManager) -> None:
        self._agent = agent
        self._manager = manager
        self._broadcast_task: Optional[asyncio.Task[None]] = None

    async def handle(self, websocket: WebSocket, connection_id: str) -> None:
        """Main WebSocket handling loop."""
        await self._manager.connect(websocket, connection_id)

        # Start broadcast task if not running
        if self._broadcast_task is None:
            self._broadcast_task = asyncio.create_task(self._broadcast_metrics())

        try:
            # Send welcome message
            await self._manager.send_message(connection_id, {
                "type": "connected",
                "payload": {
                    "connection_id": connection_id,
                    "message": "Connected to Athena Agent v2.0",
                    "timestamp": time.time(),
                }
            })

            while True:
                # Receive message
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                msg_type = data.get("type", "unknown")
                payload = data.get("payload", {})

                log.debug(f"WebSocket message [{msg_type}] from {connection_id}")

                # Route by message type
                if msg_type == "chat":
                    await self._handle_chat(connection_id, payload)
                elif msg_type == "ping":
                    await self._manager.send_message(connection_id, {
                        "type": "pong",
                        "payload": {"timestamp": time.time()},
                    })
                elif msg_type == "health":
                    await self._handle_health(connection_id)
                elif msg_type == "get_metrics":
                    await self._handle_get_metrics(connection_id)
                elif msg_type == "get_system_metrics":
                    await self._handle_get_system_metrics(connection_id)
                else:
                    await self._manager.send_message(connection_id, {
                        "type": "error",
                        "payload": {"message": f"Unknown message type: {msg_type}"},
                    })

        except WebSocketDisconnect:
            self._manager.disconnect(connection_id)
        except Exception as e:
            log.error(f"WebSocket error for {connection_id}: {e}")
            self._manager.disconnect(connection_id)

    async def _handle_chat(self, connection_id: str, payload: dict[str, Any]) -> None:
        """Handle chat message over WebSocket."""
        message = payload.get("message", "")
        module = payload.get("module", "general")
        session_id = payload.get("session_id")

        if not message:
            await self._manager.send_message(connection_id, {
                "type": "error",
                "payload": {"message": "Empty message received"},
            })
            return

        # Send acknowledgment
        await self._manager.send_message(connection_id, {
            "type": "processing",
            "payload": {"message": "Analyzing your query..."},
        })

        # Get response from agent
        response = await self._agent.chat(
            message=message,
            module=module,
            session_id=session_id,
        )

        # Send response
        await self._manager.send_message(connection_id, {
            "type": "response",
            "payload": response.to_dict(),
        })

    async def _handle_health(self, connection_id: str) -> None:
        """Handle health check over WebSocket."""
        await self._manager.send_message(connection_id, {
            "type": "health",
            "payload": {
                "status": "healthy",
                "uptime_seconds": self._agent.uptime_seconds,
                "active_connections": self._manager.connection_count,
                "timestamp": time.time(),
            },
        })

    async def _handle_get_metrics(self, connection_id: str) -> None:
        """Handle token metrics request."""
        stats = metrics_tracker.get_stats()
        await self._manager.send_message(connection_id, {
            "type": "metrics",
            "payload": {
                "total_requests": stats.total_requests,
                "total_tokens": stats.total_prompt_tokens + stats.total_completion_tokens,
                "avg_tokens_per_second": round(stats.avg_tokens_per_second, 2),
                "avg_latency_ms": round(stats.avg_latency_ms, 2),
                "rolling_avg_tps": round(stats.rolling_avg_tps, 2),
            },
        })

    async def _handle_get_system_metrics(self, connection_id: str) -> None:
        """Handle system metrics request."""
        metrics = system_monitor.get_system_metrics()
        await self._manager.send_message(connection_id, {
            "type": "system_metrics",
            "payload": metrics.to_dict(),
        })

    async def _broadcast_metrics(self) -> None:
        """Periodically broadcast system metrics to all clients."""
        while True:
            await asyncio.sleep(5)  # Broadcast every 5 seconds
            if self._manager.connection_count > 0:
                try:
                    metrics = system_monitor.get_system_metrics()
                    throughput = metrics_tracker.get_stats()
                    await self._manager.broadcast({
                        "type": "realtime_metrics",
                        "payload": {
                            "cpu_percent": metrics.cpu.overall_percent,
                            "memory_percent": metrics.ram.percent_used,
                            "network_rx_bytes": metrics.network.bytes_received,
                            "network_tx_bytes": metrics.network.bytes_sent,
                            "tokens_per_second": throughput.rolling_avg_tps,
                            "active_connections": self._manager.connection_count,
                            "timestamp": time.time(),
                        },
                    })
                except Exception as e:
                    log.warning(f"Broadcast error: {e}")


# Global connection manager
ws_manager = ConnectionManager()
