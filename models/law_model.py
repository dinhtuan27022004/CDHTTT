"""
models/law_model.py – CRUD + Vector search cho bảng law_documents
"""

from __future__ import annotations
from typing import Any
from models.db import get_connection


def insert_chunk(chunk: dict[str, Any]) -> None:
    """
    Insert một chunk luật vào bảng law_documents.

    Args:
        chunk: Dict với các key tương ứng cột trong bảng.
    """
    
    sql = """
        INSERT INTO law_documents (
            law_name, 
            chapter, 
            article, 
            article_name, 
            clause, 
            content,
            chunk_id, 
            chunk_index, 
            embedding
        ) VALUES (
            %(law_name)s, 
            %(chapter)s, 
            %(article)s, 
            %(article_name)s, 
            %(clause)s, 
            %(content)s,
            %(chunk_id)s, 
            %(chunk_index)s, 
            %(embedding)s
        );
    """
    conn = get_connection()

    try:
        cur = conn.cursor()
        try:
            cur.execute(sql, chunk)
            conn.commit()
        except Exception as e:
            conn.rollback()
            # Xem SQL thực tế (mogrify)
            full_sql = cur.mogrify(sql, chunk).decode('utf-8')
            print(f"|-- Error INSERT: {e}", flush=True)
            print(f"|-- SQL: {full_sql[:500]}...", flush=True)
            raise e
        finally:
            cur.close()
    except Exception as e:
        print(f"Error inserting chunk: {e}")
    finally:
        conn.close()


def vector_search(
    query_embedding: list[float],
    top_k: int = 100,
    threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Tìm kiếm top-K chunks gần nhất bằng cosine similarity và lọc theo ngưỡng.

    Args:
        query_embedding: Vector câu hỏi.
        top_k: Số kết quả tối đa trước khi lọc.
        threshold: Ngưỡng tương đồng tối thiểu (0.0 đến 1.0).

    Returns:
        Danh sách dict chứa thông tin từng chunk.
    """
    params: list[Any] = [str(query_embedding), str(query_embedding), threshold, top_k]

    sql = f"""
        SELECT
            id, 
            law_name,
            chapter, article, article_name, clause, content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM law_documents
        WHERE embedding IS NOT NULL
          AND (1 - (embedding <=> %s::vector)) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    # Lưu ý: %s xuất hiện 3 lần cho embedding, ta cần 4 params
    params = [str(query_embedding), str(query_embedding), threshold, str(query_embedding), top_k]

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        print(f"|-- Vector Search found {len(rows)} results.", flush=True)
        import json
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=4, ensure_ascii=False)
        return rows
    finally:
        conn.close()


def count_records() -> int:
    """Đếm tổng số bản ghi trong bảng law_documents."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM law_documents;")
        result = cur.fetchone()
        cur.close()
        return result[0] if result else 0
    finally:
        conn.close()


def keyword_search(
    articles: list[str] | None = None,
    chapters: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Tìm kiếm chunk chính xác theo Điều/Chương được đề cập trong câu hỏi.
    Các chunk tìm được sẽ có similarity = 1.0 (ưu tiên tối đa).

    Args:
        articles: Danh sách số điều cần tìm, ví dụ ["2", "185"].
        chapters: Danh sách số/tên chương cần tìm, ví dụ ["I", "2"].

    Returns:
        Danh sách chunk khớp, với similarity = 1.0.
    """
    if not articles and not chapters:
        return []

    conditions: list[str] = []
    params: list[Any] = []

    if articles:
        placeholders = ", ".join(["%s"] * len(articles))
        conditions.append(f"article::text IN ({placeholders})")
        params.extend(articles)

    if chapters:
        or_parts = []
        for ch in chapters:
            or_parts.append("chapter ILIKE %s")
            params.append(f"%{ch}%")
        conditions.append(f"({' OR '.join(or_parts)})")

    where_clause = " OR ".join(conditions)
    sql = f"""
        SELECT
            id,
            law_name,
            chapter, article, article_name, clause, content,
            1.0::float AS similarity
        FROM law_documents
        WHERE {where_clause}
        ORDER BY article, clause;
    """

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        print(f"|-- Keyword search found {len(rows)} exact matches.", flush=True)
        return rows
    finally:
        conn.close()


def check_chunk_exists(
    law_name: str,
    chapter: str | None = None,
    article: int | None = None,
    clause: int | None = None,
) -> bool:
    """
    Kiểm tra xem chunk đã tồn tại trong DB chưa dựa trên law_name, chapter, article, clause.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # Xây dựng câu lệnh WHERE linh hoạt cho các giá trị None
        sql = "SELECT 1 FROM law_documents WHERE law_name = %s"
        params = [law_name]
        
        if chapter:
            sql += " AND chapter = %s"
            params.append(chapter)
        else:
            sql += " AND chapter IS NULL"
            
        if article:
            sql += " AND article = %s"
            params.append(article)
        else:
            sql += " AND article IS NULL"
            
        if clause:
            sql += " AND clause = %s"
            params.append(clause)
        else:
            sql += " AND clause IS NULL"
            
        cur.execute(sql, params)
        exists = cur.fetchone() is not None
        cur.close()
        return exists
    finally:
        conn.close()
