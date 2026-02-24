"""
app.py – Entrypoint của ứng dụng Chatbot Tra Cứu Luật Việt Nam
Kiến trúc MVC: Streamlit + PostgreSQL/pgvector + OpenRouter
"""

import streamlit as st
from models.db import init_db
from views.upload_view import render_upload_sidebar
from views.chat_view import render_chat_main

# ── Cấu hình trang ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot Tra Cứu Luật Việt Nam",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# # ── Khởi tạo DB một lần khi app start ──────────────────────────────────────
@st.cache_resource(show_spinner="Đang kết nối cơ sở dữ liệu...")
def startup():
    init_db()

startup()

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ Luật Việt Nam")
    st.markdown("---")
    render_upload_sidebar()

# ── Nội dung chính ──────────────────────────────────────────────────────────
render_chat_main()
