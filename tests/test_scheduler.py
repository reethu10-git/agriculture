"""
Tests for 7-Day Irrigation Scheduling Engine and Performance Benchmarking.
"""

import pytest
import pandas as pd
from src.irrigation_scheduler import (
    generate_irrigation_schedule,
    convert_depth_to_volume_litres
)


def test_volume_conversion():
    """Verify mm to Litres conversion for 1 Acre (4046.86 m2)."""
    # 10 mm depth over 1 Acre = 10 * 4046.856 = 40,468.6 Litres
    vol_10mm_acre = convert_depth_to_volume_litres(10.0, 1.0, "Acre")
    assert abs(vol_10mm_acre - 40468.6) < 1.0

    # 10 mm depth over 1 Hectare (10,000 m2) = 100,000 Litres
    vol_10mm_ha = convert_depth_to_volume_litres(10.0, 1.0, "Hectare")
    assert abs(vol_10mm_ha - 100000.0) < 1.0


def test_7day_schedule_generation_and_performance():
    """
    Tests 7-day schedule generation using the Coimbatore sample dataset.
    Validates:
    - Execution time < 10 seconds.
    - Consistent day-by-day outputs.
    - Water savings comparison >= 15% under standard conditions with rainfall.
    """
    df = pd.read_csv("data/sample/coimbatore_7day_weather.csv")

    res = generate_irrigation_schedule(
        weather_df=df,
        crop_name="Rice",
        growth_stage="Development",
        soil_type="Loamy",
        field_area_val=1.0,
        field_area_unit="Acre",
        initial_water_condition="Moderate"
    )

    # 1. Performance benchmark: Calculation under 10 seconds (Target < 10.0s)
    calc_time = res["calculation_time_seconds"]
    print(f"\n--- Irrigation Scheduler Performance ---")
    print(f"Calculation Time: {calc_time:.4f} seconds (Target: < 10.0s)")
    assert calc_time < 10.0, f"Calculation took too long: {calc_time}s"

    # 2. Structural consistency
    records = res["schedule_records"]
    assert len(records) == 7, f"Expected 7 daily records, got {len(records)}"

    for r in records:
        assert "date" in r
        assert "eto_mm" in r
        assert "kc" in r
        assert "etc_mm" in r
        assert "rainfall_mm" in r
        assert "effective_rainfall_mm" in r
        assert "recommended_irrigation_mm" in r
        assert "irrigation_volume_litres" in r
        assert "decision" in r
        assert r["decision"] in ["IRRIGATE", "SKIP", "MONITOR"]
        assert len(r["reason"]) > 10

    # 3. Water savings validation
    savings_pct = res["water_savings_pct"]
    print(f"Total Recommended Irrigation: {res['total_irrigation_recommended_mm']:.1f} mm ({res['total_irrigation_volume_litres']:,.0f} L)")
    print(f"Baseline Traditional Practice: {res['baseline_irrigation_mm']:.1f} mm ({res['baseline_irrigation_litres']:,.0f} L)")
    print(f"Measured Water Savings:       {savings_pct:.1f} % (Target: >= 15.0 %)")

    assert savings_pct >= 15.0, f"Water savings {savings_pct}% did not achieve 15% reduction against baseline"
