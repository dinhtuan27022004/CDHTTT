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

            # �️ Hiển thị tổng thời gian xử lý (Nếu có)
            if role == "assistant" and msg.get("timings"):
                t_total = msg["timings"].get("total")
                if t_total:
                    st.caption(f"⚡ Tổng thời gian xử lý: {t_total:.2f}s")

            # �🚀 Hiển thị Expanded Query (Nếu có)
            if role == "assistant" and msg.get("search_query"):
                timings = msg.get("timings", {})
                t_expand = timings.get("expand")
                label = "🛠️ Chi tiết truy vấn mở rộng (Query Expansion)"
                if t_expand is not None:
                    label += f" ({t_expand:.2f}s)"
                with st.expander(label, expanded=False):
                    if isinstance(msg["search_query"], list):
                        query_text = "\n".join([f"- {q}" for q in msg["search_query"]])
                        st.info(f"**Các truy vấn đã dùng:**\n{query_text}")
                    else:
                        st.info(f"**Truy vấn đã dùng:**\n{msg['search_query']}")

            # Candidates TRƯỚC rerank
            if role == "assistant" and msg.get("candidates"):
                timings = msg.get("timings", {})
                t_vector = timings.get("vector")
                label = f"🔍 {len(msg['candidates'])} ứng viên Vector Search (trước Rerank)"
                if t_vector is not None:
                    label += f" ({t_vector:.2f}s)"
                with st.expander(label, expanded=False):
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
                            f"**{i}.** <span style='color:red; font-weight:bold;'>{sim:.2f}</span> &nbsp; **{ref}**\n\n{c.get('content', '')}",
                            unsafe_allow_html=True,
                        )

            # Citations chỉ hiển thị trong tin nhắn assistant (Sau Rerank)
            if role == "assistant" and msg.get("citations"):
                timings = msg.get("timings", {})
                t_rerank = timings.get("rerank")
                label = f"📚 Xem {len(msg['citations'])} điều luật tham khảo (sau Rerank)"
                if t_rerank is not None:
                    label += f" ({t_rerank:.2f}s)"
                with st.expander(label):
                    for i, (citation, chunk) in enumerate(
                        zip(msg["citations"], msg.get("chunks", [])), 1
                    ):
                        rerank_score = chunk.get("rerank_score")
                        score_html = f"<span style='color:red; font-weight:bold;'>{rerank_score:.2f}</span>" if rerank_score is not None else ""
                        st.markdown(
                            f"**{i}.** {score_html} &nbsp; **{citation}**\n\n{chunk.get('content', '')}",
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

    # Gọi controller (hiển thị spinner cho bước retrieval)
    with st.spinner("Đang tìm kiếm và xử lý dữ liệu..."):
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
        # Hiển thị tin nhắn assistant (Không Streaming)
        with st.chat_message("assistant", avatar="⚖️"):
            full_answer = result["answer"]
            st.markdown(full_answer)

            # 🛠️ Hiển thị tổng thời gian xử lý
            if result.get("timings"):
                t_total = result["timings"].get("total")
                if t_total:
                    st.caption(f"⚡ Tổng thời gian xử lý: {t_total:.2f}s")
            
            if result.get("search_query"):
                timings = result.get("timings", {})
                t_expand = timings.get("expand")
                label = "🛠️ Chi tiết truy vấn mở rộng (Query Expansion)"
                if t_expand is not None:
                    label += f" ({t_expand:.2f}s)"
                with st.expander(label, expanded=False):
                    if isinstance(result["search_query"], list):
                        query_text = "\n".join([f"- {q}" for q in result["search_query"]])
                        st.info(f"**Các truy vấn đã dùng:**\n{query_text}")
                    else:
                        st.info(f"**Truy vấn đã dùng:**\n{result['search_query']}")
            
            if result.get("candidates"):
                timings = result.get("timings", {})
                t_vector = timings.get("vector")
                label = f"🔍 {len(result['candidates'])} ứng viên Vector Search (trước Rerank)"
                if t_vector is not None:
                    label += f" ({t_vector:.2f}s)"
                with st.expander(label, expanded=False):
                    for i, c in enumerate(result["candidates"], 1):
                        sim = c.get("similarity", 0)
                        ref = c.get("law_name", "")
                        if c.get("article"): ref += f" – Điều {c['article']}"
                        st.markdown(f"**{i}.** <span style='color:red; font-weight:bold;'>{sim:.2f}</span> &nbsp; **{ref}**\n\n{c.get('content', '')}", unsafe_allow_html=True)

            if result.get("citations"):
                timings = result.get("timings", {})
                t_rerank = timings.get("rerank")
                label = f"📚 Xem {len(result['citations'])} điều luật tham khảo (sau Rerank)"
                if t_rerank is not None:
                    label += f" ({t_rerank:.2f}s)"
                with st.expander(label):
                    for i, (citation, chunk) in enumerate(zip(result["citations"], result.get("chunks", [])), 1):
                        rerank_score = chunk.get("rerank_score", 0)
                        st.markdown(f"**{i}.** <span style='color:red; font-weight:bold;'>{rerank_score:.2f}</span> &nbsp; **{citation}**\n\n{chunk.get('content', '')}", unsafe_allow_html=True)

        # Lưu vào session state
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      full_answer,
            "citations":    result.get("citations", []),
            "chunks":       result.get("chunks", []),
            "candidates":   result.get("candidates", []),
            "search_query": result.get("search_query"),
            "timings":      result.get("timings", {}),
            "error":        None,
        })
