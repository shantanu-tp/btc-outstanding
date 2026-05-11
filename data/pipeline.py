"""build_master_df() — assembles the master DataFrame from all sources."""

from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config.settings import FY_START_MONTH, CLIENT_ID_ALIASES, EXCLUDED_BOOKING_IDS


@dataclass
class DataStore:
    master_df: pd.DataFrame
    last_refreshed: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # convenience subsets populated by build_master_df
    corp_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    mice_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    selected_df: pd.DataFrame = field(default_factory=pd.DataFrame)


# ── Period / FY helpers ────────────────────────────────────────────────────────

def _period(dt: pd.Timestamp) -> str:
    return dt.strftime("%Y-%m")


def _fy(dt: pd.Timestamp, start_month: int = FY_START_MONTH) -> str:
    fy_year = dt.year + 1 if dt.month >= start_month else dt.year
    return f"FY{str(fy_year)[-2:]}"


def _fy_quarter(dt: pd.Timestamp, start_month: int = FY_START_MONTH) -> str:
    offset = (dt.month - start_month) % 12
    q = offset // 3 + 1
    fy_year = dt.year + 1 if dt.month >= start_month else dt.year
    return f"Q{q}FY{str(fy_year)[-2:]}"


def _add_time_cols(df: pd.DataFrame, date_col: str = "checkout") -> pd.DataFrame:
    dt = pd.to_datetime(df[date_col], errors="coerce")
    df["period"]     = dt.map(lambda x: _period(x)     if not pd.isna(x) else None)
    df["fy"]         = dt.map(lambda x: _fy(x)         if not pd.isna(x) else None)
    df["fy_quarter"] = dt.map(lambda x: _fy_quarter(x) if not pd.isna(x) else None)
    return df


# ── Client ID normalisation ────────────────────────────────────────────────────

def _norm_id(v) -> str:
    s = str(v).strip().replace(",", "")
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def _consolidate_ids(df: pd.DataFrame) -> pd.DataFrame:
    df["corp_id"] = df["corp_id"].map(_norm_id)
    if CLIENT_ID_ALIASES:
        df["corp_id"] = df["corp_id"].replace(CLIENT_ID_ALIASES)
    return df


# ── Numeric coercion helper ────────────────────────────────────────────────────

def _to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0.0)


# ── Master column rename map ───────────────────────────────────────────────────
# Maps raw DB / sheet column names → canonical snake_case names used everywhere.

_RENAME: dict[str, str] = {
    "Corp ID":                      "corp_id",
    "Corporate Name":               "corporate_name",
    "Entity Name":                  "entity_name",
    "Booking ID":                   "booking_id",
    "Status":                       "status",
    "Invoice No.":                  "invoice_no",
    "Location":                     "location",
    "Property Name":                "property_name",
    "Occupancy":                    "occupancy",
    "Guest Name":                   "guest_name",
    "Checkin":                      "checkin",
    "Checkout":                     "checkout",
    "Room":                         "room",
    "RNs":                          "rns",
    "Base_Amount":                  "base_amount",
    "Retention_Base_Amount":        "retention_base_amount",
    "SGST":                         "sgst",
    "CGST":                         "cgst",
    "Inclusion/IGST":               "inclusion_igst",
    "convenience_fee":              "convenience_fee",
    "convenience_fee_sgst":         "convenience_fee_sgst",
    "convenience_fee_cgst":         "convenience_fee_cgst",
    "convenience_fee_igst":         "convenience_fee_igst",
    "Discount":                     "discount",
    "Grand_Total":                  "grand_total",
    "Consol./Manual Invoice":       "consol_manual_invoice",
    "CN Reason":                    "cn_reason",
    "CN No":                        "cn_no",
    "CN_Amount":                    "cn_amount",
    "Effective_total":              "effective_total",
    "Amount_Received":              "amount_received",
    "TDS":                          "tds",
    "Commission":                   "commission",
    "write off":                    "write_off",
    "Outstanding":                  "outstanding",
    "Remarks":                      "remarks",
    "Payment Ref\nNumber Part1":    "payment_ref_1",
    "Payment recd DatePart1":       "payment_date_1",
    "Payment Ref \nNumber Part2":   "payment_ref_2",
    "Payment recd DatePart2":       "payment_date_2",
    "Bank":                         "bank",
    "Invoice creation\nDate":       "invoice_creation_date",
    "Invoice Submission\nDate":     "invoice_submission_date",
    "Credit Days":                  "credit_days",
    "Ageing":                       "ageing",
    "CO Month":                     "co_month",
    "Payment Recon":                "payment_recon",
}

_MONEY_COLS = [
    "base_amount", "retention_base_amount", "sgst", "cgst", "inclusion_igst",
    "convenience_fee", "convenience_fee_sgst", "convenience_fee_cgst",
    "convenience_fee_igst", "discount", "grand_total", "cn_amount",
    "effective_total", "amount_received", "tds", "commission",
    "write_off", "outstanding",
]


# ── Main build function ────────────────────────────────────────────────────────

def build_master_df() -> DataStore:
    """
    Assembles the master DataFrame.
    Currently returns dummy data; replace the import calls below with real
    source loaders as they are wired up.
    """
    from data.dummy import load_dummy_data
    raw = load_dummy_data()

    df = raw.rename(columns=_RENAME)

    # Normalise corp_id
    if "corp_id" in df.columns:
        df = _consolidate_ids(df)

    # Coerce money cols
    for col in _MONEY_COLS:
        if col in df.columns:
            df[col] = _to_num(df[col])

    # Exclude bad booking IDs
    if EXCLUDED_BOOKING_IDS and "booking_id" in df.columns:
        df = df[~df["booking_id"].astype(str).isin(EXCLUDED_BOOKING_IDS)]

    # Add time columns (based on checkout date)
    if "checkout" in df.columns:
        df = _add_time_cols(df, date_col="checkout")

    # Derive category if not present
    if "category" not in df.columns:
        df["category"] = "Corporates"

    ds = DataStore(master_df=df)

    if "category" in df.columns:
        ds.corp_df     = df[df["category"] == "Corporates"].copy()
        ds.mice_df     = df[df["category"] == "MICE"].copy()
        ds.selected_df = df[df["category"] == "Selected Accounts"].copy()

    return ds
