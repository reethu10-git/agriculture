'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  CalendarDays,
  Droplets,
  TrendingDown,
  Info,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sprout,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';

export default function IrrigationSchedule() {
  const { schedule, setActiveScreen, language } = useApp();
  const isTelugu = language === 'Telugu';

  const dailyItems = schedule?.daily_schedule || [];
  const scorecard = schedule?.water_reduction_scorecard;

  // Verify whether the backend provided a valid baseline before claiming water savings
  const hasValidBaseline =
    scorecard &&
    scorecard.baseline_total_depth_mm > 0 &&
    scorecard.water_savings_percent !== undefined;

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-agri-100 text-agri-800 text-xs font-semibold mb-1 border border-agri-200">
            <CalendarDays className="w-3.5 h-3.5 text-agri-700" />
            <span>7-Day Tactical Schedule</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTelugu ? '7-రోజుల నీటిపారుదల కార్యాచరణ ప్రణాళిక' : '7-Day Irrigation Action Schedule'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Recommended physical water depth and volumes for field application. Manual valve/pump operation only.
          </p>
        </div>

        {schedule && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveScreen('advisory')}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs shadow-xs transition-colors cursor-pointer"
            >
              <span>{isTelugu ? 'AI సలహా & ఆమోదం' : 'Proceed to Farmer Approval'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {schedule ? (
        <div className="space-y-6">
          {/* Schedule Headline Metadata Banner */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-slate-400 block text-2xs uppercase font-semibold">Schedule ID</span>
                <span className="font-mono font-bold text-slate-800">{schedule.schedule_id}</span>
              </div>
              <div className="h-6 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-slate-400 block text-2xs uppercase font-semibold">Crop & Stage</span>
                <span className="font-semibold text-slate-800">{schedule.crop} ({schedule.growth_stage})</span>
              </div>
              <div className="h-6 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-slate-400 block text-2xs uppercase font-semibold">Field Area</span>
                <span className="font-semibold text-slate-800">{schedule.field_area_acres} Acre(s)</span>
              </div>
              <div className="h-6 w-px bg-slate-200 hidden sm:block" />
              <div>
                <span className="text-slate-400 block text-2xs uppercase font-semibold">Provenance</span>
                <span className="font-semibold text-emerald-700">{schedule.provenance_status}</span>
              </div>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-50 text-amber-900 border border-amber-200 text-2xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-700 shrink-0" />
              <span>Manual Field Valve Operation Policy</span>
            </div>
          </div>

          {/* Water-Saving Comparison Scorecard: ONLY shown when backend provides valid baseline */}
          {hasValidBaseline ? (
            <div className="bg-gradient-to-br from-emerald-50 via-agri-50 to-white rounded-xl border border-emerald-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3 border-b border-emerald-200/60 pb-2">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-emerald-700" />
                  <h3 className="font-bold text-agri-950 text-sm">
                    {isTelugu ? 'నీటి ఆదా స్కోర్‌కార్డ్ (ప్రామాణిక పోలిక)' : 'Water Conservation Scorecard (Benchmarked)'}
                  </h3>
                </div>
                {scorecard.meets_conservation_target && (
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-200/80 text-emerald-900 font-bold text-2xs border border-emerald-300">
                    Target Met (≥15% Conservation)
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3.5 rounded-lg bg-white/80 border border-emerald-100">
                  <span className="text-2xs text-slate-500 font-semibold uppercase block mb-1">
                    Baseline Requirement
                  </span>
                  <div className="text-lg font-bold text-slate-700">
                    {scorecard.baseline_total_depth_mm.toFixed(1)} mm
                  </div>
                  <span className="text-2xs text-slate-400">
                    {scorecard.baseline_volume_litres.toLocaleString()} Litres (Conventional Flood)
                  </span>
                </div>

                <div className="p-3.5 rounded-lg bg-white/80 border border-emerald-100">
                  <span className="text-2xs text-slate-500 font-semibold uppercase block mb-1">
                    AGRI-2 Recommended
                  </span>
                  <div className="text-lg font-bold text-agri-950">
                    {scorecard.recommended_total_depth_mm.toFixed(1)} mm
                  </div>
                  <span className="text-2xs text-emerald-700 font-semibold">
                    {scorecard.recommended_volume_litres.toLocaleString()} Litres (Dynamic Balance)
                  </span>
                </div>

                <div className="p-3.5 rounded-lg bg-emerald-100/70 border border-emerald-200">
                  <span className="text-2xs text-emerald-900 font-semibold uppercase block mb-1">
                    Water Saved Depth
                  </span>
                  <div className="text-lg font-bold text-emerald-800">
                    {scorecard.water_saved_depth_mm.toFixed(1)} mm
                  </div>
                  <span className="text-2xs text-emerald-700">
                    {scorecard.water_saved_litres.toLocaleString()} Litres conserved
                  </span>
                </div>

                <div className="p-3.5 rounded-lg bg-emerald-100/70 border border-emerald-200">
                  <span className="text-2xs text-emerald-900 font-semibold uppercase block mb-1">
                    Savings Percentage
                  </span>
                  <div className="text-xl font-extrabold text-emerald-900">
                    {scorecard.water_savings_percent.toFixed(1)}%
                  </div>
                  <span className="text-2xs text-emerald-800">
                    Physical conservation verified
                  </span>
                </div>
              </div>

              <p className="text-2xs text-slate-500 mt-3 italic">
                Note: Benchmarked against conventional local continuous standing water practices. Baseline computed by Python FAO-56 hydrological engine.
              </p>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
              <Info className="w-4 h-4 text-slate-400" />
              <span>Comparative water-saving metrics withheld: awaiting standardized baseline confirmation from backend calculations.</span>
            </div>
          )}

          {/* 7-Day Irrigation Schedule Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-sm text-slate-900">
                  {isTelugu ? 'రోజువారీ నీటిపారుదల సిఫార్సుల పట్టిక' : 'Daily Irrigation Recommendation Matrix'}
                </h3>
                <p className="text-2xs text-slate-400 mt-0.5">
                  Detailed day-by-day irrigation trigger decisions, depth, volumetric conversion, and agronomic justification.
                </p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                Total: {schedule.water_reduction_scorecard.recommended_volume_litres.toLocaleString()} Litres
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <th className="py-3 px-3">Day</th>
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-3">ETc (mm)</th>
                    <th className="py-3 px-3">Eff. Rain (mm)</th>
                    <th className="py-3 px-3">Decision</th>
                    <th className="py-3 px-3">Depth (mm)</th>
                    <th className="py-3 px-3">Volume (Litres)</th>
                    <th className="py-3 px-4 min-w-[240px]">Reason & Agronomic Justification</th>
                    <th className="py-3 px-3">Stage Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {dailyItems.map((r, i) => {
                    const isIrrigate = r.decision === 'IRRIGATE';
                    return (
                      <tr
                        key={i}
                        className={`transition-colors ${
                          isIrrigate ? 'bg-emerald-50/40 hover:bg-emerald-50/70' : 'hover:bg-slate-50/70'
                        }`}
                      >
                        <td className="py-3 px-3 font-bold text-slate-900">Day {r.day_index}</td>
                        <td className="py-3 px-3 text-slate-600 font-mono">{r.date}</td>
                        <td className="py-3 px-3 text-slate-800">{r.etc_mm.toFixed(1)}</td>
                        <td className="py-3 px-3 text-cyan-700">
                          {r.effective_rainfall_mm > 0 ? `${r.effective_rainfall_mm.toFixed(1)}` : '-'}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-2xs font-extrabold uppercase tracking-wide border ${
                              isIrrigate
                                ? 'bg-emerald-600 text-white border-emerald-700 shadow-2xs'
                                : 'bg-slate-100 text-slate-600 border-slate-300'
                            }`}
                          >
                            {isIrrigate ? <Droplets className="w-3 h-3" /> : null}
                            <span>{r.decision}</span>
                          </span>
                        </td>
                        <td className="py-3 px-3 font-bold text-slate-900">
                          {r.irrigation_depth_mm > 0 ? `${r.irrigation_depth_mm.toFixed(1)} mm` : '-'}
                        </td>
                        <td className="py-3 px-3 font-bold text-agri-800">
                          {r.irrigation_volume_litres > 0
                            ? `${r.irrigation_volume_litres.toLocaleString()} L`
                            : '-'}
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-700 leading-relaxed">
                          {r.reason}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-sm text-2xs font-semibold ${
                              r.stage_sensitivity.includes('Critical')
                                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                : 'text-slate-500'
                            }`}
                          >
                            {r.stage_sensitivity}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-agri-50 flex items-center justify-center text-agri-600">
            <CalendarDays className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">No Schedule Calculated Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Navigate to the Farmer Dashboard to select your field parameters and compute a 7-day schedule.
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
