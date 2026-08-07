import streamlit as st
import pandas as pd
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app_cli import load_input, enrich_denial, save_output
from src.retriever import PolicyRetriever
from src.rules_engine import load_rules

st.set_page_config(
    page_title="RCM Denial Triage Assistant",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 RCM Denial Triage Assistant")
st.markdown("AI-powered insurance claim denial analysis and action recommendations.")

# ---- Sidebar ----
with st.sidebar:
    st.header("Settings")
    use_llm = st.toggle("Enable LLM Reasoning", value=False,
        help="Enable Claude AI for claim-specific recommendations. Slower but more detailed.")
    st.markdown("---")
    st.header("Upload Data")
    uploaded_file = st.file_uploader(
        "Upload denial file",
        type=["csv", "json", "edi"],
        help="Supports X12 835 EDI, CSV, and JSON formats"
    )
    use_sample = st.button("Use Sample EDI File")

# ---- Load Data ----
@st.cache_data
def load_and_process(filepath, use_llm_flag):
    rules = load_rules()
    retriever = PolicyRetriever()
    rows = load_input(filepath)
    enriched = []
    for row in rows:
        enriched_row = enrich_denial(row, rules, retriever, use_llm=use_llm_flag)
        enriched.append(enriched_row)
    return pd.DataFrame(enriched)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'last_file' not in st.session_state:
    st.session_state.last_file = None
if 'last_llm' not in st.session_state:
    st.session_state.last_llm = None

if use_sample:
    sample_path = "data/synthetic_835_001.edi"
    if os.path.exists(sample_path):
        if st.session_state.last_file != sample_path or st.session_state.last_llm != use_llm:
            with st.spinner("Processing sample EDI file..."):
                st.session_state.df = load_and_process(sample_path, use_llm)
                st.session_state.last_file = sample_path
                st.session_state.last_llm = use_llm
        st.success(f"Loaded {len(st.session_state.df)} denial records from sample file.")
    else:
        st.error("Sample file not found.")

elif uploaded_file:
    tmp_path = f"outputs/tmp_{uploaded_file.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    if st.session_state.last_file != tmp_path or st.session_state.last_llm != use_llm:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            st.session_state.df = load_and_process(tmp_path, use_llm)
            st.session_state.last_file = tmp_path
            st.session_state.last_llm = use_llm
    st.success(f"Loaded {len(st.session_state.df)} denial records.")

df = st.session_state.df

# ---- Dashboard ----
if df is not None and len(df) > 0:

    # ---- Summary metrics ----
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Denials", len(df))
    with col2:
        total = df['denied_amount'].apply(pd.to_numeric, errors='coerce').sum()
        st.metric("Total Denied Amount", f"${total:,.2f}")
    with col3:
        needs_review = df['needs_human_review'].sum() if 'needs_human_review' in df.columns else 0
        st.metric("Needs Human Review", int(needs_review))
    with col4:
        high_conf = (df['confidence'] == 'high').sum() if 'confidence' in df.columns else 0
        st.metric("High Confidence", int(high_conf))

    st.markdown("---")

    # ---- Filters ----
    st.subheader("Filters")
    fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)

    with fcol1:
        payers = ['All'] + sorted(df['payer'].dropna().unique().tolist())
        selected_payer = st.selectbox("Payer", payers)

    with fcol2:
        if 'denial_short_name' in df.columns:
            categories = ['All'] + sorted(df['denial_short_name'].dropna().unique().tolist())
        else:
            categories = ['All'] + sorted(df['carc'].dropna().unique().tolist())
        selected_category = st.selectbox("Denial Category", categories)

    with fcol3:
        min_amt = float(df['denied_amount'].apply(pd.to_numeric, errors='coerce').min())
        max_amt = float(df['denied_amount'].apply(pd.to_numeric, errors='coerce').max())
        amount_range = st.slider("Denied Amount ($)", min_amt, max_amt, (min_amt, max_amt))

    with fcol4:
        if 'confidence' in df.columns:
            conf_levels = ['All'] + sorted(df['confidence'].dropna().unique().tolist())
            selected_conf = st.selectbox("Confidence", conf_levels)
        else:
            selected_conf = 'All'

    with fcol5:
        review_filter = st.selectbox("Human Review", ['All', 'Needs Review', 'No Review Needed'])

    # Apply filters
    filtered = df.copy()
    filtered['denied_amount'] = pd.to_numeric(filtered['denied_amount'], errors='coerce')

    if selected_payer != 'All':
        filtered = filtered[filtered['payer'] == selected_payer]
    if selected_category != 'All':
        col_name = 'denial_short_name' if 'denial_short_name' in filtered.columns else 'carc'
        filtered = filtered[filtered[col_name] == selected_category]
    filtered = filtered[
        (filtered['denied_amount'] >= amount_range[0]) &
        (filtered['denied_amount'] <= amount_range[1])
    ]
    if selected_conf != 'All' and 'confidence' in filtered.columns:
        filtered = filtered[filtered['confidence'] == selected_conf]
    if review_filter == 'Needs Review' and 'needs_human_review' in filtered.columns:
        filtered = filtered[filtered['needs_human_review'] == True]
    elif review_filter == 'No Review Needed' and 'needs_human_review' in filtered.columns:
        filtered = filtered[filtered['needs_human_review'] == False]

    st.markdown(f"**Showing {len(filtered)} of {len(df)} records**")
    st.markdown("---")

    # ---- Claims table ----
    st.subheader("Denial Records")

    display_cols = [c for c in [
        'claim_id', 'payer', 'carc', 'rarc', 'denied_amount',
        'denial_short_name', 'action_category', 'confidence', 'needs_human_review'
    ] if c in filtered.columns]

    st.dataframe(filtered[display_cols], use_container_width=True)

    # ---- Claim detail ----
    st.markdown("---")
    st.subheader("Claim Detail")

    claim_ids = filtered['claim_id'].astype(str).tolist()
    selected_claim = st.selectbox("Select a claim to view details", claim_ids)

    if selected_claim:
        claim = filtered[filtered['claim_id'].astype(str) == selected_claim].iloc[0]

        dcol1, dcol2 = st.columns(2)

        with dcol1:
            st.markdown("**Claim Facts**")
            st.write(f"**Claim ID:** {claim.get('claim_id', '')}")
            st.write(f"**Payer:** {claim.get('payer', '')}")
            st.write(f"**Service Date:** {claim.get('service_date', '')}")
            st.write(f"**Procedure Code:** {claim.get('procedure_code', '')} {claim.get('modifier', '')}")
            st.write(f"**Denied Amount:** ${pd.to_numeric(claim.get('denied_amount', 0), errors='coerce'):,.2f}")
            st.write(f"**Group Code:** {claim.get('group_code', '')}")
            st.write(f"**CARC:** {claim.get('carc', '')} — {claim.get('carc_meaning', '')}")
            st.write(f"**RARC:** {claim.get('rarc', '')} — {claim.get('rarc_meaning', '')}")

        with dcol2:
            st.markdown("**Analysis**")
            conf = claim.get('confidence', 'low')
            conf_color = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}.get(conf, '⚪')
            st.write(f"**Confidence:** {conf_color} {conf}")
            review = claim.get('needs_human_review', True)
            st.write(f"**Human Review:** {'⚠️ Yes' if review else '✅ No'}")
            st.write(f"**Priority:** {claim.get('priority', '')}")
            st.write(f"**Appeal Eligible:** {claim.get('appeal_eligible', '')}")

        if claim.get('denial_summary'):
            st.markdown("**Denial Summary**")
            st.info(claim.get('denial_summary', ''))

        if claim.get('rule_based_action'):
            st.markdown("**Rules-Based Action**")
            st.warning(claim.get('rule_based_action', ''))

        if claim.get('llm_recommended_action'):
            st.markdown("**AI Recommended Action**")
            st.success(claim.get('llm_recommended_action', ''))

        if claim.get('retrieved_policy_snippet'):
            with st.expander("Policy Evidence"):
                st.write(f"**Source:** {claim.get('retrieved_policy_source', '')}")
                st.write(claim.get('retrieved_policy_snippet', ''))

        if claim.get('reason_if_uncertain'):
            with st.expander("Uncertainty Reason"):
                st.write(claim.get('reason_if_uncertain', ''))

    # ---- Export ----
    st.markdown("---")
    st.subheader("Export")
    ecol1, ecol2 = st.columns(2)

    with ecol1:
        csv_data = filtered.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="denial_report.csv",
            mime="text/csv"
        )

    with ecol2:
        json_data = filtered.to_json(orient='records', indent=2)
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name="denial_report.json",
            mime="application/json"
        )

else:
    st.info("Upload a denial file or click 'Use Sample EDI File' to get started.")
    st.markdown("""
    **Supported formats:**
    - X12 835 EDI (`.edi`)
    - CSV (`.csv`)
    - JSON (`.json`)

    **What this tool does:**
    1. Parses denial data from EDI, CSV, or JSON
    2. Translates CARC/RARC codes to plain English
    3. Retrieves relevant payer policy evidence
    4. Applies rules-based recommended actions
    5. Generates AI-powered claim-specific explanations (when LLM enabled)
    """)