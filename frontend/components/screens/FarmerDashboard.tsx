'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import {
  Sprout,
  MapPin,
  Layers,
  Ruler,
  Droplet,
  CloudLightning,
  Sparkles,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  TrendingDown,
  Info
} from 'lucide-react';

const CROPS = [
  { id: 'Rice', name: 'Rice (Paddy)', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 25.0 },
  { id: 'Maize', name: 'Maize (Corn)', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 0.0 },
  { id: 'Wheat', name: 'Wheat', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 0.0 },
  { id: 'Tomato', name: 'Tomato', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 0.0 },
  { id: 'Cotton', name: 'Cotton', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 0.0 },
  { id: 'Sugarcane', name: 'Sugarcane', stages: ['Initial', 'Development', 'Mid-Season', 'Late-Season'], defaultDepth: 0.0 },
];

const SOILS = ['Loamy', 'Clay', 'Clay Loam', 'Sandy Loam', 'Sandy'];

const WEATHER_SOURCES = [
  { id: 'sample_coimbatore_7day', label: 'Coimbatore Kharif Normal (7-Day Default)', type: 'SIMULATION' },
  { id: 'live_openmeteo', label: 'Open-Meteo Live 7-Day Forecast (NWP API)', type: 'LIVE' },
  { id: 'sample_dry_spell', label: 'Coimbatore Dry Spell Stress Test (7-Day)', type: 'SIMULATION' },
  { id: 'sample_heavy_rain', label: 'Coimbatore Heavy Monsoon Scenario (7-Day)', type: 'SIMULATION' },
  { id: 'sample_historical_30day', label: 'Coimbatore Historical Observations (30-Day)', type: 'SIMULATION' },
];

export default function FarmerDashboard() {
  const {
    crop,
    setCrop,
    growthStage,
    setGrowthStage,
    soilType,
    setSoilType,
    locationName,
    setLocationName,
    latitude,
    setLatitude,
    longitude,
    setLongitude,
    fieldAreaAcres,
    setFieldAreaAcres,
    initialWaterDepthMm,
    setInitialWaterDepthMm,
    weatherSource,
    setWeatherSource,
    schedule,
    setSchedule,
    setActiveScreen,
    language
  } = useApp();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCropObj = CROPS.find((c) => c.id === crop) || CROPS[0];

  const handleCropChange = (newCrop: string) => {
    setCrop(newCrop);
    const cropObj = CROPS.find((c) => c.id === newCrop) || CROPS[0];
    if (!cropObj.stages.includes(growthStage)) {
      setGrowthStage(cropObj.stages[1] || cropObj.stages[0]);
    }
    if (newCrop === 'Rice') {
      setInitialWaterDepthMm(25.0);
    } else {
      setInitialWaterDepthMm(0.0);
    }
  };

  const handleGenerateSchedule = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.calculateSchedule({
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

      setSchedule(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to calculate schedule.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const isTelugu = language === 'Telugu';

  return (
    <div className={`space-y-6 ${isTelugu ? 'font-telugu' : ''}`}>
      {/* Screen Title & Welcome */}
      <div className="bg-gradient-to-r from-agri-800 via-agri-700 to-emerald-700 rounded-2xl p-6 md:p-8 text-white shadow-md relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm text-xs font-medium text-emerald-100 mb-3 border border-white/20">
            <Sprout className="w-3.5 h-3.5 text-emerald-300" />
            <span>{isTelugu ? 'ఖచ్చితమైన నీటిపారుదల వ్యవస్థ' : 'Precision Hydrological Decision Support'}</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-2">
            {isTelugu ? 'రైతు నిర్వహణ డాష్‌బోర్డ్' : 'Farmer Advisory & Field Setup'}
          </h1>
          <p className="text-emerald-100/90 text-sm md:text-base leading-relaxed">
            {isTelugu
              ? 'FAO-56 పెన్మాన్-మాంటీత్ భౌతిక సూత్రాల ఆధారంగా నిజమైన వాతావరణం మరియు నేల డేటాతో 7 రోజుల ఖచ్చితమైన నీటి షెడ్యూల్‌ను రూపొందించండి.'
              : 'Configure your crop, soil profile, and farm location to calculate a 7-day water-conserving irrigation schedule adhering strictly to FAO-56 Penman-Monteith physics.'}
          </p>
        </div>

        {/* Decorative Water Ripple Circles */}
        <div className="absolute -right-12 -bottom-16 w-64 h-64 rounded-full bg-white/5 pointer-events-none" />
        <div className="absolute right-24 -top-8 w-48 h-48 rounded-full bg-white/5 pointer-events-none" />
      </div>

      {/* Main Grid: Form Inputs and Summary Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Farm Parameters Configuration Form */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-agri-600" />
              <span>{isTelugu ? 'పొలం మరియు పంట పారామితులు' : 'Farm Profile & Meteorological Inputs'}</span>
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              {isTelugu ? 'డిఫాల్ట్ ప్రదర్శన విలువలు: వరి, కోయంబత్తూరు, 1 ఎకరం, లోమీ నేల' : 'Demonstration defaults: Rice, Coimbatore, 1.0 Acre, Loamy Soil'}
            </p>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* 1. Crop Selection */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'పంట ఎంపిక' : 'Crop'}
              </label>
              <div className="relative">
                <select
                  value={crop}
                  onChange={(e) => handleCropChange(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
                >
                  {CROPS.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 2. Growth Stage */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'పంట పెరుగుదల దశ' : 'Growth Stage'}
              </label>
              <select
                value={growthStage}
                onChange={(e) => setGrowthStage(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
              >
                {selectedCropObj.stages.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage} {stage === 'Mid-Season' ? '(Critical Reproductive Stage)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* 3. Soil Type */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'నేల రకం' : 'Soil Texture'}
              </label>
              <select
                value={soilType}
                onChange={(e) => setSoilType(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
              >
                {SOILS.map((s) => (
                  <option key={s} value={s}>
                    {s} {s === 'Loamy' ? '(Balanced retention & drainage)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* 4. Field Area */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'పొలం వైశాల్యం (ఎకరాలు)' : 'Field Area (Acres)'}
              </label>
              <div className="relative">
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="100.0"
                  value={fieldAreaAcres}
                  onChange={(e) => setFieldAreaAcres(Math.max(0.1, parseFloat(e.target.value) || 1.0))}
                  className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
                />
                <span className="absolute right-3.5 top-2.5 text-xs text-slate-400 font-semibold uppercase">
                  Acre
                </span>
              </div>
            </div>

            {/* 5. Location Name */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'ప్రాంతం పేరు' : 'Location Name'}
              </label>
              <div className="relative">
                <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={locationName}
                  onChange={(e) => setLocationName(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 pl-9 pr-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
                />
              </div>
            </div>

            {/* 6. Coordinates (Lat, Lon) */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Lat (°N)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value) || 11.0168)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Lon (°E)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value) || 76.9558)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
                />
              </div>
            </div>

            {/* 7. Initial Standing Water Depth (for Paddy) / Depletion */}
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {crop === 'Rice'
                  ? (isTelugu ? 'వరి ప్రారంభ నీటి మట్టం (మి.మీ.)' : 'Initial Standing Water Depth in Paddy Field (mm)')
                  : (isTelugu ? 'రూట్ జోన్ ప్రారంభ క్షీణత (మి.మీ.)' : 'Initial Root-Zone Depletion (mm)')}
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0"
                  max="60"
                  step="5"
                  value={initialWaterDepthMm}
                  onChange={(e) => setInitialWaterDepthMm(parseFloat(e.target.value))}
                  className="flex-1 accent-agri-600 h-2 bg-slate-200 rounded-lg cursor-pointer"
                />
                <span className="w-16 text-center text-sm font-bold bg-slate-100 py-1.5 rounded-md border border-slate-200 text-slate-800">
                  {initialWaterDepthMm} mm
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {crop === 'Rice'
                  ? 'Recommended depth range for Coimbatore lowland rice: 25 - 50 mm'
                  : 'Root zone depletion value in mm before scheduling'}
              </p>
            </div>

            {/* 8. Weather Data Source */}
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                {isTelugu ? 'వాతావరణ డేటా మూలం' : 'Weather Data Source'}
              </label>
              <select
                value={weatherSource}
                onChange={(e) => setWeatherSource(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 focus:border-agri-600 focus:ring-2 focus:ring-agri-500/20 focus:outline-hidden"
              >
                {WEATHER_SOURCES.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.type === 'LIVE' ? '🟢 ' : '🟡 '}
                    {w.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-slate-400" />
                <span>
                  {weatherSource === 'live_openmeteo'
                    ? 'Queries live 7-day numerical weather prediction via Open-Meteo.'
                    : 'Uses genuine standardized historical observations for calibrated simulation testing.'}
                </span>
              </p>
            </div>
          </div>

          {/* Error Message Banner */}
          {error && (
            <div className="p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3 text-red-800 text-sm">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Calculation Error</p>
                <p className="text-xs mt-0.5 text-red-700">{error}</p>
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="pt-2">
            <button
              onClick={handleGenerateSchedule}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-agri-600 hover:bg-agri-700 active:bg-agri-800 text-white font-semibold text-sm shadow-md shadow-agri-600/30 transition-all disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{isTelugu ? 'లెక్కించబడుతోంది...' : 'Executing FAO-56 Engine...'}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 text-emerald-200" />
                  <span>{isTelugu ? '7 రోజుల నీటిపారుదల షెడ్యూల్ రూపొందించండి' : 'Calculate 7-Day Irrigation Schedule'}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Active Schedule Summary or Demo Info Card */}
        <div className="lg:col-span-4 space-y-6">
          {schedule ? (
            /* Active Schedule Result Card */
            <div className="bg-white rounded-xl border border-emerald-200 p-6 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span className="font-semibold text-slate-900 text-sm">
                    {isTelugu ? 'షెడ్యూల్ సిద్ధంగా ఉంది' : 'Schedule Generated'}
                  </span>
                </div>
                <span className="text-2xs font-mono px-2 py-0.5 rounded-sm bg-slate-100 text-slate-600 border border-slate-200">
                  {schedule.schedule_id}
                </span>
              </div>

              {/* Water Savings Highlight */}
              <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-agri-100/60 border border-emerald-200 p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-agri-800 uppercase tracking-wide">
                    {isTelugu ? 'నీటి ఆదా శాతం' : 'Water Savings'}
                  </span>
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-700">
                    <TrendingDown className="w-3.5 h-3.5" />
                    {schedule.water_reduction_scorecard.water_savings_percent.toFixed(1)}%
                  </span>
                </div>
                <div className="text-2xl font-bold text-agri-950">
                  {schedule.water_reduction_scorecard.water_saved_litres.toLocaleString()} L
                </div>
                <p className="text-xs text-agri-700 mt-1">
                  Saved vs conventional continuous flooding baseline ({schedule.water_reduction_scorecard.water_saved_depth_mm.toFixed(1)} mm depth)
                </p>
              </div>

              {/* Key Quantitative Metrics */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-500 block mb-0.5">Recommended Depth</span>
                  <span className="text-base font-bold text-slate-800">
                    {schedule.water_reduction_scorecard.recommended_total_depth_mm.toFixed(1)} mm
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-500 block mb-0.5">Total Volume</span>
                  <span className="text-base font-bold text-slate-800">
                    {schedule.water_reduction_scorecard.recommended_volume_litres.toLocaleString()} L
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-500 block mb-0.5">Crop ET (ETc)</span>
                  <span className="text-base font-bold text-slate-800">
                    {schedule.totals.total_etc_mm.toFixed(1)} mm
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                  <span className="text-slate-500 block mb-0.5">Eff. Rainfall</span>
                  <span className="text-base font-bold text-slate-800">
                    {schedule.totals.total_effective_rainfall_mm.toFixed(1)} mm
                  </span>
                </div>
              </div>

              {/* Quick Navigation Action Links */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => setActiveScreen('schedule')}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-agri-50 hover:bg-agri-100 text-agri-800 text-xs font-semibold transition-colors"
                >
                  <span>{isTelugu ? 'పూర్తి 7-రోజుల షెడ్యూల్ చూడండి' : 'View Full 7-Day Table'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setActiveScreen('analysis')}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors"
                >
                  <span>{isTelugu ? 'హైడ్రోలాజికల్ విశ్లేషణ చార్ట్‌లు' : 'Hydrological Balance Charts'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setActiveScreen('advisory')}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors"
                >
                  <span>{isTelugu ? 'AI సలహా & ఆమోదం' : 'Nexus AI Advisory & Approval'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            /* Default Demo Parameters Explanation Card */
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
              <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-agri-600" />
                <span>{isTelugu ? 'ప్రామాణిక నమూనా వివరణ' : 'Standard Baseline Configuration'}</span>
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isTelugu
                  ? 'ఈ వ్యవసాయ నమూనా కోయంబత్తూరు (తమిళనాడు) యొక్క ఖరీఫ్ సీజన్ వరి సాగు పద్ధతులకు అనుగుణంగా రూపొందించబడింది. స్థానిక TNAU మార్గదర్శకాల ప్రకారం నీటి పారుదల లెక్కింపు జరుగుతుంది.'
                  : 'Configured for Coimbatore, Tamil Nadu agro-climatic conditions. Compares automated daily water depletion against TNAU wetland paddy water management guidelines.'}
              </p>

              <div className="p-3.5 rounded-lg bg-agri-50/70 border border-agri-200/60 text-xs text-agri-900 space-y-1.5">
                <div className="font-semibold text-agri-950 flex items-center gap-1.5">
                  <Droplet className="w-3.5 h-3.5 text-agri-700" />
                  <span>Manual Safety Policy</span>
                </div>
                <p className="text-agri-800 text-2xs leading-normal">
                  All recommendations provide advisory depth for manual valve/pump operation. No automatic valve triggers or telemetry actuators are ever initiated.
                </p>
              </div>

              <div className="border-t border-slate-100 pt-3 text-xs text-slate-500">
                <span className="font-medium text-slate-700">Quick Start:</span> Click{' '}
                <span className="font-semibold text-agri-700">&apos;Calculate 7-Day Irrigation Schedule&apos;</span> to evaluate the current profile.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
