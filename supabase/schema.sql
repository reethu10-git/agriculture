-- ==============================================================================
-- AGRI-2: Phase 4 Supabase PostgreSQL Schema Reference
-- Apply directly in Supabase Dashboard SQL Editor or via Supabase CLI
-- ==============================================================================

-- 1. Create schedules table
CREATE TABLE IF NOT EXISTS public.schedules (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    crop TEXT NOT NULL,
    growth_stage TEXT NOT NULL,
    soil_type TEXT NOT NULL,
    field_area_acres NUMERIC NOT NULL CHECK (field_area_acres > 0),
    weather_source TEXT NOT NULL,
    provenance_status TEXT NOT NULL,
    recommended_total_depth_mm NUMERIC NOT NULL CHECK (recommended_total_depth_mm >= 0),
    recommended_volume_litres BIGINT NOT NULL CHECK (recommended_volume_litres >= 0),
    water_savings_percent NUMERIC NOT NULL,
    daily_schedule JSONB NOT NULL DEFAULT '[]'::jsonb,
    full_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 2. Create approvals table with foreign key constraint
CREATE TABLE IF NOT EXISTS public.approvals (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES public.schedules(id) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    farmer_name TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('APPROVED', 'DECLINED')),
    field_notes TEXT DEFAULT '',
    approved_depth_mm NUMERIC NOT NULL CHECK (approved_depth_mm >= 0),
    approved_volume_litres BIGINT NOT NULL CHECK (approved_volume_litres >= 0),
    crop TEXT NOT NULL,
    field_area_acres NUMERIC NOT NULL CHECK (field_area_acres > 0)
);

-- 3. Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_schedules_created_at ON public.schedules (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedules_crop ON public.schedules (crop);
CREATE INDEX IF NOT EXISTS idx_approvals_schedule_id ON public.approvals (schedule_id);
CREATE INDEX IF NOT EXISTS idx_approvals_recorded_at ON public.approvals (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_farmer_name ON public.approvals (farmer_name);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;

-- 5. Revoke public/anon access
REVOKE ALL ON public.schedules FROM anon;
REVOKE ALL ON public.approvals FROM anon;
