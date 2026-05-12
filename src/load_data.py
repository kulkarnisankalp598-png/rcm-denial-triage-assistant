import pandas as pd

def load_era_data(filepath):
    df = pd.read_csv(filepath)
    return df

def print_summary(df):
    print(f"Total records: {len(df)}")
    print(f"Total denied amount: ${df['denied_amount'].sum():.2f}")
    print(f"Unique payers: {list(df['payer'].unique())}")
    print(f"Unique CARC codes: {[int(c) for c in df['carc'].unique()]}")

def filter_denials(df):
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
    print(denials[['claim_id', 'payer', 'carc', 'rarc', 'denied_amount']].to_string(index=False))