"""Print the validated data-quality summary used by the dashboard."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import health_summary, load_data


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _format_value(value: object) -> str:
    return "N/A" if value is None else str(value)


def main(data_path: str | Path | None = None) -> None:
    df = load_data(data_path)
    health = health_summary(df)

    print("DATASET INFO")
    print("=" * 40)
    df.info()

    print("\nMISSING VALUES")
    print("=" * 40)
    print(df.isnull().sum())

    print("\nDUPLICATE ROWS")
    print("=" * 40)
    print(df.duplicated().sum())

    print("\nANALYTICS HEALTH")
    print("=" * 40)
    print(
        f"Date range: {_format_value(health['start_date'])} "
        f"to {_format_value(health['end_date'])}"
    )
    print(f"Revenue coverage: {_format_percent(health['revenue_coverage_percent'])}")
    print(f"Unknown age rows: {health['unknown_age_rows']}")
    print(f"Unknown gender rows: {health['unknown_gender_rows']}")
    for insight in health["insights"]:
        print(f"- {insight['severity'].upper()}: {insight['title']} - {insight['message']}")


if __name__ == "__main__":
    main()
