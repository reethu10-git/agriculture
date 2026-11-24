"""
AI Advisory Generation Route
"""
from fastapi import APIRouter, HTTPException, status
from api.schemas.advisory import AdvisoryRequest, AdvisoryResponse
from src.advisory_generator import generate_farmer_advisory, generate_fallback_advisory
from src.nexus_client import NexusClient

router = APIRouter(prefix="/advisory", tags=["AI Advisory"])

def _normalize_schedule_for_advisory(data: dict) -> dict:
    """Adapts either raw scheduler output or API IrrigationScheduleResponse to the advisory generator schema."""
    if "schedule_records" in data and "total_irrigation_recommended_mm" in data:
        return data

    daily = data.get("daily_schedule", [])
    records = []
    for r in daily:
        records.append({
            "day_number": r.get("day_index", 1),
            "date": r.get("date", ""),
            "eto_mm": r.get("eto_mm", 0.0),
            "kc": r.get("kc", 1.0),
            "etc_mm": r.get("etc_mm", 0.0),
            "rainfall_mm": r.get("rainfall_mm", 0.0),
            "effective_rainfall_mm": r.get("effective_rainfall_mm", 0.0),
            "recommended_irrigation_mm": r.get("irrigation_depth_mm", 0.0),
            "irrigation_volume_litres": r.get("irrigation_volume_litres", 0),
            "decision": r.get("decision", "SKIP"),
            "reason": r.get("reason", "")
        })

    totals = data.get("totals", {})
    scorecard = data.get("water_reduction_scorecard", {})

    meta = {
        "crop": data.get("crop", "Rice"),
        "growth_stage": data.get("growth_stage", "Development"),
        "soil_type": data.get("soil_type", "Loamy"),
        "field_area_val": data.get("field_area_acres", 1.0),
        "field_area_unit": "Acre"
    }

    return {
        "metadata": meta,
        "schedule_records": records,
        "total_eto_mm": totals.get("total_eto_mm", 0.0),
        "total_etc_mm": totals.get("total_etc_mm", 0.0),
        "total_rainfall_mm": totals.get("total_rainfall_mm", 0.0),
        "total_effective_rainfall_mm": totals.get("total_effective_rainfall_mm", 0.0),
        "total_irrigation_recommended_mm": totals.get("total_irrigation_mm", scorecard.get("recommended_total_depth_mm", 0.0)),
        "total_irrigation_volume_litres": totals.get("total_irrigation_litres", scorecard.get("recommended_volume_litres", 0.0)),
        "baseline_irrigation_mm": scorecard.get("baseline_total_depth_mm", 0.0),
        "baseline_irrigation_litres": scorecard.get("baseline_volume_litres", 0.0),
        "water_savings_mm": scorecard.get("water_saved_depth_mm", 0.0),
        "water_savings_litres": scorecard.get("water_saved_litres", 0.0),
        "water_savings_pct": scorecard.get("water_savings_percent", 0.0)
    }

@router.post("", response_model=AdvisoryResponse, summary="Generate Farmer-Facing Advisory via Nexus AI")
def create_advisory(request: AdvisoryRequest):
    """
    Submits the calculated schedule to Nexus AI (model: gpt-5-nano) for qualitative explanation.
    Supports English and Telugu languages. Invalid languages return HTTP 422.
    Strict computational boundary: The LLM does not perform, modify, or recalculate any water values.
    Falls back gracefully to deterministic rule-based output if offline or unconfigured.
    """
    client = NexusClient()
    lang_clean = request.language.strip().title()
    if lang_clean not in ["English", "Telugu"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{request.language}'. Supported languages are 'English' and 'Telugu'."
        )

    normalized_sched = _normalize_schedule_for_advisory(request.schedule_result)

    try:
        result = generate_farmer_advisory(
            schedule_result=normalized_sched,
            nexus_client=client
        )

        if lang_clean == "Telugu":
            text = result.get("telugu_advisory", "")
        else:
            text = result.get("english_advisory", "")

        is_fallback = bool("Fallback" in result.get("source", ""))
        error_msg = result.get("error")

        # Safety: If model output was empty (e.g. reasoning token exhaustion), use deterministic fallback
        if not text or not text.strip():
            text = generate_fallback_advisory(normalized_sched, language=lang_clean)
            is_fallback = True
            if not error_msg:
                error_msg = "Model returned empty text; deployed precision agronomic fallback."

        return AdvisoryResponse(
            success=True,
            language=lang_clean,
            model_used=client.model if not is_fallback else None,
            advisory_markdown=text,
            is_fallback=is_fallback,
            error_message=error_msg
        )

    except Exception as e:
        fallback_text = generate_fallback_advisory(normalized_sched, language=lang_clean)
        return AdvisoryResponse(
            success=True,
            language=lang_clean,
            model_used=None,
            advisory_markdown=fallback_text,
            is_fallback=True,
            error_message=f"Advisory generation failed: {str(e)}"
        )
