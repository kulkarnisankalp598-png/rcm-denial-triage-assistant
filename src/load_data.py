import pandas as pd
import os

def load_era_data(filepath):
    """Load ERA data from a CSV or JSON file into a DataFrame."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext == '.json':
        return pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv or .json")

def print_summary(df):
    """Print summary statistics for the ERA dataset."""
    print(f"Total records: {len(df)}")
    print(f"Total denied amount: ${df['denied_amount'].sum():.2f}")
    print(f"Unique payers: {list(df['payer'].unique())}")
    print(f"Unique CARC codes: {[int(c) for c in df['carc'].unique()]}")
    print(f"Records with denials: {(df['denied_amount'] > 0).sum()}")
    print(f"Average denied amount: ${df['denied_amount'].mean():.2f}")

def filter_denials(df):
    """Return only rows where denied_amount > 0 or group_code indicates adjustment."""
    adjustment_codes = ['CO', 'PR', 'OA', 'PI']
    return df[
        (df['denied_amount'] > 0) |
        (df['group_code'].isin(adjustment_codes))
    ].copy()

if __name__ == "__main__":
    df = load_era_data("data/sample_era.csv")
    print_summary(df)
    print("\nDenial records:")
    denials = filter_denials(df)
    print(denials[['claim_id', 'payer', 'group_code', 'carc', 'rarc', 'denied_amount']].to_string(index=False))