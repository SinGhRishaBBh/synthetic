from __future__ import annotations

import io
import re
import csv
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import streamlit as st


HEADER_HINTS = {
    "id", "sno", "s.no", "date", "timestamp", "name", "category", "target", "label", "value", "type"
}


@dataclass
class IngestionDiagnostics:
    file_name: str
    file_type: str
    detected_header_row: int | None = None
    detected_delimiter: str = ","
    notes: list[str] = field(default_factory=list)
    raw_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaned_preview: pd.DataFrame = field(default_factory=pd.DataFrame)


def _normalize_token(value: Any) -> str:
    token = str(value).strip().lower()
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^a-z0-9_.]", "", token)
    return token


def _normalize_column_name(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value).strip())
    return text or "column"


def _make_unique(cols: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []
    for col in cols:
        if col not in seen:
            seen[col] = 0
            output.append(col)
            continue
        seen[col] += 1
        output.append(f"{col}_{seen[col]}")
    return output


def _detect_header_row(raw_df: pd.DataFrame) -> int | None:
    if raw_df.empty:
        return None

    best_by_hint: tuple[int, int] | None = None
    best_by_density: tuple[int, int] | None = None

    search_limit = min(len(raw_df), 15)

    for idx in range(search_limit):
        row = raw_df.iloc[idx]
        non_null = int(row.notna().sum())
        if best_by_density is None or non_null > best_by_density[1]:
            best_by_density = (idx, non_null)

        tokens = [_normalize_token(v) for v in row.dropna().tolist()]
        hits = sum(1 for token in tokens if token in HEADER_HINTS)
        if best_by_hint is None or hits > best_by_hint[1]:
            best_by_hint = (idx, hits)

    if best_by_hint and best_by_hint[1] > 0:
        return best_by_hint[0]

    if best_by_density and best_by_density[1] >= 2:
        return best_by_density[0]

    return 0


def _post_process(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.dropna(axis=0, how="all", inplace=True)
    out.dropna(axis=1, how="all", inplace=True)

    unnamed_cols = [c for c in out.columns if str(c).strip().lower().startswith("unnamed")]
    if unnamed_cols:
        out.drop(columns=unnamed_cols, inplace=True, errors="ignore")

    cols = [_normalize_column_name(c) for c in out.columns]
    out.columns = _make_unique(cols)
    out.reset_index(drop=True, inplace=True)
    return out


def _validate_loaded_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Blocks validation triggers if dataframe contains single column headers or is empty.
    """
    if df is None or df.empty:
        return False, "Loaded dataset is empty after parsing."

    if df.shape[1] <= 1:
        return False, "Dataset contains only one column. Separator or delimiter settings are likely incorrect."

    return True, ""


def _detect_csv_delimiter(file_bytes: bytes) -> str:
    """
    Uses csv.Sniffer to guess delimiter from bytes sample.
    """
    try:
         sample = file_bytes[:2048].decode('utf-8', errors='ignore')
         sniffer = csv.Sniffer()
         dialect = sniffer.sniff(sample, delimiters=',;\t|')
         return dialect.delimiter
    except Exception:
         return ','


@st.cache_data(show_spinner=False)
def _load_csv_from_bytes(file_bytes: bytes, sep: str = ',', header_row: int = 0) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(file_bytes), sep=sep, header=header_row)


@st.cache_data(show_spinner=False)
def _load_excel_raw(file_bytes: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
    return raw.ffill(axis=1)


@st.cache_data(show_spinner=False)
def _load_excel_with_header(file_bytes: bytes, header_row: int) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), header=header_row, engine="openpyxl")


def load_dataset(uploaded_file, sep_override: str = None, header_override: int = None) -> tuple[pd.DataFrame, IngestionDiagnostics]:
    if uploaded_file is None:
        raise ValueError("No file uploaded.")

    file_name = uploaded_file.name
    lower_name = file_name.lower()
    file_bytes = uploaded_file.getvalue()

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    diagnostics = IngestionDiagnostics(
        file_name=file_name,
        file_type="csv" if lower_name.endswith(".csv") else "excel",
    )

    if lower_name.endswith(".csv"):
        delimiter = sep_override if sep_override else _detect_csv_delimiter(file_bytes)
        diagnostics.detected_delimiter = delimiter

        # Load raw to scan header
        raw_df = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter, header=None, nrows=10)
        diagnostics.raw_preview = raw_df

        header_row = header_override if header_override is not None else _detect_header_row(raw_df)
        if header_row is None: header_row = 0
        diagnostics.detected_header_row = header_row

        parsed = _load_csv_from_bytes(file_bytes, sep=delimiter, header_row=header_row)
        cleaned = _post_process(parsed)
        diagnostics.cleaned_preview = cleaned.head(10)

        is_valid, validation_err = _validate_loaded_dataframe(cleaned)
        if not is_valid:
             raise ValueError(validation_err)

        diagnostics.notes.append(f"CSV parsed with delimiter='{delimiter}' and header index {header_row}.")
        return cleaned, diagnostics

    if lower_name.endswith((".xls", ".xlsx")):
        raw_df = _load_excel_raw(file_bytes)
        diagnostics.raw_preview = raw_df.head(10)

        header_row = header_override if header_override is not None else _detect_header_row(raw_df)
        diagnostics.detected_header_row = header_row
        if header_row is None: header_row = 0

        parsed = _load_excel_with_header(file_bytes, header_row)
        cleaned = _post_process(parsed)
        diagnostics.cleaned_preview = cleaned.head(10)

        is_valid, validation_err = _validate_loaded_dataframe(cleaned)
        if not is_valid:
             raise ValueError(validation_err)

        diagnostics.notes.append(f"Excel parsed with detected header row index {header_row}.")
        return cleaned, diagnostics

    raise ValueError("Unsupported file type. Please upload CSV or Excel.")
