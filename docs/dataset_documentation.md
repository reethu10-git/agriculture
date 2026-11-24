# Dataset Documentation: AGRI-2 Irrigation Scheduling Advisor

## 1. Overview
Accurate irrigation scheduling requires high-frequency (daily or sub-daily) agro-meteorological records capable of driving the FAO-56 Penman-Monteith physical equation. Generic agronomic datasets (such as static crop yield or crop recommendation tables based solely on N-P-K soil nutrients) do not contain radiation, humidity, or wind parameters and cannot be used for physical water balance calculations.

AGRI-2 utilizes standardized, physically consistent agro-meteorological datasets curated for the primary target region of **Coimbatore, Tamil Nadu, India** (11.0168° N, 76.9558° E, 411m ASL).

---

## 2. Dataset Repositories & Data Ingestion Pipelines

| Dataset ID | Name | Source | Time Horizon | Parameters Included | Primary Usage |
|---|---|---|---|---|---|
| `sample_coimbatore_7day` | Coimbatore Normal 7-Day | NASA POWER / TNAU Climatology | 7 Days (Oct 15 - Oct 21) | Tmax, Tmin, RH, Wind, Solar Rad, Rain | Default base scenario (moderate rains) |
| `sample_dry_spell` | Coimbatore Dry Spell Scenario | NASA POWER Historical Summer | 7 Days (Mar 10 - Mar 16) | Tmax, Tmin, RH, Wind, High Rad, Zero Rain | High evaporative stress test |
| `sample_heavy_rain` | Coimbatore Monsoon Wet Week | IMD / NASA POWER Monsoon | 7 Days (Nov 01 - Nov 07) | Tmax, Tmin, High RH, Wind, Low Rad, Heavy Rain | Smart rain-capture and irrigation skip test |
| `sample_historical_30day` | Coimbatore Historical 30-Day | TNAU ACRC / NASA POWER | 30 Days (Oct 01 - Oct 30) | Full agro-climatological daily series | Multi-week simulation & baseline validation |
| `live_forecast_openmeteo` | Open-Meteo Live 7-Day API | Open-Meteo API (ECMWF / GFS) | Live 7 Days forward | Tmax, Tmin, RH (mean/max/min), Wind 10m->2m, Shortwave Rad, Rain, Pressure | Operational live forecast mode |
| `nasa_power_historical` | NASA POWER Daily API | NASA Langley Research Center | User-specified date range | T2M_MAX, T2M_MIN, T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR, PS | Standardized historical agro-meteorology |
| `isric_soilgrids_250m` | ISRIC SoilGrids 250m API | ISRIC World Soil Information | Static depth layers (0-5, 5-15, 15-30cm) | Clay, Sand, Silt, Soil Organic Carbon, Bulk Density, pH | Modelled soil estimates & regional baseline |
| `tnau_rice_guidelines` | TNAU Agritech Water Portal | Tamil Nadu Agricultural University | Agronomic Reference | Stage Kc, critical water stress stages, AWD Pani pipe thresholds, soil intervals | Regional agricultural rules & baseline calibration |

---

## 3. Real-World API Specifications & Integration Details

### A. Open-Meteo Weather Forecast API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Default Coordinates**: 11.0168° N, 76.9558° E (Coimbatore, Tamil Nadu)
- **Timezone**: `Asia/Kolkata`
- **Parameters Retrieved**:
  - `temperature_2m_max`, `temperature_2m_min`, `temperature_2m_mean` (°C)
  - `relative_humidity_2m_mean`, `relative_humidity_2m_max`, `relative_humidity_2m_min` (%)
  - `precipitation_sum` (mm)
  - `wind_speed_10m_max` (km/h) -> Converted to m/s ($/ 3.6$) and adjusted to 2m height via logarithmic profile ($u_2 = u_{10} \times 0.748$)
  - `shortwave_radiation_sum` ($MJ/m^2/day$)
  - `surface_pressure_mean` (hPa) -> Converted to kPa ($/ 10$)
- **Caching**: 30-minute in-memory TTL caching with graceful error handling and sample fallback.

### B. NASA POWER Daily API (Historical Meteorological Data)
- **Endpoint**: `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Community**: `AG` (Agroclimatology)
- **Parameters Retrieved**: `T2M_MAX`, `T2M_MIN`, `T2M`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `PS`
- **Storage**:
  - Raw JSON downloaded and cached in: `data/raw/nasa_power/`
  - Standardized CSV export in: `data/processed/nasa_power_coimbatore_<start>_<end>.csv`
  - Metadata recorded with download date, coordinates, date range, parameters, and sentinel `-999.0` cleanup notes.

### C. ISRIC SoilGrids REST API (Modelled Soil Estimates)
- **Endpoint**: `https://rest.isric.org/soilgrids/v2.0/properties/query`
- **Soil Properties Extracted**:
  - Clay content (`clay`): g/kg -> % ($/ 10$)
  - Sand content (`sand`): g/kg -> % ($/ 10$)
  - Silt content (`silt`): g/kg -> % ($/ 10$)
  - Soil Organic Carbon (`soc`): dg/kg -> g/kg ($/ 10$)
  - Bulk density (`bdod`): cg/cm³ -> g/cm³ ($/ 100$)
  - Soil pH in H2O (`phh2o`): pH*10 -> pH ($/ 10$)
- **Depth Range**: Mean across topsoil (0-30 cm: `0-5cm`, `5-15cm`, `15-30cm`).
- **Data Provenance & Disclaimer**: SoilGrids values are strictly labelled as **modelled soil estimates** from global digital soil mapping. They are never treated as live field moisture measurements. A regional profile for Coimbatore plains (`COIMBATORE_REGIONAL_PROFILE`) acts as reliable fallback.

### D. TNAU Agritech Rice Water Management Guidelines
- **Source**: Tamil Nadu Agricultural University Agritech Portal (`https://agritech.tnau.ac.in/`)
- **Key References Incorporated**:
  - Crop growth stages and duration: Initial (Vegetative), Development (Tillering), Mid-season (Panicle Initiation to Flowering), Late season (Grain filling to Maturity).
  - Critical water sensitivity stages: Flowering / Panicle Initiation has maximum sensitivity; water stress during this window causes severe floret sterility.
  - Alternate Wetting and Drying (AWD) / Pani Pipe Protocol: Allow water level to recede 15 cm below soil surface (5 cm ponded -> 0 cm -> -15 cm perforated tube) before re-irrigating to 5 cm depth. Safe AWD saves 25-30% irrigation water without yield reduction.
  - Soil-specific irrigation intervals: Clay/Clay Loam (3-4 days), Loamy (2-3 days), Sandy Loam (1-2 days).
- **Storage**: Maintained separately in `data/reference/tnau_rice_guidelines.json` and loaded via `src/agricultural_reference.py`.

---

## 3. Data Cleaning and Preprocessing Protocol
The module `src/data_loader.py` enforces a strict validation protocol upon loading any dataset (sample CSV, live API, or uploaded file):

1. **Date Parsing**: Normalized to ISO `YYYY-MM-DD`. Non-contiguous dates raise warnings.
2. **Temperature Sanity**:
   - $T_{max} \ge T_{min}$
   - Range checks: $-10^\circ\text{C} \le T \le 55^\circ\text{C}$.
   - If $T_{mean}$ is missing, it is calculated as $(T_{max} + T_{min}) / 2$.
3. **Humidity Consistency**:
   - $0\% \le RH \le 100\%$.
   - If $RH_{max}$ and $RH_{min}$ are missing but $RH_{mean}$ is given, bounds are estimated with standard diurnal dewpoint approximations.
4. **Wind Speed (2-meter adjustment)**:
   - Wind speed measured at height $z_w \neq 2\text{m}$ (e.g. 10m standard meteorological masts) is converted to 2m height using the logarithmic wind profile formula:
     $$u_2 = u_z \frac{4.87}{\ln(67.8 z - 5.42)}$$
5. **Solar Radiation Conversion**:
   - Units accepted: $MJ/m^2/day$. If provided in $W/m^2$, conversion is applied: $1 W/m^2 \text{ over 24h} = 0.0864 MJ/m^2/day$.
6. **Rainfall Consistency**:
   - $Rainfall \ge 0\text{ mm}$. Missing rainfall records default to $0.0\text{ mm}$.

---

## 4. Distinction Between Historical Records and Live Forecasts
In compliance with Section 3 of the system requirements:
- Historical observations are never misrepresented as forecasts.
- The user interface prominently displays the source mode:
  - 🟢 **LIVE 7-DAY FORECAST**: Dynamically fetched from meteorological model API.
  - 🟡 **HISTORICAL SIMULATION**: Replayed from verified historical observations.
  - 🔵 **USER CUSTOM FORECAST CSV**: Uploaded by the farmer or researcher.
