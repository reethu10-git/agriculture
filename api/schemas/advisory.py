"""
Pydantic Schemas for AI Advisory Endpoints
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AdvisoryRequest(BaseModel):
    schedule_result: Dict[str, Any] = Field(..., description="Full output from /api/irrigation/schedule")
    language: str = Field(default="English", description="Requested language (English, Telugu)")
    farmer_name: Optional[str] = Field(default="Farmer", description="Farmer name for personalized salutation")
    field_location: Optional[str] = Field(default="Coimbatore", description="Field location for context")

class AdvisoryResponse(BaseModel):
    success: bool
    language: str
    model_used: Optional[str] = None
    advisory_markdown: str
    is_fallback: bool
    error_message: Optional[str] = None
