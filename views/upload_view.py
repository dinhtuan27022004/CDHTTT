"""
views/upload_view.py – Giao diện sidebar upload JSON / PDF / DOCX
"""

import streamlit as st
from models.law_model import count_records
from controllers.ingest_controller import ingest_law_file

ACCEPTED_TYPES = ["pdf", "docx", "doc"]


def render_upload_sidebar() -> None:
    """Render phần sidebar: upload file + thống kê số bản ghi DB."""

    # ── Thống kê nhanh ──────────────────────────────────────────────────────
    try:
        total = count_records()
        st.metric(label="📚 Bản ghi trong DB", value=f"{total:,}")
    except Exception as e:
        st.warning(f"⚠️ Không thể kết nối DB: {e}")

    st.markdown("---")
    st.subheader("📥 Import Văn Bản Luật")
    st.caption("Nhận: **PDF**, **DOCX**")

    # ── File uploader ────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        label="Chọn file",
        type=ACCEPTED_TYPES,
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        ext  = uploaded_file.name.rsplit(".", 1)[-1].lower()
        size_kb = uploaded_file.size / 1024

        st.info(
            f"**{uploaded_file.name}**  \n"
            f"`{ext.upper()}` · {size_kb:.1f} KB"
        )

        if st.button("⬆️ Import vào Database", use_container_width=True):
            with st.spinner("Đang xử lý…"):
                result = ingest_law_file(uploaded_file.getvalue(), uploaded_file.name)

            if result["success"]:
                st.success(result["message"])
            else:
                st.warning(result["message"])
                if result["errors"]:
                    with st.expander("📋 Chi tiết lỗi"):
                        for err in result["errors"][:20]:
                            st.text(err)

            st.rerun()

    # ── Thông tin định dạng ──────────────────────────────────────────────────
    with st.expander("ℹ️ Định dạng hỗ trợ"):
        st.markdown(
            """
| Định dạng | Chunking | Metadata |
|-----------|----------|----------|
| **PDF**   | Theo đoạn văn | Từ tên file |
| **DOCX**  | Theo đoạn văn + bảng | Từ tên file |

> **Lưu ý:** File `.doc` (Word cũ) cần đổi sang `.docx` trước khi upload.
            """
        )
