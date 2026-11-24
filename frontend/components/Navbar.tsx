'use client';

import React, { useState } from 'react';
import { useApp, ScreenType } from '../context/AppContext';
import {
  LayoutDashboard,
  CloudSun,
  Activity,
  CalendarDays,
  Sparkles,
  History,
  Menu,
  X,
  Droplets,
  Languages,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

const NAV_ITEMS: { id: ScreenType; label: string; teluguLabel: string; icon: React.ElementType }[] = [
  { id: 'dashboard', label: 'Dashboard', teluguLabel: 'డాష్‌బోర్డ్', icon: LayoutDashboard },
  { id: 'weather', label: 'Weather', teluguLabel: 'వాతావరణం', icon: CloudSun },
  { id: 'analysis', label: 'Analysis', teluguLabel: 'విశ్లేషణ', icon: Activity },
  { id: 'schedule', label: 'Schedule', teluguLabel: 'షెడ్యూల్', icon: CalendarDays },
  { id: 'advisory', label: 'AI Advisory', teluguLabel: 'AI సలహాదారు', icon: Sparkles },
  { id: 'history', label: 'History', teluguLabel: 'చరిత్ర', icon: History },
];

export default function Navbar() {
  const {
    activeScreen,
    setActiveScreen,
    language,
    setLanguage,
    schedule,
    health,
  } = useApp();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-agri-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & App Title */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveScreen('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-agri-700 to-agri-500 flex items-center justify-center text-white shadow-md shadow-agri-600/20">
              <Droplets className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-agri-950 tracking-tight">AGRI-2</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-agri-100 text-agri-800 border border-agri-200">
                  FAO-56 PM
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                {language === 'Telugu' ? 'నీటిపారుదల సలహాదారు' : 'Irrigation Scheduling Advisor'}
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveScreen(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-agri-600 text-white shadow-sm shadow-agri-600/30'
                      : 'text-slate-640 hover:text-agri-800 hover:bg-agri-50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                  <span>{language === 'Telugu' ? item.teluguLabel : item.label}</span>
                  {item.id === 'schedule' && schedule && (
                    <span className="w-2 h-2 rounded-full bg-emerald-300 animate-pulse" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Header Badges: Language Toggle & Status */}
          <div className="hidden sm:flex items-center gap-3">
            {/* Language Switcher */}
            <button
              onClick={() => setLanguage(language === 'English' ? 'Telugu' : 'English')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
              title="Toggle English / Telugu"
            >
              <Languages className="w-3.5 h-3.5 text-agri-600" />
              <span>{language === 'English' ? 'తెలుగు' : 'English'}</span>
            </button>

            {/* Health / Backend Status Pill */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                health
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
              title={health ? `API Online (${health.version})` : 'Connecting to API'}
            >
              {health ? (
                <>
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>API Online</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  <span>Offline Staging</span>
                </>
              )}
            </div>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => setLanguage(language === 'English' ? 'Telugu' : 'English')}
              className="p-1.5 rounded-lg border border-slate-200 text-xs text-slate-700"
            >
              {language === 'English' ? 'తె' : 'EN'}
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:text-agri-700 hover:bg-slate-100"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-100 bg-white px-4 pt-2 pb-4 space-y-1 shadow-lg">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveScreen(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-agri-600 text-white'
                    : 'text-slate-700 hover:bg-agri-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5" />
                  <span>{language === 'Telugu' ? item.teluguLabel : item.label}</span>
                </div>
                {item.id === 'schedule' && schedule && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                    Active
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </header>
  );
}
