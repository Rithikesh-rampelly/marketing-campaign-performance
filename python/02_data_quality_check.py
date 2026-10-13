"""Print the validated data-quality summary used by the dashboard."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import health_summary, load_data


df = load_data()
health = health_summary(df)

print("DATASET INFO")
print("=" * 40)
print(df.info())

print("\nMISSING VALUES")
print("=" * 40)
print(df.isnull().sum())

print("\nDUPLICATE ROWS")
print("=" * 40)
print(df.duplicated().sum())

print("\nANALYTICS HEALTH")
print("=" * 40)
print(f"Date range: {health['start_date']} to {health['end_date']}")
print(f"Revenue coverage: {health['revenue_coverage_percent']:.2f}%")
print(f"Unknown age rows: {health['unknown_age_rows']}")
print(f"Unknown gender rows: {health['unknown_gender_rows']}")
for insight in health["insights"]:
    print(f"- {insight['severity'].upper()}: {insight['title']} - {insight['message']}")
