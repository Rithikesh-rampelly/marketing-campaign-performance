"""Print portfolio KPIs using the shared, validated analytics engine."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import calculate_kpis, load_data


def _format_amount(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.2f}"


def _format_count(value: int | None) -> str:
    return "N/A" if value is None else f"{value:,}"


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _format_multiple(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}x"


def _print_revenue_warning(kpis: dict) -> None:
    missing = kpis["missing_revenue_rows"]
    row_count = kpis["row_count"]
    if not missing:
        return
    if missing == row_count:
        print(
            "WARNING: Revenue is partial (no rows have known revenue); "
            "financial KPIs are N/A."
        )
    else:
        print(
            f"WARNING: Revenue is partial ({missing} of {row_count} row(s) missing); "
            "financial KPIs use known revenue only."
        )


def main(data_path: str | Path | None = None) -> None:
    df = load_data(data_path)
    kpis = calculate_kpis(df)

    print("OVERALL MARKETING KPIs")
    print("=" * 40)
    _print_revenue_warning(kpis)

    print(f"Total Ad Spend (INR): {_format_amount(kpis['total_ad_spend'])}")
    print(f"Known Revenue (INR): {_format_amount(kpis['total_revenue'])}")
    print(f"Total Impressions: {_format_count(kpis['total_impressions'])}")
    print(f"Total Clicks: {_format_count(kpis['total_clicks'])}")
    print(f"Total Leads: {_format_count(kpis['total_leads'])}")
    print(f"Total Conversions: {_format_count(kpis['total_conversions'])}")
    print(f"CTR: {_format_percent(kpis['ctr_percent'])}")
    print(f"Conversion Rate: {_format_percent(kpis['conversion_rate_percent'])}")
    print(f"CAC (INR): {_format_amount(kpis['cac'])}")
    print(f"ROAS: {_format_multiple(kpis['roas'])}")
    print(f"ROI: {_format_percent(kpis['roi_percent'])}")
    print(f"Revenue Coverage: {_format_percent(kpis['revenue_coverage_percent'])}")


if __name__ == "__main__":
    main()
