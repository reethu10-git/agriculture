# AGRI-2 – Phase 6: Vercel Deployment Preparation Report

**Project**: AGRI-2 – Irrigation Scheduling Advisor  
**Phase**: Phase 6 – Vercel Deployment Preparation  
**Date**: November 2026  
**Status**: Ready for Deployment Review (Deployment Preparation Complete)  
**Hosting Target**: Vercel (Hybrid Serverless: Next.js 15 Frontend + FastAPI Python Backend)  
**Verification Status**:
- Next.js Production Build: `✓ Compiled successfully in 2.7s` (0 errors, 0 warnings)
- Pytest Backend Test Suite: `58 passed, 2 warnings in 5.91s` (100% passing)

---

## 1. Final Project Architecture & Folder Structure

The repository maintains a unified, monorepo-style structure supporting local development, containerized environments, legacy Streamlit exploration, and Vercel serverless execution:

```text
Industry solution/
├── api/                               # FastAPI Backend (Vercel Serverless Function)
│   ├── index.py                       # Serverless entrypoint (exposes ASGI `app`)
│   ├── routes/                        # Modular route controllers
│   │   ├── advisory.py                # POST /api/advisory (Nexus AI gpt-5-nano)
│   │   ├── approval.py                # POST /api/approval, GET /api/approval/history
│   │   ├── health.py                  # GET /api/health (Environment & config diagnostics)
│   │   ├── irrigation.py              # POST /api/irrigation/schedule, GET /api/irrigation/history
│   │   └── weather.py                 # GET /api/weather/forecast, GET /api/weather/historical
│   └── schemas/                       # Pydantic data contract models
├── config/
│   └── settings.py                    # Constants, soil/crop DBs, Vercel/serverless /tmp detection
├── data/                              # Meteorological scenarios and guidelines
├── docs/                              # Project phase migration and validation reports
│   ├── PHASE_3_TELUGU_MIGRATION_REPORT.md
│   ├── PHASE_4_SUPABASE_REPORT.md
│   ├── PHASE_5_FRONTEND_REPORT.md
│   ├── PHASE_5_FINAL_VALIDATION.md
│   └── PHASE_6_VERCEL_DEPLOYMENT_REPORT.md
├── frontend/                          # Next.js 15 Farmer-Facing Dashboard
│   ├── app/
│   │   ├── globals.css                # Tailwind base, utilities & Noto Sans Telugu font
│   │   ├── layout.tsx                 # Root layout & AppProvider context
│   │   └── page.tsx                   # Six responsive screens dynamic switcher
│   ├── components/
│   │   ├── Navbar.tsx                 # Navigation header & bilingual language toggle
│   │   └── screens/
│   │       ├── FarmerDashboard.tsx    # Screen 1: Field parameters & schedule calculation
│   │       ├── WeatherDashboard.tsx   # Screen 2: Open-Meteo & NASA POWER Recharts
│   │       ├── AgriculturalAnalysis.tsx # Screen 3: FAO-56 ETo, Kc, ETc & soil balance
│   │       ├── IrrigationSchedule.tsx # Screen 4: 7-day tactical matrix & water scorecard
│   │       ├── AiAdvisoryApproval.tsx # Screen 5: Bilingual Nexus AI advisory & approval
│   │       └── HistoryScreen.tsx      # Screen 6: Development / admin audit log
│   ├── context/
│   │   └── AppContext.tsx             # Shared state across screens
│   ├── services/
│   │   ├── api.ts                     # Browser API client querying /api endpoints
│   │   └── types.ts                   # TypeScript interfaces matching backend schemas
│   ├── next.config.js                 # Local dev rewrites & build optimization
│   ├── package.json                   # Next.js dependencies
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── tsconfig.json
├── src/                               # Agricultural Physics Core (Single Source of Truth)
│   ├── agricultural_reference.py
│   ├── crop_coefficients.py
│   ├── eto_calculator.py              # FAO-56 Penman-Monteith physical equation
│   ├── irrigation_scheduler.py        # 7-day soil water balance scheduler
│   ├── nasa_power_service.py          # NASA POWER API client
│   ├── weather_service.py             # Open-Meteo API client
│   ├── soil_service.py
│   ├── nexus_client.py                # Company Nexus API (gpt-5-nano) client
│   ├── advisory_generator.py          # Bilingual prompt template engine & fallback
│   ├── approval_logger.py             # Farmer decision logging with production enforcement
│   └── db_client.py                   # Supabase PostgreSQL client with production enforcement
├── supabase/
│   ├── migrations/                    # SQL migration scripts
│   └── schema.sql                     # Schema reference with RLS policies
├── tests/                             # Automated test suite (58 tests)
├── .env.example                       # Documented sanitized environment variables
├── app.py                             # Preserved working Streamlit application
├── package.json                       # Root Vercel build script coordinator
├── requirements.txt                   # Complete Python dependencies
└── vercel.json                        # Root Vercel deployment & routing configuration
```

---

## 2. Vercel Configuration & Routing Architecture

### `vercel.json` Specification
The root [vercel.json](file:///c:/Users/rethu/Downloads/Industry%20solution/vercel.json) orchestrates the hybrid deployment:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "version": 2,
  "framework": "nextjs",
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/.next",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/index.py"
    }
  ],
  "functions": {
    "api/index.py": {
      "maxDuration": 60,
      "memory": 1024
    }
  }
}
```

### Routing Flow
1. **API Routing (`/api/*`)**:
   - Every incoming request starting with `/api/` (e.g. `/api/irrigation/schedule`, `/api/weather/forecast`, `/api/health`) is intercepted by Vercel edge routing and dispatched to the Python Serverless Function [api/index.py](file:///c:/Users/rethu/Downloads/Industry%20solution/api/index.py).
   - `api/index.py` mounts all sub-routers with the `/api` prefix, ensuring routing match.
2. **Frontend Routing (`/*`)**:
   - All other requests (e.g. `/`, `/_next/*`, static assets) are handled by the Next.js App Router static and SSR pages.
3. **Local Development Parity**:
   - In local development, `frontend/next.config.js` proxies `/api/:path*` to `http://127.0.0.1:8000/api/:path*`, maintaining identical API contracts between local development and Vercel production.

### Serverless Execution Compatibility
- **`sys.path` Resolution**: [api/index.py](file:///c:/Users/rethu/Downloads/Industry%20solution/api/index.py) dynamically prepends the repository root to `sys.path`:
  ```python
  ROOT_DIR = Path(__file__).resolve().parent.parent
  if str(ROOT_DIR) not in sys.path:
      sys.path.insert(0, str(ROOT_DIR))
  ```
- **Read-Only Filesystem Safety**: Vercel Serverless Function runtime (`/var/task`) is strictly read-only. [config/settings.py](file:///c:/Users/rethu/Downloads/Industry%20solution/config/settings.py) detects Vercel environments (`VERCEL=1` or `AWS_LAMBDA_FUNCTION_NAME`) and redirects `OUTPUTS_DIR` to `/tmp/outputs` inside a safe `try...except` block, preventing `ReadOnlyFileSystemError`.

---

## 3. Production Environment Variables Checklist

The application requires specific server-side environment variables configured in the Vercel Project Settings. **None of these variables are prefixed with `NEXT_PUBLIC_`**, ensuring they are never bundled into client-side JavaScript.

| Variable Name | Required | Example / Placeholder | Purpose |
| :--- | :---: | :--- | :--- |
| `APP_ENV` | **Yes** | `production` | Enables strict production rules; disables local JSON fallback. |
| `NEXUS_API_KEY` | **Yes** | `sk-...` (Secret) | Company Nexus AI API authentication key. |
| `NEXUS_BASE_URL` | **Yes** | `https://nexusapi.navigatelabs.ai/v1` | Base URL for Nexus AI OpenAI-compatible endpoint. |
| `NEXUS_MODEL` | **Yes** | `gpt-5-nano` | Target AI model for bilingual agricultural explanations. |
| `SUPABASE_URL` | **Yes** | `https://<project-ref>.supabase.co` | Supabase project REST/PostgreSQL endpoint. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | `eyJhbGci...` (Secret) | Service-role key for backend writes (bypasses RLS safely). |
| `APP_DEFAULT_LANGUAGE` | No | `English` | Default UI language fallback. |

### Environment Variable Security Checklist:
- [x] No API keys or secrets in source code, Git commits, or documentation.
- [x] Zero sensitive variables exposed through `NEXT_PUBLIC_*`.
- [x] `SUPABASE_SERVICE_ROLE_KEY` is restricted strictly to backend Serverless Functions.
- [x] Logging statements filter out credentials, database URLs, and auth headers.

---

## 4. Production Database Persistence & Strict Enforcement

In accordance with Phase 6 requirements:
- **Production Persistence Requirement**: When `APP_ENV=production`, persistent storage in Supabase PostgreSQL is **mandatory**.
- **No Silent Local Fallback**: In `src/db_client.py` and `src/approval_logger.py`, if `APP_ENV == "production"` and Supabase is not configured or connection fails:
  - The system **does not silently fall back to local JSON files**.
  - Returns `{"success": False, "storage_mode": "CONFIGURATION_ERROR", "error": "Production persistence requires Supabase PostgreSQL configuration. Local JSON fallback is disabled in production."}`.
  - Causes FastAPI endpoints to return an explicit HTTP 500 status rather than reporting false persistence success.
- **Development/Test Continuity**: When `APP_ENV != "production"` (e.g. `development`), local JSON fallback remains available for offline development and test suites.

### Multi-Tenant Isolation & Authentication Notice
> [!WARNING] Production Security Limitation
> Farmer user authentication (JWT / user login) is not yet active. All schedule and approval writes are mediated through the server-side backend. 
> 
> Multi-farmer tenant isolation is **not claimed as production-secure** until individual farmer auth tokens are integrated and validated via Supabase Auth JWT in subsequent project phases.

---

## 5. Deployment Preparation Tests & Verification

### Test 1: Python Backend Test Suite
Executed from workspace root:
```bash
python -m pytest tests/ -v
```
**Result**:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\rethu\Downloads\Industry solution
collected 58 items

tests/test_api_routes.py (16 tests) ................                     [ 27%]
tests/test_crop_coefficients.py (3 tests) ...                            [ 32%]
tests/test_data_collection.py (8 tests) ........                         [ 46%]
tests/test_eto.py (3 tests) ...                                          [ 51%]
tests/test_nexus.py (6 tests) ......                                     [ 62%]
tests/test_rainfall.py (3 tests) ...                                     [ 67%]
tests/test_scheduler.py (2 tests) ..                                     [ 70%]
tests/test_supabase_integration.py (14 tests) ..............             [ 94%]
tests/test_water_balance.py (3 tests) ...                                [100%]

======================= 58 passed, 2 warnings in 5.91s ========================
```
- Covers production persistence enforcement (`test_production_persistence_enforcement_missing_supabase`).
- Covers schedule insertion, approval insertion, database retrieval, error containment, and validation checks.

### Test 2: Next.js Production Build
Executed from `frontend/` and through root `npm run build`:
```bash
npm --prefix frontend run build
```
**Result**:
```text
> agri2-frontend@1.0.0 build
> next build

▲ Next.js 15.5.29

   Creating an optimized production build ...
 ✓ Compiled successfully in 2.7s
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
- **0 TypeScript errors, 0 compilation warnings, 0 linting errors**.

### Test 3: Backend Import and Startup Verification
Executed:
```bash
python -c "from api.index import app; print('FastAPI app imported successfully:', app.title)"
```
**Result**:
```text
FastAPI app imported successfully: AGRI-2 Irrigation Scheduling Advisor
```

---

## 6. Step-by-Step Vercel Deployment Instructions

Follow these exact steps when ready to deploy to Vercel:

### Method A: Deploy via Vercel Git Integration (Recommended)
1. Push the project repository to GitHub / GitLab / Bitbucket.
2. In the [Vercel Dashboard](https://vercel.com/dashboard), click **Add New...** > **Project**.
3. Import the repository.
4. In **Project Settings**:
   - **Framework Preset**: Next.js
   - **Root Directory**: `./` (Leave as root directory)
   - **Build Command**: `cd frontend && npm install && npm run build` (configured automatically via `vercel.json`)
   - **Output Directory**: `frontend/.next` (configured automatically via `vercel.json`)
5. Under **Environment Variables**, add the production credentials:
   - `APP_ENV` = `production`
   - `NEXUS_API_KEY` = `<your-company-nexus-api-key>`
   - `NEXUS_BASE_URL` = `https://nexusapi.navigatelabs.ai/v1`
   - `NEXUS_MODEL` = `gpt-5-nano`
   - `SUPABASE_URL` = `https://<your-project>.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` = `<your-service-role-key>`
6. Click **Deploy**.

### Method B: Deploy via Vercel CLI
1. Ensure the Vercel CLI is installed:
   ```bash
   npm i -g vercel
   ```
2. Link the project from the workspace root:
   ```bash
   vercel link
   ```
3. Set the production environment variables:
   ```bash
   vercel env add APP_ENV production
   vercel env add NEXUS_API_KEY production
   vercel env add SUPABASE_URL production
   vercel env add SUPABASE_SERVICE_ROLE_KEY production
   ```
4. Deploy to production:
   ```bash
   vercel --prod
   ```

---

## 7. Known Limitations and Manual Configuration Items

1. **Live Supabase Credentials**:
   - The local development `.env` currently contains placeholder values (`SUPABASE_URL=`, `SUPABASE_SERVICE_ROLE_KEY=`).
   - Real cloud credentials must be entered in the Vercel Dashboard Environment Variables before running production schedules.
2. **Multi-Farmer Authentication**:
   - Farmer sign-off currently operates via operator identification. Individual farmer account isolation requires Supabase Auth JWT integration in a future iteration.
3. **Manual Field Safety**:
   - In accordance with project safety restrictions, valve and pump control remains strictly manual. No automated actuator commands are sent to physical hardware.
4. **Streamlit Exploration Application**:
   - `app.py` remains preserved in the repository for exploratory Streamlit use and is not affected by the Vercel Next.js deployment.
