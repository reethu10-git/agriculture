"""
AGRI-2: Soil Water Balance and Hydrological Simulation Engine
Simulates dynamic daily soil water balance for 7-day windows across two distinct regimes:
1. Lowland Ponded Rice with Alternate Wetting and Drying (AWD)
2. Upland Crops with Root Zone Depletion (FAO-56 single reservoir model)
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from config.settings import SOIL_DATABASE, CROP_DATABASE
from src.crop_coefficients import get_crop_coefficient, calculate_etc
from src.rainfall import calculate_effective_rainfall


def simulate_paddy_water_balance(
    weather_df: pd.DataFrame,
    soil_type: str = "Loamy",
    growth_stage: str = "Development",
    initial_ponded_depth_mm: float = 30.0,
    bund_height_mm: float = 80.0,
    target_ponded_depth_mm: float = 40.0,
    awd_min_depth_mm: float = 0.0,
    percolation_override: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Simulates daily soil-water balance for lowland wetland rice.
    Governing equation:
        W_pond(t) = W_pond(t-1) + Peff(t) + Irrigation(t) - ETc(t) - Perc(t)

    AWD Management Logic:
        - During Mid-Season (Flowering/Heading), continuous submergence (30-50 mm) is mandatory.
        - During Vegetative/Tillering/Late-Season stages, Alternate Wetting and Drying (AWD) allows
          the water level to drop safely to 0 mm (saturated mud) before reflooding to target depth.
    """
    soil_params = SOIL_DATABASE.get(soil_type, SOIL_DATABASE["Loamy"])
    perc_rate = percolation_override if percolation_override is not None else soil_params["percolation_rate"]

    daily_results = []
    current_pond = max(0.0, initial_ponded_depth_mm)

    is_critical_reproductive = (growth_stage == "Mid-Season")
    active_awd_min = 25.0 if is_critical_reproductive else awd_min_depth_mm

    for _, row in weather_df.iterrows():
        date_str = str(row['date'])[:10]
        eto = float(row.get('eto_mm_day', 4.5))
        rainfall = float(row.get('rainfall_mm', 0.0))
        u2 = float(row.get('wind_speed_2m', 2.0))
        rh_min = float(row.get('rh_min', 50.0)) if 'rh_min' in row and not pd.isna(row['rh_min']) else 50.0

        # 1. ETc
        kc_info = get_crop_coefficient("Rice", growth_stage, u2=u2, rh_min=rh_min)
        kc = kc_info["kc"]
        etc = calculate_etc(eto, kc)

        # 2. Effective rainfall considering bund freeboard before rain
        rain_info = calculate_effective_rainfall(
            rainfall_mm=rainfall,
            crop_name="Rice",
            cultivation_type="lowland_paddy",
            current_ponded_depth_mm=current_pond,
            bund_height_mm=bund_height_mm
        )
        peff = rain_info["effective_rainfall_mm"]
        runoff = rain_info["runoff_mm"]

        # 3. Projected ponded depth before new irrigation
        projected_pond = current_pond + peff - etc - perc_rate

        # 4. Irrigation decision based on safe threshold
        irrigation_needed = 0.0
        decision = "SKIP"
        reason = ""

        if projected_pond <= active_awd_min:
            # Need to replenish up to target ponded depth
            irrigation_needed = round(max(0.0, target_ponded_depth_mm - projected_pond), 1)
            final_pond = target_ponded_depth_mm
            decision = "IRRIGATE"
            if is_critical_reproductive:
                reason = f"Mid-Season critical panicle stage: ponded water fell to {projected_pond:.1f} mm. Irrigate {irrigation_needed:.1f} mm to maintain required 30-50 mm buffer."
            else:
                reason = f"AWD threshold reached: water subsided to {projected_pond:.1f} mm. Irrigate {irrigation_needed:.1f} mm to restore {target_ponded_depth_mm} mm ponding."
        else:
            final_pond = min(bund_height_mm, projected_pond)
            decision = "SKIP"
            if peff >= etc + perc_rate:
                reason = f"Adequate rain ({peff:.1f} mm) fully replenished daily water demand ({etc + perc_rate:.1f} mm). Irrigation skipped."
            else:
                reason = f"Ponded water depth is safe at {final_pond:.1f} mm (above AWD threshold of {active_awd_min:.1f} mm). Irrigation skipped to save water."

        current_pond = max(0.0, final_pond)

        daily_results.append({
            "date": date_str,
            "crop": "Rice",
            "growth_stage": growth_stage,
            "soil_type": soil_type,
            "eto_mm": eto,
            "kc": kc,
            "etc_mm": etc,
            "rainfall_mm": rainfall,
            "effective_rainfall_mm": peff,
            "runoff_mm": runoff,
            "percolation_mm": perc_rate,
            "soil_water_status": f"{current_pond:.1f} mm ponded",
            "ponded_water_depth_mm": current_pond,
            "recommended_irrigation_mm": irrigation_needed,
            "decision": decision,
            "reason": reason
        })

    return daily_results


def simulate_upland_water_balance(
    weather_df: pd.DataFrame,
    crop_name: str = "Maize",
    growth_stage: str = "Development",
    soil_type: str = "Loamy",
    initial_depletion_fraction: float = 0.3, # 30% of RAW depleted initially
    root_depth_override: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Simulates daily soil-water balance for upland aerated crops using FAO-56 root zone depletion.
    TAW = 1000 * (theta_fc - theta_wp) * Zr
    RAW = p * TAW
    Daily Dr = Dr(t-1) - Peff(t) - I(t) + ETc(t) + DP(t)
    """
    soil_params = SOIL_DATABASE.get(soil_type, SOIL_DATABASE["Loamy"])
    crop_params = CROP_DATABASE.get(crop_name, CROP_DATABASE["Maize"])

    theta_fc = soil_params["field_capacity"]
    theta_wp = soil_params["wilting_point"]
    zr = root_depth_override if root_depth_override is not None else crop_params.get("root_depth_default", 0.8)
    p = crop_params.get("depletion_fraction_p", 0.5)

    # Total Available Water (TAW) and Readily Available Water (RAW) in mm
    taw = 1000.0 * (theta_fc - theta_wp) * zr
    raw = p * taw

    # Initial root zone depletion Dr (mm)
    dr = min(taw, max(0.0, initial_depletion_fraction * raw))

    daily_results = []

    for _, row in weather_df.iterrows():
        date_str = str(row['date'])[:10]
        eto = float(row.get('eto_mm_day', 4.5))
        rainfall = float(row.get('rainfall_mm', 0.0))
        u2 = float(row.get('wind_speed_2m', 2.0))
        rh_min = float(row.get('rh_min', 50.0)) if 'rh_min' in row and not pd.isna(row['rh_min']) else 50.0

        # ETc
        kc_info = get_crop_coefficient(crop_name, growth_stage, u2=u2, rh_min=rh_min)
        kc = kc_info["kc"]
        etc = calculate_etc(eto, kc)

        # Effective rainfall via USDA SCS
        rain_info = calculate_effective_rainfall(
            rainfall_mm=rainfall,
            crop_name=crop_name,
            cultivation_type="upland",
            method="usda_scs"
        )
        peff = rain_info["effective_rainfall_mm"]

        # Projected root zone depletion before irrigation
        projected_dr = dr - peff + etc

        # Irrigation trigger: if depletion exceeds RAW, water stress begins
        irrigation_needed = 0.0
        decision = "SKIP"
        reason = ""

        if projected_dr >= raw:
            irrigation_needed = round(projected_dr, 1)
            decision = "IRRIGATE"
            reason = f"Root-zone depletion reached {projected_dr:.1f} mm, exceeding stress threshold (RAW = {raw:.1f} mm). Irrigate {irrigation_needed:.1f} mm to refill to field capacity."
            dr = 0.0 # Refilled to field capacity
        else:
            dr = max(0.0, projected_dr)
            decision = "SKIP"
            if peff >= etc:
                reason = f"Effective rain ({peff:.1f} mm) satisfied daily ETc ({etc:.1f} mm). No irrigation required."
            else:
                moisture_pct = max(0, int(((raw - dr) / raw) * 100)) if raw > 0 else 100
                reason = f"Readily available moisture buffer is {moisture_pct}% intact (Depletion: {dr:.1f} / {raw:.1f} mm). Irrigation skipped."

        daily_results.append({
            "date": date_str,
            "crop": crop_name,
            "growth_stage": growth_stage,
            "soil_type": soil_type,
            "eto_mm": eto,
            "kc": kc,
            "etc_mm": etc,
            "rainfall_mm": rainfall,
            "effective_rainfall_mm": peff,
            "runoff_mm": max(0.0, rainfall - peff),
            "percolation_mm": 0.0,
            "soil_water_status": f"{dr:.1f} mm deficit (RAW: {raw:.1f} mm)",
            "depletion_mm": dr,
            "taw_mm": round(taw, 1),
            "raw_mm": round(raw, 1),
            "recommended_irrigation_mm": irrigation_needed,
            "decision": decision,
            "reason": reason
        })

    return daily_results


def run_water_balance_simulation(
    weather_df: pd.DataFrame,
    crop_name: str = "Rice",
    growth_stage: str = "Development",
    soil_type: str = "Loamy",
    field_area_val: float = 1.0,
    field_area_unit: str = "Acre",
    initial_water_condition: str = "Moderate",
    bund_height_mm: float = 80.0
) -> List[Dict[str, Any]]:
    """
    Unified entry point for 7-day soil water balance simulation.
    Handles Rice (paddy flooded / AWD) and upland crops appropriately.
    """
    crop_data = CROP_DATABASE.get(crop_name, CROP_DATABASE["Rice"])
    cultivation_type = crop_data.get("cultivation_type", "lowland_paddy")

    if crop_name.lower() == "rice" and cultivation_type == "lowland_paddy":
        # Map initial condition to pond depth
        if initial_water_condition == "Dry / Low":
            init_pond = 5.0
        elif initial_water_condition == "Adequate / Target":
            init_pond = 40.0
        else: # Moderate
            init_pond = 25.0

        return simulate_paddy_water_balance(
            weather_df=weather_df,
            soil_type=soil_type,
            growth_stage=growth_stage,
            initial_ponded_depth_mm=init_pond,
            bund_height_mm=bund_height_mm,
            target_ponded_depth_mm=crop_data.get("paddy_target_depth", 40.0),
            awd_min_depth_mm=crop_data.get("paddy_min_depth_awd", 0.0)
        )
    else:
        # Upland crop
        if initial_water_condition == "Dry / Low":
            init_depletion_fraction = 0.85
        elif initial_water_condition == "Adequate / Target":
            init_depletion_fraction = 0.10
        else: # Moderate
            init_depletion_fraction = 0.40

        return simulate_upland_water_balance(
            weather_df=weather_df,
            crop_name=crop_name,
            growth_stage=growth_stage,
            soil_type=soil_type,
            initial_depletion_fraction=init_depletion_fraction
        )
