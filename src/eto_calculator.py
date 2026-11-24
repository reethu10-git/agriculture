"""
AGRI-2: FAO-56 Penman-Monteith Reference Evapotranspiration (ETo) Engine
Calculates daily reference evapotranspiration strictly following the Food and Agriculture
Organization (FAO) Irrigation and Drainage Paper No. 56 standards.
"""

import math
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from config.settings import (
    SOLAR_CONSTANT_GSC,
    STEFAN_BOLTZMANN,
    PSYCHROMETRIC_A,
    ALBEDO_CANOPY
)


def saturation_vapour_pressure(t_celsius: float) -> float:
    """
    FAO-56 Eq. 11: Saturation vapour pressure as a function of temperature T.
    e°(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))
    Unit: kPa
    """
    return 0.6108 * math.exp((17.27 * t_celsius) / (t_celsius + 237.3))


def mean_saturation_vapour_pressure(tmin: float, tmax: float) -> float:
    """
    FAO-56 Eq. 12: Mean saturation vapour pressure.
    es = (e°(Tmax) + e°(Tmin)) / 2
    Unit: kPa
    """
    return (saturation_vapour_pressure(tmax) + saturation_vapour_pressure(tmin)) / 2.0


def actual_vapour_pressure(
    tmin: float,
    tmax: float,
    rh_min: Optional[float] = None,
    rh_max: Optional[float] = None,
    rh_mean: Optional[float] = None
) -> float:
    """
    FAO-56 Eq. 17 & 19: Actual vapour pressure ea derived from relative humidity.
    If RHmax and RHmin are available:
        ea = (e°(Tmin) * (RHmax / 100) + e°(Tmax) * (RHmin / 100)) / 2
    If only RHmean is available:
        ea = (RHmean / 100) * ((e°(Tmax) + e°(Tmin)) / 2)
    Unit: kPa
    """
    e_tmin = saturation_vapour_pressure(tmin)
    e_tmax = saturation_vapour_pressure(tmax)

    if rh_max is not None and rh_min is not None and not (math.isnan(rh_max) or math.isnan(rh_min)):
        return (e_tmin * (rh_max / 100.0) + e_tmax * (rh_min / 100.0)) / 2.0
    elif rh_mean is not None and not math.isnan(rh_mean):
        return (rh_mean / 100.0) * ((e_tmax + e_tmin) / 2.0)
    else:
        # Fallback assumption (FAO-56 p. 58): In absence of RH data, assume Tdew approx Tmin
        return e_tmin


def slope_vapour_pressure_curve(t_celsius: float) -> float:
    """
    FAO-56 Eq. 13: Slope of saturation vapour pressure curve (Delta).
    Delta = (4098 * (0.6108 * exp((17.27 * T) / (T + 237.3)))) / ((T + 237.3)^2)
    Unit: kPa / °C
    """
    e_0 = saturation_vapour_pressure(t_celsius)
    return (4098.0 * e_0) / ((t_celsius + 237.3) ** 2)


def atmospheric_pressure(elevation_m: float) -> float:
    """
    FAO-56 Eq. 7: Atmospheric pressure (P) as a function of elevation.
    P = 101.3 * ((293 - 0.0065 * z) / 293)^5.26
    Unit: kPa
    """
    return 101.3 * (((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26)


def psychrometric_constant(pressure_kpa: float) -> float:
    """
    FAO-56 Eq. 8: Psychrometric constant (gamma).
    gamma = 0.000665 * P
    Unit: kPa / °C
    """
    return PSYCHROMETRIC_A * pressure_kpa


def wind_speed_at_2m(wind_speed_z: float, z_m: float = 2.0) -> float:
    """
    FAO-56 Eq. 47: Wind speed adjustment to standard 2-meter height.
    u2 = uz * (4.87 / ln(67.8 * z - 5.42))
    Unit: m/s
    """
    if abs(z_m - 2.0) < 1e-4:
        return wind_speed_z
    return wind_speed_z * (4.87 / math.log(67.8 * z_m - 5.42))


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """
    FAO-56 Eqs. 21-28: Daily extraterrestrial radiation (Ra).
    Ra = (24 * 60 / pi) * Gsc * dr * (omega_s * sin(phi) * sin(delta) + cos(phi) * cos(delta) * sin(omega_s))
    Unit: MJ / (m2 * day)
    """
    phi = math.radians(latitude_deg)
    # Inverse relative distance Earth-Sun (Eq. 23)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    # Solar declination (Eq. 24)
    delta = 0.409 * math.sin((2.0 * math.pi * day_of_year / 365.0) - 1.39)

    # Sunset hour angle (Eq. 25)
    cos_omega_s = -math.tan(phi) * math.tan(delta)
    # Clamp to [-1, 1] to prevent domain errors at polar latitudes
    cos_omega_s = max(-1.0, min(1.0, cos_omega_s))
    omega_s = math.acos(cos_omega_s)

    ra = ((24.0 * 60.0) / math.pi) * SOLAR_CONSTANT_GSC * dr * (
        omega_s * math.sin(phi) * math.sin(delta) +
        math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )
    return max(0.0, ra)


def clear_sky_solar_radiation(ra: float, elevation_m: float) -> float:
    """
    FAO-56 Eq. 37: Clear-sky solar radiation (Rso).
    Rso = (0.75 + 2e-5 * z) * Ra
    Unit: MJ / (m2 * day)
    """
    return (0.75 + (2.0e-5 * elevation_m)) * ra


def net_solar_radiation(rs: float, albedo: float = ALBEDO_CANOPY) -> float:
    """
    FAO-56 Eq. 38: Net solar (shortwave) radiation (Rns).
    Rns = (1 - albedo) * Rs
    Unit: MJ / (m2 * day)
    """
    return (1.0 - albedo) * rs


def net_longwave_radiation(
    tmin: float,
    tmax: float,
    ea: float,
    rs: float,
    rso: float
) -> float:
    """
    FAO-56 Eq. 39: Net longwave radiation (Rnl).
    Rnl = sigma * ((Tmax_k^4 + Tmin_k^4) / 2) * (0.34 - 0.14 * sqrt(ea)) * (1.35 * (Rs / Rso) - 0.35)
    Unit: MJ / (m2 * day)
    """
    tmin_k4 = (tmin + 273.16) ** 4
    tmax_k4 = (tmax + 273.16) ** 4
    mean_temp_k4 = (tmin_k4 + tmax_k4) / 2.0

    # Relative cloudiness term clamped between 0.05 and 1.0 (FAO-56 guidelines)
    rs_rso = rs / rso if rso > 0 else 0.5
    rs_rso = max(0.05, min(1.0, rs_rso))
    cloudiness_factor = 1.35 * rs_rso - 0.35
    cloudiness_factor = max(0.05, min(1.0, cloudiness_factor))

    # Humidity factor
    humidity_factor = 0.34 - 0.14 * math.sqrt(max(0.0, ea))

    rnl = STEFAN_BOLTZMANN * mean_temp_k4 * humidity_factor * cloudiness_factor
    return max(0.0, rnl)


def calculate_fao56_eto(
    tmin: float,
    tmax: float,
    tmean: Optional[float] = None,
    rh_min: Optional[float] = None,
    rh_max: Optional[float] = None,
    rh_mean: Optional[float] = None,
    wind_speed: float = 2.0,
    solar_rad_mj: Optional[float] = None,
    day_of_year: int = 180,
    latitude_deg: float = 11.0168,
    elevation_m: float = 411.0,
    z_wind: float = 2.0,
    albedo: float = ALBEDO_CANOPY
) -> Dict[str, Any]:
    """
    Calculates Reference Evapotranspiration (ETo) using the FAO-56 Penman-Monteith equation:
    ETo = (0.408 * Delta * (Rn - G) + gamma * (900 / (T + 273)) * u2 * (es - ea)) /
          (Delta + gamma * (1 + 0.34 * u2))

    Returns:
        dict: Detailed breakdown of intermediate parameters and final ETo in mm/day.
    """
    if tmean is None or math.isnan(tmean):
        tmean = (tmax + tmin) / 2.0

    # 1. Atmospheric pressure and psychrometric constant
    pressure_kpa = atmospheric_pressure(elevation_m)
    gamma = psychrometric_constant(pressure_kpa)

    # 2. Vapour pressures and slope
    delta = slope_vapour_pressure_curve(tmean)
    es = mean_saturation_vapour_pressure(tmin, tmax)
    ea = actual_vapour_pressure(tmin, tmax, rh_min=rh_min, rh_max=rh_max, rh_mean=rh_mean)
    vpd = max(0.0, es - ea)

    # 3. Wind speed adjusted to 2m
    u2 = wind_speed_at_2m(wind_speed, z_wind)

    # 4. Radiation components
    ra = extraterrestrial_radiation(latitude_deg, day_of_year)
    rso = clear_sky_solar_radiation(ra, elevation_m)

    # If solar radiation is not provided, estimate from Hargreaves-Samani (FAO-56 Eq. 50)
    if solar_rad_mj is None or math.isnan(solar_rad_mj) or solar_rad_mj <= 0:
        k_rs = 0.16 # Interior location adjustment
        solar_rad_mj = k_rs * math.sqrt(max(0.0, tmax - tmin)) * ra

    rns = net_solar_radiation(solar_rad_mj, albedo)
    rnl = net_longwave_radiation(tmin, tmax, ea, solar_rad_mj, rso)
    rn = rns - rnl

    # Soil heat flux G is assumed negligible (G = 0) for daily time steps (FAO-56 p. 54)
    g = 0.0

    # 5. FAO-56 Penman-Monteith combination equation
    # Numerator term 1 (Radiation term)
    radiation_term = 0.408 * delta * (rn - g)
    # Numerator term 2 (Aerodynamic term)
    aerodynamic_term = gamma * (900.0 / (tmean + 273.0)) * u2 * vpd
    # Denominator
    denominator = delta + gamma * (1.0 + 0.34 * u2)

    eto = (radiation_term + aerodynamic_term) / denominator
    eto = max(0.0, eto) # Evapotranspiration cannot be negative

    return {
        "eto_mm_day": round(eto, 2),
        "tmean": round(tmean, 2),
        "pressure_kpa": round(pressure_kpa, 2),
        "gamma": round(gamma, 4),
        "delta": round(delta, 4),
        "es": round(es, 3),
        "ea": round(ea, 3),
        "vpd": round(vpd, 3),
        "u2": round(u2, 2),
        "ra": round(ra, 2),
        "rso": round(rso, 2),
        "rns": round(rns, 2),
        "rnl": round(rnl, 2),
        "rn": round(rn, 2),
        "radiation_term": round(radiation_term, 3),
        "aerodynamic_term": round(aerodynamic_term, 3),
        "denominator": round(denominator, 4)
    }


def calculate_eto_series(
    df: pd.DataFrame,
    latitude_deg: float = 11.0168,
    elevation_m: float = 411.0,
    z_wind: float = 2.0
) -> pd.DataFrame:
    """
    Computes daily ETo across a pandas DataFrame of weather records.
    Requires columns: date, tmax, tmin.
    Optional columns: tmean, rh_min, rh_max, rh_mean, wind_speed_2m, solar_rad_mj, pressure_kpa.
    """
    result_df = df.copy()
    eto_values = []
    rn_values = []
    vpd_values = []

    # Ensure date is parsed
    result_df['date'] = pd.to_datetime(result_df['date'])

    for _, row in result_df.iterrows():
        doy = row['date'].dayofyear
        tmin = float(row['tmin'])
        tmax = float(row['tmax'])
        tmean = float(row['tmean']) if 'tmean' in row and not pd.isna(row['tmean']) else (tmax + tmin) / 2.0
        rh_min = float(row['rh_min']) if 'rh_min' in row and not pd.isna(row['rh_min']) else None
        rh_max = float(row['rh_max']) if 'rh_max' in row and not pd.isna(row['rh_max']) else None
        rh_mean = float(row['rh_mean']) if 'rh_mean' in row and not pd.isna(row['rh_mean']) else None
        wind = float(row['wind_speed_2m']) if 'wind_speed_2m' in row and not pd.isna(row['wind_speed_2m']) else 2.0
        sol = float(row['solar_rad_mj']) if 'solar_rad_mj' in row and not pd.isna(row['solar_rad_mj']) else None

        res = calculate_fao56_eto(
            tmin=tmin,
            tmax=tmax,
            tmean=tmean,
            rh_min=rh_min,
            rh_max=rh_max,
            rh_mean=rh_mean,
            wind_speed=wind,
            solar_rad_mj=sol,
            day_of_year=doy,
            latitude_deg=latitude_deg,
            elevation_m=elevation_m,
            z_wind=z_wind
        )
        eto_values.append(res['eto_mm_day'])
        rn_values.append(res['rn'])
        vpd_values.append(res['vpd'])

    result_df['eto_mm_day'] = eto_values
    result_df['net_radiation_mj'] = rn_values
    result_df['vpd_kpa'] = vpd_values
    return result_df
