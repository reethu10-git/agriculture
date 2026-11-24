"""
AGRI-2: AI Farmer Advisory Generator
Synthesizes deterministic Python calculations into clear, farmer-friendly advisories
in English and Telugu. Implements rigorous LLM boundaries and reliable fallback generators.
"""

from typing import Dict, Any, Tuple, Optional
from src.nexus_client import NexusClient


SYSTEM_INSTRUCTION = """You are an expert Agricultural Advisory Assistant for the AGRI-2 Irrigation Scheduling system.
Your role:
1. Explain the 7-day irrigation schedule calculated by the deterministic agricultural engine to farmers in simple, respectful, and clear language.
2. Explain exactly why irrigation is recommended or skipped on specific days, highlighting rainfall capture, crop stage needs, and water conservation.
3. NEVER calculate, alter, or invent new water numbers. The numbers provided to you are mathematically verified and MUST remain identical.
4. Provide the advisory in the requested language (English or Telugu) with actionable, practical tips for the farmer.
"""


def build_schedule_summary_text(schedule_result: Dict[str, Any]) -> str:
    """Formats schedule metrics into a clear text prompt for the LLM."""
    meta = schedule_result["metadata"]
    records = schedule_result["schedule_records"]

    lines = [
        f"Crop: {meta['crop']}",
        f"Growth Stage: {meta['growth_stage']}",
        f"Soil Type: {meta['soil_type']}",
        f"Field Area: {meta['field_area_val']} {meta['field_area_unit']}",
        f"Total Reference ETo: {schedule_result['total_eto_mm']} mm",
        f"Total Crop Demand ETc: {schedule_result['total_etc_mm']} mm",
        f"Total Rainfall: {schedule_result['total_rainfall_mm']} mm",
        f"Total Effective Rainfall Retained: {schedule_result['total_effective_rainfall_mm']} mm",
        f"Total Recommended Irrigation: {schedule_result['total_irrigation_recommended_mm']} mm ({schedule_result['total_irrigation_volume_litres']:,.0f} Litres)",
        f"Traditional Baseline Irrigation: {schedule_result['baseline_irrigation_mm']} mm ({schedule_result['baseline_irrigation_litres']:,.0f} Litres)",
        f"Water Saved: {schedule_result['water_savings_mm']} mm ({schedule_result['water_savings_litres']:,.0f} Litres, {schedule_result['water_savings_pct']}%)",
        "\nDay-by-Day Daily Log:"
    ]

    for r in records:
        lines.append(
            f"Day {r['day_number']} ({r['date']}): ETo={r['eto_mm']}mm, ETc={r['etc_mm']}mm, Rain={r['rainfall_mm']}mm (Eff: {r['effective_rainfall_mm']}mm), Decision={r['decision']}, Irrigate={r['recommended_irrigation_mm']}mm ({r['irrigation_volume_litres']:,.0f} Litres). Reason: {r['reason']}"
        )

    return "\n".join(lines)


def generate_fallback_advisory(schedule_result: Dict[str, Any], language: str = "English") -> str:
    """
    Deterministic rule-based fallback generator for English and Telugu.
    Ensures zero downtime and complete student reproducibility even without live API keys.
    """
    meta = schedule_result["metadata"]
    total_irr_mm = schedule_result["total_irrigation_recommended_mm"]
    total_irr_l = schedule_result["total_irrigation_volume_litres"]
    savings_pct = schedule_result["water_savings_pct"]
    savings_l = schedule_result["water_savings_litres"]
    crop = meta["crop"]
    stage = meta["growth_stage"]
    area_str = f"{meta['field_area_val']} {meta['field_area_unit']}"

    # Extract days where irrigation is recommended
    irr_days = [r for r in schedule_result["schedule_records"] if r["decision"] == "IRRIGATE"]
    skip_days = [r for r in schedule_result["schedule_records"] if r["decision"] == "SKIP"]

    if language.lower() == "telugu":
        # Professional, natural agricultural Telugu suitable for farmers
        crop_telugu_map = {
            "Rice": "వరి (Rice)",
            "Maize": "మొక్కజొన్న (Maize)",
            "Wheat": "గోధుమ (Wheat)",
            "Tomato": "టమాటా (Tomato)",
            "Cotton": "పత్తి (Cotton)",
            "Sugarcane": "చెరకు (Sugarcane)"
        }
        stage_telugu_map = {
            "Initial": "ప్రారంభ దశ (Initial)",
            "Development": "అభివృద్ధి దశ (Development)",
            "Mid-Season": "మధ్యంతర దశ (Mid-Season)",
            "Late-Season": "చివరి దశ (Late-Season)"
        }
        crop_display = crop_telugu_map.get(crop, crop)
        stage_display = stage_telugu_map.get(stage, stage)

        if len(irr_days) == 0:
            action_text = (
                "రాబోయే 7 రోజుల్లో నీటిపారుదల అవసరం లేదు. ఆశించిన వర్షపాతం మరియు ప్రస్తుత నేల తేమ "
                "పంట అవసరాలను సమృద్ధిగా తీరుస్తాయి."
            )
        else:
            dates_list = ", ".join([
                f"రోజు {r['day_number']} ({r['date']}: {r['recommended_irrigation_mm']} మి.మీ)"
                for r in irr_days
            ])
            action_text = (
                f"నీటిపారుదల సిఫార్సు చేయబడిన రోజులు: {dates_list}. "
                f"మొత్తం సిఫార్సు చేసిన నీటి పరిమాణం: {total_irr_mm} మి.మీ ({total_irr_l:,.0f} లీటర్లు)."
            )

        telugu_text = f"""### 🌾 AGRI-2 నీటిపారుదల సలహాదారు (తెలుగు)

**పంట & దశ:** {crop_display} ({stage_display}) | **పొలం విస్తీర్ణం:** {area_str}

1. **నీటిపారుదల ప్రణాళిక సారాంశం (Irrigation Schedule Summary):**
   - {action_text}
   - సరిపడా నేల తేమ నిల్వ మరియు వర్షపాతం కారణంగా 7 రోజుల్లో **{len(skip_days)} రోజులు** నీటిపారుదల నిలిపివేయవచ్చు (Skip).

2. **నీటి పొదుపు మరియు వ్యవసాయ ప్రయోజనాలు (Water Conservation & Agronomic Impact):**
   - సాంప్రదాయ పద్ధతి కంటే **{savings_pct}% నీటి పొదుపు** ({savings_l:,.0f} లీటర్లు ఆదా) సాధించబడింది.
   - పంట నీటి ఎద్దడికి గురికాకుండా కాపాడుతూ, అనవసరమైన పంపింగ్ మరియు నేల ముంపు సమస్యలను అరికడుతుంది.

3. **రైతుకు ముఖ్యమైన సూచనలు (Farmer Action Instructions):**
   - ఈ సలహా రైతు ఆమోదం తర్వాతే అమలు చేయాలి. వాల్వ్ లేదా మోటారు పంపు ఆపరేషన్ మానవీయంగా (చేతితో) మాత్రమే నిర్వహించాలి.
   - పొలం గట్లను పటిష్టంగా ఉంచండి, తద్వారా వర్షపు నీరు పొలంలోనే నిలిచి వృథా కాకుండా భూమిలోకి ఇంకుతుంది."""
        return telugu_text.strip()

    else:
        # Standard English Advisory
        if len(irr_days) == 0:
            action_text = "No irrigation required for the next 7 days. Expected rainfall and soil storage will adequately meet crop water demand."
        else:
            dates_list = ", ".join([f"Day {r['day_number']} ({r['date']}: {r['recommended_irrigation_mm']} mm)" for r in irr_days])
            action_text = f"Irrigation recommended on: {dates_list}. Total application: {total_irr_mm} mm ({total_irr_l:,.0f} Litres)."

        eng_text = f"""### 🌾 AGRI-2 Irrigation Advisory (English)

**Crop & Growth Stage:** {crop} ({stage}) | **Field Area:** {area_str}

1. **Irrigation Schedule Summary:**
   - {action_text}
   - Irrigation skipped on {len(skip_days)} of 7 days due to adequate water storage and rainfall capture.

2. **Water Conservation & Agronomic Impact:**
   - Achieves a **{savings_pct}% water reduction** ({savings_l:,.0f} Litres saved) compared to the traditional fixed-interval baseline.
   - Prevents crop water stress while eliminating unnecessary pumping and field saturation.

3. **Farmer Action Instructions:**
   - This advisory requires human approval. Actual valve and pump operation must be carried out manually.
   - Maintain paddy field bunds intact to retain incoming rainfall and prevent runoff."""
        return eng_text.strip()


def generate_farmer_advisory(
    schedule_result: Dict[str, Any],
    nexus_client: Optional[NexusClient] = None
) -> Dict[str, Any]:
    """
    Generates bilingual farmer advisories in English and Telugu.
    Uses the Nexus AI API when available; gracefully falls back to deterministic rule-based
    generators when API keys are absent or unreachable.

    Returns:
        dict:
            - english_advisory: str
            - telugu_advisory: str
            - source: "Nexus AI (gpt-5-nano)" or "AGRI-2 Agronomic Rule Engine (Fallback)"
            - error: Optional error string if API failed
    """
    client = nexus_client or NexusClient()
    summary_text = build_schedule_summary_text(schedule_result)

    if not client.is_configured():
        eng_adv = generate_fallback_advisory(schedule_result, "English")
        tel_adv = generate_fallback_advisory(schedule_result, "Telugu")
        return {
            "english_advisory": eng_adv,
            "telugu_advisory": tel_adv,
            "source": "AGRI-2 Agronomic Rule Engine (Fallback)",
            "api_status": "OFFLINE_FALLBACK",
            "error": "Nexus API key not configured. Using high-precision deterministic template."
        }

    # Prompt for English Advisory
    eng_prompt = f"""Review the following 7-day irrigation schedule computed by our FAO-56 agricultural engine:
{summary_text}

Provide a concise, practical, 3-section farmer advisory in English:
1. Schedule Summary (When to irrigate, when to skip, exact liters).
2. Agronomic Justification (Why irrigation was recommended or skipped, rainfall impact).
3. Farmer Action Steps (Remind manual approval and valve operation).
Keep all computed numbers EXACTLY as provided."""

    eng_res = client.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": eng_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    # Prompt for Telugu Advisory
    tel_prompt = f"""Review the following 7-day irrigation schedule computed by our FAO-56 agricultural engine:
{summary_text}

Provide an authentic, respectful agricultural advisory in Telugu (తెలుగు) for the farmer:
1. నీటిపారుదల నిర్ణయ సారాంశం (ఎప్పుడు నీరు పెట్టాలి, ఎప్పుడు అవసరం లేదు, లీటర్ల పరిమాణం).
2. వ్యవసాయ శాస్త్రీయ వివరణ (వర్షపాతం సద్వినియోగం, నీటి పొదుపు ప్రాముఖ్యత).
3. రైతు చేపట్టవలసిన చర్యలు (చేతితో వాల్వ్ ఆపరేషన్, మానవ ఆమోదం).
Keep all computed numbers EXACTLY as provided."""

    tel_res = client.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": tel_prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    # Validate non-empty content
    eng_content = eng_res.get("content", "").strip() if eng_res["success"] else ""
    tel_content = tel_res.get("content", "").strip() if tel_res["success"] else ""

    if eng_content and tel_content:
        return {
            "english_advisory": eng_content,
            "telugu_advisory": tel_content,
            "source": f"Nexus AI ({client.model})",
            "api_status": "ONLINE",
            "error": None
        }
    else:
        # Fallback if any call failed or returned empty content
        err_msg = eng_res.get("error_message") or tel_res.get("error_message") or "Model returned empty content"
        eng_adv = eng_content if eng_content else generate_fallback_advisory(schedule_result, "English")
        tel_adv = tel_content if tel_content else generate_fallback_advisory(schedule_result, "Telugu")
        return {
            "english_advisory": eng_adv,
            "telugu_advisory": tel_adv,
            "source": "AGRI-2 Agronomic Rule Engine (Fallback)",
            "api_status": "API_ERROR_FALLBACK",
            "error": err_msg
        }
