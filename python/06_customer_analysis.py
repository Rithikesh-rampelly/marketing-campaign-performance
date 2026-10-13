"""Print audience segment performance with guarded KPI calculations."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import load_data, summarize_by


df = load_data()


# Age Group Analysis
age_analysis = summarize_by(df, "age_group")

print("AGE GROUP ANALYSIS")
print("=" * 70)
print(age_analysis.to_string(index=False))


# Gender Analysis
gender_analysis = summarize_by(df, "gender")

print("\nGENDER ANALYSIS")
print("=" * 70)
print(gender_analysis.to_string(index=False))
