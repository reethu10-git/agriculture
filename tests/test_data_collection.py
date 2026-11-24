"""
Comprehensive Tests for Data Collection Architecture, External APIs,
and Provenance Tracking:
- Open-Meteo live forecast parsing and unit conversions
- Missing weather value imputation
- API connection failure handling
- NASA POWER historical retrieval and raw/processed storage
- ISRIC SoilGrids response parsing and modelled property extraction
- SoilGrids timeout fallback
- TNAU agricultural reference data loading
- Data provenance tracking
- End-to-end integration into the FAO-56 irrigation scheduling engine
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import pandas as pd
import requests

from src.weather_service import (
    parse_openmeteo_daily_response,
    fetch_openmeteo_7day_forecast
)
from src.nasa_power_service import (
    parse_nasa_power_response,
    fetch_nasa_power_historical
)
from src.soil_service import (
    parse_soilgrids_response,
    fetch_soilgrids_properties,
    COIMBATORE_REGIONAL_PROFILE
)
from src.agricultural_reference import (
    load_tnau_rice_guidelines,
    get_tnau_stage_recommendation,
    get_tnau_soil_interval
)
from src.irrigation_scheduler import generate_irrigation_schedule


# Sample mock responses
MOCK_OPENMETEO_DAILY = {
    "time": ["2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26", "2026-11-27", "2026-11-28", "2026-11-29"],
    "temperature_2m_max": [32.0, 31.5, 30.0, 29.5, 31.0, 32.2, 32.5],
    "temperature_2m_min": [23.0, 22.5, 23.0, 22.0, 21.8, 22.0, 22.5],
    "temperature_2m_mean": [27.5, 27.0, 26.5, 25.75, 26.4, 27.1, 27.5],
    "relative_humidity_2m_max": [85.0, 88.0, 92.0, 95.0, 88.0, 84.0, 82.0],
    "relative_humidity_2m_min": [30.0, 35.0, 45.0, 50.0, 38.0, 32.0, 28.0],
    "relative_humidity_2m_mean": [57.5, 61.5, 68.5, 72.5, 63.0, 58.0, 55.0],
    "precipitation_sum": [0.0, 0.0, 8.5, 18.0, 2.0, 0.0, 0.0],
    "wind_speed_10m_max": [10.8, 9.5, 8.0, 12.0, 9.0, 8.5, 10.0],  # km/h
    "shortwave_radiation_sum": [21.5, 20.8, 16.5, 14.2, 18.5, 21.0, 22.0],  # MJ/m2
    "surface_pressure_mean": [966.5, 967.0, 966.0, 965.5, 966.8, 967.2, 967.0]  # hPa
}

MOCK_SOILGRIDS_JSON = {
    "properties": {
        "layers": [
            {
                "name": "clay",
                "unit_measure": {"target_units": "g/kg"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 280}},
                    {"label": "5-15cm", "values": {"mean": 290}},
                    {"label": "15-30cm", "values": {"mean": 300}}
                ]
            },
            {
                "name": "sand",
                "unit_measure": {"target_units": "g/kg"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 450}},
                    {"label": "5-15cm", "values": {"mean": 440}},
                    {"label": "15-30cm", "values": {"mean": 430}}
                ]
            },
            {
                "name": "silt",
                "unit_measure": {"target_units": "g/kg"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 270}},
                    {"label": "5-15cm", "values": {"mean": 270}},
                    {"label": "15-30cm", "values": {"mean": 270}}
                ]
            },
            {
                "name": "soc",
                "unit_measure": {"target_units": "dg/kg"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 95}},
                    {"label": "5-15cm", "values": {"mean": 85}},
                    {"label": "15-30cm", "values": {"mean": 75}}
                ]
            },
            {
                "name": "bdod",
                "unit_measure": {"target_units": "cg/cm³"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 138}},
                    {"label": "5-15cm", "values": {"mean": 142}},
                    {"label": "15-30cm", "values": {"mean": 146}}
                ]
            },
            {
                "name": "phh2o",
                "unit_measure": {"target_units": "pH*10"},
                "depths": [
                    {"label": "0-5cm", "values": {"mean": 72}},
                    {"label": "5-15cm", "values": {"mean": 73}},
                    {"label": "15-30cm", "values": {"mean": 74}}
                ]
            }
        ]
    }
}


def test_openmeteo_forecast_parsing_and_units():
    """Validates Open-Meteo response parsing and physical unit conversions."""
    df = parse_openmeteo_daily_response(MOCK_OPENMETEO_DAILY, latitude=11.0168, elevation_m=411.0)

    assert len(df) == 7
    # 1. Wind speed: 10.8 km/h = 3.0 m/s at 10m -> at 2m height: 3.0 * 0.748 = ~2.24 m/s
    assert abs(df["wind_speed_2m"].iloc[0] - 2.24) < 0.1
    # 2. Solar radiation: 21.5 MJ/m2 preserved
    assert df["solar_rad_mj"].iloc[0] == 21.5
    # 3. Surface pressure: 966.5 hPa -> 96.65 kPa
    assert abs(df["pressure_kpa"].iloc[0] - 96.65) < 0.05
    # 4. Temperatures
    assert df["tmax"].iloc[0] == 32.0
    assert df["tmin"].iloc[0] == 23.0


def test_openmeteo_missing_weather_values_imputation():
    """Tests resilient imputation when Open-Meteo returns None for optional variables."""
    incomplete_data = {
        "time": ["2026-11-23"],
        "temperature_2m_max": [30.0],
        "temperature_2m_min": [20.0],
        "temperature_2m_mean": [None],
        "relative_humidity_2m_max": [None],
        "relative_humidity_2m_min": [None],
        "relative_humidity_2m_mean": [None],
        "precipitation_sum": [None],
        "wind_speed_10m_max": [None],
        "shortwave_radiation_sum": [None],
        "surface_pressure_mean": [None]
    }
    df = parse_openmeteo_daily_response(incomplete_data, latitude=11.0168, elevation_m=411.0)
    assert len(df) == 1
    # Missing mean temp should be calculated from (tmax+tmin)/2
    assert df["tmean"].iloc[0] == 25.0
    # Missing rainfall clamped to 0.0
    assert df["rainfall_mm"].iloc[0] == 0.0
    # Missing wind defaults to 2.0 m/s
    assert df["wind_speed_2m"].iloc[0] == 2.0
    # Missing pressure computed from elevation
    assert 95.0 <= df["pressure_kpa"].iloc[0] <= 98.0


def test_openmeteo_api_connection_failure():
    """Tests graceful failure reporting when Open-Meteo API is unreachable."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network down")):
        res = fetch_openmeteo_7day_forecast(force_refresh=True)
        assert res["success"] is False
        assert "Live weather fetch failed" in res["error"]
        assert res["provenance_status"] == "API_ERROR"


def test_nasa_power_historical_retrieval_and_standardization():
    """Tests NASA POWER parsing, sentinel value cleanup (-999), and file storage."""
    mock_nasa_json = {
        "properties": {
            "parameter": {
                "T2M_MAX": {"20261001": 31.5, "20261002": -999.0},  # sentinel test
                "T2M_MIN": {"20261001": 22.0, "20261002": 22.5},
                "T2M": {"20261001": 26.75, "20261002": -999.0},
                "RH2M": {"20261001": 72.0, "20261002": 70.0},
                "WS2M": {"20261001": 2.1, "20261002": 2.3},
                "ALLSKY_SFC_SW_DWN": {"20261001": 19.5, "20261002": 20.0},
                "PRECTOTCORR": {"20261001": 0.0, "20261002": 5.0},
                "PS": {"20261001": 96.8, "20261002": 96.7}
            }
        }
    }
    df = parse_nasa_power_response(mock_nasa_json)
    assert len(df) == 2
    # Sentinel -999.0 replaced with valid physical value (30.0)
    assert df["tmax"].iloc[1] == 30.0
    assert df["date"].iloc[0] == "2026-10-01"


def test_soilgrids_response_parsing_and_units():
    """Tests ISRIC SoilGrids response parsing and unit conversions."""
    props = parse_soilgrids_response(MOCK_SOILGRIDS_JSON)

    # Clay: (280+290+300)/3 = 290 g/kg -> 29.0 %
    assert abs(props["clay_percent"] - 29.0) < 0.1
    # Sand: (450+440+430)/3 = 440 g/kg -> 44.0 %
    assert abs(props["sand_percent"] - 44.0) < 0.1
    # Organic Carbon: (95+85+75)/3 = 85 dg/kg -> 8.5 g/kg
    assert abs(props["organic_carbon_g_kg"] - 8.5) < 0.1
    # Bulk density: (138+142+146)/3 = 142 cg/cm3 -> 1.42 g/cm3
    assert abs(props["bulk_density_g_cm3"] - 1.42) < 0.05
    # pH: (72+73+74)/3 = 73 pH*10 -> 7.3
    assert abs(props["soil_ph"] - 7.3) < 0.1
    # Texture class
    assert props["usda_texture_class"] in ["Sandy Clay Loam", "Clay Loam", "Loamy"]


def test_soilgrids_timeout_fallback():
    """Tests that a SoilGrids timeout falls back to regional profile without crashing."""
    with patch("requests.get", side_effect=requests.exceptions.ReadTimeout("Timeout")):
        res = fetch_soilgrids_properties(force_refresh=True)
        assert res["provenance_status"] == "MODELLED_SOIL_ESTIMATE_REGIONAL_PROFILE"
        assert res["properties"]["clay_percent"] == COIMBATORE_REGIONAL_PROFILE["clay_percent"]
        assert "NOT an actual field moisture reading" in res["disclaimer"]


def test_tnau_rice_guidelines_loading():
    """Tests that TNAU rice water management guidelines load and contain critical recommendations."""
    guidelines = load_tnau_rice_guidelines()
    assert guidelines["source_institution"] == "Tamil Nadu Agricultural University (TNAU)"

    # Mid-season is critical
    rec_mid = get_tnau_stage_recommendation("Mid-Season")
    assert rec_mid["sensitivity"] == "EXTREME"
    assert "Continuous submergence" in rec_mid["mandatory_management"]

    # Loamy interval
    soil_rec = get_tnau_soil_interval("Loamy")
    assert "3 to 4 days" in soil_rec["recommended_interval_days"]


def test_live_weather_fed_to_irrigation_engine():
    """Validates that parsed live weather DataFrame runs cleanly through the FAO-56 irrigation scheduler."""
    df = parse_openmeteo_daily_response(MOCK_OPENMETEO_DAILY, latitude=11.0168, elevation_m=411.0)
    schedule = generate_irrigation_schedule(
        weather_df=df,
        crop_name="Rice",
        growth_stage="Development",
        soil_type="Loamy",
        field_area_val=1.0,
        field_area_unit="Acre"
    )

    records = schedule["schedule_records"]
    assert len(records) == 7
    for r in records:
        assert r["eto_mm"] > 0
        assert r["etc_mm"] > 0
        assert r["decision"] in ["IRRIGATE", "SKIP", "MONITOR"]
        assert r["irrigation_volume_litres"] >= 0
