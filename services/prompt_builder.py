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
2. **Luôn trích dẫn nguồn** theo định dạng: **Tên luật – Điều X, Khoản Y**. 
   - **Lưu ý quan trọng**: Thông tin về Khoản luôn phải đi kèm thông tin về Điều (ví dụ: "Điều X - Khoản Y", không viết mỗi "Khoản Y").
   - Nếu một câu trả lời dùng nhiều điều, liệt kê tất cả các nguồn.
3. Nếu CONTEXT không đủ thông tin để trả lời toàn bộ câu hỏi người dùng, hãy phản hồi đúng một câu: *"Không tìm thấy trong dữ liệu luật hiện có."*
4. Nếu CONTEXT chỉ đủ thông tin để trả lời một phần của câu hỏi người dùng, hãy trả lời phần có thể và phần còn lại thừa nhận không tìm thấy thông tin và tuyệt đối không bịa.

4. Không suy luận về hậu quả pháp lý nếu CONTEXT không đề cập rõ ràng.
5. Đối với các câu hỏi ngắn hoặc chỉ chứa từ khóa (v dụ: "bạo lực gia đình", "trốn thuế"), hãy hiểu người dùng đang muốn hỏi về các quy định liên quan, các hành vi vi phạm và mức xử phạt (bị phạt như thế nào, có bị phạt không). Hãy trình bày tổng quan dựa trên CONTEXT.
6. Nếu nội dung CONTEXT đủ để trả lời câu hỏi của người dùng, hãy trả lời đầy đủ và tận dụng tối đa context, bổ sung thêm các kiến thức liên quan đến câu hỏi từ CONTEXT (nếu có).
## PHONG CÁCH TRẢ LỜI:
- Ngôn ngữ: **Tiếng Việt**, trang trọng, rõ ràng.
- Cấu trúc: Dùng gạch đầu dòng hoặc đánh số nếu câu trả lời có nhiều ý.
- Ngắn gọn, súc tích, đầy đủ: Tránh lặp lại nội dung của câu hỏi.
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
        sim   = chunk.get("similarity", 0)
        content = chunk.get("content", "")

        ref = law
        if art:
            ref += f" – Điều {art}"
            if art_n:
                ref += f" ({art_n})"
        if cls:
            ref += f", Khoản {cls}"

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
        sim   = chunk.get("similarity", 0)

        ref = law
        if art:
            ref += f" – Điều {art}"
            if art_n:
                ref += f" ({art_n})"
        if cls:  ref += f", Khoản {cls}"
        ref += f" (độ tương đồng: {sim:.2%})"
        citations.append(ref)
    return citations
