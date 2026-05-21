# rcm-denial-triage-assistant
AI-powered CLI tool for healthcare claim denial triage and explanation
# RCM Denial Triage Assistant

A Python CLI tool that reads ERA-like denial data, maps CARC/RARC codes,
retrieves payer policy context, and generates AI-powered explanations for billing specialists.

## Data Notes
- All claim IDs, patient IDs, and service dates in sample data are synthetic.
- No PHI (Protected Health Information) is used anywhere in this project.
- Real ERA data must never be uploaded to LLM APIs due to HIPAA compliance.

## Week 1 Progress Video:
  https://www.youtube.com/watch?v=j1dP9ZrMjn8
  

## Week 2 Progress
- Built parser.py with extract_denials() function to filter and normalize denial records
- Implemented normalize_code() to strip whitespace, uppercase codes, and return UNKNOWN for missing values
- Tested parser against two input files: a clean 20-row dataset and a deliberately messy 10-row dataset
- Wrote 13 pytest tests covering normalization, missing value handling, filtering, and no hardcoded row indexes — all passing
- Output three CSV files: individual outputs per file and a combined denials_extracted.csv

## Week 2 Progress Video
https://www.youtube.com/watch?v=wHO7rAVMAzw