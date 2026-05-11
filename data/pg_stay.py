"""Loader for public.stay_onacc (PostgreSQL).

Field mapping will be added once the schema is confirmed.
"""

from __future__ import annotations
import pandas as pd
from config.connections import get_pg_conn
from config.settings import PG_STAY_TABLE


def load_stay_onacc() -> pd.DataFrame:
    sql = f"SELECT * FROM {PG_STAY_TABLE}"
    with get_pg_conn() as conn:
        df = pd.read_sql(sql, conn)
    return df
