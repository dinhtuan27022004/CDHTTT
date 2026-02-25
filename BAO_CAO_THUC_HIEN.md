# BÁO CÁO THỰC HIỆN DỰ ÁN CHATBOT TRA CỨU LUẬT

## 1. Giới thiệu tổng quan

Dự án nhằm xây dựng một hệ thống Chatbot thông minh hỗ trợ tra cứu văn bản pháp luật Việt Nam. Hệ thống sử dụng công nghệ RAG (Retrieval-Augmented Generation) để cung cấp câu trả lời chính xác, có trích dẫn nguồn luật cụ thể, giúp người dùng dễ dàng tiếp cận thông tin pháp lý.

## 2. Kiến trúc hệ thống

Hệ thống được thiết kế theo mô hình **MVC (Model-View-Controller)** đảm bảo tính tách biệt giữa logic nghiệp vụ, dữ liệu và giao diện:

- **Model**: Quản lý kết nối cơ sở dữ liệu PostgreSQL, thực hiện vector search và CRUD dữ liệu luật.
- **View**: Giao diện người dùng xây dựng trên nền tảng **Streamlit**, hỗ trợ upload file và tương tác chat.
- **Controller**: Điều phối luồng dữ liệu giữa View và Model, quản lý quy trình Ingest và Chat.

## 3. Công nghệ sử dụng (Tech Stack)

- **Ngôn ngữ**: Python 3.11+
- **Giao diện**: Streamlit
- **Cơ sở dữ liệu**: PostgreSQL với tiện ích mở rộng **pgvector** để lưu trữ và tìm kiếm vector.
- **LLM**: Sử dụng qua **OpenRouter** (ưu tiên model `gpt-4o-mini`).
- **Framework RAG**: LangChain với kiến trúc LCEL (LangChain Expression Language).

## 4. Các tính năng chính và kết quả thực hiện

### 4.1. Xử lý và nạp dữ liệu (Data Ingestion)

- **Parsing nâng cao**: Hỗ trợ đọc file PDF và DOCX. Hệ thống có khả năng bóc tách cấu trúc phân cấp phức tạp: **Chương > Điều > Khoản**.
- **Hierarchical Chunking**: Dữ liệu được chia nhỏ (chunking) theo đơn vị Điều/Khoản để giữ nguyên ngữ cảnh pháp lý, thay vì chia cắt ngẫu nhiên theo độ dài ký tự.
- **Embedding**: Sử dụng mô hình embedding để chuyển đổi nội dung luật thành vector, lưu trữ vào pgvector.

### 4.2. Pipeline RAG nâng cao (Advanced RAG Pipeline)

Hệ thống không chỉ tìm kiếm vector đơn thuần mà sử dụng quy trình phức tạp để tăng độ chính xác:

1. **Query Expansion (Mở rộng truy vấn)**: Sử dụng LLM để sinh ra các thuật ngữ đồng nghĩa pháp lý từ câu hỏi của người dùng (ví dụ: "lấy trộm" -> "trộm cắp tài sản", "chiếm đoạt").
2. **Hybrid Search**:
   - **Keyword Search**: Tự động nhận diện các tham chiếu trực tiếp (như "Điều 185", "Chương II") để tìm chính xác văn bản.
   - **Vector Search**: Tìm kiếm theo ý nghĩa ngữ nghĩa của câu hỏi.
3. **Reranking (Xếp hạng lại)**: Sử dụng mô hình reranker để chấm điểm lại các ứng viên, đảm bảo những đoạn luật phù hợp nhất được đưa vào prompt.
4. **Threshold-based filtering**: Hệ thống chỉ trả lời khi độ tin cậy của tài liệu tìm thấy vượt ngưỡng quy định (SIM_THRESHOLD, RERANK_THRESHOLD), tránh tình trạng LLM "ảo tưởng".

### 4.3. Hệ thống Debug và Giám sát

- Tự động ghi log các bước trung gian:
  - `debug_candidates.json`: Danh sách các đoạn luật tìm thấy sơ bộ.
  - `debug_results.json`: Kết quả sau khi đã xếp hạng lại.
  - `debug_prompt.txt`: Toàn bộ nội dung prompt gửi cho LLM.

## 5. Kết luận và Hướng phát triển

Hiện tại, hệ thống đã vận hành ổn định với khả năng hiểu sâu văn bản luật và trích dẫn chính xác.

**Hướng phát triển tiếp theo:**

- Hỗ trợ nhiều định dạng file hơn.
- Cải thiện tốc độ reranking bằng các model local.
- Tích hợp thêm tính năng so sánh các thông tư, nghị định hướng dẫn thi hành.

---
*Ngày báo cáo: 25/02/2026*
