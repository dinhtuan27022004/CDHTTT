"""
models/embedding.py – LangChain OpenAIEmbeddings qua OpenRouter
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# LangChain embedding model hướng đến OpenRouter
_embedding_model = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
    openai_api_base="https://openrouter.ai/api/v1",
)


def get_embedding(text: str) -> list[float]:
    """Tạo embedding vector 1536 chiều cho đoạn văn bản."""
    return _embedding_model.embed_query(text.strip().replace("\n", " "))

