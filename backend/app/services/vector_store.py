import time
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from qdrant_client import QdrantClient

from app.core.config import settings

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model, api_key=settings.openai_api_key
    )


@lru_cache
def get_sparse_embeddings() -> FastEmbedSparse:
    # Rule-based BM25 sparse embeddings — no weights to download, deterministic.
    return FastEmbedSparse(model_name="Qdrant/bm25")


@lru_cache
def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


def wait_for_qdrant(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    """Blocks until Qdrant answers, so backend startup doesn't race the container."""
    client = get_qdrant_client()
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            client.get_collections()
            return
        except Exception as exc:  # noqa: BLE001 - any failure means "not ready yet"
            last_error = exc
            print(f"Waiting for Qdrant ({attempt}/{max_attempts})...")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Qdrant never became reachable at {settings.qdrant_url}") from last_error


def collection_exists() -> bool:
    client = get_qdrant_client()
    try:
        client.get_collection(settings.qdrant_collection)
        return True
    except Exception:  # noqa: BLE001 - not found or unreachable both mean "no"
        return False


def get_vector_store() -> QdrantVectorStore:
    """Hybrid (dense + sparse/BM25) Qdrant-backed LangChain vector store."""
    if collection_exists():
        return QdrantVectorStore.from_existing_collection(
            collection_name=settings.qdrant_collection,
            url=settings.qdrant_url,
            embedding=get_embeddings(),
            sparse_embedding=get_sparse_embeddings(),
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name=DENSE_VECTOR_NAME,
            sparse_vector_name=SPARSE_VECTOR_NAME,
        )

    # No collection yet — created lazily on first ingestion run via from_documents.
    raise RuntimeError(
        f"Qdrant collection '{settings.qdrant_collection}' does not exist yet. "
        "Run the ingestion script first: python -m app.scripts.ingest"
    )
