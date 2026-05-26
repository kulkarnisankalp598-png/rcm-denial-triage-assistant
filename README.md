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

## Architechture

```
Input (CSV / JSON / 835 EDI)
         |
         v
   Parser Layer
   parser_json.py  →  CSV / JSON input
   parser_x12.py   →  X12 835 EDI input
         |
         v
   Pydantic Data Model (models.py)
   Validates normalized denial records
         |
         +-----------------+------------------+
         |                 |                  |
         v                 v                  v
   Code Lookup       Policy Retriever    Rules Engine
   code_lookup.py    retriever.py        rules_engine.py
   CARC/RARC         Keyword + TF-IDF    YAML playbooks
   definitions       policy evidence     deterministic actions
         |                 |                  |
         +-----------------+------------------+
                           |
                           v
                  LLM Reasoner
                  llm_reasoner.py
                  Grounded JSON action plan
                           |
                           v
              +------------+------------+
              |                         |
              v                         v
        CLI Output               Streamlit Dashboard
        app_cli.py               app_streamlit.py
        denial_report.csv        Interactive UI
              |
              v
        Evaluator
        evaluator.py
        Parser accuracy, retrieval precision, action usefulness
```