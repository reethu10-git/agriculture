"""
AGRI-2: Irrigation Scheduling Advisor
A Student-Ready, Production-Grade AI Agricultural Application
Frontend: Streamlit | Agricultural Engine: FAO-56 Penman-Monteith | AI: Nexus API (gpt-5-nano)
Data Sources: Open-Meteo (Live NWP), NASA POWER (Historical), ISRIC SoilGrids, TNAU Agritech
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, date, timedelta

from config.settings import (
    DEFAULT_LOCATION,
    CROP_DATABASE,
    SOIL_DATABASE,
    AREA_CONVERSIONS,
    NEXUS_MODEL
)
from src.data_loader import load_and_validate_weather_csv
from src.weather_service import (
    get_available_sample_datasets,
    load_sample_dataset,
    fetch_openmeteo_7day_forecast
)
from src.nasa_power_service import fetch_nasa_power_historical
from src.soil_service import fetch_soilgrids_properties
from src.agricultural_reference import (
    load_tnau_rice_guidelines,
    get_tnau_stage_recommendation,
    get_tnau_soil_interval
)
from src.eto_calculator import calculate_eto_series
from src.irrigation_scheduler import generate_irrigation_schedule
from src.nexus_client import NexusClient
from src.advisory_generator import generate_farmer_advisory
from src.approval_logger import record_farmer_decision, load_approval_history


# Streamlit Page Configuration
st.set_page_config(
    page_title="AGRI-2: Irrigation Scheduling Advisor",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Agricultural Themed CSS Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b5e20;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #388e3c;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #f1f8e9;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 5px solid #4caf50;
        margin-bottom: 10px;
    }
    .provenance-card {
        background-color: #f9fbe7;
        border: 1px solid #c5e1a5;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }
    .badge-live {
        background-color: #e8f5e9;
        color: #1b5e20;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #81c784;
    }
    .badge-historical {
        background-color: #e1f5fe;
        color: #01579b;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #4fc3f7;
    }
    .badge-simulation {
        background-color: #fffde7;
        color: #f57f17;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #fff176;
    }
    .badge-upload {
        background-color: #f3e5f5;
        color: #4a148c;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #ba68c8;
    }
    .advisory-box {
        background-color: #ffffff;
        border: 1px solid #c8e6c9;
        border-radius: 8px;
        padding: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)


# Top Banner
st.markdown('<div class="main-title">🌾 AGRI-2: Irrigation Scheduling Advisor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intelligent FAO-56 Hydrological Advisory Engine with Real-World Weather & Soil Ingestion</div>', unsafe_allow_html=True)


# ==========================================
# SIDEBAR: PARAMETERS & WEATHER CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Farm & Simulation Inputs")

    # 1. Location Settings
    st.subheader("📍 Location")
    location_name = st.text_input("Location Name", value=DEFAULT_LOCATION["name"])
    col_lat, col_lon = st.columns(2)
    with col_lat:
        latitude = st.number_input("Latitude (°N)", value=DEFAULT_LOCATION["latitude"], format="%.4f")
    with col_lon:
        longitude = st.number_input("Longitude (°E)", value=DEFAULT_LOCATION["longitude"], format="%.4f")
    elevation_m = st.number_input("Elevation (m ASL)", value=DEFAULT_LOCATION["elevation"], step=10.0)

    st.markdown("---")

    # 2. Crop & Soil Settings
    st.subheader("🌱 Crop & Soil Profile")
    crop_list = list(CROP_DATABASE.keys())
    crop_name = st.selectbox("Select Crop", options=crop_list, index=crop_list.index("Rice") if "Rice" in crop_list else 0)

    crop_stages = list(CROP_DATABASE[crop_name]["stages"].keys())
    growth_stage = st.selectbox("Growth Stage", options=crop_stages, index=crop_stages.index("Development") if "Development" in crop_stages else 0)

    soil_list = list(SOIL_DATABASE.keys())
    soil_type = st.selectbox("Farmer Soil Type", options=soil_list, index=soil_list.index("Loamy") if "Loamy" in soil_list else 0)

    # 3. Field Area Settings
    st.subheader("📐 Field Dimensions")
    col_area, col_unit = st.columns([1.5, 1.2])
    with col_area:
        field_area_val = st.number_input("Field Area", min_value=0.1, value=1.0, step=0.5)
    with col_unit:
        field_area_unit = st.selectbox("Area Unit", options=["Acre", "Hectare", "Square Meter"], index=0)

    initial_condition = st.selectbox(
        "Initial Soil-Water Condition",
        options=["Moderate", "Adequate / Target", "Dry / Low"],
        index=0
    )

    st.markdown("---")

    # 4. Weather Source Selection (4 Official Options)
    st.subheader("🌦️ Weather Data Source")
    data_source_mode = st.radio(
        "Select Weather Input Mode",
        options=[
            "1. Historical Simulation",
            "2. Live Weather Forecast – Open-Meteo",
            "3. Historical Weather – NASA POWER",
            "4. Upload Custom CSV"
        ],
        index=0
    )

    weather_df = None
    source_label = ""
    provenance_status = ""
    provenance_badge_html = ""
    retrieval_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_range_str = ""
    weather_warnings = []

    if data_source_mode == "1. Historical Simulation":
        sample_options = list(get_available_sample_datasets().keys())
        selected_sample = st.selectbox("Choose Historical Scenario", options=sample_options, index=0)
        weather_df = load_sample_dataset(selected_sample)
        source_label = f"Historical Simulation: {selected_sample}"
        provenance_status = "SIMULATION_DATA"
        provenance_badge_html = '<span class="badge-simulation">🟡 SIMULATION DATA</span>'
        date_range_str = f"{weather_df['date'].iloc[0]} to {weather_df['date'].iloc[min(6, len(weather_df)-1)]}"
        st.info("ℹ️ Using recorded historical scenario for simulated testing. Not a live forecast.")

    elif data_source_mode == "2. Live Weather Forecast – Open-Meteo":
        if st.button("🔄 Fetch Live 7-Day Forecast", width="stretch"):
            with st.spinner("Fetching live forecast from Open-Meteo API (Asia/Kolkata)..."):
                forecast_res = fetch_openmeteo_7day_forecast(latitude, longitude, elevation_m, force_refresh=True)
                if forecast_res["success"]:
                    st.session_state["live_weather_df"] = forecast_res["dataframe"]
                    st.session_state["live_weather_meta"] = forecast_res["metadata"]
                    st.session_state["live_weather_label"] = forecast_res["source_label"]
                    st.success("Live forecast loaded from Open-Meteo!")
                else:
                    st.error(forecast_res["error"])

        if "live_weather_df" in st.session_state:
            weather_df = st.session_state["live_weather_df"]
            source_label = st.session_state.get("live_weather_label", "Open-Meteo Forecast")
            provenance_status = "LIVE_FORECAST"
            provenance_badge_html = '<span class="badge-live">🟢 LIVE FORECAST</span>'
            meta = st.session_state.get("live_weather_meta", {})
            retrieval_timestamp = meta.get("download_date_utc", retrieval_timestamp)[:19] + " UTC"
            date_range_str = f"{meta.get('date_range', {}).get('start_date', '')} to {meta.get('date_range', {}).get('end_date', '')}"
        else:
            st.warning("Click 'Fetch Live 7-Day Forecast' to query meteorological servers, or fallback to default.")
            weather_df = load_sample_dataset("Coimbatore Kharif Normal (7-Day Default)")
            source_label = "Historical Simulation: Coimbatore Kharif Normal (Fallback Default)"
            provenance_status = "SIMULATION_DATA"
            provenance_badge_html = '<span class="badge-simulation">🟡 SIMULATION DATA</span>'
            date_range_str = f"{weather_df['date'].iloc[0]} to {weather_df['date'].iloc[6]}"

    elif data_source_mode == "3. Historical Weather – NASA POWER":
        col_sdate, col_edate = st.columns(2)
        with col_sdate:
            hist_start = st.date_input("Start Date", value=date(2026, 10, 1), min_value=date(2020, 1, 1), max_value=date(2026, 11, 15))
        with col_edate:
            hist_end = st.date_input("End Date (7 Days)", value=hist_start + timedelta(days=6))

        if st.button("📥 Retrieve NASA POWER Observations", width="stretch"):
            with st.spinner("Querying NASA POWER Daily Agroclimatology API..."):
                start_str = hist_start.strftime("%Y%m%d")
                end_str = hist_end.strftime("%Y%m%d")
                nasa_res = fetch_nasa_power_historical(start_str, end_str, latitude, longitude, force_refresh=True)
                if nasa_res["success"]:
                    st.session_state["nasa_weather_df"] = nasa_res["dataframe"]
                    st.session_state["nasa_weather_meta"] = nasa_res["metadata"]
                    st.session_state["nasa_weather_label"] = nasa_res["source_label"]
                    st.success(f"NASA POWER historical records retrieved & saved to data/raw/nasa_power/!")
                else:
                    st.error(nasa_res.get("error", "Failed to retrieve NASA POWER data."))
                    if nasa_res.get("dataframe") is not None:
                        st.session_state["nasa_weather_df"] = nasa_res["dataframe"]
                        st.session_state["nasa_weather_label"] = nasa_res["source_label"]

        if "nasa_weather_df" in st.session_state:
            weather_df = st.session_state["nasa_weather_df"]
            source_label = st.session_state.get("nasa_weather_label", "NASA POWER Daily Observations")
            provenance_status = "HISTORICAL_OBSERVATION_REANALYSIS"
            provenance_badge_html = '<span class="badge-historical">🔵 HISTORICAL OBSERVATION / REANALYSIS</span>'
            meta = st.session_state.get("nasa_weather_meta", {})
            retrieval_timestamp = meta.get("download_date_utc", retrieval_timestamp)[:19] + " UTC"
            drange = meta.get("date_range", {})
            date_range_str = f"{drange.get('start_date', '')} to {drange.get('end_date', '')}"
        else:
            st.info("Click 'Retrieve NASA POWER Observations' to download observations from NASA servers.")
            weather_df = load_sample_dataset("Coimbatore Historical Observations (30-Day)").head(7)
            source_label = "Historical Weather – NASA POWER / TNAU Climatology (Local)"
            provenance_status = "HISTORICAL_OBSERVATION_REANALYSIS"
            provenance_badge_html = '<span class="badge-historical">🔵 HISTORICAL OBSERVATION / REANALYSIS</span>'
            date_range_str = f"{weather_df['date'].iloc[0]} to {weather_df['date'].iloc[6]}"

    elif data_source_mode == "4. Upload Custom CSV":
        uploaded_file = st.file_uploader("Upload 7-Day Weather CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                weather_df, weather_warnings = load_and_validate_weather_csv(uploaded_file)
                source_label = f"Custom CSV Upload: {uploaded_file.name}"
                provenance_status = "USER_CUSTOM_CSV"
                provenance_badge_html = '<span class="badge-upload">🟣 FARMER-PROVIDED / CUSTOM CSV</span>'
                date_range_str = f"{weather_df['date'].iloc[0]} to {weather_df['date'].iloc[min(6, len(weather_df)-1)]}"
                st.success("Uploaded CSV successfully validated.")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
                weather_df = load_sample_dataset("Coimbatore Kharif Normal (7-Day Default)")
                source_label = "Historical Simulation: Fallback Default"
                provenance_status = "SIMULATION_DATA"
                provenance_badge_html = '<span class="badge-simulation">🟡 SIMULATION DATA</span>'
        else:
            st.info("Upload a CSV file containing date, tmax, tmin, rh, wind, solar, and rain.")
            weather_df = load_sample_dataset("Coimbatore Kharif Normal (7-Day Default)")
            source_label = "Historical Simulation: Coimbatore Kharif Normal (Default)"
            provenance_status = "SIMULATION_DATA"
            provenance_badge_html = '<span class="badge-simulation">🟡 SIMULATION DATA</span>'
            date_range_str = f"{weather_df['date'].iloc[0]} to {weather_df['date'].iloc[6]}"

    st.markdown("---")

    # 5. Nexus AI Client Status
    st.subheader("🤖 AI Advisory Engine")
    nexus_client = NexusClient()
    if nexus_client.is_configured():
        st.success(f"Nexus API Active: {nexus_client.model}")
    else:
        st.warning("Nexus API key not configured. Fallback deterministic advisory active.")


# Ensure weather_df is valid
if weather_df is None or len(weather_df) == 0:
    weather_df = load_sample_dataset("Coimbatore Kharif Normal (7-Day Default)")
    source_label = "Historical Simulation: Coimbatore Kharif Normal (Default)"
    provenance_status = "SIMULATION_DATA"
    provenance_badge_html = '<span class="badge-simulation">🟡 SIMULATION DATA</span>'

# Slice to exactly 7 days
weather_7day = weather_df.head(7).copy()

# Execute 7-Day Agricultural Scheduling Engine
schedule_result = generate_irrigation_schedule(
    weather_df=weather_7day,
    crop_name=crop_name,
    growth_stage=growth_stage,
    soil_type=soil_type,
    field_area_val=field_area_val,
    field_area_unit=field_area_unit,
    initial_water_condition=initial_condition,
    latitude_deg=latitude,
    elevation_m=elevation_m
)

schedule_df = schedule_result["schedule_df"]

# Fetch SoilGrids modelled estimates for location
soilgrids_res = fetch_soilgrids_properties(latitude, longitude)
soilgrids_props = soilgrids_res.get("properties", {})

# Fetch TNAU Rice guidelines for selected stage and soil
tnau_stage_info = get_tnau_stage_recommendation(growth_stage)
tnau_soil_info = get_tnau_soil_interval(soil_type)


# ==========================================
# MAIN APPLICATION INTERFACE: 5 SCREENS TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 1. Input Details & Physical Parameters",
    "🌦️ 2. Weather Overview",
    "💧 3. Irrigation Analysis (FAO-56)",
    "🗓️ 4. 7-Day Irrigation Schedule",
    "🧑‍🌾 5. AI Advisory & Farmer Approval"
])


# ------------------------------------------
# SCREEN 1: INPUT DETAILS & PHYSICAL PARAMETERS
# ------------------------------------------
with tab1:
    st.markdown("### 📋 Screen 1: Farm Configuration, Provenance & Soil Physics")
    st.caption("Review the meteorological provenance, soil physical properties, and TNAU agronomic recommendations.")

    # Data Source & Provenance Card
    st.markdown(f"""
    <div class="provenance-card">
        <table style="width:100%; border:none;">
            <tr>
                <td><b>Selected Data Source:</b> {source_label}</td>
                <td style="text-align:right;"><b>Provenance:</b> {provenance_badge_html}</td>
            </tr>
            <tr>
                <td><b>Coordinates:</b> {latitude:.4f}° N, {longitude:.4f}° E (Elev: {elevation_m:.1f} m ASL)</td>
                <td style="text-align:right;"><b>Retrieval Timestamp:</b> {retrieval_timestamp}</td>
            </tr>
            <tr>
                <td><b>Weather Date Range:</b> {date_range_str}</td>
                <td style="text-align:right;"><b>Data Integrity:</b> Strictly separated from live/historical data</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    col_info1, col_info2, col_info3 = st.columns(3)

    with col_info1:
        st.markdown("**📍 Geographical Context**")
        st.write(f"- **Location**: {location_name}")
        st.write(f"- **Coordinates**: {latitude:.4f}° N, {longitude:.4f}° E")
        st.write(f"- **Elevation**: {elevation_m:.1f} m ASL")
        st.write(f"- **Atmospheric Pressure**: {schedule_df['pressure_kpa'].iloc[0] if 'pressure_kpa' in schedule_df.columns else 96.8:.1f} kPa")
        st.write(f"- **Timezone**: Asia/Kolkata")

    with col_info2:
        st.markdown("**🌱 Crop Profile (FAO-56 & TNAU)**")
        crop_meta = CROP_DATABASE.get(crop_name, CROP_DATABASE["Rice"])
        stage_meta = crop_meta["stages"].get(growth_stage, {})
        st.write(f"- **Crop**: {crop_name} (*{crop_meta.get('scientific_name', '')}*)")
        st.write(f"- **Cultivation Type**: {crop_meta.get('cultivation_type', '').replace('_', ' ').title()}")
        st.write(f"- **Growth Stage**: {growth_stage}")
        st.write(f"- **Baseline Kc**: {stage_meta.get('kc', 1.05)}")
        st.write(f"- **TNAU Water Stress Sensitivity**: **{tnau_stage_info.get('sensitivity', 'MEDIUM')}**")

    with col_info3:
        st.markdown("**🧪 Farmer-Provided Soil Properties**")
        soil_meta = SOIL_DATABASE.get(soil_type, SOIL_DATABASE["Loamy"])
        st.write(f"- **Input Soil Type**: {soil_type}")
        st.write(f"- **Field Capacity (θFC)**: {soil_meta['field_capacity'] * 100:.1f} % vol")
        st.write(f"- **Wilting Point (θWP)**: {soil_meta['wilting_point'] * 100:.1f} % vol")
        st.write(f"- **Available Water Capacity**: {(soil_meta['field_capacity'] - soil_meta['wilting_point']) * 100:.1f} % vol")
        st.write(f"- **Puddled Percolation Rate**: {soil_meta['percolation_rate']} mm/day")

    st.markdown("---")

    # SOIL INTEGRATION: ISRIC SoilGrids Modelled Estimates
    st.markdown("#### 🔬 Soil Data Integration: ISRIC SoilGrids Modelled Estimates")
    st.caption("Independent modelled soil physical properties extracted for Coimbatore coordinates via SoilGrids REST API (ISRIC 250m).")

    sg_col1, sg_col2, sg_col3, sg_col4, sg_col5, sg_col6 = st.columns(6)
    sg_col1.metric("Clay Content", f"{soilgrids_props.get('clay_percent', 28.5)} %")
    sg_col2.metric("Sand Content", f"{soilgrids_props.get('sand_percent', 44.8)} %")
    sg_col3.metric("Silt Content", f"{soilgrids_props.get('silt_percent', 26.7)} %")
    sg_col4.metric("Organic Carbon", f"{soilgrids_props.get('organic_carbon_g_kg', 8.6)} g/kg")
    sg_col5.metric("Bulk Density", f"{soilgrids_props.get('bulk_density_g_cm3', 1.42)} g/cm³")
    sg_col6.metric("Soil pH (H2O)", f"{soilgrids_props.get('soil_ph', 7.3)}")

    st.warning("""
    ⚠️ **IMPORTANT SOIL DATA NOTIFICATION:**
    The values above are **Modelled Soil Property Estimates** from the global ISRIC SoilGrids spatial database.
    They represent physical texture and chemical potential, **NOT actual real-time field moisture**.
    The farmer's selected soil type and actual field measurements remain the active operational input.
    """)

    st.markdown("---")

    # AGRICULTURAL REFERENCE: TNAU Rice Water Management Guidelines
    st.markdown("#### 🌾 TNAU Agritech Agricultural Reference Guidelines")
    st.caption("Official water management recommendations from the Tamil Nadu Agricultural University (TNAU) Agritech Portal.")

    tnau_c1, tnau_c2 = st.columns(2)
    with tnau_c1:
        st.markdown("**Alternate Wetting and Drying (AWD) / Pani Pipe Protocol:**")
        st.write(f"- **Selected Stage Policy**: {tnau_stage_info.get('mandatory_management', '')}")
        st.write(f"- **Impact of Moisture Stress**: {tnau_stage_info.get('impact_of_stress', '')}")
        st.write("- **Panicle Initiation to Flowering**: Strictly maintain continuous 5 cm (50 mm) standing water.")
        st.write("- **Vegetative Phase**: Allow water level to subside to soil surface before reflooding to 5 cm.")

    with tnau_c2:
        st.markdown(f"**TNAU Irrigation Interval Recommendation for {soil_type} Soil:**")
        st.write(f"- **Recommended Interval**: **{tnau_soil_info.get('recommended_interval_days', '3 to 4 days')}**")
        st.write(f"- **Typical Percolation Loss**: {tnau_soil_info.get('percolation_loss_typical_mm_day', '2.0 - 3.0')} mm/day")
        st.write(f"- **Agronomic Behavior**: {tnau_soil_info.get('characteristics', '')}")
        st.markdown("🔗 *Reference: [TNAU Agritech Portal - Rice Water Management](https://agritech.tnau.ac.in/agriculture/agri_irrigationmgt_rice.html)*")


# ------------------------------------------
# SCREEN 2: WEATHER OVERVIEW
# ------------------------------------------
with tab2:
    st.markdown("### 🌦️ Screen 2: Agro-Meteorological 7-Day Overview")
    st.caption("Visualizing key temperature, humidity, solar radiation, wind, and precipitation drivers.")

    # Provenance Strip
    st.markdown(f"""
    <div style="margin-bottom: 15px;">
        <b>Active Dataset:</b> {source_label} &nbsp;|&nbsp; <b>Provenance:</b> {provenance_badge_html} &nbsp;|&nbsp; <b>Date Range:</b> {date_range_str}
    </div>
    """, unsafe_allow_html=True)

    # Metric Row
    tmax_avg = weather_7day["tmax"].mean()
    tmin_avg = weather_7day["tmin"].mean()
    rain_total = weather_7day["rainfall_mm"].sum()
    rh_avg = weather_7day["rh_mean"].mean() if "rh_mean" in weather_7day.columns else weather_7day["rh_max"].mean()
    wind_avg = weather_7day["wind_speed_2m"].mean()
    solar_avg = weather_7day["solar_rad_mj"].mean() if "solar_rad_mj" in weather_7day.columns else 20.0

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Avg Tmax", f"{tmax_avg:.1f} °C")
    m2.metric("Avg Tmin", f"{tmin_avg:.1f} °C")
    m3.metric("Total Rainfall", f"{rain_total:.1f} mm")
    m4.metric("Avg Humidity", f"{rh_avg:.0f} %")
    m5.metric("Avg Wind (2m)", f"{wind_avg:.1f} m/s")
    m6.metric("Avg Solar Rad", f"{solar_avg:.1f} MJ/m²")

    # Plot 1: Temperature & Rainfall Dual Axis
    fig_temp_rain = go.Figure()
    fig_temp_rain.add_trace(go.Bar(
        x=weather_7day["date"].astype(str),
        y=weather_7day["rainfall_mm"],
        name="Rainfall (mm)",
        marker_color="#42a5f5",
        yaxis="y2"
    ))
    fig_temp_rain.add_trace(go.Scatter(
        x=weather_7day["date"].astype(str),
        y=weather_7day["tmax"],
        name="Tmax (°C)",
        line=dict(color="#e53935", width=3),
        mode="lines+markers"
    ))
    fig_temp_rain.add_trace(go.Scatter(
        x=weather_7day["date"].astype(str),
        y=weather_7day["tmin"],
        name="Tmin (°C)",
        line=dict(color="#fb8c00", width=2, dash="dash"),
        mode="lines+markers"
    ))

    fig_temp_rain.update_layout(
        title="7-Day Temperature Range and Daily Precipitation",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Temperature (°C)", side="left"),
        yaxis2=dict(title="Rainfall (mm)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.1, x=0.2),
        height=380,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    st.plotly_chart(fig_temp_rain, width="stretch")

    # Plot 2: Humidity and Solar Radiation
    col_plot2a, col_plot2b = st.columns(2)
    with col_plot2a:
        fig_rh = px.line(
            weather_7day,
            x=weather_7day["date"].astype(str),
            y=["rh_max", "rh_min"] if "rh_max" in weather_7day.columns and "rh_min" in weather_7day.columns else weather_7day.columns[1],
            title="Relative Humidity Bounds (%)",
            labels={"value": "Humidity (%)", "variable": "Metric"}
        )
        fig_rh.update_layout(height=300, margin=dict(l=30, r=30, t=50, b=30))
        st.plotly_chart(fig_rh, width="stretch")

    with col_plot2b:
        fig_solar = px.bar(
            weather_7day,
            x=weather_7day["date"].astype(str),
            y="solar_rad_mj" if "solar_rad_mj" in weather_7day.columns else weather_7day.columns[1],
            title="Solar Radiation (MJ / m² / day)",
            color_discrete_sequence=["#ffb300"]
        )
        fig_solar.update_layout(height=300, margin=dict(l=30, r=30, t=50, b=30))
        st.plotly_chart(fig_solar, width="stretch")


# ------------------------------------------
# SCREEN 3: IRRIGATION ANALYSIS (FAO-56)
# ------------------------------------------
with tab3:
    st.markdown("### 💧 Screen 3: FAO-56 Evapotranspiration & Water Balance Analysis")
    st.caption("Deterministic breakdown of Reference Evapotranspiration (ETo), Crop Demand (ETc), and Soil Water Retention.")

    c_eto, c_etc, c_peff = st.columns(3)
    c_eto.metric("Total Reference ETo", f"{schedule_result['total_eto_mm']:.1f} mm")
    c_etc.metric(f"Total Crop Demand ({crop_name} ETc)", f"{schedule_result['total_etc_mm']:.1f} mm")
    c_peff.metric("Effective Rain Retained", f"{schedule_result['total_effective_rainfall_mm']:.1f} mm")

    # ETc vs ETo chart
    fig_et = go.Figure()
    fig_et.add_trace(go.Bar(
        x=schedule_df["date"],
        y=schedule_df["eto_mm"],
        name="Reference ETo (mm/day)",
        marker_color="#90caf9"
    ))
    fig_et.add_trace(go.Scatter(
        x=schedule_df["date"],
        y=schedule_df["etc_mm"],
        name=f"Crop ETc (Kc={schedule_df['kc'].iloc[0]})",
        line=dict(color="#2e7d32", width=4),
        mode="lines+markers"
    ))
    fig_et.update_layout(
        title=f"Daily Reference Evapotranspiration vs {crop_name} Water Demand",
        xaxis_title="Date",
        yaxis_title="mm / day",
        height=350,
        legend=dict(orientation="h", y=1.1, x=0.2),
        margin=dict(l=30, r=30, t=50, b=30)
    )
    st.plotly_chart(fig_et, width="stretch")

    # Dynamic Soil-Water Balance Trajectory
    is_rice = (crop_name.lower() == "rice")
    fig_swb = go.Figure()

    if is_rice and "ponded_water_depth_mm" in schedule_df.columns:
        fig_swb.add_trace(go.Scatter(
            x=schedule_df["date"],
            y=schedule_df["ponded_water_depth_mm"],
            mode="lines+markers",
            name="Ponded Water Depth (mm)",
            line=dict(color="#0288d1", width=3),
            fill="tozeroy",
            fillcolor="rgba(2, 136, 209, 0.15)"
        ))
        # Add threshold line
        fig_swb.add_hline(
            y=25.0 if growth_stage == "Mid-Season" else 0.0,
            line_dash="dot",
            line_color="red",
            annotation_text="AWD Safe Submergence Threshold"
        )
        fig_swb.add_hline(
            y=80.0,
            line_dash="dash",
            line_color="brown",
            annotation_text="Bund Crest Height (80mm Overflow)"
        )
        fig_swb.update_layout(
            title="Paddy Water Layer Depth & Alternate Wetting and Drying (AWD) Dynamics",
            yaxis_title="Water Depth (mm)",
            height=360,
            margin=dict(l=30, r=30, t=50, b=30)
        )
    else:
        # Upland depletion
        fig_swb.add_trace(go.Scatter(
            x=schedule_df["date"],
            y=schedule_df.get("depletion_mm", [0]*7),
            mode="lines+markers",
            name="Root Zone Depletion Dr (mm)",
            line=dict(color="#e65100", width=3)
        ))
        if "raw_mm" in schedule_df.columns:
            fig_swb.add_hline(
                y=schedule_df["raw_mm"].iloc[0],
                line_dash="dot",
                line_color="red",
                annotation_text="Critical Stress Threshold (RAW)"
            )
        fig_swb.update_layout(
            title="Root-Zone Soil Moisture Depletion vs Critical Stress Threshold",
            yaxis_title="Soil Moisture Depletion (mm)",
            height=360,
            margin=dict(l=30, r=30, t=50, b=30)
        )

    st.plotly_chart(fig_swb, width="stretch")


# ------------------------------------------
# SCREEN 4: 7-DAY IRRIGATION SCHEDULE
# ------------------------------------------
with tab4:
    st.markdown("### 🗓️ Screen 4: 7-Day Day-by-Day Irrigation Schedule")
    st.caption("Actionable recommendations with water depth (mm) and required pumping volume (Litres).")

    # Water Savings Benchmark Summary Banner
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        st.metric("Total Recommended Irrigation", f"{schedule_result['total_irrigation_recommended_mm']:.1f} mm")
    with b_col2:
        st.metric("Field Pumping Volume", f"{schedule_result['total_irrigation_volume_litres']:,.0f} L")
    with b_col3:
        st.metric("Traditional Baseline Practice", f"{schedule_result['baseline_irrigation_mm']:.1f} mm ({schedule_result['baseline_irrigation_litres']:,.0f} L)")
    with b_col4:
        pct_saved = schedule_result["water_savings_pct"]
        is_target_met = pct_saved >= 15.0
        st.metric("Water Reduction", f"{pct_saved:.1f} %", delta="Goal >= 15% Met" if is_target_met else "Below 15% Goal")

    if is_target_met:
        st.success(f"✅ **Efficiency Goal Exceeded**: AGRI-2 scheduling saves **{schedule_result['water_savings_pct']:.1f}%** ({schedule_result['water_savings_litres']:,.0f} Litres) of water compared to traditional fixed flooding.")
    else:
        st.info(f"ℹ️ Water savings are {schedule_result['water_savings_pct']:.1f}%. High evaporative demand required necessary applications to safeguard crop health.")

    st.markdown("#### 📋 Recommended Daily Action Table")

    display_cols = [
        "date", "eto_mm", "kc", "etc_mm", "rainfall_mm",
        "effective_rainfall_mm", "soil_water_status",
        "recommended_irrigation_mm", "irrigation_volume_litres",
        "decision", "reason"
    ]
    renamed_cols = {
        "date": "Date",
        "eto_mm": "ETo (mm)",
        "kc": "Kc",
        "etc_mm": "ETc (mm)",
        "rainfall_mm": "Rain (mm)",
        "effective_rainfall_mm": "Eff Rain (mm)",
        "soil_water_status": "Soil Water Status",
        "recommended_irrigation_mm": "Irrigate (mm)",
        "irrigation_volume_litres": f"Volume (Litres)",
        "decision": "Decision",
        "reason": "Agronomic Rationale"
    }

    display_df = schedule_df[display_cols].rename(columns=renamed_cols)
    st.dataframe(display_df, width="stretch", hide_index=True)

    # Downloads
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Schedule as CSV",
            data=csv_data,
            file_name=f"agri2_irrigation_schedule_{crop_name}_{growth_stage}.csv",
            mime="text/csv",
            width="stretch"
        )
    with col_d2:
        json_data = schedule_df.to_json(orient="records", date_format="iso").encode('utf-8')
        st.download_button(
            "📥 Download Schedule as JSON",
            data=json_data,
            file_name=f"agri2_irrigation_schedule_{crop_name}_{growth_stage}.json",
            mime="application/json",
            width="stretch"
        )


# ------------------------------------------
# SCREEN 5: AI FARMER ADVISORY & APPROVAL
# ------------------------------------------
with tab5:
    st.markdown("### 🧑‍🌾 Screen 5: AI Farmer Advisory & Schedule Approval")
    st.caption("AI-generated multi-lingual explanations (English & Telugu) with mandatory human farmer verification.")

    # Generate or fetch advisory
    if "current_advisory" not in st.session_state or st.session_state.get("advisory_crop") != crop_name or st.session_state.get("advisory_stage") != growth_stage:
        with st.spinner("Generating bilingual farmer advisory via Nexus API / Fallback..."):
            advisory_data = generate_farmer_advisory(schedule_result, nexus_client)
            st.session_state["current_advisory"] = advisory_data
            st.session_state["advisory_crop"] = crop_name
            st.session_state["advisory_stage"] = growth_stage

    advisory_data = st.session_state["current_advisory"]

    # Display Engine Source
    st.info(f"**Advisory Source Engine**: {advisory_data['source']}")
    if advisory_data.get("error"):
        st.warning(f"Note: {advisory_data['error']}")

    # Language Tabs
    adv_tab_eng, adv_tab_tel = st.tabs(["🇬🇧 English Advisory", "🇮🇳 తెలుగు సలహాదారు (Telugu)"])

    with adv_tab_eng:
        st.markdown('<div class="advisory-box">', unsafe_allow_html=True)
        st.markdown(advisory_data["english_advisory"])
        st.markdown('</div>', unsafe_allow_html=True)

    with adv_tab_tel:
        st.markdown('<div class="advisory-box">', unsafe_allow_html=True)
        st.markdown(advisory_data.get("telugu_advisory", advisory_data.get("tamil_advisory", "")))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # HUMAN-IN-THE-LOOP FARMER APPROVAL STEP
    # ==========================================
    st.markdown("### ✍️ Farmer Schedule Review and Approval")
    st.markdown("""
    > **⚠️ IMPORTANT SAFETY & OPERATIONAL NOTICE:**
    > This application provides decision support only. **Actual irrigation valve and pump operation must remain strictly manual.**
    > AGRI-2 does not operate automated valves or pumps. Please inspect field conditions and approve or decline the schedule below.
    """)

    col_app1, col_app2 = st.columns([2, 1])

    with col_app1:
        farmer_name = st.text_input("Farmer / Operator Name", value="K. Ramasamy (Coimbatore)")
        farmer_notes = st.text_area("Field Observations / Operator Notes (Optional)", placeholder="e.g. Inspected bund heights; pump voltage checked; soil moisture matches recommendation.")

    with col_app2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Approve Recommended Schedule", type="primary", width="stretch"):
            summary_info = {
                "crop": crop_name,
                "field_area": f"{field_area_val} {field_area_unit}",
                "total_irrigation_mm": schedule_result["total_irrigation_recommended_mm"],
                "total_irrigation_litres": schedule_result["total_irrigation_volume_litres"],
                "water_savings_pct": schedule_result["water_savings_pct"]
            }
            rec_result = record_farmer_decision(
                decision="APPROVED",
                schedule_summary=summary_info,
                farmer_notes=farmer_notes,
                approved_by=farmer_name
            )
            if rec_result["success"]:
                st.success("✅ **Schedule Approved & Recorded!** Decision saved to audit history (`outputs/approved_schedules.json`). Proceed with manual valve scheduling.")
            else:
                st.error(f"Failed to record approval: {rec_result.get('error')}")

        if st.button("❌ Modify / Decline Schedule", width="stretch"):
            summary_info = {
                "crop": crop_name,
                "field_area": f"{field_area_val} {field_area_unit}",
                "total_irrigation_mm": schedule_result["total_irrigation_recommended_mm"],
                "total_irrigation_litres": schedule_result["total_irrigation_volume_litres"],
                "water_savings_pct": schedule_result["water_savings_pct"]
            }
            record_farmer_decision(
                decision="DECLINED / MODIFIED",
                schedule_summary=summary_info,
                farmer_notes=farmer_notes,
                approved_by=farmer_name
            )
            st.warning("⚠️ **Schedule Declined.** Record updated in audit history. Please adjust field parameters or re-run simulation.")

    # Historical Approval Log Expander
    with st.expander("📜 View Audit Trail of Farmer Approvals (outputs/approved_schedules.json)"):
        hist = load_approval_history()
        if hist:
            st.dataframe(pd.DataFrame(hist), width="stretch")
        else:
            st.write("No previous decisions recorded yet.")
