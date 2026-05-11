"""Sidebar filter component — shared across all pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from config.settings import BOOKING_CATEGORIES, FY_START_MONTH
from data.pipeline import DataStore


@dataclass
class FilterState:
    start_date: date
    end_date: date
    categories: list[str]
    client_ids: list[str]
    metric: str
    regions: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)


# ── Quick-select helpers ───────────────────────────────────────────────────────

def _this_fy_start() -> date:
    today = date.today()
    year  = today.year if today.month >= FY_START_MONTH else today.year - 1
    return date(year, FY_START_MONTH, 1)


def _earliest_date(df: pd.DataFrame) -> date:
    if df.empty or "checkout" not in df.columns:
        return date(2020, 4, 1)
    dt = pd.to_datetime(df["checkout"], errors="coerce").dropna()
    return dt.min().date() if not dt.empty else date(2020, 4, 1)


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_sidebar_filters(ds: DataStore, page_key: str = "shared") -> FilterState:
    df   = ds.master_df
    today = date.today()

    st.sidebar.markdown("## Filters")

    # ── Date quick-select (2×2 grid) ──────────────────────────────────────────
    st.sidebar.markdown("**Date range**")
    q1, q2 = st.sidebar.columns(2)
    q3, q4 = st.sidebar.columns(2)

    if q1.button("This FY",   key=f"{page_key}_btn_thisfy",  use_container_width=True):
        st.session_state[f"{page_key}_date_start"] = _this_fy_start()
        st.session_state[f"{page_key}_date_end"]   = today

    if q2.button("Last 6M",   key=f"{page_key}_btn_6m",     use_container_width=True):
        st.session_state[f"{page_key}_date_start"] = today - timedelta(days=183)
        st.session_state[f"{page_key}_date_end"]   = today

    if q3.button("Last 3M",   key=f"{page_key}_btn_3m",     use_container_width=True):
        st.session_state[f"{page_key}_date_start"] = today - timedelta(days=91)
        st.session_state[f"{page_key}_date_end"]   = today

    if q4.button("All",       key=f"{page_key}_btn_all",    use_container_width=True):
        st.session_state[f"{page_key}_date_start"] = _earliest_date(df)
        st.session_state[f"{page_key}_date_end"]   = today

    default_start = st.session_state.get(f"{page_key}_date_start", _this_fy_start())
    default_end   = st.session_state.get(f"{page_key}_date_end",   today)

    start_date = st.sidebar.date_input(
        "From", value=default_start, key=f"{page_key}_start_date_input",
    )
    end_date = st.sidebar.date_input(
        "To",   value=default_end,   key=f"{page_key}_end_date_input",
    )
    st.session_state[f"{page_key}_date_start"] = start_date
    st.session_state[f"{page_key}_date_end"]   = end_date

    st.sidebar.markdown("---")

    # ── Metric selector ────────────────────────────────────────────────────────
    metric = st.sidebar.selectbox(
        "Primary metric",
        options=["outstanding", "grand_total", "effective_total", "amount_received"],
        format_func=lambda x: x.replace("_", " ").title(),
        key=f"{page_key}_metric",
    )

    st.sidebar.markdown("---")

    # ── Segment expander ───────────────────────────────────────────────────────
    with st.sidebar.expander("Segments & Clients", expanded=False):
        # Category filter
        _cat_key = f"{page_key}_categories"
        _cat_opts = BOOKING_CATEGORIES
        _cat_prev = [v for v in st.session_state.get(_cat_key, _cat_opts) if v in _cat_opts]
        categories = st.multiselect("Category", options=_cat_opts, default=_cat_prev)
        st.session_state[_cat_key] = categories

        # Region filter
        _reg_key  = f"{page_key}_regions"
        _reg_opts = sorted(df["location"].dropna().unique().tolist()) if "location" in df.columns else []
        _reg_prev = [v for v in st.session_state.get(_reg_key, []) if v in _reg_opts]
        regions = st.multiselect("Location / Region", options=_reg_opts, default=_reg_prev)
        st.session_state[_reg_key] = regions

        # Status filter
        _stat_key  = f"{page_key}_statuses"
        _stat_opts = sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else []
        _stat_prev = [v for v in st.session_state.get(_stat_key, []) if v in _stat_opts]
        statuses = st.multiselect("Status", options=_stat_opts, default=_stat_prev)
        st.session_state[_stat_key] = statuses

        # Client filter
        _cli_key  = f"{page_key}_client_ids"
        _cli_opts = sorted(df["corp_id"].dropna().unique().tolist()) if "corp_id" in df.columns else []
        _cli_prev = [v for v in st.session_state.get(_cli_key, []) if v in _cli_opts]
        client_ids = st.multiselect("Corp ID", options=_cli_opts, default=_cli_prev)
        st.session_state[_cli_key] = client_ids

    return FilterState(
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        client_ids=client_ids,
        metric=metric,
        regions=regions,
        statuses=statuses,
    )


# ── apply_filters ──────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, fs: FilterState) -> pd.DataFrame:
    if df.empty:
        return df

    # Date filter on checkout
    if "checkout" in df.columns:
        dt = pd.to_datetime(df["checkout"], errors="coerce")
        df = df[
            (dt.dt.date >= fs.start_date) &
            (dt.dt.date <= fs.end_date)
        ]

    if fs.categories:
        df = df[df["category"].isin(fs.categories)]

    if fs.regions:
        df = df[df["location"].isin(fs.regions)]

    if fs.statuses:
        df = df[df["status"].isin(fs.statuses)]

    if fs.client_ids:
        df = df[df["corp_id"].isin(fs.client_ids)]

    return df
