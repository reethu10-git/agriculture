"""
Unit tests for Crop Coefficients (Kc) and Crop Evapotranspiration (ETc).
"""

import pytest
from src.crop_coefficients import get_crop_coefficient, calculate_etc


def test_rice_kc_stages():
    """Verify standard FAO-56 Rice Kc stages."""
    kc_init = get_crop_coefficient("Rice", "Initial")
    assert kc_init["kc"] == 1.05
    assert "transplanting" in kc_init["description"].lower()

    kc_dev = get_crop_coefficient("Rice", "Development")
    assert kc_dev["kc"] == 1.15

    kc_mid = get_crop_coefficient("Rice", "Mid-Season", u2=2.0, rh_min=45.0)
    assert kc_mid["kc"] == 1.25

    kc_late = get_crop_coefficient("Rice", "Late-Season", u2=2.0, rh_min=45.0)
    assert kc_late["kc"] == 0.90


def test_kc_climatic_adjustment():
    """
    Test FAO-56 Eq. 62 climatic adjustment for mid-season under arid windy conditions:
    u2 = 4.0 m/s (higher than 2.0 m/s), RHmin = 20% (drier than 45%).
    Kc must increase.
    """
    kc_standard = get_crop_coefficient("Rice", "Mid-Season", u2=2.0, rh_min=45.0)
    kc_adjusted = get_crop_coefficient("Rice", "Mid-Season", u2=4.0, rh_min=20.0, crop_height_m=1.0)

    assert kc_adjusted["adjustment_applied"] is True
    assert kc_adjusted["kc"] > kc_standard["kc"]


def test_calculate_etc():
    """Test ETc = Kc * ETo."""
    eto = 4.5 # mm/day
    kc = 1.25
    etc = calculate_etc(eto, kc)
    assert etc == 5.62 or etc == 5.63 or abs(etc - 5.625) < 0.02
