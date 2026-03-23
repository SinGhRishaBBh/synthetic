from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class CleaningReport:
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    dropped_columns: list[str] = field(default_factory=list)
    dropped_rows: int = 0
    converted_columns: list[str] = field(default_factory=list)
    imputed_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)



def _normalize_column_name(name: str) -> str:
    value = re.sub(r"\s+", "_", str(name).strip())
    value = re.sub(r"[^0-9a-zA-Z_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "column"



def _make_unique(cols: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []
    for col in cols:
        if col not in seen:
            seen[col] = 0
            output.append(col)
        else:
            seen[col] += 1
            output.append(f"{col}_{seen[col]}")
    return output



def _try_parse_datetime(series: pd.Series) -> pd.Series | None:
    sample = series.dropna().astype("string").head(200)
    if sample.empty:
        return None

    parsed_sample = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
    if parsed_sample.notna().mean() < 0.85:
        return None

    parsed_full = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    return parsed_full



def _try_parse_numeric(series: pd.Series) -> pd.Series | None:
    sample = series.dropna().astype("string").str.replace(",", "", regex=False).head(200)
    if sample.empty:
        return None

    parsed_sample = pd.to_numeric(sample, errors="coerce")
    if parsed_sample.notna().mean() < 0.9:
        return None

    parsed_full = pd.to_numeric(series.astype("string").str.replace(",", "", regex=False), errors="coerce")
    return parsed_full



def clean_dataset(df: pd.DataFrame, fill_missing: bool = True) -> tuple[pd.DataFrame, CleaningReport]:
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Input dataset is invalid.")
    if df.empty:
        raise ValueError("Input dataset has no rows.")

    working = df.copy()
    report = CleaningReport(
        rows_before=len(working),
        rows_after=len(working),
        cols_before=working.shape[1],
        cols_after=working.shape[1],
    )

    working.replace([np.inf, -np.inf], np.nan, inplace=True)

    unnamed_cols = [c for c in working.columns if str(c).strip().lower().startswith("unnamed")]
    if unnamed_cols:
        working.drop(columns=unnamed_cols, inplace=True, errors="ignore")
        report.dropped_columns.extend(list(map(str, unnamed_cols)))

    all_null_cols = [c for c in working.columns if working[c].isna().all()]
    if all_null_cols:
        working.drop(columns=all_null_cols, inplace=True, errors="ignore")
        report.dropped_columns.extend(list(map(str, all_null_cols)))

    before_rows = len(working)
    working.dropna(axis=0, how="all", inplace=True)
    report.dropped_rows = before_rows - len(working)

    normalized = [_normalize_column_name(c) for c in working.columns]
    working.columns = _make_unique(normalized)

    for col in working.columns:
        if pd.api.types.is_datetime64_any_dtype(working[col]) or pd.api.types.is_numeric_dtype(working[col]):
            continue

        dt_parsed = _try_parse_datetime(working[col])
        if dt_parsed is not None:
            working[col] = dt_parsed
            report.converted_columns.append(f"{col}:datetime")
            continue

        num_parsed = _try_parse_numeric(working[col])
        if num_parsed is not None:
            working[col] = num_parsed
            report.converted_columns.append(f"{col}:numeric")
            continue

        working[col] = working[col].astype("string").str.strip()
        working[col] = working[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "null": pd.NA})

    if fill_missing:
        for col in working.columns:
            s = working[col]
            if not s.isna().any():
                continue

            if pd.api.types.is_numeric_dtype(s):
                median = s.median()
                fill_value = 0 if pd.isna(median) else median
                working[col] = s.fillna(fill_value)
                report.imputed_columns.append(f"{col}:median")
            elif pd.api.types.is_datetime64_any_dtype(s):
                mode = s.mode(dropna=True)
                if not mode.empty:
                    working[col] = s.fillna(mode.iloc[0])
                    report.imputed_columns.append(f"{col}:mode_datetime")
                else:
                    report.warnings.append(f"Datetime column '{col}' remains partially missing.")
            else:
                mode = s.mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else "missing"
                working[col] = s.fillna(fill_value)
                report.imputed_columns.append(f"{col}:mode")

    report.rows_after = len(working)
    report.cols_after = working.shape[1]
    return working, report
