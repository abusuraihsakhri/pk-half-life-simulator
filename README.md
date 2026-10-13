# PK Half-Life Simulator

A deterministic, one-compartment intravenous bolus pharmacokinetic simulator for research and teaching. The browser app calculates locally and does not require a backend.

## Features

- Single IV bolus or repeated doses at a fixed interval.
- Concentration–time curve, elimination rate constant, derived clearance, initial concentration, and single-dose AUC to infinity.
- AUC over a selected simulation horizon; theoretical steady-state peak, trough, and accumulation factor for repeat dosing.
- CSV export of sampled concentration and cumulative exposure.
- A reference Python implementation in `pk_model.py` plus independent analytical tests.
- Retained legacy clinical utility functions (`pk_sim.py`) and experimental audit-agent CLI/API.

**Educational use only.** The PK model assumes instantaneous distribution into one homogeneous compartment, first-order linear elimination, and constant volume/clearance. It does not represent absorption, distribution phases, interpatient variability, organ dysfunction, drug interactions, or therapeutic/toxic concentrations. It must not be used to prescribe or adjust patient medication.

## Browser application

The `web/` directory contains a dependency-free HTML/CSS/JavaScript application suitable for static hosting, including GitHub Pages. No account, API key, Pyodide, or server is required. All entered parameters remain in browser memory and are not transmitted or stored by the app. The standalone application does not load third-party scripts.

To run locally from the repository root:

```bash
python -m http.server 8000 -d web
# Open http://localhost:8000/
```

Enter dose (mg), volume of distribution (L), half-life (hours), simulation duration (hours), and optionally the repeat-dose interval (hours). Clear the interval field for a single dose. Press **Calculate** and optionally **Export CSV**.

Concentrations on an administration boundary represent the instant *after* dosing. The steady-state peak/trough figures assume indefinitely repeated boluses and are not the same as finite-horizon values. The reported AUC∞ is for **one dose**; the horizon AUC includes all doses during the simulated period.

## Python

Requires Python 3.10+.

```bash
python -m pip install -e '.[dev]'
python -m pytest -q

# The new PK CLI
python cli.py pk --dose 500 --volume 40 --half-life 6 --hours 48 --interval 12

# Direct reference model
python - <<'PY'
from pk_model import simulate_iv_bolus
print(simulate_iv_bolus(500, 40, 6, horizon_h=48, interval_h=12)['summary'])
PY

# Existing legacy QTc utility
python pk_sim.py single --qt 420 --hr 70
```

### Optional backend

The existing audit-agent CLI/FastAPI system is retained for compatibility. Configure a private `AUDIT_SECRET_KEY` before importing or starting those modules (see `.env.example`). A key can be generated with `python -c "import secrets; print(secrets.token_hex(32))"`. Never commit it or embed it in browser code.

```bash
python cli.py serve
# POST /api/pk/simulate — deterministic PK model
# GET /health — service status
# Existing /api/audit, /api/chat, /api/audit/logs, /metrics also remain
```

The audit subsystem's mock provider is **not** a clinical language-model service. Its regex identifier screen is **not** comprehensive PHI detection or guaranteed HIPAA de-identification. Its HMAC audit chain is in memory, not an immutable/persistent audit store. Legacy clinical scoring routines should be independently reviewed before any medical application; for example `calculate_bmi_z` computes adult-category BMI, not a validated age/sex-based z-score.

## Tests, deployment, compatibility

GitHub Actions runs the Python test suite on 3.10–3.12, a signing-key-isolated module check, and Node.js tests for the independent browser model. The Pages workflow publishes `web/` when GitHub Pages is configured for GitHub Actions deployments. The browser code uses standard ES modules; modern Chrome, Firefox, Safari, and Edge are intended. JavaScript must be enabled.

For Docker, `docker compose up --build` starts the **backend**, not the static GitHub Pages app. Docker requires a private `AUDIT_SECRET_KEY` in the environment.

## License

MIT — see [LICENSE](LICENSE).
