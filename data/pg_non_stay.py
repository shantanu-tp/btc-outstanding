"""Loader for public.mis_data_non_stay."""

from __future__ import annotations
import pandas as pd
from config.connections import get_pg_conn

_TABLE = "public.mis_data_non_stay"

# Consolidate messy sub_category values → canonical labels
_SUB_CAT_MAP: dict[str, str] = {
    "flight":    "Flight",
    "flights":   "Flight",
    "i-flight":  "Flight",
    "fLight":    "Flight",   # handle mixed case before lower()
    "cab":       "Cab",
    "bus-train": "Bus / Train",
    "bus-trian": "Bus / Train",
    "train":     "Bus / Train",
    "visa":      "Visa",
    "i-hotel":   "Hotel",
}

# Ordered for display
NON_STAY_SUB_CATS: list[str] = ["Flight", "Cab", "Bus / Train", "Visa", "Hotel"]

# Normalise raw ageing_submission strings → canonical labels
# Raw values: "0-15D", "16-30 D", "31-45 D" … "365+ D", "#VALUE!", "#N/A"
_AGEING_RAW_MAP: dict[str, str] = {
    "0-15d":    "0-15 D",
    "16-30 d":  "16-30 D",
    "31-45 d":  "31-45 D",
    "46-60 d":  "46-60 D",
    "61-90 d":  "61-90 D",
    "91-120 d": "91-120 D",
    "121-150 d":"121-150 D",
    "151-180 d":"151-180 D",
    "181-365 d":"181-365 D",
    "365+ d":   "365+ D",
}

NON_STAY_AGEING_LABELS: list[str] = [
    "0-15 D", "16-30 D", "31-45 D", "46-60 D", "61-90 D",
    "91-120 D", "121-150 D", "151-180 D", "181-365 D", "365+ D",
]

_MONEY_COLS = [
    "base_amount", "convenience_fee", "cgst", "sgst", "igst",
    "grand_total", "cn_amount", "effective_total",
    "amount_received", "tds", "commission", "outstanding",
]


def load_non_stay_data() -> pd.DataFrame:
    conn = get_pg_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {_TABLE}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=cols)

    # Align key column names to match stay schema
    df = df.rename(columns={
        "corporate_id": "corp_id",
        "client_name":  "corporate_name",
    })

    for col in _MONEY_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "corp_id" in df.columns:
        df["corp_id"] = df["corp_id"].astype(str).str.strip()

    if "sub_category" in df.columns:
        df["sub_category"] = (
            df["sub_category"]
            .astype(str).str.strip().str.lower()
            .map(_SUB_CAT_MAP)
        )
        df = df[df["sub_category"].notna()].copy()

    if "ageing_submission" in df.columns:
        df["ageing_submission"] = (
            df["ageing_submission"]
            .astype(str).str.strip().str.lower()
            .map(_AGEING_RAW_MAP)
        )

    return df
