from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go



def missing_values_chart(df: pd.DataFrame):
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        return None

    chart_df = pd.DataFrame({"column": missing.index, "missing_count": missing.values})
    fig = px.bar(
        chart_df,
        x="missing_count",
        y="column",
        orientation="h",
        color="missing_count",
        color_continuous_scale="OrRd",
        title="Missing Values by Column",
    )
    fig.update_layout(height=420)
    return fig



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



def class_balance_chart(df: pd.DataFrame, target_col: str):
    if target_col not in df.columns:
        return None

    counts = df[target_col].astype(str).value_counts(dropna=False).reset_index()
    counts.columns = ["class", "count"]
    fig = px.bar(counts, x="class", y="count", title=f"Class Balance: {target_col}", color="count")
    fig.update_layout(height=380)
    return fig



def distribution_comparison(real_df: pd.DataFrame, synthetic_df: pd.DataFrame, column: str):
    if column not in real_df.columns or column not in synthetic_df.columns:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=real_df[column],
            name="Real",
            opacity=0.58,
            marker_color="#2563eb",
            nbinsx=50,
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



def feature_distribution(df: pd.DataFrame, column: str):
    if column not in df.columns:
        return None

    if pd.api.types.is_numeric_dtype(df[column]):
        fig = px.histogram(df, x=column, nbins=50, title=f"Feature Distribution: {column}")
    else:
        counts = df[column].astype(str).value_counts().head(25).reset_index()
        counts.columns = ["value", "count"]
        fig = px.bar(counts, x="value", y="count", title=f"Top Categories: {column}")
    fig.update_layout(height=380)
    return fig



def time_trend_chart(df: pd.DataFrame, time_col: str, value_col: str | None = None):
    if time_col not in df.columns:
        return None

    working = df.copy()
    working[time_col] = pd.to_datetime(working[time_col], errors="coerce")
    working = working.dropna(subset=[time_col]).sort_values(time_col)
    if working.empty:
        return None

    if value_col and value_col in working.columns and pd.api.types.is_numeric_dtype(working[value_col]):
        by_time = working.groupby(time_col, as_index=False)[value_col].mean()
        fig = px.line(by_time, x=time_col, y=value_col, title=f"Time Trend ({value_col})")
    else:
        by_time = working.groupby(time_col, as_index=False).size().rename(columns={"size": "count"})
        fig = px.line(by_time, x=time_col, y="count", title="Record Volume Over Time")
    fig.update_layout(height=380)
    return fig
