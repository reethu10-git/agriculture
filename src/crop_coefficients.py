"""
AGRI-2: Crop Evapotranspiration (ETc) and Kc Coefficient Engine
Calculates crop-specific evapotranspiration and manages stage-dependent
crop coefficient (Kc) selection adhering to FAO-56 standards.
"""

from typing import Dict, Any, Optional
from config.settings import CROP_DATABASE


def get_crop_coefficient(
    crop_name: str,
    stage: str,
    u2: float = 2.0,
    rh_min: float = 45.0,
    crop_height_m: Optional[float] = None,
    kc_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Selects and adjusts the crop coefficient (Kc) for a given crop and stage.
    Optionally applies FAO-56 Eq. 62 climatic adjustment for mid- and late-season stages
    under non-standard wind and relative humidity conditions:
    Kc = Kc(table) + [0.04 * (u2 - 2) - 0.004 * (rh_min - 45)] * (h / 3)^0.3

    Args:
        crop_name: Target crop (Rice, Maize, Wheat, Tomato, Cotton, Sugarcane).
        stage: Growth stage (Initial, Development, Mid-Season, Late-Season).
        u2: Wind speed at 2m height (m/s).
        rh_min: Minimum relative humidity (%).
        crop_height_m: Mean plant height (m).
        kc_override: Optional user-specified manual Kc value.

    Returns:
        dict: Detailed Kc metadata, adjustments, and stage descriptions.
    """
    if kc_override is not None and kc_override > 0:
        return {
            "crop": crop_name,
            "stage": stage,
            "kc": round(kc_override, 3),
            "kc_base": round(kc_override, 3),
            "adjustment_applied": False,
            "description": "User custom overridden Kc"
        }

    crop_info = CROP_DATABASE.get(crop_name)
    if not crop_info:
        # Default fallback to Rice Mid-Season if unknown
        crop_info = CROP_DATABASE["Rice"]
        crop_name = "Rice"

    stage_info = crop_info["stages"].get(stage)
    if not stage_info:
        stage_info = crop_info["stages"]["Mid-Season"]
        stage = "Mid-Season"

    kc_base = stage_info["kc"]
    h = crop_height_m if crop_height_m is not None else crop_info.get("crop_height", 1.0)

    # Climate adjustment applies to Mid-Season and Late-Season (FAO-56 p. 116)
    # Only if wind speed deviates from 2.0 m/s or RHmin deviates from 45%
    adjustment = 0.0
    adjustment_applied = False
    if stage in ["Mid-Season", "Late-Season"]:
        wind_delta = u2 - 2.0
        rh_delta = rh_min - 45.0
        if abs(wind_delta) > 0.1 or abs(rh_delta) > 1.0:
            height_factor = max(0.1, h / 3.0) ** 0.3
            adjustment = (0.04 * wind_delta - 0.004 * rh_delta) * height_factor
            adjustment_applied = True

    final_kc = max(0.15, kc_base + adjustment)

    return {
        "crop": crop_name,
        "stage": stage,
        "kc": round(final_kc, 3),
        "kc_base": round(kc_base, 3),
        "climate_adjustment": round(adjustment, 4),
        "adjustment_applied": adjustment_applied,
        "description": stage_info["description"]
    }


def calculate_etc(eto_mm_day: float, kc: float) -> float:
    """
    FAO-56 Eq. 58: Crop evapotranspiration under standard conditions.
    ETc = Kc * ETo
    Unit: mm/day
    """
    etc = max(0.0, eto_mm_day * kc)
    return round(etc, 2)
