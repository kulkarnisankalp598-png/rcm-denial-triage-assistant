import pandas as pd
import os

def normalize_code(code):
    """Strip whitespace, uppercase, and handle missing values."""
    if pd.isna(code):
        return "UNKNOWN"
    return str(code).strip().upper()

def normalize_optional(value):
    """Normalize optional fields — return empty string if missing."""
    if pd.isna(value):
        return ""
    return str(value).strip()

def extract_denials(df, source_file=""):
    """Filter to denial rows and normalize all code columns."""
    denials = df[df['denied_amount'] > 0].copy()
    denials['carc'] = denials['carc'].apply(normalize_code)
    denials['rarc'] = denials['rarc'].apply(normalize_code)
    denials['group_code'] = denials['group_code'].apply(normalize_code)
    denials['carc'] = denials['carc'].apply(lambda x: str(int(float(x))) if x != 'UNKNOWN' else x)
    denials['modifier'] = denials['modifier'].apply(normalize_optional)
    denials['source_file'] = source_file
    return denials

def load_file(filepath):
    """Load a CSV or JSON file into a DataFrame."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext == '.json':
        return pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv or .json")

if __name__ == "__main__":
    files = ["sample_era.csv", "sample_era_messy.csv"]
    all_denials = []

    for filename in files:
        filepath = f"data/{filename}"
        if not os.path.exists(filepath):
            print(f"File not found: {filepath} — skipping")
            continue
        df = load_file(filepath)
        denials = extract_denials(df, source_file=filename)
        output_path = f"outputs/denials_extracted_{filename}"
        denials.to_csv(output_path, index=False)
        print(f"Extracted {len(denials)} denials from {filename} → {output_path}")
        all_denials.append(denials)

    combined = pd.concat(all_denials, ignore_index=True)
    combined.to_csv("outputs/denials_extracted.csv", index=False)
    print(f"Combined output → outputs/denials_extracted.csv ({len(combined)} total rows)")