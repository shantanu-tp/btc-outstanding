"""Client × Month Outstanding."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import datetime as _dt
import streamlit as st
import pandas as pd

st.set_page_config(page_title="BTC | Client Outstanding", layout="wide")

from utils.ui import apply_theme, page_header
from store.cache import get_client_month, get_stay_on_acc, sidebar_refresh_widget
from store.comments import init_db
from utils.formatting import fmt_money
from config.settings import DISPLAY_UNITS, DEFAULT_UNIT, UNIT_DIVISOR, FY_START_MONTH

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

unit    = st.session_state.get("display_unit", "Cr")
divisor = UNIT_DIVISOR.get(unit, 1e7)

# ── Data ──────────────────────────────────────────────────────────────────────
df        = get_client_month()
oac_s     = get_stay_on_acc().set_index("corp_id")["on_account"]

page_header("Client Outstanding", "Outstanding balance by checkout month")
st.markdown("---")

if df.empty:
    st.info("No data — use the refresh button to load from DB.")
    st.stop()

# ── Month default (This FY) ───────────────────────────────────────────────────
all_months = sorted(
    df["co_month"].dropna().unique(),
    key=lambda m: pd.to_datetime(m, format="%b-%y", errors="coerce"),
)
name_map    = df.groupby("corp_id")["corporate_name"].first() if "corporate_name" in df.columns else {}
all_clients = sorted(df["corp_id"].dropna().unique())
all_client_opts = [f"{cid} — {name_map.get(cid, cid)}" for cid in all_clients]

_today = _dt.date.today()
_fy_start_year = _today.year if _today.month >= FY_START_MONTH else _today.year - 1
_fy_start = pd.Timestamp(_fy_start_year, FY_START_MONTH, 1)
_fy_months = [m for m in all_months
              if pd.to_datetime(m, format="%b-%y", errors="coerce") >= _fy_start] \
             or all_months[-6:]
_default_6m = all_months[-6:] if len(all_months) >= 6 else all_months

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    mc1, mc2 = st.columns(2)
    mc3, mc4 = st.columns(2)
    if mc1.button("3M",      key="om_3m",  use_container_width=True):
        st.session_state["om_months"] = all_months[-3:] if len(all_months) >= 3 else all_months
    if mc2.button("6M",      key="om_6m",  use_container_width=True):
        st.session_state["om_months"] = _default_6m
    if mc3.button("This FY", key="om_fy",  use_container_width=True):
        st.session_state["om_months"] = _fy_months
    if mc4.button("All",     key="om_all", use_container_width=True):
        st.session_state["om_months"] = list(all_months)

    _prev = [m for m in st.session_state.get("om_months", _default_6m) if m in all_months]
    sel_months = st.multiselect("Months", options=all_months, default=_prev)
    st.session_state["om_months"] = sel_months

    st.markdown("---")
    _prev_c = [o for o in st.session_state.get("om_clients", []) if o in all_client_opts]
    sel_client_opts = st.multiselect("Client", options=all_client_opts, default=_prev_c, placeholder="Search by ID or name…")
    st.session_state["om_clients"] = sel_client_opts
    sel_clients = [o.split(" — ")[0] for o in sel_client_opts]

    sort_by = st.selectbox("Sort by", ["Total"] + (sel_months or list(all_months)), key="om_sort")

# ── Filter & pivot ────────────────────────────────────────────────────────────
filt = df.copy()
if sel_months:
    filt = filt[filt["co_month"].isin(sel_months)]
if sel_clients:
    filt = filt[filt["corp_id"].isin(sel_clients)]

if filt.empty:
    st.info("No data for the selected filters.")
    st.stop()

pivot = filt.pivot_table(
    index="corp_id", columns="co_month",
    values="outstanding_billed", aggfunc="sum", fill_value=0,
)
sorted_cols = sorted(
    pivot.columns,
    key=lambda m: pd.to_datetime(m, format="%b-%y", errors="coerce"),
)
pivot = pivot[sorted_cols]
pivot["Total"] = pivot.sum(axis=1)

sort_col = sort_by if sort_by in pivot.columns else "Total"
pivot = pivot.sort_values(sort_col, ascending=False)

pivot["On Acc"]           = pivot.index.map(oac_s).fillna(0.0)
pivot["O/S after On Acc"] = pivot["Total"] - pivot["On Acc"]
pivot.insert(0, "Name", pivot.index.map(name_map).fillna(""))

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_os      = pivot["Total"].sum()
all_time_total = df["outstanding_billed"].sum()
# On Account is a live balance — unaffected by month filter, only by client filter
if sel_clients:
    total_on_acc = oac_s[oac_s.index.isin(sel_clients)].sum()
else:
    total_on_acc = oac_s.sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Outstanding (filtered)",  fmt_money(total_os, unit))
k2.metric("On Account",              fmt_money(total_on_acc, unit))
k3.metric("All-time total",          fmt_money(all_time_total, unit))
k4.metric("Clients",                 f"{len(pivot):,}")
k5.metric("Months",                  str(len(sorted_cols)))

st.markdown("---")

# ── Table ─────────────────────────────────────────────────────────────────────
numeric_cols = [c for c in pivot.columns if c != "Name"]
display = pivot.copy()
display[numeric_cols] = (pivot[numeric_cols] / divisor).round(2)

def _hl(val):
    if not isinstance(val, (int, float)) or val <= 0:
        return "color: #cbd5e1"
    if val > display["Total"].quantile(0.75):
        return "background-color: #eff6ff; font-weight: 600"
    if val > display["Total"].quantile(0.5):
        return "background-color: #f8fafc"
    return ""

st.caption(f"₹ {unit} · sorted by {sort_by}")
styled = display.style.format("{:,.2f}", subset=numeric_cols).applymap(_hl, subset=numeric_cols)
st.dataframe(styled, use_container_width=True, height=min(580, 44 + len(pivot) * 36))

st.markdown("---")

# ── Trend for selected client ─────────────────────────────────────────────────
trend_opts = [""] + [f"{cid} — {name_map.get(cid, cid)}" for cid in pivot.index]
sel_trend = st.selectbox("Monthly trend — select client", trend_opts)
if sel_trend:
    sel_client = sel_trend.split(" — ")[0]
    import plotly.graph_objects as go
    from components.charts import _CHART_LAYOUT, _BLUE_MID
    row = pivot.loc[sel_client, sorted_cols] / divisor
    fig = go.Figure(go.Bar(
        x=list(row.index), y=list(row.values),
        marker_color=_BLUE_MID, marker_line_width=0,
    ))
    fig.update_layout(
        height=260,
        xaxis=dict(type="category", tickfont=dict(size=10)),
        yaxis=dict(title=f"₹ {unit}", gridcolor="#f1f5f9"),
        **_CHART_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True, key="om_trend")

st.markdown("---")

# ── Download ──────────────────────────────────────────────────────────────────
col_csv, col_xl = st.columns(2)
raw_exp = filt.copy()
raw_exp["outstanding_billed"] /= divisor

col_csv.download_button(
    "Download CSV", raw_exp.to_csv(index=False).encode("utf-8-sig"),
    file_name="client_month_outstanding.csv", mime="text/csv", use_container_width=True,
)
xl_buf = io.BytesIO()
with pd.ExcelWriter(xl_buf, engine="openpyxl") as w:
    (pivot / divisor).round(2).to_excel(w, sheet_name="Outstanding")
xl_buf.seek(0)
col_xl.download_button(
    "Download Excel", xl_buf,
    file_name="client_month_outstanding.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
