from __future__ import annotations

import os
import time
import pandas as pd
import streamlit as st

# Custom UI Modules
from ui.dashboard import setup_dashboard_styles, render_top_navbar, render_page_header, render_sidebar_header
from ui.cards import metric_card, glass_card_container, close_glass_card, section_header, list_item_card, info_tooltip
from ui.charts import apply_luminal_theme

# Backend Logic Modules
from modules.cleaning import clean_dataset
from modules.evaluator import (
    build_evaluation_report,
    compare_column_statistics,
    correlation_similarity_score,
    ks_test_report,
)
from modules.generators import generate_with_fallback
from modules.ingestion import load_dataset
from modules.model_selector import recommend_model
from modules.remote_executor import run_remote_generation
from modules.profiling import (
    build_profile,
    missing_values_table,
    summary_statistics,
)
from modules.visualizer import (
    correlation_heatmap,
    distribution_comparison,
    missing_heatmap,
)

# 1. Page Config Setup
st.set_page_config(
    page_title="Synthetic Data Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject CSS Theme and styles
setup_dashboard_styles()

def init_session_state() -> None:
    defaults = {
        "raw_df": None,
        "clean_df": None,
        "synthetic_df": None,
        "evaluation_df": None,
        "diagnostics": None,
        "cleaning_report": None,
        "source_name": None,
        "last_model_used": None,
        "original_df": None,
        "reduced_df": None,
        "sampling_enabled": False,
        "remote_worker_url": os.getenv("SYNTHETIC_WORKER_URL", ""),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# 3. Sidebar Navigation
with st.sidebar:
    render_sidebar_header()
    
    st.markdown('<p style="font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.2rem; color: #a7abb2; opacity: 0.4; margin-bottom: 0.5rem;">Navigation</p>', unsafe_allow_html=True)
    if "nav_index" not in st.session_state:
        st.session_state.nav_index = 0

    section = st.radio(
        "Module",
        ["📥 Upload", "🧹 Cleaning", "🔄 Synthesis", "📊 Evaluation"],
        index=st.session_state.nav_index,
        label_visibility="collapsed"
    )

_nav_items = ["Upload", "Cleaning", "Synthesis", "Evaluation"]
current_section = section.split(" ")[1] if " " in section else section
if current_section in _nav_items:
    st.session_state.nav_index = _nav_items.index(current_section)

# 4. Global Navbar Header
render_top_navbar()

# Main Container Sub Layout
main_content = st.container()

with main_content:
    st.markdown('<div style="padding-top: 2rem; padding-left: 1.5rem; padding-right: 1.5rem;">', unsafe_allow_html=True)

    # Ingestion Side Effects
    with st.sidebar:
        st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.2rem; color: #a7abb2; opacity: 0.4; margin-bottom: 0.5rem;">Quick Action</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Drop Asset", type=["csv", "xls", "xlsx"], label_visibility="collapsed")

    sep_override = None
    header_override = None

    if uploaded_file is not None:
        with st.sidebar:
            with st.expander("Advanced Settings", expanded=False):
                 if uploaded_file.name.lower().endswith(".csv"):
                      sep_choice = st.selectbox("Delimiter", ["Auto", ",", ";", "\t", "|"])
                      if sep_choice != "Auto": sep_override = sep_choice
                 
                 header_choice = st.selectbox("Header Row", ["Auto", "Row 0", "Row 1", "Row 2", "Row 3"])
                 if header_choice != "Auto":
                      header_override = int(header_choice.split(" ")[1])

        current_key = f"{uploaded_file.name}_{sep_override}_{header_override}"
        if st.session_state.get('source_name') != current_key:
            try:
                raw_df, diagnostics = load_dataset(uploaded_file, sep_override=sep_override, header_override=header_override)
                cleaned_df, cleaning_report = clean_dataset(raw_df, fill_missing=True)

                if cleaned_df.empty:
                    st.sidebar.error("Dataset is empty after cleaning.")
                else:
                    st.session_state.raw_df = raw_df
                    st.session_state.clean_df = cleaned_df
                    st.session_state.original_df = cleaned_df
                    st.session_state.reduced_df = None
                    st.session_state.sampling_enabled = False
                    st.session_state.synthetic_df = None
                    st.session_state.evaluation_df = None
                    st.session_state.diagnostics = diagnostics
                    st.session_state.cleaning_report = cleaning_report
                    st.session_state.source_name = current_key
            except Exception as exc:
                st.sidebar.error(f"Load failed: {exc}")
    # 5. Global Metrics & Header Layer
    render_page_header("Synthetic Data Platform", "Unified workflows for ingestion, cleaning, synthesis, evaluation, and export.")

    # Calculate Metrics with Safe Fallbacks
    rows_val = "Pending"
    cols_val = "Pending"
    missing_cells = "Pending"
    missing_pct = "Pending"
    model_used = st.session_state.get('last_model_used', "Pending") or "Pending"
    sim_score = "Pending"

    if st.session_state.get('sampling_enabled') and st.session_state.get('reduced_df') is not None:
        real_df = st.session_state.reduced_df
    else:
        real_df = st.session_state.get('clean_df')

    profile = None
    if real_df is not None:
        from modules.profiling import build_profile
        profile = build_profile(real_df)
        rows_val = f"{profile.rows:,}"
        cols_val = f"{profile.columns}"
        missing_cells = f"{profile.missing_cells:,}"
        missing_pct = f"{profile.missing_percent:.1f}%"
        
        if st.session_state.synthetic_df is not None:
            try:
                from modules.evaluator import correlation_similarity_score
                sim_score = f"{correlation_similarity_score(real_df, st.session_state.synthetic_df):.3f}"
            except Exception:
                pass

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: metric_card("Rows", rows_val, "Aggregate Data Points", "lan")
    with m2: metric_card("Columns", cols_val, "Schema Density", "grid_view")
    with m3: metric_card("Missing Cells", missing_cells, "Sparsity Nodes", "query_stats", color="tertiary")
    with m4: metric_card("Sparsity %", missing_pct, "Integrity Deficit", "opacity", color="tertiary")
    with m5: metric_card("Model Node", model_used, "Active Sub-Network", "memory")
    with m6: metric_card("Similarity", sim_score, "Distribution Overlap", "hub")

    st.markdown('<div style="height: 1.5rem; margin-top: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.04);"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # 6. Page Routing Execution
    # ---------------- Upload Section ----------------
    if current_section == "Upload":
        section_header("Data Ingestion", "Streamline layout for real-time validation comparison.")
        
        diagnostics = st.session_state.diagnostics
        if diagnostics is not None:
             st.markdown(glass_card_container("Asset Metadata", icon="fingerprint"), unsafe_allow_html=True)
             c1, c2, c3 = st.columns(3)
             with c1: st.markdown(f'<p style="font-size: 11px; font-weight: bold; color: #a7abb2; text-transform: uppercase;">File</p><p style="color: #fff; font-size: 0.875rem; margin-top: 0.25rem;">{diagnostics.file_name}</p>', unsafe_allow_html=True)
             with c2: st.markdown(f'<p style="font-size: 11px; font-weight: bold; color: #a7abb2; text-transform: uppercase;">Header Row</p><p style="color: #fff; font-size: 0.875rem; margin-top: 0.25rem;">{diagnostics.detected_header_row or "N/A"}</p>', unsafe_allow_html=True)
             with c3: st.markdown(f'<p style="font-size: 11px; font-weight: bold; color: #a7abb2; text-transform: uppercase;">Format</p><p style="color: #fff; font-size: 0.875rem; margin-top: 0.25rem;">{diagnostics.file_type}</p>', unsafe_allow_html=True)
             st.markdown(close_glass_card(), unsafe_allow_html=True)
             st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)
             
             c1, c2 = st.columns(2)
             with c1:
                 st.markdown(glass_card_container("Raw Node Preview", icon="table_chart"), unsafe_allow_html=True)
                 st.dataframe(diagnostics.raw_preview, use_container_width=True)
                 st.markdown(close_glass_card(), unsafe_allow_html=True)
             with c2:
                 st.markdown(glass_card_container("Cleaned Cluster Preview", icon="cleaning_services"), unsafe_allow_html=True)
                 st.dataframe(diagnostics.cleaned_preview, use_container_width=True)
                 st.markdown(close_glass_card(), unsafe_allow_html=True)
        else:
             st.markdown(
                 """
                 <div class="glass-panel" style="border-radius: 1rem; padding: 4rem; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border: 1px dashed rgba(129, 236, 255, 0.1); background: rgba(20, 26, 32, 0.2);">
                     <div style="width: 4rem; height: 4rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.05); border-radius: 1rem; display: flex; align-items: center; justify-content: center; margin-bottom: 1.5rem;">
                         <span class="material-symbols-outlined" style="font-size: 2rem; color: rgba(129, 236, 255, 0.8);">cloud_upload</span>
                     </div>
                     <h3 style="font-size: 1.25rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem;">Initialize Canvas</h3>
                     <p style="color: #a7abb2; font-size: 0.875rem; max-width: 24rem; margin-bottom: 1.5rem; opacity: 0.6;">Upload a CSV or Excel asset in the sidebar to populate the engine cluster cluster pipeline diagnostics.</p>
                 </div>
                 """, 
                 unsafe_allow_html=True
             )

    # ---------------- Cleaning Section ----------------
    elif current_section == "Cleaning":
        section_header("Core Clean Intelligence", "Insights into dataframe sanitization metrics.")
        
        if st.session_state.clean_df is None:
             st.markdown(
                 """
                 <div class="glass-panel" style="border-radius: 1rem; padding: 3rem; text-align: center; border: 1px dashed rgba(129, 236, 255, 0.1);">
                     <span class="material-symbols-outlined" style="font-size: 2.5rem; color: rgba(167, 171, 178, 0.4); margin-bottom: 0.75rem;">lock</span>
                     <p style="font-size: 0.875rem; font-weight: 700; color: #white; margin-bottom: 0.25rem;">Node Empty</p>
                     <p style="color: #a7abb2; font-size: 0.75rem; opacity: 0.7;">Upload data asset to enable cleaning diagnostics reports filters dashboard diagnostics.</p>
                 </div>
                 """, unsafe_allow_html=True
             )
        else:
             report = st.session_state.cleaning_report
             if report is not None:
                  st.markdown(glass_card_container("Sanitization Summary", description="Impact statement post-isolation check."), unsafe_allow_html=True)
                  c1, c2, c3, c4 = st.columns(4)
                  with c1: list_item_card("Row Deltas", f"{report.rows_before} → {report.rows_after}", "swap_vert")
                  with c2: list_item_card("Col Deltas", f"{report.cols_before} → {report.cols_after}", "view_column")
                  with c3: list_item_card("Imputes", f"{len(report.imputed_columns)} columns", "build")
                  with c4: list_item_card("Outliers isolated", f"{report.dropped_rows} dropped", "dangerous", status_color="error")
                  st.markdown(close_glass_card(), unsafe_allow_html=True)
                  st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

             c1, c2 = st.columns([2, 1])
             with c1:
                  st.markdown(glass_card_container("Sparsity Matrix", icon="grid_on", description="Check column density nodes."), unsafe_allow_html=True)
                  fig_missing = missing_heatmap(real_df)
                  st.plotly_chart(apply_luminal_theme(fig_missing), use_container_width=True)
                  st.markdown(close_glass_card(), unsafe_allow_html=True)
             with c2:
                  st.markdown(glass_card_container("Schema Breakdown", icon="schema"), unsafe_allow_html=True)
                  st.markdown(f"""
                  <div style="display: flex; flex-direction: column; gap: 1rem; padding-top: 0.5rem;">
                      <div style="display: flex; justify-content: space-between; font-size: 0.75rem;"><span style="color: #a7abb2;">Numerical node density</span><span style="color: #fff; font-weight: bold;">{len(profile.numerical_columns) if profile else 0}</span></div>
                      <div style="display: flex; justify-content: space-between; font-size: 0.75rem;"><span style="color: #a7abb2;">Categorical node density</span><span style="color: #fff; font-weight: bold;">{len(profile.categorical_columns) if profile else 0}</span></div>
                  </div>
                  """, unsafe_allow_html=True)
                  st.markdown(close_glass_card(), unsafe_allow_html=True)

             st.markdown('<div style="height: 1.5rem;"></div>', unsafe_allow_html=True)
             st.markdown(glass_card_container("Data Sampling Controls", icon="tune", description="Reduce dataframe size for faster prototyping."), unsafe_allow_html=True)
             
             col_t, col_f = st.columns([1, 2])
             with col_t:
                 enable_sampling = st.toggle("Enable Sampling", value=st.session_state.get('sampling_enabled', False))
                 
             with col_f:
                 if enable_sampling:
                      curr_df = st.session_state.clean_df
                      max_rows = len(curr_df)
                      
                      c_s1, c_s2 = st.columns(2)
                      with c_s1:
                           sample_method = st.selectbox("Sampling Method", ["Random", "Stratified", "Time-based"])
                      with c_s2:
                           n_rows = st.number_input("Target Rows", min_value=50, max_value=max(50, max_rows), value=min(5000, max_rows), step=100)
                           
                      target_col = "None"
                      if sample_method == "Stratified":
                           cat_cols = curr_df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
                           target_col = st.selectbox("Target Column for Stratification", ["None"] + cat_cols)
                      
                      time_col = "None"
                      if sample_method == "Time-based":
                           time_cols = curr_df.select_dtypes(include=['datetime', 'datetimetz', 'datetime64[ns]']).columns.tolist()
                           time_col = st.selectbox("Time Column", ["None"] + time_cols)
                           
                      if st.button("Apply Reduction", use_container_width=True, type="primary"):
                           with st.spinner("Downsampling dataset..."):
                                st.session_state.sampling_enabled = True
                                if sample_method == "Stratified" and target_col != "None":
                                     try:
                                          from sklearn.model_selection import train_test_split
                                          test_size = n_rows / max_rows
                                          if test_size < 1.0:
                                              _, st.session_state.reduced_df = train_test_split(curr_df, test_size=test_size, stratify=curr_df[target_col], random_state=42)
                                          else:
                                              st.session_state.reduced_df = curr_df.copy()
                                     except Exception:
                                          st.session_state.reduced_df = curr_df.sample(n=min(n_rows, max_rows), random_state=42)
                                elif sample_method == "Time-based" and time_col != "None":
                                     st.session_state.reduced_df = curr_df.sort_values(time_col).tail(n_rows)
                                else:
                                     st.session_state.reduced_df = curr_df.sample(n=min(n_rows, max_rows), random_state=42)
                                     
                                st.session_state.synthetic_df = None
                                st.session_state.evaluation_df = None
                                st.rerun()
                 else:
                      if st.session_state.get('sampling_enabled'):
                           st.session_state.sampling_enabled = False
                           st.session_state.reduced_df = None
                           st.session_state.synthetic_df = None
                           st.session_state.evaluation_df = None
                           st.rerun()
                           
             if st.session_state.get('sampling_enabled') and st.session_state.get('reduced_df') is not None:
                 red_df = st.session_state.reduced_df
                 orig_df = st.session_state.clean_df
                 orig_len = len(orig_df)
                 red_len = len(red_df)
                 pct = (red_len / max(1, orig_len)) * 100
                 
                 st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                 st.success(f"Reduced dataset from {orig_len:,} rows to {red_len:,} rows ({pct:.1f}%).")
                 if red_len < 100:
                     st.warning("Datasets smaller than 100 rows may reduce synthetic data quality significantly.")
                 
                 c1, c2, c3 = st.columns(3)
                 with c1: list_item_card("Rows", f"{orig_len:,} → {red_len:,}", "table_rows")
                 with c2: list_item_card("Columns", f"{orig_df.shape[1]} → {red_df.shape[1]}", "view_column")
                 orig_miss = orig_df.isna().sum().sum() / max(1, orig_df.size) * 100
                 red_miss = red_df.isna().sum().sum() / max(1, red_df.size) * 100
                 with c3: list_item_card("Missing %", f"{orig_miss:.1f}% → {red_miss:.1f}%", "analytics")
                 
                 st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                 numeric_cols = red_df.select_dtypes(include=['number']).columns.tolist()
                 if numeric_cols:
                      samp_col = st.selectbox("Sample Distribution Check Node", numeric_cols, key="samp_check")
                      fig_dist = distribution_comparison(orig_df, red_df, samp_col)
                      if fig_dist:
                           fig_dist.layout.title.text = f"Distribution: Original vs Sampled"
                           fig_dist.data[0].name = "Original"
                           fig_dist.data[1].name = "Sampled"
                           st.plotly_chart(apply_luminal_theme(fig_dist), use_container_width=True)
             
             st.markdown(close_glass_card(), unsafe_allow_html=True)

    # ---------------- Synthesis Section ----------------
    elif current_section == "Synthesis":
        section_header("Engine Controls", "Adjust node capacity limits for model execution.")
        
        if st.session_state.clean_df is None:
             st.markdown(
                 """
                 <div class="glass-panel" style="border-radius: 1rem; padding: 3rem; text-align: center; border: 1px dashed rgba(129, 236, 255, 0.1);">
                     <span class="material-symbols-outlined" style="font-size: 2.5rem; color: rgba(167, 171, 178, 0.4); margin-bottom: 0.75rem;">lock</span>
                     <p style="font-size: 0.875rem; font-weight: 700; color: #white; margin-bottom: 0.25rem;">Node Empty</p>
                     <p style="color: #a7abb2; font-size: 0.75rem; opacity: 0.7;">Upload data asset to enable model selectors pipelines configurations filters.</p>
                 </div>
                 """, unsafe_allow_html=True
             )
        else:
             st.markdown(glass_card_container("Configuration Panel", icon="settings_suggest"), unsafe_allow_html=True)
             c1, c2 = st.columns(2)
             with c1:
                 mode = st.radio("Optimization Mode", ["AUTO", "MANUAL"], horizontal=True)
                 all_cols = real_df.columns.tolist()
                 target_col = st.selectbox("Target Node (Labels)", ["None"] + all_cols)
                 time_col = st.selectbox("Frequency Node (Timestamp)", ["None"] + all_cols)
                 
                 target_value = None if target_col == "None" else target_col
                 time_value = None if time_col == "None" else time_col

             with c2:
                 recommendation = recommend_model(real_df, target_col=target_value, time_col=time_value)
                 selected_model = recommendation.model
                 default_epochs = 15 if len(real_df) < 1000 else 30 if len(real_df) < 5000 else 60
                 epochs = default_epochs
                 min_rows = max(10, len(real_df))
                 optimized_default = max(min_rows, min(len(real_df) * 3, 1000))
                 sample_size = optimized_default
                 
                 if mode == "AUTO":
                      st.markdown(f'<div style="padding: 0.75rem; background: rgba(129, 236, 255, 0.05); border: 1px solid rgba(129, 236, 255, 0.1); border-radius: 0.5rem; font-size: 0.75rem; margin-top: 1rem; color: #81ecff;"><span style="font-weight: bold;">Recommendation:</span> {recommendation.model}<br/><span style="opacity: 0.7;">{recommendation.reason}</span></div>', unsafe_allow_html=True)
                 else:
                      selected_model = st.selectbox("Model Unit", ["CTGAN", "TVAE", "GaussianCopula", "SMOTE", "TimeGAN"])
                      epochs = st.slider("Epoch Processing Cycle", min_value=5, max_value=200, value=default_epochs, step=5)
                      sample_size = st.number_input("Density Size (Sample count)", min_value=10, max_value=max(1000, len(real_df)*10), value=optimized_default, step=10)

             st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
             remote_url = st.text_input(
                 "Remote Worker URL (optional)",
                 value=st.session_state.get("remote_worker_url", ""),
                 placeholder="https://<public-colab-url>",
                 help="If set, heavy generation runs on remote worker (e.g., Google Colab).",
             ).strip()
             st.session_state.remote_worker_url = remote_url
             if remote_url:
                 st.caption("Remote worker enabled: synthesis/evaluation compute will be offloaded.")

             st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
             run = st.button("Generate Synthetic Cluster", type="primary", use_container_width=True)
             st.markdown(close_glass_card(), unsafe_allow_html=True)

             if run:
                 progress = st.progress(0)
                 status = st.empty()
                 try:
                     status.markdown('<p style="color: #81ecff; font-size: 0.75rem;">Validating cluster configs...</p>', unsafe_allow_html=True)
                     progress.progress(15)
                     time.sleep(0.1)

                     status.markdown('<p style="color: #81ecff; font-size: 0.75rem;">Propagating sub-graphs & weights...</p>', unsafe_allow_html=True)
                     progress.progress(55)
                     
                     if remote_url:
                         remote_result = run_remote_generation(
                             df=real_df,
                             selected_model=selected_model,
                             sample_size=int(sample_size),
                             epochs=int(epochs),
                             target_col=target_value,
                             time_col=time_value,
                             worker_url=remote_url,
                         )
                         synthetic_df, _ = clean_dataset(remote_result.synthetic_df, fill_missing=True)
                         st.session_state.synthetic_df = synthetic_df
                         st.session_state.last_model_used = remote_result.model_used
                         st.session_state.evaluation_df = (
                             remote_result.evaluation_df
                             if remote_result.evaluation_df is not None
                             else build_evaluation_report(real_df, synthetic_df)
                         )
                     else:
                         result = generate_with_fallback(
                             df=real_df,
                             selected_model=selected_model,
                             sample_size=int(sample_size),
                             epochs=int(epochs),
                             target_col=target_value,
                             time_col=time_value,
                         )

                         synthetic_df, _ = clean_dataset(result.synthetic_df, fill_missing=True)
                         st.session_state.synthetic_df = synthetic_df
                         st.session_state.last_model_used = result.model_used
                         st.session_state.evaluation_df = build_evaluation_report(real_df, synthetic_df)

                     progress.progress(100)
                     status.success(f"Cluster populated using {result.model_used}.")
                     time.sleep(0.5)
                     st.session_state.nav_index = 3 # Navigate to Evaluation
                     st.rerun()

                 except Exception as exc:
                     st.error(f"Execution Aborted: {exc}")

             synth = st.session_state.synthetic_df
             if synth is not None:
                  st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)
                  st.markdown(glass_card_container("Synthetic Preview", icon="table_view"), unsafe_allow_html=True)
                  st.dataframe(synth.head(10), use_container_width=True)
                  st.download_button("📥 Download Asset", data=synth.to_csv(index=False).encode("utf-8"), file_name=f"synthetic_{st.session_state.last_model_used}.csv", mime="text/csv", use_container_width=True)
                  st.markdown(close_glass_card(), unsafe_allow_html=True)

    # ---------------- Evaluation Section ----------------
    elif current_section == "Evaluation":
        section_header("Analytics Diagnostics", "Evaluating synthetic cluster weight distribution overlap matrix filters layer diagnostics configurations.")
        
        if st.session_state.clean_df is None:
             st.markdown(
                 """
                 <div class="glass-panel" style="border-radius: 1rem; padding: 3rem; text-align: center; border: 1px dashed rgba(129, 236, 255, 0.1);">
                     <span class="material-symbols-outlined" style="font-size: 2.5rem; color: rgba(167, 171, 178, 0.4); margin-bottom: 0.75rem;">lock</span>
                     <p style="font-size: 0.875rem; font-weight: 700; color: #white; margin-bottom: 0.25rem;">Node Empty</p>
                     <p style="color: #a7abb2; font-size: 0.75rem; opacity: 0.7;">Upload data asset and execute Synthesis to enable evaluation visuals metrics diagnostics dashboards grids filters.</p>
                 </div>
                 """, unsafe_allow_html=True
             )
        else:
             synth = st.session_state.synthetic_df
             if synth is None:
                  st.markdown(
                      """
                      <div class="glass-panel" style="border-radius: 1rem; padding: 3rem; text-align: center; border: 1px dashed rgba(129, 236, 255, 0.1);">
                          <span class="material-symbols-outlined" style="font-size: 2.5rem; color: rgba(167, 171, 178, 0.4); margin-bottom: 0.75rem;">query_stats</span>
                          <p style="font-size: 0.875rem; font-weight: 700; color: #white; margin-bottom: 0.25rem;">Synthesis Required</p>
                          <p style="color: #a7abb2; font-size: 0.75rem; opacity: 0.7;">Generate synthetic data first to unlock distribution overlap verified diagnostics grids reporting filters layouts nodes diagnostics.</p>
                      </div>
                      """, unsafe_allow_html=True
                  )
             else:
                  tabs = st.tabs(["Overview", "Statistics", "Distributions", "Correlation", "Quality Report"])
                  
                  with tabs[0]:
                      st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                      c1, c2 = st.columns(2)
                      with c1:
                          st.markdown(glass_card_container("Original Dataset Overview", icon="table_chart"), unsafe_allow_html=True)
                          st.markdown(f"""
                          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Rows</span><span style="color: #fff; font-weight: bold;">{len(real_df):,}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Columns</span><span style="color: #fff; font-weight: bold;">{real_df.shape[1]}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Memory Usage</span><span style="color: #fff; font-weight: bold;">{real_df.memory_usage(deep=True).sum() / 1024:.1f} KB</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Numerical Columns</span><span style="color: #fff; font-weight: bold;">{len(real_df.select_dtypes(include=['number']).columns)}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Categorical Columns</span><span style="color: #fff; font-weight: bold;">{len(real_df.select_dtypes(include=['object', 'category']).columns)}</span></div>
                          </div>
                          """, unsafe_allow_html=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)
                      with c2:
                          st.markdown(glass_card_container("Synthetic Dataset Overview", icon="blur_on"), unsafe_allow_html=True)
                          st.markdown(f"""
                          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Rows</span><span style="color: #fff; font-weight: bold;">{len(synth):,}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Columns</span><span style="color: #fff; font-weight: bold;">{synth.shape[1]}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Memory Usage</span><span style="color: #fff; font-weight: bold;">{synth.memory_usage(deep=True).sum() / 1024:.1f} KB</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Numerical Columns</span><span style="color: #fff; font-weight: bold;">{len(synth.select_dtypes(include=['number']).columns)}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Categorical Columns</span><span style="color: #fff; font-weight: bold;">{len(synth.select_dtypes(include=['object', 'category']).columns)}</span></div>
                          </div>
                          """, unsafe_allow_html=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)

                  with tabs[1]:
                      st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                      c1, c2 = st.columns(2)
                      with c1:
                          st.markdown(glass_card_container("Original Numerical Statistics", icon="query_stats"), unsafe_allow_html=True)
                          st.dataframe(real_df.describe().transpose(), use_container_width=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)
                      with c2:
                          st.markdown(glass_card_container("Synthetic Numerical Statistics", icon="query_stats"), unsafe_allow_html=True)
                          st.dataframe(synth.describe().transpose(), use_container_width=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)

                  with tabs[2]:
                      st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                      numeric_overlap = [c for c in real_df.select_dtypes(include=["number"]).columns if c in synth.columns]
                      if numeric_overlap:
                          col_pick = st.selectbox("Feature Overlap Node", numeric_overlap, key="eval_dist_pick")
                          fig_dist = distribution_comparison(real_df, synth, col_pick)
                          if fig_dist:
                              st.plotly_chart(apply_luminal_theme(fig_dist), use_container_width=True)
                      else:
                          st.info("No numeric Node Overlaps.")

                  with tabs[3]:
                      st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                      c1, c2 = st.columns(2)
                      with c1:
                          fig_c1 = correlation_heatmap(real_df, title="Real Matrix")
                          if fig_c1: st.plotly_chart(apply_luminal_theme(fig_c1), use_container_width=True)
                      with c2:
                          fig_c2 = correlation_heatmap(synth, title="Synthetic Matrix")
                          if fig_c2: st.plotly_chart(apply_luminal_theme(fig_c2), use_container_width=True)

                  with tabs[4]:
                      st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
                      c1, c2 = st.columns(2)
                      with c1:
                          st.markdown(glass_card_container("Original Quality Insights", icon="verified"), unsafe_allow_html=True)
                          missing_total = real_df.isna().sum().sum()
                          dup_count = real_df.duplicated().sum()
                          st.markdown(f"""
                          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Total Missing Cells</span><span style="color: #fff; font-weight: bold;">{missing_total:,}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Duplicate Rows</span><span style="color: #fff; font-weight: bold;">{dup_count:,}</span></div>
                          </div>
                          """, unsafe_allow_html=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)
                      with c2:
                          st.markdown(glass_card_container("Synthetic Quality Insights", icon="verified"), unsafe_allow_html=True)
                          missing_total_s = synth.isna().sum().sum()
                          dup_count_s = synth.duplicated().sum()
                          st.markdown(f"""
                          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Total Missing Cells</span><span style="color: #fff; font-weight: bold;">{missing_total_s:,}</span></div>
                              <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;"><span style="color: #a7abb2;">Duplicate Rows</span><span style="color: #fff; font-weight: bold;">{dup_count_s:,}</span></div>
                          </div>
                          """, unsafe_allow_html=True)
                          st.markdown(close_glass_card(), unsafe_allow_html=True)

                  if st.session_state.evaluation_df is not None:
                       st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)
                       st.download_button("📥 Diagnostics Report", data=st.session_state.evaluation_df.to_csv(index=False).encode('utf-8'), file_name="evaluation_report.csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
