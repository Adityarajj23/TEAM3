"""EchoBox Defect Reproduction, Remediation, and Retest Suite.

Tests DEF-ECHO-LIVE-001:
- Unremediated behavior: non-string room_id causes AttributeError in lambda_function.py, crashing with HTTP 500.
- Remediated behavior: explicit isinstance(room_id, str) check rejects non-string types with HTTP 400 Bad Request.
- Regression suite: valid string room IDs continue to function as expected.
"""
from __future__ import annotations

import json

import pytest
from echobox_harness.backend import EchoBoxBackend
from echobox_harness.table import InMemoryTable


class PatchedEchoBoxBackend(EchoBoxBackend):
    """Remediated EchoBox backend applying the recommended fix for DEF-ECHO-LIVE-001."""

    def get_room(self, body):
        room_id = body.get("room_id")
        # Fix for DEF-ECHO-LIVE-001: Validate that room_id is explicitly a non-empty string
        if not room_id or not isinstance(room_id, str) or not room_id.strip():
            from echobox_harness.backend import _response
            return _response(400, {"error": "room_id must be a non-empty string"})
        return super().get_room(body)

    def submit_feedback(self, body, user=None):
        room_id = body.get("room_id")
        # Fix for DEF-ECHO-LIVE-001: Validate that room_id is explicitly a non-empty string
        if not room_id or not isinstance(room_id, str) or not room_id.strip():
            from echobox_harness.backend import _response
            return _response(400, {"error": "room_id must be a non-empty string"})
        return super().submit_feedback(body, user)


@pytest.fixture
def unpatched_backend():
    return EchoBoxBackend(table=InMemoryTable())


@pytest.fixture
def patched_backend():
    return PatchedEchoBoxBackend(table=InMemoryTable())


def test_unremediated_non_string_room_id_causes_crash(unpatched_backend):
    """Proves DEF-ECHO-LIVE-001: unpatched handler crashes with AttributeError when room_id is integer."""
    with pytest.raises(AttributeError):
        # In unpatched backend, 12345 passes 'if not room_id' and crashes on room_id.strip()
        unpatched_backend.get_room({"action": "get_room", "room_id": 12345})


def test_remediated_non_string_room_id_returns_400(patched_backend):
    """Proves remediation: patched handler returns HTTP 400 Bad Request for integer room_id."""
    res = patched_backend.get_room({"action": "get_room", "room_id": 12345})
    assert res["statusCode"] == 400
    data = json.loads(res["body"])
    assert "room_id must be a non-empty string" in data["error"]


def test_remediated_boolean_room_id_returns_400(patched_backend):
    """Proves remediation: patched handler returns HTTP 400 Bad Request for boolean room_id."""
    res = patched_backend.get_room({"action": "get_room", "room_id": True})
    assert res["statusCode"] == 400
    data = json.loads(res["body"])
    assert "room_id must be a non-empty string" in data["error"]


def test_retest_regression_valid_room_works(patched_backend):
    """Proves regression safety: valid string room IDs continue to operate correctly."""
    # 1. Create a room
    c_res = patched_backend.create_room({
        "action": "create_room",
        "room_name": "Regression Room",
        "room_description": "Verifying regression pass",
        "visibility": "public"
    })
    assert c_res["statusCode"] == 201
    room_id = json.loads(c_res["body"])["room_id"]

    # 2. Get the room with valid string ID
    g_res = patched_backend.get_room({"action": "get_room", "room_id": room_id})
    assert g_res["statusCode"] == 200
    room_data = json.loads(g_res["body"])["room"]
    assert room_data["room_name"] == "Regression Room"

    # 3. Submit feedback with valid string ID
    f_res = patched_backend.submit_feedback({
        "action": "submit_feedback",
        "room_id": room_id,
        "message": "Regression feedback message"
    })
    assert f_res["statusCode"] in (200, 201)
