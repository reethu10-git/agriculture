"""
AGRI-2: NASA POWER Daily Agroclimatology Historical Integration Engine
Fetches, stores, and standardizes historical daily meteorological observations
from NASA's Prediction Of Worldwide Energy Resources (POWER) API.
Stores raw JSON in data/raw/nasa_power/ and standardized CSVs in data/processed/.
"""

from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import logging
import requests
import pandas as pd
import numpy as np

from config.settings import DEFAULT_LOCATION, DATA_DIR, IS_VERCEL
from src.data_loader import load_and_validate_weather_csv

logger = logging.getLogger("agri2.nasa_power")

if IS_VERCEL:
    NASA_POWER_RAW_DIR = Path("/tmp/nasa_power")
    PROCESSED_DATA_DIR = Path("/tmp/processed")
else:
    NASA_POWER_RAW_DIR = DATA_DIR / "raw" / "nasa_power"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"

for _dir in (NASA_POWER_RAW_DIR, PROCESSED_DATA_DIR):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Unable to create NASA POWER directory %s: %s", _dir, exc)


def parse_nasa_power_response(raw_json: Dict[str, Any]) -> pd.DataFrame:
    """
    Parses raw NASA POWER daily JSON response into a standardized DataFrame.
    Replaces NASA POWER missing value sentinel (-999 or -999.0) with appropriate physical defaults.
    """
    properties = raw_json.get("properties", {})
    parameters = properties.get("parameter", {})

    tmax_dict = parameters.get("T2M_MAX", {})
    tmin_dict = parameters.get("T2M_MIN", {})
    tmean_dict = parameters.get("T2M", {})
    rh_dict = parameters.get("RH2M", {})
    wind_dict = parameters.get("WS2M", {})
    solar_dict = parameters.get("ALLSKY_SFC_SW_DWN", {})
    rain_dict = parameters.get("PRECTOTCORR", {})
    pressure_dict = parameters.get("PS", {})

    dates_raw = sorted(list(tmax_dict.keys()))
    records = []

    for d_str in dates_raw:
        # Date string format is YYYYMMDD
        date_iso = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"

        def clean_val(val, default_val=0.0):
            if val is None or val <= -900:
                return default_val
            return float(val)

        tmax = clean_val(tmax_dict.get(d_str), 30.0)
        tmin = clean_val(tmin_dict.get(d_str), 22.0)
        tmean = clean_val(tmean_dict.get(d_str), (tmax + tmin) / 2.0)
        rh_mean = clean_val(rh_dict.get(d_str), 70.0)
        wind2m = clean_val(wind_dict.get(d_str), 2.0)
        solar = clean_val(solar_dict.get(d_str), 18.0)
        rain = clean_val(rain_dict.get(d_str), 0.0)
        pressure = clean_val(pressure_dict.get(d_str), 96.8)

        # Estimate diurnal RH bounds if not separate
        rh_max = min(100.0, rh_mean + 15.0)
        rh_min = max(20.0, rh_mean - 15.0)

        records.append({
            "date": date_iso,
            "tmax": round(tmax, 2),
            "tmin": round(tmin, 2),
            "tmean": round(tmean, 2),
            "rh_max": round(rh_max, 1),
            "rh_min": round(rh_min, 1),
            "rh_mean": round(rh_mean, 1),
            "wind_speed_2m": round(wind2m, 2),
            "solar_rad_mj": round(solar, 2),
            "rainfall_mm": round(rain, 2),
            "pressure_kpa": round(pressure, 2)
        })

    df = pd.DataFrame(records)
    return df


def fetch_nasa_power_historical(
    start_date: str = "20261001",
    end_date: str = "20261007",
    latitude: float = DEFAULT_LOCATION["latitude"],
    longitude: float = DEFAULT_LOCATION["longitude"],
    timeout: float = 15.0,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetches historical daily agroclimatology data from NASA POWER API.
    Saves raw payload to data/raw/nasa_power/ and standardized CSV to data/processed/.

    Args:
        start_date: Format YYYYMMDD
        end_date: Format YYYYMMDD
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        timeout: Network timeout in seconds
        force_refresh: If True, bypasses local disk cache

    Returns:
        dict: Standardized DataFrame, metadata provenance, and storage paths.
    """
    clean_start = start_date.replace("-", "")
    clean_end = end_date.replace("-", "")

    raw_filename = f"nasa_power_raw_{latitude:.4f}_{longitude:.4f}_{clean_start}_{clean_end}.json"
    raw_path = NASA_POWER_RAW_DIR / raw_filename

    processed_filename = f"nasa_power_standardized_{latitude:.4f}_{longitude:.4f}_{clean_start}_{clean_end}.csv"
    processed_path = PROCESSED_DATA_DIR / processed_filename

    meta_filename = f"nasa_power_meta_{latitude:.4f}_{longitude:.4f}_{clean_start}_{clean_end}.json"
    meta_path = PROCESSED_DATA_DIR / meta_filename

    retrieval_timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Check local cache
    if not force_refresh and raw_path.exists() and processed_path.exists():
        try:
            df, warnings = load_and_validate_weather_csv(processed_path)
            meta = {}
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            return {
                "success": True,
                "dataframe": df,
                "metadata": meta,
                "source_label": f"Historical Weather – NASA POWER (Cached: {clean_start} to {clean_end})",
                "provenance_status": "HISTORICAL_OBSERVATION_REANALYSIS",
                "raw_file": str(raw_path),
                "processed_file": str(processed_path),
                "error": None
            }
        except Exception:
            pass

    # 2. Query NASA POWER API
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M_MAX,T2M_MIN,T2M,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": clean_start,
        "end": clean_end,
        "format": "JSON"
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        raw_json = response.json()

        # Save raw JSON
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_json, f, indent=2)

        # Standardize DataFrame
        df = parse_nasa_power_response(raw_json)
        df, _ = load_and_validate_weather_csv(df)

        # Save standardized CSV
        df.to_csv(processed_path, index=False)

        # Record Provenance Metadata
        metadata = {
            "source": "NASA Prediction Of Worldwide Energy Resources (POWER) Daily API",
            "source_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
            "download_date_utc": retrieval_timestamp,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "date_range": {
                "start_date": f"{clean_start[:4]}-{clean_start[4:6]}-{clean_start[6:]}",
                "end_date": f"{clean_end[:4]}-{clean_end[4:6]}-{clean_end[6:]}"
            },
            "parameters": {
                "T2M_MAX": {"name": "Maximum Temperature at 2m", "units": "°C"},
                "T2M_MIN": {"name": "Minimum Temperature at 2m", "units": "°C"},
                "T2M": {"name": "Mean Temperature at 2m", "units": "°C"},
                "RH2M": {"name": "Relative Humidity at 2m", "units": "%"},
                "WS2M": {"name": "Wind Speed at 2m", "units": "m/s"},
                "ALLSKY_SFC_SW_DWN": {"name": "All-Sky Solar Radiation", "units": "MJ/m^2/day"},
                "PRECTOTCORR": {"name": "Precipitation Corrected", "units": "mm/day"},
                "PS": {"name": "Surface Atmospheric Pressure", "units": "kPa"}
            },
            "data_category": "Historical Observation / Satellite Reanalysis",
            "disclaimer": "Historical observations. Strictly NOT a future live weather forecast."
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "success": True,
            "dataframe": df,
            "metadata": metadata,
            "source_label": f"Historical Weather – NASA POWER ({clean_start} to {clean_end})",
            "provenance_status": "HISTORICAL_OBSERVATION_REANALYSIS",
            "raw_file": str(raw_path),
            "processed_file": str(processed_path),
            "error": None
        }

    except Exception as e:
        # If API is unreachable or times out, try loading existing local 30-day sample as fallback
        sample_path = DATA_DIR / "sample" / "coimbatore_historical_30day.csv"
        if sample_path.exists():
            df_fallback, _ = load_and_validate_weather_csv(sample_path)
            df_slice = df_fallback.head(7)
            return {
                "success": False,
                "dataframe": df_slice,
                "metadata": {
                    "source": "NASA POWER / TNAU Climatology (Local Historical Archive)",
                    "download_date_utc": retrieval_timestamp,
                    "coordinates": {"latitude": latitude, "longitude": longitude},
                    "note": f"Online query failed ({str(e)}). Loaded verified local historical archive."
                },
                "source_label": "Historical Weather – NASA POWER (Local Historical Archive)",
                "provenance_status": "HISTORICAL_OBSERVATION_REANALYSIS",
                "raw_file": None,
                "processed_file": str(sample_path),
                "error": f"NASA POWER API request failed: {str(e)}. Used local historical archive."
            }
        else:
            return {
                "success": False,
                "dataframe": None,
                "metadata": None,
                "source_label": "NASA POWER Request Failed",
                "provenance_status": "API_ERROR",
                "raw_file": None,
                "processed_file": None,
                "error": f"NASA POWER API failed: {str(e)}"
            }
