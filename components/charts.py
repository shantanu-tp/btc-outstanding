"""Plotly chart builder functions."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import UNIT_DIVISOR
from utils.formatting import fmt_money, col_label

# ── Palette ───────────────────────────────────────────────────────────────────

_BLUE      = "#1e40af"
_BLUE_MID  = "#3b82f6"
_BLUE_LITE = "#93c5fd"
_SLATE     = "#475569"

_AGEING_PALETTE = ["#22c55e", "#84cc16", "#eab308", "#f97316", "#ef4444",
                   "#dc2626", "#b91c1c", "#991b1b", "#7f1d1d", "#581c0c"]

_SANKEY_NODE_COLORS = {
    "outstanding": "#0f172a",
    "billed":      "#1e40af",
    "unbilled":    "#475569",
    "tds":         "#334155",
    "ready_to_bill": "#64748b",
    "future_co":   "#94a3b8",
    "pending_co":  "#cbd5e1",
}

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, sans-serif", size=11, color="#334155"),
    margin=dict(l=8, r=8, t=36, b=8),
    hoverlabel=dict(bgcolor="#0f172a", font_color="white", font_size=11),
)


def _divisor() -> float:
    unit = st.session_state.get("display_unit", "Cr")
    return UNIT_DIVISOR.get(unit, 1e7)


def _unit_label() -> str:
    return st.session_state.get("display_unit", "Cr")


def _rgba(hex_color: str, alpha: float = 0.35) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Outstanding flow (Sankey) ─────────────────────────────────────────────────

def outstanding_flow_chart(
    outstanding: float,
    billed: float,
    unbilled: float,
    tds: float,
    ready_to_bill: float,
    future_co: float,
    pending_co: float,
    title: str = "",
) -> go.Figure:
    div  = _divisor()
    unit = _unit_label()

    def _lbl(name: str, val: float) -> str:
        pct = (val / outstanding * 100) if outstanding else 0
        return f"{name}<br>₹{val/div:,.2f} {unit}  ({pct:.1f}%)"

    nodes = [
        _lbl("Outstanding",   outstanding),
        _lbl("Billed",        billed),
        _lbl("Unbilled",      unbilled),
        _lbl("TDS",           tds),
        _lbl("Ready to Bill", ready_to_bill),
        _lbl("Future CO",     future_co),
        _lbl("Pending CO",    pending_co),
    ]
    node_colors = [
        _SANKEY_NODE_COLORS["outstanding"],
        _SANKEY_NODE_COLORS["billed"],
        _SANKEY_NODE_COLORS["unbilled"],
        _SANKEY_NODE_COLORS["tds"],
        _SANKEY_NODE_COLORS["ready_to_bill"],
        _SANKEY_NODE_COLORS["future_co"],
        _SANKEY_NODE_COLORS["pending_co"],
    ]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=16, thickness=20,
            label=nodes,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[0, 0, 0, 2, 2, 2],
            target=[1, 2, 3, 4, 5, 6],
            value=[
                max(billed, 0), max(unbilled, 0), max(tds, 0),
                max(ready_to_bill, 0), max(future_co, 0), max(pending_co, 0),
            ],
            color=[_rgba(c) for c in [
                _SANKEY_NODE_COLORS["billed"],
                _SANKEY_NODE_COLORS["unbilled"],
                _SANKEY_NODE_COLORS["tds"],
                _SANKEY_NODE_COLORS["ready_to_bill"],
                _SANKEY_NODE_COLORS["future_co"],
                _SANKEY_NODE_COLORS["pending_co"],
            ]],
        ),
    ))
    fig.update_layout(
        height=300,
        **{**_CHART_LAYOUT, "margin": dict(l=8, r=8, t=8, b=8)},
    )
    return fig


# ── Stacked bar (ageing buckets × clients) ────────────────────────────────────

def ageing_client_bar(
    pivot: pd.DataFrame,
    ordered_cols: list[str],
    n: int = 15,
    unit: str = "Cr",
    divisor: float = 1e7,
) -> go.Figure:
    top = pivot.nlargest(n, "Total").drop(columns="Total")

    fig = go.Figure()
    for i, bucket in enumerate(ordered_cols):
        if bucket not in top.columns:
            continue
        color = _AGEING_PALETTE[i % len(_AGEING_PALETTE)]
        fig.add_trace(go.Bar(
            name=bucket,
            x=[str(c) for c in top.index.tolist()],
            y=(top[bucket] / divisor).tolist(),
            marker_color=color,
            marker_line_width=0,
        ))

    fig.update_layout(
        barmode="stack",
        height=340,
        xaxis=dict(title="Corp ID", type="category", tickfont=dict(size=10)),
        yaxis=dict(title=f"₹ {unit}", gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    font=dict(size=10)),
        **_CHART_LAYOUT,
    )
    return fig


# ── Simple bar (single series) ────────────────────────────────────────────────

def simple_bar(
    x: list,
    y: list,
    x_title: str = "",
    y_title: str = "",
    title: str = "",
    color: str = _BLUE_MID,
    height: int = 300,
) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=color,
        marker_line_width=0,
    ))
    fig.update_layout(
        title_text=title,
        title_font_size=12,
        height=height,
        xaxis=dict(title=x_title, type="category", tickfont=dict(size=10)),
        yaxis=dict(title=y_title, gridcolor="#f1f5f9"),
        **_CHART_LAYOUT,
    )
    return fig
