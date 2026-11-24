'use client';

import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import {
  ScheduleHistorySummary,
  ApprovalHistoryItem
} from '../../services/types';
import {
  History,
  ShieldAlert,
  Calendar,
  Layers,
  User,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Loader2,
  AlertCircle,
  Database,
  Lock
} from 'lucide-react';

export default function HistoryScreen() {
  const { language } = useApp();
  const isTelugu = language === 'Telugu';

  const [activeTab, setActiveTab] = useState<'schedules' | 'approvals'>('schedules');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [schedules, setSchedules] = useState<ScheduleHistorySummary[]>([]);
  const [approvals, setApprovals] = useState<ApprovalHistoryItem[]>([]);
  const [schedStorageMode, setSchedStorageMode] = useState<string>('LOCAL_JSON_FALLBACK');
  const [apprStorageMode, setApprStorageMode] = useState<string>('LOCAL_JSON_FALLBACK');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 'schedules') {
        const res = await api.getScheduleHistory(25);
        setSchedules(res.schedules || []);
        setSchedStorageMode(res.storage_mode || 'LOCAL_JSON_FALLBACK');
      } else {
        const res = await api.getApprovalHistory(25);
        setApprovals(res.approvals || []);
        setApprStorageMode(res.storage_mode || 'LOCAL_JSON_FALLBACK');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve history logs';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab]);

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-800 text-xs font-semibold mb-1 border border-slate-300">
            <Lock className="w-3.5 h-3.5 text-slate-600" />
            <span>Development & Administrative Audit Mode</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTelugu ? 'ఆడిట్ మరియు చరిత్ర రికార్డులు' : 'Historical Audit & Provenance Records'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Persistent storage audit trail in Supabase PostgreSQL (with local file fallback).
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tab Switcher */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
            <button
              onClick={() => setActiveTab('schedules')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'schedules'
                  ? 'bg-white text-agri-900 shadow-2xs border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {isTelugu ? 'షెడ్యూల్స్ లాగ్' : 'Schedules Log'}
            </button>
            <button
              onClick={() => setActiveTab('approvals')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeTab === 'approvals'
                  ? 'bg-white text-agri-900 shadow-2xs border border-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {isTelugu ? 'ఆమోదాల లాగ్' : 'Approvals Log'}
            </button>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors shadow-2xs cursor-pointer"
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Mandatory Security Limitation Callout Banner */}
      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-bold">Administrative / Development Access Limitation</p>
          <p className="text-amber-800 leading-relaxed text-2xs">
            Farmer user authentication and multi-tenant row isolation are not yet fully implemented.
            This audit screen is restricted to development and agronomist verification only.
            Do not claim production multi-farmer data security until Supabase Auth JWT validation is integrated.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {/* Main Table Content */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-agri-600" />
            <h3 className="font-semibold text-sm text-slate-900">
              {activeTab === 'schedules' ? 'Calculated Schedules Repository' : 'Farmer Decision Audit Trail'}
            </h3>
          </div>
          <div className="flex items-center gap-2 text-2xs text-slate-500">
            <span className="font-medium">Storage Mode:</span>
            <span className="font-mono font-bold px-2 py-0.5 rounded-sm bg-slate-100 text-slate-700 border border-slate-200">
              {activeTab === 'schedules' ? schedStorageMode : apprStorageMode}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center space-y-3">
            <Loader2 className="w-6 h-6 animate-spin text-agri-600 mx-auto" />
            <p className="text-xs text-slate-500">Querying backend database logs...</p>
          </div>
        ) : activeTab === 'schedules' ? (
          /* Schedules Table */
          schedules.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Schedule ID</th>
                    <th className="py-2.5 px-3">Created At</th>
                    <th className="py-2.5 px-3">Crop & Stage</th>
                    <th className="py-2.5 px-3">Soil</th>
                    <th className="py-2.5 px-3">Area (Acres)</th>
                    <th className="py-2.5 px-3">Recommended Depth</th>
                    <th className="py-2.5 px-3">Recommended Volume</th>
                    <th className="py-2.5 px-3">Water Savings</th>
                    <th className="py-2.5 px-3">Provenance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {schedules.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{s.id}</td>
                      <td className="py-2.5 px-3 text-slate-500">{s.created_at.slice(0, 16).replace('T', ' ')}</td>
                      <td className="py-2.5 px-3 text-slate-800 font-semibold">{s.crop} ({s.growth_stage})</td>
                      <td className="py-2.5 px-3 text-slate-600">{s.soil_type}</td>
                      <td className="py-2.5 px-3 text-slate-700">{s.field_area_acres}</td>
                      <td className="py-2.5 px-3 font-bold text-emerald-800">{s.recommended_total_depth_mm.toFixed(1)} mm</td>
                      <td className="py-2.5 px-3 font-bold text-slate-900">{s.recommended_volume_litres.toLocaleString()} L</td>
                      <td className="py-2.5 px-3 text-emerald-700 font-bold">{s.water_savings_percent.toFixed(1)}%</td>
                      <td className="py-2.5 px-3">
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded-sm bg-slate-100 text-slate-700 border border-slate-200">
                          {s.provenance_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">
              No schedules recorded in storage repository yet.
            </div>
          )
        ) : (
          /* Approvals Table */
          approvals.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Approval ID</th>
                    <th className="py-2.5 px-3">Schedule ID</th>
                    <th className="py-2.5 px-3">Recorded At</th>
                    <th className="py-2.5 px-3">Farmer</th>
                    <th className="py-2.5 px-3">Decision</th>
                    <th className="py-2.5 px-3">Crop & Area</th>
                    <th className="py-2.5 px-3">Approved Depth</th>
                    <th className="py-2.5 px-3">Approved Volume</th>
                    <th className="py-2.5 px-4 min-w-[180px]">Field Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {approvals.map((a) => {
                    const isApproved = a.decision === 'APPROVED';
                    return (
                      <tr key={a.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{a.id}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-600">{a.schedule_id}</td>
                        <td className="py-2.5 px-3 text-slate-500">{a.recorded_at.slice(0, 16).replace('T', ' ')}</td>
                        <td className="py-2.5 px-3 font-semibold text-slate-800">{a.farmer_name}</td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-bold ${
                              isApproved
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : 'bg-red-100 text-red-800 border border-red-300'
                            }`}
                          >
                            {isApproved ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <XCircle className="w-3 h-3 text-red-600" />}
                            <span>{a.decision}</span>
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-700">{a.crop} ({a.field_area_acres} Ac)</td>
                        <td className="py-2.5 px-3 font-bold text-emerald-800">{a.approved_depth_mm.toFixed(1)} mm</td>
                        <td className="py-2.5 px-3 font-bold text-slate-900">{a.approved_volume_litres.toLocaleString()} L</td>
                        <td className="py-2.5 px-4 text-slate-600 italic text-2xs">{a.field_notes || '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">
              No farmer approval records in audit trail yet.
            </div>
          )
        )}
      </div>
    </div>
  );
}
