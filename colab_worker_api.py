"""
Run this on Google Colab to offload heavy synthesis/evaluation.

Colab cells:
!pip -q install fastapi uvicorn nest-asyncio pyngrok pandas numpy scipy scikit-learn imbalanced-learn openpyxl plotly sdv
!wget -q -O collab.py https://raw.githubusercontent.com/<you>/<repo>/<branch>/collab.py
!wget -q -O colab_worker_api.py https://raw.githubusercontent.com/<you>/<repo>/<branch>/colab_worker_api.py
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from collab import build_evaluation_report, clean_dataset, generate_with_fallback

app = FastAPI(title="Synthetic Colab Worker")


class GenerateRequest(BaseModel):
    df_json: str
    selected_model: str
    sample_size: int
    epochs: int = 30
    target_col: str | None = None
    time_col: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
def generate(req: GenerateRequest) -> dict[str, Any]:
    try:
        real_df = pd.read_json(io.StringIO(req.df_json), orient="split")
        result = generate_with_fallback(
            df=real_df,
            selected_model=req.selected_model,
            sample_size=int(req.sample_size),
            epochs=int(req.epochs),
            target_col=req.target_col,
            time_col=req.time_col,
        )
        synthetic_df, _ = clean_dataset(result.synthetic_df, fill_missing=True)
        evaluation_df = build_evaluation_report(real_df, synthetic_df)
        return {
            "model_used": result.model_used,
            "logs": result.logs,
            "synthetic_json": synthetic_df.to_json(orient="split", date_format="iso"),
            "evaluation_json": evaluation_df.to_json(orient="split", date_format="iso"),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
