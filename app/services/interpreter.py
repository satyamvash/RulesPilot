"""
LLM-based natural language interpreter using Google Gemini.
Extracts a NacRuleIntent from free-form user text using Gemini function calling.
Returns ClarificationNeeded when required fields are missing or ambiguous.
"""

import json
import logging

import google.generativeai as genai

from app.config import settings
from app.models.rule import ClarificationNeeded, NacRuleIntent

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

# Tool (function) definitions sent to Gemini
_TOOLS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="emit_nac_rule",
                description=(
                    "Emit a structured NAC rule when all required fields are confidently "
                    "extracted from the user's input. Required fields: name, action. "
                    "Do not guess missing values — use request_clarification instead."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Name of the NAC rule",
                        ),
                        "action": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            enum=["ALLOW", "BLOCK"],
                            description="ALLOW or BLOCK",
                        ),
                        "status": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            enum=["ACTIVE", "INACTIVE"],
                            description="Rule status, defaults to ACTIVE",
                        ),
                        "description": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Optional one-sentence rule description",
                        ),
                        "os_types": genai.protos.Schema(
                            type=genai.protos.Type.ARRAY,
                            items=genai.protos.Schema(
                                type=genai.protos.Type.STRING,
                                enum=["WINDOWS", "MACOS", "LINUX"],
                            ),
                            description="Target OS types if mentioned",
                        ),
                        "hash_type": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            enum=["SHA256", "MD5"],
                            description="Hash type: SHA256 (64 chars) or MD5 (32 chars)",
                        ),
                        "hash_value": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The raw hash hex string",
                        ),
                    },
                    required=["name", "action"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="request_clarification",
                description="Ask the user for missing or ambiguous fields before creating the rule.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "missing_fields": genai.protos.Schema(
                            type=genai.protos.Type.ARRAY,
                            items=genai.protos.Schema(type=genai.protos.Type.STRING),
                            description="List of field names that are missing or ambiguous",
                        ),
                        "questions": genai.protos.Schema(
                            type=genai.protos.Type.ARRAY,
                            items=genai.protos.Schema(type=genai.protos.Type.STRING),
                            description="Human-readable questions to ask the user",
                        ),
                    },
                    required=["missing_fields", "questions"],
                ),
            ),
        ]
    )
]

_SYSTEM_PROMPT = """\
You are a NAC (Network Access Control) rule creation assistant.

Your job is to extract structured rule details from the user's free-form text and call
exactly ONE of these two functions:

1. emit_nac_rule — when you can confidently extract all required fields (name, action).
2. request_clarification — when required fields are missing or ambiguous.

Rules:
- NEVER guess a missing required field. If name or action is unclear, ask.
- action must be ALLOW or BLOCK. Synonyms: "block"/"deny"/"prevent" → BLOCK; "allow"/"permit"/"whitelist" → ALLOW.
- hash_value should be the raw hex string. Detect SHA256 (64 chars) or MD5 (32 chars) automatically.
- os_types: extract any mentioned OS (windows/macos/linux). If none mentioned, omit the field.
- Keep description concise — one sentence.
- Always call one of the two functions. Never respond with plain text.
"""


def interpret(user_text: str) -> NacRuleIntent | ClarificationNeeded:
    """
    Interpret free-form text and return either a NacRuleIntent or ClarificationNeeded.
    Raises ValueError if Gemini returns an unexpected response.
    """
    logger.info("Interpreting user input (length=%d)", len(user_text))

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=_SYSTEM_PROMPT,
        tools=_TOOLS,
        # Force Gemini to always call one of the tools, never return plain text
        tool_config={"function_calling_config": {"mode": "ANY"}},
    )

    response = model.generate_content(user_text)

    # Extract the function call from the response
    function_call = None
    for part in response.parts:
        if part.function_call:
            function_call = part.function_call
            break

    if function_call is None:
        raise ValueError("Gemini did not call a function — unexpected response format.")

    # Convert MapComposite to plain dict
    args = dict(function_call.args)
    logger.debug("Function called: %s | args: %s", function_call.name, json.dumps(args))

    if function_call.name == "emit_nac_rule":
        # Reassemble nested hash object from flat fields
        intent_data: dict = {
            "name": args["name"],
            "action": args["action"],
            "status": args.get("status", "ACTIVE"),
        }
        if "description" in args:
            intent_data["description"] = args["description"]
        if "os_types" in args:
            intent_data["os_types"] = list(args["os_types"])
        if "hash_value" in args:
            intent_data["hash"] = {
                "hash_type": args.get("hash_type", "SHA256"),
                "value": args["hash_value"],
            }
        return NacRuleIntent.model_validate(intent_data)

    if function_call.name == "request_clarification":
        return ClarificationNeeded.model_validate(
            {
                "missing_fields": list(args["missing_fields"]),
                "questions": list(args["questions"]),
            }
        )

    raise ValueError(f"Unexpected function name: {function_call.name}")
