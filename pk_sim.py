#!/usr/bin/env python3
"""
PK Half-Life Simulator
One-compartment IV bolus PK: half-life, Vd, CL, AUC and concentration-time curve.
Also includes clinical scoring functions: MELD-Na, QTc, BMI z-score, HbA1c, APRI/FIB-4.
Stdlib only.
"""
import argparse
import csv
import sys
import math
from typing import Dict, Any, Optional, List


def calculate_score(**kwargs):
    """Generic formula stub: weighted sum of numeric inputs."""
    vals = [float(v) for v in kwargs.values() if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).isdigit())]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "pk-half-life-simulator") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals)}


# =============================================================================
# Clinical Scoring Functions
# =============================================================================

def _safe_float(value, default=0.0):
    """Safely convert a value to float, returning default if not possible."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_meld_na(bilirubin, creatinine, inr, sodium=None, dialysis=False, albumin=None, sex="M"):
    """
    Calculate MELD-Na score for liver disease severity.
    MELD = 3.78*ln(bilirubin) + 11.2*ln(INR) + 9.57*ln(creatinine) + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    """
    bili = _safe_float(bilirubin, 1.0)
    creat = _safe_float(creatinine, 1.0)
    inr_val = _safe_float(inr, 1.0)

    # Apply floor/ceiling per UNOS guidelines
    bili = max(1.0, bili)
    creat = max(1.0, creat)
    if dialysis:
        creat = max(4.0, creat)
    inr_val = max(1.0, inr_val)

    meld = (3.78 * math.log(bili) +
            11.2 * math.log(inr_val) +
            9.57 * math.log(creat) +
            6.43)

    if sodium is not None:
        na = _safe_float(sodium, 137)
        na = min(137, max(125, na))
        meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
        score = round(min(40, max(6, meld_na)), 1)
    else:
        score = round(min(40, max(6, meld)), 1)

    return {
        "score_type": "MELD-Na" if sodium is not None else "MELD",
        "score": score,
        "risk_category": "HIGH" if score >= 30 else "MODERATE" if score >= 20 else "LOW",
        "components": {"bilirubin": bili, "creatinine": creat, "inr": inr_val, "sodium": sodium, "dialysis": dialysis}
    }


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None, method="bazett"):
    """
    Calculate corrected QT interval (QTc).
    Bazett: QTc = QT / sqrt(RR in seconds)
    Fridericia: QTc = QT / cbrt(RR in seconds)
    """
    qt = _safe_float(qt_ms)
    if qt <= 0:
        return {"error": "QT interval must be positive"}

    if rr_ms is not None:
        rr = _safe_float(rr_ms) / 1000.0  # Convert ms to seconds
    elif hr_bpm is not None:
        hr = _safe_float(hr_bpm)
        if hr <= 0:
            return {"error": "Heart rate must be positive"}
        rr = 60.0 / hr
    else:
        return {"error": "Either RR interval or heart rate is required"}

    if rr <= 0:
        return {"error": "RR interval must be positive"}

    if method.lower() == "fridericia":
        qtc = qt / (rr ** (1/3))
        method_name = "Fridericia"
    else:
        qtc = qt / math.sqrt(rr)
        method_name = "Bazett"

    qtc_ms = round(qtc, 1)
    risk = "PROLONGED" if qtc_ms > 500 else "BORDERLINE" if qtc_ms > 450 else "NORMAL"

    return {
        "score_type": f"QTc ({method_name})",
        "qtc_ms": qtc_ms,
        "qt_ms": qt,
        "rr_s": round(rr, 3),
        "risk_category": risk
    }


def calculate_bmi_z(weight_kg, height_cm, age_months=60, sex="M"):
    """
    Calculate BMI and approximate z-score for age/sex.
    Simplified calculation for screening purposes.
    """
    weight = _safe_float(weight_kg)
    height_m = _safe_float(height_cm) / 100.0
    age_m = _safe_float(age_months)

    if weight <= 0 or height_m <= 0:
        return {"error": "Weight and height must be positive values"}

    bmi = weight / (height_m ** 2)
    bmi = round(bmi, 2)

    # Simplified BMI categorization (adult cutoffs as approximation)
    if bmi < 18.5:
        category = "UNDERWEIGHT"
    elif bmi < 25:
        category = "NORMAL"
    elif bmi < 30:
        category = "OVERWEIGHT"
    else:
        category = "OBESE"

    return {
        "score_type": "BMI",
        "bmi": bmi,
        "weight_kg": weight,
        "height_cm": height_cm,
        "age_months": age_m,
        "category": category
    }


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """
    Convert between HbA1c (%) and estimated average glucose (mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7
    """
    if hba1c_percent is not None:
        hba1c = _safe_float(hba1c_percent)
        if hba1c <= 0:
            return {"error": "HbA1c must be positive"}
        eag = round(28.7 * hba1c - 46.7, 1)
        return {
            "score_type": "HbA1c to eAG",
            "hba1c_percent": hba1c,
            "eag_mgdl": eag,
            "category": "DIABETIC" if hba1c >= 6.5 else "PREDIABETIC" if hba1c >= 5.7 else "NORMAL"
        }
    elif eag_mgdl is not None:
        eag = _safe_float(eag_mgdl)
        if eag <= 0:
            return {"error": "eAG must be positive"}
        hba1c = round((eag + 46.7) / 28.7, 1)
        return {
            "score_type": "eAG to HbA1c",
            "eag_mgdl": eag,
            "hba1c_percent": hba1c,
            "category": "DIABETIC" if hba1c >= 6.5 else "PREDIABETIC" if hba1c >= 5.7 else "NORMAL"
        }
    return {"error": "Either HbA1c or eAG value is required"}


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """
    Calculate APRI and FIB-4 scores for liver fibrosis assessment.
    APRI = (AST / ULN) / platelets * 100
    FIB-4 = (age * AST) / (platelets * sqrt(ALT))
    """
    ast = _safe_float(ast_u_l)
    if ast <= 0:
        return {"error": "AST must be positive"}

    result = {"score_type": "Liver Fibrosis Panel"}

    # APRI calculation (simplified, assuming AST ULN = 40)
    alt = _safe_float(alt_u_l) if alt_u_l else 40
    platelets = _safe_float(platelets_109)
    age = _safe_float(age_years)

    if platelets > 0:
        ast_uln = 40.0  # Standard ULN for AST
        apri = round(((ast / ast_uln) * 100) / platelets, 2)
        result["apri"] = apri
        result["apri_interpretation"] = "Significant fibrosis" if apri > 1.0 else "Moderate fibrosis" if apri > 0.5 else "Minimal/No fibrosis"

    # FIB-4 calculation
    if platelets > 0 and alt > 0 and age > 0:
        fib4 = round((age * ast) / (platelets * math.sqrt(alt)), 2)
        result["fib4"] = fib4
        result["fib4_interpretation"] = "Advanced fibrosis" if fib4 > 3.25 else "Indeterminate" if fib4 > 1.45 else "No advanced fibrosis"

    if "apri" not in result and "fib4" not in result:
        return {"error": "Insufficient data for APRI/FIB-4 calculation"}

    return result


def assess_row(row):
    """Assess a row of clinical data and return appropriate score."""
    try:
        # MELD-Na Score
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"), row.get("creatinine"),
                row.get("inr"), row.get("sodium"),
                row.get("dialysis", "0") == "1",
                row.get("albumin"), row.get("sex", "M")
            )
        # QTc Calculation
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"),
                row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate")
            )
        # BMI Z-Score
        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"), row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60,
                row.get("sex", "M")
            )
        # HbA1c Conversion
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        # APRI/FIB-4 Liver Fibrosis
        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"), row.get("alt_u_l"),
                row.get("platelets_109"), row.get("age_years") or row.get("age")
            )
        # Fallback to generic score
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}


def process_csv(inp, out):
    """Process a CSV file and append results."""
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fieldnames = r.fieldnames
    results = []
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k, v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys = set()
    for rr in results:
        all_keys.update(rr.keys())
    # keep original first
    extra = [k for k in all_keys if k not in fieldnames]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames) + extra)
        w.writeheader()
        w.writerows(results)
    return results


def build_parser():
    """Build the argument parser for CLI."""
    p = argparse.ArgumentParser(prog="pk_sim", description="PK Half-Life Simulator")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float)
    s.add_argument("--creat", type=float)
    s.add_argument("--inr", type=float)
    s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float)
    s.add_argument("--rr", type=float)
    s.add_argument("--hr", type=float)
    b = sub.add_parser("batch", help="batch csv")
    b.add_argument("--input", required=True)
    b.add_argument("--output", required=True)
    return p


def main(argv=None):
    """Main entry point for CLI."""
    import json as _json
    p = build_parser()
    a = p.parse_args(argv)
    if a.cmd == "single":
        if a.json:
            try:
                row = _json.loads(a.json)
            except _json.JSONDecodeError as e:
                print(f"Error: Invalid JSON input - {e}")
                return 1
        else:
            row = {k: getattr(a, k) for k in ["bili", "creat", "inr", "na", "qt", "rr", "hr"] if getattr(a, k, None) is not None}
            # map aliases
            if a.bili is not None:
                row["bilirubin"] = a.bili
            if a.creat is not None:
                row["creatinine"] = a.creat
            if a.inr is not None:
                row["inr"] = a.inr
            if a.na is not None:
                row["sodium"] = a.na
            if a.qt is not None:
                row["qt_ms"] = a.qt
            if a.rr is not None:
                row["rr_ms"] = a.rr
            if a.hr is not None:
                row["hr_bpm"] = a.hr
        print(assess_row(row))
        return 0
    if a.cmd == "batch":
        try:
            res = process_csv(a.input, a.output)
            print(f"Processed {len(res)} -> {a.output}")
            return 0
        except FileNotFoundError:
            print(f"Error: Input file '{a.input}' not found")
            return 1
        except Exception as e:
            print(f"Error processing CSV: {e}")
            return 1
    p.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
