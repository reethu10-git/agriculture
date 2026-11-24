"""
AGRI-2: Effective Rainfall (Peff) Calculation Engine
Calculates the fraction of total precipitation that enters and remains in the crop
root zone or paddy ponded storage, distinguishing between wetland rice and upland crops.
"""

from typing import Dict, Any


def usda_scs_effective_rainfall(rainfall_mm: float) -> float:
    """
    USDA Soil Conservation Service (SCS) method adapted for daily rainfall.
    Small rain events (< 3.0 mm) evaporate from canopy/soil surface with 0% effectiveness.
    For P <= 250 mm:
        Peff = P * (125 - 0.2 * P) / 125
    For P > 250 mm:
        Peff = 125 + 0.1 * P
    Unit: mm
    """
    if rainfall_mm <= 3.0:
        return 0.0

    if rainfall_mm <= 250.0:
        peff = rainfall_mm * ((125.0 - 0.2 * rainfall_mm) / 125.0)
    else:
        peff = 125.0 + 0.1 * rainfall_mm

    return round(max(0.0, min(rainfall_mm, peff)), 2)


def fao_aglw_effective_rainfall(rainfall_mm: float) -> float:
    """
    FAO AGLW empirical formula for daily precipitation:
    If P <= 4.0 mm: Peff = 0 mm
    If 4.0 < P <= 50.0 mm: Peff = 0.8 * P - 4.0 mm
    If P > 50.0 mm: Peff = 0.7 * P
    Unit: mm
    """
    if rainfall_mm <= 4.0:
        return 0.0
    elif rainfall_mm <= 50.0:
        return round(0.8 * rainfall_mm - 4.0, 2)
    else:
        return round(0.7 * rainfall_mm, 2)


def paddy_bund_effective_rainfall(
    rainfall_mm: float,
    current_ponded_depth_mm: float,
    bund_height_mm: float = 80.0
) -> Dict[str, float]:
    """
    Effective rainfall model specifically for Lowland Ponded Rice with earthen bunds.
    In flooded rice fields, bunds retain water up to the crest/spillway height (Hbund).
    Available freeboard storage capacity = max(0, Hbund - current_ponded_depth).
    Rainfall up to this storage capacity is 100% effective (stored in pond without runoff).
    Excess rainfall over bund height overflows as surface runoff.

    Returns:
        dict: effective_rainfall_mm, runoff_mm, freeboard_capacity_mm
    """
    freeboard_capacity = max(0.0, bund_height_mm - max(0.0, current_ponded_depth_mm))

    if rainfall_mm <= freeboard_capacity:
        peff = rainfall_mm
        runoff = 0.0
    else:
        peff = freeboard_capacity
        runoff = rainfall_mm - freeboard_capacity

    return {
        "effective_rainfall_mm": round(peff, 2),
        "runoff_mm": round(runoff, 2),
        "freeboard_capacity_mm": round(freeboard_capacity, 2)
    }


def calculate_effective_rainfall(
    rainfall_mm: float,
    crop_name: str = "Rice",
    cultivation_type: str = "lowland_paddy",
    current_ponded_depth_mm: float = 0.0,
    bund_height_mm: float = 80.0,
    method: str = "auto"
) -> Dict[str, Any]:
    """
    Master dispatcher for effective rainfall calculation.
    Automatically chooses paddy bund retention for lowland rice, or USDA-SCS for upland crops.
    """
    if rainfall_mm <= 0.0:
        return {
            "rainfall_mm": 0.0,
            "effective_rainfall_mm": 0.0,
            "runoff_mm": 0.0,
            "method": method
        }

    if method == "auto":
        if crop_name.lower() == "rice" and cultivation_type == "lowland_paddy":
            method = "paddy_bund"
        else:
            method = "usda_scs"

    if method == "paddy_bund":
        res = paddy_bund_effective_rainfall(rainfall_mm, current_ponded_depth_mm, bund_height_mm)
        return {
            "rainfall_mm": round(rainfall_mm, 2),
            "effective_rainfall_mm": res["effective_rainfall_mm"],
            "runoff_mm": res["runoff_mm"],
            "freeboard_capacity_mm": res["freeboard_capacity_mm"],
            "method": "Paddy Bund Storage (Freeboard)"
        }
    elif method == "fao_aglw":
        peff = fao_aglw_effective_rainfall(rainfall_mm)
        runoff = max(0.0, rainfall_mm - peff)
        return {
            "rainfall_mm": round(rainfall_mm, 2),
            "effective_rainfall_mm": peff,
            "runoff_mm": round(runoff, 2),
            "method": "FAO AGLW Empirical Formula"
        }
    else:
        peff = usda_scs_effective_rainfall(rainfall_mm)
        runoff = max(0.0, rainfall_mm - peff)
        return {
            "rainfall_mm": round(rainfall_mm, 2),
            "effective_rainfall_mm": peff,
            "runoff_mm": round(runoff, 2),
            "method": "USDA-SCS Empirical Model"
        }
