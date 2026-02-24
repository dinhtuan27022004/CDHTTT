"""
views/chat_view.py – Giao diện chat giống ChatGPT dùng st.chat_message + st.chat_input
"""

import streamlit as st
from controllers.chat_controller import ask_law_question


def render_chat_main() -> None:

    if "messages" not in st.session_state:
        st.session_state.messages = []          # [{"role", "content", "citations", "chunks", "error"}]
    if "chat_topk" not in st.session_state:
        st.session_state.chat_topk = 5

    # ── Tiêu đề ──────────────────────────────────────────────────────────────
    # Chỉ hiển thị khi chưa có tin nhắn (như trang chủ GPT)

    # ── Cài đặt hội thoại (compact, trong expander) ──────────────────────────
    with st.expander("⚙️ Cài đặt tìm kiếm", expanded=False):
        st.session_state.chat_topk = st.slider(
            "Số điều tham khảo (top-K)",
            min_value=1, max_value=10,
            value=st.session_state.chat_topk,
        )

    st.markdown("---")

    # ── Hiển thị lịch sử tin nhắn ────────────────────────────────────────────
    for msg in st.session_state.messages:
        role = msg["role"]

        with st.chat_message(role, avatar="🙋" if role == "user" else "⚖️"):
            st.markdown(msg["content"])

            # Citations chỉ hiển thị trong tin nhắn assistant
            if role == "assistant" and msg.get("citations"):
                with st.expander(f"📚 Xem {len(msg['citations'])} điều luật tham khảo"):
                    for i, (citation, chunk) in enumerate(
                        zip(msg["citations"], msg.get("chunks", [])), 1
                    ):
                        preview = chunk.get("content", "")[:250]
                        if len(chunk.get("content", "")) > 250:
                            preview += "…"
                        st.markdown(
                            f"""<div class="citation-card">
                                <div class="citation-title">{i}. {citation}</div>
                                {preview}
                            </div>""",
                            unsafe_allow_html=True,
                        )

            if role == "assistant" and msg.get("error"):
                st.error(f"❌ {msg['error']}")

    # ── Chat input (cố định ở dưới như GPT) ─────────────────────────────────
    if prompt := st.chat_input("Hỏi về luật Việt Nam…"):
        _handle_question(prompt)
        st.rerun()

    # ── Nút xóa lịch sử ──────────────────────────────────────────────────────
    if st.session_state.messages:
        if st.button("🗑️ Cuộc hội thoại mới", type="secondary"):
            st.session_state.messages = []
            st.rerun()


def _handle_question(question: str) -> None:
    """Thêm câu hỏi vào lịch sử, gọi controller, thêm câu trả lời."""

    # Thêm tin nhắn user
    st.session_state.messages.append({"role": "user", "content": question})

    top_k = st.session_state.get("chat_topk", 5)

    # Gọi controller (hiển thị spinner)
    with st.spinner("Đang tìm kiếm và tổng hợp…"):
        result = ask_law_question(question, top_k=top_k)

    if result.get("error"):
        st.session_state.messages.append({
            "role":      "assistant",
            "content":   "Đã xảy ra lỗi khi xử lý câu hỏi của bạn.",
            "citations": [],
            "chunks":    [],
            "error":     result["error"],
        })
    else:
        st.session_state.messages.append({
            "role":      "assistant",
            "content":   result["answer"],
            "citations": result.get("citations", []),
            "chunks":    result.get("chunks", []),
            "error":     None,
        })
