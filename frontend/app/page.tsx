'use client';

import React from 'react';
import Navbar from '../components/Navbar';
import { useApp } from '../context/AppContext';
import FarmerDashboard from '../components/screens/FarmerDashboard';
import WeatherDashboard from '../components/screens/WeatherDashboard';
import AgriculturalAnalysis from '../components/screens/AgriculturalAnalysis';
import IrrigationSchedule from '../components/screens/IrrigationSchedule';
import AiAdvisoryApproval from '../components/screens/AiAdvisoryApproval';
import HistoryScreen from '../components/screens/HistoryScreen';
import { ShieldCheck, Droplet, ExternalLink } from 'lucide-react';

export default function Home() {
  const { activeScreen } = useApp();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-8">
        {activeScreen === 'dashboard' && <FarmerDashboard />}
        {activeScreen === 'weather' && <WeatherDashboard />}
        {activeScreen === 'analysis' && <AgriculturalAnalysis />}
        {activeScreen === 'schedule' && <IrrigationSchedule />}
        {activeScreen === 'advisory' && <AiAdvisoryApproval />}
        {activeScreen === 'history' && <HistoryScreen />}
      </main>

      {/* Standardized Agricultural Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800">AGRI-2</span>
            <span>•</span>
            <span>FAO-56 Penman-Monteith Hydrology Engine</span>
            <span>•</span>
            <span>Company Nexus AI (gpt-5-nano)</span>
          </div>

          <div className="flex items-center gap-4 text-2xs">
            <span className="flex items-center gap-1 text-emerald-800 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Strict Manual Operation Policy</span>
            </span>
            <span>•</span>
            <span className="text-slate-400">Coimbatore Agricultural Division</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
