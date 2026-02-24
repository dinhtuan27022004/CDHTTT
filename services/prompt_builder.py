"""
services/prompt_builder.py – LangChain ChatPromptTemplate cho RAG luật Việt Nam
"""

from __future__ import annotations
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là trợ lý pháp lý chuyên về luật Việt Nam.
Chỉ được trả lời dựa trên nội dung luật được cung cấp trong phần CONTEXT bên dưới.
Luôn trích dẫn nguồn theo định dạng: **Tên luật – Điều X, Khoản Y**.
Nếu không tìm thấy thông tin liên quan, hãy trả lời đúng một câu:
"Không tìm thấy trong dữ liệu luật hiện có."
Không tự suy diễn hay bịa đặt thông tin pháp lý."""

# ── LangChain ChatPromptTemplate ─────────────────────────────────────────────
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "CONTEXT:\n{context}\n\nCÂU HỎI: {question}",
        ),
    ]
)


def build_context(chunks: list[dict[str, Any]]) -> str:
    """
    Ghép danh sách chunks thành chuỗi context đưa vào prompt.

    Args:
        chunks: Kết quả vector search (list dict từ law_model.py).

    Returns:
        Chuỗi context gồm các đoạn trích dẫn có header.
    """
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        law   = chunk.get("law_name", "")
        art   = chunk.get("article", "")
        art_n = chunk.get("article_name", "")
        cls   = chunk.get("clause", "")
        point = chunk.get("point", "")
        sim   = chunk.get("similarity", 0)
        content = chunk.get("content", "")

        ref = law
        if art:
            ref += f" – Điều {art}"
            if art_n:
                ref += f" ({art_n})"
        if cls:
            ref += f", Khoản {cls}"
        if point:
            ref += f", Điểm {point}"

        parts.append(f"[{i}] {ref} (tương đồng: {sim:.2f})\n{content}")

    return "\n\n---\n\n".join(parts)


def format_citations(chunks: list[dict[str, Any]]) -> list[str]:
    """Tạo danh sách chuỗi trích dẫn hiển thị trong UI."""
    citations: list[str] = []
    for chunk in chunks:
        law   = chunk.get("law_name", "")
        art   = chunk.get("article", "")
        art_n = chunk.get("article_name", "")
        cls   = chunk.get("clause", "")
        point = chunk.get("point", "")
        sim   = chunk.get("similarity", 0)

        ref = law
        if art:
            ref += f" – Điều {art}"
            if art_n:
                ref += f" ({art_n})"
        if cls:  ref += f", Khoản {cls}"
        if point: ref += f", Điểm {point}"
        ref += f" (độ tương đồng: {sim:.2%})"
        citations.append(ref)
    return citations
