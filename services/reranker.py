"""
services/reranker.py – Reranking sử dụng BAAI/bge-reranker-v2-m3
Chấm điểm lại các chunk sau Vector Search để cải thiện độ chính xác.
"""
from typing import Any

# Model name – có thể thay bằng model nhẹ hơn nếu cần tốc độ
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


import streamlit as st

@st.cache_resource
def _get_reranker():
    """Load model một lần duy nhất và giữ lại trong bộ nhớ Streamlit."""
    from sentence_transformers import CrossEncoder
    print(f"--- Loading Reranker model: {RERANKER_MODEL}...", flush=True)
    model = CrossEncoder(RERANKER_MODEL, max_length=512)
    print(f"--- Reranker is ready.", flush=True)
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

    # Sắp xếp toàn bộ theo điểm giảm dần
    chunks.sort(key=lambda c: c["rerank_score"], reverse=True)

    # Lấy các chunk đạt ngưỡng
    reranked = [c for c in chunks if c["rerank_score"] >= score_threshold]

    # Cơ chế Fallback: Nếu quá ít kết quả đạt ngưỡng ( < 5), lấy ít nhất 5 cái tốt nhất
    MIN_RESULTS = 5
    if len(reranked) < MIN_RESULTS:
        # Lấy top 5 từ danh sách đã sắp xếp (hoặc lấy hết nếu tổng < 5)
        reranked = chunks[:max(MIN_RESULTS, len(reranked))]
        # Lưu ý: lấy max(5, current) để đảm bảo nếu có 7 cái đạt ngưỡng thì vẫn lấy 7, 
        # nhưng nếu chỉ có 2 cái đạt ngưỡng thì lấy 5. 
        # Thực tế đơn giản hơn: lấy top 5 từ list chunks đã sort.
        reranked = chunks[:MIN_RESULTS] if len(chunks) >= MIN_RESULTS else chunks

    if top_k is not None:
        return reranked[:top_k]
    return reranked
