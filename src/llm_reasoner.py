import os
import json
import logging
from dotenv import load_dotenv
import anthropic
from src.models import ActionPlan
from src.code_lookup import get_code_meanings

load_dotenv()
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an expert healthcare billing specialist assistant. Your job is to analyze insurance claim denials and provide structured, actionable guidance to billing teams.

You will be given:
- Claim details (claim ID, payer, procedure code, denied amount)
- CARC and RARC codes with their official meanings
- A rules-based recommended action
- Retrieved policy evidence (if available)

Your response must be a valid JSON object following this exact schema. Do not include any text outside the JSON.

{{
  "claim_id": "string",
  "payer": "string",
  "group_code": "string",
  "carc": "string",
  "rarc": "string",
  "denied_amount": number,
  "code_meaning": "string — plain English summary of CARC + RARC combined",
  "denial_summary": "string — 1-2 sentence plain English summary of what happened",
  "likely_cause": "string — most probable root cause of this denial",
  "rule_based_action": "string — the deterministic action from the rules engine",
  "llm_recommended_action": "string — your specific recommended action for this claim",
  "evidence": ["list of policy sources used"],
  "confidence": "high | medium | low",
  "needs_human_review": true | false,
  "reason_if_uncertain": "string or null — explain if confidence is low or medium"
}}

Rules you must follow:
1. Set confidence to "high" only when retrieved policy evidence directly supports the denial reason.
2. Set confidence to "medium" when the rules baseline applies but policy evidence is weak or indirect.
3. Set confidence to "low" and needs_human_review to true when no policy evidence is available or the denial reason is ambiguous.
4. Never fabricate policy text. Only reference evidence that is explicitly provided to you.
5. llm_recommended_action must be specific to this claim — not generic. Reference the procedure code, modifier, and CARC/RARC where relevant.
6. If evidence is missing, still provide a recommendation but set needs_human_review to true.

CLAIM DATA:
{claim_data}

RULES BASELINE:
{rules_baseline}

POLICY EVIDENCE:
{policy_evidence}

Respond with only the JSON object. No preamble, no explanation, no markdown.
"""


def build_prompt(denial_row: dict, rule: dict, policy_results: list) -> str:
    """Build the prompt for the LLM from denial data, rule, and retrieved policy."""
    claim_data = {
        "claim_id": denial_row.get("claim_id", ""),
        "payer": denial_row.get("payer", ""),
        "group_code": denial_row.get("group_code", ""),
        "carc": denial_row.get("carc", ""),
        "rarc": denial_row.get("rarc", ""),
        "denied_amount": denial_row.get("denied_amount", 0),
        "procedure_code": denial_row.get("procedure_code", ""),
        "modifier": denial_row.get("modifier", ""),
        "service_date": denial_row.get("service_date", ""),
    }

    meanings = get_code_meanings(denial_row.get("carc", ""), denial_row.get("rarc", ""))
    claim_data["carc_meaning"] = meanings["carc_meaning"]
    claim_data["rarc_meaning"] = meanings["rarc_meaning"]

    rules_baseline = {
        "short_name": rule.get("short_name", ""),
        "action_category": rule.get("action_category", ""),
        "recommended_action": rule.get("recommended_action", ""),
        "appeal_eligible": rule.get("appeal_eligible", None),
        "priority": rule.get("priority", ""),
    }

    if policy_results:
        policy_evidence = [
            {
                "source": r.get("source", ""),
                "section": r.get("section", ""),
                "topic": r.get("topic", ""),
                "score": r.get("score", 0),
                "text": r.get("text", "")[:500]
            }
            for r in policy_results
        ]
    else:
        policy_evidence = []

    return PROMPT_TEMPLATE.format(
        claim_data=json.dumps(claim_data, indent=2),
        rules_baseline=json.dumps(rules_baseline, indent=2),
        policy_evidence=json.dumps(policy_evidence, indent=2) if policy_evidence else "No policy evidence retrieved."
    )


def call_llm(prompt: str, max_retries: int = 2) -> dict:
    """Call the Anthropic API and return parsed JSON response."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")

    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            raw_text = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            logger.info(f"LLM response parsed successfully on attempt {attempt + 1}")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                raise ValueError(f"LLM returned invalid JSON after {max_retries + 1} attempts: {e}")

        except Exception as e:
            logger.error(f"LLM API call failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                raise


def validate_action_plan(response_dict: dict) -> ActionPlan:
    """Validate LLM response against ActionPlan Pydantic schema."""
    try:
        plan = ActionPlan(**response_dict)
        logger.info(f"ActionPlan validated for claim {plan.claim_id} — confidence={plan.confidence}")
        return plan
    except Exception as e:
        logger.error(f"ActionPlan validation failed: {e}")
        raise ValueError(f"LLM response does not match ActionPlan schema: {e}")


def reason_about_denial(denial_row: dict, rule: dict, policy_results: list) -> ActionPlan:
    """
    Full pipeline: build prompt → call LLM → validate → return ActionPlan.
    Falls back to human_review if LLM fails.
    """
    try:
        prompt = build_prompt(denial_row, rule, policy_results)
        response_dict = call_llm(prompt)
        plan = validate_action_plan(response_dict)
        return plan

    except Exception as e:
        logger.error(f"reason_about_denial failed for claim {denial_row.get('claim_id', 'UNKNOWN')}: {e}")
        # Return a safe human_review fallback
        fallback = ActionPlan(
            claim_id=denial_row.get("claim_id", "UNKNOWN"),
            payer=denial_row.get("payer", "UNKNOWN"),
            group_code=denial_row.get("group_code", ""),
            carc=denial_row.get("carc", ""),
            rarc=denial_row.get("rarc", ""),
            denied_amount=float(denial_row.get("denied_amount", 0)),
            code_meaning="Unable to retrieve code meaning.",
            denial_summary="LLM reasoning failed. Manual review required.",
            likely_cause="Unknown — LLM error.",
            rule_based_action=rule.get("recommended_action", ""),
            llm_recommended_action="Route to human review due to LLM failure.",
            evidence=[],
            confidence="low",
            needs_human_review=True,
            reason_if_uncertain=f"LLM error: {str(e)}"
        )
        return fallback


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    from src.rules_engine import load_rules, get_rule
    from src.retriever import PolicyRetriever

    rules = load_rules()
    retriever = PolicyRetriever()

    # Test with first 3 claims from normalized.json
    with open('outputs/normalized.json') as f:
        rows = json.load(f)

    print("\n" + "="*60)
    print("LLM REASONER TEST")
    print("="*60)

    for row in rows[:3]:
        print(f"\nProcessing claim {row['claim_id']} | CARC {row['carc']}...")
        rule = get_rule(row['carc'], rules=rules)
        policy_results = retriever.retrieve_for_denial(
            carc=row['carc'],
            rarc=row['rarc'],
            carc_meaning=row.get('carc_meaning', ''),
            short_description=row.get('short_description', '')
        )

        plan = reason_about_denial(row, rule, policy_results)

        print(f"\nClaim: {plan.claim_id}")
        print(f"Confidence: {plan.confidence}")
        print(f"Needs human review: {plan.needs_human_review}")
        print(f"Denial summary: {plan.denial_summary}")
        print(f"Recommended action: {plan.llm_recommended_action}")
        print(f"Evidence sources: {plan.evidence}")
        print("-"*50)