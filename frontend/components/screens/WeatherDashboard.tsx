'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import {
  WeatherForecastResponse,
  WeatherHistoricalResponse,
  DailyWeatherRecord
} from '../../services/types';
import {
  CloudSun,
  Radio,
  History,
  Calendar,
  Thermometer,
  Droplets,
  Wind,
  Sun,
  CloudRain,
  Loader2,
  AlertCircle,
  Clock,
  ShieldCheck,
  MapPin
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
  Area
} from 'recharts';

export default function WeatherDashboard() {
  const {
    latitude,
    longitude,
    locationName,
    weatherForecast,
    setWeatherForecast,
    weatherHistorical,
    setWeatherHistorical,
    language
  } = useApp();

  const [activeTab, setActiveTab] = useState<'live' | 'historical'>('live');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Historical date range state
  const [histStart, setHistStart] = useState('2026-10-01');
  const [histEnd, setHistEnd] = useState('2026-10-07');

  const isTelugu = language === 'Telugu';

  // Fetch Open-Meteo live forecast
  const handleFetchForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWeatherForecast(latitude, longitude);
      setWeatherForecast(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch Open-Meteo live forecast.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Fetch NASA POWER historical weather
  const handleFetchHistorical = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWeatherHistorical(latitude, longitude, histStart, histEnd);
      setWeatherHistorical(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve NASA POWER historical data.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const activeRecords: DailyWeatherRecord[] =
    activeTab === 'live'
      ? weatherForecast?.daily_records || []
      : weatherHistorical?.daily_records || [];

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-100 text-sky-800 text-xs font-semibold mb-1 border border-sky-200">
            <CloudSun className="w-3.5 h-3.5 text-sky-600" />
            <span>Meteorological Ingestion</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {isTelugu ? 'వాతావరణ పర్యవేక్షణ డాష్‌బోర్డ్' : 'Weather Dashboard'}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <span>{locationName} ({latitude.toFixed(4)}°N, {longitude.toFixed(4)}°E)</span>
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => { setActiveTab('live'); setError(null); }}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'live'
                ? 'bg-white text-agri-900 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Radio className="w-3.5 h-3.5 text-emerald-600" />
            <span>{isTelugu ? 'ప్రత్యక్ష సూచన (Open-Meteo)' : 'Live 7-Day Forecast'}</span>
          </button>
          <button
            onClick={() => { setActiveTab('historical'); setError(null); }}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'historical'
                ? 'bg-white text-agri-900 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <History className="w-3.5 h-3.5 text-sky-600" />
            <span>{isTelugu ? 'చారిత్రక డేటా (NASA POWER)' : 'NASA POWER Historical'}</span>
          </button>
        </div>
      </div>

      {/* Control Bar & Provenance Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {activeTab === 'live' ? (
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold border border-emerald-300 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                LIVE FORECAST
              </span>
              <span className="text-xs text-slate-500">
                Source: <strong className="text-slate-800">Open-Meteo Weather API (ECMWF/GFS)</strong>
              </span>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <span className="px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-xs font-bold border border-sky-300">
                HISTORICAL REANALYSIS
              </span>
              <div className="flex items-center gap-2 text-xs">
                <label className="text-slate-600 font-medium">Start:</label>
                <input
                  type="date"
                  value={histStart}
                  onChange={(e) => setHistStart(e.target.value)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                />
                <label className="text-slate-600 font-medium">End:</label>
                <input
                  type="date"
                  value={histEnd}
                  onChange={(e) => setHistEnd(e.target.value)}
                  className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                />
              </div>
            </div>
          )}

          {/* Fetch Buttons */}
          <div>
            {activeTab === 'live' ? (
              <button
                onClick={handleFetchForecast}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs shadow-xs transition-colors cursor-pointer disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
                <span>{isTelugu ? 'ప్రత్యక్ష వాతావరణాన్ని పొందండి' : 'Fetch Open-Meteo Forecast'}</span>
              </button>
            ) : (
              <button
                onClick={handleFetchHistorical}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-700 hover:bg-sky-800 text-white font-medium text-xs shadow-xs transition-colors cursor-pointer disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4" />}
                <span>{isTelugu ? 'NASA POWER పరిశీలనలను పొందండి' : 'Fetch NASA POWER Observations'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Provenance Metadata & Strict Disclaimers */}
        <div className="border-t border-slate-100 pt-3 flex flex-col md:flex-row md:items-center justify-between text-2xs text-slate-500 gap-2">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Retrieved:{' '}
                {activeTab === 'live'
                  ? weatherForecast?.retrieval_timestamp || 'Not fetched yet'
                  : weatherHistorical?.retrieval_timestamp || 'Not fetched yet'}
              </span>
            </span>
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Verified Numerical Ingestion</span>
            </span>
          </div>

          <p className="text-slate-500 italic">
            {activeTab === 'live'
              ? 'Never label synthetic simulation data as genuine weather. Live forecast ingested via Open-Meteo.'
              : 'NASA POWER data reflects satellite-derived agroclimatological reanalysis, not direct localized station sensors.'}
          </p>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Weather Service Response Error</p>
            <p className="text-red-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Main Meteorological Content */}
      {activeRecords.length > 0 ? (
        <div className="space-y-6">
          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Avg Temp</span>
                <Thermometer className="w-4 h-4 text-amber-500" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {(
                  activeRecords.reduce((acc, r) => acc + r.temp_mean, 0) / activeRecords.length
                ).toFixed(1)}
                °C
              </div>
              <span className="text-2xs text-slate-400">Mean 7-day temp</span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Peak Temp</span>
                <Thermometer className="w-4 h-4 text-red-500" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {Math.max(...activeRecords.map((r) => r.temp_max)).toFixed(1)}°C
              </div>
              <span className="text-2xs text-slate-400">Max day temperature</span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Mean Humidity</span>
                <Droplets className="w-4 h-4 text-blue-500" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {(
                  activeRecords.reduce((acc, r) => acc + r.humidity_mean, 0) / activeRecords.length
                ).toFixed(0)}
                %
              </div>
              <span className="text-2xs text-slate-400">Relative humidity</span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Total Rain</span>
                <CloudRain className="w-4 h-4 text-cyan-600" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {activeRecords.reduce((acc, r) => acc + r.rainfall, 0).toFixed(1)} mm
              </div>
              <span className="text-2xs text-slate-400">Cumulative precipitation</span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Solar Rad</span>
                <Sun className="w-4 h-4 text-orange-500" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {(
                  activeRecords.reduce((acc, r) => acc + r.solar_radiation, 0) / activeRecords.length
                ).toFixed(1)}
              </div>
              <span className="text-2xs text-slate-400">MJ/m²/day</span>
            </div>

            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-2xs font-semibold uppercase">Wind (2m)</span>
                <Wind className="w-4 h-4 text-teal-600" />
              </div>
              <div className="text-lg font-bold text-slate-900">
                {(
                  activeRecords.reduce((acc, r) => acc + r.wind_speed_2m, 0) / activeRecords.length
                ).toFixed(1)}{' '}
                m/s
              </div>
              <span className="text-2xs text-slate-400">Standardized anemometer</span>
            </div>
          </div>

          {/* Weather Charts (Recharts) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart 1: Temperature Envelope */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center justify-between">
                <span>Daily Temperature Profile (°C)</span>
                <span className="text-2xs text-slate-400 font-normal">Max, Min & Mean</span>
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={activeRecords} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(d) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} domain={['dataMin - 2', 'dataMax + 2']} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Area type="monotone" dataKey="temp_max" name="Max Temp" stroke="#ef4444" fill="#fee2e2" fillOpacity={0.4} />
                    <Line type="monotone" dataKey="temp_mean" name="Mean Temp" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="temp_min" name="Min Temp" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2: Rainfall & Solar Radiation */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center justify-between">
                <span>Precipitation (mm) & Solar Radiation (MJ/m²/d)</span>
                <span className="text-2xs text-slate-400 font-normal">Dual-Axis Agroclimatology</span>
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={activeRecords} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(d) => d.slice(5)} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Bar yAxisId="left" dataKey="rainfall" name="Rainfall (mm)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                    <Line yAxisId="right" type="monotone" dataKey="solar_radiation" name="Solar Radiation" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Daily Records Data Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-sm text-slate-900">
                Detailed 7-Day Meteorological Records
              </h3>
              <span className="text-xs text-slate-400">
                {activeRecords.length} Daily Observations
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Tmax (°C)</th>
                    <th className="py-2.5 px-3">Tmin (°C)</th>
                    <th className="py-2.5 px-3">Tmean (°C)</th>
                    <th className="py-2.5 px-3">RH Mean (%)</th>
                    <th className="py-2.5 px-3">Wind (m/s)</th>
                    <th className="py-2.5 px-3">Solar (MJ/m²)</th>
                    <th className="py-2.5 px-3">Precip (mm)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {activeRecords.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-slate-900">{r.date}</td>
                      <td className="py-2.5 px-3 text-red-600">{r.temp_max.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-blue-600">{r.temp_min.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-slate-700">{r.temp_mean.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-slate-700">{r.humidity_mean.toFixed(0)}%</td>
                      <td className="py-2.5 px-3 text-slate-700">{r.wind_speed_2m.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-orange-600">{r.solar_radiation.toFixed(1)}</td>
                      <td className="py-2.5 px-3 font-bold text-cyan-700">
                        {r.rainfall > 0 ? `${r.rainfall.toFixed(1)} mm` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Empty / Not Fetched State */
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <CloudSun className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">
              {activeTab === 'live' ? 'No Live Forecast Ingested' : 'No Historical Weather Ingested'}
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
              {activeTab === 'live'
                ? "Click 'Fetch Open-Meteo Forecast' to pull the genuine 7-day forecast for Coimbatore coordinates."
                : "Select a valid historical date range and click 'Fetch NASA POWER Observations' to pull gridded reanalysis."}
            </p>
          </div>
          <button
            onClick={activeTab === 'live' ? handleFetchForecast : handleFetchHistorical}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-agri-600 hover:bg-agri-700 text-white font-medium text-xs cursor-pointer shadow-xs transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            <span>Load Weather Data</span>
          </button>
        </div>
      )}
    </div>
  );
}
