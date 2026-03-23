from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class DataProfile:
    rows: int
    columns: int
    numerical_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    missing_cells: int
    missing_percent: float



def build_profile(df: pd.DataFrame) -> DataProfile:
    if df is None or df.empty:
        raise ValueError("Dataset is empty.")

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime", "datetimetz", "datetime64[ns]"]).columns.tolist()
    cat_cols = [
        c
        for c in df.columns
        if c not in num_cols and c not in dt_cols
    ]

    missing_cells = int(df.isna().sum().sum())
    total_cells = int(df.shape[0] * df.shape[1])

    return DataProfile(
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        numerical_columns=num_cols,
        categorical_columns=cat_cols,
        datetime_columns=dt_cols,
        missing_cells=missing_cells,
        missing_percent=(missing_cells / total_cells * 100) if total_cells > 0 else 0.0,
    )



def summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    try:
        return df.describe(include="all", datetime_is_numeric=True).transpose()
    except TypeError:
        return df.describe(include="all").transpose()



def missing_values_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    missing_count = df.isna().sum()
    out = pd.DataFrame(
        {
            "column": missing_count.index,
            "missing_count": missing_count.values,
            "missing_pct": (missing_count.values / len(df) * 100) if len(df) else 0,
        }
    )
    return out[out["missing_count"] > 0].sort_values("missing_pct", ascending=False)



def class_distribution(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    if df is None or df.empty or not target_col or target_col not in df.columns:
        return pd.DataFrame()

    counts = df[target_col].value_counts(dropna=False)
    out = pd.DataFrame(
        {
            "class": counts.index.astype(str),
            "count": counts.values,
            "pct": counts.values / len(df) * 100,
        }
    )
    return out.sort_values("count", ascending=False)



def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    num_df = df.select_dtypes(include=["number"])
    if num_df.shape[1] < 2:
        return pd.DataFrame()
    return num_df.corr(numeric_only=True)
