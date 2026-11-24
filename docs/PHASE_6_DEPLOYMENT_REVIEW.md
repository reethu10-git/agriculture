# AGRI-2 – Phase 6: Vercel Configuration and Security Review

**Date:** 2026-11-24  
**Project:** AGRI-2 – Irrigation Scheduling Advisor  
**Review Type:** Architecture, Routing, Build Configuration & Security Audit  
**Deployment Status:** **NOT READY FOR PRODUCTION** (Pre-requisites & Security Gates Required)

---

## Executive Summary

This document presents a rigorous architectural, routing, build, and security review of the AGRI-2 full-stack application preparing for Vercel deployment. 

While the core agricultural hydrological engine (FAO-56 Penman-Monteith) and Next.js 15 user interface are functional and pass automated testing, **the project is currently NOT READY for public production deployment**. The review identifies a critical rewrite routing collision in `next.config.js`, severe unauthenticated database read/write vulnerabilities across all backend API endpoints, serverless bundle bloat from development dependencies (`streamlit`, `matplotlib`), and unverified cloud database connectivity.

---

## 1. Vercel Architecture Evaluation

We evaluated three potential deployment architectures:

| Architecture Option | Description | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Unified Monorepo (Single Vercel Project)** | Next.js frontend in `frontend/` and FastAPI serverless function in `api/index.py` hosted together under one Vercel project with rewrites. | Single domain; zero cross-origin (CORS) complications; unified Git trigger. | `next.config.js` vs `vercel.json` rewrite priority conflicts; shared build limits; Python bundle size risks. | **Recommended for small team / demo** (with configuration corrections). |
| **Option B: Vercel Services (Beta Monorepo)** | Uses Vercel's new multi-service configuration (`services: { frontend: ..., backend: ... }`) in `vercel.json`. | Native isolation of build pipelines and runtimes; dedicated health routing. | Requires Vercel Services beta feature availability; less community standardization. | **Viable alternative** once generally available. |
| **Option C: Decoupled Deployments (Frontend on Vercel, Backend on Dedicated Container)** | Next.js frontend on Vercel (`frontend/` root); FastAPI backend on container service (Cloud Run, Railway, or Render). | Complete independence; no serverless package size limits (pandas, scipy, pyarrow run smoothly); persistent connections. | Two separate URLs; requires CORS configuration; two deployment pipelines. | **Recommended for high-traffic multi-farmer production**. |

### Recommended Approach for Current Phase:
**Option A (Unified Monorepo with Corrected Configuration)** remains the simplest and most cost-effective path for AGRI-2 on Vercel, provided the configuration bugs detailed below are fixed prior to deployment.

---

## 2. API Routing Verification & Exact Path Analysis

### The Critical `next.config.js` vs `vercel.json` Priority Conflict

A critical issue exists in the interaction between `frontend/next.config.js` and `vercel.json`:

```javascript
// frontend/next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: process.env.API_BACKEND_URL 
        ? `${process.env.API_BACKEND_URL}/api/:path*` 
        : 'http://127.0.0.1:8000/api/:path*',
    },
  ];
}
```

#### The Problem:
1. **Evaluation Order**: Official Vercel documentation confirms that **framework-level rewrites (`next.config.js`) take precedence over platform-level rewrites (`vercel.json`)**.
2. **Production Failure**: If deployed without setting `API_BACKEND_URL`, Next.js will intercept every `/api/*` call and attempt to proxy it to `http://127.0.0.1:8000`. On Vercel serverless containers, there is **no process listening on port 8000**, resulting in immediate `ECONNREFUSED` (HTTP 500/502) errors for every user interaction.
3. **Redundancy**: `vercel.json` attempts to route `/api/(.*)` to `/api/index.py`, but this rule is eclipsed if `next.config.js` rewrites it first.

### Verification of FastAPI Path Preservation

In `api/index.py`, routes are explicitly mounted with the `/api` prefix:
```python
app.include_router(health.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(irrigation.router, prefix="/api")
app.include_router(advisory.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
```

When Vercel forwards a request from the edge to `@vercel/python`:
- Incoming URL: `https://agri2.vercel.app/api/irrigation/schedule`
- The ASGI adapter passes `scope["path"] = "/api/irrigation/schedule"`.
- Because the router is mounted with `prefix="/api"`, FastAPI matches `@router.post("/schedule")` exactly at `/api/irrigation/schedule`.
- **Verdict**: The internal FastAPI routing structure is **correct and preserves paths**, provided the request actually reaches `@vercel/python` without being intercepted by Next.js rewrites.

### Exact Endpoint Route Mapping

| Incoming Public URL | Next.js Handling | Vercel Rewrite Target | FastAPI Handler Path | Status |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/health` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `GET /api/health` | Valid |
| `GET /api/weather/forecast` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `GET /api/weather/forecast` | Valid |
| `GET /api/weather/historical` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `GET /api/weather/historical` | Valid |
| `POST /api/irrigation/schedule` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `POST /api/irrigation/schedule` | Valid |
| `GET /api/irrigation/history` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `GET /api/irrigation/history` | Valid |
| `POST /api/advisory` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `POST /api/advisory` | Valid |
| `POST /api/approval` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `POST /api/approval` | Valid |
| `GET /api/approval/history` | Must NOT proxy to 127.0.0.1 | `/api/index.py` | `GET /api/approval/history` | Valid |

---

## 3. Build & Runtime Configuration Audit

### 1. Root Directory & Monorepo Build Command
- **Current Root**: `.` (Repository root).
- **Frontend Directory**: `frontend/`.
- **Root `package.json`**:
  ```json
  "scripts": {
    "build": "cd frontend && npm install && npm run build"
  }
  ```
- **Next.js Output Directory**: Default is `.next` inside `frontend/`.
- **Vercel Output Setting**: In `vercel.json`, `outputDirectory: "frontend/.next"`.
  - *Recommendation*: Do not override Next.js output settings unnecessarily. In standard Vercel monorepos where root directory is set to `.`, Vercel recognizes `frontend/.next` when explicitly instructed, but if the project is configured with Root Directory as `frontend`, Vercel handles `.next` with zero configuration.

### 2. Python Runtime Compatibility & Dependency Size
- **Runtime**: `@vercel/python` runs Python 3.9 or 3.12 depending on system configuration.
- **Dependency File**: Vercel inspects the root `requirements.txt` when building Python functions in `api/`.
- **Serverless Bundle Bloat Risk**:
  The root `requirements.txt` currently contains:
  ```text
  streamlit>=1.30.0
  plotly>=5.18.0
  pandas>=2.0.0,<2.3.0
  numpy>=1.24.0,<2.0.0
  pyarrow>=14.0.0,<=18.1.0
  scipy>=1.10.0
  matplotlib>=3.7.0
  fastapi>=0.110.0
  uvicorn>=0.28.0
  pydantic>=2.6.0
  httpx>=0.27.0
  supabase>=2.3.0
  ```
  - `streamlit`, `matplotlib`, and `plotly` are **only needed for the local Streamlit application (`app.py`)**, not for the FastAPI backend.
  - Vercel serverless uncompressed limit is 250MB–500MB. Bundling `streamlit` + `matplotlib` + `scipy` + `pandas` risks crossing the function size ceiling during cloud packaging.
  - *Required Fix*: Separate `requirements.txt` or ensure `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` is set in Vercel environment variables, while preserving `requirements.txt` for local development.

### 3. Function Limits & Duration
- `vercel.json` currently specifies:
  ```json
  "functions": {
    "api/index.py": {
      "maxDuration": 60,
      "memory": 1024
    }
  }
  ```
- **Hobby vs Pro Plan Compatibility**:
  - On Vercel Hobby accounts, Serverless Functions default to and are capped at 300s, but older accounts or specific regions may enforce strict 15s ceilings.
  - 1024 MB memory is optimal for FAO-56 hydrological matrix calculations.

---

## 4. Deep Security Review: Public API Endpoints

A deep inspection of the four critical endpoints reveals severe security vulnerabilities for an unauthenticated public deployment:

### 1. `GET /api/irrigation/history`
- **Current Implementation**: Retrieves up to 100 historical irrigation schedules from Supabase (or local store) and returns them to the caller.
- **Vulnerability**: **Unrestricted Public Data Exposure**.
- **Impact**: Any anonymous user or bot on the public internet can scrape all recorded field parameters: crop, acreage, coordinates, daily irrigation volumes, and weather sources.
- **Risk Level**: **HIGH**.

### 2. `GET /api/approval/history`
- **Current Implementation**: Queries recent approvals with `limit=20` to `100`.
- **Vulnerability**: **PII Leakage & Agronomic Espionage**.
- **Impact**: Returns farmer names (`farmer_name`), field notes (`field_notes`), crops, acreage, approved irrigation depths, and approval decisions. There is no session, tenant, or ownership filter.
- **Risk Level**: **CRITICAL**.

### 3. `POST /api/irrigation/schedule`
- **Current Implementation**: Accepts arbitrary inputs (crop, coordinates, acreage), queries external APIs (Open-Meteo), computes FAO-56 schedules, and executes `insert_schedule()` into Supabase PostgreSQL using the server-side service-role key.
- **Vulnerability**: **Denial of Service (DoS) & Database Table Flooding**.
- **Impact**: An attacker can script requests to flood the database with millions of fake schedules, rapidly exhausting Supabase database storage limits and Open-Meteo API rate limits.
- **Risk Level**: **HIGH**.

### 4. `POST /api/approval`
- **Current Implementation**: Validates that `schedule_id` exists in Supabase, then records an `APPROVED` or `DECLINED` decision.
- **Vulnerability**: **Tampering & Decision Forgery**.
- **Impact**: While the endpoint validates that the `schedule_id` exists, **any anonymous caller who knows or guesses a `schedule_id` can submit an approval or decline under any farmer's name**. There is no identity check verifying that the caller is indeed the farmer who owns the field.
- **Risk Level**: **CRITICAL**.

### Flaw in Frontend "Admin Warning"
The frontend Screen 6 includes a banner reading:
> *"Development / Admin Mode only: Multi-farmer authentication is not configured."*

**A frontend UI banner provides zero backend security.** Any client can bypass Next.js and directly invoke `curl -X POST https://agri2.vercel.app/api/approval` or `curl https://agri2.vercel.app/api/approval/history`.

### Protection of the Supabase Service-Role Key
- The Supabase Service-Role Key (`SUPABASE_SERVICE_ROLE_KEY`) is kept in backend server-side environment variables and is **not exposed to client code** (no `NEXT_PUBLIC_` prefix).
- **However**, because the FastAPI endpoints themselves have no authentication, the FastAPI server functions as an **unauthenticated open proxy with service-role permissions** over the database.

### Mandatory Pre-Deployment Security Restrictions

Before making this application publicly accessible on Vercel, one of the following two security controls **MUST** be implemented:

1. **Option 1 (Immediate / Staging Gate – Recommended for Phase 6)**:
   Implement an **API Gateway Secret Header / Shared Token**:
   - Introduce an environment variable `AGRI_API_SECRET_TOKEN`.
   - Add a FastAPI middleware or dependency requiring `X-AGRI-KEY: <secret>` or HTTP Basic Auth for all `/api/approval/*` and `/api/irrigation/*` routes.
   - Configure Next.js server-side API handlers or proxy headers to supply this secret.
   - Restrict Vercel deployment to **Preview / Password Protected** mode using Vercel Deployment Protection.
2. **Option 2 (Production Multi-Tenant Architecture – Post-Phase 6)**:
   - Implement Supabase Auth (JWT).
   - Require bearer tokens (`Authorization: Bearer <jwt>`) on all history and modification routes.
   - Enforce Row Level Security (RLS) policies in PostgreSQL based on `auth.uid() = farmer_id`.

---

## 5. Supabase Readiness & Real Credential Protocol

### Required Environment Variables

| Variable Name | Environment | Description | Example / Format |
| :--- | :--- | :--- | :--- |
| `SUPABASE_URL` | Production & Preview | Supabase project REST URL | `https://[project-id].supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Production & Preview (Secret) | Server-side service role key (bypasses RLS) | `eyJhbGciOi...` (Never prefix with `NEXT_PUBLIC_`) |
| `APP_ENV` | Production | Enforces strict cloud persistence | `production` |
| `NEXUS_API_KEY` | Production & Preview (Secret) | API key for LLM explanations | `sk-nexus-...` |
| `NEXUS_BASE_URL` | Production & Preview | Base URL for Nexus endpoint | `https://nexusapi.navigatelabs.ai/v1` |
| `NEXUS_MODEL` | Production & Preview | Model identifier | `gpt-5-nano` |

### Production Persistence Behavior
- When `APP_ENV=production` and `SUPABASE_URL` is empty, `src/db_client.py` and `src/approval_logger.py` **refuse to fall back to local JSON**.
- They return an explicit `CONFIGURATION_ERROR` (HTTP 500) to prevent false persistence assurances in ephemeral serverless containers.

### Step-by-Step Cloud Verification Protocol (To be performed once credentials exist)

Do not claim live database persistence until the following four-step verification is executed with real cloud credentials:

1. **Step 1: Configure Credentials in Vercel Dashboard**:
   - Go to **Project Settings** &rarr; **Environment Variables**.
   - Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for Production and Preview environments.
   - Set `APP_ENV=production`.

2. **Step 2: Verify Live Schedule Insertion**:
   - Send a `POST /api/irrigation/schedule` payload (e.g., Rice, Coimbatore, 1.0 acre).
   - Confirm HTTP 200 response with `storage_mode: "SUPABASE_POSTGRESQL"`.
   - Log into the Supabase Dashboard &rarr; Table Editor &rarr; `schedules` table.
   - Verify that the returned `schedule_id` exists in the table with valid `daily_schedule` and `full_metadata` JSONB records.

3. **Step 3: Verify Live Approval Insertion**:
   - Send a `POST /api/approval` payload citing the verified `schedule_id`.
   - Confirm HTTP 200 response with `persisted_mode: "SUPABASE_POSTGRESQL"`.
   - Check Supabase Dashboard &rarr; Table Editor &rarr; `approvals` table.
   - Verify that the row is linked to `schedule_id` via foreign key constraint.

4. **Step 4: Verify Live Historical Retrieval**:
   - Call `GET /api/irrigation/history?limit=5`. Confirm that the inserted schedule is returned with `storage_mode: "SUPABASE_POSTGRESQL"`.
   - Call `GET /api/approval/history?limit=5`. Confirm that the approval record is returned with `storage_mode: "SUPABASE_POSTGRESQL"`.

---

## 6. Corrected Configuration Artifacts

To prevent the `next.config.js` rewrite conflict from crashing the Vercel deployment, the following configuration adjustment is required:

### Corrected `frontend/next.config.js`
In local development, `rewrites()` should proxy to `127.0.0.1:8000`. In production on Vercel, Next.js should **NOT** rewrite `/api/*` to `127.0.0.1:8000`, allowing Vercel's edge layer to handle `/api/*` directly:

```javascript
const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.resolve(__dirname),
  async rewrites() {
    // Only apply local proxy rewrite during development when API_BACKEND_URL is not set
    if (process.env.NODE_ENV === 'development' && !process.env.API_BACKEND_URL) {
      return [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8000/api/:path*',
        },
      ];
    }
    // When API_BACKEND_URL is explicitly configured (e.g. separate backend host)
    if (process.env.API_BACKEND_URL) {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.API_BACKEND_URL}/api/:path*`,
        },
      ];
    }
    // In unified Vercel deployment without external backend URL, return no rewrites
    // so vercel.json routes /api/* directly to the Python serverless function.
    return [];
  },
};

module.exports = nextConfig;
```

---

## 7. Deployment Readiness Decision

| Evaluation Area | Status | Critical Findings |
| :--- | :--- | :--- |
| **Agricultural Computation Engine** | **PASS** | FAO-56 Penman-Monteith logic intact in Python; verified by 58 passing tests. |
| **Next.js 15 Frontend Build** | **PASS** | Compiles cleanly in 2.7s; 0 TypeScript or lint errors. |
| **Streamlit Preservation** | **PASS** | `app.py` remains unmodified and operational for local desktop/field use. |
| **Routing Architecture** | **ACTION REQUIRED** | `frontend/next.config.js` will intercept `/api/*` and fail with `ECONNREFUSED` in production unless updated to check `NODE_ENV`. |
| **Serverless Bundle Optimization** | **ACTION REQUIRED** | Root `requirements.txt` includes unnecessary desktop dependencies (`streamlit`, `matplotlib`). Requires `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` or dependency trimming. |
| **API Security & Multi-Farmer Isolation** | **FAIL** | All history and modification endpoints are publicly open without authentication. Vulnerable to data harvesting, decision forgery, and database flooding. |
| **Supabase Cloud Persistence** | **PENDING** | Cloud credentials have not been configured or tested against a real Supabase instance. |

### Final Decision:
# **NOT READY FOR PRODUCTION DEPLOYMENT**

### Required Action Items Before Production Release:
1. Update `frontend/next.config.js` to avoid proxying to `127.0.0.1:8000` in production.
2. Enable Vercel Deployment Protection (password protect or team-only access) OR introduce an API secret key header before exposing endpoints to the public internet.
3. Provision real Supabase project credentials, configure them in Vercel, and execute the 4-step live verification protocol.
4. Set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` in Vercel project settings to prevent serverless function packaging failures.
