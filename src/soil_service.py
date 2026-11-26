"""
AGRI-2: ISRIC SoilGrids Integration & Soil Property Estimation Engine
Queries the SoilGrids REST API (https://rest.isric.org/) for modelled global soil property
estimates (clay, sand, silt, organic carbon, bulk density, pH).

IMPORTANT AGRICULTURAL NOTICE:
SoilGrids outputs are MODELLED SOIL PROPERTY ESTIMATES derived from spatial machine learning
(250m resolution). They indicate static physical soil potential and texture fractions.
They MUST NEVER be treated as real-time field moisture measurements.
Farmer-selected soil type and field measurements remain the primary calculation inputs.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging
import time
from datetime import datetime, timezone
import requests
from config.settings import DEFAULT_LOCATION, DATA_DIR, IS_VERCEL

logger = logging.getLogger("agri2.soil_service")

if IS_VERCEL:
    SOILGRIDS_RAW_DIR = Path("/tmp/soilgrids")
    SOILGRIDS_PROCESSED_FILE = Path("/tmp/processed/soilgrids_coimbatore.json")
else:
    SOILGRIDS_RAW_DIR = DATA_DIR / "raw" / "soilgrids"
    SOILGRIDS_PROCESSED_FILE = DATA_DIR / "processed" / "soilgrids_coimbatore.json"

for _dir in (SOILGRIDS_RAW_DIR, SOILGRIDS_PROCESSED_FILE.parent):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Unable to create SoilGrids directory %s: %s", _dir, exc)

# Standard regional SoilGrids 250m reference profile for Coimbatore Agricultural Plains (11.0168°N, 76.9558°E)
COIMBATORE_REGIONAL_PROFILE = {
    "clay_percent": 28.5,           # 285 g/kg
    "sand_percent": 44.8,           # 448 g/kg
    "silt_percent": 26.7,           # 267 g/kg
    "organic_carbon_g_kg": 8.6,     # 86 dg/kg
    "bulk_density_g_cm3": 1.42,     # 142 cg/cm3
    "soil_ph": 7.3,                 # 73 pH*10
    "usda_texture_class": "Sandy Clay Loam / Loam",
    "provenance_note": "ISRIC SoilGrids 250m Modelled Regional Profile (Coimbatore plains, depth 0-30cm)"
}


def parse_soilgrids_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses ISRIC SoilGrids REST API v2 JSON response into standardized physical units.
    ISRIC unit conventions:
    - clay, sand, silt: g/kg (convert to % by dividing by 10)
    - soc (soil organic carbon): dg/kg (convert to g/kg by dividing by 10)
    - bdod (bulk density): cg/cm3 (convert to g/cm3 by dividing by 100)
    - phh2o: pH * 10 (convert to pH by dividing by 10)
    """
    layers = data.get("properties", {}).get("layers", [])
    extracted: Dict[str, float] = {}

    for layer in layers:
        prop_name = layer.get("name")
        depths = layer.get("depths", [])
        # We average across topsoil and subsoil root layers (0-5cm, 5-15cm, 15-30cm)
        values = []
        for d in depths:
            val = d.get("values", {}).get("mean")
            if val is not None:
                values.append(val)

        if values:
            avg_raw = sum(values) / len(values)
            if prop_name == "clay":
                extracted["clay_percent"] = round(avg_raw / 10.0, 1)
            elif prop_name == "sand":
                extracted["sand_percent"] = round(avg_raw / 10.0, 1)
            elif prop_name == "silt":
                extracted["silt_percent"] = round(avg_raw / 10.0, 1)
            elif prop_name == "soc":
                extracted["organic_carbon_g_kg"] = round(avg_raw / 10.0, 1)
            elif prop_name == "bdod":
                extracted["bulk_density_g_cm3"] = round(avg_raw / 100.0, 2)
            elif prop_name == "phh2o":
                extracted["soil_ph"] = round(avg_raw / 10.0, 1)

    # Determine USDA textural class from fractions if clay and sand are present
    clay = extracted.get("clay_percent", COIMBATORE_REGIONAL_PROFILE["clay_percent"])
    sand = extracted.get("sand_percent", COIMBATORE_REGIONAL_PROFILE["sand_percent"])
    silt = extracted.get("silt_percent", max(0.0, 100.0 - clay - sand))

    if clay >= 40:
        texture = "Clay"
    elif clay >= 27 and sand <= 45:
        texture = "Clay Loam"
    elif clay >= 20 and sand >= 45:
        texture = "Sandy Clay Loam"
    elif sand >= 70:
        texture = "Sandy Loam"
    else:
        texture = "Loamy"

    extracted["usda_texture_class"] = texture
    return extracted


def fetch_soilgrids_properties(
    latitude: float = DEFAULT_LOCATION["latitude"],
    longitude: float = DEFAULT_LOCATION["longitude"],
    timeout: float = 6.0,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Retrieves modelled soil properties from SoilGrids REST API with caching and resilient fallback.

    Returns:
        dict: Standardized soil properties, metadata, provenance, and data type badge.
    """
    cache_key = f"soilgrids_{latitude:.4f}_{longitude:.4f}.json"
    cache_path = SOILGRIDS_RAW_DIR / cache_key

    # Check local cache first unless forced refresh
    if not force_refresh and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                return cached_data
        except Exception:
            pass

    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {
        "lon": longitude,
        "lat": latitude,
        "property": ["clay", "sand", "silt", "soc", "bdod", "phh2o"],
        "depth": ["0-5cm", "5-15cm", "15-30cm"],
        "value": ["mean"]
    }

    retrieval_time = datetime.now(timezone.utc).isoformat()

    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={"User-Agent": "AGRI-2-IrrigationAdvisor/1.0"}
        )
        response.raise_for_status()
        raw_json = response.json()

        # Parse properties
        props = parse_soilgrids_response(raw_json)

        result = {
            "success": True,
            "provenance_status": "MODELLED_SOIL_ESTIMATE_ONLINE",
            "provenance_badge": "ISRIC SoilGrids 2.0 (Modelled Estimate)",
            "retrieval_timestamp": retrieval_time,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "properties": props,
            "disclaimer": "Modelled machine-learning estimate (250m grid). NOT an actual field moisture reading.",
            "source_url": "https://rest.isric.org/"
        }

        # Save raw and processed cache
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return result

    except Exception as e:
        # Fallback to local regional profile
        fallback_result = {
            "success": False,
            "error_detail": f"SoilGrids API request timed out or was unreachable: {str(e)}",
            "provenance_status": "MODELLED_SOIL_ESTIMATE_REGIONAL_PROFILE",
            "provenance_badge": "ISRIC SoilGrids Regional Profile (Pre-cached)",
            "retrieval_timestamp": retrieval_time,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "properties": dict(COIMBATORE_REGIONAL_PROFILE),
            "disclaimer": "Modelled regional soil profile for Western Tamil Nadu. NOT an actual field moisture reading.",
            "source_url": "https://rest.isric.org/"
        }

        # Save fallback cache if none exists
        if not cache_path.exists():
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(fallback_result, f, indent=2)

        return fallback_result
