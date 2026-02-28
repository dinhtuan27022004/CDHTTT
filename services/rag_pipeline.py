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
import time
from services.reranker import rerank
from services.query_expansion import generate_similar_questions
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
    total_start = time.time()
    print(f"\n--- [RAG START] Question: {question} ---", flush=True)
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

    # 1. Trích xuất tham chiếu luật và Mở rộng câu hỏi thành nhiều câu tương tự
    refs = extract_legal_references(question)
    print(f"|-- [1/8] Refs Extraction: Articles={refs['articles']}, Chapters={refs['chapters']}", flush=True)
    
    t0 = time.time()
    all_queries = generate_similar_questions(question)
    time_expand = time.time() - t0
    print(f"|-- [2/8] Multi-Query Expansion: {len(all_queries)} queries generated ({time_expand:.2f}s)", flush=True)
    
    # 2. Keyword search (dựa trên câu hỏi gốc và các tham chiếu)
    kw_hits = keyword_search(
        articles=refs["articles"] or None, 
        chapters=refs["chapters"] or None
    )
    
    # 3. Vector search cho từng câu hỏi và gộp kết quả
    t1 = time.time()
    all_vec_results = []
    
    for idx, q in enumerate(all_queries):
        print(f"    |-- Vector searching query {idx+1}: {q[:60]}...", flush=True)
        q_vec = get_embedding(q)
        q_results = vector_search(q_vec, top_k=MAX_CANDIDATES_FETCH, threshold=SIM_THRESHOLD)
        all_vec_results.extend(q_results)
    all_vec_results.sort(key=lambda x: x["similarity"], reverse=True)
    time_vector = time.time() - t1
    print(f"|-- [4/8] Multi-Vector Search: {len(all_vec_results)} raw results total ({time_vector:.2f}s)", flush=True)

    # 4. Merge + deduplicate (ưu tiên kết quả keyword search, sau đó là vector search)
    seen_ids: set = set()
    candidates: list[dict] = []
    
    # Gộp kết quả, lọc trùng theo ID
    for chunk in (kw_hits + all_vec_results):
        cid = chunk.get("id")
        if cid not in seen_ids:
            seen_ids.add(cid)
            candidates.append(chunk)

    print(f"|-- [5/8] Combined & Deduplicated: {len(candidates)} unique candidates", flush=True)

    # [DEBUG] Lưu candidates ra file JSON
    try:
        with open("debug_candidates.json", "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"|-- Warning: Failed to save debug_candidates.json: {e}", flush=True)

    if not candidates:
        return {
            "answer":       f" Không tìm thấy tài liệu luật nào đủ độ tin cậy để trả lời câu hỏi này (Similarity < {SIM_THRESHOLD}).",
            "citations":    [],
            "chunks":       [],
            "candidates":   [],
            "search_query": all_queries,
            "timings": {
                "expand": time_expand,
                "vector": time_vector,
                "rerank": 0.0,
                "total": time.time() - total_start
            }
        }

    # 6. Rerank: Sử dụng TẤT CẢ các câu hỏi đã mở rộng (nối lại) để chấm điểm
    combined_query = " ".join(all_queries)
    t2 = time.time()
    chunks = rerank(combined_query, candidates, score_threshold=RERANK_THRESHOLD)
    time_rerank = time.time() - t2
    print(f"|-- [6/8] Reranking (using combined queries): {len(chunks)} chunks kept ({time_rerank:.2f}s)", flush=True)

    # [DEBUG] Lưu kết quả sau Rerank ra file JSON
    try:
        with open("debug_results.json", "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"|-- Warning: Failed to save debug_results.json: {e}", flush=True)

    if not chunks:
        return {
            "answer":       f"Tìm thấy tài liệu liên quan nhưng độ chính xác không đủ cao (Rerank < {RERANK_THRESHOLD}) để đưa ra câu trả lời.",
            "citations":    [],
            "chunks":       [],
            "candidates":   candidates,
            "search_query": all_queries,
            "timings": {
                "expand": time_expand,
                "vector": time_vector,
                "rerank": time_rerank,
                "total": time.time() - total_start
            }
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
        print(f"|-- Warning: Failed to save debug_prompt.txt: {e}", flush=True)

    print(f"|-- [7/8] Invoking LLM...", flush=True)
    answer = chain.invoke({"context": context, "question": question})
    print(f"|-- [8/8] RAG Complete. Response Length: {len(answer)} chars", flush=True)
    
    return {
        "answer":       answer,
        "citations":    citations,
        "chunks":       chunks,
        "candidates":   candidates,
        "search_query": all_queries,
        "timings": {
            "expand": time_expand,
            "vector": time_vector,
            "rerank": time_rerank,
            "total": time.time() - total_start
        }
    }
