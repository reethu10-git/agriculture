"""
Pydantic Schemas for Farmer Approval Endpoints
"""
from typing import Optional, List
from pydantic import BaseModel, Field

class ApprovalRequest(BaseModel):
    schedule_id: str = Field(..., description="Unique schedule identifier being approved or declined")
    decision: str = Field(..., pattern="^(APPROVED|DECLINED)$", description="Farmer decision: APPROVED or DECLINED")
    farmer_name: str = Field(..., min_length=1, max_length=150, description="Name of the approving farmer")
    field_notes: Optional[str] = Field(default="", description="Optional farmer field observations or notes")
    approved_depth_mm: float = Field(..., ge=0.0, description="Total recommended water depth in mm approved")
    approved_volume_litres: int = Field(..., ge=0, description="Total recommended water volume in litres approved")
    crop: str = Field(default="Rice", description="Crop name")
    field_area_acres: float = Field(default=1.0, gt=0.0, description="Field area in acres")

class ApprovalResponse(BaseModel):
    success: bool
    approval_id: str
    schedule_id: str
    decision: str
    farmer_name: str
    recorded_at: str
    message: str
    persisted_mode: str = Field(default="SERVICE_INTERFACE_STUB", description="Persistence mode (e.g. LOCAL_JSON_FALLBACK / SUPABASE_POSTGRESQL)")

class ApprovalHistoryItem(BaseModel):
    id: str
    schedule_id: str
    recorded_at: str
    farmer_name: str
    decision: str
    field_notes: Optional[str] = ""
    approved_depth_mm: float
    approved_volume_litres: int
    crop: str
    field_area_acres: float

class ApprovalHistoryResponse(BaseModel):
    success: bool
    count: int
    storage_mode: str
    approvals: List[ApprovalHistoryItem]
