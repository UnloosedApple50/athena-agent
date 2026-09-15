"""Tests for the WebSocket handler."""

from __future__ import annotations

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from athena.server.websocket import ConnectionManager, WebSocketHandler
from athena.core.agent import AthenaAgent, ChatResponse
from unittest.mock import MagicMock, AsyncMock


class TestConnectionManager:
    """Tests for the WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test accepting a WebSocket connection."""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws, "conn_1")
        
        assert "conn_1" in manager._active_connections
        assert manager.connection_count == 1
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnecting a WebSocket."""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws, "conn_1")
        manager.disconnect("conn_1")
        
        assert "conn_1" not in manager._active_connections
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_send_message(self) -> None:
        """Test sending a message to a connection."""
        manager = ConnectionManager()
        mock_ws = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws, "conn_1")
        result = await manager.send_message("conn_1", {"type": "test"})
        
        assert result is True
        mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_to_disconnected(self) -> None:
        """Test sending a message to a disconnected client."""
        manager = ConnectionManager()
        result = await manager.send_message("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        """Test broadcasting to all connections."""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect(mock_ws1, "conn_1")
        await manager.connect(mock_ws2, "conn_2")
        
        await manager.broadcast({"type": "broadcast"})
        
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed(self) -> None:
        """Test that broadcast removes connections that fail."""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws2.send_text.side_effect = Exception("Connection lost")
        
        await manager.connect(mock_ws1, "conn_1")
        await manager.connect(mock_ws2, "conn_2")
        
        await manager.broadcast({"type": "broadcast"})
        
        assert "conn_1" in manager._active_connections
        assert "conn_2" not in manager._active_connections
