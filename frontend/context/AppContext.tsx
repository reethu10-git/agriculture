'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  IrrigationScheduleResponse,
  WeatherForecastResponse,
  WeatherHistoricalResponse,
  HealthResponse
} from '../services/types';
import { api } from '../services/api';

export type ScreenType = 'dashboard' | 'weather' | 'analysis' | 'schedule' | 'advisory' | 'history';

interface AppContextType {
  activeScreen: ScreenType;
  setActiveScreen: (screen: ScreenType) => void;
  // Shared Farm Config
  crop: string;
  setCrop: (crop: string) => void;
  growthStage: string;
  setGrowthStage: (stage: string) => void;
  soilType: string;
  setSoilType: (soil: string) => void;
  locationName: string;
  setLocationName: (loc: string) => void;
  latitude: number;
  setLatitude: (lat: number) => void;
  longitude: number;
  setLongitude: (lon: number) => void;
  fieldAreaAcres: number;
  setFieldAreaAcres: (area: number) => void;
  initialWaterDepthMm: number;
  setInitialWaterDepthMm: (depth: number) => void;
  weatherSource: string;
  setWeatherSource: (src: string) => void;
  // Calculation / Advisory Results
  schedule: IrrigationScheduleResponse | null;
  setSchedule: (sched: IrrigationScheduleResponse | null) => void;
  weatherForecast: WeatherForecastResponse | null;
  setWeatherForecast: (wf: WeatherForecastResponse | null) => void;
  weatherHistorical: WeatherHistoricalResponse | null;
  setWeatherHistorical: (wh: WeatherHistoricalResponse | null) => void;
  // Language & Farmer Identity
  language: 'English' | 'Telugu';
  setLanguage: (lang: 'English' | 'Telugu') => void;
  farmerName: string;
  setFarmerName: (name: string) => void;
  // System Health
  health: HealthResponse | null;
  refreshHealth: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [activeScreen, setActiveScreen] = useState<ScreenType>('dashboard');

  // Default demonstration values: Crop: Rice, Location: Coimbatore, Soil: Loamy, Area: 1 acre
  const [crop, setCrop] = useState<string>('Rice');
  const [growthStage, setGrowthStage] = useState<string>('Development');
  const [soilType, setSoilType] = useState<string>('Loamy');
  const [locationName, setLocationName] = useState<string>('Coimbatore, Tamil Nadu');
  const [latitude, setLatitude] = useState<number>(11.0168);
  const [longitude, setLongitude] = useState<number>(76.9558);
  const [fieldAreaAcres, setFieldAreaAcres] = useState<number>(1.0);
  const [initialWaterDepthMm, setInitialWaterDepthMm] = useState<number>(25.0);
  const [weatherSource, setWeatherSource] = useState<string>('sample_coimbatore_7day');

  const [schedule, setSchedule] = useState<IrrigationScheduleResponse | null>(null);
  const [weatherForecast, setWeatherForecast] = useState<WeatherForecastResponse | null>(null);
  const [weatherHistorical, setWeatherHistorical] = useState<WeatherHistoricalResponse | null>(null);

  const [language, setLanguage] = useState<'English' | 'Telugu'>('English');
  const [farmerName, setFarmerName] = useState<string>('Farmer / Operator');
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const refreshHealth = async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch {
      // Offline or backend not yet up
      setHealth(null);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <AppContext.Provider
      value={{
        activeScreen,
        setActiveScreen,
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
        weatherForecast,
        setWeatherForecast,
        weatherHistorical,
        setWeatherHistorical,
        language,
        setLanguage,
        farmerName,
        setFarmerName,
        health,
        refreshHealth,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
