from models.db import get_connection
import psycopg2

def check_and_fix():
    print("🔍 Đang kiểm tra Database...")
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        # Kiểm tra kích thước cột embedding
        cur.execute("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'law_documents'::regclass 
              AND attname = 'embedding';
        """)
        res = cur.fetchone()
        
        if res:
            # atttypmod cho vector(N) là N
            dim = res[0]
            print(f"📊 Kích thước hiện tại của cột embedding: {dim}")
            
            if dim != 1024:
                print("❌ Kích thước vector không khớp (Cần 1024 nhưng đang là 1536).")
                print("♻️ Đang xóa bảng law_documents để khởi tạo lại...")
                cur.execute("DROP TABLE IF EXISTS law_documents CASCADE;")
                print("✅ Đã xóa bảng. Vui lòng chạy lại App hoặc Upload file để tự động tạo lại bảng mới.")
            else:
                print("✅ Kích thước vector đã đúng 1024.")
        else:
            print("❓ Không tìm thấy bảng hoặc cột embedding. Có thể bảng chưa được tạo.")
            
    except psycopg2.ProgrammingError:
        print("ℹ️ Bảng law_documents chưa tồn tại. Không cần xử lý.")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_and_fix()
