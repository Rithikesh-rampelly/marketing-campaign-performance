"""Normalize the original cleaned export into the dashboard-ready CSV."""

from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import validate_data


ROOT = Path(__file__).resolve().parents[1]
file_path = ROOT / "data" / "cleaned" / "marketing_campaign_cleaned.csv"
df = pd.read_csv(file_path, encoding="utf-8-sig", dtype="string")

# Keep only the original 13 marketing dataset columns, then run the same
# validation used by the dashboard and tests.
df = validate_data(df.iloc[:, :13])

# Save the corrected CSV
output_path = ROOT / "data" / "cleaned" / "marketing_campaign_cleaned_final.csv"
df.to_csv(output_path, index=False)

print("Corrected dataset saved successfully!")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("\nColumn names:")
print(df.columns.tolist())
