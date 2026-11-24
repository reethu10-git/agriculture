/**
 * AGRI-2 Frontend TypeScript Schema Interfaces
 * Aligned with FastAPI backend schemas in api/schemas/
 */

export interface HealthResponse {
  status: string;
  app_title: string;
  version: string;
  environment: string;
  nexus_configured: boolean;
  nexus_model: string;
  timestamp: string;
}

export interface DailyWeatherRecord {
  date: string;
  temp_max: number;
  temp_min: number;
  temp_mean: number;
  humidity_mean: number;
  humidity_max?: number | null;
  humidity_min?: number | null;
  wind_speed_2m: number;
  solar_radiation: number;
  rainfall: number;
  pressure_kpa?: number | null;
}

export interface WeatherForecastResponse {
  success: boolean;
  provenance_status: string;
  provenance_badge: string;
  source_name: string;
  retrieval_timestamp: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  date_range: {
    start: string;
    end: string;
  };
  daily_records: DailyWeatherRecord[];
  disclaimer: string;
}

export interface WeatherHistoricalResponse {
  success: boolean;
  provenance_status: string;
  provenance_badge: string;
  source_name: string;
  retrieval_timestamp: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  date_range: {
    start: string;
    end: string;
  };
  daily_records: DailyWeatherRecord[];
  disclaimer: string;
}

export interface IrrigationScheduleRequest {
  crop: string;
  growth_stage: string;
  soil_type: string;
  location?: string;
  latitude: number;
  longitude: number;
  field_area_acres: number;
  initial_water_depth_mm?: number;
  initial_depletion_mm?: number;
  weather_source: string;
  custom_weather_records?: DailyWeatherRecord[];
}

export interface DailyScheduleItem {
  day_index: number;
  date: string;
  eto_mm: number;
  kc: number;
  etc_mm: number;
  rainfall_mm: number;
  effective_rainfall_mm: number;
  water_depth_before_mm?: number | null;
  water_depth_after_mm?: number | null;
  depletion_before_mm?: number | null;
  depletion_after_mm?: number | null;
  irrigation_depth_mm: number;
  irrigation_volume_litres: number;
  decision: 'IRRIGATE' | 'SKIP' | string;
  reason: string;
  stage_sensitivity: string;
}

export interface WaterReductionScorecard {
  baseline_total_depth_mm: number;
  recommended_total_depth_mm: number;
  water_saved_depth_mm: number;
  water_savings_percent: number;
  baseline_volume_litres: number;
  recommended_volume_litres: number;
  water_saved_litres: number;
  meets_conservation_target: boolean;
}

export interface IrrigationScheduleResponse {
  success: boolean;
  schedule_id: string;
  crop: string;
  growth_stage: string;
  soil_type: string;
  location: string;
  field_area_acres: number;
  provenance_status: string;
  daily_schedule: DailyScheduleItem[];
  water_reduction_scorecard: WaterReductionScorecard;
  totals: {
    total_eto_mm: number;
    total_etc_mm: number;
    total_rainfall_mm: number;
    total_effective_rainfall_mm: number;
    total_irrigation_mm: number;
    total_irrigation_litres: number;
  };
  metadata: {
    calculation_time_seconds?: number;
    latitude?: number;
    longitude?: number;
    storage_mode?: string;
  };
}

export interface AdvisoryRequest {
  schedule_result: Record<string, unknown>;
  language: 'English' | 'Telugu' | string;
  farmer_name?: string;
  field_location?: string;
}

export interface AdvisoryResponse {
  success: boolean;
  language: string;
  model_used?: string | null;
  advisory_markdown: string;
  is_fallback: boolean;
  error_message?: string | null;
}

export interface ApprovalRequest {
  schedule_id: string;
  decision: 'APPROVED' | 'DECLINED';
  farmer_name: string;
  field_notes?: string;
  approved_depth_mm: number;
  approved_volume_litres: number;
  crop: string;
  field_area_acres: number;
}

export interface ApprovalResponse {
  success: boolean;
  approval_id: string;
  schedule_id: string;
  decision: string;
  farmer_name: string;
  recorded_at: string;
  message: string;
  persisted_mode: string;
}

export interface ScheduleHistorySummary {
  id: string;
  created_at: string;
  crop: string;
  growth_stage: string;
  soil_type: string;
  field_area_acres: number;
  weather_source: string;
  provenance_status: string;
  recommended_total_depth_mm: number;
  recommended_volume_litres: number;
  water_savings_percent: number;
}

export interface ScheduleHistoryResponse {
  success: boolean;
  count: number;
  storage_mode: string;
  schedules: ScheduleHistorySummary[];
}

export interface ApprovalHistoryItem {
  id: string;
  schedule_id: string;
  recorded_at: string;
  farmer_name: string;
  decision: string;
  field_notes?: string;
  approved_depth_mm: number;
  approved_volume_litres: number;
  crop: string;
  field_area_acres: number;
}

export interface ApprovalHistoryResponse {
  success: boolean;
  count: number;
  storage_mode: string;
  approvals: ApprovalHistoryItem[];
}
