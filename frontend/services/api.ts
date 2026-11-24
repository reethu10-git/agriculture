/**
 * AGRI-2 API Service Layer
 * Directly interfaces with FastAPI backend routes without direct browser calls
 * to Nexus AI or Supabase PostgreSQL.
 */

import {
  HealthResponse,
  WeatherForecastResponse,
  WeatherHistoricalResponse,
  IrrigationScheduleRequest,
  IrrigationScheduleResponse,
  AdvisoryRequest,
  AdvisoryResponse,
  ApprovalRequest,
  ApprovalResponse,
  ScheduleHistoryResponse,
  ApprovalHistoryResponse
} from './types';

// Browser-safe API base URL resolution:
// In Next.js client side, relative /api paths are rewritten via next.config.js to backend.
const API_BASE = '';

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error (${status}): ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    
    if (!response.ok) {
      let detail = `Request failed with HTTP ${response.status}`;
      try {
        const errorJson = await response.json();
        detail = errorJson.detail || errorJson.error || detail;
      } catch {
        // use default status message if response is not JSON
      }
      throw new ApiError(response.status, detail);
    }

    return await response.json() as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Unknown network error';
    throw new ApiError(0, `Network error communicating with agricultural backend: ${message}`);
  }
}

export const api = {
  /**
   * Health & Status probe
   */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/api/health');
  },

  /**
   * Open-Meteo live 7-day weather forecast
   */
  async getWeatherForecast(latitude: number, longitude: number): Promise<WeatherForecastResponse> {
    return request<WeatherForecastResponse>(
      `/api/weather/forecast?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}`
    );
  },

  /**
   * NASA POWER historical agroclimatological reanalysis
   */
  async getWeatherHistorical(
    latitude: number,
    longitude: number,
    startDate: string,
    endDate: string
  ): Promise<WeatherHistoricalResponse> {
    return request<WeatherHistoricalResponse>(
      `/api/weather/historical?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}&start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
    );
  },

  /**
   * Calculate FAO-56 7-Day Irrigation Schedule
   */
  async calculateSchedule(payload: IrrigationScheduleRequest): Promise<IrrigationScheduleResponse> {
    return request<IrrigationScheduleResponse>('/api/irrigation/schedule', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Retrieve Irrigation Schedule History
   */
  async getScheduleHistory(limit = 20, crop?: string): Promise<ScheduleHistoryResponse> {
    let url = `/api/irrigation/history?limit=${limit}`;
    if (crop) {
      url += `&crop=${encodeURIComponent(crop)}`;
    }
    return request<ScheduleHistoryResponse>(url);
  },

  /**
   * Generate Farmer Advisory in English or Telugu via Nexus AI
   */
  async generateAdvisory(payload: AdvisoryRequest): Promise<AdvisoryResponse> {
    return request<AdvisoryResponse>('/api/advisory', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Record Farmer Approval / Decline Decision
   */
  async recordApproval(payload: ApprovalRequest): Promise<ApprovalResponse> {
    return request<ApprovalResponse>('/api/approval', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Retrieve Farmer Approval Decision History
   */
  async getApprovalHistory(limit = 20, scheduleId?: string, farmerName?: string): Promise<ApprovalHistoryResponse> {
    let url = `/api/approval/history?limit=${limit}`;
    if (scheduleId) {
      url += `&schedule_id=${encodeURIComponent(scheduleId)}`;
    }
    if (farmerName) {
      url += `&farmer_name=${encodeURIComponent(farmerName)}`;
    }
    return request<ApprovalHistoryResponse>(url);
  },
};
