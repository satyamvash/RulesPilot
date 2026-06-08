"""
LLM-based natural language interpreter using Anthropic Claude.
Extracts a NacRuleIntent from free-form user text using Claude tool use.
Returns ClarificationNeeded when required fields are missing or ambiguous.

Cost controls:
- Uses claude-3-haiku (cheapest model).
- System prompt is marked with cache_control so it is only billed once per cache TTL (5 min).
- max_tokens capped at 512 — tool call responses are small.
- temperature=0 for deterministic, shorter outputs.
"""

import json
import logging

import anthropic

from app.config import settings
from app.models.rule import ClarificationNeeded, NacRuleIntent

logger = logging.getLogger(__name__)

# Single shared client — reused across requests
_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# ── Tool definitions ───────────────────────────────────────────────────────────

_TOOLS: list[anthropic.types.ToolParam] = [
    {
        "name": "emit_nac_rule",
        "description": (
            "Emit a structured NAC rule when all required fields are confidently extracted "
            "from the user's input. Required fields: name, action. "
            "Do not guess missing values — use request_clarification instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the NAC rule"},
                "action": {
                    "type": "string",
                    "enum": ["ALLOW", "BLOCK"],
                    "description": "ALLOW or BLOCK",
                },
                "status": {
                    "type": "string",
                    "enum": ["ACTIVE", "INACTIVE"],
                    "description": "Rule status, defaults to ACTIVE",
                },
                "description": {
                    "type": "string",
                    "description": "Optional one-sentence rule description",
                },
                "os_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["WINDOWS", "MACOS", "LINUX"]},
                    "description": "Target OS types if mentioned",
                },
                "hash_type": {
                    "type": "string",
                    "enum": ["SHA256", "MD5"],
                    "description": "Hash type: SHA256 (64 chars) or MD5 (32 chars)",
                },
                "hash_value": {
                    "type": "string",
                    "description": "The raw hash hex string",
                },
            },
            "required": ["name", "action"],
        },
    },
    {
        "name": "request_clarification",
        "description": "Ask the user for missing or ambiguous fields before creating the rule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "missing_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of field names that are missing or ambiguous",
                },
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Human-readable questions to ask the user",
                },
            },
            "required": ["missing_fields", "questions"],
        },
    },
]

# ── System prompt ──────────────────────────────────────────────────────────────
# Marked with cache_control so Anthropic caches it for 5 minutes.
# Subsequent requests within that window are charged at 10% of normal input cost.

_SYSTEM: list[anthropic.types.TextBlockParam] = [
    {
        "type": "text",
        "text": (
            "You are a NAC (Network Access Control) rule creation assistant.\n\n"
            "Your job is to extract structured rule details from the user's free-form text "
            "and call exactly ONE of these two tools:\n\n"
            "1. emit_nac_rule — when you can confidently extract all required fields (name, action).\n"
            "2. request_clarification — when required fields are missing or ambiguous.\n\n"
            "Rules:\n"
            "- NEVER guess a missing required field. If name or action is unclear, ask.\n"
            "- action must be ALLOW or BLOCK. "
            'Synonyms: "block"/"deny"/"prevent" → BLOCK; "allow"/"permit"/"whitelist" → ALLOW.\n'
            "- hash_value should be the raw hex string. "
            "Detect SHA256 (64 chars) or MD5 (32 chars) automatically.\n"
            "- os_types: extract any mentioned OS (windows/macos/linux). If none mentioned, omit.\n"
            "- Keep description concise — one sentence.\n"
            "- Always call one of the two tools. Never respond with plain text."
        ),
        # Cache this block — billed at 10% cost on cache hits (5-min TTL)
        "cache_control": {"type": "ephemeral"},
    }
]


def interpret(user_text: str) -> NacRuleIntent | ClarificationNeeded:
    """
    Interpret free-form text and return either a NacRuleIntent or ClarificationNeeded.
    Raises ValueError if Claude returns an unexpected response.
    """
    logger.info("Interpreting user input (length=%d)", len(user_text))

    response = _client.messages.create(
        model=settings.anthropic_model,
        max_tokens=512,          # tool call payloads are small — cap to save credits
        temperature=0,           # deterministic output, no creative variation
        system=_SYSTEM,
        tools=_TOOLS,
        tool_choice={"type": "any"},  # force a tool call, never plain text
        messages=[{"role": "user", "content": user_text}],
    )

    # Log cache usage so we can verify credits are being saved
    usage = response.usage
    logger.info(
        "Token usage — input: %d, output: %d, cache_read: %s, cache_write: %s",
        usage.input_tokens,
        usage.output_tokens,
        getattr(usage, "cache_read_input_tokens", "n/a"),
        getattr(usage, "cache_creation_input_tokens", "n/a"),
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )

    if tool_use is None:
        raise ValueError("Claude did not call a tool — unexpected response format.")

    logger.debug("Tool called: %s | input: %s", tool_use.name, json.dumps(tool_use.input))

    if tool_use.name == "emit_nac_rule":
        args = tool_use.input
        intent_data: dict = {
            "name": args["name"],
            "action": args["action"],
            "status": args.get("status", "ACTIVE"),
        }
        if "description" in args:
            intent_data["description"] = args["description"]
        if "os_types" in args:
            intent_data["os_types"] = args["os_types"]
        if "hash_value" in args:
            intent_data["hash"] = {
                "hash_type": args.get("hash_type", "SHA256"),
                "value": args["hash_value"],
            }
        return NacRuleIntent.model_validate(intent_data)

    if tool_use.name == "request_clarification":
        return ClarificationNeeded.model_validate(tool_use.input)

    raise ValueError(f"Unexpected tool name: {tool_use.name}")
