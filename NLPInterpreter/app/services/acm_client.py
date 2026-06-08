"""
GraphQL client for app-control-manager (ACM).
Forwards the end-user's bearer token on every request.
Logs the full request payload before sending so it can be inspected.
"""

import json
import logging
from typing import Any

import httpx

from app.config import settings
from app.models.rule import NacRuleIntent

logger = logging.getLogger(__name__)

# Mirrors the exact mutation from the ACM NAC rules API
_CREATE_RULE_MUTATION = """
mutation UpdateNACSingleRule($input: NACRuleInput!) {
    updateNACSingleRule(input: $input) {
        success
        statusMessage
        validationErrors {
            id { code value message }
            ruleName { code value message }
            osType { code value message }
            scope { code value message }
            label { code value message }
            behavior { code value message }
            parameters {
                publisher { code value message }
                path { code value message }
                signer { code value message }
                sha256 { code value message }
                process { code value message }
                parentProcess { code value message }
                parentLabel { code value message }
            }
            exceptions {
                publisher { code value message }
                path { code value message }
                signer { code value message }
                sha256 { code value message }
                process { code value message }
                parentProcess { code value message }
                parentLabel { code value message }
            }
            unmapped { code value message }
        }
    }
}
"""


def _build_graphql_input(intent: NacRuleIntent) -> dict[str, Any]:
    """Convert a NacRuleIntent into the GraphQL mutation input shape."""
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

    if not intent.scope.scope_ids:
        raise ValueError("scope_ids must not be empty — ACM requires at least one scope ID.")

    graphql_input: dict[str, Any] = {
        "ruleName": intent.rule_name,
        "behavior": intent.behavior.value,
        "osType": [os.value for os in intent.os_type],
        "propagation": intent.propagation,
        "scope": {
            "scopeType": intent.scope.scope_type.value,
            "scopeIds": intent.scope.scope_ids,
        },
        "parameters": params,
    }
    if exceptions:
        graphql_input["exceptions"] = exceptions

    return graphql_input


async def create_rule(intent: NacRuleIntent, bearer_token: str) -> dict[str, Any]:
    """
    Create a NAC rule via the ACM GraphQL API.
    Logs the full request payload before sending for inspection.
    Forwards the caller's bearer token for auth + audit trail.
    """
    graphql_input = _build_graphql_input(intent)
    payload = {
        "query": _CREATE_RULE_MUTATION,
        "variables": {"input": graphql_input},
    }

    # Log the full request before sending so it can be verified
    logger.info("=" * 60)
    logger.info("ACM GraphQL Request")
    logger.info("URL    : %s", settings.acm_graphql_url)
    logger.info("Payload:\n%s", json.dumps(payload, indent=2))
    logger.info("=" * 60)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "accept": "*/*",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.acm_graphql_url, json=payload, headers=headers)

    logger.info("ACM Response status : %d", response.status_code)
    logger.info("ACM Response body   : %s", response.text)

    response.raise_for_status()
    body = response.json()

    if errors := body.get("errors"):
        logger.error("GraphQL errors from ACM: %s", errors)
        raise ValueError(f"Rule creation failed: {errors[0].get('message', 'unknown error')}")

    result = body["data"]["updateNACSingleRule"]

    if not result.get("success"):
        validation_errors = result.get("validationErrors", {})
        logger.error(
            "Rule creation returned success=false: %s", json.dumps(validation_errors, indent=2)
        )
        raise ValueError(f"Rule creation failed: {result.get('statusMessage', 'unknown error')}")

    return result
