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

## Week 3 Progress
- Wrote full domain brief covering ERA, 835, CLP, CAS, SVC, LQ, DTM, NM1, CARC, RARC, group codes, claim-level vs service-line denials, and PHI
- Added architecture diagram to README showing full data flow from input to dashboard
- Upgraded project from 8-week basic track to 10-week advanced track
- Created new src modules: parser_x12.py, models.py, code_lookup.py, rules_engine.py, evaluator.py, app_cli.py, app_streamlit.py
- Created docs/ folder with domain_brief.md, architecture.md, schema.json, prompt_template.md
- Created data/policies/ folder for payer policy documents
- Updated parser_json.py to support both CSV and JSON input
- Added source_file tracking, procedure_code, modifier, and patient_control_number fields to parser and sample data
- Built src/code_lookup.py with complete official CARC and RARC definitions sourced from x12.org
- 40/40 pytest tests passing across all test files

## Week 3 Progress Video
https://www.youtube.com/watch?v=VQud7EHCjYo
## Week 4 Progress
- Created synthetic X12 835 EDI file with 10 claims (`data/synthetic_835_001.edi`)
- Built `parser_x12.py` that splits segments by tilde and fields by asterisk
- Extracts CLP, CAS, SVC, DTM, NM1, and LQ segments into normalized denial rows
- Code meanings looked up automatically from code_lookup module during parsing
- Malformed segments handled gracefully with try/except and warning logs
- Runs via `py -m src.parser_x12 data/synthetic_835_001.edi outputs/normalized.json`
- 24 pytest tests covering claim-level and service-line denials — all passing

## Week 4 & 5 Progress Video
https://www.youtube.com/watch?v=QudOqRV2MJA&feature=youtu.be

## Week 5 Progress
- Built `src/models.py` with six Pydantic models: Claim, Adjustment, ServiceLine, DenialFinding, PolicyEvidence, ActionPlan
- Claim model validates group_code, denied_amount, service_date, carc, payer, claim_id, and source_file
- Invalid rows return clear logged errors instead of raw stack traces
- Built `validate_denial_row` and `validate_all_denials` utility functions
- Auto-exported Claim model as JSON schema to `docs/schema.json`
- 29 pytest tests covering valid and invalid fixtures — all passing
- 93/93 total tests passing across all test files

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
## Week 6 Progress
- Created 6 synthetic payer policy documents covering missing information, medical necessity, modifier 25/inconsistent modifier, bundled services, duplicate claims, and deductible/coinsurance
- Built `src/policy_loader.py` to extract and chunk policy text by section heading, attaching payer, topic, effective date, and section metadata to each chunk
- Loaded 36 total policy chunks across all 6 documents
- Built `src/retriever.py` using TF-IDF and cosine similarity for keyword-based retrieval
- Implemented `retrieve_for_denial()` which builds a query automatically from CARC meaning, RARC, and short description
- Achieved correct top-3 policy retrieval for all 5 tested CARC denial scenarios (16, 50, 97, 1, 4)
- 20 pytest tests covering policy loading, metadata extraction, and retrieval accuracy
- 113/113 total tests passing across all test files

## Week 6 Progress Video
https://www.youtube.com/watch?v=TS-FKLIUfx0
