"""
controllers/chat_controller.py – Điều phối quá trình hỏi đáp pháp lý
"""

from __future__ import annotations
from typing import Any

from services.rag_pipeline import run_rag


def ask_law_question(
    question: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Nhận câu hỏi và lĩnh vực từ View, gọi RAG pipeline, trả về kết quả.

    Args:
        question: Câu hỏi của người dùng.
        top_k:    Số chunks context.

    Returns:
        {
            "answer":    str,
            "citations": List[str],
            "chunks":    List[dict],
            "error":     str | None
        }
    """
    if not question.strip():
        return {
            "answer": "",
            "citations": [],
            "chunks": [],
            "error": "Câu hỏi không được để trống.",
        }
    try:
        result = run_rag(question=question, top_k=top_k)
        result["error"] = None
        return result
    except Exception as e:
        return {
            "answer": "",
            "citations": [],
            "chunks": [],
            "error": str(e),
        }
