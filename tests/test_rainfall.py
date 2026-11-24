"""
Unit tests for Effective Rainfall calculation methods.
"""

import pytest
from src.rainfall import (
    usda_scs_effective_rainfall,
    fao_aglw_effective_rainfall,
    paddy_bund_effective_rainfall,
    calculate_effective_rainfall
)


def test_usda_scs_effective_rainfall():
    """Test USDA-SCS daily effective rainfall."""
    # Negligible rainfall <= 3mm is 0
    assert usda_scs_effective_rainfall(2.0) == 0.0

    # Moderate rainfall (25mm)
    peff_25 = usda_scs_effective_rainfall(25.0)
    assert 18.0 <= peff_25 <= 25.0

    # Heavy rainfall (60mm)
    peff_60 = usda_scs_effective_rainfall(60.0)
    assert 40.0 <= peff_60 <= 60.0


def test_paddy_bund_effective_rainfall():
    """
    Test Paddy Bund Freeboard Storage Model:
    Bund height: 80 mm
    Current ponded depth: 30 mm
    Available freeboard: 50 mm
    """
    # Event 1: Rain of 35 mm (within freeboard of 50mm) -> 100% retained, 0 runoff
    res1 = paddy_bund_effective_rainfall(rainfall_mm=35.0, current_ponded_depth_mm=30.0, bund_height_mm=80.0)
    assert res1["effective_rainfall_mm"] == 35.0
    assert res1["runoff_mm"] == 0.0

    # Event 2: Rain of 70 mm (exceeds freeboard of 50mm) -> 50mm retained, 20mm overflow runoff
    res2 = paddy_bund_effective_rainfall(rainfall_mm=70.0, current_ponded_depth_mm=30.0, bund_height_mm=80.0)
    assert res2["effective_rainfall_mm"] == 50.0
    assert res2["runoff_mm"] == 20.0


def test_calculate_effective_rainfall_dispatcher():
    """Test auto-dispatch between rice and upland."""
    res_rice = calculate_effective_rainfall(rainfall_mm=40.0, crop_name="Rice", current_ponded_depth_mm=20.0, bund_height_mm=80.0)
    assert "Paddy Bund" in res_rice["method"]
    assert res_rice["effective_rainfall_mm"] == 40.0

    res_maize = calculate_effective_rainfall(rainfall_mm=40.0, crop_name="Maize", cultivation_type="upland")
    assert "USDA-SCS" in res_maize["method"]
    assert res_maize["effective_rainfall_mm"] < 40.0
