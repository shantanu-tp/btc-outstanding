"""MTD collections queries — receipt_data (stay) and non_stay_receipt.

For each of the last N months, sums amounts from the 1st of that month up
to the same day-of-month as today.  Mirrors the Google Sheets logic:
  SUMIFS(amount, date, ">=1-{month}", date, "<={day}-{month}", corp_id, "<>X")
"""

from __future__ import annotations

import calendar
import datetime as dt

import pandas as pd

from config.connections import get_pg_conn
from config.clients import apply_canonical_names


def month_ranges(today: dt.date, n: int = 6) -> list[tuple[dt.date, dt.date, str]]:
    """Return (start, end, label) for the last n months, capped at today's day-of-month."""
    result = []
    for i in range(n):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        start = dt.date(year, month, 1)
        end   = dt.date(year, month, min(today.day, last_day))
        label = f"{today.day:02d}-{start.strftime('%b-%y')}"
        result.append((start, end, label))
    return result


def _read_sql(sql: str) -> pd.DataFrame:
    conn = get_pg_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()


def fetch_stay_mom(today: dt.date) -> pd.DataFrame:
    """Client-level MTD collections from receipt_data (stay).

    Columns: corporate_id, corporate_name, <month-label>...
    Sorted by most-recent month DESC.
    """
    ranges = month_ranges(today)
    cases = ",\n        ".join(
        f'SUM(CASE WHEN "date" >= \'{s}\' AND "date" <= \'{e}\''
        f" THEN COALESCE(amount, 0) ELSE 0 END) AS \"{lbl}\""
        for s, e, lbl in ranges
    )
    sql = f"""
        SELECT
            corporate_id,
            MAX(corporate_name) AS corporate_name,
            {cases}
        FROM receipt_data
        WHERE corporate_id IS NOT NULL
        GROUP BY corporate_id
        ORDER BY "{ranges[0][2]}" DESC NULLS LAST
    """
    df = _read_sql(sql)
    df["corporate_id"] = df["corporate_id"].astype(str).str.strip()
    return apply_canonical_names(df, "corporate_id", "corporate_name")


def fetch_nonstay_mom(today: dt.date) -> pd.DataFrame:
    """Client-level MTD collections from non_stay_receipt.

    Columns: corporate_id, corporate_name, <month-label>...
    Sorted by most-recent month DESC.
    """
    ranges = month_ranges(today)
    cases = ",\n        ".join(
        f"SUM(CASE WHEN receipt_date >= '{s}' AND receipt_date <= '{e}'"
        f" THEN COALESCE(amount, 0) ELSE 0 END) AS \"{lbl}\""
        for s, e, lbl in ranges
    )
    sql = f"""
        SELECT
            corporate_id,
            MAX(corporate_name) AS corporate_name,
            {cases}
        FROM non_stay_receipt
        WHERE corporate_id IS NOT NULL
        GROUP BY corporate_id
        ORDER BY "{ranges[0][2]}" DESC NULLS LAST
    """
    df = _read_sql(sql)
    df["corporate_id"] = df["corporate_id"].astype(str).str.strip()
    return apply_canonical_names(df, "corporate_id", "corporate_name")
