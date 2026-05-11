"""Formatting helpers shared across all pages."""

from __future__ import annotations
from config.settings import UNIT_DIVISOR

# ── Money formatting ──────────────────────────────────────────────────────────

def fmt_money(value: float | None, unit: str = "Cr") -> str:
    if value is None or value != value:   # NaN check
        return "—"
    divisor = UNIT_DIVISOR.get(unit, 1.0)
    scaled = value / divisor
    if unit == "₹":
        # Indian comma style: 1,23,45,678
        return "₹" + _indian_comma(int(round(value)))
    return f"₹{scaled:,.2f} {unit}"


def _indian_comma(n: int) -> str:
    s = str(abs(n))
    if len(s) <= 3:
        result = s
    else:
        result = s[-3:]
        s = s[:-3]
        while s:
            result = s[-2:] + "," + result
            s = s[:-2]
    return ("-" if n < 0 else "") + result


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    if value is None or value != value:
        return "—"
    return f"{value:.{decimals}f}%"


def fmt_count(value: int | float | None) -> str:
    if value is None:
        return "—"
    return f"{int(value):,}"


# ── Column labels ─────────────────────────────────────────────────────────────

COL_LABELS: dict[str, str] = {
    "corp_id":                "Corp ID",
    "corporate_name":         "Corporate Name",
    "entity_name":            "Entity Name",
    "booking_id":             "Booking ID",
    "status":                 "Status",
    "invoice_no":             "Invoice No.",
    "location":               "Location",
    "property_name":          "Property Name",
    "occupancy":              "Occupancy",
    "guest_name":             "Guest Name",
    "checkin":                "Check-in",
    "checkout":               "Check-out",
    "room":                   "Room",
    "rns":                    "RNs",
    "base_amount":            "Base Amount",
    "retention_base_amount":  "Retention Base Amount",
    "sgst":                   "SGST",
    "cgst":                   "CGST",
    "inclusion_igst":         "Inclusion / IGST",
    "convenience_fee":        "Convenience Fee",
    "discount":               "Discount",
    "grand_total":            "Grand Total",
    "cn_amount":              "CN Amount",
    "effective_total":        "Effective Total",
    "amount_received":        "Amount Received",
    "tds":                    "TDS",
    "commission":             "Commission",
    "write_off":              "Write Off",
    "outstanding":            "Outstanding",
    "remarks":                "Remarks",
    "bank":                   "Bank",
    "credit_days":            "Credit Days",
    "ageing":                 "Ageing",
    "co_month":               "CO Month",
    "payment_recon":          "Payment Recon",
    "period":                 "Period",
    "fy":                     "FY",
    "fy_quarter":             "FY Quarter",
    "category":               "Category",
    "region":                 "Region",
    # derived / aggregate
    "outstanding_total":      "Total Outstanding",
    "billed":                 "Billed",
    "unbilled":               "Unbilled",
    "ready_to_bill":          "Ready to Bill",
    "future_co":              "Future CO",
    "pending_co":             "Pending CO",
}


def col_label(col: str) -> str:
    return COL_LABELS.get(col, col.replace("_", " ").title())


# ── Chronological sort keys ───────────────────────────────────────────────────

def _period_sort_key(p: str) -> str:
    """YYYY-MM → sortable string (already sortable, but centralised here)."""
    return p or "0000-00"


def _fy_quarter_sort_key(q: str) -> tuple[int, int]:
    """Q1FY26 → (26, 1) for correct chronological ordering."""
    try:
        qnum = int(q[1])
        fynum = int(q[4:])
        return (fynum, qnum)
    except Exception:
        return (0, 0)


COL_SORT_KEYS: dict[str, object] = {
    "period":             _period_sort_key,
    "fy_quarter":         _fy_quarter_sort_key,
    "onboarding_quarter": _fy_quarter_sort_key,
}
