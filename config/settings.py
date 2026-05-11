"""Application-wide constants."""

from __future__ import annotations

# ── Fiscal year ───────────────────────────────────────────────────────────────
FY_START_MONTH: int = 4          # April → FY starts in April

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_TTL: int = 14_400          # 4 hours in seconds

# ── Display ───────────────────────────────────────────────────────────────────
DISPLAY_UNITS: list[str] = ["Cr", "L", "₹"]
DEFAULT_UNIT: str = "Cr"

UNIT_DIVISOR: dict[str, float] = {
    "Cr": 1e7,
    "L":  1e5,
    "₹":  1.0,
}

# ── Client ID consolidation map ───────────────────────────────────────────────
# Maps alias IDs → canonical ID.  Add entries as needed.
CLIENT_ID_ALIASES: dict[str, str] = {}

# ── Excluded booking IDs ──────────────────────────────────────────────────────
EXCLUDED_BOOKING_IDS: list[str] = []

# ── Segment / category lists ──────────────────────────────────────────────────
BOOKING_CATEGORIES: list[str] = ["Corporates", "MICE", "Selected Accounts"]

# ── Ageing buckets — exact strings as stored in public.mis_data ───────────────
AGEING_LABELS: list[str] = [
    "00-15 Days",
    "16-30 Days",
    "31-45 Days",
    "46-60 Days",
    "61-90 Days",
    "91-120 Days",
    "121-150 Days",
    "151-180 Days",
    "181-365 Days",
    "365+ Days",
]
# '#N/A' rows are excluded from ageing analysis

# Cancelled statuses to exclude from outstanding calculations
EXCLUDED_STATUSES: list[str] = ["Cancelled"]

# ── PostgreSQL tables ─────────────────────────────────────────────────────────
PG_MIS_TABLE:     str = "public.mis_data"      # primary source — billed portion
PG_RECEIPT_TABLE: str = "public.receipt_data"  # payment receipts
PG_STAY_TABLE:    str = "public.stay_onacc"    # stay-on-account records

# ── Google Sheet IDs ──────────────────────────────────────────────────────────
# Populate when sheets are added.
SHEET_IDS: dict[str, str] = {}

# ── Metric label map ──────────────────────────────────────────────────────────
METRIC_LABELS: dict[str, str] = {
    "outstanding":        "Outstanding",
    "billed":             "Billed",
    "unbilled":           "Unbilled",
    "tds":                "TDS",
    "ready_to_bill":      "Ready to Bill",
    "future_co":          "Future CO",
    "pending_co":         "Pending CO",
    "amount_received":    "Amount Received",
    "grand_total":        "Grand Total",
    "effective_total":    "Effective Total",
    "base_amount":        "Base Amount",
    "commission":         "Commission",
    "write_off":          "Write Off",
}

# ── Outstanding flow node colours ─────────────────────────────────────────────
FLOW_COLORS: dict[str, str] = {
    "outstanding":   "#1f4e79",
    "billed":        "#2e75b6",
    "unbilled":      "#ed7d31",
    "tds":           "#70ad47",
    "ready_to_bill": "#ffc000",
    "future_co":     "#5a96c8",
    "pending_co":    "#bf9000",
}
