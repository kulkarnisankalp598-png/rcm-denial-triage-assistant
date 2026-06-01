import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import Claim, Adjustment, ServiceLine, ActionPlan, validate_denial_row, validate_all_denials

# --- Valid fixture ---

def valid_claim_data():
    return {
        "claim_id": "CLM10001",
        "payer": "SyntheticPayerA",
        "patient_control_number": "PAT-SYN-001",
        "service_date": "2026-05-01",
        "source_file": "synthetic_835_001.edi",
        "billed_amount": "250.00",
        "paid_amount": "0.00",
        "denied_amount": 120.50,
        "group_code": "CO",
        "carc": "16",
        "rarc": "MA130",
        "carc_meaning": "Claim/service lacks information or has submission/billing error(s).",
        "rarc_meaning": "Your claim contains incomplete and/or invalid information.",
        "procedure_code": "99213",
        "modifier": "25",
        "payer_icn": "ICN10001",
        "claim_status": "4"
    }

# --- Claim model tests ---

def test_claim_valid():
    claim = Claim(**valid_claim_data())
    assert claim.claim_id == "CLM10001"

def test_claim_invalid_group_code():
    data = valid_claim_data()
    data['group_code'] = 'XX'
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_invalid_denied_amount():
    data = valid_claim_data()
    data['denied_amount'] = -50.0
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_empty_claim_id():
    data = valid_claim_data()
    data['claim_id'] = ''
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_empty_payer():
    data = valid_claim_data()
    data['payer'] = ''
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_empty_source_file():
    data = valid_claim_data()
    data['source_file'] = ''
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_invalid_service_date():
    data = valid_claim_data()
    data['service_date'] = '05-01-2026'
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_valid_service_date():
    data = valid_claim_data()
    data['service_date'] = '2026-05-01'
    claim = Claim(**data)
    assert claim.service_date == '2026-05-01'

def test_claim_empty_carc():
    data = valid_claim_data()
    data['carc'] = ''
    with pytest.raises(Exception):
        Claim(**data)

def test_claim_pr_group_code_valid():
    data = valid_claim_data()
    data['group_code'] = 'PR'
    claim = Claim(**data)
    assert claim.group_code == 'PR'

def test_claim_oa_group_code_valid():
    data = valid_claim_data()
    data['group_code'] = 'OA'
    claim = Claim(**data)
    assert claim.group_code == 'OA'

def test_claim_optional_modifier_empty():
    data = valid_claim_data()
    data['modifier'] = ''
    claim = Claim(**data)
    assert claim.modifier == ''

def test_claim_carc_uppercased():
    data = valid_claim_data()
    data['carc'] = 'a1'
    claim = Claim(**data)
    assert claim.carc == 'A1'

def test_claim_group_code_uppercased():
    data = valid_claim_data()
    data['group_code'] = 'co'
    claim = Claim(**data)
    assert claim.group_code == 'CO'

# --- Adjustment model tests ---

def test_adjustment_valid():
    adj = Adjustment(group_code='CO', carc='16', denied_amount=120.50)
    assert adj.group_code == 'CO'

def test_adjustment_invalid_group_code():
    with pytest.raises(Exception):
        Adjustment(group_code='XX', carc='16', denied_amount=120.50)

def test_adjustment_negative_amount():
    with pytest.raises(Exception):
        Adjustment(group_code='CO', carc='16', denied_amount=-10.0)

def test_adjustment_empty_carc():
    with pytest.raises(Exception):
        Adjustment(group_code='CO', carc='', denied_amount=120.50)

# --- ServiceLine model tests ---

def test_service_line_valid():
    sl = ServiceLine(procedure_code='99213', modifier='25')
    assert sl.procedure_code == '99213'

def test_service_line_empty_procedure_code():
    with pytest.raises(Exception):
        ServiceLine(procedure_code='')

def test_service_line_optional_modifier():
    sl = ServiceLine(procedure_code='99213')
    assert sl.modifier == ''

# --- ActionPlan model tests ---

def test_action_plan_valid():
    ap = ActionPlan(
        claim_id='CLM10001',
        payer='SyntheticPayerA',
        group_code='CO',
        carc='16',
        denied_amount=120.50,
        code_meaning='Claim lacks information.',
        denial_summary='Claim denied for missing info.',
        likely_cause='Incomplete procedure code.',
        confidence='high',
        needs_human_review=False
    )
    assert ap.confidence == 'high'

def test_action_plan_invalid_confidence():
    with pytest.raises(Exception):
        ActionPlan(
            claim_id='CLM10001',
            payer='SyntheticPayerA',
            group_code='CO',
            carc='16',
            denied_amount=120.50,
            code_meaning='Claim lacks information.',
            denial_summary='Claim denied.',
            likely_cause='Missing info.',
            confidence='unknown'
        )

def test_action_plan_defaults_to_needs_human_review():
    ap = ActionPlan(
        claim_id='CLM10001',
        payer='SyntheticPayerA',
        group_code='CO',
        carc='16',
        denied_amount=120.50,
        code_meaning='Claim lacks information.',
        denial_summary='Claim denied.',
        likely_cause='Missing info.'
    )
    assert ap.needs_human_review == True

# --- validate_all_denials tests ---

def test_validate_all_denials_all_valid():
    rows = [valid_claim_data(), valid_claim_data()]
    rows[1]['claim_id'] = 'CLM10002'
    valid, errors = validate_all_denials(rows)
    assert len(valid) == 2
    assert len(errors) == 0

def test_validate_all_denials_mixed():
    bad = valid_claim_data()
    bad['group_code'] = 'XX'
    rows = [valid_claim_data(), bad]
    valid, errors = validate_all_denials(rows)
    assert len(valid) == 1
    assert len(errors) == 1

def test_validate_denial_row_valid():
    claim = validate_denial_row(valid_claim_data())
    assert claim.claim_id == 'CLM10001'

def test_validate_denial_row_invalid():
    data = valid_claim_data()
    data['denied_amount'] = -100.0
    with pytest.raises(Exception):
        validate_denial_row(data)

def test_validate_all_from_normalized_json():
    import json
    with open('outputs/normalized.json') as f:
        rows = json.load(f)
    valid, errors = validate_all_denials(rows)
    assert len(valid) == 10
    assert len(errors) == 0