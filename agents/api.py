"""
FastAPI REST API Server for Pk Half Life Simulator.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pk_model import simulate_iv_bolus
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Pk Half Life Simulator API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "pk-half-life-simulator", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


class PKSimulationRequest(BaseModel):
    dose_mg: float = Field(gt=0, allow_inf_nan=False)
    volume_l: float = Field(gt=0, allow_inf_nan=False)
    half_life_h: float = Field(gt=0, allow_inf_nan=False)
    horizon_h: float = Field(default=48.0, gt=0, le=1e6, allow_inf_nan=False)
    interval_h: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    points: int = Field(default=241, ge=2, le=2001)


@app.post("/api/pk/simulate")
def api_pk_simulate(request: PKSimulationRequest):
    """Analytical educational one-compartment IV bolus simulation."""
    try:
        return simulate_iv_bolus(**request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
