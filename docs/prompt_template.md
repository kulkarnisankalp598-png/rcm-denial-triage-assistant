# LLM Prompt Template Documentation

## Overview
The prompt template used in `src/llm_reasoner.py` is a strict structured prompt
that instructs Claude to generate a grounded, evidence-based denial explanation
and recommended action for a given insurance claim denial.

## Design Principles

**1. Strict JSON output**
The prompt instructs the model to return only a JSON object with no preamble,
explanation, or markdown. This makes the response directly parseable and
validatable against the ActionPlan Pydantic schema.

**2. Deterministic settings**
The API is called with `temperature=0` to minimize randomness and make outputs
as consistent and reproducible as possible across repeated calls.

**3. Grounding rules**
The prompt contains explicit rules the model must follow:
- Never fabricate policy text — only reference evidence explicitly provided
- Set confidence to high only when retrieved policy evidence directly supports the denial
- Set confidence to medium when rules apply but policy evidence is weak
- Set confidence to low and needs_human_review to true when no evidence is available
- llm_recommended_action must be specific to the claim — not generic

**4. Fallback handling**
If the LLM returns invalid JSON or the API call fails, `reason_about_denial`
catches the exception and returns a safe human_review ActionPlan with
confidence=low and needs_human_review=True. No bad output ever reaches
the billing team.

## Input Fields

| Field | Source | Description |
|---|---|---|
| claim_id | Parser output | Unique claim identifier |
| payer | Parser output | Insurance company name |
| group_code | Parser output | CO, PR, OA, PI |
| carc | Parser output | Claim Adjustment Reason Code |
| rarc | Parser output | Remittance Advice Remark Code |
| denied_amount | Parser output | Dollar amount denied |
| procedure_code | Parser output | CPT procedure code |
| modifier | Parser output | Procedure modifier (e.g. 25) |
| service_date | Parser output | Date of service |
| carc_meaning | code_lookup.py | Official X12 plain-English CARC definition |
| rarc_meaning | code_lookup.py | Official X12 plain-English RARC definition |
| rules_baseline | rules_engine.py | Deterministic action category and recommended action |
| policy_evidence | retriever.py | Top-3 TF-IDF retrieved policy chunks with source and section |

## Output Schema (ActionPlan)

| Field | Type | Description |
|---|---|---|
| claim_id | string | Claim identifier |
| payer | string | Insurance company |
| group_code | string | Adjustment group code |
| carc | string | CARC code |
| rarc | string | RARC code |
| denied_amount | float | Denied dollar amount |
| code_meaning | string | Plain English summary of CARC + RARC combined |
| denial_summary | string | 1-2 sentence summary of what happened |
| likely_cause | string | Most probable root cause |
| rule_based_action | string | Deterministic action from rules engine |
| llm_recommended_action | string | Claim-specific LLM recommendation |
| evidence | list | Policy sources referenced |
| confidence | high/medium/low | Confidence level based on evidence quality |
| needs_human_review | boolean | True when confidence is low or evidence is missing |
| reason_if_uncertain | string or null | Explanation when confidence is not high |

## Hallucination Risk and Grounding Strategy

Hallucination risk is when the LLM generates facts not present in its input —
such as citing a policy that was not retrieved or inventing procedure details.

This project mitigates hallucination risk through three layers:

**Layer 1 — Evidence-only input**
Only real retrieved policy text is passed to the LLM. The model cannot
reference information that was not explicitly provided in the prompt.

**Layer 2 — Explicit prompt rules**
The prompt instructs the model: "Never fabricate policy text. Only reference
evidence that is explicitly provided to you."

**Layer 3 — Confidence and review flags**
When no policy evidence is retrieved, the model is instructed to set
confidence=low and needs_human_review=True. This flags the output for
human review rather than allowing it to be acted on autonomously.

**Layer 4 — Pydantic validation**
Every LLM response is validated against the ActionPlan schema before use.
Structurally invalid responses are caught and replaced with a safe fallback.

## Rules Baseline vs LLM Output

The rules engine provides a **deterministic, auditable** baseline action for
every known CARC code. It is fast, consistent, and readable by non-engineers
in the YAML playbook.

The LLM adds a **claim-specific, evidence-grounded** layer on top — taking
the rules baseline, the retrieved policy text, and the CARC/RARC meanings
and generating a nuanced explanation and specific recommended action for
this particular claim.

In short: the rules engine answers **what to do**, the LLM answers
**why and how — specifically for this claim**.