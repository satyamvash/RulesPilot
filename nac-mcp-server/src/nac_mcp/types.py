"""Shared helpers for building GraphQL input types."""
import os
from typing import Any

# Default scope read from environment — tools use these when caller omits scope args.
# NAC_DEFAULT_SCOPE_TYPE: ACCOUNT | SITE | GROUP
# NAC_DEFAULT_SCOPE_IDS: comma-separated list of IDs, e.g. "123,456"
_DEFAULT_SCOPE_TYPE = os.environ.get("NAC_DEFAULT_SCOPE_TYPE", "")
_DEFAULT_SCOPE_IDS = [s.strip() for s in os.environ.get("NAC_DEFAULT_SCOPE_IDS", "").split(",") if s.strip()]


def resolve_scope(scope_type: str | None, scope_ids: list[str] | None) -> tuple[str, list[str]]:
    """Return (scope_type, scope_ids), falling back to env defaults if either is None/empty."""
    resolved_type = scope_type or _DEFAULT_SCOPE_TYPE
    resolved_ids = scope_ids if scope_ids else _DEFAULT_SCOPE_IDS
    if not resolved_type or not resolved_ids:
        raise ValueError(
            "scope_type and scope_ids are required. "
            "Pass them explicitly or set NAC_DEFAULT_SCOPE_TYPE and NAC_DEFAULT_SCOPE_IDS in .env"
        )
    return resolved_type, resolved_ids


def build_scope(scope_type: str | None = None, scope_ids: list[str] | None = None) -> dict:
    t, ids = resolve_scope(scope_type, scope_ids)
    return {"scopeType": t, "scopeIds": ids}


def build_pagination(size: int | None = None, cursor: str | None = None, direction: str | None = None) -> dict:
    p: dict[str, Any] = {}
    if size is not None:
        p["size"] = size
    if cursor:
        p["cursor"] = cursor
    if direction:
        p["direction"] = direction
    return p


def build_conditions(
    publisher: str | None = None,
    path: str | None = None,
    signer: str | None = None,
    sha256: str | None = None,
    process: str | None = None,
    parent_process: str | None = None,
    parent_label: str | None = None,
) -> dict:
    c: dict[str, Any] = {}
    if publisher is not None:
        c["publisher"] = publisher
    if path is not None:
        c["path"] = path
    if signer is not None:
        c["signer"] = signer
    if sha256 is not None:
        c["sha256"] = sha256
    if process is not None:
        c["process"] = process
    if parent_process is not None:
        c["parentProcess"] = parent_process
    if parent_label is not None:
        c["parentLabel"] = parent_label
    return c
