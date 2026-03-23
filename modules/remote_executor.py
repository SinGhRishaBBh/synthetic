from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class RemoteExecutionResult:
    synthetic_df: pd.DataFrame
    model_used: str
    logs: list[str] = field(default_factory=list)
    evaluation_df: pd.DataFrame | None = None


def run_remote_generation(
    df: pd.DataFrame,
    selected_model: str,
    sample_size: int,
    epochs: int = 50,
    target_col: str | None = None,
    time_col: str | None = None,
    worker_url: str = "",
    timeout_sec: int = 900,
) -> RemoteExecutionResult:
    if df is None or df.empty:
        raise ValueError("Cannot offload generation: input dataframe is empty.")
    if not worker_url:
        raise ValueError("Remote worker URL is required.")

    payload = {
        "df_json": df.to_json(orient="split", date_format="iso"),
        "selected_model": selected_model,
        "sample_size": int(sample_size),
        "epochs": int(epochs),
        "target_col": target_col,
        "time_col": time_col,
    }

    endpoint = worker_url.rstrip("/") + "/generate"
    req = urllib.request.Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Remote worker HTTP {exc.code}: {err_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Remote worker is unreachable: {exc}") from exc

    response_obj = json.loads(raw)
    synthetic_json = response_obj.get("synthetic_json")
    if not synthetic_json:
        raise RuntimeError("Remote worker response missing synthetic_json.")

    synthetic_df = pd.read_json(io.StringIO(synthetic_json), orient="split")
    evaluation_json = response_obj.get("evaluation_json")
    evaluation_df = (
        pd.read_json(io.StringIO(evaluation_json), orient="split")
        if evaluation_json
        else None
    )

    return RemoteExecutionResult(
        synthetic_df=synthetic_df,
        model_used=str(response_obj.get("model_used", selected_model)),
        logs=[str(x) for x in response_obj.get("logs", [])],
        evaluation_df=evaluation_df,
    )
