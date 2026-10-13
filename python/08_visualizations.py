"""Generate the original PNG portfolio charts from the shared analytics core.

The Streamlit dashboard is the recommended interactive experience. This file
keeps the original static-image workflow available for presentations and
Power BI documentation, while preventing divide-by-zero and inconsistent KPI
calculations.
"""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import pandas as pd

from python.marketing_analytics import grouped_summaries, load_data


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _finish(title: str, path: Path, *, rotate_labels: bool = False) -> None:
    plt.title(title)
    if rotate_labels:
        plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    print(path)


def _bar(series: pd.Series, title: str, ylabel: str, filename: str) -> None:
    if series.empty:
        return
    ax = series.plot(kind="bar", figsize=(9, 5), color="#2563EB")
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    _finish(title, OUTPUT_DIR / filename, rotate_labels=True)


def main() -> None:
    summaries = grouped_summaries(load_data())
    channels = summaries["channel"].set_index("Channel")
    months = summaries["month"].set_index("Month")
    age_groups = summaries["age_group"].set_index("Age_Group")

    _bar(
        channels["total_revenue"].sort_values(ascending=False),
        "Revenue by Marketing Channel",
        "Known revenue (₹)",
        "revenue_by_channel.png",
    )
    _bar(
        months["total_revenue"],
        "Monthly Revenue Trend",
        "Known revenue (₹)",
        "monthly_revenue_trend.png",
    )
    _bar(
        channels["conversion_rate_percent"].dropna().sort_values(ascending=False),
        "Conversion Rate by Marketing Channel",
        "Conversion rate (%)",
        "conversion_rate_by_channel.png",
    )
    _bar(
        channels["cac"].dropna().sort_values(),
        "Customer Acquisition Cost by Marketing Channel",
        "CAC (₹)",
        "cac_by_channel.png",
    )
    _bar(
        channels["roi_percent"].dropna().sort_values(ascending=False),
        "ROI by Marketing Channel",
        "ROI (%)",
        "roi_by_channel.png",
    )

    financials = channels[["total_ad_spend", "total_revenue"]]
    ax = financials.plot(kind="bar", figsize=(9, 5), color=["#D97706", "#2563EB"])
    ax.set_xlabel("")
    ax.set_ylabel("Amount (₹)")
    _finish("Revenue vs Ad Spend by Marketing Channel", OUTPUT_DIR / "revenue_vs_ad_spend.png", rotate_labels=True)

    _bar(
        age_groups["conversion_rate_percent"].dropna().sort_values(ascending=False),
        "Conversion Rate by Age Group",
        "Conversion rate (%)",
        "conversion_rate_by_age_group.png",
    )

    print("Static charts generated from validated analytics.")


if __name__ == "__main__":
    main()
