"""Regression tests for P1-1 to P1-4: execution fidelity (moto DynamoDB), defect derivation,
provenance (origin, commit, confidence), and AI provider honesty & secret redaction."""
from __future__ import annotations

import json
import time

import pytest

from app.core.config import REPO_ROOT


def test_real_echobox_lambda_runs_under_moto():
    from echobox_harness.backend import RealLambdaBackend

    backend = RealLambdaBackend(repo_dir=REPO_ROOT / "var" / "repos" / "sohan10012_EchoBox")
    # Verify public discovery returns valid response
    disc_res = backend.dispatch({"body": json.dumps({"action": "discover_rooms"})})
    assert disc_res["statusCode"] == 200
    disc_body = json.loads(disc_res["body"])
    assert "rooms" in disc_body
    assert disc_body["count"] == 0

    # Verify public room creation works against moto DynamoDB
    create_res = backend.dispatch({
        "body": json.dumps({
            "action": "create_room",
            "room_name": "Moto Architecture Space",
            "room_description": "Verification of real lambda under moto DynamoDB mock",
            "visibility": "public"
        })
    })
    assert create_res["statusCode"] == 201
    create_body = json.loads(create_res["body"])
    assert len(create_body["room_id"]) == 8
    assert create_body["room_name"] == "Moto Architecture Space"

    # Stop moto mock cleanly
    backend.stop()


@pytest.mark.xfail(
    strict=True,
    reason="DEF-ECHO-006: EchoBox lambda_function.py decodes JWT payload without cryptographic signature verification"
)
def test_real_echobox_authenticator_rejects_forged_signature():
    """Verify that EchoBox's real authenticate_request in lambda_function.py fails to reject forged signatures."""
    from echobox_harness.backend import RealLambdaBackend
    from test_echobox_jwt_security import create_mock_jwt

    backend = RealLambdaBackend(repo_dir=REPO_ROOT / "var" / "repos" / "sohan10012_EchoBox")
    try:
        forged_token = create_mock_jwt(
            payload={
                "sub": "victim-user-uuid-9999",
                "iss": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_NfCww8cVp",
                "exp": int(time.time()) + 3600,
                "cognito:username": "victim_admin",
            },
            signature="FORGED_INVALID_SIGNATURE_ATTACK"
        )
        headers = {"Authorization": f"Bearer {forged_token}"}
        caller = backend.lambda_mod.authenticate_request(headers, {})

        # A secure implementation MUST return None for a forged signature.
        # In EchoBox, this assertion FAILS because the real lambda_function.py decodes without verifying signature!
        assert caller is None, "Vulnerability DEF-ECHO-006 confirmed: authenticate_request accepted forged signature!"
    finally:
        backend.stop()


def test_defect_creation_tracks_evidence_type_and_artifact(app):
    from app.db.base import session_scope
    from app.db.models import Defect, Project
    from app.services.defects import create_manual

    with session_scope() as db:
        proj = db.query(Project).filter_by(key="ECHO").first() or db.query(Project).first()
        assert proj is not None

        defect_data = {
            "title": "Unverified JWT signature in lambda_function.py",
            "description": "Token is decoded without signature validation against Cognito JWKS",
            "severity": "critical",
            "priority": "p1",
            "evidence_type": "static_analysis",
            "source_commit_sha": "7d036b3",
            "expected_result": "Signature must be validated against Cognito JWKS",
            "actual_result": "Claims parsed directly with base64.urlsafe_b64decode",
        }
        d = create_manual(db, proj.id, proj.key, defect_data, actor_id=proj.owner_id)
        db.commit()

        # Query back and verify persisted evidence_type
        saved = db.get(Defect, d.id)
        assert saved.evidence_type == "static_analysis"
        assert saved.source_commit_sha == "7d036b3"
        assert saved.severity == "critical"


def test_requirement_provenance_and_inferred_needs_confirmation(app):
    from app.db.base import session_scope
    from app.db.models import Project, Requirement
    from app.services.requirements import create_requirement

    with session_scope() as db:
        proj = db.query(Project).filter_by(key="ECHO").first() or db.query(Project).first()
        assert proj is not None
        req = create_requirement(
            db,
            proj,
            title="Inferred Room Expiration Policy",
            description="All public rooms must expire after exactly 24 hours (86400 seconds) from creation epoch.",
            origin="inferred_from_code",
            source_commit_sha="7d036b3",
            confidence=0.95,
        )
        db.commit()

        saved = db.get(Requirement, req.id)
        assert saved.origin == "inferred_from_code"
        assert saved.source_commit_sha == "7d036b3"
        assert saved.confidence == 0.95
        assert saved.status == "needs_confirmation"


def test_source_code_secrets_redacted_before_llm():
    from app.llm.router import redact_secrets

    dummy_groq = "gsk_" + "1234567890abcdef1234567890abcdef1234567890abcdef"
    sensitive_prompt = (
        "Analyze this code:\n"
        "AWS_KEY = 'AKIA1234567890ABCDEF'\n"
        "TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz0123456789'\n"
        f"GROQ = '{dummy_groq}'\n"
    )
    redacted = redact_secrets(sensitive_prompt)
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in redacted
    assert dummy_groq not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_llm_slot_pool_cooldown_on_429_and_retirement_on_401():
    from app.llm.providers import SlotPool

    keys = ["key-slot-1", "key-slot-2", "key-slot-3"]
    pool = SlotPool(keys, "groq")
    assert pool.configured()

    candidates = pool.get_candidate_slots()
    assert len(candidates) == 3

    # Simulate HTTP 429 Rate Limit on slot 1 -> enters cooldown
    s1 = candidates[0]
    pool.record_failure(s1, is_rate_limit=True, retry_after=60.0)
    assert s1.state == "rate_limited"

    # Candidates should now exclude slot 1
    candidates_after_429 = pool.get_candidate_slots()
    assert len(candidates_after_429) == 2
    assert s1 not in candidates_after_429

    # Simulate HTTP 401 Auth Error on slot 2 -> marked invalid permanently
    s2 = candidates_after_429[0]
    pool.record_failure(s2, is_auth=True)
    assert s2.state == "invalid"

    # Only slot 3 remains healthy
    candidates_final = pool.get_candidate_slots()
    assert len(candidates_final) == 1
    assert candidates_final[0].slot_id == 3
