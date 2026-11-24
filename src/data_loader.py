"""
AGRI-2: Weather Data Ingestion and Validation Pipeline
Loads, sanitizes, and validates agro-meteorological CSV datasets from local storage,
sample scenarios, or user uploads.
"""

from typing import Tuple, List, Optional, Union
from pathlib import Path
import io
import pandas as pd
import numpy as np


REQUIRED_COLUMNS = ["date", "tmax", "tmin"]
OPTIONAL_COLUMNS = [
    "tmean", "rh_max", "rh_min", "rh_mean",
    "wind_speed_2m", "solar_rad_mj", "rainfall_mm", "pressure_kpa"
]


def load_and_validate_weather_csv(
    source: Union[str, Path, io.BytesIO, io.StringIO, pd.DataFrame]
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Loads and rigorously validates an agro-meteorological CSV dataset or DataFrame.

    Validation rules:
    - Must contain columns: date, tmax, tmin.
    - Dates parsed to YYYY-MM-DD.
    - Tmax >= Tmin checked.
    - Missing Tmean calculated as (Tmax + Tmin) / 2.
    - Humidity bounded to [0, 100].
    - Rainfall clamped to >= 0.
    - Wind speed clamped to >= 0.

    Returns:
        tuple: (validated_df, warning_messages_list)
    """
    warnings: List[str] = []

    try:
        if isinstance(source, pd.DataFrame):
            df = source.copy()
        elif isinstance(source, (str, Path)):
            df = pd.read_csv(source)
        else:
            df = pd.read_csv(source)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")

    # Normalize column names to lowercase stripped
    df.columns = [c.strip().lower() for c in df.columns]

    # Verify required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing mandatory columns: {missing}. Required: {REQUIRED_COLUMNS}")

    # Parse and sort by date
    try:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        raise ValueError(f"Invalid date format in dataset: {str(e)}")

    # Ensure numeric types
    for col in ["tmax", "tmin"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isnull().any():
            raise ValueError(f"Column '{col}' contains NaN or unparseable numeric values.")

    # Sanity check: Tmax >= Tmin
    inverted_mask = df["tmax"] < df["tmin"]
    if inverted_mask.any():
        warnings.append(f"Fixed {inverted_mask.sum()} records where Tmax < Tmin by swapping values.")
        df.loc[inverted_mask, ["tmax", "tmin"]] = df.loc[inverted_mask, ["tmin", "tmax"]].values

    # Compute tmean if missing
    if "tmean" not in df.columns or df["tmean"].isnull().any():
        df["tmean"] = (df["tmax"] + df["tmin"]) / 2.0

    # Ensure optional columns have safe defaults
    if "rainfall_mm" not in df.columns:
        df["rainfall_mm"] = 0.0
    else:
        df["rainfall_mm"] = pd.to_numeric(df["rainfall_mm"], errors="coerce").fillna(0.0).clip(lower=0.0)

    if "wind_speed_2m" not in df.columns:
        df["wind_speed_2m"] = 2.0
    else:
        df["wind_speed_2m"] = pd.to_numeric(df["wind_speed_2m"], errors="coerce").fillna(2.0).clip(lower=0.1)

    if "solar_rad_mj" not in df.columns:
        df["solar_rad_mj"] = np.nan
    else:
        df["solar_rad_mj"] = pd.to_numeric(df["solar_rad_mj"], errors="coerce").clip(lower=0.0)

    # Relative humidity checks
    for rh_col in ["rh_max", "rh_min", "rh_mean"]:
        if rh_col in df.columns:
            df[rh_col] = pd.to_numeric(df[rh_col], errors="coerce").clip(0.0, 100.0)

    return df, warnings
