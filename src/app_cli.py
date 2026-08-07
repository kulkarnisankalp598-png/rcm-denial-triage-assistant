import argparse
import json
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.parser_json import load_file, extract_denials
from src.parser_x12 import parse_835, filter_denials as filter_x12_denials
from src.code_lookup import get_code_meanings
from src.retriever import PolicyRetriever
from src.rules_engine import load_rules, get_rule, apply_rules
from src.llm_reasoner import reason_about_denial
from src.models import validate_all_denials

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_input(filepath):
    """Load input file — supports CSV, JSON, and EDI."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.edi':
        logger.info(f"Parsing X12 835 EDI file: {filepath}")
        rows = parse_835(filepath)
        rows = filter_x12_denials(rows)
        return rows
    elif ext in ['.csv', '.json']:
        logger.info(f"Loading {ext.upper()} file: {filepath}")
        df = load_file(filepath)
        denials = extract_denials(df, source_file=os.path.basename(filepath))
        return denials.to_dict(orient='records')
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .edi, .csv, or .json")


def enrich_denial(row, rules, retriever, use_llm=True):
    """Run a single denial row through the full pipeline."""
    carc = str(row.get('carc', ''))
    rarc = str(row.get('rarc', ''))

    # Code lookup
    meanings = get_code_meanings(carc, rarc)
    row['carc_meaning'] = meanings['carc_meaning']
    row['rarc_meaning'] = meanings['rarc_meaning']

    # Rules engine
    rule = get_rule(carc, rules=rules)
    row = apply_rules(row, rules=rules)

    # Retrieval
    policy_results = retriever.retrieve_for_denial(
        carc=carc,
        rarc=rarc,
        carc_meaning=meanings['carc_meaning'],
        short_description=row.get('short_description', '')
    )
    row['retrieved_policy_source'] = policy_results[0]['source'] if policy_results else ''
    row['retrieved_policy_snippet'] = policy_results[0]['text'][:300] if policy_results else ''

    # LLM reasoning
    if use_llm:
        try:
            plan = reason_about_denial(row, rule, policy_results)
            row['llm_recommended_action'] = plan.llm_recommended_action
            row['denial_summary'] = plan.denial_summary
            row['likely_cause'] = plan.likely_cause
            row['confidence'] = plan.confidence
            row['needs_human_review'] = plan.needs_human_review
            row['reason_if_uncertain'] = plan.reason_if_uncertain or ''
            row['evidence'] = ' | '.join(plan.evidence) if plan.evidence else ''
        except Exception as e:
            logger.error(f"LLM failed for claim {row.get('claim_id', 'UNKNOWN')}: {e}")
            row['llm_recommended_action'] = 'LLM unavailable — use rule-based action'
            row['denial_summary'] = ''
            row['likely_cause'] = ''
            row['confidence'] = 'low'
            row['needs_human_review'] = True
            row['reason_if_uncertain'] = str(e)
            row['evidence'] = ''
    else:
        row['llm_recommended_action'] = ''
        row['denial_summary'] = ''
        row['likely_cause'] = ''
        row['confidence'] = 'low'
        row['needs_human_review'] = True
        row['reason_if_uncertain'] = 'LLM disabled'
        row['evidence'] = ''

    return row


def save_output(rows, output_path):
    """Save enriched denial rows to CSV or JSON."""
    ext = os.path.splitext(output_path)[1].lower()
    df = pd.DataFrame(rows)

    if ext == '.csv':
        df.to_csv(output_path, index=False)
    elif ext == '.json':
        df.to_json(output_path, orient='records', indent=2)
    else:
        raise ValueError(f"Unsupported output format: {ext}. Use .csv or .json")

    logger.info(f"Saved {len(rows)} records to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='RCM Denial Triage Assistant — process insurance claim denials'
    )
    parser.add_argument('--input', required=True, help='Input file path (.edi, .csv, or .json)')
    parser.add_argument('--output', required=True, help='Output file path (.csv or .json)')
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM reasoning (faster, rules-only)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("RCM DENIAL TRIAGE ASSISTANT")
    print(f"{'='*60}")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print(f"LLM:    {'disabled' if args.no_llm else 'enabled'}")
    print(f"{'='*60}\n")

    enriched = []

    try:
        # Load input
        print("Loading input file...")
        rows = load_input(args.input)
        print(f"Loaded {len(rows)} denial records\n")

        # Load rules and retriever once
        print("Initializing rules engine and retriever...")
        rules = load_rules()
        retriever = PolicyRetriever()
        print(f"Ready — {len(rules)} rules, {len(retriever.chunks)} policy chunks\n")

        # Process each denial
        for i, row in enumerate(rows):
            claim_id = row.get('claim_id', f'ROW{i+1}')
            carc = row.get('carc', 'UNKNOWN')
            print(f"Processing [{i+1}/{len(rows)}] Claim {claim_id} | CARC {carc}...")
            try:
                enriched_row = enrich_denial(row, rules, retriever, use_llm=not args.no_llm)
                enriched.append(enriched_row)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Failed to process claim {claim_id}: {e}")
                row['error'] = str(e)
                row['confidence'] = 'low'
                row['needs_human_review'] = True
                enriched.append(row)

        # Save output
        print(f"\nSaving output to {args.output}...")
        save_output(enriched, args.output)

        # Summary
        needs_review = sum(1 for r in enriched if r.get('needs_human_review'))
        high_conf = sum(1 for r in enriched if r.get('confidence') == 'high')
        total_denied = sum(float(r.get('denied_amount', 0)) for r in enriched)

        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total denials processed: {len(enriched)}")
        print(f"Total denied amount:     ${total_denied:,.2f}")
        print(f"High confidence:         {high_conf}")
        print(f"Needs human review:      {needs_review}")
        print(f"Output saved to:         {args.output}")
        print(f"{'='*60}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        if enriched:
            print(f"Saving {len(enriched)} processed records before exit...")
            save_output(enriched, args.output)
            print(f"Partial output saved to {args.output}")
        sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"CLI failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()