"""Canonical client name lookup from config/client_list.csv."""

from __future__ import annotations
from pathlib import Path
import pandas as pd

_CSV = Path(__file__).parent / "client_list.csv"

def _load() -> dict[str, str]:
    df = pd.read_csv(_CSV, dtype=str)
    df = df.drop_duplicates(subset="client_id", keep="first")
    return dict(zip(df["client_id"].str.strip(), df["client_name"].str.strip()))

CLIENT_NAMES: dict[str, str] = _load()


def apply_canonical_names(df: pd.DataFrame, id_col: str, name_col: str) -> pd.DataFrame:
    """Overwrite name_col with canonical names from client_list.csv where available."""
    df = df.copy()
    df[name_col] = df[id_col].astype(str).str.strip().map(CLIENT_NAMES).fillna(df[name_col])
    return df
