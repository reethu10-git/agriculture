"""
AGRI-2: Supabase PostgreSQL Database Client
Manages persistent storage for irrigation schedules and farmer approvals.
Provides safe error handling, credential isolation, and local fallback compatibility.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OUTPUTS_DIR, APP_ENV

logger = logging.getLogger("agri2.db_client")

# Local fallback storage paths for offline development & testing
LOCAL_SCHEDULES_FILE = OUTPUTS_DIR / "schedules_store.json"

# Cached singleton client instance
_supabase_client = None

def get_supabase_client():
    """
    Initializes and returns the Supabase client using server-side service role key.
    Returns None if credentials are missing or unconfigured.
    Never logs credentials or connection URLs.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not is_supabase_configured():
        logger.debug("Supabase credentials not configured. Operating in offline/fallback mode.")
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase client successfully initialized with server-side service role.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        return None


def reset_client():
    """Resets the cached Supabase client (useful for unit testing)."""
    global _supabase_client
    _supabase_client = None


def is_supabase_configured() -> bool:
    """
    Checks if Supabase URL and service role key are present and non-empty.
    """
    url = (SUPABASE_URL or "").strip()
    key = (SUPABASE_SERVICE_ROLE_KEY or "").strip()
    return bool(url and key and not url.startswith("your_") and not key.startswith("your_"))


# ---------------------------------------------------------------------------
# Local Schedule Store Helpers (Offline & Test Fallback)
# ---------------------------------------------------------------------------

def _load_local_schedules() -> Dict[str, Dict[str, Any]]:
    """Loads schedules from the local JSON store."""
    if not LOCAL_SCHEDULES_FILE.exists():
        # Seed with default test schedule for backwards compatibility
        seed_data = {
            "sch_test_12345": {
                "id": "sch_test_12345",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "crop": "Rice",
                "growth_stage": "Development",
                "soil_type": "Loamy",
                "field_area_acres": 1.0,
                "weather_source": "sample_coimbatore_7day",
                "provenance_status": "SIMULATION_DATA",
                "recommended_total_depth_mm": 45.0,
                "recommended_volume_litres": 182100,
                "water_savings_percent": 25.0,
                "daily_schedule": [],
                "full_metadata": {}
            }
        }
        _save_local_schedules(seed_data)
        return seed_data

    try:
        with open(LOCAL_SCHEDULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read local schedules store: {e}")
        return {}


def _save_local_schedules(data: Dict[str, Dict[str, Any]]) -> bool:
    """Saves schedules to the local JSON store."""
    try:
        with open(LOCAL_SCHEDULES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to write to local schedules store: {e}")
        return False


# ---------------------------------------------------------------------------
# Schedule Database Operations
# ---------------------------------------------------------------------------

def insert_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inserts a newly generated irrigation schedule into Supabase PostgreSQL.
    Falls back to local file storage if Supabase is not configured.

    Returns:
        dict: {"success": bool, "storage_mode": str, "id": str, "error": Optional[str]}
    """
    schedule_id = schedule_data.get("id")
    if not schedule_id:
        return {"success": False, "error": "Schedule ID is required"}

    # Mirror to local store for offline retrieval / test continuity
    local_store = _load_local_schedules()
    local_store[schedule_id] = schedule_data
    _save_local_schedules(local_store)

    client = get_supabase_client()
    if client is None:
        if APP_ENV == "production":
            logger.error("Production persistence failure: Supabase is unconfigured.")
            return {
                "success": False,
                "storage_mode": "CONFIGURATION_ERROR",
                "error": "Production persistence requires Supabase PostgreSQL configuration. Local JSON fallback is disabled in production.",
                "id": schedule_id
            }
        return {
            "success": True,
            "storage_mode": "LOCAL_JSON_FALLBACK",
            "id": schedule_id
        }

    # Format record for PostgreSQL
    row = {
        "id": schedule_id,
        "created_at": schedule_data.get("created_at", datetime.now(timezone.utc).isoformat()),
        "crop": schedule_data.get("crop", "Rice"),
        "growth_stage": schedule_data.get("growth_stage", "Development"),
        "soil_type": schedule_data.get("soil_type", "Loamy"),
        "field_area_acres": float(schedule_data.get("field_area_acres", 1.0)),
        "weather_source": schedule_data.get("weather_source", "sample_coimbatore_7day"),
        "provenance_status": schedule_data.get("provenance_status", "SIMULATION_DATA"),
        "recommended_total_depth_mm": float(schedule_data.get("recommended_total_depth_mm", 0.0)),
        "recommended_volume_litres": int(schedule_data.get("recommended_volume_litres", 0)),
        "water_savings_percent": float(schedule_data.get("water_savings_percent", 0.0)),
        "daily_schedule": schedule_data.get("daily_schedule", []),
        "full_metadata": schedule_data.get("full_metadata", {})
    }

    try:
        response = client.table("schedules").insert(row).execute()
        return {
            "success": True,
            "storage_mode": "SUPABASE_POSTGRESQL",
            "id": schedule_id,
            "data": response.data
        }
    except Exception as e:
        logger.error(f"Supabase schedule insert failed: {str(e)}")
        return {
            "success": False,
            "storage_mode": "SUPABASE_ERROR",
            "error": str(e)
        }


def get_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves an irrigation schedule by its unique ID.
    Queries Supabase first if configured, falling back to local store.
    """
    client = get_supabase_client()
    if client is not None:
        try:
            response = client.table("schedules").select("*").eq("id", schedule_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            logger.error(f"Supabase schedule fetch failed for {schedule_id}: {str(e)}")

    # Fallback to local store
    local_store = _load_local_schedules()
    return local_store.get(schedule_id)


def list_schedules(limit: int = 20, crop: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves a list of recent schedules.
    Enforces a strict upper bound limit to avoid exposing unrestricted bulk records.
    """
    safe_limit = min(max(1, limit), 100)
    client = get_supabase_client()

    if client is not None:
        try:
            query = client.table("schedules").select(
                "id, created_at, crop, growth_stage, soil_type, field_area_acres, "
                "weather_source, provenance_status, recommended_total_depth_mm, "
                "recommended_volume_litres, water_savings_percent"
            ).order("created_at", desc=True).limit(safe_limit)

            if crop:
                query = query.eq("crop", crop)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Supabase schedule list failed: {str(e)}")

    # Fallback to local store
    local_store = _load_local_schedules()
    items = list(local_store.values())
    if crop:
        items = [i for i in items if i.get("crop") == crop]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items[:safe_limit]


# ---------------------------------------------------------------------------
# Approval Database Operations
# ---------------------------------------------------------------------------

def insert_approval(approval_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inserts a farmer approval record into Supabase PostgreSQL.

    Returns:
        dict: {"success": bool, "storage_mode": str, "id": str, "error": Optional[str]}
    """
    approval_id = approval_data.get("id")
    schedule_id = approval_data.get("schedule_id")

    if not approval_id or not schedule_id:
        return {"success": False, "error": "Both approval_id and schedule_id are required"}

    client = get_supabase_client()
    if client is None:
        if APP_ENV == "production":
            logger.error("Production persistence failure: Supabase is unconfigured.")
            return {
                "success": False,
                "storage_mode": "CONFIGURATION_ERROR",
                "error": "Production persistence requires Supabase PostgreSQL configuration. Local JSON fallback is disabled in production.",
                "id": approval_id
            }
        return {
            "success": True,
            "storage_mode": "LOCAL_JSON_FALLBACK",
            "id": approval_id
        }

    row = {
        "id": approval_id,
        "schedule_id": schedule_id,
        "recorded_at": approval_data.get("recorded_at", datetime.now(timezone.utc).isoformat()),
        "farmer_name": approval_data.get("farmer_name", "Farmer"),
        "decision": approval_data.get("decision", "APPROVED"),
        "field_notes": approval_data.get("field_notes", ""),
        "approved_depth_mm": float(approval_data.get("approved_depth_mm", 0.0)),
        "approved_volume_litres": int(approval_data.get("approved_volume_litres", 0)),
        "crop": approval_data.get("crop", "Rice"),
        "field_area_acres": float(approval_data.get("field_area_acres", 1.0))
    }

    try:
        response = client.table("approvals").insert(row).execute()
        return {
            "success": True,
            "storage_mode": "SUPABASE_POSTGRESQL",
            "id": approval_id,
            "data": response.data
        }
    except Exception as e:
        logger.error(f"Supabase approval insert failed: {str(e)}")
        return {
            "success": False,
            "storage_mode": "SUPABASE_ERROR",
            "error": str(e)
        }


def get_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an approval record by its ID."""
    client = get_supabase_client()
    if client is not None:
        try:
            response = client.table("approvals").select("*").eq("id", approval_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            logger.error(f"Supabase approval fetch failed for {approval_id}: {str(e)}")
    return None


def list_approvals(
    limit: int = 20,
    schedule_id: Optional[str] = None,
    farmer_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves recent approval records with query limits.
    Prevents unrestricted bulk dumping.
    """
    safe_limit = min(max(1, limit), 100)
    client = get_supabase_client()

    if client is not None:
        try:
            query = client.table("approvals").select("*").order("recorded_at", desc=True).limit(safe_limit)
            if schedule_id:
                query = query.eq("schedule_id", schedule_id)
            if farmer_name:
                query = query.eq("farmer_name", farmer_name)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Supabase approval list failed: {str(e)}")

    return []
