# Vercel Read-Only Filesystem Fix Report

## Root Cause
When deployed to Vercel's Python serverless runtime, the application bundle under `/var/task` is mounted read-only, while `/tmp` is writable. During module import:
- `src/nasa_power_service.py` defined `NASA_POWER_RAW_DIR = DATA_DIR / "raw" / "nasa_power"` and `PROCESSED_DATA_DIR = DATA_DIR / "processed"`, and executed `.mkdir(parents=True, exist_ok=True)` at import time, triggering `OSError: [Errno 30] Read-only file system: '/var/task/data/raw'`.
- `src/soil_service.py` similarly defined `SOILGRIDS_RAW_DIR = DATA_DIR / "raw" / "soilgrids"` and `SOILGRIDS_PROCESSED_FILE = DATA_DIR / "processed" / "soilgrids_coimbatore.json"`, calling `.mkdir(parents=True, exist_ok=True)` at import time under `DATA_DIR`.

## Changes Made
1. **`src/nasa_power_service.py`**:
   - Imported `IS_VERCEL` from `config.settings`.
   - When `IS_VERCEL` is `True` (`VERCEL=1`), set:
     - `NASA_POWER_RAW_DIR = Path("/tmp/nasa_power")`
     - `PROCESSED_DATA_DIR = Path("/tmp/processed")`
   - Preserved `DATA_DIR / "raw" / "nasa_power"` and `DATA_DIR / "processed"` for local development.
   - Replaced broad exception handling with `except OSError as exc:` and `logger.warning(...)`.
2. **`src/soil_service.py`**:
   - Imported `IS_VERCEL` from `config.settings`.
   - When `IS_VERCEL` is `True`, set:
     - `SOILGRIDS_RAW_DIR = Path("/tmp/soilgrids")`
     - `SOILGRIDS_PROCESSED_FILE = Path("/tmp/processed/soilgrids_coimbatore.json")`
   - Preserved `DATA_DIR / "raw" / "soilgrids"` and `DATA_DIR / "processed" / "soilgrids_coimbatore.json"` for local development.
   - Replaced broad exception handling with `except OSError as exc:` and `logger.warning(...)`.
3. **`config/settings.py`**:
   - Replaced `except Exception: pass` around `OUTPUTS_DIR.mkdir(...)` with `except OSError as exc:` and `logger.warning(...)`.
4. **Test Isolation Fixes**:
   - `tests/test_api_routes.py::test_approval_endpoint_valid`: Isolated from live `.env` Supabase credentials by patching `src.db_client.is_supabase_configured` and `src.approval_logger.is_supabase_configured` to `False`, and redirecting `LOCAL_SCHEDULES_FILE` and `APPROVAL_FILE` to `tmp_path`.
   - `tests/test_supabase_integration.py::test_local_offline_fallback`: Patched `src.approval_logger.is_supabase_configured` (in addition to `src.db_client.is_supabase_configured`) and redirected local JSON store paths to `tmp_path`.

## Audit of Other Backend Modules
- `src/db_client.py` & `src/approval_logger.py`: Write local JSON fallbacks under `OUTPUTS_DIR` (`/tmp/outputs` on Vercel).
- `src/weather_service.py` & `src/agricultural_reference.py`: Read-only access to bundled `data/sample/` and `data/reference/` files.

## Verification & Test Results
### 1. Python Test Suite (`python -m pytest`)
- **58 passed, 0 failed, 0 skipped** (in 7.53s).

### 2. Vercel Mode (`VERCEL=1`) Import & Route Verification
- Verified `api.index:app` imports without filesystem errors under `VERCEL=1`:
  - `NASA_POWER_RAW_DIR`: `/tmp/nasa_power`
  - `PROCESSED_DATA_DIR`: `/tmp/processed`
  - `SOILGRIDS_RAW_DIR`: `/tmp/soilgrids`
- Tested FastAPI endpoints via `TestClient(app)` with `VERCEL=1`:
  - `GET /api/health` → `200 OK` (`is_vercel: True`)
  - `GET /api/weather/forecast` → `200 OK` (`success: True`)
  - `GET /api/weather/historical?start_date=2026-10-01&end_date=2026-10-07` → `200 OK` (`success: True`, `HISTORICAL_OBSERVATION_REANALYSIS`)
  - `POST /api/irrigation/schedule` → `200 OK` (`success: True`, `schedule_id: sch_9bd973fb1c`)
