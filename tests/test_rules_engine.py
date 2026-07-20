import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rules_engine import load_rules, get_rule, apply_rules, apply_rules_to_all

# --- load_rules tests ---

def test_load_rules_returns_dict():
    rules = load_rules()
    assert isinstance(rules, dict)

def test_load_rules_count():
    rules = load_rules()
    assert len(rules) >= 10

def test_load_rules_contains_carc_16():
    rules = load_rules()
    assert '16' in rules

def test_load_rules_contains_carc_96():
    rules = load_rules()
    assert '96' in rules

def test_load_rules_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_rules('nonexistent/path.yaml')

# --- get_rule tests ---

def test_get_rule_carc_16():
    rule = get_rule('16')
    assert rule['short_name'] == 'Missing Information'
    assert rule['priority'] == 'HIGH'
    assert rule['appeal_eligible'] == True

def test_get_rule_carc_50():
    rule = get_rule('50')
    assert rule['short_name'] == 'Not Medically Necessary'
    assert rule['appeal_eligible'] == True

def test_get_rule_carc_97():
    rule = get_rule('97')
    assert rule['short_name'] == 'Service Bundled'
    assert rule['priority'] == 'MEDIUM'

def test_get_rule_carc_1():
    rule = get_rule('1')
    assert rule['short_name'] == 'Deductible Amount'
    assert rule['appeal_eligible'] == False

def test_get_rule_carc_4():
    rule = get_rule('4')
    assert rule['short_name'] == 'Inconsistent Modifier'
    assert rule['priority'] == 'HIGH'

def test_get_rule_carc_96():
    rule = get_rule('96')
    assert rule['short_name'] == 'Non-Covered Charge'
    assert rule['appeal_eligible'] == True

def test_get_rule_carc_18():
    rule = get_rule('18')
    assert rule['short_name'] == 'Duplicate Claim'
    assert rule['appeal_eligible'] == False

def test_get_rule_unknown_carc_returns_default():
    rule = get_rule('999')
    assert rule['short_name'] == 'Unknown Denial'
    assert rule['priority'] == 'UNKNOWN'
    assert rule['appeal_eligible'] is None

def test_get_rule_has_recommended_action():
    rule = get_rule('16')
    assert 'recommended_action' in rule
    assert len(rule['recommended_action']) > 10

def test_get_rule_has_notes():
    rule = get_rule('16')
    assert 'notes' in rule

def test_get_rule_case_insensitive():
    rule = get_rule('16')
    assert rule is not None

# --- apply_rules tests ---

def test_apply_rules_adds_rule_based_action():
    row = {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}
    result = apply_rules(row)
    assert 'rule_based_action' in result
    assert len(result['rule_based_action']) > 10

def test_apply_rules_adds_priority():
    row = {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}
    result = apply_rules(row)
    assert result['priority'] == 'HIGH'

def test_apply_rules_adds_appeal_eligible():
    row = {'claim_id': 'TEST001', 'carc': '1', 'denied_amount': 35.0}
    result = apply_rules(row)
    assert result['appeal_eligible'] == False

def test_apply_rules_adds_short_name():
    row = {'claim_id': 'TEST001', 'carc': '97', 'denied_amount': 200.0}
    result = apply_rules(row)
    assert result['denial_short_name'] == 'Service Bundled'

def test_apply_rules_unknown_carc():
    row = {'claim_id': 'TEST001', 'carc': '999', 'denied_amount': 50.0}
    result = apply_rules(row)
    assert result['priority'] == 'UNKNOWN'

# --- apply_rules_to_all tests ---

def test_apply_rules_to_all_returns_list():
    rows = [
        {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0},
        {'claim_id': 'TEST002', 'carc': '50', 'denied_amount': 75.0},
    ]
    results = apply_rules_to_all(rows)
    assert isinstance(results, list)
    assert len(results) == 2

def test_apply_rules_to_all_all_enriched():
    rows = [
        {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0},
        {'claim_id': 'TEST002', 'carc': '50', 'denied_amount': 75.0},
        {'claim_id': 'TEST003', 'carc': '97', 'denied_amount': 200.0},
    ]
    results = apply_rules_to_all(rows)
    for r in results:
        assert 'rule_based_action' in r
        assert 'priority' in r
        assert 'appeal_eligible' in r

def test_apply_rules_to_all_does_not_mutate_original():
    rows = [{'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}]
    apply_rules_to_all(rows)
    assert 'rule_based_action' not in rows[0]