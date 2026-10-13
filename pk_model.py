"""Deterministic one-compartment IV-bolus pharmacokinetic simulation.

Educational/research model: instantaneous distribution, first-order elimination,
constant volume/clearance, complete systemic availability, doses at t=0 and
successive integer multiples of the dosing interval.
"""
from __future__ import annotations

import math


def simulate_iv_bolus(
    dose_mg: float,
    volume_l: float,
    half_life_h: float,
    horizon_h: float = 48.0,
    interval_h: float | None = None,
    points: int = 241,
) -> dict:
    """Return model parameters and a sampled concentration/exposure time series.

    A scheduled dose at the horizon is included (right-continuous C(t)).
    For repeated doses, AUC is integrated from t=0 to the horizon.
    """
    inputs = {"dose_mg": dose_mg, "volume_l": volume_l,
              "half_life_h": half_life_h, "horizon_h": horizon_h}
    for name, value in inputs.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")
    if interval_h is not None:
        if isinstance(interval_h, bool) or not isinstance(interval_h, (float, int)) or not math.isfinite(interval_h) or interval_h <= 0:
            raise ValueError("interval_h must be a finite positive number")
    if type(points) is not int or not 2 <= points <= 2001:
        raise ValueError("points must be an integer between 2 and 2001")
    if horizon_h > 1e6:
        raise ValueError("horizon_h exceeds the supported range")
    # This model must not be used to extrapolate excessive bolus histories.
    if interval_h is not None and horizon_h / interval_h > 100_000:
        raise ValueError("More than 100,000 doses exceed the supported range")

    k = math.log(2.0) / half_life_h
    clearance = k * volume_l
    c0 = dose_mg / volume_l
    dose_auc = dose_mg / clearance
    tau = interval_h
    decay_interval = math.exp(-k * tau) if tau is not None else None
    accumulation = 1.0 / (-math.expm1(-k * tau)) if tau is not None else 1.0

    def concentration_and_auc(t: float) -> tuple[float, float]:
        if tau is None:
            decay = math.exp(-k * t)
            return c0 * decay, dose_auc * (-math.expm1(-k * t))
        n = math.floor(t / tau + 1e-12)
        since_last = max(0.0, t - n * tau)
        total = -math.expm1(-(n + 1) * k * tau) / (-math.expm1(-k * tau))
        c = c0 * math.exp(-k * since_last) * total
        # Sum of integrals of each bolus, including the most recent bolus.
        auc = dose_auc * ((n + 1) - math.exp(-k * since_last) * total)
        return c, max(0.0, auc)

    series = []
    for i in range(points):
        t = horizon_h * i / (points - 1)
        c, auc = concentration_and_auc(t)
        series.append({"time_h": t, "concentration_mg_l": c, "auc_mg_h_l": auc})

    c_end, auc_end = concentration_and_auc(horizon_h)
    summary = {
        "elimination_rate_h_inv": k,
        "clearance_l_h": clearance,
        "initial_concentration_mg_l": c0,
        "single_dose_auc_infinity_mg_h_l": dose_auc,
        "concentration_at_horizon_mg_l": c_end,
        "auc_to_horizon_mg_h_l": auc_end,
        "accumulation_ratio": accumulation,
        "steady_state_peak_mg_l": c0 * accumulation if tau is not None else None,
        "steady_state_trough_mg_l": c0 * accumulation * decay_interval if tau is not None else None,
        "number_of_doses": (math.floor(horizon_h / tau + 1e-12) + 1) if tau is not None else 1,
    }
    return {"model": "one_compartment_iv_bolus", "inputs": {**inputs, "interval_h": tau},
            "summary": summary, "series": series}
