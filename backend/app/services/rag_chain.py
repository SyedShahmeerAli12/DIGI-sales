from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.services.vector_store import get_chat_model, get_vector_store

SYSTEM_PROMPT = """You are DIGI, an Intelligent Sales Supervisor assistant for DigiTrends field sales staff.

Rules you must follow:
- Answer using only the retrieved knowledge base context below. Do not invent sales figures, policy, or facts not present in the context.
- Clearly distinguish confirmed facts from recommendations and unverified market feedback.
- Never authorize a commercial exception (extra discount, free goods, credit terms) that is outside documented policy.
- Keep answers concise and actionable for a field user; provide deeper detail only if the question asks for analysis or a summary.
- If the context does not contain the answer, say so plainly instead of guessing.

Formatting rules:
- Always respond in Markdown, never as a raw wall of text.
- Use bullet lists for multiple items (documents, SKUs, outlets, steps).
- Use short bold labels (e.g. **Target:**) for key figures when it improves scannability.
- Use a heading only for genuinely multi-part answers (e.g. a daily summary); skip it for a single fact.

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


# Retrieved chunks come from many different section tables even for a narrow
# question (hybrid search pulls in loosely related rows). Rather than exposing
# that internal retrieval detail as a citation list, every answer is attributed
# to a single constant source.
CONSTANT_SOURCE = "Internal Knowledge"


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


def answer_question(question: str) -> dict:
    docs = _retrieve(question)
    context = _format_docs(docs)

    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    answer = chain.invoke({"question": question, "context": context})

    return {"answer": answer, "sources": [CONSTANT_SOURCE]}


def stream_answer(question: str):
    """Yields ('sources', list[str]) once, then ('token', str) per generated chunk."""
    docs = _retrieve(question)
    context = _format_docs(docs)

    yield "sources", [CONSTANT_SOURCE]

    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    for chunk in chain.stream({"question": question, "context": context}):
        if chunk:
            yield "token", chunk
