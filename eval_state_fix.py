import sys
import os
import pandas as pd
from sdv.metadata import SingleTableMetadata

# Direct node triggers benchmarks loads diagnostics
import streamlit as st

def mock_synthesis_flow():
    # 1. Setup session state
    st.session_state.clean_df = pd.DataFrame({'A': [1,2,3], 'B': [4,5,6]})
    st.session_state.synthetic_df = pd.DataFrame({'A': [1,2,2], 'B': [4,4,5]})
    st.session_state.diagnostics = "Mock diagnostics"
    
    # 2. Evaluation dashboard trigger simulation
    from modules.evaluator import build_evaluation_report
    st.session_state.evaluation_df = build_evaluation_report(st.session_state.clean_df, st.session_state.synthetic_df)
    print("Evaluation DF built successfully.")
    print(st.session_state.evaluation_df)

if __name__ == "__main__":
    if 'clean_df' not in st.session_state:
         class MockState(dict):
              def __getattr__(self, name): return self.get(name)
              def __setattr__(self, name, val): self[name] = val
         st.session_state = MockState()
    mock_synthesis_flow()
