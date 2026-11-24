"""
Weather Forecast and Historical Data Routes
"""
from typing import List
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, status
from api.schemas.weather import DailyWeatherRecord, WeatherForecastResponse, WeatherHistoricalResponse
from src.weather_service import fetch_openmeteo_7day_forecast
from src.nasa_power_service import fetch_nasa_power_historical

router = APIRouter(prefix="/weather", tags=["Weather"])

def _df_to_daily_records(df: pd.DataFrame) -> List[DailyWeatherRecord]:
    """Helper to convert weather DataFrame rows to Pydantic DailyWeatherRecord models."""
    records = []
    for _, row in df.iterrows():
        # Handle standardized names (tmax, rainfall_mm) as well as legacy names
        tmax = row.get("tmax", row.get("temp_max", 30.0))
        tmin = row.get("tmin", row.get("temp_min", 20.0))
        tmean = row.get("tmean", row.get("temp_mean", (tmax + tmin) / 2))
        rh_mean = row.get("rh_mean", row.get("humidity_mean", 70.0))
        rh_max = row.get("rh_max", row.get("humidity_max", None))
        rh_min = row.get("rh_min", row.get("humidity_min", None))
        wind = row.get("wind_speed_2m", row.get("wind_speed", 2.0))
        rad = row.get("solar_rad_mj", row.get("solar_radiation", 18.0))
        rain = row.get("rainfall_mm", row.get("rainfall", 0.0))
        pres = row.get("pressure_kpa", row.get("pressure", None))

        records.append(
            DailyWeatherRecord(
                date=str(row["date"])[:10],
                temp_max=float(tmax),
                temp_min=float(tmin),
                temp_mean=float(tmean),
                humidity_mean=float(rh_mean),
                humidity_max=float(rh_max) if rh_max is not None and not pd.isna(rh_max) else None,
                humidity_min=float(rh_min) if rh_min is not None and not pd.isna(rh_min) else None,
                wind_speed_2m=float(wind),
                solar_radiation=float(rad),
                rainfall=float(rain),
                pressure_kpa=float(pres) if pres is not None and not pd.isna(pres) else None,
            )
        )
    return records

@router.get("/forecast", response_model=WeatherForecastResponse, summary="Fetch Genuine Live 7-Day Weather Forecast")
def get_live_forecast(
    latitude: float = Query(default=11.0168, ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    longitude: float = Query(default=76.9558, ge=-180.0, le=180.0, description="Longitude in decimal degrees")
):
    """
    Fetches genuine 7-day numerical weather forecast from Open-Meteo API.
    Converts 10m wind speed to 2m, normalizes radiation to MJ/m2/day and pressure to kPa.
    Does NOT replace FAO-56 ETo calculations.
    """
    result = fetch_openmeteo_7day_forecast(latitude=latitude, longitude=longitude)

    if not result.get("success", False) or result.get("dataframe") is None:
        error_msg = result.get("error", "Failed to retrieve forecast data from Open-Meteo API.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Open-Meteo Forecast Error: {error_msg}"
        )

    df = result["dataframe"]
    meta = result.get("metadata", {})
    records = _df_to_daily_records(df)

    start_date = records[0].date if records else ""
    end_date = records[-1].date if records else ""

    return WeatherForecastResponse(
        success=True,
        provenance_status=result.get("provenance_status", "LIVE_FORECAST"),
        provenance_badge="Open-Meteo Live 7-Day Forecast",
        source_name="Open-Meteo Weather API",
        retrieval_timestamp=meta.get("download_date_utc", ""),
        coordinates={"latitude": latitude, "longitude": longitude},
        date_range={"start": start_date, "end": end_date},
        daily_records=records,
        disclaimer="Live numerical forecast from Open-Meteo (ECMWF/GFS models). Not historical data."
    )

@router.get("/historical", response_model=WeatherHistoricalResponse, summary="Fetch Genuine Historical Reanalysis Weather")
def get_historical_weather(
    latitude: float = Query(default=11.0168, ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    longitude: float = Query(default=76.9558, ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    start_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date (YYYY-MM-DD)")
):
    """
    Retrieves historical meteorological data from NASA POWER Daily API.
    Identifies NASA POWER data as gridded meteorological/reanalysis data, not direct local weather-station measurements.
    Does NOT fabricate synthetic data upon failure.
    """
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date range: start_date '{start_date}' cannot be after end_date '{end_date}'."
        )

    clean_start = start_date.replace("-", "")
    clean_end = end_date.replace("-", "")

    result = fetch_nasa_power_historical(
        start_date=clean_start,
        end_date=clean_end,
        latitude=latitude,
        longitude=longitude
    )

    if not result.get("success", False) or result.get("dataframe") is None:
        error_msg = result.get("error", "Failed to retrieve historical data from NASA POWER API.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NASA POWER API Error: {error_msg}"
        )

    df = result["dataframe"]
    meta = result.get("metadata", {})
    records = _df_to_daily_records(df)

    start_iso = records[0].date if records else start_date
    end_iso = records[-1].date if records else end_date

    return WeatherHistoricalResponse(
        success=True,
        provenance_status=result.get("provenance_status", "HISTORICAL_OBSERVATION_REANALYSIS"),
        provenance_badge="NASA POWER Daily Observations",
        source_name="NASA POWER Daily API",
        retrieval_timestamp=meta.get("download_date_utc", ""),
        coordinates={"latitude": latitude, "longitude": longitude},
        date_range={"start": start_iso, "end": end_iso},
        daily_records=records,
        disclaimer="Historical gridded agroclimatology from NASA POWER (GEOSIT / MERRA-2 assimilation). Not direct local physical gauge measurements."
    )
