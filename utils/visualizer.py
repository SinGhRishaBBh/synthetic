import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

class Visualizer:
    @staticmethod
    def plot_missing_values(df: pd.DataFrame):
        """
        Plots Heatmap of missing rows or bar chart of totals.
        """
        missing_count = df.isna().sum()
        missing_df = pd.DataFrame({'Column': missing_count.index, 'Missing Count': missing_count.values})
        missing_df = missing_df[missing_df['Missing Count'] > 0].sort_values(by='Missing Count', ascending=True)

        if missing_df.empty:
            st.success("✅ No missing values detected in dataset.")
            return

        fig = px.bar(
            missing_df,
            y='Column',
            x='Missing Count',
            title='Missing Values Distribution',
            color='Missing Count',
            color_continuous_scale='Reds',
            text_auto=True
        )
        fig.update_layout(height=400, title={'x': 0.5})
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def plot_class_distribution(df: pd.DataFrame, target_col: str):
        """
        Plots class distribution using Plotly Pie and Bar.
        """
        if target_col not in df.columns:
            return

        counts = df[target_col].value_counts().reset_index()
        counts.columns = ['Label', 'Count']

        fig = px.pie(
            counts, 
            values='Count', 
            names='Label', 
            title=f"Class Balance for '{target_col}'",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(title={'x': 0.5})
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def plot_correlation_heatmap(df: pd.DataFrame, title: str = "Correlation Heatmap"):
        """
        Plots a Pearson Correlation Heatmap for continuous columns.
        """
        num_df = df.select_dtypes(include=['number'])
        if num_df.shape[1] < 2:
             st.warning("⚠️ Need at least 2 numerical columns for correlations.")
             return

        corr = num_df.corr()
        
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale='RdBu_r',
            title=title,
            labels=dict(color="Correlation"),
            aspect="auto"
        )
        fig.update_layout(title={'x': 0.5}, height=500)
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def plot_distribution_comparison(real_df: pd.DataFrame, synthetic_df: pd.DataFrame, column: str):
         """
         Overlays distribution comparison of Real vs Synthetic columns.
         """
         if column not in real_df.columns or column not in synthetic_df.columns:
              return

         real_series = real_df[column].fillna(0)
         synth_series = synthetic_df[column].fillna(0)

         fig = go.Figure()

         # Add Real
         fig.add_trace(go.Histogram(
             x=real_series,
             name='Real',
             opacity=0.6,
             marker_color='#3366ff'
         ))

         # Add Synthetic
         fig.add_trace(go.Histogram(
             x=synth_series,
             name='Synthetic',
             opacity=0.6,
             marker_color='#ff3366'
         ))

         fig.update_layout(
             title=dict(text=f"Distribution Comparison: {column} (Real vs Synthetic)", x=0.5),
             barmode='overlay',
             xaxis_title=column,
             yaxis_title="Density Count",
             legend_title_text="Source"
         )
         st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def plot_correlation_side_by_side(real_df: pd.DataFrame, synthetic_df: pd.DataFrame):
         """
         Compares Correlation Matrix side by side accurately.
         """
         num_real = real_df.select_dtypes(include=['number'])
         num_synth = synthetic_df.select_dtypes(include=['number'])

         if num_real.shape[1] < 2:
              return

         col1, col2 = st.columns(2)

         with col1:
              Visualizer.plot_correlation_heatmap(num_real, title="Real Dataset Correlation")

         with col2:
              Visualizer.plot_correlation_heatmap(num_synth, title="Synthetic Dataset Correlation")
