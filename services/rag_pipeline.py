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
import os
import json
from concurrent.futures import ThreadPoolExecutor
from services.reranker import rerank
from services.query_expansion import expand_query_for_search
from config.rag_config import SIM_THRESHOLD, RERANK_THRESHOLD, MAX_CANDIDATES_FETCH



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
    3. Vector search: lấy kết quả theo ngưỡng SIM_THRESHOLD.
    4. Merge + deduplicate.
    5. Rerank: chấm lại toàn bộ ứng viên bằng search_query.
    6. Build context → Invoke LLM → Trả về kết quả.
    """

    # 1. Chạy song song: Query Expansion và Trích xuất tham chiếu luật
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_expansion = executor.submit(expand_query_for_search, question)
        future_refs = executor.submit(extract_legal_references, question)
        
        search_query = future_expansion.result()
        refs = future_refs.result()
        
    print(f"🚀 Expanded Query: {search_query}")
    
    # 2. Sinh song song tiếp: Keyword search và Embedding
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_kw = executor.submit(
            keyword_search, 
            articles=refs["articles"] or None, 
            chapters=refs["chapters"] or None
        )
        future_vec = executor.submit(get_embedding, search_query)
        
        kw_hits = future_kw.result()
        query_vec = future_vec.result()

    # 3. Vector search sơ bộ (lọc theo ngưỡng trực tiếp trong DB)
    vec_results = vector_search(query_vec, top_k=MAX_CANDIDATES_FETCH, threshold=SIM_THRESHOLD)

    # 4. Merge + deduplicate (Keyword hits luôn được giữ và đứng trước)
    seen_ids: set = set()
    candidates: list[dict] = []
    
    # Gộp kết quả
    chunks = kw_hits + vec_results
    for chunk in chunks:
        cid = chunk.get("id")
        if cid not in seen_ids:
            seen_ids.add(cid)
            candidates.append(chunk)

    # [DEBUG] Lưu candidates ra file JSON
    try:
        with open("debug_candidates.json", "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Failed to save debug_candidates.json: {e}")

    if not candidates:
        return {
            "answer":       f"Không tìm thấy tài liệu luật nào đủ độ tin cậy để trả lời câu hỏi này (Similarity < {SIM_THRESHOLD}).",
            "citations":    [],
            "chunks":       [],
            "candidates":   [],
            "search_query": search_query,
        }

    # 6. Rerank: lọc theo ngưỡng rerank_score >= 0.7
    chunks = rerank(search_query, candidates, score_threshold=RERANK_THRESHOLD)

    # [DEBUG] Lưu kết quả sau Rerank ra file JSON
    try:
        with open("debug_results.json", "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Failed to save debug_results.json: {e}")

    if not chunks:
        return {
            "answer":       f"Tìm thấy tài liệu liên quan nhưng độ chính xác không đủ cao (Rerank < {RERANK_THRESHOLD}) để đưa ra câu trả lời.",
            "citations":    [],
            "chunks":       [],
            "candidates":   candidates,
            "search_query": search_query,
        }

    # 7. Build context
    context = build_context(chunks)

    # 8. Trả về kết quả (Đã gỡ bỏ Streaming)
    citations = format_citations(chunks)
    
    # Chuẩn bị chain
    llm = get_llm()
    chain = RAG_PROMPT | llm | StrOutputParser()

    # [DEBUG] Lưu Prompt đầy đủ ra file TXT
    try:
        full_prompt_text = RAG_PROMPT.format(context=context, question=question)
        with open("debug_prompt.txt", "w", encoding="utf-8") as f:
            f.write(full_prompt_text)
    except Exception as e:
        print(f"⚠️ Failed to save debug_prompt.txt: {e}")

    answer = chain.invoke({"context": context, "question": question})
    
    return {
        "answer":       answer,
        "citations":    citations,
        "chunks":       chunks,
        "candidates":   candidates,
        "search_query": search_query,
    }
