import logging
from datetime import date
from typing import Optional
from pydantic import BaseModel, field_validator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VALID_GROUP_CODES = {'CO', 'PR', 'OA', 'PI', 'CR'}


class Adjustment(BaseModel):
    """Represents a single CAS segment — group code, CARC, and denied amount."""
    group_code: str
    carc: str
    denied_amount: float
    rarc: Optional[str] = ''
    carc_meaning: Optional[str] = ''
    rarc_meaning: Optional[str] = ''

    @field_validator('group_code')
    @classmethod
    def validate_group_code(cls, v):
        v = v.strip().upper()
        if v not in VALID_GROUP_CODES:
            logger.warning(f"Invalid group_code '{v}' — must be one of {VALID_GROUP_CODES}")
            raise ValueError(f"Invalid group_code '{v}'. Must be one of {VALID_GROUP_CODES}")
        return v

    @field_validator('carc')
    @classmethod
    def validate_carc(cls, v):
        v = str(v).strip().upper()
        if not v:
            logger.warning("CARC code is empty")
            raise ValueError("CARC code cannot be empty")
        return v

    @field_validator('denied_amount')
    @classmethod
    def validate_denied_amount(cls, v):
        if v < 0:
            logger.warning(f"denied_amount {v} is negative")
            raise ValueError("denied_amount cannot be negative")
        return v


class ServiceLine(BaseModel):
    """Represents a single SVC segment — procedure code, modifier, amounts."""
    procedure_code: str
    modifier: Optional[str] = ''
    billed_amount: Optional[float] = 0.0
    paid_amount: Optional[float] = 0.0

    @field_validator('procedure_code')
    @classmethod
    def validate_procedure_code(cls, v):
        v = str(v).strip()
        if not v:
            logger.warning("procedure_code is empty")
            raise ValueError("procedure_code cannot be empty")
        return v


class Claim(BaseModel):
    """Represents a normalized claim-level denial record."""
    claim_id: str
    payer: str
    patient_control_number: Optional[str] = ''
    service_date: Optional[str] = ''
    source_file: str
    billed_amount: Optional[str] = ''
    paid_amount: Optional[str] = ''
    denied_amount: float
    group_code: str
    carc: str
    rarc: Optional[str] = ''
    carc_meaning: Optional[str] = ''
    rarc_meaning: Optional[str] = ''
    procedure_code: Optional[str] = ''
    modifier: Optional[str] = ''
    payer_icn: Optional[str] = ''
    claim_status: Optional[str] = ''

    @field_validator('claim_id')
    @classmethod
    def validate_claim_id(cls, v):
        if not v or not v.strip():
            raise ValueError("claim_id cannot be empty")
        return v.strip()

    @field_validator('payer')
    @classmethod
    def validate_payer(cls, v):
        if not v or not v.strip():
            raise ValueError("payer cannot be empty")
        return v.strip()

    @field_validator('source_file')
    @classmethod
    def validate_source_file(cls, v):
        if not v or not v.strip():
            raise ValueError("source_file cannot be empty")
        return v.strip()

    @field_validator('group_code')
    @classmethod
    def validate_group_code(cls, v):
        v = v.strip().upper()
        if v not in VALID_GROUP_CODES:
            logger.warning(f"Invalid group_code '{v}'")
            raise ValueError(f"Invalid group_code '{v}'. Must be one of {VALID_GROUP_CODES}")
        return v

    @field_validator('carc')
    @classmethod
    def validate_carc(cls, v):
        v = str(v).strip().upper()
        if not v:
            raise ValueError("CARC code cannot be empty")
        return v

    @field_validator('denied_amount')
    @classmethod
    def validate_denied_amount(cls, v):
        if v < 0:
            raise ValueError("denied_amount cannot be negative")
        return v

    @field_validator('service_date')
    @classmethod
    def validate_service_date(cls, v):
        if not v:
            return v
        try:
            date.fromisoformat(v)
        except ValueError:
            logger.warning(f"Invalid service_date format '{v}' — expected YYYY-MM-DD")
            raise ValueError(f"Invalid service_date format '{v}'. Expected YYYY-MM-DD")
        return v


class DenialFinding(BaseModel):
    """Represents the full denial finding after code lookup and retrieval."""
    claim: Claim
    denial_summary: Optional[str] = ''
    likely_cause: Optional[str] = ''
    retrieved_policy_source: Optional[str] = ''
    retrieved_policy_snippet: Optional[str] = ''


class PolicyEvidence(BaseModel):
    """Represents a retrieved policy snippet."""
    source: str
    page_or_section: Optional[str] = ''
    snippet: str


class ActionPlan(BaseModel):
    """Represents the final LLM-generated action plan for a denial."""
    claim_id: str
    payer: str
    group_code: str
    carc: str
    rarc: Optional[str] = ''
    denied_amount: float
    code_meaning: str
    denial_summary: str
    likely_cause: str
    rule_based_action: Optional[str] = ''
    llm_recommended_action: Optional[str] = ''
    evidence: Optional[list] = []
    confidence: Optional[str] = 'low'
    needs_human_review: bool = True
    reason_if_uncertain: Optional[str] = ''

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        valid = {'high', 'medium', 'low'}
        if v.lower() not in valid:
            raise ValueError(f"confidence must be one of {valid}")
        return v.lower()


def validate_denial_row(row: dict) -> Claim:
    """Validate a denial dict and return a Claim model. Logs errors clearly."""
    try:
        claim = Claim(**row)
        logger.info(f"Claim {claim.claim_id} validated successfully")
        return claim
    except Exception as e:
        logger.error(f"Validation failed for row {row.get('claim_id', 'UNKNOWN')}: {e}")
        raise


def validate_all_denials(rows: list) -> tuple:
    """
    Validate a list of denial dicts.
    Returns (valid_claims, errors) tuple.
    """
    valid = []
    errors = []
    for row in rows:
        try:
            claim = validate_denial_row(row)
            valid.append(claim)
        except Exception as e:
            errors.append({'row': row.get('claim_id', 'UNKNOWN'), 'error': str(e)})
    logger.info(f"Validation complete: {len(valid)} valid, {len(errors)} errors")
    return valid, errors


if __name__ == "__main__":
    import json

    # Export JSON schema
    schema = Claim.model_json_schema()
    with open('docs/schema.json', 'w') as f:
        json.dump(schema, f, indent=2)
    print("Schema exported to docs/schema.json")

    # Validate normalized.json
    print("\nTesting models with normalized.json...\n")
    with open('outputs/normalized.json') as f:
        rows = json.load(f)

    valid, errors = validate_all_denials(rows)
    print(f"\nValid claims: {len(valid)}")
    print(f"Errors: {len(errors)}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")
    else:
        print("\nAll rows passed validation.")