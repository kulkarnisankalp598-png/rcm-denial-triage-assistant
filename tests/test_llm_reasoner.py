import sys
import os
import pytest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.llm_reasoner import build_prompt, validate_action_plan
from src.models import ActionPlan

SAMPLE_DENIAL = {
    "claim_id": "CLM10001",
    "payer": "SyntheticPayerA",
    "group_code": "CO",
    "carc": "16",
    "rarc": "MA130",
    "denied_amount": 120.50,
    "procedure_code": "99213",
    "modifier": "25",
    "service_date": "2026-05-01",
    "source_file": "synthetic_835_001.edi"
}

SAMPLE_RULE = {
    "short_name": "Missing Information",
    "action_category": "correct_claim",
    "recommended_action": "Review RARC and correct the identified field. Resubmit as corrected claim.",
    "appeal_eligible": True,
    "priority": "HIGH"
}

SAMPLE_POLICY = [
    {
        "source": "synthetic_missing_information_policy.txt",
        "section": "SECTION 1 — OVERVIEW",
        "topic": "Missing Information / Submission Errors",
        "score": 0.39,
        "text": "Claims submitted with missing, incomplete, or invalid information will be denied under CARC 16."
    }
]

VALID_ACTION_PLAN_DICT = {
    "claim_id": "CLM10001",
    "payer": "SyntheticPayerA",
    "group_code": "CO",
    "carc": "16",
    "rarc": "MA130",
    "denied_amount": 120.50,
    "code_meaning": "Claim lacks information.",
    "denial_summary": "Claim denied for missing information.",
    "likely_cause": "Incomplete procedure code.",
    "rule_based_action": "Correct and resubmit.",
    "llm_recommended_action": "Review RARC MA130 and resubmit with complete procedure code.",
    "evidence": ["synthetic_missing_information_policy.txt"],
    "confidence": "high",
    "needs_human_review": False,
    "reason_if_uncertain": None
}

# --- build_prompt tests ---

def test_build_prompt_returns_string():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert isinstance(prompt, str)

def test_build_prompt_contains_claim_id():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "CLM10001" in prompt

def test_build_prompt_contains_carc():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "16" in prompt

def test_build_prompt_contains_rule_action():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "correct_claim" in prompt

def test_build_prompt_contains_policy_evidence():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "synthetic_missing_information_policy" in prompt

def test_build_prompt_no_policy_evidence():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, [])
    assert "No policy evidence retrieved" in prompt

def test_build_prompt_contains_procedure_code():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "99213" in prompt

def test_build_prompt_contains_modifier():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "25" in prompt

def test_build_prompt_contains_carc_meaning():
    prompt = build_prompt(SAMPLE_DENIAL, SAMPLE_RULE, SAMPLE_POLICY)
    assert "carc_meaning" in prompt

# --- validate_action_plan tests ---

def test_validate_action_plan_valid():
    plan = validate_action_plan(VALID_ACTION_PLAN_DICT)
    assert isinstance(plan, ActionPlan)

def test_validate_action_plan_claim_id():
    plan = validate_action_plan(VALID_ACTION_PLAN_DICT)
    assert plan.claim_id == "CLM10001"

def test_validate_action_plan_confidence():
    plan = validate_action_plan(VALID_ACTION_PLAN_DICT)
    assert plan.confidence == "high"

def test_validate_action_plan_needs_human_review():
    plan = validate_action_plan(VALID_ACTION_PLAN_DICT)
    assert plan.needs_human_review == False

def test_validate_action_plan_invalid_confidence():
    bad = VALID_ACTION_PLAN_DICT.copy()
    bad['confidence'] = 'very_high'
    with pytest.raises(Exception):
        validate_action_plan(bad)

def test_validate_action_plan_missing_required_field():
    bad = VALID_ACTION_PLAN_DICT.copy()
    del bad['claim_id']
    with pytest.raises(Exception):
        validate_action_plan(bad)

def test_validate_action_plan_low_confidence():
    low = VALID_ACTION_PLAN_DICT.copy()
    low['confidence'] = 'low'
    low['needs_human_review'] = True
    low['reason_if_uncertain'] = 'No policy evidence available'
    plan = validate_action_plan(low)
    assert plan.confidence == 'low'
    assert plan.needs_human_review == True

def test_validate_action_plan_evidence_is_list():
    plan = validate_action_plan(VALID_ACTION_PLAN_DICT)
    assert isinstance(plan.evidence, list)