"""
models/db.py – Kết nối PostgreSQL và khởi tạo schema
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

# Cố gắng lấy từ .env, nếu không có thì dùng mặc định khớp với Docker container của bạn
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Trả về một kết nối psycopg2 tới PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """
    Khởi tạo extension pgvector và tạo bảng law_documents nếu chưa tồn tại.
    Gọi một lần khi ứng dụng khởi động.
    """
    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Kích hoạt pgvector
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Tạo bảng chính
    cur.execute("""
        CREATE TABLE IF NOT EXISTS law_documents (
            id          BIGSERIAL PRIMARY KEY,

            -- Văn bản
            law_name    TEXT NOT NULL,
            law_code    TEXT,
            document_type TEXT,
            issuing_body  TEXT,
            field         TEXT,

            -- Cấu trúc
            chapter     TEXT,
            section     TEXT,
            article     INT,
            article_name TEXT,
            clause      INT,
            point       TEXT,

            -- Nội dung
            content     TEXT NOT NULL,

            -- RAG
            chunk_id    UUID,
            chunk_index INT,
            embedding   VECTOR(1536)
        );
    """)

    # Tạo index IVFFLAT cho vector search (chỉ tạo khi chưa có)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'law_documents'
                  AND indexname = 'law_documents_embedding_idx'
            ) THEN
                CREATE INDEX law_documents_embedding_idx
                ON law_documents
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            END IF;
        END
        $$;
    """)

    cur.close()
    conn.close()
