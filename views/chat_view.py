"""
views/chat_view.py – Giao diện chat giống ChatGPT dùng st.chat_message + st.chat_input
"""

import streamlit as st
from controllers.chat_controller import ask_law_question


def render_chat_main() -> None:

    if "messages" not in st.session_state:
        st.session_state.messages = []          # [{"role", "content", "citations", "chunks", "error"}]
    # ── Hiển thị lịch sử tin nhắn ────────────────────────────────────────────
    for msg in st.session_state.messages:
        role = msg["role"]

        with st.chat_message(role, avatar="🙋" if role == "user" else "⚖️"):
            st.markdown(msg["content"])

            # Candidates TRƯỚC rerank
            if role == "assistant" and msg.get("candidates"):
                with st.expander(f"🔍 {len(msg['candidates'])} ứng viên Vector Search (trước Rerank)", expanded=False):
                    for i, c in enumerate(msg["candidates"], 1):
                        law   = c.get("law_name", "")
                        art   = c.get("article", "")
                        art_n = c.get("article_name", "")
                        cls   = c.get("clause", "")
                        sim   = c.get("similarity", 0)
                        
                        ref = law
                        if art:
                            ref += f" – Điều {art}"
                            if art_n: ref += f" ({art_n})"
                        if cls: ref += f", Khoản {cls}"
                        
                        st.markdown(
                            f"**{i}.** `sim={sim:.2f}` &nbsp; **{ref}**\n\n{c.get('content', '')}",
                            unsafe_allow_html=True,
                        )

            # Citations chỉ hiển thị trong tin nhắn assistant (Sau Rerank)
            if role == "assistant" and msg.get("citations"):
                with st.expander(f"📚 Xem {len(msg['citations'])} điều luật tham khảo (sau Rerank)"):
                    for i, (citation, chunk) in enumerate(
                        zip(msg["citations"], msg.get("chunks", [])), 1
                    ):
                        rerank_score = chunk.get("rerank_score")
                        score_text = f"`rerank={rerank_score:.2f}`" if rerank_score is not None else ""
                        st.markdown(
                            f"**{i}.** {score_text} &nbsp; **{citation}**\n\n{chunk.get('content', '')}",
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

    # Gọi controller (hiển thị spinner)
    with st.spinner("Đang tìm kiếm và tổng hợp…"):
        result = ask_law_question(question)

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
            "role":       "assistant",
            "content":    result["answer"],
            "citations":  result.get("citations", []),
            "chunks":     result.get("chunks", []),
            "candidates": result.get("candidates", []),
            "error":      None,
        })
