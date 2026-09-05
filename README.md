# PK Half-Life Simulator

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

PK Half-Life Simulator is a clinical pharmacokinetics toolkit providing:

- **One-compartment IV bolus PK**: half-life, Vd, CL, AUC and concentration-time curve
- **Clinical scoring functions**: MELD-Na, QTc (Bazett/Fridericia), BMI z-score, HbA1c conversion, APRI/FIB-4
- **Multi-agent supervision system** with specialized workers for QC, safety, and protocol conformance
- **Zero-PHI outbound guard** protecting against HIPAA violations
- **HMAC-SHA256 tamper-evident audit trail** for all evaluations

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Clinical Scoring Functions

| Function | Description | Inputs |
|:---------|:------------|:-------|
| `calculate_meld_na()` | MELD/MELD-Na liver disease severity score | bilirubin, creatinine, INR, sodium, dialysis, albumin |
| `calculate_qtc()` | Corrected QT interval (Bazett or Fridericia) | QT, RR or heart rate |
| `calculate_bmi_z()` | BMI calculation with categorization | weight, height, age |
| `convert_hba1c()` | HbA1c ↔ eAG conversion | HbA1c (%) or eAG (mg/dL) |
| `calculate_apri_fib4()` | Liver fibrosis assessment scores | AST, ALT, platelets, age |

### 🛡️ Security & Audit

- **PHI Outbound Guard**: Regex-based detection and blocking of SSNs, MRNs, phone numbers, emails, and patient identifiers
- **HMAC-SHA256 Audit Trail**: Cryptographically chained logs with tamper detection
- **Zero-PHI enforcement** at all API and supervisor entry points

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/pk-half-life-simulator.git
cd pk-half-life-simulator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env and set AUDIT_SECRET_KEY
```

### Environment Variables

| Variable | Description | Required |
|:---------|:------------|:---------|
| `AUDIT_SECRET_KEY` | Secret key for HMAC audit signing | Yes |
| `MODEL_PROVIDER` | LLM provider: `mock`, `ollama`, `claude`, `openai` | No (default: mock) |

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🚀 Quickstart

### 1. Direct Clinical Scoring (pk_sim.py)

```bash
# MELD-Na Score
python pk_sim.py single --bili 2.0 --creat 1.2 --inr 1.5 --na 135

# QTc Calculation
python pk_sim.py single --qt 420 --hr 70

# JSON Input
python pk_sim.py single --json '{"bilirubin": 2.0, "creatinine": 1.2, "inr": 1.5}'

# Batch CSV Processing
python pk_sim.py batch --input sample.csv --output results.csv
```

### 2. Supervisor System (cli.py)

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Interactive chat
python cli.py chat "Explain the MELD-Na scoring system"
```

### 3. High-Throughput Simulation

```bash
python simulator.py --tasks 1000
```

---

## 🐳 Container Deployment

```bash
# Build and run
docker compose up --build

# Or manually
docker build -t pk-half-life-simulator .
docker run -p 8000:8000 --env-file .env pk-half-life-simulator
```

The API will be available at `http://localhost:8000`

### API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/api/audit` | POST | Submit task for evaluation |
| `/api/chat` | POST | Supervisory chat |
| `/api/audit/logs` | GET | Retrieve audit trail |

---

## 🧪 Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_pk_half_life_simulator.py -v
```

---

## 📐 Mathematical Formulations

### MELD Score
```
MELD = 3.78 × ln(bilirubin) + 11.2 × ln(INR) + 9.57 × ln(creatinine) + 6.43
MELD-Na = MELD + 1.32 × (137 - Na) - [0.033 × MELD × (137 - Na)]
```

### QTc (Bazett)
```
QTc = QT / √(RR in seconds)
```

### HbA1c ↔ eAG
```
eAG (mg/dL) = 28.7 × HbA1c(%) - 46.7
```

### APRI
```
APRI = ((AST / AST_ULN) × 100) / platelets
```

### FIB-4
```
FIB-4 = (age × AST) / (platelets × √ALT)
```

---

## 🛡️ Security Features

- **Zero-PHI Outbound Interceptor**: Active regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **Tamper-Evident HMAC-SHA256 Audit Trail**: Chained, cryptographically signed logs for every evaluation
- **Environment-based secrets**: No hardcoded credentials; `AUDIT_SECRET_KEY` must be provided via environment

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 📞 Contact

- **Author:** Dr. Abu Suraih Sakhri
- **GitHub:** [@abusuraihsakhri](https://github.com/abusuraihsakhri)
