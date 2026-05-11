"""Styled DataFrames, download buttons, client navigation table."""

from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from utils.formatting import fmt_money, fmt_pct, fmt_count, col_label


# ── Display unit helper ────────────────────────────────────────────────────────

def _unit() -> str:
    return st.session_state.get("display_unit", "Cr")


# ── Download buttons ───────────────────────────────────────────────────────────

def render_download_buttons(df: pd.DataFrame, filename_stem: str = "export") -> None:
    col_csv, col_xl = st.columns(2)

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    col_csv.download_button(
        "⬇ Download CSV",
        data=csv_bytes,
        file_name=f"{filename_stem}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    xl_buf = io.BytesIO()
    with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    xl_buf.seek(0)
    col_xl.download_button(
        "⬇ Download Excel",
        data=xl_buf,
        file_name=f"{filename_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ── Client summary table ───────────────────────────────────────────────────────

def render_client_table(df: pd.DataFrame, value_col: str = "outstanding") -> str | None:
    """
    Aggregates to client level, shows a selectable table.
    Returns the selected client_id or None.
    """
    if df.empty:
        st.info("No data for current filters.")
        return None

    agg = (
        df.groupby(["corp_id", "corporate_name", "category"])
        .agg(
            outstanding=("outstanding",    "sum"),
            grand_total=("grand_total",    "sum"),
            amount_received=("amount_received", "sum"),
            tds=("tds",             "sum"),
            bookings=("booking_id",    "count"),
        )
        .reset_index()
        .sort_values(value_col, ascending=False)
    )

    unit = _unit()
    display = agg.copy()
    for col in ["outstanding", "grand_total", "amount_received", "tds"]:
        display[col] = display[col].apply(lambda v: fmt_money(v, unit))
    display = display.rename(columns={
        "corp_id":        "Corp ID",
        "corporate_name": "Corporate Name",
        "category":       "Segment",
        "outstanding":    f"Outstanding ({unit})",
        "grand_total":    f"Grand Total ({unit})",
        "amount_received":f"Received ({unit})",
        "tds":            f"TDS ({unit})",
        "bookings":       "Bookings",
    })

    event = st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    rows = event.selection.get("rows", []) if event.selection else []
    if rows:
        selected_id = agg.iloc[rows[0]]["corp_id"]
        if st.button(f"Open Deep Dive → {agg.iloc[rows[0]]['corporate_name']}", type="primary"):
            st.session_state["deep_dive_client_id"] = selected_id
            st.switch_page("pages/02_deep_dive.py")
        return selected_id
    return None


# ── Generic styled table ───────────────────────────────────────────────────────

def render_table(df: pd.DataFrame, money_cols: list[str] | None = None) -> None:
    if df.empty:
        st.info("No data.")
        return

    unit = _unit()
    display = df.copy()
    if money_cols:
        for col in money_cols:
            if col in display.columns:
                display[col] = display[col].apply(lambda v: fmt_money(v, unit))

    display = display.rename(columns={c: col_label(c) for c in display.columns})
    st.dataframe(display, use_container_width=True, hide_index=True)


# ── Outstanding summary cards ──────────────────────────────────────────────────

def render_flow_metric_cards(
    outstanding: float,
    billed: float,
    unbilled: float,
    tds: float,
    ready_to_bill: float,
    future_co: float,
    pending_co: float,
) -> None:
    unit = _unit()
    cols = st.columns(7)
    data = [
        ("Outstanding",   outstanding),
        ("Billed",        billed),
        ("Unbilled",      unbilled),
        ("TDS",           tds),
        ("Ready to Bill", ready_to_bill),
        ("Future CO",     future_co),
        ("Pending CO",    pending_co),
    ]
    for col, (label, val) in zip(cols, data):
        col.metric(label, fmt_money(val, unit))
