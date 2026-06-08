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

    Flow:
    - If all required fields are present → creates the rule in ACM and returns it.
    - If any required field is missing → returns clarification_needed with questions.
    - If dry_run=true → returns parsed intent only, no ACM call.

    Required fields (must be in the text or clarification is requested):
      rule_name, behavior (ALLOW/BLOCK), os_type, scope_ids,
      and at least one of: publisher, path, process, parent_process, sha256, signer.
    """
    if len(request.text) > settings.max_input_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    # Extract structured intent from natural language
    result = interpreter.interpret(request.text)

    # Return clarification questions to the caller — no ACM call made
    if isinstance(result, ClarificationNeeded):
        logger.info(
            "Clarification needed — missing fields: %s | questions: %s",
            result.missing_fields,
            result.questions,
        )
        return InterpretResponse(clarification_needed=result)

    # Dry run — return intent without hitting ACM
    if request.dry_run:
        logger.info("Dry run — returning intent without creating rule.")
        return InterpretResponse(intent=result, dry_run=True)

    # Create the rule via ACM GraphQL
    created = await acm_client.create_rule(result, bearer_token=token)
    logger.info("Rule created successfully in ACM.")

    return InterpretResponse(intent=result, created_rule=created)
