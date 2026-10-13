"""Analytical reference tests for one-compartment IV bolus pharmacokinetics."""
import math
import pytest

from pk_model import simulate_iv_bolus


def test_single_bolus_half_life_and_auc():
    result = simulate_iv_bolus(500, 40, 6, horizon_h=12, points=3)
    assert result["series"][0]["concentration_mg_l"] == 12.5
    assert result["series"][1]["concentration_mg_l"] == pytest.approx(6.25)
    assert result["series"][2]["concentration_mg_l"] == pytest.approx(3.125)
    assert result["summary"]["clearance_l_h"] == pytest.approx(math.log(2) * 40 / 6)
    assert result["summary"]["single_dose_auc_infinity_mg_h_l"] == pytest.approx(500 / (math.log(2) * 40 / 6))
    assert result["summary"]["auc_to_horizon_mg_h_l"] == pytest.approx(result["summary"]["single_dose_auc_infinity_mg_h_l"] * 0.75)


def test_repeated_bolus_peak_trough_and_auc():
    result = simulate_iv_bolus(100, 20, 6, horizon_h=12, interval_h=6, points=3)
    assert [r["concentration_mg_l"] for r in result["series"]] == pytest.approx([5, 7.5, 8.75])
    assert result["summary"]["accumulation_ratio"] == pytest.approx(2)
    assert result["summary"]["steady_state_peak_mg_l"] == pytest.approx(10)
    assert result["summary"]["steady_state_trough_mg_l"] == pytest.approx(5)
    assert result["summary"]["number_of_doses"] == 3
    # Third bolus occurs at t=12 and contributes no AUC within the horizon.
    assert result["summary"]["auc_to_horizon_mg_h_l"] == pytest.approx((5 / (math.log(2)/6)) * 1.25)


def test_simulator_boundary_inputs():
    for arg in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            simulate_iv_bolus(arg, 40, 6)
    with pytest.raises(ValueError):
        simulate_iv_bolus(100, 20, 6, interval_h=0)
    with pytest.raises(ValueError):
        simulate_iv_bolus(100, 20, 6, horizon_h=1e6, interval_h=0.01)
    with pytest.raises(ValueError):
        simulate_iv_bolus(100, 20, 6, points=1)


def test_auc_monotonic_and_nonnegative():
    x = simulate_iv_bolus(250, 25, 4, horizon_h=31, interval_h=8, points=511)
    values = [p["auc_mg_h_l"] for p in x["series"]]
    assert values[0] == pytest.approx(0)
    assert all(b >= a - 1e-9 for a, b in zip(values, values[1:]))
    assert all(p["concentration_mg_l"] >= 0 for p in x["series"])
