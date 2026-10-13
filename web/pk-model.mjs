// Pure first-order IV bolus model. No network, storage, or clinical dosing advice.
export function simulatePk({ dose, volume, halfLife, horizon, interval = null, samples = 241 }) {
  const vals = { dose, volume, halfLife, horizon };
  for (const [name, val] of Object.entries(vals)) {
    if (typeof val !== 'number' || !Number.isFinite(val) || val <= 0) {
      throw new Error(name + ' must be a finite positive number.');
    }
  }
  if (interval !== null && (typeof interval !== 'number' || !Number.isFinite(interval) || interval <= 0)) {
    throw new Error('Dosing interval must be a finite positive number.');
  }
  if (!Number.isInteger(samples) || samples < 2 || samples > 2001) {
    throw new Error('Sample count must be between 2 and 2001.');
  }
  if (horizon > 1e6 || (interval !== null && horizon / interval > 100000)) {
    throw new Error('Simulation horizon or dose count is too large.');
  }
  const k = Math.LN2 / halfLife;
  const clearance = k * volume;
  const c0 = dose / volume;
  const aucInf = dose / clearance;
  const accumulated = interval === null ? 1 : 1 / (-Math.expm1(-k * interval));
  const q = interval === null ? null : Math.exp(-k * interval);
  function at(t) {
    if (interval === null) {
      const e = Math.exp(-k * t);
      return { time: t, concentration: c0 * e, auc: aucInf * (-Math.expm1(-k * t)) };
    }
    const n = Math.floor(t / interval + 1e-12);
    const dt = Math.max(0, t - n * interval);
    const geometric = (-Math.expm1(-(n + 1) * k * interval)) / (-Math.expm1(-k * interval));
    const concentration = c0 * Math.exp(-k * dt) * geometric;
    const auc = Math.max(0, aucInf * (n + 1 - Math.exp(-k * dt) * geometric));
    return { time: t, concentration, auc };
  }
  const points = Array.from({ length: samples }, (_, i) => at(horizon * i / (samples - 1)));
  // Add points immediately before each bolus so plotted peaks/troughs remain visible.
  if (interval !== null && Math.floor(horizon / interval) <= 500) {
    for (let n = 1; n * interval <= horizon; n++) {
      const t = n * interval;
      const prev = Math.max(0, t - Math.min(interval, horizon) * 1e-8);
      points.push(at(prev), at(t));
    }
    points.sort((a, b) => a.time - b.time);
  }
  const end = at(horizon);
  return {
    summary: {
      k, clearance, c0, aucInf,
      accumulation: accumulated,
      peak: interval === null ? null : c0 * accumulated,
      trough: interval === null ? null : c0 * accumulated * q,
      endConcentration: end.concentration,
      horizonAuc: end.auc,
      doses: interval === null ? 1 : Math.floor(horizon / interval + 1e-12) + 1
    },
    points
  };
}
