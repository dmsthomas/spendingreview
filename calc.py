from __future__ import annotations
import pandas as pd
from pathlib import Path

BASELINE_DEFICIT = 137  # £bn (positive number → deficit)


def load_tax_table(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    needed = {"name", "unit", "baseline", "delta_per_unit", "min_change", "max_change"}
    if not needed.issubset(df.columns):
        raise ValueError(f"tax CSV missing columns {needed - set(df.columns)}")
    return df


def load_spend_table(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    needed = {"name", "baseline", "min_pct", "max_pct"}
    if not needed.issubset(df.columns):
        raise ValueError(f"spend CSV missing columns {needed - set(df.columns)}")
    return df


def compute_tax_delta(df: pd.DataFrame, change_dict: dict[str, float]) -> float:
    """Return £bn change in receipts (negative = revenue loss)."""
    delta = 0.0
    for _, row in df.iterrows():
        change_units = change_dict.get(row["name"], 0)
        delta += change_units * row["delta_per_unit"]
    return round(delta, 2)


def compute_spend_delta(df: pd.DataFrame, change_dict: dict[str, float]) -> float:
    """Return £bn change in programme spend (positive = spend rises)."""
    delta = 0.0
    for _, row in df.iterrows():
        pct_change = change_dict.get(row["name"], 0.0)
        delta += pct_change * row["baseline"]
    return round(delta, 2)
