"""
AGRI-2: Weather Service Engine
Manages all external meteorological data ingestion pipelines:
1. Live 7-Day Forecast via Open-Meteo API (Asia/Kolkata timezone, raw variables, unit conversions)
2. Historical Weather via NASA POWER Daily API
3. Pre-packaged Historical Scenarios
4. Custom CSV ingestion and provenance tracking
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import requests
import pandas as pd
import numpy as np

from config.settings import DEFAULT_LOCATION, DATA_DIR
from src.eto_calculator import wind_speed_at_2m, atmospheric_pressure
from src.data_loader import load_and_validate_weather_csv
from src.nasa_power_service import fetch_nasa_power_historical


SAMPLE_DATASETS = {
    "Coimbatore Kharif Normal (7-Day Default)": DATA_DIR / "sample" / "coimbatore_7day_weather.csv",
    "Coimbatore Dry Spell Stress Test (7-Day)": DATA_DIR / "sample" / "coimbatore_dry_spell_7day.csv",
    "Coimbatore Heavy Monsoon Scenario (7-Day)": DATA_DIR / "sample" / "coimbatore_heavy_rain_7day.csv",
    "Coimbatore Historical Observations (30-Day)": DATA_DIR / "sample" / "coimbatore_historical_30day.csv"
}

# In-memory cache for live forecasts: {(lat, lon, tz): {"cached_at": datetime, "data": dict}}
_LIVE_FORECAST_CACHE: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def get_available_sample_datasets() -> Dict[str, Path]:
    """Returns mapping of human-readable dataset scenario names to file paths."""
    return SAMPLE_DATASETS


def load_sample_dataset(dataset_name: str) -> pd.DataFrame:
    """Loads a named sample scenario dataset."""
    path = SAMPLE_DATASETS.get(dataset_name, SAMPLE_DATASETS["Coimbatore Kharif Normal (7-Day Default)"])
    df, _ = load_and_validate_weather_csv(path)
    return df


def parse_openmeteo_daily_response(
    daily_data: Dict[str, Any],
    latitude: float,
    elevation_m: float = DEFAULT_LOCATION["elevation"]
) -> pd.DataFrame:
    """
    Parses Open-Meteo daily forecast dictionary into a standardized 7-day DataFrame.
    Performs physical unit conversions:
    - Wind speed: 10m max in km/h -> m/s -> adjusted to 2m height via logarithmic profile (FAO-56 Eq. 47)
    - Surface pressure: hPa -> kPa (/ 10.0)
    - Solar radiation: shortwave_radiation_sum (MJ/m^2)
    - Humidity: relative_humidity_2m_mean / max / min (%)
    - Temperature: temperature_2m_max / min / mean (°C)
    - Precipitation: precipitation_sum (mm)
    """
    dates = daily_data.get("time", [])[:7]
    tmax_raw = daily_data.get("temperature_2m_max", [])[:7]
    tmin_raw = daily_data.get("temperature_2m_min", [])[:7]
    tmean_raw = daily_data.get("temperature_2m_mean", [])[:7]
    rh_max_raw = daily_data.get("relative_humidity_2m_max", [])[:7]
    rh_min_raw = daily_data.get("relative_humidity_2m_min", [])[:7]
    rh_mean_raw = daily_data.get("relative_humidity_2m_mean", [])[:7]
    rain_raw = daily_data.get("precipitation_sum", [])[:7]
    wind10m_kmh_raw = daily_data.get("wind_speed_10m_max", [])[:7]
    solar_raw = daily_data.get("shortwave_radiation_sum", [])[:7]
    pressure_hpa_raw = daily_data.get("surface_pressure_mean", [])[:7]

    default_pressure_kpa = atmospheric_pressure(elevation_m)
    records = []

    for i in range(len(dates)):
        d_val = dates[i]

        # Temperature
        tmax = float(tmax_raw[i]) if i < len(tmax_raw) and tmax_raw[i] is not None else 31.0
        tmin = float(tmin_raw[i]) if i < len(tmin_raw) and tmin_raw[i] is not None else 22.0
        if i < len(tmean_raw) and tmean_raw[i] is not None:
            tmean = float(tmean_raw[i])
        else:
            tmean = (tmax + tmin) / 2.0

        # Humidity
        rh_max = float(rh_max_raw[i]) if i < len(rh_max_raw) and rh_max_raw[i] is not None else 85.0
        rh_min = float(rh_min_raw[i]) if i < len(rh_min_raw) and rh_min_raw[i] is not None else 50.0
        if i < len(rh_mean_raw) and rh_mean_raw[i] is not None:
            rh_mean = float(rh_mean_raw[i])
        else:
            rh_mean = (rh_max + rh_min) / 2.0

        # Rainfall
        rain = float(rain_raw[i]) if i < len(rain_raw) and rain_raw[i] is not None else 0.0
        rain = max(0.0, rain)

        # Wind speed: Convert km/h to m/s, then apply logarithmic height profile from 10m to 2m
        if i < len(wind10m_kmh_raw) and wind10m_kmh_raw[i] is not None:
            w_10m_ms = float(wind10m_kmh_raw[i]) / 3.6
            w_2m_ms = wind_speed_at_2m(w_10m_ms, z_m=10.0)
        else:
            w_2m_ms = 2.0

        # Solar radiation (MJ/m^2/day)
        if i < len(solar_raw) and solar_raw[i] is not None:
            sol_mj = float(solar_raw[i])
        else:
            sol_mj = 19.5

        # Surface pressure: hPa -> kPa
        if i < len(pressure_hpa_raw) and pressure_hpa_raw[i] is not None:
            p_kpa = float(pressure_hpa_raw[i]) / 10.0
        else:
            p_kpa = default_pressure_kpa

        records.append({
            "date": str(d_val)[:10],
            "tmax": round(tmax, 2),
            "tmin": round(tmin, 2),
            "tmean": round(tmean, 2),
            "rh_max": round(rh_max, 1),
            "rh_min": round(rh_min, 1),
            "rh_mean": round(rh_mean, 1),
            "wind_speed_2m": round(w_2m_ms, 2),
            "solar_rad_mj": round(sol_mj, 2),
            "rainfall_mm": round(rain, 2),
            "pressure_kpa": round(p_kpa, 2)
        })

    df = pd.DataFrame(records)
    return df


def fetch_openmeteo_7day_forecast(
    latitude: float = DEFAULT_LOCATION["latitude"],
    longitude: float = DEFAULT_LOCATION["longitude"],
    elevation: float = DEFAULT_LOCATION["elevation"],
    timezone_str: str = "Asia/Kolkata",
    timeout: float = 10.0,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetches real-time 7-day agricultural weather forecast from Open-Meteo API.
    Enforces timezone='Asia/Kolkata' and retrieves all raw variables for the FAO-56 Penman-Monteith engine.
    Caches responses to prevent repeated unnecessary network requests.

    Returns:
        dict:
            - success: bool
            - dataframe: pd.DataFrame
            - metadata: dict with provenance, timestamps, date range, coordinates
            - source_label: str
            - provenance_status: "LIVE_FORECAST"
            - error: Optional error string
    """
    cache_key = f"{latitude:.4f}_{longitude:.4f}_{timezone_str}"
    now_ts = datetime.now(timezone.utc)

    # Check cache
    if not force_refresh and cache_key in _LIVE_FORECAST_CACHE:
        cached_entry = _LIVE_FORECAST_CACHE[cache_key]
        cache_age = (now_ts - cached_entry["cached_at"]).total_seconds()
        if cache_age < CACHE_TTL_SECONDS:
            res_copy = dict(cached_entry["data"])
            res_copy["is_cached"] = True
            return res_copy

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone_str,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "relative_humidity_2m_max",
            "relative_humidity_2m_min",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "wind_speed_10m_max",
            "shortwave_radiation_sum",
            "surface_pressure_mean"
        ]
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        df = parse_openmeteo_daily_response(daily, latitude=latitude, elevation_m=elevation)
        df, _ = load_and_validate_weather_csv(df)

        date_list = df["date"].tolist()
        start_d = date_list[0] if date_list else ""
        end_d = date_list[-1] if date_list else ""

        retrieval_iso = now_ts.isoformat()

        metadata = {
            "source": "Open-Meteo Weather Forecast API",
            "source_url": "https://open-meteo.com/en/docs",
            "download_date_utc": retrieval_iso,
            "timezone": timezone_str,
            "coordinates": {"latitude": latitude, "longitude": longitude, "elevation_m": elevation},
            "date_range": {"start_date": start_d, "end_date": end_d},
            "data_category": "Live Numerical Weather Prediction (NWP) Forecast",
            "parameters": {
                "tmax": "Maximum Temperature at 2m (°C)",
                "tmin": "Minimum Temperature at 2m (°C)",
                "tmean": "Mean Temperature at 2m (°C)",
                "rh_max": "Maximum Relative Humidity at 2m (%)",
                "rh_min": "Minimum Relative Humidity at 2m (%)",
                "rh_mean": "Mean Relative Humidity at 2m (%)",
                "rainfall_mm": "Daily Precipitation Total (mm)",
                "wind_speed_2m": "Wind Speed converted from 10m to 2m (m/s)",
                "solar_rad_mj": "Shortwave Solar Radiation (MJ/m^2/day)",
                "pressure_kpa": "Atmospheric Surface Pressure converted from hPa (kPa)"
            }
        }

        result = {
            "success": True,
            "dataframe": df,
            "metadata": metadata,
            "source_label": f"Live Weather Forecast – Open-Meteo ({start_d} to {end_d})",
            "provenance_status": "LIVE_FORECAST",
            "is_cached": False,
            "error": None
        }

        # Update cache
        _LIVE_FORECAST_CACHE[cache_key] = {
            "cached_at": now_ts,
            "data": result
        }

        return result

    except Exception as e:
        return {
            "success": False,
            "dataframe": None,
            "metadata": None,
            "source_label": "Failed to connect to Open-Meteo",
            "provenance_status": "API_ERROR",
            "is_cached": False,
            "error": f"Live weather fetch failed: {str(e)}"
        }
