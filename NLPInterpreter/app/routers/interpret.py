import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.models.rule import ClarificationNeeded, DeleteRequest, DeleteResponse, InterpretRequest, InterpretResponse, UpdateRequest, UpdateResponse
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


@router.post("/delete", response_model=DeleteResponse)
async def delete_rule(
    request: DeleteRequest,
    authorization: str = Header(..., description="Bearer <token>"),
) -> DeleteResponse:
    """
    Delete NAC rule(s) from natural language text.

    Examples:
    - "Delete rule 126 from site 2440012200350466160"
    - "Remove rules 125 and 126 in site 2440012200350466160"
    """
    if len(request.text) > settings.max_input_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    result = interpreter.interpret_delete(request.text)

    if isinstance(result, ClarificationNeeded):
        logger.info("Delete clarification needed: %s", result.missing_fields)
        return DeleteResponse(deleted_ids=[], clarification_needed=result)

    acm_response = await acm_client.delete_rules(result, bearer_token=token)
    logger.info("Rules deleted successfully: ids=%s", result.rule_ids)

    return DeleteResponse(deleted_ids=result.rule_ids, acm_response=acm_response)


@router.post("/update", response_model=UpdateResponse)
async def update_rule(
    request: UpdateRequest,
    authorization: str = Header(..., description="Bearer <token>"),
) -> UpdateResponse:
    """
    Update an existing NAC rule from natural language text.

    Examples:
    - "Change rule 126 in site 2440012200350466160 to allow instead of block"
    - "Rename rule 125 in site 2440012200350466160 to 'Safe Publisher'"
    - "Update rule 126 in site 2440012200350466160 to also apply on MacOS"
    """
    if len(request.text) > settings.max_input_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    result = interpreter.interpret_update(request.text)

    if isinstance(result, ClarificationNeeded):
        logger.info("Update clarification needed: %s", result.missing_fields)
        return UpdateResponse(rule_id="", clarification_needed=result)

    acm_response = await acm_client.update_rule(result, bearer_token=token)
    logger.info("Rule %s updated successfully.", result.rule_id)

    return UpdateResponse(rule_id=result.rule_id, acm_response=acm_response)
