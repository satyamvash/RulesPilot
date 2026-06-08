"""Thin GraphQL client using httpx."""
import json
import os
import re
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_URL = os.environ.get("NAC_GRAPHQL_URL", "http://localhost:8080/graphql")
_TOKEN = os.environ.get("NAC_AUTH_TOKEN", "")


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if _TOKEN:
        h["Authorization"] = f"Bearer {_TOKEN}"
    return h


def _operation_name(query: str) -> str | None:
    """Extract the operation name from a GraphQL query/mutation string."""
    match = re.search(r"(?:query|mutation)\s+(\w+)", query)
    return match.group(1) if match else None


def execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query/mutation and return the parsed response.

    Appends opname and requestId query params to the URL, matching the
    format: /graphql?opname=<OperationName>&requestId=<uuid>
    """
    op = _operation_name(query)
    params: dict[str, str] = {"requestId": str(uuid.uuid4())}
    if op:
        params["opname"] = op

    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    with httpx.Client(timeout=30) as http:
        resp = http.post(_URL, headers=_headers(), params=params, json=payload)
        resp.raise_for_status()

    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    return data.get("data", {})
