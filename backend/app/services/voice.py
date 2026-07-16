from functools import lru_cache
from io import BytesIO

from openai import OpenAI

from app.core.config import settings


@lru_cache
def get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Speech-to-text via OpenAI's transcription model. Auto-detects language
    (English or Urdu) — no language hint needed."""
    client = get_openai_client()
    audio_file = BytesIO(file_bytes)
    audio_file.name = filename or "recording.webm"
    result = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
    )
    return result.text


def synthesize_speech(text: str) -> bytes:
    """Text-to-speech via OpenAI's TTS model. Reads the given text (English or
    Urdu) aloud in the same language it's written in."""
    client = get_openai_client()
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text,
    )
    return response.read()
