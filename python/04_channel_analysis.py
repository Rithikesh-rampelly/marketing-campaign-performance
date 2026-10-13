"""Print channel performance using the same logic as the dashboard."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import load_data, summarize_by


channel_analysis = summarize_by(load_data(), "channel").sort_values(
    "total_revenue", ascending=False, na_position="last"
)

print("CHANNEL PERFORMANCE ANALYSIS")
print("=" * 60)
print(channel_analysis.round(2).to_string(index=False))
