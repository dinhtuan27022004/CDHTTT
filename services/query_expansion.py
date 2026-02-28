"""
services/query_expansion.py – Mở rộng truy vấn bằng các từ đồng nghĩa pháp lý.
"""

from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.openrouter_service import get_llm

SIMILAR_QUESTIONS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Bạn là chuyên gia ngôn ngữ pháp lý Việt Nam. 
Nhiệm vụ của bạn là lấy một câu hỏi của người dùng và viết lại nó thành 5 câu hỏi khác nhau nhưng có cùng ý nghĩa nội dung.

QUY TẮC:
1. Trả về đúng 5 câu hỏi, mỗi câu trên một dòng.
2. Các câu hỏi phải đa dạng về cách dùng từ nhưng giữ nguyên ý nghĩa cốt lõi của câu hỏi gốc.
3. Tập trung vào các thuật ngữ chuyên môn có khả năng xuất hiện trong văn bản luật.
4. KHÔNG trả lời câu hỏi, chỉ viết lại câu hỏi.
5. Chỉ trả về các câu hỏi, không thêm bất kỳ văn bản giải thích nào khác.

Ví dụ:
Input: "lấy trộm xe máy bị phạt thế nào?"
Output:
Xử lý hành vi trộm cắp xe gắn máy như thế nào?
Hình phạt cho tội chiếm đoạt xe máy là gì?
Mức án đối với hành vi trộm xe máy được quy định ra sao?
Tội trộm cắp tài sản là xe máy bị xử lý pháp luật như thế nào?
Quy định về việc xử phạt hành vi lấy cắp xe máy?
"""),
    ("human", "{question}")
])

def generate_similar_questions(question: str) -> list[str]:
    """
    Sử dụng LLM để viết lại câu hỏi thành 5 biến thể khác nhau.
    Trả về list gồm [câu hỏi gốc, biến thể 1, ..., biến thể 5]
    """
    questions = [question]
    try:
        llm = get_llm(model_name="openai/gpt-4o-mini")
        chain = SIMILAR_QUESTIONS_PROMPT | llm | StrOutputParser()
        response = chain.invoke({"question": question})
        
        # Tách các dòng và làm sạch
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        
        # Chỉ lấy tối đa 5 biến thể đầu tiên
        variants = lines[:5]
        questions.extend(variants)
        
        print(f"|-- Generated {len(variants)} similar questions", flush=True)
        return questions
    except Exception as e:
        print(f"|-- Warning: Query Expansion error: {e}", flush=True)
        return questions
