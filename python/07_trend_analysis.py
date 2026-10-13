"""Print monthly trends with calendar-safe dates and guarded KPIs."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import load_data, summarize_by


monthly_analysis = summarize_by(load_data(), "month")

print("MONTHLY TREND ANALYSIS")
print("=" * 80)
print(monthly_analysis.round(2).to_string(index=False))
