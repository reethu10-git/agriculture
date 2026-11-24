# AGRI-2 Datasets Overview and Guide

This directory contains meteorological and agricultural datasets used by the **AGRI-2: Irrigation Scheduling Advisor**.

## 1. Primary Geographical Focus
- **Location**: Coimbatore, Tamil Nadu, India
- **Coordinates**: Latitude: 11.0168° N, Longitude: 76.9558° E
- **Elevation**: 411 meters above sea level
- **Climate Zone**: Semi-arid / tropical wet-and-dry (BSh/Aw under Köppen classification)
- **Primary Kharif/Rabi Crop**: Rice (Oryza sativa), Maize, Sugarcane, Tomato

## 2. Public Dataset Sources & Provenance

### A. NASA POWER Agroclimatology
- **Source**: NASA Prediction Of Worldwide Energy Resources (POWER) Project
- **URL**: https://power.larc.nasa.gov/
- **License**: Public Domain (NASA Open Data Policy)
- **Parameters retrieved**:
  - `T2M_MAX`: Maximum air temperature at 2m (°C)
  - `T2M_MIN`: Minimum air temperature at 2m (°C)
  - `T2M`: Mean air temperature at 2m (°C)
  - `RH2M`: Relative humidity at 2m (%)
  - `WS2M`: Wind speed at 2m height (m/s)
  - `ALLSKY_SFC_SW_DWN`: All-sky surface shortwave downward irradiance / Solar Radiation ($MJ/m^2/day$)
  - `PRECTOTCORR`: Corrected total precipitation (mm/day)
  - `PS`: Surface atmospheric pressure (kPa)

### B. Open-Meteo Agro-Weather & Forecast API
- **Source**: Open-Meteo Historical & 7-Day Forecast API
- **URL**: https://open-meteo.com/
- **License**: CC BY 4.0 (Non-commercial & Commercial open access without API key requirement)
- **Purpose**: Provides real-time 7-day weather forecasts and historical series for any geographical coordinate.

### C. TNAU Agro Climate Research Centre (ACRC)
- **Source**: Tamil Nadu Agricultural University (TNAU) Agritech Portal
- **URL**: https://agritech.tnau.ac.in/
- **Reference**: Daily weather observations and crop water requirement benchmarks for Western Agroclimatic Zone of Tamil Nadu.

### D. FAO CLIMWAT 2.0 & CROPWAT 8.0 Databases
- **Source**: Food and Agriculture Organization of the United Nations (FAO)
- **URL**: https://www.fao.org/land-water/databases-and-software/cropwat/climwat-for-cropwat/en/
- **Station**: Coimbatore Station (Station ID: 43285, Lat 11.0°N, Lon 77.0°E, Elev 411m)
- **Purpose**: Reference baseline for monthly evapotranspiration and standard crop coefficient parameters.

## 3. Dataset Integrity & Critical Distinction
> **IMPORTANT NOTE**:
> A critical software and agricultural requirement of AGRI-2 is to **strictly distinguish between historical weather observations and live 7-day weather forecasts**.
> - Historical datasets (`coimbatore_historical_30day.csv`) are strictly labeled as **Historical Data Simulation Mode**.
> - The application clearly indicates to the user whether a schedule is generated from:
>   1. **Live 7-Day Forecast Service** (via Open-Meteo API),
>   2. **Pre-configured Historical Scenario Simulation** (Default 7-day, Dry Spell, or Heavy Monsoon), or
>   3. **User-Uploaded CSV Forecast File**.
> - Kaggle crop recommendation datasets (which contain N, P, K, pH, rainfall totals) are NOT suitable for daily irrigation scheduling because they lack daily solar radiation, vapor pressure, and wind speed. AGRI-2 uses genuine full-parameter agro-meteorological records conforming to FAO-56.

## 4. Column Schema and Units
Every weather CSV consumed by AGRI-2 must conform to the following schema:
- `date`: `YYYY-MM-DD` (String/Date)
- `tmax`: Daily maximum temperature in degrees Celsius (°C)
- `tmin`: Daily minimum temperature in degrees Celsius (°C)
- `tmean`: Daily mean temperature in degrees Celsius (°C)
- `rh_max`: Daily maximum relative humidity (%)
- `rh_min`: Daily minimum relative humidity (%)
- `rh_mean`: Daily mean relative humidity (%)
- `wind_speed_2m`: Daily wind speed adjusted to 2-meter height (m/s)
- `solar_rad_mj`: Daily total downward solar radiation ($MJ/m^2/day$)
- `rainfall_mm`: Total daily precipitation (mm)
- `pressure_kpa`: Surface atmospheric pressure in kilopascals (kPa, optional, defaults to barometric elevation formula if missing)
