import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models.event import Event
from backend.models.alert import Alert


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


def test_cameras_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/cameras")
        assert response.status_code == 200
        cameras = response.json()
        assert isinstance(cameras, list)
        assert len(cameras) >= 2


def test_zones_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/zones")
        assert response.status_code == 200
        zones = response.json()
        assert isinstance(zones, list)
        assert len(zones) >= 1


def test_post_event_and_alert_generation():
    evt_id = f"EVT-TEST-{int(datetime.now().timestamp() * 1000)}"
    payload = {
        "event_id": evt_id,
        "event_type": "intrusion",
        "camera_id": "CAM-001",
        "entity_id": "PERSON-99",
        "severity": "HIGH",
        "confidence": 0.96,
        "zone_id": "ZONE-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "NEW",
        "metadata": {"model": "YOLOv8", "test_run": True}
    }

    with TestClient(app) as client:
        # Connect to websocket to test live broadcast
        with client.websocket_connect("/ws/events") as websocket:
            # POST event
            resp = client.post("/api/v1/events", json=payload)
            assert resp.status_code == 201
            data = resp.json()
            assert data["event_id"] == evt_id
            assert data["severity"] == "HIGH"

            # Check websocket received the broadcast
            ws_msg = websocket.receive_json()
            assert ws_msg["type"] == "NEW_EVENT"
            assert ws_msg["event"]["event_id"] == evt_id
            assert ws_msg["event"]["severity"] == "HIGH"

        # Verify event persisted in events table
        get_resp = client.get("/api/v1/events?camera_id=CAM-001")
        assert get_resp.status_code == 200
        events = get_resp.json()
        assert any(e["event_id"] == evt_id for e in events)

        # Verify alert auto-generated in alerts table
        alerts_resp = client.get("/api/v1/alerts")
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()
        assert any(a["event_id"] == evt_id for a in alerts)


