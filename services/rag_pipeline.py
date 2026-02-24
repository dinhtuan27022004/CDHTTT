"""
services/rag_pipeline.py – LangChain LCEL RAG pipeline
Pipeline: embed → (keyword search + vector search) → merge → rerank → build context → LLM → answer
"""

from __future__ import annotations
import re
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from models.embedding import get_embedding
from models.law_model import vector_search, keyword_search
from services.prompt_builder import RAG_PROMPT, build_context, format_citations
from services.openrouter_service import get_llm
from services.reranker import rerank


def extract_legal_references(question: str) -> dict[str, list[str]]:
    """
    Phát hiện các tham chiếu Chương/Điều cụ thể trong câu hỏi bằng regex.

    Ví dụ:
        "Điều 2 và Điều 185 quy định gì?"
        → {"articles": ["2", "185"], "chapters": []}

    Returns:
        Dict với keys: articles, chapters (list[str]).
    """
    # Điều X
    articles = re.findall(r"[đd]i[eềệểẹẻ]u\s+?(\d+)", question, re.IGNORECASE)

    # Chương X
    chapters = re.findall(r"ch[ưươ]ng\s+([\dIVXLivxl]+)", question, re.IGNORECASE)

    return {
        "articles": list(dict.fromkeys(articles)),   # deduplicate, giữ thứ tự
        "chapters": list(dict.fromkeys(chapters)),
    }


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
) -> dict[str, Any]:
    """
    Chạy toàn bộ RAG pipeline tự động dựa trên ngưỡng điểm số (Threshold-based).

    Quy trình:
    1. Embed câu hỏi.
    2. Keyword search: phát hiện Chương/Điều cụ thể → fetch DB (sim = 1.0).
    3. Vector search: lấy top 50 ứng viên gần nhất.
    4. Lọc & Merge:
       - Chỉ giữ ứng viên Vector có similarity >= 0.8.
       - Gộp với Keyword hits (nếu có).
    5. Rerank: chấm lại toàn bộ ứng viên, chỉ giữ kết quả có score >= 0.7.
    6. Build context → Invoke LLM → Trả về kết quả.

    Args:
        question: Câu hỏi của người dùng.

    Returns:
        {"answer": str, "citations": List[str], "chunks": List[dict], "candidates": List[dict]}
    """
    SIM_THRESHOLD = 0.7
    RERANK_THRESHOLD = 0.7
    MAX_CANDIDATES_FETCH = 50

    # 1. Embedding câu hỏi
    query_vec = get_embedding(question)

    # 2. Keyword search: phát hiện Chương/Điều trong câu hỏi
    refs = extract_legal_references(question)
    kw_hits = keyword_search(
        articles=refs["articles"] or None,
        chapters=refs["chapters"] or None,
    )
    if kw_hits:
        print(f"🔑 Keyword hits: {len(kw_hits)} chunks (articles={refs['articles']}, chapters={refs['chapters']})")

    # 3. Vector search sơ bộ (lấy mẫu rộng)
    vec_results = vector_search(query_vec, top_k=MAX_CANDIDATES_FETCH)

    # 4. Lọc theo ngưỡng similarity 0.8 cho kết quả vector
    vec_filtered = [c for c in vec_results if c.get("similarity", 0) >= SIM_THRESHOLD]

    # 5. Merge + deduplicate (Keyword hits luôn được giữ và đứng trước)
    seen_ids: set = set()
    candidates: list[dict] = []
    for chunk in kw_hits + vec_filtered:
        cid = chunk.get("id")
        if cid not in seen_ids:
            seen_ids.add(cid)
            candidates.append(chunk)

    if not candidates:
        return {
            "answer":    "Không tìm thấy tài liệu luật nào đủ độ tin cậy để trả lời câu hỏi này (Similarity < 0.8).",
            "citations": [],
            "chunks":    [],
            "candidates": [],
        }

    # 6. Rerank: lọc theo ngưỡng rerank_score >= 0.7
    chunks = rerank(question, candidates, score_threshold=RERANK_THRESHOLD)

    if not chunks:
        return {
            "answer":    "Tìm thấy tài liệu liên quan nhưng độ chính xác không đủ cao (Rerank < 0.7) để đưa ra câu trả lời.",
            "citations": [],
            "chunks":    [],
            "candidates": candidates,
        }

    # 7. Build context
    context = build_context(chunks)

    # 8. Invoke LCEL chain
    chain = _build_chain()
    answer = chain.invoke({"context": context, "question": question})

    # 9. Citations
    citations = format_citations(chunks)

    return {
        "answer":     answer,
        "citations":  citations,
        "chunks":     chunks,
        "candidates": candidates,   # danh sách bản ghi trước rerank
    }
