"""Client × Ageing Bucket Outstanding — Stay and Non-Stay."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import streamlit as st
import pandas as pd

st.set_page_config(page_title="BTC | Ageing", layout="wide")

from utils.ui import apply_theme, page_header
from store.cache import (get_client_ageing, get_non_stay_ageing,
                          get_stay_on_acc, get_ns_on_acc, sidebar_refresh_widget)
from store.comments import init_db
from config.settings import AGEING_LABELS, DISPLAY_UNITS, DEFAULT_UNIT, UNIT_DIVISOR
from data.pg_non_stay import NON_STAY_AGEING_LABELS, NON_STAY_SUB_CATS
from utils.formatting import fmt_money
from components.charts import ageing_client_bar

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
df          = get_client_ageing()
ns_age      = get_non_stay_ageing()
stay_oac_s  = get_stay_on_acc().set_index("corp_id")["on_account"]
ns_oac_s    = get_ns_on_acc().set_index("corp_id")["on_account"]

page_header("Client Ageing", "Outstanding by ageing bucket")
st.markdown("---")

# ── Sidebar filters (shared by both sections) ─────────────────────────────────
all_clients    = sorted(set(df["corp_id"].dropna().unique()) |
                        set(ns_age["corp_id"].dropna().unique()))
all_s_buckets  = [b for b in AGEING_LABELS if b in df["ageing_bucket"].unique()]

with st.sidebar:
    st.markdown("### Filters")
    _prev_b = [b for b in st.session_state.get("ag_buckets", all_s_buckets) if b in all_s_buckets]
    sel_buckets = st.multiselect("Stay — Ageing Bucket", options=all_s_buckets, default=_prev_b)
    st.session_state["ag_buckets"] = sel_buckets

    st.markdown("---")
    _prev_c = [c for c in st.session_state.get("ag_clients", []) if c in all_clients]
    sel_clients = st.multiselect("Corp ID", options=all_clients, default=_prev_c)
    st.session_state["ag_clients"] = sel_clients

    sort_by = st.selectbox("Sort by", ["Total Outstanding"] + all_s_buckets, key="ag_sort")


# ── Shared rendering helper ────────────────────────────────────────────────────

_BUCKET_BG_STAY = {
    "00-15 Days":   "#f0fdf4", "16-30 Days":   "#f0fdf4",
    "31-45 Days":   "#fefce8", "46-60 Days":   "#fefce8",
    "61-90 Days":   "#fff7ed",
    "91-120 Days":  "#fef2f2", "121-150 Days": "#fef2f2",
    "151-180 Days": "#fee2e2", "181-365 Days": "#fee2e2",
    "365+ Days":    "#fecaca",
}
_BUCKET_BG_NS = {
    "0-15 D":    "#f0fdf4", "16-30 D":   "#f0fdf4",
    "31-45 D":   "#fefce8", "46-60 D":   "#fefce8",
    "61-90 D":   "#fff7ed",
    "91-120 D":  "#fef2f2", "121-150 D": "#fef2f2",
    "151-180 D": "#fee2e2", "181-365 D": "#fee2e2",
    "365+ D":    "#fecaca",
}


def _render_ageing_pivot(
    data: pd.DataFrame,
    ageing_labels: list[str],
    bucket_bg: dict,
    overdue_buckets: list[str],
    on_acc_s: pd.Series | None = None,
    sort_col_override: str | None = None,
    key_prefix: str = "ag",
) -> None:
    if data.empty:
        st.caption("No data.")
        return

    all_buckets = [b for b in ageing_labels if b in data["ageing_bucket"].unique()]
    pivot = data.pivot_table(
        index="corp_id", columns="ageing_bucket",
        values="outstanding_billed", aggfunc="sum", fill_value=0,
    )
    ordered_cols = [b for b in all_buckets if b in pivot.columns]
    pivot = pivot.reindex(columns=ordered_cols, fill_value=0)
    pivot["Total"] = pivot.sum(axis=1)

    if on_acc_s is not None:
        pivot["On Acc"]           = pivot.index.map(on_acc_s).fillna(0.0)
        pivot["O/S after On Acc"] = pivot["Total"] - pivot["On Acc"]

    sc = sort_col_override if sort_col_override in pivot.columns else "Total"
    pivot = pivot.sort_values(sc, ascending=False)

    total_os   = pivot["Total"].sum()
    on_acc_tot = pivot["On Acc"].sum() if "On Acc" in pivot.columns else 0.0
    overdue_90 = pivot[[b for b in overdue_buckets if b in pivot.columns]].sum().sum()
    pct        = (overdue_90 / total_os * 100) if total_os else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Outstanding", fmt_money(total_os, unit))
    k2.metric("On Account",        fmt_money(on_acc_tot, unit))
    k3.metric("O/S after On Acc",  fmt_money(total_os - on_acc_tot, unit))
    k4.metric("Overdue >90 days",  fmt_money(overdue_90, unit))
    k5.metric("Clients",           f"{len(pivot):,}")

    display = (pivot / divisor).round(2)

    def _cell(val, col):
        if not isinstance(val, (int, float)) or val == 0:
            return "color: #cbd5e1"
        bg = bucket_bg.get(col, "")
        fw = "font-weight: 600" if col in ("Total", "O/S after On Acc") else ""
        parts = [p for p in [f"background-color: {bg}" if bg else "", fw] if p]
        return "; ".join(parts)

    styled = display.style.format("{:,.2f}")
    for col in display.columns:
        styled = styled.applymap(lambda v, c=col: _cell(v, c), subset=[col])

    st.caption(f"₹ {unit}")
    st.dataframe(styled, use_container_width=True, height=min(560, 44 + len(pivot) * 36))
    st.markdown("---")

    st.markdown("### Top 15 clients")
    st.plotly_chart(
        ageing_client_bar(pivot, ordered_cols, n=15, unit=unit, divisor=divisor),
        use_container_width=True,
        key=f"{key_prefix}_chart",
    )
    st.markdown("---")

    # Download
    col_csv, col_xl = st.columns(2)
    raw_exp = data.copy()
    raw_exp["outstanding_billed"] /= divisor
    col_csv.download_button(
        "Download CSV", raw_exp.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{key_prefix}_ageing.csv", mime="text/csv", use_container_width=True,
    )
    xl_buf = io.BytesIO()
    with pd.ExcelWriter(xl_buf, engine="openpyxl") as w:
        (pivot / divisor).round(2).to_excel(w, sheet_name="Ageing")
    xl_buf.seek(0)
    col_xl.download_button(
        "Download Excel", xl_buf,
        file_name=f"{key_prefix}_ageing.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — STAY AGEING
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Stay")

if df.empty:
    st.info("No stay ageing data.")
else:
    filt = df.copy()
    if sel_buckets:
        filt = filt[filt["ageing_bucket"].isin(sel_buckets)]
    if sel_clients:
        filt = filt[filt["corp_id"].isin(sel_clients)]

    sort_col = "Total" if sort_by == "Total Outstanding" else sort_by

    if filt.empty:
        st.info("No data for the selected filters.")
    else:
        _render_ageing_pivot(
            data=filt,
            ageing_labels=AGEING_LABELS,
            bucket_bg=_BUCKET_BG_STAY,
            overdue_buckets=["91-120 Days", "121-150 Days", "151-180 Days",
                             "181-365 Days", "365+ Days"],
            on_acc_s=stay_oac_s,
            sort_col_override=sort_col,
            key_prefix="stay",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — NON-STAY AGEING (per sub-category)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## Non-Stay")

present_cats = [c for c in NON_STAY_SUB_CATS if c in ns_age["sub_category"].unique()]
ns_tabs = st.tabs(present_cats)

for tab, cat in zip(ns_tabs, present_cats):
    with tab:
        cat_data = ns_age[ns_age["sub_category"] == cat].copy()
        if sel_clients:
            cat_data = cat_data[cat_data["corp_id"].isin(sel_clients)]

        _render_ageing_pivot(
            data=cat_data,
            ageing_labels=NON_STAY_AGEING_LABELS,
            bucket_bg=_BUCKET_BG_NS,
            overdue_buckets=["91-120 D", "121-150 D", "151-180 D", "181-365 D", "365+ D"],
            on_acc_s=ns_oac_s,
            key_prefix=f"ns_{cat.lower().replace(' / ', '_').replace(' ', '_')}",
        )
