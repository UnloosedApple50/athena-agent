"""Extended tests for server endpoints and integrations."""

from __future__ import annotations

import pytest
from athena.server.api import create_app


class TestSystemMetricsEndpoint:
    """Test system metrics endpoints."""

    def test_system_metrics(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "ram" in data

    def test_system_info(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/system/info")
        assert response.status_code == 200


class TestThroughputEndpoint:
    """Test throughput metrics endpoints."""

    def test_throughput_metrics(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/metrics/throughput")
        assert response.status_code == 200

    def test_throughput_history(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/metrics/throughput/history")
        assert response.status_code == 200


class TestIntegrationsEndpoints:
    """Test integrations endpoints."""

    def test_list_integrations(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/integrations")
        assert response.status_code == 200

    def test_list_webhooks(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/integrations/webhooks")
        assert response.status_code == 200

    def test_register_webhook(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/integrations/webhooks", json={
            "url": "https://example.com/webhook",
            "events": ["chat.created"],
        })
        assert response.status_code == 200

    def test_delete_webhook(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.delete("/api/v1/integrations/webhooks/nonexistent")
        assert response.status_code == 404

    def test_generate_api_key(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/integrations/api-keys", json={
            "name": "test-key",
            "scopes": ["chat"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "key" in data

    def test_revoke_api_key(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.delete("/api/v1/integrations/api-keys/nonexistent")
        assert response.status_code == 404

    def test_list_connectors(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/integrations")
        assert response.status_code == 200


class TestTrainingEndpoints:
    """Test training endpoints."""

    def test_submit_feedback(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/training/feedback", json={
            "memory_id": 1,
            "rating": 4,
            "correction": "Better response",
        })
        assert response.status_code == 200

    def test_get_training_history(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/training/history")
        assert response.status_code == 200

    def test_get_training_stats(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/training/stats")
        assert response.status_code == 200

    def test_trigger_adaptation(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/training/adapt")
        assert response.status_code == 200

    def test_replay_session(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/training/replay/test_session")
        assert response.status_code == 200


class TestSettingsEndpoint:
    """Test settings endpoint."""

    def test_get_settings(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert "llm_base_url" in data


class TestConnectService:
    """Test service connection endpoint."""

    def test_connect_slack(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/integrations/slack/connect", json={
            "bot_token": "xoxb-test",
        })
        assert response.status_code == 200

    def test_connect_discord(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/integrations/discord/connect", json={
            "bot_token": "test-token",
        })
        assert response.status_code == 200

    def test_connect_telegram(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.post("/api/v1/integrations/telegram/connect", json={
            "bot_token": "123456",
        })
        assert response.status_code == 200

    def test_disconnect_service(self):
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)
        
        response = client.delete("/api/v1/integrations/slack")
        assert response.status_code in (200, 404)
