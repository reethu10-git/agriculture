# AGRI-2 – Phase 5: Next.js Frontend Implementation Report

**Project**: AGRI-2 – Irrigation Scheduling Advisor  
**Phase**: Phase 5 – Next.js Frontend Implementation  
**Date**: November 2026  
**Status**: Completed  
**Frontend Framework**: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Recharts, Lucide Icons  
**Next.js Production Build**: `✓ Compiled successfully`, `✓ Generating static pages (4/4)` (Zero TypeScript or Linting Errors)  
**Backend Automated Tests**: 57 Passed (44 Existing + 13 Supabase Integration Tests)

---

## 1. Frontend Folder Structure

The complete frontend application is encapsulated inside the `frontend/` directory, following Next.js 15 App Router architecture:

```text
frontend/
├── app/
│   ├── globals.css              # Tailwind base, utilities, custom scrollbars, and Noto Sans Telugu font
│   ├── layout.tsx               # Root layout with HTML metadata and AppProvider context wrapper
│   └── page.tsx                 # Main application page managing dynamic screen rendering
├── components/
│   ├── Navbar.tsx               # Responsive navigation header, screen tabs, language toggle, API status
│   └── screens/
│       ├── FarmerDashboard.tsx  # Screen 1: Crop/soil setup, location coordinates, schedule generation
│       ├── WeatherDashboard.tsx # Screen 2: Open-Meteo live forecast & NASA POWER historical charts
│       ├── AgriculturalAnalysis.tsx # Screen 3: FAO-56 ETo, Kc, ETc, rainfall & soil water balance charts
│       ├── IrrigationSchedule.tsx # Screen 4: 7-day tactical matrix, depth, volume, benchmark scorecard
│       ├── AiAdvisoryApproval.tsx # Screen 5: Bilingual Nexus AI advisory, manual farmer approval sign-off
│       └── HistoryScreen.tsx    # Screen 6: Development / administrative schedule & approval audit logs
├── context/
│   └── AppContext.tsx           # React Context for cross-screen shared state (schedule, weather, language)
├── services/
│   ├── api.ts                   # Centralized API service interfacing with FastAPI REST endpoints
│   └── types.ts                 # Full TypeScript interfaces strictly aligned with backend Pydantic schemas
├── next.config.js               # Next.js configuration with server-side /api route rewrites
├── package.json                 # Project dependencies, scripts, and build definitions
├── postcss.config.js            # PostCSS configuration for Tailwind CSS
├── tailwind.config.js           # Custom agricultural color palette (agri, earth) and Telugu typography
└── tsconfig.json                # Strict TypeScript configuration
```

---

## 2. Six Screens Implemented

### Screen 1: Farmer Dashboard (`components/screens/FarmerDashboard.tsx`)
- **Profile Inputs**: Crop selection (Rice, Maize, Wheat, Tomato, Cotton, Sugarcane), growth-stage selection (Initial, Development, Mid-Season, Late-Season), and soil texture (Loamy, Clay, Clay Loam, Sandy Loam, Sandy).
- **Location & Dimensions**: Location name (Coimbatore, Tamil Nadu), coordinate inputs (11.0168°N, 76.9558°E), and field area (1.0 Acre default).
- **Water Conditions**: Configurable initial standing water depth (25 mm for lowland paddy) or initial root-zone depletion.
- **Weather Source**: Toggle between live Open-Meteo NWP forecasts, Coimbatore Kharif normal default, dry spell stress test, heavy monsoon scenario, and 30-day historical observations.
- **Schedule Calculation**: Triggers `POST /api/irrigation/schedule` with loading states, error containment, and live KPI summary cards with 1-click links to subsequent screens.

### Screen 2: Weather Dashboard (`components/screens/WeatherDashboard.tsx`)
- **Live Forecast (Open-Meteo)**: Ingests 7-day numerical weather prediction via `GET /api/weather/forecast`. Displays temperature envelope, relative humidity, wind speed (at 2m), solar radiation, and precipitation.
- **Historical Observations (NASA POWER)**: Date-range picker querying gridded satellite/reanalysis data via `GET /api/weather/historical`.
- **Data Provenance**: Clear badges distinguishing `LIVE_FORECAST` from `HISTORICAL_OBSERVATION_REANALYSIS` and `SIMULATION_DATA`.
- **Strict Provenance Rule**: Never labels synthetic simulation data as genuine weather.
- **Recharts Visualizations**:
  - Dual temperature envelope chart (Max, Min, Mean °C).
  - Dual-axis precipitation (mm) and shortwave solar radiation (MJ/m²/day) chart.
- **Detailed 7-Day Table**: Comprehensive day-by-day meteorological observation matrix.

### Screen 3: Agricultural Analysis (`components/screens/AgriculturalAnalysis.tsx`)
- Displays backend-calculated FAO-56 hydrological parameters:
  - Reference Evapotranspiration ($ET_0$)
  - Stage-specific Crop Coefficient ($K_c$) with climatic adjustments
  - Crop Evapotranspiration ($ET_c = K_c \times ET_0$)
  - Effective Rainfall ($P_{eff}$) accounting for bund retention and USDA-SCS methods
  - Daily Soil-Water Balance ($D_r$ depletion or standing water depth)
- **Recharts Visualizations**:
  - Daily Hydrological Flux (Crop $ET_c$ vs Effective Rainfall vs Recommended Irrigation).
  - Paddy Standing Water Depth Progression (tracking against lower 25 mm trigger and upper 50 mm bund retention limits).
- Complete tabular accounting matrix for daily FAO-56 soil-water balance.

### Screen 4: Irrigation Schedule (`components/screens/IrrigationSchedule.tsx`)
- **7-Day Tactical Matrix**: Daily breakdown with calendar dates, $ET_c$, effective rainfall, decision badge (`IRRIGATE` vs `SKIP`), recommended depth (mm), volumetric conversion (Litres), agronomic reason, and growth stage sensitivity.
- **Water Conservation Scorecard**:
  - Displayed **only when the backend provides a valid physical baseline**; does not make unsupported water-saving claims.
  - Compares recommended dynamic scheduling against conventional continuous flooding baseline (depth in mm, volume in Litres, percentage saved, and $\ge 15\%$ conservation target achievement).
- Prominently enforces the **Manual Field Valve Operation Policy**.

### Screen 5: AI Advisory and Approval (`components/screens/AiAdvisoryApproval.tsx`)
- **Bilingual Support**: Instant toggle between **English** and **తెలుగు (Telugu)** with Noto Sans Telugu typography.
- **Nexus AI Explanations**: Submits schedule to `POST /api/advisory` powered by Company Nexus API (`gpt-5-nano`) with automatic deterministic agronomic fallback.
- **Strict Computational Boundary**: The LLM provides qualitative explanations only; physical water numbers are computed strictly in Python.
- **Farmer Review Sign-Off**:
  - Displays verified schedule ID, crop, area, recommended depth, and volumetric requirement.
  - Farmer name and field observation notes input.
  - **Approve Schedule** (`APPROVED`) and **Decline Schedule** (`DECLINED`) actions sending verified payload to `POST /api/approval`.
  - Confirmation card displaying approval ID (`appr_...`), timestamp, persistence mode (`SUPABASE_POSTGRESQL` or `LOCAL_JSON_FALLBACK`), and audit confirmation.
- **Safety Rule**: Explicit warning confirming that field valve and pump operation remains strictly manual. No automated actuator signals are triggered.

### Screen 6: History (`components/screens/HistoryScreen.tsx`)
- Sub-tabs for **Calculated Schedules Repository** (`GET /api/irrigation/history`) and **Farmer Decision Audit Trail** (`GET /api/approval/history`).
- Displays schedule IDs, creation dates, crop, growth stage, soil, area, recommended depth, volume, savings percentage, and provenance.
- Displays approval decisions, approving farmer, timestamp, field notes, and persistence modes.
- **Documented Limitation Banner**: Explicitly identifies this view as restricted to **Development & Administrative Audit Mode**, documenting that multi-tenant farmer isolation is not enforced until Supabase Auth JWT is integrated.

---

## 3. API Integration Mapping

| Frontend Function | Backend Endpoint | Request Type | Purpose |
| :--- | :--- | :--- | :--- |
| `api.getHealth()` | `GET /api/health` | Query | System health and Nexus configuration check |
| `api.getWeatherForecast(lat, lon)` | `GET /api/weather/forecast` | Query | Open-Meteo live 7-day forecast |
| `api.getWeatherHistorical(lat, lon, start, end)` | `GET /api/weather/historical` | Query | NASA POWER historical reanalysis |
| `api.calculateSchedule(payload)` | `POST /api/irrigation/schedule` | Body (`IrrigationScheduleRequest`) | Computes 7-day schedule & persists to Supabase |
| `api.getScheduleHistory(limit, crop)` | `GET /api/irrigation/history` | Query | Retrieves historical schedule audit records |
| `api.generateAdvisory(payload)` | `POST /api/advisory` | Body (`AdvisoryRequest`) | Generates English or Telugu advisory via Nexus AI |
| `api.recordApproval(payload)` | `POST /api/approval` | Body (`ApprovalRequest`) | Validates schedule & records farmer approval |
| `api.getApprovalHistory(limit, schedId, farmer)` | `GET /api/approval/history` | Query | Retrieves farmer approval decision history |

Browser requests communicate through standard relative `/api` paths with Next.js rewrites in `next.config.js`. **Neither Nexus API keys nor Supabase service-role keys are ever contacted or exposed in client browser code.**

---

## 4. UI Libraries and Styling

| Library | Version | Role |
| :--- | :--- | :--- |
| **Next.js** | 15.1.7 | App Router framework, SSR/SSG, route rewrites |
| **React / React-DOM** | 19.0.0 | Component rendering and client interactivity |
| **TypeScript** | 5.7.3 | Static type safety and contract enforcement |
| **Tailwind CSS** | 3.4.17 | Utility-first styling with custom agricultural color palette |
| **Recharts** | 2.15.1 | Responsive SVG charting (composed line, bar, area charts) |
| **Lucide Icons** | 0.475.0 | Clean, accessible iconography |
| **Google Fonts** | Inter & Noto Sans Telugu | Typography supporting bilingual English and Telugu scripts |

---

## 5. Security Enforcements

1. **No Client-Side Credentials**:
   - `NEXUS_API_KEY` and `SUPABASE_SERVICE_ROLE_KEY` reside exclusively on the server side.
   - Zero private variables prefixed with `NEXT_PUBLIC_`.
2. **FastAPI Mediation**:
   - All external API calls (Nexus AI, Supabase PostgreSQL, Open-Meteo, NASA POWER) are mediated strictly by the FastAPI backend.
3. **No Automated Physical Actuators**:
   - Field operations strictly adhere to manual safety policy. The UI includes clear reminders that valve/pump operation must be performed manually.
4. **Documented Multi-Farmer Limitation**:
   - The history screen contains prominent administrative notices indicating that multi-tenant isolation requires future JWT authentication.

---

## 6. Build and Test Results

### Next.js Production Build
Executed from `frontend/`:
```text
> agri2-frontend@1.0.0 build
> next build

▲ Next.js 15.5.29

   Creating an optimized production build ...
 ✓ Compiled successfully in 33.3s
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (4/4)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                     136 kB         239 kB
└ ○ /_not-found                            997 B         104 kB
+ First Load JS shared by all             103 kB
  ├ chunks/255-d1a5c4d6b601e986.js       46.3 kB
  ├ chunks/4bd1b696-409494caf8c83275.js  54.2 kB
  └ other shared chunks (total)          2.05 kB

○  (Static)  prerendered as static content
```

### Backend Automated Test Suite
Executed from workspace root:
```text
python -m pytest tests/ -v
======================= 57 passed, 2 warnings in 12.67s =======================
```
All 57 tests passed with zero failures.

---

## 7. Known Limitations

1. **Farmer Authentication**: Individual farmer user accounts and login sessions are not yet active; all farmer actions operate via operator identity and admin audit mode.
2. **Hardware Telemetry**: In accordance with project safety guidelines, physical solenoid valves and IoT pump telemetry are not connected or automated.
3. **Next.js API Proxying in Development**: When running locally without Vercel, the frontend connects to `http://127.0.0.1:8000` via Next.js rewrites configured in `next.config.js`.

---

## 8. Local Startup Instructions

### 1. Start the FastAPI Backend
From the workspace root directory:
```bash
uvicorn api.index:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Probe: `http://127.0.0.1:8000/api/health`

### 2. Start the Next.js Frontend
In a separate terminal, navigate to the `frontend/` directory:
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to access the complete AGRI-2 Agricultural Advisor dashboard.

To run the production build locally:
```bash
cd frontend
npm run build
npm start
```
