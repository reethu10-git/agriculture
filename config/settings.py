"""
AGRI-2: Configuration and Agricultural Settings
Centralized management of physical constants, crop databases, soil parameters,
default project inputs, and Nexus API environment settings.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("agri2.settings")

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Serverless / Production environment detection
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
APP_ENV = os.getenv("APP_ENV", "production" if IS_VERCEL else "development")

if IS_VERCEL:
    OUTPUTS_DIR = Path("/tmp/outputs")
else:
    OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure output directory exists (safe for read-only root in serverless)
try:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    logger.warning("Unable to create outputs directory %s: %s", OUTPUTS_DIR, exc)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Nexus API configuration
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")
NEXUS_BASE_URL = os.getenv("NEXUS_BASE_URL", "https://nexusapi.navigatelabs.ai/v1")
NEXUS_MODEL = os.getenv("NEXUS_MODEL", "gpt-5-nano")

# Supabase Database Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Default geographical configuration (Coimbatore, Tamil Nadu, India)
DEFAULT_LOCATION = {
    "name": "Coimbatore, Tamil Nadu, India",
    "latitude": 11.0168,       # Degrees North
    "longitude": 76.9558,      # Degrees East
    "elevation": 411.0,        # Meters above sea level
    "anemometer_height": 2.0   # Default height of wind measurement (m)
}

# Soil physical parameters database
SOIL_DATABASE = {
    "Loamy": {
        "field_capacity": 0.27,      # m3/m3 (volumetric water content)
        "wilting_point": 0.12,       # m3/m3
        "saturation": 0.45,          # m3/m3
        "percolation_rate": 2.5,     # mm/day (puddled lowland paddy)
        "description": "Medium texture, balanced water retention and drainage. Highly common in Coimbatore agricultural plains."
    },
    "Clay": {
        "field_capacity": 0.38,
        "wilting_point": 0.22,
        "saturation": 0.52,
        "percolation_rate": 1.2,
        "description": "Heavy texture, slow percolation, high water retention. Ideal for lowland wetland paddy."
    },
    "Clay Loam": {
        "field_capacity": 0.32,
        "wilting_point": 0.18,
        "saturation": 0.48,
        "percolation_rate": 1.8,
        "description": "Moderately fine texture with strong nutrient and moisture retention."
    },
    "Sandy Loam": {
        "field_capacity": 0.18,
        "wilting_point": 0.08,
        "saturation": 0.40,
        "percolation_rate": 4.5,
        "description": "Coarse to medium texture, rapid infiltration, low water storage."
    },
    "Sandy": {
        "field_capacity": 0.12,
        "wilting_point": 0.04,
        "saturation": 0.38,
        "percolation_rate": 7.0,
        "description": "Very coarse texture, low moisture retention, requires frequent light irrigation."
    },
    "Silt Loam": {
        "field_capacity": 0.30,
        "wilting_point": 0.15,
        "saturation": 0.46,
        "percolation_rate": 2.2,
        "description": "Smooth silty texture with high available water capacity and moderate drainage."
    },
    "Silty Clay": {
        "field_capacity": 0.39,
        "wilting_point": 0.23,
        "saturation": 0.51,
        "percolation_rate": 1.4,
        "description": "Fine-textured soil with high moisture retention and slow internal drainage."
    },
    "Silty Clay Loam": {
        "field_capacity": 0.35,
        "wilting_point": 0.20,
        "saturation": 0.49,
        "percolation_rate": 1.6,
        "description": "Well-structured medium-fine soil with strong water-holding capacity."
    },
    "Sandy Clay Loam": {
        "field_capacity": 0.26,
        "wilting_point": 0.14,
        "saturation": 0.43,
        "percolation_rate": 3.2,
        "description": "Balanced sand-clay mix with moderate water retention and good aeration."
    },
    "Loamy Sand": {
        "field_capacity": 0.15,
        "wilting_point": 0.06,
        "saturation": 0.39,
        "percolation_rate": 5.8,
        "description": "Coarse-textured soil with fast infiltration and low moisture storage."
    }
}

# Crop parameters and FAO-56 Kc values database
CROP_DATABASE = {
    "Rice": {
        "scientific_name": "Oryza sativa",
        "cultivation_type": "lowland_paddy", # or upland
        "stages": {
            "Initial": {
                "kc": 1.05,
                "days": 20,
                "description": "Transplanting / nursery establishment, shallow standing water"
            },
            "Development": {
                "kc": 1.15,
                "days": 30,
                "description": "Tillering and stem elongation"
            },
            "Mid-Season": {
                "kc": 1.25,
                "days": 40,
                "description": "Panicle initiation, flowering, heading (water-stress critical stage)"
            },
            "Late-Season": {
                "kc": 0.90,
                "days": 30,
                "description": "Grain filling, ripening, pre-harvest field dry-down"
            }
        },
        "root_depth_default": 0.50, # meters
        "depletion_fraction_p": 0.20, # soil water depletion fraction for no stress
        "paddy_bund_height": 80.0,   # mm (spillway/overflow threshold)
        "paddy_target_depth": 40.0,  # mm target ponded depth
        "paddy_min_depth_awd": 0.0,  # mm threshold for Alternate Wetting and Drying reflooding
        "crop_height": 1.0           # meters (for mid-season Kc aerodynamic correction)
    },
    "Maize": {
        "scientific_name": "Zea mays",
        "cultivation_type": "upland",
        "stages": {
            "Initial": {"kc": 0.30, "days": 20, "description": "Emergence and seedling"},
            "Development": {"kc": 0.70, "days": 35, "description": "Rapid vegetative growth"},
            "Mid-Season": {"kc": 1.20, "days": 40, "description": "Tasseling, silking, cob formation"},
            "Late-Season": {"kc": 0.60, "days": 30, "description": "Grain maturity and dry-down"}
        },
        "root_depth_default": 1.00,
        "depletion_fraction_p": 0.55,
        "crop_height": 2.0
    },
    "Wheat": {
        "scientific_name": "Triticum aestivum",
        "cultivation_type": "upland",
        "stages": {
            "Initial": {"kc": 0.30, "days": 15, "description": "Germination and crown root initiation"},
            "Development": {"kc": 0.75, "days": 30, "description": "Tillering and jointing"},
            "Mid-Season": {"kc": 1.15, "days": 45, "description": "Booting, heading, milk stage"},
            "Late-Season": {"kc": 0.40, "days": 30, "description": "Dough stage and senescence"}
        },
        "root_depth_default": 0.90,
        "depletion_fraction_p": 0.55,
        "crop_height": 0.9
    },
    "Tomato": {
        "scientific_name": "Solanum lycopersicum",
        "cultivation_type": "upland",
        "stages": {
            "Initial": {"kc": 0.60, "days": 30, "description": "Transplanting to first flowering"},
            "Development": {"kc": 0.80, "days": 40, "description": "Vegetative branching and fruit set"},
            "Mid-Season": {"kc": 1.15, "days": 45, "description": "Fruit sizing and color turn"},
            "Late-Season": {"kc": 0.80, "days": 25, "description": "Harvesting and final picking"}
        },
        "root_depth_default": 0.70,
        "depletion_fraction_p": 0.40,
        "crop_height": 0.6
    },
    "Cotton": {
        "scientific_name": "Gossypium hirsutum",
        "cultivation_type": "upland",
        "stages": {
            "Initial": {"kc": 0.35, "days": 30, "description": "Emergence to first square"},
            "Development": {"kc": 0.75, "days": 50, "description": "Squaring to early flowering"},
            "Mid-Season": {"kc": 1.20, "days": 60, "description": "Peak bloom and boll development"},
            "Late-Season": {"kc": 0.65, "days": 40, "description": "Boll opening and defoliation"}
        },
        "root_depth_default": 1.20,
        "depletion_fraction_p": 0.65,
        "crop_height": 1.2
    },
    "Sugarcane": {
        "scientific_name": "Saccharum officinarum",
        "cultivation_type": "upland",
        "stages": {
            "Initial": {"kc": 0.40, "days": 35, "description": "Sprouting and tillering"},
            "Development": {"kc": 0.80, "days": 60, "description": "Canopy development"},
            "Mid-Season": {"kc": 1.25, "days": 180, "description": "Grand elongation period"},
            "Late-Season": {"kc": 0.75, "days": 90, "description": "Ripening and sucrose accumulation"}
        },
        "root_depth_default": 1.20,
        "depletion_fraction_p": 0.65,
        "crop_height": 3.0
    }
}

# Unit conversion constants
AREA_CONVERSIONS = {
    "Acre": 4046.8564224,      # 1 Acre = 4046.856 m2
    "Hectare": 10000.0,        # 1 Hectare = 10,000 m2
    "Square Meter": 1.0        # 1 m2
}

# Physical constants for FAO-56 Penman-Monteith
SOLAR_CONSTANT_GSC = 0.0820  # MJ / (m2 * min)
STEFAN_BOLTZMANN = 4.903e-9  # MJ / (K4 * m2 * day)
PSYCHROMETRIC_A = 0.000665   # kPa / °C
ALBEDO_CANOPY = 0.23         # Standard grass reference albedo

# Multilingual configuration (English and Telugu)
DEFAULT_LANGUAGE = "English"
SUPPORTED_LANGUAGES = ["English", "Telugu"]
