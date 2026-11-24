'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import {
  Activity,
  Layers,
  Sprout,
  Droplet,
  CloudRain,
  ShieldAlert,
  TrendingUp,
  BarChart3,
  Loader2,
  AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  Area
} from 'recharts';

export default function AgriculturalAnalysis() {
  const {
    crop,
    growthStage,
    soilType,
    locationName,
    latitude,
    longitude,
    fieldAreaAcres,
    initialWaterDepthMm,
    weatherSource,
    schedule,
    setSchedule,
    language
  } = useApp();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isTelugu = language === 'Telugu';

  const handleCompute = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.calculateSchedule({
        crop,
        growth_stage: growthStage,
        soil_type: soilType,
        location: locationName,
        latitude,
        longitude,
        field_area_acres: fieldAreaAcres,
        initial_water_depth_mm: crop === 'Rice' ? initialWaterDepthMm : undefined,
        initial_depletion_mm: crop !== 'Rice' ? initialWaterDepthMm : undefined,
        weather_source: weatherSource,
      });
      setSchedule(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Calculation failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const dailyItems = schedule?.daily_schedule || [];

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-semibold mb-1 border border-emerald-200">
            <Activity className="w-3.5 h-3.5 text-emerald-600" />
            <span>FAO-56 Dual Hydrological Water Balance</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTelugu ? 'వ్యవసాయ మరియు హైడ్రోలాజికల్ విశ్లేషణ' : 'Agricultural Hydrological Analysis'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Single computational source of truth in Python: Penman-Monteith reference evapotranspiration, Kc crop coefficients, and daily soil-water equilibrium.
          </p>
        </div>

        {!schedule && (
          <button
            onClick={handleCompute}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs shadow-xs transition-colors cursor-pointer"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            <span>Calculate Analysis</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {schedule ? (
        <div className="space-y-6">
          {/* Hydrological Parameter Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Ref. Evapotranspiration (ET₀)
              </span>
              <div className="text-xl font-bold text-slate-900">
                {schedule.totals.total_eto_mm.toFixed(1)} <span className="text-xs font-normal text-slate-500">mm / 7d</span>
              </div>
              <p className="text-2xs text-slate-400 mt-1">
                Avg: {(schedule.totals.total_eto_mm / 7).toFixed(1)} mm/day
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Crop Coefficient (Kc)
              </span>
              <div className="text-xl font-bold text-emerald-700">
                {dailyItems[0]?.kc.toFixed(2) || '1.15'}
              </div>
              <p className="text-2xs text-slate-400 mt-1">
                {schedule.crop} – {schedule.growth_stage} stage
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Crop Water Need (ETc)
              </span>
              <div className="text-xl font-bold text-slate-900">
                {schedule.totals.total_etc_mm.toFixed(1)} <span className="text-xs font-normal text-slate-500">mm / 7d</span>
              </div>
              <p className="text-2xs text-slate-400 mt-1">
                ETc = Kc × ET₀ physical uptake
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500 block mb-1">
                Effective Rainfall (Peff)
              </span>
              <div className="text-xl font-bold text-cyan-700">
                {schedule.totals.total_effective_rainfall_mm.toFixed(1)} <span className="text-xs font-normal text-slate-500">mm</span>
              </div>
              <p className="text-2xs text-slate-400 mt-1">
                Bund retention efficiency: {schedule.crop === 'Rice' ? '80%' : 'USDA-SCS'}
              </p>
            </div>
          </div>

          {/* Recharts Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart 1: Daily ETc vs Effective Rainfall vs Irrigation */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Hydrological Flux: ETc vs Effective Rain vs Irrigation (mm)
                  </h3>
                  <p className="text-2xs text-slate-400 mt-0.5">
                    Evaluates rainfall buffering before triggering irrigation
                  </p>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={dailyItems} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(d) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Line type="monotone" dataKey="etc_mm" name="Crop ET (ETc)" stroke="#e11d48" strokeWidth={2.5} dot={{ r: 3 }} />
                    <Bar dataKey="effective_rainfall_mm" name="Effective Rain (Peff)" fill="#06b6d4" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="irrigation_depth_mm" name="Irrigation Given (mm)" fill="#16a34a" radius={[3, 3, 0, 0]} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Soil Water Balance Progression */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    {schedule.crop === 'Rice'
                      ? 'Paddy Water Depth Progression (mm)'
                      : 'Root-Zone Depletion vs MAD Threshold (mm)'}
                  </h3>
                  <p className="text-2xs text-slate-400 mt-0.5">
                    {schedule.crop === 'Rice'
                      ? 'Target band: 25 mm - 50 mm bund retention'
                      : 'Management Allowed Depletion (MAD) threshold'}
                  </p>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={dailyItems} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(d) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    {schedule.crop === 'Rice' ? (
                      <>
                        <ReferenceLine y={25} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Lower Trigger (25mm)', fill: '#b45309', fontSize: 10 }} />
                        <ReferenceLine y={50} stroke="#10b981" strokeDasharray="3 3" label={{ value: 'Target Max (50mm)', fill: '#047857', fontSize: 10 }} />
                        <Line type="monotone" dataKey="water_depth_before_mm" name="Depth Before Irrigation" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                        <Area type="monotone" dataKey="water_depth_after_mm" name="Depth After Irrigation" stroke="#16a34a" fill="#dcfce7" fillOpacity={0.4} />
                      </>
                    ) : (
                      <>
                        <Line type="monotone" dataKey="depletion_before_mm" name="Depletion Before" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
                        <Area type="monotone" dataKey="depletion_after_mm" name="Depletion After" stroke="#10b981" fill="#ecfdf5" fillOpacity={0.4} />
                      </>
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Detailed Daily Water Balance Accounting Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-sm text-slate-900">
                Daily Soil-Water Balance Accounting (FAO-56 Tabulation)
              </h3>
              <span className="text-2xs text-slate-500 font-medium">
                Crop: {schedule.crop} | Soil: {schedule.soil_type}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Day</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">ET₀ (mm)</th>
                    <th className="py-2.5 px-3">Kc</th>
                    <th className="py-2.5 px-3">ETc (mm)</th>
                    <th className="py-2.5 px-3">Rainfall</th>
                    <th className="py-2.5 px-3">Eff. Rain</th>
                    <th className="py-2.5 px-3">{schedule.crop === 'Rice' ? 'Depth Before' : 'Depletion Before'}</th>
                    <th className="py-2.5 px-3">{schedule.crop === 'Rice' ? 'Depth After' : 'Depletion After'}</th>
                    <th className="py-2.5 px-3">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {dailyItems.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-slate-900">Day {r.day_index}</td>
                      <td className="py-2.5 px-3 text-slate-600">{r.date}</td>
                      <td className="py-2.5 px-3 text-slate-700">{r.eto_mm.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-emerald-700 font-bold">{r.kc.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-slate-800">{r.etc_mm.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-slate-600">{r.rainfall_mm.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-cyan-700">{r.effective_rainfall_mm.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-slate-700">
                        {schedule.crop === 'Rice'
                          ? `${r.water_depth_before_mm?.toFixed(1) || 0} mm`
                          : `${r.depletion_before_mm?.toFixed(1) || 0} mm`}
                      </td>
                      <td className="py-2.5 px-3 text-slate-700">
                        {schedule.crop === 'Rice'
                          ? `${r.water_depth_after_mm?.toFixed(1) || 0} mm`
                          : `${r.depletion_after_mm?.toFixed(1) || 0} mm`}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-2xs font-bold ${
                            r.decision === 'IRRIGATE'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {r.decision}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">No Hydrological Run Loaded</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              Click &apos;Calculate Analysis&apos; to run the FAO-56 hydrological water balance engine on current farm parameters.
            </p>
          </div>
          <button
            onClick={handleCompute}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs cursor-pointer shadow-xs transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            <span>Run FAO-56 Analysis</span>
          </button>
        </div>
      )}
    </div>
  );
}
