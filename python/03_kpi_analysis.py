"""Print portfolio KPIs using the shared, validated analytics engine."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import calculate_kpis, load_data


df = load_data()
kpis = calculate_kpis(df)

print("OVERALL MARKETING KPIs")
print("=" * 40)

print(f"Total Ad Spend (INR): {kpis['total_ad_spend']:,.2f}")
print(f"Known Revenue (INR): {kpis['total_revenue']:,.2f}")
print(f"Total Impressions: {kpis['total_impressions']:,}")
print(f"Total Clicks: {kpis['total_clicks']:,}")
print(f"Total Leads: {kpis['total_leads']:,}")
print(f"Total Conversions: {kpis['total_conversions']:,}")
print(f"CTR: {kpis['ctr_percent']:.2f}%")
print(f"Conversion Rate: {kpis['conversion_rate_percent']:.2f}%")
print(f"CAC (INR): {kpis['cac']:,.2f}")
print(f"ROAS: {kpis['roas']:.2f}x")
print(f"ROI: {kpis['roi_percent']:.2f}%")
print(f"Revenue Coverage: {kpis['revenue_coverage_percent']:.2f}%")
