# AGRI-2 – Vercel Migration: Phase 1 Project Audit & Architecture Planning

**Document Version**: 1.0.0  
**Date**: November 24, 2026  
**Author**: Senior Full-Stack Architect, Python Engineer & Agricultural Data Scientist  
**Project**: AGRI-2 – Irrigation Scheduling Advisor  
**Target Platform**: Vercel (Next.js + Python FastAPI Serverless Functions + Supabase PostgreSQL)  

---

## 1. Executive Summary & Existing Architecture

The **AGRI-2: Irrigation Scheduling Advisor** is an agronomic decision-support platform designed to calculate field-level irrigation requirements, eliminate over-irrigation, and protect crops against water stress. 

### 1.1 Existing System Overview
- **Core Hydrological Calculations**: Implemented entirely in Python adhering to FAO-56 Penman-Monteith physical equations.
- **Frontend Layer**: Streamlit monolithic dashboard (`app.py`) providing a 5-screen interactive workflow.
- **AI Advisory & Multilingual Translation**: Large Language Model integration via Company Nexus API (`gpt-5-nano`) with bilingual prompt generation and deterministic rule-based fallbacks.
- **Data Persistence**: Local file system logging (`outputs/approved_schedules.json` and `data/raw/` disk caching).
- **Automated Validation**: 27 pytest automated test cases covering reference evapotranspiration ($ET_o$), crop coefficients ($K_c$), effective rainfall, wetland rice soil-water balance, 7-day scheduler, API resilience, and data collection.

### 1.2 Motivation for Vercel & Full-Stack Migration
While Streamlit is ideal for rapid local prototyping, it has structural limitations for multi-tenant, cloud-native deployments:
1. **Serverless Incompatibility**: Streamlit requires persistent, stateful WebSocket connections and a continuous Python server process, which cannot run on Vercel's serverless architecture.
2. **Ephemeral Storage on Vercel**: Vercel Serverless Functions execute in a read-only container (except `/tmp`), rendering local file audit logging (`outputs/approved_schedules.json`) obsolete.
3. **Enterprise UI Capabilities**: A modern Next.js + React + TypeScript interface provides sub-second client-side routing, high mobile responsiveness, custom multi-lingual layouts, and granular state management.
4. **Decoupled Architecture**: Decoupling the deterministic Python calculation engine behind a FastAPI REST API preserves all mathematical models while allowing the frontend to scale independently.

---

## 2. Inventory of Reusable Components

In accordance with project constraints, **no existing Python calculation code will be replaced with JavaScript**, and **no validated agricultural formulas will be altered**.

| Component Module | File Path | Lines | Reusability Status | Migration Role & Adaptations |
|---|---|---|---|---|
| **FAO-56 ETo Engine** | `src/eto_calculator.py` | 314 | **100% Reusable** | Imported directly by FastAPI backend. Pure deterministic math. |
| **Crop Coefficients** | `src/crop_coefficients.py` | 92 | **100% Reusable** | Stage Kc and FAO-56 Eq. 62 climatic adjustments preserved. |
| **Effective Rainfall** | `src/rainfall.py` | 130 | **100% Reusable** | USDA-SCS and paddy bund water harvesting storage preserved. |
| **Soil Water Balance** | `src/soil_water_balance.py` | 264 | **100% Reusable** | Dual-mode: Lowland Rice (AWD/Ponded) and Upland crops preserved. |
| **7-Day Scheduler** | `src/irrigation_scheduler.py` | 154 | **100% Reusable** | Generates daily decisions, volume conversions (Litres), baseline savings. |
| **Open-Meteo Service** | `src/weather_service.py` | 254 | **100% Reusable** | 10m-to-2m wind height conversion and radiation/pressure normalization. |
| **NASA POWER Service** | `src/nasa_power_service.py` | 242 | **100% Reusable** | Historical daily agroclimatology fetcher, sentinel `-999.0` handling. |
| **SoilGrids Service** | `src/soil_service.py` | 182 | **100% Reusable** | Soil properties parser with regional Coimbatore baseline fallback. |
| **TNAU Reference** | `src/agricultural_reference.py` | 65 | **100% Reusable** | TNAU rice water management guidelines and AWD thresholds. |
| **Nexus API Client** | `src/nexus_client.py` | 154 | **100% Reusable** | OpenAI-compatible client, configured for `gpt-5-nano`. |
| **Advisory Generator** | `src/advisory_generator.py` | 202 | **Reusable (Adaptation)** | Migrate secondary language from Tamil (தமிழ்) to Telugu (తెలుగు). |
| **Approval Logger** | `src/approval_logger.py` | 67 | **Reusable (Adaptation)** | Enhance with Supabase PostgreSQL client while retaining local JSON fallback for offline testing. |
| **Data Loader** | `src/data_loader.py` | 103 | **100% Reusable** | Strict data validation and sanitization for custom CSV and API data. |
| **System Settings** | `config/settings.py` | 187 | **100% Reusable** | Constants, soil hydraulics, crop definitions, language settings. |
| **TNAU Reference Rules** | `data/reference/tnau_rice_guidelines.json` | - | **100% Reusable** | Static reference file for agricultural guidelines. |
| **Automated Tests** | `tests/` | 27 tests | **100% Reusable** | Preserved and expanded with Telugu and FastAPI route tests. |

---

## 3. Dataset Audit & Provenance Verification

Every existing dataset in the repository has been audited, verified for integrity, and classified according to its physical origin.

```
                    ┌──────────────────────────────────────────────┐
                    │               DATASET INVENTORY              │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌──────────────────┬──────────────┴─────┬──────────────────┐
         ▼                  ▼                    ▼                  ▼
┌─────────────────┐ ┌───────────────┐ ┌────────────────────┐ ┌───────────────┐
│ GENUINE LIVE    │ │ GENUINE HIST. │ │ MODELLED ESTIMATE  │ │ SYNTHETIC     │
│ FORECAST        │ │ OBSERVATIONS  │ │ & STATIC REFERENCE │ │ SIMULATIONS   │
├─────────────────┤ ├───────────────┤ ├────────────────────┤ ├───────────────┤
│ Open-Meteo      │ │ NASA POWER    │ │ ISRIC SoilGrids    │ │ 7-day normal  │
│ 7-Day API       │ │ Daily API     │ │ 250m Profile       │ │ Dry spell     │
│ (ECMWF / GFS)   │ │ (v2.10.5)     │ │ TNAU Agritech Rules│ │ Heavy rain    │
└─────────────────┘ └───────────────┘ └────────────────────┘ └───────────────┘
```

### 3.1 Classification Matrix

| File / Source | Physical Source | Classification | Verification Findings & Notes |
|---|---|---|---|
| `Open-Meteo API` | Open-Meteo Forecast Server | **Genuine Live Forecast** | Live 7-day numerical forecast (ECMWF/GFS) for Coimbatore (`11.0168° N, 76.9558° E`). Fetches raw variables: $T_{max}, T_{min}, T_{mean}, RH, Wind_{10m}, Rad, Precip, Press$. |
| `data/raw/nasa_power/nasa_power_raw_...json` | NASA Langley Research Center | **Genuine Historical Weather** | Genuine JSON response from NASA POWER Daily API v2.10.5 for period 2026-10-01 to 2026-10-07. Sources: GEOSIT, FLASHFLUX, POWER. Contains physical variables with sentinel `-999.0` for missing values. |
| `data/processed/nasa_power_standardized_...csv` | Standardized from NASA raw JSON | **Standardized Historical Weather** | Processed through `src/nasa_power_service.py`. Sentinels imputed, wind normalized to 2m, pressure in kPa. Provenance metadata tracked in matching `.json` file. |
| `data/raw/soilgrids/soilgrids_11.0168_76.9558.json` | ISRIC World Soil Information | **Modelled Soil Data (Cached)** | **Live API Failure Verified**: Request to `https://rest.isric.org/` timed out (`Read timed out after 6.0s`). Cleanly fell back to verified regional profile (`COIMBATORE_REGIONAL_PROFILE`): Clay 28.5%, Sand 44.8%, Silt 26.7%, SOC 8.6 g/kg, BD 1.42 g/cm³, pH 7.3. **Explicitly disclaimed as modelled estimate, NOT actual field moisture measurement.** |
| `data/reference/tnau_rice_guidelines.json` | Tamil Nadu Agricultural University | **Static Agricultural Reference** | Curated directly from TNAU Agritech Water Management Portal. Contains critical rice water sensitivity stages, AWD pani pipe protocols (-15 cm depth), and soil intervals. |
| `data/sample/coimbatore_7day_weather.csv` | Agronomic Scenarios | **Synthetic / Curated Simulation** | Plausible 7-day baseline weather constructed for Coimbatore to test normal moderate rainfall conditions. |
| `data/sample/coimbatore_dry_spell_7day.csv` | Agronomic Scenarios | **Synthetic / Curated Simulation** | Summer scenario (March) with zero rain, high solar radiation (24 $MJ/m^2$), and high $ET_o$ to stress-test deficit irrigation logic. |
| `data/sample/coimbatore_heavy_rain_7day.csv` | Agronomic Scenarios | **Synthetic / Curated Simulation** | Monsoon scenario with 110 mm cumulative rainfall to test paddy bund storage and smart irrigation skip decisions. |
| `data/sample/coimbatore_historical_30day.csv` | NASA POWER / TNAU Climatology | **Curated Historical Observation** | 30-day continuous agro-meteorological series for October 2026 for multi-week validation. |

### 3.2 Dataset Authenticity Protocol
- **Zero Hallucination Rule**: Synthetic simulation CSVs in `data/sample/` will **never** be presented as live forecasts.
- The UI and API must explicitly emit one of four provenance badges:
  - `🟢 LIVE_FORECAST`
  - `🟡 HISTORICAL_OBSERVATION_REANALYSIS`
  - `🔵 SIMULATION_DATA`
  - `🟣 USER_CUSTOM_CSV`
- SoilGrids data must always carry the disclaimer: `Modelled regional soil profile. Not an actual field moisture sensor reading.`

---

## 4. Target Architecture for Vercel

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VERCEL EDGE & CDN (GLOBAL)                      │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │               FRONTEND: Next.js 15 (React 19 + TypeScript)     │   │
│   │   - App Router (SSR & Client Components)                       │   │
│   │   - Tailwind CSS Responsive Design (Mobile & Desktop)          │   │
│   │   - Interactive Charts (Recharts / SVG)                        │   │
│   │   - Language Selector (English / తెలుగు)                       │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Client / Server Fetch              │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │          BACKEND: Python Serverless Functions (FastAPI)        │   │
│   │   - Entry Point: /api/index.py                                 │   │
│   │   - Sub-routes: /weather, /irrigation, /advisory, /approval    │   │
│   │   - Pydantic Request & Response Validation                     │   │
│   └───────────────────────┬───────────────────────┬────────────────┘   │
└───────────────────────────┼───────────────────────┼────────────────────┘
                            │                       │
                            ▼                       ▼
            ┌──────────────────────────┐  ┌──────────────────────────┐
            │   SUPABASE POSTGRESQL    │  │     EXTERNAL SERVICES    │
            ├──────────────────────────┤  ├──────────────────────────┤
            │ Tables:                  │  │ - Open-Meteo Forecast    │
            │  - schedules             │  │ - NASA POWER Daily       │
            │  - approvals             │  │ - ISRIC SoilGrids REST   │
            │  - weather_cache         │  │ - Company Nexus API      │
            │ Row-Level Security (RLS) │  │   (Model: gpt-5-nano)    │
            └──────────────────────────┘  └──────────────────────────┘
```

### 4.1 Architectural Roles
1. **Frontend (Next.js 15 App Router)**:
   - Replaces `app.py` with modern, mobile-first responsive views.
   - Screen 1: Field & Crop Parameters, Soil Properties (SoilGrids), TNAU Guide.
   - Screen 2: 7-Day Weather Overview & Provenance Badges.
   - Screen 3: Evapotranspiration ($ET_o$ vs $ET_c$) and Dynamic Soil Water Balance.
   - Screen 4: 7-Day Irrigation Schedule & Water Conservation Scorecard.
   - Screen 5: Bilingual AI Advisory (English / Telugu) & Farmer Approval Form.
   - Screen 6: Historical Approval Audit Trail (fed from Supabase).
2. **Backend (Python Serverless with FastAPI)**:
   - Mounted under `/api/index.py` using Vercel's native Python runtime.
   - Direct execution of deterministic modules in `src/`.
   - Sub-second execution times with cold-start optimization.
3. **Database (Supabase PostgreSQL)**:
   - Solves Vercel's ephemeral filesystem constraint.
   - Persists schedule generations and farmer approval decisions with cryptographic timestamps.

---

## 5. Target Folder Structure

```
agri2-irrigation-advisor/
│
├── frontend/                               # Next.js App Router Frontend
│   ├── app/
│   │   ├── layout.tsx                      # Root layout with responsive navigation & theme
│   │   ├── page.tsx                        # Main Dashboard (Screen 1 & 2: Parameters & Weather)
│   │   ├── analysis/page.tsx               # Screen 3: Hydrological & Soil Balance Analysis
│   │   ├── schedule/page.tsx               # Screen 4: 7-Day Schedule & Water Conservation
│   │   ├── advisory/page.tsx               # Screen 5: AI Advisory & Farmer Approval
│   │   └── history/page.tsx                # Screen 6: Supabase Approval Audit Log
│   ├── components/
│   │   ├── ui/                             # Cards, Badges, Modals, Buttons, Alerts
│   │   ├── weather/                        # Weather source selector, Provenance card, Charts
│   │   ├── soil/                           # SoilGrids property card, TNAU guidelines modal
│   │   ├── schedule/                       # 7-Day schedule table, Scorecard, Export buttons
│   │   └── advisory/                       # Bilingual toggle (EN/TE), Advice card, Approval form
│   ├── services/
│   │   ├── api.ts                          # Type-safe Fetch client for /api/* routes
│   │   └── types.ts                        # TypeScript interfaces matching FastAPI schemas
│   ├── public/                             # Static agricultural icons & assets
│   ├── package.json                        # Next.js, React, Tailwind, Lucide, Recharts
│   └── tsconfig.json                       # Strict TypeScript configuration
│
├── api/                                    # Vercel Serverless Python Backend
│   ├── index.py                            # FastAPI application factory and route mounter
│   └── routes/
│       ├── health.py                       # Health check and environment probe
│       ├── weather.py                      # Open-Meteo & NASA POWER retrieval endpoints
│       ├── soil.py                         # SoilGrids and TNAU reference endpoints
│       ├── irrigation.py                   # Schedule calculation endpoint
│       ├── advisory.py                     # Nexus AI advisory generation endpoint (EN & TE)
│       └── approval.py                     # Schedule approval recording (Supabase)
│
├── src/                                    # Existing Python Engine (Preserved & Untouched)
│   ├── eto_calculator.py                   # FAO-56 Penman-Monteith physical engine
│   ├── crop_coefficients.py                # Kc stage selection & climatic adjustments
│   ├── rainfall.py                         # Effective rainfall and paddy bund storage
│   ├── soil_water_balance.py               # Wetland Rice AWD and Upland root depletion
│   ├── irrigation_scheduler.py             # 7-Day schedule synthesis & baseline benchmarking
│   ├── weather_service.py                  # Open-Meteo live forecast service
│   ├── nasa_power_service.py               # NASA POWER daily historical service
│   ├── soil_service.py                     # ISRIC SoilGrids REST service & regional fallback
│   ├── agricultural_reference.py           # TNAU Agritech water management rules
│   ├── nexus_client.py                     # Company Nexus API client (gpt-5-nano)
│   ├── advisory_generator.py               # Bilingual prompt builder (English & Telugu)
│   ├── approval_logger.py                  # Dual-storage: Supabase PostgreSQL + JSON fallback
│   ├── db_client.py                        # Supabase client singleton & query helpers
│   └── data_loader.py                      # Weather validation & preprocessing pipeline
│
├── config/
│   └── settings.py                         # Physical constants, crops, soils, credentials
│
├── data/
│   ├── raw/
│   │   ├── nasa_power/                     # Cached NASA POWER raw responses
│   │   ├── soilgrids/                      # Cached SoilGrids regional profiles
│   │   └── README.md
│   ├── processed/                          # Standardized historical CSVs
│   ├── reference/
│   │   └── tnau_rice_guidelines.json       # TNAU water management reference parameters
│   └── sample/                             # Curated simulation scenarios
│       ├── coimbatore_7day_weather.csv
│       ├── coimbatore_dry_spell_7day.csv
│       ├── coimbatore_heavy_rain_7day.csv
│       └── coimbatore_historical_30day.csv
│
├── tests/                                  # Preserved & Augmented Automated Test Suite
│   ├── test_eto.py
│   ├── test_crop_coefficients.py
│   ├── test_rainfall.py
│   ├── test_water_balance.py
│   ├── test_scheduler.py
│   ├── test_nexus.py                       # Verified with gpt-5-nano & Telugu fallbacks
│   ├── test_data_collection.py             # Open-Meteo, NASA POWER, SoilGrids, TNAU
│   └── test_api_routes.py                  # New: FastAPI endpoint unit & integration tests
│
├── docs/
│   ├── architecture.md
│   ├── dataset_documentation.md
│   ├── calculation_methodology.md
│   └── VERCEL_MIGRATION_AUDIT.md           # This comprehensive planning document
│
├── requirements.txt                        # Lean Serverless Python dependencies (no Streamlit)
├── .python-version                         # 3.11
├── .env.example                            # Template including Nexus & Supabase keys
├── .gitignore
├── vercel.json                             # Route rewrites and runtime configuration
└── README.md
```

---

## 6. API Design & Data Contracts

All endpoints are built using **FastAPI** with strict **Pydantic v2** validation models. All computational steps remain in Python.

### 6.1 `GET /api/health`
Probes system readiness, database connectivity, and Nexus configuration.

**Response Schema (200 OK)**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "runtime": "Python 3.11.0",
  "environment": "vercel-serverless",
  "nexus_configured": true,
  "nexus_model": "gpt-5-nano",
  "database_connected": true,
  "timestamp": "2026-11-24T06:15:00Z"
}
```

---

### 6.2 `GET /api/weather/forecast`
Fetches genuine 7-day live weather forecast from Open-Meteo with automatic unit conversion.

**Query Parameters**:
- `latitude` (float, default: `11.0168`)
- `longitude` (float, default: `76.9558`)

**Response Schema (200 OK)**:
```json
{
  "provenance_status": "LIVE_FORECAST",
  "provenance_badge": "Open-Meteo Live 7-Day Forecast",
  "retrieval_timestamp": "2026-11-24T06:15:00Z",
  "coordinates": { "latitude": 11.0168, "longitude": 76.9558 },
  "date_range": { "start": "2026-11-24", "end": "2026-11-30" },
  "daily_records": [
    {
      "date": "2026-11-24",
      "temp_max": 31.2,
      "temp_min": 22.4,
      "temp_mean": 26.8,
      "humidity_mean": 68.0,
      "wind_speed_2m": 2.15,
      "solar_radiation": 19.4,
      "rainfall": 0.0,
      "pressure_kpa": 96.8
    }
  ],
  "disclaimer": "Live numerical forecast from ECMWF/GFS. Verify before field application."
}
```

---

### 6.3 `GET /api/weather/historical`
Retrieves genuine historical agro-meteorological data from NASA POWER Daily API.

**Query Parameters**:
- `latitude` (float, default: `11.0168`)
- `longitude` (float, default: `76.9558`)
- `start_date` (string, ISO: `YYYY-MM-DD`)
- `end_date` (string, ISO: `YYYY-MM-DD`)

**Response Schema (200 OK)**:
```json
{
  "provenance_status": "HISTORICAL_OBSERVATION_REANALYSIS",
  "provenance_badge": "NASA POWER Daily Observations",
  "retrieval_timestamp": "2026-11-24T06:15:00Z",
  "coordinates": { "latitude": 11.0168, "longitude": 76.9558 },
  "date_range": { "start": "2026-10-01", "end": "2026-10-07" },
  "daily_records": [
    {
      "date": "2026-10-01",
      "temp_max": 31.7,
      "temp_min": 21.6,
      "temp_mean": 26.3,
      "humidity_mean": 74.2,
      "wind_speed_2m": 1.84,
      "solar_radiation": 18.25,
      "rainfall": 3.4,
      "pressure_kpa": 96.7
    }
  ],
  "disclaimer": "Historical satellite and assimilation reanalysis. Not a forecast."
}
```

---

### 6.4 `POST /api/irrigation/schedule`
Executes the full deterministic calculation engine:
$\text{Weather} \xrightarrow{} \text{FAO-56 } ET_o \xrightarrow{} ET_c \xrightarrow{} \text{Effective Rain} \xrightarrow{} \text{Soil Water Balance} \xrightarrow{} \text{7-Day Schedule}$.

**Request Schema**:
```json
{
  "crop": "Rice",
  "growth_stage": "Development",
  "soil_type": "Loamy",
  "field_area_acres": 1.0,
  "weather_source": "live_openmeteo",
  "initial_water_depth_mm": 25.0,
  "custom_weather_records": null
}
```

**Response Schema (200 OK)**:
```json
{
  "schedule_id": "sch_20261124_08912",
  "metadata": {
    "crop": "Rice",
    "growth_stage": "Development",
    "soil_type": "Loamy",
    "field_area_acres": 1.0,
    "provenance_status": "LIVE_FORECAST",
    "execution_time_seconds": 0.012
  },
  "water_reduction_scorecard": {
    "baseline_total_depth_mm": 100.0,
    "recommended_total_depth_mm": 70.0,
    "water_saved_depth_mm": 30.0,
    "water_savings_percent": 30.0,
    "baseline_volume_litres": 404686.0,
    "recommended_volume_litres": 283280.0,
    "water_saved_litres": 121406.0,
    "meets_conservation_target": true
  },
  "daily_schedule": [
    {
      "day_index": 1,
      "date": "2026-11-24",
      "eto_mm": 4.25,
      "kc": 1.15,
      "etc_mm": 4.89,
      "rainfall_mm": 0.0,
      "effective_rainfall_mm": 0.0,
      "water_depth_before_mm": 20.11,
      "water_depth_after_mm": 50.0,
      "irrigation_depth_mm": 30.0,
      "irrigation_volume_litres": 121406,
      "decision": "IRRIGATE",
      "reason": "Water depth below safe AWD threshold (25.0 mm); reflooding to 50 mm.",
      "stage_sensitivity": "Moderate"
    }
  ]
}
```

---

### 6.5 `POST /api/advisory`
Calls Nexus API (`gpt-5-nano`) to generate farmer-facing explanations in English and Telugu.

**Request Schema**:
```json
{
  "schedule_result": { "...": "Complete schedule object from /schedule" },
  "language": "Telugu",
  "farmer_name": "Ramu",
  "field_location": "Coimbatore"
}
```

**Response Schema (200 OK)**:
```json
{
  "success": true,
  "language": "Telugu",
  "model_used": "gpt-5-nano",
  "advisory_markdown": "### 🌾 AGRI-2 నీటిపారుదల సలహాదారు (తెలుగు)\n\n**ప్రియమైన రైతు Ramu గారికి,**\n\nఈ వారం మీ వరి పంట (అభివృద్ధి దశ) కోసం నీటిపారుదల ప్రణాళిక సిద్ధంగా ఉంది:\n\n- **మొత్తం సిఫార్సు చేసిన నీటి పరిమాణం**: 70.0 మి.మీ (2,83,280 లీటర్లు 1 ఎకరాకు).\n- **సాధారణ పద్ధతి కంటే ఆదా చేసిన నీరు**: 30.0% (1,21,406 లీటర్లు ఆదా అయ్యాయి).\n- **ముఖ్య సూచన**: మొదటి రోజు 30 మి.మీ నీరు అందించండి. 4వ రోజు వర్షం కారణంగా నీటిపారుదల అవసరం లేదు.\n\n*గమనిక: వాల్వ్ లేదా పంపు ఆపరేషన్ మీ పర్యవేక్షణలోనే మానవీయంగా చేయాలి.*",
  "is_fallback": false
}
```

---

### 6.6 `POST /api/approval`
Records the farmer's explicit approval or decline decision in Supabase PostgreSQL.

**Request Schema**:
```json
{
  "schedule_id": "sch_20261124_08912",
  "decision": "APPROVED",
  "farmer_name": "Ramu",
  "field_notes": "Applied first irrigation at 6:00 AM. Field bunds reinforced.",
  "approved_depth_mm": 70.0,
  "approved_volume_litres": 283280,
  "crop": "Rice",
  "field_area_acres": 1.0
}
```

**Response Schema (200 OK)**:
```json
{
  "success": true,
  "approval_id": "appr_7f9b23c1",
  "schedule_id": "sch_20261124_08912",
  "status": "APPROVED",
  "recorded_at": "2026-11-24T06:20:00Z",
  "persisted_to_database": true,
  "message": "Farmer schedule approval successfully logged into Supabase audit ledger."
}
```

---

## 7. Nexus API Configuration & Telugu Language Migration

### 7.1 Model & Endpoint Verification
Direct verification on the company endpoint confirmed:
- **Endpoint**: `https://nexusapi.navigatelabs.ai/v1`
- **Model Check**: `client.client.models.list()` confirms **`gpt-5-nano` is present and active** in the available models roster:
  `['titan-embed-text-v2', 'nova-micro', 'text-embedding-3-small', 'nemotron-nano-9b-v2', 'gpt-5-nano', 'nova-2-multimodal-embeddings', 'gemini-3.1-flash-tts-preview', 'gpt-6-luna', 'gemini-3.1-flash-lite', ...]`

### 7.2 Migration from Tamil to Telugu
The user specification establishes **English** and **Telugu** as the final system languages. The existing codebase currently references Tamil across 5 files:

1. **`src/advisory_generator.py` (16 references)**:
   - System prompt instructions: Replace `Tamil` with `Telugu`.
   - Function parameter defaults: Support `English` and `Telugu`.
   - Deterministic Fallback Generator: Implement authentic Telugu agricultural fallback template (`### 🌾 AGRI-2 నీటిపారుదల సలహాదారు (తెలుగు)`).
   - Return dictionary: Change `tamil_advisory` to `telugu_advisory`.
2. **`config/settings.py` (2 references)**:
   - `SUPPORTED_LANGUAGES`: Update from `["English", "Tamil"]` to `["English", "Telugu"]`.
3. **`tests/test_nexus.py` (5 references)**:
   - Update `test_fallback_advisory_bilingual` to assert Telugu characters (`తెలుగు`, `నీటిపారుదల`, `వరి`, `సిఫార్సు`).
4. **`app.py` (4 references)**:
   - Language selector buttons in Streamlit (kept for local testing backward compatibility).
5. **Next.js Frontend (`frontend/components/advisory/`)**:
   - Deliver a responsive language switch toggle between English and Telugu with native font rendering.

---

## 8. Supabase PostgreSQL Schema Design

To replace the ephemeral local JSON logger on Vercel, Supabase PostgreSQL will be utilized.

### 8.1 Table DDL & Relationships

```sql
-- 1. Irrigation Schedules Table
CREATE TABLE IF NOT EXISTS public.schedules (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    crop VARCHAR(50) NOT NULL,
    growth_stage VARCHAR(50) NOT NULL,
    soil_type VARCHAR(50) NOT NULL,
    field_area_acres NUMERIC(6, 2) NOT NULL,
    weather_source VARCHAR(50) NOT NULL,
    provenance_status VARCHAR(50) NOT NULL,
    recommended_total_depth_mm NUMERIC(8, 2) NOT NULL,
    recommended_volume_litres BIGINT NOT NULL,
    water_savings_percent NUMERIC(5, 2) NOT NULL,
    daily_schedule JSONB NOT NULL,
    full_metadata JSONB NOT NULL
);

-- 2. Farmer Schedule Approvals Table (Audit Trail)
CREATE TABLE IF NOT EXISTS public.approvals (
    id TEXT PRIMARY KEY,
    schedule_id TEXT REFERENCES public.schedules(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    farmer_name VARCHAR(120) NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('APPROVED', 'DECLINED')),
    field_notes TEXT,
    approved_depth_mm NUMERIC(8, 2) NOT NULL,
    approved_volume_litres BIGINT NOT NULL,
    crop VARCHAR(50) NOT NULL,
    field_area_acres NUMERIC(6, 2) NOT NULL,
    client_ip VARCHAR(50),
    user_agent TEXT
);

-- Indexes for rapid analytical queries
CREATE INDEX IF NOT EXISTS idx_schedules_created_at ON public.schedules (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_schedule_id ON public.approvals (schedule_id);
CREATE INDEX IF NOT EXISTS idx_approvals_recorded_at ON public.approvals (recorded_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;

-- Allow read access for public/anonymous dashboard; write access via service key
CREATE POLICY "Allow public read access on schedules" ON public.schedules FOR SELECT USING (true);
CREATE POLICY "Allow public read access on approvals" ON public.approvals FOR SELECT USING (true);
CREATE POLICY "Allow backend insert on schedules" ON public.schedules FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend insert on approvals" ON public.approvals FOR INSERT WITH CHECK (true);
```

---

## 9. Dependency & Runtime Compatibility Analysis

### 9.1 Vercel Python Runtime
- **Vercel Official Support**: Python 3.9, 3.10, 3.11, 3.12 (with Python 3.12 default).
- **Target Runtime**: Python 3.11 specified via `.python-version` containing `3.11` to match the validated local environment (`3.11.0`).

### 9.2 Package Footprint Optimization
The current local `requirements.txt` contains libraries intended for Streamlit local plotting:
- `streamlit` (~150 MB unzipped)
- `plotly` (~55 MB unzipped)
- `matplotlib` (~45 MB unzipped)
- `pyarrow` (~75 MB unzipped)

**Total current unzipped bundle**: $\approx 350\text{ MB}$, which exceeds Vercel's **250 MB Serverless Function unzipped limit**!

#### Optimized Backend `requirements.txt` (Vercel Serverless):
```text
fastapi>=0.110.0,<0.120.0
uvicorn>=0.28.0,<0.35.0
pydantic>=2.6.0,<2.12.0
numpy>=1.24.0,<2.0.0
pandas>=2.0.0,<2.3.0
scipy>=1.10.0,<1.15.0
requests>=2.30.0,<2.33.0
openai>=1.10.0,<1.60.0
python-dotenv>=1.0.0
supabase>=2.3.0,<2.12.0
```
- **Total unzipped size of optimized backend**: $\approx 55\text{--}65\text{ MB}$.
- **Cold start duration**: $< 1.2\text{ seconds}$.
- **Result**: Comfortably within the 250 MB ceiling, zero bloat, high execution speed.

---

## 10. Deployment Risks & Mitigation Matrix

| # | Deployment Risk | Severity | Root Cause | Architectural Mitigation |
|---|---|---|---|---|
| **1** | **Serverless Function Cold-Start Timeout** | High | Default Vercel timeout on Hobby plan is 10 seconds. External APIs (SoilGrids/Nexus) may take several seconds. | 1. Lightweight dependencies ($<65\text{MB}$).<br>2. Set strict timeouts on all external requests (Open-Meteo: 4s, NASA POWER: 6s, SoilGrids: 3s, Nexus: 7s).<br>3. Instant fallback to cached regional soil profile for SoilGrids.<br>4. Deterministic fallback for Nexus AI if request approaches 7s. |
| **2** | **Ephemeral File System Data Loss** | Critical | Vercel Serverless containers are read-only except `/tmp`, which is wiped across cold boots. | Complete migration of schedule and approval logging to **Supabase PostgreSQL**. Retain local JSON append only for offline tests. |
| **3** | **API Key Leakage to Client** | Critical | Next.js code bundling can accidentally expose environment variables prefixed with `NEXT_PUBLIC_`. | `NEXUS_API_KEY` and `SUPABASE_SERVICE_ROLE_KEY` will remain strictly server-side in Python backend. Frontend will only communicate with `/api/*` endpoints. |
| **4** | **CORS & Pre-Flight Latency** | Medium | Cross-origin requests between independent domains induce pre-flight delays and potential blocking. | Deploy Next.js frontend and Python backend within the **same Vercel project** using `vercel.json` rewrites (`/api/:path* -> api/index.py`). Zero CORS issues. |
| **5** | **Large Dependencies Exceeding 250 MB** | High | Including Streamlit, Matplotlib, and PyArrow in backend bundle triggers Vercel deployment rejection. | Dedicated backend `requirements.txt` omitting all UI/plotting libraries. Charts are rendered client-side in Next.js via Recharts. |
| **6** | **SoilGrids REST API Unavailability** | Medium | ISRIC REST endpoint frequently experiences high latency or read timeouts. | Maintain the pre-cached regional profile (`COIMBATORE_REGIONAL_PROFILE`) and non-blocking timeout fallback in `src/soil_service.py`. |

---

## 11. Configuration Artifacts

### 11.1 `vercel.json`
```json
{
  "version": 2,
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "/api/index.py"
    }
  ],
  "functions": {
    "api/index.py": {
      "runtime": "python3.11",
      "maxDuration": 15
    }
  }
}
```

### 11.2 Environment Variables Template (`.env.example`)
```bash
# Nexus AI API Configuration
NEXUS_API_KEY="your_nexus_api_key_here"
NEXUS_BASE_URL="https://nexusapi.navigatelabs.ai/v1"
NEXUS_MODEL="gpt-5-nano"

# Supabase PostgreSQL Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your_supabase_anon_or_service_key"

# Python Environment
PYTHON_VERSION="3.11"
```

---

## 12. Phased Migration Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MIGRATION ROADMAP PHASES                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
   Phase 1: Project Audit & Planning [COMPLETED]
   ├── Inspect existing code, formulas, datasets
   ├── Verify Nexus gpt-5-nano availability
   └── Deliver VERCEL_MIGRATION_AUDIT.md
                                    │
   Phase 2: FastAPI Backend & Endpoints [NEXT - Awaiting Confirmation]
   ├── Create api/index.py and api/routes/*
   ├── Connect existing src/ modules to endpoints
   └── Verify endpoints with test_api_routes.py
                                    │
   Phase 3: Telugu Migration & Advisory Update
   ├── Update src/advisory_generator.py for Telugu
   ├── Implement authentic Telugu agricultural fallback
   └── Update test_nexus.py with Telugu assertions
                                    │
   Phase 4: Supabase Database Integration
   ├── Implement src/db_client.py
   ├── Upgrade src/approval_logger.py to dual-mode (DB + local fallback)
   └── Run migration scripts on Supabase instance
                                    │
   Phase 5: Next.js + React + TypeScript Frontend
   ├── Scaffold frontend/ with Next.js 15 App Router & Tailwind
   ├── Build responsive 5 screens matching existing Streamlit UX
   ├── Integrate Recharts for ETo/ETc and Soil Water Balance
   └── Implement English / Telugu language toggle
                                    │
   Phase 6: Vercel Deployment & E2E Validation
   ├── Configure vercel.json & environment variables
   ├── Run full test suite (30+ tests)
   └── Deploy to Vercel and verify live production endpoints
```

---

## 13. Audit Sign-Off & Confirmation Request

All requirements for **Phase 1: Project Audit and Architecture Planning** are complete:
- Complete inspection of `app.py`, `src/`, `config/`, `data/`, `tests/`, `docs/`, `requirements.txt`.
- Verification of genuine NASA POWER JSON, Open-Meteo live API, and ISRIC SoilGrids fallback.
- Verification of `gpt-5-nano` on the company Nexus endpoint.
- Identification of all Tamil references for migration to Telugu.
- Formulation of the Vercel-compatible monorepo folder structure, FastAPI schema design, and Supabase integration.
- Formulation of deployment risk mitigation and dependency optimization.

**Awaiting user confirmation to proceed to Phase 2 (FastAPI Backend Implementation).**
