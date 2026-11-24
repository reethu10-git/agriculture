"""
AGRI-2: Farmer Schedule Approval Logger
Safely logs farmer schedule reviews, approvals, modifications, and notes.
Persists records to Supabase PostgreSQL when configured, with a resilient local
JSON fallback audit trail in outputs/approved_schedules.json.
Enforces manual operation policy.
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
import json
import logging
from config.settings import OUTPUTS_DIR, APP_ENV
from src.db_client import (
    is_supabase_configured,
    insert_approval,
    list_approvals as db_list_approvals
)

logger = logging.getLogger("agri2.approval_logger")
APPROVAL_FILE = OUTPUTS_DIR / "approved_schedules.json"


def load_approval_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Loads historical approval logs.
    Retrieves from Supabase when configured, otherwise reads from local JSON file.
    """
    if is_supabase_configured():
        records = db_list_approvals(limit=limit)
        if records:
            return records

    if not APPROVAL_FILE.exists():
        return []
    try:
        with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[-limit:] if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Error loading approval history from file: {e}")
        return []


def record_farmer_decision(
    decision: str,
    schedule_summary: Dict[str, Any],
    farmer_notes: str = "",
    approved_by: str = "Farmer / Operator",
    approval_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records a farmer approval or decline decision.
    Persists to Supabase PostgreSQL when configured.
    Falls back to local JSON only when Supabase is not configured.
    Does NOT report false success if Supabase is configured and write fails.

    Args:
        decision: "APPROVED" or "DECLINED"
        schedule_summary: Key metrics of the schedule
        farmer_notes: Optional comments by the farmer
        approved_by: Name of farmer
        approval_id: Optional existing ID, or generated automatically

    Returns:
        Dict[str, Any]: {
            "success": bool,
            "storage_status": str,
            "record": Dict[str, Any],
            "error": Optional[str]
        }
    """
    record_id = approval_id or f"appr_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    schedule_id = schedule_summary.get("schedule_id", "")

    # Clean numeric fields
    depth_mm = float(schedule_summary.get("total_irrigation_mm") or schedule_summary.get("approved_depth_mm") or 0.0)
    vol_litres = int(schedule_summary.get("total_irrigation_litres") or schedule_summary.get("approved_volume_litres") or 0)
    crop = schedule_summary.get("crop", "Rice")
    field_area_raw = schedule_summary.get("field_area_acres") or schedule_summary.get("field_area", 1.0)
    try:
        if isinstance(field_area_raw, str):
            field_area_acres = float(field_area_raw.split()[0])
        else:
            field_area_acres = float(field_area_raw)
    except Exception:
        field_area_acres = 1.0

    record = {
        "approval_id": record_id,
        "record_id": record_id,
        "schedule_id": schedule_id,
        "timestamp": now_iso,
        "recorded_at": now_iso,
        "decision": decision,
        "approved_by": approved_by,
        "farmer_name": approved_by,
        "farmer_notes": farmer_notes,
        "field_notes": farmer_notes,
        "crop": crop,
        "field_area": f"{field_area_acres} Acre",
        "field_area_acres": field_area_acres,
        "total_irrigation_mm": depth_mm,
        "approved_depth_mm": depth_mm,
        "total_irrigation_litres": vol_litres,
        "approved_volume_litres": vol_litres,
        "water_savings_pct": schedule_summary.get("water_savings_pct", 0.0),
        "safety_confirmation": "Farmer confirmed manual valve operation. No automatic valve triggers were initiated."
    }

    # If Supabase is configured, write to PostgreSQL
    if is_supabase_configured():
        db_payload = {
            "id": record_id,
            "schedule_id": schedule_id,
            "recorded_at": now_iso,
            "farmer_name": approved_by,
            "decision": decision,
            "field_notes": farmer_notes,
            "approved_depth_mm": depth_mm,
            "approved_volume_litres": vol_litres,
            "crop": crop,
            "field_area_acres": field_area_acres
        }

        db_res = insert_approval(db_payload)

        if not db_res.get("success", False):
            # Database persistence failed: DO NOT falsely report success
            logger.error(f"Persistent database approval write failed: {db_res.get('error')}")
            return {
                "success": False,
                "storage_status": "DATABASE_ERROR",
                "error": f"Database write failed: {db_res.get('error')}",
                "approval_id": record_id,
                "record": record
            }

        # Also write locally for offline redundancy if in dev
        if APP_ENV != "production":
            _append_local_approval(record)

        return {
            "success": True,
            "storage_status": "SUPABASE_POSTGRESQL",
            "approval_id": record_id,
            "record": record
        }

    # If Supabase is NOT configured in production, fail explicitly (no silent fallback)
    if APP_ENV == "production":
        logger.error("Production persistence failure: Supabase is unconfigured. Local JSON fallback is disabled in production.")
        return {
            "success": False,
            "storage_status": "CONFIGURATION_ERROR",
            "error": "Production persistence requires Supabase PostgreSQL configuration. Local JSON fallback is disabled in production.",
            "approval_id": record_id,
            "record": record
        }

    # Offline development fallback
    saved_local = _append_local_approval(record)
    if not saved_local:
        return {
            "success": False,
            "storage_status": "LOCAL_WRITE_ERROR",
            "error": "Failed to write approval to local JSON fallback",
            "approval_id": record_id,
            "record": record
        }

    return {
        "success": True,
        "storage_status": "LOCAL_JSON_FALLBACK",
        "approval_id": record_id,
        "record": record
    }


def _append_local_approval(record: Dict[str, Any]) -> bool:
    """Appends an approval record to local JSON file."""
    history = []
    if APPROVAL_FILE.exists():
        try:
            with open(APPROVAL_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except Exception:
            history = []

    history.append(record)

    try:
        with open(APPROVAL_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to append to local approval file: {e}")
        return False
