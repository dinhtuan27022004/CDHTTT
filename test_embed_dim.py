from models.embedding import get_embedding

def test():
    print("🧪 Testing get_embedding dimension...")
    vec = get_embedding("Test text")
    print(f"📏 Dimension: {len(vec)}")
    if len(vec) == 1536:
        print("❌ Vẫn là 1536 (Ada-002 dimension)!")
    elif len(vec) == 1024:
        print("✅ Đã là 1024 (BGE-M3 dimension)!")
    else:
        print(f"❓ Kích thước lạ: {len(vec)}")

if __name__ == "__main__":
    test()
