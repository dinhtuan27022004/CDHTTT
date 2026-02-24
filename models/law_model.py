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
            law_code, 
            document_type, 
            issuing_body, 
            field,
            chapter, 
            section, 
            article, 
            article_name, 
            clause, 
            point,
            content,
            chunk_id, 
            chunk_index, 
            embedding
        ) VALUES (
            %(law_name)s, 
            %(law_code)s, 
            %(document_type)s, 
            %(issuing_body)s, 
            %(field)s,
            %(chapter)s, 
            %(section)s, 
            %(article)s, 
            %(article_name)s, 
            %(clause)s, 
            %(point)s,
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
            print(f"\n❌ LỖI INSERT: {e}")
            print(f"--- SQL: {full_sql[:500]}...")
            raise e
        finally:
            cur.close()
    except Exception as e:
        print(f"Error inserting chunk: {e}")
    finally:
        conn.close()


def vector_search(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Tìm kiếm top-K chunks gần nhất bằng cosine similarity.

    Args:
        query_embedding: Vector câu hỏi (1536-dim).
        field: Lĩnh vực luật cần lọc (None = tất cả).
        top_k: Số kết quả trả về.

    Returns:
        Danh sách dict chứa thông tin từng chunk.
    """
    params: list[Any] = [str(query_embedding), str(query_embedding), top_k]

    sql = f"""
        SELECT
            id, 
            law_name, law_code, document_type, issuing_body, field,
            chapter, article, article_name, clause, point, content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM law_documents
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        cur.close()
        print(f"✅ Tìm thấy {len(rows)} kết quả.")
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


