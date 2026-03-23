"""
Synthetic Data Platform - Colab Single File

Usage in Google Colab:
1) Install dependencies:
   !pip -q install pandas numpy scipy scikit-learn imbalanced-learn openpyxl plotly sdv

2) Save this script as collab.py or paste directly in one cell.
3) Example:
   from google.colab import files
   uploaded = files.upload()  # upload csv/xlsx
   name, content = next(iter(uploaded.items()))
   results = run_full_pipeline(
       source=(name, content),
       model_mode="AUTO",
       sample_size=1000,
       epochs=30,
   )
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from imblearn.over_sampling import SMOTE
from scipy.stats import ks_2samp
from sklearn.preprocessing import LabelEncoder

try:
    from sdv.metadata import SingleTableMetadata
    from sdv.single_table import (
        CTGANSynthesizer,
        GaussianCopulaSynthesizer,
        TVAESynthesizer,
    )
except Exception:
    SingleTableMetadata = None
    CTGANSynthesizer = None
    GaussianCopulaSynthesizer = None
    TVAESynthesizer = None

try:
    from sdv.sequential import PARSynthesizer
except Exception:
    PARSynthesizer = None


HEADER_HINTS = {
    "id",
    "sno",
    "s.no",
    "date",
    "timestamp",
    "name",
    "category",
    "target",
    "label",
    "value",
    "type",
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


@dataclass
class DataProfile:
    rows: int
    columns: int
    numerical_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    missing_cells: int
    missing_percent: float


@dataclass
class ModelRecommendation:
    model: str
    reason: str
    imbalance_ratio: float | None
    detected_time_column: str | None


@dataclass
class GenerationResult:
    synthetic_df: pd.DataFrame
    model_used: str
    logs: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    raw_df: pd.DataFrame
    clean_df: pd.DataFrame
    synthetic_df: pd.DataFrame
    ingestion: IngestionDiagnostics
    cleaning: CleaningReport
    profile: DataProfile
    recommendation: ModelRecommendation
    evaluation_report: pd.DataFrame
    generation_logs: list[str]


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


def _validate_loaded_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    if df is None or df.empty:
        return False, "Loaded dataset is empty after parsing."
    if df.shape[1] <= 1:
        return False, "Dataset contains only one column. Check delimiter/header."
    return True, ""


def _detect_csv_delimiter(file_bytes: bytes) -> str:
    try:
        sample = file_bytes[:2048].decode("utf-8", errors="ignore")
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","


def load_dataset_from_bytes(
    file_name: str,
    file_bytes: bytes,
    sep_override: str | None = None,
    header_override: int | None = None,
) -> tuple[pd.DataFrame, IngestionDiagnostics]:
    if not file_bytes:
        raise ValueError("Uploaded content is empty.")

    lower_name = file_name.lower()
    diagnostics = IngestionDiagnostics(
        file_name=file_name,
        file_type="csv" if lower_name.endswith(".csv") else "excel",
    )

    if lower_name.endswith(".csv"):
        delimiter = sep_override if sep_override else _detect_csv_delimiter(file_bytes)
        diagnostics.detected_delimiter = delimiter

        raw_df = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter, header=None, nrows=10)
        diagnostics.raw_preview = raw_df

        header_row = header_override if header_override is not None else _detect_header_row(raw_df)
        header_row = 0 if header_row is None else header_row
        diagnostics.detected_header_row = header_row

        parsed = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter, header=header_row)
        cleaned = _post_process(parsed)
        diagnostics.cleaned_preview = cleaned.head(10)

        is_valid, err = _validate_loaded_dataframe(cleaned)
        if not is_valid:
            raise ValueError(err)

        diagnostics.notes.append(
            f"CSV parsed with delimiter='{delimiter}' and header index {header_row}."
        )
        return cleaned, diagnostics

    if lower_name.endswith((".xls", ".xlsx")):
        raw_df = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
        raw_df = raw_df.ffill(axis=1)
        diagnostics.raw_preview = raw_df.head(10)

        header_row = header_override if header_override is not None else _detect_header_row(raw_df)
        header_row = 0 if header_row is None else header_row
        diagnostics.detected_header_row = header_row

        parsed = pd.read_excel(io.BytesIO(file_bytes), header=header_row, engine="openpyxl")
        cleaned = _post_process(parsed)
        diagnostics.cleaned_preview = cleaned.head(10)

        is_valid, err = _validate_loaded_dataframe(cleaned)
        if not is_valid:
            raise ValueError(err)

        diagnostics.notes.append(f"Excel parsed with detected header row index {header_row}.")
        return cleaned, diagnostics

    raise ValueError("Unsupported file type. Use CSV/XLS/XLSX.")


def load_dataset_from_path(
    path: str,
    sep_override: str | None = None,
    header_override: int | None = None,
) -> tuple[pd.DataFrame, IngestionDiagnostics]:
    with open(path, "rb") as f:
        content = f.read()
    file_name = path.split("/")[-1].split("\\")[-1]
    return load_dataset_from_bytes(file_name, content, sep_override, header_override)


def _normalize_clean_name(name: str) -> str:
    value = re.sub(r"\s+", "_", str(name).strip())
    value = re.sub(r"[^0-9a-zA-Z_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "column"


def _try_parse_datetime(series: pd.Series) -> pd.Series | None:
    sample = series.dropna().astype("string").head(200)
    if sample.empty:
        return None
    parsed_sample = pd.to_datetime(sample, errors="coerce")
    if parsed_sample.notna().mean() < 0.85:
        return None
    return pd.to_datetime(series, errors="coerce")


def _try_parse_numeric(series: pd.Series) -> pd.Series | None:
    sample = series.dropna().astype("string").str.replace(",", "", regex=False).head(200)
    if sample.empty:
        return None
    parsed_sample = pd.to_numeric(sample, errors="coerce")
    if parsed_sample.notna().mean() < 0.9:
        return None
    return pd.to_numeric(
        series.astype("string").str.replace(",", "", regex=False), errors="coerce"
    )


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

    normalized = [_normalize_clean_name(c) for c in working.columns]
    working.columns = _make_unique(normalized)

    for col in working.columns:
        if pd.api.types.is_datetime64_any_dtype(working[col]) or pd.api.types.is_numeric_dtype(
            working[col]
        ):
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
        working[col] = working[col].replace(
            {"": pd.NA, "nan": pd.NA, "None": pd.NA, "null": pd.NA}
        )

    if fill_missing:
        for col in working.columns:
            s = working[col]
            if not s.isna().any():
                continue
            if pd.api.types.is_numeric_dtype(s):
                median = s.median()
                working[col] = s.fillna(0 if pd.isna(median) else median)
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


def build_profile(df: pd.DataFrame) -> DataProfile:
    if df is None or df.empty:
        raise ValueError("Dataset is empty.")
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    dt_cols = df.select_dtypes(include=["datetime", "datetimetz", "datetime64[ns]"]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols and c not in dt_cols]
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

def _infer_time_column(df: pd.DataFrame) -> str | None:
    datetime_cols = df.select_dtypes(include=["datetime", "datetimetz", "datetime64[ns]"]).columns.tolist()
    if datetime_cols:
        return datetime_cols[0]
    for col in df.columns:
        if any(k in str(col).lower() for k in ["date", "time", "timestamp"]):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() >= 0.8:
                return col
    return None


def _imbalance_ratio(df: pd.DataFrame, target_col: str | None) -> float | None:
    if not target_col or target_col not in df.columns:
        return None
    counts = df[target_col].value_counts(dropna=False)
    if len(counts) < 2:
        return None
    maj = counts.max()
    min_ = counts.min()
    if maj == 0:
        return None
    return float(min_ / maj)


def recommend_model(
    df: pd.DataFrame, target_col: str | None = None, time_col: str | None = None
) -> ModelRecommendation:
    if df is None or df.empty:
        return ModelRecommendation(
            model="GaussianCopula",
            reason="Fallback model because dataset is empty or invalid.",
            imbalance_ratio=None,
            detected_time_column=None,
        )

    detected_time = time_col if time_col in df.columns else _infer_time_column(df)
    ratio = _imbalance_ratio(df, target_col)

    if detected_time:
        return ModelRecommendation(
            model="TimeGAN",
            reason=f"Time signal detected in '{detected_time}', selecting sequential synthesis.",
            imbalance_ratio=ratio,
            detected_time_column=detected_time,
        )
    if ratio is not None and ratio < 0.35:
        return ModelRecommendation(
            model="SMOTE",
            reason=f"Imbalance ratio {ratio:.2f} detected on '{target_col}', selecting SMOTE.",
            imbalance_ratio=ratio,
            detected_time_column=None,
        )

    n_rows, n_cols = df.shape
    n_cat = len(df.select_dtypes(include=["object", "category", "string", "bool"]).columns)
    cat_ratio = n_cat / max(n_cols, 1)

    if n_rows > 8000 and n_cols > 12:
        return ModelRecommendation(
            model="TVAE",
            reason="Large dataset with moderate/high dimensionality; TVAE generally scales better.",
            imbalance_ratio=ratio,
            detected_time_column=None,
        )
    if cat_ratio >= 0.35 or n_cat >= 5:
        return ModelRecommendation(
            model="CTGAN",
            reason="Mixed/categorical-heavy schema detected; CTGAN is preferred.",
            imbalance_ratio=ratio,
            detected_time_column=None,
        )
    return ModelRecommendation(
        model="GaussianCopula",
        reason="Smaller/simple tabular structure; GaussianCopula is fast and stable.",
        imbalance_ratio=ratio,
        detected_time_column=None,
    )


def _validate_input(df: pd.DataFrame, sample_size: int) -> None:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input dataset is empty or invalid.")
    if sample_size <= 0:
        raise ValueError("Sample size must be positive.")


def _reduce_features(df: pd.DataFrame, protected: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    working = df.copy()
    protected = protected if protected else []
    const_cols = [col for col in working.columns if working[col].nunique() <= 1 and col not in protected]
    id_terms = ["id", "uuid", "guid", "key", "index", "hash"]
    id_cols: list[str] = []
    high_card_cols: list[str] = []
    cat_cols = working.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    for col in cat_cols:
        if col in protected:
            continue
        n_unique = working[col].nunique()
        ratio = n_unique / max(1, len(working))
        if ratio > 0.6 and n_unique > 50:
            high_card_cols.append(col)
        elif any(term in str(col).lower() for term in id_terms):
            id_cols.append(col)
    dropped = list(set(const_cols + id_cols + high_card_cols))
    if dropped:
        working = working.drop(columns=dropped)
    return working, dropped


def _bootstrap_synthesize(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    idx = np.random.choice(np.arange(len(df)), size=sample_size, replace=True)
    return df.iloc[idx].reset_index(drop=True)


def _train_single_table_model(df: pd.DataFrame, model_name: str, epochs: int) -> Any:
    if SingleTableMetadata is None:
        raise ImportError("sdv is not installed.")
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(data=df)

    if model_name == "CTGAN":
        if CTGANSynthesizer is None:
            raise ImportError("CTGANSynthesizer unavailable.")
        model = CTGANSynthesizer(metadata=metadata, epochs=epochs)
    elif model_name == "TVAE":
        if TVAESynthesizer is None:
            raise ImportError("TVAESynthesizer unavailable.")
        model = TVAESynthesizer(metadata=metadata, epochs=epochs)
    elif model_name == "GaussianCopula":
        if GaussianCopulaSynthesizer is None:
            raise ImportError("GaussianCopulaSynthesizer unavailable.")
        model = GaussianCopulaSynthesizer(metadata=metadata)
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    model.fit(df)
    return model


def generate_ctgan(df: pd.DataFrame, sample_size: int, epochs: int = 50) -> pd.DataFrame:
    _validate_input(df, sample_size)
    model = _train_single_table_model(df, "CTGAN", int(epochs))
    return model.sample(num_rows=int(sample_size))


def generate_tvae(df: pd.DataFrame, sample_size: int, epochs: int = 50) -> pd.DataFrame:
    _validate_input(df, sample_size)
    model = _train_single_table_model(df, "TVAE", int(epochs))
    return model.sample(num_rows=int(sample_size))


def generate_gaussian_copula(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    _validate_input(df, sample_size)
    model = _train_single_table_model(df, "GaussianCopula", 1)
    return model.sample(num_rows=int(sample_size))


def generate_smote(df: pd.DataFrame, target_col: str, sample_size: int) -> pd.DataFrame:
    _validate_input(df, sample_size)
    if not target_col or target_col not in df.columns:
        raise ValueError("SMOTE requires a valid target column.")
    x = df.drop(columns=[target_col]).copy()
    y = df[target_col].copy()
    if x.empty:
        raise ValueError("SMOTE requires at least one feature column.")

    y = y.fillna("__missing_target__")
    counts = y.value_counts(dropna=False)
    if len(counts) < 2:
        raise ValueError("SMOTE requires at least two classes.")

    for col in x.columns:
        if pd.api.types.is_numeric_dtype(x[col]):
            median = x[col].median()
            x[col] = x[col].fillna(0 if pd.isna(median) else median)
        else:
            mode = x[col].mode(dropna=True)
            x[col] = x[col].fillna(mode.iloc[0] if not mode.empty else "missing")

    cat_cols = x.select_dtypes(include=["object", "category", "bool", "string"]).columns.tolist()
    encoders: dict[str, LabelEncoder] = {}
    for col in cat_cols:
        encoder = LabelEncoder()
        x[col] = encoder.fit_transform(x[col].astype(str))
        encoders[col] = encoder

    min_class = int(counts.min())
    if min_class < 2:
        raise ValueError("Minority class has <2 rows; SMOTE cannot run.")
    k_neighbors = max(1, min(5, min_class - 1))

    sampler = SMOTE(random_state=42, k_neighbors=k_neighbors)
    x_res, y_res = sampler.fit_resample(x, y)
    synth = pd.DataFrame(x_res, columns=x.columns)
    synth[target_col] = y_res

    for col, encoder in encoders.items():
        max_idx = len(encoder.classes_) - 1
        synth[col] = synth[col].round().clip(lower=0, upper=max_idx).astype(int)
        synth[col] = encoder.inverse_transform(synth[col])

    synth = synth.sample(
        sample_size,
        replace=len(synth) < sample_size,
        random_state=42,
    )
    return synth.reset_index(drop=True)


def generate_timegan(
    df: pd.DataFrame,
    sample_size: int,
    time_col: str,
    sequence_key: str | None = None,
    context_columns: list[str] | None = None,
) -> pd.DataFrame:
    _validate_input(df, sample_size)
    if not time_col or time_col not in df.columns:
        raise ValueError("TimeGAN mode requires a valid time column.")
    if PARSynthesizer is None or SingleTableMetadata is None:
        raise ImportError("Sequential synthesizer unavailable in this SDV installation.")

    working = df.copy()
    working[time_col] = pd.to_datetime(working[time_col], errors="coerce")
    working = working.sort_values(time_col).reset_index(drop=True)

    seq_key = sequence_key if sequence_key and sequence_key in working.columns else time_col
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(data=working)
    model = PARSynthesizer(
        metadata=metadata,
        sequence_key=seq_key,
        context_columns=list(context_columns) if context_columns else None,
    )
    model.fit(working)
    return model.sample(num_rows=int(sample_size))


def _fallback_chain(selected_model: str) -> list[str]:
    mapping = {
        "CTGAN": ["CTGAN", "TVAE", "GaussianCopula", "BOOTSTRAP"],
        "TVAE": ["TVAE", "CTGAN", "GaussianCopula", "BOOTSTRAP"],
        "GaussianCopula": ["GaussianCopula", "CTGAN", "BOOTSTRAP"],
        "SMOTE": ["SMOTE", "CTGAN", "GaussianCopula", "BOOTSTRAP"],
        "TimeGAN": ["TimeGAN", "CTGAN", "TVAE", "GaussianCopula", "BOOTSTRAP"],
        "BOOTSTRAP": ["BOOTSTRAP"],
    }
    return mapping.get(selected_model.strip(), ["GaussianCopula", "BOOTSTRAP"])


def generate_with_fallback(
    df: pd.DataFrame,
    selected_model: str,
    sample_size: int,
    epochs: int = 50,
    target_col: str | None = None,
    time_col: str | None = None,
) -> GenerationResult:
    chain = _fallback_chain(selected_model)
    logs: list[str] = [f"Requested model: {selected_model}"]

    protected_cols: list[str] = []
    if target_col:
        protected_cols.append(target_col)
    if time_col:
        protected_cols.append(time_col)
    reduced_df, dropped = _reduce_features(df, protected=protected_cols)

    if dropped:
        logs.append(f"Dropped {len(dropped)} constant/ID/high-cardinality columns for training: {dropped}")

    for model_name in chain:
        try:
            logs.append(f"Trying {model_name}...")
            if model_name == "CTGAN":
                synthetic = generate_ctgan(reduced_df, sample_size, epochs)
            elif model_name == "TVAE":
                synthetic = generate_tvae(reduced_df, sample_size, epochs)
            elif model_name == "GaussianCopula":
                synthetic = generate_gaussian_copula(reduced_df, sample_size)
            elif model_name == "SMOTE":
                synthetic = generate_smote(reduced_df, target_col or "", sample_size)
            elif model_name == "TimeGAN":
                synthetic = generate_timegan(reduced_df, sample_size, time_col or "")
            elif model_name == "BOOTSTRAP":
                synthetic = _bootstrap_synthesize(reduced_df, sample_size)
            else:
                raise ValueError(f"Unknown model '{model_name}'.")

            if synthetic is None or synthetic.empty:
                raise ValueError(f"{model_name} returned empty output.")

            for col in dropped:
                fill_value = "NA" if pd.api.types.is_string_dtype(df[col]) else None
                synthetic[col] = fill_value

            synthetic = synthetic[df.columns].reset_index(drop=True)
            logs.append(f"Success with {model_name}.")
            return GenerationResult(synthetic_df=synthetic, model_used=model_name, logs=logs)

        except Exception as exc:
            logs.append(f"{model_name} failed: {exc}")

    raise ValueError("All generation models failed. Check generation logs.")

def compare_column_statistics(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
    num_cols = [
        c for c in real_df.select_dtypes(include=["number"]).columns if c in synthetic_df.columns
    ]
    if not num_cols:
        return pd.DataFrame()

    rows = []
    for col in num_cols:
        r = real_df[col].dropna()
        s = synthetic_df[col].dropna()
        if r.empty or s.empty:
            continue
        rows.append(
            {
                "column": col,
                "real_mean": float(r.mean()),
                "synth_mean": float(s.mean()),
                "real_std": float(r.std()),
                "synth_std": float(s.std()),
                "mean_abs_diff": float(abs(r.mean() - s.mean())),
                "std_abs_diff": float(abs(r.std() - s.std())),
            }
        )
    return pd.DataFrame(rows)


def ks_test_report(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
    num_cols = [
        c for c in real_df.select_dtypes(include=["number"]).columns if c in synthetic_df.columns
    ]
    results: list[dict[str, float | str]] = []
    for col in num_cols:
        r = real_df[col].dropna()
        s = synthetic_df[col].dropna()
        if r.empty or s.empty:
            continue
        stat, p_value = ks_2samp(r, s)
        results.append(
            {
                "column": col,
                "ks_statistic": float(stat),
                "p_value": float(p_value),
                "similarity_score": float(1 - stat),
            }
        )
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("similarity_score", ascending=False)


def correlation_similarity_score(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> float:
    real_num = real_df.select_dtypes(include=["number"])
    synth_num = synthetic_df.select_dtypes(include=["number"])
    overlap = [c for c in real_num.columns if c in synth_num.columns]
    if len(overlap) < 2:
        return 0.0
    r_corr = real_num[overlap].corr(numeric_only=True).fillna(0)
    s_corr = synth_num[overlap].corr(numeric_only=True).fillna(0)
    diff = np.abs(r_corr.values - s_corr.values)
    return float(max(0.0, 1 - np.mean(diff)))


def build_evaluation_report(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
    stats_df = compare_column_statistics(real_df, synthetic_df)
    ks_df = ks_test_report(real_df, synthetic_df)
    corr_score = correlation_similarity_score(real_df, synthetic_df)

    summary_rows = [
        {"metric": "real_rows", "value": int(len(real_df))},
        {"metric": "synthetic_rows", "value": int(len(synthetic_df))},
        {"metric": "correlation_similarity_score", "value": corr_score},
        {
            "metric": "avg_ks_similarity",
            "value": float(ks_df["similarity_score"].mean()) if not ks_df.empty else np.nan,
        },
    ]
    summary_df = pd.DataFrame(summary_rows)
    if stats_df.empty and ks_df.empty:
        return summary_df

    stats_export = stats_df.copy()
    stats_export.insert(0, "section", "column_statistics")
    if ks_df.empty:
        return pd.concat([summary_df.assign(section="summary"), stats_export], ignore_index=True, sort=False)

    ks_export = ks_df.copy()
    ks_export.insert(0, "section", "ks_test")
    return pd.concat(
        [summary_df.assign(section="summary"), stats_export, ks_export],
        ignore_index=True,
        sort=False,
    )


def missing_heatmap(df: pd.DataFrame, max_rows: int = 300):
    sample = df.head(max_rows).isna().astype(int)
    fig = px.imshow(
        sample.transpose(),
        color_continuous_scale=[[0, "#1f2937"], [1, "#ef4444"]],
        aspect="auto",
        title=f"Missing Data Heatmap (first {len(sample)} rows)",
    )
    fig.update_layout(height=420)
    return fig


def correlation_heatmap(df: pd.DataFrame, title: str = "Correlation Heatmap"):
    num_df = df.select_dtypes(include=["number"])
    if num_df.shape[1] < 2:
        return None
    corr = num_df.corr(numeric_only=True)
    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
        title=title,
    )
    fig.update_layout(height=500)
    return fig


def distribution_comparison(real_df: pd.DataFrame, synthetic_df: pd.DataFrame, column: str):
    if column not in real_df.columns or column not in synthetic_df.columns:
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=real_df[column], name="Real", opacity=0.58, marker_color="#2563eb", nbinsx=50
        )
    )
    fig.add_trace(
        go.Histogram(
            x=synthetic_df[column],
            name="Synthetic",
            opacity=0.58,
            marker_color="#f97316",
            nbinsx=50,
        )
    )
    fig.update_layout(
        barmode="overlay",
        title=f"Distribution Comparison: {column}",
        xaxis_title=column,
        yaxis_title="Count",
        height=400,
    )
    return fig


def run_full_pipeline(
    source: str | tuple[str, bytes],
    model_mode: str = "AUTO",
    selected_model: str | None = None,
    sample_size: int | None = None,
    epochs: int = 30,
    target_col: str | None = None,
    time_col: str | None = None,
    sep_override: str | None = None,
    header_override: int | None = None,
) -> PipelineResult:
    """
    source:
      - local path string, or
      - tuple(file_name, file_bytes) e.g., from google.colab files.upload()
    """
    if isinstance(source, str):
        raw_df, ingestion = load_dataset_from_path(
            source, sep_override=sep_override, header_override=header_override
        )
    else:
        file_name, file_bytes = source
        raw_df, ingestion = load_dataset_from_bytes(
            file_name, file_bytes, sep_override=sep_override, header_override=header_override
        )

    clean_df, cleaning = clean_dataset(raw_df, fill_missing=True)
    profile = build_profile(clean_df)

    recommendation = recommend_model(clean_df, target_col=target_col, time_col=time_col)
    model_to_use = recommendation.model if model_mode.upper() == "AUTO" else (selected_model or "GaussianCopula")
    row_count = len(clean_df)
    synth_rows = sample_size if sample_size and sample_size > 0 else min(max(row_count, 100), 1000)

    generation = generate_with_fallback(
        df=clean_df,
        selected_model=model_to_use,
        sample_size=int(synth_rows),
        epochs=int(epochs),
        target_col=target_col,
        time_col=time_col,
    )

    synthetic_df, _ = clean_dataset(generation.synthetic_df, fill_missing=True)
    eval_report = build_evaluation_report(clean_df, synthetic_df)

    return PipelineResult(
        raw_df=raw_df,
        clean_df=clean_df,
        synthetic_df=synthetic_df,
        ingestion=ingestion,
        cleaning=cleaning,
        profile=profile,
        recommendation=recommendation,
        evaluation_report=eval_report,
        generation_logs=generation.logs,
    )


if __name__ == "__main__":
    print("collab.py loaded.")
    print("Use run_full_pipeline(...) with a file path or (filename, bytes).")
