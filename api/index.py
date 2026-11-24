"""
AGRI-2 FastAPI Application Entry Point
Supports local development (uvicorn api.index:app) and Vercel Serverless Function deployment.
"""
import sys
import os
import logging
from pathlib import Path

# Ensure root repository directory is on sys.path for Vercel serverless execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import health, weather, irrigation, advisory, approval

# Configure structured logging without sensitive leaks
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agri2.api")

app = FastAPI(
    title="AGRI-2 Irrigation Scheduling Advisor",
    description=(
        "Production-ready agricultural advisory REST API combining physical FAO-56 Penman-Monteith "
        "hydrology calculations, live & historical weather integration, and Nexus AI explanations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Enable CORS for Next.js frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for uncaught server errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_type": "INTERNAL_SERVER_ERROR",
            "detail": "An internal server error occurred while processing the agricultural calculation."
        }
    )

# Include API route modules with /api prefix for Vercel route compatibility
app.include_router(health.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(irrigation.router, prefix="/api")
app.include_router(advisory.router, prefix="/api")
app.include_router(approval.router, prefix="/api")

# Also mount root /health for generic container health probes
app.include_router(health.router)

@app.get("/", summary="Root Welcome")
def root_welcome():
    return {
        "title": "AGRI-2 Irrigation Scheduling Advisor API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
