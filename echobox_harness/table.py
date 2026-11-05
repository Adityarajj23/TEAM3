"""EchoBox Test-Safe Local In-Memory Harness.
Enables isolated, zero-network, high-fidelity testing of EchoBox RPC actions and DynamoDB patterns.
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any


class InMemoryTable:
    """In-memory mock for DynamoDB Single-Table storage conforming to boto3 Table API."""

    def __init__(self, name: str = "EchoBox"):
        self.name = name
        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def reset(self) -> None:
        self._items.clear()

    def put_item(self, Item: dict[str, Any]) -> dict[str, Any]:
        pk = Item.get("PK")
        sk = Item.get("SK")
        if not pk or not sk:
            raise ValueError("Item must contain both PK and SK")
        self._items[(str(pk), str(sk))] = dict(Item)
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:
        pk = str(Key.get("PK"))
        sk = str(Key.get("SK"))
        item = self._items.get((pk, sk))
        if item is not None:
            return {"Item": dict(item), "ResponseMetadata": {"HTTPStatusCode": 200}}
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def delete_item(self, Key: dict[str, Any], ReturnValues: str = "NONE") -> dict[str, Any]:
        pk = str(Key.get("PK"))
        sk = str(Key.get("SK"))
        old = self._items.pop((pk, sk), None)
        res: dict[str, Any] = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        if ReturnValues == "ALL_OLD" and old is not None:
            res["Attributes"] = dict(old)
        return res

    def update_item(self, Key: dict[str, Any], UpdateExpression: str,
                    ExpressionAttributeNames: dict[str, str] | None = None,
                    ExpressionAttributeValues: dict[str, Any] | None = None,
                    ReturnValues: str = "NONE") -> dict[str, Any]:
        pk = str(Key.get("PK"))
        sk = str(Key.get("SK"))
        item = self._items.get((pk, sk))
        if item is None:
            item = {"PK": pk, "SK": sk}
            self._items[(pk, sk)] = item

        names = ExpressionAttributeNames or {}
        values = ExpressionAttributeValues or {}

        # Simple SET parser for common patterns like 'SET #status = :status'
        if UpdateExpression.startswith("SET "):
            clauses = UpdateExpression[4:].split(",")
            for clause in clauses:
                parts = clause.strip().split("=")
                if len(parts) == 2:
                    raw_lhs = parts[0].strip()
                    raw_rhs = parts[1].strip()
                    attr_name = names.get(raw_lhs, raw_lhs)
                    attr_val = values.get(raw_rhs, raw_rhs)
                    item[attr_name] = attr_val

        res: dict[str, Any] = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        if ReturnValues == "ALL_NEW":
            res["Attributes"] = dict(item)
        return res

    def query(self, KeyConditionExpression: Any, ScanIndexForward: bool = True,
              Select: str = "ALL_ATTRIBUTES", ExclusiveStartKey: Any = None) -> dict[str, Any]:
        # Evaluates Key("PK").eq(...) & Key("SK").begins_with(...)
        # For simplicity, extract matching items from in-memory dict
        matched = []
        # KeyConditionExpression can be a string or boto3 Key condition object or custom comparator
        # We handle both boto3 condition objects and string/repr forms
        expr_str = str(KeyConditionExpression)

        # Parse PK equality
        pk_val = None
        sk_prefix = None
        if hasattr(KeyConditionExpression, "get_expression"):
            # boto3 builder
            pass

        # Robust string matching for KeyConditionExpression
        import re
        pk_match = re.search(r"Key\('PK'\)\.eq\('([^']+)'\)", expr_str)
        if not pk_match:
            pk_match = re.search(r"PK\s*=\s*['\"]?([^'\"\s)]+)", expr_str)
        if pk_match:
            pk_val = pk_match.group(1)

        sk_match = re.search(r"Key\('SK'\)\.begins_with\('([^']+)'\)", expr_str)
        if not sk_match:
            sk_match = re.search(r"begins_with\(SK,\s*['\"]?([^'\"\s)]+)", expr_str)
        if sk_match:
            sk_prefix = sk_match.group(1)

        for (pk, sk), it in self._items.items():
            if pk_val and pk != pk_val:
                continue
            if sk_prefix and not sk.startswith(sk_prefix):
                continue
            matched.append(dict(it))

        if not ScanIndexForward:
            matched.reverse()

        if Select == "COUNT":
            return {"Count": len(matched), "Items": [], "ResponseMetadata": {"HTTPStatusCode": 200}}

        return {"Items": matched, "Count": len(matched), "ResponseMetadata": {"HTTPStatusCode": 200}}


_default_table = InMemoryTable()


def get_default_table() -> InMemoryTable:
    return _default_table


def make_jwt_token(sub: str, username: str = "", email: str = "", is_owner: bool = False) -> str:
    """Generates an unverified or signature-free JWT suitable for mock auth parsing."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {
        "sub": sub,
        "username": username,
        "email": email,
        "name": username or (email.split("@")[0] if email else "Test User"),
        "iss": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_NfCww8cVp" if is_owner else "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_vRfOd670T",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    return f"{header}.{payload}."

