"""Shared UI helpers — inject once per page via apply_theme()."""

from __future__ import annotations
import streamlit as st

_CSS = """
<style>
/* ── Hide Streamlit chrome ─────────────────────────────────────────────────── */
#MainMenu, footer { display: none !important; }
header, [data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }

/* ── Typography ────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, sans-serif !important;
    color: #1e293b;
}

/* ── Layout ────────────────────────────────────────────────────────────────── */
.main .block-container {
    padding-top: 0.5rem;
    padding-bottom: 1.5rem;
    max-width: 1440px;
}

/* ── Headings ──────────────────────────────────────────────────────────────── */
h1 {
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: #0f172a !important;
    letter-spacing: -0.01em;
    margin-bottom: 0.1rem !important;
}
h2 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #1e293b !important;
    margin-top: 1.5rem !important;
}
h3 {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: #334155 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ── Caption / helper text ─────────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] p {
    color: #94a3b8 !important;
    font-size: 0.75rem !important;
}

/* ── Divider ───────────────────────────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; margin: 1rem 0 !important; }

/* ── Metric cards (Streamlit native) ──────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.7rem !important;
    font-weight: 500;
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.8rem;
    color: #475569;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.8rem;
}
[data-testid="stSidebar"] h2 {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    text-transform: none !important;
    letter-spacing: normal !important;
}

/* ── Buttons ───────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    border: 1px solid #e2e8f0;
    background: #fff;
    color: #334155;
    transition: background 0.15s;
}
.stButton > button:hover { background: #f1f5f9; }

/* ── Download buttons — compact ────────────────────────────────────────────── */
.stDownloadButton > button {
    border-radius: 6px !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    padding: 0.2rem 0.6rem !important;
    height: 1.9rem !important;
    min-height: 0 !important;
    border: 1px solid #e2e8f0 !important;
    background: #f8fafc !important;
    color: #334155 !important;
}
.stDownloadButton > button:hover { background: #f1f5f9 !important; }

/* ── Sidebar compact ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] { margin-bottom: 0.2rem !important; }
[data-testid="stSidebar"] [data-testid="stMultiSelect"] { margin-bottom: 0.2rem !important; }
[data-testid="stSidebar"] .stSelectbox { margin-bottom: 0.2rem !important; }

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #e2e8f0;
}
[data-baseweb="tab"] {
    font-size: 0.8rem !important;
    font-weight: 500;
    color: #64748b !important;
    padding: 8px 16px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #1e40af !important;
    border-bottom: 2px solid #1e40af !important;
}

/* ── DataFrames ────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    overflow: hidden;
}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    """Render a compact page title + optional subtitle line."""
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


def kpi_row(metrics: list[tuple[str, str]]) -> None:
    """
    Render a row of native Streamlit metric cards.
    metrics: list of (label, formatted_value)
    """
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


def section(label: str) -> None:
    """A lightweight section divider — just a small label, no <hr> spam."""
    st.markdown(f"### {label}")
