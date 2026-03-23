import pandas as pd
import numpy as np
from scipy.stats import ks_2samp

class Evaluator:
    @staticmethod
    def compare_statistics(real_df: pd.DataFrame, synthetic_df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Compares basic descriptive statistics (Mean, Std, Max, Min) between
        Real and Synthetic series for numerical fields.
        """
        if column not in real_df.columns or column not in synthetic_df.columns:
            return {}

        s_real = real_df[column].dropna()
        s_synth = synthetic_df[column].dropna()

        if s_real.empty or s_synth.empty:
            return {}

        stats = {
            'Metric': ['Mean', 'Std Dev', 'Min', 'Max'],
            'Real': [s_real.mean(), s_real.std(), s_real.min(), s_real.max()],
            'Synthetic': [s_synth.mean(), s_synth.std(), s_synth.min(), s_synth.max()]
        }

        # Calculate absolute percentage error or difference
        diff = []
        for r, s in zip(stats['Real'], stats['Synthetic']):
            if pd.notna(r) and pd.notna(s):
                diff.append(abs(r - s) / abs(r) if r != 0 else abs(r - s))
            else:
                diff.append(0)

        stats['% Error'] = [d * 100 for d in diff]
        
        return pd.DataFrame(stats)

    @staticmethod
    def run_ks_test(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> pd.DataFrame:
        """
        Runs Kolmogorov-Smirnov test on all numerical columns.
        Higher p-value means distributions are more similar.
        Generally with Alpha=0.05, p-value > 0.05 fails to reject null hypothesis,
        which implies distributions are statistically IDENTICAL or highly similar.
        """
        num_cols = real_df.select_dtypes(include=['number']).columns.tolist()
        num_cols = [col for col in num_cols if col in synthetic_df.columns]
        
        results = []
        for col in num_cols:
            s_real = real_df[col].dropna()
            s_synth = synthetic_df[col].dropna()

            if s_real.empty or s_synth.empty:
                 continue

            try:
                stat, p_value = ks_2samp(s_real, s_synth)
                # KS Score can be 1 - statistics (where lower stat means high similarity)
                similarity_score = 1 - stat 
                
                results.append({
                    'Column': col,
                    'KS Statistic': stat,
                    'p-value': p_value,
                    'Similarity Score': similarity_score
                })
            except Exception:
                pass

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results).sort_values(by='Similarity Score', ascending=False)

    @staticmethod
    def get_correlation_difference(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> float:
        """
        Computes average absolute difference in Numerical Correlation matrix.
        0 means identical correlation weights. 1 means completely opposite.
        """
        num_real = real_df.select_dtypes(include=['number'])
        num_synth = synthetic_df.select_dtypes(include=['number'])

        # Ensure same columns
        overlap_cols = [c for c in num_real.columns if c in num_synth.columns]
        if len(overlap_cols) < 2:
             return 0.0

        r_corr = num_real[overlap_cols].corr().fillna(0).values
        s_corr = num_synth[overlap_cols].corr().fillna(0).values

        diff = np.abs(r_corr - s_corr)
        return np.mean(diff)
