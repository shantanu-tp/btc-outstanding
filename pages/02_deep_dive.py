"""Client Deep Dive."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="BTC | Deep Dive", layout="wide")

from utils.ui import apply_theme
from store.cache import get_raw, sidebar_refresh_widget
from store.comments import init_db
from config.settings import EXCLUDED_STATUSES, DISPLAY_UNITS, DEFAULT_UNIT, UNIT_DIVISOR, AGEING_LABELS
from utils.formatting import fmt_money
from components.charts import simple_bar

apply_theme()
init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## BTC Dashboard")
    if "display_unit" not in st.session_state:
        st.session_state["display_unit"] = DEFAULT_UNIT
    st.session_state["display_unit"] = st.radio(
        "Unit", DISPLAY_UNITS,
        index=DISPLAY_UNITS.index(st.session_state["display_unit"]),
    )
    st.markdown("---")
    sidebar_refresh_widget()
    st.markdown("### Client")

unit    = st.session_state.get("display_unit", "Cr")
divisor = UNIT_DIVISOR.get(unit, 1e7)

df_all = get_raw()
all_clients = sorted(df_all["corp_id"].dropna().unique().tolist())

with st.sidebar:
    pre = str(st.session_state.get("deep_dive_client_id", ""))
    default_idx = all_clients.index(pre) if pre in all_clients else 0
    sel_client = st.selectbox("Corp ID", options=all_clients, index=default_idx)
    st.session_state["deep_dive_client_id"] = sel_client

# ── Data ──────────────────────────────────────────────────────────────────────
df     = df_all[df_all["corp_id"] == str(sel_client)]
active = df[~df["status"].isin(EXCLUDED_STATUSES)] if "status" in df.columns else df

corp_name = (
    active["corporate_name"].dropna().iloc[0]
    if "corporate_name" in active.columns and len(active) > 0
    else sel_client
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"## {corp_name}")
st.caption(f"Corp ID: {sel_client} · {len(active):,} active bookings")
st.markdown("---")

# ── KPIs ──────────────────────────────────────────────────────────────────────
outstanding  = float(active["outstanding"].sum())    if "outstanding"    in active.columns else 0.0
tds          = float(active["tds"].sum())            if "tds"            in active.columns else 0.0
grand_total  = float(active["grand_total"].sum())    if "grand_total"    in active.columns else 0.0
received     = float(active["amount_received"].sum())if "amount_received"in active.columns else 0.0
write_off    = float(active["write_off"].sum())      if "write_off"      in active.columns else 0.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Outstanding",     fmt_money(outstanding, unit))
k2.metric("TDS",             fmt_money(tds, unit))
k3.metric("Grand Total",     fmt_money(grand_total, unit))
k4.metric("Received",        fmt_money(received, unit))
k5.metric("Write-off",       fmt_money(write_off, unit))

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
c_age, c_mo = st.columns(2)

with c_age:
    if "ageing" in active.columns:
        ageing_s = (
            active[active["ageing"].isin(AGEING_LABELS)]
            .groupby("ageing")["outstanding"]
            .sum()
            .reindex(AGEING_LABELS)
            .fillna(0)
            / divisor
        )
        from components.charts import _AGEING_PALETTE
        import plotly.graph_objects as go
        fig_a = go.Figure(go.Bar(
            x=[str(b) for b in ageing_s.index],
            y=ageing_s.values,
            marker_color=_AGEING_PALETTE[:len(ageing_s)],
            marker_line_width=0,
        ))
        from components.charts import _CHART_LAYOUT
        fig_a.update_layout(
            height=280,
            xaxis=dict(title="", type="category", tickfont=dict(size=9)),
            yaxis=dict(title=f"₹ {unit}", gridcolor="#f1f5f9"),
            **_CHART_LAYOUT,
        )
        st.markdown("### By Ageing Bucket")
        st.plotly_chart(fig_a, use_container_width=True, key="dd_ageing")

with c_mo:
    if "co_month" in active.columns:
        month_df = (
            active[active["co_month"].notna()]
            .groupby("co_month")["outstanding"].sum()
            .reset_index()
        )
        month_df["_s"] = pd.to_datetime(month_df["co_month"], format="%b-%y", errors="coerce")
        month_df = month_df.sort_values("_s").drop(columns="_s")
        st.markdown("### By Checkout Month")
        st.plotly_chart(
            simple_bar(
                x=month_df["co_month"].tolist(),
                y=(month_df["outstanding"] / divisor).tolist(),
                y_title=f"₹ {unit}",
                height=280,
            ),
            use_container_width=True,
            key="dd_month",
        )

st.markdown("---")

# ── Booking detail ────────────────────────────────────────────────────────────
st.markdown("### Bookings")
show_cols = [c for c in [
    "booking_id", "status", "invoice_no", "property_name", "location",
    "checkin", "checkout", "co_month", "ageing",
    "grand_total", "amount_received", "tds", "outstanding", "remarks",
] if c in active.columns]

st.dataframe(active[show_cols], use_container_width=True, hide_index=True, height=380)
