"""
Irrigation Scheduling Calculation Route
Calculates 7-day physical schedules and persists them to Supabase PostgreSQL.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from api.schemas.irrigation import (
    IrrigationScheduleRequest,
    IrrigationScheduleResponse,
    DailyScheduleItem,
    WaterReductionScorecard,
    ScheduleHistoryResponse,
    ScheduleHistorySummary
)
from src.irrigation_scheduler import generate_irrigation_schedule
from src.weather_service import load_sample_dataset, fetch_openmeteo_7day_forecast
from src.data_loader import load_and_validate_weather_csv
from src.db_client import insert_schedule, list_schedules, is_supabase_configured
from config.settings import CROP_DATABASE, SOIL_DATABASE, DEFAULT_LOCATION

router = APIRouter(prefix="/irrigation", tags=["Irrigation"])

SCENARIO_MAP = {
    "sample_coimbatore_7day": "Coimbatore Kharif Normal (7-Day Default)",
    "sample_dry_spell": "Coimbatore Dry Spell Stress Test (7-Day)",
    "sample_heavy_rain": "Coimbatore Heavy Monsoon Scenario (7-Day)",
    "sample_historical_30day": "Coimbatore Historical Observations (30-Day)"
}

@router.post("/schedule", response_model=IrrigationScheduleResponse, summary="Calculate 7-Day Irrigation Schedule")
def calculate_schedule(request: IrrigationScheduleRequest):
    """
    Computes a physical 7-day irrigation schedule adhering strictly to FAO-56 Penman-Monteith,
    soil water balance, and baseline water savings benchmarking.
    Persists the schedule in Supabase PostgreSQL when configured.
    Python remains the single computational source of truth.
    """
    # 1. Validate Crop
    if request.crop not in CROP_DATABASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported crop '{request.crop}'. Supported crops: {list(CROP_DATABASE.keys())}"
        )

    # 2. Validate Soil Type
    if request.soil_type not in SOIL_DATABASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported soil type '{request.soil_type}'. Supported types: {list(SOIL_DATABASE.keys())}"
        )

    # 3. Validate Growth Stage
    valid_stages = list(CROP_DATABASE.get(request.crop, {}).get("stages", {}).keys())
    if valid_stages and request.growth_stage not in valid_stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported growth stage '{request.growth_stage}' for {request.crop}. Supported stages: {valid_stages}"
        )

    # 4. Resolve Weather Data
    weather_df = None
    provenance_status = "SIMULATION_DATA"

    if request.weather_source == "live_openmeteo":
        result = fetch_openmeteo_7day_forecast(latitude=request.latitude, longitude=request.longitude)
        if not result.get("success", False) or result.get("dataframe") is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Live weather fetch failed: {result.get('error', 'Open-Meteo unreachable')}"
            )
        weather_df = result["dataframe"]
        provenance_status = result.get("provenance_status", "LIVE_FORECAST")

    elif request.weather_source == "custom_records":
        if not request.custom_weather_records or len(request.custom_weather_records) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_weather_records must be provided when weather_source is 'custom_records'."
            )
        dict_records = [r.model_dump() for r in request.custom_weather_records]
        raw_df = pd.DataFrame(dict_records)
        col_map = {
            "temp_max": "tmax",
            "temp_min": "tmin",
            "temp_mean": "tmean",
            "humidity_mean": "rh_mean",
            "humidity_max": "rh_max",
            "humidity_min": "rh_min",
            "wind_speed_2m": "wind_speed_2m",
            "solar_radiation": "solar_rad_mj",
            "rainfall": "rainfall_mm",
            "pressure_kpa": "pressure_kpa"
        }
        raw_df.rename(columns=col_map, inplace=True)
        try:
            clean_df, warns = load_and_validate_weather_csv(raw_df)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Custom weather validation failed: {str(e)}"
            )
        weather_df = clean_df
        provenance_status = "USER_CUSTOM_CSV"

    else:
        scenario_key = SCENARIO_MAP.get(request.weather_source, "Coimbatore Kharif Normal (7-Day Default)")
        try:
            weather_df = load_sample_dataset(scenario_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load scenario weather: {str(e)}"
            )
        provenance_status = "SIMULATION_DATA"

    # 5. Execute 7-Day Scheduler Engine
    initial_cond = "Moderate"
    if request.initial_water_depth_mm is not None:
        if request.initial_water_depth_mm < 15.0:
            initial_cond = "Low"
        elif request.initial_water_depth_mm > 40.0:
            initial_cond = "High"
        else:
            initial_cond = "Adequate"

    calc_res = generate_irrigation_schedule(
        weather_df=weather_df,
        crop_name=request.crop,
        growth_stage=request.growth_stage,
        soil_type=request.soil_type,
        field_area_val=request.field_area_acres,
        field_area_unit="Acre",
        initial_water_condition=initial_cond,
        latitude_deg=request.latitude,
        elevation_m=DEFAULT_LOCATION["elevation"]
    )

    # 6. Map to Response Schema
    daily_items = []
    for rec in calc_res["schedule_records"]:
        daily_items.append(
            DailyScheduleItem(
                day_index=rec.get("day_number", 1),
                date=str(rec.get("date", "")),
                eto_mm=float(rec.get("eto_mm", 0.0)),
                kc=float(rec.get("kc", 1.0)),
                etc_mm=float(rec.get("etc_mm", 0.0)),
                rainfall_mm=float(rec.get("rainfall_mm", 0.0)),
                effective_rainfall_mm=float(rec.get("effective_rainfall_mm", 0.0)),
                water_depth_before_mm=float(rec["water_depth_before_mm"]) if rec.get("water_depth_before_mm") is not None else None,
                water_depth_after_mm=float(rec["water_depth_after_mm"]) if rec.get("water_depth_after_mm") is not None else None,
                depletion_before_mm=float(rec["root_zone_depletion_before_mm"]) if rec.get("root_zone_depletion_before_mm") is not None else None,
                depletion_after_mm=float(rec["root_zone_depletion_after_mm"]) if rec.get("root_zone_depletion_after_mm") is not None else None,
                irrigation_depth_mm=float(rec.get("recommended_irrigation_mm", 0.0)),
                irrigation_volume_litres=int(rec.get("irrigation_volume_litres", 0)),
                decision=str(rec.get("decision", "SKIP")),
                reason=str(rec.get("reason", "")),
                stage_sensitivity=str(rec.get("critical_stage", "Normal"))
            )
        )

    scorecard = WaterReductionScorecard(
        baseline_total_depth_mm=float(calc_res["baseline_irrigation_mm"]),
        recommended_total_depth_mm=float(calc_res["total_irrigation_recommended_mm"]),
        water_saved_depth_mm=float(calc_res["water_savings_mm"]),
        water_savings_percent=float(calc_res["water_savings_pct"]),
        baseline_volume_litres=float(calc_res["baseline_irrigation_litres"]),
        recommended_volume_litres=float(calc_res["total_irrigation_volume_litres"]),
        water_saved_litres=float(calc_res["water_savings_litres"]),
        meets_conservation_target=bool(calc_res["water_savings_pct"] >= 15.0)
    )

    schedule_id = f"sch_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    # 7. Persist Schedule to Supabase PostgreSQL (or local fallback)
    schedule_data = {
        "id": schedule_id,
        "created_at": now_iso,
        "crop": request.crop,
        "growth_stage": request.growth_stage,
        "soil_type": request.soil_type,
        "field_area_acres": request.field_area_acres,
        "weather_source": request.weather_source,
        "provenance_status": provenance_status,
        "recommended_total_depth_mm": float(calc_res["total_irrigation_recommended_mm"]),
        "recommended_volume_litres": int(calc_res["total_irrigation_volume_litres"]),
        "water_savings_percent": float(calc_res["water_savings_pct"]),
        "daily_schedule": [d.model_dump() for d in daily_items],
        "full_metadata": {
            "calculation_time_seconds": float(calc_res["calculation_time_seconds"]),
            "latitude": request.latitude,
            "longitude": request.longitude,
            "totals": {
                "total_eto_mm": float(calc_res["total_eto_mm"]),
                "total_etc_mm": float(calc_res["total_etc_mm"]),
                "total_rainfall_mm": float(calc_res["total_rainfall_mm"]),
                "total_effective_rainfall_mm": float(calc_res["total_effective_rainfall_mm"]),
                "total_irrigation_mm": float(calc_res["total_irrigation_recommended_mm"]),
                "total_irrigation_litres": float(calc_res["total_irrigation_volume_litres"])
            }
        }
    }

    save_res = insert_schedule(schedule_data)
    if is_supabase_configured() and not save_res.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database persistence failure for schedule: {save_res.get('error')}"
        )

    storage_mode = save_res.get("storage_mode", "LOCAL_JSON_FALLBACK")

    return IrrigationScheduleResponse(
        success=True,
        schedule_id=schedule_id,
        crop=request.crop,
        growth_stage=request.growth_stage,
        soil_type=request.soil_type,
        location=request.location,
        field_area_acres=request.field_area_acres,
        provenance_status=provenance_status,
        daily_schedule=daily_items,
        water_reduction_scorecard=scorecard,
        totals={
            "total_eto_mm": float(calc_res["total_eto_mm"]),
            "total_etc_mm": float(calc_res["total_etc_mm"]),
            "total_rainfall_mm": float(calc_res["total_rainfall_mm"]),
            "total_effective_rainfall_mm": float(calc_res["total_effective_rainfall_mm"]),
            "total_irrigation_mm": float(calc_res["total_irrigation_recommended_mm"]),
            "total_irrigation_litres": float(calc_res["total_irrigation_volume_litres"])
        },
        metadata={
            "calculation_time_seconds": float(calc_res["calculation_time_seconds"]),
            "latitude": request.latitude,
            "longitude": request.longitude,
            "storage_mode": storage_mode
        }
    )


@router.get("/history", response_model=ScheduleHistoryResponse, summary="Retrieve Irrigation Schedule History")
def get_schedule_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return (1-100)"),
    crop: Optional[str] = Query(default=None, description="Filter by crop name")
):
    """
    Retrieves recent irrigation schedules with strict upper-bound limits.
    Prevents unrestricted bulk dumping of records.
    """
    storage_mode = "SUPABASE_POSTGRESQL" if is_supabase_configured() else "LOCAL_JSON_FALLBACK"
    records = list_schedules(limit=limit, crop=crop)

    items = []
    for r in records:
        items.append(
            ScheduleHistorySummary(
                id=str(r.get("id")),
                created_at=str(r.get("created_at")),
                crop=str(r.get("crop", "Rice")),
                growth_stage=str(r.get("growth_stage", "Development")),
                soil_type=str(r.get("soil_type", "Loamy")),
                field_area_acres=float(r.get("field_area_acres", 1.0)),
                weather_source=str(r.get("weather_source", "")),
                provenance_status=str(r.get("provenance_status", "")),
                recommended_total_depth_mm=float(r.get("recommended_total_depth_mm", 0.0)),
                recommended_volume_litres=int(r.get("recommended_volume_litres", 0)),
                water_savings_percent=float(r.get("water_savings_percent", 0.0))
            )
        )

    return ScheduleHistoryResponse(
        success=True,
        count=len(items),
        storage_mode=storage_mode,
        schedules=items
    )
