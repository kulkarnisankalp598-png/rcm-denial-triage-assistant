import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rules_engine import load_rules, get_rule, apply_rules, apply_rules_to_all

VALID_ACTION_CATEGORIES = {
    'resubmit', 'correct_claim', 'add_documentation',
    'appeal', 'bill_patient', 'human_review'
}

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

def test_all_rules_have_valid_action_category():
    rules = load_rules()
    for carc, rule in rules.items():
        assert rule['action_category'] in VALID_ACTION_CATEGORIES, \
            f"CARC {carc} has invalid action_category: {rule['action_category']}"

def test_all_rules_have_required_fields():
    rules = load_rules()
    required = ['carc', 'short_name', 'action_category', 'recommended_action',
                'appeal_eligible', 'priority']
    for carc, rule in rules.items():
        for field in required:
            assert field in rule, f"CARC {carc} missing field: {field}"

# --- parameterized get_rule tests ---

@pytest.mark.parametrize("carc,expected_short_name,expected_action,expected_priority", [
    ("16",  "Missing Information",      "correct_claim",     "HIGH"),
    ("50",  "Not Medically Necessary",  "appeal",            "HIGH"),
    ("97",  "Service Bundled",          "correct_claim",     "MEDIUM"),
    ("1",   "Deductible Amount",        "bill_patient",      "LOW"),
    ("4",   "Inconsistent Modifier",    "correct_claim",     "HIGH"),
    ("96",  "Non-Covered Charge",       "human_review",      "MEDIUM"),
    ("18",  "Duplicate Claim",          "resubmit",          "LOW"),
    ("29",  "Timely Filing",            "appeal",            "MEDIUM"),
    ("45",  "Exceeds Fee Schedule",     "correct_claim",     "LOW"),
    ("197", "Missing Authorization",    "add_documentation", "HIGH"),
])
def test_get_rule_parameterized(carc, expected_short_name, expected_action, expected_priority):
    rule = get_rule(carc)
    assert rule['short_name'] == expected_short_name
    assert rule['action_category'] == expected_action
    assert rule['priority'] == expected_priority

# --- parameterized appeal_eligible tests ---

@pytest.mark.parametrize("carc,expected_appeal", [
    ("16",  True),
    ("50",  True),
    ("97",  True),
    ("1",   False),
    ("4",   True),
    ("96",  True),
    ("18",  False),
    ("29",  True),
    ("45",  False),
    ("197", True),
])
def test_appeal_eligible_parameterized(carc, expected_appeal):
    rule = get_rule(carc)
    assert rule['appeal_eligible'] == expected_appeal

# --- fallback tests ---

def test_get_rule_unknown_carc_returns_human_review():
    rule = get_rule('999')
    assert rule['action_category'] == 'human_review'

def test_get_rule_unknown_carc_short_name():
    rule = get_rule('999')
    assert rule['short_name'] == 'Unknown Denial'

def test_get_rule_unknown_carc_priority():
    rule = get_rule('999')
    assert rule['priority'] == 'UNKNOWN'

def test_get_rule_unknown_carc_appeal_eligible_is_none():
    rule = get_rule('999')
    assert rule['appeal_eligible'] is None

def test_get_rule_has_recommended_action():
    rule = get_rule('16')
    assert len(rule['recommended_action']) > 10

def test_get_rule_has_notes():
    rule = get_rule('16')
    assert 'notes' in rule

# --- apply_rules tests ---

def test_apply_rules_adds_action_category():
    row = {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}
    result = apply_rules(row)
    assert result['action_category'] == 'correct_claim'

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

def test_apply_rules_unknown_carc_human_review():
    row = {'claim_id': 'TEST001', 'carc': '999', 'denied_amount': 50.0}
    result = apply_rules(row)
    assert result['action_category'] == 'human_review'
    assert result['priority'] == 'UNKNOWN'

def test_apply_rules_does_not_mutate_original():
    row = {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}
    original_keys = set(row.keys())
    apply_rules(row.copy())
    assert set(row.keys()) == original_keys

# --- apply_rules_to_all tests ---

def test_apply_rules_to_all_returns_list():
    rows = [
        {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0},
        {'claim_id': 'TEST002', 'carc': '50', 'denied_amount': 75.0},
    ]
    results = apply_rules_to_all(rows)
    assert isinstance(results, list)
    assert len(results) == 2

def test_apply_rules_to_all_all_have_action_category():
    rows = [
        {'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0},
        {'claim_id': 'TEST002', 'carc': '50', 'denied_amount': 75.0},
        {'claim_id': 'TEST003', 'carc': '999', 'denied_amount': 200.0},
    ]
    results = apply_rules_to_all(rows)
    for r in results:
        assert r['action_category'] in VALID_ACTION_CATEGORIES

def test_apply_rules_to_all_does_not_mutate_original():
    rows = [{'claim_id': 'TEST001', 'carc': '16', 'denied_amount': 100.0}]
    apply_rules_to_all(rows)
    assert 'rule_based_action' not in rows[0]