"""
services/file_parsers.py – Parser nâng cao cho PDF và DOCX
Sửa lỗi bóc tách nhầm tiêu đề Chương thành Điều.
"""

from __future__ import annotations
import io
import re
import uuid
import json
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Cấu hình Splitter dự phòng ───────────────────────────────────────────────
_sub_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

# ── Regex Patterns ────────────────────────────────────────────────────────────
RE_CHAPTER = re.compile(r"^Chương\s+([IVXLCDM\d]+|[a-zA-Zà-ỹÀ-Ỹ ]+)", re.IGNORECASE | re.MULTILINE)
RE_ARTICLE = re.compile(r"^Điều\s+(\d+)", re.IGNORECASE | re.MULTILINE)
RE_CLAUSE  = re.compile(r"^(\d+)[\.\)]\s+", re.MULTILINE)


def _make_meta_from_filename(filename: str) -> dict[str, Any]:
    law_name = re.sub(r"\.(pdf|docx|doc)$", "", filename, flags=re.IGNORECASE).strip()
    return {
        "law_name":       law_name,
        "law_code":       None,
        "document_type":  None,
        "issuing_body":   None,
        "field":          None,
    }


def _parse_to_hierarchy(text: str) -> dict[str, Any]:
    """
    Bóc tách văn bản thành Chương > Điều > Khoản.
    Đã sửa lỗi nhận diện nhầm tiêu đề Chương là Điều.
    """
    # 1. Tách theo Chương
    chapter_parts = re.split(r"(?=^Chương\s+(?:[IVXLCDM\d]+|[a-zA-Zà-ỹÀ-Ỹ ]+))", text, flags=re.IGNORECASE | re.MULTILINE)
    
    hierarchy = {"chapters": [], "orphan_articles": []}

    for part in chapter_parts:
        part = part.strip()
        if not part: continue

        chap_match = RE_CHAPTER.match(part)
        current_chapter_info = None

        if chap_match:
            # Lấy tên chương và tìm tiêu đề chương (thường ở dòng ngay sau)
            lines = part.split('\n')
            chap_label = lines[0].strip() # "Chương I"
            chap_title = ""
            if len(lines) > 1:
                # Tìm dòng tiếp theo có chữ nhưng không phải "Điều"
                for line in lines[1:5]: # Kiểm tra 4 dòng tiếp theo
                    l = line.strip()
                    if l and not RE_ARTICLE.match(l):
                        chap_title = l
                        break
            
            current_chapter_info = {
                "chapter_name": chap_label,
                "chapter_title": chap_title,
                "articles": []
            }

        # 2. Tách theo Điều trong phần này
        article_parts = re.split(r"(?=^Điều\s+\d+)", part, flags=re.IGNORECASE | re.MULTILINE)
        
        current_articles = []
        for art_p in article_parts:
            art_p = art_p.strip()
            if not art_p: continue
            
            art_match = RE_ARTICLE.match(art_p)
            if not art_match:
                # Đây là phần text TRƯỚC Điều đầu tiên của part (có thể là tiêu đề chương)
                # Chúng ta bỏ qua vì đã lấy thông tin chương ở trên, 
                # trừ khi nó chứa nội dung dẫn nhập quan trọng không phải tiêu đề.
                continue
            
            art_num = int(art_match.group(1))
            
            # 3. Tách theo Khoản trong Điều
            clause_parts = re.split(r"(?=^\d+[\.\)]\s+)", art_p, flags=re.MULTILINE)
            current_clauses = []
            article_title = ""
            
            for i, cls_p in enumerate(clause_parts):
                cls_p = cls_p.strip()
                if not cls_p: continue
                
                cls_match = RE_CLAUSE.match(cls_p)
                cls_num = int(cls_match.group(1)) if cls_match else None
                
                if i == 0 and not cls_num:
                    # Lấy tiêu đề Điều (dòng đầu tiên)
                    lines = cls_p.split('\n')
                    title_line = lines[0].strip()
                    article_title = re.sub(r"^Điều\s+\d+[\.\s:]*", "", title_line, flags=re.IGNORECASE).strip()
                    
                    # Phần nội dung còn lại sau dòng tiêu đề (nếu có)
                    remaining_text = "\n".join(lines[1:]).strip()
                    if remaining_text:
                        current_clauses.append({"clause_num": None, "content": remaining_text})
                else:
                    current_clauses.append({"clause_num": cls_num, "content": cls_p})
            
            current_articles.append({
                "article_num": art_num,
                "article_name": article_title,
                "clauses": current_clauses
            })

        if current_chapter_info:
            current_chapter_info["articles"] = current_articles
            hierarchy["chapters"].append(current_chapter_info)
        else:
            hierarchy["orphan_articles"].extend(current_articles)

    return hierarchy


def _build_chunks_from_hierarchy(
    hierarchy: dict[str, Any], 
    meta: dict[str, Any]
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    shared_chunk_id = str(uuid.uuid4())
    chunk_idx = 0

    def _process_article(
        art: dict, 
        chapter_label: str | None, 
        chapter_title: str | None
    ):
        nonlocal chunk_idx
        art_num = art["article_num"]
        art_title = art.get("article_name", "")
        
        for cls in art["clauses"]:
            cls_num = cls["clause_num"]
            raw_content = cls["content"]

            sub_parts = _sub_splitter.split_text(raw_content) if len(raw_content) > 1500 else [raw_content]

            for sub_p in sub_parts:
                header_parts = []
                if chapter_label: 
                    chap_display = chapter_label
                    if chapter_title: chap_display += f" ({chapter_title})"
                    header_parts.append(chap_display)
                
                if art_num:      header_parts.append(f"Điều {art_num}")
                if art_title:    header_parts.append(f"{art_title}")
                if cls_num:      header_parts.append(f"Khoản {cls_num}")
                
                header = " ".join(header_parts)
                
                chunks.append({
                    **meta,
                    "chapter": chapter_label,
                    "section": None,
                    "article": art_num,
                    "article_name": art_title,
                    "clause": cls_num,
                    "point": None,
                    "content": f"{header}:\n{sub_p}",
                    "chunk_id": shared_chunk_id,
                    "chunk_index": chunk_idx,
                    "embedding": None,
                })
                chunk_idx += 1

    for art in hierarchy["orphan_articles"]:
        _process_article(art, None, None)
    for chap in hierarchy["chapters"]:
        for art in chap["articles"]:
            _process_article(art, chap["chapter_name"], chap.get("chapter_title"))

    return chunks


def _text_to_chunks(text: str, meta: dict[str, Any]) -> list[dict[str, Any]]:
    hierarchy = _parse_to_hierarchy(text)
    
    with open("hierarchy_debug.json", "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, indent=4, ensure_ascii=False)
        
    chunks = _build_chunks_from_hierarchy(hierarchy, meta)
    
    if not chunks:
        shared_chunk_id = str(uuid.uuid4())
        raw_texts = _sub_splitter.split_text(text)
        for i, t in enumerate(raw_texts):
            chunks.append({
                **meta,
                "chapter": None, 
                "article": None, 
                "article_name": None,
                "clause": None, 
                "point": None,
                "content": f"[{meta['law_name']}] Đoạn {i+1}:\n{t}",
                "chunk_id": shared_chunk_id, 
                "chunk_index": i, 
                "embedding": None
            })
    
    with open("chunks_debug.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=4, ensure_ascii=False)
        
    return chunks


def parse_pdf(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    try: import pdfplumber
    except ImportError: raise ImportError("Cần cài pdfplumber: pip install pdfplumber")
    meta = _make_meta_from_filename(filename)
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t: pages.append(t)
    return _text_to_chunks("\n\n".join(pages), meta)


def parse_docx(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    try: from docx import Document
    except ImportError: raise ImportError("Cần cài python-docx: pip install python-docx")
    meta = _make_meta_from_filename(filename)
    doc = Document(io.BytesIO(file_bytes))
    full_text = "\n\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
    return _text_to_chunks(full_text, meta)
