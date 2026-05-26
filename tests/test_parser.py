import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser_json import normalize_code, extract_denials

# --- normalize_code tests ---

def test_normalize_code_missing_none():
    assert normalize_code(None) == "UNKNOWN"

def test_normalize_code_missing_nan():
    assert normalize_code(float('nan')) == "UNKNOWN"

def test_normalize_code_strips_whitespace():
    assert normalize_code("  co  ") == "CO"

def test_normalize_code_uppercases():
    assert normalize_code("ma130") == "MA130"

def test_normalize_code_normal_value():
    assert normalize_code("16") == "16"

def test_normalize_code_already_clean():
    assert normalize_code("CO") == "CO"

# --- extract_denials tests ---

def test_extract_denials_filters_zero_amount():
    df = pd.DataFrame({
        'claim_id': [1, 2, 3],
        'payer': ['Cigna', 'Aetna', 'UHC'],
        'denied_amount': [100.0, 0.0, 50.0],
        'carc': ['16', '50', '1'],
        'rarc': ['MA130', 'N20', 'N4'],
        'group_code': ['CO', 'CO', 'PR']
    })
    result = extract_denials(df)
    assert len(result) == 2
    assert 2 not in result['claim_id'].values

def test_extract_denials_normalizes_codes():
    df = pd.DataFrame({
        'claim_id': [1],
        'payer': ['Cigna'],
        'denied_amount': [100.0],
        'carc': [' 16 '],
        'rarc': ['ma130'],
        'group_code': [' co ']
    })
    result = extract_denials(df)
    assert result.iloc[0]['carc'] == '16'
    assert result.iloc[0]['rarc'] == 'MA130'
    assert result.iloc[0]['group_code'] == 'CO'

def test_extract_denials_handles_missing_carc():
    df = pd.DataFrame({
        'claim_id': [1],
        'payer': ['Cigna'],
        'denied_amount': [100.0],
        'carc': [None],
        'rarc': ['MA130'],
        'group_code': ['CO']
    })
    result = extract_denials(df)
    assert result.iloc[0]['carc'] == 'UNKNOWN'

def test_extract_denials_handles_missing_rarc():
    df = pd.DataFrame({
        'claim_id': [1],
        'payer': ['Cigna'],
        'denied_amount': [100.0],
        'carc': ['16'],
        'rarc': [None],
        'group_code': ['CO']
    })
    result = extract_denials(df)
    assert result.iloc[0]['rarc'] == 'UNKNOWN'

def test_extract_denials_no_hardcoded_indexes():
    df = pd.DataFrame({
        'claim_id': [1, 2, 3],
        'payer': ['Cigna', 'Aetna', 'UHC'],
        'denied_amount': [0.0, 100.0, 75.0],
        'carc': ['16', '50', '1'],
        'rarc': ['MA130', 'N20', 'N4'],
        'group_code': ['CO', 'CO', 'PR']
    })
    result = extract_denials(df)
    assert len(result) == 2
    assert result.iloc[0]['claim_id'] == 2

def test_extract_denials_works_on_clean_file():
    df = pd.read_csv('data/sample_era.csv')
    result = extract_denials(df)
    assert len(result) == 20
    assert result['carc'].str.contains('UNKNOWN').sum() == 0

def test_extract_denials_works_on_messy_file():
    df = pd.read_csv('data/sample_era_messy.csv')
    result = extract_denials(df)
    assert len(result) == 10
    assert (result['group_code'] == result['group_code'].str.upper()).all()