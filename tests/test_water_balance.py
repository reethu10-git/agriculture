"""
Unit tests for Soil-Water Balance Simulations:
- No rainfall
- Heavy rainfall
- Low initial soil moisture
- Adequate initial soil moisture
- Irrigation required vs Irrigation not required
"""

import pytest
import pandas as pd
from src.soil_water_balance import (
    simulate_paddy_water_balance,
    simulate_upland_water_balance,
    run_water_balance_simulation
)


def create_dummy_weather(rain_values, eto_val=5.0):
    dates = pd.date_range("2026-10-01", periods=len(rain_values))
    return pd.DataFrame({
        "date": dates,
        "eto_mm_day": [eto_val] * len(rain_values),
        "rainfall_mm": rain_values,
        "wind_speed_2m": [2.0] * len(rain_values),
        "rh_min": [50.0] * len(rain_values)
    })


def test_water_balance_no_rainfall():
    """Test water balance with 0 rainfall: water must deplete and trigger irrigation."""
    df_no_rain = create_dummy_weather([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    results = simulate_paddy_water_balance(
        weather_df=df_no_rain,
        soil_type="Loamy",
        growth_stage="Development",
        initial_ponded_depth_mm=10.0, # Low initial pond
        target_ponded_depth_mm=40.0,
        awd_min_depth_mm=0.0
    )
    # With 10mm initial pond and daily ETc ~ 5.7mm + Perc 2.5mm = 8.2mm loss,
    # Day 2 pond projected is <= 0mm, triggering irrigation
    irrigation_days = [r for r in results if r["decision"] == "IRRIGATE"]
    assert len(irrigation_days) > 0, "No irrigation triggered under zero rain!"


def test_water_balance_heavy_rainfall():
    """Test water balance with heavy rainfall: irrigation must be skipped."""
    df_heavy_rain = create_dummy_weather([30.0, 40.0, 25.0, 15.0, 20.0, 10.0, 5.0])
    results = simulate_paddy_water_balance(
        weather_df=df_heavy_rain,
        soil_type="Loamy",
        growth_stage="Development",
        initial_ponded_depth_mm=30.0,
        bund_height_mm=80.0
    )
    # High rainfall maintains pond, so no irrigation is needed
    irrigation_days = [r for r in results if r["decision"] == "IRRIGATE"]
    assert len(irrigation_days) == 0, "Irrigation should be skipped during heavy monsoon rain!"
    for r in results:
        assert r["decision"] == "SKIP"


def test_low_vs_adequate_initial_moisture():
    """Compare low initial moisture vs adequate initial moisture."""
    df = create_dummy_weather([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    res_low = run_water_balance_simulation(
        weather_df=df,
        crop_name="Rice",
        growth_stage="Development",
        initial_water_condition="Dry / Low"
    )

    res_adequate = run_water_balance_simulation(
        weather_df=df,
        crop_name="Rice",
        growth_stage="Development",
        initial_water_condition="Adequate / Target"
    )

    # Low initial moisture should require irrigation earlier than adequate
    first_irr_low = next((i for i, r in enumerate(res_low) if r["decision"] == "IRRIGATE"), 99)
    first_irr_adequate = next((i for i, r in enumerate(res_adequate) if r["decision"] == "IRRIGATE"), 99)

    assert first_irr_low <= first_irr_adequate, "Low moisture did not trigger earlier irrigation than adequate moisture"
