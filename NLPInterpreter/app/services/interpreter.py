"""
LLM-based natural language interpreter using Anthropic Claude.
Extracts a NacRuleIntent from free-form user text using Claude tool use.
Returns ClarificationNeeded when required fields are missing or ambiguous.

Cost controls:
- Uses claude-haiku (cheapest model).
- System prompt marked with cache_control — billed at 10% cost on cache hits (5-min TTL).
- max_tokens capped at 1024 — tool call responses are small.
- temperature=0 for deterministic, shorter outputs.

Required fields for rule creation (ACM schema):
  - rule_name     : name of the rule (no default)
  - behavior      : ALLOW or BLOCK (no default)
  - os_type       : at least one of WINDOWS / MACOS / LINUX (no default)
  - scope_ids     : at least one numeric site/group/account ID (no default)

Required with safe defaults:
  - scope_type    : defaults to SITE
  - propagation   : defaults to true

At least one parameter must be provided (rule would match nothing otherwise):
  - publisher, path, process, parent_process, sha256, signer
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
            "Emit a structured NAC rule ONLY when ALL of the following are present: "
            "rule_name, behavior, os_type (non-empty), scope_ids (non-empty), "
            "and at least one of: publisher, path, process, parent_process, sha256, signer. "
            "If ANY of these are missing or ambiguous, call request_clarification instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                # ── Core required fields ──────────────────────────────────────
                "rule_name": {
                    "type": "string",
                    "description": "Exact name of the NAC rule as stated by the user.",
                },
                "behavior": {
                    "type": "string",
                    "enum": ["ALLOW", "BLOCK"],
                    "description": (
                        "ALLOW or BLOCK. "
                        "Synonyms → BLOCK: block, deny, prevent, restrict; "
                        "Synonyms → ALLOW: allow, permit, whitelist, trust."
                    ),
                },
                "os_type": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["WINDOWS", "MACOS", "LINUX"]},
                    "description": (
                        "One or more target OS types. "
                        "'windows' → WINDOWS, 'mac'/'macos' → MACOS, 'linux' → LINUX. "
                        "Must be non-empty."
                    ),
                },
                "scope_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One or more numeric scope IDs (site/group/account) from the user's text. "
                        "MUST be non-empty — if the user did not mention any ID, call request_clarification."
                    ),
                },
                # ── Fields with safe defaults ─────────────────────────────────
                "scope_type": {
                    "type": "string",
                    "enum": ["SITE", "ACCOUNT", "GROUP"],
                    "description": "Scope type. Defaults to SITE if not mentioned.",
                },
                "propagation": {
                    "type": "boolean",
                    "description": "Propagate to child scopes. Default true unless user says otherwise.",
                },
                # ── Rule match criteria (at least one required) ────────────────
                "publisher": {
                    "type": "string",
                    "description": "Publisher / vendor name e.g. 'Microsoft', 'Zoom'.",
                },
                "path": {
                    "type": "string",
                    "description": "Full file path e.g. C:\\\\Applications\\\\app.exe",
                },
                "process": {
                    "type": "string",
                    "description": "Process executable name e.g. svchost.exe",
                },
                "parent_process": {
                    "type": "string",
                    "description": "Parent process name e.g. setup.exe",
                },
                "sha256": {
                    "type": "string",
                    "description": "SHA256 hash — exactly 64 hex characters.",
                },
                "signer": {
                    "type": "string",
                    "description": "Certificate signer name.",
                },
            },
            "required": ["rule_name", "behavior", "os_type", "scope_ids"],
        },
    },
    {
        "name": "request_clarification",
        "description": (
            "Ask the user for ALL missing or ambiguous fields in one shot. "
            "Collect every missing field before asking — do not ask one at a time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "missing_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exact field names that are missing or ambiguous.",
                },
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One clear, human-readable question per missing field. "
                        "Include context — e.g. 'What is the Scope ID? "
                        "(numeric site/group/account ID visible in the SentinelOne console)'"
                    ),
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
            "You are a NAC (Network Access Control) rule creation assistant for SentinelOne.\n\n"

            "Your job: extract a structured NAC rule from the user's free-form text and call exactly ONE tool.\n\n"

            "━━ REQUIRED FIELDS (no defaults — must be in user text or ask) ━━\n"
            "1. rule_name   — exact rule name as stated by the user.\n"
            "2. behavior    — ALLOW or BLOCK. block/deny/prevent/restrict → BLOCK; allow/permit/whitelist/trust → ALLOW.\n"
            "3. os_type     — at least one: WINDOWS, MACOS, LINUX. 'windows' → WINDOWS, 'mac'/'macos' → MACOS.\n"
            "4. scope_ids   — at least one numeric ID (site/group/account). Visible in the SentinelOne console.\n"
            "                 If not mentioned → ask. NEVER pass an empty list.\n"
            "5. parameters  — at least one of: publisher, path, process, parent_process, sha256, signer.\n"
            "                 A rule with no parameters would match everything — always ask if none provided.\n\n"

            "━━ FIELDS WITH SAFE DEFAULTS (do not ask if missing) ━━\n"
            "- scope_type  : default SITE.\n"
            "- propagation : default true.\n\n"

            "━━ TOOL SELECTION RULES ━━\n"
            "• Call emit_nac_rule   → only when ALL 5 required groups above are present.\n"
            "• Call request_clarification → when ANY required field is missing or ambiguous.\n"
            "  - Collect ALL missing fields in ONE call. Never ask one at a time.\n"
            "  - Write questions in plain English with enough context for a non-technical user.\n\n"

            "━━ EXTRACTION RULES ━━\n"
            "- sha256: must be exactly 64 hex chars — extract as-is, do not validate.\n"
            "- path: preserve backslashes exactly as written.\n"
            "- Never invent or guess values for required fields.\n"
            "- Never respond with plain text — always call a tool."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]


def _has_at_least_one_parameter(args: dict) -> bool:
    """Check if at least one rule match parameter was extracted."""
    return any(args.get(f) for f in ["publisher", "path", "process", "parent_process", "sha256", "signer"])


def interpret(user_text: str) -> NacRuleIntent | ClarificationNeeded:
    """
    Interpret free-form text and return either a NacRuleIntent or ClarificationNeeded.
    Raises ValueError if Claude returns an unexpected response.
    """
    logger.info("Interpreting user input (length=%d)", len(user_text))

    response = _client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        temperature=0,
        system=_SYSTEM,
        tools=_TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": user_text}],
    )

    # Log token usage — shows cache hits saving credits
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

        # Safety net: if Claude somehow emitted an empty scope_ids or no parameters, convert to clarification
        missing: list[str] = []
        questions: list[str] = []

        if not args.get("scope_ids"):
            missing.append("scope_ids")
            questions.append(
                "What is the Scope ID? (numeric site, group, or account ID visible in the SentinelOne console)"
            )

        if not _has_at_least_one_parameter(args):
            missing.append("parameters")
            questions.append(
                "Please provide at least one match criteria for the rule: "
                "publisher, file path, process name, parent process, SHA256 hash, or signer."
            )

        if missing:
            logger.warning("emit_nac_rule called with missing required fields: %s — converting to clarification", missing)
            return ClarificationNeeded(missing_fields=missing, questions=questions)

        return NacRuleIntent.model_validate({
            "rule_name": args["rule_name"],
            "behavior": args["behavior"],
            "os_type": args["os_type"],
            "propagation": args.get("propagation", True),
            "scope": {
                "scope_type": args.get("scope_type", "SITE"),
                "scope_ids": args["scope_ids"],
            },
            "parameters": {
                "publisher": args.get("publisher"),
                "path": args.get("path"),
                "process": args.get("process"),
                "parent_process": args.get("parent_process"),
                "sha256": args.get("sha256"),
                "signer": args.get("signer"),
            },
            "exceptions": [],
        })

    if tool_use.name == "request_clarification":
        return ClarificationNeeded.model_validate(tool_use.input)

    raise ValueError(f"Unexpected tool name: {tool_use.name}")
