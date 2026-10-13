"""
Automated Pytest Test Suite for Pk Half Life Simulator.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import sys
import os
from pathlib import Path

# Set a test secret key before importing agents
os.environ.setdefault("AUDIT_SECRET_KEY", "test-secret-key-for-unit-tests-only")

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main
from pk_sim import (
    calculate_score,
    calculate_meld_na,
    calculate_qtc,
    calculate_bmi_z,
    convert_hba1c,
    calculate_apri_fib4,
    assess_row,
    process_csv,
)
import tempfile


# =============================================================================
# Core PK Simulator Tests
# =============================================================================

def test_calculate_score_basic():
    result = calculate_score(value=10)
    assert isinstance(result, dict)
    assert "score" in result
    assert "inputs" in result
    assert result["inputs"] == 10 or result["inputs"] >= 1


def test_calculate_score_multiple_values():
    result = calculate_score(a=5, b=10, c=15)
    assert result["score"] > 0
    assert result["inputs"] == 3


def test_calculate_score_empty():
    result = calculate_score()
    assert result["score"] > 0
    assert result["inputs"] == 1


# =============================================================================
# MELD-Na Score Tests
# =============================================================================

def test_meld_na_basic():
    result = calculate_meld_na(bilirubin=1.2, creatinine=0.9, inr=1.1)
    assert result["score_type"] == "MELD"
    assert 6 <= result["score"] <= 40


def test_meld_na_with_sodium():
    result = calculate_meld_na(bilirubin=3.0, creatinine=1.5, inr=1.8, sodium=130)
    assert result["score_type"] == "MELD-Na"
    assert 6 <= result["score"] <= 40
    assert "risk_category" in result


def test_meld_na_high_values():
    result = calculate_meld_na(bilirubin=20.0, creatinine=4.0, inr=3.0, sodium=125)
    assert result["risk_category"] == "HIGH"


def test_meld_na_dialysis():
    result = calculate_meld_na(bilirubin=1.0, creatinine=1.0, inr=1.0, dialysis=True)
    # With dialysis, creatinine should be at least 4.0
    assert result["score"] >= 6


# =============================================================================
# QTc Calculation Tests
# =============================================================================

def test_qtc_bazett_basic():
    result = calculate_qtc(qt_ms=400, hr_bpm=60)
    assert result["score_type"] == "QTc (Bazett)"
    assert result["risk_category"] in ["NORMAL", "BORDERLINE", "PROLONGED"]
    assert result["qtc_ms"] > 0


def test_qtc_with_rr():
    result = calculate_qtc(qt_ms=400, rr_ms=1000)
    assert result["rr_s"] == 1.0


def test_qtc_fridericia():
    result = calculate_qtc(qt_ms=400, hr_bpm=60, method="fridericia")
    assert result["score_type"] == "QTc (Fridericia)"


def test_qtc_prolonged():
    result = calculate_qtc(qt_ms=550, hr_bpm=60)
    assert result["risk_category"] == "PROLONGED"


def test_qtc_invalid_input():
    result = calculate_qtc(qt_ms=-100)
    assert "error" in result


def test_qtc_no_rr_or_hr():
    result = calculate_qtc(qt_ms=400)
    assert "error" in result


# =============================================================================
# BMI Calculation Tests
# =============================================================================

def test_bmi_normal():
    result = calculate_bmi_z(weight_kg=70, height_cm=175)
    assert result["score_type"] == "BMI"
    assert 22 <= result["bmi"] <= 23  # 70 / (1.75^2) = 22.86
    assert result["category"] == "NORMAL"


def test_bmi_underweight():
    result = calculate_bmi_z(weight_kg=50, height_cm=180)
    assert result["category"] == "UNDERWEIGHT"


def test_bmi_obese():
    result = calculate_bmi_z(weight_kg=120, height_cm=175)
    assert result["category"] == "OBESE"


def test_bmi_invalid():
    result = calculate_bmi_z(weight_kg=-10, height_cm=175)
    assert "error" in result


# =============================================================================
# HbA1c Conversion Tests
# =============================================================================

def test_hba1c_to_eag():
    result = convert_hba1c(hba1c_percent=7.0)
    assert result["score_type"] == "HbA1c to eAG"
    assert result["eag_mgdl"] > 0
    assert result["category"] == "DIABETIC"


def test_eag_to_hba1c():
    result = convert_hba1c(eag_mgdl=154.0)
    assert result["score_type"] == "eAG to HbA1c"
    assert result["hba1c_percent"] > 0


def test_hba1c_normal():
    result = convert_hba1c(hba1c_percent=5.5)
    assert result["category"] == "NORMAL"


def test_hba1c_prediabetic():
    result = convert_hba1c(hba1c_percent=6.0)
    assert result["category"] == "PREDIABETIC"


def test_hba1c_invalid():
    result = convert_hba1c(hba1c_percent=-5)
    assert "error" in result


# =============================================================================
# APRI/FIB-4 Tests
# =============================================================================

def test_apri_basic():
    result = calculate_apri_fib4(ast_u_l=80, alt_u_l=60, platelets_109=200, age_years=45)
    assert "apri" in result
    assert result["apri"] > 0


def test_fib4_calculation():
    result = calculate_apri_fib4(ast_u_l=100, alt_u_l=80, platelets_109=150, age_years=55)
    assert "fib4" in result
    assert result["fib4"] > 0


def test_apri_fib4_insufficient_data():
    result = calculate_apri_fib4(ast_u_l=50)
    assert "error" in result


# =============================================================================
# assess_row Tests
# =============================================================================

def test_assess_row_meld():
    result = assess_row({"bilirubin": 2.0, "creatinine": 1.2, "inr": 1.5})
    assert result["score_type"] in ["MELD", "MELD-Na"]


def test_assess_row_qtc():
    result = assess_row({"qt_ms": 420, "hr_bpm": 70})
    assert "QTc" in result["score_type"]


def test_assess_row_bmi():
    result = assess_row({"weight_kg": 70, "height_cm": 175})
    assert result["score_type"] == "BMI"


def test_assess_row_hba1c():
    result = assess_row({"hba1c_percent": 6.5})
    assert "HbA1c" in result["score_type"]


def test_assess_row_apri():
    result = assess_row({"ast_u_l": 80, "alt_u_l": 60, "platelets_109": 200})
    assert "apri" in result


def test_assess_row_generic():
    result = assess_row({"value": 10, "qty": 2})
    assert "score" in result


# =============================================================================
# CSV Processing Tests
# =============================================================================

def test_process_csv():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write("bilirubin,creatinine,inr\n1.5,1.0,1.2\n3.0,2.0,1.8\n")
        input_path = f.name

    output_path = input_path + ".out.csv"

    try:
        results = process_csv(input_path, output_path)
        assert len(results) == 2
        # MELD results have 'score_type' key
        assert all("score_type" in r for r in results)

        with open(output_path, 'r') as f:
            content = f.read()
            assert "bilirubin" in content
    finally:
        os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


# =============================================================================
# PHI Guard & Security Tests
# =============================================================================

def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_redaction():
    result = PHIGuard.redact_phi("Patient John Doe, MRN-12345")
    assert "REDACTED_IDENTIFIER" in result


def test_phi_guard_ssn():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("SSN: 123-45-6789")


def test_phi_guard_phone():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Contact: (555) 123-4567")


def test_phi_guard_email():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Email: patient@example.com")


# =============================================================================
# Audit Trail Tests
# =============================================================================

def test_audit_trail_creation():
    trail = AuditTrail(secret_key="test-key-12345")
    entry = trail.log("test_actor", "test_tier", "TEST_EVENT", {"detail": "value"})
    assert entry["audit_id"].startswith("AUDIT-")
    assert entry["current_hash"] != ""


def test_audit_trail_integrity():
    trail = AuditTrail(secret_key="test-key-12345")
    trail.log("actor1", "tier1", "EVENT1", {"a": 1})
    trail.log("actor2", "tier2", "EVENT2", {"b": 2})
    assert trail.verify_integrity() is True


def test_audit_trail_tamper_detection():
    trail = AuditTrail(secret_key="test-key-12345")
    trail.log("actor1", "tier1", "EVENT1", {"a": 1})
    trail.log("actor2", "tier2", "EVENT2", {"b": 2})

    # Tamper with the prev_hash of the second entry to break the chain
    trail.logs[1]["prev_hash"] = "tampered_hash_value"
    assert trail.verify_integrity() is False


def test_audit_trail_requires_secret():
    # Ensure no default fallback
    os.environ.pop("AUDIT_SECRET_KEY", None)
    with pytest.raises(RuntimeError):
        AuditTrail()


# =============================================================================
# Worker Tests
# =============================================================================

def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_worker_no_alerts_nominal():
    p = SystemTaskPayload(task_id="T-NOMINAL", target_identifier="KEY-01", primary_metric=15.0, status_descriptor="NOMINAL")
    assert len(InvariantQCWorker.evaluate(p)) == 0
    assert len(SafetyEscalationWorker.evaluate(p)) == 0
    assert len(ProtocolConformanceWorker.evaluate(p)) == 0


# =============================================================================
# Supervisor Tests
# =============================================================================

def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True


def test_supervisor_elevated_risk():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-ELEVATED",
        target_identifier="KEY-02",
        primary_metric=35.0,  # > 25 threshold
        secondary_metric=5.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ELEVATED


def test_supervisor_critical():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-CRITICAL",
        target_identifier="KEY-03",
        primary_metric=15.0,
        secondary_metric=15.0,
        is_critical_flag=True
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.CRITICAL_STAT


# =============================================================================
# CLI Tests
# =============================================================================

def test_cli_audit():
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0


def test_cli_chat():
    assert main(["chat", "Explain", "specifications"]) == 0


def test_cli_verify_audit():
    assert main(["verify-audit"]) == 0


def test_cli_single_meld():
    from pk_sim import main as pk_main
    assert pk_main(["single", "--bili", "2.0", "--creat", "1.2", "--inr", "1.5"]) == 0


def test_cli_single_qtc():
    from pk_sim import main as pk_main
    assert pk_main(["single", "--qt", "420", "--hr", "70"]) == 0


def test_cli_single_json():
    from pk_sim import main as pk_main
    assert pk_main(["single", "--json", '{"bilirubin": 2.0, "creatinine": 1.2}']) == 0


def test_cli_batch_missing_file():
    from pk_sim import main as pk_main
    result = pk_main(["batch", "--input", "nonexistent.csv", "--output", "out.csv"])
    assert result == 1  # Should fail gracefully


# =============================================================================
# Integration Tests
# =============================================================================

def test_end_to_end_workflow():
    """Test a complete workflow from input to output."""
    supervisor = SystemSupervisor(model_provider="mock")

    # Process multiple tasks
    for i in range(5):
        payload = SystemTaskPayload(
            task_id=f"INTEGRATION-{i:03d}",
            target_identifier=f"KEY-{i:03d}",
            primary_metric=10.0 + i * 5,
            secondary_metric=5.0 + i * 2,
            status_descriptor="NOMINAL"
        )
        dossier = supervisor.process_task(payload)
        assert dossier.overall_urgency in [UrgencyLevel.ROUTINE, UrgencyLevel.ELEVATED, UrgencyLevel.CRITICAL_STAT]

    # Verify all audit entries are valid
    assert AuditLogger.verify_integrity() is True
    assert len(AuditLogger.get_trail()) >= 5


def test_phi_blocking_in_supervisor():
    """Test that PHI-containing inputs are blocked by supervisor."""
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PHI-TEST",
        target_identifier="MRN-12345",  # Contains PHI pattern
        primary_metric=10.0
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)


def test_audit_trail_detects_modified_signed_fields():
    trail = AuditTrail(secret_key="test-signing-key-only")
    entry = trail.log("tester", "unit", "TEST_EVENT", {"ok": True})
    entry["event_type"] = "ALTERED"
    assert trail.verify_integrity() is False


def test_new_pk_cli(capsys):
    assert main(["pk", "--dose", "500", "--volume", "40", "--half-life", "6", "--hours", "12", "--points", "3"]) == 0
    import json
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["initial_concentration_mg_l"] == 12.5
    assert len(result["series"]) == 3
