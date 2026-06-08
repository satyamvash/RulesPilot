import logging

from fastapi import APIRouter, Header, HTTPException, Query, UploadFile, status

from app.config import settings
from app.models.rule import ClarificationNeeded, InterpretRequest, InterpretResponse
from app.services import acm_client, interpreter, transcriber

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/nac-rules", tags=["NAC Rules"])


def _run_interpret_flow(
    text: str,
    token: str,
) -> tuple[str, "ClarificationNeeded | None", "InterpretResponse | None"]:
    """
    Shared helper: validate input length, run the interpreter.
    Returns (text, clarification_or_none, final_response_or_none).
    """
    if len(text) > settings.max_input_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input exceeds maximum length of {settings.max_input_length} characters.",
        )
    return text, None, None


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_rule(
    request: InterpretRequest,
    authorization: str = Header(..., description="Bearer <token>"),
) -> InterpretResponse:
    """
    Interpret free-form **text** and create a NAC rule.

    Flow:
    - All required fields present → creates rule in ACM and returns it.
    - Any required field missing  → returns clarification_needed with questions.
    - dry_run=true                → returns parsed intent only, no ACM call.

    Required fields:
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

    return await _interpret_and_respond(request.text, token, request.dry_run)


@router.post("/interpret/voice", response_model=InterpretResponse)
async def interpret_rule_from_voice(
    file: UploadFile,
    authorization: str = Header(..., description="Bearer <token>"),
    dry_run: bool = Query(False, description="If true, return parsed intent without creating rule"),
) -> InterpretResponse:
    """
    Transcribe an **audio file** and create a NAC rule from the spoken content.

    Accepts: mp3, mp4, wav, m4a, ogg, flac, webm
    Max size: 25MB

    The audio is transcribed locally using Whisper (offline — no external calls).
    The transcribed text is then passed through the same interpreter pipeline as /interpret.

    Use dry_run=true to see the transcription + parsed intent without creating a rule.
    """
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    # Validate file is provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No file provided.",
        )

    # Read and size-check the audio
    audio_bytes = await file.read()
    max_bytes = 25 * 1024 * 1024  # 25MB
    if len(audio_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file too large. Maximum size is 25MB.",
        )

    # Transcribe audio → text
    try:
        text = transcriber.transcribe(audio_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    logger.info("Voice input transcribed: '%s'", text)

    return await _interpret_and_respond(text, token, dry_run, transcribed_from=file.filename)


async def _interpret_and_respond(
    text: str,
    token: str,
    dry_run: bool,
    transcribed_from: str | None = None,
) -> InterpretResponse:
    """
    Shared logic: run interpreter → handle clarification / dry-run / ACM call.
    """
    result = interpreter.interpret(text)

    if isinstance(result, ClarificationNeeded):
        logger.info(
            "Clarification needed — missing: %s | source: %s",
            result.missing_fields,
            transcribed_from or "text",
        )
        return InterpretResponse(clarification_needed=result)

    if dry_run:
        logger.info("Dry run — intent parsed, no ACM call. source=%s", transcribed_from or "text")
        return InterpretResponse(intent=result, dry_run=True)

    created = await acm_client.create_rule(result, bearer_token=token)
    logger.info("Rule created successfully in ACM. source=%s", transcribed_from or "text")

    return InterpretResponse(intent=result, created_rule=created)
