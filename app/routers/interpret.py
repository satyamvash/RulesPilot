import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.models.rule import ClarificationNeeded, InterpretRequest, InterpretResponse
from app.services import acm_client, interpreter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/nac-rules", tags=["NAC Rules"])


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_rule(
    request: InterpretRequest,
    authorization: str = Header(..., description="Bearer <token>"),
) -> InterpretResponse:
    """
    Interpret free-form text and create a NAC rule.

    - Returns 200 with `intent` + `created_rule` on success.
    - Returns 200 with `clarification_needed` when required fields are missing.
    - Set `dry_run=true` to get the parsed intent without creating the rule.
    """
    if len(request.text) > settings.max_input_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters.",
        )

    # Strip "Bearer " prefix if present
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    # Extract structured intent from natural language
    result = interpreter.interpret(request.text)

    if isinstance(result, ClarificationNeeded):
        logger.info("Clarification needed: missing_fields=%s", result.missing_fields)
        return InterpretResponse(clarification_needed=result)

    # Dry run — return intent without hitting ACM
    if request.dry_run:
        return InterpretResponse(intent=result, dry_run=True)

    # Create the rule via ACM GraphQL
    created = await acm_client.create_rule(result, bearer_token=token)
    logger.info("Rule created successfully: id=%s", created.get("id"))

    return InterpretResponse(intent=result, created_rule=created)
