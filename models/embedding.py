import os
from dotenv import load_dotenv
import openai

load_dotenv()

# Sử dụng OpenAI client trực tiếp để đảm bảo tương thích tốt nhất với OpenRouter
_client = openai.OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
    base_url="https://openrouter.ai/api/v1",
)

MODEL_NAME = "baai/bge-m3"

def get_embedding(text: str) -> list[float]:
    """Tạo embedding vector 1024 chiều cho đoạn văn bản (BGE-M3)."""
    clean_text = text.strip().replace("\n", " ")
    if not clean_text:
        return [0.0] * 1024
        
    response = _client.embeddings.create(
        model=MODEL_NAME,
        input=clean_text
    )
    return response.data[0].embedding

