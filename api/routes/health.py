"""
Health and Status Check Route
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from src.nexus_client import NexusClient
from src.db_client import is_supabase_configured
from config.settings import APP_ENV, IS_VERCEL

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", summary="System Health and Environment Probe")
def get_health():
    """
    Returns API health status, runtime metadata, and configuration status.
    """
    nexus = NexusClient()
    return {
        "status": "healthy",
        "app_title": "AGRI-2 Irrigation Scheduling Advisor",
        "version": "1.0.0",
        "environment": "production-ready",
        "app_env": APP_ENV,
        "is_vercel": IS_VERCEL,
        "nexus_configured": nexus.is_configured(),
        "nexus_model": nexus.model,
        "supabase_configured": is_supabase_configured(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

