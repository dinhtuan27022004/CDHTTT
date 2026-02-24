import os
from dotenv import load_dotenv
import openai

load_dotenv()

def test_raw_openai():
    print("🔍 Đang test embedding qua OpenRouter (Direct OpenAI Client)...")
    client = openai.OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )
    
    try:
        response = client.embeddings.create(
            model="baai/bge-m3",
            input="Xin chào, đây là bài test."
        )
        print("✅ Thành công (Direct client)!")
        print(f"Kích thước vector: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"❌ Thất bại (Direct client): {e}")

if __name__ == "__main__":
    test_raw_openai()
