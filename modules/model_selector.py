from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ModelRecommendation:
    model: str
    reason: str
    imbalance_ratio: float | None
    detected_time_column: str | None



def _infer_time_column(df: pd.DataFrame) -> str | None:
    datetime_cols = df.select_dtypes(include=["datetime", "datetimetz", "datetime64[ns]"]).columns.tolist()
    if datetime_cols:
        return datetime_cols[0]

    for col in df.columns:
        col_lower = str(col).lower()
        if any(k in col_lower for k in ["date", "time", "timestamp"]):
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
    df: pd.DataFrame,
    target_col: str | None = None,
    time_col: str | None = None,
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
            reason="Mixed/categorical-heavy schema detected; CTGAN is preferred for tabular dependencies.",
            imbalance_ratio=ratio,
            detected_time_column=None,
        )

    return ModelRecommendation(
        model="GaussianCopula",
        reason="Smaller/simple tabular structure detected; Gaussian Copula is fast and stable.",
        imbalance_ratio=ratio,
        detected_time_column=None,
    )
