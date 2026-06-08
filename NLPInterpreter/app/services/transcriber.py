"""
Local speech-to-text transcription using OpenAI Whisper (offline).
The model is loaded once at startup and reused across requests.
No external API calls — runs entirely on this machine.

Model size guide (set WHISPER_MODEL in .env):
  tiny   (~150MB) — fastest, good for clear speech
  base   (~300MB) — slightly more accurate
  small  (~500MB) — good balance of speed and accuracy
  medium (~1.5GB) — highest accuracy, slower
"""

import logging
import tempfile
from pathlib import Path

import whisper

from app.config import settings

logger = logging.getLogger(__name__)

# Supported audio formats by Whisper via ffmpeg
SUPPORTED_FORMATS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".webm"}

# Load model once at module import — reused for all requests
logger.info("Loading Whisper model '%s' — this may take a moment on first run...", settings.whisper_model)
_model = whisper.load_model(settings.whisper_model)
logger.info("Whisper model '%s' loaded successfully.", settings.whisper_model)


def transcribe(audio_bytes: bytes, filename: str) -> str:
    """
    Transcribe audio bytes to text using the local Whisper model.

    Args:
        audio_bytes: Raw audio file content.
        filename: Original filename — used to determine audio format extension.

    Returns:
        Transcribed text string.

    Raises:
        ValueError: If the file format is not supported or transcription is empty.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format '{suffix}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    # Write to a temp file — Whisper requires a file path, not bytes
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    logger.info("Transcribing audio file: filename=%s size=%d bytes", filename, len(audio_bytes))

    try:
        result = _model.transcribe(tmp_path, language="en", fp16=False)
        text: str = result["text"].strip()
    finally:
        # Always clean up the temp file
        Path(tmp_path).unlink(missing_ok=True)

    if not text:
        raise ValueError("Transcription returned empty text — audio may be silent or unclear.")

    logger.info("Transcription result: %s", text)
    return text
