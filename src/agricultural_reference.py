"""
AGRI-2: Agricultural Reference Data Engine (TNAU Guidelines)
Maintains official rice water management guidelines, critical growth stages,
AWD protocols, and soil-specific irrigation intervals sourced from Tamil Nadu
Agricultural University (TNAU) Agritech Portal.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json

REFERENCE_FILE = Path(__file__).resolve().parent.parent / "data" / "reference" / "tnau_rice_guidelines.json"


def load_tnau_rice_guidelines() -> Dict[str, Any]:
    """Loads validated TNAU rice water management reference data."""
    if not REFERENCE_FILE.exists():
        return {}
    try:
        with open(REFERENCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_tnau_stage_recommendation(stage_name: str) -> Dict[str, Any]:
    """
    Returns TNAU water management advice and critical sensitivity status for a given stage.
    """
    data = load_tnau_rice_guidelines()
    practices = data.get("water_management_practices", {})
    critical_stages = practices.get("critical_stages_ranked_by_water_stress_sensitivity", [])

    stage_lower = stage_name.lower()
    for item in critical_stages:
        if "mid" in stage_lower or "panicle" in stage_lower or "flower" in stage_lower:
            if "panicle" in item["stage"].lower() or "mid" in item["stage"].lower():
                return item
        elif "dev" in stage_lower or "tiller" in stage_lower:
            if "tillering" in item["stage"].lower():
                return item
        elif "init" in stage_lower or "transplant" in stage_lower:
            if "transplanting" in item["stage"].lower():
                return item
        elif "late" in stage_lower or "ripen" in stage_lower:
            if "ripening" in item["stage"].lower():
                return item

    return {
        "stage": stage_name,
        "sensitivity": "MEDIUM",
        "impact_of_stress": "General vegetative moisture stress",
        "mandatory_management": "Maintain adequate root-zone moisture"
    }


def get_tnau_soil_interval(soil_type: str) -> Dict[str, Any]:
    """Returns TNAU recommended irrigation intervals for a given soil type."""
    data = load_tnau_rice_guidelines()
    intervals = data.get("water_management_practices", {}).get("soil_specific_irrigation_intervals", {})
    return intervals.get(soil_type, {
        "recommended_interval_days": "3 to 4 days",
        "percolation_loss_typical_mm_day": "2.0 - 3.0",
        "characteristics": "Medium texture soil"
    })
