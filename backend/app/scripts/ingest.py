"""
Ingests the Source Question Q&A dataset (backend/data/source_questions_qa.json)
into Qdrant via LangChain. Each entry is one chunk: persona + category + question
+ answer. force_recreate=True drops and rebuilds the collection on every run, so
Qdrant only ever holds this dataset.

Run from backend/: python -m app.scripts.ingest
"""

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, RetrievalMode

from app.core.config import settings
from app.services.vector_store import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    get_embeddings,
    get_sparse_embeddings,
)

QA_PATH = Path(__file__).resolve().parents[2] / "data" / "source_questions_qa.json"
SOURCE_LABEL = "Source Question.docx"


def load_documents() -> list[Document]:
    entries = json.loads(QA_PATH.read_text(encoding="utf-8"))

    docs = []
    for entry in entries:
        text = (
            f"Persona: {entry['persona']}\n"
            f"Category: {entry['category']}\n"
            f"Q: {entry['question']}\n"
            f"A: {entry['answer']}"
        )
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": SOURCE_LABEL,
                    "persona": entry["persona"],
                    "category": entry["category"],
                    "question": entry["question"],
                },
            )
        )
    return docs


def run_ingestion(force_recreate: bool = True) -> int:
    documents = load_documents()
    print(f"Prepared {len(documents)} chunks from {QA_PATH.name}")

    QdrantVectorStore.from_documents(
        documents,
        embedding=get_embeddings(),
        sparse_embedding=get_sparse_embeddings(),
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        retrieval_mode=RetrievalMode.HYBRID,
        vector_name=DENSE_VECTOR_NAME,
        sparse_vector_name=SPARSE_VECTOR_NAME,
        force_recreate=force_recreate,
    )
    print(f"Ingested into Qdrant collection '{settings.qdrant_collection}'")
    return len(documents)


if __name__ == "__main__":
    run_ingestion()
