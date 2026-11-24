# System Architecture: AGRI-2 Irrigation Scheduling Advisor

## 1. System Philosophy and Design Principles
The core architecture of AGRI-2 is founded on the principle of **computational sovereignty**:
1. **Mathematical Single Source of Truth**: All physical, agronomic, and hydrological calculations (Reference Evapotranspiration, Crop Coefficients, Effective Rainfall, and Soil Water Balance) are strictly computed by deterministic Python engines adhering to FAO-56 standards.
2. **LLM Boundary Protection**: The Large Language Model (Nexus API / GPT-5-nano) **never** calculates, infers, or alters any numerical values. Its role is strictly confined to farmer-facing qualitative explanation, rationale summarization, and multilingual translation (English & Tamil).
3. **Manual Farmer In-the-Loop Control**: In strict compliance with agricultural safety guidelines, all valve operations remain strictly manual. The application requires explicit human farmer approval before recording a schedule.

---

## 2. Architectural Block Diagram

```mermaid
flowchart TD
    subgraph Data & Reference Layer
        A1[Sample Scenarios CSV\ndata/sample/] --> DL[data_loader.py]
        A2[User Uploaded CSV] --> DL
        A3[Open-Meteo Live API\nweather_service.py] --> DL
        A4[NASA POWER Daily API\nnasa_power_service.py] --> DL
        A5[ISRIC SoilGrids REST API\nsoil_service.py] --> SG[Soil Properties\nModelled Estimates]
        A6[TNAU Rice Guidelines\nagricultural_reference.py] --> REF[Agronomic Reference\nKc, AWD, Critical Stages]
    end

    subgraph Deterministic Agricultural Engine
        DL --> ETO[eto_calculator.py\nFAO-56 Penman-Monteith]
        ETO --> ETC[crop_coefficients.py\nKc Selection & Adjustment]
        REF -.-> ETC
        DL --> RAIN[rainfall.py\nEffective Rainfall & Bund Storage]
        ETC --> SWB[soil_water_balance.py\nPaddy AWD & Root Zone Depletion]
        RAIN --> SWB
        SG -.-> SWB
        SWB --> SCHED[irrigation_scheduler.py\n7-Day Decision & Volume Engine]
    end

    subgraph AI Explanation & Translation Layer
        SCHED --> AG[advisory_generator.py\nPrompt Builder]
        AG --> NEX[nexus_client.py\nNexus OpenAI-compatible Client]
        NEX --> LLM[Nexus AI API\nModel: gpt-5-nano]
        LLM --> AG
    end

    subgraph UI Presentation & Human Approval
        SCHED --> UI[app.py\nStreamlit Dashboard]
        AG --> UI
        SG --> UI
        REF --> UI
        UI --> APR[Farmer Schedule Approval\nRecord Decision to outputs/approval_history.json]
    end
```

---

## 3. Directory and Module Organization
- `config/settings.py`: Stores soil physical properties, crop stage parameters, geographical constants, and Nexus credentials.
- `src/eto_calculator.py`: FAO-56 Penman-Monteith reference evapotranspiration calculation.
- `src/crop_coefficients.py`: Stage-specific crop coefficient selection and aerodynamic corrections.
- `src/rainfall.py`: USDA-SCS effective precipitation model and rice bund retention simulation.
- `src/soil_water_balance.py`: Dual-mode simulation: Wetland Rice (Ponded & AWD) and Upland Crop (Root Zone Depletion).
- `src/irrigation_scheduler.py`: 7-day schedule synthesis, water volume calculation (Litres), baseline comparison (15%+ water saving).
- `src/weather_service.py`: Open-Meteo live 7-day forecast retrieval with 10m-to-2m wind conversion and unit standardizations.
- `src/nasa_power_service.py`: NASA POWER daily API client, raw caching, and standardized historical agro-climatology processing.
- `src/soil_service.py`: ISRIC SoilGrids REST client for modelled soil property estimates with regional baseline fallback.
- `src/agricultural_reference.py`: TNAU Agritech water management guidelines, AWD protocol, and critical sensitivity stages.
- `src/nexus_client.py`: Robust client handling timeouts, rate limits, and fallback rules.
- `src/advisory_generator.py`: Bridges the calculation output to structured multi-lingual advisories.
- `app.py`: 5-screen interactive Streamlit web dashboard with 4 real-world data modes.
- `tests/`: Automated unit and integration test suite with official FAO-56 worked examples and data collection mocks.
