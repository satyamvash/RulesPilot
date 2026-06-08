"""
GraphQL client for app-control-manager (ACM).
Forwards the end-user's bearer token on every request.
"""

import logging
from typing import Any

import httpx

from app.config import settings
from app.models.rule import NacRuleIntent

logger = logging.getLogger(__name__)

# Placeholder mutation — update with the real mutation name and fields
# once the ACM GraphQL schema is confirmed.
_CREATE_RULE_MUTATION = """
mutation CreateNacRule($input: NacRuleInput!) {
  createNacRule(input: $input) {
    id
    name
    action
    status
    createdAt
  }
}
"""


def _build_rule_input(intent: NacRuleIntent) -> dict[str, Any]:
    """Convert a NacRuleIntent into the GraphQL mutation input shape."""
    data: dict[str, Any] = {
        "name": intent.name,
        "action": intent.action.value,
        "status": intent.status.value,
    }
    if intent.description:
        data["description"] = intent.description
    if intent.os_types:
        data["osTypes"] = [os.value for os in intent.os_types]
    if intent.hash:
        data["hash"] = {
            "hashType": intent.hash.hash_type.value,
            "value": intent.hash.value,
        }
    return data


async def create_rule(intent: NacRuleIntent, bearer_token: str) -> dict[str, Any]:
    """
    Create a NAC rule via the ACM GraphQL API.
    Forwards the caller's bearer token for auth + audit trail.
    """
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": _CREATE_RULE_MUTATION,
        "variables": {"input": _build_rule_input(intent)},
    }

    logger.info("Creating NAC rule via ACM GraphQL: name=%s action=%s", intent.name, intent.action)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.acm_graphql_url, json=payload, headers=headers)
        response.raise_for_status()

    body = response.json()

    if errors := body.get("errors"):
        logger.error("GraphQL errors from ACM: %s", errors)
        raise ValueError(f"Rule creation failed: {errors[0].get('message', 'unknown error')}")

    return body["data"]["createNacRule"]
