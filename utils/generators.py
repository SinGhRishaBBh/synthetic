import pandas as pd
import numpy as np

# SDV Imports (Robust Imports handling)
from sdv.metadata import SingleTableMetadata
from sdv.single_table import CTGANSynthesizer, TVAESynthesizer, GaussianCopulaSynthesizer

try:
    from sdv.sequential import PARSynthesizer
except ImportError:
    PARSynthesizer = None

from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import LabelEncoder

def _canonical_model_type(model_type: str) -> str:
    mapping = {
        "TimeGAN": "Sequential",
        "TimeGAN / Sequential": "Sequential",
    }
    return mapping.get(model_type, model_type)


def train_sdv_model(df: pd.DataFrame, model_type: str, epochs: int = 10, time_col: str = None):
    """
    Trains an SDV Model for CTGAN, TVAE, GaussianCopula, or PAR (Sequential).
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Training dataset is empty or invalid.")

    model_type = _canonical_model_type(model_type)

    try:
        # 1. Initialize Metadata
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(df)

        # 2. Sequential/PAR Setup If requested
        if model_type == 'TimeGAN' or model_type == 'Sequential':
            if PARSynthesizer is None:
                raise ImportError("PARSynthesizer could not be loaded from sdv.sequential.")
            
            # PAR takes metadata as fit target
            synthesizer = PARSynthesizer(metadata)
            # You usually specify sequential parameters, but let's train standard
            synthesizer.fit(df)
            return synthesizer

        # 3. Choose Tabular model
        if model_type == 'CTGAN':
            synthesizer = CTGANSynthesizer(metadata, epochs=epochs)
        elif model_type == 'TVAESynthesizer':
            synthesizer = TVAESynthesizer(metadata, epochs=epochs)
        else:  # Gaussian Copula
            synthesizer = GaussianCopulaSynthesizer(metadata)

        # Progress bars are managed in the UI layer, let's just do the fit
        synthesizer.fit(df)
        return synthesizer

    except Exception as e:
        raise ValueError(f"Generation Failed for {model_type}. Reason: {str(e)}")


def generate_smote(df: pd.DataFrame, target_col: str, num_samples: int = 1000) -> pd.DataFrame:
    """
    Generates synthetic balanced rows using SMOTE for classification targets.
    Note: SMOTE works best with numerical vectors, so categoricals are label encoded.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("Input dataframe is empty or invalid for SMOTE.")

    if target_col is None:
        raise ValueError("SMOTE requires target_col but got None.")

    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset for SMOTE.")

    X = df.drop(columns=[target_col]).copy()
    y = df[target_col].copy()

    if X.empty:
        raise ValueError("SMOTE requires at least one feature column besides target.")

    # Step 1: Clean target and validate class count
    y = y.fillna("__missing_target__")
    class_counts = y.value_counts(dropna=False)
    if class_counts.shape[0] < 2:
        raise ValueError("SMOTE requires at least two target classes.")

    # Step 2: Fill missing values column-by-column
    for col in X.columns:
        if pd.api.types.is_numeric_dtype(X[col]):
            fill_value = X[col].median()
            if pd.isna(fill_value):
                fill_value = 0
        else:
            mode = X[col].mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else "__missing__"
        X[col] = X[col].fillna(fill_value)

    # Step 3: Encode Categoricals
    cat_cols = X.select_dtypes(include=['object', 'category', 'bool', 'string']).columns.tolist()
    encoders = {}

    for col in cat_cols:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le

    # Step 4: Fit SMOTE with dynamic k_neighbors based on minority class size
    min_class_count = int(class_counts.min())
    if min_class_count < 2:
        raise ValueError("SMOTE requires at least 2 samples in each class after cleaning target values.")

    k_neighbors = min(5, min_class_count - 1)
    try:
        sm = SMOTE(random_state=42, k_neighbors=k_neighbors)
        X_resampled, y_resampled = sm.fit_resample(X, y)
    except Exception as e:
        raise ValueError(f"SMOTE fit failed: {str(e)}")

    # Step 5: Reconstitute DataFrame
    synthetic_df = pd.DataFrame(X_resampled, columns=X.columns)
    synthetic_df[target_col] = y_resampled

    # Step 6: Decode back categorical columns
    for col, le in encoders.items():
        max_idx = len(le.classes_) - 1
        synthetic_df[col] = synthetic_df[col].round().clip(lower=0, upper=max_idx).astype(int)
        synthetic_df[col] = le.inverse_transform(synthetic_df[col])

    if synthetic_df.empty:
        raise ValueError("SMOTE returned no rows.")

    sample_size = min(num_samples, len(synthetic_df))
    return synthetic_df.sample(sample_size, replace=False, random_state=42).reset_index(drop=True)
