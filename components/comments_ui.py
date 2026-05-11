"""Comment thread UI component."""

from __future__ import annotations
import streamlit as st
from store.comments import add_comment, get_comments, toggle_pin, delete_comment


def render_comments(client_id: str, author: str = "Analyst") -> None:
    with st.expander("💬 Comments & Notes", expanded=False):
        comments = get_comments(client_id)

        if not comments:
            st.caption("No comments yet.")
        else:
            for c in comments:
                pin_icon = "📌" if c.is_pinned else "☆"
                with st.container():
                    cols = st.columns([6, 1, 1])
                    cols[0].markdown(
                        f"**{c.author}** · <span style='color:grey;font-size:12px'>{c.created_at}</span>  \n{c.comment}",
                        unsafe_allow_html=True,
                    )
                    if cols[1].button(pin_icon, key=f"pin_{c.id}", help="Pin / Unpin"):
                        toggle_pin(c.id)
                        st.rerun()
                    if cols[2].button("🗑", key=f"del_{c.id}", help="Delete"):
                        delete_comment(c.id)
                        st.rerun()
                    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

        st.markdown("**Add a note**")
        note_author = st.text_input("Your name", value=author, key=f"comment_author_{client_id}")
        note_text   = st.text_area("Note", key=f"comment_text_{client_id}", height=80)
        if st.button("Post", key=f"comment_submit_{client_id}") and note_text.strip():
            add_comment(client_id, note_author.strip() or "Analyst", note_text.strip())
            st.success("Note saved.")
            st.rerun()
