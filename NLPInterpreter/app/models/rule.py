from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Behavior(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class OsType(StrEnum):
    WINDOWS = "WINDOWS"
    MACOS = "MACOS"
    LINUX = "LINUX"


class ScopeType(StrEnum):
    SITE = "SITE"
    ACCOUNT = "ACCOUNT"
    GROUP = "GROUP"


class Scope(BaseModel):
    scope_type: ScopeType = Field(..., description="SITE, ACCOUNT, or GROUP")
    scope_ids: list[str] = Field(..., description="List of scope IDs")


class RuleParameters(BaseModel):
    """Main rule match criteria — all fields optional, at least one should be provided."""

    publisher: str | None = Field(None, description="Publisher / signer name")
    path: str | None = Field(None, description="File path")
    process: str | None = Field(None, description="Process name")
    parent_process: str | None = Field(None, description="Parent process name")
    sha256: str | None = Field(None, description="SHA256 hash value")
    signer: str | None = Field(None, description="Signer name")


class RuleException(BaseModel):
    """A single exception entry for the rule."""

    publisher: str | None = None
    path: str | None = None
    process: str | None = None
    parent_process: str | None = None
    sha256: str | None = None
    signer: str | None = None


class NacRuleIntent(BaseModel):
    """Structured intent extracted from free-form user text — mirrors the ACM GraphQL schema."""

    rule_name: str = Field(..., description="Name of the NAC rule")
    behavior: Behavior = Field(..., description="ALLOW or BLOCK")
    os_type: list[OsType] = Field(..., description="Target OS types")
    scope: Scope = Field(..., description="Scope of the rule")
    parameters: RuleParameters = Field(..., description="Rule match criteria")
    exceptions: list[RuleException] = Field(default_factory=list, description="Exception entries")
    propagation: bool = Field(True, description="Whether to propagate to child scopes")


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


class UpdateRequest(BaseModel):
    text: str = Field(..., description="Free-form text describing which rule to update and how")


class UpdateIntent(BaseModel):
    rule_id: str = Field(..., description="ID of the rule to update")
    scope_type: ScopeType = Field(ScopeType.SITE, description="SITE, ACCOUNT, or GROUP")
    scope_id: str = Field(..., description="Scope ID")
    rule_name: str | None = None
    behavior: Behavior | None = None
    os_type: list[OsType] | None = None
    propagation: bool | None = None
    publisher: str | None = None
    path: str | None = None
    process: str | None = None
    parent_process: str | None = None
    sha256: str | None = None
    signer: str | None = None


class UpdateResponse(BaseModel):
    rule_id: str
    acm_response: dict[str, Any] | None = None
    clarification_needed: ClarificationNeeded | None = None


class DeleteRequest(BaseModel):
    text: str = Field(..., description="Free-form text describing which rule(s) to delete")


class DeleteIntent(BaseModel):
    rule_ids: list[str] = Field(..., description="Rule IDs to delete")
    scope_type: ScopeType = Field(..., description="SITE, ACCOUNT, or GROUP")
    scope_id: str = Field(..., description="Scope ID")


class DeleteResponse(BaseModel):
    deleted_ids: list[str]
    acm_response: dict[str, Any] | None = None
    clarification_needed: ClarificationNeeded | None = None
