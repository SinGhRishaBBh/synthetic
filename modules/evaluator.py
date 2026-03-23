from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp



def compare_column_statistics(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
    num_cols = [
        c
        for c in real_df.select_dtypes(include=["number"]).columns
        if c in synthetic_df.columns
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
        c
        for c in real_df.select_dtypes(include=["number"]).columns
        if c in synthetic_df.columns
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

    return pd.DataFrame(results).sort_values("similarity_score", ascending=False) if results else pd.DataFrame()



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
        {"metric": "avg_ks_similarity", "value": float(ks_df["similarity_score"].mean()) if not ks_df.empty else np.nan},
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
