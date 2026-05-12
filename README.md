# rcm-denial-triage-assistant
AI-powered CLI tool for healthcare claim denial triage and explanation
# RCM Denial Triage Assistant

A Python CLI tool that reads ERA-like denial data, maps CARC/RARC codes,
retrieves payer policy context, and generates AI-powered explanations for billing specialists.

## Week 1 Progress
- Project structure and GitHub repo set up
- Virtual environment with pandas, python-dotenv, pytest, streamlit
- Synthetic sample ERA data created (`data/sample_era.csv`)
- `load_data.py` loads CSV, prints summary stats, and filters denials

## Setup
```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Usage
```bash
py src\load_data.py
```

## Data Notes
- All claim IDs, patient IDs, and service dates in sample data are synthetic.
- No PHI (Protected Health Information) is used anywhere in this project.
- Real ERA data must never be uploaded to LLM APIs due to HIPAA compliance.
