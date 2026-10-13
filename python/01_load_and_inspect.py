"""Normalize the original cleaned export into the dashboard-ready CSV."""

from pathlib import Path
import sys

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.marketing_analytics import validate_data


ROOT = Path(__file__).resolve().parents[1]
file_path = ROOT / "data" / "cleaned" / "marketing_campaign_cleaned.csv"
output_path = ROOT / "data" / "cleaned" / "marketing_campaign_cleaned_final.csv"

ORIGINAL_COLUMNS = (
    "Campaign_ID",
    "Campaign_Name",
    "Date",
    "Channel",
    "Customer_ID",
    "Age_Group",
    "Gender",
    "Impressions",
    "Clicks",
    "Leads",
    "Conversions",
    "Ad_Spend",
    "Revenue",
)


def load_original_data(source_path: str | Path) -> pd.DataFrame:
    """Read and select the named columns from the original export.

    ``keep_default_na=False`` keeps literal values such as ``NA`` in text
    columns. Empty Revenue cells are still normalized as missing by
    ``validate_data``, so unavailable revenue is never changed to zero.
    """
    data = pd.read_csv(
        source_path,
        encoding="utf-8-sig",
        dtype="string",
        keep_default_na=False,
    )
    missing = [column for column in ORIGINAL_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Missing expected source columns: {', '.join(missing)}")
    return data.loc[:, ORIGINAL_COLUMNS]


def normalize_data(source_path: str | Path) -> pd.DataFrame:
    """Return the validated original schema without writing a file."""
    return validate_data(load_original_data(source_path))


def main(
    source_path: str | Path | None = None,
    destination_path: str | Path | None = None,
) -> None:
    """Validate the source export and write the dashboard-ready CSV."""
    source = file_path if source_path is None else source_path
    destination = output_path if destination_path is None else Path(destination_path)
    df = normalize_data(source)

    # Keep the source/dashboard convention when serializing the normalized
    # datetime values, and keep missing Revenue cells blank.
    df.to_csv(destination, index=False, na_rep="", date_format="%d-%m-%Y")

    print("Corrected dataset saved successfully!")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("\nColumn names:")
    print(df.columns.tolist())


if __name__ == "__main__":
    main()
