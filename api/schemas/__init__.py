"""
AGRI-2 API Schemas Package
"""
from api.schemas.weather import DailyWeatherRecord, WeatherForecastResponse, WeatherHistoricalResponse
from api.schemas.irrigation import IrrigationScheduleRequest, IrrigationScheduleResponse, DailyScheduleItem, WaterReductionScorecard
from api.schemas.advisory import AdvisoryRequest, AdvisoryResponse
from api.schemas.approval import ApprovalRequest, ApprovalResponse

__all__ = [
    "DailyWeatherRecord",
    "WeatherForecastResponse",
    "WeatherHistoricalResponse",
    "IrrigationScheduleRequest",
    "IrrigationScheduleResponse",
    "DailyScheduleItem",
    "WaterReductionScorecard",
    "AdvisoryRequest",
    "AdvisoryResponse",
    "ApprovalRequest",
    "ApprovalResponse",
]
