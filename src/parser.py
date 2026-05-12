import pandas as pd

def normalize_code(code):
    if pd.isna(code):
        return "UNKNOWN"
    return str(code).strip().upper()

def extract_denials(df):
    denials = df[df['denied_amount'] > 0].copy()
    denials['carc'] = denials['carc'].apply(normalize_code)
    denials['rarc'] = denials['rarc'].apply(normalize_code)
    denials['group_code'] = denials['group_code'].apply(normalize_code)
    return denials

if __name__ == "__main__":
    for filename in ["sample_era.csv", "sample_era_messy.csv"]:
        df = pd.read_csv(f"data/{filename}")
        denials = extract_denials(df)
        output_path = f"outputs/denials_extracted_{filename}"
        denials.to_csv(output_path, index=False)
        print(f"Extracted {len(denials)} denials from {filename} → {output_path}")