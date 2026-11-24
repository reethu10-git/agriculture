"""
Tests for Nexus API Integration, Error Handling, and Advisory Generation.
"""

import pytest
import pandas as pd
from src.nexus_client import NexusClient
from src.advisory_generator import (
    generate_farmer_advisory,
    generate_fallback_advisory,
    build_schedule_summary_text
)
from src.irrigation_scheduler import generate_irrigation_schedule


@pytest.fixture
def sample_schedule():
    df = pd.read_csv("data/sample/coimbatore_7day_weather.csv")
    return generate_irrigation_schedule(
        weather_df=df,
        crop_name="Rice",
        growth_stage="Development",
        soil_type="Loamy",
        field_area_val=1.0,
        field_area_unit="Acre"
    )


def test_missing_api_key_handling():
    """Verify that unconfigured API key does not crash and reports MISSING_API_KEY."""
    client = NexusClient(api_key="", base_url="https://nexusapi.navigatelabs.ai/v1")
    assert not client.is_configured()

    res = client.chat_completion([{"role": "user", "content": "Hello"}])
    assert not res["success"]
    assert res["error_type"] == "MISSING_API_KEY"
    assert "not configured" in res["error_message"].lower()


def test_whitespace_api_key_handling():
    """Verify that an API key containing only whitespace is treated as unconfigured."""
    client = NexusClient(api_key="   ", base_url="https://nexusapi.navigatelabs.ai/v1")
    assert not client.is_configured()

    res = client.chat_completion([{"role": "user", "content": "Hello"}])
    assert not res["success"]
    assert res["error_type"] == "MISSING_API_KEY"


def test_valid_api_key_configuration():
    """Verify that a valid non-empty API key with valid base URL returns True for is_configured()."""
    client = NexusClient(api_key="sk-test-valid-key-12345", base_url="https://nexusapi.navigatelabs.ai/v1")
    assert client.is_configured()


def test_fallback_advisory_bilingual(sample_schedule):
    """Verify high-quality deterministic fallback advisory generation in English and Telugu."""
    eng_adv = generate_fallback_advisory(sample_schedule, "English")
    tel_adv = generate_fallback_advisory(sample_schedule, "Telugu")

    # English checks
    assert "AGRI-2 Irrigation Advisory" in eng_adv
    assert "Rice" in eng_adv
    assert "water reduction" in eng_adv.lower()
    assert "manual" in eng_adv.lower()

    # Telugu checks
    assert "నీటిపారుదల సలహాదారు" in tel_adv
    assert "నీటి పొదుపు" in tel_adv
    assert "రైతుకు ముఖ్యమైన సూచనలు" in tel_adv
    assert "వరి" in tel_adv


def test_advisory_generator_resilience(sample_schedule):
    """Test generate_farmer_advisory with unconfigured client."""
    client = NexusClient(api_key="your_nexus_api_key_here")
    advisory = generate_farmer_advisory(sample_schedule, client)

    assert "english_advisory" in advisory
    assert "telugu_advisory" in advisory
    assert len(advisory["english_advisory"]) > 50
    assert len(advisory["telugu_advisory"]) > 50
    assert advisory["api_status"] in ["OFFLINE_FALLBACK", "API_ERROR_FALLBACK"]


def test_advisory_generator_empty_content_fallback(sample_schedule):
    """Verify that an empty content response from Nexus triggers deterministic fallback."""
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.is_configured.return_value = True
    mock_client.model = "gpt-5-nano"
    mock_client.chat_completion.return_value = {
        "success": True,
        "content": "",  # Empty response (e.g. reasoning tokens exhausted)
        "error_type": None,
        "error_message": None
    }

    advisory = generate_farmer_advisory(sample_schedule, mock_client)
    assert len(advisory["english_advisory"]) > 50
    assert len(advisory["telugu_advisory"]) > 50
    assert "AGRI-2 Irrigation Advisory" in advisory["english_advisory"]
    assert "నీటిపారుదల సలహాదారు" in advisory["telugu_advisory"]
    assert advisory["api_status"] == "API_ERROR_FALLBACK"
