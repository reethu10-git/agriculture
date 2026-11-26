"""
Automated Integration and Unit Tests for AGRI-2 FastAPI Backend
Tests health, weather endpoints, irrigation schedule calculations,
advisory generation, approval recording, and robust error handling.
"""
import pytest
from unittest.mock import patch
import pandas as pd
from fastapi.testclient import TestClient
from api.index import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_weather_df():
    """Generates a standardized 7-day agro-meteorological test DataFrame."""
    dates = pd.date_range("2026-10-01", periods=7, freq="D")
    return pd.DataFrame({
        "date": dates,
        "tmax": [31.5, 32.0, 30.5, 31.0, 33.0, 29.5, 30.0],
        "tmin": [22.0, 21.5, 22.5, 21.0, 23.0, 20.5, 21.0],
        "tmean": [26.75, 26.75, 26.5, 26.0, 28.0, 25.0, 25.5],
        "rh_mean": [75.0, 72.0, 78.0, 80.0, 68.0, 82.0, 76.0],
        "rh_max": [95.0, 92.0, 96.0, 98.0, 90.0, 98.0, 94.0],
        "rh_min": [55.0, 52.0, 60.0, 62.0, 46.0, 66.0, 58.0],
        "wind_speed_2m": [2.1, 1.8, 2.5, 2.0, 2.8, 1.5, 1.9],
        "solar_rad_mj": [18.5, 19.2, 17.0, 16.5, 20.1, 15.2, 17.8],
        "rainfall_mm": [0.0, 0.0, 5.0, 12.0, 0.0, 2.0, 0.0],
        "pressure_kpa": [96.8, 96.7, 96.5, 96.6, 96.9, 96.7, 96.8]
    })

# 1. Health Endpoint Tests
def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_title"] == "AGRI-2 Irrigation Scheduling Advisor"
    assert data["version"] == "1.0.0"
    assert "nexus_configured" in data
    assert "timestamp" in data

# 2. Weather Forecast Tests
def test_weather_forecast_endpoint_mocked(client, sample_weather_df):
    mock_result = {
        "success": True,
        "dataframe": sample_weather_df,
        "metadata": {"download_date_utc": "2026-10-01T00:00:00Z"},
        "provenance_status": "LIVE_FORECAST"
    }
    with patch("api.routes.weather.fetch_openmeteo_7day_forecast", return_value=mock_result):
        response = client.get("/api/weather/forecast?latitude=11.0168&longitude=76.9558")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["provenance_status"] == "LIVE_FORECAST"
        assert len(data["daily_records"]) == 7
        assert data["daily_records"][0]["temp_max"] == 31.5

def test_weather_forecast_invalid_coordinates(client):
    # Latitude > 90 must fail validation
    response = client.get("/api/weather/forecast?latitude=999.0&longitude=76.9558")
    assert response.status_code == 422

    # Longitude < -180 must fail validation
    response = client.get("/api/weather/forecast?latitude=11.0168&longitude=-250.0")
    assert response.status_code == 422

def test_weather_forecast_api_failure(client):
    mock_failure = {
        "success": False,
        "dataframe": None,
        "error": "Open-Meteo connection timed out"
    }
    with patch("api.routes.weather.fetch_openmeteo_7day_forecast", return_value=mock_failure):
        response = client.get("/api/weather/forecast?latitude=11.0168&longitude=76.9558")
        assert response.status_code == 502
        assert "Open-Meteo Forecast Error" in response.json()["detail"]

# 3. Weather Historical Tests
def test_weather_historical_endpoint_mocked(client, sample_weather_df):
    mock_result = {
        "success": True,
        "dataframe": sample_weather_df,
        "metadata": {"download_date_utc": "2026-10-01T00:00:00Z"},
        "provenance_status": "HISTORICAL_OBSERVATION_REANALYSIS"
    }
    with patch("api.routes.weather.fetch_nasa_power_historical", return_value=mock_result):
        response = client.get("/api/weather/historical?start_date=2026-10-01&end_date=2026-10-07")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["provenance_status"] == "HISTORICAL_OBSERVATION_REANALYSIS"
        assert len(data["daily_records"]) == 7

def test_weather_historical_invalid_date_range(client):
    # start_date > end_date must return 400 Bad Request
    response = client.get("/api/weather/historical?start_date=2026-10-10&end_date=2026-10-01")
    assert response.status_code == 400
    assert "cannot be after end_date" in response.json()["detail"]

def test_weather_historical_api_failure(client):
    mock_failure = {
        "success": False,
        "dataframe": None,
        "error": "NASA POWER server unavailable"
    }
    with patch("api.routes.weather.fetch_nasa_power_historical", return_value=mock_failure):
        response = client.get("/api/weather/historical?start_date=2026-10-01&end_date=2026-10-07")
        assert response.status_code == 502
        assert "NASA POWER API Error" in response.json()["detail"]

# 4. Irrigation Schedule Endpoint Tests
def test_irrigation_schedule_valid_scenario(client):
    payload = {
        "crop": "Rice",
        "growth_stage": "Development",
        "soil_type": "Loamy",
        "weather_source": "sample_coimbatore_7day",
        "field_area_acres": 1.0,
        "initial_water_depth_mm": 25.0
    }
    response = client.post("/api/irrigation/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["crop"] == "Rice"
    assert data["growth_stage"] == "Development"
    assert len(data["daily_schedule"]) == 7
    scorecard = data["water_reduction_scorecard"]
    assert scorecard["water_savings_percent"] >= 15.0
    assert scorecard["meets_conservation_target"] is True
    assert data["totals"]["total_eto_mm"] > 0.0

def test_irrigation_schedule_invalid_crop(client):
    payload = {
        "crop": "Pineapple",
        "growth_stage": "Development",
        "soil_type": "Loamy",
        "weather_source": "sample_coimbatore_7day"
    }
    response = client.post("/api/irrigation/schedule", json=payload)
    assert response.status_code == 400
    assert "Unsupported crop" in response.json()["detail"]

def test_irrigation_schedule_invalid_soil(client):
    payload = {
        "crop": "Rice",
        "growth_stage": "Development",
        "soil_type": "VolcanicAsh",
        "weather_source": "sample_coimbatore_7day"
    }
    response = client.post("/api/irrigation/schedule", json=payload)
    assert response.status_code == 400
    assert "Unsupported soil type" in response.json()["detail"]

def test_irrigation_schedule_custom_weather_records(client):
    custom_records = []
    for day in range(1, 8):
        custom_records.append({
            "date": f"2026-11-0{day}",
            "temp_max": 32.0,
            "temp_min": 22.0,
            "temp_mean": 27.0,
            "humidity_mean": 70.0,
            "wind_speed_2m": 2.0,
            "solar_radiation": 18.0,
            "rainfall": 0.0,
            "pressure_kpa": 96.5
        })

    payload = {
        "crop": "Maize",
        "growth_stage": "Development",
        "soil_type": "Sandy Loam",
        "weather_source": "custom_records",
        "field_area_acres": 2.0,
        "custom_weather_records": custom_records
    }
    response = client.post("/api/irrigation/schedule", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["crop"] == "Maize"
    assert data["provenance_status"] == "USER_CUSTOM_CSV"
    assert len(data["daily_schedule"]) == 7

# 5. Advisory Endpoint Tests
def test_advisory_endpoint_deterministic_fallback(client):
    # Mock NexusClient.is_configured to False to verify fallback generation
    with patch("src.nexus_client.NexusClient.is_configured", return_value=False):
        schedule_dummy = {
            "metadata": {
                "crop": "Rice",
                "growth_stage": "Development",
                "soil_type": "Loamy",
                "field_area_val": 1.0,
                "field_area_unit": "Acre"
            },
            "schedule_records": [
                {
                    "day_number": 1,
                    "date": "2026-10-01",
                    "eto_mm": 4.5,
                    "etc_mm": 5.1,
                    "rainfall_mm": 0.0,
                    "effective_rainfall_mm": 0.0,
                    "decision": "IRRIGATE",
                    "recommended_irrigation_mm": 30.0,
                    "irrigation_volume_litres": 121406,
                    "reason": "Water level dropped below threshold."
                }
            ],
            "total_eto_mm": 30.0,
            "total_etc_mm": 34.5,
            "total_rainfall_mm": 0.0,
            "total_effective_rainfall_mm": 0.0,
            "total_irrigation_recommended_mm": 30.0,
            "total_irrigation_volume_litres": 121406,
            "baseline_irrigation_mm": 90.0,
            "baseline_irrigation_litres": 364217,
            "water_savings_mm": 60.0,
            "water_savings_litres": 242811,
            "water_savings_pct": 66.7
        }
        response = client.post("/api/advisory", json={
            "schedule_result": schedule_dummy,
            "language": "English",
            "farmer_name": "Ramu"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["language"] == "English"
        assert len(data["advisory_markdown"]) > 0
        assert data["is_fallback"] is True


def test_advisory_endpoint_telugu_language(client):
    """Test Telugu advisory request via API."""
    with patch("src.nexus_client.NexusClient.is_configured", return_value=False):
        schedule_dummy = {
            "metadata": {
                "crop": "Rice",
                "growth_stage": "Development",
                "soil_type": "Loamy",
                "field_area_val": 1.0,
                "field_area_unit": "Acre"
            },
            "schedule_records": [
                {
                    "day_number": 1,
                    "date": "2026-10-01",
                    "eto_mm": 4.5,
                    "etc_mm": 5.1,
                    "rainfall_mm": 0.0,
                    "effective_rainfall_mm": 0.0,
                    "decision": "IRRIGATE",
                    "recommended_irrigation_mm": 30.0,
                    "irrigation_volume_litres": 121406,
                    "reason": "Water level dropped below threshold."
                }
            ],
            "total_eto_mm": 30.0,
            "total_etc_mm": 34.5,
            "total_rainfall_mm": 0.0,
            "total_effective_rainfall_mm": 0.0,
            "total_irrigation_recommended_mm": 30.0,
            "total_irrigation_volume_litres": 121406,
            "baseline_irrigation_mm": 90.0,
            "baseline_irrigation_litres": 364217,
            "water_savings_mm": 60.0,
            "water_savings_litres": 242811,
            "water_savings_pct": 66.7
        }
        response = client.post("/api/advisory", json={
            "schedule_result": schedule_dummy,
            "language": "Telugu",
            "farmer_name": "Ramu"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["language"] == "Telugu"
        assert "నీటిపారుదల సలహాదారు" in data["advisory_markdown"]
        assert "వరి" in data["advisory_markdown"]


def test_advisory_endpoint_invalid_language_rejected(client):
    """Verify that unsupported languages return HTTP 422."""
    schedule_dummy = {
        "metadata": {"crop": "Rice", "growth_stage": "Development", "soil_type": "Loamy", "field_area_val": 1.0, "field_area_unit": "Acre"},
        "schedule_records": [],
        "total_eto_mm": 0, "total_etc_mm": 0, "total_rainfall_mm": 0, "total_effective_rainfall_mm": 0,
        "total_irrigation_recommended_mm": 0, "total_irrigation_volume_litres": 0,
        "baseline_irrigation_mm": 0, "baseline_irrigation_litres": 0,
        "water_savings_mm": 0, "water_savings_litres": 0, "water_savings_pct": 0
    }
    # Tamil was removed in Phase 3 and must be rejected with 422
    response_tam = client.post("/api/advisory", json={"schedule_result": schedule_dummy, "language": "Tamil"})
    assert response_tam.status_code == 422
    assert "Unsupported language 'Tamil'" in response_tam.json()["detail"]

    # French must be rejected with 422
    response_fr = client.post("/api/advisory", json={"schedule_result": schedule_dummy, "language": "French"})
    assert response_fr.status_code == 422
    assert "Unsupported language 'French'" in response_fr.json()["detail"]

# 6. Approval Endpoint Tests
def test_approval_endpoint_valid(client, tmp_path):
    payload = {
        "schedule_id": "sch_test_12345",
        "decision": "APPROVED",
        "farmer_name": "Ramu",
        "field_notes": "Field tested bund retention",
        "approved_depth_mm": 45.0,
        "approved_volume_litres": 182100,
        "crop": "Rice",
        "field_area_acres": 1.0
    }
    with patch("src.db_client.is_supabase_configured", return_value=False), \
         patch("src.approval_logger.is_supabase_configured", return_value=False), \
         patch("src.db_client.LOCAL_SCHEDULES_FILE", tmp_path / "schedules_store.json"), \
         patch("src.approval_logger.APPROVAL_FILE", tmp_path / "approved_schedules.json"):
        response = client.post("/api/approval", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["decision"] == "APPROVED"
    assert data["schedule_id"] == "sch_test_12345"
    assert data["approval_id"].startswith("appr_")
    assert "manual" in data["message"].lower()

def test_approval_endpoint_invalid_decision(client):
    payload = {
        "schedule_id": "sch_test_12345",
        "decision": "MAYBE",
        "farmer_name": "Ramu",
        "approved_depth_mm": 45.0,
        "approved_volume_litres": 182100
    }
    response = client.post("/api/approval", json=payload)
    # Pydantic regex pattern validation returns 422
    assert response.status_code in [400, 422]
