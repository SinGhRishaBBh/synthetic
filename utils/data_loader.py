import logging
import re
import csv
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

HEADER_KEYWORDS = {
    "sno", "s_no", "s_no_", "s_no.", "s.no", "id", "date", "name", "value", "type"
}

def _normalize_header_token(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[\s\-\/]+", "_", text)
    text = re.sub(r"[^a-z0-9_.]", "", text)
    return text

def _normalize_column_name(name: object) -> str:
    text = str(name).strip()
    text = re.sub(r"\s+", " ", text)
    return text

def _make_unique_columns(columns: List[str]) -> List[str]:
    seen = {}
    unique_cols = []
    for col in columns:
        if col not in seen:
            seen[col] = 0
            unique_cols.append(col)
        else:
            seen[col] += 1
            unique_cols.append(f"{col}_{seen[col]}")
    return unique_cols

def _detect_header_row(raw_df: pd.DataFrame) -> Optional[int]:
    """
    Scans looking for row with highest non-null density and keyword scores to guess header index.
    """
    if raw_df is None or raw_df.empty:
        return 0 # default

    best_keyword_row = None
    best_keyword_score = -1
    best_non_null_row = 0
    best_non_null_count = -1

    search_limit = min(len(raw_df), 15) # Only scan top 15 rows

    for row_idx in range(search_limit):
        row = raw_df.iloc[row_idx]
        non_null_count = int(row.notna().sum())
        if non_null_count > best_non_null_count:
            best_non_null_count = non_null_count
            best_non_null_row = row_idx

        tokens = [_normalize_header_token(v) for v in row.dropna().tolist()]
        keyword_hits = sum(1 for token in tokens if token in HEADER_KEYWORDS)
        if keyword_hits > best_keyword_score:
            best_keyword_score = keyword_hits
            best_keyword_row = row_idx

    # Prioritize keyword match if it exists
    if best_keyword_row is not None and best_keyword_score > 0:
        return best_keyword_row

    if best_non_null_row is not None and best_non_null_count > 1:
        return best_non_null_row

    return 0

def _clean_loaded_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.dropna(axis=1, how="all", inplace=True)
    cleaned.dropna(axis=0, how="all", inplace=True)

    unnamed_cols = [col for col in cleaned.columns if str(col).strip().lower().startswith("unnamed")]
    if unnamed_cols:
        cleaned.drop(columns=unnamed_cols, inplace=True, errors="ignore")

    cleaned.columns = [_normalize_column_name(col) for col in cleaned.columns]
    cleaned.columns = _make_unique_columns(cleaned.columns.tolist())
    return cleaned

def _validate_loaded_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return False, "Loaded dataset is empty after parsing."

    if df.shape[1] <= 1:
        return False, "Dataset contains only one column. Separator or delimiter settings are likely incorrect."

    return True, ""

def _detect_csv_delimiter(uploaded_file) -> str:
    """
    Uses csv.Sniffer to guess delimiter from the first few lines.
    """
    try:
         uploaded_file.seek(0)
         sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
         uploaded_file.seek(0)
         sniffer = csv.Sniffer()
         dialect = sniffer.sniff(sample, delimiters=',;\t|')
         return dialect.delimiter
    except Exception:
         return ',' # default fallback

def smart_load_csv(uploaded_file, sep_override=None, header_override=None) -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    diagnostics = {
        "detected_delimiter": ",",
        "detected_header_row": 0,
        "raw_preview": pd.DataFrame(),
        "cleaned_preview": pd.DataFrame()
    }

    try:
        delimiter = sep_override if sep_override else _detect_csv_delimiter(uploaded_file)
        diagnostics["detected_delimiter"] = delimiter
        
        uploaded_file.seek(0)
        raw = pd.read_csv(uploaded_file, sep=delimiter, header=None, nrows=10)
        diagnostics["raw_preview"] = raw

        header_row = header_override if header_override is not None else _detect_header_row(raw)
        diagnostics["detected_header_row"] = header_row

        uploaded_file.seek(0)
        parsed_df = pd.read_csv(uploaded_file, sep=delimiter, header=header_row)
        
        cleaned_df = _clean_loaded_dataframe(parsed_df)
        diagnostics["cleaned_preview"] = cleaned_df.head(8)

        is_valid, err = _validate_loaded_dataframe(cleaned_df)
        if not is_valid:
             return None, {"error": err, **diagnostics}
             
        return cleaned_df, diagnostics

    except Exception as e:
         return None, {"error": f"CSV Parse Error: {str(e)}", **diagnostics}

def smart_load_excel(uploaded_file, sheet_name=0, header_override=None) -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    diagnostics = {
        "detected_header_row": None,
        "raw_preview": pd.DataFrame(),
        "cleaned_preview": pd.DataFrame()
    }

    try:
        uploaded_file.seek(0)
        raw_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None, engine="openpyxl")
        diagnostics["raw_preview"] = raw_df.head(10)
    except Exception as e:
        return None, {"error": f"Failed to read raw Excel content: {e}", **diagnostics}

    header_row = header_override if header_override is not None else _detect_header_row(raw_df)
    diagnostics["detected_header_row"] = header_row

    try:
        uploaded_file.seek(0)
        parsed_df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=header_row, engine="openpyxl")
    except Exception as e:
        return None, {"error": f"Failed to reload Excel with header row {header_row}: {e}", **diagnostics}

    cleaned_df = _clean_loaded_dataframe(parsed_df)
    diagnostics["cleaned_preview"] = cleaned_df.head(8)

    is_valid, err = _validate_loaded_dataframe(cleaned_df)
    if not is_valid:
        return None, {"error": err, **diagnostics}

    return cleaned_df, diagnostics

@st.cache_data(show_spinner="Loading dataset...")
def load_data(uploaded_file, return_diagnostics: bool = False, sep_override=None, header_override=None):
    if uploaded_file is None:
        return (None, {}) if return_diagnostics else None

    diagnostics = {}
    name = uploaded_file.name.lower()

    try:
        if name.endswith(".csv"):
             df, diagnostics = smart_load_csv(uploaded_file, sep_override, header_override)
        elif name.endswith((".xls", ".xlsx")):
             df, diagnostics = smart_load_excel(uploaded_file, header_override=header_override)
        else:
             st.error("Unsupported file format. Please upload a CSV or Excel file.")
             return (None, {}) if return_diagnostics else None

        if df is None:
             # diagnostics contains error
             st.error(diagnostics.get("error", "Dataset Loading failed."))
             return (None, diagnostics) if return_diagnostics else None

        return (df, diagnostics) if return_diagnostics else df

    except Exception as e:
        st.error(f"Error loading file: {e}")
        return (None, {}) if return_diagnostics else None

def get_data_metadata(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}

    metadata = {
        "rows": df.shape[0], "columns": df.shape[1],
        "missing": int(df.isna().sum().sum()),
        "missing_percentage": (df.isna().sum().sum() / (df.shape[0] * df.shape[1])) * 100 if df.size > 0 else 0,
        "types": df.dtypes.to_dict(),
    }

    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool", "string"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime", "datetimetz", "datetime64[ns]"]).columns.tolist()

    inferred_date_cols = []
    for col in cat_cols:
        if "date" in str(col).lower() or "time" in str(col).lower():
            try:
                temp_series = pd.to_datetime(df[col].dropna().head(100), errors="coerce")
                if not temp_series.isna().all():
                    inferred_date_cols.append(col)
            except Exception: pass

    date_cols = list(dict.fromkeys(date_cols + inferred_date_cols))
    cat_cols = [col for col in cat_cols if col not in date_cols]

    metadata["numerical_columns"] = num_cols
    metadata["categorical_columns"] = cat_cols
    metadata["datetime_columns"] = date_cols

    return metadata
