import json
import re
from functools import lru_cache
from pathlib import Path

from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services import sql_chain
from app.services.vector_store import (
    DENSE_VECTOR_NAME,
    get_chat_model,
    get_embeddings,
    get_qdrant_client,
    get_vector_store,
)

QA_PATH = Path(__file__).resolve().parents[2] / "data" / "source_questions_qa.json"
HISTORY_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "chat_history.db"

SYSTEM_PROMPT = """You are DIGI, an Intelligent Sales Supervisor assistant for DigiTrends field sales staff.

Rules you must follow:
- Answer using ONLY the retrieved knowledge base context below. Never use outside/general knowledge, training data, or plausible-sounding assumptions to fill a gap the context doesn't cover — this applies to every topic, not just numbers.
- Before answering, check whether the context actually addresses what was asked. If it doesn't, say plainly that the knowledge base doesn't cover this topic and stop there — do not still produce a reasonable-sounding answer from general knowledge just because you're capable of one.
- Do not invent sales figures, policies, names, or any other fact not present in the context.
- Clearly distinguish confirmed facts from recommendations and unverified market feedback.
- Be actionable for a field user, but never answer in a single terse line — even a simple factual question should get at least 3-4 lines of context (what the number/fact is, and a bit of relevant context like comparison, trend, or what it means), not just the bare answer.
- Always answer in the same language the user asked in. If the question is in Urdu (Urdu script or Roman Urdu), answer fully in Urdu, applying the exact same facts, context, and policy logic you would use in English — never a shorter or vaguer answer just because the language changed. If the question is in English, answer in English.

Formatting rules:
- Always respond in Markdown, never as a raw wall of text.
- Use bullet lists for multiple items (documents, SKUs, outlets, steps).
- Use a Markdown table whenever the answer involves a ranking, comparison, or any list of items each with more than one attribute (e.g. name + value, multiple SKUs with their figures) — a table is easier to scan than bullets for that shape of data.
- Use short bold labels (e.g. **Target:**) for key figures when it improves scannability.
- Use a heading for any answer with more than one part (e.g. a daily summary, a ranking, a comparison); skip it only for a single standalone fact.
- Never put a name or term in quotation marks — whenever you'd naturally quote something (a product/SKU/brand/distributor/employee name, a specific term), wrap it in Markdown bold (**like this**) instead.

Context from the knowledge base:
{context}"""

QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's question into a short, retrieval-optimized search query "
            "for a sales knowledge base (outlets, SKUs, promotions, targets, route plans, "
            "competitor intel, policy, FAQ). Expand abbreviations and vague references. "
            "Return only the rewritten query, nothing else.",
        ),
        ("human", "{question}"),
    ]
)

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)

# Broad/aggregate questions ("summarize", "how many outlets total") retrieve more
# chunks so a single section isn't under-represented; specific lookups stay tight.
BROAD_KEYWORDS = (
    "summar",
    "all outlets",
    "how many",
    "overview",
    "review",
    "compare",
    "every",
    "total",
)


def _top_k_for(question: str) -> int:
    lowered = question.lower()
    return 20 if any(kw in lowered for kw in BROAD_KEYWORDS) else 8


SOURCE_LABEL = "Source Question.docx"


def _rewrite_query(question: str) -> str:
    chain = QUERY_REWRITE_PROMPT | get_chat_model() | StrOutputParser()
    return chain.invoke({"question": question}).strip()


def _retrieve(question: str):
    rewritten = _rewrite_query(question)
    retriever = get_vector_store().as_retriever(
        search_kwargs={"k": _top_k_for(question)}
    )
    return retriever.invoke(rewritten)


def _format_docs(docs) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def _sources_for(docs) -> list[dict]:
    """The top retrieval hit is the strongest match for the question, so the
    citation points at its exact page in source_questions_qa.pdf."""
    if not docs:
        return [{"label": SOURCE_LABEL, "page": 1}]
    top_page = docs[0].metadata.get("page", 1)
    return [{"label": SOURCE_LABEL, "page": top_page}]


def answer_question(question: str) -> dict:
    docs = _retrieve(question)
    context = _format_docs(docs)

    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context})

    return {"answer": answer, "sources": _sources_for(docs)}


def stream_answer(question: str):
    """Yields ('sources', list[dict]) once, then ('token', str) per generated chunk."""
    docs = _retrieve(question)
    context = _format_docs(docs)

    yield "sources", _sources_for(docs)

    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    for chunk in chain.stream({"question": question, "context": context}):
        if chunk:
            yield "token", chunk


# Below FAQ_MATCH_THRESHOLD, try the analytical SQL path first. Deliberately
# biased toward attempting SQL: if SQL can't answer confidently it falls back
# to the FAQ answer anyway (verified safety net), so a wrong "try SQL first"
# guess just costs one extra generation attempt. Going straight to FAQ has no
# equivalent fallback to SQL, so that mistake is unrecoverable — e.g. "What
# was our total revenue in Karachi?" scored 0.6174 against the unrelated FAQ
# question "Which city generated highest revenue?" and would have returned a
# non-answer despite the real number being available from the SQL database.
FAQ_MATCH_THRESHOLD = 0.72
SQL_SOURCE_LABEL = "FMCG Sales Database"


def _faq_match_score(question: str) -> float:
    vec = get_embeddings().embed_query(question)
    results = get_qdrant_client().query_points(
        settings.qdrant_collection, query=vec, using=DENSE_VECTOR_NAME, limit=1
    ).points
    return results[0].score if results else 0.0


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


@lru_cache
def _known_faq_questions() -> frozenset[str]:
    entries = json.loads(QA_PATH.read_text(encoding="utf-8"))
    return frozenset(_normalize(e["question"]) for e in entries)


def _is_known_faq_question(question: str) -> bool:
    """Exact/near-exact match (case/punctuation-insensitive) against the 165
    curated FAQ questions — guaranteed, zero-risk routing for questions we
    already have a validated answer for, bypassing embedding-score ambiguity
    entirely (see FAQ_MATCH_THRESHOLD's note on 'requires management
    attention' scoring low enough to otherwise get a worse SQL-derived answer
    for a fundamentally subjective question)."""
    return _normalize(question) in _known_faq_questions()


class _StandaloneQuestion(BaseModel):
    """Structured rewrite output — the model must explicitly declare whether
    it actually used the history, rather than us reverse-engineering that by
    diffing text afterward. Two plain-text prompt variants (both official
    LangChain references) silently pulled the previous turn's city/channel
    into unrelated new questions on both GPT-4o and Llama-3.3-70b (verified:
    "How many customers are in the Modern Trade channel?" right after a
    Lahore question came back with "in Lahore" appended, out of nowhere).
    Forcing a structured, self-reported decision is the framework-native fix,
    not a hand-rolled keyword/regex guess about what the model was doing."""

    used_history: bool = Field(
        description="True only if answering this question actually requires "
        "resolving something from the prior conversation (a pronoun, 'what "
        "about X', an implicit continuation of the same topic). False if the "
        "question is already fully self-contained on its own."
    )
    standalone_question: str = Field(
        description="The question rewritten to be standalone. If used_history "
        "is False, this MUST be the original question, completely unchanged — "
        "do not add any scope, place, or category it didn't already have."
    )


REPHRASE_PROMPT = ChatPromptTemplate.from_template(
    "Given a chat history and the latest user question which might reference "
    "context in the chat history, decide whether the question actually needs "
    "the chat history to be understood, and formulate a standalone version.\n\n"
    "Chat History:\n{chat_history}\n"
    "Latest question: {input}"
)

# Only the most recent exchange is passed in — not the whole growing
# conversation — since even a single prior turn was enough to get spuriously
# carried into an unrelated new question during testing.
CONTEXTUALIZE_HISTORY_MESSAGES = 2  # last question + its answer


def _get_history(session_id: str) -> SQLChatMessageHistory:
    return SQLChatMessageHistory(
        session_id=session_id, connection=f"sqlite:///{HISTORY_DB_PATH}"
    )


def _format_history(messages) -> str:
    return "\n".join(
        f"{'Human' if m.type == 'human' else 'Assistant'}: {m.content}" for m in messages
    )


def _resolve_standalone_question(question: str, session_id: str | None) -> str:
    """Mirrors create_history_aware_retriever's own branch: no history means
    no rewrite at all — the question is used exactly as typed, never passed
    through the LLM, so there's zero chance of it injecting anything."""
    if not session_id:
        return question
    history = _get_history(session_id).messages
    if not history:
        return question
    recent_history = history[-CONTEXTUALIZE_HISTORY_MESSAGES:]
    chain = REPHRASE_PROMPT | get_chat_model().with_structured_output(_StandaloneQuestion)
    result: _StandaloneQuestion = chain.invoke(
        {"chat_history": _format_history(recent_history), "input": question}
    )
    if not result.used_history:
        return question
    return result.standalone_question


def answer(question: str, session_id: str | None = None) -> dict:
    """Routes to the FAQ knowledge base when the question closely matches an
    existing entry; otherwise tries the FMCG analytical database. Falls back
    to the FAQ answer (never a guess) if SQL can't answer confidently."""
    standalone = _resolve_standalone_question(question, session_id)

    if _is_known_faq_question(standalone) or _faq_match_score(standalone) >= FAQ_MATCH_THRESHOLD:
        result = answer_question(standalone)
    else:
        sql_result = sql_chain.answer_analytical_question(standalone)
        if sql_result is not None:
            result = {
                "answer": sql_result["answer"],
                "sources": [{"label": SQL_SOURCE_LABEL, "query": sql_result["sql"]}],
            }
        else:
            result = answer_question(standalone)

    if session_id:
        history = _get_history(session_id)
        history.add_user_message(question)
        history.add_ai_message(result["answer"])
    return result


def stream(question: str, session_id: str | None = None):
    """Same routing as answer(), but streaming."""
    standalone = _resolve_standalone_question(question, session_id)
    full_answer_parts: list[str] = []

    def _record(chunk: str):
        full_answer_parts.append(chunk)
        return "token", chunk

    if _is_known_faq_question(standalone) or _faq_match_score(standalone) >= FAQ_MATCH_THRESHOLD:
        for kind, payload in stream_answer(standalone):
            yield (kind, payload) if kind != "token" else _record(payload)
    else:
        executed = sql_chain.generate_and_execute(standalone)
        if executed is not None:
            yield "sources", [{"label": SQL_SOURCE_LABEL, "query": executed["sql"]}]
            for chunk in sql_chain.stream_analytical_answer(
                standalone, executed["sql"], executed["result_text"]
            ):
                yield _record(chunk)
        else:
            for kind, payload in stream_answer(standalone):
                yield (kind, payload) if kind != "token" else _record(payload)

    if session_id:
        history = _get_history(session_id)
        history.add_user_message(question)
        history.add_ai_message("".join(full_answer_parts))
