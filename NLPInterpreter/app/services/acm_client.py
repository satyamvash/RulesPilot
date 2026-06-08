"""
REST client for app-control-manager (ACM).
Forwards the end-user's bearer token on every request.
Logs the full request payload before sending so it can be inspected.

Endpoint: POST /web/api/v2.1/nac/config/api/v1/nac/rules
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings
from app.models.rule import DeleteIntent, NacRuleIntent, UpdateIntent

logger = logging.getLogger(__name__)

_RULES_PATH = "/web/api/v2.1/nac/config/api/v1/nac/rules"


def _build_rest_body(intent: NacRuleIntent) -> dict[str, Any]:
    """Convert a NacRuleIntent into the ACM REST request body."""
    if not intent.scope.scope_ids:
        raise ValueError("scope_ids must not be empty — ACM requires at least one scope ID.")

    params: dict[str, Any] = {}
    if intent.parameters.publisher:
        params["publisher"] = intent.parameters.publisher
    if intent.parameters.path:
        params["path"] = intent.parameters.path
    if intent.parameters.process:
        params["process"] = intent.parameters.process
    if intent.parameters.parent_process:
        params["parentProcess"] = intent.parameters.parent_process
    if intent.parameters.sha256:
        params["sha256"] = intent.parameters.sha256
    if intent.parameters.signer:
        params["signer"] = intent.parameters.signer

    exceptions = []
    for exc in intent.exceptions:
        exc_entry: dict[str, Any] = {}
        if exc.publisher:
            exc_entry["publisher"] = exc.publisher
        if exc.path:
            exc_entry["path"] = exc.path
        if exc.process:
            exc_entry["process"] = exc.process
        if exc.parent_process:
            exc_entry["parentProcess"] = exc.parent_process
        if exc.sha256:
            exc_entry["sha256"] = exc.sha256
        if exc.signer:
            exc_entry["signer"] = exc.signer
        if exc_entry:
            exceptions.append(exc_entry)

    body: dict[str, Any] = {
        "ruleName": intent.rule_name,
        "behavior": intent.behavior.value,
        "osType": [os.value for os in intent.os_type],
        "propagation": intent.propagation if intent.behavior.value == "ALLOW" else False,
        "scope": {
            "scopeType": intent.scope.scope_type.value,
            "scopeIds": intent.scope.scope_ids,
        },
        "parameters": params,
    }
    if exceptions:
        body["exceptions"] = exceptions

    return body


async def create_rule(intent: NacRuleIntent, bearer_token: str) -> dict[str, Any]:
    """
    Create a NAC rule via the ACM REST API.
    POST {acm_url}/web/api/v2.1/nac/config/api/v1/nac/rules
    """
    body = _build_rest_body(intent)
    url = f"{settings.acm_url.rstrip('/')}{_RULES_PATH}"
    query_params = {
        "scopeType": intent.scope.scope_type.value,
        "scopeId": intent.scope.scope_ids[0],
    }

    logger.info("=" * 60)
    logger.info("ACM REST Request")
    logger.info("URL    : %s  params=%s", url, query_params)
    logger.info("Body   :\n%s", json.dumps(body, indent=2))
    logger.info("=" * 60)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "accept": "*/*",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=body, headers=headers, params=query_params)

    logger.info("ACM Response status : %d", response.status_code)
    logger.info("ACM Response body   : %s", response.text)

    response.raise_for_status()
    result = response.json()

    if not result.get("success"):
        validation_errors = result.get("validationErrors", {})
        logger.error(
            "Rule creation returned success=false: %s", json.dumps(validation_errors, indent=2)
        )
        raise ValueError(f"Rule creation failed: {result.get('statusMessage', 'unknown error')}")

    return result


async def delete_rules(intent: DeleteIntent, bearer_token: str) -> dict[str, Any]:
    """
    Delete NAC rules via the ACM REST API.
    DELETE {acm_url}/web/api/v2.1/nac/config/api/v1/nac/rules?scopeType=...&scopeId=...&ids=...
    """
    url = f"{settings.acm_url.rstrip('/')}{_RULES_PATH}"
    query_params: list[tuple[str, str]] = [
        ("scopeType", intent.scope_type.value),
        ("scopeId", intent.scope_id),
        *[("ids", rid) for rid in intent.rule_ids],
    ]

    logger.info("=" * 60)
    logger.info("ACM DELETE Request")
    logger.info("URL    : %s  params=%s", url, query_params)
    logger.info("=" * 60)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "accept": "*/*",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(url, headers=headers, params=query_params)

    logger.info("ACM Response status : %d", response.status_code)
    logger.info("ACM Response body   : %s", response.text)

    response.raise_for_status()
    return response.json() if response.text else {"success": True}


async def get_rule(rule_id: str, scope_type: str, scope_id: str, bearer_token: str) -> dict[str, Any]:
    """
    Fetch a single rule by ID by querying all rules and matching client-side.
    POST /web/api/v2.1/nac/config/api/v1/nac/rules/query
    """
    query_url = f"{settings.acm_url.rstrip('/')}{_RULES_PATH}/query"
    payload: dict[str, Any] = {
        "scopeSelector": {"scopeType": scope_type, "scopeIds": [scope_id]},
    }
    headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}

    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"scopeType": scope_type, "scopeId": scope_id, "pageSize": 100}
        if cursor:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(query_url, json=payload, headers=headers, params=params)

        response.raise_for_status()
        data = response.json()

        for edge in data.get("edges", []):
            node = edge["node"]
            if str(node.get("id")) == str(rule_id):
                return node

        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    raise ValueError(f"Rule {rule_id} not found in scope {scope_id}.")


async def update_rule(intent: UpdateIntent, bearer_token: str) -> dict[str, Any]:
    """
    Update a NAC rule via the ACM REST API.
    Fetches the current rule, merges user-supplied changes, then PUTs.
    PUT {acm_url}/web/api/v2.1/nac/config/api/v1/nac/rules/{id}
    """
    current = await get_rule(intent.rule_id, intent.scope_type.value, intent.scope_id, bearer_token)

    params: dict[str, Any] = dict(current.get("parameters") or {})
    if intent.publisher is not None:
        params["publisher"] = intent.publisher
    if intent.path is not None:
        params["path"] = intent.path
    if intent.process is not None:
        params["process"] = intent.process
    if intent.parent_process is not None:
        params["parentProcess"] = intent.parent_process
    if intent.sha256 is not None:
        params["sha256"] = intent.sha256
    if intent.signer is not None:
        params["signer"] = intent.signer

    behavior = intent.behavior.value if intent.behavior else current["behavior"]
    body: dict[str, Any] = {
        "ruleName": intent.rule_name or current["ruleName"],
        "behavior": behavior,
        "osType": [o.value for o in intent.os_type] if intent.os_type else current["osType"],
        "propagation": intent.propagation if intent.propagation is not None else (
            current.get("propagation", True) if behavior == "ALLOW" else False
        ),
        "scope": {
            "scopeType": intent.scope_type.value,
            "scopeIds": [intent.scope_id],
        },
        "parameters": params,
    }
    if current.get("exceptions"):
        body["exceptions"] = current["exceptions"]

    url = f"{settings.acm_url.rstrip('/')}{_RULES_PATH}/{intent.rule_id}"
    query_params = {"scopeType": intent.scope_type.value, "scopeId": intent.scope_id}

    logger.info("=" * 60)
    logger.info("ACM UPDATE Request")
    logger.info("URL    : %s  params=%s", url, query_params)
    logger.info("Body   :\n%s", json.dumps(body, indent=2))
    logger.info("=" * 60)

    headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json", "accept": "*/*"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(url, json=body, headers=headers, params=query_params)

    logger.info("ACM Response status : %d", response.status_code)
    logger.info("ACM Response body   : %s", response.text)

    response.raise_for_status()
    result = response.json()

    if not result.get("success"):
        logger.error("Rule update failed: %s", json.dumps(result.get("validationErrors", {}), indent=2))
        raise ValueError(f"Rule update failed: {result.get('statusMessage', 'unknown error')}")

    return result
