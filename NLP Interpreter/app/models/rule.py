from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RuleAction(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class RuleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class HashType(StrEnum):
    SHA256 = "SHA256"
    MD5 = "MD5"


class OsType(StrEnum):
    WINDOWS = "WINDOWS"
    MACOS = "MACOS"
    LINUX = "LINUX"


class HashCriteria(BaseModel):
    hash_type: HashType = HashType.SHA256
    value: str = Field(..., description="The hash value")


class NacRuleIntent(BaseModel):
    """Structured intent extracted from free-form user text."""

    name: str = Field(..., description="Name of the NAC rule")
    action: RuleAction = Field(..., description="ALLOW or BLOCK")
    hash: HashCriteria | None = Field(None, description="Hash/SHA256 criteria")
    os_types: list[OsType] | None = Field(None, description="Target OS types")
    description: str | None = Field(None, description="Optional rule description")
    status: RuleStatus = Field(RuleStatus.ACTIVE, description="ACTIVE or INACTIVE")


class ClarificationNeeded(BaseModel):
    """Returned when required fields are missing or ambiguous."""

    missing_fields: list[str]
    questions: list[str]


class InterpretRequest(BaseModel):
    text: str = Field(..., description="Free-form text describing the rule")
    dry_run: bool = Field(False, description="If true, return parsed intent without creating rule")


class InterpretResponse(BaseModel):
    intent: NacRuleIntent | None = None
    clarification_needed: ClarificationNeeded | None = None
    created_rule: dict[str, Any] | None = None
    dry_run: bool = False
