import yaml
import logging
import os

logger = logging.getLogger(__name__)

VALID_ACTION_CATEGORIES = {
    'resubmit',
    'correct_claim',
    'add_documentation',
    'appeal',
    'bill_patient',
    'human_review'
}


def load_rules(playbook_path='data/playbooks/carc_rules.yaml'):
    """Load CARC rules from YAML playbook."""
    if not os.path.exists(playbook_path):
        logger.error(f"Playbook not found: {playbook_path}")
        raise FileNotFoundError(f"Playbook not found: {playbook_path}")

    with open(playbook_path, 'r') as f:
        data = yaml.safe_load(f)

    rules = {str(rule['carc']): rule for rule in data.get('rules', [])}
    logger.info(f"Loaded {len(rules)} rules from {playbook_path}")
    return rules


def get_rule(carc_code, rules=None, playbook_path='data/playbooks/carc_rules.yaml'):
    """
    Look up the rule for a given CARC code.
    Returns the rule dict or a human_review fallback if not found.
    """
    if rules is None:
        rules = load_rules(playbook_path)

    carc = str(carc_code).strip().upper()
    rule = rules.get(carc)

    if rule:
        logger.info(f"Rule found for CARC {carc}: {rule['short_name']}")
        return rule
    else:
        logger.warning(f"No rule found for CARC {carc} — returning human_review fallback")
        return {
            'carc': carc,
            'short_name': 'Unknown Denial',
            'action_category': 'human_review',
            'group_codes': [],
            'recommended_action': 'No specific rule found for this CARC code. Route to human review — do not attempt automated action.',
            'appeal_eligible': None,
            'priority': 'UNKNOWN',
            'common_rarcs': [],
            'notes': 'Add this CARC to the rules playbook for future automation.'
        }


def apply_rules(denial_row: dict, rules=None):
    """
    Apply rules to a denial row dict.
    Returns the row with rule-based fields added.
    """
    if rules is None:
        rules = load_rules()

    carc = str(denial_row.get('carc', '')).strip().upper()
    rule = get_rule(carc, rules=rules)

    denial_row['rule_based_action'] = rule['recommended_action']
    denial_row['action_category'] = rule['action_category']
    denial_row['appeal_eligible'] = rule['appeal_eligible']
    denial_row['priority'] = rule['priority']
    denial_row['denial_short_name'] = rule['short_name']

    return denial_row


def apply_rules_to_all(denial_rows: list):
    """Apply rules to a list of denial row dicts."""
    rules = load_rules()
    return [apply_rules(row.copy(), rules=rules) for row in denial_rows]


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    rules = load_rules()

    print("\n" + "="*60)
    print("RULES ENGINE TEST")
    print("="*60)

    test_carcs = ["16", "50", "97", "1", "4", "96", "18", "29", "45", "197", "999"]

    for carc in test_carcs:
        rule = get_rule(carc, rules=rules)
        print(f"\nCARC {carc} — {rule['short_name']}")
        print(f"  Action category: {rule['action_category']}")
        print(f"  Priority: {rule['priority']}")
        print(f"  Appeal eligible: {rule['appeal_eligible']}")
        print(f"  Action: {rule['recommended_action'][:100]}...")

    print("\n" + "="*60)
    print("APPLY RULES TO SAMPLE DENIAL ROWS")
    print("="*60)

    with open('outputs/normalized.json') as f:
        rows = json.load(f)

    enriched = apply_rules_to_all(rows)
    for r in enriched[:3]:
        print(f"\nClaim {r['claim_id']} | CARC {r['carc']} | {r['denial_short_name']}")
        print(f"  Action category: {r['action_category']}")
        print(f"  Priority: {r['priority']}")
        print(f"  Action: {r['rule_based_action'][:100]}...")