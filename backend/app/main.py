from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, chat, sources, voice
from app.scripts.ingest import run_ingestion
from app.services.sql_chain import get_vanna
from app.services.vector_store import collection_exists, wait_for_qdrant


@asynccontextmanager
async def lifespan(_app: FastAPI):
    wait_for_qdrant()
    if not collection_exists():
        print("Knowledge base collection not found — running ingestion...")
        run_ingestion(force_recreate=False)
    get_vanna()  # trains the FMCG SQL schema into Qdrant on first run, no-ops after
    yield


app = FastAPI(title="DIGI Sales Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(sources.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
