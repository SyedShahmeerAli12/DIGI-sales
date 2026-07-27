from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/sources", tags=["sources"])

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@router.get("/source-question")
async def get_source_question_document(_user: str = Depends(get_current_user)):
    path = DATA_DIR / "source_questions_qa.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Source document not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="Source Question.pdf",
    )
