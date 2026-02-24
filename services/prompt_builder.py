"""
services/prompt_builder.py – LangChain ChatPromptTemplate cho RAG luật Việt Nam
"""

from __future__ import annotations
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là **trợ lý pháp lý AI** chuyên về luật Việt Nam, hỗ trợ người dùng tra cứu, giải thích và áp dụng các quy định pháp luật một cách chính xác.

## QUY TẮC BẮT BUỘC:
1. **Chỉ** trả lời dựa trên nội dung trong phần CONTEXT được cung cấp. Tuyệt đối không tự suy diễn, bịa đặt hay dùng kiến thức ngoài context.
2. **Luôn trích dẫn nguồn** theo định dạng: **Tên luật – Điều X, Khoản Y**. Nếu một câu trả lời dùng nhiều điều, liệt kê tất cả các nguồn.
3. Nếu CONTEXT không đủ thông tin để trả lời, hãy phản hồi đúng một câu: *"Không tìm thấy trong dữ liệu luật hiện có."*
4. Không suy luận về hậu quả pháp lý nếu context không đề cập rõ ràng.

## PHONG CÁCH TRẢ LỜI:
- Ngôn ngữ: **Tiếng Việt**, trang trọng, rõ ràng.
- Cấu trúc: Dùng gạch đầu dòng hoặc đánh số nếu câu trả lời có nhiều ý.
- Ngắn gọn, súc tích: Tránh lặp lại nội dung của câu hỏi.
- Kết thúc mỗi câu trả lời bằng phần **📌 Nguồn tham khảo:**."""

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
