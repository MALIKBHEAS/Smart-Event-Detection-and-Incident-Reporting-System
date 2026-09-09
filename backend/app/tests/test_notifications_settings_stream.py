from __future__ import annotations

import pytest
from app.db.session import SessionLocal
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture(autouse=True)
def _clean():
    def wipe():
        s = SessionLocal()
        for t in ("user_roles", "refresh_tokens", "users", "notifications"):
            s.execute(text(f"DELETE FROM {t}"))
        s.commit()
        s.close()

    wipe()
    yield
    wipe()


@pytest.fixture()
def auth_client():
    with TestClient(app) as client:
        client.post("/auth/register", json={"username": "admin", "email": "a@a.com", "password": "supersecret123"})
        login = client.post("/auth/login", json={"username": "admin", "password": "supersecret123"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        yield client, headers


def test_notifications_require_auth() -> None:
    with TestClient(app) as client:
        assert client.get("/notifications").status_code == 401


def test_list_notifications_empty(auth_client) -> None:
    client, headers = auth_client
    resp = client.get("/notifications", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["unread_count"] == 0


def test_mark_notification_read_and_read_all(auth_client) -> None:
    client, headers = auth_client
    from app.notifications.repository import NotificationRepository

    session = SessionLocal()
    n1 = NotificationRepository(session).create(type="new_event", message="Test event", severity="high")
    n1_id = n1.id
    n2 = NotificationRepository(session).create(type="new_incident", message="Test incident", severity="critical")
    _n2_id = n2.id
    session.close()

    resp = client.get("/notifications", headers=headers)
    assert resp.json()["unread_count"] == 2

    resp = client.put(f"/notifications/{n1_id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["read"] is True

    resp = client.get("/notifications", headers=headers)
    assert resp.json()["unread_count"] == 1

    resp = client.put("/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 1

    resp = client.get("/notifications", headers=headers)
    assert resp.json()["unread_count"] == 0


def test_mark_missing_notification_404(auth_client) -> None:
    client, headers = auth_client
    assert client.put("/notifications/999999/read", headers=headers).status_code == 404


def test_settings_get_and_update(auth_client) -> None:
    client, headers = auth_client
    resp = client.get("/settings", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["detection_confidence_threshold"] == pytest.approx(0.5)
    assert body["notify_on_new_event"] is True

    resp = client.put("/settings", json={"notify_on_new_event": False, "evidence_retention_days": 60}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notify_on_new_event"] is False
    assert resp.json()["evidence_retention_days"] == 60

    # persisted
    resp = client.get("/settings", headers=headers)
    assert resp.json()["notify_on_new_event"] is False
    # restore for other tests sharing dev.db
    client.put("/settings", json={"notify_on_new_event": True, "evidence_retention_days": 30}, headers=headers)


def test_settings_write_requires_admin(auth_client) -> None:
    client, headers = auth_client
    client.post(
        "/auth/register",
        json={"username": "viewer", "email": "v@v.com", "password": "supersecret123", "role": "Viewer"},
        headers=headers,
    )
    viewer_login = client.post("/auth/login", json={"username": "viewer", "password": "supersecret123"})
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

    assert client.get("/settings", headers=viewer_headers).status_code == 200
    assert client.put("/settings", json={"evidence_retention_days": 10}, headers=viewer_headers).status_code == 403


def test_stream_missing_camera_returns_404(auth_client) -> None:
    client, headers = auth_client
    resp = client.get("/cameras/999999/stream", headers=headers)
    assert resp.status_code == 404


def test_stream_requires_auth() -> None:
    with TestClient(app) as client:
        assert client.get("/cameras/1/stream").status_code == 401


def test_draw_detection_overlays_actually_modifies_pixels() -> None:
    import numpy as np
    from app.main import draw_detection_overlays
    from app.workers.tracker import Track

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    track = Track(track_id=7, bbox=(20.0, 20.0, 100.0, 100.0), class_name="person", score=0.91)

    annotated = draw_detection_overlays(frame, [track])

    assert not np.array_equal(frame, annotated), "overlay must actually change pixels"
    # A box was drawn somewhere inside the region we asked for -- the exact
    # border pixels depend on cv2's line rendering, so just assert *some*
    # non-zero (drawn) pixel exists in that area.
    region = annotated[15:105, 15:105]
    assert region.any()


def test_draw_detection_overlays_noop_when_no_tracks() -> None:
    import numpy as np
    from app.main import draw_detection_overlays

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = draw_detection_overlays(frame, [])
    assert result is frame
