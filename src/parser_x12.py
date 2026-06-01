import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.code_lookup import get_carc_meaning, get_rarc_meaning


def parse_835(filepath):
    """Parse a synthetic X12 835 EDI file into normalized denial rows."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Split into segments by tilde
    segments = [s.strip() for s in content.split('~') if s.strip()]

    denials = []
    current_claim = {}
    source_file = os.path.basename(filepath)

    for segment in segments:
        try:
            fields = segment.split('*')
            seg_type = fields[0].upper()

            if seg_type == 'CLP':
                # Save previous claim if it exists
                if current_claim:
                    denials.append(current_claim.copy())
                # Start new claim
                current_claim = {
                    'claim_id': fields[1] if len(fields) > 1 else '',
                    'claim_status': fields[2] if len(fields) > 2 else '',
                    'billed_amount': fields[3] if len(fields) > 3 else '',
                    'paid_amount': fields[4] if len(fields) > 4 else '',
                    'denied_amount': float(fields[5]) if len(fields) > 5 and fields[5] else 0.0,
                    'payer_icn': fields[7] if len(fields) > 7 else '',
                    'patient_control_number': '',
                    'service_date': '',
                    'procedure_code': '',
                    'modifier': '',
                    'group_code': '',
                    'carc': '',
                    'rarc': '',
                    'carc_meaning': '',
                    'rarc_meaning': '',
                    'source_file': source_file,
                    'payer': 'SyntheticPayerA',
                }

            elif seg_type == 'NM1' and len(fields) > 1 and fields[1].upper() == 'QC':
                # Patient name segment — extract patient control number
                if current_claim:
                    current_claim['patient_control_number'] = fields[9] if len(fields) > 9 else ''

            elif seg_type == 'DTM' and len(fields) > 1 and fields[1] == '472':
                # Service date segment
                if current_claim and not current_claim.get('service_date'):
                    raw_date = fields[2] if len(fields) > 2 else ''
                    if len(raw_date) == 8:
                        current_claim['service_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                    else:
                        current_claim['service_date'] = raw_date

            elif seg_type == 'SVC':
                # Service line — extract procedure code and modifier
                if current_claim:
                    svc_code = fields[1] if len(fields) > 1 else ''
                    parts = svc_code.replace('HC:', '').split(':')
                    current_claim['procedure_code'] = parts[0] if parts else ''
                    current_claim['modifier'] = parts[1] if len(parts) > 1 else ''

            elif seg_type == 'CAS':
                # Claim adjustment — extract group code, CARC, denied amount
                if current_claim:
                    current_claim['group_code'] = fields[1].upper() if len(fields) > 1 else ''
                    current_claim['carc'] = fields[2].upper() if len(fields) > 2 else ''
                    current_claim['carc_meaning'] = get_carc_meaning(current_claim['carc'])

            elif seg_type == 'LQ':
                # Remark code — extract RARC
                if current_claim:
                    current_claim['rarc'] = fields[2].upper() if len(fields) > 2 else ''
                    current_claim['rarc_meaning'] = get_rarc_meaning(current_claim['rarc'])

        except Exception as e:
            print(f"Warning: skipping malformed segment '{segment[:30]}' — {e}")
            continue

    # Don't forget the last claim
    if current_claim:
        denials.append(current_claim.copy())

    return denials


def filter_denials(denials):
    """Keep only rows where denied_amount > 0."""
    return [d for d in denials if float(d.get('denied_amount', 0)) > 0]


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'data/synthetic_835_001.edi'

    print(f"Parsing {filepath}...\n")

    # Show segment extraction in debug mode
    with open(filepath, 'r') as f:
        content = f.read()
    segments = [s.strip() for s in content.split('~') if s.strip()]
    print(f"Total segments found: {len(segments)}\n")
    print("Segments being processed:")
    for s in segments:
        seg_type = s.split('*')[0].upper()
        if seg_type in ['CLP', 'CAS', 'SVC', 'DTM', 'LQ', 'NM1']:
            print(f"  [{seg_type}] {s}")
    print()

    denials = parse_835(filepath)
    denials = filter_denials(denials)

    output_path = sys.argv[2] if len(sys.argv) > 2 else 'outputs/normalized.json'
    with open(output_path, 'w') as f:
        json.dump(denials, f, indent=2)

    print(f"\nExtracted {len(denials)} denials → {output_path}")
    print("\nSample record:")
    if denials:
        print(json.dumps(denials[0], indent=2))