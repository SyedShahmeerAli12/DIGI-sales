import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.auth import get_current_user
from app.services.rag_chain import answer_question, stream_answer

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, _user: str = Depends(get_current_user)):
    result = answer_question(body.message)
    return ChatResponse(answer=result["answer"], sources=result["sources"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(body: ChatRequest, _user: str = Depends(get_current_user)):
    def event_generator():
        for kind, payload in stream_answer(body.message):
            if kind == "sources":
                yield _sse_event("sources", {"sources": payload})
            else:
                yield _sse_event("token", {"text": payload})
        yield _sse_event("done", {})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
