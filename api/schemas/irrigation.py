"""
Pydantic Schemas for Irrigation Scheduling Endpoints
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from api.schemas.weather import DailyWeatherRecord

class IrrigationScheduleRequest(BaseModel):
    crop: str = Field(default="Rice", description="Crop name: Rice, Maize, Wheat, Tomato, Cotton, Sugarcane")
    growth_stage: str = Field(default="Development", description="Growth stage: Initial, Development, Mid-Season, Late-Season")
    soil_type: str = Field(default="Loamy", description="Soil type: Sandy Loam, Loamy, Clay Loam, Clay, Silt Loam")
    location: str = Field(default="Coimbatore, Tamil Nadu", description="Location name or description")
    latitude: float = Field(default=11.0168, ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(default=76.9558, ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    field_area_acres: float = Field(default=1.0, gt=0.0, description="Field area in acres")
    initial_water_depth_mm: Optional[float] = Field(default=25.0, ge=0.0, description="Initial water depth in mm (for lowland rice)")
    initial_depletion_mm: Optional[float] = Field(default=0.0, ge=0.0, description="Initial root-zone depletion in mm (for upland crops)")
    weather_source: str = Field(
        default="sample_coimbatore_7day",
        description="Source: live_openmeteo, sample_coimbatore_7day, sample_dry_spell, sample_heavy_rain, sample_historical_30day, custom_records"
    )
    custom_weather_records: Optional[List[DailyWeatherRecord]] = Field(
        default=None,
        description="Custom list of 7 daily weather records if weather_source is custom_records"
    )

class DailyScheduleItem(BaseModel):
    day_index: int
    date: str
    eto_mm: float
    kc: float
    etc_mm: float
    rainfall_mm: float
    effective_rainfall_mm: float
    water_depth_before_mm: Optional[float] = None
    water_depth_after_mm: Optional[float] = None
    depletion_before_mm: Optional[float] = None
    depletion_after_mm: Optional[float] = None
    irrigation_depth_mm: float
    irrigation_volume_litres: int
    decision: str
    reason: str
    stage_sensitivity: str

class WaterReductionScorecard(BaseModel):
    baseline_total_depth_mm: float
    recommended_total_depth_mm: float
    water_saved_depth_mm: float
    water_savings_percent: float
    baseline_volume_litres: float
    recommended_volume_litres: float
    water_saved_litres: float
    meets_conservation_target: bool

class IrrigationScheduleResponse(BaseModel):
    success: bool
    schedule_id: str
    crop: str
    growth_stage: str
    soil_type: str
    location: str
    field_area_acres: float
    provenance_status: str
    daily_schedule: List[DailyScheduleItem]
    water_reduction_scorecard: WaterReductionScorecard
    totals: Dict[str, Any]
    metadata: Dict[str, Any]

class ScheduleHistorySummary(BaseModel):
    id: str
    created_at: str
    crop: str
    growth_stage: str
    soil_type: str
    field_area_acres: float
    weather_source: str
    provenance_status: str
    recommended_total_depth_mm: float
    recommended_volume_litres: int
    water_savings_percent: float

class ScheduleHistoryResponse(BaseModel):
    success: bool
    count: int
    storage_mode: str
    schedules: List[ScheduleHistorySummary]
