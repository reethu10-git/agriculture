"""
AGRI-2: Seven-Day Irrigation Scheduling and Advisory Synthesis Engine
Combines meteorological series, ETo, ETc, effective rainfall, and soil-water dynamics
into an actionable 7-day schedule with physical water volumes (Litres), decisions, and
baseline water-savings benchmarking.
"""

from typing import Dict, Any, List, Optional
import time
import pandas as pd
from config.settings import AREA_CONVERSIONS, DEFAULT_LOCATION
from src.eto_calculator import calculate_eto_series
from src.soil_water_balance import run_water_balance_simulation


def convert_depth_to_volume_litres(depth_mm: float, area_val: float, area_unit: str = "Acre") -> float:
    """
    Converts irrigation depth in millimeters to total volume in Litres.
    Physics: 1 mm depth over 1 square meter = 1 Litre of water.
    Volume (Litres) = Depth (mm) * Area (m2)
    """
    conversion_factor = AREA_CONVERSIONS.get(area_unit, AREA_CONVERSIONS["Acre"])
    area_m2 = area_val * conversion_factor
    volume_litres = depth_mm * area_m2
    return round(volume_litres, 1)


def generate_irrigation_schedule(
    weather_df: pd.DataFrame,
    crop_name: str = "Rice",
    growth_stage: str = "Development",
    soil_type: str = "Loamy",
    field_area_val: float = 1.0,
    field_area_unit: str = "Acre",
    initial_water_condition: str = "Moderate",
    latitude_deg: float = DEFAULT_LOCATION["latitude"],
    elevation_m: float = DEFAULT_LOCATION["elevation"],
    baseline_interval_days: int = 3,
    baseline_depth_mm: float = 45.0
) -> Dict[str, Any]:
    """
    Executes end-to-end 7-day irrigation schedule calculation.

    Returns:
        dict:
            - schedule_records: List of daily dicts
            - schedule_df: Formatted pandas DataFrame
            - total_eto_mm: float
            - total_etc_mm: float
            - total_rainfall_mm: float
            - total_effective_rainfall_mm: float
            - total_irrigation_recommended_mm: float
            - total_irrigation_volume_litres: float
            - baseline_irrigation_mm: float
            - baseline_irrigation_litres: float
            - water_savings_mm: float
            - water_savings_litres: float
            - water_savings_pct: float
            - calculation_time_seconds: float
            - metadata: configuration dictionary
    """
    start_time = time.perf_counter()

    # Step 1: Ensure ETo is calculated if missing
    if "eto_mm_day" not in weather_df.columns or weather_df["eto_mm_day"].isnull().any():
        processed_weather = calculate_eto_series(
            weather_df,
            latitude_deg=latitude_deg,
            elevation_m=elevation_m
        )
    else:
        processed_weather = weather_df.copy()

    # Ensure 7-day slice
    if len(processed_weather) > 7:
        processed_weather = processed_weather.head(7)

    # Step 2: Run dynamic soil-water balance simulation
    simulation_records = run_water_balance_simulation(
        weather_df=processed_weather,
        crop_name=crop_name,
        growth_stage=growth_stage,
        soil_type=soil_type,
        field_area_val=field_area_val,
        field_area_unit=field_area_unit,
        initial_water_condition=initial_water_condition
    )

    # Step 3: Compute field volumes and enrich records
    enriched_records = []
    total_irr_mm = 0.0
    total_irr_litres = 0.0
    total_eto = 0.0
    total_etc = 0.0
    total_rain = 0.0
    total_peff = 0.0

    for idx, rec in enumerate(simulation_records):
        irr_mm = rec["recommended_irrigation_mm"]
        vol_litres = convert_depth_to_volume_litres(irr_mm, field_area_val, field_area_unit)

        total_irr_mm += irr_mm
        total_irr_litres += vol_litres
        total_eto += rec["eto_mm"]
        total_etc += rec["etc_mm"]
        total_rain += rec["rainfall_mm"]
        total_peff += rec["effective_rainfall_mm"]

        record_copy = dict(rec)
        record_copy["day_number"] = idx + 1
        record_copy["irrigation_volume_litres"] = vol_litres
        enriched_records.append(record_copy)

    # Step 4: Baseline Comparison (Traditional calendar-based irrigation practice)
    # Traditional practice in Tamil Nadu rice delta / upland: fixed application every N days regardless of rain
    # e.g., Day 1: 45mm, Day 4: 45mm, Day 7: 45mm = 90-135 mm/week
    baseline_days_count = len(enriched_records)
    baseline_events = [1 if (i % baseline_interval_days == 0) else 0 for i in range(baseline_days_count)]
    baseline_irr_mm = sum(baseline_events) * baseline_depth_mm
    baseline_litres = convert_depth_to_volume_litres(baseline_irr_mm, field_area_val, field_area_unit)

    water_savings_mm = max(0.0, baseline_irr_mm - total_irr_mm)
    water_savings_litres = max(0.0, baseline_litres - total_irr_litres)
    water_savings_pct = (water_savings_mm / baseline_irr_mm * 100.0) if baseline_irr_mm > 0 else 0.0

    calculation_duration = time.perf_counter() - start_time

    schedule_df = pd.DataFrame(enriched_records)

    return {
        "schedule_records": enriched_records,
        "schedule_df": schedule_df,
        "total_eto_mm": round(total_eto, 2),
        "total_etc_mm": round(total_etc, 2),
        "total_rainfall_mm": round(total_rain, 2),
        "total_effective_rainfall_mm": round(total_peff, 2),
        "total_irrigation_recommended_mm": round(total_irr_mm, 2),
        "total_irrigation_volume_litres": round(total_irr_litres, 1),
        "baseline_irrigation_mm": round(baseline_irr_mm, 2),
        "baseline_irrigation_litres": round(baseline_litres, 1),
        "water_savings_mm": round(water_savings_mm, 2),
        "water_savings_litres": round(water_savings_litres, 1),
        "water_savings_pct": round(water_savings_pct, 1),
        "calculation_time_seconds": round(calculation_duration, 4),
        "metadata": {
            "crop": crop_name,
            "growth_stage": growth_stage,
            "soil_type": soil_type,
            "field_area_val": field_area_val,
            "field_area_unit": field_area_unit,
            "initial_water_condition": initial_water_condition,
            "baseline_assumptions": f"Traditional calendar flooding: {baseline_depth_mm} mm applied every {baseline_interval_days} days."
        }
    }
