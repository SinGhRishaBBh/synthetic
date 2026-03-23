# Synthetic Data Platform

A modular Streamlit platform for synthetic data workflows across ingestion, cleaning, model selection, generation, evaluation, visualization, and export.

## Features

- Smart ingestion for CSV/Excel (header detection, metadata-row handling, merged-cell mitigation)
- Automated cleaning and profiling for messy real-world datasets
- Intelligent model auto-selection (`CTGAN`, `TVAE`, `GaussianCopula`, `SMOTE`, `TimeGAN` mode)
- Manual override with configurable epochs, sample size, target, and time columns
- Fallback-aware synthesis engine so generation can recover if one model fails
- Evaluation suite with KS test, statistical comparisons, and correlation similarity
- Interactive Plotly dashboard for distributions, class balance, missingness, correlations, and trends
- Export synthetic data and evaluation reports

## Project Structure

- `app.py`
- `modules/`
  - `ingestion.py`
  - `cleaning.py`
  - `profiling.py`
  - `model_selector.py`
  - `generators.py`
  - `evaluator.py`
  - `visualizer.py`

## Setup

1. Create virtual environment

```bash
python -m venv venv
```

2. Activate environment

Windows PowerShell:

```powershell
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Run application

```bash
streamlit run app.py
```

## Notes

- Use sidebar navigation for `Upload`, `Cleaning`, `Synthesis`, and `Evaluation`.
- The Evaluation section includes tabs for `Data Profile`, `Correlation`, `Synthesis`, and `Evaluation`.
- Caching is enabled for ingestion and model training paths to improve repeated runs.
