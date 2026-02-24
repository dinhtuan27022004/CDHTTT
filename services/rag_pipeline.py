"""
services/rag_pipeline.py – LangChain LCEL RAG pipeline
Pipeline: embed → vector search → build context → ChatPromptTemplate | LLM → answer
"""

from __future__ import annotations
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from models.embedding import get_embedding
from models.law_model import vector_search
from services.prompt_builder import RAG_PROMPT, build_context, format_citations
from services.openrouter_service import get_llm


def _build_chain():
    """
    Xây dựng LCEL chain cho RAG.

    Luồng:
        {"context": ..., "question": ...}
        → RAG_PROMPT
        → ChatOpenAI (OpenRouter)
        → StrOutputParser
    """
    llm = get_llm()
    chain = RAG_PROMPT | llm | StrOutputParser()
    return chain


def run_rag(
    question: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Chạy toàn bộ RAG pipeline qua LangChain LCEL.

    1. Embed câu hỏi (LangChain OpenAIEmbeddings)
    2. Vector search top-K (pgvector)
    3. Build context string
    4. Invoke LCEL chain: prompt | ChatOpenAI | StrOutputParser
    5. Trả về answer + citations + chunks thô

    Args:
        question: Câu hỏi của người dùng.
        field:    Lĩnh vực luật lọc (None = tất cả).
        top_k:    Số chunks context.

    Returns:
        {"answer": str, "citations": List[str], "chunks": List[dict]}
    """
    # 1. Embedding câu hỏi
    query_vec = get_embedding(question)

    # 2. Vector search
    chunks = vector_search(query_vec, top_k=top_k)

    if not chunks:
        return {
            "answer":    "Không tìm thấy trong dữ liệu luật hiện có.",
            "citations": [],
            "chunks":    [],
        }

    # 3. Build context
    context = build_context(chunks)

    # 4. Invoke LCEL chain
    chain = _build_chain()
    answer = chain.invoke({"context": context, "question": question})

    # 5. Citations
    citations = format_citations(chunks)

    return {
        "answer":    answer,
        "citations": citations,
        "chunks":    chunks,
    }
