"""
Unit and Integration Tests for Phase 4 Supabase PostgreSQL Integration
Mocks Supabase client to test persistence, error handling, local offline fallbacks,
retrieval endpoints, and verification checks without requiring a live database.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.index import app
from src.db_client import (
    is_supabase_configured,
    get_supabase_client,
    insert_schedule,
    get_schedule,
    list_schedules,
    insert_approval,
    get_approval,
    list_approvals,
    reset_client
)
from src.approval_logger import record_farmer_decision, load_approval_history

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def clean_client():
    reset_client()
    yield
    reset_client()

# ---------------------------------------------------------------------------
# 1. Missing Supabase Configuration & Offline Fallback Tests
# ---------------------------------------------------------------------------

def test_missing_supabase_configuration():
    """Verify safe behavior when Supabase credentials are missing or empty."""
    with patch("src.db_client.SUPABASE_URL", ""), patch("src.db_client.SUPABASE_SERVICE_ROLE_KEY", ""):
        assert is_supabase_configured() is False
        assert get_supabase_client() is None

def test_production_persistence_enforcement_missing_supabase(client):
    """Verify that in production (APP_ENV=production), unconfigured Supabase fails without silent local fallback."""
    with patch("src.db_client.APP_ENV", "production"), \
         patch("src.db_client.is_supabase_configured", return_value=False), \
         patch("src.approval_logger.APP_ENV", "production"), \
         patch("src.approval_logger.is_supabase_configured", return_value=False):

        # Schedule insertion must return error and not fallback to local JSON
        res_sched = insert_schedule({"id": "sch_prod_err", "crop": "Rice"})
        assert res_sched["success"] is False
        assert res_sched["storage_mode"] == "CONFIGURATION_ERROR"
        assert "Production persistence requires Supabase" in res_sched["error"]

        # Approval insertion must return error and not fallback to local JSON
        res_appr = insert_approval({"id": "appr_prod_err", "schedule_id": "sch_prod_err"})
        assert res_appr["success"] is False
        assert res_appr["storage_mode"] == "CONFIGURATION_ERROR"
        assert "Production persistence requires Supabase" in res_appr["error"]

        # Farmer approval decision recording must return error
        res_dec = record_farmer_decision(
            decision="APPROVED",
            schedule_summary={"schedule_id": "sch_prod_err", "crop": "Rice", "field_area_acres": 1.0}
        )
        assert res_dec["success"] is False
        assert res_dec["storage_status"] == "CONFIGURATION_ERROR"


def test_local_offline_fallback(client, tmp_path):
    """Verify that schedule calculation and approval fall back to local storage when offline."""
    with patch("src.db_client.is_supabase_configured", return_value=False), \
         patch("src.approval_logger.is_supabase_configured", return_value=False), \
         patch("src.db_client.LOCAL_SCHEDULES_FILE", tmp_path / "schedules_store.json"), \
         patch("src.approval_logger.APPROVAL_FILE", tmp_path / "approved_schedules.json"):
        # 1. Generate schedule
        sched_resp = client.post("/api/irrigation/schedule", json={
            "crop": "Rice",
            "growth_stage": "Development",
            "soil_type": "Loamy",
            "field_area_acres": 1.0,
            "weather_source": "sample_coimbatore_7day"
        })
        assert sched_resp.status_code == 200
        sched_data = sched_resp.json()
        assert sched_data["success"] is True
        schedule_id = sched_data["schedule_id"]
        assert sched_data["metadata"]["storage_mode"] == "LOCAL_JSON_FALLBACK"

        # 2. Record approval for generated schedule
        appr_resp = client.post("/api/approval", json={
            "schedule_id": schedule_id,
            "decision": "APPROVED",
            "farmer_name": "Murugan",
            "field_notes": "Local offline test note",
            "approved_depth_mm": sched_data["totals"]["total_irrigation_mm"],
            "approved_volume_litres": int(sched_data["totals"]["total_irrigation_litres"]),
            "crop": "Rice",
            "field_area_acres": 1.0
        })
        assert appr_resp.status_code == 200
        appr_data = appr_resp.json()
        assert appr_data["success"] is True
        assert appr_data["persisted_mode"] == "LOCAL_JSON_FALLBACK"
        assert appr_data["schedule_id"] == schedule_id

# ---------------------------------------------------------------------------
# 2. Successful Insertion Tests (Mocked Supabase)
# ---------------------------------------------------------------------------

def test_successful_schedule_insertion_mocked(client):
    """Verify schedule insertion into Supabase PostgreSQL when configured."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock(data=[{"id": "sch_mock_123"}])

    with patch("src.db_client.is_supabase_configured", return_value=True), \
         patch("src.db_client.get_supabase_client", return_value=mock_sb):

        resp = client.post("/api/irrigation/schedule", json={
            "crop": "Rice",
            "growth_stage": "Development",
            "soil_type": "Loamy",
            "field_area_acres": 1.0,
            "weather_source": "sample_coimbatore_7day"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["metadata"]["storage_mode"] == "SUPABASE_POSTGRESQL"
        assert mock_sb.table.called
        assert mock_sb.table.call_args[0][0] == "schedules"

def test_successful_approval_insertion_mocked(client):
    """Verify approval insertion into Supabase PostgreSQL when configured."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock(data=[{"id": "appr_mock_123"}])

    with patch("src.db_client.is_supabase_configured", return_value=True), \
         patch("src.db_client.get_supabase_client", return_value=mock_sb), \
         patch("src.approval_logger.is_supabase_configured", return_value=True), \
         patch("api.routes.approval.is_supabase_configured", return_value=True):

        # Pre-seed schedule lookup
        fake_schedule = {
            "id": "sch_valid_123",
            "crop": "Rice",
            "field_area_acres": 1.0,
            "recommended_total_depth_mm": 45.0,
            "recommended_volume_litres": 182100
        }
        with patch("api.routes.approval.get_schedule", return_value=fake_schedule):
            resp = client.post("/api/approval", json={
                "schedule_id": "sch_valid_123",
                "decision": "APPROVED",
                "farmer_name": "Ramu",
                "field_notes": "Reviewed and approved",
                "approved_depth_mm": 45.0,
                "approved_volume_litres": 182100,
                "crop": "Rice",
                "field_area_acres": 1.0
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["persisted_mode"] == "SUPABASE_POSTGRESQL"
            assert data["decision"] == "APPROVED"
            assert mock_sb.table.called
            assert mock_sb.table.call_args[0][0] == "approvals"

# ---------------------------------------------------------------------------
# 3. Database Connection Failure & Resilience Tests
# ---------------------------------------------------------------------------

def test_database_connection_failure():
    """Verify graceful handling when database connection or insert throws an exception."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.side_effect = Exception("Connection refused / timeout to Supabase")

    with patch("src.db_client.is_supabase_configured", return_value=True), \
         patch("src.db_client.get_supabase_client", return_value=mock_sb):

        # 1. Schedule insert failure
        res_sched = insert_schedule({"id": "sch_err_1", "crop": "Rice"})
        assert res_sched["success"] is False
        assert res_sched["storage_mode"] == "SUPABASE_ERROR"
        assert "Connection refused" in res_sched["error"]

        # 2. Approval insert failure
        res_appr = insert_approval({"id": "appr_err_1", "schedule_id": "sch_err_1"})
        assert res_appr["success"] is False
        assert res_appr["storage_mode"] == "SUPABASE_ERROR"
        assert "Connection refused" in res_appr["error"]

def test_no_false_success_response_when_persistence_fails(client):
    """
    Verify that when Supabase is configured and write fails, the API does NOT
    return a false success response to the farmer.
    """
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_sb.table.return_value = mock_table
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.side_effect = Exception("PostgreSQL disk full or network partition")

    fake_schedule = {
        "id": "sch_valid_123",
        "crop": "Rice",
        "field_area_acres": 1.0,
        "recommended_total_depth_mm": 45.0,
        "recommended_volume_litres": 182100
    }

    with patch("src.db_client.is_supabase_configured", return_value=True), \
         patch("src.db_client.get_supabase_client", return_value=mock_sb), \
         patch("src.approval_logger.is_supabase_configured", return_value=True), \
         patch("api.routes.approval.is_supabase_configured", return_value=True), \
         patch("api.routes.approval.get_schedule", return_value=fake_schedule):

        resp = client.post("/api/approval", json={
            "schedule_id": "sch_valid_123",
            "decision": "APPROVED",
            "farmer_name": "Ramu",
            "field_notes": "Network partition test",
            "approved_depth_mm": 45.0,
            "approved_volume_litres": 182100,
            "crop": "Rice",
            "field_area_acres": 1.0
        })

        # MUST NOT return 200 with false success!
        assert resp.status_code == 500
        data = resp.json()
        assert "Database persistence failure" in data["detail"]

# ---------------------------------------------------------------------------
# 4. Schedule Verification & Validation Tests
# ---------------------------------------------------------------------------

def test_invalid_schedule_id():
    """Verify that schedule insertion without an ID is rejected."""
    res = insert_schedule({})
    assert res["success"] is False
    assert "Schedule ID is required" in res["error"]

def test_approval_for_nonexistent_schedule(client):
    """Verify that an approval for a nonexistent schedule is rejected with 404."""
    with patch("api.routes.approval.get_schedule", return_value=None):
        resp = client.post("/api/approval", json={
            "schedule_id": "sch_nonexistent_99999",
            "decision": "APPROVED",
            "farmer_name": "Ramu",
            "approved_depth_mm": 45.0,
            "approved_volume_litres": 182100,
            "crop": "Rice",
            "field_area_acres": 1.0
        })
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

def test_approval_crop_mismatch_rejected(client):
    """Verify that an approval specifying a different crop than the schedule is rejected."""
    fake_schedule = {
        "id": "sch_rice_only",
        "crop": "Rice",
        "field_area_acres": 1.0
    }
    with patch("api.routes.approval.get_schedule", return_value=fake_schedule):
        resp = client.post("/api/approval", json={
            "schedule_id": "sch_rice_only",
            "decision": "APPROVED",
            "farmer_name": "Ramu",
            "approved_depth_mm": 45.0,
            "approved_volume_litres": 182100,
            "crop": "Tomato",  # Mismatch!
            "field_area_acres": 1.0
        })
        assert resp.status_code == 400
        assert "Crop mismatch" in resp.json()["detail"]

def test_approval_field_area_mismatch_rejected(client):
    """Verify that an approval specifying an area mismatch is rejected."""
    fake_schedule = {
        "id": "sch_1acre",
        "crop": "Rice",
        "field_area_acres": 1.0
    }
    with patch("api.routes.approval.get_schedule", return_value=fake_schedule):
        resp = client.post("/api/approval", json={
            "schedule_id": "sch_1acre",
            "decision": "APPROVED",
            "farmer_name": "Ramu",
            "approved_depth_mm": 45.0,
            "approved_volume_litres": 182100,
            "crop": "Rice",
            "field_area_acres": 5.0  # Mismatch!
        })
        assert resp.status_code == 400
        assert "Field area mismatch" in resp.json()["detail"]

def test_invalid_approval_decision(client):
    """Verify that decisions other than APPROVED or DECLINED are rejected."""
    resp = client.post("/api/approval", json={
        "schedule_id": "sch_test_12345",
        "decision": "MAYBE",
        "farmer_name": "Ramu",
        "approved_depth_mm": 45.0,
        "approved_volume_litres": 182100,
        "crop": "Rice",
        "field_area_acres": 1.0
    })
    assert resp.status_code in [400, 422]

# ---------------------------------------------------------------------------
# 5. Database Retrieval & History Endpoints Tests
# ---------------------------------------------------------------------------

def test_database_retrieval_schedules(client):
    """Verify schedule history retrieval via GET /api/irrigation/history from Supabase."""
    mock_records = [
        {
            "id": "sch_hist_1",
            "created_at": "2026-11-24T10:00:00Z",
            "crop": "Rice",
            "growth_stage": "Development",
            "soil_type": "Loamy",
            "field_area_acres": 1.0,
            "weather_source": "sample_coimbatore_7day",
            "provenance_status": "SIMULATION_DATA",
            "recommended_total_depth_mm": 42.5,
            "recommended_volume_litres": 172000,
            "water_savings_percent": 22.0
        }
    ]
    with patch("api.routes.irrigation.is_supabase_configured", return_value=True), \
         patch("api.routes.irrigation.list_schedules", return_value=mock_records):
        resp = client.get("/api/irrigation/history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["storage_mode"] == "SUPABASE_POSTGRESQL"
        assert data["count"] == 1
        assert data["schedules"][0]["id"] == "sch_hist_1"
        assert data["schedules"][0]["crop"] == "Rice"

def test_database_retrieval_approvals(client):
    """Verify approval history retrieval via GET /api/approval/history from Supabase."""
    mock_records = [
        {
            "id": "appr_hist_1",
            "schedule_id": "sch_hist_1",
            "recorded_at": "2026-11-24T10:05:00Z",
            "farmer_name": "Ramu",
            "decision": "APPROVED",
            "field_notes": "All checks passed",
            "approved_depth_mm": 42.5,
            "approved_volume_litres": 172000,
            "crop": "Rice",
            "field_area_acres": 1.0
        }
    ]
    with patch("api.routes.approval.is_supabase_configured", return_value=True), \
         patch("api.routes.approval.list_approvals", return_value=mock_records):
        resp = client.get("/api/approval/history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["storage_mode"] == "SUPABASE_POSTGRESQL"
        assert data["count"] == 1
        assert data["approvals"][0]["id"] == "appr_hist_1"
        assert data["approvals"][0]["decision"] == "APPROVED"

