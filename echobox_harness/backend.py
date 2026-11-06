"""EchoBox Backend Logic implementation for local test harness execution."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .table import InMemoryTable, get_default_table


def _response(status_code: int, body_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps(body_dict)
    }


def parse_jwt(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        decoded = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


class EchoBoxBackend:
    def __init__(self, table: InMemoryTable | None = None):
        self.table = table or get_default_table()

    def authenticate_request(self, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any] | None:
        auth_header = None
        for k, v in headers.items():
            if k.lower() == "authorization":
                auth_header = v
                break
        token = None
        if auth_header and auth_header.strip():
            parts = auth_header.strip().split(" ")
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
            elif len(parts) == 1:
                token = parts[0]
        if not token:
            token = body.get("auth_token") or body.get("token") or body.get("access_token")
        if not token:
            return None
        payload = parse_jwt(token)
        if not payload:
            return None
        sub = payload.get("sub")
        if not sub:
            return None
        return {
            "sub": str(sub),
            "username": payload.get("username", "") or payload.get("cognito:username", ""),
            "email": payload.get("email", ""),
            "name": payload.get("name", "") or payload.get("username", "")
        }

    def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        try:
            raw_body = event.get("body") or "{}"
            if isinstance(raw_body, str) and len(raw_body) > 65536:
                return _response(413, {"error": "Request body exceeds maximum allowed size (64KB)"})

            if isinstance(raw_body, dict):
                body = raw_body
            else:
                body = json.loads(raw_body)

            action = body.get("action")
            headers = event.get("headers") or {}

            # Public Actions
            if action == "get_room":
                return self.get_room(body)
            elif action in ("discover_rooms", "search_rooms"):
                return self.discover_rooms(body)
            elif action == "submit_feedback":
                user = self.authenticate_request(headers, body)
                return self.submit_feedback(body, user)
            elif action == "get_feedback":
                user = self.authenticate_request(headers, body)
                return self.get_feedback(body, user)
            elif action == "create_room":
                owner = self.authenticate_request(headers, body)
                return self.create_room(body, owner)
            elif action == "health_check":
                return _response(200, {"status": "healthy", "service": "echobox-backend"})

            # Authenticated Actions
            caller = self.authenticate_request(headers, body)
            if not caller:
                return _response(401, {"error": "Unauthorized: Valid EchoBox credentials or session token required"})

            if action == "get_my_posts":
                return self.get_my_posts(body, caller)
            elif action == "delete_my_post":
                return self.delete_my_post(body, caller)
            elif action == "get_owner_rooms":
                return self.get_owner_rooms(body, caller)
            elif action == "delete_feedback":
                return self.delete_feedback(body, caller)
            elif action == "close_room":
                return self.close_room(body, caller)
            elif action == "reopen_room":
                return self.reopen_room(body, caller)
            elif action == "claim_legacy_room":
                return self.claim_legacy_room(body, caller)
            else:
                return _response(400, {"error": f"Invalid action: {action}"})

        except json.JSONDecodeError:
            return _response(400, {"error": "Invalid JSON request body"})
        except Exception as e:
            return _response(500, {"error": f"Internal server error: {str(e)}"})

    def create_room(self, body: dict[str, Any], owner: dict[str, Any] | None = None) -> dict[str, Any]:
        room_name = (body.get("room_name") or "").strip()
        if not room_name:
            return _response(400, {"error": "Room name is required"})

        room_desc = (body.get("room_description") or "").strip()
        if not room_desc:
            return _response(400, {"error": "Room description or discussion prompt is required"})

        visibility = (body.get("visibility") or "public").strip().lower()
        # Note: EchoBox defect DEF-ECHO-003: Invalid visibility falls back to "public" silently
        if visibility not in ("public", "private"):
            visibility = "public"

        # Note: EchoBox defect DEF-ECHO-002: Slicing rather than returning 400
        # Note: EchoBox defect DEF-ECHO-001: Description sliced to 1000 chars despite 500 doc limit
        clean_name = room_name[:100]
        clean_desc = room_desc[:1000]
        room_id = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        now_epoch = int(now.timestamp())
        expires_at = now_epoch + 86400

        owner_id = owner["sub"] if owner else f"anon_{uuid.uuid4().hex[:8]}"
        owner_email = owner.get("email", "") if owner else ""
        owner_username = owner.get("username", "") if owner else ""

        room_item = {
            "PK": f"ROOM#{room_id}",
            "SK": "METADATA",
            "room_id": room_id,
            "room_name": clean_name,
            "room_description": clean_desc,
            "visibility": visibility,
            "owner_id": owner_id,
            "owner_email": owner_email,
            "owner_username": owner_username,
            "created_at": now_iso,
            "expires_at": expires_at,
            "status": "active"
        }
        self.table.put_item(Item=room_item)

        if owner:
            owner_item = {
                "PK": f"OWNER#{owner_id}",
                "SK": f"ROOM#{room_id}",
                "room_id": room_id,
                "owner_id": owner_id,
                "room_name": clean_name,
                "room_description": clean_desc,
                "visibility": visibility,
                "created_at": now_iso,
                "expires_at": expires_at,
                "status": "active"
            }
            self.table.put_item(Item=owner_item)

        if visibility == "public":
            discovery_item = {
                "PK": "DISCOVERY#PUBLIC",
                "SK": f"ROOM#{room_id}",
                "room_id": room_id,
                "room_name": clean_name,
                "room_description": clean_desc,
                "visibility": "public",
                "created_at": now_iso,
                "expires_at": expires_at,
                "status": "active"
            }
            self.table.put_item(Item=discovery_item)

        return _response(201, {
            "message": "Room created successfully",
            "room_id": room_id,
            "room_name": clean_name,
            "room_description": clean_desc,
            "visibility": visibility,
            "created_at": now_iso,
            "expires_at": expires_at,
            "status": "active"
        })

    def get_room(self, body: dict[str, Any]) -> dict[str, Any]:
        room_id = body.get("room_id")
        if not room_id:
            return _response(400, {"error": "room_id is required"})

        clean_id = room_id.strip()
        res = self.table.get_item(Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"})
        room = res.get("Item")
        if not room:
            return _response(404, {"error": "Room not found"})

        now_epoch = int(datetime.now(timezone.utc).timestamp())
        expires_at = int(room.get("expires_at", 0))

        if expires_at and now_epoch >= expires_at:
            room["status"] = "expired"
            room["is_expired"] = True
        else:
            room["is_expired"] = False

        count_res = self.table.query(
            KeyConditionExpression=f"Key('PK').eq('ROOM#{clean_id}') & Key('SK').begins_with('FEEDBACK#')",
            Select="COUNT"
        )
        room["message_count"] = count_res.get("Count", 0)
        return _response(200, {"room": room})

    def discover_rooms(self, body: dict[str, Any]) -> dict[str, Any]:
        search_query = (body.get("search") or body.get("q") or "").strip().lower()
        now_epoch = int(datetime.now(timezone.utc).timestamp())

        res = self.table.query(KeyConditionExpression="Key('PK').eq('DISCOVERY#PUBLIC')", ScanIndexForward=False)
        items = res.get("Items", [])

        public_rooms = []
        for item in items:
            exp = int(item.get("expires_at", 0))
            status = item.get("status", "active")
            if (exp and now_epoch >= exp) or status in ("expired", "closed"):
                continue

            name = item.get("room_name", "")
            desc = item.get("room_description", "")
            if search_query and (search_query not in name.lower() and search_query not in desc.lower()):
                continue

            room_id = item.get("room_id")
            # Note: EchoBox defect DEF-ECHO-004: N+1 query per room
            count_res = self.table.query(
                KeyConditionExpression=f"Key('PK').eq('ROOM#{room_id}') & Key('SK').begins_with('FEEDBACK#')",
                Select="COUNT"
            )
            msg_count = count_res.get("Count", 0)

            public_rooms.append({
                "room_id": room_id,
                "room_name": name,
                "room_description": desc,
                "visibility": "public",
                "status": status,
                "created_at": item.get("created_at"),
                "expires_at": exp,
                "message_count": msg_count,
                "feedback_count": msg_count
            })

        return _response(200, {"rooms": public_rooms, "count": len(public_rooms)})

    def submit_feedback(self, body: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
        room_id = body.get("room_id")
        message = body.get("message")
        display_name = body.get("display_name")
        anonymous_session_id = body.get("anonymous_session_id")

        if not room_id or not isinstance(message, str) or not message.strip():
            return _response(400, {"error": "room_id and message are required"})

        clean_id = room_id.strip()
        clean_msg = message.strip()
        if len(clean_msg) > 2000:
            return _response(400, {"error": "Message must be under 2000 characters"})

        res = self.table.get_item(Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"})
        room = res.get("Item")
        if not room:
            return _response(404, {"error": "Room not found"})

        now_epoch = int(datetime.now(timezone.utc).timestamp())
        expires_at = int(room.get("expires_at", 0))

        if expires_at and now_epoch >= expires_at:
            return _response(410, {"error": "This room has expired (24-hour limit reached) and is no longer accepting messages."})

        if room.get("status") == "closed":
            return _response(403, {"error": "This room has been closed by its owner."})

        clean_name = (display_name or "Anonymous").strip()[:50]
        clean_sess = (anonymous_session_id or f"sess_{uuid.uuid4().hex[:12]}").strip()[:64]
        feedback_id = uuid.uuid4().hex[:12]
        now_iso = datetime.now(timezone.utc).isoformat()

        author_id = user["sub"] if user else None
        echobox_id = user.get("username") if user else None

        feedback_item = {
            "PK": f"ROOM#{clean_id}",
            "SK": f"FEEDBACK#{feedback_id}",
            "feedback_id": feedback_id,
            "message": clean_msg,
            "created_at": now_iso,
            "display_name": clean_name,
            "anonymous_session_id": clean_sess,
            "expires_at": expires_at,
            "author_id": author_id,
            "echobox_id": echobox_id
        }
        self.table.put_item(Item=feedback_item)

        if author_id:
            post_index_item = {
                "PK": f"USERPOSTS#{author_id}",
                "SK": f"MSG#{clean_id}#{feedback_id}",
                "feedback_id": feedback_id,
                "room_id": clean_id,
                "room_name": room.get("room_name", "Untitled Space"),
                "message": clean_msg,
                "display_name": clean_name,
                "created_at": now_iso,
                "expires_at": expires_at,
                "status": "active"
            }
            self.table.put_item(Item=post_index_item)

        return _response(201, {
            "message": "Feedback submitted successfully",
            "feedback_id": feedback_id,
            "display_name": clean_name,
            "created_at": now_iso
        })

    def get_feedback(self, body: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
        room_id = body.get("room_id")
        if not room_id:
            return _response(400, {"error": "room_id is required"})

        clean_id = room_id.strip()
        res = self.table.query(
            KeyConditionExpression=f"Key('PK').eq('ROOM#{clean_id}') & Key('SK').begins_with('FEEDBACK#')",
            ScanIndexForward=True
        )
        items = res.get("Items", [])
        return _response(200, {
            "messages": items,
            "feedbacks": items,
            "count": len(items)
        })

    def close_room(self, body: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        room_id = body.get("room_id")
        if not room_id:
            return _response(400, {"error": "room_id is required"})

        clean_id = room_id.strip()
        res = self.table.get_item(Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"})
        room = res.get("Item")
        if not room:
            return _response(404, {"error": "Room not found"})

        owner_id = owner["sub"]
        if room.get("owner_id") and room.get("owner_id") != owner_id:
            return _response(403, {"error": "Forbidden: You do not own this room."})

        self.table.update_item(
            Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "closed"}
        )
        return _response(200, {"message": "Room closed successfully", "room_id": clean_id, "status": "closed"})

    def reopen_room(self, body: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        room_id = body.get("room_id")
        if not room_id:
            return _response(400, {"error": "room_id is required"})

        clean_id = room_id.strip()
        res = self.table.get_item(Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"})
        room = res.get("Item")
        if not room:
            return _response(404, {"error": "Room not found"})

        owner_id = owner["sub"]
        if room.get("owner_id") and room.get("owner_id") != owner_id:
            return _response(403, {"error": "Forbidden: You do not own this room."})

        now_epoch = int(datetime.now(timezone.utc).timestamp())
        exp = int(room.get("expires_at", 0))
        if exp and now_epoch >= exp:
            return _response(400, {"error": "Cannot reopen room: This room has permanently reached its 24-hour expiration."})

        self.table.update_item(
            Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"},
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": "active"}
        )
        return _response(200, {"message": "Room reopened successfully", "room_id": clean_id, "status": "active"})

    def delete_feedback(self, body: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        room_id = body.get("room_id")
        feedback_id = body.get("feedback_id")
        if not room_id or not feedback_id:
            return _response(400, {"error": "room_id and feedback_id are required"})

        clean_id = room_id.strip()
        clean_fb_id = feedback_id.strip()

        res = self.table.get_item(Key={"PK": f"ROOM#{clean_id}", "SK": "METADATA"})
        room = res.get("Item")
        if not room:
            return _response(404, {"error": "Room not found"})

        if room.get("owner_id") and room.get("owner_id") != owner["sub"]:
            return _response(403, {"error": "Forbidden: You do not own this room."})

        del_res = self.table.delete_item(
            Key={"PK": f"ROOM#{clean_id}", "SK": f"FEEDBACK#{clean_fb_id}"},
            ReturnValues="ALL_OLD"
        )
        if not del_res.get("Attributes"):
            return _response(404, {"error": "Feedback message not found"})

        return _response(200, {"message": "Feedback deleted successfully"})

    def get_my_posts(self, body: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        user_id = user["sub"]
        now_epoch = int(datetime.now(timezone.utc).timestamp())
        res = self.table.query(
            KeyConditionExpression=f"Key('PK').eq('USERPOSTS#{user_id}') & Key('SK').begins_with('MSG#')",
            ScanIndexForward=False
        )
        items = res.get("Items", [])
        valid_posts = []
        for it in items:
            exp = int(it.get("expires_at", 0))
            if exp and now_epoch >= exp:
                continue
            valid_posts.append(it)
        return _response(200, {"posts": valid_posts, "count": len(valid_posts), "echobox_id": user.get("username")})

    def delete_my_post(self, body: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        user_id = user["sub"]
        room_id = (body.get("room_id") or "").strip()
        feedback_id = (body.get("feedback_id") or "").strip()

        if not room_id or not feedback_id:
            return _response(400, {"error": "room_id and feedback_id are required"})

        res = self.table.get_item(Key={"PK": f"ROOM#{room_id}", "SK": f"FEEDBACK#{feedback_id}"})
        item = res.get("Item")
        if not item:
            self.table.delete_item(Key={"PK": f"USERPOSTS#{user_id}", "SK": f"MSG#{room_id}#{feedback_id}"})
            return _response(404, {"error": "Post not found or already deleted"})

        if item.get("author_id") != user_id:
            return _response(403, {"error": "Forbidden: You can only delete your own submitted messages."})

        self.table.delete_item(Key={"PK": f"ROOM#{room_id}", "SK": f"FEEDBACK#{feedback_id}"})
        self.table.delete_item(Key={"PK": f"USERPOSTS#{user_id}", "SK": f"MSG#{room_id}#{feedback_id}"})

        return _response(200, {"message": "Message deleted successfully", "feedback_id": feedback_id})

    def get_owner_rooms(self, body: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        owner_id = owner["sub"]
        res = self.table.query(
            KeyConditionExpression=f"Key('PK').eq('OWNER#{owner_id}') & Key('SK').begins_with('ROOM#')",
            ScanIndexForward=False
        )
        return _response(200, {"rooms": res.get("Items", []), "count": len(res.get("Items", []))})

    def claim_legacy_room(self, body: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
        return _response(200, {"message": "Legacy room claimed successfully"})


class RealLambdaBackend:
    """Executes the REAL EchoBox lambda_function.py against mocked AWS infrastructure via moto."""

    def __init__(self, repo_dir: Any = None):
        import os
        from pathlib import Path
        os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
        os.environ["AWS_ACCESS_KEY_ID"] = "mock_key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "mock_secret"
        import boto3
        from moto import mock_aws

        self._mock = mock_aws()
        self._mock.start()

        self.dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
        self.table = self.dynamodb.create_table(
            TableName="EchoBox",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )

        candidate_paths = [
            Path("/home/Sohan/PROJECTS/tracetest-ai/var/repos/sohan10012_EchoBox/backend"),
            Path("/home/Sohan/PROJECTS/tracetest-ai/var/repos/EchoBox/backend"),
            Path("echobox_real_backend"),
        ]
        if repo_dir:
            p_repo = Path(repo_dir)
            candidate_paths.insert(0, p_repo / "backend")
            candidate_paths.insert(0, p_repo)

        real_backend_dir = None
        for p in candidate_paths:
            if (p / "lambda_function.py").exists():
                real_backend_dir = p
                break

        if not real_backend_dir:
            raise RuntimeError(f"Real EchoBox lambda_function.py not found in {candidate_paths}")

        import sys
        if str(real_backend_dir) not in sys.path:
            sys.path.insert(0, str(real_backend_dir))

        import lambda_function
        self.lambda_mod = lambda_function
        self.lambda_mod.table = self.table

    def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.lambda_mod.lambda_handler(event, None)

    def stop(self):
        try:
            self._mock.stop()
        except Exception:
            pass

    def __del__(self):
        self.stop()


_default_backend: EchoBoxBackend | None = None


def get_default_backend(mode: str | None = None) -> Any:
    global _default_backend
    exec_mode = mode or os.environ.get("ECHOBOX_EXECUTION_MODE", "simulation")
    if exec_mode == "real":
        return RealLambdaBackend()
    if _default_backend is None:
        _default_backend = EchoBoxBackend()
    return _default_backend

