"""
services/reranker.py – Reranking sử dụng BAAI/bge-reranker-v2-m3
Chấm điểm lại các chunk sau Vector Search để cải thiện độ chính xác.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Any

# Model name – có thể thay bằng model nhẹ hơn nếu cần tốc độ
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _get_reranker():
    """Load model một lần duy nhất, cache lại để tái sử dụng."""
    from sentence_transformers import CrossEncoder
    print(f"⏳ Đang tải Reranker model: {RERANKER_MODEL}...")
    model = CrossEncoder(RERANKER_MODEL, max_length=512)
    print(f"✅ Reranker đã sẵn sàng.")
    return model


def rerank(
    question: str,
    chunks: list[dict[str, Any]],
    top_k: int | None = None,
    score_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """
    Sắp xếp lại danh sách chunks dựa trên điểm Reranker và lọc theo ngưỡng.

    Args:
        question:        Câu hỏi của người dùng.
        chunks:          Danh sách chunk từ vector search (top-N bước sơ bộ).
        top_k:           Số lượng tối đa chunk giữ lại (Optional).
        score_threshold: Ngưỡng điểm tối thiểu để giữ lại chunk (mặc định 0.7).

    Returns:
        Danh sách chunk đã được rerank và lọc, sắp xếp theo điểm giảm dần.
    """
    if not chunks:
        return []

    model = _get_reranker()

    # Tạo cặp (câu hỏi, nội dung chunk) để chấm điểm
    pairs = [(question, chunk.get("content", "")) for chunk in chunks]
    scores = model.predict(pairs)

    # Gắn điểm reranker vào từng chunk
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    # Lọc theo ngưỡng và sắp xếp
    reranked = [c for c in chunks if c["rerank_score"] >= score_threshold]
    reranked.sort(key=lambda c: c["rerank_score"], reverse=True)

    if top_k is not None:
        return reranked[:top_k]
    return reranked
