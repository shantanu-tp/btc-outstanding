"""Cache layer — all pages use this module, never the DB directly."""

from __future__ import annotations

import datetime as dt
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

from store.precompute import (
    run_precompute,
    cache_exists,
    last_refreshed,
    load_client_month,
    load_client_ageing,
    load_raw,
    load_non_stay_raw,
    load_non_stay_ageing,
    load_stay_on_acc,
    load_ns_on_acc,
)


def _ensure_cache() -> None:
    if not cache_exists():
        with st.spinner("Loading data from database…"):
            run_precompute(source="db")


@st.cache_data(show_spinner=False)
def get_client_month() -> pd.DataFrame:
    _ensure_cache()
    return load_client_month()


@st.cache_data(show_spinner=False)
def get_client_ageing() -> pd.DataFrame:
    _ensure_cache()
    return load_client_ageing()


@st.cache_data(show_spinner=False)
def get_raw() -> pd.DataFrame:
    _ensure_cache()
    return load_raw()


@st.cache_data(show_spinner=False)
def get_non_stay_raw() -> pd.DataFrame:
    _ensure_cache()
    return load_non_stay_raw()


@st.cache_data(show_spinner=False)
def get_non_stay_ageing() -> pd.DataFrame:
    _ensure_cache()
    return load_non_stay_ageing()


@st.cache_data(show_spinner=False)
def get_stay_on_acc() -> pd.DataFrame:
    _ensure_cache()
    return load_stay_on_acc()


@st.cache_data(show_spinner=False)
def get_ns_on_acc() -> pd.DataFrame:
    _ensure_cache()
    return load_ns_on_acc()


def clear_cache() -> None:
    get_client_month.clear()
    get_client_ageing.clear()
    get_raw.clear()
    get_non_stay_raw.clear()
    get_non_stay_ageing.clear()
    get_stay_on_acc.clear()
    get_ns_on_acc.clear()
    load_stay_mom.clear()
    load_nonstay_mom.clear()


# ── MTD collections (receipt tables — 1-hour TTL, keyed by date) ─────────────

@st.cache_data(ttl=3600, show_spinner="Loading stay collections…")
def load_stay_mom(today: dt.date) -> pd.DataFrame:
    """MTD collections from receipt_data. Keyed by date — invalidates at midnight."""
    from data.receipts import fetch_stay_mom
    return fetch_stay_mom(today)


@st.cache_data(ttl=3600, show_spinner="Loading non-stay collections…")
def load_nonstay_mom(today: dt.date) -> pd.DataFrame:
    """MTD collections from non_stay_receipt. Keyed by date — invalidates at midnight."""
    from data.receipts import fetch_nonstay_mom
    return fetch_nonstay_mom(today)


def sidebar_refresh_widget() -> None:
    ts = last_refreshed()
    if ts:
        elapsed = int((datetime.now(timezone.utc).replace(tzinfo=None) - ts).total_seconds() / 60)
        st.sidebar.caption(f"Data refreshed {elapsed} min ago")
    else:
        st.sidebar.caption("Connecting to database…")

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        with st.spinner("Fetching from database…"):
            try:
                run_precompute(source="db")
                clear_cache()
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"DB error: {e}")
