"""
controllers/chat_controller.py – Điều phối quá trình hỏi đáp pháp lý
"""

from __future__ import annotations
from typing import Any

from services.rag_pipeline import run_rag


def ask_law_question(
    question: str,
) -> dict[str, Any]:

    if not question.strip():
        return {
            "answer": "",
            "citations": [],
            "chunks": [],
            "error": "Câu hỏi không được để trống.",
        }
    try:
        result = run_rag(question=question)
        result["error"] = None
        return result
    except Exception as e:
        return {
            "answer": "",
            "citations": [],
            "chunks": [],
            "error": str(e),
        }
