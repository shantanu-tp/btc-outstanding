"""
Pre-computation engine.

Fetches raw data from public.mis_data, cleans it, and persists two
summary tables as Parquet. All pages read from Parquet — the DB is
never hit at page-render time.
"""

from __future__ import annotations

import datetime as dt
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config.settings import AGEING_LABELS, EXCLUDED_STATUSES

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "data" / "cached"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_F_RAW            = CACHE_DIR / "mis_raw.parquet"
_F_CLIENT_MONTH   = CACHE_DIR / "client_month_outstanding.parquet"
_F_CLIENT_AGEING  = CACHE_DIR / "client_ageing_outstanding.parquet"
_F_NON_STAY_RAW    = CACHE_DIR / "non_stay_raw.parquet"
_F_NON_STAY_AGEING = CACHE_DIR / "non_stay_ageing.parquet"
_F_STAY_ON_ACC     = CACHE_DIR / "stay_on_acc.parquet"
_F_NS_ON_ACC       = CACHE_DIR / "ns_on_acc.parquet"
_F_META            = CACHE_DIR / "meta.parquet"


# ── Cleaning ──────────────────────────────────────────────────────────────────

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0.0)


def _normalise_co_month(series: pd.Series) -> pd.Series:
    """
    Convert co_month → 'Apr-25' style string.
    The DB stores co_month as YYYY-01-MM where the DAY field is the real month
    number (e.g. 2025-01-04 = April 2025).
    """
    def _parse(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, (dt.date, dt.datetime)):
            # day encodes the real month; year encodes the real year
            real_month = v.day    # 1–12
            real_year  = v.year
            if not (1 <= real_month <= 12):
                return None
            return dt.date(real_year, real_month, 1).strftime("%b-%y")
        s = str(v).strip()
        try:
            return pd.to_datetime(s).strftime("%b-%y")
        except Exception:
            return None
    return series.map(_parse)


def _clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    money_cols = [
        "base_amount", "retention_base_amount", "sgst", "cgst", "inclusion_igst",
        "convenience_fee", "convenience_fee_sgst", "convenience_fee_cgst",
        "convenience_fee_igst", "discount", "grand_total", "cn_amount",
        "effective_total", "amount_received", "tds", "commission",
        "write_off", "outstanding",
    ]
    for col in money_cols:
        if col in df.columns:
            df[col] = _to_num(df[col])

    if "corp_id" in df.columns:
        df["corp_id"] = df["corp_id"].astype(str).str.strip()

    if "co_month" in df.columns:
        df["co_month"] = _normalise_co_month(df["co_month"])

    # ageing is a string bucket in the DB — just clean whitespace
    if "ageing" in df.columns:
        df["ageing"] = df["ageing"].astype(str).str.strip()

    return df


# ── Aggregations ──────────────────────────────────────────────────────────────

def _build_client_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    SUMIF(corp_id & co_month → outstanding)
    Excludes Cancelled rows. Returns long table; pivot happens in the page.
    """
    active = df[~df["status"].isin(EXCLUDED_STATUSES)] if "status" in df.columns else df
    active = active[active["co_month"].notna()]

    agg = (
        active.groupby(["corp_id", "co_month"])["outstanding"]
        .sum()
        .reset_index()
        .rename(columns={"outstanding": "outstanding_billed"})
    )
    agg["_sort"] = pd.to_datetime(agg["co_month"], format="%b-%y", errors="coerce")
    agg = agg.sort_values(["corp_id", "_sort"]).drop(columns="_sort").reset_index(drop=True)
    return agg


def _build_client_ageing(df: pd.DataFrame) -> pd.DataFrame:
    """
    SUMIFS(outstanding, ageing_bucket, corp_id)
    ageing column in DB already contains bucket strings (e.g. '61-90 Days').
    Excludes Cancelled and '#N/A' ageing rows.
    """
    active = df[~df["status"].isin(EXCLUDED_STATUSES)] if "status" in df.columns else df
    active = active[active["ageing"].isin(AGEING_LABELS)]

    agg = (
        active.groupby(["corp_id", "ageing"])["outstanding"]
        .sum()
        .reset_index()
        .rename(columns={"outstanding": "outstanding_billed", "ageing": "ageing_bucket"})
    )
    bucket_order = {b: i for i, b in enumerate(AGEING_LABELS)}
    agg["_sort"] = agg["ageing_bucket"].map(bucket_order).fillna(99)
    agg = agg.sort_values(["corp_id", "_sort"]).drop(columns="_sort").reset_index(drop=True)
    return agg


def _load_stay_on_acc() -> pd.DataFrame:
    """SUM(amount_received) per client_id from stay_onacc."""
    from config.connections import get_pg_conn
    conn = get_pg_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT client_id, SUM(amount_received) AS on_account "
            "FROM public.stay_onacc WHERE amount_received IS NOT NULL "
            "GROUP BY client_id"
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=["corp_id", "on_account"])
    df["corp_id"]    = df["corp_id"].astype(str).str.strip()
    df["on_account"] = pd.to_numeric(df["on_account"], errors="coerce").fillna(0.0)
    return df


def _load_ns_on_acc() -> pd.DataFrame:
    """SUM(amount) per corporate_id from non_stay_on_acc."""
    from config.connections import get_pg_conn
    conn = get_pg_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT corporate_id, SUM(amount) AS on_account "
            "FROM public.non_stay_on_acc WHERE amount IS NOT NULL "
            "GROUP BY corporate_id"
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=["corp_id", "on_account"])
    df["corp_id"]    = df["corp_id"].astype(str).str.strip()
    df["on_account"] = pd.to_numeric(df["on_account"], errors="coerce").fillna(0.0)
    return df


def _build_non_stay_ageing(df: pd.DataFrame) -> pd.DataFrame:
    """
    SUMIFS(outstanding, ageing_submission, corp_id, sub_category)
    Returns long table: corp_id | sub_category | ageing_bucket | outstanding_billed
    """
    from data.pg_non_stay import NON_STAY_AGEING_LABELS
    valid = df[df["ageing_submission"].notna()].copy()

    agg = (
        valid.groupby(["corp_id", "sub_category", "ageing_submission"])["outstanding"]
        .sum()
        .reset_index()
        .rename(columns={"outstanding": "outstanding_billed",
                         "ageing_submission": "ageing_bucket"})
    )
    bucket_order = {b: i for i, b in enumerate(NON_STAY_AGEING_LABELS)}
    agg["_sort"] = agg["ageing_bucket"].map(bucket_order).fillna(99)
    agg = agg.sort_values(["corp_id", "sub_category", "_sort"]).drop(columns="_sort").reset_index(drop=True)
    return agg


# ── Public API ────────────────────────────────────────────────────────────────

def run_precompute(source: str = "db") -> datetime:
    log.info("Precompute started (source=%s)", source)

    from data.pg_mis import load_mis_data
    from data.pg_non_stay import load_non_stay_data

    raw = load_mis_data()
    raw = _clean_raw(raw)

    client_month  = _build_client_month(raw)
    client_ageing = _build_client_ageing(raw)

    non_stay = load_non_stay_data()
    non_stay_ageing = _build_non_stay_ageing(non_stay)

    raw.to_parquet(_F_RAW,                         index=False)
    client_month.to_parquet(_F_CLIENT_MONTH,        index=False)
    client_ageing.to_parquet(_F_CLIENT_AGEING,      index=False)
    non_stay.to_parquet(_F_NON_STAY_RAW,            index=False)
    non_stay_ageing.to_parquet(_F_NON_STAY_AGEING,  index=False)

    stay_on_acc = _load_stay_on_acc()
    ns_on_acc   = _load_ns_on_acc()
    stay_on_acc.to_parquet(_F_STAY_ON_ACC, index=False)
    ns_on_acc.to_parquet(_F_NS_ON_ACC,     index=False)

    ts = datetime.now(timezone.utc).replace(tzinfo=None)
    pd.DataFrame([{"last_refreshed": ts.isoformat()}]).to_parquet(_F_META, index=False)

    log.info("Done — %d stay rows, %d non-stay rows, %d corp-month, %d corp-ageing",
             len(raw), len(non_stay), len(client_month), len(client_ageing))
    return ts


def cache_exists() -> bool:
    return (
        _F_CLIENT_MONTH.exists() and _F_CLIENT_AGEING.exists()
        and _F_NON_STAY_RAW.exists() and _F_NON_STAY_AGEING.exists()
        and _F_STAY_ON_ACC.exists() and _F_NS_ON_ACC.exists()
    )


def last_refreshed() -> datetime | None:
    if not _F_META.exists():
        return None
    try:
        ts_str = pd.read_parquet(_F_META)["last_refreshed"].iloc[0]
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def load_client_month() -> pd.DataFrame:
    return pd.read_parquet(_F_CLIENT_MONTH)


def load_client_ageing() -> pd.DataFrame:
    return pd.read_parquet(_F_CLIENT_AGEING)


def load_raw() -> pd.DataFrame:
    return pd.read_parquet(_F_RAW)


def load_non_stay_raw() -> pd.DataFrame:
    return pd.read_parquet(_F_NON_STAY_RAW)


def load_non_stay_ageing() -> pd.DataFrame:
    return pd.read_parquet(_F_NON_STAY_AGEING)


def load_stay_on_acc() -> pd.DataFrame:
    return pd.read_parquet(_F_STAY_ON_ACC)


def load_ns_on_acc() -> pd.DataFrame:
    return pd.read_parquet(_F_NS_ON_ACC)
