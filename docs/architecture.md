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