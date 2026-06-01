import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser_x12 import parse_835, filter_denials

# --- Helper ---

def write_temp_edi(content):
    """Write EDI content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False)
    f.write(content)
    f.close()
    return f.name

# --- parse_835 tests ---

def test_parse_835_returns_list():
    result = parse_835('data/synthetic_835_001.edi')
    assert isinstance(result, list)

def test_parse_835_extracts_10_claims():
    result = parse_835('data/synthetic_835_001.edi')
    assert len(result) == 10

def test_parse_835_claim_id():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['claim_id'] == 'CLM10001'

def test_parse_835_denied_amount():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['denied_amount'] == 120.5

def test_parse_835_group_code():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['group_code'] == 'CO'

def test_parse_835_carc():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['carc'] == '16'

def test_parse_835_rarc():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['rarc'] == 'MA130'

def test_parse_835_procedure_code():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['procedure_code'] == '99213'

def test_parse_835_modifier():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['modifier'] == '25'

def test_parse_835_service_date():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['service_date'] == '2026-05-01'

def test_parse_835_patient_control_number():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['patient_control_number'] == 'PAT-SYN-001'

def test_parse_835_source_file():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['source_file'] == 'synthetic_835_001.edi'

def test_parse_835_carc_meaning_populated():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['carc_meaning'] != ''
    assert result[0]['carc_meaning'] != 'CARC code not found in lookup table.'

def test_parse_835_rarc_meaning_populated():
    result = parse_835('data/synthetic_835_001.edi')
    assert result[0]['rarc_meaning'] != ''
    assert result[0]['rarc_meaning'] != 'RARC code not found in lookup table.'

def test_parse_835_pr_group_code():
    result = parse_835('data/synthetic_835_001.edi')
    pr_claims = [d for d in result if d['group_code'] == 'PR']
    assert len(pr_claims) > 0

def test_parse_835_claim_without_modifier():
    result = parse_835('data/synthetic_835_001.edi')
    no_modifier = [d for d in result if d['modifier'] == '']
    assert len(no_modifier) > 0

def test_parse_835_all_claims_have_claim_id():
    result = parse_835('data/synthetic_835_001.edi')
    assert all(d['claim_id'] != '' for d in result)

def test_parse_835_all_claims_have_carc():
    result = parse_835('data/synthetic_835_001.edi')
    assert all(d['carc'] != '' for d in result)

# --- filter_denials tests ---

def test_filter_denials_removes_zero_amount():
    denials = [
        {'denied_amount': 100.0},
        {'denied_amount': 0.0},
        {'denied_amount': 50.0},
    ]
    result = filter_denials(denials)
    assert len(result) == 2

def test_filter_denials_keeps_all_when_all_denied():
    result = parse_835('data/synthetic_835_001.edi')
    filtered = filter_denials(result)
    assert len(filtered) == 10

# --- malformed segment handling ---

def test_malformed_segment_does_not_crash():
    edi = """ST*835*0001~
CLP*CLM99001*4*100.00*0.00*50.00*12*ICN99001*11*1~
THIS_IS_MALFORMED_NO_ASTERISKS~
CAS*CO*16*50.00~
LQ*HE*MA130~
SE*5*0001~"""
    tmp = write_temp_edi(edi)
    try:
        result = parse_835(tmp)
        assert isinstance(result, list)
    finally:
        os.unlink(tmp)

def test_empty_segment_skipped():
    edi = """ST*835*0001~
CLP*CLM99002*4*200.00*0.00*75.00*12*ICN99002*11*1~
~
CAS*CO*50*75.00~
LQ*HE*N20~
SE*4*0001~"""
    tmp = write_temp_edi(edi)
    try:
        result = parse_835(tmp)
        assert len(result) >= 1
    finally:
        os.unlink(tmp)

def test_claim_level_denial_extracted():
    result = parse_835('data/synthetic_835_001.edi')
    claim = next((d for d in result if d['claim_id'] == 'CLM10001'), None)
    assert claim is not None
    assert claim['carc'] == '16'
    assert claim['group_code'] == 'CO'
    assert claim['denied_amount'] == 120.5

def test_service_line_procedure_extracted():
    result = parse_835('data/synthetic_835_001.edi')
    claim = next((d for d in result if d['claim_id'] == 'CLM10001'), None)
    assert claim is not None
    assert claim['procedure_code'] == '99213'
    assert claim['modifier'] == '25'