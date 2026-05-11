"""01 — MoM MTD Collections

Month-to-date payment receipts, same-day-of-month cutoff, last 6 months.
Two sections: Stay (receipt_data) and Non-Stay (non_stay_receipt).

For each section the user can:
  - Exclude a client by ID or name → splits the total into "excl. X" + "X"
  - Toggle between Summary (one total row) and By Client (full client list)
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from components.tables import render_download_buttons
from config.settings import DISPLAY_UNITS, DEFAULT_UNIT, UNIT_DIVISOR
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


def _match_mask(df: pd.DataFrame, query: str) -> pd.Series:
    q = query.strip().lower()
    by_id   = df["corporate_id"].str.lower() == q
    by_name = df["corporate_name"].str.lower().str.contains(q, na=False, regex=False)
    return by_id | by_name


def _render_section(df: pd.DataFrame, key: str, title: str) -> None:
    section(title)

    if df.empty:
        st.info("No data available.")
        return

    month_cols = _month_cols(df)
    unit = st.session_state.get("display_unit", DEFAULT_UNIT)

    ctrl1, ctrl2 = st.columns([3, 1])
    with ctrl1:
        excl_input = st.text_input(
            "Exclude client (ID or name)",
            key=f"{key}_excl",
            placeholder="e.g. 25902 or Zomato — leave blank to show all",
        )
    with ctrl2:
        view = st.radio(
            "View",
            ["Summary", "By Client"],
            key=f"{key}_view",
            horizontal=True,
        )

    if excl_input.strip():
        mask    = _match_mask(df, excl_input)
        excl_df = df[mask].copy()
        main_df = df[~mask].copy()
        n_matched = int(mask.sum())
    else:
        excl_df   = pd.DataFrame(columns=df.columns)
        main_df   = df.copy()
        n_matched = 0

    if n_matched > 0:
        names = ", ".join(excl_df["corporate_name"].unique()[:3])
        if n_matched > 3:
            names += f" +{n_matched - 3} more"
        st.caption(f"Excluding: **{names}**")

    fmt = {c: (lambda v, u=unit: fmt_money(v, u)) for c in month_cols}

    # ── Summary view ──────────────────────────────────────────────────────────
    if view == "Summary":
        if excl_input.strip() and not excl_df.empty:
            excl_label = (
                excl_df["corporate_name"].iloc[0]
                if len(excl_df) == 1
                else excl_input.strip()
            )
            rows = {
                f"Total (excl. {excl_label})": {c: main_df[c].sum() for c in month_cols},
                excl_label:                    {c: excl_df[c].sum() for c in month_cols},
            }
        else:
            rows = {"All Clients": {c: df[c].sum() for c in month_cols}}

        summary_df = pd.DataFrame(rows).T
        summary_df.index.name = "Client"
        st.dataframe(
            summary_df.style.format(fmt, na_rep="—"),
            use_container_width=True,
        )
        render_download_buttons(summary_df.reset_index(), filename_stem=f"{key}_mtd_summary")

    # ── By Client view ────────────────────────────────────────────────────────
    else:
        if excl_input.strip() and not excl_df.empty:
            display_df = pd.concat([excl_df, main_df], ignore_index=True)
        else:
            display_df = df.copy()

        display_df = display_df.set_index("corporate_name")
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
