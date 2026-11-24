'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import { AdvisoryResponse, ApprovalResponse } from '../../services/types';
import {
  Sparkles,
  Languages,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  FileText,
  User,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function AiAdvisoryApproval() {
  const {
    schedule,
    language,
    setLanguage,
    farmerName,
    setFarmerName,
    locationName,
    setActiveScreen
  } = useApp();

  const isTelugu = language === 'Telugu';

  const [fieldNotes, setFieldNotes] = useState('');
  const [advisoryLoading, setAdvisoryLoading] = useState(false);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [advisory, setAdvisory] = useState<AdvisoryResponse | null>(null);
  const [approvalResult, setApprovalResult] = useState<ApprovalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Generate / Refresh AI Advisory from backend
  const handleGenerateAdvisory = async (selectedLang = language) => {
    if (!schedule) return;
    setAdvisoryLoading(true);
    setError(null);

    try {
      const res = await api.generateAdvisory({
        schedule_result: schedule as unknown as Record<string, unknown>,
        language: selectedLang,
        farmer_name: farmerName,
        field_location: locationName,
      });
      setAdvisory(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate advisory from AI.';
      setError(msg);
    } finally {
      setAdvisoryLoading(false);
    }
  };

  // Submit Approval or Decline decision to backend
  const handleSubmitDecision = async (decision: 'APPROVED' | 'DECLINED') => {
    if (!schedule) return;
    setApprovalLoading(true);
    setError(null);

    try {
      const res = await api.recordApproval({
        schedule_id: schedule.schedule_id,
        decision,
        farmer_name: farmerName.trim() || 'Farmer / Operator',
        field_notes: fieldNotes.trim(),
        approved_depth_mm: schedule.water_reduction_scorecard.recommended_total_depth_mm,
        approved_volume_litres: Math.round(schedule.water_reduction_scorecard.recommended_volume_litres),
        crop: schedule.crop,
        field_area_acres: schedule.field_area_acres,
      });
      setApprovalResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record approval decision.';
      setError(msg);
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleLanguageSwitch = (newLang: 'English' | 'Telugu') => {
    setLanguage(newLang);
    if (schedule) {
      handleGenerateAdvisory(newLang);
    }
  };

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Top Header & Language Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold mb-1 border border-emerald-200">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>Company Nexus AI (gpt-5-nano)</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTelugu ? 'AI సలహాదారు మరియు రైతు ఆమోదం' : 'AI Agronomic Advisory & Farmer Review'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Qualitative linguistic translation of physical calculations into actionable field guidance.
          </p>
        </div>

        {/* Bilingual Language Switcher Toggle */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200">
          <button
            onClick={() => handleLanguageSwitch('English')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              language === 'English'
                ? 'bg-white text-agri-900 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span>English</span>
          </button>
          <button
            onClick={() => handleLanguageSwitch('Telugu')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              language === 'Telugu'
                ? 'bg-white text-agri-900 shadow-xs border border-slate-200 font-telugu'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Languages className="w-3.5 h-3.5 text-emerald-600" />
            <span>తెలుగు (Telugu)</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Backend Advisory / Approval Error</p>
            <p className="mt-0.5 text-red-700">{error}</p>
          </div>
        </div>
      )}

      {schedule ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: AI Advisory Text Box */}
          <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-agri-600" />
                <h3 className="font-semibold text-slate-900 text-sm">
                  {isTelugu ? 'పంట సలహా నివేదిక' : 'Bilingual Agronomic Advisory'}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                {advisory && (
                  <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                    {advisory.is_fallback ? 'Rule Fallback' : `Nexus (${advisory.model_used || 'gpt-5-nano'})`}
                  </span>
                )}
                <button
                  onClick={() => handleGenerateAdvisory()}
                  disabled={advisoryLoading}
                  className="px-2.5 py-1 text-2xs font-semibold text-agri-700 hover:bg-agri-50 rounded-md border border-agri-200 transition-colors"
                >
                  {advisoryLoading ? 'Refreshing...' : 'Regenerate'}
                </button>
              </div>
            </div>

            {advisoryLoading ? (
              <div className="p-12 text-center space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-agri-600 mx-auto" />
                <p className="text-xs text-slate-500">
                  {isTelugu
                    ? 'Nexus AI సలహాను రూపొందిస్తోంది...'
                    : 'Nexus AI is formatting hydrological schedule into qualitative guidance...'}
                </p>
              </div>
            ) : advisory ? (
              <div className={`p-5 rounded-xl bg-slate-50/70 border border-slate-200/80 text-slate-800 text-sm whitespace-pre-line leading-relaxed ${isTelugu ? 'font-telugu text-base' : ''}`}>
                {advisory.advisory_markdown}
              </div>
            ) : (
              <div className="p-8 text-center space-y-3 border border-dashed border-slate-200 rounded-xl">
                <p className="text-xs text-slate-500">
                  {isTelugu
                    ? 'AI సలహాను రూపొందించడానికి దిగువ బటన్‌ను క్లిక్ చేయండి.'
                    : 'Click below to generate personalized farmer advisory in ' + language + '.'}
                </p>
                <button
                  onClick={() => handleGenerateAdvisory()}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs shadow-xs transition-colors cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{isTelugu ? 'సలహాను రూపొందించండి' : `Generate ${language} Advisory`}</span>
                </button>
              </div>
            )}

            {/* Strict Computational Boundary Notice */}
            <div className="p-3 rounded-lg bg-slate-100/70 text-2xs text-slate-500 border border-slate-200">
              <strong>Strict Boundary:</strong> Nexus AI provides qualitative explanations only. The LLM does not perform, modify, or recalculate physical water numbers.
            </div>
          </div>

          {/* Right Column: Farmer Review & Manual Approval Submission */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>{isTelugu ? 'రైతు సమీక్ష & కార్యాచరణ ఆమోదం' : 'Farmer Schedule Review & Decision'}</span>
                </h3>
                <p className="text-2xs text-slate-400 mt-0.5">
                  Explicit farmer sign-off for audit tracking in Supabase PostgreSQL.
                </p>
              </div>

              {/* Pre-populated Schedule Details */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Verified Schedule ID:</span>
                  <span className="font-mono font-bold text-slate-800">{schedule.schedule_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Crop & Area:</span>
                  <span className="font-semibold text-slate-800">{schedule.crop} ({schedule.field_area_acres} Acre)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Approved Total Depth:</span>
                  <span className="font-bold text-emerald-700">
                    {schedule.water_reduction_scorecard.recommended_total_depth_mm.toFixed(1)} mm
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Approved Total Volume:</span>
                  <span className="font-bold text-emerald-700">
                    {schedule.water_reduction_scorecard.recommended_volume_litres.toLocaleString()} L
                  </span>
                </div>
              </div>

              {/* Farmer Name & Notes Input */}
              <div className="space-y-3">
                <div>
                  <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                    {isTelugu ? 'రైతు పేరు' : 'Farmer / Operator Name'}
                  </label>
                  <div className="relative">
                    <User className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      value={farmerName}
                      onChange={(e) => setFarmerName(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 pl-8 pr-3 py-2 text-xs font-medium text-slate-900 focus:border-agri-600 focus:outline-hidden"
                      placeholder="e.g. Ramu / Murugan"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-2xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                    {isTelugu ? 'పొలం పరిశీలన గమనికలు' : 'Field Observations / Notes'}
                  </label>
                  <textarea
                    rows={3}
                    value={fieldNotes}
                    onChange={(e) => setFieldNotes(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:border-agri-600 focus:outline-hidden"
                    placeholder="e.g. Bund height intact, soil moisture adequate in south plot..."
                  />
                </div>
              </div>

              {/* Safety Manual Operation Policy Banner */}
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-2xs space-y-1">
                <div className="font-bold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span>Mandatory Manual Operation Rule</span>
                </div>
                <p>
                  Approving this schedule logs your confirmation for manual pump/valve operation. No automated actuator signals are triggered.
                </p>
              </div>

              {/* Approval / Decline Action Buttons */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <button
                  onClick={() => handleSubmitDecision('APPROVED')}
                  disabled={approvalLoading}
                  className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-agri-600 hover:bg-agri-700 active:bg-agri-800 text-white font-semibold text-xs shadow-xs transition-colors cursor-pointer disabled:opacity-60"
                >
                  {approvalLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  <span>{isTelugu ? 'షెడ్యూల్ ఆమోదించండి' : 'Approve Schedule'}</span>
                </button>

                <button
                  onClick={() => handleSubmitDecision('DECLINED')}
                  disabled={approvalLoading}
                  className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-slate-100 hover:bg-red-50 hover:text-red-700 text-slate-700 font-semibold text-xs border border-slate-300 transition-colors cursor-pointer disabled:opacity-60"
                >
                  <XCircle className="w-4 h-4" />
                  <span>{isTelugu ? 'తిరస్కరించండి' : 'Decline Schedule'}</span>
                </button>
              </div>

              {/* Successful Response Confirmation Card */}
              {approvalResult && (
                <div className="mt-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold flex items-center gap-1.5 text-emerald-800">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>{approvalResult.decision} Recorded</span>
                    </span>
                    <span className="text-2xs font-mono font-bold px-2 py-0.5 rounded-sm bg-white text-emerald-800 border border-emerald-200">
                      {approvalResult.approval_id}
                    </span>
                  </div>
                  <p className="text-emerald-900/90 text-2xs leading-normal">
                    {approvalResult.message}
                  </p>
                  <div className="pt-1 border-t border-emerald-200/60 flex items-center justify-between text-2xs text-emerald-800">
                    <span>Mode: {approvalResult.persisted_mode}</span>
                    <button
                      onClick={() => setActiveScreen('history')}
                      className="font-semibold underline cursor-pointer hover:text-emerald-950"
                    >
                      View in History
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">No Active Schedule to Advise or Approve</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Please calculate an irrigation schedule first from the Farmer Dashboard before generating advisories or submitting approval.
            </p>
          </div>
          <button
            onClick={() => setActiveScreen('dashboard')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs cursor-pointer shadow-xs transition-colors"
          >
            <span>Go to Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
