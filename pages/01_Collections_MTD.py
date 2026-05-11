"""01 — MoM MTD Collections

Month-to-date payment receipts, same-day-of-month cutoff, last 6 months.
Two sections: Stay (receipt_data) and Non-Stay (non_stay_receipt).

For each section the user can:
  - Track specific clients separately (multiselect) — they appear as individual rows in Summary
  - Toggle between Summary (one total row + tracked clients) and By Client (full client list)
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from components.tables import render_download_buttons
from config.settings import DISPLAY_UNITS, DEFAULT_UNIT
from store.cache import load_nonstay_mom, load_stay_mom
from utils.formatting import fmt_money
from utils.ui import apply_theme, page_header, section

apply_theme()

_TODAY = dt.date.today()

_DAY_SUFFIX = {1: "st", 2: "nd", 3: "rd"}


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{_DAY_SUFFIX.get(n % 10, 'th')}"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## BTC Dashboard")
    current_unit = st.session_state.get("display_unit", DEFAULT_UNIT)
    st.session_state["display_unit"] = st.radio(
        "Unit", DISPLAY_UNITS,
        index=DISPLAY_UNITS.index(current_unit),
    )
    st.markdown("---")
    st.caption(
        f"MTD cutoff: {_ordinal(_TODAY.day)} of each month  \n"
        f"Today: {_TODAY.strftime('%d %b %Y')}"
    )
    if st.button("Refresh collections data", use_container_width=True):
        load_stay_mom.clear()
        load_nonstay_mom.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────

stay_df    = load_stay_mom(_TODAY)
nonstay_df = load_nonstay_mom(_TODAY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _month_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("corporate_id", "corporate_name")]


def _render_section(df: pd.DataFrame, key: str, title: str) -> None:
    section(title)

    if df.empty:
        st.info("No data available.")
        return

    month_cols = _month_cols(df)
    unit = st.session_state.get("display_unit", DEFAULT_UNIT)

    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl1:
        tracked = st.multiselect(
            "Track clients separately",
            options=sorted(df["corporate_name"].dropna().unique()),
            key=f"{key}_tracked",
            placeholder="Select clients to show as separate rows…",
        )
    with ctrl2:
        view = st.radio(
            "View",
            ["Summary", "By Client"],
            key=f"{key}_view",
            horizontal=True,
        )

    fmt = {c: (lambda v, u=unit: fmt_money(v, u)) for c in month_cols}

    if tracked:
        tracked_mask = df["corporate_name"].isin(tracked)
        tracked_df   = df[tracked_mask].copy()
        main_df      = df[~tracked_mask].copy()
    else:
        tracked_df = pd.DataFrame(columns=df.columns)
        main_df    = df.copy()

    # ── Summary view ──────────────────────────────────────────────────────────
    if view == "Summary":
        rows: dict[str, dict] = {
            "Total": {c: main_df[c].sum() for c in month_cols}
        }
        for name in tracked:
            subset = tracked_df[tracked_df["corporate_name"] == name]
            rows[name] = {c: subset[c].sum() for c in month_cols}

        summary_df = pd.DataFrame(rows).T
        summary_df.index.name = "Client"
        st.dataframe(
            summary_df.style.format(fmt, na_rep="—"),
            use_container_width=True,
        )
        render_download_buttons(summary_df.reset_index(), filename_stem=f"{key}_mtd_summary")

    # ── By Client view ────────────────────────────────────────────────────────
    else:
        display_df = df.set_index("corporate_name").drop(columns=["corporate_id"])
        display_df.index.name = "Client"

        st.dataframe(
            display_df.style.format(fmt, na_rep="—"),
            use_container_width=True,
            height=500,
        )
        render_download_buttons(
            display_df.reset_index(),
            filename_stem=f"{key}_mtd_clients",
        )


# ── Page ──────────────────────────────────────────────────────────────────────

page_header(
    "Collections — MoM MTD",
    f"Month-to-date receipts · 1st → {_ordinal(_TODAY.day)} of each month · last 6 months",
)

st.divider()
_render_section(stay_df,    key="stay",    title="Stay")
st.divider()
_render_section(nonstay_df, key="nonstay", title="Non-Stay")
