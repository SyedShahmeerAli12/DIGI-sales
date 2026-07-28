import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.auth import get_current_user
from app.services.rag_chain import answer, stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class SourceRef(BaseModel):
    label: str
    # FAQ-sourced answers cite a PDF page; SQL-sourced answers cite the query
    # that was run instead — exactly one of the two is set.
    page: int | None = None
    query: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, _user: str = Depends(get_current_user)):
    try:
        result = answer(body.message, session_id=body.session_id)
    except Exception:
        logger.exception("chat request failed")
        raise HTTPException(
            status_code=502, detail="The assistant couldn't answer that just now."
        )
    return ChatResponse(answer=result["answer"], sources=result["sources"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(body: ChatRequest, _user: str = Depends(get_current_user)):
    def event_generator():
        try:
            for kind, payload in stream(body.message, session_id=body.session_id):
                if kind == "sources":
                    yield _sse_event("sources", {"sources": payload})
                else:
                    yield _sse_event("token", {"text": payload})
        except Exception:
            # A mid-stream failure (e.g. an OpenAI outage/quota error) would
            # otherwise abort the HTTP response with no explanation, which the
            # browser just reports as a raw network error — send a proper
            # error event instead so the UI can show something readable.
            logger.exception("chat stream failed")
            yield _sse_event(
                "error", {"message": "Something went wrong. Please try again."}
            )
            return
        yield _sse_event("done", {})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
