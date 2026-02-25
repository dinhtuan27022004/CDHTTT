"""
config/rag_config.py – Các hằng số cấu hình cho RAG pipeline
"""

# Ngưỡng tương đồng tối thiểu cho Vector Search (0.0 - 1.0)
SIM_THRESHOLD = 0.6

# Ngưỡng lọc sau khi Rerank (0.0 - 1.0)
RERANK_THRESHOLD = 0.6

# Số lượng ứng viên tối đa lấy từ cơ sở dữ liệu để đưa vào Reranker
MAX_CANDIDATES_FETCH = 100
