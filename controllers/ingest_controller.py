"""
controllers/ingest_controller.py – Điều phối ingest: JSON / PDF / DOCX
"""

from __future__ import annotations
import streamlit as st
from typing import Any

from services.file_parsers import parse_pdf, parse_docx
from models.embedding import get_embedding
from models.law_model import insert_chunk, check_chunk_exists


def _detect_file_type(filename: str) -> str:
    """Trả về 'pdf' | 'docx' | 'unknown' dựa vào extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return "pdf"
    if ext in ("docx", "doc"):
        return "docx"
    return "unknown"


def _get_chunks(file_bytes: bytes, filename: str, file_type: str) -> list[dict[str, Any]]:
    """
    Chuyển đổi nội dung file thành danh sách chunks theo loại file.

    PDF  → parse_pdf  (paragraph-based)
    DOCX → parse_docx (paragraph-based)
    """
    if file_type == "pdf":
        return parse_pdf(file_bytes, filename)

    if file_type == "docx":
        return parse_docx(file_bytes, filename)

    raise ValueError(f"Định dạng file không được hỗ trợ: {filename}")


def ingest_law_file(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Nhận nội dung file, chunk, tạo embedding và insert vào DB.

    Args:
        file_bytes: Bytes nội dung file.
        filename:   Tên file gốc (dùng để detect loại file và lấy law_name).

    Returns:
        {"success": bool, "inserted": int, "skipped": int, "errors": List[str], "message": str}
    """
    errors: list[str] = []
    inserted = 0
    skipped = 0

    # 1. Detect loại file
    file_type = _detect_file_type(filename)
    if file_type == "unknown":
        return {
            "success": False,
            "inserted": 0,
            "skipped": 0,
            "errors": [f"Định dạng không hỗ trợ: {filename}"],
            "message": f"❌ Định dạng không hỗ trợ. Chỉ nhận PDF, DOCX.",
        }

    # 2. Parse → chunks
    try:
        chunks = _get_chunks(file_bytes, filename, file_type)
    except Exception as e:
        return {
            "success": False,
            "inserted": 0,
            "skipped": 0,
            "errors": [str(e)],
            "message": f"❌ Lỗi đọc file: {e}",
        }

    if not chunks:
        return {
            "success": False,
            "inserted": 0,
            "skipped": 0,
            "errors": ["Không tìm thấy nội dung hợp lệ trong file."],
            "message": "⚠️ File không có nội dung để import.",
        }

    # 3. Embed + insert từng chunk
    total = len(chunks)
    progress = st.progress(0, text=f"Đang xử lý 0/{total} chunks…")

    for i, chunk in enumerate(chunks):
        try:
            # Kiểm tra trùng lắp trước khi get embedding
            if check_chunk_exists(
                law_name=chunk.get("law_name"),
                chapter=chunk.get("chapter"),
                article=chunk.get("article"),
                clause=chunk.get("clause")
            ):
                skipped += 1
            else:
                chunk["embedding"] = get_embedding(chunk["content"])
                insert_chunk(chunk)
                inserted += 1
        except Exception as e:
            errors.append(f"[chunk {i}] {e}")

        progress.progress((i + 1) / total, text=f"Đang xử lý {i + 1}/{total} chunks…")

    progress.empty()

    type_label = {"pdf": "PDF", "docx": "DOCX"}.get(file_type, file_type.upper())
    message = f"✅ [{type_label}] Đã xử lý {total} chunks."
    message += f"\n- Thành công: {inserted}"
    if skipped > 0:
        message += f"\n- Bỏ qua (đã tồn tại): {skipped}"
    if errors:
        message += f"\n- Lỗi: {len(errors)}"

    return {
        "success": len(errors) == 0,
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "message": message,
    }
