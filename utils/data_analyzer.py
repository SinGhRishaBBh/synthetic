import pandas as pd
import numpy as np
import streamlit as st

class DataAnalyzer:
    """
    Computes statistical characteristics, correlation weights, and class distribution
    from a pandas.DataFrame for downstream synthetic modeling or dashboard rendering.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
    def get_summary_stats(self) -> pd.DataFrame:
        """
        Returns descriptive statistics summary.
        Fallback to categoricals if no numerical columns exist.
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()
            
        num_df = self.df.select_dtypes(include=['number'])
        if num_df.empty:
             return self.df.describe(include='all').T
             
        return self.df.describe(include=[np.number]).T

    def get_missing_values(self) -> pd.DataFrame:
        """
        Returns table containing columns and missing row count/ratio.
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()
            
        missing_count = self.df.isna().sum()
        missing_pct = (missing_count / len(self.df)) * 100
        
        missing_df = pd.DataFrame({
            'Column': missing_count.index,
            'Missing Count': missing_count.values,
            'Missing %': missing_pct.values
        })
        
        return missing_df[missing_df['Missing Count'] > 0].sort_values(by='Missing %', ascending=False)

    def get_class_distribution(self, target_col: str) -> pd.DataFrame:
        """
        Returns distribution of labels in target columns.
        """
        if target_col not in self.df.columns:
            return pd.DataFrame()
            
        counts = self.df[target_col].value_counts()
        pct = self.df[target_col].value_counts(normalize=True) * 100
        
        return pd.DataFrame({
            'Label': counts.index,
            'Count': counts.values,
            'Percentage %': pct.values
        })

    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        Computes pearson correlation for continuous features.
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()
            
        num_df = self.df.select_dtypes(include=['number'])
        if num_df.shape[1] < 2:
            return pd.DataFrame()
            
        return num_df.corr()
