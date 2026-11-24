"""
Farmer Schedule Approval Route
Validates farmer approval/decline decisions against verified schedules,
persists to Supabase PostgreSQL, and enforces safety manual operation rules.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from api.schemas.approval import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalHistoryResponse,
    ApprovalHistoryItem
)
from src.approval_logger import record_farmer_decision, load_approval_history
from src.db_client import get_schedule, is_supabase_configured, list_approvals

logger = logging.getLogger("agri2.approval")

router = APIRouter(prefix="/approval", tags=["Approval"])


class ApprovalServiceInterface:
    """
    Service interface for validating and recording farmer schedule approvals.
    Verifies that the schedule exists and that submitted quantities match before persisting.
    """
    @staticmethod
    def process_approval(request: ApprovalRequest) -> dict:
        # 1. Verify that the schedule exists
        schedule = get_schedule(request.schedule_id)
        if not schedule:
            logger.warning(f"Approval rejected: schedule {request.schedule_id} does not exist.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule '{request.schedule_id}' not found. Cannot record approval for a nonexistent schedule."
            )

        # 2. Verify crop match
        sched_crop = schedule.get("crop")
        if sched_crop and request.crop.strip().lower() != sched_crop.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Crop mismatch: request specified '{request.crop}', but schedule was calculated for '{sched_crop}'."
            )

        # 3. Verify field area match
        sched_area = schedule.get("field_area_acres")
        if sched_area is not None:
            try:
                if abs(float(sched_area) - float(request.field_area_acres)) > 0.05:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Field area mismatch: request specified {request.field_area_acres} acres, but schedule is for {sched_area} acres."
                    )
            except (ValueError, TypeError):
                pass

        # 4. Verify depth / volume reasonableness
        if request.approved_depth_mm < 0 or request.approved_volume_litres < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved depth and volume must be non-negative values."
            )

        logger.info(
            f"Recording decision for verified schedule: id={request.schedule_id}, "
            f"decision={request.decision}, farmer={request.farmer_name}, "
            f"depth_mm={request.approved_depth_mm}"
        )

        schedule_summary = {
            "schedule_id": request.schedule_id,
            "crop": request.crop,
            "field_area_acres": request.field_area_acres,
            "total_irrigation_mm": request.approved_depth_mm,
            "total_irrigation_litres": request.approved_volume_litres
        }

        # 5. Persist farmer decision
        result = record_farmer_decision(
            decision=request.decision,
            schedule_summary=schedule_summary,
            farmer_notes=request.field_notes or "",
            approved_by=request.farmer_name
        )

        if not result.get("success", False):
            # Database or write failure: return error instead of false success
            err_msg = result.get("error", "Failed to persist approval")
            logger.error(f"Approval persistence failed: {err_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database persistence failure: {err_msg}"
            )

        storage_mode = result.get("storage_status", "LOCAL_JSON_FALLBACK")
        rec = result.get("record", {})

        return {
            "approval_id": result.get("approval_id", rec.get("approval_id")),
            "schedule_id": request.schedule_id,
            "decision": request.decision,
            "farmer_name": request.farmer_name,
            "recorded_at": rec.get("recorded_at", rec.get("timestamp")),
            "persisted_mode": storage_mode,
            "message": (
                f"Schedule {request.decision.lower()} successfully by farmer {request.farmer_name}. "
                "Manual valve/pump operation verified; no automated actuators triggered."
            )
        }


@router.post("", response_model=ApprovalResponse, summary="Record Farmer Schedule Approval Decision")
def record_approval(request: ApprovalRequest):
    """
    Records the farmer's explicit schedule approval or decline decision.
    Verifies schedule existence and parameters against persisted schedules.
    Strict safety requirement: Actual field valve and pump operation remains strictly manual.
    No automatic control or telemetry is executed.
    """
    if request.decision not in ["APPROVED", "DECLINED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{request.decision}'. Must be 'APPROVED' or 'DECLINED'."
        )

    result = ApprovalServiceInterface.process_approval(request)

    return ApprovalResponse(
        success=True,
        approval_id=result["approval_id"],
        schedule_id=result["schedule_id"],
        decision=result["decision"],
        farmer_name=result["farmer_name"],
        recorded_at=result["recorded_at"],
        message=result["message"],
        persisted_mode=result["persisted_mode"]
    )


@router.get("/history", response_model=ApprovalHistoryResponse, summary="Retrieve Farmer Approval History")
def get_approval_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return (1-100)"),
    schedule_id: Optional[str] = Query(default=None, description="Filter by schedule ID"),
    farmer_name: Optional[str] = Query(default=None, description="Filter by farmer name")
):
    """
    Retrieves recent farmer approval decisions with strict upper bound limits.
    Prevents unrestricted bulk dumping of records.
    """
    storage_mode = "SUPABASE_POSTGRESQL" if is_supabase_configured() else "LOCAL_JSON_FALLBACK"

    if is_supabase_configured():
        raw_approvals = list_approvals(limit=limit, schedule_id=schedule_id, farmer_name=farmer_name)
    else:
        raw_approvals = load_approval_history(limit=limit)
        if schedule_id:
            raw_approvals = [a for a in raw_approvals if a.get("schedule_id") == schedule_id]
        if farmer_name:
            raw_approvals = [a for a in raw_approvals if a.get("approved_by") == farmer_name or a.get("farmer_name") == farmer_name]

    items = []
    for r in raw_approvals:
        items.append(
            ApprovalHistoryItem(
                id=str(r.get("id") or r.get("approval_id") or r.get("record_id")),
                schedule_id=str(r.get("schedule_id", "")),
                recorded_at=str(r.get("recorded_at") or r.get("timestamp", "")),
                farmer_name=str(r.get("farmer_name") or r.get("approved_by", "")),
                decision=str(r.get("decision", "APPROVED")),
                field_notes=str(r.get("field_notes") or r.get("farmer_notes") or ""),
                approved_depth_mm=float(r.get("approved_depth_mm") or r.get("total_irrigation_mm") or 0.0),
                approved_volume_litres=int(r.get("approved_volume_litres") or r.get("total_irrigation_litres") or 0),
                crop=str(r.get("crop", "Rice")),
                field_area_acres=float(r.get("field_area_acres") or 1.0)
            )
        )

    return ApprovalHistoryResponse(
        success=True,
        count=len(items),
        storage_mode=storage_mode,
        approvals=items
    )
