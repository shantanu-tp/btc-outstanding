"""BTC Analytics Dashboard — home page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="BTC | Outstanding",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.ui import apply_theme, page_header
from store.cache import get_raw, get_non_stay_raw, get_stay_on_acc, get_ns_on_acc, sidebar_refresh_widget
from store.comments import init_db
from components.charts import outstanding_flow_chart
from components.tables import render_flow_metric_cards, render_download_buttons
from config.settings import DEFAULT_UNIT, DISPLAY_UNITS, EXCLUDED_STATUSES
from data.pg_non_stay import NON_STAY_SUB_CATS
from utils.formatting import fmt_money

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

df_all       = get_raw()
stay_oac_s   = get_stay_on_acc().set_index("corp_id")["on_account"]
ns_oac_s     = get_ns_on_acc().set_index("corp_id")["on_account"]


def _flow_numbers(df: pd.DataFrame) -> dict:
    active = df[~df["status"].isin(EXCLUDED_STATUSES)] if "status" in df.columns else df
    billed      = float(active["outstanding"].sum())  if "outstanding" in active.columns else 0.0
    tds         = float(active["tds"].sum())          if "tds"         in active.columns else 0.0
    return dict(
        outstanding=billed + tds,
        billed=billed,
        unbilled=0.0,
        tds=tds,
        ready_to_bill=0.0,
        future_co=0.0,
        pending_co=0.0,
    )


# ── Page header ───────────────────────────────────────────────────────────────
page_header("Outstanding Overview")
st.markdown("---")

# ── Overall KPIs + flow ───────────────────────────────────────────────────────
overall = _flow_numbers(df_all)
render_flow_metric_cards(**overall)
st.plotly_chart(outstanding_flow_chart(**overall), use_container_width=True, key="flow_overall")

st.markdown("---")

# ── Segment tabs ──────────────────────────────────────────────────────────────
tab_corp, tab_mice, tab_sel = st.tabs(["Corporates", "MICE", "Selected Accounts"])

for tab, seg_name in zip(
    [tab_corp, tab_mice, tab_sel],
    ["Corporates", "MICE", "Selected Accounts"],
):
    with tab:
        seg_df = df_all[df_all["category"] == seg_name] if "category" in df_all.columns else df_all
        if seg_df.empty:
            st.caption(f"No data for {seg_name}.")
            continue
        seg_nums = _flow_numbers(seg_df)
        render_flow_metric_cards(**seg_nums)
        st.plotly_chart(outstanding_flow_chart(**seg_nums, title=seg_name),
                        use_container_width=True, key=f"flow_seg_{seg_name}")

st.markdown("---")

# ── Account-level table ───────────────────────────────────────────────────────
if not df_all.empty:
    grp_cols = ["corp_id", "category"] if "category" in df_all.columns else ["corp_id"]
    active_all = (
        df_all[~df_all["status"].isin(EXCLUDED_STATUSES)]
        if "status" in df_all.columns else df_all
    )

    agg = (
        active_all.groupby(grp_cols)
        .agg(
            outstanding     = ("outstanding",     "sum"),
            tds             = ("tds",             "sum"),
            grand_total     = ("grand_total",     "sum"),
            amount_received = ("amount_received", "sum"),
            bookings        = ("booking_id",      "count"),
        )
        .reset_index()
        .sort_values("outstanding", ascending=False)
    )
    agg["billed"]      = agg["outstanding"]
    agg["on_account"]  = agg["corp_id"].map(stay_oac_s).fillna(0.0)
    agg["net_os"]      = agg["outstanding"] - agg["on_account"]

    unit = st.session_state.get("display_unit", "Cr")
    display_agg = agg.copy()
    for col in ["outstanding", "billed", "tds", "grand_total", "amount_received",
                "on_account", "net_os"]:
        if col in display_agg.columns:
            display_agg[col] = display_agg[col].apply(lambda v: fmt_money(v, unit))

    display_agg = display_agg.rename(columns={
        "corp_id":          "Corp ID",
        "category":         "Segment",
        "outstanding":      f"Outstanding ({unit})",
        "billed":           f"Billed ({unit})",
        "tds":              f"TDS ({unit})",
        "grand_total":      f"Grand Total ({unit})",
        "amount_received":  f"Received ({unit})",
        "bookings":         "Bookings",
        "on_account":       f"On Acc ({unit})",
        "net_os":           f"O/S after On Acc ({unit})",
    })

    event = st.dataframe(
        display_agg,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    rows = event.selection.get("rows", []) if event.selection else []
    if rows:
        sel_row  = agg.iloc[rows[0]]
        sel_id   = sel_row["corp_id"]
        sel_df   = df_all[df_all["corp_id"] == sel_id]
        sel_nums = _flow_numbers(sel_df)

        st.markdown(f"**{sel_id}**")
        render_flow_metric_cards(**sel_nums)
        st.plotly_chart(outstanding_flow_chart(**sel_nums, title=sel_id),
                        use_container_width=True, key="flow_selected_client")

        if st.button("Open Deep Dive →", type="primary"):
            st.session_state["deep_dive_client_id"] = sel_id
            st.switch_page("pages/02_deep_dive.py")

    st.markdown("---")
    render_download_buttons(agg, filename_stem="outstanding_summary")

# ══════════════════════════════════════════════════════════════════════════════
# NON-STAY
# ══════════════════════════════════════════════════════════════════════════════
ns_all = get_non_stay_raw()
unit   = st.session_state.get("display_unit", "Cr")

st.markdown("---")
page_header("Non-Stay Outstanding")
st.markdown("---")


def _ns_kpis(df: pd.DataFrame) -> tuple:
    outstanding  = float(df["outstanding"].sum())     if "outstanding"    in df.columns else 0.0
    tds          = float(df["tds"].sum())             if "tds"            in df.columns else 0.0
    grand_total  = float(df["grand_total"].sum())     if "grand_total"    in df.columns else 0.0
    received     = float(df["amount_received"].sum()) if "amount_received"in df.columns else 0.0
    bookings     = len(df)
    return outstanding, tds, grand_total, received, bookings


# ── Overall KPIs ──────────────────────────────────────────────────────────────
os_tot, tds_tot, gt_tot, rcv_tot, bk_tot = _ns_kpis(ns_all)
nk1, nk2, nk3, nk4, nk5 = st.columns(5)
nk1.metric("Outstanding",    fmt_money(os_tot,  unit))
nk2.metric("TDS",            fmt_money(tds_tot, unit))
nk3.metric("Grand Total",    fmt_money(gt_tot,  unit))
nk4.metric("Received",       fmt_money(rcv_tot, unit))
nk5.metric("Transactions",   f"{bk_tot:,}")

st.markdown("---")

# ── Sub-category tabs (KPIs + client table per category) ─────────────────────
present_cats = [c for c in NON_STAY_SUB_CATS if c in ns_all["sub_category"].unique()]
ns_tabs = st.tabs(present_cats)

for tab, cat in zip(ns_tabs, present_cats):
    with tab:
        cat_df = ns_all[ns_all["sub_category"] == cat]

        # KPIs
        c_os, c_tds, c_gt, c_rcv, c_bk = _ns_kpis(cat_df)
        ck1, ck2, ck3, ck4, ck5 = st.columns(5)
        ck1.metric("Outstanding",  fmt_money(c_os,  unit))
        ck2.metric("TDS",          fmt_money(c_tds, unit))
        ck3.metric("Grand Total",  fmt_money(c_gt,  unit))
        ck4.metric("Received",     fmt_money(c_rcv, unit))
        ck5.metric("Transactions", f"{c_bk:,}")

        st.markdown("---")

        # Client table for this category
        cat_agg = (
            cat_df.groupby("corp_id")
            .agg(
                corporate_name  = ("corporate_name",  "first"),
                outstanding     = ("outstanding",      "sum"),
                tds             = ("tds",              "sum"),
                grand_total     = ("grand_total",      "sum"),
                amount_received = ("amount_received",  "sum"),
                transactions    = ("corp_id",          "count"),
            )
            .reset_index()
            .sort_values("outstanding", ascending=False)
        )

        cat_agg["on_account"] = cat_agg["corp_id"].map(ns_oac_s).fillna(0.0)
        cat_agg["net_os"]     = cat_agg["outstanding"] - cat_agg["on_account"]

        cat_display = cat_agg.copy()
        for col in ["outstanding", "tds", "grand_total", "amount_received",
                    "on_account", "net_os"]:
            cat_display[col] = cat_display[col].apply(lambda v: fmt_money(v, unit))
        cat_display = cat_display.rename(columns={
            "corp_id":          "Corp ID",
            "corporate_name":   "Name",
            "outstanding":      f"Outstanding ({unit})",
            "tds":              f"TDS ({unit})",
            "grand_total":      f"Grand Total ({unit})",
            "amount_received":  f"Received ({unit})",
            "transactions":     "Transactions",
            "on_account":       f"On Acc ({unit})",
            "net_os":           f"O/S after On Acc ({unit})",
        })

        st.dataframe(cat_display, use_container_width=True, hide_index=True,
                     height=min(500, 44 + len(cat_agg) * 36))
        render_download_buttons(cat_agg, filename_stem=f"non_stay_{cat.lower().replace(' / ', '_')}")
