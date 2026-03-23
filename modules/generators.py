from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import streamlit as st
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import LabelEncoder

from sdv.metadata import SingleTableMetadata
from sdv.single_table import CTGANSynthesizer, GaussianCopulaSynthesizer, TVAESynthesizer

try:
    from sdv.sequential import PARSynthesizer
except Exception:  # pragma: no cover
    PARSynthesizer = None


def _reduce_features(df: pd.DataFrame, protected: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    working = df.copy()
    protected = protected if protected else []
    
    const_cols = [col for col in working.columns if working[col].nunique() <= 1 and col not in protected]
    id_terms = ["id", "uuid", "guid", "key", "index", "hash"]
    id_cols = []
    high_card_cols = []
    
    cat_cols = working.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    for col in cat_cols:
         if col in protected: continue
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



@dataclass
class GenerationResult:
    synthetic_df: pd.DataFrame
    model_used: str
    logs: list[str] = field(default_factory=list)



def _validate_input(df: pd.DataFrame, sample_size: int) -> None:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input dataset is empty or invalid.")
    if sample_size <= 0:
        raise ValueError("Sample size must be positive.")


@st.cache_resource(show_spinner=False)
def _train_single_table_model(df: pd.DataFrame, model_name: str, epochs: int) -> Any:
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(data=df)

    if model_name == "CTGAN":
        model = CTGANSynthesizer(metadata=metadata, epochs=epochs)
    elif model_name == "TVAE":
        model = TVAESynthesizer(metadata=metadata, epochs=epochs)
    elif model_name == "GaussianCopula":
        model = GaussianCopulaSynthesizer(metadata=metadata)
    else:
        raise ValueError(f"Unsupported single-table model: {model_name}")

    model.fit(df)
    return model


@st.cache_resource(show_spinner=False)
def _train_sequential_model(df: pd.DataFrame, sequence_key: str, context_columns: tuple[str, ...]) -> Any:
    if PARSynthesizer is None:
        raise ImportError("Sequential synthesizer is not available in this SDV installation.")

    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(data=df)

    model = PARSynthesizer(
        metadata=metadata,
        sequence_key=sequence_key,
        context_columns=list(context_columns) if context_columns else None,
    )
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
        raise ValueError("Minority class has fewer than 2 rows; SMOTE cannot be applied.")

    k_neighbors = max(1, min(5, min_class - 1))
    sampler = SMOTE(random_state=42, k_neighbors=k_neighbors)
    x_res, y_res = sampler.fit_resample(x, y)

    synth = pd.DataFrame(x_res, columns=x.columns)
    synth[target_col] = y_res

    for col, encoder in encoders.items():
        max_idx = len(encoder.classes_) - 1
        synth[col] = synth[col].round().clip(lower=0, upper=max_idx).astype(int)
        synth[col] = encoder.inverse_transform(synth[col])

    if len(synth) < sample_size:
        synth = synth.sample(sample_size, replace=True, random_state=42)
    else:
        synth = synth.sample(sample_size, replace=False, random_state=42)

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

    working = df.copy()
    working[time_col] = pd.to_datetime(working[time_col], errors="coerce")
    working = working.sort_values(time_col).reset_index(drop=True)

    seq_key = sequence_key if sequence_key and sequence_key in working.columns else time_col
    model = _train_sequential_model(
        working,
        sequence_key=seq_key,
        context_columns=tuple(context_columns or []),
    )
    return model.sample(num_rows=int(sample_size))



def _fallback_chain(selected_model: str) -> list[str]:
    model = selected_model.strip()
    mapping = {
        "CTGAN": ["CTGAN", "TVAE", "GaussianCopula"],
        "TVAE": ["TVAE", "CTGAN", "GaussianCopula"],
        "GaussianCopula": ["GaussianCopula", "CTGAN"],
        "SMOTE": ["SMOTE", "CTGAN", "GaussianCopula"],
        "TimeGAN": ["TimeGAN", "CTGAN", "TVAE", "GaussianCopula"],
    }
    return mapping.get(model, ["GaussianCopula"])



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

    # 1. Feature reduction optimization
    protected_cols = []
    if target_col: protected_cols.append(target_col)
    if time_col: protected_cols.append(time_col)
    reduced_df, dropped = _reduce_features(df, protected=protected_cols)
    if dropped:
         logs.append(f"Optimized training speed by skipping {len(dropped)} constant/ID columns: {dropped}")

    for model_name in chain:
        try:
            logs.append(f"Trying {model_name}...")
            if model_name == "CTGAN":
                synthetic = generate_ctgan(df=reduced_df, sample_size=sample_size, epochs=epochs)
            elif model_name == "TVAE":
                synthetic = generate_tvae(df=reduced_df, sample_size=sample_size, epochs=epochs)
            elif model_name == "GaussianCopula":
                synthetic = generate_gaussian_copula(df=reduced_df, sample_size=sample_size)
            elif model_name == "SMOTE":
                synthetic = generate_smote(df=reduced_df, target_col=target_col or "", sample_size=sample_size)
            elif model_name == "TimeGAN":
                synthetic = generate_timegan(df=reduced_df, sample_size=sample_size, time_col=time_col or "")
            else:
                raise ValueError(f"Unknown model '{model_name}'.")

            if synthetic is None or synthetic.empty:
                raise ValueError(f"{model_name} returned empty output.")

            # 2. Re-inject dropped columns to match original schema
            for col in dropped:
                 synthetic[col] = "NA" if pd.api.types.is_string_dtype(df[col]) else None

            logs.append(f"Success with {model_name}.")
            return GenerationResult(
                synthetic_df=synthetic[df.columns].reset_index(drop=True),
                model_used=model_name,
                logs=logs,
            )

        except Exception as exc:
            logs.append(f"{model_name} failed: {exc}")

    raise ValueError("All generation models failed. Check logs for details.")
