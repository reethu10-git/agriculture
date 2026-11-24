"""
Pydantic Schemas for Weather Endpoints
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DailyWeatherRecord(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD ISO format")
    temp_max: float = Field(..., description="Maximum temperature in degrees Celsius")
    temp_min: float = Field(..., description="Minimum temperature in degrees Celsius")
    temp_mean: float = Field(..., description="Mean temperature in degrees Celsius")
    humidity_mean: float = Field(..., ge=0.0, le=100.0, description="Mean relative humidity in %")
    humidity_max: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Max relative humidity in %")
    humidity_min: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Min relative humidity in %")
    wind_speed_2m: float = Field(..., ge=0.0, description="Wind speed at 2m height in m/s")
    solar_radiation: float = Field(..., ge=0.0, description="Shortwave solar radiation in MJ/m2/day")
    rainfall: float = Field(default=0.0, ge=0.0, description="Precipitation in mm")
    pressure_kpa: Optional[float] = Field(default=None, description="Surface atmospheric pressure in kPa")

class WeatherForecastResponse(BaseModel):
    success: bool
    provenance_status: str = Field(default="LIVE_FORECAST")
    provenance_badge: str
    source_name: str
    retrieval_timestamp: str
    coordinates: Dict[str, float]
    date_range: Dict[str, str]
    daily_records: List[DailyWeatherRecord]
    disclaimer: str

class WeatherHistoricalResponse(BaseModel):
    success: bool
    provenance_status: str = Field(default="HISTORICAL_OBSERVATION_REANALYSIS")
    provenance_badge: str
    source_name: str
    retrieval_timestamp: str
    coordinates: Dict[str, float]
    date_range: Dict[str, str]
    daily_records: List[DailyWeatherRecord]
    disclaimer: str
