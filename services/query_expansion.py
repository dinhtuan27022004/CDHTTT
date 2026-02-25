"""
services/query_expansion.py – Mở rộng truy vấn bằng các từ đồng nghĩa pháp lý.
"""

from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.openrouter_service import get_llm

EXPANSION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Bạn là chuyên gia ngôn ngữ pháp lý Việt Nam. 
Nhiệm vụ của bạn là lấy một câu hỏi của người dùng và mở rộng nó bằng các thuật ngữ đồng nghĩa, các khái niệm tương đương với các từ khóa trong câu hỏi, mở rộng các câu hỏi ngắn, thiếu.

QUY TẮC:
1. Trả về một chuỗi duy nhất chứa các từ mở rộng (không lặp lại câu gốc).
2. Tập trung vào các thuật ngữ chuyên môn có khả năng xuất hiện trong văn bản luật và phải đảm bảo liên quan tới câu hỏi người dùng.
3. KHÔNG trả lời câu hỏi, chỉ mở rộng từ khóa.
4. Trả về kết quả dưới dạng danh sách từ khóa cách nhau bởi dấu phẩy hoặc khoảng trắng.
5. không mở rộng các từ khóa không liên quan tới câu hỏi người dùng.
Ví dụ:
Input: "lấy trộm xe máy"
Output: "trộm cắp tài sản, chiếm đoạt tài sản, tội trộm cắp"
"""),
    ("human", "{question}")
])

def expand_query_for_search(question: str) -> str:
    """
    Sử dụng LLM (model nhanh + ổn định) để sinh ra các thuật ngữ đồng nghĩa.
    """
    try:
        # Sử dụng gpt-4o-mini vì Gemini Flash đang gặp lỗi endpoint 404 trên OpenRouter
        llm = get_llm(model_name="openai/gpt-4o-mini")
        chain = EXPANSION_PROMPT | llm | StrOutputParser()
        expanded = chain.invoke({"question": question})
        print(f"🚀 Expanded Query: {expanded}")
        return f"{question} {expanded.strip()}"
    except Exception as e:
        print(f"⚠️ Query Expansion error: {e}")
        return question
