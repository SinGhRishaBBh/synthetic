import pandas as pd
import numpy as np
import warnings

def detect_best_model(df: pd.DataFrame, target_col: str = None, time_col: str = None) -> dict:
    """
    Intelligently select the best Synthetic Data Generator model for a DataFrame
    based on columns, sparsity, dimension, and optional target/time headers.
    
    Returns:
        dict: {
            'model': 'CTGAN' | 'TVAESynthesizer' | 'GaussianCopulaSynthesizer' | 'SMOTE' | 'Sequential',
            'reason': 'Explanation string for user reasoning dashboard'
        }
    """
    results = {
        'model': 'GaussianCopulaSynthesizer', 
        'reason': 'Default back-up model for general tabular processing.'
    }

    if df is None or df.empty:
        return results

    # 1. Check for Sequential/Time-Series triggers
    datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    if time_col and time_col in df.columns:
        results['model'] = 'TimeGAN' if time_col else 'Sequential'
        results['reason'] = f"Detected chronological ordering using time column: '{time_col}'. Sequential training triggers Time-Series generators."
        return results
    elif datetime_cols:
         results['model'] = 'TimeGAN'
         results['reason'] = f"Detected datetime fields: {datetime_cols}. Recommending sequence-based sequential modeling for accuracy."
         return results

    # 2. Check for Imbalanced-Learn triggers (SMOTE)
    if target_col and target_col in df.columns:
         label_counts = df[target_col].value_counts()
         if len(label_counts) == 2: # Binary classification
             maj_class = label_counts.max() 
             min_class = label_counts.min()
             imbalance_ratio = min_class / maj_class
             if imbalance_ratio < 0.3: # Less than 30% ratio is generally imbalanced
                  results['model'] = 'SMOTE'
                  results['reason'] = f"Detected high class-imbalance ratio ({imbalance_ratio:.2f}) on '{target_col}'. SMOTE balancing solves skewness best."
                  return results

    cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    cat_pct = len(cat_cols) / len(df.columns) if len(df.columns) > 0 else 0

    # 3. Choose Deep Learning vs Statistical Copula
    if cat_pct > 0.4 or len(cat_cols) > 5:
        results['model'] = 'CTGAN'
        results['reason'] = "Columns heavily contain non-numerical discrete weights (category features). CTGAN performs best for deep correlation structures with labels."
    elif len(df) > 10000 and len(num_cols) > 10:
        results['model'] = 'TVAESynthesizer'
        results['reason'] = "Large numeric-heavy datasets train extremely fast and with high correlation accuracy on Auto-Encoder neural structures (TVAE)."
    else:
        results['model'] = 'GaussianCopulaSynthesizer'
        results['reason'] = "Small discrete correlations easily train on statistical multivariate Gaussian Copulas with low memory budgets."

    return results
