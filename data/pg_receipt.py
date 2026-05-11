"""Loader for public.receipt_data (PostgreSQL).

Field mapping will be added once the schema is confirmed.
"""

from __future__ import annotations
import pandas as pd
from config.connections import get_pg_conn
from config.settings import PG_RECEIPT_TABLE


def load_receipt_data() -> pd.DataFrame:
    sql = f"SELECT * FROM {PG_RECEIPT_TABLE}"
    with get_pg_conn() as conn:
        df = pd.read_sql(sql, conn)
    return df
