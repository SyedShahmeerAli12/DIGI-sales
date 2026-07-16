from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.routers.auth import get_current_user
from app.services.voice import synthesize_speech, transcribe_audio

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SpeakRequest(BaseModel):
    text: str


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    _user: str = Depends(get_current_user),
):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    text = transcribe_audio(data, audio.filename or "recording.webm")
    return {"text": text}


@router.post("/speak")
async def speak(body: SpeakRequest, _user: str = Depends(get_current_user)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")
    audio_bytes = synthesize_speech(body.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
