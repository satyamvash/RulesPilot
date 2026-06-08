"""
Unit tests for the interpreter service.
LLM calls are mocked — no real Anthropic API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.rule import ClarificationNeeded, HashType, NacRuleIntent, OsType, RuleAction
from app.services.interpreter import interpret


def _make_tool_use_block(name: str, input_data: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    return block


def _make_response(tool_block: MagicMock) -> MagicMock:
    response = MagicMock()
    response.content = [tool_block]
    return response


@patch("app.services.interpreter._client")
def test_interpret_block_rule_with_sha256(mock_client: MagicMock) -> None:
    mock_client.messages.create.return_value = _make_response(
        _make_tool_use_block(
            "emit_nac_rule",
            {
                "name": "Block Malware Hash",
                "action": "BLOCK",
                "hash": {
                    "hash_type": "SHA256",
                    "value": "a" * 64,
                },
                "os_types": ["WINDOWS"],
                "status": "ACTIVE",
            },
        )
    )

    result = interpret("Block the sha256 aaaa...aaaa on Windows, name it Block Malware Hash")

    assert isinstance(result, NacRuleIntent)
    assert result.action == RuleAction.BLOCK
    assert result.name == "Block Malware Hash"
    assert result.hash is not None
    assert result.hash.hash_type == HashType.SHA256
    assert result.hash.value == "a" * 64
    assert result.os_types == [OsType.WINDOWS]


@patch("app.services.interpreter._client")
def test_interpret_allow_rule_no_hash(mock_client: MagicMock) -> None:
    mock_client.messages.create.return_value = _make_response(
        _make_tool_use_block(
            "emit_nac_rule",
            {
                "name": "Allow Internal Tool",
                "action": "ALLOW",
                "status": "ACTIVE",
            },
        )
    )

    result = interpret("Allow Internal Tool")

    assert isinstance(result, NacRuleIntent)
    assert result.action == RuleAction.ALLOW
    assert result.hash is None


@patch("app.services.interpreter._client")
def test_interpret_missing_action_returns_clarification(mock_client: MagicMock) -> None:
    mock_client.messages.create.return_value = _make_response(
        _make_tool_use_block(
            "request_clarification",
            {
                "missing_fields": ["action"],
                "questions": ["Should this rule ALLOW or BLOCK the traffic?"],
            },
        )
    )

    result = interpret("Create a rule named Test Rule for sha256 " + "b" * 64)

    assert isinstance(result, ClarificationNeeded)
    assert "action" in result.missing_fields


@patch("app.services.interpreter._client")
def test_interpret_raises_on_no_tool_call(mock_client: MagicMock) -> None:
    response = MagicMock()
    response.content = []  # no tool use blocks
    mock_client.messages.create.return_value = response

    with pytest.raises(ValueError, match="did not call a tool"):
        interpret("some input")
