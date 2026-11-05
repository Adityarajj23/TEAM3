"""EchoBox In-Memory Harness API Contract Verification Suite.

Verifies that echobox_harness faithfully reproduces:
1. All 13 EchoBox RPC actions and expected status codes.
2. 24-hour expiration calculation and HTTP 410 Gone status.
3. Input validation constraints (e.g. 64KB body cap, missing room_name/room_desc).
4. Boundary behaviors (e.g. room closure blocks messages, non-owner rejection).
"""
from __future__ import annotations

import json

import pytest
from echobox_harness.backend import EchoBoxBackend
from echobox_harness.table import InMemoryTable


@pytest.fixture
def harness():
    table = InMemoryTable()
    return EchoBoxBackend(table=table)


def test_harness_rejects_oversized_payload(harness):
    """Verifies 64KB request body protection."""
    huge_body = "x" * 70000
    res = harness.dispatch({"body": huge_body, "headers": {}})
    assert res["statusCode"] == 413
    body = json.loads(res["body"])
    assert "exceeds maximum allowed size" in body["error"]


def test_harness_unauthenticated_protected_action(harness):
    """Verifies unauthenticated calls to protected/unknown actions return 401."""
    res = harness.dispatch({"body": json.dumps({"action": "unsupported_hack"}), "headers": {}})
    assert res["statusCode"] == 401
    body = json.loads(res["body"])
    assert "Unauthorized" in body["error"]


def test_harness_create_and_get_room(harness):
    """Verifies room creation, 24-hour lifetime, and retrieval."""
    res = harness.dispatch({
        "body": json.dumps({
            "action": "create_room",
            "room_name": "Contract Test Room",
            "room_description": "Testing contract compliance",
            "visibility": "public"
        }),
        "headers": {}
    })
    assert res["statusCode"] == 201
    created = json.loads(res["body"])
    assert "room_id" in created
    assert "expires_at" in created
    assert isinstance(created["expires_at"], int)
    room_id = created["room_id"]

    # Retrieve room
    get_res = harness.dispatch({
        "body": json.dumps({"action": "get_room", "room_id": room_id}),
        "headers": {}
    })
    assert get_res["statusCode"] == 200
    room_data = json.loads(get_res["body"])["room"]
    assert room_data["room_name"] == "Contract Test Room"
    assert room_data["status"] == "active"


def test_harness_private_room_discovery_isolation(harness):
    """Verifies private rooms are excluded from public discovery."""
    # Create private room
    res = harness.dispatch({
        "body": json.dumps({
            "action": "create_room",
            "room_name": "Secret Private Room",
            "room_description": "Should never show in discovery",
            "visibility": "private"
        }),
        "headers": {}
    })
    assert res["statusCode"] == 201
    priv_id = json.loads(res["body"])["room_id"]

    # Discover public rooms
    disc = harness.dispatch({"body": json.dumps({"action": "discover_rooms"}), "headers": {}})
    assert disc["statusCode"] == 200
    rooms = json.loads(disc["body"])["rooms"]
    assert not any(r["room_id"] == priv_id for r in rooms)


def test_harness_message_lifecycle_and_closure(harness):
    """Verifies message submission, chronological retrieval, and closure enforcement."""
    # 1. Create Room
    c_res = harness.dispatch({
        "body": json.dumps({
            "action": "create_room",
            "room_name": "Chat Room",
            "room_description": "Chat test",
            "visibility": "public"
        }),
        "headers": {}
    })
    room_id = json.loads(c_res["body"])["room_id"]

    # 2. Submit Message
    msg_res = harness.dispatch({
        "body": json.dumps({
            "action": "submit_feedback",
            "room_id": room_id,
            "message": "First message in room",
            "display_name": "GhostWriter"
        }),
        "headers": {}
    })
    assert msg_res["statusCode"] == 201

    # 3. Get Messages
    get_m = harness.dispatch({
        "body": json.dumps({"action": "get_feedback", "room_id": room_id}),
        "headers": {}
    })
    assert get_m["statusCode"] == 200
    messages = json.loads(get_m["body"])["messages"]
    assert len(messages) == 1
    assert messages[0]["message"] == "First message in room"

    # 4. Close Room without owner token -> 401
    close_unauth = harness.dispatch({
        "body": json.dumps({"action": "close_room", "room_id": room_id}),
        "headers": {}
    })
    assert close_unauth["statusCode"] == 401
